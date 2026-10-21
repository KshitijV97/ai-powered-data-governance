# Pipeline walkthrough (`scripts/run_poc.sh`)

`run_poc.sh` runs 13 numbered steps. Each step is either a **toolbox** module (`python -m poc.<module>`) or the official **`metadata` CLI** inside `om-cli`. Steps are idempotent, so a run can be resumed with `--from N`.

## Overview

```mermaid
flowchart TD
    S1["1 · Start stack<br/>dc.sh up; build toolbox; wait for server"] --> S2
    S2["2 · Synthetic data + ETL<br/>generate_data, etl_to_dw"] --> S3
    S3["3 · Org model<br/>bootstrap_governance org"] --> S4
    S4["4 · Ingest metadata<br/>workflows; metadata ingest ×2"] --> S5
    S5["5 · Baseline classification<br/>metadata classify (PII) ×2; evaluate"] --> S6
    S6["6 · Canada-tuned classification<br/>bootstrap_governance classification;<br/>classify_with.py PIPEDA ×2; evaluate"] --> S7
    S7["7 · Human in the loop<br/>glossary approval; recognizer feedback;<br/>re-classify; evaluate"] --> S8
    S8["8 · Governance metadata + lineage<br/>post_ingestion metadata, lineage"] --> S9
    S9["9 · Profiler + PIPEDA DQ tests<br/>metadata profile ×2; metadata test ×7"] --> S10
    S10["10 · Data products, glossary links,<br/>data contract"] --> S11
    S11["11 · Access tests + warehouse enforcement<br/>human_in_the_loop access; enforce_from_catalog"] --> S12
    S12["12 · AI assistant via MCP<br/>mcp_demo"] --> S13
    S13["13 · Compliance summary<br/>compliance_report"]

    classDef ai fill:#e8f0fe,stroke:#1a56db;
    classDef human fill:#fff4e5,stroke:#c2410c;
    class S5,S6,S12 ai;
    class S7 human;
```

Blue steps use OpenMetadata's AI features; the orange step represents human decisions.

## Step by step

| # | What happens | Runs | Writes |
|---|---|---|---|
| 1 | `docker compose up -d`, build the toolbox image, block until `GET /api/v1/system/version` returns 200 (up to 15 min) | `dc.sh`, `poc.workflows` | – |
| 2 | Create 1 500 synthetic customers (seed 5301) and related rows in `core_banking`; batch-load the warehouse | `poc.generate_data`, `poc.etl_to_dw` | `bank-db` |
| 3 | Teams, persona users, policies, roles, domains, `PIPEDAPurpose` tags, PIPEDA glossary (with reviewers → approval workflow) | `poc.bootstrap_governance org` | OpenMetadata |
| 4 | Render workflow YAMLs with the ingestion-bot token; ingest both database services | `poc.workflows`, `metadata ingest` | `work/workflows/*.yaml`, `work/*.log` |
| 5 | Auto-classify with the out-of-the-box `PII` classification; score against ground truth | `metadata classify`, `poc.evaluate_classification baseline_ootb` | `results/classification_baseline_ootb.json` |
| 6 | Create the `PIPEDA` classification with Canadian recognizers and PIPEDA policies; classify with it | `poc.bootstrap_governance classification`, `om-ext/classify_with.py`, evaluate | `results/classification_canada_tuned.json` |
| 7 | CPO approves glossary terms; steward reports 3 false positives; CPO approves; re-classify | `poc.human_in_the_loop glossary/feedback`, `classify_with.py`, evaluate | `results/workflow_audit.json`, `results/classification_after_feedback.json` |
| 8 | Owners, domains, purposes, retention, tier, column→table sensitivity roll-up; ETL pipeline entity + column lineage | `poc.post_ingestion metadata/lineage` | OpenMetadata |
| 9 | Profile both services; run the 7 PIPEDA test suites (failures are **expected findings**) | `metadata profile`, `metadata test` | `work/dq__*.log` |
| 10 | Data products, glossary-term links on tables, data contract on the marketing mart | `poc.post_ingestion products` | OpenMetadata |
| 11 | Persona access tests against the catalogue; generate masked views + grants in `bank_dw` and verify | `poc.human_in_the_loop access`, `poc.enforce_from_catalog` | `results/workflow_audit.json`, `results/enforcement.json` |
| 12 | Ask four PIPEDA questions through the MCP server | `poc.mcp_demo` | `results/mcp_transcript.json` |
| 13 | Assemble everything into a Markdown report + chart | `poc.compliance_report` | `results/pipeda_compliance_summary.md`, `results/summary.json`, `results/figures/` |

## Who talks to whom during a run

```mermaid
sequenceDiagram
    autonumber
    participant R as run_poc.sh
    participant T as toolbox
    participant C as om-cli
    participant O as OpenMetadata
    participant B as bank-db

    R->>T: generate_data, etl_to_dw
    T->>B: COPY synthetic rows, then INSERT … SELECT into bank_dw
    R->>T: bootstrap_governance org
    T->>O: PUT teams, users, policies, roles, domains, glossary
    R->>T: workflows
    T->>O: fetch ingestion-bot JWT
    T-->>R: work/workflows/*.yaml
    R->>C: metadata ingest -c …metadata.yaml
    C->>B: read information_schema (om_reader)
    C->>O: create services, databases, schemas, tables
    R->>C: metadata classify / classify_with.py
    C->>B: sample 50 rows per table
    C->>O: column tags + sample data
    R->>T: evaluate_classification
    T->>O: GET tables with column tags
    T-->>R: results/classification_*.json
    R->>T: human_in_the_loop, post_ingestion
    T->>O: resolve tasks, patch tags/owners/domains, lineage
    R->>C: metadata profile / test
    C->>B: metrics + test SQL
    C->>O: profiles + test results
    R->>T: enforce_from_catalog
    T->>O: read tags + purposes
    T->>B: CREATE VIEW governed_*, GRANT
    R->>T: mcp_demo, compliance_report
    T->>O: JSON-RPC on /mcp, REST
    T-->>R: results/*
```

## Helper functions in `run_poc.sh`

| Helper | Does |
|---|---|
| `step N "title"` | Prints a banner and returns success only if `N >= --from` |
| `tool <module> …` | `dc.sh run --rm toolbox <module> …` with compose noise filtered out |
| `om <cmd> -c <yaml>` | Runs the `metadata` CLI, logs to `work/<cmd>…log`, aborts the run on failure |
| `omx <yaml> <CLASSIFICATION…>` | Runs `om-ext/classify_with.py` in the ingestion image (see [classification](classification.md#the-classify_withpy-workaround)) |

Data-quality steps deliberately do **not** abort on failure: a failing test is a governance finding, not a script error.

## Evidence produced

```mermaid
flowchart LR
    E5["step 5"] --> f1["classification_baseline_ootb.json"]
    E6["step 6"] --> f2["classification_canada_tuned.json"]
    E7["step 7"] --> f3["classification_after_feedback.json"]
    E7 --> f4["workflow_audit.json"]
    E11["step 11"] --> f4
    E11 --> f5["enforcement.json"]
    E12["step 12"] --> f6["mcp_transcript.json"]
    f1 & f2 & f3 & f4 & f5 & f6 --> E13["step 13<br/>compliance_report"]
    E13 --> f7["pipeda_compliance_summary.md"]
    E13 --> f8["summary.json"]
    E13 --> f9["figures/classification_comparison.png"]
    f9 --> rep["report/figures/"]
```
