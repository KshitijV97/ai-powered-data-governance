# Team activity: research summary

Team 2, GNG/ELG 5301, Fall 2026. All facts and numbers below come from the report ([`report/main.tex`](../report/main.tex)) and the POC evidence in [`poc/results/`](../poc/results/).

> **Draft for team review.** Claude Code helped write this draft. Before it is submitted, the team should check it, rewrite it in its own words, and cover it in the AI-use statement (report Appendix D).

## 1. Core research question

How can a Canadian bank use an open-source, AI-assisted metadata platform (OpenMetadata) to put PIPEDA's fair information principles into practice across its transactional (OLTP) and analytical (OLAP) data, and what professional safeguards does this require?

## 2. Research method

We reviewed 45 scholarly, regulatory, standards, professional and patent sources, coded under six themes. We also built a reproducible Docker proof of concept on OpenMetadata 2.0.5 with a synthetic bank of 1,500 customers, and scored its AI auto-classification against column-level ground truth.

## 3. Principal findings

1. **Accuracy depends on the deployment, not the product.** Out of the box, the classifier found 72% of personal-information columns and only 4 of 7 high-risk identifiers. Some Social Insurance Numbers were caught only because Australian and U.S. patterns happened to match. Canada-specific recognizers raised recall to 100% (F1 0.783 → 0.943), and steward feedback removed the remaining false positives (F1 1.000).
2. **Metadata detects problems; people and pipelines have to fix them.** Catalogue tests and lineage exposed planted PIPEDA defects: 55 customers e-mailed after withdrawing consent, 38 records kept past retention in both the OLTP database and the warehouse, and 1,239 stored card-verification values. The platform fixed none of them.
3. **The platform governs the catalogue, not the data.** Catalogue policies do not reach the database, so we had to generate views and grants from the tags ourselves. These tag-driven safeguards fail open: a column the AI misses gets no tag and therefore no protection, and nothing flags the omission.

## 4. Most critical responsibility implication

**Handing classification to AI does not hand over accountability.** PIPEDA Principle 4.1 and OSFI Guideline E-23 both require a named person to own the outcome. Because a missed tag silently leaves data unprotected, the Chief Privacy Officer must own the classifier as a controlled, measured model. That means testing it on the bank's own data, reviewing its decisions, and never treating the catalogue's report of compliance as proof of it.

## 5. Summary text

Canadian banks copy personal information from operational systems into analytical warehouses, and PIPEDA requires them to know where it is, why it is held, who may use it and when it must be destroyed. We asked how, and with what professional safeguards, a bank can use an open-source, AI-assisted metadata platform to meet these obligations. We combined a review of 45 sources with a reproducible OpenMetadata 2.0.5 proof of concept built on a synthetic bank of 1,500 customers, and scored its AI classification against column-level ground truth. Out of the box, the AI found only 72% of personal-information columns and 4 of 7 high-risk identifiers. Canada-specific recognizers and steward feedback raised F1 from 0.783 to 1.000, so accuracy turned out to depend on local tuning rather than on the product. Catalogue tests and lineage exposed planted consent, retention and card-data defects but fixed none of them. Because the platform governs the catalogue rather than the data, we had to generate database-level enforcement from its tags, and that enforcement fails open whenever a column is missed. The central responsibility implication is that delegating classification to AI does not delegate accountability: a named privacy officer must own, measure and review the AI as a supervised control, and must not take the catalogue's report of compliance as proof of it.
