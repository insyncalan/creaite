// @ts-check
/* stores/minutes.js (v2.1.0 P7, BL-338, dev/COMPONENTS.md §2): the minutes view's state, one store for the area.
   Everything comes from P4's routes: /api/minutes/draft (the record, its versions, the transcript's turns and, while its items
   are pending, the approve popup's plan), /api/minutes/save (the page as a new version, or one row or coverage change: the
   record and its proposal change together), /api/minutes/approve (the minutes and the ticked items in one apply) and
   /api/minutes/export. Nothing here writes any other way; nothing is sent.
   #275: trackApprove is Approve minutes by the Track column, the one implementation: the minutes view's Approve minutes and
   Review's Approve (and Approve n routine) on minutes kept as a record all call it, so both give the same result. */
import { isMovedMinutes } from "../core/say.js";
import { signal } from "@preact/signals";
import { approveArgs, reconcileOps } from "../components/minutes/track.js";
import { store } from "../core/page.js";
import { needsConnection } from "../core/say.js";
import { REV } from "../core/data.js";
import { askFiling, noteNumbered } from "./minutesFiling.js";
import { mountFiling } from "../components/minutes/FilingDialog.jsx";
import { api, applyNow, oneLine, REVIEW_CHANGED, STALE_ROW_MSG, viaServer } from "../core/server.js";

/** @typedef {import("../components/report/Sheet.jsx").SheetDoc} SheetDoc */
/** @typedef {{n: number, who: string|null, start: string|null, end: string|null, text: string}} Turn */
/** @typedef {{version: number, current: boolean, at?: string, change?: number, why?: string, backup?: string}} Version */
/** @typedef {{n: number, group: string, why: string|null, label: string}} PlanItem */
/** @typedef {{files: string[], transcripts: string[], items: PlanItem[], group: number, joins: string[]}} Plan */
/** @typedef {{ok: boolean, message?: string, path?: string, doc?: SheetDoc, versions?: Version[],
    turns?: {timed: boolean, turns: Turn[]}, proposal?: string|null, plan?: Plan|null, labels?: Record<string, string[]>,
    withheld?: Record<string, string>, settle?: number[]}} MinutesView */

/** What the view was opened with: {file} (the proposal) or {path} (the record). */
export const minutesArg = signal(/** @type {{file?: string, path?: string}|null} */ (null));
/** The route's answer, as it came. */
export const minutesView = signal(/** @type {MinutesView|null} */ (null));
/** The document on screen (the view keeps it; the sheet hands back a new one on every edit). */
export const minutesDoc = signal(/** @type {SheetDoc|null} */ (null));
/** The version the page was opened at, sent with each save. */
export const minutesBase = signal(/** @type {number|undefined} */ (undefined));
export const minutesBusy = signal("");
/** #268: whether the transcript pane is shown is remembered per browser (shown by default) and applies to the next minutes
    opened, whichever meeting. The page works without the storage (store.get and store.set are inside try/catch). */
export const PANE_KEY = "creaite-minutes-transcript";
/** The transcript pane: open, the turn picked from a time tag, the words searched for. */
export const paneOpen = signal(true);
/** Show or hide the transcript, and remember the choice. @param {boolean} on */
export function setPane(on) { paneOpen.value = !!on; if (!on) paneTurn.value = null; store.set(PANE_KEY, !!on); }
/** The remembered choice, read as each minutes opens. */
export function paneRemembered() { paneOpen.value = store.get(PANE_KEY, true) !== false; }
/** #268: the turn lit by hovering, both ways: a row lights its turn (from "row", the pane scrolls to it), a turn lights its
    rows (from "pane"). */
export const hoverTurn = signal(/** @type {{turn: number, from: "row"|"pane"}|null} */ (null));
export const paneTurn = signal(/** @type {number|null} */ (null));
export const paneQuery = signal("");
/** Checks Alan kept his words on (Keep mine), by check id, for this page's life. */
export const keptChecks = signal(/** @type {string[]} */ ([]));
/** #268: the Before approving box (only when a ticked item has a real problem). */
export const approveOpen = signal(false);

let mnAsked = 0;
/** A minutes record's view answer (/api/minutes/draft), settled first (#268): after Undo of Approve minutes the record still holds
    the approve's own changes (lines taken out or kept as lines only) while their items are pending again, so they are put back
    first and the minutes are exactly as they were before Approve. `stale` says a newer request has taken over (null then).
    @param {{file?: string, path?: string}} arg @param {() => boolean} [stale] @returns {Promise<MinutesView|null>} */
export async function openMinutesRecord(arg, stale = () => false) {
  let r = await api("/api/minutes/draft", arg);
  if (stale()) return null;
  if (r && r.ok && r.doc && r.doc.state === "draft" && Array.isArray(r.settle) && r.settle.length) {
    const s = await api("/api/minutes/save", { path: r.path, op: { op: "settle" }, base_version: Number(r.doc.version) || undefined });
    if (stale()) return null;
    if (s && s.ok) r = await api("/api/minutes/draft", { path: r.path });
    if (stale()) return null;
  }
  return r;
}

/** Open (or reload) the minutes: by the proposal's file name or the record's stored path.
    @param {{file?: string, path?: string}} arg */
export async function loadMinutes(arg) {
  const mine = ++mnAsked;
  minutesArg.value = arg;
  if (!viaServer()) { minutesView.value = { ok: false, message: needsConnection("The minutes view") }; return; }
  minutesBusy.value = "Opening the minutes…";
  const r = await openMinutesRecord(arg, () => mine !== mnAsked);
  if (r === null) return;
  minutesBusy.value = "";
  take(r && r.ok ? r : { ok: false, message: oneLine((r && r.message) || "") || "Couldn't open the minutes" });
}

/** Take a route's view answer onto the page. @param {MinutesView} r */
function take(r) {
  minutesView.value = r;
  minutesDoc.value = r.ok && r.doc ? r.doc : null;
  minutesBase.value = r.ok && r.doc ? Number(r.doc.version) || undefined : undefined;
}

/** Reload what the route says now, keeping the place (the sheet keeps its scroll). */
export async function reloadMinutes() {
  const v = minutesView.value;
  if (v && v.ok && v.path) return loadMinutes({ path: v.path });
  if (minutesArg.value) return loadMinutes(minutesArg.value);
}

/** One row or coverage change (P4's ops: remove, restore, update, keep_new, edit, deadline, cover, uncover). The record and its
    proposal change together; the answer's doc replaces the page's. Returns {ok, message}.
    @param {Record<string, any>} op @returns {Promise<{ok: boolean, message: string, needs_approval?: boolean}>} */
export async function changeMinutes(op) {
  const v = minutesView.value;
  if (!v || !v.ok || !v.path) return { ok: false, message: "The minutes aren't open." };
  const r = await api("/api/minutes/save", { path: v.path, op, base_version: minutesBase.value });
  if (r && r.ok && r.doc) {
    minutesDoc.value = r.doc;
    minutesBase.value = Number(r.version) || minutesBase.value;
    minutesView.value = { ...v, doc: r.doc };
    refreshPlan();
  }
  return { ok: !!(r && r.ok), message: oneLine((r && r.message) || ""), needs_approval: !!(r && r.needs_approval) };
}

/** The approve popup's plan follows a change (an item removed or added): mnAsked again, read only. */
async function refreshPlan() {
  const v = minutesView.value;
  if (!v || !v.ok || !v.path) return;
  const r = await api("/api/minutes/draft", { path: v.path });
  if (r && r.ok && minutesView.value && minutesView.value.path === r.path) minutesView.value = { ...minutesView.value, plan: r.plan, versions: r.versions, labels: r.labels, withheld: r.withheld };
}

/** The sheet's save: the page as Alan edited it, as a new version. @param {{doc: SheetDoc, base_version: number|undefined}} req */
export async function saveMinutesPage(req) {
  const v = minutesView.value;
  if (!v || !v.ok || !v.path) return { ok: false, message: "The minutes aren't open." };
  const r = await api("/api/minutes/save", { path: v.path, doc: req.doc, base_version: req.base_version });
  if (r && r.ok) { minutesBase.value = Number(r.version) || minutesBase.value; refreshPlan(); }
  return { ok: !!(r && r.ok), version: r && r.version, conflict: !!(r && r.conflict), message: oneLine((r && r.message) || "") };
}

/** @typedef {{ok: boolean, message?: string, made: number, done?: Record<string, any>[], apply_id?: number|null, approved?: number, waiting?: number[]}} TrackApproved */

/** #275: Approve minutes by the Track column, the one implementation (the minutes view's Approve minutes, Review's Approve and
    Approve n routine). The record is first brought in line with the Track column (track.reconcileOps: a cross is `remove`,
    neither `remove` with `keep_line`, a tick on a kept line `restore`), then the minutes and every ticked row are applied in one
    apply (/api/minutes/approve with track.approveArgs: `group` false and `own` the ticked rows' numbers, so an item the minutes
    show no row for, such as a promise, is never registered unseen and waits in Review, Cap's #268 review H1). `v` is the record's view answer, as
    on screen. `how.change` makes one change (the view's keeps its page in step; by default straight to /api/minutes/save, each
    on the version the last one made); `how.only` limits the changes to some items (Review's Approve n routine, one project's);
    `how.approve` false makes the changes only (the bulk rule: Approve n routine never approves the minutes); `how.mine` limits
    what is registered to some items (Review's Approve under one project of minutes covering several: the others wait in Review).
    The server checks it again (review.approve_minutes: never an item crossed, left with neither, or with no row).
    @param {MinutesView} v @param {{change?: (op: Record<string, any>) => Promise<{ok: boolean, message: string}>,
    only?: (n: number) => boolean, mine?: (n: number) => boolean, approve?: boolean}} [how] @returns {Promise<TrackApproved>} */
export async function trackApprove(v, how = {}) {
  const doc = v && v.ok ? v.doc : null, plan = v && v.plan ? v.plan.items : null;
  if (!doc || !plan || !v.path) return { ok: false, message: "These minutes have nothing pending.", made: 0 };
  const args = approveArgs(doc, plan);                     // review H1: only the ticked rows, never an item with no row
  if (how.approve !== false && v.proposal) {                // #324, #332: where they are filed and what they are called, before anything changes
    mountFiling();
    if (!(await askFiling(v.proposal))) return { ok: false, message: "Cancelled: nothing was filed or approved.", made: 0 };
  }
  let base = Number(doc.version) || undefined, made = 0; /** @type {Record<string, any>[]} */ const done = [];
  const change = how.change || (async (/** @type {Record<string, any>} */ op) => {
    const r = await api("/api/minutes/save", { path: v.path, op, base_version: base });
    if (r && r.ok) base = Number(r.version) || base;
    return { ok: !!(r && r.ok), message: oneLine((r && r.message) || "") };
  });
  for (const op of reconcileOps(doc, plan)) {
    if (how.only && !how.only(op.n)) continue;
    const r = await change(op);
    if (!r.ok) return { ok: false, message: r.message, made, done };
    made++; done.push(op);
  }
  if (how.approve === false) return { ok: true, made, done };
  if (!v.proposal) return { ok: false, message: "These minutes have nothing pending.", made };
  const r = await api("/api/minutes/approve", { file: v.proposal, group: args.group, own: how.mine ? args.own.filter(how.mine) : args.own });
  if (r && r.ok) noteNumbered(r.numbered);                    // #324: another meeting took the name first: the note says what it was filed as
  return { ...(r || { ok: false, message: "Nothing was saved or changed." }), made };
}

/** #275 round 3: the Track column's changes a trackApprove made (`done`, in order) taken back, newest first: a `remove` by
    `restore` (the item pending and its row back where it was), a `restore` by `remove` keeping the line (as the row was before).
    Used when the apply that was to carry them stops, so the minutes are exactly as they were. Each change on the version the
    last one made. @param {string} path the record's stored path @param {Record<string, any>[]} done
    @returns {Promise<{ok: boolean, message: string}>} */
export async function trackPutBack(path, done) {
  const cur = await api("/api/minutes/draft", { path });
  if (!cur || !cur.ok || !cur.doc) return { ok: false, message: oneLine((cur && cur.message) || "The minutes couldn't be read.") };
  let base = Number(cur.doc.version) || undefined;
  for (const op of [...done].reverse()) {
    const back = op.op === "remove" ? { op: "restore", n: op.n } : { op: "remove", n: op.n, keep_line: true };
    const r = await api("/api/minutes/save", { path, op: back, base_version: base });
    if (!r || !r.ok) return { ok: false, message: oneLine((r && r.message) || "") };
    base = Number(r.version) || base;
  }
  return { ok: true, message: "" };
}

/** What a failed trackApprove says (review M1: and that some of the Track column's changes were made). @param {TrackApproved} r
    @param {string} button the button to press again */
export const trackFailWords = (r, button) => (r.made ? `${r.message ? `${oneLine(r.message)} ` : ""}Some changes were made to the minutes; press ${button} again.`
  : String(r.message || "The minutes weren't approved; nothing was saved.").split("\n")[0]);

/** What an approve says: "Minutes approved · 3 work items registered · 1 still to check". @param {TrackApproved} r */
export function trackApprovedWords(r) {
  const n = r.approved || 0, left = (r.waiting || []).length;
  return `Minutes approved · ${n ? `${n} work item${n === 1 ? "" : "s"} registered` : "no work items registered"}${left ? ` · ${left} still to check` : ""}`;
}

/** Export the minutes as HTML, Word or PDF (P2's export, opened once made). #330: `version` "distributed" is the Shareable file
    (the server's distributed_of: no Sensitive, partner-only, excluded or Internal only content); anything else is the Internal one.
    @param {string} format @param {"internal"|"distributed"} [version] */
export async function exportMinutes(format, version = "internal") {
  const v = minutesView.value;
  if (!v || !v.ok || !v.path) return { ok: false, message: "The minutes aren't open." };
  return (await api("/api/minutes/export", { path: v.path, format, file_beside: true, version: version === "distributed" ? "distributed" : "internal" })) || { ok: false, message: "Not exported." };
}

/** #306: the words when the transcript has gone (review.HELD_MINUTES_WORDS). */
export const HELD_MINUTES_WORDS = "These minutes can't be filed yet: the transcript is no longer in your inbox. You can file the minutes without the transcript copy.";

/** #307: the minutes were filed or moved elsewhere while this view was open (the server's "That file isn't there." or "nothing pending"). */
export const MOVED_MINUTES_WORDS = "These minutes have moved or been filed. The list has been refreshed.";
export { isMovedMinutes };   /* defined in core/say.js (plain words), used here and by the tests */

/** #306: Approve minutes stopped because the transcript has left the inbox (the server's plain words say so). @param {string} m */
export const isHeldMinutes = m => /transcript is no longer in your inbox/.test(String(m || ""));

/** #306: file held minutes without the transcript copy, in place: the minutes and their ticked items in one go.
    @param {string} proposal the minutes' proposal file @returns {Promise<{ok: boolean, message: string, stale?: boolean, n?: number, apply_id?: number|null}>} */
export async function fileWithoutTranscript(proposal) {
  const held = REV.find(x => x.kind === "draft" && x.file === proposal);   /* 2.6.2 (#314): the server files these minutes only if they are still the ones on the page */
  const res = await api("/api/review", { file: proposal, ref: "meeting", decision: "approved", modes: ["without-transcript", "as-staged"], ...(held && held.fp ? { expect: held.fp } : {}) });
  if (res && !res.ok && REVIEW_CHANGED.test(res.message || "")) return { ok: false, stale: true, message: STALE_ROW_MSG };
  if (!res || !res.ok) return { ok: false, message: oneLine((res && res.message) || "creaite couldn't file these minutes").replace(/^\d+:\s*/, "").replace(/not approved — /, "") };
  const a = await applyNow();
  if (!a.ok) return { ok: false, message: oneLine(a.message || "creaite couldn't file these minutes") };
  const n = Number((String(a.message || "").match(/written (\d+)/) || [])[1] || 0);
  return { ok: true, message: "", n, apply_id: a.apply_id };
}
