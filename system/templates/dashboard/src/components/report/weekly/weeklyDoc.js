// @ts-check
/* weeklyDoc.js (v2.1.0 P6, BL-335): the weekly report view's plain helpers: dates as the page writes them, the small Markdown the
   sheet shows, health tones, milestone states and the changes the sections make to the document (a section and the layout
   together, as the sheet's contract §4.1 asks, so P3's remember_layout gets a consistent layout). No DOM here. */

/** @typedef {import("../SheetStub.jsx").SheetDoc} SheetDoc */
/** @typedef {import("../SheetStub.jsx").SheetSection} SheetSection */

const WK_DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const WK_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const DAY = /^(\d{4})-(\d{2})-(\d{2})/;

/** Days since 1970 for a YYYY-MM-DD. @param {string} iso */
export const dayNo = iso => { const m = DAY.exec(iso || ""); return m ? Date.UTC(+m[1], +m[2] - 1, +m[3]) / 864e5 : NaN; };
/** DD-MM-YYYY for a stored date (else the words as they are). @param {string|null|undefined} iso */
export const wkDmy = iso => { const m = DAY.exec(iso || ""); return m ? `${m[3]}-${m[2]}-${m[1]}` : String(iso || ""); };
/** DD-MM for a stored date. @param {string} iso */
export const wkDm = iso => { const m = DAY.exec(iso || ""); return m ? `${m[3]}-${m[2]}` : ""; };
/** "Friday 16 October 2026". @param {string} iso */
export function wkLongDate(iso) {
  const m = DAY.exec(iso || ""); if (!m) return String(iso || "");
  const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
  return `${WK_DAYS[d.getUTCDay()]} ${+m[3]} ${WK_MONTHS[+m[2] - 1]} ${m[1]}`;
}
/** Today as YYYY-MM-DD in the page's own clock. */
export const todayIso = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; };

/** The wkTone a health flag is drawn in: g (on track), a (at risk), r (off track), n (not set). @param {string|null|undefined} flag */
export const wkTone = flag => /off/i.test(flag || "") ? "r" : /risk/i.test(flag || "") ? "a" : /on track|achieved/i.test(flag || "") ? "g" : "n";

/** One block of the small Markdown the sheet shows: paragraphs, "- " bullets, **bold**, *italic*.
    @typedef {{t: "p"|"ul", lines: string[]}} MdBlock
    @param {string|null|undefined} text @returns {MdBlock[]} */
export function wkMdBlocks(text) {
  /** @type {MdBlock[]} */ const out = [];
  for (const src of String(text || "").split(/\n/)) {
    const line = src.trimEnd(); if (!line.trim()) { out.push({ t: "p", lines: [] }); continue; }
    const b = /^\s*[-*]\s+(.*)$/.exec(line);
    const last = out[out.length - 1];
    if (b) { if (last && last.t === "ul") last.lines.push(b[1]); else out.push({ t: "ul", lines: [b[1]] }); }
    else if (last && last.t === "p") last.lines.push(line.trim());
    else out.push({ t: "p", lines: [line.trim()] });
  }
  return out.filter(b => b.lines.length);
}

/** A line's inline marks as parts: {s, b?, i?}. @param {string} line @returns {{s: string, b?: boolean, i?: boolean}[]} */
export function inline(line) {
  /** @type {{s: string, b?: boolean, i?: boolean}[]} */ const parts = [];
  let at = 0;
  for (const m of line.matchAll(/\*\*([^*]+)\*\*|\*([^*]+)\*/g)) {
    if (m.index > at) parts.push({ s: line.slice(at, m.index) });
    parts.push(m[1] ? { s: m[1], b: true } : { s: m[2], i: true }); at = m.index + m[0].length;
  }
  if (at < line.length) parts.push({ s: line.slice(at) });
  return parts;
}

/** A milestone's state for the list and the timeline: its own state when Alan set one, else worked out from its dates.
    @param {any} m a milestone item @returns {{word: string, tone: string}} */
export function wkMsState(m) {
  const st = m.state, fc = m.forecast_date || m.baseline_date, base = m.baseline_date;
  if (m.status === "Done" || st === "Achieved") return { word: "ACHIEVED", tone: "g" };
  if (m.status === "Cancelled") return { word: "CANCELLED", tone: "n" };
  if (st === "Overdue") return { word: "OVERDUE", tone: "r" };
  if (st === "Slipped" || (fc && base && dayNo(fc) > dayNo(base))) return { word: "SLIPPED", tone: "a" };
  if (st === "At risk") return { word: "AT RISK", tone: "a" };
  return { word: "ON TRACK", tone: "g" };
}

/** Days a date is past another (a whole number, never below 0). @param {string} due @param {string} on */
export const daysLate = (due, on) => Math.max(0, Math.round(dayNo(on) - dayNo(due)));

/** The same document with one section changed (and, with `layout`, the layout merged).
    @param {SheetDoc} doc @param {string} id @param {Partial<SheetSection>|((s: SheetSection) => Partial<SheetSection>)} patch
    @param {Record<string, any>} [layout] @returns {SheetDoc} */
export function withSection(doc, id, patch, layout) {
  const sections = doc.sections.map(s => s.id === id ? { ...s, ...(typeof patch === "function" ? patch(s) : patch) } : s);
  return { ...doc, sections, layout: layout ? { ...(doc.layout || {}), ...layout } : doc.layout };
}

/** The cells of a row that was hidden and kept only its reference, made again from the item as it stood (ID, words, priority,
    owner, due). @param {string} sid @param {any} item @param {string} on the report's date */
export function cellsFromItem(sid, item, on) {
  if (!item) return {};
  const t = item.title || item.description || "";
  if (sid === "risks") return { id: item.id, risk: `${item.type || "Risk"}: ${t}`, priority: item.priority || "", owner: item.owner || "" };
  if (sid === "overdue") return { id: item.id, action: t, owner: item.owner || "", due: wkDmy(item.due_date) };
  if (sid === "decisions") return { decision: t, by: item.made_by || "", date: wkDmy(item.date), source: "" };
  return { id: item.id, title: t, on };
}
