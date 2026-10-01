"""Follow-up chat about one checked invoice, grounded in that invoice's validation results."""

import json
import re
from dataclasses import dataclass, field

from facturaguard.llm.ask import CallRecord
from facturaguard.llm.client import LLMClient
from facturaguard.llm.prompts import LANGUAGES
from facturaguard.rules.index import rule_text
from facturaguard.rules.search import search_rules
from facturaguard.search.citations import flag_uncited
from facturaguard.search.tavily import Source, TavilyClient

CHAT_SYSTEM = """You are FacturaGuard's assistant. You answer questions about ONE Romanian \
e-Factura invoice that has been checked by a deterministic validator. The context below is \
the only source of truth.

Rules:
- Validity is decided only by the validator results in the context. Never claim an invoice is \
valid or invalid on your own judgement.
- Base answers on the validator results, the official rule texts and the proposed fix in the \
context. Do not rely on memory of Romanian tax law. If the question needs tax or legal advice \
beyond the rule texts (VAT treatment, deadlines, penalties, signatures, SPV), say that this \
needs their accountant and say what to ask them.
- Never state tax rates, percentages, deadlines, fines or legal references from memory, not \
even as examples or "typical" values. Model memory of Romanian tax law is often out of date.
- Never invent invoice data, identifiers or amounts. State amounts in the invoice's own \
currency (invoice_currency in the context); never assume RON.
- relevant_official_rules are texts from ANAF's official CIUS-RO Schematron that match the \
question. They say how the e-Factura XML must be built, so use them and cite them by rule id, \
for example (BR-RO-030). They cover XML requirements only, not tax rates or legal deadlines.
- If the question can mean different things (for example an invoice "rejected" by the client \
versus rejected by ANAF's validation), ask one short clarifying question, or answer each \
meaning separately and say which is which.
- Be brief and practical: two to six sentences, or a short list.
- Answer in {language}."""

SOURCES_RULES = """

Official sources were retrieved for this question from anaf.ro, mfinante.gov.ro or \
legislatie.just.ro. They are numbered in the context.
- For facts beyond the invoice context, use only these sources and cite them inline as [1], [2].
- Every number, rate, deadline or legal reference you state must come from a cited source.
- End every sentence that states a rule, number, deadline, fine or legal requirement with its \
citation, for example "... within 5 working days [2]." A sentence without a citation must not \
state any such fact. Code checks this and shows uncited sentences to the user as unverified.
- Cite only sources that actually say it. Ignore sources that are off-topic.
- If the sources do not answer the question, say so plainly and suggest what to ask the \
accountant. Do not fill the gap from memory.
- Sources may be in Romanian or out of date; mention the publication date when it matters.
- This is information, not legal advice; keep the suggestion to confirm with the accountant."""

MAX_HISTORY = 10


def _document_currency(session: dict) -> str | None:
    xml = session.get("corrected_xml") or session.get("original_xml") or b""
    m = re.search(rb"<cbc:DocumentCurrencyCode[^>]*>\s*([A-Za-z]{3})\s*<", xml)
    return m.group(1).decode().upper() if m else None


def build_context(session: dict, question: str = "") -> str:
    validation = session.get("validation") or {}
    issues = []
    for i in validation.get("issues", []):
        rt = rule_text(i["rule_id"])
        issues.append({
            "rule_id": i["rule_id"], "severity": i["severity"], "message": i["message"],
            "official_rule_text": rt.en if rt else None,
        })
    repair = session.get("repair") or {}
    ctx = {
        "file_name": session.get("file_name"),
        "source": session.get("source"),
        "invoice_currency": _document_currency(session),
        "validator_verdict": "valid" if validation.get("valid") else "invalid",
        "errors": issues[:40],
        "plain_explanations": [
            {k: e.get(k) for k in ("rule_id", "title", "what_is_wrong", "how_to_fix")}
            for e in (session.get("explain") or {}).get("explanations", [])
        ],
        "proposed_fix": {
            "status": repair.get("status"),
            "summary": repair.get("summary"),
            "remaining_errors": [i["rule_id"] for i in (repair.get("final") or {})
                                 .get("issues", [])],
            "questions_for_business": repair.get("needs_input"),
            "diff": (repair.get("diff") or "")[:6000],
        } if repair else None,
        "extracted_from_pdf": session.get("pdf_fields"),
        # Official rule texts matching the question, found offline by keyword search.
        "relevant_official_rules": [
            {"rule_id": r.rule_id, "text_en": r.en, "text_ro": r.ro}
            for r in search_rules(question)
        ] if question else [],
    }
    return json.dumps(ctx, ensure_ascii=False)


@dataclass
class ChatReply:
    answer: str
    call: CallRecord
    sources: list[Source] = field(default_factory=list)
    search_s: float | None = None
    search_error: str = ""
    uncited: list[str] = field(default_factory=list)  # factual sentences without a citation


def chat_reply(session: dict, message: str, llm: LLMClient, lang: str = "en",
               role: str = "reasoning", search: TavilyClient | None = None) -> ChatReply:
    """Answer one question. With `search`, retrieve official sources first and cite them."""
    history = session.setdefault("chat", [])
    message = message[:2000]
    sources, search_s, search_error = [], None, ""
    if search is not None:
        try:
            # The question as asked: the domain restriction already keeps results Romanian and
            # official, and a fixed "e-Factura" suffix pulled VAT questions to the wrong pages.
            sources, search_s = search.search(message, max_results=5, depth="advanced")
        except Exception as e:  # noqa: BLE001  search is optional; answer without it
            search_error = f"{type(e).__name__}"
    system = CHAT_SYSTEM.format(language=LANGUAGES[lang]) + (SOURCES_RULES if sources else "")
    context = "Context for this invoice (JSON):\n" + build_context(session, message)
    if sources:
        context += "\n\nOfficial sources (JSON):\n" + json.dumps(
            [{"n": i, "title": s.title, "url": s.url, "published_date": s.published_date,
              "excerpt": s.excerpt} for i, s in enumerate(sources, 1)], ensure_ascii=False)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": context},
        {"role": "assistant", "content": "Understood. Ask me about this invoice."},
        *history[-MAX_HISTORY:],
        {"role": "user", "content": message},
    ]
    res = llm.chat(role, messages, max_tokens=3000, temperature=0.2)
    record = CallRecord("chat", res.model, round(res.latency_s, 2), res.prompt_tokens,
                        res.completion_tokens, ok=bool(res.text))
    answer = res.text or "Sorry, I could not produce an answer. Please try rephrasing."
    history += [{"role": "user", "content": message}, {"role": "assistant", "content": answer}]
    uncited = flag_uncited(answer, len(sources)) if sources else []
    return ChatReply(answer, record, sources,
                     round(search_s, 2) if search_s is not None else None, search_error, uncited)
