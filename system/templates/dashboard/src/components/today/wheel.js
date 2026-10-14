// @ts-check
/* BL-293's build note: a trackpad doesn't move the pointer, so Chrome keeps sending a swipe's wheel events to the element it
   last hit. When a new day replaces that element, the events bubble only inside the removed piece and never reach the band.
   So each piece the band redraws for a new day carries the wheel handler itself (a native, non-passive listener, which
   stays on the piece after it is removed); the handler ignores an event it has already seen on the way up. */
const HOOKED = new WeakSet();

/** A ref that gives its element the band's wheel handler, once.
    @param {((e: WheelEvent) => void) | undefined} onWheel
    @returns {(el: Element | null) => void} */
export const wheelRef = onWheel => el => {
  if (!el || !onWheel || HOOKED.has(el)) return;
  HOOKED.add(el);
  el.addEventListener("wheel", /** @type {EventListener} */ (onWheel), { passive: false });
};
