"""Extract one invoice PDF with Nemotron, build UBL, validate, and optionally explain/repair.

    python scripts/try_pdf.py data/synthetic/pdf/SYN-001.pdf
    python scripts/try_pdf.py data/synthetic/pdf/SYN-037.pdf --assist --lang ro --save-xml out.xml
"""

import argparse
import json
import sys
from pathlib import Path

from facturaguard.explain import explain
from facturaguard.extraction.pipeline import pdf_to_invoice
from facturaguard.llm.client import LLMClient, LLMNotConfigured
from facturaguard.repair.engine import repair


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", type=Path)
    ap.add_argument("--assist", action="store_true", help="also explain and repair errors")
    ap.add_argument("--lang", choices=["en", "ro"], default="en")
    ap.add_argument("--save-xml", type=Path)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        llm = LLMClient()
    except LLMNotConfigured as e:
        print(f"error: {e}. Copy .env.example to .env first.", file=sys.stderr)
        return 2
    r = pdf_to_invoice(args.file.read_bytes(), llm)
    for c in r.calls:
        print(f"call {c.purpose}: {c.model} {c.latency_s}s in={c.prompt_tokens} "
              f"out={c.completion_tokens} ok={c.ok} {c.error}")
    if not r.ok:
        print(f"failed: {r.error}")
        return 1
    print(json.dumps(r.fields, indent=1, ensure_ascii=False))
    for u in r.ungrounded:
        print(f"NOT FOUND IN PDF: {u['field']} = {u['value']}")
    for w in r.build.warnings:
        print(f"build warning: {w}")
    v = r.validation
    print(f"\nvalidator: {'VALID' if v.valid else 'INVALID'} "
          f"{sorted({i.rule_id for i in v.issues if i.severity == 'fatal'})}")
    if args.save_xml:
        args.save_xml.write_bytes(r.xml)
    if args.assist and not v.valid:
        for e in explain(v, r.xml, llm, lang=args.lang).explanations:
            print(f"\n[{e.rule_id}] {e.title}\n  {e.what_is_wrong}\n  fix: {e.how_to_fix}")
        rep = repair(r.xml, llm, lang=args.lang)
        print(f"\nrepair: {rep.status}; {rep.summary}")
        for q in rep.needs_input:
            print(f"  needs input: {q.get('field')} {q.get('question')}")
        if rep.diff:
            print(rep.diff)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
