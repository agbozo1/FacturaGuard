"""Romanian CUI/CIF control-digit check (ANAF checks identifiers outside Schematron)."""

_KEY = "753217532"


def cui_control_digit(body: str) -> int:
    padded = body.zfill(len(_KEY))
    total = sum(int(d) * int(k) for d, k in zip(padded, _KEY, strict=True))
    c = (total * 10) % 11
    return 0 if c == 10 else c


def cui_is_valid(cui: str) -> bool:
    digits = cui.removeprefix("RO").strip()
    if not digits.isdigit() or not 2 <= len(digits) <= 10 or len(digits) - 1 > len(_KEY):
        return False
    return cui_control_digit(digits[:-1]) == int(digits[-1])
