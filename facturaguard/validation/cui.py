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


_CNP_KEY = "279146358279"


def cnp_is_valid(cnp: str) -> bool:
    """13-digit CNP (persons) or NIF (non-residents). ANAF accepts 13 zeros for B2C."""
    if len(cnp) != 13 or not cnp.isdigit():
        return False
    if cnp == "0" * 13:
        return True
    s = sum(int(d) * int(k) for d, k in zip(cnp[:12], _CNP_KEY, strict=True)) % 11
    return (1 if s == 10 else s) == int(cnp[12])
