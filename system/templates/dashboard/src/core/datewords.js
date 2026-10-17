// @ts-check
/* core/datewords.js (BL-147, v2.1.0 P4 BL-338): dates in plain words, the one parser. No imports, so the scripts' copy
   (system/scripts/date_words.py) is checked against this file word for word by dev/tests/test_minutes_record.py.

   parseWords(text, today, due, mode, weekend) returns YYYY-MM-DD, or null.
   - today, tomorrow, yesterday; a weekday ("fri", "friday": the next one, never today; "next fri": the one after that);
     +3d, +2w, +1m (also "3 days", "in 2 weeks"); "next week" (its Monday), "end of week" (Friday), "end of month";
     a day and month ("15/10", "15-10", "15 oct": this year, or next year when a due date would otherwise be in the past);
     DD-MM-YYYY (also with / or ., a two-digit year, or YYYY-MM-DD).
   - mode "deadline" (the minutes' deadlines, minutes-style.md; `today` is the meeting's date, and every date is a due date):
     a leading "by" or "on" is dropped; "next week" is that week's Friday; "next wed" is the Wednesday of the next week;
     "end of month" is its last working day; a period ("in 2 weeks", "+3d") that lands on a weekend moves to the nearest
     working day (the earlier on a tie, BL-181). A weekday or a date that was said stays as said.
   - weekend: the weekend's days as getDay() numbers (Sunday 0), from settings work.weekend_days; Saturday and Sunday by default. */
export const DAYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];
const MON = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];
const MONTH_WORDS = "january february march april may june july august september sept october november december".split(" ");
const DAYNAMES = "sunday monday tuesday wednesday thursday friday saturday tues weds thur thurs".split(" ");
const pad = n => String(n).padStart(2, "0");
const iso = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

/** @param {string} today @param {number} n @param {string} unit */
function shift(today, n, unit) {
  const d = new Date(today + "T12:00:00");
  if (unit === "m") { const day = d.getDate(); d.setDate(1); d.setMonth(d.getMonth() + n); d.setDate(Math.min(day, new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate())); }
  else d.setDate(d.getDate() + n * (unit === "w" ? 7 : 1));
  return iso(d);
}
/** @param {number} y @param {number} m @param {number} d */
function real(y, m, d) { if (y < 100) y += 2000; const x = new Date(y, m - 1, d, 12); return x.getFullYear() === y && x.getMonth() === m - 1 && x.getDate() === d ? iso(x) : null; }
/** @param {string} w */
function monthOf(w) { const i = MON.indexOf(w.slice(0, 3)); return i >= 0 && (MONTH_WORDS.some(n => n.startsWith(w)) || w.length === 3) ? i + 1 : 0; }
/** @param {string} w */
function weekdayOf(w) { return DAYS.findIndex(d => w.startsWith(d) && DAYNAMES.some(n => n.startsWith(w))); }
/** The nearest working day to `day` (the earlier on a tie). @param {string} day @param {number[]} weekend */
export function workingDay(day, weekend = [0, 6]) {
  const off = s => weekend.includes(new Date(s + "T12:00:00").getDay());
  if (!off(day)) return day;
  for (let n = 1; n < 7; n++) { const back = shift(day, -n, "d"), on = shift(day, n, "d"); if (!off(back)) return back; if (!off(on)) return on; }
  return day;
}
/** The last working day of the month `day` is in. @param {string} day @param {number[]} weekend */
function lastWorkingDay(day, weekend) {
  const d = new Date(day + "T12:00:00"); let s = iso(new Date(d.getFullYear(), d.getMonth() + 1, 0, 12));
  for (let n = 0; n < 7 && weekend.includes(new Date(s + "T12:00:00").getDay()); n++) s = shift(s, -1, "d");
  return s;
}
/** The deadline words only: null when the words aren't one of them. @param {string} s @param {string} today @param {number[]} weekend */
function deadlineOnly(s, today, weekend) {
  const dow = new Date(today + "T12:00:00").getDay(), monday = ((1 - dow + 7) % 7) || 7;
  if (s === "next week") return shift(today, monday + 4, "d");                                         /* that week's Friday */
  if (s === "end of month" || s === "eom") return lastWorkingDay(today, weekend);
  const m = s.match(/^next ([a-z]{3,9})$/), w = m ? weekdayOf(m[1]) : -1;
  if (w >= 0) return shift(today, monday + ((w + 6) % 7), "d");                                        /* in the next week */
  return null;
}
/** @param {string} s @param {string} today @param {boolean} due */
function dayMonth(s, today, due) {
  const dm = (d, m, y) => { if (y != null) return real(+y, +m, +d); const yr = +today.slice(0, 4); let r = real(yr, +m, +d); if (r && due && r < today) r = real(yr + 1, +m, +d); return r; };
  let m = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/); if (m) return real(+m[1], +m[2], +m[3]);
  m = s.match(/^(\d{1,2})[\/\-. ](\d{1,2})(?:[\/\-. ](\d{2}|\d{4}))?$/); if (m) return dm(m[1], m[2], m[3]);
  m = s.match(/^(\d{1,2})(?:st|nd|rd|th)? ([a-z]{3,9})(?: (\d{4}))?$/); if (m && monthOf(m[2])) return dm(m[1], monthOf(m[2]), m[3]);
  m = s.match(/^([a-z]{3,9}) (\d{1,2})(?:st|nd|rd|th)?(?: (\d{4}))?$/); if (m && monthOf(m[1])) return dm(m[2], monthOf(m[1]), m[3]);
  return null;
}
/** @param {string} text @param {string} today @param {boolean} [due] @param {string} [mode] @param {number[]} [weekend] @returns {string|null} */
export function parseWords(text, today, due = false, mode = "", weekend = [0, 6]) {
  let s = String(text || "").trim().toLowerCase().replace(/\s+/g, " ").replace(/[.,]$/, ""); if (!s) return null;
  const deadline = mode === "deadline"; if (deadline) { due = true; s = s.replace(/^(?:by|on) /, ""); const d = deadlineOnly(s, today, weekend); if (d) return d; }
  const dow = new Date(today + "T12:00:00").getDay(), period = r => deadline && r ? workingDay(r, weekend) : r;
  if (s === "today" || s === "now") return today; if (s === "tomorrow" || s === "tmrw" || s === "tmr") return shift(today, 1, "d"); if (s === "yesterday") return shift(today, -1, "d");
  let m = s.match(/^(next |this )?([a-z]{3,9})$/);
  if (m) { const w = weekdayOf(m[2]); if (w >= 0) return shift(today, (((w - dow + 7) % 7) || 7) + (m[1] === "next " ? 7 : 0), "d"); }
  if (s === "next week") return shift(today, ((1 - dow + 7) % 7) || 7, "d");                           /* Monday */
  if (s === "end of week" || s === "eow") return shift(today, (5 - dow + 7) % 7, "d");                  /* Friday: today on a Friday */
  if (s === "end of month" || s === "eom") { const d = new Date(today + "T12:00:00"); return iso(new Date(d.getFullYear(), d.getMonth() + 1, 0, 12)); }
  if (s === "end of next week") return shift(today, ((5 - dow + 7) % 7) + 7, "d");
  m = s.match(/^(?:\+|in )?\s*(\d{1,3}) ?(d|days?|w|wks?|weeks?|m|mos?|months?)$/); if (m) return period(shift(today, +m[1], m[2][0]));
  m = s.match(/^\+(\d{1,3})$/); if (m) return period(shift(today, +m[1], "d"));
  return dayMonth(s, today, due);
}
