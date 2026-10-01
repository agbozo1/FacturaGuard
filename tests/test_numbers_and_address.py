from decimal import Decimal

import pytest

from facturaguard.extraction.build import _split_address, build_from_fields
from facturaguard.extraction.numbers import parse_amount


@pytest.mark.parametrize(("raw", "expected"), [
    ("2054.66", "2054.66"), ("2.054,66", "2054.66"), ("10,00", "10.00"), ("1,234.56", "1234.56"),
    ("1.234.567", "1234567"), ("1.069.59", "1069.59"), ("21%", "21"), ("417,45 RON", "417.45"),
    ("-5,00", "-5.00"), (12, "12"),
])
def test_parse_amount(raw, expected):
    assert parse_amount(raw) == Decimal(expected)


@pytest.mark.parametrize("raw", [None, "", "abc", "12a", "RON"])
def test_parse_amount_rejects_non_numbers(raw):
    assert parse_amount(raw) is None


def test_split_address_keeps_only_the_street():
    assert _split_address("Str. Model 36, Brasov, Jud. Brasov, 500001, Romania", "Brasov") \
        == "Str. Model 36"
    assert _split_address("Str. Exemplu 38, Bucuresti Sector 3, 030167, Romania", None) \
        == "Str. Exemplu 38"
    assert _split_address("Str. Mare nr. 5, bl. A, sc. 2", "Iasi") == "Str. Mare nr. 5, bl. A, sc. 2"


def _fields(**over):
    base = {
        "invoice_number": "FG-1", "issue_date": "2026-06-01", "currency": "RON",
        "seller": {"name": "A SRL", "vat_id": "RO44172032", "street": "Str. A 1", "city": "Iasi",
                   "county": "Iasi", "postal_code": "700001", "country": "Romania"},
        "buyer": {"name": "B SRL", "vat_id": "RO44172032",
                  "street": "Str. Model 36, Brasov, Jud. Brasov, 500001, Romania",
                  "city": "Brasov", "county": None, "postal_code": "500001", "country": None},
        "lines": [{"description": "x", "unit": "buc", "quantity": "3,00", "unit_price": "581,19",
                   "line_total": "1.743,57", "vat_rate": "21"}],
    }
    base.update(over)
    return base


def test_builder_recovers_county_trims_street_and_parses_romanian_numbers():
    b = build_from_fields(_fields())
    buyer = b.model["buyer"]
    assert buyer["subdivision"] == "RO-BV" and buyer["street"] == "Str. Model 36"
    assert buyer["country"] == "RO"
    assert b.model["lines"][0]["amount"] == Decimal("1743.57")
    assert not b.warnings


def test_builder_warns_when_a_column_was_misread():
    f = _fields()
    f["lines"][0]["line_total"] = "581.19"  # unit price copied into the total
    assert any("please check the PDF" in w for w in build_from_fields(f).warnings)
