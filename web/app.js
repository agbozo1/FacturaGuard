"use strict";

/* FacturaGuard UI. Plain JS, no build step. All dynamic text goes through textContent. */

const I18N = {
  en: {
    newCheck: "New check", trySample: "Try a sample invoice",
    synthetic: "Synthetic demo data only. Do not upload real client invoices.",
    tagline: "Check your Romanian e-Factura before ANAF does.",
    sub: "Upload a UBL XML or a PDF invoice. We validate it against ANAF's official RO_CIUS rules, explain every error in plain words and propose a corrected XML.",
    drop: "Drop an invoice here, or browse (XML or PDF, max 5 MB)",
    p1t: "Official rules", p1: "ANAF CIUS-RO 1.0.9 Schematron and UBL 2.1, cross-checked with ANAF's own validator.",
    p2t: "Plain explanations", p2: "NVIDIA Nemotron explains each error in English or Romanian, grounded in the official rule text.",
    p3t: "Checked fixes", p3: "Every proposed fix is re-validated. Missing business facts are asked, never invented.",
    explainAi: "Explain with AI", fix: "Propose a fix", share: "Share with accountant",
    submit: "Submit to ANAF (mock)", pdfTitle: "Read from the PDF", fixTitle: "Proposed correction",
    submitTitle: "Mock ANAF submission", assistant: "AI Assistant",
    chatEmpty: "Check an invoice, then ask me anything about its errors.",
    ask: "Ask about this invoice", summaryTitle: "Summary for your accountant",
    copy: "Copy text", download: "Download .md", print: "Print or save as PDF",
    aiOn: "AI connected (NVIDIA Nemotron on Nebius)", aiOff: "Validation only (AI not configured)",
    checking: "Checking the invoice...", readingPdf: "Reading the PDF with Nemotron and checking it...",
    explaining: "Nemotron is explaining the errors...", fixing: "Nemotron is proposing a fix; every change is re-validated...",
    submitting: "Simulating the ANAF upload...", valid: "Valid", invalid: "Invalid",
    validSub: "Passes ANAF's RO_CIUS 1.0.9 checks. Ready to send.",
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
    submitOk: "accepted", submitNok: "rejected", copied: "Copied.", correctedValid: "Corrected version is valid",
    chips: ["Why would ANAF reject this?", "What should I ask my accountant?", "Which fields do I need to fill in?"],
    errNoAi: "AI features are not configured on this server. Validation still works.",
    thinking: "Thinking...", mockNote: "Simulation only. Nothing was sent to ANAF.",
    rulesVersion: "Rules: ANAF CIUS-RO 1.0.9", checkUpdates: "Check ANAF for updates",
    checkingRules: "Searching official sources...",
    newerFound: (v) => `ANAF sources mention CIUS-RO ${v}, newer than the 1.0.9 rules used here. Results may be out of date; check before relying on them.`,
    noNewer: (when) => `No newer CIUS-RO version found in official sources (checked ${when}).`,
    officialSources: "Search official sources (ANAF, MF, legislatie.just.ro)",
    sourcesTitle: "Official sources", searchUnavailable: "Official-source search was unavailable for this answer.",
    uncitedTitle: "Not from a cited source, please verify:",
    productOf: "© 2026 Product of Nova Analytica S.R.L.", license: "Source code (AGPL-3.0)",
  },
  ro: {
    newCheck: "Verificare nouă", trySample: "Încearcă o factură exemplu",
    synthetic: "Doar date sintetice de demonstrație. Nu încărcați facturi reale ale clienților.",
    tagline: "Verifică-ți e-Factura înainte s-o verifice ANAF.",
    sub: "Încarcă o factură UBL XML sau PDF. O validăm după regulile oficiale RO_CIUS ale ANAF, explicăm fiecare eroare pe înțeles și propunem un XML corectat.",
    drop: "Trage factura aici sau alege fișierul (XML sau PDF, max. 5 MB)",
    p1t: "Reguli oficiale", p1: "Schematron ANAF CIUS-RO 1.0.9 și UBL 2.1, verificate încrucișat cu validatorul ANAF.",
    p2t: "Explicații clare", p2: "NVIDIA Nemotron explică fiecare eroare în română sau engleză, pe baza textului oficial al regulii.",
    p3t: "Corecturi verificate", p3: "Fiecare corectură propusă este revalidată. Datele firmei care lipsesc sunt cerute, nu inventate.",
    explainAi: "Explică cu AI", fix: "Propune o corectură", share: "Trimite contabilului",
    submit: "Trimite la ANAF (simulare)", pdfTitle: "Citit din PDF", fixTitle: "Corectură propusă",
    submitTitle: "Trimitere ANAF simulată", assistant: "Asistent AI",
    chatEmpty: "Verifică o factură, apoi întreabă-mă orice despre erorile ei.",
    ask: "Întreabă despre această factură", summaryTitle: "Rezumat pentru contabil",
    copy: "Copiază textul", download: "Descarcă .md", print: "Tipărește sau salvează PDF",
    aiOn: "AI conectat (NVIDIA Nemotron pe Nebius)", aiOff: "Doar validare (AI neconfigurat)",
    checking: "Se verifică factura...", readingPdf: "Nemotron citește PDF-ul și îl verificăm...",
    explaining: "Nemotron explică erorile...", fixing: "Nemotron propune o corectură; fiecare modificare este revalidată...",
    submitting: "Se simulează încărcarea la ANAF...", valid: "Validă", invalid: "Invalidă",
    validSub: "Trece verificările RO_CIUS 1.0.9 ale ANAF. Gata de trimis.",
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
    submitOk: "acceptată", submitNok: "respinsă", copied: "Copiat.", correctedValid: "Versiunea corectată este validă",
    chips: ["De ce ar respinge ANAF factura?", "Ce să-l întreb pe contabil?", "Ce câmpuri trebuie să completez?"],
    errNoAi: "Funcțiile AI nu sunt configurate pe acest server. Validarea funcționează.",
    thinking: "Mă gândesc...", mockNote: "Doar simulare. Nimic nu a fost trimis la ANAF.",
    rulesVersion: "Reguli: ANAF CIUS-RO 1.0.9", checkUpdates: "Verifică actualizări ANAF",
    checkingRules: "Se caută în surse oficiale...",
    newerFound: (v) => `Sursele ANAF menționează CIUS-RO ${v}, mai nou decât regulile 1.0.9 folosite aici. Rezultatele pot fi depășite; verificați înainte de a vă baza pe ele.`,
    noNewer: (when) => `Nu s-a găsit o versiune CIUS-RO mai nouă în sursele oficiale (verificat ${when}).`,
    officialSources: "Caută în surse oficiale (ANAF, MF, legislatie.just.ro)",
    sourcesTitle: "Surse oficiale", searchUnavailable: "Căutarea în surse oficiale nu a fost disponibilă pentru acest răspuns.",
    uncitedTitle: "Nu provine dintr-o sursă citată, vă rugăm verificați:",
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
  ["#pdf-panel", "#fix-panel", "#submit-panel"].forEach((s) => ($(s).hidden = true));
  $("#file-name").textContent = file.name;
  $("#verdict").textContent = "";
  $("#verdict-sub").textContent = "";
  const isPdf = file.name.toLowerCase().endsWith(".pdf") || file.type === "application/pdf";
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
  $("#verdict-sub").textContent = (valid ? t("validSub") : t("invalidSub", n)) + (warn ? " " + t("warnings", warn) : "");
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
  const body = [el("dl", { class: "kv" }, rows.flatMap(([k, val]) => [el("dt", {}, k), el("dd", {}, val ?? "")]))];
  if (pdf.ungrounded?.length) {
    body.push(el("div", { class: "note bad" }, t("ungrounded"),
      el("ul", {}, pdf.ungrounded.map((u) => el("li", {}, `${u.field} = ${u.value}`)))));
  } else {
    body.push(el("p", { class: "note ok" }, t("pdfOk")));
  }
  if (pdf.warnings?.length) body.push(el("ul", { class: "note" }, pdf.warnings.map((w) => el("li", {}, w))));
  $("#pdf-body").replaceChildren(...body);
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

async function doSubmit() {
  await run(t("submitting"), async () => {
    const r = await post("/api/submit", { session_id: state.check.session_id });
    $("#submit-panel").hidden = false;
    const ok = r.status === "ok";
    $("#submit-body").replaceChildren(...[
      el("p", { class: `note ${ok ? "ok" : "bad"}` }, `${r.status}: ${ok ? t("submitOk") : t("submitNok")}`),
      el("p", {}, r.message),
      r.errors?.length ? el("p", { class: "muted" }, r.errors.join(", ")) : null,
      el("p", { class: "muted" }, `Index: ${r.upload_index}. ${t("mockNote")}`)].filter(Boolean));
  });
}

/* ---------- summary ---------- */
function renderMarkdown(md) {
  const root = el("div");
  let list = null, code = null;
  const inline = (text) => {
    const frag = document.createDocumentFragment();
    text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).forEach((part) => {
      if (/^\*\*[^*]+\*\*$/.test(part)) frag.append(el("strong", {}, part.slice(2, -2)));
      else if (/^`[^`]+`$/.test(part)) frag.append(el("code", {}, part.slice(1, -1)));
      else if (part) frag.append(document.createTextNode(part));
    });
    return frag;
  };
  for (const line of md.split("\n")) {
    if (line.startsWith("```")) {
      if (code) { root.append(code); code = null; } else code = el("pre");
      continue;
    }
    if (code) { code.append(document.createTextNode(line + "\n")); continue; }
    if (/^- /.test(line)) {
      if (!list) { list = el("ul"); root.append(list); }
      list.append(el("li", {}, inline(line.slice(2))));
      continue;
    }
    list = null;
    const h = line.match(/^(#{1,3}) (.*)$/);
    if (h) root.append(el(`h${h[1].length}`, {}, h[2]));
    else if (line === "---") root.append(el("hr"));
    else if (/^_.*_$/.test(line)) root.append(el("p", {}, el("em", {}, line.slice(1, -1))));
    else if (line.trim()) root.append(el("p", {}, inline(line)));
  }
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
  const pending = el("p", { class: "msg bot thinking" }, t("thinking"));
  log.append(pending);
  log.scrollTop = log.scrollHeight;
  try {
    const web = state.search && $("#web-search").checked;
    const r = await post("/api/chat", { session_id: state.check.session_id, message, lang: state.lang, web });
    pending.textContent = r.answer;
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

function renderSources(sources) {
  return el("ul", { class: "sources", "aria-label": t("sourcesTitle") },
    sources.map((s, i) => sourceLink(s, i + 1)));
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
  $("#btn-submit").addEventListener("click", doSubmit);
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
