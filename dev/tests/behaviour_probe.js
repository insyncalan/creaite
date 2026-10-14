/* BL-316: the one keyboard script every menu, picker and dialog answers to, on every screen (dev/tests/test_shared_behaviour.py).
   window.SB.openers(region) lists the visible controls that open a popup (aria-haspopup); SB.popups() lists what is open now;
   SB.state(i) says, for opener i, whether it says it is open, where focus is and what is active. The test presses the keys
   (open with Enter, ↓ ↑, Esc, Tab) through Chrome itself and reads SB.state() after each. Development only. */
window.SB = (() => {
  const vis = el => { if (!el || !el.isConnected) return false; if (el.closest("[hidden]")) return false;
    const cs = getComputedStyle(el); if (cs.display === "none" || cs.visibility === "hidden") return false;
    const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const POP = '[role="menu"],[role="listbox"],[role="dialog"],dialog[open],.ddmenu.on,.dmenu.on,.pkpop,.bmenu,.combo.open,.cal,#railMoreMenu,td.ce.editing';
  let L = [];
  const name = el => (el.getAttribute("aria-label") || el.getAttribute("data-tip") || el.textContent || el.id || el.tagName).trim().replace(/\s+/g, " ").slice(0, 60);
  const sig = el => { const id = el.id ? "#" + el.id : ""; const c = (el.className && typeof el.className === "string") ? "." + el.className.trim().split(/\s+/).slice(0, 2).join(".") : "";
    return el.tagName.toLowerCase() + id + c; };
  /** every visible opener in the region, in document order (a disabled one says why and opens nothing: left out) */
  const openers = region => { const root = document.querySelector(region) || document;
    L = [...root.querySelectorAll("[aria-haspopup]:not([aria-haspopup=false])")].filter(el => vis(el) && !el.disabled
      && el.getAttribute("aria-disabled") !== "true" && !el.closest(".ddmenu.on,[role=menu],[role=listbox]"));
    return L.map((el, i) => ({ i, sig: sig(el), name: name(el), kind: el.getAttribute("aria-haspopup"), role: el.getAttribute("role") || el.tagName.toLowerCase() })); };
  /** what is open: visible popups, ignoring the page's permanent regions */
  const popups = () => [...document.querySelectorAll(POP)].filter(el => vis(el) && !el.matches("#panel,#chat") && !el.closest("[role=tablist]"));
  const inPop = el => !!el && popups().some(p => p.contains(el) && p !== document.body);
  const state = i => { const o = L[i], a = document.activeElement, ad = a && a.getAttribute && a.getAttribute("aria-activedescendant");
    return { expanded: o ? o.getAttribute("aria-expanded") : null, connected: !!(o && o.isConnected),
      open: popups().length, focusOnOpener: a === o, focusInPopup: inPop(a) || (!!ad && !!document.getElementById(ad)),
      active: a ? sig(a) + "|" + name(a) + (ad ? "|" + ad : "") : "", modal: !!document.querySelector("dialog:modal"),
      items: popups().reduce((n, p) => n + p.querySelectorAll('[role^="menuitem"]:not([aria-disabled="true"]),[role="option"]:not([aria-disabled="true"])').length, 0) }; };
  const focus = i => { const o = L[i]; if (!o) return false; o.scrollIntoView({ block: "center" }); o.focus(); return document.activeElement === o; };
  /** close whatever is still open, without pressing anything that changes data */
  const reset = () => { document.querySelectorAll("dialog[open]").forEach(d => d.close());
    if (document.activeElement && document.activeElement.blur) document.activeElement.blur(); return popups().length; };
  return { openers, popups: () => popups().map(sig), state, focus, reset };
})();
