// @ts-check
/* Intake and Review's rows (#232-0 skeleton, v2.5.0). MeetingRow is one meeting (232-A fills its actions: Process, Later, Not needed
   with a reason, progress on the row). The proposal rows live in proposals.jsx (232-B's file). Tokens and the app's own classes only
   (style.css, "#232 Intake and Review"). */
import { pName } from "../../core/data.js";
import { fd } from "../../core/page.js";
import { irBusy, irClickMeeting, irOpen } from "../../stores/intakeReview.js";

export const IR_STATE_WORDS = { ready: "Transcript ready", waiting: "Waiting for the transcript", proposals: "proposals to check", done: "Done", running: "Drafting in the background" };
export const IR_GROUP_HEAD = {
  needs: ["Needs your decision", "Approved one by one: minutes, new decisions, new risks, closing updates and other bigger changes"],
  routine: ["Routine", "Each has a project and no conflict, and none is a change you approve one by one"],
};
const IR_KIND_WORDS = { actions: "Action", decisions: "Decision", update: "Update", draft: "Minutes", files: "File changes" };
/** The kind pill's word for a Review row. @param {any} r */
export const irKind = r => (r.kind === "raid" ? (r.rec && r.rec.type) || "Risk" : IR_KIND_WORDS[/** @type {keyof IR_KIND_WORDS} */ (r.kind)] || "Proposal");
const ageWords = (/** @type {number} */ d) => (d === 0 ? "today" : d === 1 ? "1 day" : `${d} days`);

/** @param {{m: any, live: {needs: number[], routine: number[]}}} props */
export function MeetingRow({ m, live }) {
  const open = irOpen.value === m.id, n = live.needs.length + live.routine.length;
  const state = irBusy.value.includes(m.id) ? "running" : m.state;
  const words = state === "proposals" ? `${n} ${IR_STATE_WORDS.proposals}` : IR_STATE_WORDS[/** @type {keyof IR_STATE_WORDS} */ (state)] || "";
  const can = m.stage === "drafted";
  return (
    <tr class={`click irmeet${open ? " icopen" : ""}`} data-irm={m.id} data-stage={m.stage} data-state={state} tabindex={0}
      aria-expanded={can ? open : undefined}
      onClick={e => { if (!(/** @type {Element} */ (e.target)).closest("button,a,input")) irClickMeeting(m.id); }}>
      <td class="title">
        <b class="icmeethd">{m.title}</b>
        {m.stale ? <> <span class="tag stale">Stale · {ageWords(m.age)}</span></> : null}
        <div class="why">{m.day ? fd(m.day) : ""}{m.start ? ` ${m.start}` : ""}{m.p ? ` · ${pName(m.p)}` : ""}</div>
        <div class="why">{words}{m.later_back ? " · back from Later" : ""}</div>
      </td>
      <td class="iracts">
        {can ? <button type="button" class="mini" data-ira="open" onClick={() => irClickMeeting(m.id)}>{open ? "Close" : "Check them"}</button> : null}
      </td>
    </tr>
  );
}
