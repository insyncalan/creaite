// @ts-check
/* #238 Activity › Usage: what each Claude run costs and what every run loads before it starts. Read only: D.usage is worked
   out when the page is built (usage_report.page, context_size.table, usage_reviews.load). The one write is Alan's own review
   note, POST /api/usage/review. Counts, dates and his notes only; tokens are estimates. Built with DOM nodes, never HTML text. */
import { $ } from "./core/dom.js";
import { D, fd, TODAY } from "./core/page.js";
import { api } from "./core/server.js";

export const U_KINDS = { ask: "ask creaite", sweep: "Sweep", generate: "Generate current state", prep: "Prep page",
  check: "Transcript check", load: "Transcript load", draft: "Drafts", vip: "VIP check" };
export const U_FILES = { rules: "Rules (creaite-rules.md)", claude_md: "Your CLAUDE.md", memory: "Project memory and registers",
  skills: "Skill names and descriptions" };
const SVG = "http://www.w3.org/2000/svg";

export const uNum = (/** @type {number} */ n) => Math.round(n || 0).toLocaleString("en-GB");
export const uMoney = (/** @type {number} */ n) => `$${(n || 0).toFixed(2)}`;
export const uKB = (/** @type {number} */ b) => `${(b / 1024).toFixed(1)} KB`;
/** "+12% on last week", or "no runs last week to compare" @param {number|null|undefined} p */
export const uPct = p => p === null || p === undefined ? "nothing last week to compare" : `${p > 0 ? "+" : p < 0 ? "−" : ""}${Math.abs(p)}% on last week`;

/** @param {HTMLElement} tr @param {string} text @param {string} [cls] */
function uCell(tr, text, cls) { const td = document.createElement("td"); td.textContent = text; if (cls) td.className = cls; tr.append(td); return td; }
/** @param {string} id @param {string[][]} tableRows @param {number} cols @param {string} none */
function rowsInto(id, tableRows, cols, none) {
  const body = $(id); body.replaceChildren();
  if (!tableRows.length) { const tr = document.createElement("tr"); const td = uCell(tr, none, "empty"); td.colSpan = cols; body.append(tr); return; }
  tableRows.forEach(r => { const tr = document.createElement("tr"); r.forEach(c => uCell(tr, c)); body.append(tr); });
}

/** The four cards: cost, runs, start load and the average run, each with its change on the week before. */
export function uCards(c) {
  const w = c.week || {}, ch = c.change || {};
  const st = ch.start_tokens === null || ch.start_tokens === undefined ? "nothing last week to compare"
    : `${ch.start_tokens > 0 ? "+" : ch.start_tokens < 0 ? "−" : ""}${uNum(Math.abs(ch.start_tokens))} on last week`;
  return [[uMoney(w.cost_usd), "Cost this week", uPct(ch.cost_pct)], [uNum(w.runs), "Runs this week", uPct(ch.runs_pct)],
    [w.start_median ? uNum(w.start_median) : "—", "Tokens a run loads before it starts (about)", st],
    [uMoney(w.avg_cost_usd), "Cost of an average run", uPct(ch.avg_cost_pct)]];
}
function drawCards(c) {
  const host = $("#uSum"); host.replaceChildren();
  uCards(c).forEach(([v, l, d]) => { const box = document.createElement("div"); box.className = "ucard";
    [["v", v], ["l", l], ["d", d]].forEach(([k, t]) => { const e = document.createElement("div"); e.className = k; e.textContent = t; box.append(e); });
    host.append(box); });
}

/** @param {string} tag @param {Record<string, string|number>} at @param {string} [title] */
function sv(tag, at, title) { const e = document.createElementNS(SVG, tag); Object.entries(at).forEach(([k, v]) => e.setAttribute(k, String(v)));
  if (title) { const t = document.createElementNS(SVG, "title"); t.textContent = title; e.append(t); } return e; }
/** A nice top for an axis: 1, 2 or 5 times a power of ten. @param {number} v */
export function uTop(v) { if (!(v > 0)) return 1; const p = 10 ** Math.floor(Math.log10(v)); return [1, 2, 5, 10].map(m => m * p).find(t => t >= v) || 10 * p; }
const U_L = 54, U_R = 8;
/** One panel: bars (cost) or a line (start load), its own y axis from 0, three grid lines, the days under the last one.
    Drawn at the card's own width in pixels, so the text stays at its token size. */
function panel(perDay, key, opts) {
  const W = opts.w, H = opts.h, B = opts.labels ? 22 : 6, T = 26, n = perDay.length, bw = (W - U_L - U_R) / n;
  const vals = perDay.map(d => d[key]), top = uTop(Math.max(0, ...vals.filter(v => v !== null)));
  const y = v => H - B - (H - B - T) * v / top, svg = sv("svg", { viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: "img", "aria-label": opts.aria });
  const head = sv("text", { class: "uglab", x: 0, y: 12 }); head.textContent = opts.title; svg.append(head);
  [0, top / 2, top].forEach(g => { svg.append(sv("line", { class: "ugrid", x1: U_L, x2: W - U_R, y1: y(g), y2: y(g) }));
    const t = sv("text", { class: "ax", x: U_L - 6, y: y(g) + 4, "text-anchor": "end" }); t.textContent = opts.tick(g); svg.append(t); });
  const pts = [];
  perDay.forEach((d, i) => { const cx = U_L + i * bw + bw / 2, v = d[key], tip = `${fd(d.day)}: ${v === null ? "no runs" : opts.tip(v)}`;
    if (opts.bars) { const h = Math.max(0, H - B - y(v || 0)); svg.append(sv("rect", { class: "ubar", x: cx - bw * 0.3, y: H - B - h, width: bw * 0.6, height: h, rx: 2 }, tip)); }
    else if (v !== null) pts.push([cx, y(v), tip]);
    svg.append(sv("rect", { class: "uhit", x: cx - bw / 2, y: T, width: bw, height: H - B - T }, tip));
    if (opts.labels && i % 2 === n % 2) { const t = sv("text", { class: "ax", x: cx, y: H - 6, "text-anchor": "middle" }); t.textContent = fd(d.day).slice(0, 5); svg.append(t); } });
  if (pts.length) { svg.append(sv("polyline", { class: "uline", points: pts.map(p => `${p[0]},${p[1]}`).join(" ") }));
    pts.forEach(p => svg.append(sv("circle", { class: "udot", cx: p[0], cy: p[1], r: 4 }, p[2]))); }
  return svg;
}
function drawChart(perDay) {
  const host = $("#uChart"), w = Math.max(360, Math.floor(host.clientWidth || 760));
  host.replaceChildren(
    panel(perDay, "cost_usd", { w, h: 140, bars: true, title: "Cost per day", aria: "Cost per day, last 14 days", tick: g => `$${g.toFixed(g < 1 && g > 0 ? 2 : 0)}`, tip: uMoney }),
    panel(perDay, "start_median", { w, h: 120, labels: true, title: "Median tokens loaded at start (about)", aria: "Median start load per run, last 14 days",
      tick: g => g >= 1000 ? `${Math.round(g / 1000)}k` : String(Math.round(g)), tip: v => `about ${uNum(v)} tokens` }));
}

/** @param {any} k */
export const uKindRow = k => [U_KINDS[k.kind] || k.kind, uNum(k.runs), uNum(k.avg_tokens), k.start_median ? uNum(k.start_median) : "—",
  uMoney(k.cost_usd), `${Math.round((k.share || 0) * 100)}%`];
/** "+2.0 KB since 12-10-2026", "no change", or "first measured today" @param {any} c */
export function uChange(c) {
  if (c.change_bytes === null || c.change_bytes === undefined) return "no earlier measure yet";
  if (!c.change_bytes) return "no change";
  return `${c.change_bytes > 0 ? "+" : "−"}${uKB(Math.abs(c.change_bytes))}${c.changed_on ? ` since ${fd(c.changed_on)}` : ""}`;
}
/** @param {any} s */
export function uLast(s) {
  if (s.days_since === null || s.days_since === undefined) return "never used";
  const ago = s.days_since === 0 ? "today" : s.days_since === 1 ? "yesterday" : `${s.days_since} days ago`;
  return s.never_in_period ? `never in this period (last ${ago})` : ago;
}
function drawSkills(list) {
  rowsInto("#uSkill", list.map(s => [s.skill, uNum(s.runs), uMoney(s.cost_usd), uLast(s)]), 4, "No skills found.");
  $("#uSkill").querySelectorAll("tr").forEach((tr, i) => { if (list[i] && list[i].never_in_period) tr.lastElementChild?.classList.add("unever"); });
}
function drawContext(ctx, cards) {
  rowsInto("#uCtx", ctx.map(c => [U_FILES[c.file] || c.file, uKB(c.bytes), uNum(c.tokens), uChange(c)]), 4, "Nothing measured yet.");
  const total = ctx.reduce((a, c) => a + (c.tokens || 0), 0), note = $("#uCtxNote"), start = (cards.week || {}).start_median;
  note.hidden = !total; note.replaceChildren();
  const b = document.createElement("b"); b.textContent = "Why this matters: ";
  note.append(b, `these files come to about ${uNum(total)} tokens${start ? `, and a run this week loaded about ${uNum(start)} before doing anything` : ""}. ` +
    "Trimming the rules file, or loading its detail only when a skill needs it, would lower the cost of every run.");
}
export function drawReviews(list) {
  rowsInto("#uRev", list.slice().reverse().map(r => [fd(r.date), r.saw, r.decided]), 3, "No review notes yet.");
}

/** Draw the whole tab from D.usage. */
export function renderUsage() {
  const u = D.usage || {}, err = $("#uErr");
  err.hidden = !u.error; err.textContent = u.error ? `Usage couldn't be counted (${u.error}).` : "";
  if (u.error) return;
  const empty = !!u.empty || !u.runs && !(u.daily || []).some(d => d.runs);
  $("#uEmpty").hidden = !empty; $("#uRuns").hidden = empty; $("#uRuns2").hidden = empty;
  if (!empty) { drawCards(u.cards || {}); drawChart(u.daily || []); rowsInto("#uKind", (u.kinds || []).map(uKindRow), 6, "No runs in this period."); drawSkills(u.skills || []); }
  drawContext(u.context || [], u.cards || {}); drawReviews(u.reviews || []);
}

/** The review notes as CSV (date as DD-MM-YYYY), each field quoted. @param {any[]} list */
export function uCsv(list) {
  const q = s => `"${String(s ?? "").replace(/"/g, '""')}"`;
  return ["Date,What you saw,What you decided", ...list.map(r => [fd(r.date), r.saw, r.decided].map(q).join(","))].join("\r\n") + "\r\n";
}
function downloadCsv() {
  const a = document.createElement("a"), u = URL.createObjectURL(new Blob([uCsv((D.usage || {}).reviews || [])], { type: "text/csv" }));
  a.href = u; a.download = "creaite usage reviews.csv"; document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(u), 1000);
}
function formOpen(on) {
  $("#uRevForm").hidden = !on; $("#uRevAdd").hidden = on; $("#uRevMsg").textContent = "";
  if (on) { $("#uRevDate").value = TODAY; $("#uRevSaw").value = ""; $("#uRevDec").value = ""; $("#uRevSaw").focus(); }
}
async function saveReview() {
  const r = await api("/api/usage/review", { date: $("#uRevDate").value, saw: $("#uRevSaw").value, decided: $("#uRevDec").value });
  if (!r || !r.ok) { $("#uRevMsg").textContent = r && /not found/i.test(r.message || "") ? "Saving a review note needs the live server's next update." : (r && r.message) || "Not saved."; return; }
  D.usage = { ...(D.usage || {}), reviews: r.reviews || [] }; drawReviews(D.usage.reviews); formOpen(false); $("#uRevAdd").focus();
}
/* BL-231: what this block does at load, run by src/main.js */
export function bootUsage() {
  $("#uRevAdd").addEventListener("click", () => formOpen(true));
  $("#uRevCancel").addEventListener("click", () => { formOpen(false); $("#uRevAdd").focus(); });
  $("#uRevSave").addEventListener("click", () => { saveReview(); });
  $("#uRevForm").addEventListener("keydown", e => { if (e.key === "Enter" && e.target instanceof HTMLInputElement) { e.preventDefault(); saveReview(); }
    if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); formOpen(false); $("#uRevAdd").focus(); } });
  $("#uRevCsv").addEventListener("click", downloadCsv);
  let wait = 0;
  window.addEventListener("resize", () => { clearTimeout(wait); wait = window.setTimeout(() => { if (!$("#actUsage").hidden && !$("#uRuns").hidden) drawChart((D.usage || {}).daily || []); }, 150); });
}
