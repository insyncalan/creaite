// @ts-check
/* stores/hub.js (#221 H1): the Reporting hub's own state: which report is in view (Internal, Client or Side by side), the zoom and
   Show as exported that the one toolbar shares, whether the cog's panel is open, and the opening of the week: the internal report
   through stores/weekly.js and, when the project has a client report (stores/reportingSettings.js), the client report through
   stores/clientReport.js. Nothing here writes; Export and Approve call those two stores. */
import { signal } from "@preact/signals";
import { viaServer } from "../core/server.js";
import { SHEET_ZOOM_DEFAULT } from "../components/report/sheetLib.js";
import { crDoc, crInfo, crInternal, crOpen, loadClientReport } from "./clientReport.js";
import { clientReportOn } from "./reportingSettings.js";
import { setWeeklyDirty, weeklyDoc, loadWeekly } from "./weekly.js";

/** @typedef {"internal"|"client"|"side"} HubView */

/** What is in view. */
export const hubView = signal(/** @type {HubView} */ ("internal"));
/** The zoom both sheets share (the sheet's own scale: 0.4 to 0.8, the top being Fit). */
export const hubZoom = signal(SHEET_ZOOM_DEFAULT);
/** Show as exported. */
export const hubExported = signal(false);
/** The cog's panel is open. */
export const hubCfg = signal(false);
/** What the last client approval said, when it wasn't a yes (with "Approve anyway" for a check awaiting review). */
export const hubNote = signal("");
/** What is open: "<code>|<week asked>|<client report on>" once both documents are in, else "". */
export const hubReady = signal("");
/** The code and week the hub was asked for (week "" = the latest). */
export const hubAsk = signal(/** @type {{code: string, week: string}|null} */ (null));

let hubAsked = 0;

/** The key a loaded hub carries. @param {string} code @param {string} week */
export const hubKey = (code, week) => `${code}|${week}|${clientReportOn(code) ? 1 : 0}`;

/** Open the week: the internal report, then (the project having one) the client report for the same week.
    @param {string} code @param {string} [week] YYYY-MM-DD, or none for the latest */
export async function loadHub(code, week = "") {
  const mine = ++hubAsked;
  hubAsk.value = { code, week };
  hubReady.value = "";
  hubNote.value = "";
  setWeeklyDirty(false);
  await loadWeekly({ code, week: week || undefined });
  if (mine !== hubAsked) return;
  const d = weeklyDoc.value, date = (d && d.date) || week;
  if (clientReportOn(code) && viaServer()) await loadClientReport({ code, week: date || undefined });
  else { crDoc.value = null; crInternal.value = null; crInfo.value = null; crOpen.value = null; }
  if (mine !== hubAsked) return;
  hubReady.value = hubKey(code, week);
}

/** Open the hub again for what it shows (after an approval changes the facts the client report locks to). */
export function reloadHub() {
  const a = hubAsk.value;
  return a ? loadHub(a.code, a.week) : Promise.resolve();
}
