// @ts-check
/* core/displayMenu.js (#360): the Display menu's pieces, shared by Work and People so the two look and behave the same: a labelled
   select, Order by with its reverse button, Properties (tick, and move earlier or later) and the foot (Reset, Done), as the HTML
   strings Work always drew (same classes, same attributes), and the open and close of the menu under its button. The pages keep
   their own state, their own option lists and their own handlers; nothing here knows what a row is. */
import { $, $$, esc } from "./dom.js";

/** A heading: the label of the control under it when there is one. @param {string} label @param {string} [forId] @param {string} [extra] */
export const dispHead = (label, forId, extra = "") => `<h2>${forId ? `<label for="${forId}">${esc(label)}</label>` : esc(label)}${extra}</h2>`;

/** A select with its heading. `hidden` hides the whole block (a control with nothing to choose, not greyed: BL-114).
    @param {{id: string, label: string, options: [string, string][], cur: string, hidden?: boolean}} o */
export function dispSelect({ id, label, options, cur, hidden }) {
  return `<div${hidden ? " hidden" : ""}>${dispHead(label, id)}<div class="dline"><select id="${id}">${options.map(([v, l]) => `<option value="${esc(v)}"${v === cur ? " selected" : ""}>${esc(l)}</option>`).join("")}</select></div></div>`;
}

/** Order by: the select, and a reverse button that is pressed when the order is reversed. `extra` is more option markup (already safe).
    @param {{id: string, revId: string, options: [string, string][], cur: string, reversed: boolean, extra?: string}} o */
export function dispOrder({ id, revId, options, cur, reversed, extra = "" }) {
  return `${dispHead("Order by", id)}<div class="dline"><select id="${id}">${options.map(([v, l]) => `<option value="${esc(v)}"${v === cur ? " selected" : ""}>${esc(l)}</option>`).join("")}${extra}</select><button type="button" class="btn" id="${revId}" aria-pressed="${reversed}" aria-label="Reverse the order" title="Reverse the order">⇅</button></div>`;
}

/** Properties: every column, ticked when shown, the shown ones with ↑ ↓ (24 px targets; the first can't go earlier nor the last later).
    `shown` is in order. `pinFirst` keeps the first column where it is: it has no arrows and the next one can't go above it (People's Name).
    @param {{shown: [string, string][], rest: [string, string][], locked: string, prefix: string, pinFirst?: boolean}} o */
export function dispPropsMarkup({ shown, rest, locked, prefix, pinFirst }) {
  const ord = shown.map(c => c[0]);
  return [...shown, ...rest].map(c => {
    const on = ord.includes(c[0]), i = ord.indexOf(c[0]), l = esc(c[1]);
    return `<label><input type="checkbox" data-prop id="${prefix}-${c[0]}" value="${c[0]}" ${on ? "checked" : ""} ${c[0] === locked ? "disabled" : ""}>${l}${on && !(pinFirst && i === 0) ? `<span class="colmv"><button type="button" data-mv="${c[0]}" data-d="-1" aria-label="Move ${l} earlier" ${i === 0 || (pinFirst && i === 1) ? "disabled" : ""}>↑</button><button type="button" data-mv="${c[0]}" data-d="1" aria-label="Move ${l} later" ${i === ord.length - 1 ? "disabled" : ""}>↓</button></span>` : ""}</label>`;
  }).join("");
}

/** The foot: Reset on the left, Done on the right. @param {{resetId: string, doneId: string, resetLabel: string}} o */
export const dispFoot = ({ resetId, doneId, resetLabel }) => `<div class="dfoot"><button type="button" class="linkbtn" id="${resetId}">${esc(resetLabel)}</button><span class="sp"></span><button type="button" class="btn primary" id="${doneId}">Done</button></div>`;

/** Open and close of a Display menu under its button. `draw` fills the menu each time it opens.
    @param {{btn: string, menu: string, draw: () => void}} o */
export function dispController({ btn, menu, draw }) {
  const isOpen = () => !!$(menu) && $(menu).classList.contains("on");
  /** @param {boolean} [focus] */
  const close = focus => {
    const m = $(menu), b = $(btn); if (!m || !b || (!isOpen() && m.hidden)) return;
    m.classList.remove("on"); m.hidden = true; b.setAttribute("aria-expanded", "false"); b.classList.remove("on"); if (focus) b.focus();
  };
  const open = () => {
    const m = $(menu), b = $(btn); if (!m || !b) return;
    if (isOpen()) { close(true); return; }
    $$(".ddmenu.on").forEach(x => x.classList.remove("on"));
    draw(); m.hidden = false; m.classList.add("on"); b.setAttribute("aria-expanded", "true"); b.classList.add("on");
    /** @type {HTMLElement|null} */ (m.querySelector('[aria-pressed="true"]') || m.querySelector("button,select,input"))?.focus();
  };
  return { isOpen, open, close };
}
