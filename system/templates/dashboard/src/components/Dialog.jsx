// @ts-check
/* Dialog (BL-256 building block, dev/COMPONENTS.md §3): a modal on the native <dialog> with showModal(). Named by its heading
   (aria-labelledby); on opening, focus goes to the field given (a selector) or the first control; Esc (the dialog's cancel) asks
   the owner to close it (onClose), so the owner's state decides; when it closes, focus goes back to whatever opened it; a click on
   the scrim closes it only when nothing is typed (`dirty` false). Popovers inside it render inside it. First used by Close the
   day (BL-295). */
import { useEffect, useRef } from "preact/hooks";

const FOCUSABLE = 'button:not([disabled]),[href],input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';

/** @typedef {{open: boolean, onClose: () => void, labelledBy: string, id?: string, class?: string, focus?: string,
    dirty?: boolean, children?: import("preact").ComponentChildren}} DialogProps */

/** A modal dialog, open while `open` is true.
    @param {DialogProps} props */
export function Dialog({ open, onClose, labelledBy, id, class: cls, focus, dirty, children }) {
  const ref = useRef(/** @type {HTMLDialogElement | null} */ (null));
  const opener = useRef(/** @type {Element | null} */ (null));
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) {
      opener.current = document.activeElement;
      d.showModal();
      const f = /** @type {HTMLElement | null} */ ((focus && d.querySelector(focus)) || d.querySelector(FOCUSABLE));
      if (f) f.focus();
    } else if (!open && d.open) d.close();
  }, [open]);
  /** @param {Event} e */
  const cancel = e => { e.preventDefault(); onClose(); };
  const closed = () => {
    const o = /** @type {HTMLElement | null} */ (opener.current);
    opener.current = null;
    if (o && o.isConnected && typeof o.focus === "function") o.focus();
    if (open) onClose();                     // closed by the browser (a form's method=dialog): tell the owner
  };
  /** @param {MouseEvent} e */
  const scrim = e => {
    const d = ref.current;
    if (!d || e.target !== d || dirty) return;
    const r = d.getBoundingClientRect();
    if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) onClose();
  };
  return (
    <dialog ref={ref} id={id} class={cls} aria-labelledby={labelledBy} onCancel={cancel} onClose={closed} onClick={scrim}>
      {children}
    </dialog>
  );
}
