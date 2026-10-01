"""Measure repair quality on the synthetic set with real model calls.

    python scripts/eval_repair.py --limit 20 --out eval_repair.json

For each invalid invoice: run the repair loop, then let the validator judge. Reports how many
were fixed, how many correctly asked for business input, and latency per call. Invoices whose
fix needs a business fact (missing number, date, name, identifier) count as correct when the
model asks instead of inventing a value.
"""

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

from facturaguard.llm.client import LLMClient, LLMNotConfigured
from facturaguard.repair.engine import repair

DATA = Path(__file__).resolve().parents[1] / "data" / "synthetic"
# Mutations whose only honest fix needs information the invoice does not contain.
NEEDS_FACTS = {
    "missing_invoice_number", "missing_issue_date", "missing_seller_name", "missing_buyer_name",
    "bad_cif_checksum", "foreign_buyer_no_ro_id", "no_invoice_lines", "missing_seller_country",
    "missing_buyer_country", "missing_ro_subdivision", "xsd_bad_date", "vat_no_country_prefix",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="0 = all invalid invoices")
    ap.add_argument("--lang", choices=["en", "ro"], default="en")
    ap.add_argument("--out", type=Path, default=Path("eval_repair.json"))
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        llm = LLMClient()
    except LLMNotConfigured as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    manifest = json.loads((DATA / "manifest.json").read_text())["invoices"]
    # One invoice per mutation type first, so a small --limit still covers every kind of error.
    invalid = [e for e in manifest if not e["designed_valid"]]
    seen, firsts, rest = set(), [], []
    for e in invalid:
        key = tuple(e["mutations"])
        (rest if key in seen else firsts).append(e)
        seen.add(key)
    ordered = firsts + rest
    if args.limit:
        ordered = ordered[: args.limit]

    rows, outcomes, latencies = [], Counter(), []
    for n, e in enumerate(ordered, 1):
        r = repair((DATA / e["file"]).read_bytes(), llm, lang=args.lang)
        needs_facts = bool(set(e["mutations"]) & NEEDS_FACTS)
        if r.status == "fixed":
            verdict = "fixed"
        elif needs_facts and r.status in ("needs_input", "partial") and r.needs_input:
            verdict = "asked_for_input"
        elif r.status == "unsupported":
            verdict = "unsupported"
        else:
            verdict = "failed"
        outcomes[verdict] += 1
        latencies += [c.latency_s for c in r.calls if c.ok]
        rows.append({"id": e["id"], "mutations": e["mutations"], "status": r.status,
                     "verdict": verdict, "rounds": r.rounds, "ops_applied": r.ops_applied,
                     "ops_rejected": r.ops_rejected, "needs_input": r.needs_input,
                     "remaining": sorted({i.rule_id for i in r.final.issues}),
                     "calls": [c.to_dict() for c in r.calls]})
        print(f"{n:3d}/{len(ordered)} {e['id']} {'+'.join(e['mutations']):40s} "
              f"{r.status:12s} -> {verdict}", flush=True)

    total = len(ordered)
    print("\nresults:", dict(outcomes), f"of {total}")
    if latencies:
        print(f"model latency: median {statistics.median(latencies):.2f}s, "
              f"max {max(latencies):.2f}s over {len(latencies)} calls")
    args.out.write_text(json.dumps({"summary": dict(outcomes), "total": total, "rows": rows},
                                   indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"details: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
