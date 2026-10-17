// @ts-check
/* Pop (v2.1.0 P7): the minutes view's small popovers (the deadline, the owner picker, a check, What changes), in the pattern of
   the building blocks (dev/COMPONENTS.md §3): a non-modal dialog under the button that opened it, named by `label`. On opening,
   focus goes to the field given (a selector) or the first control; Esc closes it (and goes no further, so the page or a dialog
   behind it stays), and so does a click anywhere outside it and its button; focus then goes back to the button. It keeps the
   peek picker's look (.pkpop). A candidate for a top-level Popover block once P5's sheet needs one too. */
import { useEffect, useRef } from "preact/hooks";

const POP_FOCUSABLE = 'input:not([disabled]),button:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';

/** @typedef {{open: boolean, onClose: () => void, label: string, anchor: {current: HTMLElement|null}, focus?: string,
    cls?: string, wide?: boolean, children?: import("preact").ComponentChildren}} PopProps */

/** A popover, open while `open` is true. @param {PopProps} props */
export function Pop({ open, onClose, label, anchor, focus, cls, wide, children }) {
  const box = useRef(/** @type {HTMLDivElement|null} */ (null));
  const back = useRef(true);
  useEffect(() => {
    if (!open) return;
    back.current = true;
    const b = box.current;
    if (b) {                                    // past the right edge of the sheet's scroller (or the window): open leftwards
      const lim = Math.min(window.innerWidth, (b.closest(".sheet-scroll") || document.documentElement).getBoundingClientRect().right);
      b.classList.toggle("flip", b.getBoundingClientRect().right > lim - 8);
    }
    const f = /** @type {HTMLElement|null} */ (b && ((focus && b.querySelector(focus)) || b.querySelector(POP_FOCUSABLE)) || b);   // a popover of words only (What changes) takes focus itself, so Esc is heard
    if (f) f.focus();
    /** @param {Event} e */
    const away = e => {
      const t = /** @type {Node} */ (e.target);
      if (box.current && !box.current.contains(t) && !(anchor.current && anchor.current.contains(t))) { back.current = false; onClose(); }
    };
    document.addEventListener("pointerdown", away, true);
    return () => {
      document.removeEventListener("pointerdown", away, true);
      const a = anchor.current;
      if (back.current && a && a.isConnected) a.focus();          // closed by Esc, a pick or its own button: focus goes back
    };
  }, [open]);
  if (!open) return null;
  /** @param {KeyboardEvent} e */
  const key = e => { if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); onClose(); } };
  return (
    <div ref={box} class={`pkpop on mnpop${wide ? " wide" : ""}${cls ? " " + cls : ""}`} role="dialog" aria-label={label} tabIndex={-1} onKeyDown={key}>
      {children}
    </div>
  );
}
