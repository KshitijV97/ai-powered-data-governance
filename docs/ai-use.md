# Generative-AI use disclosure

This page states which generative-AI tools helped build this repository, what they were used for, what they were not used for, and how the output was checked. It follows the course's responsible-AI rules (GNG/ELG 5301, section 17): AI may support the work, but it cannot replace the team's analysis, source evaluation, professional judgement, interpretation or authorship, and AI use that materially affects the work must be declared.

## Summary

| | |
|---|---|
| **Tools** | **Claude** (Anthropic), used through **Claude Code**. **ChatGPT** (OpenAI) helped the team discover candidate research sources. |
| **Period** | October 21 to November 23, 2026 |
| **Used for** | Writing, testing and commenting the proof-of-concept code; CI, linting and repository tooling; drafting and editing the technical documentation; the results website; suggesting candidate sources |
| **Not used for** | Replacing the team's analysis, source evaluation, professional judgement, interpretation or authorship. The team is responsible for every claim. |
| **Checks** | Unit tests, Ruff linting and CI on every push; an end-to-end POC run that anyone can repeat (`poc/scripts/run_poc.sh`); team review of AI-suggested sources for accuracy, credibility and relevance; pull-request review before merging to `master` |

## Log

Compiled from the `Co-Authored-By` trailers in the git history (`git log --grep=Co-Authored-By`).

| Date (2026) | What AI assisted with | Where |
|---|---|---|
| Oct 21 | Proof-of-concept code: Docker stack, synthetic bank data, ETL, governance automation, evaluation pipeline, reference run | `poc/` |
| Oct 21 | Unit and integration tests, Ruff configuration, pre-commit hook, CI workflows | `poc/tests/`, `.github/`, `ruff.toml` |
| Oct 21 | Technical documentation, PIPEDA mapping, glossary, README, paper index | `docs/`, `README.md`, `references/` |
| Oct 25 | Inventory of OpenMetadata's AI/ML features; branching strategy and pull-request template | `docs/openmetadata-ai-features.md`, `CONTRIBUTING.md` |
| Nov 13 | Static results website | `site/` |
| Nov 20 | Explanatory code comments; Claude Code project instructions | `poc/`, `CLAUDE.md` |
| Nov 23 | This disclosure, the personal-information check and the website update | `docs/ai-use.md`, `tools/`, `site/` |

## Safeguards in this repository

- **Commit trailer.** A commit written with an AI tool carries a `Co-Authored-By:` trailer naming the tool ([CONTRIBUTING.md](../CONTRIBUTING.md#rules)), so the history shows which changes AI touched.
- **Pull requests.** The PR template asks whether AI was used, whether the trailer is present and whether AI-generated claims were checked.
- **Personal information.** A pre-commit hook and the `No personal information` CI job run [`tools/check_personal_data.py`](../tools/check_personal_data.py). It fails when a file holds a uOttawa student number (nine digits starting with `300`) or an e-mail address outside a short allow list. It reads text files and the text inside `.docx`, `.pptx` and `.xlsx` files, but not PDFs, so check a PDF by hand before committing it. If personal information is ever committed, deleting it in a new commit is not enough. The history must be rewritten (for example with [`git filter-repo`](https://github.com/newren/git-filter-repo)) and force-pushed, and GitHub Support asked to purge cached views.
- **Private material.** Team-private work and course material go in the git-ignored `private/` folder and are never published.
- **Synthetic data only.** The bank is fictional and every record is generated (`poc/toolbox/poc/generate_data.py`). No real personal information was given to an AI tool.
