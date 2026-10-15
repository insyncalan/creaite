// @ts-check
/* Picker (BL-256, BL-316, dev/COMPONENTS.md §3): choose one value from a control already in the page (a property chip, a
   project button, a Review row's button). One popup at a time, in three forms, one behaviour:
   - `openPicker(anchor, props)`: a list (role="listbox", or "menu"), with an optional search box first: ↑ ↓ (wrapping; ↑ from the
     first option back to the search) Home End move, Enter picks (in the search: the first option), Esc closes with focus back on
     the control, Tab closes it and moves on from the control; "No match"; "Use “…”" when new values are allowed; `filter(q)` gives
     the list for what is typed (it does its own matching, as the owner list's ownerMatches does);
   - `openDatePicker(anchor, props)`: a month's calendar (role="dialog"): ← → ↑ ↓ move a day or a week (across months), Enter or a
     click picks, the quick days, a typed box (`parse` reads it), Esc closes with focus back; weekend days marked when `weekend` says;
   - `openPopover(anchor, props)`: a small dialog with its own contents (a vnode): focus to `focus` or its first field, Esc closes
     with focus back, Tab out of either end closes it and moves on from the control.
   It keeps the old pickers' classes (.pkpop, .pkopt, .pkq, .pkcal, .pkday …), so nothing looks different. The control's
   aria-expanded follows; a click away and a window resize close it; it sits inside an open dialog when its control does (as the
   calendar does), kept inside the window, above ask creaite. While it is open `shared.PKPOP` is {el, anchor} for code not yet
   moved; `closePicker`, `pickerOpenFor`. `onClose(how)` is told after it closes: return true when the owner has put focus
   somewhere itself (a redraw). Keys other than Esc stop at the popup, so the page's own shortcuts don't run under it.
   Text only through JSX; the one exception is `htmlPopover`, a transitional shim for Review's move preview (an HTML string), to go
   when Review moves (BL-316). */
import { render } from "preact";
import { useLayoutEffect, useRef, useState } from "preact/hooks";
import { putHTML, raw } from "../core/dom.js";
import { fd, TODAY } from "../core/page.js";
import { shared } from "../core/state.js";
import { Icon } from "./Icon.jsx";
import { IconButton } from "./IconButton.jsx";

/** One choice. `icon` an icon's name, or `mark` a drawn mark (a vnode: a status ring, initials); `hint` a line under it;
    `id` the option's id (a popup it opens names it as its way in); the rest (`t`, `typed`, `name` …) is the owner's, handed back.
    @typedef {{v: any, label: string, icon?: string, mark?: any, hint?: string, disabled?: boolean, id?: string, [k: string]: any}} PickerOption */
/** How a picker closed: Esc, Tab, a click away, an option picked, or the owner closing it.
    @typedef {"esc" | "tab" | "away" | "pick" | "owner"} PickerClose */
/** @typedef {{options: PickerOption[], value?: any, onPick: (v: any, typed?: boolean, o?: PickerOption) => any, search?: boolean,
    label?: string, allowNew?: boolean, role?: "listbox" | "menu", filter?: (q: string) => PickerOption[], cls?: string,
    onClose?: (how: PickerClose) => any}} PickerProps */
/** @typedef {{value?: string, label: string, onPick: (iso: string) => any, parse: (text: string) => string | null, error?: string,
    weekend?: (iso: string) => boolean, typedNote?: (text: string) => string, placeholder?: string,
    onClose?: (how: PickerClose) => any}} DatePickerProps */
/** @typedef {{label: string, content?: any, cls?: string, id?: string, role?: string, focus?: string,
    onClose?: (how: PickerClose) => any}} PopoverProps */

/** @type {{host: HTMLDivElement, el: HTMLElement | null, anchor: HTMLElement, onClose?: (how: PickerClose) => any} | null} */
let PICK = null;

/** Place a popup under its control (above it when there is no room), inside the window.
    @param {HTMLElement} el @param {HTMLElement} anchor */
export function placePicker(el, anchor) {
  const r = anchor.getBoundingClientRect(), w = el.offsetWidth, h = el.offsetHeight;
  let x = r.left, y = r.bottom + 4;
  x = Math.max(8, Math.min(x, innerWidth - w - 8));
  if (y + h > innerHeight - 8) y = Math.max(8, r.top - h - 4);
  el.style.left = `${x}px`; el.style.top = `${y}px`;
}

/** The focusable things inside a popup, in order. @param {Element} el @returns {HTMLElement[]} */
const focusables = el => /** @type {HTMLElement[]} */ ([...el.querySelectorAll("button:not([disabled]),input:not([disabled]),select,textarea,[tabindex='0']")])
  .filter(x => x.offsetParent !== null || x === document.activeElement);

/** Tab out of either end of a dialog popup closes it (focus back on the control, so Tab moves on from there).
    @param {KeyboardEvent} e @param {HTMLElement | null} el */
function tabOut(e, el) {
  if (e.key !== "Tab" || !el) return;
  const L = focusables(el), first = L[0], last = L[L.length - 1];
  if ((e.shiftKey && document.activeElement === first) || (!e.shiftKey && document.activeElement === last) || !L.length) closePicker("tab");
}

/** The popup's frame: the .pkpop box, placed after every draw; keys other than Esc stop here.
    @param {{cls?: string, role?: string, label?: string, id?: string, anchor: HTMLElement, onKey?: (e: KeyboardEvent) => void,
      boxRef: {current: HTMLDivElement | null}, children?: any}} props */
function Frame({ cls, role, label, id, anchor, onKey, boxRef, children }) {
  useLayoutEffect(() => { if (boxRef.current && anchor.isConnected) placePicker(boxRef.current, anchor); });
  /** @param {KeyboardEvent} e */
  const keys = e => { if (onKey) onKey(e); if (e.key !== "Escape") e.stopPropagation(); };
  return <div class={`pkpop${cls ? " " + cls : ""}`} role={/** @type {any} */ (role || undefined)} aria-label={role ? label : undefined} id={id} ref={boxRef} onKeyDown={keys}>{children}</div>;
}

/** The options a key can move between. @param {Element | null} el @returns {HTMLElement[]} */
const optionsIn = el => el ? /** @type {HTMLElement[]} */ ([...el.querySelectorAll(".pkopt")]).filter(b => b.tagName === "BUTTON" && b.getAttribute("aria-disabled") !== "true") : [];

/** The list. @param {{anchor: HTMLElement, props: PickerProps}} p */
function PickerList({ anchor, props }) {
  const { options, value, onPick, search, label = "", allowNew, role = "listbox", filter, cls } = props;
  const [q, setQ] = useState("");
  const box = useRef(/** @type {HTMLDivElement | null} */ (null)), field = useRef(/** @type {HTMLInputElement | null} */ (null));
  const item = role === "menu" ? "menuitem" : "option", t = q.trim().toLowerCase();
  const cur = filter ? filter(q.trim()) : options;
  const shown = cur.map((o, i) => /** @type {[PickerOption, number]} */ ([o, i])).filter(([o]) => filter || !t || o.label.toLowerCase().includes(t));
  const useNew = !!(allowNew && !filter && t && !options.some(o => o.label.toLowerCase() === t));
  useLayoutEffect(() => {
    const el = box.current; if (!el) return;
    if (field.current) { field.current.focus(); return; }
    (/** @type {HTMLElement | null} */ (el.querySelector('.pkopt[aria-selected="true"]:not([aria-disabled="true"])')) || optionsIn(el)[0])?.focus();
  }, []);
  /** @param {PickerOption} o */
  const pick = o => { if (o.disabled) return; closePicker("pick"); onPick(o.v, false, o); };
  const pickNew = () => { const typed = q.trim(); closePicker("pick"); onPick(typed, true); };
  /** @param {KeyboardEvent} e */
  const keys = e => {
    const L = optionsIn(box.current), i = L.indexOf(/** @type {HTMLElement} */ (document.activeElement));
    if (e.key === "ArrowDown") { e.preventDefault(); (L[i + 1] || L[0])?.focus(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); (i <= 0 && field.current ? field.current : L[i - 1] || L[L.length - 1])?.focus(); }
    else if (e.key === "Home" && i >= 0) { e.preventDefault(); L[0]?.focus(); }
    else if (e.key === "End" && i >= 0) { e.preventDefault(); L[L.length - 1]?.focus(); }
    else if (e.key === "Enter" && e.target === field.current && !e.metaKey && !e.ctrlKey) { e.preventDefault(); L[0]?.click(); }
    else if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); closePicker("esc"); }
    else if (e.key === "Tab") closePicker("tab");
  };
  return (
    <Frame cls={cls} anchor={anchor} boxRef={box} onKey={keys}>
      {search ? <input class="pkq" type="search" placeholder="Search" aria-label={`Search: ${label}`} autocomplete="off" ref={field}
        value={q} onInput={e => setQ(/** @type {HTMLInputElement} */ (e.currentTarget).value)} /> : null}
      <div role={role} aria-label={label}>
        {shown.length || useNew ? <>
          {shown.map(([o, i]) => (
            <button key={`${i}:${o.v}`} type="button" class="pkopt" role={item} data-i={String(i)} id={o.id}
              aria-selected={role === "listbox" ? (o.v === value ? "true" : "false") : undefined} aria-disabled={o.disabled ? "true" : undefined}
              onClick={() => pick(o)}>
              {o.mark ? o.mark : o.icon && !o.icon.includes("<") ? <Icon name={o.icon} /> : null}
              <span>{o.label}{o.hint ? <span class="h">{o.hint}</span> : null}</span>
              {role === "listbox" && o.v === value ? <Icon name="check" cls="ck" /> : null}
            </button>
          ))}
          {useNew ? <button type="button" class="pkopt" role={item} data-new="1" onClick={pickNew}><Icon name="plus" /><span>Use “{q.trim()}”</span></button> : null}
        </> : <div class="pkopt" aria-disabled="true">No match</div>}
      </div>
    </Frame>
  );
}

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const DOW = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];
/** @param {string} iso @param {number} n @returns {string} */
const calAdd = (iso, n) => { const d = new Date(iso + "T00:00:00Z"); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };
/** Monday 0 … Sunday 6. @param {string} iso */
const dow = iso => (new Date(iso + "T00:00:00Z").getUTCDay() + 6) % 7;
/** @param {number} y @param {number} m @param {number} d */
const isoOf = (y, m, d) => `${y}-${String(m + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;

/** The calendar. @param {{anchor: HTMLElement, props: DatePickerProps}} p */
function DateCalendar({ anchor, props }) {
  const { value = "", label, onPick, parse, error, weekend, typedNote, placeholder } = props;
  const base = value || TODAY;
  const [ym, setYm] = useState(/** @type {[number, number]} */ ([+base.slice(0, 4), +base.slice(5, 7) - 1]));
  const [focusIso, setFocusIso] = useState(/** @type {string | null} */ (value || TODAY));
  const [bad, setBad] = useState(false), [note, setNote] = useState("");
  const box = useRef(/** @type {HTMLDivElement | null} */ (null)), typed = useRef(/** @type {HTMLInputElement | null} */ (null));
  useLayoutEffect(() => { if (typed.current) typed.current.value = fd(value || ""); }, []);   /* the typed box is the person's once drawn */
  const [y, m] = ym, lead = (new Date(Date.UTC(y, m, 1)).getUTCDay() + 6) % 7, n = new Date(Date.UTC(y, m + 1, 0)).getUTCDate();
  const days = Array.from({ length: n }, (_, i) => isoOf(y, m, i + 1));
  const tabDay = days.find(d => d === focusIso) || days.find(d => d === value) || days.find(d => d === TODAY) || days[0];
  useLayoutEffect(() => {
    if (focusIso === null || !box.current) return;
    /** @type {HTMLElement | null} */ (box.current.querySelector(`.pkday[data-d="${tabDay}"]`))?.focus();
  }, [focusIso, ym]);
  /** @param {string} iso */
  const pick = iso => { closePicker("pick"); onPick(iso); };
  /** @param {number} by */
  const month = by => { let mm = m + by, yy = y; if (mm < 0) { mm = 11; yy--; } if (mm > 11) { mm = 0; yy++; } setFocusIso(null); setYm([yy, mm]); };
  /** @param {KeyboardEvent} e */
  const keys = e => {
    const tg = /** @type {HTMLElement} */ (e.target);
    if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); closePicker("esc"); return; }
    if (tg.matches(".pkday") && ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.key)) {
      e.preventDefault();
      const to = calAdd(tg.dataset.d || TODAY, /** @type {Record<string, number>} */ ({ ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 })[e.key]);
      setYm([+to.slice(0, 4), +to.slice(5, 7) - 1]); setFocusIso(to); return;
    }
    if (e.key === "Enter" && tg.matches(".pkdt") && !e.metaKey && !e.ctrlKey) {
      e.preventDefault(); const t = /** @type {HTMLInputElement} */ (tg).value.trim();
      if (!t) { pick(""); return; }
      const iso = parse(t); if (iso) pick(iso); else setBad(true);
      return;
    }
    tabOut(e, box.current);
  };
  const nextMonday = calAdd(TODAY, 7 - dow(TODAY));
  const quick = /** @type {[string, string][]} */ ([["Today", TODAY], ["Tomorrow", calAdd(TODAY, 1)], ["Next Monday", nextMonday], ["In a week", calAdd(TODAY, 7)], ["Clear", ""]]);
  return (
    <Frame cls="pkcal" role="dialog" label={label} anchor={anchor} boxRef={box} onKey={keys}>
      <div class="pkcalh">
        <IconButton icon="chevleft" label="Previous month" sm={false} data={{ m: "-1" }} onClick={() => month(-1)} />
        <b aria-live="polite">{MONTHS[m]} {y}</b>
        <IconButton icon="chevright" label="Next month" sm={false} data={{ m: "1" }} onClick={() => month(1)} />
      </div>
      <div class="pkgrid" role="group" aria-label={label}>
        {DOW.map(w => <span key={w} class="wd" aria-hidden="true">{w}</span>)}
        {Array.from({ length: lead }, (_, i) => <span key={`l${i}`}></span>)}
        {days.map(iso => { const we = !!(weekend && weekend(iso)); return (
          <button key={iso} type="button" class={`pkday${iso === TODAY ? " today" : ""}${iso === value ? " on" : ""}${we ? " wkend" : ""}`} data-d={iso}
            aria-label={`${fd(iso)}${we ? ", weekend" : ""}`} aria-pressed={iso === value ? "true" : undefined} tabIndex={iso === tabDay ? 0 : -1}
            onClick={() => pick(iso)}>{+iso.slice(8)}</button>
        ); })}
      </div>
      <div class="pkquick">{quick.map(([w, d]) => <button key={w} type="button" class="mini" data-d={d} onClick={() => pick(d)}>{w}</button>)}</div>
      <input class={`pkdt${bad ? " bad" : ""}`} type="text" ref={typed} placeholder={placeholder || "DD-MM-YYYY, or words like fri or +3d"}
        aria-label={`${label}, typed`} aria-invalid={bad ? "true" : undefined} autocomplete="off"
        onInput={e => { setBad(false); if (typedNote) setNote(typedNote(/** @type {HTMLInputElement} */ (e.currentTarget).value.trim())); }} />
      <div class="pkerr" role="alert">{bad ? error || "Use DD-MM-YYYY, for example 14-10-2026, or words like fri or +3d." : ""}</div>
      {note ? <div class="wkline" role="status" aria-live="polite">{note}</div> : null}
    </Frame>
  );
}

/** A small dialog with its own contents. @param {{anchor: HTMLElement, props: PopoverProps}} p */
function Popover({ anchor, props }) {
  const { label, content, cls, id, role = "dialog", focus } = props;
  const box = useRef(/** @type {HTMLDivElement | null} */ (null));
  useLayoutEffect(() => {
    const el = box.current; if (!el || !content) return;
    const f = /** @type {HTMLElement | null} */ (focus ? el.querySelector(focus) : focusables(el)[0] || null);
    if (f) { f.focus(); if (f instanceof HTMLInputElement) f.select(); }
  }, []);
  /** @param {KeyboardEvent} e */
  const keys = e => { if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); closePicker("esc"); return; } tabOut(e, box.current); };
  return <Frame cls={cls} role={role} label={label} id={id} anchor={anchor} boxRef={box} onKey={keys}>{content}</Frame>;
}

/** Open one of the three in a host at the end of the page (or of the open dialog the control is in).
    @param {HTMLElement} anchor @param {any} vnode @param {((how: PickerClose) => any) | undefined} onClose @returns {HTMLElement} */
function popupMount(anchor, vnode, onClose) {
  closePicker("owner", false);
  bootPicker();
  const host = document.createElement("div"); host.className = "pophost";
  (anchor.closest("dialog[open]") || document.body).appendChild(host);
  PICK = { host, el: null, anchor, onClose };
  if (anchor.hasAttribute("aria-haspopup")) anchor.setAttribute("aria-expanded", "true");
  render(vnode, host);
  PICK.el = /** @type {HTMLElement} */ (host.firstElementChild);
  shared.PKPOP = { el: PICK.el, anchor };
  return PICK.el;
}

/** Open a list from `anchor`. Returns the popup (.pkpop).
    @param {HTMLElement} anchor @param {PickerProps} props @returns {HTMLElement} */
export function openPicker(anchor, props) { return popupMount(anchor, <PickerList anchor={anchor} props={props} />, props.onClose); }

/** Open a calendar from `anchor`. Returns the popup (.pkpop.pkcal).
    @param {HTMLElement} anchor @param {DatePickerProps} props @returns {HTMLElement} */
export function openDatePicker(anchor, props) { return popupMount(anchor, <DateCalendar anchor={anchor} props={props} />, props.onClose); }

/** Open a small dialog from `anchor`; without `content` it is an empty box the caller fills. Returns the popup (.pkpop).
    @param {HTMLElement} anchor @param {PopoverProps} props @returns {HTMLElement} */
export function openPopover(anchor, props) { return popupMount(anchor, <Popover anchor={anchor} props={props} />, props.onClose); }

/** Close the open picker. Focus goes back to its control (unless `how` is a click away, or `focus` is false, or the owner's
    onClose put it somewhere itself); after Tab it is on the control, so Tab moves on from there.
    @param {PickerClose} [how] @param {boolean} [focus] */
export function closePicker(how = "owner", focus = true) {
  const p = PICK; if (!p) return;
  PICK = null; shared.PKPOP = null;
  render(null, p.host); p.host.remove();
  const a = p.anchor;
  if (a.hasAttribute("aria-haspopup")) a.setAttribute("aria-expanded", "false");
  const done = p.onClose ? p.onClose(how) : false;
  if (!done && focus && how !== "away" && a.isConnected) a.focus({ preventScroll: true });
}

/** Whether a picker is open (from `anchor`, when one is given). @param {HTMLElement | null} [anchor] */
export function pickerOpenFor(anchor) { return !!PICK && (anchor === undefined || PICK.anchor === anchor); }

/* a click away (not on the control, which toggles it itself) and a resize close it; installed once */
let BOOTED = false;
function bootPicker() {
  if (BOOTED) return; BOOTED = true;
  document.addEventListener("mousedown", e => {
    const t = /** @type {Node} */ (e.target);
    if (PICK && !(PICK.el && PICK.el.contains(t)) && !PICK.anchor.contains(t)) closePicker("away");
  }, true);
  addEventListener("resize", () => closePicker("away"));
}

/* ---- transitional (BL-316): a popover filled with an HTML string, for Review's move preview until Review moves; new code
   passes `content` to openPopover ---- */
/** @param {HTMLElement} anchor @param {string} cls @param {string} htmlText @returns {HTMLElement} */
export function htmlPopover(anchor, cls, htmlText) {
  const el = openPopover(anchor, { label: "", cls, role: "" });
  putHTML(el, raw(htmlText)); placePicker(el, anchor);
  return el;
}
