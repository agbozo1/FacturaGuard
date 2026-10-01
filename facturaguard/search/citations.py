"""Flag factual sentences in a sourced answer that carry no valid citation.

The prompt tells the model to cite every rule, number and deadline. Real calls showed it still
adds the odd sentence from memory, so code checks: any sentence that states something factual
without a valid [n] is returned, and the UI shows it as "not from a cited source".
Heuristic by design: it may flag a harmless sentence, but it surfaces memory leaks.
"""

import re

_CITATION = re.compile(r"\[(\d{1,2})\]")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-ZĂÂÎȘȚ\"'*(\[])|\n+")
# Statements of fact: numbers, money, rates, time limits, legal references, obligations.
_FACTUAL = re.compile(
    r"\d|%|\b(lei|ron|eur)\b|\b(art\.?|articol|lege|legea|ordin|ordonan|hot[aă]r[aâ]re|cod(ul)? "
    r"fiscal|norme|norms|law|regulation)\b|\b(must|required|mandatory|obliged|deadline|fine|"
    r"penalt|trebuie|obligatori|termen|amend|sanc[tț]|interzis|prohibited|not allowed|cannot)\b",
    re.IGNORECASE)
# Not claims about the outside world: this invoice's validator findings, advice to ask the
# accountant, or statements about what the retrieved sources do or do not say.
_EXEMPT = re.compile(
    r"\b(BR-[A-Z]{0,3}-?\w+|BT-\d+|BG-\d+)\b|accountant|contabil|this invoice|aceast[aă] factur"
    r"|\b(the|these|official) sources\b|\bsursele\b|\bdocumentele\b|sources (do|does) not"
    r"|nu (specific|men[tț]ion|con[tț]in)",
    re.IGNORECASE)
# Models write non-ASCII hyphens (U+2010..U+2015, U+2212), e.g. "BR‑CO‑16".
_HYPHENS = str.maketrans({c: "-" for c in "‐‑‒–—―−"})


def split_sentences(text: str) -> list[str]:
    text = text.translate(_HYPHENS).replace("**", "").replace("__", "")
    out = []
    for p in _SENTENCE_END.split(text):
        s = re.sub(r"^[\s>*#-]*(\d+[.)]\s*)?", "", p).strip(" *_")
        if len(s) > 3:
            out.append(s)
    return out


def flag_uncited(answer: str, n_sources: int) -> list[str]:
    """Factual sentences with no citation, or citing a source number that does not exist."""
    flagged = []
    for s in split_sentences(answer):
        cites = [int(n) for n in _CITATION.findall(s)]
        bad = [n for n in cites if not 1 <= n <= n_sources]
        if bad or (not cites and _FACTUAL.search(s) and not _EXEMPT.search(s)):
            flagged.append(s if len(s) <= 300 else s[:297] + "...")
    return flagged
