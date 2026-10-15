// @ts-check
/* Peek (BL-256, BL-316, dev/COMPONENTS.md §3): the frame of a side peek over the page: role="dialog", not modal, named by
   `label` ("Edit milestone", "Edit ABC-A-003"), in the peek's place and size. Its contents stay the area's: old code fills the
   frame (`peekFrame` returns the element, made once at the end of the page and found again after), a component passes children
   to `Peek`. `PeekBar` is the frame's row of controls: Close (with its key), Expand, Previous and Next (disabled at the ends),
   each an IconButton (the same words in aria-label and the tooltip). Esc and focus return stay the owner's (it knows whether a
   popup inside is open, and where the peek was opened from). Text only through JSX. */
import { render } from "preact";
import { IconButton } from "./IconButton.jsx";

/** @typedef {{id: string, label: string, cls?: string, open?: boolean, children?: any}} PeekProps */
/** @typedef {{onClose: () => void, closeKey?: string, onExpand?: () => void, expandLabel?: string, onPrev?: () => void,
    onNext?: () => void, prevOff?: boolean, nextOff?: boolean, ids?: {close?: string, expand?: string, prev?: string, next?: string},
    children?: any}} PeekBarProps */

/** @param {PeekProps} props */
export function Peek({ id, label, cls, open = true, children }) {
  return <aside class={cls} id={id} role="dialog" aria-label={label} hidden={!open}>{children}</aside>;
}

/** The frame's controls; `children` come after Previous and Next (an area's own, such as More).
    @param {PeekBarProps} props */
export function PeekBar({ onClose, closeKey = "Esc", onExpand, expandLabel = "Expand to full width", onPrev, onNext, prevOff, nextOff, ids = {}, children }) {
  return (
    <div class="pk-bar">
      <IconButton icon="arrowright" label="Close" sm={false} id={ids.close} keyHint={closeKey} onClick={onClose} />
      {onExpand ? <IconButton icon="expand" label={expandLabel} sm={false} id={ids.expand} onClick={onExpand} /> : null}
      {onPrev || onNext ? <span class="pk-sep" aria-hidden="true"></span> : null}
      {onPrev ? <IconButton icon="chevup" label="Previous item" sm={false} id={ids.prev} why={prevOff ? "This is the first item" : undefined} onClick={onPrev} /> : null}
      {onNext ? <IconButton icon="chevdown" label="Next item" sm={false} id={ids.next} why={nextOff ? "This is the last item" : undefined} onClick={onNext} /> : null}
      {children}
    </div>
  );
}

/** The frame with this id, made once at the end of the page (hidden) and returned for old code to fill and show.
    @param {string} id @param {{label: string, cls?: string}} props @returns {HTMLElement} */
export function peekFrame(id, { label, cls }) {
  const was = document.getElementById(id); if (was) return was;
  const host = document.createElement("div");
  render(<Peek id={id} label={label} cls={cls} open={false} />, host);
  const el = /** @type {HTMLElement} */ (host.firstElementChild);
  document.body.appendChild(el);     /* moved out of its host: the page's own code owns it from here */
  return el;
}

/** Draw a PeekBar into `host` (old code's peek bar, and the block's own test). @param {Element} host @param {PeekBarProps} props */
export function drawPeekBar(host, props) { render(<PeekBar {...props} />, host); }
