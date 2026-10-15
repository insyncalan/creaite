// @ts-check
/* Toast (BL-256, BL-316, dev/COMPONENTS.md §3): the one message at the foot of the page, with Undo or another action.
   role="status", polite. BL-215's rules are built in: it stays 10 seconds with an action and 5 without; the pointer over it
   or focus inside it holds it (the bar pauses, .held), and leaving starts the full time again (the bar too); Esc hides it,
   at once when you are on it, otherwise only when Esc has nothing else to close (`layers`); focus that was in it goes back
   where it came from. The text goes through JSX only. It keeps today's markup and classes (#snack, #snackT, #snackU, .on,
   .held, .mtimer), so the styles and the tests that read it are unchanged.
   The page draws one, from core/server.js: `snack(msg, undo, label)` stays the call everyone uses (and the seam tests
   replace); it draws this block with `drawToast`, synchronously, so code that reads #snack straight after sees it. */
import { render } from "preact";
import { useLayoutEffect, useRef, useState } from "preact/hooks";

/** How long a message stays: with an action, and without. */
export const TOAST_ACTION_MS = 10000, TOAST_MS = 5000;
/** What Esc closes before the message, when you are not on it: a dialog, the peek, ask creaite, a menu, a picker. */
export const TOAST_LAYERS = "dialog[open],#panel.on,#chat.on,.ddmenu.on,[role=menu]:not([hidden]),.combo.open,#mvPeek:not([hidden]),.cal";

/** @typedef {{open: boolean, text: string, action?: string, onAction?: () => void, onHide: () => void, run?: number,
    id?: string, textId?: string, actionId?: string, ms?: number, actionMs?: number, layers?: string}} ToastProps
    `action` is the button's words (none: no button, the shorter time); `onAction` runs on its click, and the message then
    hides. `onHide` is told when the message should go (its time is up, Esc, the action): the owner draws it again closed.
    `run` changes with each new message, so its time and its bar start again. `id`, `textId` and `actionId` default to the
    page's (#snack, #snackT, #snackU); `layers` is what Esc closes first. */

/** The toast.
    @param {ToastProps} props */
export function Toast({ open, text, action, onAction, onHide, run = 0, id = "snack", textId = "snackT", actionId = "snackU",
  ms = TOAST_MS, actionMs = TOAST_ACTION_MS, layers = TOAST_LAYERS }) {
  const box = useRef(/** @type {HTMLDivElement | null} */ (null));
  const [over, setOver] = useState(false), [inside, setInside] = useState(false);
  const overRef = useRef(false), inRef = useRef(false), from = useRef(/** @type {HTMLElement | null} */ (null));
  const wasOpen = useRef(false), wasHeld = useRef(false);
  const cur = useRef({ open, onHide, layers });
  cur.current = { open, onHide, layers };
  const held = over || inside;
  const hide = () => cur.current.onHide();
  /** The bar runs again from the start: off, a reflow, on (only a message with an action has one). */
  const restartBar = () => { const b = box.current; if (!b || !open || !action) return; b.classList.remove("mtimer"); void b.offsetWidth; b.classList.add("mtimer"); };

  useLayoutEffect(restartBar, [run]);
  useLayoutEffect(() => { if (wasHeld.current && !held) restartBar(); wasHeld.current = held; }, [held]);
  useLayoutEffect(() => {          /* its time; checked again when it fires, in case a focus or pointer event was missed */
    if (!open || held) return undefined;
    const t = setTimeout(() => {
      const b = box.current, i = !!b && b.contains(document.activeElement), o = !!b && b.matches(":hover");
      if (i || o) { inRef.current = i; overRef.current = o; setInside(i); setOver(o); } else hide();
    }, action ? actionMs : ms);
    return () => clearTimeout(t);
  }, [open, run, held, action]);
  useLayoutEffect(() => {          /* closed: focus that was in it goes back where it came from */
    if (wasOpen.current && !open) {
      const b = box.current, wasIn = inRef.current || (!!b && b.contains(document.activeElement));
      inRef.current = false; overRef.current = false; setInside(false); setOver(false);
      if (wasIn) {
        const f = from.current; from.current = null;
        if (f && f.isConnected && f !== document.body) f.focus({ preventScroll: true });
        else /** @type {HTMLElement | null} */ (document.activeElement)?.blur();
      }
    }
    wasOpen.current = open;
  }, [open]);
  useLayoutEffect(() => {          /* Esc, before the page's own Esc handlers (registered as the toast is first drawn) */
    /** @param {KeyboardEvent} e */
    const key = e => {
      const p = cur.current;
      if (e.key !== "Escape" || !p.open) return;
      if (inRef.current || overRef.current) { e.preventDefault(); e.stopImmediatePropagation(); p.onHide(); return; }
      if (!p.layers || !document.querySelector(p.layers)) p.onHide();
    };
    document.addEventListener("keydown", key, true);
    return () => document.removeEventListener("keydown", key, true);
  }, []);

  const cls = ["snack", open ? "on" : "", action ? "mtimer" : "", held && open ? "held" : ""].filter(Boolean).join(" ");
  return (
    <div class={cls} id={id} role="status" aria-live="polite" ref={box}
      onMouseEnter={() => { overRef.current = true; setOver(true); }}
      onMouseLeave={() => { overRef.current = false; setOver(false); }}
      onFocusIn={/** @param {FocusEvent} e */ e => {
        const r = /** @type {HTMLElement | null} */ (e.relatedTarget);
        if (!inRef.current && r && !box.current?.contains(r)) from.current = r;
        inRef.current = true; setInside(true);
      }}
      onFocusOut={/** @param {FocusEvent} e */ e => {
        const r = /** @type {Node | null} */ (e.relatedTarget);
        if (r && box.current?.contains(r)) return;
        inRef.current = false; setInside(false);
      }}>
      <span key={run} id={textId}>{text}</span>
      <button id={actionId} style={action ? "" : "display:none"} onClick={() => { if (onAction) onAction(); hide(); }}>{action || "Undo"}</button>
    </div>
  );
}

/* A modal dialog makes the rest of the page inert, so a message (and its Undo) drawn behind one can't be reached. While a
   modal is open the toast's host sits inside the top one (it is fixed to the window either way, and an open dialog has no
   transform); when the last modal closes it goes back where it was. */
/** @type {Map<Element, {parent: Node, next: Node | null}>} */
const HOMES = new Map();
let WATCHING = false;
/** The top modal dialog, or null. */
const topModal = () => [...document.querySelectorAll("dialog")].filter(d => d.matches(":modal")).pop() || null;
/** Put `host` in the top modal dialog, or back home. @param {Element} host */
export function toastLayer(host) {
  if (!HOMES.has(host)) HOMES.set(host, { parent: /** @type {Node} */ (host.parentNode), next: host.nextSibling });
  const top = topModal(), home = /** @type {{parent: Node, next: Node | null}} */ (HOMES.get(host));
  if (top) { if (host.parentNode !== top) top.appendChild(host); }
  else if (host.parentNode !== home.parent) home.parent.insertBefore(host, home.next && home.next.parentNode === home.parent ? home.next : null);
  if (!WATCHING) {
    WATCHING = true;
    document.addEventListener("close", () => HOMES.forEach((_, h) => toastLayer(h)), true);   /* a dialog closed: the next one down, or home */
  }
}

/** Draw the toast into `host`, redrawn in place (synchronously) by calling it again with new props. An open toast is moved into
    the top modal dialog, so its action can be reached there.
    @param {Element} host @param {ToastProps} props */
export function drawToast(host, props) {
  if (props.open || HOMES.has(host)) toastLayer(host);
  render(<Toast {...props} />, host);
}
