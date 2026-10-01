"""Parse amounts the way they are printed on invoices, so the model need not convert them.

Lightning sometimes returns Romanian formatting ("2.054,66", "10,00") despite instructions, and
occasionally a mangled "1.069.59". Code normalises; the model only copies.
"""

import re
from decimal import Decimal, InvalidOperation


def parse_amount(value) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))
    s = re.sub(r"[\s ]|RON|EUR|lei|%", "", str(value), flags=re.IGNORECASE)
    if not s:
        return None
    sign = "-" if s.startswith("-") else ""
    s = s.lstrip("+-")
    if not re.fullmatch(r"[\d.,]+", s) or not re.search(r"\d", s):
        return None
    if "," in s and "." in s:
        # The separator that appears last is the decimal one: 1.234,56 or 1,234.56
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        thou = "." if dec == "," else ","
        s = s.replace(thou, "").replace(dec, ".")
    elif "," in s:
        parts = s.split(",")
        # One comma is the Romanian decimal comma (10,00); several are thousands (1,234,567).
        s = ".".join(parts) if len(parts) == 2 else "".join(parts)
    elif s.count(".") > 1:
        parts = s.split(".")
        # 1.234.567 is thousands; 1.069.59 (last group of two) is a mangled decimal
        s = "".join(parts[:-1]) + ("." + parts[-1] if len(parts[-1]) != 3 else parts[-1])
    try:
        return Decimal(sign + s)
    except InvalidOperation:
        return None
