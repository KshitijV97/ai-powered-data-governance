# Generative-AI use: policy, log and audit


## The rules



| Rule | What it means for this repo |
|---|---|
| AI may be used **only within the boundaries set for each assessment**. | Check each assessment's instructions before using AI for it. |
| Where allowed, AI may support brainstorming, language editing, format checking and alternative explanations. | – |
| AI **cannot replace** student analysis, source evaluation, professional judgement, interpretation or authorship. | AI-drafted text (report, deliverables) is a draft. The team rewrites the analysis, responsibility and recommendation parts in its own words. |
| Undeclared or inappropriate AI use may be treated as an **academic-integrity concern**. | Declare all tools (Claude Code, ChatGPT, others), not only one. |
| Do not upload **confidential or restricted information** to public AI tools; collect no **personal information** (section 5). | No student numbers, personal e-mail addresses or course materials in the repo or in prompts. |

### Repository rules

- **Commit trailer.** A commit written with an AI tool carries a `Co-Authored-By:` trailer naming the tool ([CONTRIBUTING.md](../CONTRIBUTING.md#rules)). The git history is then the evidence for the AI-use log below.
- **Pull requests.** The PR template asks whether AI was used and whether the trailer is present.

### Personal information

This repository is public. A pre-commit hook and a CI job (`No personal information`) run [`tools/check_personal_data.py`](../tools/check_personal_data.py), which fails when a file contains a uOttawa student number (nine digits starting with `300`) or an e-mail address outside a short allow list. It reads text files and the text inside `.docx`, `.pptx` and `.xlsx` files; it cannot read PDFs, so check a PDF by hand before committing it.

If personal information was ever committed, deleting it in a new commit is not enough: it stays in the history. The history must be rewritten (for example with [`git filter-repo`](https://github.com/newren/git-filter-repo)) and force-pushed, and GitHub Support asked to purge cached pull-request views.

### Course materials


## AI-use log

Compiled from the `Co-Authored-By` trailers in the git history. Tool: **Claude** (Anthropic), used through **Claude Code**. The submitted proposal also declares **ChatGPT** for source discovery. Add any other tool the team used, with dates.

| Date (2026) | Work AI assisted with | Where |
|---|---|---|
| Oct 21 | Proof-of-concept code, Docker stack, synthetic data, evaluation pipeline, reference POC run | `poc/` |
| Oct 21 | Unit and integration tests, Ruff configuration, pre-commit hook, CI workflows | `poc/tests/`, `.github/`, `ruff.toml` |
| Oct 21 | Technical documentation, research overview, PIPEDA mapping, report guide, glossary, README | `docs/`, `README.md` |
| Oct 21 | Index of papers cited as evidence | `references/papers/README.md` |
| Oct 25 | Inventory of OpenMetadata's AI/ML features; branching strategy and PR template | `docs/openmetadata-ai-features.md`, `CONTRIBUTING.md` |
| Nov 13 | Static results website | `site/` |
| Nov 23 | This audit: AI-use log, personal-data check, history rewrite to remove student numbers and course materials | `docs/ai-use.md`, `tools/` |


## Audit of 23 November 2026

| # | Finding | Rule | Status |
|---|---|---|---|
| 1 | The proposal `.docx` (and, on PR #7, the submitted proposal PDF) published teammates' student numbers. | Course section 5 and checklist (personal / restricted information) | **Fixed:** numbers redacted from every commit by a history rewrite; check added to pre-commit and CI. |
| 3 | Two AI-assisted commits (research docs, README diagram, Oct 21) had no `Co-Authored-By` trailer. | CONTRIBUTING.md | **Fixed:** trailers added by the history rewrite. |
| 5 | The submitted proposal's AI statement names ChatGPT only, while the commits that added and edited the proposal's search log and source evaluation (Oct 21 and Oct 27) carry a Claude trailer. | Undeclared AI use | **Team action** (cannot be fixed in the repo). |
