// @ts-check
/* NotesPage (BL-301 B): a project's Notes tab (#notes=ABC), or the portfolio's notes (#notes=_portfolio, under Portfolio).
   Left: the list (search, Pinned, Recent), collapsible with « and » or ⌘\ (remembered per browser; the note widens). Centre: the
   open note, editable at once (NoteEditor), with its title, tags and flags in the header and "Saved 14:02" when the file is written
   (about two seconds after the last key, #119). The note can be lifted over the page (focus mode, the same live element); Esc, a click
   outside and the leave icon all save first and then close, or ask what to do when the save failed.
   Right: Mentioned in (notes that link here), Linked work (the items it mentions, live) and People. "+ New note" makes one from
   a template (Blank, Stakeholder, Lessons learned, Working session). Text only through JSX. */
import { useEffect, useState } from "preact/hooks";
import { P, pName } from "../../core/data.js";
import { fd, readDate, TODAY } from "../../core/page.js";
import { snack, viaServer } from "../../core/server.js";
import { shared } from "../../core/state.js";
import { addNoteImage, allNotes, closeNote, createNote, loadNotes, noteBodyFrom, noteCopyText, noteCur, noteFind, noteFindP, noteFlush, noteFocus,
  noteFocusClose, noteFocusOpen, noteImageSrc, noteLeave, noteLeaveCopy, noteLeaveKeep, noteLeaveRetry, noteLoading, noteMarks, noteMeta, noteRenamed,
  noteDiscardAsk, noteDiscardNow, noteEscape, noteHeld, noteEscLayers, noteOpenFileVersion, noteSave, notesCode, notesList, notesListOpen, notesMsg, notesQuery, noteTyped, openNote, toggleNotesList } from "../../stores/notes.js";
import { fuHover, fuPath } from "../../stores/findUpdates.js";
import { aiAction, aiBarClose, aiDiscard, aiSug } from "../../stores/aiEdit.js";
import { FindUpdates } from "./FindUpdates.jsx";
import { askDeleteNote, DeleteNoteDialog } from "./DeleteNote.jsx";
import { Dialog } from "../Dialog.jsx";
import { Icon } from "../Icon.jsx";
import { Menu, menuOpenFor, openMenu } from "../Menu.jsx";
import { noteMenuItems, noteMenuPick } from "./noteMenu.js";
import { NewTile } from "../work/NewTile.jsx";
import { NoteDate, NoteTags } from "./NoteHeader.jsx";
import { ProjectTabs } from "../project/ProjectTabs.jsx";
import { itemOf, itemState, NoteEditor } from "./NoteEditor.jsx";

/** @typedef {import("../../stores/notes.js").NoteSummary} NoteSummary */
/** @typedef {{code: string, onGo: (view: string, arg?: string) => void, onOpenItem: (id: string) => void,
    onOpenFile: (path: string) => void, onAddressChange: () => void}} NotesPageProps */

export const TEMPLATES = [["blank", "Blank", "An empty note"], ["stakeholder", "Stakeholder", "Role, what matters to them, how they work"],
  ["lessons-learned", "Lessons learned", "What happened, what to change"], ["working-session", "Working session", "A conversation: its date and who it was with"]];

/** "Today, 09:42", "11-10-2026" for a note in the list. @param {NoteSummary} n */
function when(n) {
  const m = String(n.mod || ""), d = m.slice(0, 10) || n.updated;
  return d === TODAY ? `Today, ${m.slice(11, 16)}` : fd(d);
}
/** Every note title in this project first, then the rest. @param {string} code */
function titlesFor(code) {
  const all = allNotes(), mine = (all[code] || []).map(n => n.title), rest = Object.entries(all).filter(([c]) => c !== code).flatMap(([, L]) => (L || []).map(n => n.title));
  return [...new Set([...mine, ...rest])];
}
/** The note with this title (this project first). @param {string} code @param {string} title @returns {NoteSummary | null} */
export function noteByTitle(code, title) {
  const t = title.trim().toLowerCase(), all = allNotes();
  const pick = /** @param {NoteSummary[]} L */ L => (L || []).find(n => n.title.toLowerCase() === t || n.file.replace(/\.md$/i, "").toLowerCase() === t);
  return pick(all[code]) || Object.values(all).map(pick).find(Boolean) || null;
}

/** When the keyboard last opened a row menu: the browser then sends its own contextmenu event, which must not open a second one. */
let kbAt = 0;

/** The list. @param {{code: string, onOpen: (path: string) => Promise<void> | void, onOpenFile: (path: string) => void}} props */
function NotesList({ code, onOpen, onOpenFile }) {
  const open = notesListOpen.value, q = notesQuery.value.trim().toLowerCase(), cur = noteCur.value;
  const L = notesList.value.filter(n => !q || n.title.toLowerCase().includes(q) || n.tags.some(t => t.toLowerCase().includes(q)));
  const pinned = L.filter(n => n.pinned), recent = L.filter(n => !n.pinned);
  /** The note's … menu for a row (#194): the same menu as its … button, for THAT row's note, with nothing opened or switched (the open note, its
      typing, scroll and focus are not touched). At the pointer, or under the row for the keyboard. Esc closes it with focus back on the row.
      @param {Event} e @param {NoteSummary} n @param {number} x @param {number} y */
  const rowMenu = (e, n, x, y) => {
    e.preventDefault(); e.stopPropagation();
    const btn = /** @type {HTMLElement} */ (e.currentTarget);
    const st = { pinned: !!n.pinned, confidential: !!n.confidential, path: n.path, title: n.title, code };
    openMenu(btn, { label: "Note", cls: "nrowmenu", at: { x, y }, items: noteMenuItems(st),
      onPick: id => { noteMenuPick(id, st, onOpenFile); if (id === "pin" || id === "conf") setTimeout(() => { if (btn.isConnected) btn.focus({ preventScroll: true }); }, 0); } });
  };
  const row = /** @param {NoteSummary} n */ n => (
    <li key={n.path}>
      <button type="button" data-path={n.path} class={`ni${cur && cur.path === n.path ? " on" : ""}`} aria-current={cur && cur.path === n.path ? "page" : undefined} onClick={() => onOpen(n.path)}
        onContextMenu={e => { const r = e.currentTarget.getBoundingClientRect(); if (Date.now() - kbAt < 400 && menuOpenFor(e.currentTarget)) { e.preventDefault(); return; } rowMenu(e, n, e.clientX || r.left + 24, e.clientY || r.bottom); }}
        onKeyDown={e => { if (e.key === "ContextMenu" || (e.key === "F10" && e.shiftKey)) { const r = e.currentTarget.getBoundingClientRect(); kbAt = Date.now(); rowMenu(e, n, r.left + 24, r.bottom); } }}>
        <b>{n.pinned ? <span class="pin" aria-hidden="true">◆ </span> : null}{n.title}</b>
        <small>{when(n)}{n.kind ? ` · ${n.kind}` : ""}{n.confidential ? <span class="conf"> · Confidential</span> : null}</small>
      </button>
    </li>);
  const label = open ? "Hide the notes list" : "Show the notes list";
  return (
    <aside class="nlist" aria-label="Notes">
      <div class="lhead">
        <b id="notesListH">Notes</b><span class="sp" />
        <button type="button" class="ib sm col" id="notesCollapse" aria-expanded={open ? "true" : "false"} aria-controls="notesListBody"
          aria-label={label} data-tip={`${label} (⌘\\)`} onClick={() => toggleNotesList()}><Icon name={open ? "chevsleft" : "chevsright"} /></button>
        <span class="vlabel" aria-hidden="true">{notesList.value.length} notes</span>
      </div>
      <div id="notesListBody" tabindex={-1} hidden={!open}>
        <input class="search nsearch" type="search" placeholder={`Search ${code === "_portfolio" ? "portfolio" : pName(code)} notes`} aria-label="Search notes"
          value={notesQuery.value} onInput={e => { notesQuery.value = /** @type {HTMLInputElement} */ (e.target).value; }} />
        {!L.length ? <p class="sub nnone">{notesList.value.length ? "No note matches." : "No notes yet."}</p> : null}
        {pinned.length ? <><div class="grp" id="ngPinned">Pinned</div><ul class="nul" aria-labelledby="ngPinned">{pinned.map(row)}</ul></> : null}
        {recent.length ? <><div class="grp" id="ngRecent">Recent</div><ul class="nul" aria-labelledby="ngRecent">{recent.map(row)}</ul></> : null}
      </div>
    </aside>);
}

/** The right column: Mentioned in, Linked work, People. @param {{code: string, onOpen: (path: string) => void, onOpenItem: (id: string) => void}} props */
function NoteContext({ code, onOpen, onOpenItem }) {
  const cur = noteCur.value;
  if (!cur) return <aside class="nctx" aria-label="About this note" />;
  const n = cur.note, t = n.title.toLowerCase(), stem = n.file.replace(/\.md$/i, "").toLowerCase();
  const back = Object.entries(allNotes()).flatMap(([c, L]) => (L || []).filter(x => x.path !== n.path && (x.links || []).some(l => [t, stem].includes(l.toLowerCase()))).map(x => ({ c, x })));
  const people = [...new Set([...(n.with || []), ...(n.people || [])])];
  const reg = /** @type {any[]} */ (shared.REG || []);
  return (
    <aside class="nctx" aria-label="About this note">
      <section class="box" aria-labelledby="nxMent"><h2 id="nxMent">Mentioned in</h2>
        {back.length ? <ul>{back.map(({ c, x }) => <li key={x.path}><button type="button" class="linkbtn" onClick={() => onOpen(x.path)}>{x.title}</button>{c !== code ? <small> · {c === "_portfolio" ? "Portfolio" : pName(c)}</small> : null}</li>)}</ul>
          : <p class="sub">No other note links here yet.</p>}
      </section>
      <section class="box" aria-labelledby="nxWork"><h2 id="nxWork">Linked work</h2>
        {(n.items || []).length ? <ul>{n.items.map(id => { const s = itemState(id), hit = itemOf(id); return (
          <li key={id}>{hit ? <button type="button" class={`nchip ${s.tone}`} aria-label={s.title} data-tip={s.title} onClick={() => onOpenItem(id)}>{id}</button>
            : <span class={`nchip ${s.tone}`}>{id}</span>} <small>{s.words}</small></li>); })}</ul>
          : <p class="sub">No work items mentioned. Type # to link one.</p>}
      </section>
      <section class="box" aria-labelledby="nxPeople"><h2 id="nxPeople">People</h2>
        {people.length ? <ul>{people.map(p => { const r = reg.find(x => x && x.name === p); return <li key={p}>{p}{r && r.role ? <small> · {r.role}</small> : null}</li>; })}</ul>
          : <p class="sub">Nobody mentioned. Type @ to mention someone.</p>}
      </section>
    </aside>);
}

/** BL-301 E: open (or close) Find updates beside the note. The note is written first, so Claude reads what is on screen.
    `p` (BL-301 D's AI › Make this an action…) looks at that one line only. @param {boolean} [open] @param {number} [p] */
export async function toggleFind(open = !noteFind.value, p = 0) {
  if (!open) { noteFind.value = false; noteFindP.value = 0; return; }
  if (!noteCur.value) return;
  await noteFlush();
  noteFindP.value = p || 0;
  noteFind.value = true;
}
/** The note's line (`data-p`, drawn by the editor) a selection starts in, or 0. @param {any} h @param {number} from */
function lineAt(h, from) {
  try {
    const v = h.editor.view, at = v.domAtPos(Math.min(from + 1, v.state.doc.content.size));
    const n = /** @type {any} */ (at.node), el = n && n.nodeType === 1 ? n : n && n.parentElement;
    const b = el && el.closest ? el.closest("[data-p]") : null;
    return b && h.el.contains(b) ? +(b.getAttribute("data-p") || 0) : 0;
  } catch (e) { return 0; }
}
/** The one line a selection is on, or 0 when it is on none (a picture, a table) or spans more than one. @param {any} h
    @param {{from: number, to: number}} range */
export function selectedLine(h, range) {
  const a = lineAt(h, range.from), b = lineAt(h, Math.max(range.from, range.to - 1));
  return a && a === b ? a : 0;
}
/* BL-301 D × E: AI › "Make this an action, a risk, a decision or an update" on a note's selection opens Find updates on its line
   only (never the whole note: a selection on no line, or on more than one, says so and runs nothing) */
aiAction({ id: "fu-line", name: "Make this an action, a risk, a decision or an update", line: "Find updates on this line only",
  icon: "check", places: ["notes"], run: (range, h) => {
    const p = selectedLine(h, range);
    if (!p) { snack("Select text on one line of the note: Find updates looks at that line only"); return; }
    toggleFind(true, p);
  } });
/** ✦ Find updates, in the note's header (the slot part B left for it). */
function FindButton() {
  const on = noteFind.value;
  return <button type="button" class={`btn sm${on ? " on" : ""}`} id="noteFind" aria-expanded={on ? "true" : "false"} aria-controls="noteSide"
    disabled={!viaServer()} data-tip={viaServer() ? "Find the tracker changes this note's new lines state" : "Find updates needs the live server"}
    onClick={() => toggleFind()}><span aria-hidden="true">✦ </span>Find updates</button>;
}
/** The right-hand column: the note's context, or Find updates while it is open. @param {{code: string, onOpen: (path: string) => void, onOpenItem: (id: string) => void}} props */
function NoteSide({ code, onOpen, onOpenItem }) {
  const cur = noteCur.value;
  if (!(noteFind.value && cur)) return <div class="nside" id="noteSide"><NoteContext code={code} onOpen={onOpen} onOpenItem={onOpenItem} /></div>;
  const close = () => {
    fuPath.value = ""; noteMarks.value = { markers: {}, hover: 0 }; noteFind.value = false; noteFindP.value = 0;
    const b = /** @type {HTMLElement|null} */ (document.getElementById("noteFind")); if (b) b.focus();
  };
  return <div class="nside" id="noteSide"><FindUpdates key={`${cur.path}|${noteFindP.value}`} path={cur.path} p={noteFindP.value || undefined} onClose={close}
    onMarks={(markers, hover) => { noteMarks.value = { markers, hover }; }} /></div>;
}

/** The save state, as the header says it (#119): "Saved 14:02" once the file is written, "Editing" while typing, "Saving…" as it is written,
    "Not saved" when it couldn't be, and a short word for a file that changed outside creaite. The reason is in the banner below. */
function SaveLine() {
  const s = noteSave.value;
  const text = s.state === "saved" ? `Saved${s.at ? ` ${s.at}` : ""}` : s.state === "typing" ? "Editing" : s.state === "saving" ? "Saving…" :
    s.state === "conflict" ? "Changed outside creaite" : s.state === "wait" || s.state === "error" ? "Not saved" : "";
  return <span class={`nsave ${s.state}`} id="noteSave" data-save={s.state || undefined} role="status" aria-live="polite">{text}</span>;
}

/* Esc over the note closes what is on top first: the AI suggestion, then the bar over a selection (a link popover adds itself in
   stores/notes.js noteEscLayers). The / menu and the pickers, the date pop-up, the tag box and menus take Esc themselves. */
noteEscLayers.push(() => { if (!aiSug.value) return false; aiDiscard(); return true; }, () => aiBarClose());

/** A key pressed while an input method is composing text (Esc cancels the composition, not the note). @param {KeyboardEvent} e */
const composing = e => e.isComposing || e.keyCode === 229;
/** Esc when nothing has focus (the page body: a click on the note's blank space): the same close path. A capture listener on the
    document, only while focus mode is on; it acts only when no element has focus, so every overlay and field that takes Esc itself
    still gets it first. */
function FocusKeys() {
  useEffect(() => {
    /** @param {KeyboardEvent} e */
    const key = e => {
      if (e.key !== "Escape" || composing(e) || !noteFocus.value || document.querySelector("dialog[open]")) return;
      const t = e.target;
      if (t instanceof Element && t !== document.body && t !== document.documentElement) return;
      e.preventDefault(); e.stopPropagation();
      if (!noteEscape()) noteFocusClose();
    };
    document.addEventListener("keydown", key, true);
    return () => document.removeEventListener("keydown", key, true);
  }, []);
  return null;
}

const NOTE_TABBABLE = 'button:not([disabled]),[href],input:not([disabled]):not([type=hidden]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"]),[contenteditable=true]';
/** Tab stays inside the lifted note (a modal): from the last control to the first, and back. @param {KeyboardEvent} e @param {HTMLElement} root */
function trapTab(e, root) {
  const all = /** @type {HTMLElement[]} */ ([...root.querySelectorAll(NOTE_TABBABLE)]).filter(x => x.offsetParent !== null || x.getClientRects().length > 0);
  if (!all.length) return;
  const first = all[0], last = all[all.length - 1], at = document.activeElement;
  if (e.shiftKey && (at === first || !root.contains(at))) { e.preventDefault(); last.focus(); }
  else if (!e.shiftKey && (at === last || !root.contains(at))) { e.preventDefault(); first.focus(); }
}

/** Everything on the page except the lifted note is inert while focus mode is on (no clicks, no Tab, hidden from a screen reader):
    at each level from the note up to the body, every sibling that is not on the path to the note is marked. The scrim, a native
    dialog (the "couldn't save" question, a pop-up in one) and the overlay layers on the body (messages, menus, the AI bar and the pickers, whether drawn already or later) stay live. What was
    already inert stays as it was. */
const BEHIND_ON_BODY = "#chat,#runBadge";                  // the only things on the body, beside the page itself, that belong to the page behind
function FocusInert() {
  useEffect(() => {
    const root = document.querySelector(".ndoc.nfocus");
    /** @type {Element[]} */
    const marked = [];
    for (let el = /** @type {Element | null} */ (root); el && el !== document.body; el = el.parentElement) {
      for (const sib of /** @type {Element[]} */ ([...(el.parentElement ? el.parentElement.children : [])])) {
        if (el.parentElement === document.body && !sib.matches(BEHIND_ON_BODY)) continue;        // (the body also holds the overlay layers: menus, pickers, messages, the AI bar)
        if (sib === el || sib.hasAttribute("inert") || sib.hasAttribute("data-nscrim") || sib.tagName === "SCRIPT" || sib.tagName === "STYLE"
          || sib.matches("dialog,[role=dialog]") || sib.querySelector("dialog")) continue;
        sib.setAttribute("inert", ""); marked.push(sib);
      }
    }
    return () => { for (const m of marked) m.removeAttribute("inert"); };
  }, []);
  return null;
}

/** ⌘⇧F (Ctrl+Shift+F) enters focus mode on the open note, and leaves it by the one close path. @param {KeyboardEvent} e */
export function focusShortcut(e) {
  if (!(e.metaKey || e.ctrlKey) || !e.shiftKey || e.altKey || String(e.key).toLowerCase() !== "f" || composing(e)) return false;
  if (document.querySelector("dialog[open]")) return false;                // (the "couldn't save" question is answered first)
  if (noteFocus.value) { e.preventDefault(); noteFocusClose(); return true; }
  if (!noteCur.value) return false;
  e.preventDefault();
  const a = document.activeElement;
  noteFocusOpen(a && a !== document.body ? a : document.getElementById("noteExpand"));
  return true;
}

/** The open note: header, body, the banner when it couldn't be saved. @param {{code: string, onOpen: (path: string) => void,
    onOpenItem: (id: string) => void, onNew: (title: string) => void, onOpenFile: (path: string) => void}} props */
function NoteDoc({ code, onOpen, onOpenItem, onNew, onOpenFile }) {
  const cur = noteCur.value;
  if (!cur) return (
    <article class="ndoc empty">
      {noteLoading.value ? <p class="sub">Opening…</p> : <>
        <h2>{notesList.value.length ? "Pick a note on the left, or start a new one" : "No notes yet"}</h2>
        <p class="sub"><a class="hhow" href="#help-reference-notes" data-hhow="notes">How Notes works</a></p>
        <p class="sub">Notes are your own working thinking: stakeholders, positions, lessons, a conversation. They stay internal and are never extracted on their own.</p>
      </>}
    </article>);
  const m = cur.meta || {}, n = cur.note, tags = /** @type {string[]} */ (m.tags || []);
  const conf = !!m.confidential, pinned = !!m.pinned;
  const created = String(m.created || n.created || "");
  const focus = noteFocus.value, st = noteSave.value;
  /** Esc and Tab in the lifted note: the topmost overlay closes first; with none open Esc leaves focus mode (the one close path).
      A modal dialog (the "couldn't save" one) takes Esc itself. @param {KeyboardEvent} e */
  const onKey = e => {
    if (!noteFocus.value || composing(e) || (e.target instanceof Element && e.target.closest("dialog"))) return;
    if (e.key === "Tab") { trapTab(e, /** @type {HTMLElement} */ (e.currentTarget)); return; }
    if (e.key !== "Escape") return;                  // (the editor marks Esc as handled itself, so defaultPrevented says nothing; an overlay that took Esc stopped it)
    e.preventDefault(); e.stopPropagation();
    if (!noteEscape()) noteFocusClose();
  };
  /* the same element in both modes (never moved or copied: the cursor, date, tags and save line stay live); the slots before it
     hold the empty place the note leaves in the page and the dimmed scrim, so it keeps its place in the tree */
  return (
    <>
      {focus ? <div class="ndocgh" aria-hidden="true" /> : null}
      {focus ? <div class="nscrim" data-nscrim onClick={e => { if (e.target === e.currentTarget) noteFocusClose(); }} /> : null}
      <article key="doc" class={`ndoc${focus ? " nfocus" : ""}`} aria-labelledby="noteTitle" role={focus ? "dialog" : undefined}
        aria-modal={focus ? "true" : undefined} data-focus={focus ? "on" : undefined} onKeyDown={onKey}>
        <div class="nhead">
          <div class="trow">
            <button type="button" class="ib sm nexpand" id="noteExpand" data-nfocus={focus ? "leave" : "open"} aria-label={focus ? "Leave focus" : "Focus on this note"}
              data-tip={focus ? "Leave focus (Esc or ⌘⇧F)" : "Focus on this note (⌘⇧F)"} onClick={e => { if (noteFocus.value) noteFocusClose(); else noteFocusOpen(/** @type {Element} */ (e.currentTarget)); }}>
              <Icon name={focus ? "shrink" : "expand"} /></button>
            <input class="ntitle" id="noteTitle" aria-label="Title" value={String(m.title ?? n.title)} maxLength={160}
              onInput={e => noteMeta({ title: /** @type {HTMLInputElement} */ (e.target).value })} onBlur={() => { noteFlush(); }} />
            <SaveLine />
            <span class="nslot" id="noteFindSlot" data-slot="find-updates"><FindButton /></span>
            <Menu label="More" btnCls="ib sm bd nmore" menuLabel="Note" left={false} cls="nmorewrap"
              items={noteMenuItems({ pinned, confidential: conf, path: n.path })}
              onPick={id => noteMenuPick(id, { pinned, confidential: conf, path: n.path, title: n.title, code: cur.code }, onOpenFile)} />
          </div>
          <div class="meta props">
            {created ? <span>Created {fd(created)}</span> : null}
            {m.date || n.kind === "Working session" ? <WorkingSession key={`ws|${cur.load}`} date={String(m.date || "")} people={/** @type {string[]} */ (m.with || [])} /> : null}
          </div>
          <NoteTags tags={tags} />
        </div>
        {focus ? <><FocusEnter /><FocusKeys /><FocusInert /></> : null}
        {focus && notesMsg.value ? <div class="nmsg" role="status" data-nfocusmsg>{notesMsg.value}</div> : null}
        {st.state === "conflict" || st.state === "error" || st.state === "wait" ? (
          <div class="nstale" role="alert" data-nbanner={st.state}><span>{st.msg}</span>
            <button type="button" class="btn sm" data-ncopy onClick={() => { noteCopyText().then(ok => snack(ok ? "Your text is copied" : "It couldn't be copied: select it in the note instead")); }}>Copy my text</button>
            {st.state === "conflict" ? <button type="button" class="btn sm" data-nopenfile onClick={() => { noteOpenFileVersion(); }}>Open the file's version</button> : null}
            <button type="button" class="btn sm" data-ndiscard onClick={() => noteDiscardAsk(false)}>Discard my typing</button></div>) : null}
        {noteHeld.value === cur.path ? (
          <div class="nstale nheld" role="status"><span>Waiting on the approval card in ask creaite to move this note to the archive. It can't be changed until you answer the card.</span></div>) : null}
        <NoteEditor key={`n${cur.load}`} readOnly={noteHeld.value === cur.path} loadKey={`n${cur.load}`} markdown={cur.body} code={code} label={`${n.title}, the note`}
          noteTitles={() => titlesFor(code)} onInput={noteTyped} onBody={noteBodyFrom} path={cur.path} imageSrc={noteImageSrc} onImage={addNoteImage}
          onHoverLine={l => { if (noteFind.value && fuHover.value !== l) fuHover.value = l; }}
          onOpenItem={onOpenItem} onOpenNote={t => { const hit = noteByTitle(code, t); if (hit) onOpen(hit.path); else onNew(t); }} />
      </article>
    </>);
}

/** On entering focus mode the cursor goes into the note (where it was, if it was in it). */
function FocusEnter() {
  useEffect(() => {
    const ed = /** @type {any} */ (document.querySelector(".ndoc.nfocus .nbody"));
    if (ed && ed.cxed) ed.cxed.focus();
  }, []);
  return null;
}

/** The question when leaving focus mode and the note couldn't be saved: the note stays open, nothing is dropped. The reason is
    the save line's own message. Esc is Keep editing. */
function LeaveDialog() {
  const q = noteLeave.value, st = noteSave.value;
  return (
    <Dialog open={q !== null} onClose={noteLeaveKeep} labelledBy="noteLeaveH" describedBy="noteLeaveP" id="noteLeaveDlg" focus="[data-nlkeep]">
      {q && q.confirm ? (
        <div class="nleave" data-nlstage="discard">
          <h2 id="noteLeaveH">Discard what you typed?</h2>
          <p id="noteLeaveP">It isn't saved, and it can't be got back unless you copied it. The note shows the file's version again.</p>
          <div class="nlfoot">
            <button type="button" class="btn" data-nlkeep onClick={noteLeaveKeep}>Cancel</button>
            <button type="button" class="btn primary" data-nldiscard onClick={() => { noteDiscardNow(); }}>Discard my typing</button>
          </div>
        </div>
      ) : (
        <div class="nleave" data-nlstage="ask">
          <h2 id="noteLeaveH">This note isn't saved</h2>
          <p id="noteLeaveP">{st.msg || "It couldn't be saved."} Your typing is still in the note.{q && q.copyFailed ? " It couldn't be copied: select the text and copy it yourself, or keep editing." : ""}</p>
          <div class="nlfoot">
            <button type="button" class="btn" data-nlkeep onClick={noteLeaveKeep}>Keep editing</button>
            <button type="button" class="btn" data-nlcopy onClick={() => { noteLeaveCopy(); }}>Copy my text then close</button>
            <button type="button" class="btn primary" data-nlretry onClick={() => { noteLeaveRetry(); }}>Save again</button>
          </div>
          <p class="nlalt">
            {st.state === "conflict" ? <button type="button" class="linkbtn" data-nlopen onClick={() => { noteOpenFileVersion(); }}>Open the file's version</button> : null}
            <button type="button" class="linkbtn" data-nlgiveup onClick={() => noteDiscardAsk(true)}>Discard my typing</button>
          </p>
        </div>
      )}
    </Dialog>);
}

/** BL-301 B gaps: a Working session's date and who it was with, editable in the note's header after it is made. The date is typed or
    picked (NoteDate); both are saved like the title: a change ends with Enter or leaving the field.
    @param {{date: string, people: string[]}} props */
function WorkingSession({ date, people }) {
  return (
    <>
      <span class="nprop"><span class="nk">Date</span><NoteDate date={date} /></span>
      <span class="nprop"><span class="nk">With</span>
        <input type="text" id="noteWsWith" class="nin who" defaultValue={people.join(", ")} placeholder="Names, separated by commas" aria-label="With, names separated by commas"
          onChange={e => noteMeta({ with: /** @type {HTMLInputElement} */ (e.target).value.split(",").map(x => x.trim()).filter(Boolean) })} /></span>
    </>);
}

/** "+ New note": a template, a title, and for a Working session its date and who it was with.
    @param {{code: string, open: boolean, title: string, onClose: () => void, onMade: () => void}} props */
function NewNote({ code, open, title, onClose, onMade }) {
  const [tpl, setTpl] = useState("blank"), [t, setT] = useState(title), [day, setDay] = useState(fd(TODAY)), [who, setWho] = useState(""), [busy, setBusy] = useState(false);
  useEffect(() => { if (open) { setT(title); setDay(fd(TODAY)); setWho(""); setBusy(false); } }, [open, title]);
  const bad = tpl === "working-session" && day.trim() && !readDate(day);
  const make = async () => {
    if (busy || bad) return;
    setBusy(true);
    const made = await createNote(code, { template: tpl, title: t.trim(), ...(tpl === "working-session" ? { date: readDate(day) || TODAY, with: who.split(",").map(x => x.trim()).filter(Boolean) } : {}) });
    setBusy(false);
    if (made) onMade();
  };
  return (
    <Dialog open={open} onClose={onClose} labelledBy="nnH" id="newNoteDlg" focus="#nnTitle" dirty={!!t.trim()}>
      <form method="dialog" class="nnew" onSubmit={e => { e.preventDefault(); make(); }}>
        <h2 id="nnH">New note{code === "_portfolio" ? " · Portfolio" : ` · ${pName(code)}`}</h2>
        <label class="fl">Title<input id="nnTitle" type="text" value={t} maxLength={160} placeholder="What is it about?" onInput={e => setT(/** @type {HTMLInputElement} */ (e.target).value)} /></label>
        <fieldset class="nntpl"><legend>Template</legend>
          {TEMPLATES.map(([id, name, line]) => (
            <label key={id} class={`nntopt${tpl === id ? " on" : ""}`}><input type="radio" name="nntpl" value={id} checked={tpl === id} onChange={() => setTpl(id)} />
              <span><b>{name}</b><small>{line}</small></span></label>))}
        </fieldset>
        {tpl === "working-session" ? <div class="nnws">
          <label class="fl">Date<input type="text" value={day} placeholder="DD-MM-YYYY, or e.g. last monday" aria-invalid={bad ? "true" : undefined} onInput={e => setDay(/** @type {HTMLInputElement} */ (e.target).value)} /></label>
          <label class="fl">With<input type="text" value={who} placeholder="Names, separated by commas" onInput={e => setWho(/** @type {HTMLInputElement} */ (e.target).value)} /></label>
        </div> : null}
        <p class="sub">Saved in the project's notes folder, named by its title. Internal: never in a client report.</p>
        <div class="nnfoot"><button type="button" class="btn" onClick={onClose}>Cancel</button>
          <button type="submit" class="btn primary" id="nnMake" disabled={busy || !!bad || !viaServer()}>{busy ? "Making…" : "Make the note"}</button></div>
      </form>
    </Dialog>);
}

/** The Notes tab. @param {NotesPageProps} props */
export function NotesPage({ code, onGo, onOpenItem, onOpenFile, onAddressChange }) {
  const [dlg, setDlg] = useState(/** @type {string|null} */ (null));
  const name = code === "_portfolio" ? "Portfolio" : pName(code), proj = P.find(x => x.code === code);
  const openPath = /** @param {string} p */ async p => { if (await openNote(p)) onAddressChange(); };
  const renamed = noteRenamed.value;
  useEffect(() => { if (renamed) onAddressChange(); }, [renamed]);          /* BL-301 B gaps: the address names the renamed file */
  return (
    <div class="wrapmax notespage">
      <nav class="crumb" aria-label="Breadcrumb">
        {code === "_portfolio" ? <><a href="#" data-go="today">Today</a><span aria-hidden="true">›</span><span>Portfolio</span></>
          : <><a href="#" data-go="projects">Projects</a><span aria-hidden="true">›</span><a href="#" data-proj={code}>{name}</a></>}
        <span aria-hidden="true">›</span><span aria-current="page">Notes</span>
      </nav>
      <div class="hhead nhh">
        <div style={{ flex: 1 }}><h1>{code === "_portfolio" ? "Portfolio notes" : name}</h1>
          {code === "_portfolio" ? <div class="sub">Notes that cover several projects, and anything not yet filed under one.</div> : proj && proj.client ? <div class="sub">{proj.client}</div> : null}</div>
        <NewTile id="notesNew" popup="dialog" word="New note" decisions={false} hidden={false} onNew={() => setDlg("")} onDecision={() => {}} />
      </div>
      {code !== "_portfolio" ? <ProjectTabs code={code} selected="notes" count={notesList.value.length} onGo={id => { if (id === "overview") onGo("cockpit", code); }} /> : null}
      {notesMsg.value ? <div class="nmsg" role="status">{notesMsg.value}</div> : null}
      {!viaServer() ? <div class="nmsg" role="status">Notes open and save through the live server. Start it to edit; the list is as of the last build.</div> : null}
      <div class={`nsplit${notesListOpen.value ? "" : " collapsed"}${noteFind.value && noteCur.value ? " finding" : ""}`} id="notesSplit">
        <NotesList code={code} onOpen={openPath} onOpenFile={onOpenFile} />
        <NoteDoc code={code} onOpen={openPath} onOpenItem={onOpenItem} onNew={t => setDlg(t)} onOpenFile={onOpenFile} />
        <NoteSide code={code} onOpen={openPath} onOpenItem={onOpenItem} />
      </div>
      <DeleteNoteDialog />
      <LeaveDialog />
      <NewNote code={code} open={dlg !== null} title={dlg || ""} onClose={() => setDlg(null)} onMade={() => { setDlg(null); onAddressChange(); }} />
    </div>);
}

export { closeNote, loadNotes, notesCode };
