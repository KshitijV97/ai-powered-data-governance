"""Policy-as-code: generate warehouse access controls FROM OpenMetadata metadata.

OpenMetadata policies protect the *catalogue* (who can see sample data,
who can edit tags); they do not stop a SQL user from reading the warehouse.
This step closes that gap for the POC: it reads each warehouse table's
column-level PIPEDA tags and table-level PIPEDAPurpose tags from the
OpenMetadata API and generates masked views + grants in Postgres.

Rules (PIPEDA 4.5 limiting use, 4.7 safeguards):
  HighRisk          -> column dropped from the view
  DirectIdentifier  -> pseudonymised (md5) unless the table's purpose matches the role's purpose
  QuasiIdentifier   -> visible (aggregation use)        Financial -> visible
  untagged          -> visible
Roles: marketing_analyst (purpose Marketing), fraud_analyst (purposes FraudPrevention, RegulatoryReporting)
"""

from __future__ import annotations

import json

import psycopg

from poc import config
from poc.om_client import OpenMetadata

ROLE_PURPOSES = {
    "marketing_analyst": {"Marketing"},
    "fraud_analyst": {"FraudPrevention", "RegulatoryReporting"},
}
GOVERNED_SCHEMA = "governed"


def column_sensitivity(col: dict) -> str | None:
    for x in col.get("tags", []):
        if x["tagFQN"].startswith("PIPEDA.") and x.get("source") != "Glossary":
            return x["tagFQN"].split(".", 1)[1]
    return None


def build(om: OpenMetadata) -> tuple[list[str], list[dict]]:
    sql: list[str] = []
    decisions: list[dict] = []
    tables = [
        t
        for t in om.list_all("tables", {"fields": "columns,tags"})
        if t["fullyQualifiedName"].startswith(f"{config.OLAP_SERVICE}.bank_dw.")
        and t["databaseSchema"]["name"] in ("dw", "mart")
    ]
    for role, purposes in ROLE_PURPOSES.items():
        sql += [
            f"REVOKE ALL ON ALL TABLES IN SCHEMA dw, mart FROM {role}",
            f"REVOKE USAGE ON SCHEMA dw, mart FROM {role}",
            f"GRANT CONNECT ON DATABASE bank_dw TO {role}",
            f"CREATE SCHEMA IF NOT EXISTS {GOVERNED_SCHEMA}_{role}",
            f"GRANT USAGE ON SCHEMA {GOVERNED_SCHEMA}_{role} TO {role}",
        ]
        for t in sorted(tables, key=lambda x: x["fullyQualifiedName"]):
            schema, name = t["databaseSchema"]["name"], t["name"]
            table_purposes = {
                x["tagFQN"].split(".", 1)[1]
                for x in t.get("tags", [])
                if x["tagFQN"].startswith("PIPEDAPurpose.")
            }
            purpose_match = bool(purposes & table_purposes)
            exprs, dropped, masked = [], [], []
            for c in t["columns"]:
                s = column_sensitivity(c)
                if s == "HighRisk":
                    dropped.append(c["name"])
                elif s == "DirectIdentifier" and not purpose_match:
                    exprs.append(f"md5({c['name']}::text) AS {c['name']}")
                    masked.append(c["name"])
                else:
                    exprs.append(c["name"])
            view = f"{GOVERNED_SCHEMA}_{role}.{name}"
            where = ""
            if (
                "Marketing" in purposes
                and "Marketing" in table_purposes
                and "customer_key" in [c["name"] for c in t["columns"]]
            ):
                # PIPEDA 4.3: marketing may only see customers whose MARKETING_EMAIL consent is current.
                where = (
                    f" WHERE EXISTS (SELECT 1 FROM dw.dim_consent dc WHERE dc.customer_key = {schema}.{name}.customer_key"
                    " AND dc.purpose = 'MARKETING_EMAIL' AND dc.granted AND dc.withdrawn_on IS NULL)"
                )
            sql += [
                f"DROP VIEW IF EXISTS {view}",
                f"CREATE VIEW {view} AS SELECT {', '.join(exprs)} FROM {schema}.{name}{where}",
                f"GRANT SELECT ON {view} TO {role}",
            ]
            decisions.append(
                {
                    "role": role,
                    "view": view,
                    "source": f"{schema}.{name}",
                    "table_purposes": sorted(table_purposes),
                    "purpose_match": purpose_match,
                    "dropped": dropped,
                    "pseudonymised": masked,
                    "consent_row_filter": bool(where),
                }
            )
    return sql, decisions


def verify() -> list[dict]:
    checks = []
    for role, q in [
        ("marketing_analyst", "SELECT email FROM governed_marketing_analyst.dim_customer LIMIT 1"),
        (
            "marketing_analyst",
            "SELECT email FROM governed_marketing_analyst.marketing_campaign_audience LIMIT 1",
        ),
        (
            "marketing_analyst",
            "SELECT count(*) FROM governed_marketing_analyst.marketing_campaign_audience",
        ),
        ("marketing_analyst", "SELECT email FROM dw.dim_customer LIMIT 1"),
        (
            "marketing_analyst",
            "SELECT full_name FROM governed_marketing_analyst.aml_large_cash_txn LIMIT 1",
        ),
        (
            "fraud_analyst",
            "SELECT full_name FROM governed_fraud_analyst.aml_large_cash_txn LIMIT 1",
        ),
        ("fraud_analyst", "SELECT account_number FROM governed_fraud_analyst.dim_account LIMIT 1"),
    ]:
        try:
            with psycopg.connect(config.dsn("bank_dw", role, config.ANALYST_PASSWORD)) as c:
                v = c.execute(q).fetchone()
                out = f"OK: {str(v[0])[:24]}..." if v else "OK: no rows"
        except psycopg.Error as e:
            out = "DENIED/ERROR: " + str(e).splitlines()[0][:90]
        checks.append({"role": role, "query": q, "result": out})
        print(f"  {role:<18} {q[:78]:<78} -> {out}")
    return checks


def main() -> None:
    om = OpenMetadata.login()
    sql, decisions = build(om)
    with psycopg.connect(config.dsn("bank_dw"), autocommit=True) as conn:
        for stmt in sql:
            conn.execute(stmt)
    for d in decisions:
        if d["dropped"] or d["pseudonymised"] or d["consent_row_filter"]:
            print(
                f"  {d['view']:<52} drop={d['dropped']} pseudonymise={d['pseudonymised']}"
                + (" consent-row-filter" if d["consent_row_filter"] else "")
            )
    checks = verify()
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (config.RESULTS_DIR / "enforcement.json").write_text(
        json.dumps({"decisions": decisions, "checks": checks, "sql": sql}, indent=2)
    )


if __name__ == "__main__":
    main()
