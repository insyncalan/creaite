// @ts-check
/* ReportingHub (#221 H1; brief dev/sprints/reporting-hub-brief.md, mockup dev/mockups/reporting-hub-mockup.html, Round 10 = final):
   one page for a project's weekly reporting, #reporting=<CODE>[&w=<Friday>][&v=client|side]. It replaces the weekly page and the
   client report page and mounts the existing Sheet for the Internal report, the Client report, or both side by side (one scroller, so
   they scroll together). What the hub adds is the page around the sheet: the view switch (only when the project has a client report,
   `clientReportOn(code)`), the week Menu, and ONE toolbar on one line (HubBar) with icons only: zoom, Show as exported, Export, Approve,
   and the cog last. The sheet's own bar is replaced by it (Sheet's `renderBar`); the sheet itself is mounted as it is today.
   The scrolling header is the sheet's (#202, #207: core/scrollPolicy.js). Nothing here sends anything.
   Collisions to know about: H2 owns the sheet's insides (components/report/sheet*, weekly/*, ClientParts); H3 owns the cog's panel
   (hub/ClientReportPanel.jsx, replaced) and the setting (stores/reportingSettings.js, replaced). */
import { useEffect } from "preact/hooks";
import { LeftOutDialog } from "../LeftOutDialog.jsx";
import { ExportSave } from "../ExportSave.jsx";
import { CLIENT_RENDERERS, setClientDoc } from "../ClientParts.jsx";
import { doExport, clientHealthApply, matchFor } from "../ClientView.jsx";
import { matchClientAll } from "../clientDoc.js";
import { countRedraft, redrafter } from "../redraft.js";
import { ReportSheet } from "../ReportParts.jsx";
import { WEEKLY_RENDER } from "../weekly/WeeklyView.jsx";
import { HubBar } from "./HubBar.jsx";
import { hubApproveClient } from "./hubActions.js";
import { clientStatus, internalStatus, menuWeeks, toneByTrail, toneByWeek } from "./hubLib.js";
import { P } from "../../../core/data.js";
import { navWrite, tabTitle } from "../../../core/nav.js";
import { fd } from "../../../core/page.js";
import { crBase, crDirty, crDoc, crInfo, crInternal, crOpen, loadClientReport, saveClientPage } from "../../../stores/clientReport.js";
import { hubAsk, hubCfg, hubExported, hubKey, hubNote, hubReady, hubView, hubZoom, loadHub, reloadHub } from "../../../stores/hub.js";
import { repTick, spaceCode, spaceWeek, spaceWeeks, weekView } from "../../../stores/reporting.js";
import { clientReportOn, crTick } from "../../../stores/reportingSettings.js";
import { editDoc, saveWeekly, setWeeklyDirty, weeklyBase, weeklyBusy, weeklyDoc, weeklyEditing, weeklyView } from "../../../stores/weekly.js";

/** @typedef {import("../Sheet.jsx").SheetDoc} SheetDoc */

/** Take a week: the address keeps it, the hub opens it. @param {string} code @param {string} week */
function pickWeek(code, week) {
  spaceWeek.value = week;
  navWrite(true);
  tabTitle();
  loadHub(code, week);
}

/** Change what is in view; the address keeps it. @param {"internal"|"client"|"side"} v */
function pickView(v) { hubView.value = v; navWrite(false); }

/** The weeks the menu lists, each with its health tone and both reports' states. @param {string} code @param {SheetDoc|null} doc @param {boolean} on */
function weekRows(code, doc, on) {
  const tones = { ...toneByTrail(P.find(/** @param {any} p */ p => p.code === code)), ...toneByWeek(doc) }, shown = doc ? doc.date : "", ci = crInfo.value, cd = crDoc.value;
  return menuWeeks(spaceWeeks(code), shown).map(w => {
    const v = weekView(code, w), isShown = w === shown;
    return { week: w, tone: tones[w] || "n", current: isShown,
      internal: isShown && doc ? internalStatus(doc).label : v.internal.label,
      client: isShown && on && cd ? clientStatus(cd, ci).label : (v.clients[0] ? v.clients[0].state.label : "") };
  });
}

/** One of the quiet labels above a report: its name, who it is for and its status. @param {{k: "internal"|"client", on: boolean, doc: SheetDoc}} props */
function ReportLabel({ k, on, doc }) {
  const internal = k === "internal";
  const st = internal ? internalStatus(weeklyDoc.value) : clientStatus(crDoc.value, crInfo.value);
  const approved = weeklyDoc.value && weeklyDoc.value.state === "approved";
  const cd = crDoc.value, info = crInfo.value;
  return (
    <div class="hubpl" data-k={k}>
      {on ? <><b>{internal ? "Internal report" : "Client report"}</b><span class="sub">{internal ? "for you and the team" : `for ${(cd && cd.client) || "the client"}`}</span></> : null}
      {internal && approved && !weeklyEditing.value ? <button type="button" class="linkbtn hubedit" id="hubEdit" onClick={() => { weeklyEditing.value = true; }}>Edit again</button> : null}
      {!internal && cd && cd.state !== "approved" ? <>
        <button type="button" class="linkbtn rb-x" data-crmatchall disabled={!crInternal.value} onClick={() => { const d = crDoc.value, i = crInternal.value; if (d && i) setClientDoc(matchClientAll(d, i)); }}>Match internal for every section</button>
        {info && info.ready && info.baseline && !(cd.based_on && cd.based_on.version === info.baseline.version) ? <button type="button" class="linkbtn rb-x" data-crrefresh
          title="This draft was made before the internal report was approved. Refreshing rebuilds it from the approved week's locked facts and replaces your edits when you save."
          onClick={() => { const a = hubAsk.value; if (a) loadClientReport({ code: a.code, week: doc.date }, true); }}>Refresh from the approved week</button> : null}
      </> : null}
      <span class="hubstat" data-k={k} data-state={st.key}>{st.label}</span>
    </div>);
}

/** The label row inside the report's grey pane (the mockup): a label for the report, or one for each side by side, at the top of
    the pane and scrolling with it. `slot` says which pane it is in.
    @param {{slot: "one"|"left"|"right"|"both", view: "internal"|"client"|"side", on: boolean, doc: SheetDoc}} props */
function PaneRow({ slot, view, on, doc }) {
  const kinds = slot === "both" ? ["internal", "client"] : slot === "left" ? ["internal"] : slot === "right" ? ["client"] : [view === "client" ? "client" : "internal"];
  return (
    <div class={`hubrow inpane${kinds.length > 1 ? " two" : ""}`}>
      {kinds.map(k => k === "client" && !on ? null : <ReportLabel key={k} k={/** @type {"internal"|"client"} */ (k)} on={on} doc={doc} />)}
    </div>);
}

/** The client report's message, a strip under the bar (it stays in view; the labels are in the panes). */
function HubNote() {
  const note = hubNote.value;
  if (!note || hubView.value === "internal") return null;
  return (
    <div class="hubrow hubnote">
      <span class="crnote" role="status">{note} {/awaiting review/.test(note) ? <button type="button" class="btn sm" data-crforce onClick={() => hubApproveClient(true)}>Approve anyway</button> : null}</span>
    </div>);
}

/** What the internal report's pane does (the internal view and the left pane of Side by side are the same): an edit is kept on the page and
    is what Match internal reads; the save is its own. */
const internalChange = (/** @type {SheetDoc} */ d) => { editDoc(d); if (crInternal.value) crInternal.value = d; };
const internalSave = async (/** @type {any} */ req) => { const r = await saveWeekly(req); if (r.ok) setWeeklyDirty(false); return r; };
/** The AI bar's account of the internal report's pane: its own place and no client document. @param {SheetDoc} doc */
const internalAi = (/** @type {SheetDoc} */ doc) => ({ place: "report", project: () => doc.project, confidential: () => false });
/** ✦ on the internal report. @param {SheetDoc} doc */
const internalRedraft = (/** @type {SheetDoc} */ doc) => redrafter(() => ({ code: doc.project, document: { kind: "weekly", code: doc.project, week_ending: doc.date } }), "report");
/** ✦ on the client report. @param {SheetDoc} cd */
const clientRedraft = (/** @type {SheetDoc} */ cd) => redrafter(() => ({ code: cd.project, document: { kind: "client", code: cd.project, week_ending: cd.date, client: cd.client || "" } }), "report", "client", clientHealthApply);

/** The sheet for what is in view. @param {{code: string, view: "internal"|"client"|"side", on: boolean, doc: SheetDoc}} props */
function HubSheet({ code, view, on, doc }) {
  const cd = crDoc.value, ci = crInternal.value, cinfo = crInfo.value;
  const iLocked = doc.state === "approved" && !weeklyEditing.value;
  const cFiled = !!cd && cd.state === "approved";
  const side = view === "side" && !!cd;
  const clientAi = cd ? { place: "client", project: () => cd.project, confidential: () => false,
    document: () => ({ kind: "client", code: cd.project, week_ending: cd.date, client: cd.client || "" }) } : undefined;
  const common = { zoom: hubZoom.value, onZoom: (/** @type {number} */ z) => { hubZoom.value = z; }, exported: hubExported.value,
    onExported: (/** @type {boolean} */ on_) => { hubExported.value = on_; },
    banner: { title: "Weekly reporting", sub: `${doc.project_name || code} · ${fd(doc.date)}` },
    renderBar: (/** @type {any} */ ctx) => <HubBar ctx={ctx} code={code} view={view} on={on} doc={doc} week={doc.date} tone={toneByWeek(doc)[doc.date] || "n"}
      rows={weekRows(code, doc, on)} onWeek={(/** @type {string} */ w) => pickWeek(code, w)} onView={pickView} />,
    belowBar: <HubNote />, paneHead: (/** @type {"one"|"left"|"right"|"both"} */ slot) => <PaneRow slot={slot} view={view} on={on} doc={doc} /> };
  const reloadClient = () => { const a = hubAsk.value; if (a) loadClientReport({ code: a.code, week: doc.date }); };
  if (view === "client" && cd) {
    return <ReportSheet audience="client" key={`c:${cd.date}`} {...common} doc={cd} baseVersion={crBase.value} scrollKey={`client:${cd.project}:${cd.date}:${cd.client || ""}`}
      readOnly={cFiled} renderers={CLIENT_RENDERERS} onChange={setClientDoc} onSave={saveClientPage} ai={clientAi}
      onRedraft={clientRedraft(cd)}
      onEvent={ev => { if (ev.type === "reload") reloadClient(); else countRedraft(ev, "report"); }} />;
  }
  if (side && cd) {
    const key = `side:${cd.project}:${cd.date}:${cd.client || ""}`;
    return <ReportSheet audience="client" key={`s:${cd.date}`} {...common} doc={doc} baseVersion={weeklyBase.value} scrollKey={key} readOnly={iLocked} panesApart
      renderers={WEEKLY_RENDER} onChange={internalChange} onSave={internalSave} ai={internalAi(doc)} onRedraft={internalRedraft(doc)}
      partner={{ doc: cd, label: "Client", baseVersion: crBase.value, scrollKey: key, renderers: CLIENT_RENDERERS, readOnly: cFiled,
        match: (/** @type {string} */ id) => setClientDoc(matchFor(id)), onChange: setClientDoc, onSave: saveClientPage, dirty: () => crDirty.value, ai: clientAi, onRedraft: clientRedraft(cd) }}
      onEvent={ev => { if (ev.type === "reload") { if (ev.partner) reloadClient(); else reloadHub(); } else countRedraft(ev, "report"); }} />;
  }
  return <ReportSheet audience="internal" key={`i:${doc.date}`} {...common} doc={doc} baseVersion={weeklyBase.value} scrollKey={`weekly:${doc.project}:${doc.date}`} readOnly={iLocked}
    renderers={WEEKLY_RENDER} onChange={internalChange} onSave={internalSave}
    ai={internalAi(doc)} onRedraft={internalRedraft(doc)}
    onEvent={ev => { if (ev.type === "reload") reloadHub(); else countRedraft(ev, "report"); }} />;
}

/** The page. */
export function ReportingHub() {
  repTick.value; crTick.value;                          // a reload of the data, or a change to the client report setting, redraws
  const code = spaceCode.value, p = P.find(x => x.code === code);
  const on = code ? clientReportOn(code) : false, asked = spaceWeek.value;
  const ready = !!code && hubReady.value === hubKey(code, asked);
  useEffect(() => {                                     // the client report switched on or off while the hub is open: open the week again
    const a = hubAsk.value;
    if (code && a && a.code === code && hubReady.value && hubReady.value !== hubKey(code, a.week)) loadHub(code, a.week);
  }, [on, code]);
  useEffect(() => {                                     // Esc closes the cog's panel
    if (!hubCfg.value) return undefined;
    const key = (/** @type {KeyboardEvent} */ e) => { if (e.key === "Escape") { hubCfg.value = false; const b = document.getElementById("hubCfg"); if (b) b.focus({ preventScroll: true }); } };
    document.addEventListener("keydown", key);
    return () => document.removeEventListener("keydown", key);
  }, [hubCfg.value]);
  if (!p) return null;
  const v = weeklyView.value, doc = weeklyDoc.value;
  const view = on ? hubView.value : "internal";
  const date = (doc && doc.date) || asked;
  const head = (
    <header class="wrhead">
      <nav class="crumb" aria-label="Breadcrumb">
        <a href="#" data-go="projects">Projects</a><span aria-hidden="true"> › </span>
        <a href="#" data-cock={code}>{p.name}</a><span aria-hidden="true"> › </span><span aria-current="page">Reporting</span>
      </nav>
      <h1 id="hubTitle">Weekly reporting</h1>
      <p class="sub wrmeta" id="hubMeta">{p.name}{date ? ` · week ending ${fd(date)}` : ""}{view === "client" ? " · client report" : view === "side" ? " · internal and client side by side" : ""}</p>
    </header>);
  let body;
  if (!ready) body = <p class="sub hubwait">{weeklyBusy.value || "Opening the reporting…"}</p>;
  else if (!v || !v.ok || !doc) body = <p class="wr-err" role="alert">{(v && v.message) || "Couldn't open the weekly report"}</p>;
  else if (view !== "internal" && (!crDoc.value || (crOpen.value && !crOpen.value.ok))) body = <p class="mnerr" role="alert">{(crOpen.value && crOpen.value.message) || "Couldn't open the client report"}</p>;
  else body = <HubSheet code={code} view={view} on={on} doc={doc} />;
  return (
    <div class="wrview rhub">
      {head}
      <div class={view === "internal" ? "wrsheet" : "crsheet wrsheet"}>{body}</div>
      {on ? <LeftOutDialog client={(crDoc.value && crDoc.value.client) || ""} onExport={doExport} /> : null}
      <ExportSave />
    </div>);
}
