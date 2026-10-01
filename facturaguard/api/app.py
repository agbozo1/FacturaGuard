"""FacturaGuard web API and static UI.

    uvicorn facturaguard.api.app:app --reload

Validation and official-rule explanations work without a model. PDF reading, AI explanations,
repair and chat need NEBIUS_API_KEY; without it those endpoints return 503.
"""

import json
import re
import threading
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from facturaguard.api.sessions import SessionStore
from facturaguard.chat import chat_reply
from facturaguard.config import get_settings
from facturaguard.explain import explain
from facturaguard.extraction.pipeline import pdf_to_invoice
from facturaguard.llm.client import LLMClient, LLMNotConfigured
from facturaguard.repair.engine import repair
from facturaguard.repair.patch import unified_diff
from facturaguard.search.rule_watch import RuleWatch
from facturaguard.search.tavily import SearchNotConfigured, TavilyClient
from facturaguard.submission.mock import MockAnafAdapter
from facturaguard.summary import accountant_summary
from facturaguard.validation.models import Issue, ValidationResult
from facturaguard.validation.validate import validate_xml
from facturaguard.xmlsafe import UnsafeXML, parse

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
DATA = ROOT / "data" / "synthetic"
MAX_UPLOAD = 5 * 1024 * 1024
Lang = Literal["en", "ro"]

app = FastAPI(title="FacturaGuard", version="0.1.0")
app.state.sessions = SessionStore()
app.state.submission = MockAnafAdapter()
app.state.llm = None  # created lazily; tests may set a fake
app.state.search = None  # Tavily client, created lazily; None when TAVILY_API_KEY is unset
app.state.rule_watch = RuleWatch()


# --- helpers -----------------------------------------------------------------------------

def get_llm() -> LLMClient | None:
    if app.state.llm is None:
        try:
            app.state.llm = LLMClient()
        except LLMNotConfigured:
            return None
    return app.state.llm


def get_search() -> TavilyClient | None:
    if app.state.search is None:
        try:
            app.state.search = TavilyClient()
        except SearchNotConfigured:
            return None
    return app.state.search


def require_llm() -> LLMClient:
    llm = get_llm()
    if llm is None:
        raise HTTPException(503, "AI features are not configured on this server "
                                 "(NEBIUS_API_KEY missing). Validation still works.")
    return llm


def get_session(sid: str) -> dict:
    s = app.state.sessions.get(sid)
    if s is None:
        raise HTTPException(404, "Session not found or expired. Please upload the invoice again.")
    return s


class _RateLimit:
    """Per-client cap on AI calls, so a public demo cannot burn the model budget."""

    def __init__(self, limit: int = 40, window: int = 600):
        self.limit, self.window = limit, window
        self.hits: dict[str, deque] = defaultdict(deque)
        self.lock = threading.Lock()

    def check(self, request: Request) -> None:
        key = request.client.host if request.client else "unknown"
        now = time.time()
        with self.lock:
            q = self.hits[key]
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.limit:
                raise HTTPException(429, "Too many AI requests. Please wait a few minutes.")
            q.append(now)


app.state.ai_limit = _RateLimit()


def _calls(calls) -> list[dict]:
    return [c.to_dict() for c in calls]


def _seller_cif(xml: bytes) -> str:
    try:
        root = parse(xml)
    except (UnsafeXML, ValueError):
        return ""
    return root.xpath(
        "normalize-space(*[local-name()='AccountingSupplierParty']/*[local-name()='Party']"
        "/*[local-name()='PartyTaxScheme']/*[local-name()='CompanyID'])")


# --- samples -----------------------------------------------------------------------------

SAMPLES = [
    ("valid", "xml", None, "Valid invoice", "Factură validă"),
    ("payable", "xml", ["bad_payable"], "Wrong amount due", "Total de plată greșit"),
    ("currency", "xml", ["bad_currency_code"], "Currency 'LEI' instead of RON",
     "Monedă 'LEI' în loc de RON"),
    ("county", "xml", ["bad_ro_subdivision"], "County not coded (RO-XX)",
     "Județ necodificat (RO-XX)"),
    ("number", "xml", ["missing_invoice_number"], "Missing invoice number",
     "Lipsește numărul facturii"),
    ("buyer", "xml", ["foreign_buyer_no_ro_id"], "EU buyer without Romanian ID",
     "Client UE fără cod românesc"),
    ("pdf-valid", "pdf", None, "PDF invoice (valid)", "Factură PDF (validă)"),
    ("pdf-payable", "pdf", ["bad_payable"], "PDF with wrong total", "PDF cu total greșit"),
]


def _sample_entry(kind: str, mutations):
    manifest = DATA / ("pdf/manifest.json" if kind == "pdf" else "manifest.json")
    for e in json.loads(manifest.read_text(encoding="utf-8"))["invoices"]:
        if (mutations is None and e["designed_valid"]) or e["mutations"] == mutations:
            return e
    return None


@app.get("/api/samples")
def samples() -> list[dict]:
    out = []
    for key, kind, muts, en, ro in SAMPLES:
        e = _sample_entry(kind, muts)
        if e:
            out.append({"key": key, "kind": kind, "label_en": en, "label_ro": ro,
                        "file_name": Path(e["file"]).name, "url": f"/api/samples/{key}"})
    return out


@app.get("/api/samples/{key}")
def sample_file(key: str):
    for k, kind, muts, *_ in SAMPLES:
        if k == key and (e := _sample_entry(kind, muts)):
            media = "application/pdf" if kind == "pdf" else "application/xml"
            return FileResponse(DATA / e["file"], media_type=media,
                                filename=Path(e["file"]).name)
    raise HTTPException(404, "Unknown sample")


# --- core flow ---------------------------------------------------------------------------

@app.get("/api/health")
def health() -> dict:
    s = get_settings()
    return {"ok": True, "ai": get_llm() is not None, "search": get_search() is not None,
            "rules": "CIUS-RO 1.0.9 / UBL 2.1",
            "models": {"fast": s.model_fast, "reasoning": s.model_reasoning}}


@app.get("/api/rules/updates")
def rule_updates(request: Request, refresh: bool = False):
    """Search official sources for a CIUS-RO version newer than ours (cached for 12 hours)."""
    search = get_search()
    if search is None:
        raise HTTPException(503, "Official-source search is not configured (TAVILY_API_KEY).")
    app.state.ai_limit.check(request)
    try:
        return app.state.rule_watch.check(search, force=refresh).to_dict()
    except Exception as e:  # report search outages without failing the page
        raise HTTPException(502, f"The search service did not answer: {type(e).__name__}") from e


@app.post("/api/check")
async def check(request: Request, file: Annotated[UploadFile, File()],
                lang: Annotated[Lang, Form()] = "en"):
    data = await file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "File too large (max 5 MB).")
    if not data:
        raise HTTPException(400, "Empty file.")
    name = Path(file.filename or "invoice").name[:120]
    session: dict = {"file_name": name, "lang": lang}
    calls = []
    if data.lstrip()[:5] == b"%PDF-":
        llm = require_llm()
        app.state.ai_limit.check(request)
        r = pdf_to_invoice(data, llm)
        calls = r.calls
        if not r.ok:
            raise HTTPException(422, r.error)
        session.update(source="pdf", pdf_fields=r.fields, ungrounded=r.ungrounded,
                       build_warnings=r.build.warnings, original_xml=r.xml)
        xml = r.xml
    else:
        session.update(source="xml", original_xml=data)
        xml = data
    result = validate_xml(xml)
    session["validation"] = result.to_dict()
    session["explain"] = explain(result, xml, None, lang=lang).to_dict()  # official texts now
    sid = app.state.sessions.create(**session)
    return {
        "session_id": sid,
        "file_name": name,
        "source": session["source"],
        "validation": session["validation"],
        "explain": session["explain"],
        "pdf": {"fields": session.get("pdf_fields"), "ungrounded": session.get("ungrounded"),
                "warnings": session.get("build_warnings")} if session["source"] == "pdf"
        else None,
        "calls": _calls(calls),
    }


class SessionLang(BaseModel):
    session_id: str
    lang: Lang = "en"


@app.post("/api/explain")
def explain_endpoint(body: SessionLang, request: Request):
    s = get_session(body.session_id)
    llm = require_llm()
    app.state.ai_limit.check(request)
    v = s["validation"]
    result = ValidationResult(kind=v["kind"], issues=[Issue(**i) for i in v["issues"]])
    ex = explain(result, s["original_xml"], llm, lang=body.lang)
    s["explain"] = ex.to_dict()
    return s["explain"]


class RepairBody(SessionLang):
    answers: dict[str, str] = Field(default_factory=dict)


@app.post("/api/repair")
def repair_endpoint(body: RepairBody, request: Request):
    s = get_session(body.session_id)
    llm = require_llm()
    app.state.ai_limit.check(request)
    answers = {k[:20]: v[:300] for k, v in body.answers.items() if v and v.strip()}
    s.setdefault("answers", {}).update(answers)
    start = s.get("corrected_xml") or s["original_xml"]
    r = repair(start, llm, lang=body.lang, user_facts=s["answers"] or None)
    best = r.corrected_xml or s.get("corrected_xml")
    if best:
        s["corrected_xml"] = best
    out = r.to_dict()
    out["diff"] = unified_diff(s["original_xml"], best) if best else ""
    out["corrected_xml"] = best.decode("utf-8") if best else None
    if best and r.corrected_xml is None:  # this round changed nothing; report current best
        out["final"] = validate_xml(best).to_dict()
    s["repair"] = out
    return out


class ChatBody(SessionLang):
    message: str = Field(min_length=1, max_length=2000)
    web: bool = True  # search official sources first, when TAVILY_API_KEY is configured


@app.post("/api/chat")
def chat_endpoint(body: ChatBody, request: Request):
    s = get_session(body.session_id)
    llm = require_llm()
    app.state.ai_limit.check(request)
    search = get_search() if body.web else None
    try:
        r = chat_reply(s, body.message, llm, lang=body.lang, search=search)
    except Exception as e:  # surface model errors as a friendly 502
        raise HTTPException(502, f"The AI model did not answer: {type(e).__name__}") from e
    cited = {int(n) for n in re.findall(r"\[(\d{1,2})\]", r.answer)}
    sources = [{**x.to_dict(), "n": i, "cited": i in cited} for i, x in enumerate(r.sources, 1)]
    return {"answer": r.answer, "call": r.call.to_dict(), "sources": sources,
            "search_s": r.search_s, "search_error": r.search_error, "uncited": r.uncited}


@app.get("/api/summary/{sid}")
def summary(sid: str, lang: Lang = "en", download: bool = False):
    md = accountant_summary(get_session(sid), lang=lang)
    headers = {"Content-Disposition": 'attachment; filename="facturaguard-summary.md"'} \
        if download else {}
    return PlainTextResponse(md, media_type="text/markdown; charset=utf-8", headers=headers)


@app.get("/api/download/{sid}")
def download(sid: str, which: Literal["original", "corrected"] = "corrected"):
    s = get_session(sid)
    xml = s.get("corrected_xml") if which == "corrected" else s["original_xml"]
    if not xml:
        raise HTTPException(404, "No corrected XML yet.")
    stem = Path(s["file_name"]).stem
    return Response(xml, media_type="application/xml", headers={
        "Content-Disposition": f'attachment; filename="{stem}-{which}.xml"'})


class SubmitBody(BaseModel):
    session_id: str
    which: Literal["original", "corrected"] = "corrected"


@app.post("/api/submit")
def submit(body: SubmitBody):
    s = get_session(body.session_id)
    xml = s.get("corrected_xml") if body.which == "corrected" else None
    xml = xml or s["original_xml"]
    result = app.state.submission.submit(xml, _seller_cif(xml))
    s["submission"] = result.to_dict()
    return s["submission"]


if WEB.exists():
    app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
