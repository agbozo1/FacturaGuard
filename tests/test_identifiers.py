"""Identifier checks. Each case mirrors a probe run against ANAF's offline validator 1.3.0."""

import random

import pytest
from lxml import etree

from facturaguard.synthetic.invoice import build_invoice, eu_party, render
from facturaguard.validation.cui import cnp_is_valid, cui_control_digit
from facturaguard.validation.identifiers import check_identifiers

VALID_CUI = "4417203" + str(cui_control_digit("4417203"))
BAD_CUI = VALID_CUI[:-1] + str((int(VALID_CUI[-1]) + 1) % 10)


def _rules(seller_vat=None, buyer_vat=None, buyer_legal="keep", foreign=False):
    m = build_invoice(random.Random(7), 1)
    if foreign:
        m["buyer"] = eu_party(random.Random(7))
    if seller_vat is not None:
        m["seller"]["vat_id"] = seller_vat
    if buyer_vat is not None:
        m["buyer"]["vat_id"] = buyer_vat
    if buyer_legal != "keep":
        m["buyer"]["reg_no"] = buyer_legal
    root = etree.fromstring(render(m).encode())
    return sorted(i.rule_id for i in check_identifiers(root))


@pytest.mark.parametrize(
    ("kwargs", "expected", "anaf_said"),
    [
        ({}, [], "este valid"),
        ({"seller_vat": f"RO{BAD_CUI}"}, ["FG-CUI-SELLER"], "CUI vanzator incorect"),
        ({"buyer_vat": f"RO{BAD_CUI}"}, ["FG-CUI-BUYER"], "CUI cumparator incorect"),
        ({"foreign": True}, ["FG-BUYER-ID"], "nu a fost identificat cui cumparator"),
        ({"foreign": True, "buyer_legal": "0" * 13}, [], "este valid"),
        ({"foreign": True, "buyer_legal": VALID_CUI}, [], "este valid"),
        ({"foreign": True, "buyer_legal": f"RO{VALID_CUI}"}, [], "este valid"),
        ({"foreign": True, "buyer_legal": "1960101123456"}, [], "este valid"),
        ({"foreign": True, "buyer_legal": "1960101123457"}, ["FG-CNP-BUYER"],
         "CNP sau NIF cumparator incorect"),
        ({"foreign": True, "buyer_legal": "196010112345"}, ["FG-CUI-BUYER"],
         "CUI cumparator incorect"),
        ({"foreign": True, "buyer_legal": "HRB 12345"}, ["FG-BUYER-ID"],
         "nu a fost identificat cui cumparator"),
    ],
)
def test_matches_anaf_offline_validator(kwargs, expected, anaf_said):
    assert _rules(**kwargs) == expected, anaf_said


def test_ro_buyer_without_vat_and_only_trade_register_number_is_not_identified():
    # ANAF probe M: no BT-48, BT-47 = J-number -> "nu a fost identificat cui cumparator"
    m = build_invoice(random.Random(7), 1)
    m["buyer"]["vat_id"] = None
    root = etree.fromstring(render(m).encode())
    assert [i.rule_id for i in check_identifiers(root)] == ["FG-BUYER-ID"]


def test_cnp_checksum():
    assert cnp_is_valid("1960101123456")
    assert cnp_is_valid("0" * 13)
    assert not cnp_is_valid("1960101123457")
    assert not cnp_is_valid("196010112345")
