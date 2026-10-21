// @ts-check
/* FirstThing (BL-295): what the last Close the day put on First thing tomorrow, heading Today's brief (D.day.first, read afresh by
   the server: an item already dealt with is left out). Each opens where it is dealt with: a proposal in Review (highlighted), an
   action, RAID item or decision in its peek, a file or a transcript in Intake. today.js mounts it into #ftList and shows #ftSec
   only when something is open. The session-start line lists the same (session.py). */
import { render } from "preact";
import { REV, pName } from "../../core/data.js";
import { go } from "../../core/nav.js";
import { irReveal } from "../../stores/intakeReview.js";

/** @typedef {{ref: string, kind: string, type: string, t: string, p?: string|null, open: boolean}} FirstItem */
/** @typedef {{day: string, day_shown: string, items: FirstItem[]}} First */

const TABLE = { Action: "actions", "RAID item": "raid", Decision: "decisions" };

/** Open a proposal's row in Review, highlighted. @param {string} ref p:<file>#<n | block> */
function ftOpenProposal(ref) {
  const [file, part] = ref.slice(2).split("#"), want = /^\d+$/.test(part) ? +part : part;
  go("intake-review");
  const r = REV.find(x => x.file === file && x.ref === want && !x.done);
  if (r) irReveal([r.n]);   /* #232-C: the meeting it came from opens */
}

/** One line of the list. @param {{x: FirstItem, n: number}} props */
function Line({ x, n }) {
  const id = x.ref.startsWith("i:") ? x.ref.slice(2) : "", k = id ? TABLE[x.type] || "actions" : "";
  /** @param {MouseEvent} e */
  const click = e => { e.preventDefault(); if (x.ref.startsWith("p:")) ftOpenProposal(x.ref); else go("intake-review", { stage: "arrived" }); };
  return (
    <li><span class="n">{n}</span><div class="tb">
      {id ? <a class="t" href="#" data-open={`${k}:${id}`}>{x.t || id}</a> : <a class="t" href="#" onClick={click}>{x.t || x.type}</a>}
      <p>{x.type}{x.p ? ` · ${pName(x.p)}` : ""}</p></div></li>
  );
}

/** The list, or nothing. @param {{first: First | null}} props */
export function FirstThing({ first }) {
  const items = ((first && first.items) || []).filter(x => x.open);
  return <>{items.map((x, i) => <Line x={x} n={i + 1} />)}</>;
}

/** Draw First thing into Today: the section shows only when something from the last close is still open.
    @param {First | null} first */
export function mountFirstThing(first) {
  const sec = document.getElementById("ftSec"), list = document.getElementById("ftList"), cnt = document.getElementById("nFt");
  if (!sec || !list) return;
  const n = ((first && first.items) || []).filter(x => x.open).length;
  sec.hidden = !n;
  if (cnt) cnt.textContent = n ? `from ${first.day_shown}` : "";
  render(<FirstThing first={first} />, list);
}
