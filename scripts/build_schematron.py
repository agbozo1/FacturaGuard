"""Compile the vendored CIUS-RO Schematron (.sch) to a validating XSLT with saxonche.

    python scripts/build_schematron.py

Pipeline: iso_dsdl_include -> iso_abstract_expand -> iso_svrl_for_xslt2.
Output is committed so deployments do not need to compile.
"""

import re
import sys
import tempfile
from pathlib import Path

from saxonche import PySaxonProcessor

ROOT = Path(__file__).resolve().parents[1]
ISO = ROOT / "vendor" / "iso-schematron"
SRC = ROOT / "vendor" / "anaf" / "ro16931-ubl-1.0.9" / "EN16931-CIUS_RO-UBL-validation.sch"
OUT = ROOT / "vendor" / "anaf" / "compiled" / "ro16931-ubl-1.0.9.xslt"


def main() -> int:
    with PySaxonProcessor(license=False) as proc, tempfile.TemporaryDirectory() as tmp:
        xslt = proc.new_xslt30_processor()
        current = str(SRC)
        for step, name in enumerate(
            ["iso_dsdl_include.xsl", "iso_abstract_expand.xsl", "iso_svrl_for_xslt2.xsl"]
        ):
            target = str(OUT) if name.startswith("iso_svrl") else f"{tmp}/step{step}.sch"
            try:
                exe = xslt.compile_stylesheet(stylesheet_file=str(ISO / name))
                exe.transform_to_file(source_file=current, output_file=target)
            except Exception as e:  # noqa: BLE001  saxonche raises its own error types
                print(f"{name} failed: {e}", file=sys.stderr)
                return 1
            current = target
    # The ISO skeleton only visits attributes when `parent::node()` holds for a global
    # variable, which is never true, so rules with attribute contexts (BR-CL-03 on
    # //@currencyID, BR-CL-23 on //@unitCode) never fire. ANAF's validator does fire them.
    # Make every rule walk attributes as well as elements.
    text = OUT.read_text(encoding="utf-8")
    text, n = re.subn(r'<xsl:apply-templates select="\*" mode="(M\d+)"/>',
                      r'<xsl:apply-templates select="@*|*" mode="\1"/>', text)
    if n == 0:
        print("attribute patch matched nothing; skeleton output changed?", file=sys.stderr)
        return 1
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KB, {n} walks patched)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
