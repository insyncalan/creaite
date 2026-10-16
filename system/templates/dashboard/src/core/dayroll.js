// @ts-check
/* core/dayroll.js (#171): a window left open past midnight keeps yesterday as today unless something rolls TODAY.
   rollDay() compares the laptop's date with the one the page holds. On a new day, with nothing unsaved, it moves TODAY (a live
   binding, core/page.js), reloads the page's data and re-renders. With unsaved edits it shows "It's a new day: reload" once and
   changes nothing under the user; the next check rolls the day when the edit is saved or dropped. It runs when the page becomes
   visible and once a minute. The clock is the page's own Date, which tests pin (live_browser.pin_page_clock). */
import { PK } from "../projects.js";
import { selDay } from "../stores/today.js";
import { noteDirty } from "../stores/notes.js";
import { rollWeekStart } from "./data.js";
import { pkNewPending } from "./nav.js";
import { setToday, TODAY } from "./page.js";
import { reloadData, refreshAll, SERVED, snack } from "./server.js";
import { shared } from "./state.js";

let warnedFor = "";   /* the day the "reload" snack was last shown for, so it appears once, not every minute */
let rolling = false;

/** Unsaved work the roll must not redraw under the user: an open editor, a new item, Current state, a proposal, a note. */
export const dayRollBlocked = () => !!((shared.EDITING && shared.CUR) || (shared.CURED && shared.CURED.dirty) || pkNewPending() || PK.dirty || noteDirty());

const dayOf = () => { const d = new Date(), z = n => String(n).padStart(2, "0"); return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}`; };

/** Roll the day if the date has changed. Returns "rolled", "blocked" or "same". */
export async function rollDay() {
  if (rolling || dayOf() === TODAY) return "same";
  if (dayRollBlocked()) {
    const day = dayOf();
    if (warnedFor !== day) { warnedFor = day; snack("It's a new day: reload"); }
    return "blocked";
  }
  rolling = true;
  try {
    const was = setToday(); if (!was) return "same";
    rollWeekStart();
    if (selDay.value === was) selDay.value = "";   /* following "today" again, not pinned to yesterday */
    if (SERVED) await reloadData();   /* refreshAll runs inside it */
    else refreshAll();
    return "rolled";
  } finally { rolling = false; }
}

export function bootDayRoll() {
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") rollDay(); });
  setInterval(rollDay, 60000);
}
