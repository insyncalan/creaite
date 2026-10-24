// @ts-check
/* stores/peopleDisplay.js (#360): the People page's Display state, kept in this browser only (never in the people register, never in
   settings.json): how the table is grouped, which columns show and in what order, which groups are folded, and the sort. The rules
   (the allow-lists and the safe reading of what was saved) are core/peopleDisplay.js; this holds the state and saves it. */
import { store } from "../core/page.js";
import { shared } from "../core/state.js";
import { pdDefault, pdNormalise, pdSort, PD_DEFAULT_SORT } from "../core/peopleDisplay.js";

const PD_KEY = "creaite-peopledisplay", PD_SORT_KEY = "creaite-peoplesort";
/** @type {import("../core/peopleDisplay.js").PdState|null} */
let PD_ST = null;
let sortRead = false;

/** The state now; read once from storage, then kept. */
export const pdState = () => PD_ST || (PD_ST = pdNormalise(store.get(PD_KEY, null)));
export const pdSave = () => { store.set(PD_KEY, pdState()); };
/** Put the state back to the starting one (and the sort). */
export function pdReset() { PD_ST = pdDefault(); pdSave(); shared.PSORT = { ...PD_DEFAULT_SORT }; pdSaveSort(); }

/** The sort: read once from storage (a heading click and Order by are the one thing, shared.PSORT), saved after each change. */
export function pdSyncSort() {
  if (!sortRead) { sortRead = true; shared.PSORT = pdSort(store.get(PD_SORT_KEY, null)); return; }
  pdSaveSort();
}
function pdSaveSort() { store.set(PD_SORT_KEY, pdSort(shared.PSORT)); }

/** Test seam: forget what was read, so the next draw reads storage again. */
export function pdForget() { PD_ST = null; sortRead = false; }
