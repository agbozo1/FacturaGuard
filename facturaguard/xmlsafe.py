"""Hardened XML parsing for untrusted uploads.

UBL invoices never need a DOCTYPE, so any DTD or entity declaration is refused before parsing
(blocks XXE and entity-expansion attacks in both lxml and Saxon). Network access and DTD
loading are off as a second line of defence.
"""

import re

from lxml import etree

_DTD = re.compile(rb"<!\s*(DOCTYPE|ENTITY)", re.IGNORECASE)
_PARSER = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False,
                          huge_tree=False)


class UnsafeXML(ValueError):
    pass


def check_bytes(data: bytes) -> None:
    if _DTD.search(data[:4096]) or _DTD.search(data):
        raise UnsafeXML("DOCTYPE and ENTITY declarations are not allowed in e-Factura XML.")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as e:
        raise UnsafeXML(f"The file must be UTF-8 encoded (ANAF requires UTF-8): {e}") from e


def parse(data: bytes) -> etree._Element:
    """Parse untrusted XML. Raises UnsafeXML or etree.XMLSyntaxError."""
    check_bytes(data)
    return etree.fromstring(data, parser=_PARSER)
