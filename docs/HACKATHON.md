# Hackathon requirements checklist

Nebius x NVIDIA Global AI Hackathon. Track: **Best Apps and Agents**.
Deadline Oct 30, 2026. Our target: submit by Oct 27.

## Hard requirements
| # | Requirement | Status |
|---|---|---|
| 1 | Runs on Nebius Token Factory or Nebius AI Cloud | Token Factory client verified on a real key. Hosted run pending (Render) |
| 2 | Uses at least one NVIDIA open source model | Nemotron 3 Ultra (explain, repair, chat), 3.5 Lightning (PDF extraction) |
| 3 | Public repo with OSI license, visible at the top of the repo page | Done: AGPL-3.0-only `LICENSE` (OSI-approved), `NOTICE` with copyright and commercial licensing. Repo must be made public; check the official rules accept any OSI licence (not only permissive) |
| 4 | README with setup and run instructions | Done: quick start, Docker, Render |
| 5 | README highlights Nemotron use, where Token Factory helped, other Nebius services | Done, with real eval numbers: repair 18/28 fixed + 8/28 correctly asked; extraction 97.2% fields, 51/52 verdicts (`docs/eval/`) |
| 6 | Working demo URL (hosted app) | Live: https://facturaguard.onrender.com (Render free tier, Frankfurt). Validation verified on the hosted app; AI pending until NEBIUS_API_KEY is set |
| 7 | Public YouTube demo video, 3 minutes or shorter, shows Token Factory and Nemotron | Script ready: `docs/DEMO.md`. Recording pending |
| 8 | Project description: what, why, how | Draft in README "What, why, how" |
| 9 | Feedback on Token Factory, AI Cloud and NVIDIA tools | `FEEDBACK.md` running |
| 10 | If the project existed before the Submission Period, explain what was updated during it | Repo started 2026-09-30. Confirm the official period start date |
| 11 | Pick the track | Best Apps and Agents |

## Track guidance (Best Apps and Agents)
- Nemotron 3 Ultra for serious reasoning, Nano or Super for fast everyday calls.
  Ours: Lightning (fast, thinking off), Ultra (explain and repair), Super (fallback).
- Nebius Serverless Endpoints for deploying and Serverless Jobs for background work are
  encouraged, not required.

## Judging criteria and how we answer them
1. **Technological implementation:** deterministic XSD + Schematron validation with the LLM only
   explaining and repairing, every proposed fix re-validated, model roles swappable by config.
   Report numbers in the README: error recall, fix success rate after re-validation.
2. **Design:** one polished end-to-end flow: upload, results, fix diff, chat, accountant export.
3. **Potential impact:** foreign founders and small Romanian SMEs who depend on accountants.
   Evidence from our own tests: Nemotron Ultra and Super both gave a wrong answer about
   e-Factura requirements without grounding (see `FEEDBACK.md`), which motivates the design.
4. **Quality of the idea:** grounding explanations in official rule text, not model memory.

## Other prizes worth a look
- **Most Valuable Feedback** ($100, 10 winners): keep `FEEDBACK.md` specific and dated.
- **Best Use of Tavily** ($3,000): optional. Possible use: search current ANAF announcements
  so explanations can flag recent rule or VAT changes. Needs a decision before we add a
  dependency.

## Rules to keep
- Synthetic data only, no real client data.
- Never commit API keys.
- Keep the demo within 3 minutes and public on YouTube.
