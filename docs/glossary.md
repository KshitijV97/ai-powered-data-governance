# Glossary

Terms used across the documentation, the POC and the report.

## Privacy and regulation

| Term | Meaning |
|---|---|
| **PIPEDA** | *Personal Information Protection and Electronic Documents Act*, Canada's federal private-sector privacy law. Schedule 1 contains the ten fair-information principles (4.1–4.10). See [PIPEDA mapping](pipeda-mapping.md). |
| **Fair-information principles** | The ten principles of PIPEDA Schedule 1, taken from the CSA Model Code (CAN/CSA-Q830): accountability, identifying purposes, consent, limiting collection, limiting use/disclosure/retention, accuracy, safeguards, openness, individual access, challenging compliance. |
| **Personal information (PI)** | Information about an identifiable individual. Broader than "PII". |
| **PII** | Personally identifiable information; the US-origin term used by Presidio and OpenMetadata's default classification. |
| **OPC** | Office of the Privacy Commissioner of Canada; oversees PIPEDA. |
| **OSFI** | Office of the Superintendent of Financial Institutions; regulates federally chartered banks. Guideline **B-13** covers technology and cyber risk (including data classification); **E-23** covers model risk, including AI models. |
| **FINTRAC** | Financial Transactions and Reports Analysis Centre of Canada; anti-money-laundering regulator. Sets record-keeping periods and the large cash transaction report (**LCTR**, $10 000 or more). |
| **AML** | Anti-money laundering. |
| **Bill C-36** | *Protecting Privacy and Consumer Data Act* (2026), proposed federal privacy reform; treated as forthcoming, not law. |
| **CPO** | Chief Privacy Officer; the person accountable under principle 4.1. In the POC, the persona `priya.cpo`. |
| **SIN** | Social Insurance Number; treated as `HighRisk`. |
| **CVV** | Card verification value; must not be stored after authorization. Planted in the POC's legacy card table. |
| **Retention period** | How long a record may be kept. The POC assumes seven years after a customer relationship ends. |

## Data and architecture

| Term | Meaning |
|---|---|
| **OLTP** | Online transaction processing: the operational database (`core_banking`). |
| **OLAP** | Online analytical processing: the warehouse (`bank_dw`), a Kimball-style star schema. |
| **Star schema** | Fact tables (events such as transactions) joined to dimension tables (customers, accounts). |
| **Mart** | A subject-specific slice of the warehouse, such as `mart.marketing_campaign_audience` or `mart.aml_large_cash_txn`. |
| **ETL** | Extract, transform, load: the batch job (`etl_to_dw.py`) that copies OLTP data into the warehouse. |
| **Lineage** | A record of where data came from and where it goes. **Column-level lineage** traces individual columns through the ETL. |
| **Planted defect** | A deliberate compliance problem in the synthetic data, used to check that controls catch it. See [Data model](data-model.md#planted-defects). |
| **Synthetic data** | Generated data that represents no real person. All data in this project is synthetic. |
| **Ground truth** | The hand-made label for every column (H, D, Q, F, N) used to score the classifier. See [Classification](classification.md#ground-truth). |

## OpenMetadata

| Term | Meaning |
|---|---|
| **OpenMetadata** | Open-source metadata platform (catalogue, lineage, quality, governance). The POC uses version 2.0.5. |
| **Service** | A connection to a data source; the POC has two database services, one for OLTP and one for OLAP. |
| **Ingestion** | Reading schemas and tables from a service into the catalogue (`metadata ingest`). |
| **Profiler** | Computes column statistics and sample data (`metadata profile`). |
| **Classification** | A family of tags. The POC uses `PIPEDA` (sensitivity: HighRisk, DirectIdentifier, QuasiIdentifier, Financial) and `PIPEDAPurpose` (purpose of processing). |
| **Tag** | A label from a classification applied to a table or column. |
| **Auto-classification** | OpenMetadata's AI feature that samples column values and suggests tags (`metadata classify`). |
| **Recognizer** | A detection rule (pattern, context words or NER entity) attached to a tag. The POC adds Canadian recognizers such as SIN and postal code. |
| **Presidio** | Microsoft's open-source PII detection library, used by OpenMetadata's auto-classification. |
| **spaCy / NER** | The NLP library and its named-entity recognition, used by Presidio to find names and places. |
| **Roll-up** | Copying the most sensitive column tag to the table, needed because some policies only check table tags. |
| **Glossary** | Business vocabulary with definitions; the POC's PIPEDA glossary terms need reviewer approval. |
| **Domain / data product** | Business ownership groupings; a data product is a set of assets published for a purpose. |
| **Data contract** | A machine-readable agreement about a dataset's schema, quality and purpose. |
| **Data-quality test** | A check run against the data (for example, "no withdrawn consent in the marketing audience"). The POC's tests are named after the principle they check (`p4_3_*`). |
| **Policy / role** | Access rules in OpenMetadata. A policy's conditions can use functions such as `matchAnyTag()`. |
| **Workflow** | A governance process with human tasks, such as glossary approval or recognizer feedback. |
| **Ingestion bot** | The service account whose token the POC uses to run ingestion workflows. |
| **MCP** | Model Context Protocol, an open standard that lets AI assistants call tools. OpenMetadata exposes its catalogue through an MCP server. See [MCP](mcp.md). |

## Evaluation

| Term | Meaning |
|---|---|
| **Precision** | Of the columns the classifier flagged, the share that really hold personal information. |
| **Recall** | Of the columns that really hold personal information, the share the classifier flagged. |
| **F1** | The harmonic mean of precision and recall. |
| **False negative** | A sensitive column the classifier missed; the dangerous kind of error, because nobody sees it. |
| **Automation bias** | The tendency of people to over-trust automated suggestions; the reason human review must be designed, not assumed. |
| **Human-in-the-loop** | A process where a person reviews or approves an automated decision. See [Human-in-the-loop](human-in-the-loop.md). |
