"""Tavily web search, restricted to official Romanian sources.

The same principle as everywhere else in FacturaGuard: the model does not answer from memory.
Here it answers from pages published by ANAF, the Ministry of Finance or the official
legislation portal, and every answer carries its links. Only the user's question is sent,
with identifiers removed; invoice data is never sent.
"""

import re
import time
from dataclasses import asdict, dataclass
from urllib.parse import urlparse

import httpx

from facturaguard.config import Settings, get_settings

API_URL = "https://api.tavily.com/search"
OFFICIAL_DOMAINS = ["anaf.ro", "mfinante.gov.ro", "legislatie.just.ro"]
MAX_QUERY_CHARS = 300

# Strip anything that could identify a business or person before a query leaves the server.
_REDACT = [
    re.compile(r"\bRO\d{2}(?:\s?[A-Z0-9]{4}){5}\b", re.IGNORECASE),     # Romanian IBAN
    re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"),                          # email
    re.compile(r"\b[1-9]\d{12}\b"),                                      # CNP
    re.compile(r"\b(?:RO)?\s?\d{6,10}\b", re.IGNORECASE),                # CUI / CIF
]


class SearchNotConfigured(RuntimeError):
    pass


@dataclass
class Source:
    title: str
    url: str
    excerpt: str
    published_date: str | None
    score: float

    def to_dict(self) -> dict:
        return asdict(self)


def sanitize_query(text: str) -> str:
    for pattern in _REDACT:
        text = pattern.sub(" ", text)
    return " ".join(text.split())[:MAX_QUERY_CHARS]


def is_official(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in OFFICIAL_DOMAINS)


class TavilyClient:
    def __init__(self, settings: Settings | None = None, http: httpx.Client | None = None):
        self.settings = settings or get_settings()
        if not self.settings.tavily_api_key:
            raise SearchNotConfigured("TAVILY_API_KEY is not set")
        self._http = http or httpx.Client(timeout=self.settings.tavily_timeout_seconds)

    def search(self, query: str, *, max_results: int = 5, time_range: str | None = None,
               depth: str = "basic") -> tuple[list[Source], float]:
        """Return official sources for the query and the search latency in seconds."""
        body = {
            "query": sanitize_query(query),
            "search_depth": depth,
            "max_results": max_results,
            "include_domains": OFFICIAL_DOMAINS,
            "include_answer": False,
        }
        if time_range:
            body["time_range"] = time_range
        start = time.perf_counter()
        resp = self._http.post(API_URL, json=body, headers={
            "Authorization": f"Bearer {self.settings.tavily_api_key}"})
        resp.raise_for_status()
        latency = time.perf_counter() - start
        sources = []
        for r in resp.json().get("results", []):
            url = str(r.get("url", ""))
            if not is_official(url):  # defence in depth; include_domains should already do this
                continue
            sources.append(Source(
                title=str(r.get("title", ""))[:200],
                url=url,
                excerpt=" ".join(str(r.get("content", "")).split())[:1200],
                published_date=r.get("published_date"),
                score=float(r.get("score") or 0),
            ))
        return sources, latency
