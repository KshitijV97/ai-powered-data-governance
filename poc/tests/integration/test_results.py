"""Assert the headline results of a completed POC run (see docs/results.md)."""

import re

import pytest

from poc import ground_truth

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------- classification
EXPECTED_RUNS = {
    # run label in summary.json -> (precision, recall, f1, tp, fp, fn, high-risk recall)
    "Out-of-the-box PII": (0.857, 0.72, 0.783, 18, 3, 7, "4/7"),
    "Canada-tuned PIPEDA": (0.893, 1.0, 0.943, 25, 3, 0, "7/7"),
    "Tuned + steward feedback": (1.0, 1.0, 1.0, 25, 0, 0, "7/7"),
}


def test_summary_has_expected_sections(summary):
    assert {"classification", "data_quality", "inventory", "scorecard", "workflows",
            "enforcement_checks"} <= set(summary)


@pytest.mark.parametrize("run", EXPECTED_RUNS)
def test_classification_scores(summary, run):
    by_run = {r["run"]: r for r in summary["classification"]}
    r = by_run[run]
    p, rcl, f1, tp, fp, fn, hr = EXPECTED_RUNS[run]
    assert (r["precision"], r["recall"], r["f1"]) == pytest.approx((p, rcl, f1))
    assert (r["tp"], r["fp"], r["fn"]) == (tp, fp, fn)
    assert r["high_risk_recall"] == hr
    assert len(r["false_positives"]) == fp and len(r["false_negatives"]) == fn


def test_f1_improves_monotonically(summary):
    f1 = [r["f1"] for r in summary["classification"]]
    assert f1 == sorted(f1) and f1[0] < f1[-1]


@pytest.mark.parametrize("file,key,f1", [
    ("classification_baseline_ootb.json", "ootb_pii_sensitive", 0.783),
    ("classification_canada_tuned.json", "pipeda_tuned_highrisk_or_direct", 0.943),
    ("classification_after_feedback.json", "pipeda_tuned_highrisk_or_direct", 1.0),
])
def test_per_run_classification_files(load, file, key, f1):
    s = load(file)["summary"]
    assert s["columns_total"] == 145
    assert s["truth_distribution"] == {"N": 105, "H": 7, "F": 5, "D": 18, "Q": 10}
    assert s[key]["f1"] == pytest.approx(f1)
    m = s[key]
    assert m["tp"] + m["fp"] + m["fn"] + m["tn"] == 145


def test_snapshot_columns_match_ground_truth(load):
    columns = load("classification_after_feedback.json")["columns"]
    keys = {(c["database"], c["schema"], c["table"], c["column"]) for c in columns}
    assert keys == set(ground_truth.labels())
    assert all(c["truth"] == ground_truth.labels()[(c["database"], c["schema"], c["table"], c["column"])]
               for c in columns)


# ---------------------------------------------------------------- data quality
FAILING_DQ = {
    # (test, table) -> failing rows
    ("p4_3_consent_not_withdrawn", "bank_dw.mart.marketing_campaign_audience"): 55,
    ("p4_4_limiting_collection_no_cvv_stored", "core_banking.core.card"): 1239,
    ("p4_5_retention_closed_customers_purged", "core_banking.core.customer"): 38,
    ("p4_5_retention_closed_customers_purged", "bank_dw.dw.dim_customer"): 38,
    ("p4_6_accuracy_email_format", "core_banking.core.customer"): 240,
    ("p4_6_accuracy_postal_code_format", "core_banking.core.customer"): 17,
}


def failing_rows(result: str) -> int:
    """Failing-row count from an OpenMetadata test result message."""
    if m := re.fullmatch(r"Found (\d+) row\(s\)\. .*", result):
        return int(m[1])
    if m := re.fullmatch(r"Found (\d+) value\(s\) matching regex pattern vs (\d+) value\(s\) in the column\.", result):
        return int(m[2]) - int(m[1])
    raise ValueError(f"unrecognised result: {result}")


def test_dq_six_of_twelve_fail(summary):
    dq = summary["data_quality"]
    assert len(dq) == 12
    assert {(t["test"], t["table"]) for t in dq if t["status"] == "Failed"} == set(FAILING_DQ)


@pytest.mark.parametrize("key", FAILING_DQ)
def test_dq_failing_rows(summary, key):
    by_key = {(t["test"], t["table"]): t for t in summary["data_quality"]}
    assert failing_rows(by_key[key]["result"]) == FAILING_DQ[key]


def test_dq_row_count_tests_that_pass_find_nothing(summary):
    passing = [t for t in summary["data_quality"] if t["status"] == "Success" and "row(s)" in t["result"]]
    assert passing and all(failing_rows(t["result"]) == 0 for t in passing)


# ---------------------------------------------------------------- access control
EXPECTED_CATALOGUE = [
    ("maya.marketing", "core_banking.core.customer", "View sampleData", 403),
    ("maya.marketing", "bank_dw.mart.marketing_campaign_audience", "View sampleData", 403),
    ("maya.marketing", "bank_dw.mart.monthly_branch_activity", "View sampleData", 200),
    ("femi.aml", "core_banking.core.customer", "View sampleData", 200),
    ("priya.cpo", "core_banking.core.customer", "View sampleData", 200),
    ("maya.marketing", "core_banking.core.customer", "Add tag, keep PIPEDA.HighRisk", 403),
    ("maya.marketing", "core_banking.core.customer", "Remove PIPEDA.HighRisk tag", 403),
]


def test_catalogue_access_checks(summary):
    tests = summary["workflows"]["access_control_tests"]
    assert [(t["user"], t["table"], t["operation"], t["http"]) for t in tests] == EXPECTED_CATALOGUE


def test_catalogue_tag_tampering_left_highrisk_in_place(summary):
    tampering = [t for t in summary["workflows"]["access_control_tests"] if "PIPEDA.HighRisk_present_after" in t]
    assert len(tampering) == 2 and all(t["PIPEDA.HighRisk_present_after"] for t in tampering)


EXPECTED_WAREHOUSE = [
    # (role, query, expected result prefix)
    ("marketing_analyst", "SELECT email FROM governed_marketing_analyst.dim_customer LIMIT 1", "OK: "),
    ("marketing_analyst", "SELECT email FROM governed_marketing_analyst.marketing_campaign_audience LIMIT 1", "OK: "),
    ("marketing_analyst", "SELECT count(*) FROM governed_marketing_analyst.marketing_campaign_audience", "OK: "),
    ("marketing_analyst", "SELECT email FROM dw.dim_customer LIMIT 1", "DENIED/ERROR: permission denied"),
    ("marketing_analyst", "SELECT full_name FROM governed_marketing_analyst.aml_large_cash_txn LIMIT 1", "OK: "),
    ("fraud_analyst", "SELECT full_name FROM governed_fraud_analyst.aml_large_cash_txn LIMIT 1", "OK: "),
    ("fraud_analyst", "SELECT account_number FROM governed_fraud_analyst.dim_account LIMIT 1",
     'DENIED/ERROR: column "account_number" does not exist'),
]


@pytest.mark.parametrize("source", ["summary", "enforcement"])
def test_warehouse_access_checks(summary, load, source):
    checks = summary["enforcement_checks"] if source == "summary" else load("enforcement.json")["checks"]
    assert len(checks) == len(EXPECTED_WAREHOUSE)
    for check, (role, query, prefix) in zip(checks, EXPECTED_WAREHOUSE, strict=True):
        assert (check["role"], check["query"]) == (role, query)
        assert check["result"].startswith(prefix), check


def test_marketing_analyst_denied_raw_dim_customer_email(summary):
    check = next(c for c in summary["enforcement_checks"]
                 if c["role"] == "marketing_analyst" and c["query"] == "SELECT email FROM dw.dim_customer LIMIT 1")
    assert check["result"] == "DENIED/ERROR: permission denied for schema dw"


def test_marketing_sees_pseudonymised_email_in_dim_customer(summary):
    check = summary["enforcement_checks"][0]
    value = check["result"].removeprefix("OK: ").removesuffix("...")
    assert "@" not in value and all(ch in "0123456789abcdef" for ch in value)   # md5 hex


def test_consent_row_filter_drops_withdrawn_customers(summary):
    # countInSet=611 marketing-flagged rows in the mart, 556 left after the consent filter: 55 withdrawn.
    flag = next(t for t in summary["data_quality"] if t["test"] == "p4_3_consent_marketing_flag_true")
    count = next(c for c in summary["enforcement_checks"] if "count(*)" in c["query"])
    assert flag["result"] == "Found countInSet=611."
    assert count["result"].startswith("OK: 556")


def test_enforcement_decisions(load):
    decisions = {(d["role"], d["source"]): d for d in load("enforcement.json")["decisions"]}
    assert decisions[("fraud_analyst", "dw.dim_account")]["dropped"] == ["account_number"]
    assert "email" in decisions[("marketing_analyst", "dw.dim_customer")]["pseudonymised"]
    assert decisions[("marketing_analyst", "mart.marketing_campaign_audience")]["consent_row_filter"]
    assert decisions[("fraud_analyst", "mart.aml_large_cash_txn")]["pseudonymised"] == []
