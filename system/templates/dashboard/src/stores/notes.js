// @ts-check
/* stores/notes.js (BL-301 B, BL-256): the Notes tab's state. One store per area (dev/COMPONENTS.md §2).

   A project's notes (or the portfolio's) are listed from the dashboard's data (D.notes: front matter and references, never text)
   and refreshed from the live server (/api/notes/list). An open note is editable: as Alan types, a draft is kept in
   system/staging/drafts/notes/ (/api/notes/draft, a second after the last key), and the file is written once per editing session
   through filechange.py (/api/notes/save: backed up, logged, undoable): when he leaves the note, or after 30 seconds without
   typing. "Saved" shows in the note's header. A note changed outside creaite since it was opened is never overwritten. */
import { signal } from "@preact/signals";
import { D } from "../core/page.js";
import { api, oneLine, viaServer } from "../core/server.js";

/** @typedef {{path: string, file: string, title: string, created: string, updated: string, tags: string[], pinned: boolean,
    confidential: boolean, date: string, with: string[], kind: string, mod: string, links: string[], items: string[],
    people: string[], p?: string}} NoteSummary */
/** @typedef {{path: string, code: string, note: NoteSummary, body: string, meta: Record<string, any>, base: string,
    restored?: boolean, stale?: {body: string, at: string} | null, load: number, images?: Record<string, string>,
    sent?: SentLine[]}} OpenNote */
/** @typedef {{p: number, ids: string[], text: string}} SentLine  a line Find updates already sent (notes.sent_ids): the margin tick */
/** @typedef {{state: ""|"typing"|"saving"|"saved"|"draft"|"wait"|"conflict"|"error", at?: string, msg?: string}} SaveState */

export const IDLE_MS = 30000;          // a session ends after 30 seconds without typing
export const DRAFT_MS = 1000;          // the draft is kept a second after the last key
const LIST_KEY = "creaite-notes-list-open";

export const notesCode = signal(/** @type {string | null} */ (null));
export const notesList = signal(/** @type {NoteSummary[]} */ ([]));
export const notesQuery = signal("");
export const noteCur = signal(/** @type {OpenNote | null} */ (null));
export const noteSave = signal(/** @type {SaveState} */ ({ state: "" }));
export const noteLoading = signal(false);
export const notesMsg = signal("");
/** #124: the stored path of a note whose Delete note waits on the approval card: read only until the card is answered. */
export const noteHeld = signal(/** @type {string | null} */ (null));

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
/** @type {{getBody: (() => string|null) | null, changes: Record<string, any>, dirty: boolean, draftT: any, idleT: any, busy: Promise<any> | null}} */
const ses = { getBody: null, changes: {}, dirty: false, draftT: null, idleT: null, busy: null };

/** The open editor gives the store its body (null while nothing was typed). @param {(() => string|null) | null} f */
export function noteBodyFrom(f) { ses.getBody = f; }

let loads = 0;
const clock = () => new Date().toTimeString().slice(0, 5);

/** Open a note (the current one is saved first). @param {string} path */
export async function openNote(path) {
  await noteFlush();
  if (!noteCur.value || noteCur.value.path !== path) { noteFind.value = false; noteFindP.value = 0; noteMarks.value = { markers: {}, hover: 0 }; }   /* BL-301 E: Find updates is per note */
  if (!viaServer()) { notesMsg.value = "Opening a note needs the live server."; return false; }
  noteLoading.value = true;
  const r = await api("/api/notes/get", { path });
  noteLoading.value = false;
  if (!r || !r.ok) { notesMsg.value = oneLine((r && r.message) || "That note couldn't be opened."); return false; }
  notesMsg.value = "";
  ses.changes = {}; ses.dirty = false;
  /** @type {OpenNote} */
  const cur = { path: r.note.path, code: r.code, note: r.note, body: r.body, meta: r.meta || {}, base: r.base, stale: null, load: ++loads, images: r.images || {},
    sent: Array.isArray(r.sent) ? r.sent : [] };
  const d = r.draft;
  if (d && !d.stale && (d.body !== null && d.body !== undefined && d.body !== r.body || Object.keys(d.changes || {}).length)) {
    cur.body = d.body ?? r.body; cur.restored = true; ses.changes = { ...(d.changes || {}) }; ses.dirty = true;
    cur.meta = { ...cur.meta, ...ses.changes };
  } else if (d && d.stale && d.body !== null && d.body !== undefined && d.body !== r.body) cur.stale = { body: d.body, at: d.at };
  noteCur.value = cur;
  noteSave.value = cur.restored ? { state: "draft", msg: "Restored what you typed before; it saves in a moment." } : { state: "" };
  if (cur.restored) idleSoon();
  return true;
}

/** Use the draft typed before the file changed outside creaite (it replaces the file's text when saved). */
export function useStaleDraft() {
  const c = noteCur.value;
  if (!c || !c.stale) return;
  noteCur.value = { ...c, body: c.stale.body, stale: null, restored: true, load: ++loads };
  ses.dirty = true; noteSave.value = { state: "draft", msg: "Your draft is back; it saves in a moment." }; idleSoon();
}
/** Keep the file as it is (the old draft is dropped at the next save). */
export function dropStaleDraft() { const c = noteCur.value; if (c) noteCur.value = { ...c, stale: null }; }

/** Close the open note (after saving it). */
export async function closeNote() { await noteFlush(); noteCur.value = null; noteSave.value = { state: "" }; }

/** #124: the note at `path` was moved to the archive: forget it without a save (its file has gone, so a save would only fail).
    @param {string} path */
export function noteGone(path) {
  if (noteHeld.value === path) noteHeld.value = null;
  if (!noteCur.value || noteCur.value.path !== path) return;
  clearTimeout(ses.draftT); clearTimeout(ses.idleT);
  ses.dirty = false; ses.changes = {};
  noteCur.value = null; noteSave.value = { state: "" };
}

function idleSoon() { clearTimeout(ses.idleT); ses.idleT = setTimeout(() => { noteFlush(); }, IDLE_MS); }

/** Alan typed in the note: keep a draft soon, and end the session after 30 seconds without typing. */
export function noteTyped() {
  if (!noteCur.value) return;
  ses.dirty = true;
  if (noteSave.value.state !== "conflict") noteSave.value = { state: "typing" };
  clearTimeout(ses.draftT); ses.draftT = setTimeout(keepDraft, DRAFT_MS);
  idleSoon();
}

/** Change the note's front matter (title, tags, pinned, confidential, date, with): saved like typing.
    @param {Record<string, any>} changes @param {boolean} [now] save at once (a toggle) */
export function noteMeta(changes, now) {
  const c = noteCur.value;
  if (!c) return;
  if (noteHeld.value === c.path) { notesMsg.value = "This note waits on the approval card to be deleted: answer the card first."; return; }
  ses.changes = { ...ses.changes, ...changes };
  noteCur.value = { ...c, meta: { ...c.meta, ...changes } };
  if (now) { ses.dirty = true; noteFlush(); } else noteTyped();
}

const body = () => { try { return ses.getBody ? ses.getBody() : null; } catch (e) { return null; } };

async function keepDraft() {
  const c = noteCur.value;
  if (!c || !ses.dirty || !viaServer()) return;
  const r = await api("/api/notes/draft", { path: c.path, body: body(), changes: ses.changes, base: c.base });
  if (r && r.ok && noteSave.value.state === "typing") noteSave.value = { state: "draft", msg: "Draft kept" };
}

/** End the editing session: write the note's file now, if anything changed. Returns whether it is saved. */
export async function noteFlush() {
  clearTimeout(ses.draftT); clearTimeout(ses.idleT);
  if (ses.busy) await ses.busy;
  const c = noteCur.value;
  if (!c || !ses.dirty) return true;
  if (!viaServer()) { noteSave.value = { state: "error", msg: "Not saved: the live server isn't running. Your typing is still here." }; return false; }
  const sent = { ...ses.changes }, b = body(), oldTitle = c.note.title;
  noteSave.value = { state: "saving" };
  ses.busy = api("/api/notes/save", { path: c.path, body: b, changes: sent, base: c.base });
  const r = await ses.busy; ses.busy = null;
  if (r && r.ok) {
    ses.dirty = false;
    for (const k of Object.keys(sent)) if (ses.changes[k] === sent[k]) delete ses.changes[k];
    const now = noteCur.value;
    if (now && now.path === c.path) noteCur.value = { ...now, note: r.note, base: r.base, body: b ?? now.body, restored: false };
    keepSummary(c.code, r.note);
    noteSave.value = { state: "saved", at: clock() };
    if (sent.title !== undefined && !r.unchanged) await renameToTitle(c.code, r.note.path, r.base, oldTitle);
    return true;
  }
  if (r && r.conflict) { noteSave.value = { state: "conflict", msg: oneLine(r.message) }; keepDraft(); return false; }
  if (r && r.wait) { noteSave.value = { state: "wait", msg: oneLine(r.message) }; keepDraft(); idleSoon(); return false; }
  noteSave.value = { state: "error", msg: oneLine((r && r.message) || "Not saved.") }; keepDraft();
  return false;
}

/** The page is going away: write the note with a request that outlives it. */
export function noteFlushOnExit() {
  const c = noteCur.value;
  if (!c || !ses.dirty || !viaServer()) return;
  try {
    fetch("/api/notes/save", { method: "POST", keepalive: true, headers: { "Content-Type": "application/json", "X-Creaite-Token": /** @type {any} */ (D).token || "" },
      body: JSON.stringify({ path: c.path, body: body(), changes: ses.changes, base: c.base }) });
    ses.dirty = false;
  } catch (e) { /* the draft is kept on the server */ }
}

/** Make a note from a template; it opens once made.
    @param {string} code @param {{template: string, title: string, date?: string, with?: string[]}} o */
export async function createNote(code, o) {
  await noteFlush();
  if (!viaServer()) { notesMsg.value = "Making a note needs the live server."; return null; }
  const r = await api("/api/notes/new", { code, ...o });
  if (!r || !r.ok) { notesMsg.value = oneLine((r && r.message) || "The note wasn't made."); return null; }
  keepSummary(code, r.note);
  ses.changes = {}; ses.dirty = false;
  noteCur.value = { path: r.note.path, code, note: r.note, body: r.body, meta: r.meta || {}, base: r.base, stale: null, load: ++loads, images: {} };
  noteSave.value = { state: "saved", at: clock() };
  return r.note;
}

/** Whether the open note has typing not yet written to its file. */
export const noteDirty = () => ses.dirty;

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
