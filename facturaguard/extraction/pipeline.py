"""PDF or scan -> text -> Nemotron fields -> grounding check -> UBL (code) -> validator.

Text PDFs are read directly. Scanned PDFs and photos (JPG, PNG) are first transcribed by the
vision model (see scan.py), when one is configured; the rest of the pipeline is identical.
"""

from dataclasses import dataclass, field

from facturaguard.extraction.build import _COUNTY_IN_TEXT, BuildResult, build_from_fields
from facturaguard.extraction.extract import extract_fields
from facturaguard.extraction.grounding import check_grounding
from facturaguard.extraction.pdf_text import NoTextLayer, PdfTextError, extract_text
from facturaguard.extraction.scan import (
    ScanError,
    is_image,
    page_images,
    preview_data_url,
    scan_suspects,
    transcribe,
)
from facturaguard.llm.ask import CallRecord
from facturaguard.llm.client import LLMClient
from facturaguard.validation.models import ValidationResult
from facturaguard.validation.validate import validate_xml

SCAN_NOTE = ("Read from a scanned image by an AI vision model. Please check every value against "
             "the original before relying on it. If a total does not add up, compare it with the "
             "scan first: it may be a reading error rather than an error on the invoice.")


@dataclass
class PdfResult:
    ok: bool
    error: str = ""
    source: str = "pdf"            # "pdf" (text layer) or "scan" (image read by the vision model)
    text: str = ""
    fields: dict = field(default_factory=dict)
    ungrounded: list[dict] = field(default_factory=list)
    build: BuildResult | None = None
    validation: ValidationResult | None = None
    calls: list[CallRecord] = field(default_factory=list)
    preview: str | None = None     # data URL of the first scanned page, for the UI

    @property
    def xml(self) -> bytes | None:
        return self.build.xml.encode("utf-8") if self.build else None

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "error": self.error,
            "source": self.source,
            "fields": self.fields,
            "ungrounded": self.ungrounded,
            "build_warnings": self.build.warnings if self.build else [],
            "xml": self.build.xml if self.build else None,
            "validation": self.validation.to_dict() if self.validation else None,
            "calls": [c.to_dict() for c in self.calls],
        }


def recover_counties(fields: dict, text: str) -> None:
    """The model sometimes drops a printed county. If a party has none, take "Jud. X" from the
    source line that holds its street: deterministic, and on the page by construction."""
    lines = text.splitlines()
    for role in ("seller", "buyer"):
        p = fields.get(role)
        street = (p or {}).get("street") or ""
        if not p or p.get("county") or len(street) < 4:
            continue
        for line in lines:
            if street in line:
                m = _COUNTY_IN_TEXT.search(line[line.index(street):])
                if m:
                    p["county"] = m.group(1).strip()
                break


def vision_available(llm: LLMClient) -> bool:
    return bool(llm.model_for("vision"))


def _read_scan(data: bytes, llm: LLMClient, out: PdfResult) -> bool:
    out.source = "scan"
    if not vision_available(llm):
        out.error = ("This looks like a scan. Scan reading is not configured on this server "
                     "(MODEL_VISION). Upload the PDF exported from your invoicing software.")
        return False
    try:
        pages = page_images(data)
        out.preview = preview_data_url(pages[0])
        out.text = transcribe(pages, llm, out.calls)
    except ScanError as e:
        out.error = str(e)
        return False
    except Exception as e:  # noqa: BLE001  report model/API failures to the user
        out.error = f"Reading the scan failed: {type(e).__name__}: {e}"[:400]
        return False
    return True


def pdf_to_invoice(data: bytes, llm: LLMClient, role: str = "fast") -> PdfResult:
    """Accepts a text PDF, a scanned PDF, or a JPG/PNG photo of an invoice."""
    out = PdfResult(ok=False)
    if is_image(data):
        if not _read_scan(data, llm, out):
            return out
    else:
        try:
            out.text = extract_text(data)
        except NoTextLayer:
            if not _read_scan(data, llm, out):
                return out
        except PdfTextError as e:
            out.error = str(e)
            return out
    try:
        out.fields = extract_fields(out.text, llm, out.calls, role=role)
    except Exception as e:  # noqa: BLE001  report model/API failures to the user
        out.error = f"Field extraction failed: {type(e).__name__}: {e}"[:400]
        return out
    recover_counties(out.fields, out.text)
    out.ungrounded = check_grounding(out.fields, out.text)
    if out.source == "scan":
        flagged = {u["field"] for u in out.ungrounded}
        out.ungrounded += [s for s in scan_suspects(out.fields) if s["field"] not in flagged]
    out.build = build_from_fields(out.fields)
    if out.source == "scan":
        out.build.warnings.insert(0, SCAN_NOTE)
    out.validation = validate_xml(out.xml)
    out.ok = True
    return out
