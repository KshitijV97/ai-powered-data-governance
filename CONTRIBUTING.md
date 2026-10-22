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
| `style` | Formatting only (e.g. a `ruff format` pass), no behaviour change |
| `test` | Code tests in `poc/tests/`, evaluation or ground-truth changes |
| `build` | Docker, compose files, dependencies |
| `ci` | GitHub Actions workflows |
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
test(poc): cover the SIN and postal-code recognizers
```

## Code style and pre-commit hook

Python code is linted and formatted with [Ruff](https://docs.astral.sh/ruff/), configured in [`ruff.toml`](ruff.toml) (Python 3.12, 100-character lines).
Set up the Git hook once per clone:

```bash
pip install -r poc/requirements-dev.txt
pre-commit install
```

From then on every `git commit` runs [`.pre-commit-config.yaml`](.pre-commit-config.yaml):

1. `ruff check --fix` lints the staged Python files and fixes what it safely can,
2. `ruff format` formats them,
3. the unit tests (`pytest poc/tests/unit`) run when the commit touches any Python file.

If Ruff changes a file, the commit stops: review the change, `git add` it and commit again.
Run every hook over the whole repo with `pre-commit run --all-files`.
CI runs the same checks (`ruff check`, `ruff format --check`, unit tests) on every push and pull request, so skipping the hook with `--no-verify` only moves the failure to CI.

To leave a hand-laid-out data table alone, wrap it in `# fmt: off` / `# fmt: on` (see the lookup tables in `generate_data.py`).
When bumping Ruff, change the version in both `poc/requirements-dev.txt` and the `rev` in `.pre-commit-config.yaml`.

**Editor:** the repo ships VS Code settings (format on save with Ruff, pytest test explorer) and recommended extensions in [`.vscode/`](.vscode/); VS Code offers to install them when you open the folder.
`git blame` skips the bulk reformat commit if you run `git config blame.ignoreRevsFile .git-blame-ignore-revs` (GitHub does this automatically).

## Branches

Work on a short-lived branch (`<name>/<topic>`, e.g. `kshitij/report-discussion`) and open a pull request into `master` so a teammate can review it.
