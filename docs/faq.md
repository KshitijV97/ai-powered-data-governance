# Frequently asked questions

Answers to the questions people are likely to ask about Team 2's final presentation, the research project and the proof of concept (POC).
Every number here comes from the committed evidence in [`poc/results/`](../poc/results/) or from the sources listed at the end. The bank is fictional and all data is synthetic.

Jump to: [the project](#the-project) · [method and evidence](#method-and-evidence) · [the presentation](#the-presentation) · [findings](#findings) · [the proof of concept](#the-proof-of-concept) · [responsibility and ethics](#responsibility-and-ethics) · [limits](#limits) · [sources](#sources)

---

## The project

### What is the project about?

Canadian banks are starting to use AI coding assistants to write the SQL and ETL code that moves customer data from operational databases into warehouses. That code can run without errors and still produce wrong or unlawful data. The project asks whether a data governance platform, OpenMetadata, can help a bank manage the security and data-quality risks this creates.

### What is the research question?

> How can Canadian banks use data governance frameworks such as OpenMetadata to manage data security and validation risks while adopting AI-assisted tools for relational data pipelines?

It has five sub-questions:

| | Sub-question | Answered by |
|---|---|---|
| SQ1 | Data quality and validation: which validation risks arise, and how can AI add to them? | Finding 1 (data-quality tests) |
| SQ2 | Data security: which security and privacy risks arise, and how can AI add new ones? | Finding 3 (access control, MCP) |
| SQ3 | Regulatory compliance: what do PIPEDA and OSFI require? | PIPEDA scorecard ([pipeda-mapping.md](pipeda-mapping.md)) |
| SQ4 | Governance and OpenMetadata: how can lineage, quality tests, classification and access control help? | Findings 1 to 3 |
| SQ5 | Limits and human oversight: what can OpenMetadata not do, and what oversight is still needed? | Limitations; human-in-the-loop workflows |

### The repository README states a different question. Which one is right?

Both describe the same work. The README describes the POC's original framing: operationalizing PIPEDA with OpenMetadata. The final report and the presentation use the research question from the team's submitted proposal (above), which is broader. It treats PIPEDA as the yardstick and AI-assisted pipeline development as the source of risk. The POC evidence answers both.

### What is the one-sentence answer?

OpenMetadata is **one useful layer, not a compliance solution**. It catches errors when people have written the bank's obligations down as tests and tuned and approved its AI. It falls short when the bank expects it to find problems or enforce access on its own.

### Why OpenMetadata and not Collibra, Apache Atlas or another tool?

OpenMetadata is open source, can be self-hosted at no cost, and in one product has column-level lineage, AI auto-classification, data-quality tests, tag-based policies, approval workflows and an MCP server for AI agents. A study comparing it with Amundsen preferred OpenMetadata (da Silva et al., 2025). We did **not** test Collibra, Atlas, a simple scanner or database-native controls, so we make no claim that OpenMetadata is better than them. See [limits](#limits).

### Why PIPEDA, and where does OSFI fit?

PIPEDA's ten fair-information principles (Schedule 1) are binding on federally regulated banks and give a concrete checklist: consent, limiting collection, retention, accuracy, safeguards and so on. OSFI Guideline B-13 (technology and cyber risk) and the OSFI Integrity and Security Guideline set supervisory expectations for protecting data. The joint OSFI–FCAC report (2024) names data quality, privacy and governance as key AI risks. We used PIPEDA as the measuring stick and OSFI as supporting context.

### What is in scope and what is not?

In scope: relational data (one operational OLTP database and one warehouse with marts), OpenMetadata 2.0.5 open source, and human oversight of AI. Out of scope: production deployment, real customer data, full compliance audits, unstructured data and data lakes, other platforms, Quebec Law 25 and legal advice.

---

## Method and evidence

### How did you gather evidence?

Two lines of evidence, checked against each other:

1. **Literature and regulation.** 80 logged searches (IEEE Xplore, Scopus, uOttawa Omni, Google Scholar, ACM Digital Library, Springer, plus Canadian regulator websites). 82 sources were screened in full, 56 were included and 26 excluded with a recorded reason. The included sources were coded into five themes: data security and validation problems; Canadian law and regulation; oversight of AI-assisted development; governance tools; implementation findings.
2. **A proof of concept.** A fictional bank with 1,500 synthetic customers, 19 tables and 145 columns, governed end to end by OpenMetadata 2.0.5 (see [the proof of concept](#the-proof-of-concept)).

Each finding is labelled **documented** (stated in a source), **demonstrated** (observed in the POC) or **both**. We then ask what risk remains and what human oversight it still needs.

### Did AI find your sources?

ChatGPT suggested some candidate sources. A team member located and read every source before it was included. See the [AI-use disclosure](ai-use.md).

### What were the success criteria?

Ten criteria, one per risk, for example: 100% recall on high-risk columns, every planted defect caught, every access check giving the expected allow or deny, and every PIPEDA principle having at least one demonstrated control. The thresholds were set after the POC ran. That is a limitation, so each threshold is justified by what failure would cost, not by the result we got.

### Who decided which columns hold personal information?

The team labelled all 145 columns by hand as high-risk identifier, direct identifier, quasi-identifier, financial or not personal. 25 columns count as positives, 7 of them high-risk. We did not use AI to label them, because the labels are the yardstick the AI is scored against. See [classification.md](classification.md#ground-truth).

---

## The presentation

### How long is it and who presents what?

About 9 minutes 25 seconds, within the 10-minute limit, followed by 2 minutes of questions.

| Slides | Speaker | Content |
|---|---|---|
| 1 to 3 | Victor Blaja | Title, opening question, the problem |
| 4 to 6 | Khang Tran | Research question and scope, method, what the literature says |
| 7 to 10 | Kshitij Vengurlekar | The POC (which he built) and its three findings |
| 11 | Khang Tran | Answer to the research question |
| 12 to 15 | Mustafa Bayirli | Responsibility, recommendations, limitations, discussion question |
| 16 to 17 | (appendix) | References (APA 7), AI-use disclosure |

### Where do the opening statistics come from?

KPMG Canada's 2025 GenAI Business Survey of Canadian financial services leaders (KPMG, 2026): over 90% see generative AI as critical to competitive advantage, 60% are upgrading core systems to embed it, 95% worry about breaches and misuse of sensitive data, and 30% cite data quality as a major barrier. KPMG's page does not publish the sample size. Respondents were mostly C-suite, VP and director-level leaders.

### Is "about 40% of Copilot programs vulnerable" a fair figure?

It comes from Pearce et al. (2022), who generated 1,689 programs with GitHub Copilot across 89 security-relevant scenarios and found about 40% vulnerable. It measures code written for security-sensitive tasks in a lab study, not code running in banks.

### Were the TD Bank and Desjardins incidents caused by AI?

No, and the slide says so. TD Bank's US subsidiary was ordered to pay about US$28 million for furnishing inaccurate account data (CFPB, 2024). At Desjardins an insider extracted data on about 9.7 million people (OPC, 2020). They show what inaccurate data and weak safeguards cost. The one AI-related case on the slide is CB Financial Services (2026): its Form 8-K reports that customer data, including Social Security numbers, was handled through an unauthorized AI application.

### What is the discussion question, and what is the team's view?

*When AI-generated code causes a data-security failure, who should be accountable: the developer, the organization, or both?*
Our view, if asked: **both**. The developer owns review and testing of code they accept. The organization owns the business rules, the controls and the named accountable officer that PIPEDA principle 4.1 requires. A bank cannot tell a regulator "the AI wrote it".

### Why APA citations?

The course guideline asks for APA 7. The deck and the final report use the same style and the same reference list.

---

## Findings

### Is data quality covered?

Yes, explicitly. Data quality and validation is SQ1, and Finding 1 is about it. The consent, collection, retention and accuracy tests are data-quality tests run in OpenMetadata. Data quality also appears on the title slide (subtitle), the opening statistics (30% cite it as a barrier), the problem slide (OSFI–FCAC top AI risks), the literature slide (BCBS 239: data quality is a banking duty) and Recommendation 1 (data-quality tests as a release gate).

### What exactly did the twelve data-quality tests find?

Six of twelve tests flagged problems (OpenMetadata labels them "Failed"). Five were the defects we planted; the sixth was a faulty rule.

| PIPEDA principle | What the test found |
|---|---|
| 4.3 Consent | 55 customers who had withdrawn consent were in the marketing audience (the AI-style ETL bug) |
| 4.4 Limiting collection | 1,239 card security codes (CVVs) stored by a legacy system |
| 4.5 Retention | 38 customers kept past retention in the operational database, and the same 38 in the warehouse |
| 4.6 Accuracy | 17 malformed postal codes |
| 4.6 Accuracy | 240 valid e-mail addresses flagged because the rule rejected accented letters: the **rule** was wrong |

A naive check (`consent_marketing = TRUE`) passed on all 611 marketing rows. Only the cross-table rule that compares withdrawal dates caught the bug. Full table: [results.md](results.md#2-data-quality-findings).

### Did OpenMetadata discover the consent bug by itself?

No. It ran a rule a person had written: no customer with a withdrawal date may appear in the marketing audience. If nobody had written that rule, the bug would have shipped. The value is in the discipline of writing obligations as tests; the tool stores, schedules and reports them.

### What does F1 mean, and is 1.000 overfitting?

F1 combines precision (how many flagged columns really are personal information) and recall (how many personal-information columns were flagged) into one score, where 1.0 is perfect. Out of the box the classifier scored 0.783 and found 4 of 7 high-risk columns. With Canadian recognizers it scored 0.943 and found all 7. After a steward removed three false alarms (city columns read as person names), it scored 1.000.
Yes, the 1.000 is optimistic: it was scored on the same 145 columns the recognizers were tuned on, built by the same team. The honest number is 0.943, and the reliable lesson is the direction: defaults miss Canadian identifiers, and local rules plus human review fix it.

### Why did the built-in classifier miss Canadian identifiers?

OpenMetadata's classifier uses Microsoft Presidio, whose built-in recognizers cover US, Australian and other identifiers but not Canadian ones such as the Social Insurance Number (SIN) or postal code. In the baseline, SIN columns were flagged only because Australian Tax File Number and US ABA routing patterns happened to match. See [classification.md](classification.md).

### What does "catalogue security is not database security" mean?

OpenMetadata's access policies control what people can see **inside OpenMetadata**, such as sample data and tags. All seven catalogue checks behaved as expected. But the policies do not reach PostgreSQL, so anyone who queries the database directly bypasses them. We closed the gap with our own code, which reads the catalogue's tags and generates masked views and grants. After that, all seven warehouse checks behaved as expected; for example, the marketing role saw 556 audience rows instead of 611 because withdrawn customers were filtered out. See [enforcement.md](enforcement.md).

### What is the MCP risk?

OpenMetadata ships a Model Context Protocol (MCP) server so AI agents can query the catalogue. It answered four privacy questions correctly from catalogue facts. But it exposed 15 tools, four of which write (`create_entity`, `patch_entity`, `create_lineage`, `create_test_case`). An over-privileged or manipulated agent could remove the tag that protects a column, which would also switch off the masking generated from that tag. Hou et al. (2026) describe this class of risk for MCP in general. See [mcp.md](mcp.md).

### What does "8 of 10 PIPEDA principles" mean?

Eight principles had a demonstrated control in the POC: four implemented (4.1, 4.2, 4.7, 4.8) and four where the control detected the planted gap (4.3 to 4.6). Two were partial: 4.9 individual access (lineage helps, but there is no per-person search) and 4.10 challenging compliance (the feedback workflow is internal only). This is coverage, not compliance: the platform reported 1,239 stored CVVs; it did not delete them. See [pipeda-mapping.md](pipeda-mapping.md).

### Why is "tests as a release gate" the priority recommendation?

It is the only control that catches an AI-written defect even when the classifier, the lineage or the access controls are wrong, and it does not care who wrote the code. The other three recommendations are: measure the classifier on your own labelled columns and accept only 100% recall on high-risk columns; generate database views and grants from tags and treat untagged columns as sensitive; give AI agents read-only, least-privilege access.

### Could a simpler tool do the same?

Partly. A regular-expression scanner could find many of the same columns, and database features (row-level security, column grants, scheduled SQL checks) could enforce access and run the same tests. We did not test these. What we observed is that OpenMetadata brings classification, lineage, tests, ownership and audit into one place, which helps accountability more than detection.

---

## The proof of concept

### What did you build?

A fictional bank, "Borealis Bank of Canada": an operational database (`core_banking`, 10 tables) feeding a warehouse (`bank_dw`, 9 tables: a star schema and three marts) through an ETL job. OpenMetadata 2.0.5 catalogues both, traces column lineage, classifies personal data, runs 12 data-quality tests, applies tag-based policies, and runs approval and feedback workflows. A generator compiles the tags into masked database views. See [architecture.md](architecture.md) and [data-model.md](data-model.md).

### How was the "AI-style" bug made?

The team wrote it by hand to look like an AI-generated error: the ETL checks that a customer agreed to marketing but not whether they later withdrew consent. No AI tool wrote it, so the POC shows such an error can be caught, not how often AI produces one.

### Which defects were planted?

The ETL ignores consent withdrawal; a legacy table stores card CVVs; some closed customers are kept past the seven-year retention period; some postal codes are malformed; personal information hides in legacy `fld_*` columns and in a free-text notes column. See [data-model.md](data-model.md).

### Where does lineage come from?

Our ETL job declares its column mappings and our code publishes them to OpenMetadata as column-level lineage. OpenMetadata did not infer lineage from the SQL. Lineage is only as reliable as the process that registers it.

### Which OpenMetadata problems did you find?

Six behaviours of OpenMetadata 2.0.5 open source:

1. The `metadata classify` command hard-codes the built-in PII classification, so custom recognizers never run. Our workaround is [`classify_with.py`](../poc/om-ext/classify_with.py).
2. There are no built-in recognizers for Canadian identifiers.
3. The sample-data endpoint checks policy tags at table level only, while the permission debugger also counts column tags, so the debugger can say "denied" when the endpoint allows. Our workaround rolls column tags up to the table.
4. Custom Python recognizers are not available in open source, so there is no SIN checksum test.
5. Catalogue policies do not reach the database.
6. The MCP server exposes write tools.

See [results.md](results.md#product-limitations-found).

### How do I run it, and will I get the same numbers?

Run one command, `poc/scripts/run_poc.sh`. It takes about 15 to 20 minutes and needs Docker with at least 4 GB of memory. The data generator uses a fixed seed (5301), so a rerun reproduces the same data and numbers. See [poc/README.md](../poc/README.md) and the [operations guide](operations.md).

### Is any real personal information involved?

No. Every record is synthetic and the bank is fictional. The course forbids collecting data from human participants, and a pre-commit hook blocks personal information from entering this public repository.

---

## Responsibility and ethics

### Who is responsible when AI-written code leaks or corrupts data?

Responsibility is shared, and it cannot be handed to the AI. Developers review and test every pipeline, whoever or whatever wrote it. Data owners and stewards write the business rules and approve AI tags. The bank enforces controls in the database and protects the catalogue as a privileged system (OSFI B-13). Vendors state plainly what their defaults do not do. PIPEDA principle 4.1 keeps a named person accountable.

### What is automation bias, and did you test it?

Automation bias is the tendency to accept automated output without checking it, which gets worse with trust, workload and time pressure (Goddard et al., 2012; Parasuraman & Riley, 1997). We did **not** test it: our reviewers were scripted personas who knew the right answers.

### What is the biggest professional risk you saw?

False assurance: a dashboard of green tests and tagged tables that looks compliant while protecting nothing. A test passes because nobody wrote the right one, a tag set looks complete because the classifier missed a column, or a policy looks enforced because nobody checked the database.

### How was AI used in this project?

See the [AI-use disclosure](ai-use.md). In short: Claude (through Claude Code) helped write the POC code, tests, documentation and drafts of the report and slides; ChatGPT suggested candidate sources. The team checked every number against `poc/results/`, read every source, and is responsible for the analysis and every claim.

---

## Limits

### What can your evidence not show?

- The bank and data are synthetic; real schemas are larger and messier.
- The AI error was simulated, so we did not measure how often AI-written code fails.
- The same team built the data, rules, recognizers and answer key, with no held-out test set.
- We tested one product version (OpenMetadata 2.0.5 open source) and no comparator.
- Reviewers were scripted, so automation bias was not observed.
- Little public data exists on AI-generated defects in Canadian banks.
- Searches were in English, limited to sources accessible through uOttawa, and focused on 2021 to 2026.

So the POC is evidence of feasibility and of specific product behaviour, not proof of production effectiveness or regulatory compliance. Trust the product behaviours (policies that stop at the catalogue, exposed write tools, hard-coded classification) more than the accuracy scores.

### Are the product limitations permanent?

Some, such as the hard-coded classification and the table-level tag check, are defects a later release may fix. Others are built in: a catalogue does not sit in the query path of every database, and AI classification will always need local recognizers and review.

---

## Sources

APA 7. The full list, with every source the project used, is in the team's final report.

- Consumer Financial Protection Bureau. (2024). *TD Bank, N.A. – Furnishing (2024)*. https://www.consumerfinance.gov/enforcement/actions/td-bank-na-furnishing-2024/
- CB Financial Services, Inc. (2026, May 11). *Current report (Form 8-K), Item 1.05: Material cybersecurity incidents*. U.S. Securities and Exchange Commission. https://www.sec.gov/Archives/edgar/data/1605301/000160530126000021/cbfv-20260507.htm
- da Silva, H. A. B., et al. (2025). Análise de ferramentas de código aberto para gestão de metadados: OpenMetadata e Amundsen. In *Anais da Escola Regional de Banco de Dados* (pp. 40–49). https://doi.org/10.5753/erbd.2025.7328
- Goddard, K., Roudsari, A., & Wyatt, J. C. (2012). Automation bias: A systematic review of frequency, effect mediators, and mitigators. *JAMIA, 19*(1), 121–127. https://doi.org/10.1136/amiajnl-2011-000089
- Hou, X., Zhao, Y., Wang, S., & Wang, H. (2026). Model Context Protocol (MCP): Landscape, security threats, and future research directions. *ACM TOSEM, 35*(10). https://doi.org/10.1145/3796519
- KPMG. (2026). *Generative AI adoption in Canadian financial services*. KPMG Canada. https://kpmg.com/ca/en/insights/2026/02/generative-ai-adoption-in-canadian-financial-services.html
- Lin, L., Zhu, Q., Hong, J., Wang, C., Liu, Y., & Wu, R. (2026). Validating LLM-generated SQL queries through metamorphic prompting. *Proceedings of the ACM on Software Engineering, 3*(FSE), Article FSE019. https://doi.org/10.1145/3797146
- Office of the Privacy Commissioner of Canada. (2020, December 14). *Joint investigation of major privacy breach at Desjardins finds failures to meet obligations under privacy law*. https://www.priv.gc.ca/en/opc-news/news-and-announcements/2020/nr-c_201214/
- Office of the Superintendent of Financial Institutions & Financial Consumer Agency of Canada. (2024). *OSFI–FCAC risk report: AI uses and risks at federally regulated financial institutions*. https://www.osfi-bsif.gc.ca/en/about-osfi/reports-publications/osfi-fcac-risk-report-ai-uses-risks-federally-regulated-financial-institutions
- Parasuraman, R., & Riley, V. (1997). Humans and automation: Use, misuse, disuse, abuse. *Human Factors, 39*(2), 230–253. https://doi.org/10.1518/001872097778543886
- Pearce, H., Ahmad, B., Tan, B., Dolan-Gavitt, B., & Karri, R. (2022). Asleep at the keyboard? Assessing the security of GitHub Copilot's code contributions. In *2022 IEEE Symposium on Security and Privacy* (pp. 754–768). https://doi.org/10.1109/SP46214.2022.9833571
- Personal Information Protection and Electronic Documents Act, S.C. 2000, c. 5. https://laws-lois.justice.gc.ca/eng/acts/P-8.6/
- Vengurlekar, K. (2026). *ai-powered-data-governance: OpenMetadata PIPEDA proof-of-concept* (Version 1.0) [Computer software]. GitHub. https://github.com/KshitijV97/ai-powered-data-governance
