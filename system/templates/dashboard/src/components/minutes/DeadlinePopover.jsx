// @ts-check
/* DeadlinePopover (v2.1.0 P7, BL-338 point 9): a row's deadline. The button (#268: a pill, dashed while empty) shows the date
   (DD-MM-YYYY) or No date; it opens a
   popover with words to type ("Friday", "next week", "next Wednesday", "end of month", "in 2 weeks", "30-10"), the date they
   mean shown before anything is set, the quick picks with their dates, a calendar and Not set. Words are worked out from the
   meeting's date by the one parser (core/datewords.js, deadline mode, the same as minutes_record's), never from today. Setting
   one is the record's `deadline` change (P4), so the row and its staged item change together. */
import { useRef, useState } from "preact/hooks";
import { parseWords } from "../../core/datewords.js";
import { wkDays } from "../../core/fields.js";
import { fd } from "../../core/page.js";
import { Pop } from "./Pop.jsx";

const WEEK = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const LONG = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const DP_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
export const QUICK = [["Friday", "Friday"], ["Next week", "next week"], ["Next Wednesday", "next wednesday"], ["End of month", "end of month"]];

/** The weekend as getDay() numbers (Sunday 0), from settings work.weekend_days (Monday 0 there). */
export const offDays = () => [...wkDays()].map(d => (d + 1) % 7);
/** What words mean as a deadline from the meeting's day: YYYY-MM-DD or null. @param {string} words @param {string} day */
export const deadlineOf = (words, day) => parseWords(words, day, true, "deadline", offDays());
/** "Friday 16-10-2026". @param {string} iso */
export const deadlineDay = iso => `${LONG[new Date(iso + "T12:00:00").getDay()]} ${fd(iso)}`;
const pad2 = (/** @type {number} */ n) => String(n).padStart(2, "0");

/** @typedef {{due: string|null, day: string, label: string, readOnly?: boolean, onSet: (words: string) => Promise<boolean>}} DeadlineProps */

/** The deadline button and its popover. @param {DeadlineProps} props */
export function DeadlinePopover({ due, day, label, readOnly, onSet }) {
  const [open, setOpen] = useState(false);
  const btn = useRef(/** @type {HTMLButtonElement|null} */ (null));
  if (readOnly) return <span class="mndue">{due ? fd(due) : "Not set"}</span>;
  return (
    <span class="mnpopw">
      <button type="button" ref={btn} class={`mndue msel dueb${due ? "" : " empty"}`} aria-haspopup="dialog" aria-expanded={open ? "true" : "false"}
        aria-label={`Deadline: ${due ? deadlineDay(due) : "not set"}. Change the deadline of ${label}`} onClick={() => setOpen(!open)}>
        {due ? fd(due) : "No date"}
      </button>
      <Pop open={open} onClose={() => setOpen(false)} label={`Deadline for ${label}`} anchor={btn} focus="input" cls="pkcal mndl">
        {open ? <DeadlineBody due={due} day={day} onPick={async w => { if (await onSet(w)) setOpen(false); }} /> : null}
      </Pop>
    </span>
  );
}

/** The popover's contents: words, quick picks, a calendar, Not set.
    @param {{due: string|null, day: string, onPick: (words: string) => void}} props */
function DeadlineBody({ due, day, onPick }) {
  const [words, setWords] = useState("");
  const start = due || day;
  const [month, setMonth] = useState(start.slice(0, 7));
  const got = words.trim() ? deadlineOf(words, day) : null;
  const set = () => { if (got) onPick(words.trim()); };
  return (
    <div>
      <label class="mndl-l" for="mnDlWords">Type a due date, worked out from the meeting on {fd(day)}</label>
      <input id="mnDlWords" class="pkdt" type="text" autocomplete="off" placeholder="Friday, next week, 30-10…" value={words}
        aria-describedby="mnDlSaid" onInput={e => setWords(/** @type {HTMLInputElement} */ (e.currentTarget).value)}
        onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); set(); } }} />
      <div id="mnDlSaid" class={`mndl-said${words.trim() && !got ? " bad" : ""}`} role="status">
        {!words.trim() ? "" : got ? <span>{deadlineDay(got)} <button type="button" class="btn sm primary" onClick={set}>Set</button></span>
          : "Not a date creaite can read. Try “Friday”, “next week” or 30-10."}
      </div>
      <div class="pkquick" role="group" aria-label="Quick picks">
        {QUICK.map(([name, w]) => { const d = deadlineOf(w, day); return d ? (
          <button key={w} type="button" class="btn sm" data-quick={w} aria-label={`${name}: ${deadlineDay(d)}`} onClick={() => onPick(w)}>
            {name} <span class="sub">{fd(d).slice(0, 5)}</span></button>) : null; })}
      </div>
      <Calendar month={month} setMonth={setMonth} due={due} day={day} onPick={iso => onPick(fd(iso))} />
      <button type="button" class="pkopt" data-quick="not set" onClick={() => onPick("not set")}>Not set</button>
    </div>
  );
}

/** A month of days to pick from; weekend days are marked, the meeting's day ringed.
    @param {{month: string, setMonth: (m: string) => void, due: string|null, day: string, onPick: (iso: string) => void}} props */
function Calendar({ month, setMonth, due, day, onPick }) {
  const y = +month.slice(0, 4), m = +month.slice(5, 7);
  const first = new Date(y, m - 1, 1, 12), lead = (first.getDay() + 6) % 7, count = new Date(y, m, 0, 12).getDate();
  const step = (/** @type {number} */ k) => { const d = new Date(y, m - 1 + k, 1, 12); setMonth(`${d.getFullYear()}-${pad2(d.getMonth() + 1)}`); };
  const off = new Set(offDays());
  const cells = [];
  for (let i = 0; i < lead; i++) cells.push(<span key={`b${i}`} />);
  for (let d = 1; d <= count; d++) {
    const iso = `${month}-${pad2(d)}`, dow = new Date(iso + "T12:00:00").getDay();
    cells.push(<button key={iso} type="button" class={`pkday${iso === due ? " on" : ""}${iso === day ? " today" : ""}${off.has(dow) ? " wk" : ""}`}
      data-day={iso} aria-label={deadlineDay(iso)} aria-pressed={iso === due ? "true" : "false"} onClick={() => onPick(iso)}>{d}</button>);
  }
  return (
    <div class="mncal">
      <div class="pkcalh">
        <button type="button" class="btn sm" aria-label="Previous month" onClick={() => step(-1)}>‹</button>
        <b>{DP_MONTHS[m - 1]} {y}</b>
        <button type="button" class="btn sm" aria-label="Next month" onClick={() => step(1)}>›</button>
      </div>
      <div class="pkgrid">{WEEK.map(w => <span key={w} class="wd" aria-hidden="true">{w.slice(0, 2)}</span>)}{cells}</div>
    </div>
  );
}
