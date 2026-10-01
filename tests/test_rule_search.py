from facturaguard.chat import build_context
from facturaguard.rules.search import search_rules


def ids(q):
    return [r.rule_id for r in search_rules(q)]


def test_usd_question_finds_the_currency_rules():
    # Real user question (2026-10-02) that the assistant could not answer before.
    found = ids("in the case where USD was the transaction amount how do i show it and the RON "
                "equivalent?")
    assert found[:2] == ["BR-RO-030", "BR-53"]


def test_any_iso_currency_finds_the_currency_rules():
    for q in ["How do I invoice in HUF?", "Can I issue the invoice in JPY with the RON value?",
              "invoice amounts in CAD", "Factura in PLN, ce trebuie sa completez?"]:
        assert {"BR-RO-030", "BR-53"} & set(ids(q)), q


def test_currency_codes_that_are_english_words_need_capitals():
    # ALL (lek) and TRY (lira) are ISO codes; lowercase "all"/"try" are just words.
    assert "BR-RO-030" not in ids("I will try to fix all the errors on my invoice")
    assert "BR-RO-030" in ids("Can I invoice in TRY?")


def test_other_questions_land_on_the_right_rule_families():
    assert {"BR-RO-110", "BR-RO-111"} <= set(ids("Do I need the county for a Bucharest address?"))
    assert {"BR-41", "BR-42"} <= set(ids("How do I add a discount to the invoice?"))


def test_no_rules_for_empty_or_meaningless_questions():
    assert ids("hello") == [] and ids("") == []


def test_context_carries_relevant_rules_and_the_invoice_currency():
    session = {"validation": {"valid": True, "issues": []},
               "original_xml": b"<x><cbc:DocumentCurrencyCode>USD</cbc:DocumentCurrencyCode></x>"}
    ctx = build_context(session, "how do I show the RON equivalent of a USD invoice?")
    assert '"invoice_currency": "USD"' in ctx and "BR-RO-030" in ctx
