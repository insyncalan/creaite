// @ts-check
/* DayMeetings (BL-293): the meetings of the day the band shows, drawn into #dayMeets. A column per meeting: its times, its
   title and project (by name, BL-101), where and who organises it, and what to do about it:
   - a past day: the follow-up, as Calendar import works it out: Minutes made, Draft in Review (with Review), Transcript ready
     (with Process), or No transcript; a transcript not checked yet offers Check (Alan, 13-10-2026);
   - today and later: one pill that opens the meeting's Prep popup, the accent **Prepare** for a meeting worth preparing for
     (the Week ahead's reason) and **Prep** otherwise; when a prep page exists, BL-287's Open icon and "Prep page made".
   A private meeting is "Busy" with its times only. A confidential one shows only its title and times: no project, no where,
   no Prepare (Alan, 13-10-2026). Off today, one quiet line says that everything below is as of today. */
import { Fragment, render } from "preact";
import { Chip } from "../Chip.jsx";
import { minsOf } from "./DayCurve.jsx";
import { wheelRef } from "./wheel.js";

/** @typedef {{state: string, draft?: boolean, processed_shown?: string, why?: string, checked?: boolean, cleared?: boolean,
    process?: {id: string | null, loaded?: string | null}}} Follow */
/** @typedef {{key: string, page?: string | null, page_at_shown?: string}} PrepRef */
/** @typedef {{start: string, end: string, title: string, private?: boolean, confidential?: boolean, id?: string | null,
    p?: string | null, where?: string, organiser?: string | boolean | null, follow?: Follow, prep?: PrepRef | null,
    plan?: string | null, ix?: number | null, page?: string | null, pageWhen?: string, running?: string}} DayMeeting
    `ix`: the meeting's place in today's calendar (the Prep link's data-prep, as before); `page`:
    its newest prep page; `running`: a check or a process under way ("Checking…"). */
/** @typedef {{title: string, p?: string | null}} AllDay */
/** @typedef {{prep: (m: DayMeeting) => void, open: (path: string) => void, process: (m: DayMeeting) => void,
    check: (m: DayMeeting) => void, review: () => void, name: (code: string) => string,
    note?: (m: DayMeeting, day: string) => void}} DayActs
    `note`: "Note for this meeting" (BL-301 C), the capture drawer with the Working session template. */
/** @typedef {{day: string, dow: string, isToday: boolean, past: boolean, now: number, mode: string, live: boolean,
    calendar: boolean, lastRead?: string, meetings: DayMeeting[], allDay: AllDay[], acts: DayActs,
    onWheel?: (e: WheelEvent) => void}} DayMeetingsProps
    `mode`: "meetings", or "none" (no calendar for today yet: Refresh calendar). */


/** BL-287's Open icon (the mockup's markup, as the Prep popup draws it). */
const OpenIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" />
  </svg>
);

/** A project by name, opening it as pLink does. @param {{code: string, name: (c: string) => string}} props */
function Proj({ code, name }) {
  if (code === "_portfolio") return <span class="pcode">Portfolio</span>;
  const n = name(code);
  return <span class="pcode plink" data-proj={code} role="link" tabIndex={0} title={`Open ${n}`}>{n}</span>;
}

/** What a past meeting's follow-up is. @param {{m: DayMeeting, live: boolean, acts: DayActs}} props */
function FollowUp({ m, live, acts }) {
  const f = m.follow, off = live ? undefined : "Needs the live server";
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

/** Today's and a later day's Prep pill, with BL-287's Open icon and "Prep page made" when a page exists, as the Prep popup
    branch drew them (joined on release-190): the icon is its own button, never inside Prep, and goes to the page inside
    creaite (Meetings › Prep, #prep=<key>, through meetings.js's [data-prepgo] handler); without the live server it is shown
    disabled. @param {{m: DayMeeting, day: string, isToday: boolean, live: boolean, acts: DayActs}} props */
function PrepActs({ m, day, isToday, live, acts }) {
  if (!m.prep) return null;
  const word = m.plan ? "Prepare" : "Prep", byIx = isToday && m.ix != null;
  return (
    <span class="prepline">
      <Chip tone={m.plan ? "cta plan" : "cta"} className="preplink" name={`${word} for ${m.title}`} tip={m.plan ? `Worth preparing for: ${m.plan}` : undefined}
        button {...(byIx ? { "data-prep": String(m.ix) } : { onClick: () => acts.prep(m) })}>{word}</Chip>
      {m.page ? <button type="button" class="ib prepgo" data-prepgo={m.prep.key} data-prepgoday={day} aria-label={`Open the prep page for ${m.title}`}
        aria-disabled={live ? undefined : "true"} data-tip={live ? `Prep page saved ${m.pageWhen || ""}`.trim() : "Needs the live server"}><OpenIcon /></button> : null}
      {m.page ? <span class="tag ok prepmade">Prep page made</span> : null}
    </span>
  );
}

/** The day's meetings.
    @param {DayMeetingsProps} props */
export function DayMeetings(props) {
  const { day, dow, isToday, past, now, mode, live, calendar, lastRead, meetings, allDay, acts, onWheel } = props;
  const ref = wheelRef(onWheel);
  if (mode === "none") return (
    <div class="daynone" ref={ref}><span>{calendar ? "No calendar for today yet" : "No calendar yet"}</span>
      <button type="button" class="btn" data-refcal="" disabled={!live} title={live ? undefined : "Needs the live server"}>Refresh calendar</button>
      {lastRead ? <span class="sub">Last read {lastRead}</span> : null}</div>);
  const st = (/** @type {DayMeeting} */ e) => past ? "past" : !isToday ? "" : minsOf(e.end) <= now ? "past" : minsOf(e.start) <= now && now < minsOf(e.end) ? "now" : "";
  return (
    <Fragment key={day}>
      {meetings.length ? <div class="daymeets" ref={ref}>{meetings.map(e => {
        const hidden = e.private || e.confidential, wh = hidden ? "" : [e.where, e.organiser === true ? "You organise" : e.organiser ? `Organised by ${e.organiser}` : ""].filter(Boolean).join(" · ");
        const acts2 = e.private ? null : past ? <FollowUp m={e} live={live} acts={acts} /> : <PrepActs m={e} day={day} isToday={isToday} live={live} acts={acts} />;
        return (
          <div class={`dm ${st(e)}`}>
            <div class="tm">{e.start} – {e.end}</div>
            <div class="tt">{e.title ?? ""}{!hidden && e.p ? <> <Proj code={e.p} name={acts.name} /></> : null}</div>
            {wh ? <div class="wh">{wh}</div> : null}
            {acts2 || (acts.note && !e.private) ? <div class="acts">{acts2}
              {acts.note && !e.private ? <button type="button" class="linkbtn mnote" aria-label={`Note for this meeting: ${e.title ?? ""}`} data-tip="Note for this meeting"
                onClick={() => acts.note && acts.note(e, day)}>Note</button> : null}</div> : null}
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
