// @ts-check
/* WeekAhead (BL-319, v1.9.2; BL-72, BL-127, BL-235 before it; #112, #105 v2.2.0): Today's Week ahead, day by day to next Monday,
   as calm rows (Alan chose layout A, 16-10-2026). Under each day, a quiet small-capitals heading ("Thursday 15th October") and
   one rounded list; a row is one meeting, milestone or piece of work: a priority dot (red Urgent, amber High) and a kind icon
   (action tick, risk triangle, milestone diamond), the title with who and the project (a link) under it, one quiet "why" word
   on the right ("due", "due over the weekend", "needed by", "at risk", "on track"), and its actions (Done, Move date, Chase,
   Open) only when the row is pointed at or has focus. A meeting row is tinted, shows its time and one quiet Prep chip ("Prep
   page made" once saved). Above the days, ONE QUIET LINE when other people's work is overdue ("4 actions owned by others are
   overdue. See them in Work"); overdue work no longer leads the list. A group's "+n more" is a [data-more] button that
   today.js's handler opens. Urgent work with no date leads; "Further ahead" (the two weeks after) follows, as before. today.js
   builds the groups from D.week (weekGroups) and does the actions (weekAct); the links keep their data- attributes
   (data-open, data-cock, data-prepgo), so the page-wide handlers open them as they always have. */
import { render } from "preact";
import { Icon } from "../Icon.jsx";
import { IconButton } from "../IconButton.jsx";
import { typeWord } from "../../core/page.js";
import { PrepPeek, usePeek } from "../prep/PrepPopup.jsx";

/** @typedef {{id: string, icon: string, label: string, name?: string, primary?: boolean, why?: string, data?: Record<string, string>}} WkAct */
/** @typedef {{made: boolean, label: string, aria: string, key: string, day: string, live: boolean, title: string, start: string,
    where?: string, pname?: string, pageWhen?: string, page?: string | null}} WkChip
    The Prep chip: it opens the Prep peek on pointer rest or focus (#111) and goes to the prep page when pressed. */
/** @typedef {{key: string, kind: string, type?: string, dot?: string, t: string, time?: string, open?: Record<string, string>, who?: string,
    p?: string, pname?: string, why: string, whyTone?: string, acts: WkAct[], chip?: WkChip,
}} WkRow
    `type`: a RAID item's type (Risk, Issue, Assumption, Dependency); `dot`: "u" (Urgent) or "h" (High); `time`: a meeting's start; `chip`: a meeting's Prep chip (`made`: the saved page's, which goes to it). */
/** @typedef {{key: string, title: string, note?: string, rows: WkRow[], cap: number, open: boolean}} WkGroup */
/** @typedef {{groups: WkGroup[], empty: string, others?: {n: number, nav: string}, onAct: (row: WkRow, act: WkAct, btn: HTMLElement) => void,
    blocked: (why: string) => void, openFile: (path: string) => void}} WeekAheadProps
    `others`: the quiet line's count of overdue items owned by others and the Work address it opens. */

/** @param {Record<string, string> | undefined} o @returns {Record<string, string>} */
function dataOf(o) {
  /** @type {Record<string, string>} */
  const d = {};
  for (const k of Object.keys(o || {})) d[`data-${k}`] = String((o || {})[k]);
  return d;
}

/** The priority dot's words. */
const DOTS = /** @type {Record<string, string>} */ ({ u: "Urgent", h: "High" });
const Diamond = () => <svg class="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l9 9-9 9-9-9z" /></svg>;
/** The kind icon: action tick, risk triangle, milestone diamond, a decision's speech bubble. #286: named on hover (the one
    tooltip) and to a screen reader with the type's word, "Action", "Risk", "Decision"… @param {{kind: string, type?: string}} props */
function Kind({ kind, type }) {
  const w = typeWord(kind, { type });
  return <span class="wkic" role="img" aria-label={w} data-tip={w}>{kind === "milestone" ? <Diamond /> : <Icon name={kind === "raid" ? "alert" : kind === "decisions" ? "chat" : "check"} />}</span>;
}

/** The Prep chip with its peek. @param {{c: WkChip, openFile: (path: string) => void}} props */
function PrepChip({ c, openFile }) {
  const pk = usePeek(), id = `wkpk-${c.day}-${c.start}`.replace(/[^\w-]/g, "");
  const bits = [`${c.day.slice(8)}-${c.day.slice(5, 7)} ${c.start}`, c.pname || "", "Internal"].filter(Boolean);
  return (
    <span class="wkpk" onFocusOut={pk.onFocusOut}>
      <button type="button" ref={/** @type {any} */ (pk.trigger)} class={`wkchip${c.made ? " made" : ""}`} data-prepgo={c.key} data-prepgoday={c.day} aria-label={c.aria}
        aria-haspopup="dialog" aria-expanded={pk.open ? "true" : "false"} aria-controls={pk.open ? id : undefined}
        aria-disabled={c.live ? undefined : "true"}>{c.label}</button>
      {pk.open ? <PrepPeek mkey={c.key} day={c.day} title={c.title} bits={bits} page={c.page} pageWhen={c.pageWhen} live={c.live} id={id}
        panel={pk.panel} onEsc={() => pk.shut(true)} open={openFile} /> : null}
    </span>
  );
}

/** One row. @param {{r: WkRow, hidden: boolean, p: WeekAheadProps}} props */
function WkLine({ r, hidden, p }) {
  const meeting = r.kind === "meeting";
  return (
    <li class={`wkrow wk-${r.kind}`} data-wk={r.key} hidden={hidden}>
      {meeting ? <span class="wktm">{r.time}</span>
        : <><span class={`wkdot${r.dot ? " " + r.dot : ""}`} role={r.dot ? "img" : undefined} aria-label={r.dot ? DOTS[r.dot] : undefined} aria-hidden={r.dot ? undefined : "true"} /><Kind kind={r.kind} type={r.type} /></>}
      <div class="tb">
        {r.open ? <a class="t" href="#" {...dataOf(r.open)}>{r.t}</a> : <span class="t">{r.t}</span>}
        {r.who || r.p ? <span class="wkwho">{r.who || ""}{r.who && r.p ? " · " : ""}{r.p ? <a class="s" href="#" data-cock={r.p}>{r.pname || r.p}</a> : null}</span> : null}
      </div>
      {r.chip ? <PrepChip c={r.chip} openFile={p.openFile} /> : null}
      {r.why ? <span class={`wkwhy${r.whyTone ? " " + r.whyTone : ""}`}>{r.why}</span> : null}
      <span class="tacts">
        {r.acts.map(a => (
          <IconButton icon={a.icon} label={a.label} name={a.name} primary={a.primary} why={a.why} data={{ wkact: a.id, ...(a.data || {}) }}
            onBlocked={() => p.blocked(a.why || "")}
            onClick={e => p.onAct(r, a, /** @type {HTMLElement} */ (e.currentTarget))} />
        ))}
      </span>
    </li>
  );
}

/** The days. @param {WeekAheadProps} props */
export function WeekAhead(props) {
  const { groups, empty, others } = props;
  return (
    <>
      {others && others.n ? <p class="wkpoint">{others.n === 1 ? "1 action owned by others is overdue." : `${others.n} actions owned by others are overdue.`}{" "}
        <a href="#" class="cntl" data-nav={others.nav}>See them in Work</a></p> : null}
      {!groups.length ? <p class="none">{empty}</p> : groups.map(g => {
        const more = g.rows.length - g.cap;
        return (
          <div class="wkday" key={g.key} data-day={g.key}>
            <h3 class="wkdh" id={`wkd-${g.key}`}>{g.title}{g.note ? <span class="wkdn">{g.note}</span> : null}</h3>
            <ul class="wkl" aria-labelledby={`wkd-${g.key}`}>
              {g.rows.map((r, i) => <WkLine key={r.key} r={r} hidden={!g.open && i >= g.cap} p={props} />)}
            </ul>
            {more > 0 ? <div class="moreline"><button type="button" class="qa" aria-expanded={g.open ? "true" : "false"} data-more={g.key}>{g.open ? "Show fewer" : `+${more} more`}</button></div> : null}
          </div>
        );
      })}
    </>
  );
}

/** Draw the Week ahead into #weekList (only today.js calls it). @param {Element} host @param {WeekAheadProps} props */
export function drawWeekAhead(host, props) {
  render(<WeekAhead {...props} />, host);
}
