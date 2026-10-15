// @ts-check
/* WeekAhead (BL-319, v1.9.2; BL-72, BL-127, BL-235 before it): Today's Week ahead, day by day to next Monday. Under each
   day, quiet small capitals ("Thursday 15th October"), one row per meeting, milestone and piece of work: its kind (and
   priority) as a tag, the title (it opens the item, a meeting's Prep or the project), who and where, why it is there
   ("due", "3 days overdue", "needed by", "at risk"), and its icon action, calm until the row is pointed at or tabbed into.
   A group's "+n more" is a [data-more] button that today.js's handler opens. Urgent work with no date leads; "Further ahead" (the two weeks after) follows, as before. today.js builds the groups from
   D.week (weekGroups) and does the actions (weekAct); the links keep their data- attributes (data-open, data-cock,
   data-prepday, data-prepgo, data-meeting), so the page-wide handlers open them as they always have. */
import { render } from "preact";
import { Icon } from "../Icon.jsx";
import { IconButton } from "../IconButton.jsx";

/** @typedef {{id: string, icon: string, label: string, name?: string, primary?: boolean, why?: string, data?: Record<string, string>}} WkAct */
/** @typedef {{key: string, kind: string, tag: string, tone?: string, t: string, open?: Record<string, string>, who?: string,
    p?: string, pname?: string, why: string, whyTone?: string, acts: WkAct[], prepgo?: {key: string, day: string, when: string, live: boolean},
    hub?: string}} WkRow */
/** @typedef {{key: string, title: string, note?: string, rows: WkRow[], cap: number, open: boolean}} WkGroup */
/** @typedef {{groups: WkGroup[], empty: string, onAct: (row: WkRow, act: WkAct, btn: HTMLElement) => void,
    blocked: (why: string) => void}} WeekAheadProps */

/** @param {Record<string, string> | undefined} o @returns {Record<string, string>} */
function dataOf(o) {
  /** @type {Record<string, string>} */
  const d = {};
  for (const k of Object.keys(o || {})) d[`data-${k}`] = String((o || {})[k]);
  return d;
}

/** One row. @param {{r: WkRow, hidden: boolean, p: WeekAheadProps}} props */
function WkLine({ r, hidden, p }) {
  return (
    <li class={`wkrow wk-${r.kind}`} data-wk={r.key} hidden={hidden}>
      <span class={`tag wktag${r.tone ? " " + r.tone : ""}`}>{r.tag}</span>
      <div class="tb">
        {r.open ? <a class="t" href="#" {...dataOf(r.open)}>{r.t}</a> : <span class="t">{r.t}</span>}
        {r.who || r.p ? <span class="wkwho">{" — "}{r.who || ""}{r.who && r.p ? ", " : ""}{r.p ? <a class="s" href="#" data-cock={r.p}>{r.pname || r.p}</a> : null}</span> : null}
        {r.prepgo ? <><button type="button" class="ib prepgo" data-prepgo={r.prepgo.key} data-prepgoday={r.prepgo.day}
            aria-label={`Open the prep page for ${r.t}`} data-tip={r.prepgo.live ? `Prep page saved ${r.prepgo.when}` : "Needs the live server"}
            aria-disabled={r.prepgo.live ? undefined : "true"}><Icon name="external" /></button><span class="tag ok prepmade">Prep page made</span></> : null}
        {r.hub ? <>{" "}<a href={`#meeting=${r.hub}`} class="linkbtn mhlink" data-meeting={r.hub} title="Everything about this meeting, from invite to follow-up">Meeting</a></> : null}
      </div>
      <span class={`wkwhy${r.whyTone ? " " + r.whyTone : ""}`}>{r.why}</span>
      <span class="tacts">
        {r.acts.map(a => (
          <IconButton icon={a.icon} label={a.label} name={a.name} primary={a.primary} why={a.why} data={{ wkact: a.id, ...(a.data || {}) }}
            onBlocked={() => p.blocked(a.why || "")}
            onClick={a.data && a.data.prepday ? undefined : e => p.onAct(r, a, /** @type {HTMLElement} */ (e.currentTarget))} />
        ))}
      </span>
    </li>
  );
}

/** The days. @param {WeekAheadProps} props */
export function WeekAhead(props) {
  const { groups, empty } = props;
  if (!groups.length) return <p class="none">{empty}</p>;
  return (
    <>
      {groups.map(g => {
        const more = g.rows.length - g.cap;
        return (
          <div class="wkday" key={g.key} data-day={g.key}>
            <h3 class="wkdh" id={`wkd-${g.key}`}>{g.title}{g.note ? <span class="wkdn">{g.note}</span> : null}</h3>
            <ol class="bl wklist" aria-labelledby={`wkd-${g.key}`}>
              {g.rows.map((r, i) => <WkLine key={r.key} r={r} hidden={!g.open && i >= g.cap} p={props} />)}
            </ol>
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
