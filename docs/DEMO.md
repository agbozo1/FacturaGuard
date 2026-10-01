# Demo video script (3 minutes)

Goal: show one complete flow on the hosted app, make Nemotron on Nebius Token Factory visible,
and show why grounding matters. Record at 1440x900, browser zoom 100%, English UI unless noted.
Use only synthetic samples. Keep it under 3:00 (YouTube, public).

Before recording:
- Open the hosted app once to wake the free Render instance (first request is slow).
- Tabs ready: app home, `/?sample=payable`, `/?sample=number`, `/?sample=pdf-payable`,
  the GitHub README, and `FEEDBACK.md`.
- Check the sidebar shows "AI connected (NVIDIA Nemotron on Nebius)".

| Time | Screen | Say (short) |
|---|---|---|
| 0:00 to 0:15 | Home page | "Romanian businesses must send every B2B invoice through ANAF's e-Factura. One wrong field and it bounces back with a rule code in technical Romanian. FacturaGuard catches that first." |
| 0:15 to 0:35 | `FEEDBACK.md`, the note where Ultra and Super answered wrongly | "We asked Nemotron directly what an e-Factura needs. Both Ultra and Super got it wrong. So FacturaGuard never trusts model memory: official rules decide, Nemotron explains." |
| 0:35 to 1:05 | Sample "Wrong amount due": verdict Invalid, BR-CO-16 card, then **Explain with AI** | "The validator runs ANAF's own rule files, and agrees with ANAF's official validator on all 100 of our test invoices. Nemotron 3 Ultra on Token Factory turns rule BR-CO-16 into plain words, with the official text right beside it." |
| 1:05 to 1:35 | **Propose a fix**: diff, "Corrected version is valid", download | "Nemotron proposes a small edit, not a new document. Code applies it and re-validates. The total comes from code, not the model. Only a fix that passes is shown." |
| 1:35 to 2:00 | Sample "Missing invoice number", switch to **RO**, Propose a fix, answer the question | "Some fixes need facts only the business knows. FacturaGuard asks instead of inventing. In Romanian, too." |
| 2:00 to 2:25 | Sample "PDF with wrong total": fields read from the PDF, grounding note, BR-CO-16 | "PDFs too. Nemotron 3.5 Lightning copies the fields, code checks every value really is in the PDF, and code builds the e-Factura XML. The mistake printed on the PDF is caught." |
| 2:25 to 2:45 | Chat chip "What should I ask my accountant?", then **Share with accountant** | "Ask follow-up questions, then send your accountant a summary with the official rules and the exact changes." |
| 2:45 to 3:00 | README architecture diagram | "Deterministic validation, grounded Nemotron explanations, re-validated fixes. FacturaGuard, built on Nebius Token Factory with NVIDIA Nemotron. Open source under AGPL-3.0." |

Notes:
- If a model call is slow on camera, cut the wait in editing; do not fake output.
- After the fix, click **Export final XML** to show the clean file and its "ready to send"
  message. FacturaGuard does not send invoices to ANAF; say so if asked.
- The About page (`/about.html`) has a simple five-step diagram that works well as an opening
  or closing shot.
- Do not show the `.env` file or any API key.
