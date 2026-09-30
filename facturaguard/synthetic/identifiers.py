"""Romanian CUI/CIF and IBAN helpers for synthetic data."""

import random

from facturaguard.validation.cui import cui_control_digit, cui_is_valid  # noqa: F401


def make_cui(rng: random.Random) -> str:
    body = str(rng.randint(10_000, 99_999_999))
    return body + str(cui_control_digit(body))


def corrupt_cui(cui: str) -> str:
    """Change the control digit so the checksum fails."""
    return cui[:-1] + str((int(cui[-1]) + 1) % 10)


def make_iban(rng: random.Random, bank: str = "TEST") -> str:
    bban = bank + "".join(str(rng.randint(0, 9)) for _ in range(16))
    rearranged = bban + "RO00"
    number = "".join(str(int(ch, 36)) for ch in rearranged)
    check = 98 - int(number) % 97
    return f"RO{check:02d}{bban}"
