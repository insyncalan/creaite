// @ts-check
/* core/hover.js (#143, v2.2.0): the one hover standard. Every delay a hover popup waits is a named constant here, and no feature
   has a number of its own. Alan's rule: no hover popup is instantaneous (WCAG 1.4.13: dismissible, hoverable, persistent).

   - tooltip (a small label, #tip): opens TIP_OPEN after the pointer arrives, closes TIP_CLOSE after it leaves; while one is
     showing, the next opens after TIP_NEXT.
   - card (the item peek, the meeting title popup, the Prep peek): opens CARD_OPEN after arriving, closes CARD_CLOSE after the
     pointer leaves the trigger AND the card.
   - menu (rail flyouts and More, toolbar groups, the AI bar's groups): opens MENU_OPEN after arriving, closes MENU_CLOSE after
     leaving; moving to a neighbouring menu while one is open takes MENU_NEXT; a diagonal move toward the menu's box is kept
     open by a safe triangle.
   - keyboard focus opens a tooltip or card with no delay (a menu opens from its key, also with no delay); Esc dismisses and the
     popup stays shut until the pointer has left the trigger; the pointer can move onto the popup without it closing.
   - touch: nothing here reacts to a touch pointer (a tap keeps what it did before). Reduced motion removes the fade in CSS;
     the delays are the same.

   - decided (#160): a menu the keyboard has taken (released) is not closed when the pointer opens a different hover menu, so the two
     can show together. Closing a menu the user is working in, because the pointer passed another trigger, is the worse fault.
     The released one closes by its own Esc, Tab or a pick.

   `hoverGroup` is the state machine (pure: timers are injectable, so a test runs it on a fake clock); `hoverAttach` wires it to
   a trigger and a popup in the page. The tooltip (core/dom.js) uses the TIP_ constants, Menu.jsx's `hover` uses the menu group. */

/** Tooltip: first open, close after leaving, follow-on while one is showing (ms). */
export const TIP_OPEN = 400, TIP_CLOSE = 150, TIP_NEXT = 100;
/** Hover card or peek: open, close after leaving the trigger or the card (ms). */
export const CARD_OPEN = 600, CARD_CLOSE = 300;
/** Hover menu: open, close after leaving, switch to a neighbouring menu while one is open (ms). */
export const MENU_OPEN = 200, MENU_CLOSE = 300, MENU_NEXT = 80;

/** @typedef {"card" | "menu"} HoverKind */
/** @typedef {{x: number, y: number}} Point */
/** @typedef {{left: number, top: number, right: number, bottom: number}} Rect */
/** What a trigger gives the group: how to open and close its popup, and (for the safe triangle) where the popup is; `isOpen` says
    whether the popup is showing, so a popup the keyboard has taken is not claimed back by the pointer.
    @typedef {{open: () => void, close: () => void, rect?: () => Rect | null, isOpen?: () => boolean}} HoverHandlers */
/** @typedef {{set: (fn: () => void, ms: number) => any, clear: (id: any) => void}} HoverClock */

const DELAYS = { card: { open: CARD_OPEN, close: CARD_CLOSE, next: CARD_OPEN }, menu: { open: MENU_OPEN, close: MENU_CLOSE, next: MENU_NEXT } };

/** Is `p` inside the triangle a, b, c?
    @param {Point} p @param {Point} a @param {Point} b @param {Point} c */
export function inTriangle(p, a, b, c) {
  const s = (/** @type {Point} */ u, /** @type {Point} */ v, /** @type {Point} */ w) => (u.x - w.x) * (v.y - w.y) - (v.x - w.x) * (u.y - w.y);
  const d1 = s(p, a, b), d2 = s(p, b, c), d3 = s(p, c, a);
  return !((d1 < 0 || d2 < 0 || d3 < 0) && (d1 > 0 || d2 > 0 || d3 > 0));
}

/** The safe triangle: from where the pointer left the trigger to the two corners of the popup's nearest side.
    @param {Point} from @param {Rect} r @returns {[Point, Point, Point]} */
export function safeTriangle(from, r) {
  if (from.x <= r.left) return [from, { x: r.left, y: r.top }, { x: r.left, y: r.bottom }];
  if (from.x >= r.right) return [from, { x: r.right, y: r.top }, { x: r.right, y: r.bottom }];
  if (from.y <= r.top) return [from, { x: r.left, y: r.top }, { x: r.right, y: r.top }];
  return [from, { x: r.left, y: r.bottom }, { x: r.right, y: r.bottom }];
}

/** One family of hover popups of a kind, of which one shows at a time (the page's menus, or its cards). `key` is whatever names
    the trigger (the element). Every method is safe to call at any time.
    @param {HoverKind} kind @param {Partial<HoverClock>} [clock] */
export function hoverGroup(kind, clock = {}) {
  const T = DELAYS[kind];
  const set = clock.set || ((fn, ms) => setTimeout(fn, ms)), clear = clock.clear || (id => clearTimeout(id));
  /** @type {{key: any, h: HoverHandlers} | null} */ let cur = null;          // the popup showing
  /** @type {any} */ let openT = 0, closeT = 0, wantKey = null;                // timers; who is waiting to open
  /** @type {any} */ let dismissed = null;                                      // Esc: shut until the pointer has left this trigger
  /** @type {{key: any, h: HoverHandlers} | null} */ let released = null;       // the keyboard has this popup: the pointer does not claim it back
  /** @type {{from: Point, h: HoverHandlers} | null} */ let tri = null;         // the pointer left a trigger heading for its popup

  const stopOpen = () => { clear(openT); openT = 0; wantKey = null; };
  const stopClose = () => { clear(closeT); closeT = 0; tri = null; };
  const shut = () => { stopClose(); const c = cur; cur = null; if (c) c.h.close(); };
  /** @param {any} key @param {HoverHandlers} h */
  const show = (key, h) => { released = null; stopOpen(); stopClose(); if (cur && cur.key !== key) shut(); if (!cur) { cur = { key, h }; h.open(); } };
  const later = () => { stopClose(); closeT = set(() => { closeT = 0; tri = null; shut(); }, T.close); };

  return {
    kind,
    /** The key of the popup showing, or null. */
    get current() { return cur ? cur.key : null; },
    /** The pointer arrived at a trigger: open after the delay (the short one when a neighbour is showing).
        @param {any} key @param {HoverHandlers} h */
    enter(key, h) {
      if (dismissed === key) return;                                            // Esc closed it: not again until the pointer has left
      if (released && released.key === key) {                                   // the keyboard has it: leave it alone while it shows
        if (released.h.isOpen && released.h.isOpen()) return;
        released = null;
      }
      if (cur && cur.key === key) { stopClose(); return; }
      if (wantKey === key) return;
      stopOpen(); stopClose();
      wantKey = key;
      openT = set(() => { openT = 0; wantKey = null; show(key, h); }, cur ? T.next : T.open);
    },
    /** The pointer left a trigger (with where it was, for the safe triangle): a wait to open is dropped; an open popup closes after
        the grace unless the pointer reaches it.
        @param {any} key @param {Point} [at] */
    leave(key, at) {
      if (dismissed === key) dismissed = null;
      if (wantKey === key) stopOpen();
      if (cur && cur.key === key) { later(); tri = at ? { from: at, h: cur.h } : null; }
    },
    /** The pointer moved: while it heads for the open popup (inside the safe triangle), the close is put off.
        @param {Point} p */
    move(p) {
      if (!tri || !cur || !closeT) return;
      const r = tri.h.rect && tri.h.rect();
      if (!r) return;
      const [a, b, c] = safeTriangle(tri.from, r);
      if (inTriangle(p, a, b, c)) { const f = tri.from; later(); tri = { from: f, h: cur.h }; }
    },
    /** The pointer is on the popup itself: it stays. */
    panelEnter() { stopClose(); },
    /** The pointer left the popup (and is not on its trigger): it closes after the grace. */
    panelLeave() { if (cur) later(); },
    /** Keyboard focus: opens at once. @param {any} key @param {HoverHandlers} h */
    focus(key, h) { if (dismissed === key) return; show(key, h); },
    /** Focus left the trigger and the popup: closes at once. @param {any} key */
    blur(key) { if (wantKey === key) stopOpen(); if (dismissed === key) dismissed = null; if (cur && cur.key === key) shut(); },
    /** Esc: whatever shows is closed at once, and the trigger stays quiet until the pointer has left it. Returns whether
        anything was closed. */
    dismiss() {
      const was = cur ? cur.key : wantKey;
      stopOpen(); const had = !!cur; shut();
      if (was != null) dismissed = was;
      return had;
    },
    /** The keyboard has taken the popup (focus went into it, or a click or ↓ on its trigger): the group lets go without closing it,
        so Esc, Tab and the arrows are the popup's own and the pointer drifting away no longer closes it. A wait to open is dropped.
        @param {any} key */
    release(key) {
      if (wantKey === key) stopOpen();
      if (cur && cur.key === key) { stopClose(); released = { key, h: cur.h }; cur = null; }
    },
    /** Close at once without the Esc rule (the trigger was removed, or the page changed). */
    close() { stopOpen(); shut(); },
  };
}

/** The page's shared groups: one menu and one card open at a time, across every component. */
export const menuGroup = hoverGroup("menu");
export const cardGroup = hoverGroup("card");

/** Does this device hover? A touch-only screen has no hover: nothing here opens on it.
    @returns {boolean} */
export const canHover = () => typeof matchMedia !== "function" || matchMedia("(hover: hover)").matches;

/** Wire a trigger and its popup to a group, for the pointer, keyboard focus and Esc. `panel` gives the popup (it may not exist until
    it opens). `focusOpens` (default true) opens it from keyboard focus; a menu leaves it off and opens from its keys. Returns the
    function that takes everything off again.
    @param {HTMLElement} trigger
    @param {{group: ReturnType<typeof hoverGroup>, open: () => void, close: () => void, panel: () => Element | null, focusOpens?: boolean, isOpen?: () => boolean}} o
    @returns {() => void} */
export function hoverAttach(trigger, o) {
  const { group, panel } = o, focusOpens = o.focusOpens !== false;
  /** @type {HoverHandlers} */
  const h = { isOpen: o.isOpen, open: o.open, close: () => { document.removeEventListener("pointermove", track, true); o.close(); }, rect: () => { const p = panel(); return p ? p.getBoundingClientRect() : null; } };
  /** @type {"" | "trigger" | "panel"} */ let at = "";
  /** @param {PointerEvent} e */
  const touch = e => e.pointerType === "touch" || !canHover();
  /** @param {EventTarget | null} t */
  const zone = t => { const n = /** @type {Node | null} */ (t); if (!n) return ""; if (trigger.contains(n)) return "trigger"; const p = panel(); return p && p.contains(n) ? "panel" : ""; };
  /** @param {PointerEvent} e */
  const track = e => group.move({ x: e.clientX, y: e.clientY });
  /** @param {PointerEvent} e @param {EventTarget | null} t */
  const pointerAt = (e, t) => {
    if (touch(e)) return;
    const z = zone(t); if (z === at) return;
    const was = at; at = z;
    if (z === "trigger") { document.removeEventListener("pointermove", track, true); group.enter(trigger, h); }
    else if (z === "panel") { document.removeEventListener("pointermove", track, true); group.panelEnter(); }
    else if (was === "trigger") { group.leave(trigger, { x: e.clientX, y: e.clientY }); document.addEventListener("pointermove", track, true); }
    else group.panelLeave();
  };
  /** @param {PointerEvent} e */
  const over = e => pointerAt(e, e.target);
  /** @param {PointerEvent} e */
  const out = e => { if (!e.relatedTarget) pointerAt(e, null); };       // left the window
  /** @param {FocusEvent} e */
  const focusin = e => { if (focusOpens && trigger.matches(":focus-visible") && e.target === trigger) group.focus(trigger, h); };
  /** @param {FocusEvent} e */
  const focusout = e => {
    const to = /** @type {Node | null} */ (e.relatedTarget), p = panel();
    if (!to || (!trigger.contains(to) && !(p && p.contains(to)))) group.blur(trigger);
  };
  /** @param {FocusEvent} e */
  const taken = e => { const p = panel(); if (group.current === trigger && p && e.target instanceof Node && p.contains(e.target)) group.release(trigger); };
  /** @param {KeyboardEvent} e */
  const key = e => { if (e.key === "Escape" && group.current === trigger && group.dismiss()) { e.stopPropagation(); } };
  document.addEventListener("pointerover", over, true); document.addEventListener("pointerout", out, true);
  trigger.addEventListener("focusin", focusin); trigger.addEventListener("focusout", focusout);
  document.addEventListener("keydown", key, true); document.addEventListener("focusin", taken, true);
  return () => {
    document.removeEventListener("focusin", taken, true);
    document.removeEventListener("pointerover", over, true); document.removeEventListener("pointerout", out, true);
    document.removeEventListener("pointermove", track, true); document.removeEventListener("keydown", key, true);
    trigger.removeEventListener("focusin", focusin); trigger.removeEventListener("focusout", focusout);
    if (group.current === trigger) group.close();
  };
}
