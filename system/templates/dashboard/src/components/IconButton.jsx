// @ts-check
/* IconButton (BL-256, dev/COMPONENTS.md §3; first used by BL-319's Today rows): an icon-only button, the component form of
   core/dom.js `ibtn`. It keeps ibtn's markup (`<button class="ib">`, the same words in aria-label and data-tip, so the page's
   one tooltip shows them on hover and on keyboard focus), so a screen that moves to it doesn't change its snapshot.
   - `label` names what it does, for the tooltip and a screen reader ("Approve and save", "Reject, with a reason"); `name`,
     when given, is what a screen reader hears instead: the action and what it acts on ("Approve and save: Share the plan").
   - `why` blocks it: aria-disabled="true" (still focusable, so the reason can be read), the reason as its tooltip, and a
     click calls `onBlocked` instead of `onClick`.
   - `primary` gives it the accent colour (the row's main action); `sm` (default on) the 28px size; `cls` extra classes.
   - `data` adds data-* attributes (a page-wide handler can act on them); `haspopup` marks one that opens a menu; `id` and `hidden` (BL-316) as on any button.
   Text only through JSX: nothing here takes HTML. */
import { render } from "preact";
import { Icon } from "./Icon.jsx";

/** @typedef {{icon: string, label: string, name?: string, onClick?: (e: MouseEvent) => void, why?: string, onBlocked?: (e: MouseEvent) => void,
    primary?: boolean, sm?: boolean, cls?: string, data?: Record<string, string>, haspopup?: string, keyHint?: string, id?: string, hidden?: boolean}} IconButtonProps */

/** @param {IconButtonProps} props */
export function IconButton({ icon, label, name, onClick, why, onBlocked, primary, sm = true, cls, data, haspopup, keyHint, id, hidden }) {
  const c = ["ib", sm ? "sm" : "", primary ? "pri" : "", cls].filter(Boolean).join(" ");
  /** @type {Record<string, string>} */
  const extra = {};
  for (const k of Object.keys(data || {})) extra[`data-${k}`] = String((data || {})[k]);
  /** @param {MouseEvent} e */
  const click = e => {
    if (why) { e.preventDefault(); if (onBlocked) onBlocked(e); return; }
    if (onClick) onClick(e);
  };
  return (
    <button type="button" class={c} id={id} hidden={hidden} aria-label={name || label} data-tip={why || label} data-key={keyHint}
      aria-disabled={why ? "true" : undefined} aria-haspopup={/** @type {any} */ (haspopup)} onClick={click} {...extra}>
      <Icon name={icon} />
    </button>
  );
}

/** Draw an IconButton into `host` (the block's own test, and old code that wants one).
    @param {Element} host @param {IconButtonProps} props */
export function drawIconButton(host, props) {
  render(<IconButton {...props} />, host);
}
