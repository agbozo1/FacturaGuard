import json
from pathlib import Path

from lxml import etree

from facturaguard.explain import explain
from facturaguard.llm.client import LLMResult
from facturaguard.llm.jsonparse import parse_json_object
from facturaguard.repair.engine import repair
from facturaguard.repair.facts import compute_facts
from facturaguard.repair.patch import apply_ops
from facturaguard.rules.index import rule_text
from facturaguard.validation.validate import validate_xml

DATA = Path(__file__).resolve().parents[1] / "data" / "synthetic"
MANIFEST = json.loads((DATA / "manifest.json").read_text())["invoices"]
LMT = "/ubl:Invoice/cac:LegalMonetaryTotal"


def sample(mutation: str | None) -> bytes:
    for e in MANIFEST:
        if (mutation is None and e["designed_valid"]) or e["mutations"] == [mutation]:
            return (DATA / e["file"]).read_bytes()
    raise LookupError(mutation)


class FakeLLM:
    """Stands in for LLMClient. `respond` maps the request payload to a JSON reply."""

    def __init__(self, respond):
        self.respond = respond
        self.requests = []

    def model_for(self, role):
        return f"fake/{role}"

    def chat(self, role, messages, **kw):
        payload = json.loads(messages[-1]["content"])
        self.requests.append(payload)
        return LLMResult(json.dumps(self.respond(payload)), f"fake/{role}", None, 0.01, 10, 10)


# --- helpers ---------------------------------------------------------------------------

def test_parse_json_object_tolerates_fences_and_prose():
    assert parse_json_object('Sure!\n```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_object('note {not json} then {"b": [1, 2]} end') == {"b": [1, 2]}


def test_rule_index_has_official_texts():
    assert "BT-115" in rule_text("BR-CO-16").business_terms
    ro = rule_text("BR-RO-110")
    assert ro.ro and "RO-B" in ro.ro and "Bucharest" in ro.en


def test_facts_match_a_valid_invoice_and_expose_a_wrong_payable():
    root = etree.fromstring(sample(None))
    facts = compute_facts(root)
    ns = {"cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
          "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"}
    assert facts["expected_amount_due_BT115"] == root.xpath(
        "string(cac:LegalMonetaryTotal/cbc:PayableAmount)", namespaces=ns)
    bad = etree.fromstring(sample("bad_payable"))
    assert compute_facts(bad)["expected_amount_due_BT115"] != bad.xpath(
        "string(cac:LegalMonetaryTotal/cbc:PayableAmount)", namespaces=ns)


def test_patch_rejects_ambiguous_and_invalid_ops_but_applies_good_ones():
    out = apply_ops(sample(None), [
        {"op": "set_text", "xpath": "//cbc:ID", "value": "x"},           # matches many
        {"op": "set_text", "xpath": "/ubl:Invoice/cbc:Nope", "value": "x"},  # matches none
        {"op": "explode", "xpath": "/ubl:Invoice"},                        # unknown op
        {"op": "set_text", "xpath": f"{LMT}/cbc:PayableAmount", "value": "1.00"},
    ])
    assert len(out.applied) == 1 and len(out.rejected) == 3
    assert b">1.00</cbc:PayableAmount>" in out.xml


def test_patch_inserts_fragment_at_position():
    xml = sample("missing_invoice_number")
    out = apply_ops(xml, [{"op": "insert_after", "xpath": "/ubl:Invoice/cbc:CustomizationID",
                           "xml": "<cbc:ID>FG-2026-0001</cbc:ID>"}])
    assert not out.rejected
    res = validate_xml(out.xml)
    assert "XSD" not in {i.rule_id for i in res.issues}


# --- repair ----------------------------------------------------------------------------

def test_repair_fixes_totals_using_computed_facts():
    def respond(p):
        due = p["computed_facts"]["expected_amount_due_BT115"]
        return {"ops": [{"op": "set_text", "xpath": f"{LMT}/cbc:PayableAmount", "value": due}],
                "needs_input": [], "summary": "Set the amount due to the computed value."}

    r = repair(sample("bad_payable"), FakeLLM(respond))
    assert r.status == "fixed" and r.final.valid
    assert "PayableAmount" in r.diff and len(r.ops_applied) == 1


def test_repair_discards_edits_that_make_things_worse():
    llm = FakeLLM(lambda p: {"ops": [{"op": "delete", "xpath": "/ubl:Invoice/cbc:ID"}],
                             "needs_input": [], "summary": ""})
    r = repair(sample("bad_payable"), llm, max_rounds=2)
    assert r.status == "not_fixed" and r.corrected_xml is None and not r.ops_applied
    assert "NOT applied" in llm.requests[1]["feedback_from_previous_attempt"]


def test_repair_asks_for_facts_instead_of_inventing_them():
    llm = FakeLLM(lambda p: {"ops": [], "summary": "",
                             "needs_input": [{"rule_id": "BR-02", "field": "BT-1",
                                              "question": "What is the invoice number?"}]})
    r = repair(sample("missing_invoice_number"), llm)
    assert r.status == "needs_input" and r.needs_input[0]["field"] == "BT-1"


def test_repair_refuses_malformed_xml_and_skips_valid():
    assert repair(sample("malformed_xml"), FakeLLM(lambda p: {})).status == "unsupported"
    assert repair(sample(None), FakeLLM(lambda p: {})).status == "already_valid"


def test_repair_survives_model_errors():
    def boom(p):
        raise RuntimeError("API down")

    r = repair(sample("bad_payable"), FakeLLM(boom))
    assert r.status == "not_fixed" and r.calls and not r.calls[-1].ok


# --- explain ---------------------------------------------------------------------------

def test_explain_without_model_uses_official_rule_text():
    xml = sample("bad_ro_subdivision")
    res = explain(validate_xml(xml), xml, None, lang="ro")
    e = res.explanations[0]
    assert e.source == "rule_text" and e.rule_id == "BR-RO-110" and "RO-B" in e.official_rule


def test_explain_with_model_keeps_official_text_and_falls_back_for_skipped_rules():
    xml = sample("bad_currency_code")  # fires BR-CL-03, BR-CL-04, BR-RO-030
    llm = FakeLLM(lambda p: {"explanations": [
        {"rule_id": "BR-CL-04", "title": "Currency code is not valid",
         "what_is_wrong": "LEI is not a currency code.", "why_it_matters": "ANAF rejects it.",
         "how_to_fix": "Use RON.", "fields": ["BT-5"], "needs_business_input": False}]})
    res = explain(validate_xml(xml), xml, llm, lang="en")
    by = {e.rule_id: e for e in res.explanations}
    assert by["BR-CL-04"].source == "model" and "ISO" in by["BR-CL-04"].official_rule
    assert by["BR-CL-03"].source == "rule_text"
    assert len(res.explanations) == len({e.rule_id for e in res.explanations})
