// @ts-check
/* Intake's ticks and right-click menu (#323). A tick box on every row that can be set aside; a right-click (or the Menu key, or
   Shift+F10) on a row opens one menu: on a ticked row it acts on every ticked row, on any other row on that row alone.
   The menu is the shared ContextMenu (components/review/ContextMenu.jsx). The actions are actions.js's; each works on the rows
   as the model has them now (never a list kept from earlier), so a row that changed behind the page is simply left out. */
import { openContextMenu } from "../review/ContextMenu.jsx";
import { irModel, irClearTicks, irIsShown, irTickedShown } from "../../stores/intakeReview.js";
import { irAsideMany, irCanCheck, irCanProcess, irCanSetAside, irCheck, irProcess, IR_REASONS } from "./actions.js";

/** The rows a menu opened on row `id` acts on: every ticked row when that row is ticked, else that row alone. @param {string} id */
export function irTargets(id) {
  const ms = irModel().meetings || [], shown = irTickedShown(), ids = shown.includes(id) ? shown : [id];        /* only rows on the page: a ticked row a filter hides is never acted on */
  return ms.filter((/** @type {any} */ m) => ids.includes(m.id) && irIsShown(m.id));
}

/** The menu's items for these rows. A single row also offers Process and Check again; several rows offer only what applies to all
    (Later, Not needed). @param {any[]} ms */
export function irMenuItems(ms) {
  const n = ms.length, one = n === 1 ? ms[0] : null, can = ms.filter(irCanSetAside).length, words = n === 1 ? "" : ` · ${n} meetings`;
  const menu = /** @type {any[]} */ ([]);
  if (one && irCanProcess(one)) menu.push({ label: "Process", run: () => irProcess(one) });
  menu.push({ label: `Later${words}`, disabled: !can, hint: can ? "" : "Nothing here can be set aside", run: () => irAsideMany(ms, "later") });
  menu.push({ label: `Not needed because${words}`, disabled: !can, sub: IR_REASONS.map(r => ({ label: r, run: () => irAsideMany(ms, { reason: r }) })) });
  if (one && irCanCheck(one)) menu.push({ label: "Check again", run: () => irCheck(one) });
  if (n > 1 || irTickedShown().length) menu.push({ sep: true }, { label: "Clear the ticks", run: () => irClearTicks() });
  return menu;
}

let irKbAt = 0;
/** onContextMenu for a row. The Menu key and Shift+F10 also raise this event (with no pointer position), so a row's own key handler
    opens it first and this one stands down when it just did. @param {MouseEvent} e @param {any} m */
export function irRowMenu(e, m) {
  const el = /** @type {HTMLElement} */ (e.currentTarget);
  if (/** @type {Element} */ (e.target).closest("a,input,select,textarea")) return;
  e.preventDefault();
  if (Date.now() - irKbAt < 400) return;
  const r = el.getBoundingClientRect();
  openContextMenu(irMenuItems(irTargets(m.id)), e.clientX || r.left + 24, e.clientY || r.bottom, { label: "Intake actions", from: el });
}
/** onKeyDown for a row: the Menu key or Shift+F10 opens the same menu under the row. @param {KeyboardEvent} e @param {any} m */
export function irRowKey(e, m) {
  if (e.target !== e.currentTarget || !(e.key === "ContextMenu" || (e.key === "F10" && e.shiftKey))) return;
  const el = /** @type {HTMLElement} */ (e.currentTarget), r = el.getBoundingClientRect();
  e.preventDefault(); irKbAt = Date.now();
  openContextMenu(irMenuItems(irTargets(m.id)), r.left + 24, r.bottom, { label: "Intake actions", from: el });
}
