"""Extract invoice fields from PDF text with Nemotron (fast tier, thinking off).

The model copies; it does not compute or infer. Code builds the UBL afterwards, and the
grounding check confirms that every extracted value appears in the PDF text.
"""

import json

from facturaguard.llm.ask import CallRecord, ask_json
from facturaguard.llm.client import LLMClient

MAX_TEXT_CHARS = 30_000

FIELDS_SCHEMA = {
    "invoice_number": "string",
    "issue_date": "YYYY-MM-DD",
    "due_date": "YYYY-MM-DD or null",
    "currency": "ISO 4217 code as printed, e.g. RON",
    "seller": {
        "name": "string", "vat_id": "string, as printed, e.g. RO12345678",
        "registration_number": "trade register number, e.g. J40/123/2020, or null",
        "street": "string", "city": "string", "county": "county name without 'Jud.', or null",
        "postal_code": "string or null", "country": "as printed, or null",
        "iban": "string or null",
    },
    "buyer": {
        "name": "string", "vat_id": "string or null",
        "registration_number": "string or null", "street": "string", "city": "string",
        "county": "string or null", "postal_code": "string or null", "country": "string or null",
    },
    "lines": [{
        "description": "string", "unit": "unit of measure as printed",
        "quantity": "decimal", "unit_price": "decimal", "line_total": "decimal",
        "vat_rate": "percent as a decimal, e.g. 21.00",
    }],
    "vat_breakdown": [{"rate": "decimal", "taxable_amount": "decimal", "vat_amount": "decimal"}],
    "totals": {
        "total_without_vat": "decimal", "total_vat": "decimal",
        "total_with_vat": "decimal", "amount_due": "decimal",
    },
}

EXTRACT_SYSTEM = f"""You extract fields from the text of a Romanian invoice PDF.

Rules:
- Copy values exactly as printed. Do not correct, complete, compute or infer anything. If the \
invoice has an arithmetic mistake, copy the printed numbers anyway.
- If a field is not printed, use null. Never guess.
- Only two conversions are allowed: dates to YYYY-MM-DD, and numbers to plain decimals with a \
dot and no thousands separator (Romanian "1.234,56" becomes "1234.56").
- "Furnizor" or "Vanzator" is the seller; "Client", "Cumparator" or "Beneficiar" is the buyer. \
"CIF", "CUI" or "Cod fiscal" is the vat_id. "Reg. Com." is the registration_number.

Respond with JSON only, matching this shape:
{json.dumps(FIELDS_SCHEMA, indent=1)}"""


def extract_fields(text: str, llm: LLMClient, calls: list[CallRecord],
                   role: str = "fast") -> dict:
    messages = [
        {"role": "system", "content": EXTRACT_SYSTEM},
        {"role": "user", "content": text[:MAX_TEXT_CHARS]},
    ]
    return ask_json(llm, role, messages, purpose="extract", max_tokens=4000, calls=calls)
