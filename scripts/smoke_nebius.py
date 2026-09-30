"""Make one real call per model role. Usage:

    python scripts/smoke_nebius.py --list
    python scripts/smoke_nebius.py [--roles fast reasoning]

Prints latency so you can paste notes into FEEDBACK.md.
"""

import argparse
import json
import sys

from facturaguard.llm.client import LLMClient, LLMNotConfigured

PROMPT = (
    "Reply with one short sentence: what does a Romanian e-Factura invoice "
    "need before ANAF accepts it?"
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="list model IDs visible to your key")
    ap.add_argument("--extra-body", help="JSON merged into the request body")
    ap.add_argument("--max-tokens", type=int, default=800)
    ap.add_argument("--roles", nargs="*", default=["fast", "reasoning"])
    args = ap.parse_args()
    try:
        client = LLMClient()
    except LLMNotConfigured as e:
        print(f"error: {e}. Copy .env.example to .env first.", file=sys.stderr)
        return 2
    if args.list:
        print("\n".join(client.list_models()))
        return 0
    extra = json.loads(args.extra_body) if args.extra_body else None
    failed = False
    for role in args.roles:
        try:
            r = client.chat(role, [{"role": "user", "content": PROMPT}], max_tokens=args.max_tokens, extra_body=extra)
            print(f"[{role}] {r.model} {r.latency_s:.2f}s tokens={r.completion_tokens}")
            print(f"  answer: {r.text or '(empty, raise --max-tokens)'}")
            print(f"  reasoning chars: {len(r.reasoning or '')}\n")
        except Exception as e:  # noqa: BLE001  report every role, then exit non-zero
            failed = True
            msg = f"[{role}] {client.model_for(role)} FAILED: {type(e).__name__}: {e}\n"
            print(msg, file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
