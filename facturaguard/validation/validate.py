"""Deterministic validation. This is the only source of truth for valid vs invalid."""

from lxml import etree

from facturaguard.validation.identifiers import check_identifiers
from facturaguard.validation.models import Issue, ValidationResult
from facturaguard.validation.schematron import validate_schematron
from facturaguard.validation.xsd import validate_xsd

UBL_NS = {
    "Invoice": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "CreditNote": "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2",
}


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
    result.issues += check_identifiers(root)
    return result
