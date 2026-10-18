// @ts-check
/* Dialog (BL-256 building block, dev/COMPONENTS.md §3): a modal on the native <dialog> with showModal(). Named by its heading
   (aria-labelledby, or aria-label when it has none); on opening, focus goes to the field given (a selector) or the first control;
   Esc (the dialog's cancel) asks the owner to close it (onClose), so the owner's state decides; when it closes, focus goes back to
   whatever opened it (unless the owner has since put focus somewhere else); a click on the scrim closes it only when nothing is
   typed (`dirty` false). Popovers inside it render inside it. First used by Close the day (BL-295).

   Two ways to own one (BL-316):
   - controlled: `open` is true or false, and the owner redraws it (Close the day, Customise sidebar);
   - opened by old code: `open` left out. The dialog is drawn once (its inner ids then exist for the old code that fills them) and
     openDialog(id, {focus}) / closeDialog(id) open and close it, at once, as showModal() and close() did. Esc and a form's
     method=dialog close it as the browser does (the owner's own "close" listener hears it); a scrim click closes it unless
     something was typed or chosen in it since it opened (or `dirty` says so); `onClose`, if given, is told after it closed.
   openDialog's `modal: false` opens it without the scrim (the Prep popup's swap while a peek sits over it, BL-286 E); a close
   whose event arrives after the dialog was opened again (such a swap) is not a close.

   ⌘↵ (Ctrl+↵ off a Mac) presses the dialog's primary button (#101), by default, in every dialog: the one marked data-cmdenter, else the
   last visible, enabled .btn.primary. It is the button's own click, so the same checks and messages run, and a disabled button (an
   invalid form) is never pressed. It does nothing during IME composition, when something else already took the key, from a Cancel or
   other button, or while a picker is open (the picker takes the key first and the save follows). In a multi-line field it saves
   instead of adding a line. `cmdEnter={false}` opts a dialog out (a preview whose button only closes it, or a choice that must be
   clicked on purpose: bulk Approve, Undo, Merge, Cancel them all and archive). Dialogs the page's own handler covers (core/fields.js
   CMDENTER: the peek, the panel, the milestone editor) are not <dialog>s and are unchanged. */
import { useEffect, useRef } from "preact/hooks";
import { pickedAnchor } from "./Menu.jsx";

const FOCUSABLE = 'button:not([disabled]),[href],input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';
/** What had focus when each open dialog opened. @type {WeakMap<HTMLDialogElement, Element | null>} */
const OPENER = new WeakMap();
/** Whether anything was typed or chosen in each dialog since it opened. @type {WeakMap<HTMLDialogElement, boolean>} */
const TYPED = new WeakMap();

const PICKER = ".combo.open,#mvCal:not([hidden]),#mvPop:not([hidden]),.cal:not([hidden]):not(:empty)";

/** The button ⌘↵ presses in a dialog: data-cmdenter, else the last visible, enabled primary button; null when there is none.
    @param {HTMLDialogElement} d @returns {HTMLButtonElement | null} */
export function cmdEnterButton(d) {
  const vis = /** @param {Element} b */ b => /** @type {HTMLButtonElement} */ (b).offsetParent !== null || b.getClientRects().length > 0;
  const marked = [...d.querySelectorAll("button[data-cmdenter]")].filter(vis);
  const all = marked.length ? marked : [...d.querySelectorAll("button.primary")].filter(vis);
  return /** @type {HTMLButtonElement | null} */ (all.length ? all[all.length - 1] : null);
}

/** @param {KeyboardEvent} e @param {HTMLDialogElement} d */
function cmdEnter(e, d) {
  if (e.key !== "Enter" || !(e.metaKey || e.ctrlKey) || e.isComposing || e.keyCode === 229 || e.defaultPrevented) return;
  const t = /** @type {HTMLElement} */ (e.target), b = cmdEnterButton(d);
  if (!b) return;
  if (t !== b && t.closest && t.closest("button,a[href]")) return;   // from Cancel or another button: not a save
  e.preventDefault(); e.stopPropagation();                           // a multi-line field saves, it does not add a line
  if (e.repeat) return;
  const go = () => { if (b.isConnected && !b.disabled && d.open) b.click(); };
  if (document.querySelector(PICKER)) setTimeout(go, 0); else go();
}

/** @param {string | Element | null} target @returns {HTMLDialogElement | null} */
const dialogEl = target => /** @type {HTMLDialogElement | null} */ (typeof target === "string" ? document.getElementById(target) : target);

/** Focus the field `focus` names, else the first control that takes focus; `false` leaves focus where it is.
    @param {HTMLDialogElement} d @param {string | false | undefined} focus */
function focusIn(d, focus) {
  if (focus === false) return;
  const want = focus ? d.querySelector(focus) : null;
  for (const f of /** @type {HTMLElement[]} */ ([...(want ? [want] : []), ...d.querySelectorAll(FOCUSABLE)])) {
    f.focus();
    if (document.activeElement === f) return;
  }
}

/** @typedef {{focus?: string | false, modal?: boolean}} OpenOptions */

/** Open a dialog (an id or the element) as the block does: remember what opened it, open it modal (or, `modal: false`, without
    the scrim), focus the field given or the first control. Nothing happens when it is already open. Returns the element.
    @param {string | Element | null} target @param {OpenOptions} [opts] */
export function openDialog(target, { focus, modal = true } = {}) {
  const d = dialogEl(target);
  if (!d || d.open) return d;
  if (!OPENER.has(d)) {
    const a = document.activeElement, picked = pickedAnchor();   // always read, so a pick never goes stale; opened by a menu item: back to the menu's control
    const from = !a || a === document.body || !a.isConnected ? picked : null;
    OPENER.set(d, from || a); TYPED.set(d, false);
  }   // a swap keeps the first opener
  if (modal) d.showModal(); else d.show();
  focusIn(d, focus);
  return d;
}

/** Close a dialog (an id or the element), with an optional return value. @param {string | Element | null} target @param {string} [value] */
export function closeDialog(target, value) {
  const d = dialogEl(target);
  if (d && d.open) d.close(value);
}

/** @typedef {{open?: boolean, onClose?: () => void, labelledBy?: string, ariaLabel?: string, describedBy?: string, id?: string,
    class?: string, focus?: string, cmdEnter?: boolean, dirty?: boolean | (() => boolean), children?: import("preact").ComponentChildren}} DialogProps */

/** A modal dialog: open while `open` is true, or, with `open` left out, opened by openDialog().
    @param {DialogProps} props */
export function Dialog({ open, onClose, labelledBy, ariaLabel, describedBy, id, class: cls, focus, cmdEnter: cmdKey = true, dirty, children }) {
  const ref = useRef(/** @type {HTMLDialogElement | null} */ (null));
  const owned = open !== undefined;
  useEffect(() => {
    const d = ref.current;
    if (!d || !owned) return;
    if (open) openDialog(d, { focus });
    else closeDialog(d);
  }, [open]);
  /** @param {Event} e */
  const cancel = e => { if (owned) { e.preventDefault(); if (onClose) onClose(); } };
  const closed = () => {
    const d = ref.current;
    if (!d || d.open) return;                // opened again before the close event came (a swap): not closed
    const o = /** @type {HTMLElement | null | undefined} */ (OPENER.get(d)), a = document.activeElement;
    OPENER.delete(d);
    if (o && o.isConnected && typeof o.focus === "function" && (!a || a === document.body || d.contains(a))) o.focus();
    if (onClose && (open || !owned)) onClose();   // controlled: closed by the browser (a form's method=dialog), so tell the owner
  };
  const typed = () => { if (ref.current) TYPED.set(ref.current, true); };
  /** @param {MouseEvent} e */
  const scrim = e => {
    const d = ref.current;
    if (!d || e.target !== d) return;
    const busy = typeof dirty === "function" ? dirty() : dirty === undefined ? !owned && !!TYPED.get(d) : dirty;
    if (busy) return;
    const r = d.getBoundingClientRect();
    if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) {
      if (owned) { if (onClose) onClose(); } else d.close();
    }
  };
  return (
    <dialog ref={ref} id={id} class={cls} aria-label={ariaLabel} aria-labelledby={labelledBy} aria-describedby={describedBy}
      onCancel={cancel} onClose={closed} onKeyDown={cmdKey ? (/** @type {KeyboardEvent} */ e) => { if (ref.current) cmdEnter(e, ref.current); } : undefined} onClick={scrim} onInput={typed}>
      {children}
    </dialog>
  );
}
