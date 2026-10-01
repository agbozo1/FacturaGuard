"""Build UBL from extracted fields with deterministic code, then validate it as usual.

The printed totals are kept even when they disagree with the lines, so an arithmetic mistake on
the original PDF shows up as a validator error instead of being silently corrected.
"""

import re
from dataclasses import dataclass, field
from decimal import Decimal

from facturaguard.extraction.numbers import parse_amount
from facturaguard.ubl.codes import bucharest_sector, county_code, normalise, unit_code
from facturaguard.ubl.render import CUSTOMIZATION_ID, TOTAL_KEYS, compute_totals, money, render

COUNTRIES = {
    "romania": "RO", "germany": "DE", "germania": "DE", "deutschland": "DE", "france": "FR",
    "franta": "FR", "italy": "IT", "italia": "IT", "hungary": "HU", "ungaria": "HU",
    "bulgaria": "BG", "austria": "AT", "spain": "ES", "spania": "ES", "netherlands": "NL",
    "olanda": "NL", "poland": "PL", "polonia": "PL", "moldova": "MD",
    "republica moldova": "MD", "united kingdom": "GB", "marea britanie": "GB",
}


@dataclass
class BuildResult:
    xml: str
    model: dict
    warnings: list[str] = field(default_factory=list)


def _dec(value, warnings: list[str], what: str) -> Decimal | None:
    if value is None or value == "":
        return None
    amount = parse_amount(value)
    if amount is None:
        warnings.append(f"{what}: '{value}' is not a number")
    return amount


_ADDRESS_TAIL = re.compile(r",\s*(?=jud(?:e[tț]ul)?\b\.?|\d{6}\b|rom[aâ]nia\b|bucure[sș]ti\b)",
                           re.IGNORECASE)
_COUNTY_IN_TEXT = re.compile(r"\bjud(?:e[tț]ul)?\.?\s+([^,\d]+)", re.IGNORECASE)


def _split_address(street: str, city: str | None) -> str:
    """The model sometimes pastes the whole address line into `street`; keep the street part."""
    cuts = [m.start() for m in _ADDRESS_TAIL.finditer(street)]
    if city and f", {city}" in street:
        cuts.append(street.index(f", {city}"))
    return street[: min(cuts)].strip() if cuts else street


def _country(value: str | None) -> str | None:
    if not value:
        return None
    v = value.strip()
    if re.fullmatch(r"[A-Za-z]{2}", v):
        return v.upper()
    return COUNTRIES.get(normalise(v), v)


def _party(p: dict | None, warnings: list[str], role: str) -> dict:
    p = p or {}
    country = _country(p.get("country"))
    city, county = p.get("city"), p.get("county")
    raw_street = p.get("street") or ""
    address_text = ", ".join(x for x in (raw_street, city, county) if x)
    if not county:  # recover "Jud. Cluj" or Bucharest from the address text itself
        m = _COUNTY_IN_TEXT.search(address_text)
        if m:
            county = m.group(1).strip()
        elif "bucuresti" in normalise(address_text):
            county = "Bucuresti"
    if country is None and "romania" in normalise(address_text):
        country = "RO"
    street = _split_address(raw_street, city) or None
    subdivision = county_code(county)
    is_bucharest = subdivision == "RO-B" or "bucuresti" in normalise(city or "")
    if country is None and (subdivision or p.get("vat_id", "") or "").startswith("RO"):
        country = "RO"  # Romanian county or RO VAT id printed, country line omitted
    if is_bucharest:
        subdivision = "RO-B"
        sector = bucharest_sector(city, address_text, county)
        if sector:
            city = sector
        else:
            warnings.append(f"{role}: Bucharest address without a sector (1 to 6)")
    elif country == "RO" and county and not subdivision:
        warnings.append(f"{role}: county '{county}' not recognised")
        subdivision = county
    vat = re.sub(r"\s+", "", p.get("vat_id") or "") or None
    return {
        "legal_name": p.get("name"),
        "vat_id": vat,
        "reg_no": p.get("registration_number"),
        "street": street,
        "city": city,
        "postal": p.get("postal_code"),
        "subdivision": subdivision,
        "country": country,
        "iban": re.sub(r"\s+", "", p.get("iban") or "") or None,
    }


def build_from_fields(fields: dict) -> BuildResult:
    warnings: list[str] = []
    lines = []
    for n, raw in enumerate(fields.get("lines") or [], 1):
        qty = _dec(raw.get("quantity"), warnings, f"line {n} quantity") or Decimal(1)
        price = _dec(raw.get("unit_price"), warnings, f"line {n} unit price")
        amount = _dec(raw.get("line_total"), warnings, f"line {n} total")
        rate = _dec(raw.get("vat_rate"), warnings, f"line {n} VAT rate")
        if amount is None and price is not None:
            amount = money(qty * price)
        if price is None and amount is not None:
            price = money(amount / qty) if qty else amount
        if amount is None:
            warnings.append(f"line {n}: no amount, skipped")
            continue
        if rate is None:
            warnings.append(f"line {n}: no VAT rate printed")
            rate = Decimal(0)
        if price is not None and abs(money(qty * price) - money(amount)) > Decimal("0.01"):
            # A real printed mistake or a misread column; either way a person should look.
            warnings.append(f"line {n}: quantity x unit price = {money(qty * price)} but the "
                            f"line total read is {money(amount)}; please check the PDF")
        unit = unit_code(raw.get("unit"))
        if raw.get("unit") and not unit:
            warnings.append(f"line {n}: unit '{raw.get('unit')}' not recognised")
        name = raw.get("description")
        if name and raw.get("unit") and name.endswith(" " + str(raw["unit"]).strip()):
            name = name[: -len(str(raw["unit"]).strip())].rstrip()  # unit column leaked in
        lines.append({"id": str(n), "name": name, "unit": unit or "C62",
                      "qty": qty, "price": price, "amount": money(amount), "rate": rate})

    currency = (fields.get("currency") or "").strip().upper() or None
    model = {
        "customization": CUSTOMIZATION_ID,
        "number": fields.get("invoice_number"),
        "issue_date": fields.get("issue_date"),
        "due_date": fields.get("due_date"),
        "type_code": "380",
        "currency": currency,
        "seller": _party(fields.get("seller"), warnings, "seller"),
        "buyer": _party(fields.get("buyer"), warnings, "buyer"),
        "lines": lines,
        "delta": {},
    }

    # Reproduce the printed totals as deltas over what the lines imply.
    base = compute_totals(model)
    printed = fields.get("totals") or {}
    mapping = {"total_without_vat": ("line_sum", "tax_excl"), "total_vat": ("tax_total",),
               "total_with_vat": ("tax_incl",), "amount_due": ("payable",)}
    for src, keys in mapping.items():
        value = _dec(printed.get(src), warnings, f"printed {src}")
        if value is None:
            continue
        for key in keys:
            if key in TOTAL_KEYS and value != base[key]:
                model["delta"][key] = value - base[key]
    breakdown = fields.get("vat_breakdown") or []
    if breakdown and base["subtotals"]:
        first_rate = next(iter(base["subtotals"]))
        for row in breakdown:
            if _dec(row.get("rate"), warnings, "VAT breakdown rate") == Decimal(first_rate):
                printed_tax = _dec(row.get("vat_amount"), warnings, "VAT breakdown amount")
                if printed_tax is not None and printed_tax != base["subtotals"][first_rate][1]:
                    model["delta"]["subtotal_tax"] = printed_tax - base["subtotals"][first_rate][1]
    return BuildResult(xml=render(model), model=model, warnings=warnings)
