"""Make synthetic scanned invoices for tests, samples and evals (dev tool; needs Playwright).

    python scripts/make_scans.py [SYN-001 SYN-003 ...]

Renders each invoice's printed fields as an A4 page image, degrades it like a scanner would
(greyscale, slight tilt, blur, speckle, JPEG compression) and wraps it in an image-only PDF with
no text layer. Output: data/synthetic/scans/<id>-scan.pdf and manifest.json (ground truth).
"""

import io
import json
import random
import sys
import zlib
from pathlib import Path

from fpdf import FPDF
from PIL import Image, ImageFilter
from playwright.sync_api import sync_playwright

from facturaguard.synthetic.pdf import _address, ro_amount, ro_date

ROOT = Path(__file__).resolve().parents[1] / "data" / "synthetic"
OUT = ROOT / "scans"
DEFAULT_IDS = ["SYN-001", "SYN-002", "SYN-003", "SYN-007", "SYN-035", "SYN-037", "SYN-039",
               "SYN-041", "SYN-043", "SYN-045", "SYN-075", "SYN-077", "SYN-079"]


def page_html(f: dict) -> str:
    def party(title: str, p: dict) -> str:
        rows = [f"<b>{title}</b>", p["name"] or "", f"CIF: {p['vat_id'] or ''}"]
        if p.get("registration_number"):
            rows.append(f"Reg. Com.: {p['registration_number']}")
        rows.append(f"Adresa: {_address(p)}")
        if p.get("iban"):
            rows.append(f"IBAN: {p['iban']}")
        return "<div class=party>" + "<br>".join(rows) + "</div>"

    num = lambda v: ro_amount(float(v))
    lines = "".join(
        f"<tr><td>{i}</td><td class=l>{x['description']}</td><td>{x['unit']}</td>"
        f"<td>{num(x['quantity'])}</td><td>{num(x['unit_price'])}</td><td>{num(x['line_total'])}</td>"
        f"<td>{float(x['vat_rate']):.0f}%</td></tr>" for i, x in enumerate(f["lines"], 1))
    tot, cur = f["totals"], f["currency"]
    vat = "".join(f"<tr><td>TVA {float(v['rate']):.0f}% (baza {num(v['taxable_amount'])})</td>"
                  f"<td>{num(v['vat_amount'])} {cur}</td></tr>" for v in f["vat_breakdown"])
    return f"""<html><body style="margin:0;background:#fff;font:15px Arial;color:#111;width:1240px">
<style>.party{{margin-top:18px;line-height:1.5}} table{{border-collapse:collapse;margin-top:22px;width:100%}}
td,th{{border:1px solid #333;padding:6px 8px;text-align:right}} .l{{text-align:left}} .tot td{{border:0;padding:3px 0}}</style>
<div style="padding:70px 80px">
<h1 style="text-align:center;font-size:30px;margin:0 0 20px">FACTURA</h1>
<div>Nr. factura: {f['invoice_number']}<br>Data emiterii: {ro_date(f['issue_date'])}<br>
Data scadentei: {ro_date(f['due_date'])}<br>Moneda: {cur}</div>
{party('FURNIZOR', f['seller'])}{party('CLIENT', f['buyer'])}
<table><tr><th>Nr</th><th>Denumire</th><th>U.M.</th><th>Cant.</th><th>Pret unitar</th><th>Valoare</th><th>TVA %</th></tr>{lines}</table>
<table class=tot style="width:520px;margin-left:auto">
<tr><td>Total fara TVA</td><td>{num(tot['total_without_vat'])} {cur}</td></tr>{vat}
<tr><td>Total TVA</td><td>{num(tot['total_vat'])} {cur}</td></tr>
<tr><td>Total cu TVA</td><td>{num(tot['total_with_vat'])} {cur}</td></tr>
<tr><td><b>TOTAL DE PLATA</b></td><td><b>{num(tot['amount_due'])} {cur}</b></td></tr></table>
<p style="font-size:11px;margin-top:40px">Document generat sintetic pentru testare. Date fictive.</p>
</div></body></html>"""


def degrade(png: bytes, seed: int) -> Image.Image:
    rnd = random.Random(seed)
    img = Image.open(io.BytesIO(png)).convert("L")
    img = img.rotate(rnd.uniform(-1.2, 1.2), resample=Image.BICUBIC, expand=True, fillcolor=245)
    img = img.filter(ImageFilter.GaussianBlur(0.7))
    px = img.load()
    for _ in range(img.width * img.height // 60):  # scanner speckle
        x, y = rnd.randrange(img.width), rnd.randrange(img.height)
        px[x, y] = max(0, min(255, px[x, y] + rnd.randint(-70, 70)))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=62)
    return Image.open(io.BytesIO(buf.getvalue()))


def to_pdf(img: Image.Image) -> bytes:
    pdf = FPDF(format="A4")
    pdf.add_page()
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=62)
    pdf.image(buf, x=0, y=0, w=210)
    return bytes(pdf.output())


def main() -> None:
    ids = sys.argv[1:] or DEFAULT_IDS
    entries = {e["id"]: e for e in json.loads((ROOT / "pdf" / "manifest.json").read_text())["invoices"]}
    OUT.mkdir(exist_ok=True)
    made = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1240, "height": 1754})
        for sid in ids:
            e = entries[sid]
            page.set_content(page_html(e["fields"]))
            img = degrade(page.screenshot(full_page=True), seed=zlib.crc32(sid.encode()))
            (OUT / f"{sid}-scan.pdf").write_bytes(to_pdf(img))
            made.append({"id": sid, "file": f"scans/{sid}-scan.pdf",
                         "designed_valid": e["designed_valid"], "mutations": e["mutations"],
                         "fields": e["fields"]})
            print("made", sid)
        browser.close()
    manifest = {"count": len(made), "invoices": made,
                "note": "Image-only PDFs (no text layer); fields = what the page prints."}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8",
                                       newline="\n")


if __name__ == "__main__":
    main()
