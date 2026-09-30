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
