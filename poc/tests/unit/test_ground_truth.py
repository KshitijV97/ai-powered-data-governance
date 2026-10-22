"""Ground-truth labels used to score auto-classification."""

from collections import Counter

from poc import ground_truth as gt


def test_every_label_is_valid():
    assert set(gt.labels().values()) <= {"H", "D", "Q", "F", "N"}


def test_column_count():
    assert len(gt.labels()) == 145


def test_positive_count():
    assert sum(gt.is_positive(v) for v in gt.labels().values()) == 25


def test_distribution():
    assert Counter(gt.labels().values()) == {"N": 105, "D": 18, "Q": 10, "H": 7, "F": 5}


def test_is_positive():
    assert gt.is_positive("H") and gt.is_positive("D")
    assert not any(gt.is_positive(x) for x in ("Q", "F", "N", "?"))


def test_keys_are_db_schema_table_column():
    for key in gt.labels():
        db, schema, table, column = key
        assert db in gt.DATABASES
        assert all(part and "." not in part for part in key)


def test_known_high_risk_columns():
    labels = gt.labels()
    for key in [("core_banking", "core", "customer", "sin"), ("core_banking", "core", "card", "card_number"),
                ("core_banking", "core", "card", "cvv"), ("core_banking", "ops", "legacy_member_import", "fld_02")]:
        assert labels[key] == "H"
