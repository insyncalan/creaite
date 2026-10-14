// @ts-check
/* PageDialogs (BL-316): the page's own modal dialogs, each one the Dialog building block (dev/COMPONENTS.md §3), with the ids,
   classes and words they had as hand-made dialogs. They are opened by old code (openDialog / closeDialog), and their inner
   parts (a list, a preview, a form's options) are still filled by that code, by id. The Dialog owns only the frame: the name,
   focus on opening, Esc, the scrim, focus back to the opener.
   - bootDialogs() draws the ones that were in shell.html, once, as the page starts (before any other start-up step):
     ⌘K (#cmdk), the Intake and search previews (#inPrev, #searchPrev), Compare a repeat (#llDlg), the approval preview (#rvDlg),
     the date prompt (#boardDlg), Generate current state (#genDlg) and the person prompt (#personDlg);
   - the ones made the first time they are needed: the draft email (#deDlg, drafts.js), Undo changes (#actDlg, activity.js) and
     the Prep popup (#prepDlg, projects.js). */
import { render } from "preact";
import { Dialog } from "../Dialog.jsx";
import { Icon } from "../Icon.jsx";

const ROW = "display:flex;align-items:center;gap:8px;margin-bottom:8px";
const CUT = "Only the start is shown; open it in its app for the rest.";

/** The shell's dialogs, all closed. */
export function PageDialogs() {
  return (
    <>
      <Dialog id="cmdk" ariaLabel="Search or jump to" dirty={false}>
        <input id="cmdkIn" placeholder="Search projects, items, commands…" autocomplete="off" aria-label="Search projects, items and commands" />
        <div id="cmdkList"></div>
        <div id="ckPrev" hidden></div>
      </Dialog>
      <Dialog id="inPrev" labelledBy="inPrevName">
        <div style={ROW}><h2 id="inPrevName" style="flex:1;margin:0"></h2><button class="btn" id="inPrevOpen" type="button">Open in its app</button>
          <form method="dialog"><button class="btn primary">Close</button></form></div>
        <pre id="inPrevText"></pre><div id="inPrevMd" hidden></div><div class="sub" id="inPrevCut" hidden>{CUT}</div>
      </Dialog>
      <Dialog id="searchPrev" labelledBy="spName">
        <div style={ROW}><h2 id="spName" style="flex:1;margin:0"></h2><button class="btn" id="spOpen" type="button">Open in its app</button>
          <form method="dialog"><button class="btn primary">Close</button></form></div>
        <div id="spText"></div><div class="sub" id="spCut" hidden>{CUT}</div>
      </Dialog>
      {/* BL-221 (sprint-drafts-extraction): Compare a repeat */}
      <Dialog id="llDlg" class="rvdlg lldlg" labelledBy="llTitle">
        <h2 id="llTitle">Compare</h2><p class="sub">The proposal beside the item it looks like. Nothing changes until you choose.</p>
        <table class="lltab"><thead><tr><th scope="col"><span class="vh">Field</span></th><th scope="col" id="llNew">Proposed</th>
          <th scope="col" id="llOld">Existing</th></tr></thead><tbody id="llRows"></tbody></table>
        <div class="row" style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap"><span class="sp" style="flex:1"></span>
          <button type="button" class="btn" id="llClose">Close</button><button type="button" class="btn" id="llKeep">Keep as new</button>
          <button type="button" class="btn primary" id="llMerge">Merge</button></div>
      </Dialog>
      {/* BL-133: the preview before a large or global approval */}
      <Dialog id="rvDlg" class="bdlg rvdlg" labelledBy="rvDlgTitle">
        <div id="rvDlgBody"></div>
        <div class="row" style="display:flex;gap:8px;margin-top:12px"><span class="sp" style="flex:1"></span>
          <button type="button" class="btn" id="rvDlgCancel">Cancel</button><button type="button" class="btn primary" id="rvDlgOk">Approve</button></div>
      </Dialog>
      <Dialog id="boardDlg" labelledBy="bdTitle">
        <div id="bdForm">
          <h2 id="bdTitle" style="margin:0 0 4px"></h2><div class="sub" id="bdHint" style="margin-bottom:10px"></div>
          <div id="bdDateRow"><label class="sub" for="bdDate">Due date</label>
            <span class="dwrap"><input type="text" id="bdDate" placeholder="DD-MM-YYYY" autocomplete="off" data-min="today" data-noclear="" />
              <button type="button" class="dbtn" data-cal="bdDate" aria-label="Choose date" data-tip="Choose a date"><Icon name="calendar" /></button></span>
            <div class="bdquick" id="bdQuick"><button type="button" class="vchip" data-q="fri">This Friday</button>
              <button type="button" class="vchip" data-q="nfri">Next Friday</button><button type="button" class="vchip" data-q="2w">In two weeks</button></div>
            <div class="sub" id="bdRange"></div></div>
          <div class="perr" id="bdErr" role="alert" style="color:var(--bad);min-height:18px;font-size:var(--fs-sm)"></div>
          <div class="curacts"><span class="sp"></span><button class="btn" type="button" id="bdCancel">Cancel</button>
            <button class="btn primary" type="button" id="bdOk">Move</button></div>
        </div>
      </Dialog>
      <Dialog id="genDlg" labelledBy="genTitle">
        <form method="dialog" id="genForm">
          <h2 id="genTitle" style="margin:0 0 10px">Generate current state</h2>
          <div class="sub" id="genWho"></div>
          <fieldset><legend>Period</legend><div class="views" id="genDays"></div>
            <div class="drange" id="genCustom" hidden><input type="text" id="genFrom" placeholder="DD-MM-YYYY" aria-label="From" /><span>to</span>
              <input type="text" id="genTo" placeholder="DD-MM-YYYY" aria-label="To" /></div></fieldset>
          <fieldset><legend>Form</legend><div class="views" id="genFormKind"></div><div class="sub" id="genFormNote"></div></fieldset>
          <fieldset><legend>Audience</legend><div class="views" id="genAud"></div><div class="sub" id="genAudNote"></div></fieldset>
          <fieldset><legend>Length</legend><div class="views" id="genLen"></div></fieldset>
          <fieldset><legend>Draw on</legend><div id="genSrc"></div></fieldset>
          <label class="sub" for="genNote">Steer it (optional)</label>
          <textarea id="genNote" rows={2} placeholder="For example: focus on the pilot results"></textarea>
          <div class="sub" id="genSweep"></div>
          <div class="curacts"><span class="sp"></span><button class="btn" value="cancel" formnovalidate>Cancel</button>
            <button class="btn primary" id="genGo" value="go">Generate</button></div>
          <div id="genOut" class="fmout"></div>
        </form>
      </Dialog>
      {/* People (BL-55, BL-56); the VIP field shows when editing (BL-99) */}
      <Dialog id="personDlg" labelledBy="pdTitle">
        <form method="dialog" id="personForm">
          <h2 id="pdTitle" style="margin:0 0 10px">New person</h2>
          <div id="pdMatch" hidden></div>
          <div id="pdFields"><label for="pd_name">Full name <span class="req">required</span></label><input id="pd_name" type="text" autocomplete="off" />
            <label for="pd_email">Email</label><input id="pd_email" type="text" autocomplete="off" />
            <label for="pd_aliases">Aliases</label><input id="pd_aliases" type="text" autocomplete="off" placeholder="Sara, Sara K, SK" />
            <label for="pd_org">Organisation</label><input id="pd_org" type="text" autocomplete="off" />
            <label for="pd_role">Role</label><input id="pd_role" type="text" autocomplete="off" />
            <label for="pd_vip" class="pdvip">VIP</label><select id="pd_vip" class="pdvip"><option value="">No</option>
              <option value="management">Management</option><option value="client">Client</option><option value="yes">Yes</option></select></div>
          <div class="sub" id="pdErr" role="alert" style="color:var(--bad)"></div>
          <div class="curacts"><span class="sp"></span><button class="btn" value="cancel" formnovalidate>Cancel</button>
            <button type="button" class="btn primary" id="pdSave">Save</button></div>
        </form>
      </Dialog>
    </>
  );
}

/** Draw the shell's dialogs into #pageDialogs (the page's first start-up step). */
export function bootDialogs() {
  const host = document.getElementById("pageDialogs");
  if (host && !host.firstChild) render(<PageDialogs />, host);
}

/** Draw a dialog made on first use into a box of its own at the end of the page, and return the dialog element.
    @param {string} hostId @param {import("preact").VNode} dlg */
function later(hostId, dlg) {
  const host = document.createElement("div");
  host.id = hostId;
  document.body.appendChild(host);
  render(dlg, host);
  return /** @type {HTMLDialogElement} */ (host.firstElementChild);
}

/** The draft email (BL-53, drafts.js): made the first time it opens. */
export function makeDraftEmailDialog() {
  return later("deDlgHost",
    <Dialog id="deDlg" class="prepdlg" labelledBy="deTitle">
      <div class="prephead"><div style="flex:1"><div class="sub">Nothing is sent: copy it and paste it into Outlook</div><h2 id="deTitle"></h2></div>
        <button class="iconbtn" id="deClose" aria-label="Close"><Icon name="x" /></button></div>
      <div class="prepbody" id="deBody"></div>
    </Dialog>);
}

/** Undo changes (BL-164, activity.js): made the first time it opens; activity.js fills #actDlgBody. */
export function makeUndoDialog() {
  return later("actDlgHost", <Dialog id="actDlg" labelledBy="actDlgH"><div id="actDlgBody"></div></Dialog>);
}

/** The Prep popup (BL-286, projects.js): made the first time it opens. The header and toolbar (#prepTop), the facts line and
    invite (#prepLead) and Shape the meeting (#prepShape) are components mounted into it; the rest is drawn by projects.js. */
export function makePrepDialog() {
  return later("prepDlgHost",
    <Dialog id="prepDlg" labelledBy="prepTitle">
      <div id="prepTop"></div>
      <div class="prepbody" id="prepScroll"><div class="sub" id="prepPgStat" role="status"></div><div id="prepShape"></div><div id="prepLead"></div>
        <div id="prepAgenda" class="pkdrhost"></div><div id="prepBody"></div></div>
    </Dialog>);
}
