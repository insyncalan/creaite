// @ts-check
/* Coverage (v2.1.0 P7, BL-338 points 11 and 12; BL-339 moves BL-209's coverage here): a block of the minutes shown in creaite
   only (a §4.3 extra, never exported), where the meeting had an agenda or a prep page. Each point is Covered, Touched on or Not
   discussed (P4's meta.coverage). Deal with it… on a point that wasn't covered: carry it to the series' next meeting (on its
   draft agenda and Prep, /api/meeting/carry's store), set up a separate session (an action for Alan, due Friday; creaite never
   makes the invite), No longer needed or Covered enough; with Add a line to the minutes (on by default) a line goes under Not
   covered in this meeting. Each is P4's `cover` change, with Undo (`uncover`). Milestone notes (never a change, BL-186): Review
   the milestone opens it in the peek. */
import { useContext, useState } from "preact/hooks";
import { Menu } from "../Menu.jsx";
import { openMilestone } from "../../milestones.js";
import { MinutesCtx } from "./context.js";

/** @typedef {{point: string, verdict: string, action?: {how: string, line: string, item?: number}}} Point */

const HOW = [{ id: "carry", name: "Carry it to the next meeting", line: "On the series' next agenda and Prep, marked carried" },
  { id: "session", name: "Set up a separate session", line: "Adds an action for you, due Friday; creaite never makes the invite" },
  { id: "drop", name: "No longer needed", line: "Nothing more is done about it" },
  { id: "enough", name: "Covered enough", line: "It was covered well enough in this meeting" }];
const DONE = { carry: "Carried to the next meeting", session: "A separate session is to be set up", drop: "No longer needed", enough: "Covered enough" };
const CLS = { "Covered": "ok", "Touched on": "warn", "Not discussed": "bad" };

/** The coverage block. @param {{c: {doc: any, editing: boolean, readOnly: boolean}}} props */
export function Coverage({ c }) {
  const m = useContext(MinutesCtx);
  const [line, setLine] = useState(true);
  const meta = c.doc.meta || {}, points = /** @type {Point[]} */ (meta.coverage || []), notes = /** @type {{id: string, note: string}[]} */ (meta.milestones || []);
  if (!points.length && !notes.length) return null;
  const live = c.editing && !!m;
  return (
    <div class="mncov" aria-labelledby="mnCovH">
      <div class="mncov-h"><h2 id="mnCovH">Agenda coverage</h2><span class="sub">In creaite only, never in the minutes sent</span></div>
      {points.length ? <ul class="mncov-l">
        {points.map(p => (
          <li key={p.point} data-point={p.point}>
            <span class={`mnverdict ${CLS[/** @type {keyof CLS} */ (p.verdict)] || ""}`}>{p.verdict}</span>
            <span class="mncov-p">{p.point}</span>
            {p.action ? <span class="mncov-done">{DONE[/** @type {keyof DONE} */ (p.action.how)] || p.action.how}
              {live && m ? <button type="button" class="linkbtn" onClick={() => m.change({ op: "uncover", point: p.point })}>Undo</button> : null}</span>
              : live && m && p.verdict !== "Covered" ? <Menu label="Deal with it…" btnCls="btn sm" menuLabel={`Deal with ${p.point}`} items={HOW}
                data={{ mncover: p.point }} onPick={how => m.change({ op: "cover", point: p.point, how, line }, { op: "uncover", point: p.point })} /> : null}
          </li>
        ))}
      </ul> : null}
      {live && points.some(p => p.verdict !== "Covered" && !p.action) ? <label class="mncov-line"><input type="checkbox" checked={line}
        onChange={e => setLine(/** @type {HTMLInputElement} */ (e.currentTarget).checked)} /> Add a line to the minutes</label> : null}
      {notes.length ? <ul class="mncov-ms">{notes.map(x => (
        <li key={x.id}><span>{x.note}</span> <button type="button" class="btn sm" onClick={() => openMilestone(x.id)}>Review the {x.id} milestone</button></li>))}</ul> : null}
    </div>
  );
}
