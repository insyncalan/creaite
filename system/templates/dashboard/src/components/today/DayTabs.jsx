// @ts-check
/* DayTabs (BL-293): the day line at the top of Today's day band, in place of the date (#todayDate). A quiet row of small
   capitals, one tab per working day the saved calendar holds (a weekend day only when it has a meeting), with a faint
   "Next week" divider. The chosen day is written out in full; the others stay short; today is in the accent colour, with a
   small dot when another day is chosen. #147 (Alan, 16-10-2026): the line starts at today; the days before it are one quiet
   history icon at its left, which drops them down (newest first) on hover or Enter; a past day that is chosen is shown in the
   line, in its place, so Alan sees where he is. The edge arrows still step through every day. A Tabs block (← → Home End). Two faint chevrons at the band's sides, shown on hover
   and hidden at the ends, step a day for a mouse. The swipe and the keys are never hinted here (Alan, 13-10-2026): Help
   alone describes them. Without a calendar (or with one day) it is the plain date, as before. */
import { render } from "preact";
import { Menu } from "../Menu.jsx";
import { Tabs } from "../Tabs.jsx";

/** @typedef {{date: string, long: string, short: string, today?: boolean, week?: number}} TabDay */
/** @typedef {{days: TabDay[], selected: string, onSelect: (iso: string) => void, onStep: (n: number) => void}} DayTabsProps */

/** The chevron of an edge button (element data, no HTML). @param {{d: string}} props */
const Chevron = ({ d }) => <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d={d} /></svg>;

/** The day line and the band's edge chevrons.
    @param {DayTabsProps} props */
export function DayTabs({ days, selected, onSelect, onStep }) {
  const i = days.findIndex(d => d.date === selected);
  const today = (days.find(d => d.today) || { date: "" }).date;
  /* the days the line lists: today on, and the chosen day when it is earlier; the rest wait in the icon's menu */
  const shown = days.filter(d => !today || d.date >= today || d.date === selected);
  const past = days.filter(d => today && d.date < today).reverse();
  const items = shown.map((d, k) => {
    const prev = shown[k - 1], on = d.date === selected;
    const before = !prev ? null : (d.week || 0) > (prev.week || 0)
      ? <span class="daywk" aria-hidden="true">{d.week === 1 ? "Next week" : "Later"}</span>
      : <span class="daysep" aria-hidden="true">·</span>;
    return { id: d.date, label: on ? d.long : d.today ? "Today" : d.short, name: `${d.long}${d.today ? ", today" : ""}`,
             className: d.today ? "today" : "", current: !!d.today, before };
  });
  return (
    <>
      {past.length ? <Menu hover cls="dypast" btnCls="dypastbtn" icon="history" label="Earlier days" labelCls="vh" chevron={false} menuLabel="Earlier days"
        tip="Earlier days" items={past.map(d => ({ id: d.date, name: d.long, mark: d.date === selected ? "✓" : undefined }))} onPick={onSelect} /> : null}
      <Tabs items={items} selected={selected} onSelect={onSelect} label="Days in the calendar" className="daytabs" tabClass="dy" controls="dayMeets" />
      <button type="button" class="dayedge l" aria-label="Previous day" disabled={i <= 0} onClick={() => onStep(-1)}><Chevron d="M15 18l-6-6 6-6" /></button>
      <button type="button" class="dayedge r" aria-label="Next day" disabled={i >= days.length - 1} onClick={() => onStep(1)}><Chevron d="M9 18l6-6-6-6" /></button>
    </>
  );
}

/** Draw the day line into `host` (#todayDate), or the plain date `text` when there is nothing to move between.
    @param {Element} host @param {DayTabsProps | null} props @param {string} text */
export function drawDayTabs(host, props, text) {
  render(props ? <DayTabs {...props} /> : text, host);
}
