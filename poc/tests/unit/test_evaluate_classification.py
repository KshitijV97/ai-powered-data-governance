"""Precision / recall / F1 maths in evaluate_classification."""

import pytest

from poc.evaluate_classification import _metrics, evaluate


def row(truth, *tags, col="c"):
    return {"database": "db", "schema": "s", "table": "t", "column": col, "truth": truth,
            "tags": [{"tagFQN": t} for t in tags]}


def flagged(r):
    return bool(r["tags"])


def test_metrics_counts_and_scores():
    rows = [row("H", "x", col="tp1"), row("D", "x", col="tp2"), row("D", col="fn1"),
            row("N", "x", col="fp1"), row("Q", col="tn1"), row("F", col="tn2")]
    m = _metrics(rows, flagged)
    assert (m["tp"], m["fp"], m["fn"], m["tn"]) == (2, 1, 1, 2)
    assert m["precision"] == pytest.approx(0.667)
    assert m["recall"] == pytest.approx(0.667)
    assert m["f1"] == pytest.approx(0.667)
    assert m["false_positives"] == ["db.s.t.fp1"]
    assert m["false_negatives"] == ["db.s.t.fn1"]


def test_metrics_asymmetric_precision_recall():
    rows = [row("H", "x")] + [row("D") for _ in range(3)]
    m = _metrics(rows, flagged)
    assert m["precision"] == 1.0
    assert m["recall"] == 0.25
    assert m["f1"] == 0.4


def test_metrics_perfect():
    m = _metrics([row("H", "x"), row("N")], flagged)
    assert (m["precision"], m["recall"], m["f1"]) == (1.0, 1.0, 1.0)


def test_metrics_empty_input_is_zero_not_error():
    m = _metrics([], flagged)
    assert (m["tp"], m["fp"], m["fn"], m["tn"]) == (0, 0, 0, 0)
    assert (m["precision"], m["recall"], m["f1"]) == (0.0, 0.0, 0.0)


def test_metrics_no_predictions():
    m = _metrics([row("H"), row("D"), row("N")], flagged)
    assert m["precision"] == 0.0 and m["recall"] == 0.0 and m["f1"] == 0.0
    assert m["fn"] == 2


def test_metrics_only_false_positives():
    m = _metrics([row("N", "x"), row("Q", "x")], flagged)
    assert m["fp"] == 2
    assert (m["precision"], m["recall"], m["f1"]) == (0.0, 0.0, 0.0)


def test_metrics_skips_unknown_truth():
    m = _metrics([row("?", "x"), row("H", "x")], flagged)
    assert (m["tp"], m["fp"], m["fn"], m["tn"]) == (1, 0, 0, 0)


def test_evaluate_ootb_vs_pipeda():
    rows = [
        row("H", "PIPEDA.HighRisk", "PII.Sensitive"),
        row("D", "PIPEDA.DirectIdentifier"),
        row("Q", "PIPEDA.QuasiIdentifier", "PII.Sensitive"),
        row("N"),
    ]
    res = evaluate(rows)
    assert res["columns_total"] == 4
    assert res["truth_distribution"] == {"H": 1, "D": 1, "Q": 1, "N": 1}
    ootb = res["ootb_pii_sensitive"]
    assert (ootb["tp"], ootb["fp"], ootb["fn"]) == (1, 1, 1)
    tuned = res["pipeda_tuned_highrisk_or_direct"]
    assert (tuned["tp"], tuned["fp"], tuned["fn"], tuned["f1"]) == (2, 0, 0, 1.0)
    assert res["pipeda_exact_class_accuracy"] == 1.0
    assert res["high_risk_recall"] == {"ootb_pii_sensitive": "1/1", "pipeda_highrisk": "1/1"}


def test_evaluate_exact_class_accuracy_penalises_wrong_level():
    rows = [row("H", "PIPEDA.DirectIdentifier"), row("N", "PIPEDA.Financial"),
            row("N", "PIPEDA.NonPersonal"), row("F", "PIPEDA.Financial")]
    assert evaluate(rows)["pipeda_exact_class_accuracy"] == 0.5


def test_evaluate_empty():
    res = evaluate([])
    assert res["columns_total"] == 0
    assert res["pipeda_exact_class_accuracy"] == 0.0
    assert res["high_risk_recall"]["pipeda_highrisk"] == "0/0"


def test_evaluate_nonpersonal_tag_on_high_risk_column_is_not_a_match():
    assert evaluate([row("H", "PIPEDA.NonPersonal")])["pipeda_exact_class_accuracy"] == 0.0
