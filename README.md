# FacturaGuard

AI copilot that checks Romanian e-Factura invoices before ANAF rejects them,
explains errors in plain English or Romanian, and proposes corrected XML.
It complements accountants, it does not replace them.

Built for the Nebius x NVIDIA Global AI Hackathon (track: Best Apps & Agents).
Synthetic data only.

## Principles
1. Deterministic validation (XSD + Schematron) decides validity. The LLM only explains and repairs.
2. Explanations are grounded in validator output and official rule text.
3. All model access goes through `facturaguard/llm/client.py`. Models are set in `.env`.
4. Live ANAF submission is out of scope. A mock adapter sits behind an interface.

## Setup
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env     # add your NEBIUS_API_KEY
pytest
python scripts/smoke_nebius.py --list   # model IDs your key can use
python scripts/smoke_nebius.py          # one real call per role
```

## How Nebius and Nemotron are used
- Nebius Token Factory, OpenAI-compatible API, through the `openai` SDK.
- Nemotron (fast tier) for PDF field extraction and classification.
- Nemotron (reasoning tier) for error explanations, XML repair proposals and chat.
- Roles map to model IDs in `.env` (`MODEL_FAST`, `MODEL_REASONING`, ...).

## Status
Milestone 1 done (scaffold, config, client, smoke script). See `FEEDBACK.md` for platform notes.
