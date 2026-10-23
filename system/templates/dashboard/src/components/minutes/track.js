// @ts-check
/* track.js (#268, Minutes view v2): the Track column's three states, in plain functions (no drawing, no server).
   Each decision, risk, issue and action row of draft minutes is one of:
   - "y" (tick): register a work item: the staged item is approved with the minutes;
   - "n" (cross): remove the line from the minutes: the item is rejected and its line leaves (minutes_record `remove`);
   - "" (neither): the line stays in the minutes and no work item is made (minutes_record `remove` with `keep_line`); on an
     update approved one by one (the plan's "own" group: a closure, a decision recorded, an owner change…) it changes nothing
     and the update stays in Review (review H2), so neither never rejects such an update.
   Clicking the pressed button clears it (back to neither). Defaults (Alan, the v2 brief; review H2): actions and issues start
   ticked; decisions, risks and every item the bulk rule decides one by one (the plan's "own" group, review.individual_only)
   start with neither; a kept line is neither. A choice is kept in the record's layout (`layout.track`, saved with the
   page), so it survives a reload; the record's own state (a kept line, a removed row) is brought in line only when the minutes
   are approved (`reconcileOps`), through the record's existing changes. The server's code is unchanged. */

/** @typedef {"y"|"n"|""} Track */
/** @typedef {import("../report/Sheet.jsx").SheetDoc} SheetDoc */
/** @typedef {{n: number, group: string, why: string|null, label: string}} PlanItem */
/** @typedef {{n: number, section: string, row: any, item: any, kept: boolean}} TrackRow */

export const TRACK_SECTIONS = ["decisions", "raid", "actions"];

/** The item number of a row: its own, or the one a kept line was ("@3"). @param {any} rw @returns {number|null} */
export const rowN = rw => {
  if (rw && typeof rw.n === "number") return rw.n;
  const m = /^@(\d+)$/.exec(String((rw && rw.was) || ""));
  return m ? Number(m[1]) : null;
};

/** Every trackable row of the record, in page order. @param {SheetDoc} doc @returns {TrackRow[]} */
export function trackRows(doc) {
  /** @type {TrackRow[]} */
  const out = [];
  for (const s of (doc && doc.sections) || []) {
    if (!TRACK_SECTIONS.includes(s.id) || s.type !== "table") continue;
    const srows = /** @type {any[]} */ (s.rows || []);
    for (const rw of srows) {
      const n = rowN(rw);
      if (n == null || (!rw.ref && !rw.kept_line)) continue;
      out.push({ n, section: s.id, "row": rw, item: rw.ref ? (doc.items || {})[rw.ref] || null : null, kept: !!rw.kept_line });
    }
  }
  return out;
}

/** Where a plan puts item n ("group", "own", "waits", "milestone", "removed"), or "". @param {PlanItem[]|null|undefined} plan @param {number} n */
const planGroupOf = (plan, n) => ((plan || []).find(i => i.n === n) || { group: "" }).group;

/** A row's starting state: decisions, risks and the plan's "own" group neither, everything else ticked.
    @param {string} section @param {any} item @param {string} [group] where the plan puts it */
export const defaultTrack = (section, item, group) => /** @type {Track} */ (group === "own" || section === "decisions" ||
  (section === "raid" && !!item && item.op === "new" && ((item.values || {}).type || "Risk") === "Risk") ? "" : "y");

/** Whether neither on this row leaves its item in Review (an update approved one by one) rather than rejecting it.
    @param {TrackRow} r @param {PlanItem[]|null|undefined} plan */
export const waitsWhenNeither = (r, plan) => !r.kept && !!r.item && r.item.op === "update" && planGroupOf(plan, r.n) === "own";

/** The choices kept in the layout. @param {SheetDoc} doc @returns {Record<string, Track>} */
export const trackChoices = doc => {
  const t = ((doc && doc.layout) || {}).track;
  return t && typeof t === "object" && !Array.isArray(t) ? t : {};
};

/** A row's state now: the choice made, else a kept line is neither, else the default. @param {SheetDoc} doc @param {TrackRow} r
    @param {PlanItem[]|null|undefined} plan @returns {Track} */
export function trackOf(doc, r, plan) {
  const c = trackChoices(doc)[String(r.n)];
  if (c === "y" || c === "n" || c === "") return c;
  return r.kept ? "" : defaultTrack(r.section, r.item, planGroupOf(plan, r.n));
}

/** What a click on a Track button makes: the pressed one again clears it. @param {Track} now @param {"y"|"n"} pressed @returns {Track} */
export const nextTrack = (now, pressed) => (now === pressed ? "" : pressed);

/** The record with row n's choice set (kept in the layout). @param {SheetDoc} doc @param {number} n @param {Track} t @returns {SheetDoc} */
export function setTrack(doc, n, t) {
  const lay = { ...(doc.layout || {}) };
  lay.track = { ...trackChoices(doc), [String(n)]: t };
  return { ...doc, layout: lay };
}

/** The plan's pending items the minutes show no row for (a promise, a milestone): no Track control, so Approve minutes never
    registers them (Cap's #268 review H1); they wait in Review. @param {SheetDoc} doc @param {PlanItem[]|null|undefined} plan */
export function rowlessPending(doc, plan) {
  const shown = new Set(trackRows(doc).map(r => r.n));
  return (plan || []).filter(i => ["group", "own", "waits", "milestone"].includes(i.group) && !shown.has(i.n)).map(i => i.n);
}

/** How many rows will register (ticked, in a group Approve minutes applies), are kept in the minutes only, will be left in
    Review (ticked but needing a project or Review, an update approved one by one left with neither, or an item with no row) and are removed.
    @param {SheetDoc} doc @param {PlanItem[]|null|undefined} plan */
export function trackCounts(doc, plan) {
  const c = { y: 0, k: 0, n: 0, w: 0 };
  for (const r of trackRows(doc)) {
    const t = trackOf(doc, r, plan), g = planGroupOf(plan, r.n);
    if (g === "applied") continue;                      // approved earlier: its work item is in the tracker, nothing left to count
    if (t === "n") c.n++;
    else if (t === "y") { if (r.kept || g === "group" || g === "own") c.y++; else c.w++; }
    else if (waitsWhenNeither(r, plan)) c.w++;
    else c.k++;
  }
  c.w += rowlessPending(doc, plan).length;              // shown nowhere, so never registered here: left in Review
  return c;
}

const trackPlural = (/** @type {number} */ n, /** @type {string} */ one, /** @type {string} */ many) => `${n} ${n === 1 ? one : many}`;
/** The bar's summary: "3 work items to register · 2 kept in the minutes only · 1 left in Review · 1 removed" (the last two
    only when there are some). @param {{y: number, k: number, n: number, w?: number}} c */
export const trackSummary = c => `${trackPlural(c.y, "work item", "work items")} to register · ${c.k} kept in the minutes only${c.w ? ` · ${c.w} left in Review` : ""}${c.n ? ` · ${c.n} removed` : ""}`;

/** What the ticked rows will track, by kind (#302): actions, decisions, issues, risks, and for the rest assumptions,
    dependencies and updates to an existing item. A row approved earlier is not counted. @param {SheetDoc} doc @param {PlanItem[]|null|undefined} plan
    @returns {Record<string, number>} */
export function trackedKinds(doc, plan) {
  /** @type {Record<string, number>} */
  const out = {};
  for (const r of trackRows(doc)) {
    if (trackOf(doc, r, plan) !== "y" || planGroupOf(plan, r.n) === "applied") continue;
    const it = r.item || {}, ty = String((it.values || {}).type || ((r.row.cells || {}).type) || "Risk").toLowerCase();
    const k = it.op === "update" ? "update" : r.section === "actions" ? "action" : r.section === "decisions" ? "decision"
      : ["issue", "assumption", "dependency"].includes(ty) ? ty : "risk";
    out[k] = (out[k] || 0) + 1;
  }
  return out;
}

/** The Approve button's words: "Approve minutes · tracks 2 actions, 1 decision", or "… tracks nothing". @param {Record<string, number>} k */
export function approveLabel(k) {
  const order = ["action", "decision", "issue", "risk", "assumption", "dependency", "update"];
  const parts = order.filter(x => k[x]).map(x => `${k[x]} ${x}${k[x] === 1 ? "" : "s"}`);
  return `Approve minutes · tracks ${parts.length ? parts.join(", ") : "nothing"}`;
}

/** Which ticked rows still need something (#302): a new action, issue or risk that is tracked but has no owner or no date. A "vague"
    date is one the transcript gave in words that the row doesn't hold yet (a deadline check is open on it). A decision never needs
    either. @param {SheetDoc} doc @param {PlanItem[]|null|undefined} plan @param {{kind: string, n?: number}[]} checks
    @returns {Map<number, {owner: boolean, date: boolean, vague: boolean}>} */
export function needsOf(doc, plan, checks) {
  const out = new Map();
  for (const r of trackRows(doc)) {
    if (r.section === "decisions" || !r.item || r.item.op !== "new" || trackOf(doc, r, plan) !== "y" || planGroupOf(plan, r.n) === "applied") continue;
    const v = r.item.values || {}, o = String(v.owner || "").trim();
    const owner = !o || o === "TBC", date = !v.due_date, vague = date && (checks || []).some(c => c.kind === "due" && c.n === r.n);
    if (owner || date) out.set(r.n, { owner, date, vague });
  }
  return out;
}

/** The record's changes that bring its rows in line with the choices, in order (each one of minutes_record.change's ops):
    a cross on a pending row is `remove`; neither on a pending row is `remove` with `keep_line` (nothing for an update approved
    one by one: it stays in Review); a tick on a kept line is `restore`; a cross on a kept line is `restore` then `remove`. @param {SheetDoc} doc @param {PlanItem[]|null|undefined} plan
    @returns {Record<string, any>[]} */
export function reconcileOps(doc, plan) {
  const ops = [];
  for (const r of trackRows(doc)) {
    if (planGroupOf(plan, r.n) === "applied") continue;                      // approved earlier: nothing to change, never an error
    const want = trackOf(doc, r, plan), now = r.kept ? "" : "y";
    if (want === now || (want === "" && waitsWhenNeither(r, plan))) continue;     // an update decided one by one stays in Review
    if (r.kept) { ops.push({ op: "restore", n: r.n }); if (want === "n") ops.push({ op: "remove", n: r.n, keep_line: false }); }
    else ops.push({ op: "remove", n: r.n, keep_line: want === "" });
  }
  return ops;
}


/** What Approve minutes sends (review H1): never the whole group, only the numbers of the rows ticked in a group it applies
    ("group" or "own"), so an item with no row (a promise) is never registered unseen. @param {SheetDoc} doc
    @param {PlanItem[]|null|undefined} plan @returns {{group: false, own: number[]}} */
export const approveArgs = (doc, plan) => ({ group: false, own: trackRows(doc)
  .filter(r => ["group", "own"].includes(planGroupOf(plan, r.n)) && trackOf(doc, r, plan) === "y").map(r => r.n) });

/** What is worth a look before approving: only ticked items with a real problem (an owner who needs details, a possible
    duplicate). `needsDetails(name)` is the people register's check. @param {SheetDoc} doc @param {PlanItem[]|null|undefined} plan
    @param {(name: string) => boolean} needsDetails @returns {{n: number, what: string, text: string}[]} */
export function approveProblems(doc, plan, needsDetails) {
  const out = [];
  for (const r of trackRows(doc)) {
    if (trackOf(doc, r, plan) !== "y" || !r.item || r.item.op !== "new") continue;
    const v = r.item.values || {}, text = String(v.description || v.decision || "");
    const owner = String((r.section === "decisions" ? v.made_by : v.owner) || "").trim();
    if (owner && owner !== "TBC" && needsDetails(owner)) out.push({ n: r.n, what: `${owner} needs details`, text });
    const ll = r.item.looks_like || {};
    if (ll.id && !ll.kept && !ll.merged) out.push({ n: r.n, what: `Possible duplicate of ${ll.id}`, text });
  }
  return out;
}
