"""Render an invoice model (plain dict) to UBL 2.1 / CIUS-RO XML.

Used by the synthetic generator and by PDF extraction. Missing values (None) are omitted, so
the validator reports them instead of the renderer guessing.

Model shape:
  customization, number, issue_date, due_date, type_code, currency,
  seller / buyer: legal_name, vat_id, reg_no, street, city, postal, subdivision, country,
                  iban (seller only)
  lines: [{id, name, unit, qty, price, amount, rate}]
  delta: optional adjustments to computed totals, e.g. to reproduce totals printed on a PDF
"""

from decimal import ROUND_HALF_UP, Decimal
from xml.sax.saxutils import escape

from lxml import etree

CUSTOMIZATION_ID = "urn:cen.eu:en16931:2017#compliant#urn:efactura.mfinante.ro:CIUS-RO:1.0.1"
NS = (
    'xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" '
    'xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" '
    'xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"'
)
TOTAL_KEYS = ("line_sum", "tax_excl", "tax_total", "tax_incl", "payable")


def money(x) -> Decimal:
    return Decimal(x).quantize(Decimal("0.01"), ROUND_HALF_UP)


def compute_totals(m: dict) -> dict:
    """Totals implied by the lines, plus any deltas in m["delta"]."""
    by_rate: dict = {}
    for line in m["lines"]:
        by_rate[line["rate"]] = by_rate.get(line["rate"], Decimal(0)) + line["amount"]
    subtotals = {r: (t, money(t * Decimal(r) / 100)) for r, t in sorted(by_rate.items())}
    line_sum = sum((line["amount"] for line in m["lines"]), Decimal(0))
    tax_total = sum((tax for _, tax in subtotals.values()), Decimal(0))
    d = m.get("delta") or {}
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
    if text is None or text == "":
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
        _wrap("cac:PartyName", _tag("cbc:Name", p.get("legal_name"))),
        _wrap(
            "cac:PostalAddress",
            _tag("cbc:StreetName", p.get("street")),
            _tag("cbc:CityName", p.get("city")),
            _tag("cbc:PostalZone", p.get("postal")),
            _tag("cbc:CountrySubentity", p.get("subdivision")),
            _wrap("cac:Country", _tag("cbc:IdentificationCode", p.get("country"))),
        ),
        _wrap(
            "cac:PartyTaxScheme",
            _tag("cbc:CompanyID", p.get("vat_id")),
            _wrap("cac:TaxScheme", _tag("cbc:ID", "VAT")) if p.get("vat_id") else "",
        ),
        _wrap(
            "cac:PartyLegalEntity",
            _tag("cbc:RegistrationName", p.get("legal_name")),
            _tag("cbc:CompanyID", p.get("reg_no")),
        ),
    )


def _rate(rate) -> str:
    return f"{Decimal(rate):.2f}"


def render(m: dict) -> str:
    t = compute_totals(m)
    cur = f'currencyID="{m.get("currency") or "RON"}"'

    def amt(name: str, value: Decimal) -> str:
        return _tag(name, f"{value:.2f}", cur)

    def category(rate) -> str:
        return _wrap(
            "cac:TaxCategory",
            _tag("cbc:ID", "S"),
            _tag("cbc:Percent", _rate(rate)),
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
            _tag("cbc:InvoicedQuantity", f"{Decimal(line['qty']):.2f}",
                 f'unitCode="{escape(str(line.get("unit") or "C62"))}"'),
            amt("cbc:LineExtensionAmount", line["amount"]),
            _wrap(
                "cac:Item",
                _tag("cbc:Name", line.get("name")),
                _wrap(
                    "cac:ClassifiedTaxCategory",
                    _tag("cbc:ID", "S"),
                    _tag("cbc:Percent", _rate(line["rate"])),
                    _wrap("cac:TaxScheme", _tag("cbc:ID", "VAT")),
                ),
            ),
            _wrap("cac:Price", amt("cbc:PriceAmount", line["price"])),
        )
        for line in m["lines"]
    )
    seller = m.get("seller") or {}
    body = "".join(
        [
            _tag("cbc:CustomizationID", m.get("customization")),
            _tag("cbc:ID", m.get("number")),
            _tag("cbc:IssueDate", m.get("issue_date")),
            _tag("cbc:DueDate", m.get("due_date")),
            _tag("cbc:InvoiceTypeCode", m.get("type_code")),
            _tag("cbc:DocumentCurrencyCode", m.get("currency")),
            _wrap("cac:AccountingSupplierParty", _party(seller)),
            _wrap("cac:AccountingCustomerParty", _party(m.get("buyer") or {})),
            _wrap(
                "cac:PaymentMeans",
                _tag("cbc:PaymentMeansCode", "30"),
                _wrap("cac:PayeeFinancialAccount", _tag("cbc:ID", seller.get("iban"))),
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
    root = etree.fromstring(f"<Invoice {NS}>{body}</Invoice>".encode())
    etree.indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + etree.tostring(root, encoding="unicode") + "\n"
