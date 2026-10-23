// @ts-check
/* Intake and Review's rows (#232-0 skeleton, v2.5.0). MeetingRow is one meeting (232-A fills its actions: Process, Later, Not needed
   with a reason, progress on the row). The proposal rows live in proposals.jsx (232-B's file). Tokens and the app's own classes only
   (style.css, "#232 Intake and Review"). */
import { pName } from "../../core/data.js";
import { fd, TODAY } from "../../core/page.js";
import { irAskQ, irBlocked, irBusy, irChecking, irClickMeeting, irNotes, irOpen, irStep } from "../../stores/intakeReview.js";
import { IconButton } from "../IconButton.jsx";
import { IrIcon } from "./icons.js";
import { irFixed } from "../../core/irFold.js";
import { irAskAbout, irAskReason, irBadName, irCanCheck, irCanProcess, irCanStop, irStop, irCanSetAside, irChooseKind, irCheck, irFileKind, irLater, irProcess, irProcessWord, irRemoveFile } from "./actions.js";

/** What the sweep found for a waiting meeting's transcript, in words (the model's tx). */
export const IR_TX_WORDS = { none: "No transcript", no_access: "No access", not_transcribed: "Not transcribed" };
export const IR_STATE_WORDS = { ready: "Transcript ready", waiting: "Waiting for the transcript", proposals: "suggestions to check", done: "Done", running: "Drafting in the background" };
export const IR_GROUP_HEAD = {
  needs: ["Needs your decision", "Approved one by one: minutes, new decisions, new risks, closing updates and other bigger changes."],
  routine: ["Routine", "Each has a project and no conflict, and none is a change you approve one by one."],
};
const IR_KIND_WORDS = { actions: "Action", decisions: "Decision", update: "Update", draft: "Minutes", files: "File changes" };
/** The kind pill's word for a Review row. @param {any} r */
export const irKind = r => (r.kind === "raid" ? (r.rec && r.rec.type) || "Risk" : IR_KIND_WORDS[/** @type {keyof IR_KIND_WORDS} */ (r.kind)] || "Suggestion");
const ageWords = (/** @type {number} */ d) => (d === 0 ? "today" : d === 1 ? "1 day" : `${d} days`);

/** A file's size in words (the Intake file list's). @param {number} n bytes */
export const irSize = n => (n > 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round((n || 0) / 1024))} KB`);
/** "Teams transcript · 1 KB": the kind of file in words, never its extension. @param {any} m */
export const irFileFacts = m => { const x = String(m.ext || String(m.title || "").split(".").pop()).toLowerCase(),
    kind = { vtt: "Teams transcript", srt: "Teams transcript", docx: "Word document", doc: "Word document", txt: "Text file", pdf: "PDF" }[x];
  return `${kind ? kind + " · " : ""}${irSize(m.size)}`; };
/** What running a row says: someone else's minutes are read for work items; anything else is drafted. @param {any} m */
export const irRunningWords = m => (irFileKind(m) === "minutes" && m.src === "upload" ? "Reading for work items" : IR_STATE_WORDS.running);

/** A meeting's state in words, for its row and its card. @param {any} m @param {number} n proposals still to check */
export function irStateWords(m, n) {
  const state = irBusy.value.includes(m.id) ? "running" : m.state;
  if (m.src === "upload") {                        /* a file: its facts while it is ready, its own running words, and what became of it */
    if (state === "running") return irRunningWords(m);
    if (state === "ready") return `File ready · ${irFileFacts(m)}`;
    if (state === "done") return m.already ? "Already processed" : IR_STATE_WORDS.done;
  }
  const tx = state === "waiting" && IR_TX_WORDS[/** @type {keyof IR_TX_WORDS} */ (m.tx)] ? ` · ${IR_TX_WORDS[/** @type {keyof IR_TX_WORDS} */ (m.tx)]}` : "";
  const base = state === "proposals" ? (n === 1 ? "1 suggestion to check" : `${n} ${IR_STATE_WORDS.proposals}`) : `${IR_STATE_WORDS[/** @type {keyof IR_STATE_WORDS} */ (state)] || ""}${tx}`;
  const age = state === "ready" || state === "proposals" ? ` · ${ageWords(m.age)}` : "";
  return `${base}${age}${m.later_back ? " · back from Later" : ""}`;
}

/** The progress bar a meeting shows while it is drafted in the background. */
export function Progress({ words }) {
  return <>
    <div class="icprog" role="progressbar" aria-label={words || "Drafting in the background"}><i></i></div>
    {irStep.value ? <div class="why" data-irstep="1">{irStep.value}</div> : null}
  </>;
}

/** A row's note after a Process that drafted nothing; when the run asked a question (#264: "Needs you", or not staged), the note
    offers "ask creaite about this", which opens the panel with the question filled in. The same in List, Board and Two panes.
    @param {{m: any}} props */
export function IrNote({ m }) {
  const note = irNotes.value[m.id];
  if (!note) return null;
  return <div class="why irnote" role="status">{note}{irAskQ.value[m.id] ? <>{" "}<button type="button" class="linkbtn" data-ira="askabout" onClick={() => irAskAbout(m)}>ask creaite about this</button></> : null}</div>;
}

/** "Added today" or "Added 14-10-2026". @param {any} m */
export const irAdded = m => (!m.day || m.day === TODAY ? "Added today" : `Added ${fd(m.day)}`);

/** When a row's meeting was, or when its file was added: "14-10-2026 15:00" or "Added today". @param {any} m */
export const irWhen = m => (m.src === "upload" ? irAdded(m) : `${m.day ? fd(m.day) : ""}${m.start ? ` ${m.start}` : ""}`.trim());

/** Where a row is on its way: Arrived, Drafted, Approved, with a dot for each (done, now, to come). Two panes' detail. @param {{m: any}} props */
export function StageTrack({ m }) {
  const names = ["Arrived", "Drafted", "Approved"], at = ["arrived", "drafted", "approved"].indexOf(m.stage);
  return (
    <span class="ictrack" aria-label={`Step: ${names[at] || ""}`} data-irtrack={m.stage}>
      {names.map((n, k) => <><i class={k < at ? "done" : k === at ? "now" : ""}></i><span class={k === at ? "on" : ""}>{n}</span></>)}
    </span>
  );
}

/** A file's kind in words, with the link that switches it (a transcript is turned into minutes first; someone else's minutes are only
    read for work items); a file that is not sure asks. Shown while the file waits. @param {{m: any}} props */
export function FileKind({ m }) {
  const k = irFileKind(m);
  if (irBadName(m)) return <div class="why irkind" data-irkind="name"><span class="tag warn">Name not allowed</span> · Rename this file to process it.</div>;
  if (!k) return <div class="why irkind" data-irkind="unsure"><span class="tag warn">Not sure</span> · Is this a transcript or minutes?</div>;
  return (
    <div class="why irkind" data-irkind={k}>
      <span class="tag">{k === "transcript" ? "Transcript" : "Minutes"}</span> · {k === "transcript"
        ? "It will be turned into minutes, then checked for work items."
        : "Written by someone else: it will be checked for work items, and no new minutes are drafted."}{" "}
      {irFixed(m) ? null : <button type="button" class="linkbtn" data-ira="ftype" onClick={() => irChooseKind(m, k === "transcript" ? "minutes" : "transcript")}>{k === "transcript" ? "It is minutes" : "It is a transcript"}</button>}
    </div>
  );
}

/** An uploaded file's lines, the same in the List, the Board's card and the Two panes' detail: when it was added and its likely
    project, its state, and what kind it is while it waits. @param {{m: any, n: number}} props */
export function FileFacts({ m, n }) {
  const waiting = m.stage === "arrived" && m.state === "ready" && !irBusy.value.includes(m.id);
  return <>
    <div class="why">{irAdded(m)} · Likely project: {m.p ? pName(m.p) : "Not sure"}</div>
    <div class="why">{irStateWords(m, n)}</div>
    {waiting ? <FileKind m={m} /> : null}
  </>;
}

/** The Later button's tooltip: a waiting meeting comes back by itself; a ready one or a file stays until it is restored. @param {any} m */
export const laterWords = m => (m.state === "waiting" ? "Hide it until its transcript arrives" : "Hide it; it stays in Later until you restore it");

/** The row's actions: Process, Later and Not needed (with a reason) while it is arrived; Check them while it has proposals.
    @param {{m: any, mini?: boolean}} props */
export function RowActions({ m, mini }) {
  const running = irBusy.value.includes(m.id), blocked = irBlocked(), checking = irChecking.value.includes(m.id);
  const open = irOpen.value === m.id;
  if (running) return <><button type="button" class="mini" disabled data-ira="processing">Processing</button>{irCanStop(m) ? <>{" "}<button type="button" class="mini" data-ira="stop" title="Stop processing" onClick={() => irStop()}>Stop</button></> : null}</>;
  if (m.stage === "drafted") return mini ? null : <button type="button" class="mini" data-ira="open" onClick={() => irClickMeeting(m.id)}>{open ? "Close" : "Check them"}</button>;
  if (!irCanSetAside(m)) return m.stage === "approved" ? <><span class="icsub">Done</span>{m.already ? <>{" "}<button type="button" class="mini" data-ira="removefile" title="Take it out of Intake (kept in backups)" onClick={() => irRemoveFile(m)}>Remove</button></> : null}</> : null;
  const unsure = m.src === "upload" && !irFileKind(m), badName = irBadName(m);
  return <>
    {badName ? <button type="button" class="mini" data-ira="process" disabled title="Rename this file to process it">{irProcessWord(m)}</button> : unsure ? <>
      <button type="button" class="mini" data-ira="ft" data-t="transcript" title="It is a transcript: it will be turned into minutes" onClick={() => irChooseKind(m, "transcript")}>Transcript</button>{" "}
      <button type="button" class="mini" data-ira="ft" data-t="minutes" title="It is minutes: it will be checked for work items" onClick={() => irChooseKind(m, "minutes")}>Minutes</button>
    </> : irCanProcess(m) ? <button type="button" class="mini" data-ira="process" disabled={blocked} title={blocked ? "ask creaite is busy; try again when it's finished" : ""}
      onClick={() => irProcess(m)}>{irProcessWord(m)}</button> : null}
    {" "}<button type="button" class="mini" data-ira="later" title={laterWords(m)} onClick={() => irLater(m)}>Later</button>
    {irCanCheck(m) || checking ? <>{" "}<button type="button" class="mini" data-ira="check" disabled={checking || blocked} title={checking ? "" : blocked ? "ask creaite is busy; try again when it's finished" : "Look the transcript up again"}
      onClick={() => irCheck(m)}>{checking ? "Checking…" : "Check again"}</button></> : null}
    {" "}<IconButton icon="x" label="Not needed, with a reason" cls="no" data={{ ira: "notneeded" }} haspopup="menu"
      onClick={e => irAskReason(m, /** @type {HTMLElement} */ (e.currentTarget))} />
  </>;
}

/** @param {{m: any, live: {needs: number[], routine: number[]}}} props */
export function MeetingRow({ m, live }) {
  const open = irOpen.value === m.id, n = live.needs.length + live.routine.length;
  const state = irBusy.value.includes(m.id) ? "running" : m.state;
  const can = m.stage === "drafted";
  return (
    <tr class={`click irmeet${open ? " icopen" : ""}`} data-irm={m.id} data-stage={m.stage} data-state={state} tabindex={0}
      aria-expanded={can ? open : undefined}
      onClick={e => { if (!(/** @type {Element} */ (e.target)).closest("button,a,input")) irClickMeeting(m.id); }}>
      <td class="title">
        <span class="ki" aria-hidden="true" data-irki={m.src === "upload" ? "file" : "meeting"}><IrIcon name={m.src === "upload" ? "file" : "meeting"} /></span>
        <b class="icmeethd">{m.title}</b>
        {m.stale ? <> <span class="tag stale">Stale · {ageWords(m.age)}</span></> : null}
        {m.src === "upload" ? <FileFacts m={m} n={n} /> : <>
          <div class="why">{m.day ? fd(m.day) : ""}{m.start ? ` ${m.start}${m.end ? `–${m.end}` : ""}` : ""}{m.p && !m.private && !m.confidential ? ` · ${pName(m.p)}` : ""}</div>
          <div class="why">{irStateWords(m, n)}</div>
        </>}
        {state === "running" ? <><div class="why">ask creaite waits until this ends</div><Progress words={irRunningWords(m)} /></> : null}
        <IrNote m={m} />
      </td>
      <td class="iracts"><RowActions m={m} /></td>
    </tr>
  );
}
