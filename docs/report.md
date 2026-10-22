# Report guide

How the final report in [`report/`](../report/) is organised, how to build it, and what the team must finish before submitting it.

> **Status: draft.** The report was drafted with generative-AI assistance. The course requires that AI does not replace the team's own analysis and authorship, so the checklist [below](#before-submission) is mandatory, not optional.

## Files

| File | What it is |
|---|---|
| [`main.tex`](../report/main.tex) | Report source (IEEEtran class, `journal,onecolumn,11pt`) |
| [`references.bib`](../report/references.bib) | 51 BibTeX entries, IEEE style (`\bibliographystyle{IEEEtran}`) |
| [`figures/classification_comparison.png`](../report/figures/) | Classification chart, copied from `poc/results/figures/` |
| [`main.pdf`](../report/main.pdf) | Last compiled version (tracked in git so readers don't need LaTeX) |

## Structure

| Section | Content | Backed by |
|---|---|---|
| I. Introduction and problem context | Why the problem matters, stakeholders, objectives | [Research overview](research.md#problem) |
| II. Research question and scope | Primary question, SQ1–SQ3, scope, assumptions | [Research overview](research.md#research-question) |
| III. Method and evidence process | Search strategy, inclusion criteria, themes, POC design | [Research overview](research.md#method), the proposal `.docx` |
| IV. Evidence synthesis | Themes T1–T6, patterns, evidence gaps | Evidence table, [`references/papers/`](../references/papers/README.md) |
| V. Proof of concept: design and results | Results 1–7 | [Results](results.md), `poc/results/` |
| VI. Analysis | Answer to the RQ, SQ1–SQ3, alternative interpretations | [PIPEDA mapping](pipeda-mapping.md) |
| VII. Professional responsibility implications | Duties the AI features create | – |
| VIII. Recommendations | Immediate, medium term, longer term | – |
| IX. Limitations; X. Conclusion | | [Research overview](research.md#limitations) |
| Appendix A | Evidence table (abbreviated) | |
| Appendix B | Search log (summary) | Full log in the proposal `.docx` |
| Appendix C | Reproducibility | [Operations](operations.md) |
| Appendix D | Generative-AI use statement | **To be completed by the team** |

Course target: 12–15 pages excluding references.

## Building the PDF

No TeX installation is needed in the repo; any LaTeX distribution works. [Tectonic](https://tectonic-typesetting.github.io/) is the simplest because it downloads packages on demand and runs BibTeX automatically.

```bash
cd report && tectonic main.tex
```

Install Tectonic with `brew install tectonic` (macOS) or `conda install -c conda-forge tectonic`.

With a full TeX distribution (TeX Live / MacTeX), use:

```bash
cd report && latexmk -pdf main.tex
```

Build artifacts (`.aux`, `.log`, `.bbl`, …) are git-ignored; `main.pdf` is committed.

## Keeping the report in sync with the POC

Every number in Section V comes from a file in [`poc/results/`](../poc/results/). After re-running the POC:

1. Compare `poc/results/summary.json` with the figures quoted in the report (F1 scores, failing-row counts, access-check totals).
2. Copy the regenerated chart: `cp poc/results/figures/classification_comparison.png report/figures/`.
3. Rebuild the PDF and commit the result and the evidence together, e.g. `data(poc): regenerate results` followed by `docs(report): update figures from new run` (see [CONTRIBUTING.md](../CONTRIBUTING.md)).

## Citations

The report uses **IEEE** numeric citations. The course guidelines ask for **APA**, so the team must confirm the format with the instructor. Switching is mechanical: replace `\bibliographystyle{IEEEtran}` with an APA style (for example `biblatex` with `style=apa`) and adjust the `\cite` commands to author–year form where the prose needs it.

When adding a source:

1. Add an entry to `references.bib` with a DOI or official URL.
2. Add it to the evidence table (Appendix A) with its theme (T1–T6).
3. If it is a research paper, add it to [`references/papers/README.md`](../references/papers/README.md).

## Before submission

- [ ] Replace the `[Team Member N]` placeholders in the author block.
- [ ] Each team member re-reads the sources they rely on and confirms each citation supports the sentence it is attached to.
- [ ] Rewrite Sections VI–VIII (analysis, professional responsibility, recommendations) in the team's own words and judgement.
- [ ] Complete Appendix D: tools used, for what, how outputs were verified, and individual contributions.
- [ ] Confirm the citation format (APA vs IEEE) with the instructor.
- [ ] Check the page count (12–15 pages excluding references).
- [ ] Rebuild `main.pdf` and commit it.
