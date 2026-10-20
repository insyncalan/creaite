// @ts-check
/* hubActions.js (#221 H1): what the hub's Export and Approve do. They call the two report stores (stores/weekly.js for the internal
   report, stores/clientReport.js for the client report) and the export save flow (stores/exportSave.js), exactly as the weekly and
   the client pages did; nothing new is sent anywhere. */
import { effect } from "@preact/signals";
import { snack } from "../../../core/server.js";
import { approveClientReport, crDialog, exportClientReport, runCheck } from "../../../stores/clientReport.js";
import { exportClash, exportSaved } from "../../../stores/exportSave.js";
import { hubNote, reloadHub } from "../../../stores/hub.js";
import { approveWeekly, exportWeekly, weeklyBase, weeklyDoc } from "../../../stores/weekly.js";
import { WEEKLY_RENDER, saveFirst } from "../weekly/WeeklyView.jsx";
import { WEEKLY_EXPORT, reportExportPage } from "../exportPage.jsx";

/** Resolves true when the name-clash dialog was answered with a save, false when it was cancelled. */
function clashAnswered() {
  return new Promise(resolve => {
    const stop = effect(() => { if (!exportClash.value) queueMicrotask(() => { stop(); resolve(!!exportSaved.value); }); });
  });
}

/** Export the report(s) in `which` as `fmt`. "Both" saves two files, each with its own name-clash choice, and one message naming both.
    @param {"html"|"docx"|"pdf"} fmt @param {"internal"|"client"|"both"} which */
export async function hubExport(fmt, which) {
  const doc = weeklyDoc.value;
  let first = "";
  if (which !== "client") {
    if (!doc || !(await saveFirst())) return;
    const now = weeklyDoc.value || doc;
    const page = fmt === "docx" ? null : await reportExportPage(now, WEEKLY_RENDER, WEEKLY_EXPORT, weeklyBase.value);   // #226: the exported page itself
    const r = await exportWeekly(now, fmt, page);           // the dialog, the "Saved … in <project> › Reports" message or the failure show themselves (ExportSave)
    if (which === "internal") return;
    if (r && r.clash) { if (!(await clashAnswered())) return; }
    else if (!r || !r.ok) return;
    first = (exportSaved.value && exportSaved.value.name) || "";
  }
  /* the left-out check runs before every client export (BL-336): read only; when the internal week isn't approved or it finds something internal,
     the dialog says what and nothing is exported. Otherwise the export goes straight on (the server checks again). */
  const chk = await runCheck(), lo = chk && chk.ok ? chk.left_out : null;
  if (!lo || !lo.ready || lo.findings.length) { crDialog.value = true; return; }
  const c = await exportClientReport(fmt);                 // v2.5.1: the server renders it from the checked snapshot, no page posted
  if (c && !c.ok && !c.clash) { crDialog.value = true; await runCheck(); return; }       // a refusal: the check shows why, and nothing was written
  if (which === "both" && c && c.ok && first && exportSaved.value) exportSaved.value = { ...exportSaved.value, name: `${first} and ${exportSaved.value.name}` };
}

/** Approve and file the internal report (saved first). */
export async function hubApproveInternal() {
  const doc = weeklyDoc.value;
  if (!doc || !(await saveFirst())) return;
  const r = await approveWeekly(doc);
  snack(r.ok ? "Approved and filed" : String(r.message || "Not approved").split("\n").filter(Boolean).pop());
  if (r.ok) reloadHub();
}

/** Approve and file the client report; a check awaiting review leaves a note with Approve anyway. @param {boolean} force */
export async function hubApproveClient(force) {
  const r = await approveClientReport(force);
  if (r && r.ok) { hubNote.value = ""; snack("Client report approved and filed"); reloadHub(); return; }
  hubNote.value = String((r && r.message) || "Not approved").split("\n")[0];
}
