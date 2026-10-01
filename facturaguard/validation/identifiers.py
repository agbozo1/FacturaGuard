"""Seller and buyer identification checks that ANAF runs outside the Schematron.

Behaviour reproduced from ANAF's offline validator (ROeFacturaValidator 1.3.0, 12.12.2024) by
black-box probing on 2026-10-01; see FEEDBACK.md. Not covered by probing, so not enforced: a
seller without an RO VAT id, and which buyer field wins when BT-48 and BT-47 disagree.

Buyer identification order:
  1. BT-48 buyer VAT id (PartyTaxScheme/CompanyID) of the form RO<digits>: CUI checksum.
  2. else BT-47 buyer legal id (PartyLegalEntity/CompanyID) of the form [RO]<digits>:
     13 digits = CNP/NIF checksum (13 zeros allowed), otherwise CUI checksum.
  3. else the buyer is not identified.
"""

import re

from lxml import etree

from facturaguard.validation.cui import cnp_is_valid, cui_is_valid
from facturaguard.validation.models import Issue

NS = {
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}
SELLER = "cac:AccountingSupplierParty/cac:Party"
BUYER = "cac:AccountingCustomerParty/cac:Party"
_RO_VAT = re.compile(r"RO\d+")
_RO_NUMERIC = re.compile(r"(?:RO)?(\d+)")


def _text(root: etree._Element, path: str) -> str:
    return root.xpath(f"normalize-space({path})", namespaces=NS)


def _issue(rule_id: str, anaf_text: str, message: str, location: str) -> Issue:
    return Issue(
        layer="anaf_identifier",
        rule_id=rule_id,
        severity="fatal",
        message=f"{message} ANAF message: '{anaf_text}'.",
        location=location,
    )


def check_identifiers(root: etree._Element) -> list[Issue]:
    issues = []
    seller_vat = _text(root, f"{SELLER}/cac:PartyTaxScheme/cbc:CompanyID")
    if _RO_VAT.fullmatch(seller_vat) and not cui_is_valid(seller_vat):
        issues.append(_issue(
            "FG-CUI-SELLER", "CUI vanzator incorect",
            f"Seller VAT id {seller_vat} fails the Romanian CUI control-digit check.",
            "BT-31 seller VAT id",
        ))

    buyer_vat = _text(root, f"{BUYER}/cac:PartyTaxScheme/cbc:CompanyID")
    buyer_legal = _text(root, f"{BUYER}/cac:PartyLegalEntity/cbc:CompanyID")
    numeric_legal = _RO_NUMERIC.fullmatch(buyer_legal)
    if _RO_VAT.fullmatch(buyer_vat):
        if not cui_is_valid(buyer_vat):
            issues.append(_issue(
                "FG-CUI-BUYER", "CUI cumparator incorect",
                f"Buyer VAT id {buyer_vat} fails the Romanian CUI control-digit check.",
                "BT-48 buyer VAT id",
            ))
    elif numeric_legal:
        digits = numeric_legal.group(1)
        if len(digits) == 13:
            if not cnp_is_valid(digits):
                issues.append(_issue(
                    "FG-CNP-BUYER", "CNP sau NIF cumparator incorect",
                    f"Buyer legal id {buyer_legal} is not a valid 13-digit CNP or NIF.",
                    "BT-47 buyer legal registration id",
                ))
        elif not cui_is_valid(digits):
            issues.append(_issue(
                "FG-CUI-BUYER", "CUI cumparator incorect",
                f"Buyer legal id {buyer_legal} fails the Romanian CUI control-digit check.",
                "BT-47 buyer legal registration id",
            ))
    else:
        issues.append(_issue(
            "FG-BUYER-ID", "nu a fost identificat cui cumparator",
            "No Romanian buyer identifier found: BT-48 is not an RO VAT id and BT-47 is not a"
            " numeric CUI, CNP or NIF. A foreign VAT id or a trade-register number is not enough.",
            "BT-48 / BT-47 buyer identifiers",
        ))
    return issues
