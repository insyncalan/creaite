// @ts-check
/* FilterBar (BL-256, BL-316, dev/COMPONENTS.md §3): the row of filters over a list (Work's, Review's) and the funnel's field
   picker (+ Filter; Settings › People's funnel is the picker alone). The area gives the fields and keeps the state: what is
   chosen, "is not", the date ranges, the picker's field, its counts and its words; the bar only draws them and says what
   changed (onSelect, onNot, onRange, more.onField, more.onQuery), and the area redraws it with drawFilterBar. It keeps the
   classes the bars had (.wfilters host, .dd, .fbtn, .ddmenu, .fpmenu, .fpick, .fplist, .fpf, .fpr, .fpopts, .isnot, .seg,
   .fcount, .mq, .acts), so the screens look the same.
   - A main field is a button of its own (aria-haspopup="listbox", aria-expanded, its label saying what is chosen) with a
     multi-select list: "is / is not", a search when there are over six options, Only me (when the area gives its values),
     Select all (what the search shows), Clear, and the options with their counts (role="option", aria-selected; a dim one
     matches nothing now). Enter or a click opens it, ↓ too; focus goes to the search or the first option; ↑ ↓ move (from the
     search ↓ goes to the options; ↑ climbs to Clear, Select all, the search and the is / is not), Home End go to the first
     and last option; Space or Enter ticks; Esc closes with focus back on the button; Tab closes; a click away closes.
   - The funnel (aria-haspopup="dialog", aria-expanded) opens the field picker: every field, the main ones first, with a
     section's heading where it changes; ↑ ↓ Home End move between fields and show each; → or Enter goes into its options,
     ← comes back; a date-range field is two date boxes; Done or Esc closes it with focus back on the funnel; a click or focus
     away closes it.
   - BL-150: the bar never wraps. With `fold`, the unused main filters fold away from the end (never the first, never one
     that is set) while the row the area names would wrap; the picker still lists them and the funnel says how many it holds.
   The open state lives with the host (it survives the area redrawing the bar); a list just closed keeps its contents, hidden,
   until the area next redraws the bar, as the hand-made menus did. Text only through JSX. */
import { Fragment, render } from "preact";
import { Icon } from "./Icon.jsx";
import { dataAttrs } from "./Menu.jsx";

/** @typedef {{value: string, label: string, count?: number, extra?: string}} FilterOption
    `extra`: quiet words after the label ("default"). */
/** @typedef {{from: string, to: string, name: string}} FilterRange
    A date-range field: the two boxes' text (DD-MM-YYYY) and the name their labels start with ("Due" makes "Due from"). */
/** @typedef {{id: string, label: string, main?: boolean, button?: string, btnId?: string, menuId?: string,
    data?: Record<string, string>, on?: boolean, options?: () => FilterOption[], selected?: Iterable<string>, not?: boolean,
    onlyMe?: string[], single?: boolean, range?: FilterRange, section?: string, note?: string, mark?: string}} FilterField
    `main`: a button of its own on the bar (else only in the funnel's picker); `button` its words; `on` it is set (the button
    and the picker's field are marked); `options` are read only when shown; `not` is "is not" (left out: no is / is not);
    `onlyMe` the values Only me chooses (left out: no Only me); `single`: one choice (radio boxes); `section` the picker's
    heading above it; `note` a line under its heading in the picker; `mark` the picker's note beside it ("set", "not · 2"). */
/** @typedef {{id: string, menuId: string, label: string, menuLabel: string, count?: number, on?: boolean, key?: string,
    listLabel?: string, field: string, onField: (id: string) => void, query?: string, onQuery?: (q: string) => void,
    onOpen?: () => void, result: string, resultId: string, doneId: string, headId?: string,
    clearAll?: {id: string, run: () => void} | null}} FilterMore
    The funnel: its button's id and words (`label`, its tooltip too), the picker's id and name, the count on its badge,
    `key` its shortcut (data-key); `field` the picker's field and `onField` choosing one; `query`/`onQuery` the picker's
    "Find a field…" box (left out: no box); `onOpen` runs as it opens (the area may choose the field); the footer's result
    words and ids, and a Clear all. */
/** @typedef {{fields: FilterField[], onSelect: (id: string, values: string[]) => void, onNot?: (id: string, not: boolean) => void,
    onRange?: (id: string, end: "from" | "to", text: string) => void, more?: FilterMore | null, bare?: boolean,
    fold?: () => Element | null | false}} FilterBarProps
    `bare`: the host is the funnel's own .dd (a bar with no main fields; Settings › People). `fold` (BL-150) gives the row
    that must stay on one line (null: fold nothing; false: leave the folding as it is, the row isn't shown). */
/** @typedef {{open: string | null, keep: string | null, q: Record<string, string>, fold: string[]}} FilterUi */
/** @typedef {{props: FilterBarProps, ui: FilterUi, host: Element}} FilterBarState */

/** @type {WeakMap<Element, FilterBarState>} */
const FB_BARS = new WeakMap();
/** @type {Set<FilterBarState>} the bars with something open (for a click or focus away) */
const FB_OPEN = new Set();
const FB_MORE = "+more";

/** @param {FilterField} f */
const fbBtnId = f => f.btnId;
/** @param {FilterField} f */
const fbMenuId = f => f.menuId || `${f.id}Menu`;
/** @param {FilterBarProps} p */
const fbMain = p => p.fields.filter(f => f.main);
/** @param {FilterBarProps} p the picker's fields: the main ones first, then the rest, each in the area's order */
const fbPickList = p => [...p.fields.filter(f => f.main), ...p.fields.filter(f => !f.main)];

/** @param {Element} host @returns {FilterBarState} */
function fbState(host) {
  let s = FB_BARS.get(host);
  if (!s) {
    s = { props: { fields: [], onSelect: () => {} }, ui: { open: null, keep: null, q: {}, fold: [] }, host };
    FB_BARS.set(host, s);
  }
  return s;
}

/** Draw (or redraw) the bar into `host` with the area's current state. A list or the picker that is open stays open.
    @param {Element} host @param {FilterBarProps} props */
export function drawFilterBar(host, props) {
  const s = fbState(host);
  s.props = props;
  if (!s.ui.open) s.ui.keep = null;
  fbPaint(s);
  fbFit(s);
}

/** What is open in the bar in `host`: a main field's id, "more" for the funnel's picker, or null.
    @param {Element | null} host */
export function filterBarOpen(host) {
  const s = host && FB_BARS.get(host), o = s && s.ui.open;
  return o === FB_MORE ? "more" : o || null;
}

/** Open a main field's list (`which` its id) or the funnel's picker ("more") from outside (a chip, a key); focus goes into it.
    @param {Element | null} host @param {string} which */
export function openFilterBar(host, which) {
  const s = host && FB_BARS.get(host); if (!s) return;
  fbOpen(s, which === "more" ? FB_MORE : which);
}

/** Close what is open; `back` puts focus on its button.
    @param {Element | null} host @param {boolean} [back] */
export function closeFilterBar(host, back) {
  const s = host && FB_BARS.get(host); if (s) fbClose(s, !!back);
}

/** Fold the bar again for the room it has now (the area's resize observer).
    @param {Element | null} host */
export function fitFilterBar(host) {
  const s = host && FB_BARS.get(host); if (s) fbFit(s);
}

/** @param {FilterBarState} s */
function fbPaint(s) { render(<FilterBar {...s.props} ui={s.ui} host={s.host} />, s.host); fbPlace(s); }

/* #240: the funnel's picker is drawn position:fixed, so a short page that scrolls (Work's .view, overflow:auto) never cuts it
   off. It starts where it would sit in its .dd (each bar's own left or right alignment; offsets, so the opening animation's
   transform is left out), is kept inside the window, and its height is what the window has room for (it scrolls inside);
   with little room below and more above, it opens upward. Placed again on every redraw, scroll and resize. */
const FB_GAP = 8;
/** @param {FilterBarState} s */
function fbPlace(s) {
  const m = s.props.more && document.getElementById(s.props.more.menuId); if (!m || !s.host.contains(m)) return;
  const st = m.style;
  st.position = st.top = st.left = st.right = st.bottom = st.maxHeight = "";
  if (s.ui.open !== FB_MORE || !m.classList.contains("on")) return;
  const dd = /** @type {HTMLElement} */ (m.parentElement), d = dd.getBoundingClientRect();
  const vw = document.documentElement.clientWidth, vh = document.documentElement.clientHeight;
  const w = m.offsetWidth, cap = parseFloat(getComputedStyle(m).maxHeight) || vh;
  let top = d.top + m.offsetTop, room = vh - FB_GAP - top;
  const above = d.top - FB_GAP - (top - d.bottom);
  if (room < Math.min(cap, m.scrollHeight) && above > room) { room = above; top = Math.max(FB_GAP, d.top - (top - d.bottom) - Math.min(cap, room, m.scrollHeight)); }
  const left = Math.max(FB_GAP, Math.min(d.left + m.offsetLeft, vw - FB_GAP - w));
  Object.assign(st, { position: "fixed", top: `${Math.round(top)}px`, left: `${Math.round(left)}px`, right: "auto", bottom: "auto",
    maxHeight: `${Math.max(0, Math.floor(Math.min(cap, room)))}px` });
}

/** The .dd of field `id` (or of the funnel) in the bar.
    @param {FilterBarState} s @param {string} id @returns {HTMLElement | null} */
function fbDd(s, id) {
  const f = id === FB_MORE ? null : s.props.fields.find(x => x.id === id);
  const mid = id === FB_MORE ? s.props.more?.menuId : f && fbMenuId(f);
  const m = mid ? document.getElementById(mid) : null;
  return m && s.host.contains(m) ? /** @type {HTMLElement} */ (m.parentElement) : null;
}
/** @param {FilterBarState} s @param {string} id */
const fbBtn = (s, id) => /** @type {HTMLElement | null} */ (fbDd(s, id)?.querySelector(":scope>button") || null);
/** @param {FilterBarState} s @param {string} id */
const fbMenu = (s, id) => /** @type {HTMLElement | null} */ (fbDd(s, id)?.querySelector(":scope>.ddmenu") || null);

/** @param {FilterBarState} s @param {string} id */
function fbOpen(s, id) {
  if (s.ui.open && s.ui.open !== id) fbClose(s, false);
  s.ui.open = id; s.ui.keep = null;
  if (id === FB_MORE) s.props.more?.onOpen?.(); else s.ui.q[id] = "";
  FB_OPEN.add(s);
  fbPaint(s);
  const m = fbMenu(s, id); if (!m) return;
  /** @type {HTMLElement | null} */
  const to = id === FB_MORE
    ? m.querySelector(".fpl input[type=search]") || fbFirstIn(m.querySelector(".fpr")) || m.querySelector('.fpf[aria-selected="true"]')
    : m.querySelector("input.mq") || m.querySelector('[role="option"]') || m;
  to?.focus({ preventScroll: true });
}

/** @param {FilterBarState} s @param {boolean} back */
function fbClose(s, back) {
  const was = s.ui.open; if (!was) return;
  s.ui.open = null; s.ui.keep = was; FB_OPEN.delete(s);
  fbPaint(s);
  if (back) fbBtn(s, was)?.focus({ preventScroll: true });
}

/** The first thing to focus in the picker's right side: is / is not, else an option, else a date box.
    @param {Element | null} box @returns {HTMLElement | null} */
const fbFirstIn = box => box ? /** @type {HTMLElement | null} */ (box.querySelector('[role="option"]') || box.querySelector(".seg button")
  || box.querySelector(".drange input")) : null;

/* a click or focus away closes what is open (the funnel's picker and the lists alike) */
/** @param {Event} e */
function fbAway(e) {
  const t = /** @type {Node} */ (e.target);
  [...FB_OPEN].forEach(s => { const dd = s.ui.open && fbDd(s, s.ui.open);
    if (!s.host.isConnected) { FB_OPEN.delete(s); return; }
    if (dd && !dd.contains(t)) fbClose(s, false); });
}
if (typeof document !== "undefined") {
  document.addEventListener("pointerdown", fbAway, true);
  document.addEventListener("click", fbAway, true);     /* a click from a script too */
  document.addEventListener("focusin", fbAway);
  /** @param {Event} e */
  const replace = e => FB_OPEN.forEach(s => { const m = s.props.more && document.getElementById(s.props.more.menuId);
    if (s.ui.open === FB_MORE && !(m && e.target instanceof Node && m.contains(e.target))) fbPlace(s); });   /* not the picker's own lists scrolling */
  window.addEventListener("resize", replace);
  document.addEventListener("scroll", replace, { capture: true, passive: true });   /* any scroller: the page or a view */
}

/* ---- BL-150: folding ---- */
/** @param {FilterBarState} s */
function fbFit(s) {
  const fold = s.props.fold; if (!fold) return;
  const bar = fold(); if (bar === false) return;
  const main = fbMain(s.props), dds = /** @type {HTMLElement[]} */ ([...s.host.querySelectorAll(":scope>.dd:not(:has(>.fpmenu))")]);
  dds.forEach(d => d.classList.remove("wfold"));
  /** @type {string[]} */
  const folded = [];
  if (bar) {
    const first = /** @type {HTMLElement} */ (bar.firstElementChild);
    const wrapped = () => [...bar.children, ...dds].some(c => { const h = /** @type {HTMLElement} */ (c);
      return h.offsetParent && h.offsetWidth && h.offsetHeight > 8 && h.offsetTop > first.offsetTop + 8; });
    const can = dds.map((d, i) => [d, main[i]]).filter(([d, f], i) => i > 0 && f && !/** @type {FilterField} */ (f).on).reverse();
    for (const [d, f] of can) { if (!wrapped()) break; /** @type {HTMLElement} */ (d).classList.add("wfold"); folded.push(/** @type {FilterField} */ (f).id); }
  }
  if (folded.join("|") !== s.ui.fold.join("|")) { s.ui.fold = folded; fbPaint(s); }
}

/* ---- the keys ---- */
/** Move focus within `list` by ↑ ↓ (no wrap) or to `ends`' first and last by Home End: true when the key was used.
    @param {KeyboardEvent} e @param {HTMLElement[]} list @param {HTMLElement[]} ends */
function fbStep(e, list, ends) {
  const i = list.indexOf(/** @type {HTMLElement} */ (document.activeElement));
  let to = null;
  if (e.key === "ArrowDown") to = list[Math.min(list.length - 1, i + 1)];
  else if (e.key === "ArrowUp") to = list[Math.max(0, i - 1)];
  else if (e.key === "Home") to = ends[0];
  else if (e.key === "End") to = ends[ends.length - 1];
  else return false;
  e.preventDefault(); e.stopPropagation();
  to?.focus({ preventScroll: true });
  return true;
}
/** @param {Element | null} box @returns {HTMLElement[]} */
const fbOpts = box => box ? /** @type {HTMLElement[]} */ ([...box.querySelectorAll('[role="option"]')]) : [];

/** A main field's list: its keys.
    @param {FilterBarState} s @param {FilterField} f @param {KeyboardEvent} e */
function fbListKeys(s, f, e) {
  const m = fbMenu(s, f.id); if (!m) return;
  const t = /** @type {HTMLElement} */ (e.target), opts = fbOpts(m);
  if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); fbClose(s, true); return; }
  if (e.key === "Tab") { fbClose(s, false); fbBtn(s, f.id)?.focus({ preventScroll: true }); return; }   /* Tab then moves on from the button */
  if (t.matches("input.mq")) {
    if (e.key === "ArrowDown" && opts.length) { e.preventDefault(); opts[0].focus({ preventScroll: true }); }
    else if (e.key === "ArrowUp") fbStep(e, fbControls(m), opts);
    return;
  }
  if ((e.key === " " || e.key === "Enter") && t.getAttribute("role") === "option") { e.preventDefault(); e.stopPropagation(); fbTick(s, f, t); return; }
  fbStep(e, fbControls(m), opts);
}
/** Everything in a list that takes focus, in order: is / is not, the search, Only me, Select all, Clear, the options.
    @param {Element} m @returns {HTMLElement[]} */
const fbControls = m => /** @type {HTMLElement[]} */ ([...m.querySelectorAll('.seg button,input.mq,.acts button,[role="option"]')]);

/** The funnel's picker: its keys.
    @param {FilterBarState} s @param {KeyboardEvent} e */
function fbPickKeys(s, e) {
  const m = fbMenu(s, FB_MORE), more = s.props.more; if (!m || !more) return;
  const t = /** @type {HTMLElement} */ (e.target), right = m.querySelector(".fpr");
  const fieldBtn = () => /** @type {HTMLElement | null} */ (m.querySelector('.fpf[aria-selected="true"]'));
  if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); fbClose(s, true); return; }
  if (t.matches(".fpl input[type=search]")) {
    if (e.key === "Enter") { e.preventDefault(); (fbFirstIn(right) || fieldBtn())?.focus(); }
    else if (e.key === "ArrowDown") { e.preventDefault(); fieldBtn()?.focus(); }
    return;
  }
  if (t.matches(".fpf")) {
    const L = /** @type {HTMLElement[]} */ ([...m.querySelectorAll(".fpf")]), i = L.indexOf(t);
    const j = e.key === "ArrowDown" ? Math.min(L.length - 1, i + 1) : e.key === "ArrowUp" ? Math.max(0, i - 1)
      : e.key === "Home" ? 0 : e.key === "End" ? L.length - 1 : -1;
    if (j >= 0) { e.preventDefault(); const k = L[j].dataset.fpk || ""; if (k !== more.field) more.onField(k);
      /** @type {HTMLElement | null} */ (m.querySelector(`.fpf[data-fpk="${CSS.escape(k)}"]`))?.focus(); return; }
    if (e.key === "ArrowRight" || e.key === "Enter") { e.preventDefault(); fbFirstIn(right)?.focus(); }
    return;
  }
  if (!right || !right.contains(t) || t.matches(".drange input")) return;
  if (e.key === "ArrowLeft") { e.preventDefault(); fieldBtn()?.focus(); return; }
  const f = s.props.fields.find(x => x.id === more.field);
  if (f && (e.key === " " || e.key === "Enter") && t.getAttribute("role") === "option") { e.preventDefault(); e.stopPropagation(); fbTick(s, f, t); return; }

  fbStep(e, /** @type {HTMLElement[]} */ ([...right.querySelectorAll('.seg button,[role="option"]')]), fbOpts(right));
}

/* ---- what the area hears ---- */
/** An option ticked or unticked (`opt` its role="option" label), from a key.
    @param {FilterBarState} s @param {FilterField} f @param {HTMLElement} opt */
function fbTick(s, f, opt) {
  const inp = /** @type {HTMLInputElement | null} */ (opt.querySelector("input")); if (!inp) return;
  fbChoose(s, f, inp.value, f.single ? true : !inp.checked);
}
/** @param {FilterBarState} s @param {FilterField} f @param {string} v @param {boolean} on */
function fbChoose(s, f, v, on) {
  const had = document.activeElement && s.host.contains(document.activeElement);
  const sel = [...(f.selected || [])];
  s.props.onSelect(f.id, f.single ? [v] : on ? (sel.includes(v) ? sel : [...sel, v]) : sel.filter(x => x !== v));
  const a = document.activeElement;
  if (had && a && a.matches('[role="option"] input')) /** @type {HTMLElement | null} */ (a.closest('[role="option"]'))?.focus({ preventScroll: true });   /* a click left focus on the box: the option holds it */

}
/** Only me, Select all (what the search shows), Clear.
    @param {FilterBarState} s @param {FilterField} f @param {"me" | "all" | "clear"} what @param {FilterOption[]} shown */
function fbAct(s, f, what, shown) {
  const sel = [...(f.selected || [])];
  s.props.onSelect(f.id, what === "me" ? [...(f.onlyMe || [])] : what === "all" ? [...new Set([...sel, ...shown.map(o => o.value)])] : []);
  if (s.ui.q[f.id]) /** @type {HTMLElement | null} */ (fbMenu(s, f.id)?.querySelector("input.mq") || null)?.focus();   /* BL-62: the search text and its focus are kept */
}
/** is / is not.
    @param {FilterBarState} s @param {FilterField} f @param {boolean} not @param {Element | null} box */
function fbSetNot(s, f, not, box) {
  s.props.onNot?.(f.id, not);
  /** @type {HTMLElement | null} */ (box?.querySelector(`.seg [data-neg="${not ? 1 : 0}"]`) || null)?.focus();
}

/* ---- drawing ---- */
/** @param {{f: FilterField, s: FilterBarState, box: () => Element | null}} props */
function FbIsNot({ f, s, box }) {
  const n = !!f.not;
  return (
    <div class="isnot">
      <span class="seg" role="group" aria-label="Match">
        <button type="button" data-neg="0" data-nk={f.id} aria-pressed={n ? "false" : "true"} onClick={() => fbSetNot(s, f, false, box())}>is</button>
        <button type="button" data-neg="1" data-nk={f.id} aria-pressed={n ? "true" : "false"} onClick={() => fbSetNot(s, f, true, box())}>is not</button>
      </span>
      <span class="sub">{n ? "none of" : "any of"}</span>
    </div>
  );
}

/** The options of a field: a label per option (role="option"), its box, its words and its count.
    @param {{f: FilterField, s: FilterBarState, opts: FilterOption[], name: string}} props */
function FbOptions({ f, s, opts, name }) {
  /** @type {Set<string>} */ const sel = new Set(); if (f.selected) for (const v of f.selected) sel.add(v);
  if (!opts.length) return <div class="sub" style={{ padding: "6px 14px" }}>Nothing to choose</div>;
  return <>{opts.map(o => {
    const on = sel.has(o.value);
    return (
      <label key={o.value} class={o.count || on ? "" : "dim"} role="option" aria-selected={on ? "true" : "false"} tabIndex={-1}
>
        <input type={f.single ? "radio" : "checkbox"} name={f.single ? name : undefined} data-fk={f.id} value={o.value} checked={on}
          tabIndex={-1} aria-hidden="true" onChange={e => fbChoose(s, f, o.value, /** @type {HTMLInputElement} */ (e.currentTarget).checked)} />
        {o.label}{o.extra ? <>{" "}<span class="sub">{o.extra}</span></> : null}<small>{o.count ?? ""}</small>
      </label>
    );
  })}</>;
}

/** A main field's button and its list.
    @param {{f: FilterField, s: FilterBarState, folded: boolean}} props */
function FbFieldMenu({ f, s, folded }) {
  const isOpen = s.ui.open === f.id, shown = isOpen || s.ui.keep === f.id, mid = fbMenuId(f);
  const all = shown && f.options ? f.options() : [], q = (s.ui.q[f.id] || "").toLowerCase();
  const opts = q ? all.filter(o => o.label.toLowerCase().includes(q)) : all;
  const box = () => document.getElementById(mid);
  return (
    <span class={`dd${folded ? " wfold" : ""}`}>
      <button type="button" class={`btn fbtn${f.on ? " on" : ""}`} id={fbBtnId(f)} {...dataAttrs(f.data)} aria-haspopup="listbox"
        aria-expanded={isOpen ? "true" : "false"} aria-controls={mid}
        onClick={e => { e.preventDefault(); if (isOpen && box()?.classList.contains("on")) fbClose(s, false); else fbOpen(s, f.id); }}
        onKeyDown={e => { if (e.key === "ArrowDown" && !isOpen) { e.preventDefault(); fbOpen(s, f.id); } }}>
        {f.button ?? f.label}
      </button>
      <div class={`ddmenu left${isOpen ? " on" : ""}`} id={mid} tabIndex={shown ? -1 : undefined} onKeyDown={e => fbListKeys(s, f, e)}>
        {shown ? <>
          {f.not === undefined ? null : <FbIsNot f={f} s={s} box={box} />}
          {all.length > 6 ? <input type="search" class="mq" data-fk={f.id} placeholder={`Search ${f.label.toLowerCase()}`} aria-label={`Search ${f.label.toLowerCase()}`}
            value={s.ui.q[f.id] || ""} autocomplete="off" onInput={e => { s.ui.q[f.id] = /** @type {HTMLInputElement} */ (e.currentTarget).value; fbPaint(s); }} /> : null}
          <div class="acts">
            {f.onlyMe ? <button type="button" class="mini" data-ma="me" onClick={() => fbAct(s, f, "me", opts)}>Only me</button> : null}
            <button type="button" class="mini" data-ma="all" onClick={() => fbAct(s, f, "all", opts)}>Select all</button>
            <button type="button" class="mini" data-ma="clear" onClick={() => fbAct(s, f, "clear", opts)}>Clear</button>
          </div>
          <div role="listbox" aria-multiselectable={f.single ? undefined : "true"} aria-label={f.label}>
            <FbOptions f={f} s={s} opts={opts} name={`${mid}-opt`} />
          </div>
        </> : null}
      </div>
    </span>
  );
}

/** The funnel's field picker.
    @param {{s: FilterBarState, more: FilterMore}} props */
function FbPicker({ s, more }) {
  const fields = fbPickList(s.props), fq = (more.query || "").toLowerCase();
  const vis = fq ? fields.filter(f => f.label.toLowerCase().includes(fq)) : fields;
  const f = fields.find(x => x.id === more.field) || fields[0];
  const headId = more.headId || `${more.menuId}H`;
  const box = () => document.getElementById(more.menuId);
  let sec = "";
  return (
    <div class="fpick">
      <div class="fpl">
        {more.onQuery ? <input type="search" id="fpq" placeholder="Find a field…" aria-label="Find a field" value={more.query || ""}
          autocomplete="off" onInput={e => more.onQuery?.(/** @type {HTMLInputElement} */ (e.currentTarget).value)} /> : null}
        <div class="fplist" role="listbox" aria-label={more.listLabel || "Fields"}>
          {vis.map(x => {
            const head = x.section && x.section !== sec ? <div class="fsec2" role="presentation">{x.section}</div> : null;
            sec = x.section || "";
            const on = x.id === (f && f.id);
            return <Fragment key={x.id}>{head}<button type="button" role="option" class={`fpf${x.on ? " on" : ""}`} data-fpk={x.id}
              aria-selected={on ? "true" : "false"} tabIndex={on ? 0 : -1} onClick={() => { if (x.id !== more.field) more.onField(x.id); }}>
              {x.label}{x.mark ? <>{" "}<small>{x.mark}</small></> : null}</button></Fragment>;
          })}
          {!vis.length ? <div class="sub" style={{ padding: "6px 4px" }}>No field matches</div> : null}
        </div>
      </div>
      <div class="fpr">
        {f && f.range ? <>
          <h3 id={headId}>{f.label}</h3>
          <div class="drange">
            {(/** @type {("from" | "to")[]} */ (["from", "to"])).map((end, i) => <Fragment key={end}>{i ? <span>and</span> : null}<input type="text"
              {...{ [`data-${f.id}`]: end }} placeholder="DD-MM-YYYY" value={f.range?.[end] || ""} aria-label={`${f.range?.name} ${end}`}
              onChange={e => s.props.onRange?.(f.id, end, /** @type {HTMLInputElement} */ (e.currentTarget).value)} /></Fragment>)}
          </div>
        </> : f ? <>
          <h3 id={headId}>{f.label}</h3>
          {f.note ? <p class="sub" style={{ margin: "0 0 6px" }}>{f.note}</p> : null}
          {f.not === undefined ? null : <FbIsNot f={f} s={s} box={box} />}
          <div class="fpopts" role="listbox" aria-multiselectable={f.single ? undefined : "true"} aria-labelledby={headId}>
            <FbOptions f={f} s={s} opts={f.options ? f.options() : []} name={`${more.menuId}-opt`} />
          </div>
        </> : null}
        <div class="fpfoot">
          <span class="sub" id={more.resultId}>{more.result}</span><span class="sp"></span>
          {more.clearAll ? <button type="button" class="mini" id={more.clearAll.id} onClick={() => { more.clearAll?.run();
            /** @type {HTMLElement | null} */ (box()?.querySelector('.fpf[aria-selected="true"]') || null)?.focus(); }}>Clear all</button> : null}
          <button type="button" class="btn primary" id={more.doneId} onClick={() => fbClose(s, true)}>Done</button>
        </div>
      </div>
    </div>
  );
}

/** The funnel: its button and its picker.
    @param {{s: FilterBarState, more: FilterMore}} props */
function FbFunnel({ s, more }) {
  const isOpen = s.ui.open === FB_MORE, shown = isOpen || s.ui.keep === FB_MORE, n = s.ui.fold.length;
  const tip = more.label + (n ? `. ${n} more filter${n === 1 ? " is" : "s are"} here` : "");
  const inner = <>
    <button type="button" class={`ib bd fbtn${more.on ? " on" : ""}`} id={more.id} aria-haspopup="dialog" aria-expanded={isOpen ? "true" : "false"}
      aria-controls={more.menuId} data-key={more.key} aria-label={tip} data-tip={tip}
      onClick={e => { e.preventDefault(); if (isOpen && document.getElementById(more.menuId)?.classList.contains("on")) fbClose(s, false); else fbOpen(s, FB_MORE); }}>
      <Icon name="funnel" />{more.count ? <span class="fcount" aria-hidden="true">{more.count}</span> : null}
    </button>
    <div class={`ddmenu left fpmenu${isOpen ? " on" : ""}`} id={more.menuId} role="dialog" aria-label={more.menuLabel} onKeyDown={e => fbPickKeys(s, e)}>
      {shown ? <FbPicker s={s} more={more} /> : null}
    </div>
  </>;
  return s.props.bare ? inner : <span class="dd">{inner}</span>;
}

/** The bar: a button per main field, then the funnel. Drawn by drawFilterBar (its `ui` and `host` are the bar's own).
    @param {FilterBarProps & {ui: FilterUi, host: Element}} props */
export function FilterBar({ ui, host, ...props }) {
  const s = fbState(host);
  s.props = props; s.ui = ui;
  return <>
    {props.bare ? null : fbMain(props).map(f => <FbFieldMenu key={f.id} f={f} s={s} folded={ui.fold.includes(f.id)} />)}
    {props.more ? <FbFunnel s={s} more={props.more} /> : null}
  </>;
}
