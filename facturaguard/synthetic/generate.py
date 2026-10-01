"""Generate the labelled synthetic invoice set.

    python -m facturaguard.synthetic.generate --out data/synthetic --seed 2026

Output: <out>/xml/SYN-NNN.xml and <out>/manifest.json (ground-truth labels).
Deterministic for a given seed. All data is synthetic.
"""

import argparse
import json
import random
from pathlib import Path

from facturaguard.synthetic.invoice import build_invoice, render
from facturaguard.synthetic.mutations import MUTATIONS, Mutation

N_VALID = 34
PER_MUTATION = 2
N_COMBOS = 10

NOTES = [
    (
        "All data is synthetic. Company names are fictional. CIFs are random numbers with a"
        " valid control digit and could coincide with real CUIs by chance."
    ),
    (
        "designed_valid invoices pass the official ro16931-ubl-1.0.9 Schematron and UBL 2.1 XSD"
        " (checked by tests/test_validator.py)."
    ),
    "expected_rules must all fire. Validators may report additional cascading rules.",
    "VAT rates used: 21 and 11 (Romania since 1 Aug 2025). Verify against ANAF guidance.",
]


def plan(rng: random.Random) -> list[list[Mutation]]:
    plans: list[list[Mutation]] = [[] for _ in range(N_VALID)]
    for mut in MUTATIONS:
        plans += [[mut]] * PER_MUTATION
    pool = [m for m in MUTATIONS if m.combinable]
    for _ in range(N_COMBOS):
        while True:
            a, b = rng.sample(pool, 2)
            if a.group != b.group:
                plans.append([a, b])
                break
    return plans


def generate(out: Path, seed: int) -> dict:
    xml_dir = out / "xml"
    xml_dir.mkdir(parents=True, exist_ok=True)
    for old in xml_dir.glob("*.xml"):
        old.unlink()
    plans = plan(random.Random(f"{seed}-plan"))
    entries = []
    for i, muts in enumerate(plans, start=1):
        m = build_invoice(random.Random(f"{seed}-{i}"), i)
        for mut in muts:
            if mut.model_fn:
                mut.model_fn(m)
        xml = render(m)
        for mut in muts:
            if mut.xml_fn:
                xml = mut.xml_fn(xml)
        sid = f"SYN-{i:03d}"
        (xml_dir / f"{sid}.xml").write_text(xml, encoding="utf-8")
        entries.append(
            {
                "id": sid,
                "file": f"xml/{sid}.xml",
                "designed_valid": not muts,
                "mutations": [x.name for x in muts],
                "layers": sorted({x.layer for x in muts}),
                "expected_rules": sorted({r for x in muts for r in x.rules}),
                "needs_rule_mapping": any(x.needs_rule_mapping for x in muts),
                "descriptions": [x.description for x in muts],
            }
        )
    manifest = {"seed": seed, "count": len(entries), "notes": NOTES, "invoices": entries}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("data/synthetic"))
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()
    manifest = generate(args.out, args.seed)
    valid = sum(e["designed_valid"] for e in manifest["invoices"])
    print(f"wrote {manifest['count']} invoices ({valid} valid) to {args.out}")


if __name__ == "__main__":
    main()
