// @ts-check
/* ===== #122 step B ===== a popup at the caret, the way stores/aiEdit.js aiPlace puts the AI bar: position:fixed, measured from
   the editor's own coordsAtPos, so nothing it sits inside (the note's header, a scrolled card, a dialog) can move it. Below the caret when
   there is room, else above, else on the roomier side with its height cut to fit; clamped into the window; moved again when anything
   scrolls or the window resizes. (The `/` and `[[ @ #` menus were absolute inside .ned but measured from .ndoc: they dropped by the
   height of the note header and never flipped.) */

/** Place `el` at `pos` of the editor `view`. Returns what undoes its listeners. @param {any} view @param {number} pos @param {HTMLElement} el
    @param {{gap?: number, edge?: number, max?: number, x?: () => number, level?: number, scroll?: boolean, need?: number, from?: number, overlap?: boolean}} [o]
    `x` puts the left edge somewhere other than the caret (the AI bar starts at the selection's start, the card at the editor's text);
    `level` puts the element beside the caret's line instead of under it (the AI sparkle in the margin: its top is the caret's top plus this
    many pixels, it never flips); `need` is the room the element wants below it before it stays there (the AI bar and its hover menu); `from` is where a selection starts: the element sits under `pos` (its end) and, when it flips, above `from`, so it never covers the selection; `overlap` is for a card that must be read whole (the AI suggestion): when it fits neither under nor above a tall selection it sits as low in the window as it fits, over the selection, instead of being cut short; `scroll: false` leaves `overflow` alone (the AI bar's hover menus hang off it and must not be clipped). */
export function placeAtCaret(view, pos, el, o = {}) {
  const gap = o.gap ?? 4, edge = o.edge ?? 8, max = o.max ?? 360;
  const put = () => {
    if (!el.isConnected || view.isDestroyed) return;
    let c;
    try { c = view.coordsAtPos(Math.min(pos, view.state.doc.content.size)); } catch (e) { return; }
    let c0 = c;
    if (o.from !== undefined) { try { c0 = view.coordsAtPos(Math.min(o.from, view.state.doc.content.size)); } catch (e) { /* the end's */ } }
    const vw = document.documentElement.clientWidth, vh = window.innerHeight;
    el.style.position = "fixed";
    if (o.level !== undefined) {                         /* beside the line, in the margin: clamped into the window, never flipped */
      const w0 = el.offsetWidth, h0 = el.offsetHeight;
      el.style.left = `${Math.max(4, Math.min(o.x ? o.x() : c.left, vw - w0 - 4))}px`;
      el.style.top = `${Math.max(edge, Math.min(c.top + o.level, vh - h0 - edge))}px`;
      el.dataset.side = "level";
      return;
    }
    el.style.maxHeight = ""; if (o.scroll !== false) el.style.overflowY = "auto";
    const w = el.offsetWidth, natural = Math.min(el.scrollHeight, max);
    const below = vh - c.bottom - gap - edge, above = c0.top - gap - edge;
    const up = Math.max(natural, o.need || 0) > below && above > below;          /* flip only when it doesn't fit below and there is more room above */
    if (o.overlap && natural > below && natural > above) {          /* a tall selection: the card goes over it, as low as it fits, never cut short */
      const h2 = Math.min(natural, vh - 2 * edge);
      el.style.maxHeight = `${h2}px`;
      el.style.left = `${Math.max(edge, Math.min(o.x ? o.x() : c.left, vw - w - edge))}px`;
      el.style.top = `${Math.max(edge, vh - edge - h2)}px`;
      el.dataset.side = "over";
      return;
    }
    const room = Math.max(60, up ? above : below), h = Math.min(natural, room);
    if (o.scroll !== false) el.style.maxHeight = `${Math.min(max, room)}px`;
    el.style.left = `${Math.max(edge, Math.min(o.x ? o.x() : c.left, vw - w - edge))}px`;
    el.style.top = `${up ? Math.max(edge, c0.top - gap - h) : c.bottom + gap}px`;
    el.dataset.side = up ? "above" : "below";
  };
  put();
  /* a resize or scroll moves the caret AFTER the layout settles (Current state reflows its panes): place now, again on the next frame and once more shortly after */
  let raf = 0, tm = 0;
  const on = () => { put(); cancelAnimationFrame(raf); clearTimeout(tm); raf = requestAnimationFrame(put); tm = window.setTimeout(put, 120); };
  window.addEventListener("scroll", on, true); window.addEventListener("resize", on);
  const vv = window.visualViewport; if (vv) vv.addEventListener("resize", on);
  return () => { cancelAnimationFrame(raf); clearTimeout(tm); window.removeEventListener("scroll", on, true); window.removeEventListener("resize", on); if (vv) vv.removeEventListener("resize", on); };
}
