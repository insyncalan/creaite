// @ts-check
/* DeleteNote (#124, Alan 15-10-2026): "Delete note…", last in the note's … menu. Two steps, and both always show:
   1. this confirm box, naming the note (Cancel is the default; Esc and a click outside cancel);
   2. on Delete note, the live server puts the note's move into its own engagement's (or the portfolio's) 99 Archive on the one
      approval card in ask creaite (/api/notes/delete). Only Approve there moves it (tracker.py apply, the BL-09 guard exception);
      Reject leaves it where it is. The confirm box never replaces the card.
   On Approve the note closes, the list drops it and a toast says "Moved … to the archive" with Undo (tracker.py undo of that
   apply). Files › Archived lists it with Move back. Links to it in other notes show as missing until it is back. A confidential
   note is deleted the same way: nothing of its text is sent anywhere. Text only through JSX.
   While the card waits the note is read only here (noteHeld); on Approve the server checks again that the note is the version
   confirmed, with no typing waiting (another window's included), and moves nothing if not: "Delete it again". */
import { signal } from "@preact/signals";
import { navWrite } from "../../core/nav.js";
import { api, oneLine, reloadData, snack, viaServer } from "../../core/server.js";
import { serverCardFlow } from "../../ask.js";
import { loadNotes, noteCur, noteFlush, noteGone, noteHeld, notesCode, notesMsg } from "../../stores/notes.js";
import { Dialog } from "../Dialog.jsx";

/** The note the confirm box asks about, or null when it is closed. `base` (a row that is not open: the text's version read when the box
    OPENED, so the server's edit-conflict check covers what happened since) and `next` (the row after it, for focus) are set for a row.
    @typedef {{path: string, title: string, code: string, base?: string, row?: boolean, next?: string}} Deleting
    @type {import("@preact/signals").Signal<Deleting | null>} */
export const noteDeleting = signal(/** @type {Deleting | null} */ (null));

/** Focus goes back to the list row (a row's menu was used, #194), or to the row after it when it has gone, else the list.
    @param {string} path @param {string} [next] */
function focusRow(path, next) {
  setTimeout(() => {
    const rows = /** @type {HTMLElement[]} */ ([...document.querySelectorAll(".nlist .ni")]);
    const el = rows.find(x => x.dataset.path === path) || rows.find(x => x.dataset.path === next) || document.getElementById("notesListBody");
    if (el) el.focus({ preventScroll: true });
  }, 80);                                          // after the dialog has given up its own focus handling
}
/** Close the confirm box without deleting. */
function closeBox() { const n = noteDeleting.value; noteDeleting.value = null; if (n && n.row) focusRow(n.path, n.next); }
/** Whether the confirm box's Delete note is working (the card is being made). */
const busy = signal(false);

/** Open the confirm box for the open note, or (#194) for a note in the list given as `row` (a note that is not open is not touched).
    @param {{path: string, title: string, code: string}} [row] */
export async function askDeleteNote(row) {
  if (row && !(noteCur.value && noteCur.value.path === row.path)) {      // #194: a note in the list that is not the open one: the open note is left alone
    if (!viaServer()) { snack("Deleting a note needs the live server"); return; }
    const rows = /** @type {HTMLElement[]} */ ([...document.querySelectorAll(".nlist .ni")]), at = rows.findIndex(x => x.dataset.path === row.path);
    const near = at >= 0 ? rows[at + 1] || rows[at - 1] : undefined, next = near ? near.dataset.path : undefined;
    const g = await api("/api/notes/get", { path: row.path });         // the version the box is opened on: Delete sends THIS one, so a note changed since is refused
    if (!g || !g.ok) { snack(oneLine((g && g.message) || "That note couldn't be read.")); focusRow(row.path, next); return; }
    noteDeleting.value = { path: row.path, title: row.title, code: row.code, base: g.base, row: true, next };
    return;
  }
  const c = noteCur.value;
  if (!c) return;
  if (!viaServer()) { snack("Deleting a note needs the live server"); return; }
  /* The menu item that was used goes with the closed menu, so make the … button the dialog's recorded opener: Esc and Cancel
     then return focus to it (Dialog.jsx restores only an opener that is still connected). */
  const more = /** @type {HTMLElement | null} */ (document.querySelector(".nmorewrap .nmore"));
  if (more) more.focus();
  noteDeleting.value = { path: c.path, title: c.note.title, code: c.code };
}

/** After Delete note in the confirm box: save the note, ask for the card, and answer it in ask creaite.
    @param {Deleting} n */
export async function deleteNote(n) {
  busy.value = true;
  try {
    const open = !!(noteCur.value && noteCur.value.path === n.path);
    if (open && !(await noteFlush())) { noteDeleting.value = null; notesMsg.value = "Not deleted: the note isn't saved yet (the line in its header says why)."; return false; }
    const cur = noteCur.value;
    let base = cur && cur.path === n.path ? cur.base : "";
    if (!open) base = n.base || "";                      // not the open note: the version from when the box opened (the server refuses a note changed since)
    const r = await api("/api/notes/delete", { path: n.path, base });
    noteDeleting.value = null;
    if (n.row) focusRow(n.path, n.next);
    if (!r || !r.ok || !r.card) { snack(oneLine((r && r.message) || "Not deleted.")); return false; }
    snack(oneLine(r.message));
    const done = await watchCard(n, r.card);
    if (n.row) focusRow(n.path, n.next);
    return done;
  } finally { busy.value = false; }
}

const KEY = "creaite.noteDelete";
/** @param {any} v */
function remember(v) { try { if (v) sessionStorage.setItem(KEY, JSON.stringify(v)); else sessionStorage.removeItem(KEY); } catch (e) { return; /* no storage: a reload then shows the plain card */ } }

/** Hold the note read only while its card waits, then close it on Approve (or let it be edited again on Reject or expiry).
    Used by the first answer and by a card the page finds again after a reload.
    @param {{path: string, title: string, code: string}} n @param {any} card */
async function watchCard(n, card) {
  remember({ ...n, card: card.card });
  const unhold = () => { if (noteHeld.value === n.path) noteHeld.value = null; };
  noteHeld.value = n.path;                            /* read only while the card waits */
  const left = Date.parse(card.expires || "") - Date.now();
  const t = setTimeout(unhold, Number.isFinite(left) && left > 0 ? left : 30 * 60000);
  let done;
  try { done = await serverCardFlow(card, { onStale: unhold }); } finally { clearTimeout(t); unhold(); remember(null); }   /* only Approve moves it */
  if (!done) return false;
  if (noteCur.value && noteCur.value.path === n.path) { noteGone(n.path); navWrite(false); }   /* its file has gone: nothing to save */
  await loadNotes(notesCode.value || n.code);
  const id = done.apply;
  snack(`Moved “${n.title}” to the archive`, id ? async () => {
    const u = await api("/api/undo", { apply_id: id });
    snack(undoWords(u, n.title));
    if (u && u.ok) { await reloadData(); await loadNotes(notesCode.value || n.code); }
  } : null);
  return true;
}

/* After a reload the card is still waiting on the server: pendingEdit asks this first. True when the card is a note's delete
   this tab started, which is then watched exactly as the first time (read only, closed on Approve). */
export function resumeDeleteNote(/** @type {any} */ card) {
  let v = null;
  try { v = JSON.parse(sessionStorage.getItem(KEY) || "null"); } catch (e) { v = null; }
  if (!v || v.card !== card.card || !v.path) return false;
  watchCard({ path: v.path, title: v.title, code: v.code }, card);
  return true;
}

/** The new name in "restored <from> as <name>": <from> is a path, <name> has no slash and is <from>'s name with -2 and so on
    put before its extension, so split at the " as " that makes that true (a note called "Plan as built" has two).
    @param {string} s */
function renamedTo(s) {
  const tail = s.slice(s.lastIndexOf("/") + 1);
  const at = [];
  for (let i = tail.indexOf(" as "); i >= 0; i = tail.indexOf(" as ", i + 1)) at.push(i);
  for (const i of at) {
    const from = tail.slice(0, i), name = tail.slice(i + 4), dot = from.lastIndexOf(".");
    const stem = dot > 0 ? from.slice(0, dot) : from, ext = dot > 0 ? from.slice(dot) : "";
    if (name.startsWith(stem + "-") && name.endsWith(ext) && /^\d+$/.test(name.slice(stem.length + 1, name.length - ext.length))) return name;
  }
  return at.length ? tail.slice(at[at.length - 1] + 4) : tail;
}

/** What the toast says after Undo, from tracker._reverse_move's lines: back; back under another name; the archived note has
    gone; a note has the name (switch off); or, for any other line, a neutral pointer. Exported for the tests.
    @param {any} u /api/undo's answer @param {string} title */
export function undoWords(u, title) {
  if (!u || !u.ok) return oneLine((u && u.message) || "Not undone");
  const moves = /** @type {string[]} */ (u.moves || []);
  const TOOK = ": a note took its name";
  const took = moves.find(m => m.startsWith("restored ") && m.endsWith(TOOK));
  if (took) return `Restored “${title}” as ${renamedTo(took.slice(9, took.length - TOOK.length))}: a note has its old name`;
  if (moves.some(m => m.startsWith("skipped moving ") && m.endsWith(" back: it isn't there"))) return "Not restored: the archived note is no longer there";
  if (moves.some(m => m.startsWith("skipped moving ") && m.endsWith(" is there again"))) return "Not restored: a note with that name exists";
  if (moves.length) return "Undo did not restore the note: see Files › Archived";
  return `“${title}” is back in its notes folder`;
}

/** The confirm box. */
export function DeleteNoteDialog() {
  const n = noteDeleting.value;
  const where = n && n.code === "_portfolio" ? "the portfolio's archive" : "this project's archive";
  return (
    <Dialog open={!!n} onClose={() => { if (!busy.value) closeBox(); }} labelledBy="ndelH" describedBy="ndelP" id="noteDelDlg" focus="#ndelCancel" class="ndel">
      {n ? <div class="ndelbox">
        <h2 id="ndelH">Delete “{n.title}”?</h2>
        <p id="ndelP">It moves to {where}, not away for good. Restore it any time from Files › Archived. Anything that links to it shows the link as missing until it is restored.</p>
        <p class="sub">The move then waits on the approval card in ask creaite: nothing moves until you approve it there.</p>
        <div class="nnfoot">
          <button type="button" class="btn" id="ndelCancel" onClick={() => closeBox()} disabled={busy.value}>Cancel</button>
          <button type="button" class="btn danger" id="ndelGo" disabled={busy.value} onClick={() => deleteNote(n)}>{busy.value ? "Working…" : "Delete note"}</button>
        </div>
      </div> : null}
    </Dialog>);
}
