"""Deterministic validation. This is the only source of truth for valid vs invalid."""

from lxml import etree

from facturaguard.validation.cui import cui_is_valid
from facturaguard.validation.models import Issue, ValidationResult
from facturaguard.validation.schematron import validate_schematron
from facturaguard.validation.xsd import validate_xsd

UBL_NS = {
    "Invoice": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "CreditNote": "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2",
}
_XP_NS = {
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}
_PARTIES = {
    "seller": "cac:AccountingSupplierParty/cac:Party",
    "buyer": "cac:AccountingCustomerParty/cac:Party",
}


def _check_identifiers(root: etree._Element) -> list[Issue]:
    issues = []
    for role, path in _PARTIES.items():
        for el in root.xpath(f"{path}/cac:PartyTaxScheme/cbc:CompanyID", namespaces=_XP_NS):
            vat = (el.text or "").strip()
            if vat.startswith("RO") and not cui_is_valid(vat):
                issues.append(
                    Issue(
                        layer="anaf_identifier",
                        rule_id="FG-CUI-CHECKSUM",
                        severity="fatal",
                        message=f"The {role} VAT id {vat} fails the Romanian CUI control-digit check.",
                        location=f"{role} VAT id",
                    )
                )
    return issues


def validate_xml(data: bytes) -> ValidationResult:
    result = ValidationResult()
    try:
        doc = etree.ElementTree(etree.fromstring(data))
    except etree.XMLSyntaxError as e:
        result.issues.append(
            Issue("parse", "XML-WELLFORMED", "fatal", str(e), f"line {e.lineno}")
        )
        return result
    root = doc.getroot()
    kind = next((k for k, ns in UBL_NS.items() if root.tag == f"{{{ns}}}{k}"), None)
    if kind is None:
        result.issues.append(
            Issue("xsd", "XSD-ROOT", "fatal", f"Unsupported root element {root.tag}, expected UBL Invoice or CreditNote.")
        )
        return result
    result.kind = kind
    result.issues += validate_xsd(doc, kind)
    result.issues += validate_schematron(data)
    result.issues += _check_identifiers(root)
    return result
