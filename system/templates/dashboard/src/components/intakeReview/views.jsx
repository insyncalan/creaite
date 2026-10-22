// @ts-check
/* Intake and Review's three views (#232-0 skeleton, v2.5.0): minimal, drawn from the merged row model so 232-A and 232-B can fill
   them. List: the stage counts (on the page) and one list, each meeting opening in place. Board: three columns, a card per meeting,
   the open meeting's proposals under the board. Two panes: the meetings on the left, the selected one on the right. Each ends with
   From mail and Teams, and Other proposals when there are any. */
import { pName } from "../../core/data.js";
import { IR_STAGES, irLive } from "../../core/irFold.js";
import { irBusy, irClickMeeting, irDone, irHeld, irLiveCounts, irOpen, irQuery, irSel } from "../../stores/intakeReview.js";
import { ProposalGroups } from "./proposals.jsx";
import { FileFacts, IrNote, MeetingRow, Progress, RowActions, StageTrack, irRunningWords, irStateWords, irWhen } from "./rows.jsx";

export const IR_STAGE_NAMES = { arrived: "Arrived", drafted: "Drafted", approved: "Approved" };
const IR_EMPTY = "Nothing here. Meetings appear when they end.";
const irNone = () => (irQuery.value.trim() ? "Nothing matches your search." : IR_EMPTY);

/** @param {{model: any}} props */
function MailSections({ model }) {
  const mail = irLive(model.mail, irDone, irHeld), other = irLive(model.other, irDone, irHeld);
  const nm = mail.needs.length + mail.routine.length, no = other.needs.length + other.routine.length;
  return <>
    <div class="rgroup irsec" data-irsec="mail"><h2>From mail and Teams <span class="sub rgc">{nm} suggestion{nm === 1 ? "" : "s"}</span></h2></div>
    {nm ? <div class="tbl"><table><tbody><ProposalGroups groups={model.mail} /></tbody></table></div> : <div class="empty">{irQuery.value.trim() ? "Nothing from mail or Teams matches your search." : "Nothing from mail or Teams to approve."}</div>}
    {no ? <>
      <div class="rgroup irsec" data-irsec="other"><h2>Other suggestions <span class="sub rgc">{no}</span></h2></div>
      <div class="tbl"><table><tbody><ProposalGroups groups={model.other} /></tbody></table></div>
    </> : null}
  </>;
}

/** One meeting's rows: the meeting, and when it is open its groups hanging under it on the rail. @param {{m: any}} props */
function MeetingBlock({ m }) {
  const live = irLive(m.groups, irDone, irHeld);
  return <>
    <MeetingRow m={m} live={live} />
    {irOpen.value === m.id ? <ProposalGroups groups={m.groups} meet={m.title} child /> : null}
  </>;
}

/** @param {{model: any, list: any[]}} props */
export function ListView({ model, list }) {
  return <div data-irv="list">
    {list.length ? <div class="tbl"><table><tbody>{list.map(m => <MeetingBlock key={m.id} m={m} />)}</tbody></table></div> : <div class="empty">{irNone()}</div>}
    <MailSections model={model} />
  </div>;
}

/** @param {{model: any}} props */
export function BoardView({ model }) {
  const open = model.meetings.find((/** @type {any} */ m) => m.id === irOpen.value);
  return <div data-irv="board">
    <div class="icboard">{IR_STAGES.map(g => {
      const l = model.meetings.filter((/** @type {any} */ m) => m.stage === g);
      return <div class="iccol" data-ircol={g}>
        <h2>{IR_STAGE_NAMES[/** @type {keyof IR_STAGE_NAMES} */ (g)]} <span class="sub rgc">{l.length}</span></h2>
        {l.length ? l.map((/** @type {any} */ m) => (
          <div key={m.id} class="card iccard click" data-irm={m.id} data-stage={m.stage} data-state={irBusy.value.includes(m.id) ? "running" : m.state} tabindex={0}
            onClick={e => { if (!(/** @type {Element} */ (e.target)).closest("button,a,input")) irClickMeeting(m.id); }}>
            <div class="t">{m.title}</div>
            {m.src === "upload" ? <FileFacts m={m} n={m.groups.needs.length + m.groups.routine.length} /> : <>
              <div class="why">{m.p && !m.private && !m.confidential ? pName(m.p) : ""}</div>
              <div class="why">{irStateWords(m, m.groups.needs.length + m.groups.routine.length)}</div>
            </>}
            {irBusy.value.includes(m.id) ? <Progress words={irRunningWords(m)} /> : null}
            <IrNote m={m} />
            <div class="iccardacts"><RowActions m={m} /></div>
          </div>
        )) : <div class="empty">Nothing here.</div>}
      </div>;
    })}</div>
    {open ? <div class="tbl"><table><tbody><ProposalGroups groups={open.groups} meet={open.title} child /></tbody></table></div> : null}
    <MailSections model={model} />
  </div>;
}

/** @param {{model: any, list: any[]}} props */
export function TwoPanes({ model, list }) {
  const sel = list.find(m => m.id === irSel.value) || list[0], c = irLiveCounts();
  const hidden = (/** @type {any} */ m) => m.private || m.confidential;      /* title and times only */
  const right = (/** @type {any} */ m) => { const n = m.groups.needs.length + m.groups.routine.length; return n ? `${n} suggestion${n === 1 ? "" : "s"}` : m.stage === "arrived" && m.state === "ready" ? "ready" : ""; };
  return <div data-irv="two">
    <div class="icsplit">
      <div>
        <div class="icpipe icsum"><span class="icsub">Arrived {c.arrived} → Drafted {c.drafted} → Approved {c.approved}</span></div>
        {list.length ? <div class="tbl"><table><tbody>{list.map(m => (
        <tr key={m.id} class={`click${sel && sel.id === m.id ? " sel" : ""}`} data-irm={m.id} tabindex={0} onClick={() => { irSel.value = m.id; }}>
          <td class="title">{m.title}<div class="why">{IR_STAGE_NAMES[/** @type {keyof IR_STAGE_NAMES} */ (m.stage)]} · {irWhen(m)}</div></td>
          <td class="icsub irright">{right(m)}</td>
        </tr>
      ))}</tbody></table></div> : <div class="empty">{irNone()}</div>}</div>
      <div class="card icdet" data-irdet={sel ? sel.id : ""}>
        {sel ? <>
          <h2 style={{ margin: "0 0 4px" }}>{sel.title}</h2>
          <div class="why">{irWhen(sel)}{sel.src !== "upload" && sel.p && !hidden(sel) ? ` · ${pName(sel.p)}` : ""}</div>
          <div class="icrack"><StageTrack m={sel} /></div>
          {sel.src === "upload" ? <FileFacts m={sel} n={sel.groups.needs.length + sel.groups.routine.length} /> : <div class="why">{irStateWords(sel, sel.groups.needs.length + sel.groups.routine.length)}</div>}
          {sel.stage === "arrived" && sel.state === "waiting" ? <div class="empty">Waiting for the transcript. It appears here when the meeting’s transcript arrives.</div> : null}
          {irBusy.value.includes(sel.id) ? <Progress words={irRunningWords(sel)} /> : null}
          <IrNote m={sel} />
          <div class="iccardacts"><RowActions m={sel} mini /></div>
          <div class="tbl"><table><tbody><ProposalGroups groups={sel.groups} meet={sel.title} /></tbody></table></div>
        </> : <div class="empty">Select a meeting.</div>}
      </div>
    </div>
    <MailSections model={model} />
  </div>;
}
