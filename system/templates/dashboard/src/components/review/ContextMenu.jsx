// @ts-check
/* ContextMenu (BL-197, BL-316): the right-click menu of a work item or a proposal, with submenus and a search, drawn on the
   Menu block's MenuPanel (dev/COMPONENTS.md §3). It replaces review.js's hand-made one (its own open, draw, place and run
   functions and their listeners) with the same classes (.pkpop.cxmenu, .pkopt, .cxhead, .cxsep), words and keys:
   - each level is a MenuPanel (a menu named by its label): ↑ ↓ Home End move (wrapping), Enter or Space runs an item,
     → opens an item's submenu and ← closes it, Esc closes the submenu first and then the menu with focus back where it was,
     Tab closes it; a click away, a scroll outside it, a resize or leaving the window closes it;
   - a submenu opens beside its item, on the side that fits the window (BL-175); pointing at an item focuses it and opens its
     submenu; a level with `search` starts in its search box (↓ to the items, Enter runs the first, "No match");
   - opened at the pointer (openContextMenu: a right-click, Shift+F10, the context-menu key) or under a control
     (openContextMenuAt: its aria-expanded follows, as the Menu block's openMenu does).
   An item's `run` is called after the menu has closed; a failure is shown as "Not saved: …". Text only through JSX. */
import { render } from "preact";
import { useLayoutEffect, useRef } from "preact/hooks";
import { snack } from "../../core/server.js";
import { Icon } from "../Icon.jsx";
import { menuItemsIn, MenuPanel } from "../Menu.jsx";

/** @typedef {{label?: string, icon?: string | null, hint?: string, checked?: boolean, disabled?: boolean,
    sub?: CxItem[] | (() => CxItem[]), search?: boolean, run?: () => any, head?: string, sep?: boolean}} CxItem */
/** @typedef {{items: CxItem[], label: string, search: boolean, q: string, key: number, x: number, y: number,
    anchor: HTMLElement | null, pi: number}} CxLevel */
/** @typedef {{label?: string, search?: boolean, from?: Element | null}} CxOpts */

/** The open levels, the menu first; where focus goes back to; the box they are drawn in. */
let LV = /** @type {CxLevel[]} */ ([]);
let FROM = /** @type {Element | null} */ (null);
let OWNER = /** @type {HTMLElement | null} */ (null);
let HOST = /** @type {HTMLDivElement | null} */ (null);
let SEQ = 0;

const draw = () => { if (HOST) render(<ContextMenus />, HOST); };

/** The items a search leaves: headings and separators stay. @param {CxItem[]} items @param {string} q */
const shown = (items, q) => { const t = q.trim().toLowerCase(); return items.filter(it => !t || it.head || it.sep || (it.label || "").toLowerCase().includes(t)); };

/** Close the levels from `i` on. @param {number} i */
function closeFrom(i) { if (LV.length > i) { LV = LV.slice(0, i); draw(); } }

/** Close the whole menu; `ret` puts focus back where it was. @param {boolean} [ret] */
export function closeContextMenu(ret = false) {
  if (!LV.length) return;
  LV = []; draw();
  const f = FROM, o = OWNER; FROM = null; OWNER = null;
  if (o && o.hasAttribute("aria-haspopup")) o.setAttribute("aria-expanded", "false");
  if (ret && f && f.isConnected) /** @type {HTMLElement} */ (f).focus({ preventScroll: true });
}

/** Whether the menu is open (opened from `anchor`, when one is given). @param {HTMLElement | null} [anchor] */
export function contextMenuOpen(anchor) { return !!LV.length && (anchor === undefined || OWNER === anchor); }

let LISTENING = false;
function listen() {
  if (LISTENING) return; LISTENING = true;
  addEventListener("resize", () => closeContextMenu(false));
  addEventListener("blur", () => closeContextMenu(false));
  document.addEventListener("wheel", e => { const t = /** @type {Element} */ (e.target);
    if (LV.length && !(t.closest && t.closest(".cxmenu"))) closeContextMenu(false); }, { capture: true, passive: true });
}

/** @param {CxItem[]} items @param {number} x @param {number} y @param {HTMLElement | null} anchor @param {CxOpts} o */
function open0(items, x, y, anchor, { label, search, from }) {
  closeContextMenu(false);
  if (!HOST || !HOST.isConnected) { HOST = document.createElement("div"); HOST.className = "pophost"; document.body.appendChild(HOST); }
  listen();
  const a = from === undefined ? document.activeElement : from;
  FROM = a && a !== document.body ? a : null; OWNER = anchor;
  if (anchor && anchor.hasAttribute("aria-haspopup")) anchor.setAttribute("aria-expanded", "true");
  LV = [{ items, label: label || "Actions", search: !!search, q: "", key: ++SEQ, x, y, anchor, pi: -1 }];
  draw();
}

/** Open the menu at a point (a right-click, or a row's corner for the keyboard). Focus goes back to `from` (by default what
    had it) when it closes with Esc, Tab or an item.
    @param {CxItem[]} items @param {number} x @param {number} y @param {CxOpts} [o] */
export function openContextMenu(items, x, y, o = {}) { open0(items, x, y, null, o); }

/** Open the menu under a control already in the page (kept in the window, above it when there is no room below); its
    aria-expanded follows and focus goes back to it. @param {HTMLElement} anchor @param {CxItem[]} items @param {CxOpts} [o] */
export function openContextMenuAt(anchor, items, o = {}) { open0(items, 0, 0, anchor, { ...o, from: anchor }); }

/** Run an item of level `i`: open its submenu, or close the menu and run it.
    @param {number} i @param {number} ci @param {HTMLElement | null} btn */
function runItem(i, ci, btn) {
  const lv = LV[i], it = lv && lv.items[ci]; if (!it || it.disabled) return;
  if (it.sub) {
    const sub = typeof it.sub === "function" ? it.sub() : it.sub;
    LV = [...LV.slice(0, i + 1), { items: sub, label: it.label || "", search: !!it.search, q: "", key: ++SEQ, x: 0, y: 0, anchor: null, pi: ci }];
    draw(); btn?.focus({ preventScroll: true });
    focusLevel(i + 1);
    return;
  }
  closeContextMenu(true);
  Promise.resolve().then(() => it.run && it.run()).catch(e => snack("Not saved: " + (e && e.message || e)));
}

/** Focus a level's search box, else its first item (else the box, so Esc works). @param {number} i */
function focusLevel(i) {
  const el = HOST && HOST.querySelectorAll(".cxmenu")[i]; if (!el) return;
  const q = /** @type {HTMLElement | null} */ (el.querySelector(".pkq"));
  (q || menuItemsIn(el)[0] || /** @type {HTMLElement | null} */ (el.querySelector("[role=menu]")))?.focus({ preventScroll: true });
}

/** Esc or ← in level i: a submenu closes with focus back on its item; the menu closes with focus back where it was.
    @param {number} i */
function back(i) {
  if (i === 0) { closeContextMenu(true); return; }
  const el = HOST && HOST.querySelectorAll(".cxmenu")[i - 1], pi = LV[i].pi;
  closeFrom(i);
  /** @type {HTMLElement | null} */ (el && el.querySelector(`[data-ci="${pi}"]`))?.focus({ preventScroll: true });
}

/** Place a level: at its point, under its control, or beside its parent item on the side that fits (BL-175).
    @param {HTMLElement} el @param {number} i */
function place(el, i) {
  const lv = LV[i], w = el.offsetWidth, h = el.offsetHeight;
  let x = lv.x, y = lv.y;
  if (i > 0) {
    const pm = HOST && /** @type {HTMLElement | undefined} */ (HOST.querySelectorAll(".cxmenu")[i - 1]);
    const pb = pm && pm.querySelector(`[data-ci="${lv.pi}"]`);
    if (pm && pb) { const pr = pb.getBoundingClientRect(), m = pm.getBoundingClientRect(); x = m.right - 2; if (x + w > innerWidth - 8) x = Math.max(8, m.left - w + 2); y = pr.top - 6; }
  } else if (lv.anchor) {
    const r = lv.anchor.isConnected ? lv.anchor.getBoundingClientRect() : { left: innerWidth / 2, top: innerHeight / 3, bottom: innerHeight / 3 };
    x = r.left; y = r.bottom + 4; if (y + h > innerHeight - 8) y = Math.max(8, r.top - h - 4);
  }
  x = Math.max(8, Math.min(x, innerWidth - w - 8)); if (y + h > innerHeight - 8) y = Math.max(8, innerHeight - h - 8);
  el.style.left = `${x}px`; el.style.top = `${y}px`;
}

/** One level. @param {{lv: CxLevel, i: number}} props */
function Level({ lv, i }) {
  const wrap = useRef(/** @type {HTMLDivElement | null} */ (null));
  const box = useRef(/** @type {HTMLDivElement | null} */ (null));
  useLayoutEffect(() => { if (wrap.current) place(wrap.current, i); }, [lv.key, lv.q]);
  useLayoutEffect(() => { if (i === 0) focusLevel(0); }, [lv.key]);   /* a submenu is focused by what opened it */
  const next = LV[i + 1];
  const L = shown(lv.items, lv.q);

  /** The level's own keys, before MenuPanel's (↑ ↓ Home End, which wrap). @param {KeyboardEvent} e */
  const keys = e => {
    const t = /** @type {HTMLElement} */ (e.target), items = menuItemsIn(box.current), at = items.indexOf(t);
    const stop = () => { e.preventDefault(); e.stopPropagation(); };
    const q = /** @type {HTMLElement | null} */ (wrap.current && wrap.current.querySelector(".pkq"));
    if (e.key === "ArrowUp" && at <= 0 && q) { stop(); q.focus(); }        /* from the first item back to the search */
    else if (["ArrowDown", "ArrowUp", "Home", "End"].includes(e.key)) return;
    else if (e.key === "ArrowRight") { stop(); if (t.getAttribute("aria-haspopup") === "menu") runItem(i, +(t.dataset.ci || -1), t); }
    else if (e.key === "ArrowLeft") { stop(); if (i > 0) back(i); }
    else if (e.key === "Escape") { stop(); back(i); }
    else if (e.key === "Enter" || e.key === " ") { stop(); if (at >= 0) runItem(i, +(t.dataset.ci || -1), t); }
    else if (e.key === "Tab") { stop(); closeContextMenu(true); }
    else e.stopPropagation();                                              /* the page's own keys wait while it is open */
  };
  /** The search box's keys. @param {KeyboardEvent} e */
  const fieldKeys = e => {
    const items = menuItemsIn(box.current), stop = () => { e.preventDefault(); e.stopPropagation(); };
    if (e.key === "ArrowDown") { stop(); items[0]?.focus({ preventScroll: true }); }
    else if (e.key === "ArrowUp") stop();
    else if (e.key === "Enter") { stop(); const f = items[0]; if (f) runItem(i, +(f.dataset.ci || -1), f); }
    else if (e.key === "Escape") { stop(); back(i); }
    else if (e.key === "Tab") { stop(); closeContextMenu(true); }
  };
  /** Pointing at an item focuses it and opens its submenu (or closes another's). @param {MouseEvent} e */
  const over = e => {
    const b = /** @type {HTMLElement | null} */ (/** @type {Element} */ (e.target).closest("[role=menuitem]")); if (!b) return;
    const ci = +(b.dataset.ci || -1), it = lv.items[ci];
    if (document.activeElement !== b && !(wrap.current && wrap.current.querySelector(".pkq:focus"))) b.focus({ preventScroll: true });
    if (it && it.sub && !it.disabled) { if (!(LV[i + 1] && LV[i + 1].pi === ci)) runItem(i, ci, b); b.focus({ preventScroll: true }); }
    else closeFrom(i + 1);
  };

  return (
    <div class="pkpop cxmenu" ref={wrap} onMouseOver={over}>
      {lv.search ? <input class="pkq" type="search" placeholder="Search" aria-label={`Search: ${lv.label}`} autocomplete="off"
        value={lv.q} onInput={e => { lv.q = /** @type {HTMLInputElement} */ (e.target).value; closeFrom(i + 1); draw(); }} onKeyDown={fieldKeys} /> : null}
      <MenuPanel bare label={lv.label} boxRef={box} anchor={HOST} autoFocus={false} onKey={keys}
        onClose={how => { if (how === "away") closeContextMenu(false); }}>
        {L.length ? L.map((it, n) => {
          if (it.sep) return <div key={`s${n}`} class="cxsep" role="separator"></div>;
          if (it.head) return <div key={`h${n}`} class="cxhead" role="presentation">{it.head}</div>;
          const ci = lv.items.indexOf(it);
          return (
            <button type="button" class="pkopt" role="menuitem" tabIndex={-1} key={ci} data-ci={String(ci)}
              aria-haspopup={it.sub ? "menu" : undefined} aria-expanded={it.sub ? (next && next.pi === ci ? "true" : "false") : undefined}
              aria-disabled={it.disabled ? "true" : undefined} aria-current={it.checked ? "true" : undefined}
              onClick={e => { e.preventDefault(); runItem(i, ci, /** @type {HTMLElement} */ (e.currentTarget)); }}>
              {it.icon ? <Icon name={it.icon} /> : <svg width="18" height="18" aria-hidden="true"></svg>}
              <span>{it.label}{it.hint ? <span class="h">{it.hint}</span> : null}</span>
              {it.checked ? <Icon name="check" cls="ck" /> : it.sub ? <Icon name="chevright" cls="ck cxsub" /> : null}
            </button>
          );
        }) : <div class="pkopt" aria-disabled="true">No match</div>}
      </MenuPanel>
    </div>
  );
}

/** Every open level, the menu first. */
function ContextMenus() { return <>{LV.map((lv, i) => <Level key={lv.key} lv={lv} i={i} />)}</>; }
