// @ts-check
/* WeeklyView (v2.1.0 P6, BL-335): the weekly report in creaite (#weekly=<code>&week=<Friday>), drawn on the sheet's contract
   (dev/sprints/v210-contract.md §4) on P5's Sheet (components/report/Sheet.jsx), which does the zoom, move and hide, eyes, Show as exported and
   autosave. The view supplies the renderers for the weekly sections, keeps the document (stores/weekly.js) and makes
   P3's /api/report/* calls. The bar (the sheet's toolbar slot): Export, Edit again or Approve and file. Nothing here
   sends anything. */
import { render } from "preact";
import { Menu } from "../../Menu.jsx";
import { ReportSheet } from "../ReportParts.jsx";
import { ExportSave } from "../ExportSave.jsx";
import { countRedraft, redrafter } from "../redraft.js";
import { Glance } from "./Glance.jsx";
import { CurrentState, Words } from "./Notes.jsx";
import { Asks, Decisions, Overdue, Risks } from "./Tables.jsx";
import { Timeline } from "./Timeline.jsx";
import { WkHeader, WkHealth } from "./Top.jsx";
import { $ } from "../../../core/dom.js";
import { navWrite, tabTitle } from "../../../core/nav.js";
import { fd } from "../../../core/page.js";
import { snack } from "../../../core/server.js";
import { approveWeekly, editDoc, exportWeekly, loadWeekly, saveWeekly, setWeeklyDirty, weeklyArg, weeklyBase, weeklyBusy, weeklyDirty,
  weeklyDoc, weeklyEditing, weeklyView } from "../../../stores/weekly.js";

/** @typedef {import("../Sheet.jsx").SheetDoc} SheetDoc */

const sectionWords = (/** @type {string} */ label, /** @type {string} */ empty) => (/** @type {any} */ ctx) => <Words ctx={ctx} label={label} empty={empty} />;
export const WEEKLY_RENDER = { byId: {
  header: (/** @type {any} */ c) => <WkHeader ctx={c} />, health: Object.assign((/** @type {any} */ c) => <WkHealth ctx={c} />, { ownSpark: true }), glance: (/** @type {any} */ c) => <Glance ctx={c} />,
  summary: sectionWords("Summary", "Say what matters this week"), milestones: (/** @type {any} */ c) => <Timeline ctx={c} />,
  asks: (/** @type {any} */ c) => <Asks ctx={c} />, this_week: sectionWords("This week", "Nothing recorded"), next_week: sectionWords("Next week", "Nothing recorded"),
  decisions: (/** @type {any} */ c) => <Decisions ctx={c} />, risks: (/** @type {any} */ c) => <Risks ctx={c} />,
  overdue: (/** @type {any} */ c) => <Overdue ctx={c} />, current_state: (/** @type {any} */ c) => <CurrentState ctx={c} /> } };

/** Save what is on the page; false (and a message) when it didn't save. */
async function saveFirst() {
  const d = weeklyDoc.value, v = weeklyView.value;
  if (!d || !(weeklyDirty || (v && v.where === "new"))) return true;      // a report never saved is saved before it is exported
  const r = await saveWeekly({ doc: d, base_version: weeklyBase.value });
  if (!r.ok) { snack(r.message || "The report wasn't saved"); return false; }
  setWeeklyDirty(false); return true;
}

/** The bar's buttons (the sheet's `toolbar` slot). @param {{doc: SheetDoc, readOnly: boolean}} props */
function WeeklyBar({ doc, readOnly }) {
  const approved = doc.state === "approved";
  const exp = async (/** @type {string} */ fmt) => {
    if (!(await saveFirst())) return;
    await exportWeekly(doc, fmt);          // the dialog, the "Saved … in <project> › Reports" message or the failure show themselves (ExportSave)
  };
  const approve = async () => {
    if (!(await saveFirst())) return;
    const r = await approveWeekly(doc);
    snack(r.ok ? "Approved and filed" : String(r.message || "Not approved").split("\n").filter(Boolean).pop());
    if (r.ok) loadWeekly(/** @type {any} */ (weeklyArg.value));
  };
  return (
    <span class="wr-barr">
      <Menu label="Export" btnCls="btn sm" menuLabel="Export the report" data={{ wrexport: "" }} onPick={exp}
        items={[{ id: "docx", name: "Word (.docx)", line: "The firm's template, to send" }, { id: "pdf", name: "PDF", line: "Printed from the page" },
          { id: "html", name: "HTML (to share)", line: "One page that opens in any browser; read only" }]} />
      {approved && !weeklyEditing.value ? <button type="button" class="btn sm" id="wrEdit" onClick={() => { weeklyEditing.value = true; }}>Edit again</button> : null}
      {!approved || weeklyEditing.value ? <button type="button" class="btn sm primary" id="wrApprove" disabled={readOnly && approved} onClick={approve}>Approve and file</button> : null}
    </span>);
}

/** The view. */
export function WeeklyView() {
  const v = weeklyView.value, doc = weeklyDoc.value;
  if (!v) return <div class="wrview"><p class="sub">{weeklyBusy.value || "Opening the weekly report…"}</p></div>;
  if (!v.ok || !doc) return <div class="wrview"><h1 id="wrTitle">Weekly report</h1><p class="wr-err" role="alert">{v.message || "Couldn't open the weekly report"}</p></div>;
  const approved = doc.state === "approved", readOnly = approved && !weeklyEditing.value;
  const state = approved ? "Approved and filed" : v.where === "new" ? "New, not saved yet" : "Draft";
  return (
    <div class="wrview">
      <header class="wrhead">
        <nav class="crumb" aria-label="Breadcrumb"><a href="#" data-go="projects">Projects</a> › <span aria-current="page">Weekly report</span></nav>
        <h1 id="wrTitle">Weekly report</h1>
        <p class="sub wrmeta">{doc.project_name} · week ending {fd(doc.date)} · {state}{doc.version ? ` · version ${doc.version}` : ""}</p>
      </header>
      <div class="wrsheet">
        <ReportSheet audience="internal" doc={doc} baseVersion={weeklyBase.value} scrollKey={`weekly:${doc.project}:${doc.date}`} readOnly={readOnly}
          renderers={WEEKLY_RENDER} onChange={editDoc} onSave={async req => { const r = await saveWeekly(req); if (r.ok) setWeeklyDirty(false); return r; }}
          ai={{ place: "report", project: () => doc.project, confidential: () => false }}
          onRedraft={redrafter(() => ({ code: doc.project, document: { kind: "weekly", code: doc.project, week_ending: doc.date } }), "report")}
          onEvent={ev => { if (ev.type === "reload") loadWeekly(/** @type {any} */ (weeklyArg.value)); else countRedraft(ev, "report"); }}
          banner={{ title: "Weekly report", sub: `${doc.project_name} · ${fd(doc.date)}` }} toolbar={<WeeklyBar doc={doc} readOnly={readOnly} />} />
      </div>
      <ExportSave />
    </div>);
}

let wkMounted = false;
/** Draw the view into #v-weekly and open the report: {code, week?}. @param {{code: string, week?: string}|string|null} arg */
export function renderWeekly(arg) {
  const el = $("#v-weekly"); if (!el) return;
  if (!wkMounted) { render(<WeeklyView />, el); wkMounted = true; }
  const a = typeof arg === "string" ? parseWeekly(arg) : arg;
  if (a && a.code) { setWeeklyDirty(false); loadWeekly(a).then(() => { navWrite(false); tabTitle(); }); }
}

/** "ABC" or "ABC&week=2026-10-16" as the address keeps it. @param {string} s @returns {{code: string, week?: string}|null} */
export function parseWeekly(s) {
  const m = /^([A-Z][A-Z0-9]{2,6})(?:&week=(\d{4}-\d{2}-\d{2}))?$/.exec(String(s || ""));
  return m ? { code: m[1], week: m[2] } : null;
}

/** The report on screen, as the address keeps it, or null. */
export const weeklyKey = () => {
  const a = weeklyArg.value, d = weeklyDoc.value;
  return a ? `${a.code}${d ? `&week=${d.date}` : a.week ? `&week=${a.week}` : ""}` : null;
};
