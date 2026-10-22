# ai-powered-data-governance

GNG/ELG 5301 team research project (University of Ottawa, Fall 2026):
**AI-powered data governance with OpenMetadata for PIPEDA compliance in a (fictional) Canadian bank.**

> **Research question:** How, and with what professional safeguards, can a Canadian bank use an open-source, AI-assisted metadata platform (OpenMetadata) to operationalize PIPEDA's fair information principles across its OLTP and OLAP data?

The project combines a structured literature review with a reproducible proof of concept (POC). The POC builds a fictional bank, "Borealis Bank of Canada", on synthetic data, governs it with OpenMetadata 2.0.5, and measures what the AI features get right and wrong.

**Headline results:** AI auto-classification F1 rose from **0.783** out of the box to **0.943** with Canada-tuned recognizers and **1.000** after one round of steward feedback (145 columns). PIPEDA data-quality tests caught all five planted defects (consent, retention, stored CVVs, postal codes). Details: [Results and findings](docs/results.md).

## Quick start

Requires Docker Desktop with about 4 GB of memory for the VM.

```bash
cd poc && ./scripts/run_poc.sh
```

The run takes about 15–20 minutes. Then open http://localhost:8585 (login `admin@open-metadata.org` / `admin`, local only). Evidence is written to [`poc/results/`](poc/results/). See the [POC README](poc/README.md) and the [Operations guide](docs/operations.md) for configuration, resets and troubleshooting.

## Documentation

The full index with diagrams is in [`docs/README.md`](docs/README.md).

### Research

| Page | Covers |
|---|---|
| [Research overview](docs/research.md) | Problem, research question and sub-questions, scope, method, answer in brief, limitations |
| [PIPEDA principle mapping](docs/pipeda-mapping.md) | Each of the ten principles → control → code → evidence file |
| [Report guide](docs/report.md) | Report structure, building the PDF, keeping it in sync with the POC, submission checklist |

### Proof of concept

| Page | Covers |
|---|---|
| [Architecture](docs/architecture.md) | Containers, compose layering, volumes, database roles, authentication |
| [Pipeline walkthrough](docs/pipeline.md) | The 13 steps of `run_poc.sh`, the module behind each and what it writes |
| [Data model](docs/data-model.md) | OLTP and warehouse schemas, ETL, column lineage, planted defects |
| [Governance model](docs/governance-model.md) | PIPEDA as classifications, recognizers, teams, roles, policies, domains, glossary, data contract, tests |
| [AI auto-classification and evaluation](docs/classification.md) | The three classification runs, the `classify_with.py` workaround, ground truth, metrics |
| [Human-in-the-loop workflows](docs/human-in-the-loop.md) | Glossary approval and recognizer-feedback workflows |
| [Access control and enforcement](docs/enforcement.md) | Catalogue policies vs. warehouse access; masked views generated from tags |
| [AI assistant (MCP)](docs/mcp.md) | Querying the catalogue through the MCP server; security caveats |
| [Results and findings](docs/results.md) | Numbers from the last run, PIPEDA scorecard, product limitations found |
| [Operations guide](docs/operations.md) | Prerequisites, configuration, commands, troubleshooting, extending, upgrading |

### Reference

| Page | Covers |
|---|---|
| [Glossary](docs/glossary.md) | Privacy, data and OpenMetadata terms |
| [Paper index](references/papers/README.md) | Research papers cited as evidence and where to get each one |
| [Contributing](CONTRIBUTING.md) | Commit message conventions and branch workflow |

## Repository layout

| Folder | Contents |
|---|---|
| [`docs/`](docs/README.md) | Detailed documentation (listed above), with Mermaid diagrams |
| [`poc/`](poc/README.md) | Docker proof of concept: OpenMetadata 2.0.5, the synthetic bank (OLTP + OLAP), governance automation and evaluation scripts; evidence in [`poc/results/`](poc/results/) |
| [`report/`](report/) | Final research report in IEEE format: [`main.tex`](report/main.tex), [`references.bib`](report/references.bib), compiled [`main.pdf`](report/main.pdf) |
| [`deliverables/`](deliverables/) | Team research and project proposal (search log and sources evaluation) |
| [`references/papers/`](references/papers/README.md) | Index of the research papers cited as evidence (PDFs are kept locally, not committed) |
| `Project.pdf` | Course project guidelines |

## Notes

- All data is synthetic and the bank is fictional; no human-participant data is used.
- The report is a **draft** prepared with generative-AI assistance. See the AI-use statement (report Appendix D) and the [submission checklist](docs/report.md#before-submission).
- PIPEDA mappings are the authors' reading of public guidance, not legal advice.
