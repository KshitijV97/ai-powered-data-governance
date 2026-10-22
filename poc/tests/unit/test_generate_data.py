"""Synthetic data generators: Luhn validity, postal-code format, determinism."""

import random
import re

import pytest

from poc import config
from poc import generate_data as gd
from poc import governance_model as gm


def luhn_valid(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


@pytest.fixture(autouse=True)
def seeded_rng(monkeypatch):
    """generate_data draws from a module-level RNG; give each test a fresh seeded one."""
    monkeypatch.setattr(gd, "rng", random.Random(config.SEED))


@pytest.mark.parametrize("prefix,expected", [("7992739871", "79927398713"), ("4", "42"), ("0", "00")])
def test_luhn_complete_known_values(prefix, expected):
    assert gd.luhn_complete(prefix) == expected


def test_luhn_complete_always_valid():
    r = random.Random(1)
    for _ in range(500):
        prefix = "".join(r.choices("0123456789", k=r.randint(1, 18)))
        out = gd.luhn_complete(prefix)
        assert out[:-1] == prefix and luhn_valid(out)


def test_synthetic_sin_format_and_luhn():
    sin_re = re.compile(r"^[1-7]\d{2}-\d{3}-\d{3}$")
    for _ in range(300):
        sin = gd.synthetic_sin()
        assert sin_re.match(sin), sin
        assert luhn_valid(sin.replace("-", ""))


def test_synthetic_pan_format_and_luhn():
    pan_re = re.compile(r"^4\d{3}( \d{4}){3}$")
    for _ in range(300):
        pan = gd.synthetic_pan()
        assert pan_re.match(pan), pan
        assert luhn_valid(pan.replace(" ", ""))


@pytest.mark.parametrize("fsa", sorted({p[1] for p in gd.PROVINCES.values()}))
def test_postal_code_matches_ca_postal(fsa):
    pattern = re.compile(gm.CA_POSTAL)
    for _ in range(200):
        pc = gd.postal_code(fsa)
        assert pc[0] in fsa
        m = pattern.search(pc)
        assert m and m.group(0) == pc, pc


def test_generate_is_deterministic_for_fixed_seed(monkeypatch):
    first = gd.generate(n_customers=40)
    monkeypatch.setattr(gd, "rng", random.Random(config.SEED))
    second = gd.generate(n_customers=40)
    assert first == second


def test_generate_differs_for_other_seed(monkeypatch):
    first = gd.generate(n_customers=40)
    monkeypatch.setattr(gd, "rng", random.Random(config.SEED + 1))
    assert gd.generate(n_customers=40)["customers"] != first["customers"]


def test_generate_shape():
    data = gd.generate(n_customers=40)
    assert set(data) == {"branches", "customers", "consents", "accounts", "cards", "docs", "tickets",
                         "txns", "legacy", "fx"}
    assert len(data["customers"]) == 40
    assert len(data["consents"]) == 40 * 5            # five consent purposes per customer
    assert len(data["docs"]) == 40                    # one identity document per customer
    assert len(data["branches"]) == 20
    assert len(data["legacy"]) == 400
    for card in data["cards"]:
        assert luhn_valid(card[2].replace(" ", ""))
