"""Recognizer regexes in governance_model.PIPEDA_TAGS (positive and negative cases)."""

import re

import pytest

from poc import governance_model as gm


def recognizer(name: str) -> re.Pattern:
    for tag in gm.PIPEDA_TAGS:
        for r in tag.get("recognizers", []):
            if r["name"] == name:
                cfg = r["recognizerConfig"]
                flags = re.IGNORECASE if cfg["regexFlags"]["ignoreCase"] else 0
                return re.compile(cfg["patterns"][0]["regex"], flags)
    raise KeyError(name)


def full(pattern: re.Pattern, text: str) -> bool:
    """Content recognizers use \\b anchors; check that the whole value matches."""
    m = pattern.search(text)
    return bool(m) and m.group(0) == text


@pytest.mark.parametrize("code", ["K1A 0B1", "K1A0B1", "K1A-0B1", "H2X 1Y4", "V6B 4Y8", "A1A 1A1", "T2P 2W2"])
def test_ca_postal_accepts_valid(code):
    assert full(re.compile(gm.CA_POSTAL), code)


@pytest.mark.parametrize("code", [
    "90210",        # US ZIP
    "ZZZ 999",      # wrong shape
    "k1p 5j9",      # lower case (recognizer is case-sensitive)
    "D1A 1A1",      # D never used
    "W1A 1A1",      # W not allowed first
    "Z1A 1A1",      # Z not allowed first
    "K1O 1A1",      # O never used
    "K1A 1U1",      # U never used
    "K1A  0B1",     # double space
])
def test_ca_postal_rejects_invalid(code):
    assert not re.compile(gm.CA_POSTAL).search(code)


def test_ca_postal_recognizer_uses_shared_constant():
    assert recognizer("ca_postal_code").pattern == gm.CA_POSTAL


@pytest.mark.parametrize("sin", ["130-692-544", "130 692 544", "999-999-998", "700-000-002"])
def test_sin_formatted_positive(sin):
    assert full(recognizer("ca_sin_formatted"), sin)


@pytest.mark.parametrize("text", ["046-454-286", "846-454-286", "130-692-54", "130/692/544", "1306-92-544", "130692544"])
def test_sin_formatted_negative(text):
    assert not recognizer("ca_sin_formatted").search(text)


@pytest.mark.parametrize("sin", ["130692544", "999999998", "700000002"])
def test_sin_unformatted_positive(sin):
    assert full(recognizer("ca_sin_unformatted"), sin)


@pytest.mark.parametrize("text", ["046454286", "846454286", "13069254", "1306925441", "130-692-544"])
def test_sin_unformatted_negative(text):
    assert not recognizer("ca_sin_unformatted").search(text)


@pytest.mark.parametrize("col", ["sin", "SIN", "sin_no", "sinnumber", "sin_num", "social_insurance",
                                 "social_insurance_number", "socialinsuranceno", "nas"])
def test_sin_column_name_positive(col):
    assert recognizer("ca_sin_column_name").search(col)


@pytest.mark.parametrize("col", ["business", "sin_date", "cousin", "nasdaq", "insurance", "my_sin"])
def test_sin_column_name_negative(col):
    assert not recognizer("ca_sin_column_name").search(col)


@pytest.mark.parametrize("dl", ["S1234-12345-12345", "A0000-00000-00000"])
def test_drivers_licence_on_positive(dl):
    assert full(recognizer("ca_drivers_licence_on"), dl)


@pytest.mark.parametrize("text", ["s1234-12345-12345", "S123-12345-12345", "S1234-1234-12345",
                                  "S12341234512345", "SS1234-12345-12345"])
def test_drivers_licence_on_negative(text):
    assert not recognizer("ca_drivers_licence_on").search(text)


@pytest.mark.parametrize("pp", ["AB123456", "GK999999"])
def test_passport_positive(pp):
    assert full(recognizer("ca_passport"), pp)


@pytest.mark.parametrize("text", ["A1234567", "ABC123456", "AB12345", "AB1234567", "ab123456"])
def test_passport_negative(text):
    assert not recognizer("ca_passport").search(text)


@pytest.mark.parametrize("col", ["cvv", "CVV2", "cvc", "csc", "card_number", "cardnumber", "card_no",
                                 "card_num", "pan", "PAN"])
def test_card_column_name_positive(col):
    assert recognizer("card_column_name").search(col)


@pytest.mark.parametrize("col", ["card_id", "card_status", "pancake", "company", "cvv_check", "expiry_month"])
def test_card_column_name_negative(col):
    assert not recognizer("card_column_name").search(col)


def test_column_name_recognizers_ignore_case_and_content_ones_do_not():
    for tag in gm.PIPEDA_TAGS:
        for r in tag.get("recognizers", []):
            cfg = r["recognizerConfig"]
            if cfg["type"] == "pattern":
                assert cfg["regexFlags"]["ignoreCase"] == (r["target"] == "column_name"), r["name"]
