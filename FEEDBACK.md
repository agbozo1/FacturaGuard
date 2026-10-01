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
