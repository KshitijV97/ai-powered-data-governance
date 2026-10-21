# Governance model

The whole governance model is declared as data in [`governance_model.py`](../poc/toolbox/poc/governance_model.py) and pushed into OpenMetadata by [`bootstrap_governance.py`](../poc/toolbox/poc/bootstrap_governance.py) and [`post_ingestion.py`](../poc/toolbox/poc/post_ingestion.py). Every call is an idempotent `PUT`, so the model can be edited and re-applied.

## From PIPEDA to OpenMetadata

PIPEDA Schedule 1 contains ten fair-information principles (CSA Q830). Each maps to one or more OpenMetadata features:

```mermaid
flowchart LR
    subgraph P["PIPEDA Schedule 1"]
        p1["4.1 Accountability"]
        p2["4.2 Identifying purposes"]
        p3["4.3 Consent"]
        p4["4.4 Limiting collection"]
        p5["4.5 Use, disclosure, retention"]
        p6["4.6 Accuracy"]
        p7["4.7 Safeguards"]
        p8["4.8 Openness"]
        p9["4.9 Individual access"]
        p10["4.10 Challenging compliance"]
    end
    subgraph O["OpenMetadata features"]
        teams["Teams, owners, domains"]
        purp["PIPEDAPurpose tags,<br/>data contract"]
        dq["Data-quality tests"]
        cls["PIPEDA classification +<br/>AI auto-classification"]
        ret["retentionPeriod"]
        pol["Tag-based policies +<br/>generated masked views"]
        glo["PIPEDA glossary +<br/>approval workflow"]
        lin["Column-level lineage,<br/>MCP"]
        fb["Recognizer-feedback workflow,<br/>task audit trail"]
    end
    p1 --> teams
    p2 --> purp
    p3 --> dq
    p3 --> pol
    p4 --> cls
    p4 --> dq
    p5 --> ret
    p5 --> dq
    p6 --> dq
    p7 --> pol
    p7 --> cls
    p8 --> glo
    p9 --> lin
    p10 --> fb
```

## Organisation

```mermaid
flowchart TD
    BU["BorealisBank<br/>(BusinessUnit)<br/>policy: PIPEDAClassificationIntegrity"]
    BU --> PO["PrivacyOffice"]
    BU --> DGO["DataGovernanceOffice"]
    BU --> RM["RetailMarketing"]
    BU --> FA["FraudAML"]
    BU --> DE["DataEngineering"]
    PO --- u1(["priya.cpo<br/>Chief Privacy Officer<br/>role: PrivacyOfficer"])
    DGO --- u2(["dan.steward<br/>Data Steward<br/>role: PIPEDADataSteward"])
    RM --- u3(["maya.marketing<br/>Marketing Analyst<br/>role: MarketingAnalyst"])
    FA --- u4(["femi.aml<br/>AML Analyst<br/>role: AMLAnalyst"])
    DE --- u5(["eli.engineer<br/>Data Engineer<br/>role: DataEngineer"])
```

All persona users log in as `<name>@borealis.example` with a local test password.

### Roles and policies

```mermaid
flowchart LR
    subgraph Roles
        r1["PrivacyOfficer"]
        r2["PIPEDADataSteward"]
        r3["MarketingAnalyst"]
        r4["AMLAnalyst"]
        r5["DataEngineer"]
    end
    subgraph Policies
        pa["PrivacyOfficeStewardship<br/>ALLOW edit classifications,<br/>tags, glossary, tables"]
        pb["PIPEDASafeguardsNeedToKnow<br/>DENY ViewSampleData / Queries /<br/>DataProfile if HighRisk or DirectIdentifier"]
        pc["PIPEDAClassificationIntegrity<br/>DENY EditTags on PIPEDA-tagged tables<br/>unless in PrivacyOffice or DGO"]
        dc["DataConsumerPolicy (built-in)"]
        ds["DataStewardPolicy (built-in)"]
    end
    r1 --> pa
    r1 --> dc
    r2 --> pa
    r2 --> ds
    r3 --> dc
    r3 --> pb
    r4 --> dc
    r5 --> dc
    BU["Team BorealisBank<br/>(everyone)"] --> pc
```

The integrity policy is attached to the **business-unit team** rather than to a role, so it applies to everyone in the bank, including future users.

## Classifications

### `PIPEDA` (sensitivity)

Mutually exclusive, owned by the CPO, auto-classification enabled with `conflictResolution: highest_priority`, `minimumConfidence: 0.6`.

| Tag | Priority | Meaning | Recognizers |
|---|---|---|---|
| `PIPEDA.HighRisk` | 100 | Compromise creates a real risk of significant harm: SIN, card PAN, CVV, government ID, account number | SIN formatted / unformatted / column name; Presidio `CreditCardRecognizer`; card, account-number and government-ID column names; Ontario driver's licence; Canadian passport |
| `PIPEDA.DirectIdentifier` | 80 | Directly identifies or contacts a person | Presidio e-mail, phone, IP; spaCy `PERSON` NER; Canadian postal code; direct-identifier column names |
| `PIPEDA.QuasiIdentifier` | 50 | Re-identifies only in combination | Column names: city, province, FSA, birth year, age band, occupation, … |
| `PIPEDA.Financial` | 40 | Balances, income, amounts | Column names: balance, income, salary, amount, credit score |
| `PIPEDA.NonPersonal` | – | Reviewed and confirmed not personal | none (set by stewards) |

```mermaid
flowchart TD
    col["Column + 50 sampled values"] --> name{"Column-name<br/>recognizers"}
    col --> content{"Content<br/>recognizers"}
    name --> score["Candidate tags<br/>with confidence"]
    content --> score
    ctx["Context words<br/>(sin, social, postal…)"] -. "boost score" .-> score
    score --> thr{"confidence ≥ 0.6?"}
    thr -- no --> none["no tag"]
    thr -- yes --> pri["highest_priority wins<br/>HighRisk > Direct > Quasi > Financial"]
    pri --> exc{"in recognizer<br/>exception list?"}
    exc -- yes --> none
    exc -- no --> tag["Column tagged<br/>(labelType Automated)"]
```

### Recognizer design notes

* **SIN.** Three recognizers work together: a formatted pattern (`NNN-NNN-NNN`, score 0.7), an unformatted 9-digit pattern (score 0.3, too weak alone) and a column-name pattern (0.9). Context words such as `sin`, `social`, `insurance`, `nas` boost the content scores. The OSS engine cannot run Python recognizers, so the Luhn checksum is not validated.
* **Postal code.** The regex excludes letters Canada Post never uses (D, F, I, O, Q, U, and W/Z in first position), which keeps US ZIP codes and random strings out.
* **Column-name recognizers** use `target: column_name` with case-insensitive matching. They are cheap and precise for well-named schemas but useless for `fld_02`, which is why content recognizers are kept as well.

### `PIPEDAPurpose` (purpose of processing)

`AccountServicing`, `RegulatoryReporting`, `FraudPrevention`, `Marketing`, `Analytics`. Applied at table level in step 8. Purposes drive enforcement: a role sees direct identifiers only on tables whose purpose matches its own (see [enforcement](enforcement.md)).

## Table-level metadata (step 8)

`TABLE_METADATA` assigns, per table, a domain, an owner team, purposes, an ISO-8601 retention period and a tier. Retention values are **assumptions** for the POC (FINTRAC requires at least five years for most records; the bank adopts seven years after the relationship ends).

Column sensitivity is then **rolled up**: each table inherits its most sensitive column-level PIPEDA tag. This is required because the sample-data endpoint only evaluates `matchAnyTag()` against table-level tags (see [results](results.md#product-limitations-found)).

```mermaid
flowchart LR
    c1["sin: HighRisk"] --> R{{"roll-up:<br/>most sensitive wins"}}
    c2["email: DirectIdentifier"] --> R
    c3["city: QuasiIdentifier"] --> R
    c4["annual_income: Financial"] --> R
    R --> T["core.customer<br/>table tag PIPEDA.HighRisk"]
```

## Domains and data products

```mermaid
flowchart TD
    D1["Domain: RetailBanking<br/>owner DataEngineering"] --> P1["Data product: Customer360<br/>dim_customer, dim_account, fact_transaction"]
    D2["Domain: RiskCompliance<br/>owner FraudAML"] --> P2["Data product: FINTRACLargeCashReporting<br/>aml_large_cash_txn"]
    D3["Domain: Marketing<br/>owner RetailMarketing"] --> P3["Data product: EmailCampaignAudience<br/>marketing_campaign_audience"]
```

## Glossary

`PIPEDAGlossary` contains 13 terms: *Personal information*, the ten principles, *Real risk of significant harm (RROSH)* and *Breach of security safeguards*. Because the glossary has the CPO as reviewer, every new term starts as *Draft* and goes through OpenMetadata's `GlossaryTermApprovalWorkflow` (see [human-in-the-loop](human-in-the-loop.md)). Only approved terms can be linked to tables; step 10 links *Consent*, *Safeguards*, *PersonalInformation* and *LimitingUseDisclosureRetention* to the relevant tables.

## Data contract

Step 10 creates `marketing_campaign_audience_pipeda_contract` on the marketing mart:

```mermaid
flowchart TB
    K["Data contract<br/>marketing_campaign_audience_pipeda_contract"]
    K --> own["Owner: DataEngineering<br/>Reviewer: priya.cpo"]
    K --> tou["Terms of use:<br/>express-consent e-mail only; no join with transactions;<br/>honour withdrawals within 10 business days"]
    K --> sem["Semantics rules (JSON Logic)<br/>• has an owner (4.1)<br/>• tagged PIPEDAPurpose.Marketing (4.2)<br/>• has a PIPEDA sensitivity tag (4.7)"]
    K --> qe["Quality expectations:<br/>all DQ test cases on the table"]
    K --> sec["Security: PIPEDA.DirectIdentifier, Confidential;<br/>policy PIPEDASafeguardsNeedToKnow for RetailMarketing"]
    K --> sla["SLA: daily refresh; 90-day retention"]
```

## Data-quality tests as code

Declared in `DATA_QUALITY` in [`workflows.py`](../poc/toolbox/poc/workflows.py); every test name starts with the principle it checks.

| Test | Table | Type |
|---|---|---|
| `p4_3_consent_marketing_flag_true` | `mart.marketing_campaign_audience` | `columnValuesToBeInSet` |
| `p4_3_consent_not_withdrawn` | `mart.marketing_campaign_audience` | custom SQL |
| `p4_3_consent_purpose_not_null` | `core.customer_consent` | `columnValuesToBeNotNull` |
| `p4_3_consent_withdrawal_after_capture` | `core.customer_consent` | custom SQL |
| `p4_4_limiting_collection_no_cvv_stored` | `core.card` | custom SQL |
| `p4_4_minimisation_no_full_postal_code` | `dw.dim_customer` | `columnValueLengthsToBeBetween` (3–3) |
| `p4_5_retention_closed_customers_purged` | `core.customer`, `dw.dim_customer` | custom SQL (closed > 7 years) |
| `p4_6_accuracy_email_format` | `core.customer` | `columnValuesToMatchRegex` |
| `p4_6_accuracy_postal_code_format` | `core.customer` | `columnValuesToMatchRegex` |
| `p4_6_accuracy_sin_unique` | `core.customer` | `columnValuesToBeUnique` |
| `fintrac_lctr_min_amount` | `mart.aml_large_cash_txn` | custom SQL (no row under $10 000) |
