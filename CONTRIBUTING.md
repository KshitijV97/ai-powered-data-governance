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
- **One logical change per commit.** Don't mix a POC code change with a documentation edit.
- **Never commit** secrets (`poc/.env`), POC runtime state (`poc/work/`, `poc/docker-volume/`) or the downloaded paper PDFs (`references/papers/*.pdf`). `.gitignore` covers these; check `git status` before committing anyway.

### Types

| Type | Use for |
|---|---|
| `feat` | New POC capability (a script, a workflow, a governance rule) |
| `fix` | A bug fix in POC code or config |
| `docs` | Documentation and reference lists |
| `data` | Regenerated POC results or evidence in `poc/results/` |
| `refactor` | Code restructuring without a behaviour change |
| `style` | Formatting only (e.g. a `ruff format` pass), no behaviour change |
| `test` | Code tests in `poc/tests/`, evaluation or ground-truth changes |
| `build` | Docker, compose files, dependencies |
| `ci` | GitHub Actions workflows |
| `chore` | Repo housekeeping (`.gitignore`, tooling) |

### Scopes

Use the top-level area the change touches: `poc`, `docs`, `references`, `repo`.
Leave the scope out if a change really spans several areas.

### Examples

```
feat(poc): add masked analyst views generated from PII tags
fix(poc): retry OpenMetadata health check until the server is up
data(poc): regenerate results after Canada-tuned recognizers
docs(poc): add PIPEDA principle 4.7 mapping to the governance model
docs(references): add open-access links to the paper index
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
3. the unit tests (`pytest poc/tests/unit tools/tests`) run when the commit touches any Python file,
4. `tools/check_personal_data.py` scans the staged files for student numbers and personal e-mail addresses.

If Ruff changes a file, the commit stops: review the change, `git add` it and commit again.
Run every hook over the whole repo with `pre-commit run --all-files`.
CI runs the same checks (`ruff check`, `ruff format --check`, unit tests, personal-data scan) on every push and pull request, so skipping the hook with `--no-verify` only moves the failure to CI.

To leave a hand-laid-out data table alone, wrap it in `# fmt: off` / `# fmt: on` (see the lookup tables in `generate_data.py`).
When bumping Ruff, change the version in both `poc/requirements-dev.txt` and the `rev` in `.pre-commit-config.yaml`.

**Editor:** the repo ships VS Code settings (format on save with Ruff, pytest test explorer) and recommended extensions in [`.vscode/`](.vscode/); VS Code offers to install them when you open the folder.
`git blame` skips the bulk reformat commit if you run `git config blame.ignoreRevsFile .git-blame-ignore-revs` (GitHub does this automatically).

## Branching strategy

The repo uses **GitHub Flow**: one long-lived branch, `master`, plus short-lived topic branches that are merged into it through pull requests.

```mermaid
gitGraph
    commit id: "master"
    branch kshitij/consent-docs
    commit id: "docs(poc): …"
    commit id: "docs(poc): …"
    checkout master
    branch priya/consent-test
    commit id: "feat(poc): …"
    checkout master
    merge kshitij/consent-docs id: "PR #n"
    merge priya/consent-test id: "PR #m"
    commit id: "tag: v1.0" type: HIGHLIGHT
```

### `master`

- `master` is always **working and submittable**: CI is green and `run_poc.sh` runs.
- Nobody commits or pushes to `master` directly. Every change arrives through a pull request.

### Topic branches

- Branch from an up-to-date `master`: `git switch master && git pull && git switch -c <name>/<topic>`.
- Name the branch `<name>/<topic>`, using your first name (or the tool's name) and a short kebab-case topic: `kshitij/consent-docs`, `priya/consent-test`. Branches created by Claude Code sessions are named `claude/<topic>`.
- Keep one topic per branch and keep it short-lived: open the pull request within a few days. Split big work into several pull requests instead of one long-running branch.
- To pick up changes from `master`, merge it into your branch (`git merge origin/master`). Don't rebase or force-push a branch someone else has checked out.

### Pull requests

1. Push the branch and open a pull request into `master`. Its title follows the commit convention above, e.g. `docs(poc): document the consent test`.
2. Fill in the pull request template: what changed, why, and how it was checked.
3. Wait until **CI is green** (`Lint and format`, `Unit tests`). Fix failures on the branch; never skip a check.
4. Get **one review from a teammate**. Changes to `poc/results/` should be reviewed by whoever owns that part of the POC.
5. Merge with **"Create a merge commit"**, so each Conventional Commit on the branch stays in the history, and **delete the branch** afterwards. A branch whose pull request has been merged is finished: start new work on a new branch from `master`.

### Recommended GitHub settings (repo owner)

Under *Settings → Branches → Add branch ruleset* for `master`:

- require a pull request before merging, with 1 approval,
- require the `Lint and format`, `Unit tests` and `No personal information` status checks to pass,
- block force pushes and deletion.

Under *Settings → General → Pull Requests*, tick *Automatically delete head branches*.
