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

## 2026-10-01 (web app)
- Not a Token Factory note: saxonche (GraalVM native) objects are bound to the creating
  thread; using them from FastAPI worker threads crashed the process. All Schematron work now
  runs on one dedicated thread.
