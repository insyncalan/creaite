// @ts-check
/* Combobox (BL-256, BL-316, dev/COMPONENTS.md §3): type to choose, with suggestions; the people field (a PersonPicker) is one.
   An <input role="combobox"> with aria-expanded, aria-controls and aria-activedescendant: focus stays in the field while ↑ ↓
   move the active suggestion, Enter picks it (⌘/Ctrl+Enter is left to the form, which saves), Esc closes the list and a second
   Esc clears the field; focus in opens the list, a click away closes it. It keeps the old owner field's classes (.combo,
   .combo-list, .copt, .act, .cgrp), so nothing looks different. The suggestions come from `options(q, typed)` (the owner's
   one matcher, ownerMatches, for people); a suggestion may carry a `remove` (its × button, named "Remove …"). `onPick(o)`
   is told the suggestion; the field shows `o.fill` (or `o.label`) unless onPick returns false. Text only through JSX.
   Drawn into a host by `mountCombobox(host, props)`; `closeCombobox()` closes whichever is open, `comboboxOpen()` says. */
import { Fragment, render } from "preact";
import { useEffect, useRef, useState } from "preact/hooks";
import { Icon } from "./Icon.jsx";

/** One suggestion. `head` puts a group heading before it; `sub` is the small words after it; `remove` adds its × (`removeLabel`
    names it). The rest is the owner's, handed back.
    @typedef {{v: string, label: string, sub?: string, head?: string, cls?: string, fill?: string, remove?: () => any,
      removeLabel?: string, [k: string]: any}} ComboOption */
/** @typedef {{id: string, name?: string, value?: string, label?: string, placeholder?: string, empty?: string,
    options: (q: string, typed: boolean) => ComboOption[], onPick: (o: ComboOption) => any, onInput?: (v: string) => void}} ComboboxProps */

/** @type {{close: () => void} | null} */
let OPEN = null;

/** @param {ComboboxProps} props */
export function Combobox({ id, name, value = "", label, placeholder, empty = "Type a name to add it.", options, onPick, onInput }) {
  const [open, setOpen] = useState(false), [typed, setTyped] = useState(false), [act, setAct] = useState(0), [, redraw] = useState(0);
  const field = useRef(/** @type {HTMLInputElement | null} */ (null)), box = useRef(/** @type {HTMLDivElement | null} */ (null));
  const listId = `${id}-list`, q = typed && field.current ? field.current.value.trim() : "";
  const L = open ? options(q, typed) : [];
  const ai = Math.min(act, Math.max(0, L.length - 1));
  const close = () => { setOpen(false); if (OPEN && OPEN.close === close) OPEN = null; };
  const show = () => { if (OPEN && OPEN.close !== close) OPEN.close(); OPEN = { close }; setOpen(true); };
  useEffect(() => { if (field.current && field.current.value !== value) field.current.value = value; }, [value]);
  useEffect(() => {
    if (!open) return;
    /** @param {Event} e */
    const away = e => { if (!box.current?.contains(/** @type {Node} */ (e.target))) close(); };
    document.addEventListener("mousedown", away, true);
    return () => document.removeEventListener("mousedown", away, true);
  }, [open]);
  /** @param {ComboOption} o */
  const pick = async o => { close(); const r = await onPick(o); if (r !== false && field.current) field.current.value = o.fill ?? o.label; };
  /** @param {KeyboardEvent} e */
  const keys = e => {
    if (e.key === "ArrowDown") { e.preventDefault(); if (!open) show(); else setAct(Math.min(ai + 1, L.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setAct(Math.max(ai - 1, 0)); }
    else if (e.key === "Enter" && open && L[ai] && !e.metaKey && !e.ctrlKey) { e.preventDefault(); e.stopPropagation(); pick(L[ai]); }
    else if (e.key === "Escape") {
      e.preventDefault(); e.stopPropagation();
      if (open) close(); else if (field.current) { field.current.value = ""; onInput && onInput(""); }
    }
    else if (e.key === "Tab") close();
  };
  return (
    <div class={`combo${open ? " open" : ""}`} ref={box}>
      <input type="text" id={id} name={name} ref={field} role="combobox" aria-label={label} aria-autocomplete="list"
        aria-expanded={open ? "true" : "false"} aria-controls={listId} aria-activedescendant={open && L[ai] ? `${id}-o${ai}` : undefined}
        placeholder={placeholder} autocomplete="off" onKeyDown={keys}
        onFocus={() => { setTyped(false); setAct(0); show(); }}
        onInput={e => { setTyped(true); setAct(0); if (!open) show(); else redraw(n => n + 1); onInput && onInput(/** @type {HTMLInputElement} */ (e.currentTarget).value); }} />
      <div class="combo-list" id={listId} role="listbox" aria-label={label}>
        {open ? (L.length ? L.map((o, i) => (
          <Fragment key={`${i}:${o.v}`}>
            {o.head ? <div class="cgrp" role="presentation">{o.head}</div> : null}
            <div id={`${id}-o${i}`} role="option" aria-selected={i === ai ? "true" : "false"}
              class={`copt${o.cls ? " " + o.cls : ""}${i === ai ? " act" : ""}`} data-n={o.v}
              onMouseDown={e => { e.preventDefault(); pick(o); }}>
              <span>{o.label}</span>{o.sub ? <small>{o.sub}</small> : null}
              {o.remove ? <button type="button" class="cdel" aria-label={o.removeLabel || `Remove ${o.label}`} tabIndex={-1}
                onMouseDown={e => { e.preventDefault(); e.stopPropagation(); Promise.resolve(o.remove && o.remove()).then(() => redraw(n => n + 1)); }}><Icon name="x" /></button> : null}
            </div>
          </Fragment>
        )) : <div class="copt" role="presentation">{empty}</div>) : null}
      </div>
    </div>
  );
}

/** Draw a Combobox into `host` (old code's form fields, and the block's own test). Drawing again redraws it in place.
    @param {Element} host @param {ComboboxProps} props */
export function mountCombobox(host, props) { render(<Combobox {...props} />, host); }

/** Close whichever combobox list is open (a panel closing). */
export function closeCombobox() { if (OPEN) OPEN.close(); }

/** Whether a combobox list is open. */
export function comboboxOpen() { return !!OPEN; }
