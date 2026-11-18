# Team activity 2: develop your recommendations

Team 2, GNG/ELG 5301, Fall 2026. Six significant findings from the draft report ([`report/main.tex`](../report/main.tex)), each mapped to a practical recommendation. Numbers come from the POC evidence in [`poc/results/`](../poc/results/); sources are listed at the end with the key used in the report's bibliography.

> **Raw material for paraphrasing.** Each finding is written as short, factual points rather than finished prose, so the team can rewrite it in its own words. Claude Code helped prepare this draft. Before submission, the team should check every claim against the cited source, rewrite it, and cover it in the AI-use statement (report Appendix D).

## Overview

| # | Finding | Recommendation | Owner | Horizon |
|---|---|---|---|---|
| 1 | Out-of-the-box AI classification is not Canadian-aware; accuracy depends on the deployment | Measure the classifier on local schemas and add Canadian recognizers before relying on it | CDO + data platform | 0–3 months |
| 2 | Human feedback fixes errors, but oversight is fragile | Keep AI tags as suggestions; design targeted, measured human review | CPO | 0–3 months |
| 3 | Metadata tests detect PIPEDA defects but do not fix them, and only business-rule tests catch them | Write PIPEDA rules as cross-table tests and data contracts with named incident owners | Data stewards | 3–12 months |
| 4 | Catalogue policies do not reach the database, and tag-driven safeguards fail open | Generate warehouse controls from catalogue tags and treat untagged columns as sensitive | Data platform | 3–12 months |
| 5 | Lineage turns the catalogue into an inventory that exposes over-collection and copied defects | Register lineage for every pipeline that moves personal information and drive purges from it | Data engineering | 3–12 months |
| 6 | The catalogue and its AI assistant are a high-value attack surface | Lock down who and what can change metadata; connect AI assistants read-only | Security | 0–3 months |

---

## Finding 1: Out-of-the-box AI classification is not Canadian-aware

### 1. Finding (the core result)

- OpenMetadata 2.0.5's auto-classification found only **72% of personal-information columns** and **4 of 7 high-risk identifiers** (precision 0.857, recall 0.720, F1 0.783) on our 145-column synthetic bank.
- None of its 40 built-in recognizers targets the Canadian SIN, postal codes, provincial driver's licences or Canadian passports.
- Some correct results were right for the wrong reason: the SIN column was tagged because an **Australian Tax File Number** pattern happened to match; the legacy SIN column was caught by a **U.S. bank routing-number** pattern.
- Adding 17 Canada-specific recognizers raised recall to **1.000** and F1 to **0.943**, and all 7 high-risk columns were found. The gain came from local knowledge, not from better AI.
- The open-source `metadata classify` command silently ignores recognizers on any classification other than the built-in `PII` one; we needed a ~20-line workaround.

### 2. Supporting evidence (specific source)

- **POC:** report Result 1, Result 2 and Table "AI Auto-Classification Against Ground Truth"; data in `poc/results/classification_baseline_ootb.json` and `classification_canada_tuned.json`.
- **Truong, Walters and Goodsitt (2020)** [`truong`]: Capital One's work on neural sensitive-data detection for financial institutions; stresses that labelled financial datasets are scarce, so models do not transfer easily between settings.
- **OPC, Interpretation bulletin: Sensitive information (2022)** [`opc_sensitive`]: sensitivity depends on context, not on the data type alone.
- **OpenMetadata 2.0.5 source code, `classification.py`** [`om_source`]: the hard-coded `PII` filter.

### 3. Responsible implication (why it matters)

- A missed column is a **false negative**, and false negatives are invisible: nobody sees the column that was never flagged.
- Vendor or default accuracy figures are **not transferable evidence**. A bank that deploys a classifier without measuring it on its own data cannot know what it is missing.
- Results that are "right by accident" break silently when a format changes.
- Relying on an untested tool would fall short of the professional duty of care, especially under PIPEDA Principle 4.7 (safeguards appropriate to sensitivity).

### 4. Actionable recommendation (next step)

- **Measure before you trust (CDO, 0–3 months).** Hand-label a sample of the bank's real schemas, as our ground truth did, and report precision and recall. Make **recall on high-risk identifiers** the acceptance criterion.
- **Localize the classifier (data platform, 0–3 months).** Add recognizers for SIN, postal code, provincial health and licence numbers, passports and transit/institution/account formats, plus column-name rules for legacy naming.
- **Verify the recognizers actually run.** Re-run the measurement after every upgrade, because the product can silently skip custom recognizers.

---

## Finding 2: Human feedback fixes errors, but oversight is fragile

### 1. Finding (the core result)

- The tuned classifier's 3 false positives were customer and branch `city` columns that the spaCy model read as people's names.
- A data steward reported each one through the recognizer-feedback workflow; the Chief Privacy Officer approved; the platform removed the tags. Precision and F1 rose to **1.000**.
- But fixing one rule exposed another: a broader column-name rule then re-tagged the `city` columns as quasi-identifiers, which is right for customer cities but wrong for branch cities (public addresses). Exact five-level accuracy rose only from **0.959 to 0.966**.
- Every AI tag stays in a *Suggested* state until a person confirms it, and every decision leaves an audit trail.

### 2. Supporting evidence (specific source)

- **POC:** report Result 3; approvals and feedback in `poc/results/workflow_audit.json`; scores in `classification_after_feedback.json`.
- **Parasuraman and Riley (1997)** [`parasuraman`], "Humans and automation: Use, misuse, disuse, abuse": people over-trust reliable automation and stop checking it (automation bias).
- **OSFI Guideline E-23 (2025)** [`osfi_e23`] and **NIST AI RMF 1.0 (2023)** [`nist_airmf`]: require documented human accountability and review of AI/model outputs.

### 3. Responsible implication (why it matters)

- **Delegating classification to AI does not delegate accountability.** PIPEDA Principle 4.1 and OSFI E-23 both require a named person to own the outcome.
- A reviewer who approves hundreds of correct suggestions will eventually stop looking, so "a human is in the loop" is not a safeguard by itself.
- Feedback is iterative, not a one-time fix: each correction can shift errors elsewhere.

### 4. Actionable recommendation (next step)

- **Keep AI tags as suggestions (CPO, 0–3 months).** Require human confirmation for every high-risk tag, and route all corrections through the feedback workflow so each decision is attributable.
- **Design the review, don't assume it.** Review high-risk and low-confidence tags first, track how often reviewers override the AI, and periodically insert planted test columns to check reviewers are still paying attention.
- **Re-score after every round of feedback** to catch errors that move rather than disappear.

---

## Finding 3: Metadata tests detect PIPEDA defects, but do not fix them

### 1. Finding (the core result)

- Twelve data-quality tests, each named after the PIPEDA principle it checks, found every planted defect and automatically opened six incidents:
  - **55 customers** still in the marketing audience after withdrawing consent (4.3),
  - **1,239 stored card verification values (CVVs)** (4.4),
  - **38 customers** kept past the seven-year retention period, in both the OLTP database and the warehouse (4.5),
  - **17 malformed postal codes** (4.6).
- A naive consent test (the audience's consent flag is true) **passed**; only a test that cross-checked the audience against current consent records **failed**. Compliance testing needs the business rule, not just the column.
- The e-mail format test flagged **240 addresses with accented French characters**: the rule, not the data, was wrong, and only a person could decide that.
- The platform **fixed none** of the defects; suppression, deletion and pipeline changes stayed manual.

### 2. Supporting evidence (specific source)

- **POC:** report Result 5 and Table "PIPEDA Data-Quality Tests in the POC"; test outcomes in `poc/results/pipeda_compliance_summary.md` and `summary.json`.
- **Jones (2023)** [`jones_contracts`], *Driving Data Quality with Data Contracts*: obligations should be expressed as machine-checkable agreements on each dataset.
- **Wang and Strong (1996)** [`wangstrong`], "Beyond accuracy": data quality is judged by fitness for the consumer's purpose, not format alone.
- **OPC, Guidelines for obtaining meaningful consent (2018)** [`opc_consent`]: individuals may withdraw consent, and organizations must honour it.

### 3. Responsible implication (why it matters)

- A column-level check would have **certified a non-compliant mart**; a false sense of compliance is worse than an acknowledged gap.
- Metadata platforms shift effort from *finding* problems to *specifying obligations precisely*; someone has to write the legal reasoning into the test.
- Detection without an owner and a fix does not protect anyone: the 55 customers would keep receiving marketing e-mail.
- Rules can be unfair: an over-strict e-mail rule fails francophone customers more often, an equity issue as well as an accuracy one.

### 4. Actionable recommendation (next step)

- **Codify PIPEDA as tests and contracts (data stewards, 3–12 months).** On every mart holding personal information, write consent, retention and minimization rules as cross-table tests and data contracts, not just format checks.
- **Give every failing test an owner.** Route incidents to a named steward with a deadline, and fix the root cause in the pipeline (for example, make the ETL respect consent withdrawal).
- **Review rules, not just data.** When a test fails at scale, check whether the rule itself is biased or over-strict before "cleaning" customer data.

---

## Finding 4: Catalogue policies do not reach the database, and safeguards fail open

### 1. Finding (the core result)

- Tag-based OpenMetadata policies worked inside the catalogue: a marketing analyst was denied (HTTP 403) sample data from high-risk tables, and only the Privacy and Data Governance offices could change PIPEDA tags.
- But **none of these policies stops a SQL user from querying the warehouse** directly.
- We closed the gap with our own script that reads tags from the catalogue and generates database views and grants. The marketing role then saw **556 audience rows instead of 611**, exactly removing the 55 withdrawn customers, and was denied the raw tables.
- Every control keys off tags, so a column the AI misses gets **no tag, no masking and no warning**: tag-driven controls are allow-by-default, while bank controls are normally deny-by-default.
- The built-in permission debugger reported "denied" for requests the real endpoint allowed (policies only checked table-level tags).

### 2. Supporting evidence (specific source)

- **POC:** report Result 6 and "Risks of relying on the platform"; generated SQL and verification in `poc/results/enforcement.json`; catalogue access tests in `workflow_audit.json`.
- **OpenMetadata, Data contract specification (v2.0.x)** [`om_contracts`]: the contract's security section is documentation, not enforcement.
- **NIST SP 800-162 (2014)** [`nist800162`], *Guide to attribute based access control*: access policies can key off attributes such as classification tags.
- **Kakui, U.S. Patent 11,556,661 B2 (2023)** [`pat_hitachi`]: deriving access control from tags and lineage.

### 3. Responsible implication (why it matters)

- A governance tool that **looks enforced when it is not** is more dangerous than an acknowledged gap: the catalogue can report compliance while the warehouse is exposed.
- If the custom enforcement code stops running or drifts from the tags (new column, renamed table, failed job), protection silently disappears.
- Auditors cannot rely on a tool whose own diagnostics misreport its behaviour; evidence must come from testing the real access path.

### 4. Actionable recommendation (next step)

- **Close the policy-to-data gap (data platform, 3–12 months).** Generate warehouse masking, row filters and grants automatically from catalogue tags and purposes, and run it on every change.
- **Make it fail closed.** Treat untagged or newly added columns as sensitive until a person classifies them.
- **Alert on drift and test the real path.** Alert when catalogue and database permissions diverge, and verify access by querying the database as each role, not by reading the permission debugger.

---

## Finding 5: Lineage turns the catalogue into a living inventory

### 1. Finding (the core result)

- Combining confirmed tags with owners, purposes, retention periods and column-level lineage produced an inventory and data-flow map **generated from the API, not maintained by hand**.
- The inventory immediately exposed over-collection: a legacy import table holds **SINs under meaningless column names** (`fld_02`) with no identified purpose, and the card table stores CVVs that should never be kept.
- The flow map shows names, e-mails and birth dates spreading from the customer table into **three warehouse objects**, while the SIN stays in the OLTP layer.
- The **same 38 over-retained customers** appear in both the OLTP table and the warehouse copy, so a purge has to follow the lineage.

### 2. Supporting evidence (specific source)

- **POC:** report Result 4 (inventory table and flow map), Result 5 (retention); lineage registered by `poc/toolbox/poc/post_ingestion.py`.
- **Herschel, Diestelkämper and Ben Lahmar (2017)** [`herschel`], "A survey on provenance": "where" lineage is what traces data to its copies.
- **BCBS 239 (2013)** [`bcbs239`] and its **2023 progress report** [`bcbs_progress`]: banks must document data lineage, yet most large banks still had substantial work to do.
- **OPC, Desjardins investigation (2020)** [`opc_desjardins`]: data kept longer than necessary in two warehouses magnified a breach affecting about 9.7 million people.

### 3. Responsible implication (why it matters)

- Without knowing where every copy lives, a bank cannot honour an individual's access request (PIPEDA 4.9), delete data on time (4.5), or scope a breach under the real-risk-of-significant-harm test.
- Deleting from the source alone leaves copies in the warehouse, exactly the Desjardins pattern.
- Retention is not one number: FINTRAC requires records to be kept at least five years while PIPEDA says keep only as long as necessary, so rules must be purpose-specific.

### 4. Actionable recommendation (next step)

- **Complete lineage (data engineering, 3–12 months).** Make registering lineage a release requirement for every pipeline that moves personal information.
- **Drive purges and access requests from lineage.** Use the flow map to delete or report every copy, not only the source record.
- **Act on what the inventory exposes.** Assign purposes and purpose-specific retention to every table; delete or justify unpurposed data such as the legacy SIN import and the stored CVVs.

---

## Finding 6: The catalogue and its AI assistant are a high-value attack surface

### 1. Finding (the core result)

- Through OpenMetadata's MCP server (15 tools), an AI assistant answered real privacy-office questions from the catalogue: which tables hold high-risk identifiers, where a customer's e-mail flows, whether the marketing mart passes its consent tests.
- The same server exposes **write tools** (`patch_entity`, `create_entity`, `create_lineage`). An agent with an over-privileged token could **remove the tags that drive safeguards**, and because controls fail open (Finding 4), that would silently unprotect data.
- Profiling can copy **real sample rows** into the catalogue's database and search index, and the tags plus lineage form a map of where the most sensitive data sits.
- Quick-start defaults use a shared administrator account and bot token.

### 2. Supporting evidence (specific source)

- **POC:** report Result 7 and "Risks of relying on the platform"; questions and answers in `poc/results/mcp_transcript.json`; tag-integrity tests in `workflow_audit.json`.
- **Hou, Zhao, Wang and Wang (2026)** [`hou_mcp`], "Model Context Protocol (MCP): Landscape, security threats, and future research directions": catalogues tool poisoning, over-privileged servers and data exfiltration.
- **OSFI Guideline B-13 (2022)** [`osfi_b13`]: banks must classify and protect data by confidentiality and manage technology risk.

### 3. Responsible implication (why it matters)

- **Metadata is security-relevant:** whoever can change a tag can switch off a safeguard.
- Compromising the catalogue, or one over-privileged token, is worth more to an attacker than compromising any single database.
- Storing sample rows makes the catalogue another copy of the data it is meant to protect, repeating the pattern that magnified the Desjardins breach.

### 4. Actionable recommendation (next step)

- **Lock down metadata (security, 0–3 months).** Restrict who can change sensitivity tags, separate the duties of tagging and approving, and alert on every tag change.
- **Connect AI assistants read-only.** Give MCP agents and ingestion bots least-privilege, individually issued tokens; never the shared admin token.
- **Disable or mask sample storage** for high-risk tables, and protect the catalogue with the same controls as a production database holding personal information.

---

## Sources

Keys match [`report/references.bib`](../report/references.bib). Full texts for the research papers are listed in [`references/papers/README.md`](../references/papers/README.md).

| Key | Source |
|---|---|
| `bcbs239` | Basel Committee on Banking Supervision, *Principles for effective risk data aggregation and risk reporting*, BIS, 2013. |
| `bcbs_progress` | Basel Committee on Banking Supervision, *Progress in adopting the Principles for effective risk data aggregation and risk reporting*, BIS, 2023. |
| `herschel` | M. Herschel, R. Diestelkämper, H. Ben Lahmar, "A survey on provenance: What for? What form? What from?", *VLDB J.*, 2017. |
| `hou_mcp` | X. Hou, Y. Zhao, S. Wang, H. Wang, "Model Context Protocol (MCP): Landscape, security threats, and future research directions", *ACM TOSEM*, 2026. |
| `jones_contracts` | A. Jones, *Driving Data Quality with Data Contracts*, Packt, 2023. |
| `nist800162` | V. C. Hu et al., *Guide to attribute based access control (ABAC) definition and considerations*, NIST SP 800-162, 2014. |
| `nist_airmf` | E. Tabassi, *Artificial Intelligence Risk Management Framework (AI RMF 1.0)*, NIST, 2023. |
| `om_contracts` | OpenMetadata, *Data contract specification (v2.0.x)*, 2026. |
| `om_source` | OpenMetadata contributors, OpenMetadata 2.0.5 release, `ingestion/src/metadata/workflow/classification.py`, GitHub, 2026. |
| `opc_consent` | Office of the Privacy Commissioner of Canada, *Guidelines for obtaining meaningful consent*, 2018. |
| `opc_desjardins` | Office of the Privacy Commissioner of Canada, *Investigation into Desjardins' compliance with PIPEDA following a breach of personal information between 2017 and 2019*, 2020. |
| `opc_sensitive` | Office of the Privacy Commissioner of Canada, *Interpretation bulletin: Sensitive information*, 2022. |
| `osfi_b13` | OSFI, *Guideline B-13: Technology and cyber risk management*, 2022. |
| `osfi_e23` | OSFI, *Guideline E-23: Model risk management (2027)*, 2025. |
| `parasuraman` | R. Parasuraman, V. Riley, "Humans and automation: Use, misuse, disuse, abuse", *Human Factors*, 1997. |
| `pat_hitachi` | K. Kakui, *Data access control system and data access control method*, U.S. Patent 11,556,661 B2, 2023. |
| `truong` | A. Truong, A. Walters, J. Goodsitt, "Sensitive data detection with high-throughput neural network models for financial institutions", arXiv:2012.09597, 2020. |
| `wangstrong` | R. Y. Wang, D. M. Strong, "Beyond accuracy: What data quality means to data consumers", *J. Manage. Inf. Syst.*, 1996. |
