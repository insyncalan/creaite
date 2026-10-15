// @ts-check
/* ===== #122 step B ===== a popup at the caret, the way stores/aiEdit.js aiPlace puts the AI bar: position:fixed, measured from
   the editor's own coordsAtPos, so nothing it sits inside (the note's header, a scrolled card, a dialog) can move it. Below the caret when
   there is room, else above, else on the roomier side with its height cut to fit; clamped into the window; moved again when anything
   scrolls or the window resizes. (The `/` and `[[ @ #` menus were absolute inside .ned but measured from .ndoc: they dropped by the
   height of the note header and never flipped.) */

/** Place `el` at `pos` of the editor `view`. Returns what undoes its listeners. @param {any} view @param {number} pos @param {HTMLElement} el
    @param {{gap?: number, edge?: number, max?: number}} [o] */
export function placeAtCaret(view, pos, el, o = {}) {
  const gap = o.gap ?? 4, edge = o.edge ?? 8, max = o.max ?? 360;
  const put = () => {
    if (!el.isConnected || view.isDestroyed) return;
    let c;
    try { c = view.coordsAtPos(Math.min(pos, view.state.doc.content.size)); } catch (e) { return; }
    const vw = document.documentElement.clientWidth, vh = window.innerHeight;
    el.style.position = "fixed"; el.style.maxHeight = ""; el.style.overflowY = "auto";
    const w = el.offsetWidth, natural = Math.min(el.scrollHeight, max);
    const below = vh - c.bottom - gap - edge, above = c.top - gap - edge;
    const up = natural > below && above > below;          /* flip only when it doesn't fit below and there is more room above */
    const room = Math.max(60, up ? above : below), h = Math.min(natural, room);
    el.style.maxHeight = `${Math.min(max, room)}px`;
    el.style.left = `${Math.max(edge, Math.min(c.left, vw - w - edge))}px`;
    el.style.top = `${up ? Math.max(edge, c.top - gap - h) : c.bottom + gap}px`;
    el.dataset.side = up ? "above" : "below";
  };
  put();
  const on = () => put();
  window.addEventListener("scroll", on, true); window.addEventListener("resize", on);
  const vv = window.visualViewport; if (vv) vv.addEventListener("resize", on);
  return () => { window.removeEventListener("scroll", on, true); window.removeEventListener("resize", on); if (vv) vv.removeEventListener("resize", on); };
}
