// @ts-check
/* ApprovePopup (#268, Minutes view v2; was BL-338's approve popup): Approve minutes is one click. This "Before approving" box
   (titled "Approve the minutes", as wide as the signed-off mockup's) appears only when a ticked item has a real problem (an owner who needs details, a possible duplicate). It lists just
   those, with Go back (Esc, a click outside, focus back on Approve minutes) and Approve anyway. Nothing else is asked.
   Cap's #268 review L1: it also says where the minutes will be filed and lists the checks still open on the page, as the
   v2.1.0 popup did. */
import { Dialog } from "../Dialog.jsx";
import { approveOpen } from "../../stores/minutes.js";

/** @typedef {{n: number, what: string, text: string}} Problem */
/** @typedef {import("./minutesDoc.js").Check} Check */

/** A filed path as its name and the last two folders. @param {string} p */
const filedAt = p => { const parts = p.split("/"); return { name: parts.pop() || p, folder: parts.slice(-2).join(" › ") }; };

/** The box. @param {{problems: Problem[], checks?: Check[], files?: string[], transcripts?: number, busy: boolean, onApprove: () => void}} props */
export function ApprovePopup({ problems, checks = [], files = [], transcripts = 0, busy, onApprove }) {
  const close = () => { approveOpen.value = false; };
  const one = problems.length === 1, filed = files.map(filedAt)[0];
  return (
    <Dialog open={approveOpen.value && problems.length !== 0} onClose={close} labelledBy="mnApproveH" id="mnApprove" class="mnapprove" focus="#mnApproveGo">
      <div class="mnap">
        <h2 id="mnApproveH">Approve the minutes</h2>
        <p class="sub">Before these minutes are approved, {one ? "one ticked item has" : `${problems.length} ticked items have`} something worth a look. Nothing else needs checking.</p>
        {filed ? <p class="sub mnap-filed">Files the minutes as <b>{filed.name}</b> in {filed.folder}{transcripts ? ", with the transcript in Transcripts" : ""}.</p> : null}
        <ul class="mnap-l">{problems.map((p, i) => <li key={`${p.n}:${i}`} data-n={p.n}><b>{p.what}</b><span>{p.text}</span></li>)}</ul>
        {checks.length ? <div class="mnap-ck" role="note"><b>{checks.length} check{checks.length === 1 ? "" : "s"} still open</b>
          <ul>{checks.map(c => <li key={c.id}>{c.note}</li>)}</ul></div> : null}
        <div class="mnap-foot">
          <button type="button" class="btn" id="mnApproveBack" onClick={close}>Go back</button>
          <button type="button" class="btn primary" id="mnApproveGo" disabled={busy} onClick={() => { close(); onApprove(); }}>Approve anyway</button>
        </div>
      </div>
    </Dialog>
  );
}
