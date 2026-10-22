"""Measure OpenMetadata auto-classification against the synthetic ground truth.

Usage:  python -m poc.evaluate_classification <run-label>

Writes results/classification_<label>.json (per-column detail) and prints
precision / recall / F1 for:
  * the out-of-the-box PII classification (PII.Sensitive / PII.NonSensitive)
  * the Canada-tuned PIPEDA classification (HighRisk + DirectIdentifier)
"""

from __future__ import annotations

import json
import sys
from collections import Counter

from poc import config, ground_truth
from poc.om_client import OpenMetadata

SERVICES = {config.OLTP_SERVICE: "core_banking", config.OLAP_SERVICE: "bank_dw"}
LABEL_TO_PIPEDA = {
    "H": "HighRisk",
    "D": "DirectIdentifier",
    "Q": "QuasiIdentifier",
    "F": "Financial",
    "N": None,
}


def snapshot(om: OpenMetadata) -> list[dict]:
    truth = ground_truth.labels()
    rows = []
    for t in om.list_all("tables", {"fields": "columns,tags"}):
        svc, db, schema, table = t["fullyQualifiedName"].split(".", 3)
        if svc not in SERVICES:
            continue
        for c in t["columns"]:
            tags = c.get("tags", [])
            rows.append(
                {
                    "database": db,
                    "schema": schema,
                    "table": table,
                    "column": c["name"],
                    "truth": truth.get((db, schema, table, c["name"]), "?"),
                    "tags": [
                        {
                            "tagFQN": x["tagFQN"],
                            "labelType": x.get("labelType"),
                            "state": x.get("state"),
                            "reason": (x.get("reason") or "")[:300],
                        }
                        for x in tags
                    ],
                }
            )
    return rows


def _metrics(rows: list[dict], predicted) -> dict:
    tp = fp = fn = tn = 0
    errors = {"false_positives": [], "false_negatives": []}
    for r in rows:
        if r["truth"] == "?":
            continue
        actual, pred = ground_truth.is_positive(r["truth"]), predicted(r)
        name = f"{r['database']}.{r['schema']}.{r['table']}.{r['column']}"
        if actual and pred:
            tp += 1
        elif pred:
            fp += 1
            errors["false_positives"].append(name)
        elif actual:
            fn += 1
            errors["false_negatives"].append(name)
        else:
            tn += 1
    p = tp / (tp + fp) if tp + fp else 0.0
    rcl = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * rcl / (p + rcl) if p + rcl else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": round(p, 3),
        "recall": round(rcl, 3),
        "f1": round(f1, 3),
        **errors,
    }


def _has(r: dict, prefix: str) -> bool:
    return any(t["tagFQN"].startswith(prefix) for t in r["tags"])


def _exact_class_match(r: dict) -> bool:
    expected = LABEL_TO_PIPEDA[r["truth"]]
    if expected is None:
        return not _has(r, "PIPEDA.") or _has(r, "PIPEDA.NonPersonal")
    return _has(r, f"PIPEDA.{expected}")


def evaluate(rows: list[dict]) -> dict:
    res = {
        "columns_total": len(rows),
        "truth_distribution": dict(Counter(r["truth"] for r in rows)),
        "ootb_pii_sensitive": _metrics(rows, lambda r: _has(r, "PII.Sensitive")),
        "pipeda_tuned_highrisk_or_direct": _metrics(
            rows, lambda r: _has(r, "PIPEDA.HighRisk") or _has(r, "PIPEDA.DirectIdentifier")
        ),
    }
    # exact-class agreement for the 5-level PIPEDA scheme
    agree = sum(1 for r in rows if r["truth"] != "?" and _exact_class_match(r))
    res["pipeda_exact_class_accuracy"] = round(
        agree / max(1, sum(1 for r in rows if r["truth"] != "?")), 3
    )
    res["high_risk_recall"] = {
        "ootb_pii_sensitive": _recall_of(rows, "H", lambda r: _has(r, "PII.Sensitive")),
        "pipeda_highrisk": _recall_of(rows, "H", lambda r: _has(r, "PIPEDA.HighRisk")),
    }
    return res


def _recall_of(rows, label, pred) -> str:
    subset = [r for r in rows if r["truth"] == label]
    return f"{sum(1 for r in subset if pred(r))}/{len(subset)}"


def main() -> None:
    label = sys.argv[1] if len(sys.argv) > 1 else "run"
    om = OpenMetadata.login()
    rows = snapshot(om)
    res = evaluate(rows)
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (config.RESULTS_DIR / f"classification_{label}.json").write_text(
        json.dumps({"summary": res, "columns": rows}, indent=2)
    )
    for k in ("ootb_pii_sensitive", "pipeda_tuned_highrisk_or_direct"):
        m = res[k]
        print(
            f"[{label}] {k:<34} P={m['precision']:.3f} R={m['recall']:.3f} F1={m['f1']:.3f} "
            f"(tp={m['tp']} fp={m['fp']} fn={m['fn']})"
        )
    print(
        f"[{label}] high-risk recall: {res['high_risk_recall']}  PIPEDA exact-class acc: "
        f"{res['pipeda_exact_class_accuracy']}"
    )


if __name__ == "__main__":
    main()
