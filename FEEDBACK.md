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
