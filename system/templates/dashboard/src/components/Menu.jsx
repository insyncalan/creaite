// @ts-check
/* Menu (BL-256, BL-316, dev/COMPONENTS.md §3): a list of commands, in the pattern of Work's New decision menu (an icon, a bold
   name and one explaining line, or plain words). It keeps that menu's classes (.dd, .ddmenu.newmenu), so it looks the same
   wherever it is used. Four ways in, one behaviour:
   - `Menu`: a button that opens it (the button's own markup, its words, its icon and its chevron are props);
   - `openMenu(anchor, props)`: for code not yet moved, a menu opened from an existing control (Today's "…", a board card's
     Move to…, a saved view's ▾, ask creaite's History) or at the pointer (`at`), drawn at the end of the page, kept in the window;
   - `MenuPanel`: the role="menu" box with the keys built in, for a menu whose contents are its own (the sidebar's More, Review's
     reasons menu);
   - `menuMove`: the arrow keys alone, for the right-click menu's submenus (review.js cxOpen).
   Keyboard and names: the button has aria-haspopup="menu" and aria-expanded, and ↓ opens the menu. Inside it, ↑ ↓ Home End
   move, Enter or Space runs an item, and Esc closes it with focus back on the button. Tab or a click away closes it.
   `hover` (#143, core/hover.js): the pointer opens it after MENU_OPEN without moving focus, a neighbouring menu takes MENU_NEXT,
   it closes MENU_CLOSE after the pointer leaves the button and the list, Esc closes it, and a click or ↓ opens it with focus inside.
   Disabled items are aria-disabled and skipped. An item with `checked` is a menuitemcheckbox: picking it toggles it and the
   menu stays open. Headings and notes are words, not items. */
import { render } from "preact";
import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { tipHide } from "../core/dom.js";
import { hoverAttach, menuGroup } from "../core/hover.js";
import { Icon } from "./Icon.jsx";

/** @typedef {{id: string, name?: string, line?: string, icon?: string, mark?: string, checked?: boolean, sep?: boolean,
    head?: string, note?: string, tip?: string, cls?: string, disabled?: boolean, radio?: boolean, data?: Record<string, string>}} MenuItem */
/** @typedef {{label: string, items: MenuItem[], onPick: (id: string) => void, icon?: string, tip?: string, why?: string,
    onBlocked?: () => void, cls?: string, btnCls?: string, menuLabel?: string, left?: boolean, data?: Record<string, string>,
    id?: string, ariaLabel?: string, chevron?: boolean, labelCls?: string, menuId?: string, menuCls?: string,
    hidden?: boolean, hover?: boolean}} MenuProps */
/** How a menu closed: Esc (focus back to its control), Tab, a click away, or an item picked.
    @typedef {"esc" | "tab" | "away" | "pick"} MenuClose */
/** @typedef {{label: string, id?: string, cls?: string, bare?: boolean, style?: Record<string, string>, hidden?: boolean,
    anchor?: HTMLElement | null, onClose: (how: MenuClose) => void, onKey?: (e: KeyboardEvent) => void, autoFocus?: boolean,
    focusKey?: any, boxRef?: {current: HTMLDivElement | null}, children?: any}} MenuPanelProps */
/** @typedef {{label: string, items: MenuItem[], onPick: (id: string) => void, id?: string, cls?: string,
    align?: "left" | "right", at?: {x: number, y: number}, loading?: boolean, onClose?: (how: MenuClose) => void}} PopMenuProps */

/** The hover Menu the keyboard opened (its fold): the pointer opening another folds it, so one is open at a time (the group has let go of it). */
/** @type {(() => void) | null} */
let KB_OPEN = null;

/** The items a key can move between: every item that isn't disabled.
    @param {Element | null} box @returns {HTMLElement[]} */
export const menuItemsIn = box => box ? /** @type {HTMLElement[]} */ ([...box.querySelectorAll("[role^=menuitem]")])
  .filter(b => b.getAttribute("aria-disabled") !== "true") : [];

/** ↑ ↓ (wrapping) Home End between `items`: true when the key was one of them (it is then used up).
    @param {KeyboardEvent} e @param {HTMLElement[]} items @returns {boolean} */
export function menuMove(e, items) {
  const L = items, i = L.indexOf(/** @type {HTMLElement} */ (document.activeElement));
  let to = null;
  if (e.key === "ArrowDown") to = L[(i + 1) % L.length];
  else if (e.key === "ArrowUp") to = L[(i < 0 ? 0 : i + L.length - 1) % L.length];
  else if (e.key === "Home") to = L[0];
  else if (e.key === "End") to = L[L.length - 1];
  else return false;
  e.preventDefault(); e.stopPropagation(); to?.focus({ preventScroll: true });
  return true;
}

/* data: {wv: "x"} as data-wv="x" (Tabs uses it too, BL-316) */
export const dataAttrs = /** @param {Record<string, string> | undefined} d */ d =>
  Object.fromEntries(Object.entries(d || {}).map(([k, v]) => [`data-${k}`, v]));

/** The role="menu" box: focus to its first item when it opens, ↑ ↓ Home End, Esc, Tab, a click away. `onKey` sees each key
    first (a key it uses up, with preventDefault, goes no further); in a text field inside the menu ↑ Home End stay the
    field's. `bare` leaves out the dropdown's own classes (a menu with its own look). It stays in the page while `hidden`.
    `autoFocus: false` leaves focus to the caller (one that places the menu first); `boxRef` is the box, for that caller.
    @param {MenuPanelProps} props */
export function MenuPanel({ label, id, cls, bare, style, hidden, anchor, onClose, onKey, autoFocus = true, focusKey, boxRef, children }) {
  const own = useRef(/** @type {HTMLDivElement | null} */ (null)), box = boxRef || own;
  const closeRef = useRef(onClose); closeRef.current = onClose;
  useLayoutEffect(() => {
    if (hidden || !autoFocus) return;
    tipHide(); (menuItemsIn(box.current)[0] || box.current)?.focus({ preventScroll: true });   /* an empty menu: the box itself, so Esc works */
  }, [hidden, focusKey]);
  useEffect(() => {
    if (hidden) return;
    /** @param {Event} e */
    const away = e => { const t = /** @type {Node} */ (e.target);
      if (!box.current?.contains(t) && !(anchor && anchor.contains(t))) closeRef.current("away"); };
    document.addEventListener("pointerdown", away, true); document.addEventListener("click", away, true);   /* a click from a script too */
    return () => { document.removeEventListener("pointerdown", away, true); document.removeEventListener("click", away, true); };
  }, [hidden, anchor]);
  /** @param {KeyboardEvent} e */
  const keys = e => {
    if (onKey) onKey(e);
    if (e.defaultPrevented) return;
    const field = /** @type {Element} */ (e.target).matches("input,textarea,select");
    if (!field && menuMove(e, menuItemsIn(box.current))) return;
    if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); onClose("esc"); }
    else if (e.key === "Tab") onClose("tab");
  };
  return (
    <div class={`${bare ? "" : "ddmenu newmenu on "}${cls || ""}`.trim()} id={id} role="menu" aria-label={label} ref={box}
      tabIndex={-1} hidden={hidden} style={style} onKeyDown={keys}>
      {children}
    </div>
  );
}

/** A menu's items: commands, checkbox items, separators, headings and notes. An item with neither an icon nor a line is its
    plain words.
    @param {{items: MenuItem[], onPick: (it: MenuItem) => void}} props */
function MenuItems({ items, onPick }) {
  return <>{items.map((it, i) => it.sep ? <hr key={`s${i}`} role="separator" />
    : it.head ? <div key={`h${i}`} class="fsec2" role="presentation">{it.head}</div>
    : it.note ? <div key={`n${i}`} class="sub mnote" role="presentation">{it.note}</div> : (
      <button key={it.id} type="button" role={it.checked === undefined ? "menuitem" : it.radio ? "menuitemradio" : "menuitemcheckbox"} tabIndex={-1}
        class={it.cls} data-tip={it.tip} aria-checked={it.checked === undefined ? undefined : it.checked ? "true" : "false"}
        aria-disabled={it.disabled ? "true" : undefined} {...dataAttrs(it.data)} onClick={() => onPick(it)}>
        {it.icon || (it.radio && it.checked) ? <Icon name={it.checked ? "check" : it.icon || "check"} /> : null}
        {it.icon || it.line
          ? <span><b>{it.name}{it.mark ? <span class="last"> · {it.mark}</span> : null}</b>{it.line ? <small>{it.line}</small> : null}</span>
          : <>{it.name}{it.mark ? <span class="last"> · {it.mark}</span> : null}</>}
      </button>
    ))}</>;
}

/** A button that opens a menu of commands. `why` disables it (aria-disabled, the reason as its tooltip, `onBlocked` on a
    click). `data` adds data-* attributes to the button, and an item's `data` to that item. `ariaLabel` names a button whose
    words are a symbol ("…"); `chevron: false` leaves out the ▾ icon; `labelCls` classes the words; `id`, `menuId` and
    `menuCls` give the button and the menu an id and the menu more classes; `hidden` hides the button. `hover`: the hover standard
    (#143, core/hover.js; see the top of this file). An item with `radio` and `checked` is a menuitemradio: ticked
    when current, and picking it closes the menu.
    @param {MenuProps} props */
export function Menu({ label, items, onPick, icon, tip, why, onBlocked, cls, btnCls, menuLabel, left, data, id, ariaLabel,
  chevron = true, labelCls, menuId, menuCls, hidden, hover }) {
  const [open, setOpen] = useState(false);
  const btn = useRef(/** @type {HTMLButtonElement | null} */ (null));
  const back = useRef(false);
  const box = useRef(/** @type {HTMLDivElement | null} */ (null));
  const byPointer = useRef(false);                       // #143: opened by hovering, so focus stays where it was
  const isOpen = useRef(false); isOpen.current = open;   // #143: a late hover timer must not act on a menu already open

  /** @param {MenuClose} how */
  const close = how => { back.current = how === "esc"; if (back.current) btn.current?.focus({ preventScroll: true }); setOpen(false);   /* Esc: focus is back before the list goes, so a bar shown only while focus is inside it (the Notes bar) stays */
    if (hover && menuGroup.current === btn.current) menuGroup.close(); };

  const closeRef = useRef(close); closeRef.current = close;
  const fold = useRef(() => closeRef.current("esc")).current;   /* folded by another menu: focus goes back to its button, so the Notes bar (shown while focus is in it) stays */
  useEffect(() => () => { if (KB_OPEN === fold) KB_OPEN = null; }, []);
  useEffect(() => {
    const b = btn.current; if (!hover || !b) return;
    return hoverAttach(b, { group: menuGroup, focusOpens: false, panel: () => box.current, isOpen: () => isOpen.current,
      open: () => { if (why || isOpen.current) return; if (KB_OPEN && KB_OPEN !== fold) KB_OPEN(); KB_OPEN = null; byPointer.current = true; tipHide(); setOpen(true); }, close: () => setOpen(false) });
  }, [hover, why]);
  useLayoutEffect(() => {          /* #117: a hover menu that would run off the bottom of the window opens upward when there is room above (the AI bar near the window's foot) */
    if (!hover || !open) return;
    const b = btn.current, m = box.current;
    if (!b || !m) return;
    const r = m.getBoundingClientRect(), t = b.getBoundingClientRect();
    if (r.bottom > window.innerHeight - 4 && t.top - 8 > r.height) m.classList.add("up");
  }, [open]);

  useEffect(() => { if (!open && back.current) { back.current = false; btn.current?.focus(); } }, [open]);

  /** @param {MenuItem} it */
  const pick = it => {
    if (it.disabled) return;
    if (it.checked === undefined || it.radio) close("pick");
    onPick(it.id);
  };

  /** @param {KeyboardEvent} e */
  const onBtnKey = e => {
    if (e.key !== "ArrowDown" || why) return;
    if (!open) { e.preventDefault(); byPointer.current = false; if (hover) { if (menuGroup.current && menuGroup.current !== btn.current) menuGroup.close(); if (KB_OPEN && KB_OPEN !== fold) KB_OPEN(); KB_OPEN = fold; menuGroup.release(btn.current); } setOpen(true); }   /* one menu at a time: a neighbour the pointer opened folds */
    else if (byPointer.current) { e.preventDefault(); byPointer.current = false; menuGroup.release(btn.current); menuItemsIn(box.current)[0]?.focus({ preventScroll: true }); }   /* ↓ on a hover-opened menu moves in */
  };

  return (
    <span class={`dd${cls ? " " + cls : ""}`}>
      <button type="button" class={btnCls || "btn"} id={id} ref={btn} hidden={hidden} aria-haspopup="menu"
        aria-expanded={open ? "true" : "false"} aria-label={ariaLabel} aria-disabled={why ? "true" : undefined}
        data-tip={why || tip} {...dataAttrs(data)} onKeyDown={onBtnKey}
        onClick={e => { e.preventDefault(); if (why) { onBlocked && onBlocked(); return; }
          if (hover) menuGroup.release(btn.current);          /* a click is the keyboard's and the mouse's own: no pending hover open, no hover close */
          if (open && byPointer.current) { byPointer.current = false; menuItemsIn(box.current)[0]?.focus({ preventScroll: true }); return; }   /* a click on a hover-opened menu keeps it and moves in */
          byPointer.current = false; if (open) close("pick"); else setOpen(true); }}>
        {icon ? <Icon name={icon} /> : null}<span class={labelCls}>{label}</span>{chevron ? <Icon name="chevdown" cls="nch" /> : null}
      </button>
      {open ? (
        <MenuPanel label={menuLabel || ariaLabel || label} id={menuId} cls={`${left ? "left " : ""}${menuCls || ""}`}
          anchor={btn.current} onClose={close} boxRef={box} autoFocus={!byPointer.current}>
          <MenuItems items={items} onPick={pick} />
        </MenuPanel>
      ) : null}
    </span>
  );
}

/** Mount a Menu into `box`: a building block's own test, and old code that draws a menu's button in its own markup (a
    placeholder it then leaves alone). Rendering again redraws it in place.
    @param {Element} box @param {MenuProps} props */
export function mountMenu(box, props) { render(<Menu {...props} />, box); }

/** Mount a MenuPanel with `items` (and, with `field`, a text field first) into `box`: the fixture for its own test.
    @param {Element} box @param {MenuPanelProps} props @param {MenuItem[]} items @param {boolean} [field] */
export function mountMenuPanel(box, props, items, field) {
  render(<MenuPanel {...props}>{field ? <input type="text" aria-label="Type here" /> : null}<MenuItems items={items} onPick={() => {}} /></MenuPanel>, box);
}

/* ---- openMenu: one menu at a time, opened from a control that is already in the page, or at the pointer ---- */
/** @type {{host: HTMLDivElement, anchor: HTMLElement | null, props: PopMenuProps} | null} */
let POP = null;

/** The open menu, placed under its control (or at the pointer), turned to fit the window.
    @param {{anchor: HTMLElement | null, props: PopMenuProps}} p */
function PopMenu({ anchor, props }) {
  const { label, items, onPick, id, cls, align, at, loading } = props;
  const wrap = useRef(/** @type {HTMLDivElement | null} */ (null));
  useLayoutEffect(() => {
    const el = /** @type {HTMLElement | null} */ (wrap.current?.firstElementChild || null); if (!el) return;
    const w = el.offsetWidth, h = el.offsetHeight;
    const r = at ? { left: at.x, right: at.x, top: at.y, bottom: at.y }
      : anchor && anchor.isConnected ? anchor.getBoundingClientRect() : { left: innerWidth / 2, right: innerWidth / 2, top: innerHeight / 3, bottom: innerHeight / 3 };
    let top = r.bottom + (at ? 0 : 4); if (top + h > innerHeight - 8) top = Math.max(8, r.top - h - 4);
    const left = align === "right" ? r.right - w : r.left;
    el.style.top = `${Math.max(8, Math.min(top, innerHeight - h - 8))}px`;
    el.style.left = `${Math.max(8, Math.min(left, innerWidth - w - 8))}px`;
  });
  /** @param {MenuItem} it */
  const pick = it => {
    if (it.disabled) return;
    if (it.checked === undefined) closeMenu("pick");
    onPick(it.id);
  };
  return (
    <div ref={wrap}>
      <MenuPanel label={label} id={id} cls={`pop${cls ? " " + cls : ""}`} anchor={anchor} onClose={closeMenu} focusKey={loading}>
        {loading ? <div class="msk" aria-hidden="true"><i></i><i></i><i></i></div> : <MenuItems items={items} onPick={pick} />}
      </MenuPanel>
    </div>
  );
}

/** Open a menu from `anchor` (a control already in the page; its aria-expanded follows), or at `props.at`. Called again while
    it is open, it redraws it (a list that has finished loading). One at a time: another one closes it.
    @param {HTMLElement | null} anchor @param {PopMenuProps} props */
export function openMenu(anchor, props) {
  if (POP && POP.anchor !== anchor) closeMenu("away");
  if (!POP) {
    const host = document.createElement("div"); host.className = "pophost"; document.body.appendChild(host);
    POP = { host, anchor, props };
    if (anchor && anchor.hasAttribute("aria-haspopup")) anchor.setAttribute("aria-expanded", "true");
  }
  POP.props = props;
  render(<PopMenu anchor={anchor} props={props} />, POP.host);
}

/** Close the open menu. Esc puts focus back on its control; Tab does too, so Tab then moves on from there.
    @param {MenuClose} [how] */
export function closeMenu(how = "away") {
  const p = POP; if (!p) return;
  POP = null;
  render(null, p.host); p.host.remove();
  const a = p.anchor;
  if (a && a.hasAttribute("aria-haspopup")) a.setAttribute("aria-expanded", "false");
  if ((how === "esc" || how === "tab") && a && a.isConnected) a.focus({ preventScroll: true });
  if (p.props.onClose) p.props.onClose(how);
}

/** Whether a menu is open (from `anchor`, when one is given).
    @param {HTMLElement | null} [anchor] */
export function menuOpenFor(anchor) { return !!POP && (anchor === undefined || POP.anchor === anchor); }
