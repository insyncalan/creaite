// @ts-check
/* ClientView (v2.1.0 P8, BL-336; #221 H1): what is left of the client page once the Reporting hub (components/report/hub/) replaced it.
   The client report's pieces the hub uses: the left-out check before an export (openCheck, doExport), Match internal (stores/clientReport.js matchInternal, behind the client gate), the
   health suggestion's apply (clientHealthApply) and the old #client-report=CODE/week/client address (parseKey), which the hub still
   reads. Client safety is unchanged: the page only ever holds what the server built from client-visible items (report_doc.client_doc,
   through client_leak.make_safe) and what Alan typed; Match internal copies only what clientDoc.matchClientSection allows; the server
   checks again at save, approve and export. Nothing here sends anything. */
import { CLIENT_RENDERERS, setClientDoc } from "./ClientParts.jsx";
import { CLIENT_EXPORT, reportExportPage } from "./exportPage.jsx";
import { flagOf, healthDiff } from "./clientDoc.js";
import { crAskWhy } from "./ClientParts.jsx";
import { snack } from "../../core/server.js";
import { crBase, crDialog, crDirty, crDoc, crInternal, exportClientReport, runCheck, saveClientPage } from "../../stores/clientReport.js";

/** @typedef {import("./Sheet.jsx").SheetDoc} SheetDoc */

/** Save any page edits, run the left-out check and open it. */
export async function openCheck() {
  const d = crDoc.value;
  if (!d) return;
  if (crDirty.value) { const s = await saveClientPage({ doc: d, base_version: crBase.value }); if (!s.ok) { snack(String(s.message || "The report wasn't saved").split("\n")[0]); return; } }
  crDialog.value = true;
  await runCheck();
}

/** @param {"html"|"docx"|"pdf"} fmt */
export async function doExport(fmt) {
  const r = await exportClientReport(fmt, (d, v) => reportExportPage(d, CLIENT_RENDERERS, CLIENT_EXPORT, v));
  if (r && (r.ok || r.clash)) crDialog.value = false;       // saved (the message says where) or a taken name (its own dialog asks)
  else await runCheck();                                      // a refusal: the check shows why, and the message says nothing was written
}

/** Ask for the reason (the flag's popover opens on it) when the new flag differs from the internal one. @param {string} health */
const askWhy = health => { if (crInternal.value && flagOf(/** @type {SheetDoc} */ (crInternal.value)) !== health) crAskWhy.value = true; };
/** #203: Use on the client sheet's health suggestion: the client's flag and headline, and why the flag differs from the internal one when
    it does. The reason is left empty: Alan writes why in the flag's popover (kept internally, never on the client's page). @param {{health: string, reason: string}} d */
export const clientHealthApply = d => (/** @type {SheetDoc} */ doc, /** @type {{id: string}} */ s) => (askWhy(d.health), {
  ...doc, sections: doc.sections.map(x => x.id === s.id ? { ...x, text: d.reason, data: { ...((/** @type {any} */ (x)).data || {}), flag: d.health } } : x),
  meta: healthDiff(doc, crInternal.value ? flagOf(/** @type {SheetDoc} */ (crInternal.value)) : d.health, d.health, "") });

/** @param {string} text @returns {{code: string, week?: string, client?: string}|null} */
export function parseKey(text) {
  const m = /^([A-Z][A-Z0-9]{2,6})(?:\/(\d{4}-\d{2}-\d{2}))?(?:\/(.*))?$/.exec(String(text || ""));
  if (!m) return null;
  let client = "";
  try { client = decodeURIComponent(m[3] || ""); } catch (e) { return null; }
  return { code: m[1], week: m[2] || undefined, client: client || undefined };
}
