"""Render synthetic invoices as Romanian-style text PDFs, plus the ground-truth fields.

`printed_fields(m)` is the single source of what the PDF shows; the PDF is drawn from it and
the extraction eval compares against it. ASCII only (core PDF fonts), no real data.
"""

from datetime import UTC, datetime
from decimal import Decimal

from fpdf import FPDF

from facturaguard.ubl.codes import COUNTY_NAMES
from facturaguard.ubl.render import compute_totals

UNIT_LABELS = {"HUR": "ora", "C62": "buc"}


def ro_amount(x: Decimal) -> str:
    """1234.5 -> '1.234,50' (Romanian format)."""
    whole, frac = f"{Decimal(x):,.2f}".split(".")
    return whole.replace(",", ".") + "," + frac


def ro_date(iso: str | None) -> str:
    if not iso:
        return ""
    y, m, d = iso.split("-")
    return f"{d}.{m}.{y}"


def _party_fields(p: dict, with_iban: bool) -> dict:
    sub = p.get("subdivision")
    county = COUNTY_NAMES.get(sub, "").title() if sub else None
    city = p.get("city")
    if sub == "RO-B" and city and city.startswith("SECTOR"):
        city, county = f"Bucuresti Sector {city[-1]}", "Bucuresti"
    out = {
        "name": p.get("legal_name"),
        "vat_id": p.get("vat_id"),
        "registration_number": p.get("reg_no"),
        "street": p.get("street"),
        "city": city,
        "county": county,
        "postal_code": p.get("postal"),
        "country": {"RO": "Romania"}.get(p.get("country"), p.get("country")),
    }
    if with_iban:
        out["iban"] = p.get("iban")
    return out


def printed_fields(m: dict) -> dict:
    t = compute_totals(m)
    return {
        "invoice_number": m.get("number"),
        "issue_date": m.get("issue_date"),
        "due_date": m.get("due_date"),
        "currency": m.get("currency"),
        "seller": _party_fields(m["seller"], with_iban=True),
        "buyer": _party_fields(m["buyer"], with_iban=False),
        "lines": [
            {
                "description": line["name"],
                "unit": UNIT_LABELS.get(line["unit"], line["unit"]),
                "quantity": f"{Decimal(line['qty']):.2f}",
                "unit_price": f"{line['price']:.2f}",
                "line_total": f"{line['amount']:.2f}",
                "vat_rate": f"{Decimal(line['rate']):.2f}",
            }
            for line in m["lines"]
        ],
        "vat_breakdown": [
            {"rate": f"{Decimal(r):.2f}", "taxable_amount": f"{taxable:.2f}",
             "vat_amount": f"{tax:.2f}"}
            for r, (taxable, tax) in t["subtotals"].items()
        ],
        "totals": {
            "total_without_vat": f"{t['tax_excl']:.2f}",
            "total_vat": f"{t['tax_total']:.2f}",
            "total_with_vat": f"{t['tax_incl']:.2f}",
            "amount_due": f"{t['payable']:.2f}",
        },
    }


def _address(p: dict) -> str:
    parts = [p["street"], p["city"]]
    if p.get("county") and p["county"] != "Bucuresti":
        parts.append(f"Jud. {p['county']}")
    parts += [p["postal_code"], p["country"]]
    return ", ".join(x for x in parts if x)


def render_pdf(m: dict) -> bytes:
    f = printed_fields(m)
    pdf = FPDF(format="A4")
    pdf.set_creation_date(datetime(2026, 1, 1, tzinfo=UTC))  # reproducible bytes
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "FACTURA", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Nr. factura: {f['invoice_number'] or ''}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Data emiterii: {ro_date(f['issue_date'])}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Data scadentei: {ro_date(f['due_date'])}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"Moneda: {f['currency'] or ''}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    for title, p in (("FURNIZOR", f["seller"]), ("CLIENT", f["buyer"])):
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 6, title, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        rows = [p["name"] or "", f"CIF: {p['vat_id'] or ''}"]
        if p.get("registration_number"):
            rows.append(f"Reg. Com.: {p['registration_number']}")
        rows.append(f"Adresa: {_address(p)}")
        if p.get("iban"):
            rows.append(f"IBAN: {p['iban']}")
        for row in rows:
            pdf.cell(0, 5, row, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    widths = (10, 70, 15, 18, 27, 27, 18)
    head = ("Nr", "Denumire", "U.M.", "Cant.", "Pret unitar", "Valoare", "TVA %")
    pdf.set_font("Helvetica", "B", 9)
    for w, h in zip(widths, head, strict=True):
        pdf.cell(w, 7, h, border=1, align="C")
    pdf.ln()
    pdf.set_font("Helvetica", "", 9)
    for n, line in enumerate(f["lines"], 1):
        cells = (str(n), line["description"], line["unit"],
                 ro_amount(Decimal(line["quantity"])), ro_amount(Decimal(line["unit_price"])),
                 ro_amount(Decimal(line["line_total"])), f"{Decimal(line['vat_rate']):.0f}%")
        for i, (w, c) in enumerate(zip(widths, cells, strict=True)):
            pdf.cell(w, 7, c, border=1, align="L" if i == 1 else "R")
        pdf.ln()
    pdf.ln(4)

    tot = f["totals"]
    rows = [("Total fara TVA", tot["total_without_vat"])]
    rows += [(f"TVA {Decimal(v['rate']):.0f}% (baza {ro_amount(Decimal(v['taxable_amount']))})",
              v["vat_amount"]) for v in f["vat_breakdown"]]
    rows += [("Total TVA", tot["total_vat"]), ("Total cu TVA", tot["total_with_vat"]),
             ("TOTAL DE PLATA", tot["amount_due"])]
    for label, value in rows:
        bold = label == "TOTAL DE PLATA"
        pdf.set_font("Helvetica", "B" if bold else "", 10)
        pdf.cell(150, 6, label, align="R")
        pdf.cell(35, 6, f"{ro_amount(Decimal(value))} {f['currency'] or ''}", align="R",
                 new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, "Document generat sintetic pentru testare. Date fictive.",
             new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
