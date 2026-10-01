"""Deterministic code lists for turning printed invoice text into UBL codes."""

import re
import unicodedata

# ISO 3166-2:RO. Keys are normalised county names (lowercase, no diacritics, no hyphens).
RO_COUNTIES = {
    "alba": "RO-AB", "arad": "RO-AR", "arges": "RO-AG", "bacau": "RO-BC", "bihor": "RO-BH",
    "bistrita nasaud": "RO-BN", "botosani": "RO-BT", "brasov": "RO-BV", "braila": "RO-BR",
    "buzau": "RO-BZ", "caras severin": "RO-CS", "calarasi": "RO-CL", "cluj": "RO-CJ",
    "constanta": "RO-CT", "covasna": "RO-CV", "dambovita": "RO-DB", "dolj": "RO-DJ",
    "galati": "RO-GL", "giurgiu": "RO-GR", "gorj": "RO-GJ", "harghita": "RO-HR",
    "hunedoara": "RO-HD", "ialomita": "RO-IL", "iasi": "RO-IS", "ilfov": "RO-IF",
    "maramures": "RO-MM", "mehedinti": "RO-MH", "mures": "RO-MS", "neamt": "RO-NT",
    "olt": "RO-OT", "prahova": "RO-PH", "satu mare": "RO-SM", "salaj": "RO-SJ",
    "sibiu": "RO-SB", "suceava": "RO-SV", "teleorman": "RO-TR", "timis": "RO-TM",
    "tulcea": "RO-TL", "vaslui": "RO-VS", "valcea": "RO-VL", "vrancea": "RO-VN",
    "bucuresti": "RO-B", "municipiul bucuresti": "RO-B",
}
COUNTY_NAMES = {code: name for name, code in RO_COUNTIES.items() if name != "municipiul bucuresti"}

# UN/ECE Recommendation 20 codes for units commonly printed on Romanian invoices.
UNITS = {
    "buc": "C62", "buc.": "C62", "bucata": "C62", "bucati": "C62", "pcs": "C62", "pc": "C62",
    "piece": "C62", "pieces": "C62", "c62": "C62", "unit": "C62", "u": "C62",
    "ora": "HUR", "ore": "HUR", "h": "HUR", "hr": "HUR", "hour": "HUR", "hours": "HUR",
    "hur": "HUR",
    "kg": "KGM", "kgm": "KGM", "g": "GRM", "l": "LTR", "litru": "LTR", "ltr": "LTR",
    "m": "MTR", "ml": "MTR", "mp": "MTK", "m2": "MTK", "zi": "DAY", "zile": "DAY", "day": "DAY",
    "luna": "MON", "month": "MON", "set": "SET", "km": "KMT",
}


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    text = re.sub(r"^(jud(etul)?\.?|judet|county)\s+", "", text.strip())
    return " ".join(re.sub(r"[-_]", " ", text).split())


def county_code(county: str | None) -> str | None:
    """'Jud. Cluj', 'Cluj', 'RO-CJ', 'Bucuresti' -> ISO 3166-2:RO code, else None."""
    if not county:
        return None
    raw = county.strip().upper()
    if re.fullmatch(r"RO-[A-Z]{1,2}", raw) and raw in COUNTY_NAMES:
        return raw
    return RO_COUNTIES.get(normalise(county))


def bucharest_sector(*texts: str | None) -> str | None:
    """Find 'Sector 3' / 'Sectorul 3' / 'SECTOR3' in any of the texts -> 'SECTOR3'."""
    for t in texts:
        m = re.search(r"sector(?:ul)?\s*([1-6])\b", normalise(t or ""))
        if m:
            return f"SECTOR{m.group(1)}"
    return None


def unit_code(unit: str | None) -> str | None:
    if not unit:
        return None
    u = normalise(unit).rstrip(".")
    if re.fullmatch(r"[A-Z0-9]{2,3}", unit.strip()) and unit.strip() in UNITS.values():
        return unit.strip()
    return UNITS.get(u) or UNITS.get(u + ".")
