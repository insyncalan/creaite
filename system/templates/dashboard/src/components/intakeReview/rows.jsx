// @ts-check
/* Intake and Review's rows (#232-0 skeleton, v2.5.0). MeetingRow is one meeting (232-A fills its actions: Process, Later, Not needed
   with a reason, progress on the row). The proposal rows live in proposals.jsx (232-B's file). Tokens and the app's own classes only
   (style.css, "#232 Intake and Review"). */
import { mtgBusy } from "../../intake.js";
import { pName } from "../../core/data.js";
import { fd } from "../../core/page.js";
import { irBusy, irClickMeeting, irNotes, irOpen } from "../../stores/intakeReview.js";
import { IconButton } from "../IconButton.jsx";
import { irAskReason, irCanProcess, irCanSetAside, irLater, irProcess } from "./actions.js";

export const IR_STATE_WORDS = { ready: "Transcript ready", waiting: "Waiting for the transcript", proposals: "proposals to check", done: "Done", running: "Drafting in the background" };
export const IR_GROUP_HEAD = {
  needs: ["Needs your decision", "Approved one by one: minutes, new decisions, new risks, closing updates and other bigger changes"],
  routine: ["Routine", "Each has a project and no conflict, and none is a change you approve one by one"],
};
const IR_KIND_WORDS = { actions: "Action", decisions: "Decision", update: "Update", draft: "Minutes", files: "File changes" };
/** The kind pill's word for a Review row. @param {any} r */
export const irKind = r => (r.kind === "raid" ? (r.rec && r.rec.type) || "Risk" : IR_KIND_WORDS[/** @type {keyof IR_KIND_WORDS} */ (r.kind)] || "Proposal");
const ageWords = (/** @type {number} */ d) => (d === 0 ? "today" : d === 1 ? "1 day" : `${d} days`);

/** A meeting's state in words, for its row and its card. @param {any} m @param {number} n proposals still to check */
export function irStateWords(m, n) {
  const state = irBusy.value.includes(m.id) ? "running" : m.state;
  const base = state === "proposals" ? `${n} ${IR_STATE_WORDS.proposals}` : IR_STATE_WORDS[/** @type {keyof IR_STATE_WORDS} */ (state)] || "";
  const age = state === "ready" || state === "proposals" ? ` · ${ageWords(m.age)}` : "";
  return `${base}${age}${m.later_back ? " · back from Later" : ""}`;
}

/** The progress bar a meeting shows while it is drafted in the background. */
export function Progress() { return <div class="icprog" role="progressbar" aria-label="Drafting in the background"><i></i></div>; }

/** The row's actions: Process, Later and Not needed (with a reason) while it is arrived; Check them while it has proposals.
    @param {{m: any, live?: number, mini?: boolean}} props */
export function RowActions({ m, live, mini }) {
  const running = irBusy.value.includes(m.id), blocked = irBusy.value.length > 0 || mtgBusy();
  const open = irOpen.value === m.id;
  if (running) return <button type="button" class="mini" disabled data-ira="processing">Processing</button>;
  if (m.stage === "drafted") return mini ? null : <button type="button" class="mini" data-ira="open" onClick={() => irClickMeeting(m.id)}>{open ? "Close" : "Check them"}</button>;
  if (!irCanSetAside(m)) return m.stage === "approved" ? <span class="icsub">Done</span> : null;
  return <>
    {irCanProcess(m) ? <button type="button" class="mini" data-ira="process" disabled={blocked} title={blocked ? "ask creaite is busy; try again when it's finished" : ""}
      onClick={() => irProcess(m)}>Process</button> : null}
    {" "}<button type="button" class="mini" data-ira="later" title="Hide it until its transcript arrives" onClick={() => irLater(m)}>Later</button>
    {" "}<IconButton icon="x" label="Not needed, with a reason" cls="no" data={{ ira: "notneeded" }} haspopup="menu"
      onClick={e => irAskReason(m, /** @type {HTMLElement} */ (e.currentTarget))} />
  </>;
}

/** @param {{m: any, live: {needs: number[], routine: number[]}}} props */
export function MeetingRow({ m, live }) {
  const open = irOpen.value === m.id, n = live.needs.length + live.routine.length;
  const state = irBusy.value.includes(m.id) ? "running" : m.state;
  const can = m.stage === "drafted";
  const note = irNotes.value[m.id];
  return (
    <tr class={`click irmeet${open ? " icopen" : ""}`} data-irm={m.id} data-stage={m.stage} data-state={state} tabindex={0}
      aria-expanded={can ? open : undefined}
      onClick={e => { if (!(/** @type {Element} */ (e.target)).closest("button,a,input")) irClickMeeting(m.id); }}>
      <td class="title">
        <b class="icmeethd">{m.title}</b>
        {m.stale ? <> <span class="tag stale">Stale · {ageWords(m.age)}</span></> : null}
        <div class="why">{m.day ? fd(m.day) : ""}{m.start ? ` ${m.start}${m.end ? `–${m.end}` : ""}` : ""}{m.p && !m.private ? ` · ${pName(m.p)}` : ""}</div>
        <div class="why">{irStateWords(m, n)}</div>
        {state === "running" ? <><div class="why">ask creaite stays free</div><Progress /></> : null}
        {note ? <div class="why irnote" role="status">{note}</div> : null}
      </td>
      <td class="iracts"><RowActions m={m} live={n} /></td>
    </tr>
  );
}
