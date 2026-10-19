// @ts-check
/* hubLib.js (#221 H1): the Reporting hub's plain helpers, no DOM. The status words on each report, the weeks in the week menu, the
   Friday a typed date falls in, and what Export and Approve offer. */
import { wkTone } from "../weekly/weeklyDoc.js";

/** @typedef {import("../Sheet.jsx").SheetDoc} SheetDoc */
/** @typedef {{key: string, label: string}} Status */
/** @typedef {{week: string, tone: string, internal: string, client: string, current: boolean}} WeekRow */

/** The quiet label on the internal report: "Draft" or "Approved". @param {SheetDoc|null} doc @returns {Status} */
export function internalStatus(doc) {
  if (doc && doc.state === "approved") return { key: "approved", label: "Approved" };
  return { key: "draft", label: "Draft" };
}

/** The quiet label on the client report: it waits for the internal report, is a draft, or is approved.
    @param {SheetDoc|null} doc @param {{ready: boolean}|null} info @returns {Status} */
export function clientStatus(doc, info) {
  if (doc && doc.state === "approved") return { key: "approved", label: "Approved" };
  if (!info || !info.ready) return { key: "waits", label: "Waits for the internal report" };
  return { key: "draft", label: "Draft" };
}

/** The Friday (the report day) that ends the week a date falls in. `day` is the report day's index, 0 = Monday.
    @param {string} iso YYYY-MM-DD @param {number} [day] @returns {string} YYYY-MM-DD, or "" for a date that is not one */
export function weekEndingFor(iso, day = 4) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso || "")) return "";
  const t = Date.parse(iso);
  if (!Number.isFinite(t)) return "";
  const wd = (new Date(t).getUTCDay() + 6) % 7;
  return new Date(t + ((day - wd + 7) % 7) * 864e5).toISOString().slice(0, 10);
}

/** The health tone of each week the document knows: its six-week trend, and this week's own flag.
    @param {SheetDoc|null} doc @returns {Record<string, string>} week -> g|a|r|n */
export function toneByWeek(doc) {
  /** @type {Record<string, string>} */
  const out = {};
  const h = doc && doc.sections.find(s => s.id === "health");
  const d = (h && h.data) || {};
  for (const t of d.trend || []) if (t && t.date) out[t.date] = wkTone(t.flag);
  if (doc && h) out[doc.date] = wkTone(d.flag);
  return out;
}

/** The health tone of each week in the project's six-week trail (the bars on the Portfolio): ok, warn and bad become g, a and r; a week
    with no update is left out, so its dot stays neutral. @param {any} p the project, or undefined @returns {Record<string, string>} week -> g|a|r */
export function toneByTrail(p) {
  /** @type {Record<string, string>} */
  const out = {}, M = /** @type {Record<string, string>} */ ({ ok: "g", warn: "a", bad: "r" });
  const t = (p && p.trail) || [], e = (p && p.trailend) || [];
  t.forEach((/** @type {string} */ x, /** @type {number} */ i) => { if (e[i] && M[x]) out[e[i]] = M[x]; });
  return out;
}

/** The weeks the menu lists, newest first: the project's weeks (this week, the three before, any with a filed report) and the one
    on screen. @param {string[]} weeks @param {string} shown @returns {string[]} */
export function menuWeeks(weeks, shown) {
  return [...new Set([...weeks, ...(shown ? [shown] : [])])].sort().reverse();
}

/** The export formats the Export menu offers (one line each). */
export const EXPORT_FORMATS = [
  { id: "html", name: "HTML", line: "A web page you can open anywhere", icon: "filetext" },
  { id: "docx", name: "Word (.docx)", line: "The firm's template, to send", icon: "filetext" },
  { id: "pdf", name: "PDF", line: "Printed from the page", icon: "filetext" },
];

/** The question after the format, when the project has a client report. */
export const EXPORT_WHICH = [
  { id: "internal", name: "The internal report", line: "For you and the team" },
  { id: "client", name: "The client report", line: "Checked for anything the client mustn't see" },
  { id: "both", name: "Both", line: "Two files, each with its own name" },
];
