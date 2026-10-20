// @ts-check
/* notes.js (BL-301 B): the Notes tab's place in the page. The screen is components/notes/NotesPage.jsx, its state stores/notes.js.

   - #notes=ABC (a project's notes) and #notes=_portfolio (the portfolio's, under Portfolio), with &n=<file> for the open note.
   - The project page's tabs (Overview, Notes) on the cockpit.
   - ⌘\ shows or hides the notes list; leaving the page or closing the window writes the open note (its editing session ends).
   - A note found by search (⌘K, Files' search), a note in Files and a note linked from the peek open in the Notes tab.
   - The peek says which notes mention its item ("2 notes mention this"). */
import { h, render } from "preact";
import { $, html, addHTML } from "./core/dom.js";
import { P } from "./core/data.js";
import { D } from "./core/page.js";
import { NOTE_OPEN, openPath } from "./core/fields.js";
import { go, navWrite } from "./core/nav.js";
import { shared } from "./core/state.js";
import { mount } from "./components/mount.js";
import { focusShortcut, NotesPage, toggleFind } from "./components/notes/NotesPage.jsx";
import { itemOf } from "./components/notes/NoteEditor.jsx";
import { drawProjectTabs } from "./components/project/ProjectTabs.jsx";
import { openRecord } from "./panel.js";
import { allNotes, closeNote, loadNotes, noteCur, noteFind, noteFlash, noteFlush, noteFlushOnExit, noteFocus, noteLeave, noteUnsavedAtExit, notesCode, notesList, notesMentioning, openNote,
  toggleNotesList } from "./stores/notes.js";

/** The project (or _portfolio) a stored note path belongs to, from the page's data; null when it isn't a known note.
    @param {string} path */
export function noteCodeOf(path) {
  for (const [code, L] of Object.entries(allNotes())) if ((L || []).some(n => n.path === path)) return code;
  return null;
}
/** Whether a stored path is a note (a .md file in a notes folder the page knows of). @param {string} path */
export const isNotePath = path => !!path && (noteCodeOf(path) !== null || (/\/(08 Notes|notes)\/[^/]+\.md$/i.test(path)
  && !/\/(99 Archive|_Archive|zz Archive)\//i.test(path)));   /* #124: a deleted note (Files › Archived opens it by its place in 99 Archive; #252: or _Archive, zz Archive for one release) opens as a file */

/** A valid code for the Notes tab. @param {string} code */
export const notesCodeOk = code => code === "_portfolio" || P.some(p => p.code === code);

/** Draw the Notes tab for a project (or the portfolio); open the note the address names, else the first one.
    @param {string} code */
export function renderNotes(code) {
  const el = $("#v-notes");
  if (!el) return;
  const same = notesCode.value === code;
  mount(NotesPage, { code, onGo: (/** @type {string} */ v, /** @type {string|undefined} */ a) => go(v, a),
    onOpenItem: (/** @type {string} */ id) => { const found = itemOf(id); if (found) openRecord(found.k, id); },
    onOpenFile: (/** @type {string} */ p) => openPath(p), onAddressChange: () => navWrite(false) }, el);
  loadNotes(code).then(async () => {
    const want = shared.NOTEFILE, find = !!shared.NOTEFIND; shared.NOTEFILE = null; shared.NOTEFIND = false;
    const L = notesList.value, cur = noteCur.value;
    const target = want ? L.find(n => n.file === want || n.path === want) : cur && cur.code === code ? null : L[0];
    if (target && (!cur || cur.path !== target.path)) { if (await openNote(target.path)) navWrite(false); }
    else if (!target && cur && cur.code !== code) closeNote();
    else if (!same) navWrite(false);
    const now = noteCur.value;   /* BL-301 E: #notes=ABC&n=<file>&find=1 opens Find updates at once (part C's "Done and find updates") */
    if (find && now && now.code === code && (!want || now.note.file === want || now.path === want)) { await toggleFind(true); navWrite(false); }
  });
}

/** Open a note by its stored path, in its project's Notes tab; with `line`, that line in view and highlighted (a source link's
    "#p4", BL-301 E). `o.code` names the project when the caller knows it (the capture drawer's note, not yet in the page's
    data); `o.find` also opens Find updates beside it (part C's "Done and find updates", the address's &find=1).
    @param {string} path @param {number} [line] @param {{code?: string, find?: boolean}} [o] */
export function openNoteAt(path, line, o = {}) {
  if (line) noteFlash.value = { path, line };
  const code = (o.code && notesCodeOk(o.code) ? o.code : null) || noteCodeOf(path) || (() => { const m = /^projects\/([^/]+)\//.exec(path); const f = m && m[1]; if (f === "_portfolio") return "_portfolio";
    const pair = Object.entries(/** @type {any} */ (D).folders || {}).find(([, name]) => name === f); return pair ? pair[0] : null; })();
  if (!code) return false;
  shared.NOTEFILE = path; shared.NOTEFIND = !!o.find;
  if (shared.VIEW === "notes" && notesCode.value === code) { renderNotes(code); return true; }
  return go("notes", code);
}

/** The page is leaving the Notes tab: the open note's editing session ends (its file is written). */
export function notesLeave() { noteFlush(); noteFocus.value = false; noteLeave.value = null; }

/** The cockpit's tabs (Overview, Notes). @param {string} code */
export function drawCockpitTabs(code) {
  const host = $("#cockTabs");
  if (!host) return;
  drawProjectTabs(host, { code, selected: "overview", count: (allNotes()[code] || []).length,
    onGo: id => { if (id === "notes") go("notes", code); } });
}

/** "2 notes mention this" in the peek, each note a link that opens it. @param {{id: string}} props */
function NoteMentions({ id }) {
  const L = notesMentioning(id);
  if (!L.length) return null;
  return h("div", { class: "pk-notes", role: "note" },
    h("span", null, `${L.length} note${L.length === 1 ? "" : "s"} mention${L.length === 1 ? "s" : ""} this: `),
    ...L.map(({ note }, i) => h("span", { key: note.path }, i ? ", " : "",
      h("a", { href: "#", class: "hlink", "data-opennote": note.path }, note.title))));
}
/** Draw the peek's note mentions for an item (or nothing). @param {string} id */
export function drawPeekNotes(id) {
  let host = $("#pkNotes");
  const warn = $("#pkWarn");
  if (!host && warn) { addHTML(warn, "afterend", html`<div id="pkNotes"></div>`); host = $("#pkNotes"); }
  if (host) render(id ? h(/** @type {any} */ (NoteMentions), { id }) : null, host);
}

/** #119 (Alan's call, easy to take out: delete this function and its one call): closing or reloading the page while typing could not
    be saved (the file changed outside creaite, an error, a wait) asks the browser to confirm, since no draft is kept any more. */
function bootUnloadGuard() {
  window.addEventListener("beforeunload", e => { if (noteUnsavedAtExit()) { e.preventDefault(); e.returnValue = ""; } });
}

/* BL-231: what this block does at load, run by src/main.js */
export function bootNotes() {
  document.addEventListener("keydown", e => {
    if (shared.VIEW === "notes" && (e.metaKey || e.ctrlKey) && e.key === "\\") { e.preventDefault(); toggleNotesList(); }
    else if (shared.VIEW === "notes") focusShortcut(e);          /* #136: ⌘⇧F enters and leaves focus mode */
  });
  document.addEventListener("click", e => {            /* before Files' own handler: a note opens in the Notes tab */
    const t = /** @type {Element} */ (e.target);
    const a = t && t.closest ? t.closest("[data-opennote],[data-openfile],[data-go-notes]") : null;
    if (!a) return;
    const go1 = a.getAttribute("data-go-notes");
    if (go1) { e.preventDefault(); e.stopPropagation(); go("notes", go1); return; }
    const p = a.getAttribute("data-opennote") || a.getAttribute("data-openfile") || "";
    if (a.hasAttribute("data-opennote") || isNotePath(p)) { e.preventDefault(); e.stopPropagation(); openNoteAt(p, +(a.getAttribute("data-noteline") || 0)); }
  }, true);
  NOTE_OPEN.fn = (/** @type {string} */ p, /** @type {number} */ line) => { openNoteAt(p, line); };   /* BL-301 E: a source's "#p4" opens the note there */
  window.addEventListener("pagehide", noteFlushOnExit);
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "hidden") noteFlush(false); });   /* hiding the tab saves; it is not leaving the note, so no rename */
  bootUnloadGuard();
}
