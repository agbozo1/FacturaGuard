# Feedback on Nebius Token Factory and NVIDIA Nemotron

Dated notes for the hackathon submission feedback fields.

## 2026-09-30
- Docs gap: docs.tokenfactory.nebius.com and nebius.com were not reachable from
  our sandboxed environment, so the base URL and model IDs were taken from the
  public nebius/token-factory-cookbook on GitHub instead.
- Docs gap: the base URL is regional (`api.tokenfactory.us-central1.nebius.com`).
  It was not obvious how a key maps to a region.
- Docs gap: model ID casing is inconsistent across the cookbook
  (`nvidia/Nemotron-3_5-Lightning`, `nvidia/nemotron-3-super-120b-a12b`,
  `nvidia/Nemotron-3-Ultra-550b-a55b`).
- Not yet verified: structured output and function calling per model.

## 2026-09-30 (later)
- Environment note: `saxonche` has no wheel for Python 3.14 on Intel macOS older than
  macOS 11, so `pip` reports "no matching distribution". Pinned Python to 3.11-3.13.

## 2026-09-30 (first real calls, from the user's key)
- `/models` returned 18 models. Nemotron: Nemotron-3_5-Lightning, nemotron-3-super-120b-a12b,
  Nemotron-3-Ultra-550b-a55b, NVIDIA-Nemotron-3-Nano-30B-A3B. `nemotron-3-nano-omni` (listed in
  the cookbook) was NOT available on this key. Docs gap: cookbook lists models the catalog lacks.
- Lightning (fast tier) is a reasoning model. With max_tokens=200 the whole budget went to a
  visible "thinking process" in the content field and no answer was produced. Latency 2.51s for
  200 tokens. Wish: a documented, per-request switch to disable thinking.
- Ultra answered a simple e-Factura question quickly (0.47s, 61 tokens) but WRONGLY: claimed the
  invoice must be digitally signed and get an ANAF-assigned UID. This confirms that model memory
  of Romanian tax rules is unreliable, so explanations must be grounded in validator output.
- `extra_body={"chat_template_kwargs": {"enable_thinking": false}}` works on Lightning through the
  OpenAI-compatible endpoint: 1.30s and 29 tokens, no reasoning text. Without it: 4.19s and all 800
  tokens spent thinking with no final answer. Docs gap: this switch is not documented for Token
  Factory (found by trying the vLLM-style parameter).
- Same prompt, three models: Ultra (0.70s) and Super (0.84s) both wrongly said the invoice needs a
  qualified digital signature. Ultra also invented "CIUS-PT" (a Portuguese profile) and an "ANAF
  acceptance stamp". Romanian e-invoicing knowledge is unreliable at every size, so explanations
  stay grounded in validator output and official rule text.
- Ultra and Super return reasoning in a separate field (109 and 413 chars), not in the answer.

## 2026-09-30 (validator)
- Not a Token Factory note: the ANAF CIUS-RO package (ro16931-ubl-1.0.9) ships only Schematron
  source, no compiled XSLT, so the rules are compiled locally with the ISO Schematron XSLT and
  saxonche. Full run over 100 invoices takes about 1.4s including compile.

## 2026-10-01 (validator, cross-checked with ANAF's offline tool)
- Not a Token Factory note. ANAF's own validator found two gaps in ours: attribute-context
  Schematron rules were skipped by the ISO compiler (fixed), and ANAF checks buyer and seller
  identifiers outside the Schematron (reproduced). Now 100/100 verdicts agree.
- ANAF's validator takes about 37s for 100 files; ours about 1.4s.

## 2026-10-01 (PDF extraction design)
- Feature wish: a Nemotron vision model on Token Factory. `nemotron-3-nano-omni` is in the
  cookbook but not on our key, so scanned PDFs are out of scope; we read text-based PDFs only
  and use Lightning (thinking off) for extraction.
- Real-call numbers for extraction and repair are pending (no key on the dev machine).

## 2026-10-02 (user test: a USD invoice)
- On the deployed (older) version, asked how to show a USD invoice with its RON equivalent,
  Ultra said the retrieved web pages did not cover it. The answer was in our own vendored rules
  all along (BR-RO-030: BT-6 must be RON when BT-5 is not; BR-53: then BT-111 is required), but
  the chat only saw the rules this invoice breaks. Added an offline keyword search over all
  1,105 official rule texts; the top two results for the question are BR-RO-030 and BR-53, and
  Ultra now answers correctly, citing rule IDs, in about 2 s.
- Ultra stated an amount as "8.50 RON" on a USD invoice. The context now carries the invoice
  currency and the prompt forbids assuming RON.
- In both answers Tavily's pages went unused (the official rules were enough), yet the UI listed
  them as if they supported the answer. The UI now shows only cited sources and keeps the rest
  under "Also searched". Each such question still costs 2 search credits.
- The chat showed raw Markdown (**bold**, lists). Chat answers are now rendered with the same
  safe, DOM-only Markdown renderer as the accountant summary.

## 2026-10-02 (after the Tavily fixes, real calls from the dev machine)
- VAT-rate question, searched as asked with advanced depth: relevant official sources (Ministry
  of Finance fiscal strategy 2026-2028, legislation portal, Fiscal Code). Ultra cited the 19 to
  21 % change and stated nothing from memory.
- Deadline question: every factual sentence carried a citation. Sources conflict (a 2024 ANAF
  guide says 5 calendar days, newer pages say 5 working days); Tavily returned no publication
  date for most official pages, so the model cannot tell which source is newer. Wish: more
  reliable published_date on government PDFs.
- New failure mode, then fixed: on "can I resend a rejected invoice with the same number?",
  Ultra added one uncited sentence from memory about e-Factura. Added a code check that flags
  factual sentences without a valid [n] citation and shows them in the UI as unverified, plus a
  prompt rule to ask when a question is ambiguous. With the rule, Ultra asked "rejected by the
  client or by ANAF's validation?" instead of guessing.
- Repeated Tavily queries returned in 0.14 to 0.42 s (versus 3 to 4 s first time), apparently
  cached on Tavily's side.
- Advanced search depth costs 2 credits per chat question; worth it for relevance.

## 2026-10-02 (Tavily + Nemotron on the hosted app)
- Tavily search restricted to anaf.ro, mfinante.gov.ro and legislatie.just.ro: 3.5 to 4.4 s
  per search (basic depth). Results stayed on the official domains.
- Deadline and fines question (English): Tavily found an ANAF communique from January 2026 and
  the Ministry of Finance e-Factura guide; Ultra answered with [1], [2] citations and pointed to
  the accountant. 6.6 s end to end. This is the behaviour we want.
- VAT-rate question (Romanian): our query suffix ("e-Factura ANAF Romania") pulled five
  irrelevant "Servicii Web - ANAF" pages. Ultra correctly said the sources did not answer, but
  then listed 19 %, 9 % and 5 % as possible rates from memory. Those are outdated (21 % and 11 %
  since August 2025). Model memory leaks even when told not to rely on it.
  Fixes: send the question unchanged, use advanced depth for chat, drop duplicate pages, and a
  prompt rule that every rate, amount, deadline or legal reference must come from a cited
  source, never from memory, not even as an example.
- Rule-update check: 4.8 s, relevant official pages (MF "Informatii tehnice", "Validare XML
  factura"), no CIUS-RO version newer than 1.0.9 mentioned.
- PDF extraction latency varied more on this run: 9.0 s for one PDF (2.8 s median in the eval).

## 2026-10-02 (evals with real calls, from the dev machine)
- Repair, Nemotron 3 Ultra, 28 invoices: 18 fixed and re-validated, 8 correctly asked for a
  missing business fact instead of inventing it, 1 asked for the invoice type code, 1 declined
  (not XML). 29 calls, median 2.67 s, max 9.37 s; median 3,037 prompt and 893 completion
  tokens. JSON mode accepted on every call. Ultra followed "do not invent facts" reliably.
- Extraction, Nemotron 3.5 Lightning (thinking off), 52 PDFs: first run 89.7% fields correct,
  44/52 same verdict. Main issue: despite an explicit instruction, Lightning often returned
  Romanian number formats ("2.054,66", "10,00") and once a mangled "1.069.59", and pasted the
  whole address line into "street". After moving number parsing and address splitting into
  code: 97.2% fields correct, 51/52 same verdict, median 2.84 s.
- Remaining Lightning errors: a decimal shift on one invoice (715.77 for 7,157.70), caught by
  the grounding check; the unit leaking into item descriptions; a county inferred from the
  city name (correct in reality, but not printed), now flagged for the user to verify.
- Lesson for other builders: ask the model to copy, and do conversions in code.
- Wish: a structured-output / JSON-schema mode documented for Lightning on Token Factory, so
  number formats could be enforced by the API rather than by post-processing.
- Lightning, asked directly what an e-Factura needs, again claimed a digital signature is
  required (third model to make this mistake).

## 2026-10-02 (first real calls from the hosted app, Render Frankfurt to Token Factory us-central1)
- Explain, Nemotron 3 Ultra, English, one BR-CO-16 error: 4.47 s, 3,282 prompt and 1,557
  completion tokens. JSON mode accepted. Output accurate and grounded: quoted the invoice's
  real amounts and the official formula, and deferred the judgement call to the accountant.
- Repair, Nemotron 3 Ultra, Romanian summary: 2.48 s, one edit operation, re-validated as
  valid, no rejected operations. Romanian with correct diacritics.
- One small hallucination: the explanation suggested adding a "RoundingAmount" element; the
  UBL element is PayableRoundingAmount. Prompt tightened to take element names only from the
  invoice or rule text.
- Completion tokens (1,557) are high for a short explanation; most is likely reasoning.
  Wish: per-request reasoning budget controls documented for Ultra.

## 2026-10-01 (web app)
- Not a Token Factory note: saxonche (GraalVM native) objects are bound to the creating
  thread; using them from FastAPI worker threads crashed the process. All Schematron work now
  runs on one dedicated thread.
