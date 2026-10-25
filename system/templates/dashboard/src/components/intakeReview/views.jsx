// @ts-check
/* Intake and Review's three views (#232-0 skeleton, v2.5.0): minimal, drawn from the merged row model so 232-A and 232-B can fill
   them. List: the stage counts (on the page) and one list, each meeting opening in place. Board: three columns, a card per meeting,
   the open meeting's proposals under the board. Two panes: the meetings on the left, the selected one on the right. Each ends with
   From mail and Teams, and Other proposals when there are any. */
import { pName } from "../../core/data.js";
import { IR_MAIL_CAP, irCapGroups, irGroupMeetings, irIsFolded, irLive, irSplitTail } from "../../core/irFold.js";
import { fd } from "../../core/page.js";
import { irBusy, irClickFold, irClickMeeting, irDone, irFileKinds, irFolded, irGroup, irHeld, irLiveCounts, irMailAll, irOpen, irQuery, irSel, irStage, irStateFilter } from "../../stores/intakeReview.js";
import { ProposalGroups } from "./proposals.jsx";
import { irRowKey, irRowMenu } from "./selection.js";
import { FileFacts, MatchChip, IrNote, IrTick, MeetingRow, Progress, RowActions, StageTrack, IrStateLine, irRunningWords, irWhen } from "./rows.jsx";

/** The Board's columns: the work first, Arrived last (#340). */
const IR_BOARD = ["drafted", "approved", "arrived"];
export const IR_STAGE_NAMES = { arrived: "Arrived", drafted: "Drafted", approved: "Approved" };
const IR_EMPTY = "Nothing here. Meetings appear when they end.";
const irNone = () => (irQuery.value.trim() ? "Nothing matches your search." : IR_EMPTY);

/** The suggestions of a meeting still waiting on the page (what the chip and the counts read). @param {any} m */
const liveN = m => { const l = irLive(m.groups, irDone, irHeld); return l.needs.length + l.routine.length; };

/** #323: the rows under their Group by headings (None: one list, no headings). Headings carry the count. */
const irGroups = (/** @type {any[]} */ list) => irGroupMeetings(list, irGroup.value, { done: irDone, kinds: irFileKinds.value, day: fd, project: pName });
const GroupHead = ({ g }) => <tr class="icgrouphd" data-irgroup={g.key || "none"}><td colSpan={2}><b>{g.label}</b> <span class="sub">{g.items.length}</span></td></tr>;

/** #340: the meetings still waiting for a transcript fold away like Later and Not needed. They open by themselves when a stage, a Show
    choice, a search or a Group by is looking at them, so nothing the person asked for is hidden. */
export const irTailHeld = () => irStage.value === "arrived" || irStateFilter.value === "waiting" || !!irQuery.value.trim();      /* something the person asked for holds the tail open */
export const irTailFolded = () => irGroup.value === "none" && irIsFolded(irFolded.value, "waiting") && !irTailHeld();

/** The waiting tail's heading: its count and Show / Hide. @param {{n: number}} props */
function TailHead({ n }) {
  const folded = irTailFolded(), held = irTailHeld();      /* held open by a step, Show choice or search: Hide would do nothing, so it is not offered */
  return <div class="rgroup irsec" data-irsec="waiting"><h2>Waiting for the transcript <span class="sub rgc">{n}</span> {held ? null : <button type="button" class="linkbtn" data-irfold="waiting" aria-expanded={!folded} onClick={() => irClickFold("waiting")}>{folded ? "Show" : "Hide"}</button>}</h2></div>;
}

/** @param {{model: any}} props */
function MailSections({ model }) {
  const mail = irLive(model.mail, irDone, irHeld), other = irLive(model.other, irDone, irHeld);
  const nm = mail.needs.length + mail.routine.length, no = other.needs.length + other.routine.length;
  const cap = irCapGroups(model.mail, irDone, irHeld, IR_MAIL_CAP), all = irMailAll.value || cap.total <= IR_MAIL_CAP;
  return <>
    <div class="rgroup irsec" data-irsec="mail"><h2>From mail and Teams <span class="sub rgc">{nm} suggestion{nm === 1 ? "" : "s"}</span></h2></div>
    {nm ? <div class="tbl"><table><tbody><ProposalGroups groups={all ? model.mail : cap.groups} /></tbody></table>
      {cap.total > IR_MAIL_CAP ? <p class="sub irmore"><button type="button" class="linkbtn" data-ira="mailall" onClick={() => { irMailAll.value = !irMailAll.value; }}>{all ? `Show the first ${IR_MAIL_CAP}` : `Show all ${cap.total}`}</button></p> : null}</div> : <div class="empty">{irQuery.value.trim() ? "Nothing from mail or Teams matches your search." : "Nothing from mail or Teams to approve."}</div>}
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
    {irOpen.value === m.id ? <ProposalGroups groups={m.groups} meet={m.title} child meetId={m.id} /> : null}
  </>;
}

/** The List. #340: the work to decide leads: Drafted and Approved meetings first, then what was sent by mail and Teams, then Arrived
    (the long tail of meetings waiting for a transcript), so the first approvals are in the first screen. With a Group by (#323) the
    headings keep their rows together, each led the same way, and mail and Teams comes first. @param {{model: any, list: any[]}} props */
export function ListView({ model, list }) {
  const { work, tail } = irSplitTail(list), grouped = irGroup.value !== "none", folded = irTailFolded();
  const table = (/** @type {any[]} */ rows, /** @type {string} */ part) => rows.length ? <div class="tbl" data-irpart={part}><table><tbody>{irGroups(rows).map(g => <>{grouped ? <GroupHead g={g} /> : null}{g.items.map((/** @type {any} */ m) => <MeetingBlock key={m.id} m={m} />)}</>)}</tbody></table></div> : null;
  const tailRows = tail.length && !grouped ? <><TailHead n={tail.length} />{folded ? null : table(tail, "arrived")}</> : null;
  if (!list.length) return <div data-irv="list"><div class="empty">{irNone()}</div><MailSections model={model} /></div>;
  return <div data-irv="list">
    {grouped ? <><MailSections model={model} />{table([...work, ...tail], "all")}</> : <>
      {table(work, "work")}
      <MailSections model={model} />
      {tailRows}
    </>}
  </div>;
}

/** One meeting's card on the Board. @param {{m: any}} props */
function BoardCard({ m }) {
  return (
    <div class="card iccard click" data-irm={m.id} data-stage={m.stage} data-state={irBusy.value.includes(m.id) ? "running" : m.state} tabindex={0}
      onClick={e => { if (!(/** @type {Element} */ (e.target)).closest("button,a,input")) irClickMeeting(m.id); }}
      onContextMenu={e => irRowMenu(e, m)} onKeyDown={e => irRowKey(e, m)}>
      <div class="t"><IrTick m={m} /> {m.title}</div>
      {m.src === "upload" ? <FileFacts m={m} n={liveN(m)} /> : <>
        <div class="why">{m.p && !m.private && !m.confidential ? pName(m.p) : ""}</div>
        <MatchChip m={m} />
        <IrStateLine m={m} n={liveN(m)} />
      </>}
      {irBusy.value.includes(m.id) ? <Progress words={irRunningWords(m)} /> : null}
      <IrNote m={m} />
      <div class="iccardacts"><RowActions m={m} /></div>
    </div>
  );
}

/** The Board (#340): the open meeting's suggestions first, then the columns Drafted, Approved and Arrived (the work first, Arrived
    last, its waiting meetings folded), then mail and Teams. @param {{model: any}} props */
export function BoardView({ model }) {
  const open = model.meetings.find((/** @type {any} */ m) => m.id === irOpen.value), folded = irTailFolded();
  return <div data-irv="board">
    {open ? <div class="tbl" data-irpart="open"><table><tbody><ProposalGroups groups={open.groups} meet={open.title} child meetId={open.id} /></tbody></table></div> : null}
    <div class="icboard">{IR_BOARD.map(g => {
      const l = model.meetings.filter((/** @type {any} */ m) => m.stage === g), { work, tail } = irSplitTail(l), shown = folded ? work : [...work, ...tail];
      return <div class="iccol" data-ircol={g}>
        <h2>{IR_STAGE_NAMES[/** @type {keyof IR_STAGE_NAMES} */ (g)]} <span class="sub rgc">{l.length}</span></h2>
        {l.length ? <>
          {(g === "arrived" ? shown : l).map((/** @type {any} */ m) => <BoardCard key={m.id} m={m} />)}
          {g === "arrived" && tail.length ? <TailHead n={tail.length} /> : null}
        </> : <div class="empty">Nothing here.</div>}
      </div>;
    })}</div>
    <MailSections model={model} />
  </div>;
}

/** @param {{model: any, list: any[]}} props */
export function TwoPanes({ model, list }) {
  const { work, tail } = irSplitTail(list), folded = irTailFolded(), ordered = [...work, ...tail];
  const sel = ordered.filter(m => !folded || !tail.includes(m)).find(m => m.id === irSel.value) || (folded ? work : ordered)[0], c = irLiveCounts();
  const hidden = (/** @type {any} */ m) => m.private || m.confidential;      /* title and times only */
  const right = (/** @type {any} */ m) => { const n = liveN(m); return n ? `${n} suggestion${n === 1 ? "" : "s"}` : m.stage === "arrived" && m.state === "ready" ? "ready" : ""; };
  const paneRows = (/** @type {any[]} */ rs) => rs.length ? <div class="tbl"><table><tbody>{irGroups(rs).map(g => <>{irGroup.value !== "none" ? <GroupHead g={g} /> : null}{g.items.map((/** @type {any} */ m) => (
    <tr key={m.id} class={`click${sel && sel.id === m.id ? " sel" : ""}`} aria-current={sel && sel.id === m.id ? "true" : undefined} data-irm={m.id} tabindex={0} onClick={e => { if (!(/** @type {Element} */ (e.target)).closest("input")) irSel.value = m.id; }}
      onContextMenu={e => irRowMenu(e, m)} onKeyDown={e => irRowKey(e, m)}>
      <td class="title"><IrTick m={m} /> {m.title}<div class="why">{IR_STAGE_NAMES[/** @type {keyof IR_STAGE_NAMES} */ (m.stage)]} · {irWhen(m)}</div></td>
      <td class="icsub irright">{right(m)}</td>
    </tr>
  ))}</>)}</tbody></table></div> : null;
  return <div data-irv="two">
    <div class="icsplit">
      <div>
        <div class="icpipe icsum"><span class="icsub">Arrived {c.arrived} → Drafted {c.drafted} → Approved {c.approved}</span></div>
        {list.length ? <>{paneRows(work)}{tail.length && irGroup.value === "none" ? <TailHead n={tail.length} /> : null}{folded ? null : paneRows(tail)}</> : <div class="empty">{irNone()}</div>}</div>
      <div class="card icdet" data-irdet={sel ? sel.id : ""}>
        {sel ? <>
          <h2 style={{ margin: "0 0 4px" }}>{sel.title}</h2>
          <div class="why">{irWhen(sel)}{sel.src !== "upload" && sel.p && !hidden(sel) ? ` · ${pName(sel.p)}` : ""}</div>
          <div class="icrack"><StageTrack m={sel} /></div>
          {sel.src === "upload" ? <FileFacts m={sel} n={liveN(sel)} /> : <><MatchChip m={sel} /><IrStateLine m={sel} n={liveN(sel)} /></>}
          {sel.stage === "arrived" && sel.state === "waiting" ? <div class="empty">Waiting for the transcript. It appears here when the meeting’s transcript arrives.</div> : null}
          {irBusy.value.includes(sel.id) ? <Progress words={irRunningWords(sel)} /> : null}
          <IrNote m={sel} />
          <div class="iccardacts"><RowActions m={sel} mini /></div>
          <div class="tbl"><table><tbody><ProposalGroups groups={sel.groups} meet={sel.title} meetId={sel.id} /></tbody></table></div>
        </> : <div class="empty">Select a meeting.</div>}
      </div>
    </div>
    <MailSections model={model} />
  </div>;
}
