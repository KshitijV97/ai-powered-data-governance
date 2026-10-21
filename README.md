# ai-powered-data-governance

GNG/ELG 5301 team research project (University of Ottawa, Fall 2026):
**AI-powered data governance with OpenMetadata for PIPEDA compliance in a (fictional) Canadian bank.**

| Folder | Contents |
|---|---|
| [`docs/`](docs/README.md) | Detailed documentation with Mermaid diagrams: architecture, pipeline, data model, governance model, classification, workflows, enforcement, MCP, results, operations |
| [`poc/`](poc/README.md) | Reproducible Docker proof of concept: OpenMetadata 2.0.5 + synthetic bank (OLTP + OLAP), PIPEDA governance automation, evaluation scripts, and the evidence they produce in `poc/results/` |
| [`report/`](report/) | Final research report in IEEE format (`main.tex`, `references.bib`, compiled `main.pdf`) |
| [`deliverables/`](deliverables/) | Team research and project proposal (search log and sources evaluation) |
| [`references/papers/`](references/papers/README.md) | Index of the research papers cited as evidence (PDFs are kept locally, not committed) |
| `Project.pdf` | Course project guidelines |

Commit message conventions: see [CONTRIBUTING.md](CONTRIBUTING.md).

Quick start: `cd poc && ./scripts/run_poc.sh` (Docker Desktop, about 15–20 minutes), then open http://localhost:8585.

All data is synthetic, and the bank is fictional. See the AI-use statement in the report (Appendix D).
