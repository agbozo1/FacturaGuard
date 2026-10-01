"""Propose a corrected invoice: model suggests edit ops, code applies them, validator judges.

A round's edits are kept only if the validator reports fewer fatal errors and no new kinds of
error. The validator, not the model, decides whether the result is fixed.
"""

import json
from collections import Counter
from dataclasses import dataclass, field

from facturaguard.explain import unique_issues
from facturaguard.llm.ask import CallRecord, ask_json
from facturaguard.llm.client import LLMClient
from facturaguard.llm.prompts import repair_system
from facturaguard.repair.facts import compute_facts
from facturaguard.repair.patch import apply_ops, unified_diff
from facturaguard.rules.index import rule_text
from facturaguard.validation.models import ValidationResult
from facturaguard.validation.validate import validate_xml
from facturaguard.xmlsafe import parse

MAX_XML_CHARS = 40_000


@dataclass
class RepairResult:
    status: str  # fixed | partial | needs_input | not_fixed | unsupported | already_valid
    original: ValidationResult
    final: ValidationResult
    corrected_xml: bytes | None
    diff: str = ""
    ops_applied: list[dict] = field(default_factory=list)
    ops_rejected: list[dict] = field(default_factory=list)
    needs_input: list[dict] = field(default_factory=list)
    summary: str = ""
    rounds: int = 0
    calls: list[CallRecord] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "original": self.original.to_dict(),
            "final": self.final.to_dict(),
            "corrected_xml": self.corrected_xml.decode("utf-8") if self.corrected_xml else None,
            "diff": self.diff,
            "ops_applied": self.ops_applied,
            "ops_rejected": self.ops_rejected,
            "needs_input": self.needs_input,
            "summary": self.summary,
            "rounds": self.rounds,
            "calls": [c.to_dict() for c in self.calls],
        }


def _fatal_counts(res: ValidationResult) -> Counter:
    return Counter(i.rule_id for i in res.issues if i.severity == "fatal")


def _improves(before: ValidationResult, after: ValidationResult) -> bool:
    b, a = _fatal_counts(before), _fatal_counts(after)
    return sum(a.values()) < sum(b.values()) and set(a) <= set(b)


def _payload(xml: bytes, res: ValidationResult, feedback: str,
             user_facts: dict[str, str] | None = None) -> str:
    errors = []
    for i in unique_issues(res.issues):
        rt = rule_text(i.rule_id)
        errors.append({
            "rule_id": i.rule_id,
            "validator_message": i.message,
            "official_rule_text": rt.en if rt else None,
            "location": i.location,
        })
    body = {
        "errors": errors,
        "computed_facts": compute_facts(parse(xml)),
        "invoice_xml": xml.decode("utf-8", errors="replace")[:MAX_XML_CHARS],
    }
    if user_facts:
        body["facts_provided_by_business"] = user_facts
    if feedback:
        body["feedback_from_previous_attempt"] = feedback
    return json.dumps(body, ensure_ascii=False)


def repair(xml: bytes, llm: LLMClient, lang: str = "en", role: str = "reasoning",
           max_rounds: int = 2, user_facts: dict[str, str] | None = None) -> RepairResult:
    """user_facts: answers the business gave to earlier needs_input questions, keyed by field
    (e.g. {"BT-1": "FG-2026-0042"}). They are the only business facts the model may insert."""
    original = validate_xml(xml)
    if original.valid:
        return RepairResult("already_valid", original, original, xml)
    if any(i.layer == "parse" for i in original.issues):
        # Not XML at all; there is no tree to edit safely.
        return RepairResult("unsupported", original, original, None,
                            summary="The file is not well-formed XML, so it cannot be repaired "
                                    "automatically. Re-export it from the invoicing software.")
    out = RepairResult("not_fixed", original, original, None)
    current, current_res, feedback = xml, original, ""
    seen_questions = set()
    for _ in range(max_rounds):
        if current_res.valid:
            break
        out.rounds += 1
        messages = [
            {"role": "system", "content": repair_system(lang)},
            {"role": "user", "content": _payload(current, current_res, feedback, user_facts)},
        ]
        try:
            data = ask_json(llm, role, messages, purpose="repair", max_tokens=8000,
                            calls=out.calls)
        except Exception as e:  # noqa: BLE001  report it, keep the best XML so far
            out.calls.append(CallRecord("repair", llm.model_for(role), 0.0, None, None, False,
                                        f"{type(e).__name__}: {e}"[:300]))
            break
        for q in data.get("needs_input", []) or []:
            if isinstance(q, dict) and (q.get("rule_id"), q.get("field")) not in seen_questions:
                seen_questions.add((q.get("rule_id"), q.get("field")))
                out.needs_input.append(q)
        if data.get("summary"):
            out.summary = str(data["summary"])
        ops = [op for op in data.get("ops", []) or [] if isinstance(op, dict)]
        if not ops:
            break
        patched = apply_ops(current, ops)
        out.ops_rejected += [{"op": op, "reason": why} for op, why in patched.rejected]
        new_res = validate_xml(patched.xml)
        if _improves(current_res, new_res):
            current, current_res = patched.xml, new_res
            out.ops_applied += patched.applied
            feedback = ""
        else:
            new_rules = sorted(set(_fatal_counts(new_res)) - set(_fatal_counts(current_res)))
            feedback = (
                "Your previous ops were NOT applied because they did not reduce the errors"
                + (f" and introduced new errors {new_rules}" if new_rules else "")
                + ". Rejected ops: "
                + json.dumps([{"op": op, "reason": why} for op, why in patched.rejected])[:1500]
                + ". Propose a different set of ops against the XML below."
            )
    out.final = current_res
    if current is not xml:
        out.corrected_xml = current
        out.diff = unified_diff(xml, current)
    if current_res.valid:
        out.status = "fixed"
    elif out.needs_input:
        out.status = "needs_input"
    elif current is not xml:
        out.status = "partial"
    return out
