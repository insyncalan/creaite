// @ts-check
/* Intake and Review's rows (#232-0 skeleton, v2.5.0). MeetingRow is one meeting (232-A fills its actions: Process, Later, Not needed
   with a reason, progress on the row); ProposalGroups draws an open meeting's groups, or the mail and other sections, with each
   proposal as a plain line (232-B replaces ProposalLine with the full row: kind pill, title, the emphasised line, the quote, the
   source, Approve and Reject, and the peek). Tokens and the app's own classes only (style.css, "#232 Intake and Review"). */
import { pName } from "../../core/data.js";
import { fd } from "../../core/page.js";
import { irGroupsShown } from "../../core/irFold.js";
import { irBusy, irClickMeeting, irDone, irOpen, irRow } from "../../stores/intakeReview.js";

export const IR_STATE_WORDS = { ready: "Transcript ready", waiting: "Waiting for the transcript", proposals: "proposals to check", done: "Done", running: "Drafting in the background" };
export const IR_GROUP_HEAD = {
  needs: ["Needs your decision", "Approved one by one: minutes, new decisions, new risks, closing updates and other bigger changes"],
  routine: ["Routine", "Each has a project and no conflict, and none is a change you approve one by one"],
};
const KIND = { actions: "Action", decisions: "Decision", update: "Update", draft: "Minutes", files: "File changes" };
/** The kind pill's word for a Review row. @param {any} r */
export const irKind = r => (r.kind === "raid" ? (r.rec && r.rec.type) || "Risk" : KIND[/** @type {keyof KIND} */ (r.kind)] || "Proposal");
const ageWords = (/** @type {number} */ d) => (d === 0 ? "today" : d === 1 ? "1 day" : `${d} days`);

/** @param {{m: any, live: {needs: number[], routine: number[]}}} props */
export function MeetingRow({ m, live }) {
  const open = irOpen.value === m.id, n = live.needs.length + live.routine.length;
  const state = irBusy.value.includes(m.id) ? "running" : m.state;
  const words = state === "proposals" ? `${n} ${IR_STATE_WORDS.proposals}` : IR_STATE_WORDS[/** @type {keyof IR_STATE_WORDS} */ (state)] || "";
  const can = m.stage === "drafted";
  return (
    <tr class={`click irmeet${open ? " icopen" : ""}`} data-irm={m.id} data-stage={m.stage} data-state={state} tabindex={0}
      aria-expanded={can ? String(open) : undefined}
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

/** One proposal as a plain line (232-B replaces it). @param {{n: number, child?: boolean}} props */
export function ProposalLine({ n, child }) {
  const r = irRow(n);
  if (!r) return null;
  return (
    <tr class={`irprop${child ? " mchild" : ""}`} data-irn={n}>
      <td class="title"><span class="ickind">{irKind(r)}</span> <b class="icttl">{(r.rec && r.rec.t) || ""}</b>{r.p ? <span class="sub"> · {pName(r.p)}</span> : null}</td>
      <td class="iracts"></td>
    </tr>
  );
}

/** The groups under an open meeting (child rows on its rail) or in the mail and other sections.
    @param {{groups: {needs: number[], routine: number[]}, meet?: string, child?: boolean}} props */
export function ProposalGroups({ groups, meet, child }) {
  return <>{irGroupsShown(groups, irDone).map(g => (
    <>
      <tr class={`icsubhead ${g.kind}${child ? " child" : ""}`} data-irg={g.kind}><td colSpan={2}>
        <span class="icsh">{meet ? `${meet} · ` : ""}{IR_GROUP_HEAD[g.kind][0]} · {g.ns.length}</span>
        <span class="icshs">{IR_GROUP_HEAD[g.kind][1]}</span>
        {g.kind === "routine" ? <span class="icshr"><button type="button" class="mini ok" data-ira="routine" disabled title="232-B">Approve routine ({g.ns.length})</button></span> : null}
      </td></tr>
      {g.ns.map(n => <ProposalLine n={n} child={child} />)}
    </>
  ))}</>;
}
