"""Find official rule texts relevant to a free-text question. Offline, deterministic, no model.

The chat used to see only the rules this invoice breaks. A question like "how do I show a USD
invoice with its RON equivalent?" is answered by rules the invoice may not break at all
(BR-RO-030, BR-53). This ranks all ~1,100 official rule texts by keyword overlap (TF-IDF over
English and Romanian text) so the assistant can answer from ANAF's own wording.
"""

import math
import re
import unicodedata
from collections import Counter
from functools import lru_cache

from facturaguard.rules.index import RuleText, load_rules

# A plain word list reads better than a list literal here.
_STOP = set("""
a an and are as at be by can could do does for from has have how i if in into is it its may
me must my of on or our shall should show so that the their them then there these this to
was we what when where which who why will with would you your about also any only same such
si sau de la in din cu pe pentru care ce cum este sunt un o al ale unui unei daca mai
""".split())  # noqa: SIM905
# Map everyday words to the vocabulary of the rule texts.
_SYNONYMS = {
    "usd": ["currency"], "eur": ["currency"], "gbp": ["currency"], "chf": ["currency"],
    "dollar": ["currency"], "dollars": ["currency"], "euro": ["currency"], "valuta": ["currency"],
    "moneda": ["currency"], "foreign": ["currency"], "exchange": ["currency"],
    "equivalent": ["currency", "accounting"], "echivalent": ["currency"], "curs": ["currency"],
    "tva": ["vat"], "cota": ["rate", "vat"], "rate": ["vat"], "discount": ["allowance"],
    "reducere": ["allowance"], "transport": ["charge"], "storno": ["credit", "note"],
    "corectare": ["credit", "note"], "credit": ["note"], "bank": ["account", "payment"],
    "iban": ["account", "payment"], "cif": ["vat", "identifier"], "cui": ["vat", "identifier"],
    "judet": ["subdivision"], "county": ["subdivision"], "sector": ["city"],
    "transaction": ["invoice"], "date": ["date"], "data": ["date"],
}


def _tokens(text: str) -> list[str]:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return [t for t in re.findall(r"[a-z]{2,}|bt-\d+|bg-\d+", text) if t not in _STOP]


@lru_cache
def _index() -> tuple[dict[str, Counter], dict[str, float]]:
    docs = {rid: Counter(_tokens(f"{r.en} {r.ro or ''} {' '.join(r.business_terms)}"))
            for rid, r in load_rules().items() if not rid.startswith(("XSD", "XML"))}
    df = Counter(t for c in docs.values() for t in c)
    n = len(docs)
    idf = {t: math.log((n + 1) / (k + 1)) + 1 for t, k in df.items()}
    return docs, idf


def search_rules(query: str, k: int = 6, min_score: float = 6.0) -> list[RuleText]:
    words = _tokens(query)
    expanded = list(words) + [s for w in words for s in _SYNONYMS.get(w, [])]
    if not expanded:
        return []
    docs, idf = _index()
    q = Counter(expanded)
    scored = []
    for rid, terms in docs.items():
        score = sum(idf.get(t, 0) * min(terms[t], 2) * w for t, w in q.items() if t in terms)
        if score >= min_score:
            scored.append((score, rid))
    rules = load_rules()
    return [rules[rid] for _, rid in sorted(scored, key=lambda x: (-x[0], x[1]))[:k]]
