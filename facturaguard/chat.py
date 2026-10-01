"""Follow-up chat about one checked invoice, grounded in that invoice's validation results."""

import json

from facturaguard.llm.ask import CallRecord
from facturaguard.llm.client import LLMClient
from facturaguard.llm.prompts import LANGUAGES
from facturaguard.rules.index import rule_text

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
- Never invent invoice data, identifiers or amounts.
- Be brief and practical: two to six sentences, or a short list.
- Answer in {language}."""

MAX_HISTORY = 10


def build_context(session: dict) -> str:
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
    }
    return json.dumps(ctx, ensure_ascii=False)


def chat_reply(session: dict, message: str, llm: LLMClient, lang: str = "en",
               role: str = "reasoning") -> tuple[str, CallRecord]:
    history = session.setdefault("chat", [])
    messages = [
        {"role": "system", "content": CHAT_SYSTEM.format(language=LANGUAGES[lang])},
        {"role": "user", "content": "Context for this invoice (JSON):\n" + build_context(session)},
        {"role": "assistant", "content": "Understood. Ask me about this invoice."},
        *history[-MAX_HISTORY:],
        {"role": "user", "content": message[:2000]},
    ]
    res = llm.chat(role, messages, max_tokens=3000, temperature=0.2)
    record = CallRecord("chat", res.model, round(res.latency_s, 2), res.prompt_tokens,
                        res.completion_tokens, ok=bool(res.text))
    answer = res.text or "Sorry, I could not produce an answer. Please try rephrasing."
    history += [{"role": "user", "content": message[:2000]},
                {"role": "assistant", "content": answer}]
    return answer, record
