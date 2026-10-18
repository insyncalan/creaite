// @ts-check
/* WeeklyView (v2.1.0 P6, BL-335; #221 H1): what is left of the weekly page once the Reporting hub (components/report/hub/) replaced it. The
   weekly report's section renderers (WEEKLY_RENDER, drawn on the sheet's contract, dev/sprints/v210-contract.md §4), saveFirst (the
   save an export or an approval makes first) and the old #weekly=<code>&week=<Friday> address, which the hub still reads. */
import { Glance } from "./Glance.jsx";
import { CurrentState, Words } from "./Notes.jsx";
import { Asks, Decisions, Overdue, Risks } from "./Tables.jsx";
import { Timeline } from "./Timeline.jsx";
import { WkHeader, WkHealth } from "./Top.jsx";
import { snack } from "../../../core/server.js";
import { saveWeekly, setWeeklyDirty, weeklyBase, weeklyDirty, weeklyDoc, weeklyView } from "../../../stores/weekly.js";

/** @typedef {import("../Sheet.jsx").SheetDoc} SheetDoc */

const sectionWords = (/** @type {string} */ label, /** @type {string} */ empty) => (/** @type {any} */ ctx) => <Words ctx={ctx} label={label} empty={empty} />;
export const WEEKLY_RENDER = { byId: {
  header: (/** @type {any} */ c) => <WkHeader ctx={c} />, health: Object.assign((/** @type {any} */ c) => <WkHealth ctx={c} />, { ownSpark: true }), glance: (/** @type {any} */ c) => <Glance ctx={c} />,
  summary: sectionWords("Summary", "Say what matters this week"), milestones: (/** @type {any} */ c) => <Timeline ctx={c} />,
  asks: (/** @type {any} */ c) => <Asks ctx={c} />, this_week: sectionWords("This week", "Nothing recorded"), next_week: sectionWords("Next week", "Nothing recorded"),
  decisions: (/** @type {any} */ c) => <Decisions ctx={c} />, risks: (/** @type {any} */ c) => <Risks ctx={c} />,
  overdue: (/** @type {any} */ c) => <Overdue ctx={c} />, current_state: (/** @type {any} */ c) => <CurrentState ctx={c} /> } };

/** Save what is on the page; false (and a message) when it didn't save. */
export async function saveFirst() {
  const d = weeklyDoc.value, v = weeklyView.value;
  if (!d || !(weeklyDirty || (v && v.where === "new"))) return true;      // a report never saved is saved before it is exported
  const r = await saveWeekly({ doc: d, base_version: weeklyBase.value });
  if (!r.ok) { snack(r.message || "The report wasn't saved"); return false; }
  setWeeklyDirty(false); return true;
}

/** "ABC" or "ABC&week=2026-10-16" as the address keeps it. @param {string} s @returns {{code: string, week?: string}|null} */
export function parseWeekly(s) {
  const m = /^([A-Z][A-Z0-9]{2,6})(?:&week=(\d{4}-\d{2}-\d{2}))?$/.exec(String(s || ""));
  return m ? { code: m[1], week: m[2] } : null;
}
