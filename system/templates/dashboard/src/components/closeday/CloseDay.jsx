// @ts-check
/* CloseDay (BL-295, dev/COMPONENTS.md): Close the day as a guided shutdown, replacing BL-206's one card (FR-164). Four short steps,
   the same every evening, then a clear end (dev/mockups/close-the-day-mockup.html, option B):
     1 Catch up   the catch-up sweep starts as the card opens when the last sweep is older than day.catchup_after_minutes
                  (/api/day/catchup), with Stop and Skip, and runs on while Alan reads steps 2 and 3; it only stages proposals;
     2 Today      what moved and what he promised, each promise one click from his commitments (as BL-206);
     3 Loose ends everything still open (the sweep's new items first, overdue items too) gets a place: Review now (opens Review,
                  Work or Intake after closing; nothing is staged), First thing tomorrow (heads tomorrow's Today and the
                  session-start line) or Leave;
     4 Tomorrow   the next working day's meetings (and any planned weekend work before it); Make prep page queues one to run after closing.
   Back and Next by button or ← →; Esc is "Not yet" and keeps the step. Steps with nothing in them are passed over. Nothing here
   approves, rejects or applies anything; the server keeps references only (dev/sprints/BL-295-server.md). Text only through JSX.
   The Close the day door (BL-270) and ⌘K open it through openCloseDay(); its state lives here while the page is open. */
import { render } from "preact";
import { useEffect, useRef, useState } from "preact/hooks";
import { signal } from "@preact/signals";
import { Dialog } from "../Dialog.jsx";
import { REV, A, R, DEC, pName } from "../../core/data.js";
import { D, TODAY, fd } from "../../core/page.js";
import { api, viaServer, snack, oneLine, reloadData } from "../../core/server.js";
import { go, openWork } from "../../core/nav.js";
import { DC, longDay, plur } from "../../today.js";
import { decide } from "../../review.js";
import { HL, hlPaint } from "../../work.js";
import { irReveal } from "../../stores/intakeReview.js";
import { dcIcon } from "../../ask.js";

/** @typedef {{ref: string, kind: string, type: string, t: string, p?: string|null, project?: string|null, new?: boolean,
    place?: string, due?: string}} LooseEnd */
/** @typedef {{start: string, end: string, title: string, confidential: boolean, key?: string|null, page?: string|null,
    plan?: boolean, make: boolean, p?: string|null, project?: string|null}} TomorrowMeeting */
/** @typedef {{day: string, day_shown: string, long?: string|null, in_calendar: boolean, friday: boolean,
    meetings: TomorrowMeeting[], weekend?: {day: string, day_shown: string, long?: string|null, meetings: TomorrowMeeting[],
    due: {type: string, t: string, project?: string|null}[]}[]}} Tomorrow */
/** @typedef {{state: string|null, run?: {id: string}|null, started?: string|null, ended?: string|null}} CatchupPublic */
/** @typedef {{key: string, state: string, run?: string|null, path?: string|null, message?: string|null}} PrepItem */
/** @typedef {{ok: boolean, message?: string, now: string, last_sweep?: string, day: any, catchup: CatchupPublic,
    loose: LooseEnd[], tomorrow: Tomorrow, prep: {items: PrepItem[], running: boolean}}} Card */
/** @typedef {{status: string, message: string, state: string|null, run: string|null, label: string, reached: number, ended?: string|null,
    found: {ref: string, type: string, t: string, p?: string|null, project?: string|null}[]}} Catchup */
/** @typedef {{at: string, counts: {review: number, first: number, left: number, prep: number},
    open: {review: {file: string, ref: number|string}[], work: string[], intake: boolean}}} Closed */

export const CD_STEPS = ["Catch up", "Today", "Loose ends", "Tomorrow"];
const PLACES = [["review", "Review now"], ["first", "First thing tomorrow"], ["leave", "Leave"]];
const SOURCES = ["Mail", "Teams chats", "Teams channels", "Matching to projects"];
const READING = ["Reading mail", "Reading Teams chats", "Reading Teams channels", "Matching to projects"];
const SHOWN = 8;                       // Loose ends: the first eight, then "and n more"
const POLL = 1500;                     // ms between status reads while the catch-up runs or waits

/** Close the day's open state: the door, ⌘K and the tests set it. */
export const cdOpen = signal(false);
let host = /** @type {HTMLElement | null} */ (null);

/** Open Close the day (mounting the card the first time). */
export function openCloseDay() {
  if (!host) {
    host = document.createElement("div");
    host.id = "closeDayHost";
    document.body.appendChild(host);
    render(<CloseDay />, host);
  }
  cdOpen.value = true;
}

/** Which of SOURCES a run's step line is reading (its index), or -1 for another step. Labels are the server's describe_tool,
    or (BL-326: the catch-up is a run creaite started) its plain_step words.
    @param {string} label */
export function cdSourceOf(label) {
  const l = String(label || "").toLowerCase();
  if (/calendar|read resource|a meeting, a message or a chat/.test(l)) return -1;
  if (/channel/.test(l)) return 2;
  if (/teams|chat message|list chats/.test(l)) return 1;
  if (/email|outlook|mail/.test(l)) return 0;
  if (/sweep\.py stage|people map|propose\.py|staging what the sweep found|mapping names/.test(l)) return 3;
  return -1;
}

/** The ← → keys move only when focus isn't in a field. @param {EventTarget | null} t */
const cdTyping = t => t instanceof HTMLElement && !!t.closest("input,textarea,select,[contenteditable]");

/** A tick, as element data (COMPONENTS.md Q2). */
function Tick() {
  return (
    <svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"
      stroke-linejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5" /></svg>
  );
}

/** Step 1: the catch-up sweep. @param {{cu: Catchup, last: string, onStop: () => void, onSkip: () => void,
    onAgain: () => void}} props */
function CatchUp({ cu, last, onStop, onSkip, onAgain }) {
  const st = cu.state, running = st === "running", waiting = st === "waiting" || cu.status === "busy" && !st;
  if (running || waiting) {
    return (
      <div class="cdsweep" aria-busy="true">
        <div class="row"><span class="spin" aria-hidden="true"></span>
          <div class="grow"><b>{waiting ? "Waiting to catch up" : "Catching up…"}</b>{" "}
            <span class="sub">{waiting ? cu.message : cu.label || "Reading mail and Teams since the last sweep"}</span></div>
          {running ? <button type="button" class="mini" data-cdstop="1" onClick={onStop}>Stop</button> : null}
          <button type="button" class="mini" data-cdskip="1" onClick={onSkip}>Skip</button>
        </div>
        {running ? <ol class="cdsrc" aria-label="Sources">{SOURCES.map((s, i) =>
          <li class={i < cu.reached ? "done" : i === cu.reached ? "now" : ""}>{s}</li>)}</ol> : null}
        <p class="sub">It runs while you read on. It only proposes items for Review; nothing is applied, and nothing changes in
          Microsoft 365.</p>
      </div>
    );
  }
  if (st === "done") {
    return (
      <div class="cdsweep">
        <div class="row"><span class="cdok" aria-hidden="true"><Tick /></span>
          <div class="grow"><b>{`Caught up at ${cu.ended || last}.`}</b>{" "}
            <span class="sub">{cu.found.length ? `${plur(cu.found.length, "new item")} for Review; you'll give each a place in Loose ends.`
              : "Nothing new was found."}</span></div>
        </div>
        {cu.found.length ? <ul class="cdfound">{cu.found.slice(0, 5).map(f =>
          <li><span class="tag new">{f.type}</span><span class="grow">{f.t}</span>{f.project ? <span class="sub">{f.project}</span> : null}</li>)}
          {cu.found.length > 5 ? <li class="sub">and {cu.found.length - 5} more</li> : null}</ul> : null}
      </div>
    );
  }
  const words = st === "stopped" ? "Stopped. What it had read so far is in Review; the next sweep does the rest."
    : st === "skipped" ? "Skipped. The next sweep picks up anything new."
    : st === "failed" || st === "gave_up" ? "The catch-up sweep didn't run. The next sweep picks up anything new."
    : cu.message;
  const offer = cu.status === "offer" || st === "stopped" || st === "skipped" || st === "failed" || st === "gave_up";
  const again = cu.status === "recent";
  return (
    <div class="cdsweep">
      <div class="row"><div class="grow">{cu.status === "offer" ? <b>Catch up before you close?</b> : null}{" "}
        <span class={cu.status === "offer" ? "sub" : ""}>{words}</span></div>
        {offer ? <button type="button" class={cu.status === "offer" ? "btn primary" : "mini"} data-cdsweep="1" onClick={onAgain}>Sweep now</button> : null}
        {again ? <button type="button" class="mini" data-cdsweep="1" onClick={onAgain}>Sweep again</button> : null}
      </div>
    </div>
  );
}

/** Step 2: what moved and what Alan promised. @param {{day: any, onAdd: (i: number) => void}} props */
function Today({ day, onAdd }) {
  const m = day.moved || {}, prom = day.promised || [];
  const mov = [m.closed ? plur(m.closed, "action") + " closed" : "", m.decisions ? plur(m.decisions, "decision") + " recorded" : "",
    m.applied ? plur(m.applied, "item") + " changed" : ""].filter(Boolean);
  return (
    <>
      <section><h4>Moved today</h4><p>{mov.length ? mov.join(" · ") : "Nothing was applied today."}</p></section>
      <section><h4>You promised today</h4>
        {prom.length ? <><ul class="dclist">{prom.map((x, i) => {
          const r = REV.find(q => q.file === x.file && q.ref === x.n);
          return <li><span class="grow">{x.t || ""} <span class="sub">{pName(x.p) || ""}{x.due ? ` · due ${fd(x.due)}` : ""}</span></span>
            {r && !r.done ? <button type="button" class="mini" data-dcadd={i} onClick={() => onAdd(i)}>Add it to your commitments</button>
              : r && r.done ? <span class="tag">Added</span> : null}</li>;
        })}</ul>
          <p class="sub">Proposed today, owned by you, still waiting in Review. Adding approves it there; it reaches the tracker at the next apply.</p></>
          : <p class="sub">Nothing from today is waiting with your name on it.</p>}
      </section>
    </>
  );
}

/** One loose end's place: three buttons, one pressed. @param {{label: string, value: string, onPick: (v: string) => void}} props */
function Place({ label, value, onPick }) {
  return (
    <div class="cdchoice" role="group" aria-label={label}>
      {PLACES.map(([v, l]) => <button type="button" aria-pressed={value === v ? "true" : "false"} data-place={v}
        onClick={() => onPick(v)}>{l}</button>)}
    </div>
  );
}

/** A loose end's words: its type, what it is, its project and, for an item, its date. @param {{x: LooseEnd}} props */
function LooseWords({ x }) {
  return (
    <span class="grow"><span class={x.new ? "tag new" : "tag"}>{x.type}</span>{" "}{String(x.t || "").replace(/^Minutes: /, "")}
      {x.new ? <>{" "}<span class="tag new">New</span></> : null}
      {x.project ? <span class="sub"> · {x.project}</span> : null}
      {x.due && /overdue/.test(x.type) ? <span class="sub"> · due {fd(x.due)}</span> : null}</span>
  );
}

/** Step 3: every loose end gets a place. @param {{loose: LooseEnd[], places: Record<string, string>, all: boolean,
    onPick: (ref: string, v: string) => void, onAll: (v: string) => void, onMore: () => void, sweeping: boolean}} props */
function LooseEnds({ loose, places, all, onPick, onAll, onMore, sweeping }) {
  if (!loose.length) return <p class="sub">{sweeping ? "Nothing is open yet; anything the sweep finds is added here." : "Nothing is left open. Everything has a place."}</p>;
  const shown = all ? loose : loose.slice(0, SHOWN), common = loose.every(x => places[x.ref] === places[loose[0].ref]) ? places[loose[0].ref] : "";
  return (
    <>
      <section><h4>Give each a place</h4>
        <div class="cdall"><span class="sub">{loose.length > 1 ? `All ${loose.length}:` : "It:"}</span>
          <Place label={`Place for all ${plur(loose.length, "loose end")}`} value={common} onPick={onAll} /></div>
        <ul class="dclist cdloose">{shown.map(x => <li data-ref={x.ref}><LooseWords x={x} />
          <Place label={`Place for ${x.type}: ${x.t}`} value={places[x.ref]} onPick={v => onPick(x.ref, v)} /></li>)}</ul>
        {loose.length > shown.length ? <button type="button" class="linkbtn" data-cdmore="1" onClick={onMore}>and {loose.length - shown.length} more</button> : null}
      </section>
      <p class="sub">Nothing is approved here. Review now opens Intake (or Work) after you close; First thing tomorrow puts
        it at the top of tomorrow's Today.{sweeping ? " The sweep's finds are added as it ends." : ""}</p>
    </>
  );
}

/** Step 4: the next working day. @param {{tm: Tomorrow, prep: Set<string>, made: Record<string, PrepItem>,
    onPrep: (key: string) => void, first: LooseEnd[], weekly: string[], friday: boolean}} props */
function TomorrowStep({ tm, prep, made, onPrep, first, weekly, friday }) {
  const nextDay = tm.day && tm.day !== addDays(TODAY, 1);
  return (
    <>
      <section><h4>{tm.long || (tm.day ? longDay(tm.day) : "Tomorrow")}{nextDay ? " (the next working day)" : ""}</h4>
        {tm.meetings.length ? <ul class="dclist">{tm.meetings.map(m => {
          const q = m.key ? made[m.key] : null, on = !!m.key && prep.has(m.key);
          return <li><span class="grow">{m.start} {m.title}{m.project ? <span class="sub"> · {m.project}</span> : null}</span>
            {m.page || q && q.state === "made" ? <span class="tag ok">Prep page made</span>
              : q && (q.state === "running" || q.state === "queued") ? <span class="tag">Prep page being made</span>
              : m.make ? <button type="button" class="mini" aria-pressed={on ? "true" : "false"} data-cdprep={m.key}
                onClick={() => onPrep(m.key)}>{on ? "Prep page queued" : "Make prep page"}</button> : null}</li>;
        })}</ul> : <p class="sub">{tm.in_calendar === false ? "That day isn't in the saved calendar yet." : "No meetings."}</p>}
        {prep.size ? <p class="sub">{plur(prep.size, "prep page")} will be made after you close, one at a time.</p> : null}
      </section>
      {(tm.weekend || []).map(w => <section data-cdweekend={w.day}><h4>{w.long || longDay(w.day)} (planned for the weekend)</h4>
        <ul class="dclist">{w.meetings.map(m => <li><span class="grow">{m.start} {m.title}{m.project ? <span class="sub"> · {m.project}</span> : null}</span></li>)}
          {w.due.map(x => <li><span class="grow">{x.type} due: {x.t}{x.project ? <span class="sub"> · {x.project}</span> : null}</span></li>)}</ul>
      </section>)}
      {friday ? <section><h4>Friday</h4><p>{weekly.length ? weekly.join(" · ") : <span class="sub">No weekly report is due.</span>}</p></section> : null}
      <section><h4>First thing tomorrow</h4>
        {first.length ? <p>{first.slice(0, 5).map(x => x.t || x.type).join(" · ")}{first.length > 5 ? ` · and ${first.length - 5} more` : ""}</p>
          : <p class="sub">Nothing; tomorrow's Today starts clean.</p>}
      </section>
    </>
  );
}

/** The date `n` days after an ISO date. @param {string} iso @param {number} n */
function addDays(iso, n) {
  const d = new Date(iso + "T12:00:00");
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}

/** After closing: open what Alan chose to Review now. Proposals in Review (highlighted), items in Work, files and transcripts in
    Intake; nothing is staged (Alan, 13-10-2026). @param {Closed["open"]} open */
export function cdOpenPlaces(open) {
  const rv = open.review || [], wk = open.work || [];
  const later = [wk.length ? plur(wk.length, "item") + " in Work" : "", open.intake ? "Intake" : ""].filter(Boolean);
  if (rv.length) {
    go("intake-review");
    /* #232-C: the meeting the first of them came from opens on the one page */
    irReveal(rv.map(x => { const r = REV.find(y => y.file === x.file && y.ref === x.ref && !y.done); return r ? r.n : -1; }).filter(n => n >= 0));
    if (later.length) snack(`Also for Review now: ${later.join(" and ")}`, () => cdOpenPlaces({ review: [], work: wk, intake: open.intake }), "Open");
    return;
  }
  if (wk.length) {
    const kindOf = /** @param {string} id */ id => A.some(x => x.id === id) ? "actions" : R.some(x => x.id === id) ? "raid" : DEC.some(x => x.id === id) ? "decisions" : "";
    const k = kindOf(wk[0]) || "actions", mine = wk.filter(id => kindOf(id) === k);
    const codes = [...new Set(mine.map(id => { const x = [...A, ...R, ...DEC].find(y => y.id === id); return x && x.p; }).filter(Boolean))];
    openWork(codes.length === 1 ? codes[0] : "", k, "open", codes.length > 1 ? { p: codes } : null);
    HL.clear();
    mine.forEach(id => HL.set(id, k));
    hlPaint();
    const first = document.querySelector("#workTbl tr.hl");
    if (first) first.scrollIntoView({ block: "center" });
    if (open.intake) snack("Also for Review now: Intake", () => go("intake-review", { stage: "arrived" }), "Open");
    return;
  }
  if (open.intake) go("intake-review", { stage: "arrived" });
}

/** The whole card. Mounted once, by openCloseDay; it keeps its step and choices while the page is open. */
export function CloseDay() {
  const open = cdOpen.value;
  const [card, setCard] = useState(/** @type {Card | null} */ (null));
  const [err, setErr] = useState("");
  const [step, setStep] = useState(0);
  const [places, setPlaces] = useState(/** @type {Record<string, string>} */ ({}));
  const [all, setAll] = useState(false);
  const [prep, setPrep] = useState(/** @type {Set<string>} */ (new Set()));
  const [cu, setCu] = useState(/** @type {Catchup} */ ({ status: "", message: "", state: null, run: null, label: "", reached: 0, found: [] }));
  const [closed, setClosed] = useState(/** @type {Closed | null} */ (null));
  const [pending, setPending] = useState(false);
  const [busy, setBusy] = useState(false);
  const [said, setSaid] = useState("");
  const attached = useRef(""), ctl = useRef(/** @type {AbortController | null} */ (null)), seen = useRef(0);

  const loadCard = async () => {
    const c = await api("/api/day/card", {});
    if (!c.ok) { setErr(oneLine(c.message) || "Close the day couldn't read the day."); return null; }
    setErr(""); setCard(c);
    setPlaces(p => { const n = { ...p }; for (const x of c.loose) if (!n[x.ref]) n[x.ref] = x.place || "first"; return n; });
    return c;
  };

  /** Follow a running catch-up's steps (which source it is reading). @param {string} id */
  const attach = async id => {
    if (!id || attached.current === id) return;
    attached.current = id;
    const c = new AbortController(); ctl.current = c;
    let res;
    try {
      res = await fetch("/api/ask/attach", { method: "POST", signal: c.signal, headers: { "Content-Type": "application/json", "X-Creaite-Token": D.token || "" },
        body: JSON.stringify({ run: id }) });
    } catch (e) { return; }
    if (!res.ok || !res.body) return;
    const rd = res.body.getReader(), dec = new TextDecoder();
    let buf = "";
    for (;;) {
      let ch;
      try { ch = await rd.read(); } catch (e) { break; }
      if (ch.done) break;
      buf += dec.decode(ch.value, { stream: true });
      for (let i = buf.indexOf("\n\n"); i >= 0; i = buf.indexOf("\n\n")) {
        const part = buf.slice(0, i); buf = buf.slice(i + 2);
        if (!part.startsWith("data: ")) continue;
        let ev; try { ev = JSON.parse(part.slice(6)); } catch (e) { continue; }
        if (ev.type === "step") {
          const s = cdSourceOf(ev.label);
          if (s >= 0) setCu(u => ({ ...u, reached: Math.max(u.reached, s), label: READING[Math.max(u.reached, s)] }));
        }
      }
    }
  };

  /** Read the catch-up's state; when it has ended, list what it found and read the card again so Loose ends include it. */
  const status = async () => {
    const s = await api("/api/day/catchup/status", {});
    if (!s.ok) return;
    const run = s.run && s.run.id || null;
    setCu(u => ({ ...u, state: s.state, run, ended: s.ended, found: s.found || [] }));
    if (s.state === "running" && run) attach(run);
    if (s.state && !["running", "waiting"].includes(s.state)) { await loadCard(); reloadData(); }   // its finds reach Review's list
    return s.state;
  };

  /** Ask the server to start (or follow) the catch-up. @param {boolean} force Sweep now / Sweep again */
  const catchup = async force => {
    const r = await api("/api/day/catchup", force ? { force: true } : {});
    if (!r.ok) { setCu(u => ({ ...u, status: "cant", message: oneLine(r.message) || "The catch-up sweep couldn't start." })); return; }
    const pub = r.catchup || {}, run = r.run && r.run.id || pub.run && pub.run.id || null;
    setCu(u => ({ ...u, status: r.status, message: r.message || "", state: pub.state || null, run, ended: pub.ended, reached: force ? 0 : u.reached,
      label: force ? "" : u.label, found: force ? [] : u.found }));
    if (run && (pub.state === "running" || r.status === "start")) attach(run);
    else if (pub.state === "done") status();                               // ended earlier today: what it found
  };

  // On opening: the card, then the catch-up (which starts, follows the one going, or says why not).
  useEffect(() => {
    if (!open) return;
    if (closed && !pending) return;                                        // the end line stays until Look at the day again
    if (!viaServer()) { setErr("Close the day needs the live server: start it, then try again."); return; }
    if (pending) { status(); return; }                                     // closing when the sweep finishes: follow it
    (async () => { const c = await loadCard(); if (c && !closed) await catchup(false); })();
  }, [open]);

  // While it runs or waits, read its state every so often: while the card is open, or hidden with a close waiting for the sweep
  // (so the day closes, and the door says so, even when Alan has walked away).
  const live = cu.state === "running" || cu.state === "waiting";
  useEffect(() => {
    if (!(open || pending) || !live) return undefined;
    const t = setInterval(status, POLL);
    return () => clearInterval(t);
  }, [open, pending, live]);

  // A close that waited for the sweep: once the sweep has ended, the day is closed; read it back.
  useEffect(() => {
    if (!pending || live) return;
    (async () => {
      for (let i = 0; i < 40; i++) {
        const day = await api("/api/day/card", {});
        if (day.ok && day.day && day.day.closed) {
          const plan = buildPlan();
          D.day = Object.assign(DC(), { closed: day.day.closed });
          dcIcon();
          setClosed({ at: day.day.closed, counts: { review: plan.review, first: plan.first + cu.found.filter(f => !places[f.ref]).length,
            left: plan.left, prep: prep.size }, open: plan.open });
          setPending(false);
          return;
        }
        await new Promise(r => setTimeout(r, 500));
      }
      setPending(false); setErr("The day hasn't closed yet; try Close the day again.");
    })();
  }, [pending, live]);

  useEffect(() => () => { if (ctl.current) ctl.current.abort(); }, []);

  const day = (card && card.day) || DC(), loose = (card && card.loose) || [];
  const tm = (card && card.tomorrow) || { day: "", day_shown: "", in_calendar: false, friday: false, meetings: [] };
  const made = Object.fromEntries(((card && card.prep && card.prep.items) || []).map(i => [i.key, i]));
  const weekly = day.friday ? (D.reminders || []).filter(r => /weekly report/i.test(r.text || r.t || r.msg || "")).map(r => r.text || r.t || r.msg || "") : [];
  const sweeping = live;
  const hasToday = !!((day.moved && (day.moved.closed || day.moved.decisions || day.moved.applied)) || (day.promised || []).length);
  /** Whether a step has anything in it (a quiet day passes over the empty ones; Tomorrow always shows, it closes the day). */
  const full = [cu.status !== "off" && cu.status !== "cant" || !!cu.state, hasToday, loose.length > 0 || sweeping, true];
  const firstList = loose.filter(x => (places[x.ref] || "first") === "first");

  /** @param {number} d direction */
  const move = d => { let s = step + d; while (s > 0 && s < 3 && !full[s]) s += d; setStep(Math.max(0, Math.min(3, s))); };
  useEffect(() => { if (open && !closed && step === 0 && !full[0] && card) move(1); }, [card, cu.status]);   // a quiet day
  useEffect(() => { if (open) setSaid(`Step ${step + 1} of 4, ${CD_STEPS[step]}`); }, [step, open]);

  const buildPlan = () => {
    const choices = Object.fromEntries(loose.map(x => [x.ref, places[x.ref] || "first"]));
    const vals = Object.values(choices);
    const rv = loose.filter(x => choices[x.ref] === "review");
    return { choices, review: vals.filter(v => v === "review").length, first: vals.filter(v => v === "first").length,
      left: vals.filter(v => v === "leave").length,
      open: { review: rv.filter(x => x.ref.startsWith("p:")).map(x => { const [f, n] = x.ref.slice(2).split("#"); return { file: f, ref: /^\d+$/.test(n) ? +n : n }; }),
        work: rv.filter(x => x.ref.startsWith("i:")).map(x => x.ref.slice(2)), intake: rv.some(x => /^[tf]:/.test(x.ref)) } };
  };

  const close = async () => {
    if (busy) return;
    if (!viaServer()) { snack("Closing the day needs the live server"); return; }
    setBusy(true);
    const plan = buildPlan();
    const r = await api("/api/day/close", { choices: plan.choices, prep: [...prep] });
    setBusy(false);
    if (!r.ok) { snack(oneLine(r.message) || "Not closed"); return; }
    if (r.pending) { setPending(true); return; }
    D.day = Object.assign(DC(), { closed: r.at });
    dcIcon();
    setClosed({ at: r.at, counts: r.counts, open: r.open });
  };

  const again = () => { setClosed(null); setStep(0); setAll(false); loadCard(); };
  const notYet = () => { cdOpen.value = false; };
  const finish = () => { const o = closed && closed.open; cdOpen.value = false; if (o) cdOpenPlaces(o); };
  /** @param {KeyboardEvent} e */
  const keys = e => {
    if (closed || pending || cdTyping(e.target) || e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.key === "ArrowRight" && step < 3) { e.preventDefault(); move(1); }
    if (e.key === "ArrowLeft" && step > 0) { e.preventDefault(); move(-1); }
  };

  const n = closed && closed.counts, toReview = closed ? closed.open.review.length + closed.open.work.length + (closed.open.intake ? 1 : 0) : 0;
  const end = n ? [n.review ? `${n.review} for Review now` : "", n.first ? `${n.first} first thing tomorrow` : "",
    n.prep ? `${plur(n.prep, "prep page")} being made` : ""].filter(Boolean) : [];
  return (
    <Dialog open={open} onClose={notYet} labelledBy="dcH" id="closeDlg" class="dcdlg cdcard" focus={closed ? "[data-cdfinish]" : "[data-cdnext]"}>
      <div onKeyDown={keys}>
        <header class="cdhead"><h2 id="dcH">Close the day</h2><span class="sub">{longDay(day.today || TODAY)} · about three minutes</span></header>
        <div class="vh" role="status" aria-live="polite">{closed ? `Day closed at ${closed.at}` : pending ? "Closing when the sweep finishes" : said}</div>
        {closed ? (
          <div class="cddone">
            <div class="cdseal" aria-hidden="true"><Tick /></div>
            <h3>Day closed at {closed.at}</h3>
            <p>Everything has a place{end.length ? `: ${end.join(", ")}` : ""}.</p>
            <div class="cdacts"><button type="button" class="btn" data-cdagain="1" onClick={again}>Look at the day again</button>
              <button type="button" class="btn primary" data-cdfinish="1" onClick={finish}>{toReview ? "Review now" : "Done"}</button></div>
          </div>
        ) : pending ? (
          <div class="cddone"><span class="spin" aria-hidden="true"></span><h3>Closing when the sweep finishes</h3>
            <p class="sub">You can walk away: what it finds and you haven't placed goes to First thing tomorrow.</p>
            <div class="cdacts"><button type="button" class="btn" onClick={notYet}>Hide</button></div></div>
        ) : (
          <>
            <ol class="cdsteps" aria-label="Steps">{CD_STEPS.map((s, i) =>
              <li class={i < step ? "done" : i === step ? "now" : ""} aria-current={i === step ? "step" : undefined}>{s}</li>)}</ol>
            <section class="cdbody" role="group" aria-label={`Step ${step + 1} of 4, ${CD_STEPS[step]}`}>
              {err ? <p class="cderr" role="alert">{err}</p> : null}
              {step === 0 ? (full[0] ? <CatchUp cu={cu} last={(card && card.now) || ""} onStop={() => cu.run && api("/api/ask/stop", { run: cu.run }).then(status)}
                onSkip={() => api("/api/day/catchup/skip", {}).then(r => setCu(u => ({ ...u, state: (r && r.state) || "skipped" })))}
                onAgain={() => catchup(true)} /> : <p class="sub">{cu.message || "No catch-up sweep tonight."}</p>) : null}
              {step === 1 ? <Today day={day} onAdd={async i => { const x = (day.promised || [])[i], r = x && REV.find(q => q.file === x.file && q.ref === x.n);
                if (r) { await decide(r.n, "approved"); setCard(c => c && { ...c }); } }} /> : null}
              {step === 2 ? <LooseEnds loose={loose} places={places} all={all} sweeping={sweeping}
                onPick={(ref, v) => setPlaces(p => ({ ...p, [ref]: v }))}
                onAll={v => setPlaces(p => { const q = { ...p }; for (const x of loose) q[x.ref] = v; return q; })} onMore={() => setAll(true)} /> : null}
              {step === 3 ? <TomorrowStep tm={tm} prep={prep} made={made} first={firstList} weekly={weekly} friday={!!day.friday}
                onPrep={k => setPrep(p => { const q = new Set(p); q.has(k) ? q.delete(k) : q.add(k); return q; })} /> : null}
            </section>
            <footer class="cdfoot"><span class="left">{sweeping ? "The sweep only proposes; closing now closes when it finishes." : `${step + 1} of 4`}</span>
              {step ? <button type="button" class="btn" data-cdback="1" onClick={() => move(-1)}>Back</button>
                : <button type="button" class="btn" data-dcnot="1" onClick={notYet}>Not yet</button>}
              {step < 3 ? <button type="button" class="btn primary" data-cdnext="1" onClick={() => move(1)}>Next</button>
                : <button type="button" class="btn primary" data-dcdone="1" data-cdnext="1" disabled={busy} onClick={close}>{day.closed ? "Close it again" : "Close the day"}</button>}
            </footer>
          </>
        )}
      </div>
    </Dialog>
  );
}
