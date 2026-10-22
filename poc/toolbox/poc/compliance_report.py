"""Assemble POC evidence into a PIPEDA compliance summary (Markdown + JSON + figures).

Reads results/*.json written by earlier steps plus live data-quality results
from OpenMetadata. Output: results/pipeda_compliance_summary.md, results/summary.json,
results/figures/classification_comparison.png
"""

from __future__ import annotations

import json

from poc import config
from poc import governance_model as gm
from poc.om_client import OpenMetadata
from poc.post_ingestion import fqn

R = config.RESULTS_DIR
RUNS = [("baseline_ootb", "Out-of-the-box PII", "ootb_pii_sensitive"),
        ("canada_tuned", "Canada-tuned PIPEDA", "pipeda_tuned_highrisk_or_direct"),
        ("after_feedback", "Tuned + steward feedback", "pipeda_tuned_highrisk_or_direct")]

# Reference palette (dataviz skill, light mode), categorical slots 1-3 - validated all-pairs.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"


def load(name: str) -> dict:
    p = R / name
    return json.loads(p.read_text()) if p.exists() else {}


def classification_rows() -> list[dict]:
    rows = []
    for label, display, key in RUNS:
        s = load(f"classification_{label}.json").get("summary")
        if not s:
            continue
        m = s[key]
        hr = s["high_risk_recall"]["ootb_pii_sensitive" if key.startswith("ootb") else "pipeda_highrisk"]
        rows.append({"run": display, "precision": m["precision"], "recall": m["recall"], "f1": m["f1"],
                     "tp": m["tp"], "fp": m["fp"], "fn": m["fn"], "high_risk_recall": hr,
                     "false_negatives": m["false_negatives"], "false_positives": m["false_positives"]})
    return rows


def figure(rows: list[dict]) -> str | None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    if not rows:
        return None
    metrics = ["precision", "recall", "f1"]
    fig, ax = plt.subplots(figsize=(6.6, 3.2), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    width, gap = 0.26, 0.02
    for i, r in enumerate(rows):
        for j, m in enumerate(metrics):
            x = j + (i - (len(rows) - 1) / 2) * (width + gap)
            v = r[m]
            ax.add_patch(FancyBboxPatch((x - width / 2, 0), width, v, boxstyle="round,pad=0,rounding_size=0.02",
                                        linewidth=0, facecolor=SERIES[i], mutation_aspect=0.4))
            ax.text(x, v + 0.015, f"{v:.2f}", ha="center", va="bottom", fontsize=7, color=INK2)
    ax.set_xlim(-0.6, len(metrics) - 0.4)
    ax.set_ylim(0, 1.12)
    ax.set_xticks(range(len(metrics)), ["Precision", "Recall", "F1"], fontsize=8, color=INK)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.tick_params(axis="y", labelsize=7, colors=INK2, length=0)
    ax.tick_params(axis="x", length=0)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_visible(False)
    handles = [plt.Rectangle((0, 0), 1, 1, color=SERIES[i]) for i in range(len(rows))]
    ax.legend(handles, [r["run"] for r in rows], loc="upper center", bbox_to_anchor=(0.5, 1.16), ncol=3,
              frameon=False, fontsize=7.5, labelcolor=INK, handlelength=1.0)
    ax.set_ylabel("Score (145 columns, positive = H or D)", fontsize=7, color=INK2)
    fig.tight_layout()
    out = R / "figures" / "classification_comparison.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=SURFACE)
    return str(out)


def dq_rows(om: OpenMetadata) -> list[dict]:
    out = []
    for t in om.list_all("dataQuality/testCases", {"fields": "testCaseResult", "includeAllTests": "true"}):
        r = t.get("testCaseResult") or {}
        table = t["entityLink"].split("::")[2].rstrip(">").split(".", 1)[1]
        out.append({"test": t["name"], "table": table, "status": r.get("testCaseStatus"),
                    "result": (r.get("result") or "")[:140]})
    return sorted(out, key=lambda x: x["test"])


SCORECARD = [
    ("4.1 Accountability", "Privacy Office team; CPO owns PIPEDA classification and glossary; table owners assigned",
     "Implemented"),
    ("4.2 Identifying purposes", "PIPEDAPurpose tags on 14 tables; data contract states purpose", "Implemented"),
    ("4.3 Consent", "Consent DQ tests; consent row filter in governed marketing view", "Gap detected (55 withdrawn customers in audience)"),
    ("4.4 Limiting collection", "HighRisk inventory exposes stored CVVs and legacy SINs", "Gap detected (1,239 CVVs stored)"),
    ("4.5 Limiting use, disclosure, retention", "retentionPeriod on tables; retention DQ tests", "Gap detected (38 customers past retention)"),
    ("4.6 Accuracy", "Format and uniqueness DQ tests", "Gap detected (17 invalid postal codes; e-mail rule needs review)"),
    ("4.7 Safeguards", "Tag-based catalogue policies; catalogue-generated masked views in warehouse", "Implemented (POC scope)"),
    ("4.8 Openness", "Approved PIPEDA glossary published in catalogue", "Implemented"),
    ("4.9 Individual access", "Column-level lineage OLTP->OLAP; PI inventory; MCP lineage query", "Partially (no per-person search)"),
    ("4.10 Challenging compliance", "Recognizer feedback workflow; task audit trail", "Partially (internal workflow only)"),
]


def main() -> None:
    om = OpenMetadata.login()
    cls = classification_rows()
    fig = figure(cls)
    dq = dq_rows(om)
    audit = load("workflow_audit.json")
    enforcement = load("enforcement.json")
    mcp = load("mcp_transcript.json")

    inventory = []
    for key, (domain, owner, purposes, _retention, tier) in gm.TABLE_METADATA.items():
        t = om.table(fqn(key), fields="tags,owners,domains")
        if t:
            inventory.append({"table": key, "domain": domain, "owner": owner, "purposes": purposes,
                              "retention": t.get("retentionPeriod"), "tier": tier,
                              "sensitivity": [x["tagFQN"] for x in t.get("tags", []) if x["tagFQN"].startswith("PIPEDA.")]})

    summary = {"classification": cls, "data_quality": dq, "inventory": inventory, "scorecard": SCORECARD,
               "workflows": audit, "enforcement_checks": enforcement.get("checks", []),
               "mcp_tools": mcp.get("tools", []), "figure": fig}
    (R / "summary.json").write_text(json.dumps(summary, indent=2))

    md = ["# Borealis Bank (fictional) - PIPEDA governance POC results", "",
          "Generated by `poc.compliance_report` from OpenMetadata 2.0.5. All data is synthetic.", "",
          "## 1. AI auto-classification vs. ground truth (145 columns)", "",
          "| Run | Precision | Recall | F1 | TP | FP | FN | High-risk recall |", "|---|---|---|---|---|---|---|---|"]
    md += [f"| {r['run']} | {r['precision']:.3f} | {r['recall']:.3f} | {r['f1']:.3f} | {r['tp']} | {r['fp']} | "
           f"{r['fn']} | {r['high_risk_recall']} |" for r in cls]
    md += ["", "![classification](figures/classification_comparison.png)", "",
           "## 2. PIPEDA data-quality tests", "", "| Test | Table | Status | Result |", "|---|---|---|---|"]
    md += [f"| {d['test']} | {d['table']} | {d['status']} | {d['result']} |" for d in dq]
    md += ["", "## 3. Personal-information inventory", "",
           "| Table | Sensitivity | Purposes | Retention | Owner | Domain |", "|---|---|---|---|---|---|"]
    md += [f"| {i['table']} | {', '.join(i['sensitivity']) or '-'} | {', '.join(i['purposes']) or '-'} | "
           f"{i['retention']} | {i['owner']} | {i['domain']} |" for i in inventory]
    md += ["", "## 4. Access-control tests (catalogue)", "", "| User | Table | Operation | HTTP |", "|---|---|---|---|"]
    md += [f"| {a['user']} | {a['table']} | {a['operation']} | {a['http']} |" for a in audit.get("access_control_tests", [])]
    md += ["", "## 5. Warehouse enforcement generated from the catalogue", "", "| Role | Query | Result |", "|---|---|---|"]
    md += [f"| {c['role']} | `{c['query']}` | {c['result']} |" for c in enforcement.get("checks", [])]
    md += ["", "## 6. PIPEDA principle scorecard", "", "| Principle | Control in POC | Status |", "|---|---|---|"]
    md += [f"| {p} | {c} | {s} |" for p, c, s in SCORECARD]
    (R / "pipeda_compliance_summary.md").write_text("\n".join(md) + "\n")
    print(f"  wrote {R / 'pipeda_compliance_summary.md'}, summary.json, {fig}")


if __name__ == "__main__":
    main()
