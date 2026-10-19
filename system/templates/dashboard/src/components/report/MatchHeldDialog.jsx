// @ts-check
/* MatchHeldDialog (v2.5.0): what Match internal held back. Match internal runs the client gate before it copies a section
   (stores/clientReport.js matchInternal); a section whose internal wording would fail the gate stays as it was, and this lists it
   with the findings, the sections copied, and nothing else. It writes nothing. */
import { Dialog } from "../Dialog.jsx";
import { crHeld } from "../../stores/clientReport.js";

export function MatchHeldDialog() {
  const h = crHeld.value;
  const close = () => { crHeld.value = null; };
  return (
    <Dialog open={!!h} onClose={close} labelledBy="crHeldH" id="crHeldDlg" class="crdlg" focus="[data-crheldok]">
      <h2 id="crHeldH">Match internal held some sections back</h2>
      {h ? <div data-crheld>
        {h.message ? <p class="crbad" role="alert" data-crheldmsg>{h.message}</p> : null}
        <ul class="crleft">{h.held.map(x => <li key={x.id} data-crheldsec={x.id}><b>Not matched: {x.heading}</b>{x.findings.length ? <> has internal wording: {x.findings.join("; ")}</> : null}</li>)}</ul>
        {h.skipped && h.skipped.length ? <ul class="crleft">{h.skipped.map(x => <li key={x.id} data-crskipsec={x.id}>{x.heading}: internal only, add it to the client report yourself</li>)}</ul> : null}
        {h.copied.length ? <p class="sub" data-crheldcopied>Matched: {h.copied.join(", ")}.</p> : <p class="sub">Nothing was copied; the client report is as it was.</p>}
      </div> : null}
      <div class="crdacts"><button type="button" class="btn primary" data-crheldok onClick={close}>OK</button></div>
    </Dialog>
  );
}
