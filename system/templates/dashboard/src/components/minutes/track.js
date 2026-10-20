// @ts-check
/* track.js (#268, Minutes view v2): the Track column's three states, in plain functions (no drawing, no server).
   Each decision, risk, issue and action row of draft minutes is one of:
   - "y" (tick): register a work item: the staged item is approved with the minutes;
   - "n" (cross): remove the line from the minutes: the item is rejected and its line leaves (minutes_record `remove`);
   - "" (neither): the line stays in the minutes and no work item is made (minutes_record `remove` with `keep_line`).
   Clicking the pressed button clears it (back to neither). Defaults (Alan, the v2 brief): actions and issues start ticked;
   decisions and risks start with neither (they are recorded one by one); a kept line is neither. A choice is kept in the record's layout (`layout.track`, saved with the
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

/** A row's starting state: decisions and risks neither, everything else ticked. @param {string} section @param {any} item */
export const defaultTrack = (section, item) => /** @type {Track} */ (section === "decisions" ||
  (section === "raid" && !!item && item.op === "new" && ((item.values || {}).type || "Risk") === "Risk") ? "" : "y");

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
  return r.kept ? "" : defaultTrack(r.section, r.item);
}

/** What a click on a Track button makes: the pressed one again clears it. @param {Track} now @param {"y"|"n"} pressed @returns {Track} */
export const nextTrack = (now, pressed) => (now === pressed ? "" : pressed);

/** The record with row n's choice set (kept in the layout). @param {SheetDoc} doc @param {number} n @param {Track} t @returns {SheetDoc} */
export function setTrack(doc, n, t) {
  const lay = { ...(doc.layout || {}) };
  lay.track = { ...trackChoices(doc), [String(n)]: t };
  return { ...doc, layout: lay };
}

/** How many rows are ticked, kept in the minutes only and removed. @param {SheetDoc} doc @param {PlanItem[]|null|undefined} plan */
export function trackCounts(doc, plan) {
  const c = { y: 0, k: 0, n: 0 };
  for (const r of trackRows(doc)) { const t = trackOf(doc, r, plan); if (t === "y") c.y++; else if (t === "n") c.n++; else c.k++; }
  return c;
}

const trackPlural = (/** @type {number} */ n, /** @type {string} */ one, /** @type {string} */ many) => `${n} ${n === 1 ? one : many}`;
/** The bar's summary: "3 work items to register · 2 kept in the minutes only · 1 removed" (the last only when there are some).
    @param {{y: number, k: number, n: number}} c */
export const trackSummary = c => `${trackPlural(c.y, "work item", "work items")} to register · ${c.k} kept in the minutes only${c.n ? ` · ${c.n} removed` : ""}`;

/** The record's changes that bring its rows in line with the choices, in order (each one of minutes_record.change's ops):
    a cross on a pending row is `remove`; neither on a pending row is `remove` with `keep_line`; a tick on a kept line is
    `restore`; a cross on a kept line is `restore` then `remove`. @param {SheetDoc} doc @param {PlanItem[]|null|undefined} plan
    @returns {Record<string, any>[]} */
export function reconcileOps(doc, plan) {
  const ops = [];
  for (const r of trackRows(doc)) {
    const want = trackOf(doc, r, plan), now = r.kept ? "" : "y";
    if (want === now) continue;
    if (r.kept) { ops.push({ op: "restore", n: r.n }); if (want === "n") ops.push({ op: "remove", n: r.n, keep_line: false }); }
    else ops.push({ op: "remove", n: r.n, keep_line: want === "" });
  }
  return ops;
}

/** The items approved one by one that are ticked: Approve minutes' `own`. @param {SheetDoc} doc @param {PlanItem[]|null|undefined} plan */
export const ownTicked = (doc, plan) => trackRows(doc).filter(r => planGroupOf(plan, r.n) === "own" && trackOf(doc, r, plan) === "y").map(r => r.n);

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
