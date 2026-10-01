import copy
import json
from pathlib import Path

import pytest
from fpdf import FPDF

from facturaguard.extraction.build import build_from_fields
from facturaguard.extraction.grounding import check_grounding
from facturaguard.extraction.pdf_text import PdfTextError, extract_text
from facturaguard.extraction.pipeline import pdf_to_invoice
from facturaguard.llm.client import LLMResult
from facturaguard.ubl.codes import bucharest_sector, county_code, unit_code
from facturaguard.validation.validate import validate_xml

DATA = Path(__file__).resolve().parents[1] / "data" / "synthetic"
PDFS = json.loads((DATA / "pdf" / "manifest.json").read_text())["invoices"]
XML_MANIFEST = {e["id"]: e for e in json.loads((DATA / "manifest.json").read_text())["invoices"]}


class TruthLLM:
    """A perfect extractor: returns the ground-truth printed fields."""

    def __init__(self, fields):
        self.fields = fields

    def model_for(self, role):
        return "truth"

    def chat(self, role, messages, **kw):
        return LLMResult(json.dumps(self.fields), "truth", None, 0.0, 0, 0)


def _first(pred):
    return next(e for e in PDFS if pred(e))


def test_codes():
    assert county_code("Jud. Cluj") == "RO-CJ" == county_code("RO-CJ")
    assert county_code("Bistrița-Năsăud") == "RO-BN"
    assert county_code("Atlantis") is None
    assert bucharest_sector("Bucuresti Sector 3") == "SECTOR3"
    assert unit_code("buc.") == "C62" and unit_code("ora") == "HUR" and unit_code("HUR") == "HUR"


@pytest.mark.parametrize("entry", PDFS, ids=[e["id"] for e in PDFS])
def test_truth_fields_are_grounded_and_rebuild_to_the_same_verdict(entry):
    text = extract_text((DATA / entry["file"]).read_bytes())
    assert check_grounding(entry["fields"], text) == []
    built = build_from_fields(entry["fields"])
    assert built.warnings == []
    result = validate_xml(built.xml.encode())
    assert result.valid == entry["designed_valid"], sorted({i.rule_id for i in result.issues})
    # A PDF prints one "Total fara TVA", so a wrong BT-109 (bad_tax_exclusive) is indistinguishable
    # on paper from a wrong BT-106 and rebuilds as the latter. Every other PDF rebuilds exactly.
    if entry["mutations"] != ["bad_tax_exclusive"]:
        original = (DATA / XML_MANIFEST[entry["id"]]["file"]).read_text(encoding="utf-8")
        assert built.xml == original


def test_printed_arithmetic_mistakes_survive_into_the_ubl():
    e = _first(lambda e: e["mutations"] == ["bad_payable"])
    rules = {i.rule_id for i in validate_xml(build_from_fields(e["fields"]).xml.encode()).issues}
    assert "BR-CO-16" in rules


def test_grounding_flags_values_not_in_the_pdf():
    e = _first(lambda e: e["designed_valid"])
    text = extract_text((DATA / e["file"]).read_bytes())
    fields = copy.deepcopy(e["fields"])
    fields["seller"]["iban"] = "RO49AAAA1B31007593840000"
    fields["totals"]["amount_due"] = "999999.99"
    flagged = {m["field"] for m in check_grounding(fields, text)}
    assert flagged == {"seller.iban", "totals.amount_due"}


def test_missing_fields_are_left_for_the_validator_not_invented():
    e = _first(lambda e: e["designed_valid"])
    fields = copy.deepcopy(e["fields"])
    fields["invoice_number"] = None
    fields["buyer"]["name"] = None
    rules = {i.rule_id for i in validate_xml(build_from_fields(fields).xml.encode()).issues}
    assert {"BR-02", "BR-07"} <= rules


def test_scanned_pdf_is_rejected_with_a_clear_message():
    pdf = FPDF()
    pdf.add_page()
    pdf.rect(10, 10, 100, 100)  # drawing, no text layer
    with pytest.raises(PdfTextError, match="scan"):
        extract_text(bytes(pdf.output()))


def test_pipeline_end_to_end_with_a_perfect_extractor():
    e = _first(lambda e: e["designed_valid"])
    r = pdf_to_invoice((DATA / e["file"]).read_bytes(), TruthLLM(e["fields"]))
    assert r.ok and r.ungrounded == [] and r.validation.valid
    assert r.calls and r.calls[0].purpose == "extract"


def test_pipeline_reports_model_failure():
    class Broken(TruthLLM):
        def chat(self, role, messages, **kw):
            raise RuntimeError("API down")

    e = _first(lambda e: e["designed_valid"])
    r = pdf_to_invoice((DATA / e["file"]).read_bytes(), Broken({}))
    assert not r.ok and "API down" in r.error
