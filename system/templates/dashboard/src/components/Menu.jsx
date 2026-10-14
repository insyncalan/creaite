// @ts-check
/* Menu (BL-256, dev/COMPONENTS.md §3): a list of commands from a button, in the pattern of Work's New decision menu
   (#newMenu: an icon, a bold name and one explaining line). It keeps that menu's classes (.dd, .ddmenu.newmenu), so it
   looks the same wherever it is used.
   Keyboard and names: the button has aria-haspopup="menu" and aria-expanded, and ↓ opens the menu. Inside it, ↑ ↓ Home End
   move, Enter or Space runs an item, and Esc closes it with focus back on the button. Tab or a click away closes it.
   Disabled items are aria-disabled and skipped. An item with `checked` is a menuitemcheckbox: picking it toggles it and the
   menu stays open. */
import { render } from "preact";
import { useEffect, useRef, useState } from "preact/hooks";
import { Icon } from "./Icon.jsx";

/** @typedef {{id: string, name?: string, line?: string, icon?: string, mark?: string, checked?: boolean, sep?: boolean,
    disabled?: boolean, data?: Record<string, string>}} MenuItem */
/** @typedef {{label: string, items: MenuItem[], onPick: (id: string) => void, icon?: string, tip?: string, why?: string,
    onBlocked?: () => void, cls?: string, btnCls?: string, menuLabel?: string, left?: boolean,
    data?: Record<string, string>}} MenuProps */

/** The items a key can move between: every item that isn't disabled.
    @param {HTMLElement | null} box @returns {HTMLElement[]} */
const usable = box => box ? /** @type {HTMLElement[]} */ ([...box.querySelectorAll("[role^=menuitem]")])
  .filter(b => b.getAttribute("aria-disabled") !== "true") : [];

/** A button that opens a menu of commands. `why` disables it (aria-disabled, the reason as its tooltip, `onBlocked` on a
    click). `data` adds data-* attributes to the button, and an item's `data` to that item.
    @param {MenuProps} props */
export function Menu({ label, items, onPick, icon, tip, why, onBlocked, cls, btnCls, menuLabel, left, data }) {
  const [open, setOpen] = useState(false);
  const wrap = useRef(/** @type {HTMLSpanElement | null} */ (null));
  const btn = useRef(/** @type {HTMLButtonElement | null} */ (null));
  const box = useRef(/** @type {HTMLDivElement | null} */ (null));
  const back = useRef(false);

  /** @param {boolean} focusBack */
  const close = focusBack => { back.current = focusBack; setOpen(false); };

  useEffect(() => {
    if (!open) { if (back.current) { back.current = false; btn.current?.focus(); } return; }
    usable(box.current)[0]?.focus();
    /** @param {Event} e */
    const away = e => { if (wrap.current && !wrap.current.contains(/** @type {Node} */ (e.target))) close(false); };
    document.addEventListener("pointerdown", away, true);
    return () => document.removeEventListener("pointerdown", away, true);
  }, [open]);

  /** @param {MenuItem} it */
  const pick = it => {
    if (it.disabled) return;
    if (it.checked === undefined) close(false);
    onPick(it.id);
  };

  /** @param {KeyboardEvent} e */
  const onMenuKey = e => {
    const L = usable(box.current), i = L.indexOf(/** @type {HTMLElement} */ (document.activeElement));
    if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); L[(i + (e.key === "ArrowDown" ? 1 : L.length - 1)) % L.length]?.focus(); }
    else if (e.key === "Home" || e.key === "End") { e.preventDefault(); L[e.key === "Home" ? 0 : L.length - 1]?.focus(); }
    else if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); close(true); }
    else if (e.key === "Tab") close(false);
  };

  /** @param {KeyboardEvent} e */
  const onBtnKey = e => { if (e.key === "ArrowDown" && !why && !open) { e.preventDefault(); setOpen(true); } };

  const dataAttrs = /** @param {Record<string, string> | undefined} d */ d =>
    Object.fromEntries(Object.entries(d || {}).map(([k, v]) => [`data-${k}`, v]));

  return (
    <span class={`dd${cls ? " " + cls : ""}`} ref={wrap}>
      <button type="button" class={btnCls || "btn"} ref={btn} aria-haspopup="menu" aria-expanded={open ? "true" : "false"}
        aria-disabled={why ? "true" : undefined} data-tip={why || tip} {...dataAttrs(data)} onKeyDown={onBtnKey}
        onClick={e => { e.preventDefault(); if (why) { onBlocked && onBlocked(); return; } setOpen(!open); }}>
        {icon ? <Icon name={icon} /> : null}<span>{label}</span><Icon name="chevdown" cls="nch" />
      </button>
      {open ? (
        <div class={`ddmenu newmenu on${left ? " left" : ""}`} role="menu" aria-label={menuLabel || label} ref={box} onKeyDown={onMenuKey}>
          {items.map((it, i) => it.sep ? <hr key={`s${i}`} role="separator" /> : (
            <button key={it.id} type="button" role={it.checked === undefined ? "menuitem" : "menuitemcheckbox"} tabIndex={-1}
              aria-checked={it.checked === undefined ? undefined : it.checked ? "true" : "false"}
              aria-disabled={it.disabled ? "true" : undefined} {...dataAttrs(it.data)} onClick={() => pick(it)}>
              {it.icon ? <Icon name={it.checked ? "check" : it.icon} /> : null}
              <span><b>{it.name}{it.mark ? <span class="last"> · {it.mark}</span> : null}</b>{it.line ? <small>{it.line}</small> : null}</span>
            </button>
          ))}
        </div>
      ) : null}
    </span>
  );
}

/** Mount a Menu into `box` (a fixture for its own test, dev/tests/test_block_menu.py; screens compose it in JSX).
    @param {Element} box @param {MenuProps} props */
export function mountMenu(box, props) { render(<Menu {...props} />, box); }
