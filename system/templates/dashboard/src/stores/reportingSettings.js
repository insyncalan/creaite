// @ts-check
/* stores/reportingSettings.js (H3 of the Reporting hub, #221): a project's "This project needs a separate client report" setting,
   the reminder, the logos ticked for the header and the client's name; and the logo files themselves.

   Stored on the project, in its CLAUDE.md beside the client-report rhythm, and written the way the rhythm is (setMemLine in
   core/server.js: the vault, a copy of the file first, a settings-log line). "- **Client report:** on|off",
   "- **Client report reminder:** on|off", "- **Client report logos:** firm, client, partner". A project with no such line is on, its
   reminder is on and every logo is ticked (the way projects were before the setting); a new project is made with it off.
   There is no per-week question: the setting holds for every future report. Turning it off deletes nothing.

   The same functions serve the hub's panel (components/report/hub/ClientReportPanel.jsx) and Settings › Projects, so there is one
   setting. The logo files are in the live vault's system/branding/logos/, saved by /api/report/logo/save (report_server.py). */
import { signal } from "@preact/signals";
import { P, REMINDERS } from "../core/data.js";
import { api, oneLine, plainPaths, setMemLine, setRhythm, snack, viaServer } from "../core/server.js";
import { weeklyLogos } from "./weekly.js";
import { repTick } from "./reporting.js";

export const LOGO_KINDS = /** @type {const} */ (["firm", "client", "partner"]);
/** @typedef {"firm"|"client"|"partner"} LogoKind */

/** bumped when a setting changes, so an open panel or Settings row redraws */
export const crTick = signal(0);
/** @param {string} code */
const project = code => /** @type {any} */ (P.find(p => p.code === code));

/** Whether the project needs a separate client report (on unless its CLAUDE.md says off). @param {string} code */
export const clientReportOn = code => { const p = project(code); return !p || p.cr !== false; };
/** The cog's tooltip and screen-reader name. @param {string} code */
export const clientReportCogLabel = code => `Client report settings: ${clientReportOn(code) ? "on" : "off"}`;
/** Whether a reminder is wanted on the client report's due day. @param {string} code */
export const clientReminderOn = code => { const p = project(code); return !p || p.crrem !== false; };
/** The logos ticked for the header of this project's reports, the firm's first. @param {string} code @returns {LogoKind[]} */
export function clientLogosOn(code) {
  const p = project(code), l = p && Array.isArray(p.crlogos) ? p.crlogos : LOGO_KINDS;
  return LOGO_KINDS.filter(k => k === "firm" || l.includes(k));
}

/** The pages and reminders that follow the setting redraw. */
function changed() { crTick.value++; repTick.value++; }

/** Switch the project's client report on or off. Off deletes nothing and drops its client reminders; on restores the client side.
    @param {string} code @param {boolean} on @returns {Promise<boolean>} saved */
export async function setClientReport(code, on) {
  const p = project(code); if (!p) return false;
  if (!await setMemLine(code, "Client report", on ? "on" : "off", "client_report")) return false;
  p.cr = on;
  if (!on) for (let i = REMINDERS.length - 1; i >= 0; i--) if (String(REMINDERS[i].id).startsWith(`client:${code}:`)) REMINDERS.splice(i, 1);
  changed(); return true;
}

/** @param {string} code @param {boolean} on @returns {Promise<boolean>} */
export async function setClientReminder(code, on) {
  const p = project(code); if (!p) return false;
  if (!await setMemLine(code, "Client report reminder", on ? "on" : "off", "client_report_reminder")) return false;
  p.crrem = on; changed(); return true;
}

/** @param {string} code @param {LogoKind[]} kinds the ticked logos (the firm's is always kept) @returns {Promise<boolean>} */
export async function setClientLogos(code, kinds) {
  const p = project(code); if (!p) return false;
  const list = LOGO_KINDS.filter(k => k === "firm" || kinds.includes(k));
  if (!await setMemLine(code, "Client report logos", list.join(", "), "client_report_logos")) return false;
  p.crlogos = list; changed(); return true;
}

export const CLIENT_NAME_MAX = 80;
/** @param {string} code @param {string} name the client's name on the report @returns {Promise<boolean>} */
export async function setClientName(code, name) {
  const p = project(code); if (!p) return false;
  if (/[\r\n]/.test(String(name || ""))) { snack("Not saved: the client's name is one line."); return false; }     // a newline would end the line in CLAUDE.md
  const v = String(name || "").replace(/\s+/g, " ").trim();
  if (v.length > CLIENT_NAME_MAX) { snack(`Not saved: the client's name is over ${CLIENT_NAME_MAX} characters.`); return false; }
  if (!await setMemLine(code, "Client / partner", v, "client_name")) return false;
  p.client = v; changed(); return true;
}

/** How often: weekly, fortnightly or monthly (the rhythm Settings already has). @param {string} code @param {string} val */
export async function setClientRhythm(code, val) {
  const p = project(code); if (!p) return false;
  if (!await setRhythm(code, val)) return false;
  p.rhythm = val; changed(); return true;
}

// ----- the logo files -----

/** each logo kind's stored path, and each path's picture as data, for the project last read */
export const crLogoPaths = signal(/** @type {Record<string, string>} */ ({}));
export const crLogoData = signal(/** @type {Record<string, string>} */ ({}));
/** the last thing the logo controls have to say (a JPEG hint, a refusal) */
export const crLogoNote = signal("");
/** the project whose logo files crLogoPaths holds (the report header trusts the paths only for its own project) */
export const crLogoFor = signal("");

/** Read the project's logo files as data. @param {string} code */
export async function readClientLogos(code) {
  if (!viaServer()) return;
  const r = await api("/api/report/logo", { code });
  if (!r || !r.ok) return;
  crLogoFor.value = code;
  crLogoPaths.value = Object.fromEntries((r.list || []).map((/** @type {{kind: string, path: string}} */ x) => [x.kind, x.path]));
  crLogoData.value = r.logos || {};
  weeklyLogos.value = { ...weeklyLogos.peek(), ...(r.logos || {}) };      // the report headers draw the new picture too
  changed();
}

/** @param {Blob} blob @returns {Promise<string>} the base64 of the blob */
function toBase64(blob) {
  return new Promise((resolve, reject) => {
    const fr = new FileReader();
    fr.onload = () => resolve(String(fr.result).replace(/^data:[^,]*,/, ""));
    fr.onerror = () => reject(fr.error);
    fr.readAsDataURL(blob);
  });
}

const MARGIN_WHITE = 245, MARGIN_ALPHA = 8, DRAWN_MAX = 540;

/** The box of a picture's pixels that are not transparent and not white, or null when there is nothing to trim.
    @param {Uint8ClampedArray} px @param {number} w @param {number} h @returns {{x: number, y: number, w: number, h: number}|null} */
export function contentBox(px, w, h) {
  let x0 = w, y0 = h, x1 = -1, y1 = -1;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const i = (y * w + x) * 4;
    if (px[i + 3] <= MARGIN_ALPHA || (px[i] >= MARGIN_WHITE && px[i + 1] >= MARGIN_WHITE && px[i + 2] >= MARGIN_WHITE)) continue;
    if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y;
  }
  if (x1 < 0) return null;
  const box = { x: x0, y: y0, w: x1 - x0 + 1, h: y1 - y0 + 1 };
  return box.w === w && box.h === h ? null : box;
}

/** A PNG with the empty margins (transparent or white) trimmed, for a PNG or JPEG file; null when there is nothing to trim or
    the browser can't read the picture. The file chosen is not touched. @param {File} file @returns {Promise<Blob|null>} */
export async function trimmedCopy(file) {
  try {
    const bmp = await createImageBitmap(file), c = /** @type {any} */ (document.createElement("canvas"));
    c.width = bmp.width; c.height = bmp.height;
    const g = /** @type {CanvasRenderingContext2D} */ (c.getContext("2d", { willReadFrequently: true }));
    g.drawImage(bmp, 0, 0);
    const box = contentBox(g.getImageData(0, 0, c.width, c.height).data, c.width, c.height);
    if (!box) return null;
    const k = Math.min(1, DRAWN_MAX / Math.max(box.w, box.h)), out = document.createElement("canvas");
    out.width = Math.max(1, Math.round(box.w * k)); out.height = Math.max(1, Math.round(box.h * k));
    /** @type {CanvasRenderingContext2D} */ (out.getContext("2d")).drawImage(c, box.x, box.y, box.w, box.h, 0, 0, out.width, out.height);
    return await new Promise(res => out.toBlob(res, "image/png"));
  } catch { return null; }
}

/** Add or change a logo from the screen: the file is kept as chosen, the margins are trimmed on the copy that is drawn, and the
    file is saved into system/branding/logos/ under the right name. @param {string} code @param {LogoKind} kind @param {File} file
    @returns {Promise<boolean>} saved */
export async function uploadClientLogo(code, kind, file) {
  crLogoNote.value = "";
  const ext = (/\.(png|jpe?g|svg)$/i.exec(file.name) || ["", ""])[1].toLowerCase().replace("jpeg", "jpg");
  if (!ext) { crLogoNote.value = "Choose a PNG, JPEG or SVG picture."; return false; }
  if (file.size > 400000) { crLogoNote.value = "That logo is over 400 kB. Choose a smaller file."; return false; }
  const trimmed = ext === "svg" ? null : await trimmedCopy(file);
  const r = await api("/api/report/logo/save", { code, kind, ext, original: await toBase64(file), drawn: trimmed ? await toBase64(trimmed) : undefined });
  if (!r || !r.ok) { crLogoNote.value = oneLine(plainPaths(r && r.message)) || "The logo was not saved."; return false; }
  crLogoNote.value = r.hint || "";
  await readClientLogos(code); snack(r.message || "Logo saved");
  return true;
}

/** @param {string} code @param {LogoKind} kind @returns {Promise<boolean>} */
export async function removeClientLogo(code, kind) {
  crLogoNote.value = "";
  const r = await api("/api/report/logo/remove", { code, kind });
  if (!r || !r.ok) { crLogoNote.value = oneLine(plainPaths(r && r.message)) || "The logo was not removed."; return false; }
  await readClientLogos(code); snack(r.message || "Logo removed");
  return true;
}
