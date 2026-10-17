// @ts-check
/* stores/weekly.js (v2.1.0 P6, BL-335, dev/COMPONENTS.md §2): the weekly report view's state, one store for the area.
   Everything comes from P3's routes (system/scripts/report_server.py): /api/report/draft (the report to edit: its draft, else the
   filed report, else a new one built from the tracker; nothing is written until Save), /save (the page as the draft; a filed
   report is never changed in place), /approve (one proposal applied with the one writer) and /export; plus /api/report/logo
   (the project's logo files, read only). Nothing here sends anything. */
import { signal } from "@preact/signals";
import { api, oneLine, viaServer } from "../core/server.js";

/** @typedef {import("../components/report/Sheet.jsx").SheetDoc} SheetDoc */
/** @typedef {{ok: boolean, message?: string, doc?: SheetDoc, path?: string, where?: string, version?: number, filed?: boolean,
    logos?: {kind: string, path: string}[]}} WeeklyView */

/** What the view was opened with: the project's code and the week ending (a Friday, YYYY-MM-DD, or none for this week's). */
export const weeklyArg = signal(/** @type {{code: string, week?: string}|null} */ (null));
/** The route's answer, as it came. */
export const weeklyView = signal(/** @type {WeeklyView|null} */ (null));
/** The document on screen (the view keeps it; the sheet hands back a new one on every edit). */
export const weeklyDoc = signal(/** @type {SheetDoc|null} */ (null));
/** The version the page was opened at, sent with each save. */
export const weeklyBase = signal(/** @type {number|undefined} */ (undefined));
export const weeklyBusy = signal("");
/** An approved report opened to change (Edit again): its first save starts a new draft. */
export const weeklyEditing = signal(false);
/** The logo files as data, by their stored path (read once per project). */
export const weeklyLogos = signal(/** @type {Record<string, string>} */ ({}));

let wkAsked = 0;
/** Open (or reload) the weekly report. @param {{code: string, week?: string}} arg @param {boolean} [fresh] build it again from the tracker */
export async function loadWeekly(arg, fresh = false) {
  const mine = ++wkAsked;
  weeklyArg.value = arg; weeklyEditing.value = false;
  if (!viaServer()) { weeklyView.value = { ok: false, message: "The weekly report view needs the live server." }; return; }
  weeklyBusy.value = "Opening the weekly report…";
  const r = await api("/api/report/draft", { kind: "weekly", code: arg.code, week_ending: arg.week || undefined, fresh: fresh || undefined });
  if (mine !== wkAsked) return;
  weeklyBusy.value = "";
  takeWeekly(r && r.ok ? r : { ok: false, message: oneLine((r && r.message) || "") || "Couldn't open the weekly report" });
  if (r && r.ok) readLogos(arg.code, r.logos || []);
}

/** Take a route's answer onto the page. @param {WeeklyView} r */
function takeWeekly(r) {
  weeklyView.value = r;
  weeklyDoc.value = r.ok && r.doc ? r.doc : null;
  weeklyBase.value = r.ok && r.doc ? Number(r.doc.version) || undefined : undefined;
}

/** The logo files for the project, as data (once each). @param {string} code @param {{kind: string, path: string}[]} logos */
async function readLogos(code, logos) {
  const have = weeklyLogos.value, want = logos.filter(l => !(l.path in have));
  if (!want.length) return;
  const r = await api("/api/report/logo", { code, paths: want.map(l => l.path) });
  if (r && r.ok && r.logos) weeklyLogos.value = { ...weeklyLogos.peek(), ...r.logos };
}

/** The sheet's save: the page as Alan edited it, as the draft. @param {{doc: SheetDoc, base_version: number|undefined}} req */
export async function saveWeekly(req) {
  const r = await api("/api/report/save", { doc: req.doc, base_version: req.base_version });
  const ok = !!(r && r.ok);
  if (ok) {
    weeklyBase.value = Number(r.version) || weeklyBase.value;
    const v = weeklyView.value; if (v) weeklyView.value = { ...v, where: "draft", filed: !!r.filed };
  }
  return { ok, version: r && r.version, conflict: !!(r && r.conflict), message: oneLine((r && r.message) || ""), removed: r && r.removed };
}

/** Approve and file: the page's edits saved, one proposal staged and applied. @param {SheetDoc} doc @param {boolean} [force] */
export async function approveWeekly(doc, force) {
  const a = weeklyArg.value;
  const r = await api("/api/report/approve", { kind: "weekly", code: doc.project || (a && a.code), week_ending: doc.date, doc,
    base_version: weeklyBase.value, force: force || undefined });
  return r || { ok: false, message: "The apply didn't run; nothing was changed." };
}

/** Export the saved report as html, docx or pdf (P2's export, opened once made). @param {SheetDoc} doc @param {string} fmt */
export async function exportWeekly(doc, fmt) {
  const r = await api("/api/report/export", { kind: "weekly", code: doc.project, week_ending: doc.date, fmt });
  return r || { ok: false, message: "Not exported." };
}

/** Unsaved edits on the page (the sheet saves them; Approve and Export save first). */
export let weeklyDirty = false;
export const setWeeklyDirty = (/** @type {boolean} */ on) => { weeklyDirty = on; };

/** Every edit from the sheet or a section: the whole new document, kept on the page. @param {SheetDoc} d @param {string} [_why] */
export function editDoc(d, _why) { weeklyDoc.value = d; weeklyDirty = true; }
