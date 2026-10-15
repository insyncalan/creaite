// @ts-check
/* stores/notes.js (BL-301 B, BL-256): the Notes tab's state. One store per area (dev/COMPONENTS.md §2).

   A project's notes (or the portfolio's) are listed from the dashboard's data (D.notes: front matter and references, never text)
   and refreshed from the live server (/api/notes/list). An open note is editable: the file is written (/api/notes/save, through
   filechange.py: logged, undoable) AUTOSAVE_MS after the last key, and at once when he leaves the note, switches notes, toggles a
   property or the page goes away (#119: no draft step). Every save of an editing session carries the session's id, so the
   server keeps ONE backup per session. "Saved 14:02" shows in the note's header. A note changed outside creaite since it was
   opened is never overwritten (the conflict). Leaving focus mode is one path for Esc, the scrim and the leave icon: it saves
   first, and if the save fails the note stays open and a dialog asks (Keep editing, Copy my text then close, Save again). */
import { signal } from "@preact/signals";
import { D } from "../core/page.js";
import { api, oneLine, viaServer } from "../core/server.js";

/** @typedef {{path: string, file: string, title: string, created: string, updated: string, tags: string[], pinned: boolean,
    confidential: boolean, date: string, with: string[], kind: string, mod: string, links: string[], items: string[],
    people: string[], p?: string}} NoteSummary */
/** @typedef {{path: string, code: string, note: NoteSummary, body: string, meta: Record<string, any>, base: string,
    load: number, images?: Record<string, string>, sent?: SentLine[]}} OpenNote */
/** @typedef {{p: number, ids: string[], text: string}} SentLine  a line Find updates already sent (notes.sent_ids): the margin tick */
/** @typedef {{state: ""|"typing"|"saving"|"saved"|"wait"|"conflict"|"error", at?: string, msg?: string}} SaveState */

export const AUTOSAVE_MS = 2000;          // the note's file is written this long after the last key
export const SESSION_IDLE_MS = 300000;    // an editing session ends after 5 minutes without a save (a new session id, a new backup)
const WAIT_RETRY_MS = 10000;              // a save that must wait (an ask creaite run in progress) is tried again after this long
const LIST_KEY = "creaite-notes-list-open";

export const notesCode = signal(/** @type {string | null} */ (null));
export const notesList = signal(/** @type {NoteSummary[]} */ ([]));
export const notesQuery = signal("");
export const noteCur = signal(/** @type {OpenNote | null} */ (null));
export const noteSave = signal(/** @type {SaveState} */ ({ state: "" }));
export const noteLoading = signal(false);
export const notesMsg = signal("");
/** Focus mode: the open note lifted over the page (the same live element, not a copy). */
export const noteFocus = signal(false);
/** The "couldn't save" dialog while leaving focus mode: null when closed; `copyFailed` after a copy that didn't work. */
export const noteLeave = signal(/** @type {{copyFailed?: boolean, confirm?: boolean, back?: boolean} | null} */ (null));

/** Whether the notes list is shown (remembered per browser; the note widens when it is hidden). */
export const notesListOpen = signal((() => { try { return localStorage.getItem(LIST_KEY) !== "0"; } catch (e) { return true; } })());
/** Show or hide the notes list, and remember it. @param {boolean} [show] */
export function toggleNotesList(show) {
  const v = show === undefined ? !notesListOpen.value : show;
  notesListOpen.value = v;
  try { localStorage.setItem(LIST_KEY, v ? "1" : "0"); } catch (e) { /* private window: not remembered */ }
}

/** Every project's notes from the page's data, by code. @returns {Record<string, NoteSummary[]>} */
export function allNotes() { const d = /** @type {any} */ (D); if (!d.notes) d.notes = {}; return d.notes; }

/** The notes that mention an item (its chip or its ID), across every project: [{code, note}].
    @param {string} id @returns {{code: string, note: NoteSummary}[]} */
export function notesMentioning(id) {
  const out = [];
  for (const [code, L] of Object.entries(allNotes())) for (const n of L || []) if ((n.items || []).includes(id)) out.push({ code, note: n });
  return out;
}

/** Keep a note's summary in the page's data and in the open list. @param {string} code @param {NoteSummary} n */
function keepSummary(code, n) {
  const all = allNotes(), L = (all[code] || []).filter(x => x.path !== n.path);
  all[code] = sortNotes([n, ...L]);
  if (notesCode.value === code) notesList.value = all[code];
}

/** Pinned first, then the most recently changed. @param {NoteSummary[]} L */
export const sortNotes = L => [...L].sort((a, b) => (Number(b.pinned) - Number(a.pinned)) || String(b.mod || b.updated).localeCompare(String(a.mod || a.updated)));

/** Show a project's notes: at once from the page's data, then fresh from the server. @param {string} code */
export async function loadNotes(code) {
  if (notesCode.value !== code) { notesQuery.value = ""; }
  notesCode.value = code;
  notesList.value = sortNotes(allNotes()[code] || []);
  if (!viaServer()) return;
  const r = await api("/api/notes/list", { code });
  if (r && r.ok && notesCode.value === code) { allNotes()[code] = r.notes; notesList.value = sortNotes(r.notes); }
}

/* ── the editing session ── */
/** `rev` counts every change, so a save knows whether Alan typed again while it was on its way; `sid` is the editing session's id
    (sent with every save, so the server keeps one backup per session); `renameOld` is the title the file was named for before
    the title was changed (the file is renamed when the title field is left, not at every autosave).
    @type {{getBody: (() => string|null) | null, changes: Record<string, any>, dirty: boolean, rev: number, saveT: any, busy: Promise<any> | null,
    sid: string, sidAt: number, renameOld: string | null, closing: Promise<boolean> | null, released: boolean}} */
const ses = { getBody: null, changes: {}, dirty: false, rev: 0, saveT: null, busy: null, sid: "", sidAt: 0, renameOld: null, closing: null, released: false };
/* `released`: the typing that could not be saved was copied out or its loss confirmed, so another note may be opened over it */

/** The open editor gives the store its body (null while nothing was typed). @param {(() => string|null) | null} f */
export function noteBodyFrom(f) { ses.getBody = f; }

let loads = 0;
const clock = () => new Date().toTimeString().slice(0, 5);

/** A new editing-session id: a UUID (the server takes 8 to 64 letters, digits and hyphens). */
function newSid() {
  try { if (crypto && crypto.randomUUID) return crypto.randomUUID(); } catch (e) { /* no crypto: a random one */ }
  return Array.from({ length: 32 }, () => Math.floor(Math.random() * 16).toString(16)).join("");
}
/** A fresh editing session: when a note is opened or made. */
function newSession() { ses.sid = newSid(); ses.sidAt = Date.now(); ses.renameOld = null; }
/** The id a save carries: the session's, or a new one when the last save was over 5 minutes ago (the server ends the session then too). */
function sessionId() {
  const now = Date.now();
  if (!ses.sid || now - ses.sidAt > SESSION_IDLE_MS) ses.sid = newSid();
  ses.sidAt = now;
  return ses.sid;
}

/** Whether the open note may be left for another (or closed): it is saved, or nothing was typed, or its text was copied out or
    its loss confirmed (`released`). Otherwise the reason is said and it stays: nothing is dropped silently. */
async function mayLeave() {
  if (await noteFlush() || ses.released || !noteCur.value) return true;
  notesMsg.value = notSavedMsg();
  return false;
}

/** Open a note (the current one is saved first, and is not left over text that could not be saved). Opening the open note again is
    a switch like any other, unless `discard`: "open the file's version", where what was typed in it goes (after giveUpTyping).
    @param {string} path @param {boolean} [discard] */
export async function openNote(path, discard = false) {
  if (!discard && !await mayLeave()) return false;
  if (!noteCur.value || noteCur.value.path !== path) { noteFind.value = false; noteFindP.value = 0; noteMarks.value = { markers: {}, hover: 0 }; }   /* BL-301 E: Find updates is per note */
  if (!viaServer()) { notesMsg.value = "Opening a note needs the live server."; return false; }
  const rev = ses.rev;
  noteLoading.value = true;
  const r = await api("/api/notes/get", { path });
  noteLoading.value = false;
  if (!r || !r.ok) { notesMsg.value = oneLine((r && r.message) || "That note couldn't be opened."); return false; }
  if (!discard && noteCur.value && (ses.rev !== rev || ses.dirty) && !ses.released) {   // typed in this note while the other (or it again) was on its way
    notesMsg.value = "You typed in this note while the other one was opening, so it stays open. Try again once it has saved.";
    return false;
  }
  notesMsg.value = "";
  resetTyping(); newSession();
  /** @type {OpenNote} */
  const cur = { path: r.note.path, code: r.code, note: r.note, body: r.body, meta: r.meta || {}, base: r.base, load: ++loads, images: r.images || {},
    sent: Array.isArray(r.sent) ? r.sent : [] };
  noteCur.value = cur;
  noteSave.value = { state: "" };
  return true;
}

/** What was typed is given up (copied out, or its loss confirmed): nothing is sent for it. */
function giveUpTyping() { clearTimeout(ses.saveT); ses.dirty = false; ses.changes = {}; ses.released = true; ses.rev++; }

/** Nothing typed is waiting any more (a note was opened or made, or its typing was given up). */
function resetTyping() { clearTimeout(ses.saveT); ses.changes = {}; ses.dirty = false; ses.released = false; ses.rev++; }

/** Why another note isn't opened while this one couldn't be saved. */
const notSavedMsg = () => `${noteSave.value.msg || "The note isn't saved."} It stays open so your typing isn't lost: copy it, open the file's version or discard it.`;

/** Close the open note (after saving it). It stays open, and false is returned, when it couldn't be saved. */
export async function closeNote() {
  if (!await mayLeave()) return false;
  resetTyping(); noteFocus.value = false; noteLeave.value = null; noteCur.value = null; noteSave.value = { state: "" };
  return true;
}

/** The save is due AUTOSAVE_MS from now (`ms` to wait longer). Typing again moves it. @param {number} [ms] */
function saveSoon(ms = AUTOSAVE_MS) { clearTimeout(ses.saveT); ses.saveT = setTimeout(() => { noteFlush(false); }, ms); }

/** Alan typed in the note: the file is written AUTOSAVE_MS after the last key. */
export function noteTyped() {
  if (!noteCur.value) return;
  ses.dirty = true; ses.released = false; ses.rev++;
  if (noteSave.value.state === "conflict") return;           // the file changed outside creaite: nothing is written until Alan chooses
  noteSave.value = { state: "typing" };
  saveSoon();
}

/** Change the note's front matter (title, tags, pinned, confidential, date, with): saved like typing.
    @param {Record<string, any>} changes @param {boolean} [now] save at once (a toggle) */
export function noteMeta(changes, now) {
  const c = noteCur.value;
  if (!c) return;
  ses.changes = { ...ses.changes, ...changes };
  noteCur.value = { ...c, meta: { ...c.meta, ...changes } };
  if (now) { ses.dirty = true; ses.rev++; noteFlush(); } else noteTyped();
}

const body = () => { try { return ses.getBody ? ses.getBody() : null; } catch (e) { return null; } };
/** The text Alan sees in the note, as Markdown: what "Copy my text" copies. */
export function noteText() { const c = noteCur.value, b = body(); return b ?? (c ? c.body : "") ?? ""; }

/** Write the note's file now, if anything changed. Returns whether it is saved (or nothing needed saving). `final` is false for the
    timer: only a flush Alan caused (leaving, switching, a toggle, the title field's end) also renames the file for a new title.
    @param {boolean} [final] */
export async function noteFlush(final = true) {
  clearTimeout(ses.saveT);
  while (ses.busy) await ses.busy;                           // one save at a time: the next sends the text as it is by then
  const c = noteCur.value;
  if (!c) return true;
  if (!ses.dirty) return final ? settleAndRecheck() : true;
  if (!viaServer()) { noteSave.value = { state: "error", msg: "Not saved: the live server isn't running. Your typing is still here." }; return false; }
  const sent = { ...ses.changes }, b = body(), rev = ses.rev, oldTitle = c.note.title;
  noteSave.value = { state: "saving" };
  ses.busy = api("/api/notes/save", { path: c.path, body: b, changes: sent, base: c.base, session: sessionId() }).catch(() => null);
  let r;
  try { r = await ses.busy; } finally { ses.busy = null; }
  if (r && r.ok) {
    if (ses.rev === rev) ses.dirty = false;                  // typed again while it was on its way: still to save
    for (const k of Object.keys(sent)) if (ses.changes[k] === sent[k]) delete ses.changes[k];
    const now = noteCur.value;
    if (now && now.path === c.path) noteCur.value = { ...now, note: r.note, base: r.base, body: b ?? now.body };
    keepSummary(c.code, r.note);
    noteSave.value = ses.dirty ? { state: "typing" } : { state: "saved", at: clock() };
    if (ses.dirty) saveSoon();
    if (sent.title !== undefined && !r.unchanged && ses.renameOld === null) ses.renameOld = oldTitle;
    if (final && ses.dirty) return noteFlush(true);          // leaving: what was typed meanwhile goes too
    return final ? settleAndRecheck() : true;
  }
  if (r && r.conflict) { noteSave.value = { state: "conflict", msg: oneLine(r.message) }; return false; }
  if (r && r.wait) { noteSave.value = { state: "wait", msg: oneLine(r.message) }; saveSoon(WAIT_RETRY_MS); return false; }
  noteSave.value = { state: "error", msg: oneLine((r && r.message) || "Not saved.") };
  return false;
}

/** After a flush Alan caused: the file is renamed for a new title, and anything typed while that was on its way is saved too. */
async function settleAndRecheck() {
  await settleRename();
  return ses.dirty ? noteFlush(true) : true;
}

/** A saved title that differs from the file's name: rename the file now (after the title field is left, or the note is). */
async function settleRename() {
  const c = noteCur.value, old = ses.renameOld;
  if (!c || old === null || ses.dirty) return;
  ses.renameOld = null;
  ses.busy = renameToTitle(c.code, c.path, c.base, old).catch(() => { notesMsg.value = "The file could not be renamed for the new title."; });
  try { await ses.busy; } finally { ses.busy = null; }
}

/** A request body over this many characters can't ride a keepalive fetch (browsers cap them at about 64 KB). */
const KEEPALIVE_MAX = 60000;

/** The page is going away: write the note with a request that outlives it (it carries the session id too). It is not counted as
    saved until the server says so; a body too big for a keepalive request goes as an ordinary one (the window hiding flushes first). */
export function noteFlushOnExit() {
  const c = noteCur.value;
  if (!c || !ses.dirty || !viaServer()) return;
  const rev = ses.rev;
  try {
    const text = JSON.stringify({ path: c.path, body: body(), changes: ses.changes, base: c.base, session: sessionId() });
    fetch("/api/notes/save", { method: "POST", keepalive: text.length <= KEEPALIVE_MAX, headers: { "Content-Type": "application/json", "X-Creaite-Token": /** @type {any} */ (D).token || "" },
      body: text }).then(r => r.json()).then(r => {
      if (!r || !r.ok) return;
      const now = noteCur.value;
      if (now && now.path === c.path) noteCur.value = { ...now, base: r.base, note: r.note };
      if (ses.rev === rev) ses.dirty = false;
    }).catch(() => { /* the page is going; the text stays dirty here until it has */ });
  } catch (e) { /* the page is going; nothing more to do */ }
}

/** Whether leaving the page now would lose typing that could not be saved (the file changed outside creaite, an error, a wait). */
export function noteUnsavedAtExit() { return ses.dirty && ["conflict", "error", "wait"].includes(noteSave.value.state); }

/** Make a note from a template; it opens once made.
    @param {string} code @param {{template: string, title: string, date?: string, with?: string[]}} o */
export async function createNote(code, o) {
  if (!await mayLeave()) return null;
  if (!viaServer()) { notesMsg.value = "Making a note needs the live server."; return null; }
  const rev = ses.rev;
  const r = await api("/api/notes/new", { code, ...o });
  if (!r || !r.ok) { notesMsg.value = oneLine((r && r.message) || "The note wasn't made."); return null; }
  keepSummary(code, r.note);
  if (noteCur.value && (ses.rev !== rev || ses.dirty) && !ses.released) {   // typed in the open note while the new one was being made
    notesMsg.value = `The note ${r.note.title} was made (it is in the list), but you typed in this one meanwhile, so it stays open.`;
    return null;
  }
  resetTyping(); newSession();
  noteCur.value = { path: r.note.path, code, note: r.note, body: r.body, meta: r.meta || {}, base: r.base, load: ++loads, images: {} };
  noteSave.value = { state: "saved", at: clock() };
  return r.note;
}

/** Whether the open note has typing not yet written to its file. */
export const noteDirty = () => ses.dirty;

/* ── leaving focus mode (#119 closing rules; Esc, a click on the scrim and the leave icon all come here) ── */
/** What had focus when focus mode opened (the expand button), to give it back. @type {Element | null} */
let focusOpener = null;

/** Lift the open note over the page. @param {Element | null} [opener] the control that opened it */
export function noteFocusOpen(opener) {
  if (!noteCur.value || noteFocus.value) return;
  focusOpener = opener || document.activeElement;
  noteFocus.value = true;
}

/** Overlays over the note that Esc closes, topmost first: each closes its overlay and returns true, or returns false when it isn't open.
    The AI suggestion and bar are listed by the Notes page; a link popover (#120) adds itself here. Pickers, menus and the date pop-up
    take Esc themselves before it ever reaches focus mode. */
export const noteEscLayers = /** @type {(() => boolean)[]} */ ([]);
/** Esc in focus mode: close the topmost overlay, if any is open; returns whether one was. */
export function noteEscape() {
  for (const close of noteEscLayers) if (close()) return true;
  return false;
}

/** Focus goes back to the control that opened focus mode, else the note's title. When the "couldn't save" dialog is still closing
    (the shared Dialog gives focus back to what had it), this waits for it to finish, so the last word is ours. */
function focusBack() {
  const o = focusOpener; focusOpener = null;
  const back = () => setTimeout(() => {
    const t = /** @type {HTMLElement | null} */ (o && o.isConnected && o !== document.body ? o : document.getElementById("noteTitle"));
    if (t && typeof t.focus === "function") t.focus();
  }, 0);
  const d = /** @type {HTMLDialogElement | null} */ (document.getElementById("noteLeaveDlg"));
  if (d && d.open) d.addEventListener("close", back, { once: true }); else back();
}
function leftFocus() {
  noteLeave.value = null;
  if (!noteFocus.value) return;                              // (a double click on Save again comes here twice: the second finds it left)
  noteFocus.value = false; focusBack();
}

/** THE way out of focus mode: the autosave is flushed first; saved (or nothing to save) means it closes with no question; a save that
    failed or was refused (the file changed outside creaite, the server not reachable, a wait) keeps the note open and asks (noteLeave).
    Returns whether it closed. Two calls at once (Esc twice) are one. */
export function noteFocusClose() {
  if (!noteFocus.value || noteLeave.value) return Promise.resolve(false);
  if (ses.closing) return ses.closing;
  ses.closing = (async () => {
    const ok = await noteFlush(true);
    ses.closing = null;
    if (ok && noteFocus.value) { leftFocus(); return true; }
    if (!ok && noteFocus.value) noteLeave.value = {};
    return ok;
  })();
  return ses.closing;
}
/** The dialog's "Keep editing": it closes, the note stays open with the cursor back in it. (In the discard question, Esc and Cancel go
    back to the first question, or close it when it was asked from the banner.) */
export function noteLeaveKeep() {
  const q = noteLeave.value;
  if (q && q.confirm && q.back) { noteLeave.value = {}; return; }
  noteLeave.value = null;
  setTimeout(() => { const ed = /** @type {any} */ (document.querySelector(".ndoc .nbody")); if (ed && ed.cxed) ed.cxed.focus(); }, 0);
}
/** Put the note's typed text on the clipboard. Returns whether it worked; once it has, the typing is safe, so another note may be
    opened over a save that cannot work (a deleted file, a server that stays down). */
export async function noteCopyText() {
  const t = noteText();
  let ok = false;
  try { await navigator.clipboard.writeText(t); ok = true; } catch (e) { /* the old way, below */ }
  if (!ok) {
    try {
      const ta = document.createElement("textarea");
      ta.value = t; ta.setAttribute("readonly", ""); ta.style.cssText = "position:fixed;left:-9999px;top:0";
      (document.querySelector("dialog[open]") || document.body).appendChild(ta);
      ta.select(); ok = document.execCommand("copy"); ta.remove();
    } catch (e) { ok = false; }
  }
  if (ok) ses.released = true;
  return ok;
}
/** The dialog's "Copy my text then close": the typed text goes to the clipboard, then focus mode closes. If it couldn't be
    copied the dialog stays, so nothing is dropped. */
export async function noteLeaveCopy() {
  if (!await noteCopyText()) { noteLeave.value = { copyFailed: true }; return false; }
  leftFocus();
  return true;
}
/** The dialog's "Save again": the same flush; it closes when it works, and says so again when it doesn't. */
export async function noteLeaveRetry() {
  const ok = await noteFlush(true);
  if (ok) { leftFocus(); return true; }
  if (noteFocus.value) noteLeave.value = {};
  return false;
}

/** "Discard my typing": the question (inside the dialog) before it. `back` is true when it was asked from the dialog's first question. @param {boolean} [back] */
export function noteDiscardAsk(back = false) { noteLeave.value = { confirm: true, back }; }
/** Discard what was typed and could not be saved: the note shows the file's version again (or closes, when the file is gone). */
export async function noteDiscardNow() {
  const c = noteCur.value;
  if (!c) { noteLeave.value = null; return; }
  giveUpTyping();
  const ok = await openNote(c.path, true);
  if (!ok) { noteCur.value = null; noteSave.value = { state: "" }; resetTyping(); noteFocus.value = false; notesMsg.value = "That note couldn't be opened again, so it was closed. What you typed was discarded."; }
  noteLeave.value = null;
  if (noteFocus.value && !noteCur.value) noteFocus.value = false;
}
/** "Open the file's version" from the leave dialog: the same as the banner's button (the note is opened again from its file). */
export async function noteOpenFileVersion() {
  const c = noteCur.value;
  if (!c) return;
  giveUpTyping();
  await openNote(c.path, true);
  noteLeave.value = null;
}

/* ── BL-301 E in the Notes tab: Find updates beside the open note, its markers, and opening a note at a line ── */
/** Whether the Find updates panel takes the note's right-hand column. */
export const noteFind = signal(false);
/** BL-301 D in the Notes tab: the one line Find updates looks at (AI › Make this an action…), or 0 for every new line. */
export const noteFindP = signal(0);
/** The panel's markers on the note's lines ({line: number}) and the hovered line, drawn by the editor as decorations. */
export const noteMarks = signal(/** @type {{markers: Record<number, number>, hover: number}} */ ({ markers: {}, hover: 0 }));
/** BL-301 B: after a Find updates apply or its Undo, the open note's margin ticks follow (the server's notes.sent_ids).
    @param {string} path @param {SentLine[] | undefined} sent */
export function noteSetSent(path, sent) {
  const c = noteCur.value;
  if (c && c.path === path && Array.isArray(sent)) noteCur.value = { ...c, sent };
}
/** A note to open at a line, highlighted (a source link "…/08 Notes/<title>.md#p4"). */
export const noteFlash = signal(/** @type {{path: string, line: number}} */ ({ path: "", line: 0 }));

const LIST_ITEM = /^(?:[-*+]|\d{1,3}[.)])\s/;
/** The note's lines as Find updates numbers them (notes.paragraphs in notes.py): blocks separated by blank lines, and each
    top-level list item its own line. @param {string} md @returns {string[]} the lines' texts, line n at index n - 1 */
export function noteLines(md) {
  const out = [], buf = /** @type {string[]} */ ([]);
  const flush = () => { if (buf.length) { out.push(buf.join("\n")); buf.length = 0; } };
  for (const ln of String(md || "").split("\n").concat([""])) {
    if (!ln.trim()) flush();
    else if (buf.length && LIST_ITEM.test(ln) && LIST_ITEM.test(buf[0])) { flush(); buf.push(ln); }
    else buf.push(ln);
  }
  return out;
}
/* ===== BL-301 B gaps (v20-notes-gaps): pictures, and a renamed title renames the file ===== */
/** The last rename: the old and new stored paths (the page writes the new one in its address). */
export const noteRenamed = signal(/** @type {{from: string, to: string} | null} */ (null));

/** A picture of the open note for the editor: its data URL by reference (`_images/<name>`). @param {string} ref */
export const noteImageSrc = ref => (noteCur.value && noteCur.value.images || {})[ref] || null;

/** Add a picture to the open note: checked (PNG or JPEG, 2 MB at most), created at once in the notes folder's _images/ through
    filechange.py by the live server. Returns its reference, or null (and says why). @param {File} file */
export async function addNoteImage(file) {
  const c = noteCur.value;
  if (!c) return null;
  if (!/^image\/(png|jpeg)$/.test(file.type)) { notesMsg.value = `${file.name} can't be added: only PNG or JPEG pictures.`; return null; }
  if (file.size > 2 * 1024 * 1024) { notesMsg.value = `${file.name} is over 2 MB: pictures can be 2 MB at most.`; return null; }
  if (!viaServer()) { notesMsg.value = "Adding a picture needs the live server."; return null; }
  const src = await new Promise(res => { const fr = new FileReader(); fr.onload = () => res(String(fr.result || "")); fr.onerror = () => res(""); fr.readAsDataURL(file); });
  const r = src ? await api("/api/notes/image", { path: c.path, name: file.name, data: src.slice(src.indexOf(",") + 1) }) : null;
  if (!r || !r.ok) { notesMsg.value = oneLine((r && r.message) || `${file.name} couldn't be added.`); return null; }
  notesMsg.value = "";
  const now = noteCur.value;
  if (now) { if (!now.images) now.images = {}; now.images[r.ref] = src; }
  return /** @type {string} */ (r.ref);
}

/** After a save that changed the title: the file is renamed to match, and links to it in other notes follow (the server does
    both through filechange.py). Notes it couldn't change are named, to fix by hand.
    @param {string} code @param {string} path @param {string} base @param {string} old */
async function renameToTitle(code, path, base, old) {
  const r = await api("/api/notes/rename", { path, base, old });
  if (!r || !r.ok) { if (r && r.message) notesMsg.value = oneLine(r.message); return; }
  if (!r.renamed) return;
  const all = allNotes();
  all[code] = (all[code] || []).filter(x => x.path !== r.from);
  keepSummary(code, r.note);
  const now = noteCur.value;
  if (now && now.path === r.from) noteCur.value = { ...now, path: r.note.path, note: r.note, base: r.base };
  noteRenamed.value = { from: r.from, to: r.note.path };
  const changed = (r.relinked || []).length, listed = /** @type {{title: string, why: string}[]} */ (r.listed || []);
  notesMsg.value = `Renamed the file to ${r.note.file}.` + (changed ? ` ${changed === 1 ? "One link" : `${changed} links`} to it changed.` : "") +
    (listed.length ? ` Not changed, fix by hand: ${listed.map(x => `${x.title} (${x.why})`).join("; ")}.` : "");
  /** Refresh one project's summaries quietly (its links changed). @param {string} cc */
  const refresh = async cc => { const L = await api("/api/notes/list", { code: cc }); if (L && L.ok) { all[cc] = L.notes; if (notesCode.value === cc) notesList.value = sortNotes(L.notes); } };
  if (changed) for (const cc of Object.keys(all)) if ((all[cc] || []).some(x => (r.relinked || []).includes(x.path))) refresh(cc);
}
/* ===== end BL-301 B gaps ===== */
