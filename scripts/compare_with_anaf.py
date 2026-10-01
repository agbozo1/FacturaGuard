"""Compare our validator with ANAF's offline validator (ROeFacturaValidator) on the synthetic set.

ANAF's tool is a Windows/Java download and is not part of this repo. Run it first:

    jre11\\bin\\java -jar ROeFacturaValidator.jar -t FACT1 -d <copy of data/synthetic/xml>

It writes RASP_<file>.txt next to each invoice. Then:

    python scripts/compare_with_anaf.py <that directory>

ANAF reports only the first failing stage (XSD, then Schematron, then identifiers), so the
check is: same verdict, and every finding ANAF reports is also in ours.
"""

import argparse
import json
import re
from pathlib import Path

from facturaguard.validation.validate import validate_xml

ROOT = Path(__file__).resolve().parents[1] / "data" / "synthetic"
# ANAF plain-text messages for checks that run outside the Schematron.
ANAF_TEXT_TO_RULE = {
    "CUI vanzator incorect": "FG-CUI-SELLER",
    "CUI cumparator incorect": "FG-CUI-BUYER",
    "CNP sau NIF cumparator incorect": "FG-CNP-BUYER",
    "nu a fost identificat cui cumparator": "FG-BUYER-ID",
}


def anaf_findings(text: str) -> tuple[bool, set[str]]:
    if "este valid" in text:
        return True, set()
    found = set(re.findall(r"textEroare=\[([A-Za-z0-9-]+)\]", text))
    for phrase, rule in ANAF_TEXT_TO_RULE.items():
        if f"textEroare={phrase}" in text:
            found.add(rule)
    if "SAXParseException" in text:
        found.add("XSD")
    if not found:
        found.add("UNMAPPED")
    return False, found


def ours(data: bytes) -> tuple[bool, set[str]]:
    r = validate_xml(data)
    # ANAF reports both malformed XML and XSD errors as a SAXParseException.
    xml_layers = ("parse", "xsd")
    found = {i.rule_id for i in r.issues if i.severity == "fatal" and i.layer not in xml_layers}
    if any(i.layer in xml_layers for i in r.issues):
        found.add("XSD")
    return r.valid, found


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("rasp_dir", type=Path)
    args = ap.parse_args()
    manifest = json.loads((ROOT / "manifest.json").read_text())["invoices"]
    same_verdict = covered = 0
    problems = []
    for e in manifest:
        rasp = args.rasp_dir / f"RASP_{e['id']}.xml.txt"
        a_valid, a_found = anaf_findings(rasp.read_text(encoding="utf-8", errors="replace"))
        o_valid, o_found = ours((ROOT / e["file"]).read_bytes())
        same_verdict += a_valid == o_valid
        covered += a_found <= o_found
        if a_valid != o_valid or not a_found <= o_found:
            problems.append((e["id"], e["mutations"], sorted(a_found), sorted(o_found)))
    n = len(manifest)
    print(f"same verdict: {same_verdict}/{n}")
    print(f"every ANAF finding also reported by us: {covered}/{n}")
    for p in problems:
        print("  ", p[0], p[1], "ANAF:", p[2], "OURS:", p[3])
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
