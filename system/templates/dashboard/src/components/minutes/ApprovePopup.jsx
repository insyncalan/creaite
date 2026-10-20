// @ts-check
/* ApprovePopup (#268, Minutes view v2; was BL-338's approve popup): Approve minutes is one click. This "Before approving" box
   (titled "Approve the minutes", as wide as the signed-off mockup's) appears only when a ticked item has a real problem (an owner who needs details, a possible duplicate). It lists just
   those, with Go back (Esc, a click outside, focus back on Approve minutes) and Approve anyway. Nothing else is asked. */
import { Dialog } from "../Dialog.jsx";
import { approveOpen } from "../../stores/minutes.js";

/** @typedef {{n: number, what: string, text: string}} Problem */

/** The box. @param {{problems: Problem[], busy: boolean, onApprove: () => void}} props */
export function ApprovePopup({ problems, busy, onApprove }) {
  const close = () => { approveOpen.value = false; };
  const one = problems.length === 1;
  return (
    <Dialog open={approveOpen.value && problems.length > 0} onClose={close} labelledBy="mnApproveH" id="mnApprove" class="mnapprove" focus="#mnApproveGo">
      <div class="mnap">
        <h2 id="mnApproveH">Approve the minutes</h2>
        <p class="sub">Before these minutes are approved, {one ? "one ticked item has" : `${problems.length} ticked items have`} something worth a look. Nothing else needs checking.</p>
        <ul class="mnap-l">{problems.map((p, i) => <li key={`${p.n}:${i}`} data-n={p.n}><b>{p.what}</b><span>{p.text}</span></li>)}</ul>
        <div class="mnap-foot">
          <button type="button" class="btn" id="mnApproveBack" onClick={close}>Go back</button>
          <button type="button" class="btn primary" id="mnApproveGo" disabled={busy} onClick={() => { close(); onApprove(); }}>Approve anyway</button>
        </div>
      </div>
    </Dialog>
  );
}
