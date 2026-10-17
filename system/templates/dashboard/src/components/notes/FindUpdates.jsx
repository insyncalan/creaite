// @ts-check
/* FindUpdates (BL-301 E): the panel beside a note that turns its lines into tracker changes. It takes the note's right-hand
   column until it is closed. The Notes tab (part B) hosts it:

     mountFindUpdates(path, el, {noteEl, onClose, onMarks, p})

   - `path`: the note's stored path (projects/<folder>/08 Notes/<title>.md); `el`: the element it is drawn into (the right column).
   - `noteEl` (optional): the element holding the note. Each line that gave a change gets a numbered marker matching its rows, and
     hovering one highlights the other: by default the panel sets `data-fu-mk` (the number) and `data-fu-hl` on the note's elements
     that carry `data-p="<line>"` (attributes only, never markup), and listens for hovering on them. An editor that draws its own
     marks (a ProseMirror decoration) passes `onMarks(markers, hover)` instead and calls `fuHover.value = p` itself.
   - `p` (optional): one line only (AI › Make this an action, a risk…).
   - `onClose`: the panel was closed (Close, or Esc with no row open).

   Rows are grouped New, Updates to existing items, Milestones, Project information. Ticking a row is the approval; routine rows
   start ticked, new risks, decisions, milestone moves, health and memory lines unticked (the server's bulk rule); a hedged line's
   milestone move is locked. Clicking a row opens it in the peek's layout to edit it first. Apply applies the ticked rows as one
   apply (Undo in the snackbar); Save for later puts them in Review. Text only through JSX; tokens-only CSS (style.css, BL-301 E). */
import { Fragment, render } from "preact";
import { linkWords } from "../../core/linkText.js";
import { useEffect, useRef, useState } from "preact/hooks";
import { REGD } from "../../core/data.js";
import { Icon } from "../Icon.jsx";
import { IconButton } from "../IconButton.jsx";
import { TextEditor } from "../TextEditor.jsx";
import { fuApply, fuConfirm, fuEdit, fuFind, fuHover, fuMarkers, fuMsg, fuOpen, fuPath, fuQuiet, fuReset, fuRows, fuSaving, fuState,
  fuSteps, fuTick, fuTicked } from "../../stores/findUpdates.js";

/** @typedef {import("../../stores/findUpdates.js").FuRow} PanelRow */
/** @typedef {import("../../stores/findUpdates.js").FuField} PanelField */
/** @typedef {{path: string, noteEl?: HTMLElement | null, p?: number, onClose?: () => void,
    onMarks?: (markers: Record<number, number>, hover: number) => void}} FindUpdatesProps */

const FU_GROUPS = [["new", "New"], ["update", "Updates to existing items"], ["milestone", "Milestones"], ["info", "Project information"]];

/** DD-MM-YYYY (or YYYY-MM-DD) as YYYY-MM-DD, or null. @param {string} v */
function fuIsoOf(v) {
  const s = String(v || "").trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
  const m = s.match(/^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})$/);
  if (!m) return null;
  const d = new Date(+m[3], +m[2] - 1, +m[1]);
  return d.getMonth() === +m[2] - 1 ? `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}` : null;
}
/** @param {string} v */
const fuShown = v => /^\d{4}-\d{2}-\d{2}$/.test(v || "") ? `${v.slice(8, 10)}-${v.slice(5, 7)}-${v.slice(0, 4)}` : v || "";

/** A field's value on a row's item. @param {PanelRow} row @param {PanelField} f */
function valueOf(row, f) {
  const it = row.item || {}, part = f.part === "person" ? it.person : f.part === "memory" ? it.memory : it[f.part];
  return String((part || {})[f.f] ?? "");
}

/** One field in the row's peek. @param {{row: PanelRow, f: PanelField}} props */
function Field({ row, f }) {
  const id = `fuf-${row.key}-${f.f}`, v = valueOf(row, f);
  const [bad, setBad] = useState("");
  if (f.kind === "text") {
    return <TextEditor id={id} value={v} multiline={false} rows={1} cls="fu-in fu-ed" labelledBy={`${id}-l`} links
      onCommit={t => { if (t.trim() !== v) fuEdit(row.key, f, t.trim()); }} />;
  }
  if (f.kind === "enum") {
    return (
      <select id={id} class="fu-in" value={v} onChange={e => fuEdit(row.key, f, /** @type {HTMLSelectElement} */ (e.currentTarget).value)}>
        {!v && <option value="">Not set</option>}
        {(f.options || []).map(o => <option key={o} value={o}>{o}</option>)}
      </select>
    );
  }
  if (f.kind === "date") {
    return (
      <span class="fu-date">
        <input id={id} class="fu-in" type="text" inputMode="numeric" placeholder="DD-MM-YYYY" value={fuShown(v)} aria-invalid={bad ? "true" : undefined}
          aria-describedby={bad ? `${id}-e` : undefined}
          onChange={e => { const t = /** @type {HTMLInputElement} */ (e.currentTarget).value, iso = t.trim() ? fuIsoOf(t) : "";
            if (iso === null) { setBad("Write the date as DD-MM-YYYY"); return; } setBad(""); fuEdit(row.key, f, iso); }} />
        {bad && <span class="fu-bad" id={`${id}-e`} role="alert">{bad}</span>}
      </span>
    );
  }
  return <input id={id} class="fu-in" type="text" list={f.kind === "person" ? "fuPeople" : undefined} value={v} autoComplete="off"
    onChange={e => fuEdit(row.key, f, /** @type {HTMLInputElement} */ (e.currentTarget).value.trim())} />;
}

/** A row opened to edit it first, in the peek's layout (BL-177): its fields, then Done. @param {{row: PanelRow, back: () => void}} props */
function RowPeek({ row, back }) {
  return (
    <div class="fu-peek" id={`fup-${row.key}`} role="group" aria-label={`Edit: ${row.text || row.type}`}
      onKeyDown={e => { if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); back(); } }}>
      <dl class="fu-fields">
        {row.fields.map(f => <Fragment key={f.f}>
          <dt id={`fuf-${row.key}-${f.f}-l`}><label for={`fuf-${row.key}-${f.f}`}>{f.label}</label></dt>
          <dd><Field row={row} f={f} /></dd>
        </Fragment>)}
      </dl>
      {!row.fields.length && <p class="sub">Nothing to edit on this row.</p>}
      <div class="fu-pf"><span class="sub">Checked again by the tracker when you apply.</span><button type="button" class="btn sm" onClick={back}>Done</button></div>
    </div>
  );
}

/** One row. @param {{row: PanelRow, marker: number}} props */
function Row({ row, marker }) {
  const open = fuOpen.value === row.key, hl = fuHover.value === row.p;
  const btn = useRef(/** @type {HTMLButtonElement | null} */ (null));
  const name = `${row.type}${row.text ? `: ${row.text}` : ""}`;
  const back = () => { fuOpen.value = ""; if (btn.current) btn.current.focus(); };
  return (
    <li class={`fu-r${hl ? " hl" : ""}${row.invalid ? " bad" : ""}${row.lock ? " locked" : ""}`} data-fukey={row.key} data-p={row.p}
      onMouseEnter={() => { fuHover.value = row.p; }} onMouseLeave={() => { if (fuHover.value === row.p) fuHover.value = 0; }}>
      <input type="checkbox" class="fu-tick" checked={row.tick} disabled={!!row.lock}
        aria-label={`Include: ${name}`} aria-describedby={row.lock || row.invalid ? `fun-${row.key}` : undefined}
        onChange={e => fuTick(row.key, /** @type {HTMLInputElement} */ (e.currentTarget).checked)} />
      <span class="fu-mk" title={`Line ${row.p} of the note`}><span class="vh">Line </span>{marker}</span>
      <div class="fu-main">
        <button type="button" ref={btn} class="fu-open" aria-expanded={open ? "true" : "false"} aria-controls={`fup-${row.key}`}
          onClick={() => { fuOpen.value = open ? "" : row.key; }} onFocus={() => { fuHover.value = row.p; }}>
          <span class="fu-ty">{row.type}{row.flags.map(f => <span key={f.t} class={`fu-flag ${f.tone || "soft"}`} title={f.tip}>{f.t}</span>)}</span>
          {row.text && <span class="fu-tx">{row.text}</span>}
          {(row.change || []).map(c => <span key={c.f} class="fu-ch">{c.label} <s>{linkWords(c.from) || "—"}</s> <span aria-hidden="true">→</span><span class="vh"> to </span> {linkWords(c.to)}</span>)}
        </button>
        {row.notes.map(n => <div key={n} class="fu-q">{n}</div>)}
        {(row.lock || row.invalid) && <div class={row.invalid ? "fu-bad" : "fu-q"} id={`fun-${row.key}`}>
          {row.invalid ? `Can't be applied: ${row.invalid}` : row.lock === "hedged" ? "Tentative: confirm it first. Change the milestone itself once it's confirmed." : ""}</div>}
        {open && <RowPeek row={row} back={back} />}
      </div>
    </li>
  );
}

/** Paint the note's lines: the marker on each line that gave a change, the hovered one highlighted (attributes only).
    @param {HTMLElement} el @param {Record<number, number>} markers @param {number} hover */
function paint(el, markers, hover) {
  for (const n of /** @type {NodeListOf<HTMLElement>} */ (el.querySelectorAll("[data-p]"))) {
    const p = +(n.dataset.p || 0), m = markers[p];
    if (m) n.setAttribute("data-fu-mk", String(m)); else n.removeAttribute("data-fu-mk");
    n.toggleAttribute("data-fu-hl", !!m && p === hover);
  }
}

/** The panel. @param {FindUpdatesProps} props */
export function FindUpdates({ path, noteEl, p, onClose, onMarks }) {
  const box = useRef(/** @type {HTMLElement | null} */ (null));
  useEffect(() => {                                   /* a new note (or line): start over and run */
    fuReset(path);
    fuFind(p ? { p } : {});
  }, [path, p]);
  const markers = fuMarkers.value, hover = fuHover.value;
  useEffect(() => {
    if (onMarks) onMarks(markers, hover);
    else if (noteEl) paint(noteEl, markers, hover);
  }, [markers, hover, noteEl]);
  useEffect(() => {                                   /* hovering a line of the note highlights its rows */
    if (!noteEl) return undefined;
    /** @param {Event} e */
    const over = e => { const t = /** @type {HTMLElement} */ (e.target).closest && /** @type {HTMLElement} */ (e.target).closest("[data-p]");
      fuHover.value = t && noteEl.contains(t) ? +(/** @type {HTMLElement} */ (t).dataset.p || 0) : 0; };
    const out = () => { fuHover.value = 0; };
    noteEl.addEventListener("mouseover", over);
    noteEl.addEventListener("mouseleave", out);
    return () => { noteEl.removeEventListener("mouseover", over); noteEl.removeEventListener("mouseleave", out); paint(noteEl, {}, 0); };
  }, [noteEl]);
  const rows = fuRows.value, state = fuState.value, ticked = fuTicked.value.length, saving = fuSaving.value;
  const close = () => { if (onClose) onClose(); };
  const summary = state === "ready" ? [`${rows.length} found`, `${ticked} ticked`,
    fuQuiet.value ? `${fuQuiet.value} line${fuQuiet.value === 1 ? "" : "s"} left as a note` : "", "click a row to edit it"].filter(Boolean).join(" · ") : "";
  return (
    <aside class="fu" ref={box} aria-labelledby="fuTitle" data-fu-path={path}
      onKeyDown={e => { if (e.key === "Escape" && !fuOpen.value && state !== "busy") { e.preventDefault(); close(); } }}>
      <div class="fu-hd">
        <h3 id="fuTitle"><Icon name="spark" /> Found in this note</h3>
        <IconButton icon="x" label="Close Find updates" onClick={close} cls="fu-x" />
        {summary && <span class="sub fu-sum">{summary}</span>}
      </div>
      <div class="vh" role="status" aria-live="polite">{state === "busy" ? "Finding updates in the note" : summary || fuMsg.value}</div>
      {state === "busy" && <div class="fu-busy"><span class="spin" aria-hidden="true"></span>
        <span>Reading the new lines with Claude{fuSteps.value ? ` · ${fuSteps.value} step${fuSteps.value === 1 ? "" : "s"}` : ""}</span>
        <button type="button" class="mini" data-drstop>Stop</button></div>}
      {state === "ask" && <div class="fu-ask">
        <p>{fuMsg.value || "This note is confidential."} Its new items will be marked Sensitive.</p>
        <div class="fu-acts"><button type="button" class="btn primary" onClick={() => fuConfirm()}>Send to Claude</button>
          <button type="button" class="btn" onClick={close}>Not now</button></div></div>}
      {["none", "error", "done"].includes(state) && <div class="fu-msg"><p class="sub">{fuMsg.value}</p>
        <button type="button" class="btn sm" onClick={() => fuFind()}>Find updates again</button></div>}
      {state === "ready" && <>
        {FU_GROUPS.map(([g, label]) => {
          const L = rows.filter(r => r.group === g).sort((a, b) => a.p - b.p);
          if (!L.length) return null;
          return <section key={g} class="fu-gs" aria-labelledby={`fug-${g}`}>
            <h4 class="fu-g" id={`fug-${g}`}>{label}</h4>
            <ul class="fu-list">{L.map(r => <Row key={r.key} row={r} marker={markers[r.p]} />)}</ul>
          </section>;
        })}
        <div class="fu-ft">
          <button type="button" class="btn primary" id="fuApply" disabled={!ticked || !!saving} onClick={() => fuApply("apply")}>
            {saving === "apply" ? "Applying…" : `Apply ${ticked} change${ticked === 1 ? "" : "s"}`}</button>
          <button type="button" class="btn" id="fuLater" disabled={!ticked || !!saving} onClick={() => fuApply("later")}>Save for later</button>
          <span class="sub">Save for later puts them in Review</span>
        </div>
      </>}
      <datalist id="fuPeople">{(REGD.people || []).map((/** @type {{name: string}} */ x) => <option key={x.name} value={x.name} />)}</datalist>
    </aside>
  );
}

/** Draw the panel into `el` (the note's right-hand column) for the note at `path`. Returns {close}: it unmounts the panel and the
    note's markers. @param {string} path @param {HTMLElement} el @param {Omit<FindUpdatesProps, "path">} [opts] */
export function mountFindUpdates(path, el, opts = {}) {
  const done = () => { render(null, el); fuPath.value = ""; if (opts.onClose) opts.onClose(); };
  render(<FindUpdates path={path} {...opts} onClose={done} />, el);
  return { close: done };
}
