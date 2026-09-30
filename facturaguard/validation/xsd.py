from functools import lru_cache
from pathlib import Path

from lxml import etree

from facturaguard.validation.models import Issue

XSD_DIR = Path(__file__).resolve().parents[2] / "vendor" / "ubl-2.1" / "xsd" / "maindoc"
_FILES = {"Invoice": "UBL-Invoice-2.1.xsd", "CreditNote": "UBL-CreditNote-2.1.xsd"}


@lru_cache
def _schema(kind: str) -> etree.XMLSchema:
    return etree.XMLSchema(etree.parse(str(XSD_DIR / _FILES[kind])))


def validate_xsd(doc: etree._ElementTree, kind: str) -> list[Issue]:
    schema = _schema(kind)
    if schema.validate(doc):
        return []
    return [
        Issue(
            layer="xsd",
            rule_id="XSD",
            severity="fatal",
            message=err.message,
            location=f"line {err.line}",
        )
        for err in schema.error_log
    ]
