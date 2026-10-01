"""Official rule texts, used to ground every explanation.

Texts come from the vendored ANAF CIUS-RO Schematron (EN 16931 rules plus Romanian rules).
Romanian rules carry "<Romanian text> # <English text>"; EN 16931 rules are English only.
FG-* identifier checks are not in the Schematron; their texts quote ANAF's validator messages.
"""

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from lxml import etree

SCH_DIR = Path(__file__).resolve().parents[2] / "vendor" / "anaf" / "ro16931-ubl-1.0.9"
SCH_NS = "http://purl.oclc.org/dsdl/schematron"
_PREFIX = re.compile(r"^\[[^\]]+\]\s*-\s*")
_BT = re.compile(r"\b(BT|BG)-\d+\b")


@dataclass(frozen=True)
class RuleText:
    rule_id: str
    en: str
    ro: str | None
    source: str
    business_terms: tuple[str, ...]

    def text(self, lang: str = "en") -> str:
        return self.ro if lang == "ro" and self.ro else self.en


# rule id -> (English rule text, ANAF validator message in Romanian)
_FG_RULES = {
    "FG-CUI-SELLER": (
        ("The seller VAT identifier (BT-31) with prefix RO must be a valid Romanian CUI "
         "(control digit check)."),
        "CUI vanzator incorect",
    ),
    "FG-CUI-BUYER": (
        ("The buyer Romanian identifier (BT-48 RO VAT id, or BT-47 numeric legal id) must be a "
         "valid Romanian CUI (control digit check)."),
        "CUI cumparator incorect",
    ),
    "FG-CNP-BUYER": (
        ("A 13-digit buyer legal identifier (BT-47) must be a valid CNP or NIF; 13 zeros are "
         "accepted for consumers (B2C)."),
        "CNP sau NIF cumparator incorect",
    ),
    "FG-BUYER-ID": (
        ("The buyer must be identified by a Romanian identifier: an RO VAT id in BT-48, or a "
         "numeric CUI, CNP or NIF in BT-47. A foreign VAT id or a trade-register number alone "
         "is not enough for ANAF's validator."),
        "nu a fost identificat cui cumparator",
    ),
}
_GENERIC = {
    "XSD": "The XML does not follow the UBL 2.1 schema: an element is missing, unknown, in the "
    "wrong order, or has a value of the wrong type (for example a date not in YYYY-MM-DD).",
    "XSD-ROOT": "The file is not a UBL 2.1 Invoice or CreditNote.",
    "XML-WELLFORMED": "The file is not well-formed XML (for example it is truncated or has an "
    "unclosed tag), so no other check can run.",
}


def _clean(s: str) -> str:
    return " ".join(s.split())


@lru_cache
def load_rules() -> dict[str, RuleText]:
    rules: dict[str, RuleText] = {}
    for sch in sorted(SCH_DIR.rglob("*.sch")):
        for el in etree.parse(str(sch)).iter(f"{{{SCH_NS}}}assert", f"{{{SCH_NS}}}report"):
            rule_id = el.get("id")
            raw = _clean("".join(el.itertext()))
            if not rule_id or not raw or rule_id in rules:
                continue
            body = _PREFIX.sub("", raw)
            ro, en = (body.split("#", 1) + [None])[:2] if "#" in body else (None, body)
            en, ro = _clean(en), _clean(ro) if ro else None
            rules[rule_id] = RuleText(
                rule_id=rule_id,
                en=en,
                ro=ro,
                source=str(sch.relative_to(SCH_DIR)).replace("\\", "/"),
                business_terms=tuple(sorted({m.group(0) for m in _BT.finditer(raw)})),
            )
    for rule_id, (en, anaf_ro) in _FG_RULES.items():
        rules[rule_id] = RuleText(rule_id, en, anaf_ro, "ANAF validator (identifier check)",
                                  tuple(sorted({m.group(0) for m in _BT.finditer(en)})))
    for rule_id, en in _GENERIC.items():
        rules[rule_id] = RuleText(rule_id, en, None, "XML / UBL 2.1 XSD", ())
    return rules


def rule_text(rule_id: str) -> RuleText | None:
    return load_rules().get(rule_id)
