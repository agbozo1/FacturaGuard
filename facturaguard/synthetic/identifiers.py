"""Romanian CUI/CIF and IBAN helpers for synthetic data."""

import random

_CUI_KEY = "753217532"


def cui_control_digit(body: str) -> int:
    """Control digit for a CUI body (digits without the control digit)."""
    padded = body.zfill(len(_CUI_KEY))
    total = sum(int(d) * int(k) for d, k in zip(padded, _CUI_KEY, strict=True))
    c = (total * 10) % 11
    return 0 if c == 10 else c


def make_cui(rng: random.Random) -> str:
    body = str(rng.randint(10_000, 99_999_999))
    return body + str(cui_control_digit(body))


def cui_is_valid(cui: str) -> bool:
    digits = cui.removeprefix("RO")
    if not digits.isdigit() or not 2 <= len(digits) <= 10 or len(digits) - 1 > len(_CUI_KEY):
        return False
    return cui_control_digit(digits[:-1]) == int(digits[-1])


def corrupt_cui(cui: str) -> str:
    """Change the control digit so the checksum fails."""
    return cui[:-1] + str((int(cui[-1]) + 1) % 10)


def make_iban(rng: random.Random, bank: str = "TEST") -> str:
    bban = bank + "".join(str(rng.randint(0, 9)) for _ in range(16))
    rearranged = bban + "RO00"
    number = "".join(str(int(ch, 36)) for ch in rearranged)
    check = 98 - int(number) % 97
    return f"RO{check:02d}{bban}"
