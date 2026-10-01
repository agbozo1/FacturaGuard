"""Validate one invoice, explain the errors and propose a fix, with real Nemotron calls.

    python scripts/try_assist.py data/synthetic/xml/SYN-037.xml --lang ro
    python scripts/try_assist.py <file> --no-repair --save out.json
"""

import argparse
import json
import sys
from pathlib import Path

from facturaguard.explain import explain
from facturaguard.llm.client import LLMClient, LLMNotConfigured
from facturaguard.repair.engine import repair
from facturaguard.validation.validate import validate_xml


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", type=Path)
    ap.add_argument("--lang", choices=["en", "ro"], default="en")
    ap.add_argument("--no-repair", action="store_true")
    ap.add_argument("--save", type=Path, help="write the full result as JSON")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        llm = LLMClient()
    except LLMNotConfigured as e:
        print(f"error: {e}. Copy .env.example to .env first.", file=sys.stderr)
        return 2
    xml = args.file.read_bytes()
    result = validate_xml(xml)
    print(f"validator: {'VALID' if result.valid else 'INVALID'} "
          f"({sum(i.severity == 'fatal' for i in result.issues)} fatal issues)\n")
    ex = explain(result, xml, llm, lang=args.lang)
    for e in ex.explanations:
        print(f"[{e.rule_id}] {e.title}  ({e.source})")
        for label, text in (("what", e.what_is_wrong), ("why", e.why_it_matters),
                            ("fix", e.how_to_fix), ("official", e.official_rule)):
            if text:
                print(f"  {label}: {text}")
        print()
    out = {"validation": result.to_dict(), "explain": ex.to_dict()}
    if not args.no_repair and not result.valid:
        r = repair(xml, llm, lang=args.lang)
        print(f"repair: {r.status} after {r.rounds} round(s); "
              f"{len(r.ops_applied)} op(s) applied, {len(r.ops_rejected)} rejected")
        if r.summary:
            print(f"  summary: {r.summary}")
        for q in r.needs_input:
            print(f"  needs input: {q.get('field')} {q.get('question')}")
        if r.final.issues:
            print(f"  remaining: {sorted({i.rule_id for i in r.final.issues})}")
        if r.diff:
            print("\n" + r.diff)
        out["repair"] = r.to_dict()
    calls = ex.calls + (r.calls if "repair" in out else [])
    for c in calls:
        print(f"call {c.purpose}: {c.model} {c.latency_s}s "
              f"in={c.prompt_tokens} out={c.completion_tokens} ok={c.ok} {c.error}")
    if args.save:
        args.save.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
