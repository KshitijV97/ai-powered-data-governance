"""Integration tests read the evidence of a completed POC run.

They run against poc/results/ (or the directory in POC_TEST_RESULTS_DIR) and
are skipped when that directory has no summary.json, i.e. before the first run.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

DEFAULT_RESULTS = Path(__file__).resolve().parents[2] / "results"


def results_dir() -> Path:
    return Path(os.getenv("POC_TEST_RESULTS_DIR", DEFAULT_RESULTS))


def pytest_collection_modifyitems(config, items):
    if (results_dir() / "summary.json").exists():
        return
    skip = pytest.mark.skip(
        reason=f"no completed POC run: {results_dir() / 'summary.json'} not found "
        "(run poc/scripts/run_poc.sh or set POC_TEST_RESULTS_DIR)"
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def load():
    def _load(name: str):
        return json.loads((results_dir() / name).read_text())

    return _load


@pytest.fixture(scope="session")
def summary(load):
    return load("summary.json")
