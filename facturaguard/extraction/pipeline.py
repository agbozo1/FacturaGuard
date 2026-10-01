"""PDF -> text -> Nemotron fields -> grounding check -> UBL (code) -> validator."""

from dataclasses import dataclass, field

from facturaguard.extraction.build import BuildResult, build_from_fields
from facturaguard.extraction.extract import extract_fields
from facturaguard.extraction.grounding import check_grounding
from facturaguard.extraction.pdf_text import PdfTextError, extract_text
from facturaguard.llm.ask import CallRecord
from facturaguard.llm.client import LLMClient
from facturaguard.validation.models import ValidationResult
from facturaguard.validation.validate import validate_xml


@dataclass
class PdfResult:
    ok: bool
    error: str = ""
    text: str = ""
    fields: dict = field(default_factory=dict)
    ungrounded: list[dict] = field(default_factory=list)
    build: BuildResult | None = None
    validation: ValidationResult | None = None
    calls: list[CallRecord] = field(default_factory=list)

    @property
    def xml(self) -> bytes | None:
        return self.build.xml.encode("utf-8") if self.build else None

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "error": self.error,
            "fields": self.fields,
            "ungrounded": self.ungrounded,
            "build_warnings": self.build.warnings if self.build else [],
            "xml": self.build.xml if self.build else None,
            "validation": self.validation.to_dict() if self.validation else None,
            "calls": [c.to_dict() for c in self.calls],
        }


def pdf_to_invoice(data: bytes, llm: LLMClient, role: str = "fast") -> PdfResult:
    out = PdfResult(ok=False)
    try:
        out.text = extract_text(data)
    except PdfTextError as e:
        out.error = str(e)
        return out
    try:
        out.fields = extract_fields(out.text, llm, out.calls, role=role)
    except Exception as e:  # noqa: BLE001  report model/API failures to the user
        out.error = f"Field extraction failed: {type(e).__name__}: {e}"[:400]
        return out
    out.ungrounded = check_grounding(out.fields, out.text)
    out.build = build_from_fields(out.fields)
    out.validation = validate_xml(out.xml)
    out.ok = True
    return out
