// @ts-check
/* irUpdate (#232-B, release 2.6): the pure rules of an update proposal in the peek. No DOM, no imports: run under Node by
   dev/tests/test_intake_review_update.py.

   One list, `[{col, label, was, now, same}]`, is the single source for everything the peek and the row say about an update:
   the chips (`was → now`), the note "What changes if you approve", the "If approved" line in the activity, and the row's
   emphasised line ("Closes ABC-A-014: Draft the comms plan · status Open → Closed"). They are all words made from it, so they
   cannot disagree.

   `was` is the tracker row as it is now (the live row), never the proposal's own `from`, which can be stale. A change is a
   column whose new value differs from the live value; one that already has the value is `same` (shown plain: "already this
   value").

   Columns are the tracker's (`due_date`, `latest_update`, `needed_by`), as the proposal's `changes` and the server's `col` name
   them. A row's own keys are the dashboard's (`st`, `due`, `upd`): UI maps one to the other and is pinned to core/server.js's
   FIELD by the test. Internal only: nothing here reaches a client report; client message text is never shown, only on or off. */

/** The dashboard's key for each tracker column, per table (the inverse of FIELD in core/server.js; the test pins them). */
export const UI = /** @type {Record<string, Record<string, string>>} */ ({
  actions: { description: "t", project: "p", workstream: "ws", owner: "o", priority: "pr", due_date: "due", status: "st", raised: "raised", closed: "closed", latest_update: "upd", client_visible: "client", client_message: "cm", milestone: "ms" },
  raid: { description: "t", project: "p", type: "type", workstream: "ws", owner: "o", response_action: "resp", due_date: "due", impact: "imp", likelihood: "lik", status: "st", raised: "raised", closed: "closed", client_visible: "client", client_message: "cm", milestone: "ms" },
  decisions: { decision: "t", project: "p", made_by: "by", date: "date", client_visible: "client", client_message: "cmd", status: "st", needed_by: "due", reasoning: "why", options: "opts", revisit: "revisit", replaces: "replaces" },
});

/** The columns Alan can edit in the peek (Status, Due, Latest update); every other column shows `was → now` and is read-only.
    Latest update is an action's only: a RAID item has a response and a decision its reasoning, both read-only here. */
export const EDITABLE = /** @type {Record<string, string[]>} */ ({ actions: ["status", "due_date", "latest_update"], raid: ["status", "due_date"], decisions: ["status", "needed_by"] });

/** Columns a status edit can carry beside it: a decision made today needs the date it was made (the schema's CHECK). Read-only
    in the peek, written only with that status. */
export const SIDE = /** @type {Record<string, string[]>} */ ({ actions: [], raid: [], decisions: ["date"] });

/** The words for each column. */
const LABEL = /** @type {Record<string, string>} */ ({
  status: "Status", owner: "Owner", due_date: "Due date", needed_by: "Needed by", priority: "Priority", project: "Project", workstream: "Workstream",
  milestone: "Milestone", client_visible: "Client-visible", latest_update: "Latest update", description: "Description", decision: "Decision",
  response_action: "Response", reasoning: "Reasoning", options: "Options considered", revisit: "Revisit", client_message: "Client messaging",
  made_by: "Decision maker", date: "Date made", impact: "Impact", likelihood: "Likelihood", type: "Type", raised: "Raised", closed: "Date closed", replaces: "Replaces",
});

/** The shorter word the row's line uses ("due 20-10-2026 → 23-10-2026"). */
const SHORT = /** @type {Record<string, string>} */ ({ due_date: "due", needed_by: "needed by", made_by: "made by", client_visible: "client-visible" });

/** Columns that are text, said as a phrase ("the latest update") and never as `was → now`: the words can be long, and for
    client messaging they must not be shown at all. */
const PHRASE = /** @type {Record<string, string>} */ ({ latest_update: "the latest update", description: "the description", decision: "the decision", response_action: "the response",
  reasoning: "the reasoning", options: "the options considered", client_message: "the client messaging", health_reason: "the health reason" });

/** The order chips and phrases come in. */
const ORDER = ["status", "due_date", "needed_by", "owner", "made_by", "priority", "project", "workstream", "milestone", "client_visible", "impact", "likelihood", "type", "date",
  "description", "decision", "latest_update", "response_action", "reasoning", "options", "revisit", "replaces", "client_message", "raised", "closed"];

/** Whether two stored values are the same: empty is empty, a flag is 0/1, text is compared trimmed.
    @param {any} a @param {any} b */
export function irSame(a, b) {
  const n = (/** @type {any} */ v) => (v == null || v === "" ? "" : v === true ? "1" : v === false ? "0" : String(v).trim());
  return n(a) === n(b);
}

/** A column's label. @param {string} col */
export const irLabel = col => LABEL[col] || (col.charAt(0).toUpperCase() + col.slice(1).replace(/_/g, " "));

/** Whether a column is text, said as a phrase. @param {string} col */
export const irIsText = col => col in PHRASE;

/** A stored value as it is shown: a date as DD-MM-YYYY, a flag as on or off, nothing as a dash, long text cut short.
    @param {string} col @param {any} v */
export function irWord(col, v) {
  if (col === "client_visible") return v === 1 || v === true || v === "1" ? "on" : "off";
  if (v == null || String(v).trim() === "") return "—";
  const s = String(v).trim().replace(/\s+/g, " ");
  const m = /^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}:\d{2}))?/.exec(s);                     /* a stored date (any date column), with its time if it has one */
  if (m) return `${m[3]}-${m[2]}-${m[1]}${m[4] ? " " + m[4] : ""}`;
  return s.length > 60 ? s.slice(0, 59) + "…" : s;
}

/** The one list: every column the proposal changes, or Alan has edited, against the live row.
    @param {Record<string, any>} live the tracker row as it is now, under the tracker's column names
    @param {Record<string, any>} now the row as it would be: the live row with the proposal's changes and Alan's edits
    @param {string[]} proposed the columns the proposal itself changes
    @returns {{col: string, label: string, was: any, now: any, same: boolean, proposed: boolean}[]} */
export function irUpdateList(live, now, proposed) {
  const cols = new Set(proposed);
  for (const col of Object.keys(now)) if (!irSame(live[col], now[col])) cols.add(col);
  const at = (/** @type {string} */ c) => { const i = ORDER.indexOf(c); return i < 0 ? ORDER.length : i; };
  return [...cols].sort((a, b) => at(a) - at(b) || proposed.indexOf(a) - proposed.indexOf(b)).map(col =>
    ({ col, label: irLabel(col), was: live[col], now: now[col], same: irSame(live[col], now[col]), proposed: proposed.includes(col) }));
}

/** Only the columns that change. @template {{same: boolean}} T @param {T[]} list @returns {T[]} */
export const irChanged = list => list.filter(c => !c.same);

/** The row as it would be: the live row, the proposal's changes, then what Alan edited in the peek (the editable columns, and the
    side column a decision made today carries). @param {string} table @param {Record<string, any>} live @param {Record<string, any>} changes
    @param {Record<string, any>} draft the peek's draft, under the tracker's column names */
export function irNowRow(table, live, changes, draft) {
  const now = { ...live, ...changes };
  for (const col of [...(EDITABLE[table] || []), ...(SIDE[table] || [])]) if (col in draft) now[col] = draft[col];
  return now;
}

/** The words for one change in a sentence, from the list: a text column as a phrase, any other as `label was → now`.
    @param {{col: string, was: any, now: any}} c @param {boolean} [short] the row's shorter label @returns {{label: string, delta: string, text: boolean}} */
export function irPhrase(c, short) {
  if (irIsText(c.col)) return { label: PHRASE[c.col], delta: "", text: true };
  const label = short && SHORT[c.col] ? SHORT[c.col] : irLabel(c.col).toLowerCase();
  return { label, delta: `${irWord(c.col, c.was)} → ${irWord(c.col, c.now)}`, text: false };
}

/** What the note says: "ABC-A-002 · Book UAT environment: due date 20-10-2026 → 23-10-2026 and the latest update". Said once from
    the list; "" when nothing changes. @param {{col: string, was: any, now: any}[]} changed */
export function irNoteWords(changed) {
  const ph = changed.map(c => irPhrase(c));
  return ph.map(p => (p.text ? p.label : `${p.label} ${p.delta}`)).join(" and ");
}

/** The note as text. @param {string} id @param {string} title @param {{col: string, was: any, now: any}[]} changed */
export function irNoteText(id, title, changed) {
  const what = [id, title].filter(Boolean).join(" · ");
  return changed.length ? `What changes if you approve: ${what}: ${irNoteWords(changed)}. The rest of the item stays as it is.`
    : `Nothing changes if you approve: ${what} already has every value in this update.`;
}

/** The pending "If approved" line in the activity, from the same list: "Latest update replaced · Due date 20-10-2026 → 23-10-2026".
    @param {{col: string, label: string, was: any, now: any}[]} changed */
export function irIfApproved(changed) {
  return changed.map(c => (irIsText(c.col) ? `${c.label} replaced` : `${c.label} ${irWord(c.col, c.was)} → ${irWord(c.col, c.now)}`)).join(" · ");
}

/** The row's emphasised line after the verb and the item: "status Open → Closed", "due 20-10-2026 → 23-10-2026 and the latest
    update". Each changed scalar is a part; the text columns follow the last one with "and". Takes the row's changes (`from`,
    `to`) as they were built, or the peek's list. @param {{col: string, was?: any, now?: any, from?: any, to?: any}[]} changes @returns {string[]} */
export function irLineParts(changes) {
  const chs = changes.filter(c => c.col).map(c => ({ col: c.col, was: "was" in c ? c.was : c.from, now: "now" in c ? c.now : c.to }));
  const scalar = chs.filter(c => !irIsText(c.col)).map(c => { const p = irPhrase(c, true); return `${p.label} ${p.delta}`; });
  const text = chs.filter(c => irIsText(c.col)).map(c => PHRASE[c.col]);
  if (!text.length) return scalar;
  const tail = text.join(" and ");
  return scalar.length ? [...scalar.slice(0, -1), `${scalar[scalar.length - 1]} and ${tail}`] : [tail];
}

/** The verb of the line: Closes or Cancels for a status change that ends the item, else Updates.
    @param {{col: string, to?: any, now?: any}[]} changes */
export function irVerb(changes) {
  const st = changes.find(c => c.col === "status");
  const to = st ? ("now" in st ? st.now : st.to) : null;
  return to === "Closed" ? "Closes" : to === "Cancelled" ? "Cancels" : "Updates";
}

/** The line's first part: "Closes ABC-A-014: Draft the comms plan" (a project has no ID to show: "Updates Example Programme"). @param {string} verb @param {string} id @param {string} [title] */
export const irLineHead = (verb, id, title) => (id ? `${verb} ${id}${title ? `: ${title}` : ""}` : `${verb} ${title || ""}`).trim();

/** A date the way the tracker stores it, or "" when it is not one. @param {any} v */
const isoDate = v => { const s = String(v ?? "").trim(); const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s); if (!m) return ""; const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3])); return d.getUTCFullYear() === +m[1] && d.getUTCMonth() === +m[2] - 1 && d.getUTCDate() === +m[3] ? s : ""; };

/** Allowed statuses, as the tracker's ALLOWED lists them. */
export const STATUSES = /** @type {Record<string, string[]>} */ ({ actions: ["Open", "Delayed", "Closed", "Cancelled"], raid: ["Open", "Closed", "Cancelled"], decisions: ["Pending", "Made", "Withdrawn"] });

/** What a save writes: the proposal's own `changes`, with only the columns Alan edited in the peek put right.
    A column he did not touch stays exactly as the proposal had it; one he changed takes his value, or comes out of the proposal
    when his value is the live one (so the apply leaves it alone). Never a column outside EDITABLE (and SIDE with its status).
    @param {string} table
    @param {Record<string, any>} changes the proposal's changes, under the tracker's column names
    @param {Record<string, any>} live the tracker row as it is now
    @param {Record<string, any>} opened the editable columns' values when the peek opened
    @param {Record<string, any>} draft the peek's draft now, under the tracker's column names
    @returns {{changes: Record<string, any>, edited: string[]} | {error: string}} */
export function irSaveChanges(table, changes, live, opened, draft) {
  const out = { ...changes }, edited = [];
  const clean = (/** @type {string} */ col, /** @type {any} */ v) => { const s = typeof v === "string" ? v.trim() : v; return s === "" || s == null ? null : s; };
  for (const col of EDITABLE[table] || []) {
    if (!(col in draft) || irSame(draft[col], opened[col])) continue;
    const v = clean(col, draft[col]);
    if (col === "status" && !(STATUSES[table] || []).includes(String(v))) return { error: `Status must be one of ${(STATUSES[table] || []).join(", ")}.` };
    if ((col === "due_date" || col === "needed_by") && v != null && !isoDate(v)) return { error: "That is not a date creaite knows. Use DD-MM-YYYY." };
    edited.push(col);
    if (irSame(v, live[col])) delete out[col]; else out[col] = v;
  }
  if (table === "decisions" && edited.includes("status") && out.status === "Made" && !live.date && isoDate(draft.date)) { out.date = draft.date; edited.push("date"); }
  if (!Object.keys(out).length) return { error: "Nothing would change if this were approved: reject it instead, or change a value first." };
  return { changes: out, edited };
}
