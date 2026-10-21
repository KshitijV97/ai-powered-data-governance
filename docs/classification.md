# AI auto-classification and evaluation

OpenMetadata's auto-classification samples rows from each table and runs recognizers over column names and values. In 2.0.5 the engine is built on **Microsoft Presidio** (pattern and predefined recognizers) plus **spaCy** named-entity recognition. The POC measures it three times against a known ground truth.

## The three runs

```mermaid
flowchart LR
    subgraph R1["Run 1 · step 5"]
        a1["metadata classify"] --> a2["Classification: PII<br/>(out of the box)"]
    end
    subgraph R2["Run 2 · step 6"]
        b1["classify_with.py PIPEDA"] --> b2["Classification: PIPEDA<br/>+ Canadian recognizers"]
    end
    subgraph R3["Run 3 · step 7"]
        c0["steward feedback<br/>approved by CPO"] --> c1["classify_with.py PIPEDA"]
        c1 --> c2["PIPEDA + recognizer<br/>exceptions"]
    end
    R1 --> e1["evaluate baseline_ootb"]
    R2 --> e2["evaluate canada_tuned"]
    R3 --> e3["evaluate after_feedback"]
    GT[("ground_truth.py<br/>145 labelled columns")] --> e1 & e2 & e3
```

| Run | Predicted positive when the column has… |
|---|---|
| Out-of-the-box | `PII.Sensitive` |
| Canada-tuned, after feedback | `PIPEDA.HighRisk` or `PIPEDA.DirectIdentifier` |

## How one classification run works

```mermaid
sequenceDiagram
    participant CLI as om-cli (ingestion 2.0.5)
    participant DB as bank-db (om_reader)
    participant OM as OpenMetadata server

    CLI->>OM: list tables of the service
    CLI->>OM: GET classification + tags + recognizers
    loop every table
        CLI->>DB: SELECT … LIMIT 50 (sampleDataCount)
        DB-->>CLI: sample rows
        CLI->>CLI: run column-name + content recognizers<br/>(Presidio, spaCy, regex)
        CLI->>CLI: score ≥ 0.6, resolve conflicts by priority
        CLI->>OM: PATCH column tags (Automated) + store sample data
    end
```

Settings come from the rendered `…__autoclassification.yaml`: `confidence: 60`, `sampleDataCount: 50`, `storeSampleData: true`, `classificationLanguage: en`.

## The `classify_with.py` workaround

In OpenMetadata 2.0.5 OSS, the `metadata classify` command passes a hard-coded `classification_filter=[PII]` to the processor (`metadata/workflow/classification.py`). Recognizers defined on any other classification, such as `PIPEDA`, are silently ignored even though the processor itself supports them.

[`om-ext/classify_with.py`](../poc/om-ext/classify_with.py) subclasses the official `AutoClassificationWorkflow` and overrides one method so the filter comes from the command line:

```mermaid
classDiagram
    class AutoClassificationWorkflow {
        +create(config)
        +execute()
        #_get_pii_processor()  "classification_filter=[PII]"
    }
    class MultiClassificationWorkflow {
        +classification_names: list
        #_get_pii_processor()  "classification_filter=classification_names"
    }
    AutoClassificationWorkflow <|-- MultiClassificationWorkflow
```

It runs inside the unmodified ingestion image:

```bash
scripts/dc.sh run --rm --entrypoint python om-cli /ext/classify_with.py /work/workflows/borealis_core_banking_oltp__autoclassification.yaml PIPEDA
```

## Ground truth

Because the data is synthetic, the sensitivity of every column is known. [`ground_truth.py`](../poc/toolbox/poc/ground_truth.py) labels all 145 columns of both databases:

| Label | Meaning | Examples |
|---|---|---|
| **H** | High-risk identifier | `sin`, `card_number`, `cvv`, `account_number`, `document_number`, `fld_02` |
| **D** | Direct identifier | names, `email`, `phone_number`, `street_address`, `postal_code`, `date_of_birth`, `client_ip`, `agent_notes` |
| **Q** | Quasi-identifier | `city`, `province`, `postal_fsa`, `birth_year`, `age_band`, `occupation` |
| **F** | Financial | `annual_income`, `current_balance`, `amount` |
| **N** | Not personal | keys, codes, timestamps, reference data |

The **positive class** for precision/recall is **H or D**: what a PII scanner should flag for protection. There are 25 positive columns, 7 of them high-risk.

```mermaid
pie showData title Ground-truth positives (25 columns)
    "High-risk (H)" : 7
    "Direct identifier (D)" : 18
```

## Metrics

[`evaluate_classification.py`](../poc/toolbox/poc/evaluate_classification.py) snapshots every column's tags from the OpenMetadata API and computes:

```mermaid
flowchart TD
    c["column"] --> t{"truth is H or D?"}
    t -- yes --> p1{"predicted?"}
    t -- no --> p2{"predicted?"}
    p1 -- yes --> TP["TP"]
    p1 -- no --> FN["FN"]
    p2 -- yes --> FP["FP"]
    p2 -- no --> TN["TN"]
    TP & FP --> P["precision = TP / (TP + FP)"]
    TP & FN --> R["recall = TP / (TP + FN)"]
    P & R --> F["F1 = 2PR / (P + R)"]
```

It also reports **high-risk recall** (how many of the 7 H columns were caught) and **PIPEDA exact-class accuracy** (does the five-level tag match the five-level label). Per-column detail, including the recognizer's `reason` text, is saved in `results/classification_<run>.json`.

## Results

| Run | Precision | Recall | F1 | TP | FP | FN | High-risk recall |
|---|---|---|---|---|---|---|---|
| Out-of-the-box PII | 0.857 | 0.720 | 0.783 | 18 | 3 | 7 | 4/7 |
| Canada-tuned PIPEDA | 0.893 | 1.000 | 0.943 | 25 | 3 | 0 | 7/7 |
| Tuned + steward feedback | 1.000 | 1.000 | 1.000 | 25 | 0 | 0 | 7/7 |

![classification comparison](../poc/results/figures/classification_comparison.png)

```mermaid
xychart-beta
    title "F1 by run"
    x-axis ["Out-of-the-box", "Canada-tuned", "After feedback"]
    y-axis "F1" 0 --> 1
    bar [0.783, 0.943, 1.0]
```

### What each step fixed

```mermaid
flowchart LR
    subgraph B["Baseline misses (FN = 7)"]
        m1["account_number ×2"]
        m2["date_of_birth ×2"]
        m3["postal_code"]
        m4["identity_document.document_number"]
        m5["legacy fld_03 (postal code)"]
    end
    subgraph FP["False positives (FP = 3)"]
        f1["core.branch.city"]
        f2["dw.dim_branch.city"]
        f3["core.customer.city"]
    end
    B -- "Canadian recognizers<br/>(step 6)" --> ok1["all 25 found"]
    FP -- "steward feedback +<br/>CPO approval (step 7)" --> ok2["0 false positives"]
```

* **Baseline:** none of the built-in recognizers targets Canadian identifiers. It caught SINs only because an *Australian TFN* and a *US ABA routing number* pattern happened to match nine-digit strings, and it missed postal codes, account numbers, the Ontario driver's licence/passport column and dates of birth.
* **Canada-tuned:** custom SIN, postal-code, licence, passport and column-name recognizers brought recall to 1.0. Three `city` columns remained over-flagged as direct identifiers by spaCy's location NER.
* **After feedback:** the three false positives were reported through the recognizer-feedback workflow; once approved, the recognizers carry exceptions for those columns and the re-run is clean.

> A perfect score on 145 synthetic columns says the method works here, not that it generalises. See *Limitations* in the report.
