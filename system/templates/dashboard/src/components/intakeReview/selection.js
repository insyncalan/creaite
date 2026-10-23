// @ts-check
/* Intake's ticks and right-click menu (#323). A tick box on every row that can be set aside; a right-click (or the Menu key, or
   Shift+F10) on a row opens one menu: on a ticked row it acts on every ticked row, on any other row on that row alone.
   The menu is the shared ContextMenu (components/review/ContextMenu.jsx). The actions are actions.js's; each works on the rows
   as the model has them now (never a list kept from earlier), so a row that changed behind the page is simply left out. */
import { openContextMenu } from "../review/ContextMenu.jsx";
import { irModel, irTicked, irClearTicks } from "../../stores/intakeReview.js";
import { irAsideMany, irCanCheck, irCanProcess, irCanSetAside, irCheck, irProcess, IR_REASONS } from "./actions.js";

/** The rows a menu opened on row `id` acts on: every ticked row when that row is ticked, else that row alone. @param {string} id */
export function irTargets(id) {
  const ms = irModel().meetings || [], ids = irTicked.value.includes(id) ? irTicked.value : [id];
  return ms.filter((/** @type {any} */ m) => ids.includes(m.id));
}

/** The menu's items for these rows. A single row also offers Process and Check again; several rows offer only what applies to all
    (Later, Not needed). @param {any[]} ms */
export function irMenuItems(ms) {
  const n = ms.length, one = n === 1 ? ms[0] : null, can = ms.filter(irCanSetAside).length, words = n === 1 ? "" : ` · ${n} meetings`;
  /** @type {import("../review/ContextMenu.jsx").CxItem[]} */
  const items = [];
  if (one && irCanProcess(one)) items.push({ label: "Process", run: () => irProcess(one) });
  items.push({ label: `Later${words}`, disabled: !can, hint: can ? "" : "Nothing here can be set aside", run: () => irAsideMany(ms, "later") });
  items.push({ label: `Not needed because${words}`, disabled: !can, sub: IR_REASONS.map(r => ({ label: r, run: () => irAsideMany(ms, { reason: r }) })) });
  if (one && irCanCheck(one)) items.push({ label: "Check again", run: () => irCheck(one) });
  if (n > 1 || irTicked.value.length) items.push({ sep: true }, { label: "Clear the ticks", run: () => irClearTicks() });
  return items;
}

let kbAt = 0;
/** onContextMenu for a row. The Menu key and Shift+F10 also raise this event (with no pointer position), so a row's own key handler
    opens it first and this one stands down when it just did. @param {MouseEvent} e @param {any} m */
export function irRowMenu(e, m) {
  const el = /** @type {HTMLElement} */ (e.currentTarget);
  if (/** @type {Element} */ (e.target).closest("a,input,select,textarea")) return;
  e.preventDefault();
  if (Date.now() - kbAt < 400) return;
  const r = el.getBoundingClientRect();
  openContextMenu(irMenuItems(irTargets(m.id)), e.clientX || r.left + 24, e.clientY || r.bottom, { label: "Intake actions", from: el });
}
/** onKeyDown for a row: the Menu key or Shift+F10 opens the same menu under the row. @param {KeyboardEvent} e @param {any} m */
export function irRowKey(e, m) {
  if (e.target !== e.currentTarget || !(e.key === "ContextMenu" || (e.key === "F10" && e.shiftKey))) return;
  const el = /** @type {HTMLElement} */ (e.currentTarget), r = el.getBoundingClientRect();
  e.preventDefault(); kbAt = Date.now();
  openContextMenu(irMenuItems(irTargets(m.id)), r.left + 24, r.bottom, { label: "Intake actions", from: el });
}
