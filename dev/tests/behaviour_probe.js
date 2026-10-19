/* BL-316: the one keyboard script every menu, picker and dialog answers to, on every screen (dev/tests/test_shared_behaviour.py).
   window.SB.openers(region) lists the visible controls that open a popup (aria-haspopup); SB.popups() lists what is open now;
   SB.state(i) says, for opener i, whether it says it is open, where focus is and what is active. The test presses the keys
   (open with Enter, ↓ ↑, Esc, Tab) through Chrome itself and reads SB.state() after each. SB.seen(i) says what opener i
   opened (ids, names and classes, matched against the inventory read from the code); SB.writes() counts the page's saves
   and SB.undo() says whether the message at the foot offers Undo (the Undo check). Development only. */
/* The page's saves, counted, for the Undo check: a POST that changes the vault or the tracker. A POST that starts a run
   (ask creaite, a prep page, a draft, an update, a restore…) is answered here and never reaches the server. Installed once. */
if (!window.__SBW) {
  window.__SBW = { writes: 0, runs: 0 };
  const WRITE = /^\/api\/(apply|review(\/(reject|assign|retarget|repeat))?|settings(\/reset)?|intake\/clear|inbox\/(remove|restore|upload)|alerts\/(make|dismiss)|chases|day\/(card|close)|capture|meeting\/carry|agenda\/save|prep\/focus\/save|undo|undo-changes|changes\/undo|alerts\/undo)$/;
  const RUN = /^\/api\/(ask(\/queue)?|prep\/(build|page)|draft|setup\/run|update\/(install|undo|upload)|backup\/restore|stop|current\/(generate|rewrite)|search\/ask|day\/catchup|transcripts\/load|email\/followup|changes\/(approve|decline)|health\/fix\/.*)$/;
  const was = window.fetch.bind(window);
  window.fetch = (url, o) => {
    const path = String(url).replace(/^https?:\/\/[^/]+/, "").split("?")[0];
    if (o && o.method === "POST") {
      let op = ""; try { op = JSON.parse(o.body || "{}").op || ""; } catch (e) { /* not JSON: no op */ }
      if (RUN.test(path)) { window.__SBW.runs++;
        return Promise.resolve(new Response(JSON.stringify({ ok: false, message: "Not run in the behaviour test" }), { headers: { "Content-Type": "application/json" } })); }
      if (WRITE.test(path) || (path === "/api/fs" && /^(write|remove|append|upload)$/.test(op))) window.__SBW.writes++;
    }
    return was(url, o);
  };
}
window.SB = (() => {
  const vis = el => { if (!el || !el.isConnected) return false; if (el.closest("[hidden]")) return false;
    if (el.checkVisibility && !el.checkVisibility({ visibilityProperty: true, contentVisibilityAuto: true })) return false;   /* inside a folded <details> (Today's Week ahead and Resolved): drawn at size by Chrome, but not focusable */
    const cs = getComputedStyle(el); if (cs.display === "none" || cs.visibility === "hidden") return false;
    const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const POP = '[role="menu"],[role="listbox"],[role="dialog"],dialog[open],.ddmenu.on,.dmenu.on,.pkpop,.bmenu,.combo.open,.cal,#railMoreMenu,td.ce.editing';
  let L = [];
  const name = el => (el.getAttribute("aria-label") || el.getAttribute("data-tip") || el.textContent || el.id || el.tagName).trim().replace(/\s+/g, " ").slice(0, 60);
  const sig = el => { const id = el.id ? "#" + el.id : ""; const c = (el.className && typeof el.className === "string") ? "." + el.className.trim().split(/\s+/).slice(0, 2).join(".") : "";
    return el.tagName.toLowerCase() + id + c; };
  /** every visible opener in the region, in document order (a disabled one says why and opens nothing: left out) */
  const openers = region => { const roots = [...document.querySelectorAll(region)];      /* every match: the shell is ".rail,header.bar" */
    L = (roots.length ? roots : [document]).flatMap(root => [...root.querySelectorAll("[aria-haspopup]:not([aria-haspopup=false])")]).filter(el => vis(el) && !el.disabled
      && el.getAttribute("aria-disabled") !== "true" && !el.closest(".ddmenu.on,[role=menu],[role=listbox]")
      && !el.matches("#railMain [data-v]"));   /* #139: the rail's Projects and Work open a list on hover or →/↓; Enter goes to the page (test_shared_behaviour's `rail`) */
    return L.map((el, i) => ({ i, sig: sig(el), name: name(el), kind: el.getAttribute("aria-haspopup"), role: el.getAttribute("role") || el.tagName.toLowerCase() })); };
  /** what is open: visible popups, ignoring the page's permanent regions and what was already showing when the opener
      took focus (the test has closed every popup by then): the dialog a screen is (the Prep popup, the milestone editor)
      and a list that is part of the page (Movement's open milestones) */
  let base = new Set(), baseModal = null;
  const popups = () => [...document.querySelectorAll(POP)].filter(el => vis(el) && !el.matches("#panel,#chat") && !el.closest("[role=tablist]")
    && !base.has(el));
  const inPop = el => !!el && popups().some(p => p.contains(el) && p !== document.body);
  const state = i => { const o = L[i], a = document.activeElement, ad = a && a.getAttribute && a.getAttribute("aria-activedescendant");
    return { busy: !!(o && o.getAttribute("aria-busy") === "true"), expanded: o ? o.getAttribute("aria-expanded") : null, connected: !!(o && o.isConnected),
      open: popups().length, focusOnOpener: a === o, focusInPopup: inPop(a) || (!!ad && !!document.getElementById(ad)),
      active: a ? sig(a) + "|" + name(a) + (ad ? "|" + ad : "") : "", modal: !![...document.querySelectorAll("dialog:modal")].some(d => d !== baseModal),
      items: popups().reduce((n, p) => n + p.querySelectorAll('[role^="menuitem"]:not([aria-disabled="true"]),[role="option"]:not([aria-disabled="true"])').length, 0) }; };
  const focus = i => { const o = L[i]; if (!o) return false; base = new Set(); base = new Set(popups());
    baseModal = document.querySelector("dialog:modal"); o.scrollIntoView({ block: "center" }); o.focus(); return document.activeElement === o; };
  /** close whatever is still open, without pressing anything that changes data */
  const reset = () => { document.querySelectorAll("dialog[open]").forEach(d => d.close());
    if (document.activeElement && document.activeElement.blur) document.activeElement.blur(); return popups().length; };
  /** what opener i opened, for the inventory: the opener's id, name and aria-controls, its ancestors' ids, and each open
      popup's id, aria-label and classes (with the menus and lists inside it) */
  const seen = i => { const o = L[i], out = { ids: [], labels: [], classes: [] }; if (!o) return out;
    const add = el => { if (el.id) out.ids.push(el.id); const l = el.getAttribute("aria-label"); if (l) out.labels.push(l);
      if (typeof el.className === "string") out.classes.push(...el.className.split(/\s+/).filter(Boolean)); };
    if (o.id) out.ids.push(o.id); out.labels.push(name(o)); const c = o.getAttribute("aria-controls"); if (c) out.ids.push(c);
    for (let a = o.parentElement; a; a = a.parentElement) if (a.id) out.ids.push(a.id);
    popups().forEach(p => { add(p); p.querySelectorAll('[role="menu"],[role="listbox"],[role="dialog"],[id]').forEach(add); });
    return out; };
  const writes = () => ({ ...window.__SBW });
  /** the Undo on offer: the message at the foot's (#snackU, with an undo behind it) or the peek's staging bar's "Undo last"
      (#pkUndo: the peek stages each change until it is applied); null when there is none */
  const UNDOS = ["#snackU", "#pkUndo"];
  const undoEl = () => UNDOS.map(s => document.querySelector(s)).find(u => vis(u) && (u.id !== "snackU" || !!window.UNDO)) || null;
  const undo = () => { const u = undoEl(); return u ? "#" + u.id : null; };
  return { openers, popups: () => popups().map(sig), state, focus, reset, seen, writes, undo };
})();
