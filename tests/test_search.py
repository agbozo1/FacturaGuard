import json

import httpx
import pytest

from facturaguard.chat import chat_reply
from facturaguard.config import Settings
from facturaguard.llm.client import LLMResult
from facturaguard.search.rule_watch import RuleWatch, find_versions
from facturaguard.search.tavily import (
    OFFICIAL_DOMAINS,
    SearchNotConfigured,
    Source,
    TavilyClient,
    is_official,
    sanitize_query,
)


def tavily_with(results, seen):
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append({"auth": request.headers.get("authorization"), **json.loads(request.content)})
        return httpx.Response(200, json={"results": results})

    return TavilyClient(Settings(tavily_api_key="tvly-test"),
                        http=httpx.Client(transport=httpx.MockTransport(handler)))


def src(url, title="t", content="c", date="2026-05-01"):
    return {"url": url, "title": title, "content": content, "score": 0.9, "published_date": date}


def test_requires_key():
    with pytest.raises(SearchNotConfigured):
        TavilyClient(Settings(tavily_api_key=""))


def test_sanitize_query_strips_identifiers_but_keeps_words():
    q = sanitize_query("Romania: client RO44172032, CNP 1960101123456, IBAN RO49AAAA1B31007593840000, "
                       "mail a.b@firma.ro, can I fix the invoice?")
    assert "44172032" not in q and "1960101123456" not in q and "RO49" not in q and "@" not in q
    assert q.startswith("Romania") and "fix the invoice" in q


def test_search_sends_bearer_and_official_domains_and_drops_other_sites():
    seen = []
    client = tavily_with([src("https://static.anaf.ro/x.html", "x"),
                          src("https://blog.example.com/y", "y"),
                          src("https://legislatie.just.ro/z", "z")], seen)
    sources, _ = client.search("termen transmitere e-Factura")
    assert seen[0]["auth"] == "Bearer tvly-test"
    assert seen[0]["include_domains"] == OFFICIAL_DOMAINS
    assert [s.url for s in sources] == ["https://static.anaf.ro/x.html", "https://legislatie.just.ro/z"]


def test_is_official():
    assert is_official("https://www.anaf.ro/a") and is_official("https://mfinante.gov.ro/b")
    assert not is_official("https://anaf.ro.evil.com/") and not is_official("https://notanaf.ro/")


def test_rule_watch_detects_only_cius_ro_versions():
    def s(text):
        return Source("t", "https://mfinante.gov.ro/x", text, None, 1.0)

    assert find_versions([s("validare cu ro16931-ubl-1.0.10.zip publicat")]) == ["1.0.10"]
    assert find_versions([s("EN16931 schematron 1.3.16 included")]) == []


def test_rule_watch_flags_newer_and_caches():
    seen = []
    client = tavily_with([src("https://mfinante.gov.ro/static/10/eFactura/ro16931-ubl-1.0.10.zip")],
                         seen)
    watch = RuleWatch()
    r = watch.check(client)
    assert r.newer_version == "1.0.10" and r.current_version == "1.0.9"
    calls = len(seen)
    watch.check(client)
    assert len(seen) == calls  # cached, no new credits spent


class EchoLLM:
    def __init__(self):
        self.system = None
        self.context = None

    def model_for(self, role):
        return "fake"

    def chat(self, role, messages, **kw):
        self.system, self.context = messages[0]["content"], messages[1]["content"]
        return LLMResult("Per ANAF, invoices go through SPV [1].", "fake", None, 0.1, 5, 5)


def test_chat_with_sources_cites_them_and_never_sends_invoice_data():
    seen = []
    client = tavily_with([src("https://www.anaf.ro/efactura", "e-Factura", "Termenul este...")],
                         seen)
    llm = EchoLLM()
    session = {"validation": {"valid": False, "issues": []}, "file_name": "inv.xml"}
    r = chat_reply(session, "What is the deadline for RO44172032?", llm, search=client)
    assert r.sources and r.sources[0].url == "https://www.anaf.ro/efactura"
    assert "cite them inline" in llm.system and "anaf.ro/efactura" in llm.context
    assert "44172032" not in seen[0]["query"]
    # Real-call finding: a fixed "e-Factura" suffix pulled a VAT question to irrelevant pages.
    assert seen[0]["query"] == "What is the deadline for ?" and seen[0]["search_depth"] == "advanced"
    # Real-call finding: with no answer in the sources, Ultra listed outdated VAT rates.
    assert "must come from a cited source" in llm.system
    assert "Never state tax rates" in llm.system


def test_duplicate_pages_are_dropped():
    seen = []
    client = tavily_with([src("https://www.anaf.ro/a?x=1", "Servicii Web - ANAF"),
                          src("https://www.anaf.ro/a?x=2", "Servicii  web - ANAF"),
                          src("https://mfinante.gov.ro/b", "Ghidul e-Factura")], seen)
    sources, _ = client.search("q")
    assert [s.title for s in sources] == ["Servicii Web - ANAF", "Ghidul e-Factura"]


def test_chat_without_search_or_on_search_failure_still_answers():
    llm = EchoLLM()
    session = {"validation": {"valid": True, "issues": []}}
    assert chat_reply(session, "hi", llm).sources == []

    def boom(request):
        raise httpx.ConnectError("down")

    broken = TavilyClient(Settings(tavily_api_key="tvly-x"),
                          http=httpx.Client(transport=httpx.MockTransport(boom)))
    r = chat_reply(session, "hi", llm, search=broken)
    assert r.answer and r.search_error == "ConnectError" and "cite them" not in llm.system
