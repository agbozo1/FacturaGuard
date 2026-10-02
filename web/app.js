"use strict";

/* FacturaGuard UI. Plain JS, no build step. All dynamic text goes through textContent. */

const I18N = {
  en: {
    newCheck: "New check", trySample: "Try a sample invoice",
    synthetic: "Synthetic demo data only. Do not upload real client invoices.",
    tagline: "Check your Romanian e-Factura before ANAF does.",
    sub: "Upload a UBL XML or a PDF invoice. We validate it against ANAF's official RO_CIUS rules, explain every error in plain words and propose a corrected XML.",
    drop: "Drop an invoice here, or browse (XML, PDF or a scan, max 5 MB)",
    pdfTitleScan: "Read from the scan", scanAlt: "The uploaded scan", scanZoom: "Click to enlarge",
    scanSuspect: "Please check these values against the scan (possibly misread):",
    scanNote: "Read from a scanned image by an AI vision model. Please check every value against the scan before relying on it. If a total does not add up, compare it with the scan first: it may be a reading error.",
    scanOk: "All extracted values match the text read from the scan. Still compare them with the image.",
    p1t: "Official rules", p1: "ANAF CIUS-RO 1.0.9 Schematron and UBL 2.1, cross-checked with ANAF's own validator.",
    p2t: "Plain explanations", p2: "NVIDIA Nemotron explains each error in English or Romanian, grounded in the official rule text.",
    p3t: "Checked fixes", p3: "Every proposed fix is re-validated. Missing business facts are asked, never invented.",
    explainAi: "Explain with AI", fix: "Propose a fix", share: "Share with accountant",
    about: "How FacturaGuard works", aboutShort: "About",
    exportXml: "Export final XML", pdfTitle: "Read from the PDF", fixTitle: "Proposed correction",
    assistant: "AI Assistant",
    chatEmpty: "Check an invoice, then ask me anything about its errors.",
    ask: "Ask about this invoice", summaryTitle: "Summary for your accountant",
    copy: "Copy text", download: "Download .md", print: "Print or save as PDF",
    aiOn: "AI connected (NVIDIA Nemotron on Nebius)", aiOff: "Validation only (AI not configured)",
    checking: "Checking the invoice...", readingPdf: "Reading the document with AI and checking it (scans take about 15 seconds)...",
    explaining: "Nemotron is explaining the errors...", fixing: "Nemotron is proposing a fix; every change is re-validated...",
    valid: "Valid", invalid: "Invalid",
    validSub: "Passes ANAF's RO_CIUS 1.0.9 checks. Ready to send.",
    validSubScan: (n) => `Passes ANAF's RO_CIUS 1.0.9 checks, but ${n} value${n === 1 ? "" : "s"} may have been misread from the scan. Check ${n === 1 ? "it" : "them"} before sending.`,
    exportedValidScan: (n) => `Exported the XML. It passes all checks, but ${n} value${n === 1 ? "" : "s"} may have been misread from the scan: check ${n === 1 ? "it" : "them"} before sending.`,
    invalidSub: (n) => `${n} error${n === 1 ? "" : "s"} that ANAF would reject.`,
    warnings: (n) => `${n} warning${n === 1 ? "" : "s"} (not blocking).`,
    whatWrong: "What is wrong", whyMatters: "Why it matters", howFix: "How to fix",
    official: "Official rule text", details: "Details", location: "Location", fromAi: "Explained by Nemotron",
    fromRule: "Official rule text", fields: "Fields",
    ungrounded: "These values were not found in the PDF text. Please check them:",
    pdfOk: "All extracted values were found in the PDF text.",
    status_fixed: "Fixed: the corrected invoice passes all checks.",
    status_partial: "Partly fixed: some errors remain.",
    status_needs_input: "Needs your input to finish.",
    status_not_fixed: "No safe fix found. The original is unchanged.",
    status_unsupported: "This file cannot be repaired automatically.",
    status_already_valid: "Already valid, nothing to fix.",
    remaining: "Remaining errors", none: "none", answerHint: "Only you know these. Your answers are used exactly as typed.",
    applyAnswers: "Apply answers and retry", downloadXml: "Download corrected XML",
    changes: "Changes", noChanges: "No changes were applied.",
    copied: "Copied.", correctedValid: "Corrected version is valid",
    chips: ["Why would ANAF reject this?", "What should I ask my accountant?", "Which fields do I need to fill in?"],
    errNoAi: "AI features are not configured on this server. Validation still works.",
    thinking: "Thinking...",
    exportedValid: (fixed) => `Exported the ${fixed ? "corrected " : ""}XML. It passes all checks, so it is ready to send to ANAF through your usual channel.`,
    exportedInvalid: (fixed, n) => `Exported the ${fixed ? "corrected" : "original"} XML, but it still has ${n} error${n === 1 ? "" : "s"}, so ANAF would reject it. Fix ${n === 1 ? "it" : "them"} before sending.`,
    rulesVersion: "Rules: ANAF CIUS-RO 1.0.9", checkUpdates: "Check ANAF for updates",
    checkingRules: "Searching official sources...",
    newerFound: (v) => `ANAF sources mention CIUS-RO ${v}, newer than the 1.0.9 rules used here. Results may be out of date; check before relying on them.`,
    noNewer: (when) => `No newer CIUS-RO version found in official sources (checked ${when}).`,
    officialSources: "Search official sources (ANAF, MF, legislatie.just.ro)",
    sourcesTitle: "Official sources", searchUnavailable: "Official-source search was unavailable for this answer.",
    uncitedTitle: "Not from a cited source, please verify:",
    alsoSearched: (n) => `Also searched, not used in the answer (${n})`,
    productOf: "© 2026 Product of Nova Analytica S.R.L.", license: "Source code (AGPL-3.0)",
  },
  ro: {
    newCheck: "Verificare nouă", trySample: "Încearcă o factură exemplu",
    synthetic: "Doar date sintetice de demonstrație. Nu încărcați facturi reale ale clienților.",
    tagline: "Verifică-ți e-Factura înainte s-o verifice ANAF.",
    sub: "Încarcă o factură UBL XML sau PDF. O validăm după regulile oficiale RO_CIUS ale ANAF, explicăm fiecare eroare pe înțeles și propunem un XML corectat.",
    drop: "Trage factura aici sau alege fișierul (XML, PDF sau o scanare, max. 5 MB)",
    pdfTitleScan: "Citit din scanare", scanAlt: "Scanarea încărcată", scanZoom: "Clic pentru mărire",
    scanSuspect: "Verificați aceste valori față de scanare (posibil citite greșit):",
    scanNote: "Citit dintr-o imagine scanată de un model AI de viziune. Verificați fiecare valoare față de scanare înainte de a vă baza pe ea. Dacă un total nu se potrivește, comparați-l întâi cu scanarea: poate fi o eroare de citire.",
    scanOk: "Toate valorile extrase se regăsesc în textul citit din scanare. Comparați-le totuși cu imaginea.",
    p1t: "Reguli oficiale", p1: "Schematron ANAF CIUS-RO 1.0.9 și UBL 2.1, verificate încrucișat cu validatorul ANAF.",
    p2t: "Explicații clare", p2: "NVIDIA Nemotron explică fiecare eroare în română sau engleză, pe baza textului oficial al regulii.",
    p3t: "Corecturi verificate", p3: "Fiecare corectură propusă este revalidată. Datele firmei care lipsesc sunt cerute, nu inventate.",
    explainAi: "Explică cu AI", fix: "Propune o corectură", share: "Trimite contabilului",
    about: "Cum funcționează FacturaGuard", aboutShort: "Despre",
    exportXml: "Exportă XML final", pdfTitle: "Citit din PDF", fixTitle: "Corectură propusă",
    assistant: "Asistent AI",
    chatEmpty: "Verifică o factură, apoi întreabă-mă orice despre erorile ei.",
    ask: "Întreabă despre această factură", summaryTitle: "Rezumat pentru contabil",
    copy: "Copiază textul", download: "Descarcă .md", print: "Tipărește sau salvează PDF",
    aiOn: "AI conectat (NVIDIA Nemotron pe Nebius)", aiOff: "Doar validare (AI neconfigurat)",
    checking: "Se verifică factura...", readingPdf: "Citim documentul cu AI și îl verificăm (scanările durează circa 15 secunde)...",
    explaining: "Nemotron explică erorile...", fixing: "Nemotron propune o corectură; fiecare modificare este revalidată...",
    valid: "Validă", invalid: "Invalidă",
    validSub: "Trece verificările RO_CIUS 1.0.9 ale ANAF. Gata de trimis.",
    validSubScan: (n) => `Trece verificările RO_CIUS 1.0.9 ale ANAF, dar ${n === 1 ? "o valoare poate fi citită greșit" : `${n} valori pot fi citite greșit`} din scanare. Verificați înainte de trimitere.`,
    exportedValidScan: (n) => `Ați exportat XML-ul. Trece toate verificările, dar ${n === 1 ? "o valoare poate fi citită greșit" : `${n} valori pot fi citite greșit`} din scanare: verificați înainte de trimitere.`,
    invalidSub: (n) => `${n} ${n === 1 ? "eroare" : "erori"} pentru care ANAF ar respinge factura.`,
    warnings: (n) => `${n} ${n === 1 ? "avertisment" : "avertismente"} (nu blochează).`,
    whatWrong: "Ce este greșit", whyMatters: "De ce contează", howFix: "Cum se corectează",
    official: "Textul oficial al regulii", details: "Detalii", location: "Locație", fromAi: "Explicat de Nemotron",
    fromRule: "Textul oficial al regulii", fields: "Câmpuri",
    ungrounded: "Aceste valori nu au fost găsite în textul PDF. Vă rugăm verificați-le:",
    pdfOk: "Toate valorile extrase au fost găsite în textul PDF.",
    status_fixed: "Corectată: factura corectată trece toate verificările.",
    status_partial: "Corectată parțial: au rămas erori.",
    status_needs_input: "Avem nevoie de informații de la tine.",
    status_not_fixed: "Nu am găsit o corectură sigură. Originalul nu a fost modificat.",
    status_unsupported: "Acest fișier nu poate fi corectat automat.",
    status_already_valid: "Este deja validă, nu e nimic de corectat.",
    remaining: "Erori rămase", none: "niciuna", answerHint: "Doar tu știi aceste date. Răspunsurile sunt folosite exact cum le scrii.",
    applyAnswers: "Aplică răspunsurile și reîncearcă", downloadXml: "Descarcă XML corectat",
    changes: "Modificări", noChanges: "Nu s-a aplicat nicio modificare.",
    copied: "Copiat.", correctedValid: "Versiunea corectată este validă",
    chips: ["De ce ar respinge ANAF factura?", "Ce să-l întreb pe contabil?", "Ce câmpuri trebuie să completez?"],
    errNoAi: "Funcțiile AI nu sunt configurate pe acest server. Validarea funcționează.",
    thinking: "Mă gândesc...",
    exportedValid: (fixed) => `Ați exportat XML-ul${fixed ? " corectat" : ""}. Trece toate verificările, deci este gata de trimis la ANAF prin canalul obișnuit.`,
    exportedInvalid: (fixed, n) => `Ați exportat XML-ul ${fixed ? "corectat" : "original"}, dar are încă ${n} ${n === 1 ? "eroare" : "erori"}, deci ANAF l-ar respinge. Corectați înainte de trimitere.`,
    rulesVersion: "Reguli: ANAF CIUS-RO 1.0.9", checkUpdates: "Verifică actualizări ANAF",
    checkingRules: "Se caută în surse oficiale...",
    newerFound: (v) => `Sursele ANAF menționează CIUS-RO ${v}, mai nou decât regulile 1.0.9 folosite aici. Rezultatele pot fi depășite; verificați înainte de a vă baza pe ele.`,
    noNewer: (when) => `Nu s-a găsit o versiune CIUS-RO mai nouă în sursele oficiale (verificat ${when}).`,
    officialSources: "Caută în surse oficiale (ANAF, MF, legislatie.just.ro)",
    sourcesTitle: "Surse oficiale", searchUnavailable: "Căutarea în surse oficiale nu a fost disponibilă pentru acest răspuns.",
    uncitedTitle: "Nu provine dintr-o sursă citată, vă rugăm verificați:",
    alsoSearched: (n) => `Căutate, dar nefolosite în răspuns (${n})`,
    productOf: "© 2026 Un produs Nova Analytica S.R.L.", license: "Cod sursă (AGPL-3.0)",
  },
};

const state = { lang: "en", ai: false, search: false, check: null, explain: null, repair: null, busy: false };
const $ = (sel) => document.querySelector(sel);
const t = (key, ...args) => {
  const v = I18N[state.lang][key];
  return typeof v === "function" ? v(...args) : v ?? key;
};

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "class") node.className = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) {
    if (c == null || c === false) continue;
    node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return node;
}

function store(key, value) {
  try { localStorage.setItem(key, value); } catch { /* storage blocked */ }
}
function load(key) { try { return localStorage.getItem(key); } catch { return null; } }

/* ---------- API ---------- */
async function api(path, options = {}) {
  const res = await fetch(path, options);
  const type = res.headers.get("content-type") || "";
  const body = type.includes("json") ? await res.json() : await res.text();
  if (!res.ok) {
    const detail = typeof body === "object" ? body.detail : body;
    const err = new Error(res.status === 503 ? t("errNoAi") : (typeof detail === "string" ? detail : `HTTP ${res.status}`));
    err.status = res.status;
    throw err;
  }
  return body;
}
const post = (path, data) => api(path, {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data),
});

function setStatus(text, kind = "") {
  const s = $("#status");
  s.textContent = text || "";
  s.className = `status ${kind}`;
}

async function run(statusText, fn) {
  if (state.busy) return;
  state.busy = true;
  document.querySelectorAll(".actions button").forEach((b) => (b.disabled = true));
  setStatus(statusText, "busy");
  try {
    await fn();
    setStatus("");
  } catch (e) {
    setStatus(e.message, "error");
  } finally {
    state.busy = false;
    document.querySelectorAll(".actions button").forEach((b) => (b.disabled = false));
    updateActions();
  }
}

/* ---------- i18n ---------- */
function applyLang(lang) {
  state.lang = lang;
  store("fg-lang", lang);
  document.documentElement.lang = lang;
  document.querySelectorAll("[data-i18n]").forEach((n) => (n.textContent = t(n.dataset.i18n)));
  document.querySelectorAll("[data-i18n-placeholder]").forEach((n) => (n.placeholder = t(n.dataset.i18nPlaceholder)));
  document.querySelectorAll(".lang button").forEach((b) => b.classList.toggle("active", b.dataset.lang === lang));
  renderAiStatus();
  renderSamples();
  renderChips();
  if (state.check) renderResults();
}

/* ---------- sidebar ---------- */
function renderAiStatus() {
  const p = $("#ai-status");
  p.classList.toggle("on", state.ai);
  p.lastElementChild.textContent = state.ai ? t("aiOn") : t("aiOff");
}

let SAMPLES = [];
function renderSamples() {
  const ul = $("#samples");
  ul.replaceChildren(...SAMPLES.map((s) => el("li", {},
    el("button", { onclick: () => checkSample(s) },
      el("span", { class: `kind ${s.kind}` }, s.kind.toUpperCase()),
      state.lang === "ro" ? s.label_ro : s.label_en))));
}

async function checkSample(s) {
  const res = await fetch(s.url);
  const blob = await res.blob();
  checkFile(new File([blob], s.file_name, { type: blob.type }));
  $("#sidebar").classList.remove("open");
}

/* ---------- upload ---------- */
function showHero() {
  state.check = state.explain = state.repair = null;
  $("#hero").hidden = false;
  $("#results").hidden = true;
  $("#chat-log").replaceChildren(el("p", { class: "chat-empty" }, t("chatEmpty")));
  $("#file").value = "";
}

async function checkFile(file) {
  if (!file) return;
  $("#hero").hidden = true;
  $("#results").hidden = false;
  $("#errors").replaceChildren();
  ["#pdf-panel", "#fix-panel"].forEach((s) => ($(s).hidden = true));
  $("#file-name").textContent = file.name;
  $("#verdict").textContent = "";
  $("#verdict-sub").textContent = "";
  const isPdf = /\.(pdf|jpe?g|png)$/i.test(file.name) || /^(application\/pdf|image\/)/.test(file.type);
  const fd = new FormData();
  fd.append("file", file);
  fd.append("lang", state.lang);
  await run(isPdf ? t("readingPdf") : t("checking"), async () => {
    state.check = await api("/api/check", { method: "POST", body: fd });
    state.explain = state.check.explain;
    state.repair = null;
    $("#chat-log").replaceChildren();
    renderResults();
  });
}

/* ---------- results ---------- */
function fatalIssues() {
  return (state.check?.validation.issues || []).filter((i) => i.severity === "fatal");
}

function updateActions() {
  const invalid = state.check && !state.check.validation.valid;
  $("#btn-explain").hidden = !invalid || !state.ai;
  $("#btn-fix").hidden = !invalid || !state.ai;
  // Nothing to export from a file that is not XML at all.
  $("#btn-export").hidden = !state.check
    || state.check.validation.issues.some((i) => i.layer === "parse");
}

function renderResults() {
  const c = state.check;
  if (!c) return;
  $("#source-badge").textContent = c.source;
  const valid = c.validation.valid;
  const n = new Set(fatalIssues().map((i) => `${i.rule_id}|${i.message}`)).size;
  const warn = c.validation.issues.length - fatalIssues().length;
  const v = $("#verdict");
  v.className = `verdict ${valid ? "ok" : "bad"}`;
  const fixed = !valid && state.repair?.final?.valid;
  // replaceChildren would print "null", so only pass real nodes.
  v.replaceChildren(...[el("span", { class: "pill" }, valid ? t("valid") : t("invalid")),
    fixed ? el("span", { class: "pill fixed" }, `✓ ${t("correctedValid")}`) : null].filter(Boolean));
  const suspect = c.pdf?.scan ? (c.pdf.ungrounded || []).length : 0;
  $("#verdict-sub").textContent = (valid ? (suspect ? t("validSubScan", suspect) : t("validSub")) : t("invalidSub", n))
    + (warn ? " " + t("warnings", warn) : "");
  renderPdf();
  renderErrors();
  renderFix();
  updateActions();
}

function renderPdf() {
  const pdf = state.check.pdf;
  $("#pdf-panel").hidden = !pdf;
  if (!pdf) return;
  const f = pdf.fields || {};
  const rows = [
    ["Nr.", f.invoice_number], ["Data", f.issue_date],
    ["Furnizor", `${f.seller?.name ?? ""} (${f.seller?.vat_id ?? ""})`],
    ["Client", `${f.buyer?.name ?? ""} (${f.buyer?.vat_id ?? ""})`],
    ["Total", `${f.totals?.amount_due ?? ""} ${f.currency ?? ""}`],
    ["Lines", (f.lines || []).length],
  ];
  const isScan = !!pdf.scan;
  $("#pdf-panel h3").textContent = isScan ? t("pdfTitleScan") : t("pdfTitle");
  const body = [el("dl", { class: "kv" }, rows.flatMap(([k, val]) => [el("dt", {}, k), el("dd", {}, val ?? "")]))];
  if (pdf.ungrounded?.length) {
    body.push(el("div", { class: "note bad" }, isScan ? t("scanSuspect") : t("ungrounded"),
      el("ul", {}, pdf.ungrounded.map((u) => el("li", {}, `${u.field} = ${u.value}${u.reason ? ` (${u.reason})` : ""}`)))));
  } else {
    body.push(el("p", { class: "note ok" }, isScan ? t("scanOk") : t("pdfOk")));
  }
  // For scans the server's first warning is the "please verify" note, shown translated instead.
  const warnings = (pdf.warnings || []).filter((_, i) => !(isScan && i === 0));
  if (warnings.length) body.push(el("ul", { class: "note" }, warnings.map((w) => el("li", {}, w))));
  if (isScan && /^data:image\/jpeg;base64,/.test(pdf.preview || "")) {
    $("#pdf-body").replaceChildren(el("div", { class: "scan-wrap" },
      el("img", { class: "scan-img", src: pdf.preview, alt: t("scanAlt"), title: t("scanZoom"),
        tabindex: "0", onclick: (e) => e.currentTarget.closest(".scan-wrap").classList.toggle("zoom"),
        onkeydown: (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); e.currentTarget.click(); } } }),
      el("div", {}, el("p", { class: "note" }, t("scanNote")), ...body)));
  } else {
    $("#pdf-body").replaceChildren(...body);
  }
}

function renderErrors() {
  const issues = fatalIssues();
  const byRule = {};
  issues.forEach((i) => ((byRule[i.rule_id] ||= []).push(i)));
  const cards = (state.explain?.explanations || []).map((e) => {
    const loc = (byRule[e.rule_id] || [])[0]?.location;
    const ai = e.source === "model";
    // Official text in the current UI language when ANAF publishes it, else English.
    const official = (state.lang === "ro" ? e.official_ro : e.official_en) || e.official_en || e.official_rule;
    const rows = ai ? [
      [t("whatWrong"), e.what_is_wrong], [t("whyMatters"), e.why_it_matters], [t("howFix"), e.how_to_fix],
      e.fields?.length ? [t("fields"), e.fields.join(", ")] : null,
    ].filter((r) => r && r[1]) : [];
    const extra = [
      ai ? el("p", {}, official) : null,
      e.validator_message && !e.validator_message.includes(e.official_en || "\u0000")
        ? el("p", {}, e.validator_message) : null,
      loc ? el("p", {}, `${t("location")}: `, el("code", {}, loc)) : null,
    ].filter(Boolean);
    return el("article", { class: "card err" },
      el("div", { class: "err-top" },
        el("span", { class: "rule" }, e.rule_id),
        ai ? el("h4", {}, e.title) : null,
        el("span", { class: "src" }, ai ? `✦ ${t("fromAi")}` : t("fromRule"))),
      ai ? el("dl", {}, rows.flatMap(([k, val]) => [el("dt", {}, k), el("dd", {}, val)])) :
        el("p", { class: "official" }, official),
      extra.length ? el("details", {},
        el("summary", {}, ai ? t("official") : t("details")), extra) : null);
  });
  $("#errors").replaceChildren(...cards);
}

function renderDiff(diff) {
  const pre = el("pre", { class: "diff" });
  diff.split("\n").forEach((line) => {
    const cls = line.startsWith("+") && !line.startsWith("+++") ? "add"
      : line.startsWith("-") && !line.startsWith("---") ? "del" : line.startsWith("@@") ? "hunk" : "";
    pre.append(cls ? el("span", { class: cls }, line) : document.createTextNode(line + "\n"));
  });
  return pre;
}

function renderFix() {
  const r = state.repair;
  $("#fix-panel").hidden = !r;
  if (!r) return;
  const remaining = [...new Set((r.final?.issues || []).filter((i) => i.severity === "fatal").map((i) => i.rule_id))];
  const tone = r.status === "fixed" ? "ok" : r.status === "partial" || r.status === "needs_input" ? "" : "bad";
  const body = [
    el("p", { class: `note ${tone}` }, t(`status_${r.status}`)),
    r.summary ? el("p", {}, r.summary) : null,
    el("p", { class: "muted" }, `${t("remaining")}: ${remaining.join(", ") || t("none")}`),
  ];
  if (r.needs_input?.length) {
    const form = el("form", { class: "questions", onsubmit: (ev) => { ev.preventDefault(); doRepair(new FormData(form)); } },
      el("p", { class: "muted" }, t("answerHint")),
      r.needs_input.map((q, i) => el("label", {},
        `${q.field || q.rule_id}: ${q.question}`,
        el("input", { name: q.field || q.rule_id || `q${i}`, required: true }))),
      el("button", { class: "btn-ai", type: "submit" }, t("applyAnswers")));
    body.push(form);
  }
  if (r.diff) {
    body.push(el("h3", {}, t("changes")), renderDiff(r.diff),
      el("a", { class: "btn", href: `/api/download/${state.check.session_id}?which=corrected` }, t("downloadXml")));
  } else {
    body.push(el("p", { class: "muted" }, t("noChanges")));
  }
  $("#fix-body").replaceChildren(...body.filter(Boolean));
}

/* ---------- actions ---------- */
async function doExplain() {
  await run(t("explaining"), async () => {
    state.explain = await post("/api/explain", { session_id: state.check.session_id, lang: state.lang });
    renderErrors();
  });
}

async function doRepair(formData) {
  const answers = {};
  if (formData) for (const [k, v] of formData.entries()) answers[k] = String(v);
  await run(t("fixing"), async () => {
    state.repair = await post("/api/repair", { session_id: state.check.session_id, lang: state.lang, answers });
    renderResults();
    $("#fix-panel").scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

// Export the corrected XML if a fix was applied, otherwise the original (or the XML built from
// a PDF), and say plainly whether it would pass. Sending it to ANAF is up to the user.
function doExport() {
  const r = state.repair;
  const fixed = !!r?.corrected_xml;
  const result = fixed ? r.final : state.check.validation;
  const errors = new Set((result?.issues || []).filter((i) => i.severity === "fatal")
    .map((i) => `${i.rule_id}|${i.message}`)).size;
  window.location.href = `/api/download/${state.check.session_id}?which=final`;
  const suspect = state.check?.pdf?.scan ? (state.check.pdf.ungrounded || []).length : 0;
  if (result?.valid) setStatus(suspect ? t("exportedValidScan", suspect) : t("exportedValid", fixed));
  else setStatus(t("exportedInvalid", fixed, errors), "error");
}

/* ---------- markdown (summary and chat) ---------- */
// Small, safe Markdown renderer: builds DOM nodes from text, never parses HTML.
function renderMarkdown(md, headingOffset = 0) {
  const root = el("div", { class: "md-body" });
  let list = null, listType = "", code = null;
  const inline = (text) => {
    const frag = document.createDocumentFragment();
    text.split(/(\*\*[^*]+\*\*|`[^`]+`|(?<![\w*])\*[^*\s][^*]*\*(?![\w*])|(?<!\w)_[^_\s][^_]*_(?!\w))/g)
      .forEach((part) => {
        if (/^\*\*[^*]+\*\*$/.test(part)) frag.append(el("strong", {}, part.slice(2, -2)));
        else if (/^`[^`]+`$/.test(part)) frag.append(el("code", {}, part.slice(1, -1)));
        else if (/^(\*|_)[^*_].*(\*|_)$/.test(part) && part.length > 2) frag.append(el("em", {}, part.slice(1, -1)));
        else if (part) frag.append(document.createTextNode(part));
      });
    return frag;
  };
  for (const raw of md.replace(/\r/g, "").split("\n")) {
    const line = raw.replace(/\s+$/, "");
    if (line.trimStart().startsWith("```")) {
      if (code) { root.append(code); code = null; } else code = el("pre");
      continue;
    }
    if (code) { code.append(document.createTextNode(raw + "\n")); continue; }
    const item = line.match(/^\s*(?:([-*•])|(\d+)[.)])\s+(.*)$/);
    if (item) {
      const type = item[2] ? "ol" : "ul";
      if (!list || listType !== type) { list = el(type); listType = type; root.append(list); }
      list.append(el("li", {}, inline(item[3])));
      continue;
    }
    if (!line.trim()) { list = null; continue; }  // blank lines end a list
    list = null;
    const h = line.match(/^(#{1,4})\s+(.*)$/);
    if (h) root.append(el(`h${Math.min(h[1].length + headingOffset, 6)}`, {}, inline(h[2])));
    else if (/^(-{3,}|\*{3,})$/.test(line.trim())) root.append(el("hr"));
    else root.append(el("p", {}, inline(line)));
  }
  if (code) root.append(code);
  return root;
}

let summaryText = "";
async function openSummary() {
  await run("", async () => {
    const sid = state.check.session_id;
    summaryText = await api(`/api/summary/${sid}?lang=${state.lang}`);
    // The dialog already has a title, so drop the document's own top heading.
    $("#summary-body").replaceChildren(renderMarkdown(summaryText.replace(/^# .*\n/, "")));
    $("#summary-download").href = `/api/summary/${sid}?lang=${state.lang}&download=true`;
    $("#summary-dialog").showModal();
  });
}

/* ---------- chat ---------- */
function renderChips() {
  $("#chips").replaceChildren(...t("chips").map((q) => el("button", { type: "button", onclick: () => sendChat(q) }, q)));
}

async function sendChat(text) {
  const message = (text ?? $("#chat-input").value).trim();
  if (!message) return;
  const log = $("#chat-log");
  if (!state.check) {
    log.append(el("p", { class: "msg bot" }, t("chatEmpty")));
    return;
  }
  log.querySelector(".chat-empty")?.remove();
  $("#chat-input").value = "";
  log.append(el("p", { class: "msg user" }, message));
  const pending = el("div", { class: "msg bot thinking" }, t("thinking"));
  log.append(pending);
  log.scrollTop = log.scrollHeight;
  try {
    const web = state.search && $("#web-search").checked;
    const r = await post("/api/chat", { session_id: state.check.session_id, message, lang: state.lang, web });
    pending.replaceChildren(renderMarkdown(r.answer, 2));  // chat headings render small
    if (r.uncited?.length) {
      pending.append(el("div", { class: "uncited" },
        el("strong", {}, t("uncitedTitle")),
        el("ul", {}, r.uncited.map((s) => el("li", {}, s)))));
    }
    if (r.sources?.length) pending.append(renderSources(r.sources));
    else if (web && r.search_error) pending.append(el("p", { class: "sources meta" }, t("searchUnavailable")));
  } catch (e) {
    pending.textContent = e.message;
  }
  pending.classList.remove("thinking");
  log.scrollTop = log.scrollHeight;
}

/* ---------- official sources (Tavily) ---------- */
function sourceLink(s, n) {
  const host = (() => { try { return new URL(s.url).hostname; } catch { return ""; } })();
  const safe = /^https:\/\//.test(s.url) ? s.url : "#";
  return el("li", {},
    n ? `[${n}] ` : "",
    el("a", { href: safe, target: "_blank", rel: "noopener noreferrer" }, s.title || host),
    el("span", { class: "meta" }, ` ${host}${s.published_date ? ", " + s.published_date.slice(0, 10) : ""}`));
}

// Show the sources the answer actually cites, numbered as in the answer; the rest are only
// listed under "Also searched", so an unused page never looks like support for the answer.
function renderSources(sources) {
  const n = (s, i) => s.n ?? i + 1;
  const cited = sources.filter((s) => s.cited !== false);
  const other = sources.filter((s) => s.cited === false);
  const wrap = el("div", { class: "sources-wrap" });
  if (cited.length) {
    wrap.append(el("ul", { class: "sources", "aria-label": t("sourcesTitle") },
      cited.map((s, i) => sourceLink(s, n(s, i)))));
  }
  if (other.length) {
    wrap.append(el("details", { class: "sources-other" },
      el("summary", {}, t("alsoSearched", other.length)),
      el("ul", { class: "sources" }, other.map((s, i) => sourceLink(s, n(s, i))))));
  }
  return wrap;
}

async function checkRuleUpdates() {
  const box = $("#rules-result");
  const btn = $("#btn-rules");
  btn.disabled = true;
  box.replaceChildren(el("p", { class: "muted" }, t("checkingRules")));
  try {
    const r = await api("/api/rules/updates");
    box.replaceChildren(
      r.newer_version
        ? el("p", { class: "note bad" }, t("newerFound", r.newer_version))
        : el("p", { class: "note ok" }, t("noNewer", r.checked_at)),
      el("ul", { class: "sources" }, (r.sources || []).slice(0, 3).map((s) => sourceLink(s))));
  } catch (e) {
    box.replaceChildren(el("p", { class: "note bad" }, e.message));
  } finally {
    btn.disabled = false;
  }
}

/* ---------- wiring ---------- */
function wire() {
  const drop = $("#drop"), input = $("#file");
  drop.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); } });
  input.addEventListener("change", () => checkFile(input.files[0]));
  ["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
  ["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
  drop.addEventListener("drop", (e) => checkFile(e.dataTransfer.files[0]));

  document.querySelectorAll(".lang button").forEach((b) => b.addEventListener("click", () => applyLang(b.dataset.lang)));
  document.querySelectorAll("[data-action]").forEach((b) => b.addEventListener("click", () => {
    const a = b.dataset.action;
    if (a === "home") showHero();
    if (a === "samples") $("#sidebar").classList.toggle("open");
    if (a === "chat") $(".app").classList.toggle("chat-hidden");
  }));
  $("#chat-close").addEventListener("click", () => $(".app").classList.add("chat-hidden"));
  $("#btn-explain").addEventListener("click", doExplain);
  $("#btn-fix").addEventListener("click", () => doRepair(null));
  $("#btn-summary").addEventListener("click", openSummary);
  $("#btn-export").addEventListener("click", doExport);
  $("#btn-rules").addEventListener("click", checkRuleUpdates);
  $("#chat-form").addEventListener("submit", (e) => { e.preventDefault(); sendChat(); });

  const dialog = $("#summary-dialog");
  dialog.querySelector("[data-close]").addEventListener("click", () => dialog.close());
  $("#summary-copy").addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(summaryText); setStatus(t("copied")); } catch { /* clipboard blocked */ }
  });
  $("#summary-print").addEventListener("click", () => window.print());
}

async function init() {
  wire();
  if (window.matchMedia("(max-width: 1180px)").matches) $(".app").classList.add("chat-hidden");
  const saved = load("fg-lang");
  applyLang(saved === "ro" ? "ro" : "en");
  try {
    const h = await api("/api/health");
    state.ai = !!h.ai;
    state.search = !!h.search;
    $("#rules-box").hidden = !state.search;
    $("#web-toggle").hidden = !(state.search && state.ai);
  } catch { state.ai = false; }
  try { SAMPLES = await api("/api/samples"); } catch { SAMPLES = []; }
  renderAiStatus();
  renderSamples();
  // ?sample=<key> opens a sample directly (demo links and the demo video).
  const key = new URLSearchParams(location.search).get("sample");
  const sample = SAMPLES.find((s) => s.key === key);
  if (sample) checkSample(sample);
}

init();
