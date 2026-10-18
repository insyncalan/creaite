// @ts-check
/* stores/exportSave.js (#220): saving a report export. The server decides (/api/report/export saves into the project's Reports folder
   through filechange.py, and answers a taken name with `clash`); the page asks and passes the choice back as `on_clash`. One store
   for the weekly and the client report: the dialog, the "Saved … in <project> › Reports" message and a failed save's message. */
import { signal } from "@preact/signals";
import { api } from "../core/server.js";

/** @typedef {{ok: boolean, message?: string, clash?: boolean, saved?: boolean, name?: string, numbered?: string, path?: string,
    folder?: string, folder_label?: string, replaced?: boolean}} ExportAnswer */

/** A taken name waiting for Alan's choice: the request to send again, and the server's answer. */
export const exportClash = signal(/** @type {{body: Record<string, any>, r: ExportAnswer}|null} */ (null));
/** The last save, for the message with the folder link, Show in Finder and Open. */
export const exportSaved = signal(/** @type {ExportAnswer|null} */ (null));
/** Why the last save failed (plain words; nothing was written). */
export const exportFailed = signal("");

/** Ask the server to export and save. A taken name opens the dialog (nothing written); a save shows the message; a failure says why.
    Returns the server's answer. @param {Record<string, any>} body {kind, code, week_ending, client?, fmt, on_clash?, new_name?} */
export async function saveExport(body) {
  exportFailed.value = "";
  /** @type {ExportAnswer} */
  const r = (await api("/api/report/export", body)) || { ok: false, message: "Not saved: creaite didn't answer. Nothing was written." };
  if (r.ok) { exportClash.value = null; exportSaved.value = r; }
  else if (r.clash) { exportSaved.value = null; exportClash.value = { body, r }; }
  else { exportClash.value = null; exportSaved.value = null; exportFailed.value = String(r.message || "Not saved. Nothing was written.").split("\n")[0]; }
  return r;
}

/** Alan's choice in the dialog. @param {"number"|"rename"|"overwrite"} choice @param {string} [newName] */
export async function answerClash(choice, newName) {
  const c = exportClash.value;
  if (!c) return null;
  return saveExport({ ...c.body, on_clash: choice, ...(choice === "rename" ? { new_name: newName } : {}) });
}

/** Cancel: nothing is saved. */
export function cancelClash() { exportClash.value = null; }

/** The link on the message: open the folder. @param {string} folder */
export const openFolder = (folder) => api("/api/open", { path: folder });
/** Show in Finder. @param {string} path */
export const showInFinder = (path) => api("/api/report/reveal", { path });
/** Open the saved file. @param {string} path */
export const openSaved = (path) => api("/api/open", { path });
