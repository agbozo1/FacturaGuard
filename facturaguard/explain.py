"""Plain-language explanations of validator errors, grounded in official rule text.

The model only rephrases. Each explanation keeps the official rule text next to it, and if the
model is unavailable or answers badly, the official text is used directly.
"""

import json
from dataclasses import asdict, dataclass, field

from facturaguard.llm.ask import CallRecord, ask_json
from facturaguard.llm.client import LLMClient
from facturaguard.llm.prompts import explain_system
from facturaguard.rules.index import rule_text
from facturaguard.validation.models import Issue, ValidationResult

MAX_XML_CHARS = 20_000


@dataclass
class Explanation:
    rule_id: str
    title: str
    what_is_wrong: str
    why_it_matters: str
    how_to_fix: str
    fields: list[str]
    needs_business_input: bool
    official_rule: str
    validator_message: str
    source: str  # "model" | "rule_text"
    # Both languages, so the UI can switch without a new request. ANAF publishes Romanian text
    # only for its BR-RO rules; EN 16931 rules are English only (official_ro is then None).
    official_en: str | None = None
    official_ro: str | None = None

    def __post_init__(self):
        rt = rule_text(self.rule_id)
        if rt and self.official_en is None:
            self.official_en, self.official_ro = rt.en, rt.ro


@dataclass
class ExplainResult:
    lang: str
    explanations: list[Explanation]
    calls: list[CallRecord] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "lang": self.lang,
            "explanations": [asdict(e) for e in self.explanations],
            "calls": [c.to_dict() for c in self.calls],
        }


def unique_issues(issues: list[Issue]) -> list[Issue]:
    seen, out = set(), []
    for i in issues:
        key = (i.rule_id, i.message)
        if i.severity == "fatal" and key not in seen:
            seen.add(key)
            out.append(i)
    return out


def _official(issue: Issue, lang: str) -> str:
    rt = rule_text(issue.rule_id)
    return rt.text(lang) if rt else issue.message


def _fallback(issue: Issue, lang: str) -> Explanation:
    rt = rule_text(issue.rule_id)
    return Explanation(
        rule_id=issue.rule_id,
        title=issue.rule_id,
        what_is_wrong=_official(issue, lang),
        why_it_matters="",
        how_to_fix="",
        fields=list(rt.business_terms) if rt else [],
        needs_business_input=False,
        official_rule=_official(issue, lang),
        validator_message=issue.message,
        source="rule_text",
    )


def _payload(issues: list[Issue], xml: bytes, lang: str) -> str:
    errors = []
    for i in issues:
        rt = rule_text(i.rule_id)
        errors.append({
            "rule_id": i.rule_id,
            "layer": i.layer,
            "validator_message": i.message,
            "official_rule_text_en": rt.en if rt else None,
            "official_rule_text_ro": rt.ro if rt else None,
            "business_terms": list(rt.business_terms) if rt else [],
            "location": i.location,
        })
    text = xml.decode("utf-8", errors="replace")[:MAX_XML_CHARS]
    return json.dumps({"errors": errors, "invoice_xml": text}, ensure_ascii=False)


def explain(result: ValidationResult, xml: bytes, llm: LLMClient | None, lang: str = "en",
            role: str = "reasoning") -> ExplainResult:
    issues = unique_issues(result.issues)
    out = ExplainResult(lang=lang, explanations=[_fallback(i, lang) for i in issues])
    if llm is None or not issues:
        return out
    messages = [
        {"role": "system", "content": explain_system(lang)},
        {"role": "user", "content": _payload(issues, xml, lang)},
    ]
    try:
        data = ask_json(llm, role, messages, purpose="explain", max_tokens=6000, calls=out.calls)
    except Exception as e:  # noqa: BLE001  never fail the user on a model or API error
        out.calls.append(CallRecord("explain", llm.model_for(role), 0.0, None, None, False,
                                    f"{type(e).__name__}: {e}"[:300]))
        return out
    by_rule: dict[str, list[dict]] = {}
    for item in data.get("explanations", []):
        if isinstance(item, dict):
            by_rule.setdefault(str(item.get("rule_id")), []).append(item)
    for idx, issue in enumerate(issues):
        candidates = by_rule.get(issue.rule_id) or []
        if not candidates:
            continue  # keep the rule-text fallback for anything the model skipped
        item = candidates.pop(0)
        out.explanations[idx] = Explanation(
            rule_id=issue.rule_id,
            title=str(item.get("title", issue.rule_id))[:80],
            what_is_wrong=str(item.get("what_is_wrong", "")),
            why_it_matters=str(item.get("why_it_matters", "")),
            how_to_fix=str(item.get("how_to_fix", "")),
            fields=[str(f) for f in item.get("fields", []) if isinstance(f, str)],
            needs_business_input=bool(item.get("needs_business_input", False)),
            official_rule=_official(issue, lang),
            validator_message=issue.message,
            source="model",
        )
    return out
