from facturaguard.search.citations import flag_uncited, split_sentences

# The real answer from 2026-10-02 (question: resend a rejected invoice with the same number?).
REAL_ANSWER = """No. Romanian fiscal rules require a formal correction procedure, not simply resending the same number.

According to the Methodological Norms on the Fiscal Code, when a document has already been delivered to the beneficiary you must either:
1. Issue a new document that contains the original data, the number and date of the corrected document, and the amounts with a minus sign, **plus** a second document with the correct data; or
2. Issue a single new document with the correct data **and simultaneously** issue a separate document showing the amounts with a minus sign that references the corrected document's number and date [4].

The e-Factura/RO-CTC system follows the same logic: a rejected invoice must be corrected through a **factura de corectare** (correction invoice) that references the original series and number, not by re-transmitting the identical identifier.

Ask your accountant to prepare the proper correction invoice pair (storno + corectare) and to confirm the exact series/numbering rules for your e-Factura provider."""


def test_flags_the_real_uncited_e_factura_claim():
    flagged = flag_uncited(REAL_ANSWER, n_sources=5)
    assert any("RO-CTC system follows the same logic" in s for s in flagged)
    assert not any("[4]" in s for s in flagged)                  # cited sentence passes
    assert not any(s.startswith("Ask your accountant") for s in flagged)  # advice passes


def test_cited_sentences_and_invoice_findings_pass():
    answer = ("From 1 January 2026 the invoice must be sent within 5 working days [1]. "
              "Here the amount due (BT-115) is 5.00 RON too high.")
    assert flag_uncited(answer, n_sources=2) == []


def test_citation_to_a_missing_source_is_flagged():
    assert flag_uncited("The fine is 1,000 lei [7].", n_sources=3) == ["The fine is 1,000 lei [7]."]


def test_plain_sentences_without_facts_pass():
    assert flag_uncited("The sources do not cover this question.", n_sources=3) == []


def test_real_false_alarms_from_2026_10_02_now_pass():
    # Statement about the sources (Romanian), with a year in it.
    ro = ("Sursele oficiale furnizate nu specifică cota de TVA pentru servicii de consultanță "
          "în 2026. Documentele menționează că cota standard de TVA a crescut de la 19% la 21% "
          "[1][3], dar nu există informație explicită despre serviciile de consultanță.")
    assert flag_uncited(ro, n_sources=5) == []
    # Invoice finding written with non-breaking hyphens and markdown bold.
    en = ("2. **ANAF e‑Factura validation rejection** – the invoice failed the mandatory "
          "schema/business‑rule checks (your file shows a fatal BR‑CO‑16 error).")
    assert flag_uncited(en, n_sources=5) == []


def test_lead_in_line_with_a_currency_code_is_not_a_claim():
    answer = ("To show the USD transaction amount and the RON equivalent, use these e-Factura "
              "fields:\n- **BT-6** = `RON`, mandatory when BT-5 is not RON (BR-RO-030).")
    assert flag_uncited(answer, n_sources=4) == []
    # An amount in RON is still a factual claim that needs a citation.
    assert flag_uncited("The fine is 2,500 RON.", n_sources=4) == ["The fine is 2,500 RON."]


def test_statements_about_the_users_own_invoice_pass():
    assert flag_uncited("Here `PayableAmount` is 5.00 RON too high.", n_sources=2) == []
    assert flag_uncited("Your invoice shows 24,199.65 RON as amount due.", n_sources=2) == []
    # A general claim with an amount still needs a citation.
    assert flag_uncited("Late invoices cost 1,000 lei.", n_sources=2) == ["Late invoices cost 1,000 lei."]


def test_split_sentences_handles_lists_and_bold():
    parts = split_sentences("**Deadline**\n- First rule [1].\n- Second rule [2].")
    assert parts == ["Deadline", "First rule [1].", "Second rule [2]."]
