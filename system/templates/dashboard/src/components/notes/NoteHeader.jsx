// @ts-check
/* NoteHeader (#115): the pieces of an open note's header. `NoteDate` is a typed-or-picked date (DD-MM-YYYY or words such as
   "last monday", read by core/page.js readDate, with a "Reads as …" line before anything is accepted and a calendar below);
   `NoteTags` is the note's tags as chips (the same `tags` field as before: click a tag's text to rename it, × removes it, Enter
   commits, "+ Tags" adds, a few suggestions until there are some). Every handler works from the note as it is now
   (`noteCur`), by position in that list, never from a copy drawn earlier. Text only through JSX. */
import { useEffect, useRef, useState } from "preact/hooks";
import { fd, readDate, TODAY } from "../../core/page.js";
import { snack } from "../../core/server.js";
import { noteCur, noteMeta } from "../../stores/notes.js";
import { Icon } from "../Icon.jsx";

const NH_DAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];
const NH_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const nhPad = /** @param {number} n */ n => String(n).padStart(2, "0");
/** @param {Date} d */ const nhIso = d => `${d.getFullYear()}-${nhPad(d.getMonth() + 1)}-${nhPad(d.getDate())}`;
/** "Monday 12-10-2026". @param {string} iso */
export const sayDate = iso => `${new Date(`${iso}T12:00:00`).toLocaleDateString("en-GB", { weekday: "long" })} ${fd(iso)}`;

/** The Date property: a text box (typed or words), a calendar button and the pop-up. @param {{date: string}} props */
export function NoteDate({ date }) {
  const [text, setText] = useState(date ? fd(date) : ""), [open, setOpen] = useState(false);
  const [view, setView] = useState(() => (date || TODAY).slice(0, 7));
  const box = useRef(/** @type {HTMLSpanElement | null} */ (null)), inp = useRef(/** @type {HTMLInputElement | null} */ (null));
  const grid = useRef(/** @type {HTMLDivElement | null} */ (null)), quiet = useRef(false);
  const t = text.trim(), read = t ? readDate(t) : null, bad = !!t && !read;
  const chosen = read || date;
  useEffect(() => { if (read) setView(read.slice(0, 7)); }, [read]);

  /** Put focus back in the date box without opening the pop-up again (the box opens on focus; this focus is not the person's). */
  const back = () => {
    const el = inp.current; if (!el || document.activeElement === el) return;
    quiet.current = true; el.focus(); quiet.current = false;
  };
  /** Write the date (or clear it) and close; `refocus` returns focus to the box (a day picked, where the day button goes away).
      @param {string} iso @param {boolean} [refocus] */
  const commit = (iso, refocus) => {
    setText(iso ? fd(iso) : ""); setOpen(false);
    if (refocus) back();
    if (iso !== date) noteMeta({ date: iso });
  };
  const settle = () => {              /* leaving the field: a date it can read is used, anything else keeps the old date */
    const v = text.trim();
    if (!v) { commit(""); return; }
    const r = readDate(v);
    if (r) commit(r); else { setText(date ? fd(date) : ""); setOpen(false); }
  };
  const y = +view.slice(0, 4), m = +view.slice(5, 7) - 1;
  const first = (new Date(y, m, 1).getDay() + 6) % 7, start = new Date(y, m, 1 - first);
  const cells = Array.from({ length: 42 }, (_, i) => new Date(start.getFullYear(), start.getMonth(), start.getDate() + i));
  const step = /** @param {number} n */ n => { const d = new Date(y, m + n, 1); setView(`${d.getFullYear()}-${nhPad(d.getMonth() + 1)}`); };
  const focusDay = /** @param {string} iso */ iso => { setView(iso.slice(0, 7)); setTimeout(() => { const b = grid.current && grid.current.querySelector(`[data-d="${iso}"]`); if (b) /** @type {HTMLElement} */ (b).focus(); }, 0); };
  const arrow = /** @param {KeyboardEvent} e @param {string} iso */ (e, iso) => {
    const d = new Date(`${iso}T12:00:00`), s = /** @type {Record<string, number>} */ ({ ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 })[e.key];
    if (s === undefined) return;
    e.preventDefault(); d.setDate(d.getDate() + s); focusDay(nhIso(d));
  };
  return (
    <span class="nprop" ref={box} onFocusOut={e => { const to = /** @type {Node|null} */ (e.relatedTarget); if (open && (!to || !(box.current && box.current.contains(to)))) settle(); }}>
      <span class="ndwrap">
        <input ref={inp} type="text" id="noteWsDate" class="nin date" value={text} placeholder="Date, or e.g. last monday" autoComplete="off" maxLength={40}
          aria-label="Date of the session, a date or words like last monday" aria-invalid={bad ? "true" : undefined} aria-describedby={open ? "noteDateRead" : undefined}
          onFocus={() => { if (!quiet.current) setOpen(true); }} onClick={() => setOpen(true)}
          onInput={e => { setText(/** @type {HTMLInputElement} */ (e.target).value); setOpen(true); }}
          onKeyDown={e => {
            if (e.key === "Enter") { e.preventDefault(); e.stopPropagation(); if (!t) commit(""); else if (read) commit(read); else setOpen(true); }
            else if (e.key === "Escape" && open) { e.preventDefault(); e.stopPropagation(); setText(date ? fd(date) : ""); setOpen(false); }
            else if (e.key === "ArrowDown") { e.preventDefault(); setOpen(true); focusDay(chosen || TODAY); }
          }} />
        <button type="button" class="ndbtn" id="noteDateBtn" aria-label="Choose date" data-tip="Choose a date" aria-expanded={open ? "true" : "false"} aria-haspopup="dialog"
          onClick={() => { if (open) setOpen(false); else { setOpen(true); if (inp.current) inp.current.focus(); } }}><Icon name="calendar" /></button>
      </span>
      {open ? (
        <div class="dpop" id="noteDatePop" role="dialog" aria-label="Choose a date" onMouseDown={e => { if (!/** @type {Element} */ (e.target).closest("input")) e.preventDefault(); }}
          onKeyDown={e => { if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); setText(date ? fd(date) : ""); setOpen(false); back(); } }}>
          <div class={`typed${bad ? " bad" : ""}`} id="noteDateRead" role="status" aria-live="polite">
            {!t ? "Type a date or words like last monday." : read ? <>Reads as <b>{sayDate(read)}</b> · Enter to use</> : "Not a date I can read. Try 12-10-2026 or last monday."}
          </div>
          <div class="mh"><button type="button" id="noteDatePrev" aria-label="Previous month" onClick={() => step(-1)}>‹</button><b>{NH_MONTHS[m]} {y}</b>
            <button type="button" id="noteDateNext" aria-label="Next month" onClick={() => step(1)}>›</button></div>
          <div class="g" ref={grid}>
            {NH_DAYS.map(d => <div key={d} class="dn" aria-hidden="true">{d}</div>)}
            {cells.map(d => { const iso = nhIso(d), on = iso === chosen;
              return <button key={iso} type="button" data-d={iso} class={`${d.getMonth() !== m ? "o " : ""}${iso === TODAY ? "t " : ""}${on ? "s" : ""}`}
                aria-label={sayDate(iso)} aria-pressed={on ? "true" : "false"} tabIndex={iso === (chosen && chosen.slice(0, 7) === view ? chosen : `${view}-01`) ? 0 : -1}
                onKeyDown={e => arrow(e, iso)} onClick={() => commit(iso, true)}>{d.getDate()}</button>; })}
          </div>
          <div class="foot">{[["Today", "today"], ["Last Monday", "last monday"], ["Yesterday", "yesterday"]].map(([name, q]) =>
            <button key={q} type="button" data-q={q} onClick={() => { const r = readDate(q); if (r) commit(r, true); }}>{name}</button>)}</div>
        </div>) : null}
    </span>);
}

/* A tag is at most TAG_MAX characters and a note keeps at most TAG_N tags: the same limits as notes.py clean_changes, so the
   screen and the file agree. Commas and every kind of space become one space, as the server writes them. */
const TAG_MAX = 60, TAG_N = 20;
/** Commas and spaces to one space, trimmed, capped. @param {string} v */
const cleanTag = v => v.replace(/[\s,]+/g, " ").trim().slice(0, TAG_MAX).trim();
/** The open note's tags right now. @returns {string[]} */
const tagsNow = () => /** @type {string[]} */ (((noteCur.value && noteCur.value.meta) || {}).tags || []);
const SUGGEST = ["stakeholder", "decision", "follow-up"];

/** The tag chips, "+ Tags" and the suggestions. @param {{tags: string[]}} props */
export function NoteTags({ tags }) {
  const [adding, setAdding] = useState(false);
  const addBtn = useRef(/** @type {HTMLButtonElement | null} */ (null)), newIn = useRef(/** @type {HTMLInputElement | null} */ (null));
  useEffect(() => { if (adding && newIn.current) newIn.current.focus(); }, [adding]);
  /** Add tags (commas separate several): never a duplicate (any case), empty or over-long one. @param {string} raw */
  const add = raw => {
    const next = tagsNow().slice();
    for (const part of raw.split(",")) {
      const v = cleanTag(part);
      if (!v || next.some(x => x.toLowerCase() === v.toLowerCase())) continue;
      if (next.length >= TAG_N) { snack(`Notes keep up to ${TAG_N} tags`); break; }
      next.push(v);
    }
    if (next.length !== tagsNow().length) noteMeta({ tags: next });
  };
  /** @param {number} i */ const remove = i => { const L = tagsNow(); if (i >= 0 && i < L.length) noteMeta({ tags: L.filter((_, j) => j !== i) }); };
  /** @param {number} i @param {HTMLInputElement} el */
  const rename = (i, el) => {
    const L = tagsNow(); if (i < 0 || i >= L.length) return;
    const v = cleanTag(el.value);
    if (!v) { remove(i); return; }
    if (v === L[i]) { el.value = L[i]; return; }
    if (L.some((x, j) => j !== i && x.toLowerCase() === v.toLowerCase())) { el.value = L[i]; snack(`There is already a tag "${v}"`); return; }
    noteMeta({ tags: L.map((x, j) => j === i ? v : x) });
  };
  const doneAdding = /** @param {boolean} focusBack */ focusBack => { setAdding(false); if (focusBack) setTimeout(() => { if (addBtn.current) addBtn.current.focus(); }, 0); };
  return (
    <div class="nlabels" id="noteTags" role="group" aria-label="Tags">
      <TagFlag />
      {tags.map((t, i) => (
        <span key={`${i}|${t}`} class="chip">
          <input type="text" class="t" defaultValue={t} maxLength={TAG_MAX} aria-label={`Tag ${t}, edit to rename`} style={{ width: `${Math.max(2, t.length + 1)}ch` }}
            onInput={e => { const el = /** @type {HTMLInputElement} */ (e.target); el.style.width = `${Math.max(2, el.value.length + 1)}ch`; }}
            onKeyDown={e => { const el = /** @type {HTMLInputElement} */ (e.target);
              if (e.key === "Enter") { e.preventDefault(); el.blur(); } else if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); el.value = t; el.blur(); } }}
            onBlur={e => rename(i, /** @type {HTMLInputElement} */ (e.target))} />
          <button type="button" class="x" aria-label={`Remove tag ${t}`} data-tip={`Remove ${t}`} onClick={() => remove(i)}>×</button>
        </span>))}
      {adding
        ? <input type="text" class="addin" id="noteTagNew" placeholder="Tag" aria-label="New tag" maxLength={80} ref={newIn}
            onKeyDown={e => { const el = /** @type {HTMLInputElement} */ (e.target);
              if (e.key === "Enter") { e.preventDefault(); e.stopPropagation(); add(el.value); el.value = ""; doneAdding(true); }
              else if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); el.value = ""; doneAdding(true); } }}
            onBlur={e => { add(/** @type {HTMLInputElement} */ (e.target).value); doneAdding(false); }} />
        : <button type="button" class="addl" id="noteTagAdd" ref={addBtn} onClick={() => setAdding(true)}>+ Tags</button>}
      {!tags.length ? <span class="sugg" id="noteTagSugg">Suggested: {SUGGEST.map(s =>
        <button key={s} type="button" onMouseDown={e => e.preventDefault()} onClick={() => add(s)}>{s}</button>)}</span> : null}
    </div>);
}
/** The fixed Internal or Confidential chip, read from the open note. */
function TagFlag() {
  const conf = !!((noteCur.value && noteCur.value.meta) || {}).confidential;
  return <span class={`tag${conf ? " int" : ""}`}>{conf ? "Confidential" : "Internal"}</span>;
}
