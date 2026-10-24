// @ts-check
/* stores/minutesFiling.js (#324, #326, #332): where minutes will be filed and under what name, and opening them afterwards.
   The server decides (minutes_destination.py: /api/minutes/destination, /name, /where, /open); this asks and passes the choice back.
   Approve minutes asks first (askFiling): the project and folder in words, the name in a field (the extension fixed, a taken name
   already numbered), the transcript beside it. Cancel files nothing. After an approve, a note says where they went, with Open file and
   Open folder (the same call Approved this week's Open folder makes). Nothing here shows or sends a path: only a project's name and
   its folder's name, and the server opens only what it finds in the project's own Minutes folder. The dialog and the note are drawn
   by components/minutes/FilingDialog.jsx. */
import { signal } from "@preact/signals";
import { api, oneLine } from "../core/server.js";
import { REV } from "../core/data.js";

/** @typedef {{code: string, project: string, folder_label: string, name: string, ext: string, taken: boolean, numbered: string|null,
    will_be: string, local: boolean, filed_copy?: boolean, transcript: {name: string, will_be: string, folder_label: string}|null}} Destination */
/** @typedef {{file: string, key: string|null, items: Destination[], typed: Record<string, string>, resolve: (ok: boolean) => void}} Ask */

/** The question on screen, or null. */
export const filingAsk = signal(/** @type {Ask|null} */ (null));
/** Why a name was refused (plain words, in the dialog). */
export const filingError = signal("");
/** Where the last approved minutes went. */
export const filedNote = signal(/** @type {{key: string|null, items: {code: string, project: string, folder_label: string, name: string}[], numbered?: string[]}|null} */ (null));
/** Why Open file or Open folder could not (plain words, in the note). */
export const filedProblem = signal("");

/** The name without its extension. @param {string} name @param {string} ext */
export const stemOf = (name, ext) => (ext && name.toLowerCase().endsWith(ext) ? name.slice(0, -ext.length) : name);

/** Ask where the minutes will be filed and let Alan change the name. Resolves true to go on (a changed name is already in the
    proposal), false when he cancels. A proposal the server can't read goes on: the approve says why.
    @param {string} proposal @returns {Promise<boolean>} */
export async function askFiling(proposal) {
  const r = await api("/api/minutes/destination", { file: proposal });
  if (!r || !r.ok || !Array.isArray(r.items) || !r.items.length) return true;
  filingError.value = ""; filedNote.value = null; filedProblem.value = "";
  return new Promise(resolve => {
    /** @type {Record<string, string>} */ const typed = {};
    for (const it of r.items) typed[it.code] = stemOf(it.will_be, it.ext);
    filingAsk.value = { file: proposal, key: r.key || null, items: r.items, typed, resolve };
  });
}

/** The field changed. @param {string} code @param {string} value */
export function typeFiling(code, value) {
  const a = filingAsk.value;
  if (a) filingAsk.value = { ...a, typed: { ...a.typed, [code]: value } };
  filingError.value = "";
}

/** File and approve: the names that differ go to the server in one call (all or none: a refusal changes nothing, so the box always
    matches what is staged), which stays in the box in words. */
export async function confirmFiling() {
  const a = filingAsk.value;
  if (!a) return;
  /** @type {Record<string, string>} */ const names = {};
  for (const it of a.items) {
    const stem = (a.typed[it.code] || "").trim();
    if (stem !== stemOf(it.will_be, it.ext)) names[it.code] = stem + it.ext;
  }
  /** @type {Record<string, string>} */ let used = {};
  if (Object.keys(names).length) {
    const r = await api("/api/minutes/destination/name", { file: a.file, names });
    if (!r || !r.ok) { filingError.value = oneLine((r && r.message) || "That name can't be used."); return; }
    used = r.names || {};
    keepFingerprints(a.file, r.fps);
  }
  const shown = a.items.map(it => ({ code: it.code, project: it.project, folder_label: it.folder_label, name: used[it.code] || it.will_be }));
  filingAsk.value = null;
  filedNote.value = { key: a.key, items: shown };
  a.resolve(true);
}

/** 2.6.4 (#346): a new name changes what each of the meeting's items says about where it came from, so the server sends their
    fingerprints again and the open Review rows take them (otherwise the next decision on one would be declined until a reload).
    @param {string} file @param {Record<string, string>|undefined} fps by item number */
export function keepFingerprints(file, fps) {
  if (!fps) return;
  for (const r of REV) if (r.file === file && Object.prototype.hasOwnProperty.call(fps, String(r.ref))) r.fp = fps[String(r.ref)];
}

/** The approve numbered a name after all (another pending meeting took it first): the note says the name it was filed under.
    @param {{code: string, name: string, was: string, kind: string}[]|undefined} moved */
export function noteNumbered(moved) {
  const n = filedNote.value;
  if (!n || !moved || !moved.length) return;
  const said = [];
  const updated = n.items.map(i => {
    const m = moved.find(x => x.kind === "draft" && x.code === i.code);
    if (m && m.name !== i.name) said.push(m.name);          // only when it differs from what the box showed
    return m ? { ...i, name: m.name } : i;
  });
  filedNote.value = { ...n, items: updated, numbered: said };
}

/** Cancel: nothing is filed or approved. */
export function cancelFiling() {
  const a = filingAsk.value;
  filingAsk.value = null; filingError.value = ""; filedNote.value = null;
  if (a) a.resolve(false);
  /* Approve minutes is disabled while it waits for the box, so the dialog can't give focus back to it: put it there once it is enabled */
  for (const ms of [60, 300]) setTimeout(() => {
    const b = typeof document === "undefined" ? null : document.getElementById("mnApproveBtn");
    if (b && !b.disabled && document.activeElement === document.body) b.focus();
  }, ms);
}

/** The note is dismissed. */
export function dismissFiled() { filedNote.value = null; filedProblem.value = ""; }

/** Open the minutes, or show them in Finder (Open file, Open folder, Approved this week's Open folder): the server finds them in the
    project's own Minutes folder and answers in words when it can't. @param {"file"|"folder"} what @param {{key?: string|null, path?: string|null}} where
    @returns {Promise<{ok: boolean, message: string}>} */
export async function openFiled(what, where) {
  const r = await api("/api/minutes/destination/open", { what, key: where.key || undefined, path: where.path || undefined });
  const ok = !!(r && r.ok);
  return { ok, message: oneLine((r && r.message) || "") || (ok ? "" : "The minutes can't be opened.") };
}
