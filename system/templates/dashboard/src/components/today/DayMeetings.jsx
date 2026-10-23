// @ts-check
/* DayMeetings (BL-293): the meetings of the day the band shows, drawn into #dayMeets. A column per meeting: its times, its
   title and project (by name, BL-101), where and who organises it, and what to do about it:
   - a past day: the follow-up, as Calendar import works it out: Minutes made, Draft in Review (with Review), Transcript ready
     (with Process), or No transcript; a transcript not checked yet offers Check (Alan, 13-10-2026);
   - today and later: nothing under the meeting; its title opens the Prep peek (#111; #140, Alan, 16-10-2026, took away the Prepare /
     Prep pill, BL-287's Open icon, "Prep page made" and the Note link).
   A private meeting is "Busy" with its times only. A confidential one shows only its title and times: no project, no where,
   no peek (Alan, 13-10-2026). Off today, one quiet line says that everything below is as of today. */
import { Fragment, render } from "preact";
import { Chip } from "../Chip.jsx";
import { PrepPeek, usePeek } from "../prep/PrepPopup.jsx";
import { minsOf } from "./DayCurve.jsx";
import { wheelRef } from "./wheel.js";

/** @typedef {{state: string, draft?: boolean, processed_shown?: string, why?: string, checked?: boolean, cleared?: boolean,
    process?: {id: string | null, loaded?: string | null}}} Follow */
/** @typedef {{key: string, page?: string | null, page_at_shown?: string}} PrepRef */
/** @typedef {{start: string, end: string, title: string, private?: boolean, confidential?: boolean, id?: string | null,
    p?: string | null, where?: string, organiser?: string | boolean | null, follow?: Follow, prep?: PrepRef | null,
    plan?: string | null, ix?: number | null, attendees?: number, page?: string | null, pageWhen?: string, running?: string}} DayMeeting
    `ix`: the meeting's place in today's calendar (the Prep link's data-prep, as before); `page`:
    its newest prep page; `running`: a check or a process under way ("Checking…"). */
/** @typedef {{title: string, p?: string | null}} AllDay */
/** @typedef {{open: (path: string) => void, process: (m: DayMeeting) => void,
    check: (m: DayMeeting) => void, review: () => void, name: (code: string) => string}} DayActs */
/** @typedef {{day: string, dow: string, isToday: boolean, past: boolean, now: number, mode: string, live: boolean,
    calendar: boolean, unread?: boolean, lastRead?: string, meetings: DayMeeting[], allDay: AllDay[], acts: DayActs,
    onWheel?: (e: WheelEvent) => void}} DayMeetingsProps
    `mode`: "meetings", or "none" (no calendar for today yet, or, with `unread`, a day the calendar has not been read to: Refresh calendar). */


/** A project by name, opening it as pLink does. @param {{code: string, name: (c: string) => string}} props */
function Proj({ code, name }) {
  if (code === "_portfolio") return <span class="pcode">Portfolio</span>;
  const n = name(code);
  return <span class="pcode plink" data-proj={code} role="link" tabIndex={0} title={`Open ${n}`}>{n}</span>;
}

/** What a past meeting's follow-up is. @param {{m: DayMeeting, live: boolean, acts: DayActs}} props */
function FollowUp({ m, live, acts }) {
  const f = m.follow, off = live ? undefined : "creaite isn’t running";
  if (!f) return null;
  if (m.running) return <span class="sub" role="status">{m.running}</span>;
  if (f.state === "minutes") return f.draft
    ? <><Chip tone="warn">Draft in Review</Chip><button type="button" class="lk" aria-label={`Review the draft minutes of ${m.title}`} onClick={() => acts.review()}>Review</button></>
    : <Chip tone="ok" tip={f.processed_shown ? `Processed ${f.processed_shown}` : undefined}>Minutes made</Chip>;
  if (f.state === "transcript") return (
    <><Chip tone="warn">Transcript ready</Chip>
      <button type="button" class="lk" aria-label={`Process the transcript of ${m.title}`} data-tip={off || "Draft minutes and proposed items from it (cx-minutes)"}
        disabled={!live} onClick={() => acts.process(m)}>Process</button></>);
  if (f.checked === false && m.id) return (
    <><Chip tone="mute">Not checked yet</Chip>
      <button type="button" class="lk" aria-label={`Check for a transcript of ${m.title}`} data-tip={off || "Look for its transcript in Teams"}
        disabled={!live} onClick={() => acts.check(m)}>Check</button></>);
  return <Chip tone="mute" tip={f.why}>No transcript</Chip>;
}

/** A meeting's title; on today or a later day it carries the Prep peek (#111, which grew #140's popup): pointer rest or keyboard focus
    opens it, on the one hover standard (core/hover.js, CARD_OPEN and CARD_CLOSE, no timer of its own). It is the 30-second version of
    the prep page (aim, what to raise, the ask, since last time) with Open the prep page; there is no Prepare button and no second
    brief. A dialog with no focus trap, Esc closes it, Internal, never sent. `data-prepgo` is meetings.js's handler.
    @param {{m: DayMeeting, day: string, dow: string, isToday: boolean, live: boolean, acts: DayActs}} props */
function Title({ m, day, dow, isToday, live, acts }) {
  const p = m.prep, pk = usePeek(!m.private && !!p);
  if (m.private || !p) return <>{m.title ?? ""}</>;
  const id = `dmpop-${day}-${m.start}`.replace(/[^\w-]/g, ""), when = isToday ? "Today" : dow;
  const bits = [`${when} ${m.start}`, m.attendees ? `${m.attendees} attending` : "",
    !m.confidential && m.p ? (m.p === "_portfolio" ? "Portfolio" : acts.name(m.p)) : "", "Internal"].filter(Boolean);
  return (
    <span class="dmtw" onFocusOut={pk.onFocusOut}>
      <span class="dmti" ref={pk.trigger} tabIndex={0} aria-haspopup="dialog" aria-expanded={pk.open ? "true" : "false"} aria-controls={pk.open ? id : undefined}>{m.title ?? ""}</span>
      {pk.open ? <PrepPeek mkey={p.key} day={day} title={m.title} bits={bits} plan={m.plan} page={m.page} pageWhen={m.pageWhen} live={live} id={id}
        panel={pk.panel} onEsc={() => pk.shut(true)} open={acts.open} /> : null}
    </span>
  );
}

/** The day's meetings.
    @param {DayMeetingsProps} props */
export function DayMeetings(props) {
  const { day, dow, isToday, past, now, mode, live, calendar, unread, lastRead, meetings, allDay, acts, onWheel } = props;
  const ref = wheelRef(onWheel);
  if (mode === "none") return (
    <div class="daynone" ref={ref}><span>{unread ? "Not read yet" : calendar ? "No calendar for today yet" : "No calendar yet"}</span>
      <button type="button" class="btn" data-refcal="" disabled={!live} title={live ? undefined : "creaite isn’t running"}>Refresh calendar</button>
      {lastRead ? <span class="sub">Last read {lastRead}</span> : null}</div>);
  const st = (/** @type {DayMeeting} */ e) => past ? "past" : !isToday ? "" : minsOf(e.end) <= now ? "past" : minsOf(e.start) <= now && now < minsOf(e.end) ? "now" : "";
  return (
    <Fragment key={day}>
      {meetings.length ? <div class="daymeets" ref={ref}>{meetings.map(e => {
        const hidden = e.private || e.confidential, wh = hidden ? "" : [e.where, e.organiser === true ? "You organise" : e.organiser ? `Organised by ${e.organiser}` : ""].filter(Boolean).join(" · ");
        const acts2 = e.private || !past ? null : <FollowUp m={e} live={live} acts={acts} />;
        return (
          <div class={`dm ${st(e)}`}>
            <div class="tm">{e.start} – {e.end}</div>
            <div class="tt"><Title m={e} day={day} dow={dow} isToday={isToday} live={live} acts={acts} />{!hidden && e.p ? <> <Proj code={e.p} name={acts.name} /></> : null}</div>
            {wh ? <div class="wh">{wh}</div> : null}
            {acts2 ? <div class="acts">{acts2}</div> : null}
          </div>);
      })}</div> : null}
      {allDay.length ? <div class="dayall" ref={ref}>All day: {allDay.map((e, i) => <>{i ? " · " : ""}{e.title ?? ""}{e.p ? <> <Proj code={e.p} name={acts.name} /></> : null}</>)}</div> : null}
      {isToday ? null : <p class="dayaway" ref={ref}>Showing {dow}. Everything below is as of today.</p>}
    </Fragment>
  );
}

/** Draw the day's meetings into `host` (#dayMeets), or clear it with null props.
    @param {Element} host @param {DayMeetingsProps | null} props */
export function drawDayMeetings(host, props) {
  render(props ? <DayMeetings {...props} /> : null, host);
}
