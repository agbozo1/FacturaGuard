"""Measure PDF extraction against the printed ground truth, with real Nemotron calls.

    python scripts/eval_extraction.py --limit 20 --out eval_extraction.json

Per PDF: field accuracy (exact match after normalising numbers and whitespace), values the
grounding check could not find in the PDF, and whether the built UBL gets the same validator
verdict as the original invoice.
"""

import argparse
import json
import statistics
import sys
from decimal import Decimal
from pathlib import Path

from facturaguard.extraction.numbers import parse_amount
from facturaguard.extraction.pipeline import pdf_to_invoice
from facturaguard.llm.client import LLMClient, LLMNotConfigured

DATA = Path(__file__).resolve().parents[1] / "data" / "synthetic"


def _leaves(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _leaves(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _leaves(v, f"{path}[{i}]")
    else:
        yield path, obj


def _same(a, b) -> bool:
    if a in (None, "") and b in (None, ""):
        return True
    if a is None or b is None:
        return False
    # Numbers are compared by value: the app parses "2.054,66" and "2054.66" identically.
    na, nb = parse_amount(a), parse_amount(b)
    if na is not None and nb is not None:
        return na == nb
    return " ".join(str(a).split()).casefold() == " ".join(str(b).split()).casefold()


def _by_rate(fields: dict) -> dict:
    """VAT rows may come back in any order; score them matched by rate, not position."""
    out = dict(fields)
    rows = fields.get("vat_breakdown") or []
    out["vat_breakdown"] = sorted(rows, key=lambda r: parse_amount(r.get("rate")) or Decimal(0))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", type=Path, default=Path("eval_extraction.json"))
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        llm = LLMClient()
    except LLMNotConfigured as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    entries = json.loads((DATA / "pdf" / "manifest.json").read_text())["invoices"]
    if args.limit:
        entries = entries[: args.limit]
    rows, correct, total, verdicts, latencies = [], 0, 0, 0, []
    for n, e in enumerate(entries, 1):
        r = pdf_to_invoice((DATA / e["file"]).read_bytes(), llm)
        latencies += [c.latency_s for c in r.calls if c.ok]
        truth = dict(_leaves(_by_rate(e["fields"])))
        got = dict(_leaves(_by_rate(r.fields))) if r.ok else {}
        wrong = [{"field": k, "truth": v, "got": got.get(k)} for k, v in truth.items()
                 if not _same(v, got.get(k))]
        correct += len(truth) - len(wrong)
        total += len(truth)
        same_verdict = r.ok and r.validation.valid == e["designed_valid"]
        verdicts += same_verdict
        rows.append({"id": e["id"], "mutations": e["mutations"], "ok": r.ok, "error": r.error,
                     "wrong_fields": wrong, "ungrounded": r.ungrounded,
                     "build_warnings": r.build.warnings if r.build else [],
                     "same_verdict": same_verdict,
                     "calls": [c.to_dict() for c in r.calls]})
        print(f"{n:3d}/{len(entries)} {e['id']} fields {len(truth) - len(wrong)}/{len(truth)} "
              f"ungrounded {len(r.ungrounded)} verdict {'ok' if same_verdict else 'DIFF'}"
              f"{' ' + r.error[:80] if r.error else ''}", flush=True)
    print(f"\nfield accuracy: {correct}/{total} ({100 * correct / max(total, 1):.1f}%)")
    print(f"same validator verdict as the original: {verdicts}/{len(entries)}")
    if latencies:
        print(f"extraction latency: median {statistics.median(latencies):.2f}s, "
              f"max {max(latencies):.2f}s")
    args.out.write_text(json.dumps({"field_accuracy": [correct, total], "verdicts":
                                    [verdicts, len(entries)], "rows": rows}, indent=2,
                                   ensure_ascii=False), encoding="utf-8")
    print(f"details: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
