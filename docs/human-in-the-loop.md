# Human-in-the-loop workflows

Auto-classification produces suggestions; people remain accountable for them (PIPEDA 4.1). The POC uses two of OpenMetadata 2.0.5's built-in governance workflows. Both create **tasks** assigned to a reviewer, and the resolved tasks form the audit trail (PIPEDA 4.10).

[`human_in_the_loop.py`](../poc/toolbox/poc/human_in_the_loop.py) logs in **as each persona** and makes the same REST calls the UI would make, so the run is reproducible. In production every decision would be a person's judgement in the UI.

## 1. Glossary term approval

The PIPEDA glossary has the CPO as reviewer, so each new term starts in *Draft* and OpenMetadata's `GlossaryTermApprovalWorkflow` opens an approval task.

```mermaid
stateDiagram-v2
    [*] --> Draft: admin creates term (step 3)
    Draft --> InReview: workflow opens RequestApproval task
    InReview --> Approved: priya.cpo resolves task "Approved"
    InReview --> Rejected: reviewer rejects
    Approved --> [*]: term can be linked to tables (step 10)
```

```mermaid
sequenceDiagram
    actor Admin
    participant OM as OpenMetadata
    actor CPO as priya.cpo
    Admin->>OM: PUT glossary PIPEDAGlossary (reviewers: CPO)
    Admin->>OM: PUT 13 glossary terms
    OM->>OM: GlossaryTermApprovalWorkflow starts per term
    OM-->>CPO: RequestApproval tasks (Open)
    CPO->>OM: GET /v1/tasks/assigned?status=Open
    loop each task
        CPO->>OM: POST /v1/tasks/{id}/resolve {Approved, comment}
    end
    OM->>OM: term entityStatus = Approved
```

Evidence: `results/workflow_audit.json` → `glossary_approval`.

## 2. Recognizer feedback (false-positive correction)

When a steward disagrees with an automated tag, they submit feedback on the tag. OpenMetadata's `RecognizerFeedbackReviewWorkflow` opens a task for the tag's reviewer; approval adds an exception to the recognizer so the same column is not re-tagged.

```mermaid
sequenceDiagram
    actor Steward as dan.steward
    participant OM as OpenMetadata
    actor CPO as priya.cpo
    participant CLI as classify_with.py

    Steward->>OM: POST /v1/tags/name/PIPEDA.DirectIdentifier/feedback<br/>{entityLink: core.branch.city, FALSE_POSITIVE,<br/>reason PUBLIC_INFORMATION, suggestedTag NonPersonal}
    Note over Steward,OM: also dim_branch.city (FALSE_POSITIVE)<br/>and customer.city (INCORRECT_CLASSIFICATION → QuasiIdentifier)
    OM-->>CPO: RecognizerFeedbackApproval tasks
    CPO->>OM: resolve each task "Approved"
    OM->>OM: add column to recognizer exceptionList
    CLI->>OM: re-run PIPEDA classification
    OM-->>CLI: excepted columns no longer tagged DirectIdentifier
```

| Column | Feedback type | Steward's reason | Suggested tag |
|---|---|---|---|
| `core.branch.city` | False positive | Branch cities are public business addresses | `PIPEDA.NonPersonal` |
| `dw.dim_branch.city` | False positive | Public branch locations | `PIPEDA.NonPersonal` |
| `core.customer.city` | Incorrect classification | Customer city alone is a quasi-identifier | `PIPEDA.QuasiIdentifier` |

After approval the `PIPEDA.DirectIdentifier` tag carries three recognizer exceptions and the next classification run reports zero false positives (see [classification results](classification.md#results)). Evidence: `results/workflow_audit.json` → `recognizer_feedback`.

## Who decides what

```mermaid
flowchart LR
    AI["AI auto-classification"] -- "suggests tags" --> Cat["Catalogue"]
    Steward["Data steward"] -- "flags errors" --> Task["Review task"]
    Task --> CPO["Chief Privacy Officer"]
    CPO -- "approves / rejects" --> Cat
    CPO -- "approves terms" --> Glo["Glossary"]
    Cat -- "drives" --> Ctrl["Policies, masked views"]
    Task -. "audit trail" .-> Log[("Task history")]
```

The design choice worth noting: the AI never directly changes a control. It changes **tags**, and tags drive controls, so the human review sits on the one place every downstream control reads from.
