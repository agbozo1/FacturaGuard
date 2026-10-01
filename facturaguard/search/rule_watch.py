"""Check official sources for a CIUS-RO Schematron newer than the one we validate with.

Informational only: it never changes validation. Version detection is done by code (a regex
over titles, URLs and excerpts), not by a model. Results are cached to save search credits.
"""

import re
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime

from facturaguard.search.tavily import Source, TavilyClient

CURRENT_VERSION = "1.0.9"
CACHE_SECONDS = 12 * 60 * 60
QUERIES = [
    "ro16931-ubl schematron CIUS-RO versiune noua e-Factura validare",
    "e-Factura specificatii tehnice RO_CIUS modificari reguli validare",
]
# Only the CIUS-RO package name counts. Generic "schematron x.y.z" mentions also match EN 16931
# versions (1.3.x), which would raise false alarms.
_VERSION = re.compile(r"ro16931[-_ ]ubl[-_ ]?v?(\d+\.\d+\.\d+)", re.IGNORECASE)


def _key(v: str) -> tuple[int, ...]:
    return tuple(int(p) for p in v.split("."))


@dataclass
class RuleWatchResult:
    current_version: str
    newer_version: str | None
    checked_at: str
    sources: list[Source] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["sources"] = [s.to_dict() for s in self.sources]
        return d


def find_versions(sources: list[Source]) -> list[str]:
    found = set()
    for s in sources:
        text = f"{s.title} {s.url} {s.excerpt}"
        found |= set(_VERSION.findall(text))
    return sorted(found, key=_key)


class RuleWatch:
    def __init__(self):
        self._cache: tuple[float, RuleWatchResult] | None = None
        self._lock = threading.Lock()

    def check(self, client: TavilyClient, force: bool = False) -> RuleWatchResult:
        with self._lock:
            if self._cache and not force and time.time() - self._cache[0] < CACHE_SECONDS:
                return self._cache[1]
            sources: list[Source] = []
            seen = set()
            for q in QUERIES:
                for s in client.search(q, max_results=5, time_range="year")[0]:
                    if s.url not in seen:
                        seen.add(s.url)
                        sources.append(s)
            newer = [v for v in find_versions(sources) if _key(v) > _key(CURRENT_VERSION)]
            result = RuleWatchResult(
                current_version=CURRENT_VERSION,
                newer_version=newer[-1] if newer else None,
                checked_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
                sources=sources[:6],
            )
            self._cache = (time.time(), result)
            return result
