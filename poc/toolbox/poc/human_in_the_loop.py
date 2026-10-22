"""Exercise OpenMetadata's governance workflows as the POC personas.

    python -m poc.human_in_the_loop glossary   # CPO approves PIPEDA glossary terms (GlossaryTermApprovalWorkflow)
    python -m poc.human_in_the_loop feedback   # steward reports false positives -> CPO approves (RecognizerFeedbackReviewWorkflow)
    python -m poc.human_in_the_loop access     # policy tests: what can Marketing / AML / CPO actually see?

These calls stand in for clicks in the UI. They are scripted so the POC is
reproducible; in production each decision is a person's judgement, and the
task history in OpenMetadata is the audit trail (PIPEDA 4.1, 4.10).
"""

from __future__ import annotations

import json
import sys
import time

from poc import config
from poc import governance_model as gm
from poc.bootstrap_governance import PERSONA_PASSWORD  # local test accounts
from poc.om_client import OMError, OpenMetadata

AUDIT = config.RESULTS_DIR / "workflow_audit.json"


def as_user(name: str) -> OpenMetadata:
    return OpenMetadata.login(f"{name}@borealis.example", PERSONA_PASSWORD)


def _audit(section: str, rows: list) -> None:
    data = json.loads(AUDIT.read_text()) if AUDIT.exists() else {}
    data[section] = rows
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT.write_text(json.dumps(data, indent=2))


def _open_tasks(om: OpenMetadata, task_type: str, wait: int = 60) -> list[dict]:
    deadline = time.time() + wait
    while True:
        tasks = [t for t in om.get("/v1/tasks/assigned", {"limit": 100, "status": "Open"}).get("data", [])
                 if t.get("type") == task_type and t.get("status") == "Open"]
        if tasks or time.time() > deadline:
            return tasks
        time.sleep(3)


def glossary() -> None:
    cpo = as_user("priya.cpo")
    rows = []
    for t in _open_tasks(cpo, "RequestApproval"):
        term = t["about"]["fullyQualifiedName"]
        r = cpo.post(f"/v1/tasks/{t['id']}/resolve", {"resolutionType": "Approved",
                                                       "comment": "Reviewed against PIPEDA Schedule 1 - approved by CPO."})
        rows.append({"task": t.get("name"), "term": term, "resolution": "Approved", "status": r.get("status")})
    time.sleep(5)
    admin = OpenMetadata.login()
    statuses = {g["fullyQualifiedName"]: g.get("entityStatus")
                for g in admin.list_all("glossaryTerms", {"glossary": admin.by_name("glossaries", gm.GLOSSARY["name"])["id"]})}
    print(f"  CPO resolved {len(rows)} approval tasks; term status: {sorted(set(statuses.values()))}")
    _audit("glossary_approval", {"tasks": rows, "term_status": statuses})


FALSE_POSITIVES = [
    # (table FQN, column, tag, feedback type, reason, comment, suggested tag)
    (f"{config.OLTP_SERVICE}.core_banking.core.branch", "city", "PIPEDA.DirectIdentifier", "FALSE_POSITIVE",
     "PUBLIC_INFORMATION", "Branch cities are public business addresses, not customer PI.", "PIPEDA.NonPersonal"),
    (f"{config.OLAP_SERVICE}.bank_dw.dw.dim_branch", "city", "PIPEDA.DirectIdentifier", "FALSE_POSITIVE",
     "PUBLIC_INFORMATION", "Branch dimension: public branch locations.", "PIPEDA.NonPersonal"),
    (f"{config.OLTP_SERVICE}.core_banking.core.customer", "city", "PIPEDA.DirectIdentifier", "INCORRECT_CLASSIFICATION",
     "OTHER", "Customer city alone is a quasi-identifier, not a direct identifier.", "PIPEDA.QuasiIdentifier"),
]


def feedback() -> None:
    steward = as_user("dan.steward")
    submitted = []
    for table, col, tag, ftype, reason, comment, suggested in FALSE_POSITIVES:
        body = {"entityLink": f"<#E::table::{table}::columns::{col}>", "tagFQN": tag, "feedbackType": ftype,
                "userReason": reason, "userComments": comment, "suggestedTag": suggested}
        try:
            fb = steward.post(f"/v1/tags/name/{steward.q(tag)}/feedback", body)
            submitted.append({"column": f"{table}.{col}", "feedbackId": fb.get("id"), "status": fb.get("status")})
            print(f"  steward feedback on {table.split('.', 1)[1]}.{col}: {ftype}")
        except OMError as e:
            print(f"  ! feedback {table}.{col}: {str(e)[:200]}")

    cpo = as_user("priya.cpo")
    resolved = []
    for t in _open_tasks(cpo, "RecognizerFeedbackApproval"):
        r = cpo.post(f"/v1/tasks/{t['id']}/resolve", {"resolutionType": "Approved",
                                                       "comment": "Agree - add recognizer exception for this column."})
        resolved.append({"task": t.get("name"), "about": (t.get("about") or {}).get("fullyQualifiedName"),
                         "status": r.get("status")})
    print(f"  CPO approved {len(resolved)} recognizer-feedback tasks")
    time.sleep(5)
    admin = OpenMetadata.login()
    after = []
    for table, col, tag, *_ in FALSE_POSITIVES:
        t = admin.table(table, fields="columns,tags")
        c = next(c for c in t["columns"] if c["name"] == col)
        tags = [x["tagFQN"] for x in c.get("tags", [])]
        tagent = admin.by_name("tags", tag, "recognizers")
        exceptions = sum(len(r.get("exceptionList") or []) for r in tagent.get("recognizers") or [])
        after.append({"column": f"{table}.{col}", "tags_after": tags, "recognizer_exceptions_on_tag": exceptions})
        print(f"  {table.split('.', 1)[1]}.{col}: tags now {tags}; exceptions on {tag}: {exceptions}")
    _audit("recognizer_feedback", {"submitted": submitted, "resolved": resolved, "after": after})


ACCESS_TESTS = [
    ("maya.marketing", "core_banking.core.customer", "sampleData"),
    ("maya.marketing", "bank_dw.mart.marketing_campaign_audience", "sampleData"),
    ("maya.marketing", "bank_dw.mart.monthly_branch_activity", "sampleData"),
    ("femi.aml", "core_banking.core.customer", "sampleData"),
    ("priya.cpo", "core_banking.core.customer", "sampleData"),
]


def access() -> None:
    from poc.post_ingestion import fqn
    admin = OpenMetadata.login()
    rows = []
    for user, table, what in ACCESS_TESTS:
        om = as_user(user)
        t = admin.table(fqn(table), fields="")
        r = om.s.get(f"{om.api}/v1/tables/{t['id']}/{what}")
        masked = None
        if r.status_code == 200:
            sd = (r.json().get("sampleData") or {})
            rows_ = sd.get("rows") or []
            masked = sum(1 for row in rows_[:5] for v in row if v == "********") if rows_ else None
        rows.append({"user": user, "table": table, "operation": f"View {what}", "http": r.status_code,
                     "masked_values_in_first_5_rows": masked})
        print(f"  {user:<15} {what:<10} {table:<42} -> HTTP {r.status_code}"
              + (f" (masked cells in first 5 rows: {masked})" if masked is not None else ""))

    # Tag integrity (PIPEDAClassificationIntegrity). Two edits by the marketing analyst on core.customer:
    #   (a) add a purpose tag while keeping PIPEDA.HighRisk  -> expected 403
    #   (b) remove PIPEDA.HighRisk itself                     -> observed 200: the deny rule's matchAnyTag()
    #       is evaluated on the entity AFTER the change, so a tag-conditioned rule cannot protect its own tag.
    om = as_user("maya.marketing")
    t = admin.table(fqn("core_banking.core.customer"), fields="tags")
    original = t["tags"]
    hdr = {"Content-Type": "application/json-patch+json"}
    edits = [
        ("Add tag, keep PIPEDA.HighRisk", original + [{"tagFQN": "PIPEDAPurpose.Marketing", "source": "Classification",
                                                     "labelType": "Manual", "state": "Confirmed"}]),
        ("Remove PIPEDA.HighRisk tag", [x for x in original if not x["tagFQN"].startswith("PIPEDA.")]),
    ]
    for label, value in edits:
        r = om.s.patch(f"{om.api}/v1/tables/{t['id']}", json=[{"op": "add", "path": "/tags", "value": value}], headers=hdr)
        after = [x["tagFQN"] for x in admin.table(fqn("core_banking.core.customer"), fields="tags")["tags"]]
        rows.append({"user": "maya.marketing", "table": "core_banking.core.customer", "operation": label,
                     "http": r.status_code, "PIPEDA.HighRisk_present_after": "PIPEDA.HighRisk" in after})
        print(f"  maya.marketing  {label:<34} on core.customer -> HTTP {r.status_code}; "
              f"HighRisk still present: {'PIPEDA.HighRisk' in after}")
    admin.patch(f"/v1/tables/{t['id']}", [{"op": "add", "path": "/tags", "value": original}])   # restore
    _audit("access_control_tests", rows)


def main() -> None:
    step = sys.argv[1] if len(sys.argv) > 1 else "glossary"
    {"glossary": glossary, "feedback": feedback, "access": access}[step]()


if __name__ == "__main__":
    main()
