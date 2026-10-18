// @ts-check
/* core/topbar.js (#207): the app's top bar (search or jump, ask creaite, theme) hides at once on any scroll down and returns only when the
   top of the page is reached. It uses #202's rule (headerPolicy and its constants, core/scrollPolicy.js), not a second one.
   - No slide, no reveal on scroll up, none for the pointer at the top edge. Switching page shows it again (a new page starts at its top).
   - The page gains the bar's room without its text moving: the bar leaves the layout (class `tb-off` on .main), the page area grows
     upward and the page's own top padding grows by the same amount, so scrollTop and every line stay where they were.
   - Hidden means visibility:hidden (nothing to see or click) and, on the reports where #202 collapses the bar itself, tabindex -1 on its
     controls, so Tab skips the bar either way. Cmd+K, Cmd+J and the palette are keyboard shortcuts and do not need it.
   - The report views (.sheet-root: weekly, client, minutes) are #202's: its slim bar takes the top; this module leaves their scrolling alone. */
import { headerPolicy } from "./scrollPolicy.js";

const BAR_FOCUSABLE = "a[href],button,input,select,textarea,[tabindex]";

export function bootTopBar() {
  const main = document.querySelector(".main"), bar = /** @type {HTMLElement|null} */ (document.querySelector(".main>.bar")), content = /** @type {HTMLElement|null} */ (document.querySelector(".content"));
  if (!main || !bar || !content) return;
  const last = new WeakMap();
  let up = 0, grown = /** @type {{el: HTMLElement, pad: string}[]} */ ([]);

  const setPad = (/** @type {boolean} */ on, /** @type {number} */ h) => {
    if (on) {
      const v = /** @type {HTMLElement|null} */ (content.querySelector(".view:not([hidden])"));
      if (v && !v.querySelector(".sheet-root")) { grown.push({ el: v, pad: v.style.paddingTop }); v.style.paddingTop = `${parseFloat(getComputedStyle(v).paddingTop) + h}px`; }
    } else { grown.forEach(g => { g.el.style.paddingTop = g.pad; }); grown = []; }
  };
  const hide = (/** @type {boolean} */ on) => {
    if (main.classList.contains("tb-off") === on) return;
    if (on) {
      const h = bar.offsetHeight;
      /* focus inside the bar would drop to body when it turns visibility:hidden: move it to the page's scroll container first */
      const v = /** @type {HTMLElement|null} */ (content.querySelector(".view:not([hidden])"));
      if (v && bar.contains(document.activeElement)) { if (!v.hasAttribute("tabindex")) v.tabIndex = -1; v.focus({ preventScroll: true }); }
      main.classList.add("tb-off"); setPad(true, h);
    }
    else { setPad(false, 0); main.classList.remove("tb-off"); }
  };
  /** The scrollers that are "the page": a .view, and any big scroller inside the content area (not a report's sheet: that is #202's). */
  const isPage = (/** @type {Element} */ t) => {
    if (!(t instanceof HTMLElement) || !content.contains(t) || t.closest(".panel,dialog,.ddmenu,.sheet-root") || t.querySelector(".sheet-root")) return false;   /* the minutes scroll as a whole (.mnwrap) at 900 px */
    return t.classList.contains("view") || t.clientHeight >= content.clientHeight * 0.5;
  };
  document.addEventListener("scroll", e => {
    const t = /** @type {HTMLElement} */ (e.target);
    if (!(t instanceof HTMLElement) || !isPage(t)) return;
    const y = t.scrollTop, d = y - (last.get(t) || 0);
    last.set(t, y);
    up = d < 0 ? up - d : 0;
    const act = headerPolicy(y, d, up);
    if (act === "hide") hide(true); else if (act === "show") hide(false);
  }, true);

  /* a page change starts at the top: the bar is back */
  new MutationObserver(ms => { if (ms.some(m => /** @type {Element} */ (m.target).classList.contains("view"))) hide(false); })
    .observe(content, { attributes: true, attributeFilter: ["hidden"], subtree: true });

  /* Tab skips a hidden bar: tabindex -1 on its controls while it has no height (also when #202 collapsed it on a report) */
  const sync = () => {
    const off = bar.offsetHeight === 0;
    bar.querySelectorAll(BAR_FOCUSABLE).forEach(n => {
      const el = /** @type {HTMLElement} */ (n);
      if (off && !el.hasAttribute("data-tb-ti")) { el.setAttribute("data-tb-ti", el.getAttribute("tabindex") ?? ""); el.tabIndex = -1; }
      else if (!off && el.hasAttribute("data-tb-ti")) { const o = el.getAttribute("data-tb-ti"); el.removeAttribute("data-tb-ti"); if (o === "") el.removeAttribute("tabindex"); else el.setAttribute("tabindex", /** @type {string} */ (o)); }
    });
  };
  new ResizeObserver(sync).observe(bar);
}
