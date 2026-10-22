"""Table sensitivity roll-up (post_ingestion) and column sensitivity (enforce_from_catalog)."""

import pytest

from poc.enforce_from_catalog import column_sensitivity
from poc.post_ingestion import SENSITIVITY_ORDER, rollup


def table(*column_tags):
    return {
        "columns": [
            {"name": f"c{i}", "tags": [{"tagFQN": t} for t in tags]}
            for i, tags in enumerate(column_tags)
        ]
    }


def rolled(t):
    return [x["tagFQN"] for x in rollup(t)]


@pytest.mark.parametrize("i", range(len(SENSITIVITY_ORDER)))
def test_rollup_most_sensitive_wins(i):
    # Every level from i downwards is present on some column; level i must win.
    levels = SENSITIVITY_ORDER[i:]
    t = table(*[[f"PIPEDA.{lvl}"] for lvl in reversed(levels)])
    assert rolled(t) == [f"PIPEDA.{SENSITIVITY_ORDER[i]}"]


def test_rollup_order_is_highrisk_first():
    assert SENSITIVITY_ORDER == ["HighRisk", "DirectIdentifier", "QuasiIdentifier", "Financial"]


def test_rollup_label_is_automated_classification():
    (label,) = rollup(table(["PIPEDA.DirectIdentifier"]))
    assert label == {
        "tagFQN": "PIPEDA.DirectIdentifier",
        "source": "Classification",
        "labelType": "Automated",
        "state": "Confirmed",
    }


@pytest.mark.parametrize(
    "cols",
    [
        (),
        ([],),
        (["PII.Sensitive"], ["Tier.Tier1"]),
        (["PIPEDAPurpose.Marketing"],),
        (["PIPEDA.NonPersonal"], []),
    ],
)
def test_rollup_no_pipeda_column_tags_means_no_table_tag(cols):
    assert rollup(table(*cols)) == []


def test_rollup_ignores_non_pipeda_tags_next_to_pipeda_ones():
    t = table(["PII.Sensitive", "PIPEDA.Financial"], ["PIPEDAPurpose.Marketing"])
    assert rolled(t) == ["PIPEDA.Financial"]


@pytest.mark.parametrize(
    "tags,expected",
    [
        ([], None),
        ([{"tagFQN": "PII.Sensitive"}], None),
        ([{"tagFQN": "PIPEDA.HighRisk"}], "HighRisk"),
        ([{"tagFQN": "PII.Sensitive"}, {"tagFQN": "PIPEDA.DirectIdentifier"}], "DirectIdentifier"),
        ([{"tagFQN": "PIPEDA.QuasiIdentifier", "source": "Classification"}], "QuasiIdentifier"),
        ([{"tagFQN": "PIPEDA.Consent", "source": "Glossary"}], None),
        (
            [{"tagFQN": "PIPEDA.Consent", "source": "Glossary"}, {"tagFQN": "PIPEDA.Financial"}],
            "Financial",
        ),
    ],
)
def test_column_sensitivity(tags, expected):
    assert column_sensitivity({"name": "c", "tags": tags}) == expected


def test_column_sensitivity_without_tags_key():
    assert column_sensitivity({"name": "c"}) is None


def test_column_sensitivity_first_pipeda_tag_wins():
    col = {"tags": [{"tagFQN": "PIPEDA.Financial"}, {"tagFQN": "PIPEDA.HighRisk"}]}
    assert column_sensitivity(col) == "Financial"
