"""Deterministic arithmetic over an invoice, handed to the model so it never computes totals.

Covers the common case: line net amounts, document-level allowances and charges, VAT breakdown
by category and rate, prepaid and rounding amounts. Values are what EN 16931 says the totals
should be, given the lines.
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from lxml import etree

NS = {
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}


def _money(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), ROUND_HALF_UP)


def _dec(root, path: str) -> Decimal:
    total = Decimal(0)
    for el in root.xpath(path, namespaces=NS):
        try:
            total += Decimal((el.text or "0").strip())
        except InvalidOperation:
            continue
    return total


def compute_facts(root: etree._Element) -> dict:
    line_path = "cac:InvoiceLine | cac:CreditNoteLine"
    lines = root.xpath(line_path, namespaces=NS)
    line_sum = _dec(root, "cac:InvoiceLine/cbc:LineExtensionAmount | "
                          "cac:CreditNoteLine/cbc:LineExtensionAmount")
    allowances = _dec(root, "cac:AllowanceCharge[cbc:ChargeIndicator='false']/cbc:Amount")
    charges = _dec(root, "cac:AllowanceCharge[cbc:ChargeIndicator='true']/cbc:Amount")
    prepaid = _dec(root, "cac:LegalMonetaryTotal/cbc:PrepaidAmount")
    rounding = _dec(root, "cac:LegalMonetaryTotal/cbc:PayableRoundingAmount")

    breakdown: dict[tuple[str, str], Decimal] = {}
    for line in lines:
        cat = line.xpath("string(cac:Item/cac:ClassifiedTaxCategory/cbc:ID)", namespaces=NS)
        rate = line.xpath("string(cac:Item/cac:ClassifiedTaxCategory/cbc:Percent)", namespaces=NS)
        amount = _dec(line, "cbc:LineExtensionAmount")
        key = (cat or "?", rate or "0")
        breakdown[key] = breakdown.get(key, Decimal(0)) + amount
    vat_rows = []
    for (cat, rate), taxable in sorted(breakdown.items()):
        try:
            r = Decimal(rate)
        except InvalidOperation:
            r = Decimal(0)
        vat_rows.append({
            "category": cat,
            "rate_percent": rate,
            "taxable_amount": f"{_money(taxable):.2f}",
            "tax_amount": f"{_money(taxable * r / 100):.2f}",
        })
    tax_total = sum((Decimal(v["tax_amount"]) for v in vat_rows), Decimal(0))
    tax_excl = line_sum - allowances + charges
    tax_incl = tax_excl + tax_total
    return {
        "note": "Computed by code from the invoice lines. Use these numbers; do not recompute.",
        "line_count": len(lines),
        "sum_of_line_net_amounts_BT106": f"{_money(line_sum):.2f}",
        "document_allowances_BT107": f"{_money(allowances):.2f}",
        "document_charges_BT108": f"{_money(charges):.2f}",
        "expected_total_without_vat_BT109": f"{_money(tax_excl):.2f}",
        "expected_total_vat_BT110": f"{_money(tax_total):.2f}",
        "expected_total_with_vat_BT112": f"{_money(tax_incl):.2f}",
        "expected_amount_due_BT115": f"{_money(tax_incl - prepaid + rounding):.2f}",
        "expected_vat_breakdown_BG23": vat_rows,
        "caveat": "Line-level allowances or charges inside lines are already in each line amount.",
    }
