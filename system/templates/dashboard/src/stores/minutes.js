// @ts-check
/* stores/minutes.js (v2.1.0 P7, BL-338, dev/COMPONENTS.md §2): the minutes view's state, one store for the area.
   Everything comes from P4's routes: /api/minutes/draft (the record, its versions, the transcript's turns and, while its items
   are pending, the approve popup's plan), /api/minutes/save (the page as a new version, or one row or coverage change: the
   record and its proposal change together), /api/minutes/approve (the minutes and the ticked items in one apply) and
   /api/minutes/export. Nothing here writes any other way; nothing is sent. */
import { signal } from "@preact/signals";
import { api, oneLine, viaServer } from "../core/server.js";

/** @typedef {import("../components/report/Sheet.jsx").SheetDoc} SheetDoc */
/** @typedef {{n: number, who: string|null, start: string|null, end: string|null, text: string}} Turn */
/** @typedef {{version: number, current: boolean, at?: string, change?: number, why?: string, backup?: string}} Version */
/** @typedef {{n: number, group: string, why: string|null, label: string}} PlanItem */
/** @typedef {{files: string[], transcripts: string[], items: PlanItem[], group: number, joins: string[]}} Plan */
/** @typedef {{ok: boolean, message?: string, path?: string, doc?: SheetDoc, versions?: Version[],
    turns?: {timed: boolean, turns: Turn[]}, proposal?: string|null, plan?: Plan|null, labels?: Record<string, string[]>,
    withheld?: Record<string, string>}} MinutesView */

/** What the view was opened with: {file} (the proposal) or {path} (the record). */
export const minutesArg = signal(/** @type {{file?: string, path?: string}|null} */ (null));
/** The route's answer, as it came. */
export const minutesView = signal(/** @type {MinutesView|null} */ (null));
/** The document on screen (the view keeps it; the sheet hands back a new one on every edit). */
export const minutesDoc = signal(/** @type {SheetDoc|null} */ (null));
/** The version the page was opened at, sent with each save. */
export const minutesBase = signal(/** @type {number|undefined} */ (undefined));
export const minutesBusy = signal("");
/** The transcript pane: open, the turn picked from a time tag, the words searched for. */
export const paneOpen = signal(true);
export const paneTurn = signal(/** @type {number|null} */ (null));
export const paneQuery = signal("");
/** Checks Alan kept his words on (Keep mine), by check id, for this page's life. */
export const keptChecks = signal(/** @type {string[]} */ ([]));
/** Internal, Distributed or Side by side, when the distributed version is on. */
export const minutesMode = signal(/** @type {"internal"|"distributed"|"side"} */ ("internal"));
export const approveOpen = signal(false);

let mnAsked = 0;
/** Open (or reload) the minutes: by the proposal's file name or the record's stored path.
    @param {{file?: string, path?: string}} arg */
export async function loadMinutes(arg) {
  const mine = ++mnAsked;
  minutesArg.value = arg;
  if (!viaServer()) { minutesView.value = { ok: false, message: "The minutes view needs the live server." }; return; }
  minutesBusy.value = "Opening the minutes…";
  const r = await api("/api/minutes/draft", arg);
  if (mine !== mnAsked) return;
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

/** Approve the minutes and the ticked items in one apply. @param {boolean} group @param {number[]} own */
export async function approveMinutes(group, own) {
  const v = minutesView.value;
  if (!v || !v.ok || !v.proposal) return { ok: false, message: "These minutes have nothing pending." };
  const r = await api("/api/minutes/approve", { file: v.proposal, group, own });
  return r || { ok: false, message: "The apply didn't run; nothing was changed." };
}

/** Export the minutes as HTML, Word or PDF (P2's export, opened once made); `version` "distributed" exports the distributed
    version (the approved minutes only; filed under a new name, never over a file). @param {string} format @param {"internal"|"distributed"} [version] */
export async function exportMinutes(format, version = "internal") {
  const v = minutesView.value;
  if (!v || !v.ok || !v.path) return { ok: false, message: "The minutes aren't open." };
  return (await api("/api/minutes/export", { path: v.path, format, file_beside: true, version })) || { ok: false, message: "Not exported." };
}
