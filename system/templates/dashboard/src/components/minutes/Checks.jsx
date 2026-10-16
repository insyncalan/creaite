// @ts-check
/* Checks (v2.1.0 P7, BL-338 point 5): a check shown inline. The words it is about are underlined in place (CheckMark); a click,
   or Enter on it, opens what was said and who said it, with the check's own buttons (Use that, Keep mine, Show in the
   transcript, Pick from the register). The view does what the button says (MinutesCtx.onCheck). Creaite only: never exported,
   never in Show as exported. A check left open is listed when approving. */
import { useContext, useRef, useState } from "preact/hooks";
import { MinutesCtx } from "./context.js";
import { Pop } from "./Pop.jsx";

/** @typedef {import("./minutesDoc.js").Check} Check */

/** The words a check is about, underlined, opening the check. @param {{check: Check, children?: any}} props */
export function CheckMark({ check, children }) {
  const m = useContext(MinutesCtx);
  const [open, setOpen] = useState(false);
  const btn = useRef(/** @type {HTMLButtonElement|null} */ (null));
  return (
    <span class="mnpopw">
      <button type="button" ref={btn} class="mncheck" data-check={check.id} aria-haspopup="dialog" aria-expanded={open ? "true" : "false"}
        aria-label={`Check: ${check.note}`} onClick={() => setOpen(!open)}>{children || check.quote}</button>
      <Pop open={open} onClose={() => setOpen(false)} label="Check against the transcript" anchor={btn} cls="mnck" wide>
        <p class="mnck-note">{check.note}</p>
        {check.last ? <p class="sub mnck-last">{check.last}</p> : null}
        <div class="mnck-acts">
          {check.actions.map(a => <button key={a.id} type="button" class={`btn sm${a.id === "use" ? " primary" : ""}`} data-ckact={a.id}
            onClick={() => { setOpen(false); if (m) m.onCheck(check, a.id); }}>{a.label}</button>)}
        </div>
      </Pop>
    </span>
  );
}

/** A text with each check's quote underlined at its first place in it. @param {{text: string, checks: Check[]}} props */
export function Checked({ text, checks }) {
  const marks = checks.map(c => ({ c, at: c.quote ? text.indexOf(c.quote) : -1 })).filter(x => x.at >= 0).sort((a, b) => a.at - b.at);
  if (!marks.length) return <span>{text}</span>;
  const out = [];
  let i = 0;
  for (const { c, at } of marks) {
    if (at < i) continue;
    out.push(text.slice(i, at));
    out.push(<CheckMark key={c.id} check={c}>{c.quote}</CheckMark>);
    i = at + c.quote.length;
  }
  out.push(text.slice(i));
  return <span>{out}</span>;
}
