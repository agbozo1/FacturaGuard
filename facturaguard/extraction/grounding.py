"""Check that every extracted value actually appears in the PDF text.

A value the model reports but the PDF does not contain is flagged, never silently trusted.
Numbers are compared as decimals in Romanian (1.234,56) or plain (1234.56) notation; dates in
dd.mm.yyyy, dd/mm/yyyy or ISO form; text case- and accent-insensitively.
"""

import re
from decimal import Decimal, InvalidOperation

from facturaguard.ubl.codes import normalise

_NUM = re.compile(r"\d{1,3}(?:[.\s]\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?")
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_NUMERIC_KEYS = {"quantity", "unit_price", "line_total", "vat_rate", "rate", "taxable_amount",
                 "vat_amount", "total_without_vat", "total_vat", "total_with_vat", "amount_due"}


def _numbers_in(text: str) -> set[Decimal]:
    found = set()
    for raw in _NUM.findall(text):
        candidates = {raw}
        if "," in raw:  # Romanian: '.' or space thousands, ',' decimals
            candidates.add(raw.replace(".", "").replace(" ", "").replace(",", "."))
        else:
            candidates.add(raw.replace(" ", ""))
        for c in candidates:
            try:
                found.add(Decimal(c))
            except InvalidOperation:
                pass
    return found


def _date_forms(iso: str) -> list[str]:
    y, m, d = iso.split("-")
    return [iso, f"{d}.{m}.{y}", f"{d}/{m}/{y}", f"{d}-{m}-{y}"]


def _leaves(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _leaves(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _leaves(v, f"{path}[{i}]")
    elif obj is not None and obj != "":
        yield path, obj


def check_grounding(fields: dict, text: str) -> list[dict]:
    """Return the extracted values that could not be found in the text."""
    numbers = _numbers_in(text)
    flat_text = normalise(text)
    compact_text = re.sub(r"\s+", "", text)
    missing = []
    for path, value in _leaves(fields):
        key = path.rsplit(".", 1)[-1]
        sval = str(value).strip()
        if key in _NUMERIC_KEYS:
            try:
                ok = Decimal(sval) in numbers
            except InvalidOperation:
                ok = False
        elif _ISO_DATE.fullmatch(sval):
            ok = any(f in text for f in _date_forms(sval))
        elif key in ("vat_id", "iban", "registration_number", "postal_code", "invoice_number"):
            ok = re.sub(r"\s+", "", sval) in compact_text
        else:
            ok = normalise(sval) in flat_text
        if not ok:
            missing.append({"field": path, "value": sval})
    return missing
