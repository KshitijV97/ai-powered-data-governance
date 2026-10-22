# Testing

The POC has two pytest suites under [`poc/tests/`](../poc/tests/). Neither needs Docker.

| Suite | Path | What it checks | Runs in CI |
|---|---|---|---|
| Unit | `poc/tests/unit/` | Pure functions in `poc/toolbox/poc/`: recognizer regexes, synthetic data generators, precision/recall/F1 maths, sensitivity roll-up, ground-truth labels | Yes, on every push and pull request ([`tests.yml`](../.github/workflows/tests.yml)), and in the pre-commit hook |
| Integration | `poc/tests/integration/` | The evidence of a completed run in `poc/results/`: F1 scores, data-quality failures, catalogue and warehouse access checks | No |

These are **code tests**. They are separate from the PIPEDA data-quality tests (`p4_*`) that the POC registers in OpenMetadata: those are compliance checks on the synthetic data and are *meant* to fail on the planted defects (see [Results](results.md)).

## Setup

```bash
pip install -r poc/requirements-dev.txt
```

That installs pytest, plus Ruff and pre-commit for the Git hook that runs the unit tests before each commit (see [Contributing](../CONTRIBUTING.md#code-style-and-pre-commit-hook)). The unit tests never connect to Postgres or OpenMetadata, so when `psycopg`, `requests` or `PyYAML` are not installed, [`poc/tests/conftest.py`](../poc/tests/conftest.py) replaces them with empty stand-in modules. The same conftest puts `poc/toolbox` on `sys.path`, so tests import `poc.<module>` just as the toolbox image does.

## Running

Unit tests only (what CI runs):

```bash
pytest poc/tests/unit
```

Integration tests against the committed `poc/results/`:

```bash
pytest -m integration
```

Integration tests against another run's output, for example a fresh run you have not committed yet:

```bash
POC_TEST_RESULTS_DIR=/path/to/results pytest -m integration
```

Plain `pytest` from the repo root runs both suites ([`pytest.ini`](../pytest.ini) sets `testpaths` and registers the `integration` marker). Integration tests are skipped, not failed, when the results directory has no `summary.json`.

## What the integration tests expect

They pin the headline numbers in [Results](results.md). After a change that is meant to move a number (a new recognizer, another planted defect), re-run the POC, commit the new `poc/results/` as a `data` commit and update the expectations in [`test_results.py`](../poc/tests/integration/test_results.py) in the same pull request.

| Area | Expectation |
|---|---|
| Classification | F1 0.783 (out of the box), 0.943 (Canada-tuned), 1.000 (after steward feedback) over 145 columns, 25 positives |
| Data quality | 6 of 12 tests fail: 55 withdrawn-consent rows, 38 + 38 past-retention customers, 1 239 stored CVVs, 240 e-mail and 17 postal-code format failures |
| Catalogue access | 7 of 7 checks return the expected HTTP status (403 for marketing on PI tables and on tag tampering) |
| Warehouse access | 7 of 7 checks as expected, including `marketing_analyst` denied `SELECT email FROM dw.dim_customer` |

## Known issues the tests document

- `evaluate_classification.evaluate()` computes `pipeda_exact_class_accuracy` with an operator-precedence slip: a column tagged `PIPEDA.NonPersonal` counts as an exact match whatever its ground truth. The headline precision/recall/F1 are not affected. A strict `xfail` test records it; when the bug is fixed the test starts passing and pytest reports it, so remove the `xfail` marker then.

## What is not unit-tested

Modules that only orchestrate calls to OpenMetadata or Postgres (`bootstrap_governance`, `workflows`, `human_in_the_loop`, `mcp_demo`, `etl_to_dw`, `compliance_report`, and the `build`/`verify` halves of `enforce_from_catalog`) are covered only indirectly, through the integration tests on their output. Testing them directly would need a mocked OpenMetadata API or a running stack.
