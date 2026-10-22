# PIPEDA principle mapping

One row per fair-information principle in PIPEDA Schedule 1: what the principle asks, which POC control addresses it, where the control is implemented, and which evidence file proves it ran. Use this page as a traceability matrix when writing or checking the report.

The [governance model](governance-model.md#from-pipeda-to-openmetadata) shows the same mapping as a diagram; [results](results.md#4-pipeda-scorecard) gives the scorecard from the last run.

> This is the authors' reading of public guidance for a course project, not legal advice.

## Summary

| Principle | Status (last run) |
|---|---|
| 4.1 Accountability | Implemented |
| 4.2 Identifying purposes | Implemented |
| 4.3 Consent | **Gap detected** (55 withdrawn customers still in the marketing audience) |
| 4.4 Limiting collection | **Gap detected** (1 239 stored CVVs) |
| 4.5 Limiting use, disclosure and retention | **Gap detected** (38 customers past retention, in OLTP and warehouse) |
| 4.6 Accuracy | **Gap detected** (17 malformed postal codes; e-mail rule needs review) |
| 4.7 Safeguards | Implemented (POC scope) |
| 4.8 Openness | Implemented |
| 4.9 Individual access | Partial (no per-person search) |
| 4.10 Challenging compliance | Partial (internal only) |

"Gap detected" is the intended outcome: the defects were planted (see [data model](data-model.md#planted-defects)), and the controls found them.

## Principle by principle

### 4.1 Accountability

**Asks:** an organization is responsible for personal information under its control and designates someone accountable for compliance.

**Control:** a Privacy Office team; the Chief Privacy Officer owns the `PIPEDA` classification and the PIPEDA glossary; every governed table has an owner team and a domain.

**Implemented in:** [`governance_model.py`](../poc/toolbox/poc/governance_model.py) (teams, roles, ownership), [`bootstrap_governance.py`](../poc/toolbox/poc/bootstrap_governance.py) (step 3), [`post_ingestion.py`](../poc/toolbox/poc/post_ingestion.py) (owners and domains, step 8).

**Evidence:** owners and domains in the OpenMetadata UI; `summary.json`. Docs: [Governance model › Organisation](governance-model.md#organisation).

### 4.2 Identifying purposes

**Asks:** purposes are identified at or before collection.

**Control:** `PIPEDAPurpose` tags on 14 tables; a data contract on the marketing mart that states its purpose.

**Implemented in:** `governance_model.py`, `post_ingestion.py` (steps 8 and 10).

**Evidence:** table purposes and the data contract in the UI; `summary.json`. Docs: [Governance model › PIPEDAPurpose](governance-model.md#pipedapurpose-purpose-of-processing), [Data contract](governance-model.md#data-contract).

### 4.3 Consent

**Asks:** knowledge and consent are required for collection, use or disclosure; individuals may withdraw consent.

**Control:** consent data-quality tests (`p4_3_*`) on `core.customer_consent` and `mart.marketing_campaign_audience`; consent-aware row filtering in the generated masked views.

**Implemented in:** `DATA_QUALITY` in [`workflows.py`](../poc/toolbox/poc/workflows.py) (step 9), [`enforce_from_catalog.py`](../poc/toolbox/poc/enforce_from_catalog.py) (step 11).

**Evidence:** `p4_3_consent_not_withdrawn` fails with 55 rows: the ETL ignores `withdrawn_at`. Run logs in `poc/work/dq__*.log`; `enforcement.json`. Docs: [Results §2](results.md#2-data-quality-findings).

### 4.4 Limiting collection

**Asks:** collect only what is necessary for the identified purposes.

**Control:** AI auto-classification builds an inventory of high-risk columns; tests check that CVVs are not stored and that the warehouse keeps only the postal-code prefix.

**Implemented in:** [`classify_with.py`](../poc/om-ext/classify_with.py) and the `PIPEDA` recognizers (steps 5–7); `p4_4_*` tests in `workflows.py`.

**Evidence:** `classification_*.json`; `p4_4_limiting_collection_no_cvv_stored` fails with 1 239 rows. Docs: [Classification](classification.md), [Results §3](results.md#3-personal-information-inventory).

### 4.5 Limiting use, disclosure and retention

**Asks:** use only for the identified purposes; keep only as long as necessary.

**Control:** a `retentionPeriod` on every governed table (assumed seven years after the relationship ends); a retention test on both OLTP and warehouse; column lineage shows where copies live.

**Implemented in:** `post_ingestion.py` (retention, lineage); `p4_5_retention_closed_customers_purged` in `workflows.py`.

**Evidence:** the test fails with the same 38 customers in `core.customer` and `dw.dim_customer`; lineage shows a purge must cover both. Docs: [Data model › ETL and lineage](data-model.md#etl-and-lineage).

### 4.6 Accuracy

**Asks:** personal information is as accurate, complete and up to date as its purpose requires.

**Control:** format and uniqueness tests on postal code, e-mail and SIN.

**Implemented in:** `p4_6_*` tests in `workflows.py`.

**Evidence:** 17 malformed postal codes (planted). The e-mail test flags 240 addresses with accented letters: the *rule* is too strict, which is a human judgement, not a data defect. Docs: [Results §2](results.md#2-data-quality-findings).

### 4.7 Safeguards

**Asks:** security safeguards appropriate to the sensitivity of the information.

**Control:** two layers. (1) Tag-based catalogue policies restrict who can see sample data and profiles in OpenMetadata. (2) Masked views and grants in `bank_dw`, generated from the catalogue's tags and purposes, protect the database itself.

**Implemented in:** policies in `governance_model.py`; `enforce_from_catalog.py`; persona tests in [`human_in_the_loop.py`](../poc/toolbox/poc/human_in_the_loop.py) (step 11).

**Evidence:** `workflow_audit.json` (7/7 catalogue checks), `enforcement.json` (7/7 warehouse checks). Docs: [Enforcement](enforcement.md). Caveat: catalogue policies alone do not protect the database.

### 4.8 Openness

**Asks:** policies and practices about personal information are readily available.

**Control:** a PIPEDA business glossary whose terms go through a reviewer approval workflow; glossary terms linked to tables.

**Implemented in:** `bootstrap_governance.py` (glossary, step 3), `human_in_the_loop.py` (approval, step 7), `post_ingestion.py` (links, step 10).

**Evidence:** glossary approvals in `workflow_audit.json`. Docs: [Human-in-the-loop › Glossary term approval](human-in-the-loop.md#1-glossary-term-approval).

### 4.9 Individual access

**Asks:** on request, an individual is told of the existence, use and disclosure of their information.

**Control:** column-level lineage shows every copy of a person's data; the MCP server lets an assistant answer "where does this data go?"

**Implemented in:** `post_ingestion.py` (lineage), [`mcp_demo.py`](../poc/toolbox/poc/mcp_demo.py) (step 12).

**Evidence:** `mcp_transcript.json`. **Partial:** the catalogue finds *columns*, not a specific person's *rows*; answering an access request still needs queries against the data. Docs: [MCP](mcp.md).

### 4.10 Challenging compliance

**Asks:** individuals can challenge compliance with the accountable person.

**Control:** the recognizer-feedback workflow lets stewards challenge wrong classifications; tasks leave an audit trail with an owner.

**Implemented in:** `human_in_the_loop.py` (step 7).

**Evidence:** recognizer feedback in `workflow_audit.json`; F1 0.943 → 1.000 after feedback. **Partial:** this is an internal challenge process; there is no channel for customers. Docs: [Human-in-the-loop › Recognizer feedback](human-in-the-loop.md#2-recognizer-feedback-false-positive-correction).

## Related regulation

| Source | What the POC uses it for |
|---|---|
| OPC Interpretation bulletin: Sensitive information | Which data categories are treated as `HighRisk` |
| OPC PIPEDA Findings #2020-005 (Desjardins) | Motivation for retention and warehouse controls |
| OSFI Guideline B-13 | Data classification by confidentiality; periodic discovery scans |
| OSFI Guideline E-23 (effective 2027) | Model-risk framing for the AI classifier |
| FINTRAC record keeping; large cash transaction reports | Retention floor (5 years); the `fintrac_lctr_min_amount` test on the AML mart |

Full citations are in [`report/references.bib`](../report/references.bib).
