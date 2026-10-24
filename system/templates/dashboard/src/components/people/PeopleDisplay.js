// @ts-check
/* PeopleDisplay (#360): the People page's Display menu, built from the pieces Work's uses (core/displayMenu.js): Group by, Sub-group,
   Order by with a reverse button, Properties (tick, ↑ ↓; Name is locked) and Reset and Done. Key D. The state is stores/peopleDisplay.js
   (this browser only); the table reads it (PeoplePage.jsx). The options come from the allow-lists in core/peopleDisplay.js, so nothing
   private can appear here. Nothing in this file writes to a project, the register or a setting. */
import { $, putHTML, raw, html } from "../../core/dom.js";
import { dispController, dispFoot, dispOrder, dispProps, dispSelect } from "../../core/displayMenu.js";
import { PD_COLS, PD_GROUPS, PD_KEYS, PD_LOCKED, PD_ORDER, PD_SORTS, pdSort } from "../../core/peopleDisplay.js";
import { pdReset, pdSave, pdState } from "../../stores/peopleDisplay.js";
import { shared } from "../../core/state.js";
import { snack } from "../../core/server.js";
import { drawPeoplePage } from "./PeoplePage.jsx";

const sortNow = () => pdSort(shared.PSORT);

/** Fill the menu from the state now. */
export function drawPeopleDisplayMenu() {
  const m = $("#plDispMenu"); if (!m) return;
  const st = pdState(), so = sortNow(), label = /** @type {Record<string,string>} */ (Object.fromEntries(PD_COLS.map(c => [c[0], c[1]])));
  const active = document.activeElement, focusKey = active && m.contains(active) ? (active.id || (/** @type {HTMLElement} */ (active).dataset.mv + "|" + /** @type {HTMLElement} */ (active).dataset.d)) : null;
  const shown = st.cols.map(k => /** @type {[string, string]} */ ([k, label[k]])), rest = PD_KEYS.filter(k => !st.cols.includes(k)).map(k => /** @type {[string, string]} */ ([k, label[k]]));
  putHTML(m, html`${raw(dispSelect({ id: "pdgrp", label: "Group by", options: PD_GROUPS, cur: st.group }))}
    ${raw(dispSelect({ id: "pdsub", label: "Sub-group", options: [["none", "None"], ...PD_GROUPS.filter(g => g[0] !== "none" && g[0] !== st.group)], cur: st.sub, hidden: st.group === "none" }))}
    ${raw(dispOrder({ id: "pdsort", revId: "pdRev", options: PD_ORDER, cur: so.col, reversed: so.dir !== PD_SORTS[so.col] }))}
    <h2>Properties</h2><div class="dprops">${raw(dispProps({ shown, rest, locked: PD_LOCKED, prefix: "pdprop", pinFirst: true }))}</div>
    ${raw(dispFoot({ resetId: "pdReset", doneId: "pdDone", resetLabel: "Reset to the default" }))}`);
  if (focusKey) { const f = m.querySelector("#" + CSS.escape(focusKey)) || (focusKey.includes("|") ? m.querySelector(`[data-mv="${focusKey.split("|")[0]}"][data-d="${focusKey.split("|")[1]}"]`) : null); if (f && !(/** @type {any} */ (f)).disabled) /** @type {HTMLElement} */ (f).focus(); else /** @type {HTMLElement|null} */ (m.querySelector("button,select,input"))?.focus(); }
}

const MENU = dispController({ btn: "#plDispBtn", menu: "#plDispMenu", draw: drawPeopleDisplayMenu });
export const openPeopleDisplay = () => MENU.open();
export const closePeopleDisplay = (/** @type {boolean} */ focus) => MENU.close(focus);
export const peopleDisplayOpen = () => MENU.isOpen();

/** A change: saved, the table redrawn, the menu drawn again. */
function changed() { pdSave(); drawPeoplePage(); drawPeopleDisplayMenu(); }

let bound = false;
/** Listen once, at the document, so the menu works however many times the page is drawn. */
export function bindPeopleDisplay() {
  if (bound) return; bound = true;
  window.addEventListener("hashchange", () => closePeopleDisplay(false));      /* leaving the page closes the menu */
  document.addEventListener("click", e => {
    const t = /** @type {Element} */ (e.target); if (!t || !t.closest) return;
    if (t.closest("#plDispBtn")) { e.stopPropagation(); openPeopleDisplay(); return; }
    const m = t.closest("#plDispMenu");
    if (!m) { if (peopleDisplayOpen() && !t.closest(".ddisp")) closePeopleDisplay(false); return; }
    e.stopPropagation();
    const st = pdState(), mv = t.closest("[data-mv]");
    if (mv) {
      e.preventDefault(); const k = /** @type {HTMLElement} */ (mv).dataset.mv || "", i = st.cols.indexOf(k), j = i + Number(/** @type {HTMLElement} */ (mv).dataset.d);
      if (i < 1 || j < 1 || j >= st.cols.length) return;     /* Name stays first */ [st.cols[i], st.cols[j]] = [st.cols[j], st.cols[i]]; changed(); return;
    }
    const id = /** @type {HTMLElement} */ (t).id;
    if (id === "pdRev") { const so = sortNow(); shared.PSORT = { col: so.col, dir: so.dir === "asc" ? "desc" : "asc" }; changed(); return; }
    if (id === "pdReset") { pdReset(); changed(); snack("Display reset to the default"); return; }
    if (id === "pdDone") closePeopleDisplay(true);
  });
  document.addEventListener("change", e => {
    const i = /** @type {HTMLInputElement} */ (e.target); if (!i || !i.closest || !i.closest("#plDispMenu")) return;
    const st = pdState();
    if (i.id === "pdgrp") { st.group = i.value; if (st.sub === st.group) st.sub = "none"; changed(); return; }
    if (i.id === "pdsub") { st.sub = i.value; changed(); return; }
    if (i.id === "pdsort") { const c = i.value; shared.PSORT = { col: c, dir: PD_SORTS[c] || "desc" }; changed(); return; }
    if (i.dataset.prop !== undefined) {
      const k = i.value; if (k === PD_LOCKED || !PD_KEYS.includes(k)) return;
      if (i.checked) { if (!st.cols.includes(k)) st.cols.push(k); } else st.cols = st.cols.filter(x => x !== k);
      changed();
    }
  });
  document.addEventListener("keydown", e => {
    if (e.key === "Escape" && peopleDisplayOpen() && /** @type {Element} */ (e.target).closest && /** @type {Element} */ (e.target).closest("#plDispMenu")) { e.preventDefault(); e.stopPropagation(); closePeopleDisplay(true); }
  }, true);
}
