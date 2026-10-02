import io
import json
from pathlib import Path

from fastapi.testclient import TestClient
from fpdf import FPDF
from PIL import Image

from facturaguard.api import app as app_module
from facturaguard.extraction.pdf_text import extract_text
from facturaguard.extraction.pipeline import SCAN_NOTE, pdf_to_invoice, recover_counties
from facturaguard.extraction.scan import (
    MAX_SIDE,
    ScanError,
    _strip_html,
    iban_is_valid,
    is_image,
    page_images,
    scan_suspects,
)
from facturaguard.llm.client import LLMResult

DATA = Path(__file__).resolve().parents[1] / "data" / "synthetic"
SCANS = json.loads((DATA / "scans" / "manifest.json").read_text())["invoices"]


def scan_entry(mutations):
    return next(e for e in SCANS if e["mutations"] == mutations)


class FakeVisionLLM:
    """Vision role returns a transcription (here: the text of the matching text PDF, i.e. what
    the scan prints); the fast role returns the printed fields."""

    def __init__(self, transcription: str, fields: dict, vision_model: str = "fake/vision"):
        self.transcription, self.fields, self.vision_model = transcription, fields, vision_model
        self.seen_images = 0

    def model_for(self, role):
        return self.vision_model if role == "vision" else f"fake/{role}"

    def chat(self, role, messages, **kw):
        if role == "vision":
            parts = messages[0]["content"]
            assert parts[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
            self.seen_images += 1
            return LLMResult(self.transcription, "fake/vision", None, 0.1, 100, 300)
        return LLMResult(json.dumps(self.fields), "fake/fast", None, 0.1, 100, 300)


def fake_for(entry) -> FakeVisionLLM:
    text = extract_text((DATA / "pdf" / f"{entry['id']}.pdf").read_bytes())
    return FakeVisionLLM(text, entry["fields"])


def test_scanned_pdf_yields_one_normalised_page_image():
    data = (DATA / scan_entry(["bad_payable"])["file"]).read_bytes()
    pages = page_images(data)
    assert len(pages) == 1
    img = Image.open(io.BytesIO(pages[0]))
    assert img.format == "JPEG" and max(img.size) <= MAX_SIDE


def test_photo_uploads_are_recognised_and_downscaled():
    big = Image.new("RGB", (3000, 4000), "white")
    buf = io.BytesIO()
    big.save(buf, "PNG")
    assert is_image(buf.getvalue()) and not is_image(b"%PDF-1.7")
    assert max(Image.open(io.BytesIO(page_images(buf.getvalue())[0])).size) == MAX_SIDE


def test_html_table_transcriptions_become_plain_lines():
    html = "<table><tr><td>1</td><td>Servicii</td><td>1.278,28</td></tr></table>"
    assert _strip_html(html).strip() == "1 | Servicii | 1.278,28"


def test_scan_pipeline_reads_builds_and_validates():
    entry = scan_entry(["bad_payable"])
    llm = fake_for(entry)
    r = pdf_to_invoice((DATA / entry["file"]).read_bytes(), llm)
    assert r.ok and r.source == "scan" and llm.seen_images == 1
    assert r.preview.startswith("data:image/jpeg;base64,")
    assert r.build.warnings[0] == SCAN_NOTE
    assert r.ungrounded == []
    assert "BR-CO-16" in {i.rule_id for i in r.validation.issues}
    assert [c.purpose for c in r.calls] == ["transcribe", "extract"]


def test_scan_reading_off_gives_a_clear_message():
    entry = scan_entry([])
    llm = fake_for(entry)
    llm.vision_model = ""
    r = pdf_to_invoice((DATA / entry["file"]).read_bytes(), llm)
    assert not r.ok and "scan" in r.error.lower() and "MODEL_VISION" in r.error


def test_pdf_without_text_or_images_is_reported():
    pdf = FPDF()
    pdf.add_page()
    pdf.rect(10, 10, 50, 50)
    try:
        page_images(bytes(pdf.output()))
    except ScanError as e:
        assert "JPG or PNG" in str(e)
    else:
        raise AssertionError("expected ScanError")


def test_api_accepts_scans_and_returns_a_preview():
    entry = scan_entry(["bad_payable"])
    app_module.app.state.llm = fake_for(entry)
    app_module.app.state.sessions = app_module.SessionStore()
    app_module.app.state.ai_limit = app_module._RateLimit()
    try:
        client = TestClient(app_module.app)
        r = client.post("/api/check", files={"file": ("factura-scan.pdf",
                                                      (DATA / entry["file"]).read_bytes())})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["source"] == "scan" and body["pdf"]["scan"] is True
        assert body["pdf"]["preview"].startswith("data:image/jpeg")
        assert body["validation"]["valid"] is False
        md = client.get(f"/api/summary/{body['session_id']}").text
        assert "scanned image" in md
    finally:
        app_module.app.state.llm = None


def test_dropped_county_is_recovered_from_the_party_address_line():
    text = "CLIENT\nApex Test 75 SRL\nAdresa: Str. Model 59, Brasov, Jud. Brasov, 500001, Romania\n"
    fields = {"seller": {"street": "Str. Lipsa 1", "county": None},
              "buyer": {"street": "Str. Model 59", "city": "Brasov", "county": None}}
    recover_counties(fields, text)
    assert fields["buyer"]["county"] == "Brasov"
    assert fields["seller"]["county"] is None  # street not on the page: nothing invented


def test_self_checking_values_flag_likely_misreads():
    # Real misreads from the scan eval (docs/eval/eval_scans.json).
    assert iban_is_valid("RO70TEST7825067066805211")
    assert not iban_is_valid("RO70TEST782506706680521")      # digit dropped
    assert not iban_is_valid("RO26TEST1797589494926940")     # digits swapped
    fields = {"seller": {"iban": "RO70TEST782506706680521", "vat_id": "RO349537640",
                         "postal_code": "400001", "country": "Romania"},
              "buyer": {"vat_id": "RO59782610", "postal_code": "40001", "country": None},
              }
    got = {(s["field"], s["reason"].split()[0]) for s in scan_suspects(fields)}
    assert got == {("seller.iban", "IBAN"), ("buyer.vat_id", "CUI"),
                   ("buyer.postal_code", "Romanian")}
    foreign = {"buyer": {"vat_id": "DE123456789", "postal_code": "10115", "country": "DE"}}
    assert scan_suspects(foreign) == []
