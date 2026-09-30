"""Run the validator over the synthetic set and compare with the labels.

    python scripts/validate_set.py [--verbose]
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from facturaguard.validation.validate import validate_xml

ROOT = Path(__file__).resolve().parents[1] / "data" / "synthetic"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    manifest = json.loads((ROOT / "manifest.json").read_text())
    bad_valid, missed, extra = [], [], Counter()
    for e in manifest["invoices"]:
        res = validate_xml((ROOT / e["file"]).read_bytes())
        fired = {i.rule_id for i in res.issues if i.severity == "fatal"}
        if e["designed_valid"] and not res.valid:
            bad_valid.append((e["id"], sorted(fired)))
        for rule in set(e["expected_rules"]) - fired:
            missed.append((e["id"], e["mutations"], rule, sorted(fired)))
        if not e["designed_valid"] and res.valid:
            missed.append((e["id"], e["mutations"], "(anything)", []))
        extra.update(fired - set(e["expected_rules"]))
        if args.verbose:
            print(e["id"], e["mutations"], sorted(fired))
    print(f"designed-valid but rejected: {len(bad_valid)}")
    for x in bad_valid[:15]:
        print("  ", x)
    print(f"expected rule not fired: {len(missed)}")
    for x in missed[:30]:
        print("  ", x)
    print("unexpected rules fired (counts):", dict(extra))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
