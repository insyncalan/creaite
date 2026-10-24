// @ts-check
/* minutesDoc.js (v2.1.0 P7, BL-338): plain functions over the minutes record (the creaite-doc data block, kind "minutes"), shared
   by the minutes view's parts. No drawing, no server.
   - mdLines(text): a section's Markdown as lines ({kind: "topic" | "bullet" | "para", text, flag}), for drawing each with its tag;
   - lineTag(line, tags): the time tag P4 gave that line (`{ref: "transcript", turn, time, text}`);
   - checksOf(doc, turns, people): the checks against the transcript and the record (§4.5's shape), worked out here in plain
     code (no model): an owner whose record needs details (#266), an action with no owner, a deadline that isn't what was said,
     a figure the transcript doesn't say, an item your project record's checks refused;
   - distributedOf(doc): the distributed version (BL-338 point 13) as the page shows it: the internal record without the lines
     and rows marked Internal only (`layout.internal_only`) and without withheld items (Sensitive, partner-only or labelled to
     exclude: the item's own flags and the route's `withheld`, from its labels). minutes_record.distributed_of makes the same
     record on the server for /api/minutes/export with version "distributed"; this is the view's preview of it. */
import { deadlineOf, deadlineDay } from "./DeadlinePopover.jsx";
import { fd } from "../../core/page.js";

/** @typedef {import("../report/Sheet.jsx").SheetDoc} SheetDoc */
/** @typedef {import("../report/Sheet.jsx").SheetSection} SheetSection */
/** @typedef {{kind: "topic"|"bullet"|"para", text: string, flag: string}} Line */
/** @typedef {{ref: string, turn?: number, time?: string, text: string}} TimeTag */
/** @typedef {{id: string, section: string, row?: number, line?: number, field?: string, quote: string, note: string,
    last?: string, kind: string, n?: number, turn?: number, words?: string, actions: {id: string, label: string}[]}} Check */

const FLAGS = ["PRIORITY", "ACTION", "FLAG", "BLOCKED", "SUPPORT NEEDED", "NEW SCOPE", "NEW", "ON TRACK", "HIGH RISK", "DONE"];
const unbold = (/** @type {string} */ s) => s.replace(/\*\*([^*]+)\*\*/g, "$1").replace(/\*([^*]+)\*/g, "$1");

/** A section's Markdown as lines. @param {string} text @returns {Line[]} */
export function mdLines(text) {
  /** @type {Line[]} */
  const out = [];
  for (const rawLine of String(text || "").split("\n")) {
    const s = rawLine.trim();
    if (!s) continue;
    const topic = /^\*\*([^*]+)\*\*$/.exec(s);
    if (topic) { out.push({ kind: "topic", text: topic[1], flag: "" }); continue; }
    const b = /^[-*] (.*)$/.exec(s), body = b ? b[1] : s;
    const f = /^\*\*([A-Z ]+)\*\* (.*)$/.exec(body);
    const flag = f && FLAGS.includes(f[1]) ? f[1] : "";
    out.push({ kind: b ? "bullet" : "para", text: unbold(flag && f ? f[2] : body), flag });
  }
  return out;
}

/** Lines back to Markdown, after one changed. @param {Line[]} ls */
export function mdUnlines(ls) {
  const out = [];
  ls.forEach((l, i) => {
    if (l.kind === "topic") { if (i) out.push(""); out.push(`**${l.text}**`); }
    else if (l.kind === "bullet") out.push(`- ${l.flag ? `**${l.flag}** ` : ""}${l.text}`);
    else { if (i) out.push(""); out.push(`${l.flag ? `**${l.flag}** ` : ""}${l.text}`); }
  });
  return out.join("\n");
}

const squash = (/** @type {string} */ s) => String(s || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();

/** The time tag for a line: the tag whose words are the line's (or start it). @param {Line} line @param {TimeTag[]} tags */
export function lineTag(line, tags) {
  const l = squash(line.text);
  return (tags || []).find(t => t.ref === "transcript" && t.time && (squash(t.text) === l || (l && squash(t.text).startsWith(l)) || (l && l.startsWith(squash(t.text))))) || null;
}

/** Whether a staged item is Sensitive (never in the distributed version). @param {any} item */
export const sensitive = item => !!item && (((item.flags || []).some((/** @type {string} */ f) => /sensitive/i.test(f))) ||
  ((item.values || {}).labels || []).some((/** @type {string} */ l) => /sensitive/i.test(l)) || !!(item.values || {}).sensitive);

/** Lines and rows marked Internal only. @param {SheetDoc} doc @returns {{section: string, text?: string, ref?: string}[]} */
export const internalOnly = doc => Array.isArray((doc.layout || {}).internal_only) ? doc.layout.internal_only : [];
/** Whether a line or a row is marked Internal only. A row marked while a draft ("@3") stays marked once approval gives it its ID
    (the row keeps its number `n`). @param {SheetDoc} doc @param {string} section @param {{text?: string, ref?: string, n?: number}} what */
export const isInternal = (doc, section, what) => internalOnly(doc).some(x => x.section === section &&
  (what.ref ? x.ref === what.ref || (what.n != null && x.ref === `@${what.n}`) : x.text === what.text));
/** The layout with a line or row marked (or unmarked) Internal only. @param {SheetDoc} doc @param {string} section @param {{text?: string, ref?: string}} what */
export function toggleInternal(doc, section, what) {
  const was = internalOnly(doc), on = isInternal(doc, section, what);
  const next = on ? was.filter(x => !(x.section === section && (what.ref ? x.ref === what.ref : x.text === what.text))) : [...was, { section, ...what }];
  return { ...doc, layout: { ...(doc.layout || {}), internal_only: next } };
}

/** Why an item never reaches the distributed version ("Sensitive", "partner-only", "labelled …"), or "".
    @param {SheetDoc} doc @param {string} ref @param {Record<string, string>} [held] the route's `withheld` */
export const heldBack = (doc, ref, held) => (held && held[ref]) || (sensitive((doc.items || {})[ref]) ? "Sensitive" : "");

/** The distributed version as the page shows it. @param {SheetDoc} doc @param {Record<string, string>} [held] @returns {SheetDoc} */
export function distributedOf(doc, held) {
  const sections = doc.sections.map(s => {
    if (s.type === "table") {
      const keptRows = (s.rows || []).filter(r => !(r.ref && (heldBack(doc, r.ref, held) || isInternal(doc, s.id, { ref: r.ref, n: /** @type {any} */ (r).n }))));
      return { ...s, rows: keptRows, text: keptRows.length ? "" : "None recorded." };
    }
    if (s.type === "header" || !s.text) return s;
    const kept = mdLines(s.text).filter(l => !isInternal(doc, s.id, { text: l.text }));
    return { ...s, text: mdUnlines(kept) || "None recorded." };
  });
  return { ...doc, audience: "distributed", sections };
}

/** What the distributed version leaves out, in words, for the check before export. @param {SheetDoc} doc @param {Record<string, string>} [held] */
export function leftOut(doc, held) {
  const out = [];
  for (const s of doc.sections) {
    for (const r of s.rows || []) {
      const why = r.ref ? heldBack(doc, r.ref, held) : "";
      if (why) out.push(`${s.heading}: ${/^[a-z]/.test(why) ? `an item ${why}` : `a ${why} item`}`);
      else if (r.ref && isInternal(doc, s.id, { ref: r.ref, n: /** @type {any} */ (r).n })) out.push(`${s.heading}: ${Object.values(r.cells || {}).filter(Boolean).join(" · ").slice(0, 80)}`);
    }
    if (s.type !== "table" && s.type !== "header") for (const l of mdLines(s.text || "")) if (isInternal(doc, s.id, { text: l.text })) out.push(`${s.heading}: ${l.text.slice(0, 80)}`);
  }
  return out;
}

const DEADLINE = /\b(?:by |on )?(next week|end of (?:the )?month|next (?:mon|tues|wednes|thurs|fri)day|(?:mon|tues|wednes|thurs|fri)day|in \d+ weeks?|tomorrow)\b/i;
const FIGURE = /\b\d+(?:[.,]\d+)?%?/g;

/** The checks on one item row. @param {SheetDoc} doc @param {SheetSection} s @param {any} r @param {number} i
    @param {any[]} turns @param {(name: string) => boolean} unknown @returns {Check[]} */
function rowChecks(doc, s, r, i, turns, unknown) {
  const out = [], it = (doc.items || {})[r.ref], v = (it && it.values) || {};
  if (!it || it.op !== "new") return out;
  const n = it.n, label = v.description || v.decision || "";
  const owner = s.id === "decisions" ? "" : String(v.owner || "").trim();
  if (s.id !== "decisions" && owner && owner !== "TBC" && unknown(owner))
    out.push({ id: `owner:${r.ref}`, section: s.id, row: i, field: "owner", quote: owner, kind: "owner", n,
      note: `${owner} needs details.`, actions: [{ id: "details", label: "Add details" }, { id: "keep", label: "Keep mine" }] });   // #266: a name on an item is in the register; its record may need details
  else if (s.id === "actions" && (!owner || owner === "TBC"))
    out.push({ id: `owner:${r.ref}`, section: s.id, row: i, field: "owner", quote: owner || "TBC", kind: "owner", n,
      note: "No owner yet.", actions: [{ id: "pick", label: "Pick from the register" }, { id: "keep", label: "Keep mine" }] });
  const turn = r.at && r.at.turn ? turns.find(t => t.n === r.at.turn) : null;
  const said = turn && s.id === "actions" ? DEADLINE.exec(turn.text) : null;
  const meant = said ? deadlineOf(said[0], doc.date) : null;
  if (said && meant && meant !== (v.due_date || null))
    out.push({ id: `due:${r.ref}`, section: s.id, row: i, field: "due", quote: v.due_date ? fd(v.due_date) : "Not set", kind: "due", n, turn: turn.n, words: said[0],
      note: `${turn.who || "Someone"} said “${said[0]}”: ${deadlineDay(meant)}.`, last: v.due_date ? `The row says ${deadlineDay(v.due_date)}.` : "The row has no deadline.",
      actions: [{ id: "use", label: "Use that" }, { id: "keep", label: "Keep mine" }, { id: "show", label: "Show in the transcript" }] });
  if (turn) for (const f of new Set(label.match(FIGURE) || [])) if (!turn.text.includes(f))
    out.push({ id: `fig:${r.ref}:${f}`, section: s.id, row: i, quote: f, kind: "figure", n, turn: turn.n,
      note: `The transcript at ${turn.start || `turn ${turn.n}`} doesn't say ${f}.`, last: `${turn.who || "Someone"} said: “${turn.text.slice(0, 160)}”`,
      actions: [{ id: "keep", label: "Keep mine" }, { id: "show", label: "Show in the transcript" }] });
  if ((it.flags || []).some((/** @type {string} */ f) => f === "invalid" || f === "conflict"))
    out.push({ id: `item:${r.ref}`, section: s.id, row: i, quote: "", kind: "item", n,
      note: "The project record's checks couldn't accept this item as it stands: change it in Review.", actions: [{ id: "keep", label: "Keep mine" }] });
  return out;
}

/** The checks on a text section's lines: a figure its time tag's turn doesn't say. @param {SheetSection} s @param {any[]} turns
    @returns {Check[]} */
function lineChecks(s, turns) {
  const out = [];
  mdLines(s.text || "").forEach((l, i) => {
    const t = lineTag(l, /** @type {TimeTag[]} */ (s.tags || [])), turn = t ? turns.find(x => x.n === t.turn) : null;
    if (!turn) return;
    for (const f of new Set(l.text.match(FIGURE) || [])) if (!turn.text.includes(f))
      out.push({ id: `fig:${s.id}:${i}:${f}`, section: s.id, line: i, field: "text", quote: f, kind: "figure", turn: turn.n,
        note: `The transcript at ${turn.start || `turn ${turn.n}`} doesn't say ${f}.`, last: `${turn.who || "Someone"} said: “${turn.text.slice(0, 160)}”`,
        actions: [{ id: "keep", label: "Keep mine" }, { id: "show", label: "Show in the transcript" }] });
  });
  return out;
}

/** Every open check on the record. `unknown(name)`: the people register doesn't know the name (settings.js unknownOwner).
    @param {SheetDoc} doc @param {any[]} turns @param {(name: string) => boolean} unknown @param {string[]} kept @returns {Check[]} */
export function checksOf(doc, turns, unknown, kept) {
  if (!doc || doc.state !== "draft") return [];
  const out = [];
  for (const s of doc.sections) {
    if (s.hidden) continue;
    if (s.type === "table") (s.rows || []).forEach((r, i) => { if (r.ref) out.push(...rowChecks(doc, s, r, i, turns || [], unknown)); });
    else if (s.type === "text") out.push(...lineChecks(s, turns || []));
  }
  return out.filter(c => !kept.includes(c.id));
}
