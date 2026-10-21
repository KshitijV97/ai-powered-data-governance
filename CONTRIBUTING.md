# Contributing

## Commit messages

This repo follows [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).

```
<type>(<scope>): <summary>

<body: what changed and why, wrapped at ~72 characters>

<footer: Co-Authored-By, Refs, BREAKING CHANGE>
```

### Rules

- **Summary line:** imperative mood ("add", not "added"/"adds"), lower case after the colon, no trailing period, at most 72 characters.
- **Body:** optional for small changes. Explain *why*, not just *what*; the diff already shows what.
- **One logical change per commit.** Don't mix a POC code change with a report edit.
- **Never commit** secrets (`poc/.env`), POC runtime state (`poc/work/`, `poc/docker-volume/`) or the downloaded paper PDFs (`references/papers/*.pdf`). `.gitignore` covers these; check `git status` before committing anyway.
- **AI-assisted work:** if a commit was written with an AI tool, add a `Co-Authored-By:` trailer naming it. This supports the AI-use declaration the course requires (report Appendix D).

### Types

| Type | Use for |
|---|---|
| `feat` | New POC capability (a script, a workflow, a governance rule) |
| `fix` | A bug fix in POC code or config |
| `docs` | Documentation, the report, the proposal, reference lists |
| `data` | Regenerated POC results or evidence in `poc/results/` |
| `refactor` | Code restructuring without a behaviour change |
| `test` | Evaluation or ground-truth changes |
| `build` | Docker, compose files, dependencies |
| `chore` | Repo housekeeping (`.gitignore`, tooling) |

### Scopes

Use the top-level area the change touches: `poc`, `docs`, `report`, `deliverables`, `references`, `repo`.
Leave the scope out if a change really spans several areas.

### Examples

```
feat(poc): add masked analyst views generated from PII tags
fix(poc): retry OpenMetadata health check until the server is up
data(poc): regenerate results after Canada-tuned recognizers
docs(report): add PIPEDA principle 4.7 mapping to the discussion
docs(deliverables): add sources evaluation for evidence 43-82
chore(repo): ignore LaTeX build artifacts
```

## Branches

Work on a short-lived branch (`<name>/<topic>`, e.g. `kshitij/report-discussion`) and open a pull request into `master` so a teammate can review it.
