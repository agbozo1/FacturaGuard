import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from facturaguard.api import app as app_module
from facturaguard.llm.client import LLMResult

DATA = Path(__file__).resolve().parents[1] / "data" / "synthetic"
MANIFEST = json.loads((DATA / "manifest.json").read_text())["invoices"]
PDFS = json.loads((DATA / "pdf" / "manifest.json").read_text())["invoices"]
LMT = "/ubl:Invoice/cac:LegalMonetaryTotal"


def xml_for(mutations):
    for e in MANIFEST:
        if (mutations is None and e["designed_valid"]) or e["mutations"] == mutations:
            return (DATA / e["file"]).read_bytes()
    raise LookupError(mutations)


class RoutingLLM:
    """Fake model that answers by purpose (explain / repair / extract / chat)."""

    def __init__(self, pdf_fields=None):
        self.pdf_fields = pdf_fields
        self.seen = []

    def model_for(self, role):
        return f"fake/{role}"

    def chat(self, role, messages, **kw):
        system = messages[0]["content"]
        user = messages[-1]["content"]
        self.seen.append(system[:40])
        if "extract fields" in system:
            reply = self.pdf_fields
        elif "explain Romanian e-Factura" in system:
            errs = json.loads(user)["errors"]
            reply = {"explanations": [{"rule_id": e["rule_id"], "title": "Plain title",
                                       "what_is_wrong": "w", "why_it_matters": "y",
                                       "how_to_fix": "h", "fields": [],
                                       "needs_business_input": False} for e in errs]}
        elif "repair Romanian e-Factura" in system:
            p = json.loads(user)
            if "BR-02" in {e["rule_id"] for e in p["errors"]}:
                given = (p.get("facts_provided_by_business") or {}).get("BT-1")
                reply = ({"ops": [{"op": "insert_after", "xpath": "/ubl:Invoice/cbc:CustomizationID",
                                   "xml": f"<cbc:ID>{given}</cbc:ID>"}], "needs_input": []}
                         if given else
                         {"ops": [], "needs_input": [{"rule_id": "BR-02", "field": "BT-1",
                                                      "question": "Invoice number?"}]})
            else:
                due = p["computed_facts"]["expected_amount_due_BT115"]
                reply = {"ops": [{"op": "set_text", "xpath": f"{LMT}/cbc:PayableAmount",
                                  "value": due}], "needs_input": [], "summary": "Fixed total."}
        else:
            return LLMResult("Ask your accountant about BR-CO-16.", "fake/chat", None, 0.1, 5, 5)
        return LLMResult(json.dumps(reply), f"fake/{role}", None, 0.1, 5, 5)


@pytest.fixture
def client():
    app_module.app.state.llm = None
    app_module.app.state.sessions = app_module.SessionStore()
    app_module.app.state.ai_limit = app_module._RateLimit()
    yield TestClient(app_module.app)
    app_module.app.state.llm = None


def upload(client, data: bytes, name="inv.xml", lang="en"):
    r = client.post("/api/check", files={"file": (name, data)}, data={"lang": lang})
    assert r.status_code == 200, r.text
    return r.json()


def test_ui_and_health(client, monkeypatch):
    monkeypatch.setattr(app_module, "get_llm", lambda: None)
    assert "FacturaGuard" in client.get("/").text
    assert client.get("/api/health").json()["ai"] is False
    samples = client.get("/api/samples").json()
    assert {s["kind"] for s in samples} == {"xml", "pdf"}
    assert client.get(samples[0]["url"]).status_code == 200


def test_check_valid_and_invalid_without_ai(client, monkeypatch):
    monkeypatch.setattr(app_module, "get_llm", lambda: None)
    assert upload(client, xml_for(None))["validation"]["valid"] is True
    r = upload(client, xml_for(["bad_payable"]), lang="ro")
    assert r["validation"]["valid"] is False
    ex = r["explain"]["explanations"]
    assert ex[0]["rule_id"] == "BR-CO-16" and ex[0]["source"] == "rule_text"
    # AI endpoints say clearly that AI is unavailable.
    assert client.post("/api/explain", json={"session_id": r["session_id"]}).status_code == 503
    pdf = (DATA / PDFS[0]["file"]).read_bytes()
    assert client.post("/api/check", files={"file": ("a.pdf", pdf)}).status_code == 503


def test_rejects_doctype_and_oversize(client):
    evil = b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><x>&e;</x>'
    r = upload(client, evil)
    assert r["validation"]["valid"] is False
    assert "DOCTYPE" in r["validation"]["issues"][0]["message"]
    big = b"<a>" + b"x" * (5 * 1024 * 1024) + b"</a>"
    assert client.post("/api/check", files={"file": ("big.xml", big)}).status_code == 413


def test_explain_repair_summary_download_submit(client):
    app_module.app.state.llm = RoutingLLM()
    r = upload(client, xml_for(["bad_payable"]))
    sid = r["session_id"]
    ex = client.post("/api/explain", json={"session_id": sid}).json()
    assert ex["explanations"][0]["source"] == "model"

    rep = client.post("/api/repair", json={"session_id": sid}).json()
    assert rep["status"] == "fixed" and rep["final"]["valid"] and "PayableAmount" in rep["diff"]

    xml = client.get(f"/api/download/{sid}?which=corrected")
    assert xml.status_code == 200 and b"PayableAmount" in xml.content

    md = client.get(f"/api/summary/{sid}?lang=ro").text
    assert "BR-CO-16" in md and "Corectură propusă" in md and "```diff" in md

    sub = client.post("/api/submit", json={"session_id": sid}).json()
    assert sub["status"] == "ok" and sub["mock"] is True
    original = client.post("/api/submit", json={"session_id": sid, "which": "original"}).json()
    assert original["status"] == "nok"


def test_repair_asks_then_uses_the_answer(client):
    app_module.app.state.llm = RoutingLLM()
    sid = upload(client, xml_for(["missing_invoice_number"]))["session_id"]
    first = client.post("/api/repair", json={"session_id": sid}).json()
    assert first["status"] == "needs_input" and first["needs_input"][0]["field"] == "BT-1"
    second = client.post("/api/repair", json={"session_id": sid,
                                              "answers": {"BT-1": "FG-2026-0059"}}).json()
    assert second["status"] == "fixed" and "FG-2026-0059" in second["corrected_xml"]


def test_pdf_flow_and_chat(client):
    entry = next(e for e in PDFS if e["mutations"] == ["bad_payable"])
    app_module.app.state.llm = RoutingLLM(pdf_fields=entry["fields"])
    r = upload(client, (DATA / entry["file"]).read_bytes(), name="factura.pdf")
    assert r["source"] == "pdf" and r["pdf"]["ungrounded"] == []
    assert "BR-CO-16" in {i["rule_id"] for i in r["validation"]["issues"]}
    chat = client.post("/api/chat", json={"session_id": r["session_id"],
                                          "message": "Why is this rejected?"}).json()
    assert "BR-CO-16" in chat["answer"]


def test_search_features_off_without_tavily_key(client, monkeypatch):
    monkeypatch.setattr(app_module, "get_search", lambda: None)
    assert client.get("/api/health").json()["search"] is False
    assert client.get("/api/rules/updates").status_code == 503
    app_module.app.state.llm = RoutingLLM()
    sid = upload(client, xml_for(["bad_payable"]))["session_id"]
    chat = client.post("/api/chat", json={"session_id": sid, "message": "Deadline?"}).json()
    assert chat["answer"] and chat["sources"] == []


def test_chat_marks_which_sources_the_answer_cites(client, monkeypatch):
    from facturaguard.search.tavily import Source

    class FakeSearch:
        def search(self, q, **kw):
            return [Source("Used", "https://www.anaf.ro/a", "x", None, 1.0),
                    Source("Unused", "https://www.anaf.ro/b", "y", None, 0.5)], 0.1

    class CitingLLM(RoutingLLM):
        def chat(self, role, messages, **kw):
            return LLMResult("The deadline is 5 working days [1].", "fake", None, 0.1, 5, 5)

    monkeypatch.setattr(app_module, "get_search", lambda: FakeSearch())
    app_module.app.state.llm = CitingLLM()
    sid = upload(client, xml_for(["bad_payable"]))["session_id"]
    r = client.post("/api/chat", json={"session_id": sid, "message": "Deadline?"}).json()
    assert [(s["n"], s["cited"]) for s in r["sources"]] == [(1, True), (2, False)]
    assert r["uncited"] == []


def test_unknown_session_and_rate_limit(client):
    assert client.post("/api/submit", json={"session_id": "nope"}).status_code == 404
    app_module.app.state.llm = RoutingLLM()
    app_module.app.state.ai_limit = app_module._RateLimit(limit=2)
    sid = upload(client, xml_for(["bad_payable"]))["session_id"]
    codes = [client.post("/api/explain", json={"session_id": sid}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
