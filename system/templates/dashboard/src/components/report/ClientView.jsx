// @ts-check
/* ClientView (v2.1.0 P8, BL-336): the client's report as a Client view of the week's report (#client-report=<CODE>/<week>/<client>).
   The same A4 sheet with the client's own layout; the client health and its reason; Match internal (one section or all); the check
   of what is left out before every export; and Side by side with the internal report. Built on the sheet's contract
   (dev/sprints/v210-contract.md §4) on P5's Sheet (components/report/Sheet.jsx); Side by side has the internal page read only (leftReadOnly). The view keeps the document (stores/clientReport.js) and makes its own server calls (/api/report/*).
   Client safety: the page only ever holds what the server built from client-visible items (report_doc.client_doc, through
   client_leak.make_safe) and what Alan typed; Match internal copies only what clientDoc.matchClientSection allows; the server checks
   again at save, approve and export. Nothing here sends anything. */
import { render } from "preact";
import { useState } from "preact/hooks";
import { CLIENT_RENDERERS, setClientDoc } from "./ClientParts.jsx";
import { matchClientAll, matchClientSection } from "./clientDoc.js";
import { LeftOutDialog } from "./LeftOutDialog.jsx";
import { Sheet } from "./Sheet.jsx";
import { INTERNAL_RENDERERS } from "./WeeklyPartner.jsx";
import { $ } from "../../core/dom.js";
import { navWrite, tabTitle } from "../../core/nav.js";
import { fd } from "../../core/page.js";
import { snack } from "../../core/server.js";
import { approveClientReport, crArg, crBase, crBusy, crDialog, crDirty, crDoc, crInfo, crInternal, crMode, crOpen, exportClientReport,
  loadClientReport, runCheck, saveClientPage } from "../../stores/clientReport.js";

/** @typedef {import("./Sheet.jsx").SheetDoc} SheetDoc */

/** Save any page edits, run the left-out check and open it. */
async function openCheck() {
  const d = crDoc.value;
  if (!d) return;
  if (crDirty.value) { const s = await saveClientPage({ doc: d, base_version: crBase.value }); if (!s.ok) { snack(String(s.message || "The report wasn't saved").split("\n")[0]); return; } }
  crDialog.value = true;
  await runCheck();
}

/** @param {"html"|"docx"|"pdf"} fmt */
async function doExport(fmt) {
  const r = await exportClientReport(fmt);
  if (r && r.ok) { crDialog.value = false; snack(`Exported${r.path ? `: ${String(r.path).split("/").pop()}` : ""}`); }
  else { await runCheck(); snack(String((r && r.message) || "Not exported").split("\n")[0]); }
}

/** @param {{doc: SheetDoc, note: string, setNote: (s: string) => void}} props */
function Bar({ doc, note, setNote }) {
  const info = crInfo.value, ready = !!(info && info.ready), mode = crMode.value, draft = doc.state !== "approved";
  const approve = async (/** @type {boolean} */ force) => {
    const r = await approveClientReport(force);
    if (r && r.ok) { setNote(""); snack("Client report approved and filed"); const a = crArg.value; if (a) loadClientReport(a); return; }
    const msg = String((r && r.message) || "Not approved").split("\n")[0];
    setNote(msg);
  };
  return (
    <span class="crbarr">
      <span class={`tag ${ready ? "ok" : "warn"}`} data-crbase>{ready ? "Internal: approved · facts locked" : "Internal: not approved yet"}</span>
      <span class="seg" role="group" aria-label="View">
        <button type="button" data-crmode="client" aria-pressed={mode === "client" ? "true" : "false"} onClick={() => { crMode.value = "client"; }}>Client report</button>
        <button type="button" data-crmode="side" aria-pressed={mode === "side" ? "true" : "false"} disabled={!crInternal.value} onClick={() => { crMode.value = "side"; }}>Side by side</button>
      </span>
      {draft && mode !== "side" ? <button type="button" class="btn sm" data-crmatchall disabled={!crInternal.value} onClick={() => { const d = crDoc.value, i = crInternal.value; if (d && i) setClientDoc(matchClientAll(d, i)); }}>Match internal for every section</button> : null}
      {draft && ready && info && info.baseline && !(doc.based_on && doc.based_on.version === info.baseline.version) ? <button type="button" class="btn sm" data-crrefresh
        title="This draft was made before the internal report was approved. Refreshing rebuilds it from the approved week's locked facts and replaces your edits when you save."
        onClick={() => { const a = crArg.value; if (a) loadClientReport(a, true); }}>Refresh from the approved week</button> : null}
      <button type="button" class="btn sm" data-crcheck disabled={!ready} data-tip={ready ? undefined : "Approve the internal report first"} title={ready ? undefined : "Approve the internal report first"} onClick={openCheck}>Check and export ▾</button>
      {draft ? <button type="button" class="btn sm primary" data-crapprove disabled={!ready} title={ready ? undefined : "Approve the internal report first"} onClick={() => approve(false)}>Approve client report</button> : null}
      {note ? <span class="crnote" role="status">{note} {/awaiting review/.test(note) ? <button type="button" class="btn sm" data-crforce onClick={() => approve(true)}>Approve anyway</button> : null}</span> : null}
    </span>
  );
}

/** The sheet's Match internal for the client page (contract §4.6 `partner.match`): the client-safe match, never a verbatim copy of
    the internal section. @param {string|null} id the section's id, or null for every section @returns {SheetDoc} */
function matchFor(id) {
  const d = /** @type {SheetDoc} */ (crDoc.value), i = crInternal.value;
  if (!i) return d;
  return id == null ? matchClientAll(d, i) : matchClientSection(d, i, id);
}

/** The view. */
export function ClientView() {
  const [exported, setExported] = useState(false);
  const [note, setNote] = useState("");
  const open = crOpen.value, doc = crDoc.value, internal = crInternal.value, mode = crMode.value, info = crInfo.value;
  const side = mode === "side" && !!internal;
  if (!open) return <div class="crview"><p class="sub">{crBusy.value || "Opening the client report…"}</p></div>;
  if (!open.ok || !doc) return <div class="crview"><h1 id="crTitle">Client report</h1><p class="mnerr" role="alert">{open.message || "Couldn't open the client report"}</p></div>;
  const a = crArg.value, filed = doc.state === "approved";
  const key = `client:${doc.project}:${doc.date}:${doc.client || ""}:${mode}`;
  return (
    <div class="crview">
      <header class="crhead">
        <nav class="crumb" aria-label="Breadcrumb"><a href="#" data-go="projects">Projects</a> › <span aria-current="page">Client report</span></nav>
        <h1 id="crTitle">Client report{doc.client ? `: ${doc.client}` : ""}</h1>
        <p class="sub crmeta">{doc.project_name || (a && a.code) || ""} · week ending {fd(doc.date)} · {filed ? "Approved and filed" : info && info.where === "new" ? "New, not yet saved" : "Draft, not yet approved"}
          {filed ? " · Edits start a new draft" : ""}</p>
      </header>
      <div class="crsheet">
        <Sheet doc={side && internal ? internal : doc} baseVersion={crBase.value} scrollKey={key} exported={exported} onExported={setExported}
          readOnly={filed && !side} leftReadOnly renderers={side ? INTERNAL_RENDERERS : CLIENT_RENDERERS}
          partner={side ? { doc, label: "Client", baseVersion: crBase.value, scrollKey: key, renderers: CLIENT_RENDERERS, readOnly: filed, match: id => setClientDoc(matchFor(id)),
            onChange: setClientDoc, onSave: saveClientPage } : null}
          onChange={side ? () => {} : setClientDoc} onSave={side ? undefined : saveClientPage}
          onEvent={ev => { if (ev.type === "reload" && a) loadClientReport(a); }}
          toolbar={<Bar doc={doc} note={note} setNote={setNote} />} />
      </div>
      <LeftOutDialog client={doc.client || ""} onExport={doExport} />
    </div>
  );
}

let crMounted = false;
/** Draw the client view into #v-clientreport and open the report: {code, week?, client?} or its address text "CODE/week/client".
    @param {{code: string, week?: string, client?: string}|string|null} arg */
export function renderClientReport(arg) {
  const el = $("#v-clientreport");
  if (!el) return;
  if (!crMounted) { render(<ClientView />, el); crMounted = true; }
  const a = typeof arg === "string" ? parseKey(arg) : arg;
  if (a && a.code) {
    crMode.value = "client";
    loadClientReport(a).then(() => { navWrite(false); tabTitle(); });
  }
}

/** The address text of the report on screen: CODE/week ending/client (client encoded), or null. */
export function clientReportKey() {
  const a = crArg.value, d = crDoc.value;
  return a && d ? `${a.code}/${d.date}/${encodeURIComponent(d.client || a.client || "")}` : null;
}

/** @param {string} text @returns {{code: string, week?: string, client?: string}|null} */
export function parseKey(text) {
  const m = /^([A-Z][A-Z0-9]{2,6})(?:\/(\d{4}-\d{2}-\d{2}))?(?:\/(.*))?$/.exec(String(text || ""));
  if (!m) return null;
  let client = "";
  try { client = decodeURIComponent(m[3] || ""); } catch (e) { return null; }
  return { code: m[1], week: m[2] || undefined, client: client || undefined };
}
