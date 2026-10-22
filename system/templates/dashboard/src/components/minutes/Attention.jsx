// @ts-check
/* Attention (#302 A): the strip over the minutes that says how many ticked items still need an owner or a date, with a chip for each
   (a click shows only those rows; click again to show everything) and Next, which scrolls to the next one. Nothing here changes
   the record: it only filters and moves the page. The rows' own flags ("Needs an owner", "Needs a date", "Vague date: pick one")
   are drawn by ItemTable. Internal and local, like the rest of the view. */
import { signal } from "@preact/signals";
import { needsOf, trackedKinds } from "./track.js";

/** @typedef {import("../report/Sheet.jsx").SheetDoc} SheetDoc */

/** The chip pressed ("owner" or "date"), or "" for everything; and the row Next last moved to. */
export const attnFilter = signal(/** @type {"owner"|"date"|""} */ (""));
export const attnFocus = signal(/** @type {number|null} */ (null));

/** Whether a row is hidden by the chip pressed. @param {{owner: boolean, date: boolean}|undefined} need @param {string} f */
export const hiddenBy = (need, f) => !!f && !(need && (f === "owner" ? need.owner : need.date));

/** The strip. @param {{doc: SheetDoc, plan: any, checks: any[]}} props */
export function Attention({ doc, plan, checks }) {
  const need = needsOf(doc, plan, checks), tot = Object.values(trackedKinds(doc, plan)).reduce((a, b) => a + b, 0);
  if (!tot) return null;
  const no = [...need.values()].filter(x => x.owner).length, nd = [...need.values()].filter(x => x.date).length;
  const f = (attnFilter.value === "owner" && no) || (attnFilter.value === "date" && nd) ? attnFilter.value : "";
  const next = () => {
    const list = [...need.keys()].filter(n => !f || !hiddenBy(need.get(n), f)), at = list.indexOf(/** @type {number} */ (attnFocus.value));
    const n = list[(at + 1) % list.length];
    attnFocus.value = n;
    const row = document.querySelector(`#v-minutes tr.mi[data-n='${n}']`);
    if (row) row.scrollIntoView({ block: "center", behavior: "smooth" });
  };
  if (!need.size) return <div class="mnattn ok" id="mnAttn" role="status"><b>Every tracked item has an owner and a date.</b></div>;
  return (
    <div class="mnattn" id="mnAttn" role="status" data-need={need.size}>
      <b>{need.size} of {tot} tracked item{tot === 1 ? "" : "s"} need{need.size === 1 ? "s" : ""} attention</b>
      {no ? <button type="button" class="mnfchip" data-fl="owner" aria-pressed={f === "owner" ? "true" : "false"}
        onClick={() => { attnFilter.value = f === "owner" ? "" : "owner"; }}>{no} need{no === 1 ? "s" : ""} an owner</button> : null}
      {nd ? <button type="button" class="mnfchip" data-fl="date" aria-pressed={f === "date" ? "true" : "false"}
        onClick={() => { attnFilter.value = f === "date" ? "" : "date"; }}>{nd} need{nd === 1 ? "s" : ""} a date</button> : null}
      <span class="sub">{f ? "Showing only these. Press the chip again to show everything." : "Press a chip to show only these."}</span>
      <button type="button" class="btn sm" id="mnNext" onClick={next}>Next ↓</button>
    </div>
  );
}
