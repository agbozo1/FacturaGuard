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
pip install -e ".[dev]"            # core
pip install -e ".[schematron]"      # needed for validation (Milestone 3), see note below
cp .env.example .env     # add your NEBIUS_API_KEY
pytest
python scripts/smoke_nebius.py --list   # model IDs your key can use
python scripts/smoke_nebius.py          # one real call per role
```

Use Python 3.11 to 3.13 (3.12 recommended). `saxonche` has no wheel for Python 3.14 on
Intel Macs older than macOS 11 (Catalina), nor for musl/Alpine, Windows on ARM or 32-bit
Python. On those, use Python 3.12 or run via Docker.

## How Nebius and Nemotron are used
- Nebius Token Factory, OpenAI-compatible API, through the `openai` SDK.
- Nemotron 3 Ultra (`MODEL_REASONING`) explains validator errors in English or Romanian and
  proposes repairs as small edit operations (`facturaguard/explain.py`,
  `facturaguard/repair/engine.py`).
- Nemotron 3.5 Lightning (`MODEL_FAST`, thinking switched off) for PDF field extraction
  (Milestone 5).
- Roles map to model IDs in `.env` (`MODEL_FAST`, `MODEL_REASONING`, ...).

## Explain and repair
The model never decides validity and never rewrites the document:
1. The validator finds the errors.
2. Nemotron explains each one, given the validator message and the official rule text
   (`facturaguard/rules/index.py`, extracted from ANAF's Schematron, Romanian and English).
   If the model fails, the official text is shown instead.
3. Nemotron proposes edit operations (set a value, insert or delete an element). Totals come
   from code (`facturaguard/repair/facts.py`), not from the model. Missing business facts
   (invoice number, CIF, names) become questions for the user, never invented values.
4. Code applies the edits and re-validates. Edits are kept only if errors go down and no new
   kind of error appears. Up to two rounds.

```bash
python scripts/try_assist.py data/synthetic/xml/SYN-037.xml --lang ro   # one invoice
python scripts/eval_repair.py --limit 28 --out eval_repair.json        # fix rate on the set
```

## Synthetic data
`data/synthetic/` holds 100 labelled invoices (34 designed valid, 56 with one planted error,
10 with two). Labels are in `manifest.json`. Regenerate with
`python -m facturaguard.synthetic.generate --seed 2026`. Synthetic only, no real client data.

## Status
Milestones 1 (scaffold, client), 2 (synthetic set), 3 (validator) and 4 (explain and repair)
done. See `FEEDBACK.md` for platform notes.

## Validation
`facturaguard/validation/` runs three layers: UBL 2.1 XSD, the ANAF CIUS-RO 1.0.9 Schematron
(compiled with `scripts/build_schematron.py`, output committed) and ANAF's seller/buyer
identifier checks (CUI, CNP/NIF). Rule sources and versions are in `vendor/SOURCES.md`.
Check the synthetic set with `python scripts/validate_set.py`. Installing the Schematron
runtime: `pip install -e ".[schematron]"`.

Cross-checked against ANAF's own offline validator (ROeFacturaValidator 1.3.0): same verdict on
100/100 synthetic invoices. To repeat on Windows, run ANAF's tool on a copy of
`data/synthetic/xml` and then `python scripts/compare_with_anaf.py <that folder>`.
