// @ts-check
/* FilingDialog (#324, #332): "File the minutes". Shown by Approve minutes before anything is changed: for each project, the project and
   its Minutes folder in words, the file name in a field (the extension after it, fixed; a name already used shows the numbered one that
   will be used), and the transcript copy beside it. Cancel files nothing; Enter files and approves. A refused name stays in the
   dialog, in words. FiledNote is the message after an approve: where they went, with Open file and Open folder, and a moved or
   online-only file said in words. Desktop and 900 px; the classes are the approve popup's. */
import { render } from "preact";
import { Dialog } from "../Dialog.jsx";
import { cancelFiling, confirmFiling, dismissFiled, filedNote, filedProblem, filingAsk, filingError, openFiled, stemOf, typeFiling } from "../../stores/minutesFiling.js";

/** The box and the note. */
export function FilingDialog() {
  const a = filingAsk.value;
  const many = !!a && a.items.length > 1;
  return (<>
    <Dialog open={!!a} onClose={cancelFiling} labelledBy="mnFilingH" id="mnFiling" class="mnapprove" focus="#mnFilingName0">
      {a ? <form class="mnap" onSubmit={(e) => { e.preventDefault(); confirmFiling(); }}>
        <h2 id="mnFilingH">File the minutes</h2>
        <p class="sub">{many ? "The minutes are filed in each project's Minutes folder." : "Check where the minutes go and what they are called."} Cancel files nothing.</p>
        {a.items.map((it, i) => <div class="mnap-one" key={it.code} data-code={it.code} style="display:block">
          <div><b>{it.project}</b> <span class="sub">in {it.folder_label}</span></div>
          <div style="display:flex;gap:6px;align-items:center;margin-top:6px">
            <input class="pkdt" id={`mnFilingName${i}`} aria-label={`File name in ${it.project}`} style="flex:1;min-width:0" value={a.typed[it.code]}
              maxLength={140} onInput={(e) => typeFiling(it.code, /** @type {HTMLInputElement} */ (e.target).value)} />
            <span class="sub">{it.ext}</span>
          </div>
          {it.taken && stemOf(it.will_be, it.ext) === a.typed[it.code] ? <p class="sub" data-numbered>{it.filed_copy ? `A copy called “${it.name}” already exists, so these are numbered: “${it.will_be}”. If this meeting was filed before, cancel.`
            : `Another minutes called “${it.name}” are waiting, so these are numbered: “${it.will_be}”.`}</p> : null}
          {it.transcript ? <p class="sub">The transcript is filed beside it in {it.transcript.folder_label} as “{it.transcript.will_be}”.</p> : null}
          {it.local ? null : <p class="sub">That file is online-only in OneDrive.</p>}
        </div>)}
        {filingError.value ? <p class="sub" role="alert" id="mnFilingErr" style="color:var(--bad, #b00020)">{filingError.value}</p> : null}
        <div class="mnap-foot">
          <button type="button" class="btn" id="mnFilingNo" onClick={cancelFiling}>Cancel</button>
          <button type="submit" class="btn primary" id="mnFilingGo">File and approve</button>
        </div>
      </form> : null}
    </Dialog>
    <FiledNote />
  </>);
}

/** Where the minutes went, with Open file and Open folder. */
function FiledNote() {
  const n = filedNote.value;
  if (!n || filingAsk.value) return null;
  const first = n.items[0];
  const go = async (/** @type {"file"|"folder"} */ what) => { const r = await openFiled(what, { key: n.key }); filedProblem.value = r.ok ? "" : r.message; };
  return (
    <div class="snack on" role="status" data-minutes-filed style="bottom:64px">
      <span>{n.items.length > 1 ? `Filed in ${n.items.length} projects.` : `Filed as ${first.name} in ${first.folder_label}.`}{n.numbered && n.numbered.length ? " The name you chose was taken meanwhile, so it was numbered." : ""}{filedProblem.value ? ` ${filedProblem.value}` : ""}</span>
      <button type="button" data-filed="file" onClick={() => go("file")}>Open file</button>
      <button type="button" data-filed="folder" onClick={() => go("folder")}>Open folder</button>
      <button type="button" onClick={dismissFiled}>Close</button>
    </div>);
}

/** Draw the dialog once, into a host at the foot of the page (the first Approve minutes). */
export function mountFiling() {
  if (typeof document === "undefined" || document.getElementById("minutesFilingHost")) return;
  const el = document.createElement("div");
  el.id = "minutesFilingHost";
  document.body.appendChild(el);
  render(<FilingDialog />, el);
}
