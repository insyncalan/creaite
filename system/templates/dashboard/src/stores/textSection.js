// @ts-check
/* stores/textSection.js (H5, #218): what a report's text section needs beyond the sheet.

   - `addTextSection(afterId)`: the one entry point for "Add a text section" (the foot button, and any section menu that wants it): it
     adds an empty text section after the section `afterId` (null: at the end) of the report in the sheet, and puts the cursor in its
     heading. The sheet registers what it does (`bindTextSections`), so a caller needs no document.
   - the pictures: a text section's picture lives in the project's Reports folder under `_images/` (POST /api/report/image, system/scripts/
     report_server.py); the editor draws it from a data address read once (POST /api/report/images) and kept here by project and
     reference. The same 2 MB cap and PNG or JPEG rule as Notes. Nothing is sent anywhere. */
import { signal } from "@preact/signals";
import { api, oneLine, viaServer } from "../core/server.js";

/** @type {((afterId: string|null) => (string|null)) | null} */
let ADD = null;

/** The sheet says what adding a text section does (it returns the new section's id). Returns what undoes it.
    @param {(afterId: string|null) => (string|null)} fn */
export function bindTextSections(fn) {
  ADD = fn;
  return () => { if (ADD === fn) ADD = null; };
}

/** Add an empty text section after the section `afterId` (null: at the end) of the report in the sheet. True when the sheet took it.
    @param {string|null} [afterId] */
export function addTextSection(afterId = null) {
  if (!ADD) return false;
  const id = ADD(afterId == null ? null : afterId);
  if (id) NEW.id = id;
  return !!id;
}

/** The text section just added, whose heading takes the cursor when it is drawn (once). */
const NEW = { id: /** @type {string|null} */ (null) };
/** A text section was just added (by a menu): its heading takes the cursor when it is drawn. @param {string} id */
export const markNewText = id => { NEW.id = id; };
/** True once, for the section that was just added. @param {string} id */
export function takeNewText(id) {
  if (NEW.id !== id) return false;
  NEW.id = null;
  return true;
}

/** What went wrong with the last picture, as a plain sentence ("" when nothing did). */
export const textMsg = signal("");

/** @type {Map<string, Map<string, string>>} data addresses by project and report kind, then reference (v2.5.1, gap C: a client report
    draws only its own pictures, `_images/client-<name>`, so its map is its own) */
const PICS = new Map();
const mapOf = (/** @type {string} */ code, /** @type {string} */ kind = "") => {
  const key = `${code}|${kind === "client" ? "client" : ""}`;
  let m = PICS.get(key); if (!m) { m = new Map(); PICS.set(key, m); } return m; };

/** The `_images/…` pictures a text names, each once. @param {string} text @returns {string[]} */
export function imageRefsIn(text) {
  const out = new Set();
  for (const m of String(text || "").matchAll(/!\[[^\]\n]*\]\((_images\/[A-Za-z0-9][A-Za-z0-9._-]{0,120}\.(?:png|jpe?g))\)/gi)) out.add(m[1]);
  return [...out];
}

/** A picture's data address for the editor, or null while it isn't known. @param {string} code @param {string} ref @param {string} [kind] */
export const reportImageSrc = (code, ref, kind = "") => mapOf(code, kind).get(ref) || null;

/** Read the pictures `refs` names that aren't known yet (one call). @param {string} code @param {string[]} refs @param {string} [kind] */
export async function loadReportImages(code, refs, kind = "") {
  const m = mapOf(code, kind), want = refs.filter(r => !m.has(r));
  if (!want.length || !viaServer()) return;
  const r = await api("/api/report/images", { code, refs: want, kind: kind === "client" ? "client" : undefined });
  if (r && r.ok && r.images) for (const [k, v] of Object.entries(/** @type {Record<string, string>} */ (r.images))) m.set(k, v);
}

/** Add a picture to a project's reports: checked (PNG or JPEG, 2 MB at most), filed at once under `_images/` in its Reports folder by the
    live server; a client report's picture is its own (`_images/client-<name>`, v2.5.1 gap C). Returns its reference, or null (and says
    why in `textMsg`). @param {string} code @param {File} file @param {string} [kind] */
export async function addReportImage(code, file, kind = "") {
  if (!/^image\/(png|jpeg)$/.test(file.type)) { textMsg.value = `${file.name} can't be added: only PNG or JPEG pictures.`; return null; }
  if (file.size > 2 * 1024 * 1024) { textMsg.value = `${file.name} is over 2 MB: pictures can be 2 MB at most.`; return null; }
  if (!viaServer()) { textMsg.value = "Adding a picture needs the live server."; return null; }
  const src = await new Promise(res => { const fr = new FileReader(); fr.onload = () => res(String(fr.result || "")); fr.onerror = () => res(""); fr.readAsDataURL(file); });
  const r = src ? await api("/api/report/image", { code, name: file.name, data: String(src).slice(String(src).indexOf(",") + 1), kind: kind === "client" ? "client" : undefined }) : null;
  if (!r || !r.ok) { textMsg.value = oneLine((r && r.message) || `${file.name} couldn't be added.`); return null; }
  textMsg.value = "";
  mapOf(code, kind).set(r.ref, String(src));
  return /** @type {string} */ (r.ref);
}
