"""Synthetic invoice models (plain dicts rendered by facturaguard.ubl.render). Synthetic data only."""

import random
from datetime import date, timedelta
from decimal import Decimal

from facturaguard.synthetic.identifiers import make_cui, make_iban
from facturaguard.ubl.render import CUSTOMIZATION_ID, compute_totals, money, render  # noqa: F401

# Romanian VAT rates since 1 Aug 2025 (standard 21, reduced 11). Verify against ANAF guidance.
VAT_RATES = [21, 21, 21, 11]

RO_CITIES = [
    ("RO-B", "SECTOR3", "030167", "Str. Exemplu"),
    ("RO-CJ", "Cluj-Napoca", "400001", "Str. Test"),
    ("RO-TM", "Timisoara", "300001", "Bd. Demo"),
    ("RO-IS", "Iasi", "700001", "Str. Proba"),
    ("RO-BV", "Brasov", "500001", "Str. Model"),
]
EU_BUYERS = [
    ("DE", "Berlin", "10115", "Teststrasse", "DE"),
    ("FR", "Paris", "75001", "Rue de l'Exemple", "FR"),
    ("IT", "Milano", "20100", "Via di Prova", "IT"),
    ("HU", "Budapest", "1051", "Teszt utca", "HU"),
    ("BG", "Sofia", "1000", "ul. Probna", "BG"),
]
SELLER_NAMES = ["Alfa", "Bravo", "Delta", "Orion", "Vega", "Nord", "Atlas", "Luna", "Zenit", "Pixel"]
BUYER_NAMES = ["Kappa", "Sigma", "Omega", "Titan", "Helios", "Nova", "Apex", "Lotus", "Cedar"]
PRODUCTS = [
    ("Servicii consultanta", "HUR"),
    ("Licenta software anuala", "C62"),
    ("Transport marfa", "C62"),
    ("Hartie A4 (top)", "C62"),
    ("Cafea boabe 1kg", "C62"),
    ("Mentenanta website", "HUR"),
    ("Echipament birou", "C62"),
]


def _ro_party(rng: random.Random, names: list[str]) -> dict:
    sub, city, postal, street = rng.choice(RO_CITIES)
    cui = make_cui(rng)
    return {
        "legal_name": f"{rng.choice(names)} Test {rng.randint(1, 99)} SRL",
        "vat_id": f"RO{cui}",
        "reg_no": f"J{rng.randint(1, 40)}/{rng.randint(100, 9999)}/{rng.randint(2005, 2024)}",
        "street": f"{street} {rng.randint(1, 120)}",
        "city": city,
        "postal": postal,
        "subdivision": sub,
        "country": "RO",
    }


def eu_party(rng: random.Random) -> dict:
    cc, city, postal, street, prefix = rng.choice(EU_BUYERS)
    return {
        "legal_name": f"{rng.choice(BUYER_NAMES)} Muster {rng.randint(1, 99)} GmbH",
        "vat_id": f"{prefix}{rng.randint(100_000_000, 999_999_999)}",
        "reg_no": None,
        "street": f"{street} {rng.randint(1, 120)}",
        "city": city,
        "postal": postal,
        "subdivision": None,
        "country": cc,
    }


def build_invoice(rng: random.Random, index: int) -> dict:
    issue = date(2026, 1, 5) + timedelta(days=rng.randint(0, 250))
    lines = []
    for n in range(1, rng.randint(1, 5) + 1):
        name, unit = rng.choice(PRODUCTS)
        qty = Decimal(rng.choice([1, 2, 3, 5, 10]))
        price = Decimal(rng.randint(500, 250_000)) / Decimal(100)
        lines.append(
            {
                "id": str(n),
                "name": name,
                "unit": unit,
                "qty": qty,
                "price": money(price),
                "amount": money(qty * price),
                "rate": rng.choice(VAT_RATES),
            }
        )
    seller = _ro_party(rng, SELLER_NAMES)
    seller["iban"] = make_iban(rng)
    # Designed-valid invoices use Romanian buyers. ANAF's validator rejects a buyer identified
    # only by a foreign VAT id, so that case is a labelled mutation (foreign_buyer_no_ro_id).
    buyer = _ro_party(rng, BUYER_NAMES)
    return {
        "customization": CUSTOMIZATION_ID,
        "number": f"FG-2026-{index:04d}",
        "issue_date": issue.isoformat(),
        "due_date": (issue + timedelta(days=30)).isoformat(),
        "type_code": "380",
        "currency": "RON",
        "seller": seller,
        "buyer": buyer,
        "lines": lines,
        "delta": {},
    }


def shift(m: dict, **deltas) -> None:
    """Add amounts to computed totals, to plant a specific arithmetic error."""
    for key, value in deltas.items():
        m["delta"][key] = m["delta"].get(key, Decimal(0)) + Decimal(value)
