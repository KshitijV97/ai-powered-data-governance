"""Governance steps that need ingested tables.

python -m poc.post_ingestion metadata   # owners, domains, purposes, retention, tier, sensitivity roll-up
python -m poc.post_ingestion lineage    # ETL pipeline entity + column-level lineage OLTP -> OLAP
python -m poc.post_ingestion products   # data products, glossary links, data contract
"""

from __future__ import annotations

import sys

from poc import config
from poc import governance_model as gm
from poc.etl_to_dw import DW_LINEAGE, LINEAGE
from poc.om_client import OMError, OpenMetadata

DB_SERVICE = {"core_banking": config.OLTP_SERVICE, "bank_dw": config.OLAP_SERVICE}
SENSITIVITY_ORDER = ["HighRisk", "DirectIdentifier", "QuasiIdentifier", "Financial"]


def fqn(db_table: str) -> str:
    """'bank_dw.dw.dim_customer' -> 'borealis_enterprise_dw_olap.bank_dw.dw.dim_customer'"""
    return f"{DB_SERVICE[db_table.split('.')[0]]}.{db_table}"


def tag_label(tag_fqn: str, label_type: str = "Manual", state: str = "Confirmed") -> dict:
    return {"tagFQN": tag_fqn, "source": "Classification", "labelType": label_type, "state": state}


def ref(e: dict, t: str) -> dict:
    return {"id": e["id"], "type": t}


# ---------------------------------------------------------------- metadata
def table_metadata(om: OpenMetadata) -> None:
    teams = {t: om.by_name("teams", t) for t in {v[1] for v in gm.TABLE_METADATA.values()}}
    for key, (domain, owner, purposes, retention, tier) in gm.TABLE_METADATA.items():
        t = om.table(fqn(key))
        if not t:
            print(f"  ! {key} not found")
            continue
        tags = [
            x
            for x in t.get("tags", [])
            if x.get("source") == "Glossary"
            or not x["tagFQN"].startswith(("PIPEDAPurpose.", "Tier.", "PIPEDA."))
        ]
        tags += [tag_label(f"PIPEDAPurpose.{p}") for p in purposes] + [tag_label(f"Tier.{tier}")]
        tags += rollup(t)
        dom = om.by_name("domains", domain)
        om.patch(
            f"/v1/tables/{t['id']}",
            [
                {"op": "add", "path": "/tags", "value": tags},
                {"op": "add", "path": "/owners", "value": [ref(teams[owner], "team")]},
                {"op": "add", "path": "/domains", "value": [ref(dom, "domain")]},
                {"op": "add", "path": "/retentionPeriod", "value": retention},
            ],
        )
        print(
            f"  {key:<44} domain={domain:<14} owner={owner:<16} retention={retention:<5} "
            f"purposes={','.join(purposes) or '-'}  sensitivity={', '.join(x['tagFQN'] for x in rollup(t)) or '-'}"
        )


def rollup(table: dict) -> list[dict]:
    """Table inherits its most sensitive column-level PIPEDA tag (needed for table-level policies)."""
    col_tags = {
        x["tagFQN"].split(".", 1)[1]
        for c in table["columns"]
        for x in c.get("tags", [])
        if x["tagFQN"].startswith("PIPEDA.")
    }
    for level in SENSITIVITY_ORDER:
        if level in col_tags:
            return [tag_label(f"PIPEDA.{level}", label_type="Automated")]
    return []


# ---------------------------------------------------------------- lineage
def lineage(om: OpenMetadata) -> None:
    svc = om.put(
        "/v1/services/pipelineServices",
        {
            "name": "borealis_batch_etl",
            "serviceType": "CustomPipeline",
            "description": "Borealis Bank nightly batch ETL (poc/toolbox/poc/etl_to_dw.py)",
            "connection": {"config": {"type": "CustomPipeline"}},
        },
    )
    pipe = om.put(
        "/v1/pipelines",
        {
            "name": "nightly_oltp_to_dw",
            "displayName": "Nightly OLTP -> warehouse load",
            "service": svc["fullyQualifiedName"],
            "description": "Extracts core_banking (OLTP) into the bank_dw star schema and marts. Known defect: the "
            "marketing audience extract ignores consent withdrawal (see data-quality results).",
            "tasks": [
                {"name": t.replace(".", "_"), "displayName": f"load {t}"}
                for t in list(LINEAGE) + list(DW_LINEAGE)
            ],
        },
    )
    edges = 0
    for target, mapping, src_db in [(t, m, "core_banking") for t, m in LINEAGE.items()] + [
        (t, m, "bank_dw") for t, m in DW_LINEAGE.items()
    ]:
        tgt = om.table(fqn(f"bank_dw.{target}"), fields="columns")
        by_source: dict[str, list] = {}
        for tcol, sources in mapping.items():
            for s in sources:
                st = s.rsplit(".", 1)[0]
                by_source.setdefault(st, []).append((s, tcol))
        for src_table, pairs in by_source.items():
            src = om.table(fqn(f"{src_db}.{src_table}"), fields="columns")
            cols: dict[str, list] = {}
            for s, tcol in pairs:
                cols.setdefault(f"{tgt['fullyQualifiedName']}.{tcol}", []).append(
                    f"{src['fullyQualifiedName']}.{s.rsplit('.', 1)[1]}"
                )
            om.put(
                "/v1/lineage",
                {
                    "edge": {
                        "fromEntity": ref(src, "table"),
                        "toEntity": ref(tgt, "table"),
                        "lineageDetails": {
                            "pipeline": ref(pipe, "pipeline"),
                            "source": "PipelineLineage",
                            "description": f"etl_to_dw.py loads {target}",
                            "columnsLineage": [
                                {"fromColumns": f, "toColumn": t} for t, f in cols.items()
                            ],
                        },
                    }
                },
            )
            edges += 1
    print(
        f"  pipeline {pipe['fullyQualifiedName']} + {edges} table-level edges with column lineage"
    )


# ---------------------------------------------------------------- products, glossary, contract
GLOSSARY_LINKS = {
    "core_banking.core.customer_consent": ["PIPEDAGlossary.Consent"],
    "bank_dw.dw.dim_consent": ["PIPEDAGlossary.Consent"],
    "bank_dw.mart.marketing_campaign_audience": [
        "PIPEDAGlossary.Consent",
        "PIPEDAGlossary.LimitingUseDisclosureRetention",
    ],
    "core_banking.core.customer": ["PIPEDAGlossary.PersonalInformation"],
    "core_banking.core.card": ["PIPEDAGlossary.Safeguards"],
    "core_banking.kyc.identity_document": ["PIPEDAGlossary.Safeguards"],
}


def products(om: OpenMetadata) -> None:
    for name, display, domain, assets in gm.DATA_PRODUCTS:
        refs = [ref(om.table(fqn(a), fields=""), "table") for a in assets]
        dp = om.put(
            "/v1/dataProducts",
            {
                "name": name,
                "displayName": display,
                "domains": [domain],
                "description": f"{display} data product ({domain}).",
                "owners": [
                    ref(
                        om.by_name(
                            "teams", gm.DOMAINS[[d[0] for d in gm.DOMAINS].index(domain)][3]
                        ),
                        "team",
                    )
                ],
            },
        )
        try:
            om.put(
                f"/v1/dataProducts/{om.q(dp['fullyQualifiedName'])}/assets/add", {"assets": refs}
            )
        except OMError as e:
            print(f"  ! assets for {name}: {e}")
        print(f"  data product {name}: {len(refs)} assets")

    for key, terms in GLOSSARY_LINKS.items():
        t = om.table(fqn(key), fields="tags")
        tags = t.get("tags", []) + [
            {"tagFQN": term, "source": "Glossary", "labelType": "Manual", "state": "Confirmed"}
            for term in terms
        ]
        try:
            om.patch(f"/v1/tables/{t['id']}", [{"op": "add", "path": "/tags", "value": tags}])
            print(f"  glossary {key}: {', '.join(terms)}")
        except OMError as e:
            print(f"  ! glossary link {key} (terms must be Approved first): {str(e)[:160]}")

    contract(om)


def contract(om: OpenMetadata) -> None:
    t = om.table(fqn("bank_dw.mart.marketing_campaign_audience"), fields="columns")
    cpo = om.by_name("users", "priya.cpo")
    tests = om.get(
        "/v1/dataQuality/testCases",
        {
            "entityLink": f"<#E::table::{t['fullyQualifiedName']}>",
            "limit": 50,
            "includeAllTests": "true",
        },
    ).get("data", [])
    body = {
        "name": "marketing_campaign_audience_pipeda_contract",
        "displayName": "Marketing audience - PIPEDA contract",
        "entity": ref(t, "table"),
        "entityStatus": "Approved",
        "description": "Producer: Data Engineering. Consumer: Retail Marketing. The audience may only contain "
        "customers with current, express MARKETING_EMAIL consent (PIPEDA 4.3) and is retained 90 days (4.5).",
        "owners": [ref(om.by_name("teams", "DataEngineering"), "team")],
        "reviewers": [ref(cpo, "user")],
        "termsOfUse": "Use only for e-mail campaigns covered by the customer's express consent. Do not join with "
        "transaction data or disclose outside Borealis Bank. Honour withdrawals within 10 business days.",
        "schema": [{"name": c["name"], "dataType": c["dataType"]} for c in t["columns"]],
        "semantics": [
            {
                "name": "Has an owner",
                "description": "Accountability (4.1): the mart must have an owner.",
                "rule": '{"and":[{"some":[{"var":"owners"},{"!=":[{"var":"fullyQualifiedName"},null]}]}]}',
                "enabled": True,
            },
            {
                "name": "Purpose identified",
                "description": "Identifying purposes (4.2): tagged PIPEDAPurpose.Marketing.",
                "rule": '{"some":[{"var":"tags"},{"==":[{"var":"tagFQN"},"PIPEDAPurpose.Marketing"]}]}',
                "enabled": True,
            },
            {
                "name": "Sensitivity classified",
                "description": "Safeguards (4.7): a PIPEDA sensitivity tag is present.",
                "rule": '{"some":[{"var":"tags"},{"in":["PIPEDA.",{"var":"tagFQN"}]}]}',
                "enabled": True,
            },
        ],
        "qualityExpectations": [ref(tc, "testCase") for tc in tests],
        "security": {
            "dataClassification": "PIPEDA.DirectIdentifier, Confidential",
            "policies": [
                {"accessPolicy": "PIPEDASafeguardsNeedToKnow", "identities": ["RetailMarketing"]}
            ],
        },
        "sla": {
            "refreshFrequency": {"interval": 1, "unit": "day"},
            "retention": {"period": 90, "unit": "day"},
        },
    }
    existing = om.by_name("dataContracts", f"{t['fullyQualifiedName']}.dataContract_{body['name']}")
    c = om.put("/v1/dataContracts", body) if existing else om.post("/v1/dataContracts", body)
    print(f"  data contract {c['name']} with {len(tests)} quality expectations, 3 semantics rules")


def main() -> None:
    step = sys.argv[1] if len(sys.argv) > 1 else "metadata"
    om = OpenMetadata.login()
    {"metadata": table_metadata, "lineage": lineage, "products": products, "contract": contract}[
        step
    ](om)


if __name__ == "__main__":
    main()
