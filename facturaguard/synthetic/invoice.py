"""Synthetic UBL 2.1 / CIUS-RO invoice model and renderer. Synthetic data only."""

import random
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from xml.sax.saxutils import escape

from facturaguard.synthetic.identifiers import make_cui, make_iban

CUSTOMIZATION_ID = "urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.1"
# Romanian VAT rates since 1 Aug 2025 (standard 21, reduced 11). Verify against ANAF guidance.
VAT_RATES = [21, 21, 21, 11]
NS = (
    'xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" '
    'xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" '
    'xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"'
)

RO_CITIES = [
    ("RO-B", "SECTOR3", "030167", "Str. Exemplu"),
    ("RO-CJ", "Cluj-Napoca", "400001", "Str. Test"),
    ("RO-TM", "Timisoara", "300001", "Bd. Demo"),
    ("RO-IS", "Iasi", "700001", "Str. Proba"),
    ("RO-BV", "Brasov", "500001", "Str. Model"),
]
EU_BUYERS = [
    ("DE", "Berlin", "10115", "Teststrasse", "DE"),
    ("FR", "Paris", "75001", "Rue de l'Exemple", "FR"),
    ("IT", "Milano", "20100", "Via di Prova", "IT"),
    ("HU", "Budapest", "1051", "Teszt utca", "HU"),
    ("BG", "Sofia", "1000", "ul. Probna", "BG"),
]
SELLER_NAMES = ["Alfa", "Bravo", "Delta", "Orion", "Vega", "Nord", "Atlas", "Luna", "Zenit", "Pixel"]
BUYER_NAMES = ["Kappa", "Sigma", "Omega", "Titan", "Helios", "Nova", "Apex", "Lotus", "Cedar"]
PRODUCTS = [
    ("Servicii consultanta", "HUR"),
    ("Licenta software anuala", "C62"),
    ("Transport marfa", "C62"),
    ("Hartie A4 (top)", "C62"),
    ("Cafea boabe 1kg", "C62"),
    ("Mentenanta website", "HUR"),
    ("Echipament birou", "C62"),
]


def money(x) -> Decimal:
    return Decimal(x).quantize(Decimal("0.01"), ROUND_HALF_UP)


def _ro_party(rng: random.Random, names: list[str]) -> dict:
    sub, city, postal, street = rng.choice(RO_CITIES)
    cui = make_cui(rng)
    return {
        "legal_name": f"{rng.choice(names)} Test {rng.randint(1, 99)} SRL",
        "vat_id": f"RO{cui}",
        "reg_no": f"J{rng.randint(1, 40)}/{rng.randint(100, 9999)}/{rng.randint(2005, 2024)}",
        "street": f"{street} {rng.randint(1, 120)}",
        "city": city,
        "postal": postal,
        "subdivision": sub,
        "country": "RO",
    }


def _eu_party(rng: random.Random) -> dict:
    cc, city, postal, street, prefix = rng.choice(EU_BUYERS)
    return {
        "legal_name": f"{rng.choice(BUYER_NAMES)} Muster {rng.randint(1, 99)} GmbH",
        "vat_id": f"{prefix}{rng.randint(100_000_000, 999_999_999)}",
        "reg_no": None,
        "street": f"{street} {rng.randint(1, 120)}",
        "city": city,
        "postal": postal,
        "subdivision": None,
        "country": cc,
    }


def build_invoice(rng: random.Random, index: int) -> dict:
    issue = date(2026, 1, 5) + timedelta(days=rng.randint(0, 250))
    lines = []
    for n in range(1, rng.randint(1, 5) + 1):
        name, unit = rng.choice(PRODUCTS)
        qty = Decimal(rng.choice([1, 2, 3, 5, 10]))
        price = Decimal(rng.randint(500, 250_000)) / Decimal(100)
        lines.append(
            {
                "id": str(n),
                "name": name,
                "unit": unit,
                "qty": qty,
                "price": money(price),
                "amount": money(qty * price),
                "rate": rng.choice(VAT_RATES),
            }
        )
    seller = _ro_party(rng, SELLER_NAMES)
    seller["iban"] = make_iban(rng)
    buyer = _ro_party(rng, BUYER_NAMES) if rng.random() < 0.7 else _eu_party(rng)
    return {
        "customization": CUSTOMIZATION_ID,
        "number": f"FG-2026-{index:04d}",
        "issue_date": issue.isoformat(),
        "due_date": (issue + timedelta(days=30)).isoformat(),
        "type_code": "380",
        "currency": "RON",
        "seller": seller,
        "buyer": buyer,
        "lines": lines,
        "delta": {},
    }


def shift(m: dict, **deltas) -> None:
    """Add amounts to computed totals, to plant a specific arithmetic error."""
    for key, value in deltas.items():
        m["delta"][key] = m["delta"].get(key, Decimal(0)) + Decimal(value)


def compute_totals(m: dict) -> dict:
    by_rate: dict[int, Decimal] = {}
    for line in m["lines"]:
        by_rate[line["rate"]] = by_rate.get(line["rate"], Decimal(0)) + line["amount"]
    subtotals = {r: (t, money(t * r / 100)) for r, t in sorted(by_rate.items())}
    line_sum = sum((line["amount"] for line in m["lines"]), Decimal(0))
    tax_total = sum((tax for _, tax in subtotals.values()), Decimal(0))
    d = m["delta"]
    first = next(iter(subtotals), None)
    if first is not None:
        taxable, tax = subtotals[first]
        subtotals[first] = (taxable, tax + d.get("subtotal_tax", Decimal(0)))
    tax_excl = line_sum
    tax_incl = tax_excl + tax_total
    return {
        "subtotals": subtotals,
        "line_sum": line_sum + d.get("line_sum", Decimal(0)),
        "tax_excl": tax_excl + d.get("tax_excl", Decimal(0)),
        "tax_total": tax_total + d.get("tax_total", Decimal(0)),
        "tax_incl": tax_incl + d.get("tax_incl", Decimal(0)),
        "payable": tax_incl + d.get("payable", Decimal(0)),
    }


def _tag(name: str, text=None, attrs: str = "") -> str:
    if text is None:
        return ""
    return f"<{name}{' ' + attrs if attrs else ''}>{escape(str(text))}</{name}>"


def _wrap(name: str, *children: str) -> str:
    kids = [c for c in children if c]
    if not kids:
        return ""
    return f"<{name}>" + "".join(kids) + f"</{name}>"


def _party(p: dict) -> str:
    return _wrap(
        "cac:Party",
        _wrap("cac:PartyName", _tag("cbc:Name", p["legal_name"])),
        _wrap(
            "cac:PostalAddress",
            _tag("cbc:StreetName", p["street"]),
            _tag("cbc:CityName", p["city"]),
            _tag("cbc:PostalZone", p["postal"]),
            _tag("cbc:CountrySubentity", p["subdivision"]),
            _wrap("cac:Country", _tag("cbc:IdentificationCode", p["country"])),
        ),
        _wrap(
            "cac:PartyTaxScheme",
            _tag("cbc:CompanyID", p["vat_id"]),
            _wrap("cac:TaxScheme", _tag("cbc:ID", "VAT")),
        ),
        _wrap(
            "cac:PartyLegalEntity",
            _tag("cbc:RegistrationName", p["legal_name"]),
            _tag("cbc:CompanyID", p["reg_no"]),
        ),
    )


def render(m: dict) -> str:
    t = compute_totals(m)
    cur = f'currencyID="{m["currency"] or "RON"}"'

    def amt(name: str, value: Decimal) -> str:
        return _tag(name, f"{value:.2f}", cur)

    def category(rate: int) -> str:
        return _wrap(
            "cac:TaxCategory",
            _tag("cbc:ID", "S"),
            _tag("cbc:Percent", f"{rate:.2f}"),
            _wrap("cac:TaxScheme", _tag("cbc:ID", "VAT")),
        )

    subtotal_xml = "".join(
        _wrap(
            "cac:TaxSubtotal",
            amt("cbc:TaxableAmount", taxable),
            amt("cbc:TaxAmount", tax),
            category(rate),
        )
        for rate, (taxable, tax) in t["subtotals"].items()
    )
    lines_xml = "".join(
        _wrap(
            "cac:InvoiceLine",
            _tag("cbc:ID", line["id"]),
            _tag("cbc:InvoicedQuantity", f"{line['qty']:.2f}", f'unitCode="{line["unit"]}"'),
            amt("cbc:LineExtensionAmount", line["amount"]),
            _wrap(
                "cac:Item",
                _tag("cbc:Name", line["name"]),
                _wrap(
                    "cac:ClassifiedTaxCategory",
                    _tag("cbc:ID", "S"),
                    _tag("cbc:Percent", f"{line['rate']:.2f}"),
                    _wrap("cac:TaxScheme", _tag("cbc:ID", "VAT")),
                ),
            ),
            _wrap("cac:Price", amt("cbc:PriceAmount", line["price"])),
        )
        for line in m["lines"]
    )
    body = "".join(
        [
            _tag("cbc:CustomizationID", m["customization"]),
            _tag("cbc:ID", m["number"]),
            _tag("cbc:IssueDate", m["issue_date"]),
            _tag("cbc:DueDate", m["due_date"]),
            _tag("cbc:InvoiceTypeCode", m["type_code"]),
            _tag("cbc:DocumentCurrencyCode", m["currency"]),
            _wrap("cac:AccountingSupplierParty", _party(m["seller"])),
            _wrap("cac:AccountingCustomerParty", _party(m["buyer"])),
            _wrap(
                "cac:PaymentMeans",
                _tag("cbc:PaymentMeansCode", "30"),
                _wrap("cac:PayeeFinancialAccount", _tag("cbc:ID", m["seller"]["iban"])),
            ),
            _wrap("cac:TaxTotal", amt("cbc:TaxAmount", t["tax_total"]), subtotal_xml),
            _wrap(
                "cac:LegalMonetaryTotal",
                amt("cbc:LineExtensionAmount", t["line_sum"]),
                amt("cbc:TaxExclusiveAmount", t["tax_excl"]),
                amt("cbc:TaxInclusiveAmount", t["tax_incl"]),
                amt("cbc:PayableAmount", t["payable"]),
            ),
            lines_xml,
        ]
    )
    xml = f"<Invoice {NS}>{body}</Invoice>"
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + _pretty(xml)


def _pretty(xml: str) -> str:
    from lxml import etree

    root = etree.fromstring(xml.encode())
    etree.indent(root, space="  ")
    return etree.tostring(root, encoding="unicode") + "\n"
