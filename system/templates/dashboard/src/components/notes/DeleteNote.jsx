// @ts-check
/* DeleteNote (#124, Alan 15-10-2026): "Delete note…", last in the note's … menu. Two steps, and both always show:
   1. this confirm box, naming the note (Cancel is the default; Esc and a click outside cancel);
   2. on Delete note, the live server puts the note's move into its own engagement's (or the portfolio's) _Archive on the one
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

/** The note the confirm box asks about, or null when it is closed. @type {import("@preact/signals").Signal<{path: string, title: string, code: string} | null>} */
export const noteDeleting = signal(/** @type {{path: string, title: string, code: string} | null} */ (null));
/** Whether the confirm box's Delete note is working (the card is being made). */
const busy = signal(false);

/** Open the confirm box for the open note. */
export function askDeleteNote() {
  const c = noteCur.value;
  if (!c) return;
  if (!viaServer()) { snack("Deleting a note needs the live server"); return; }
  noteDeleting.value = { path: c.path, title: c.note.title, code: c.code };
}

/** After Delete note in the confirm box: save the note, ask for the card, and answer it in ask creaite.
    @param {{path: string, title: string, code: string}} n */
export async function deleteNote(n) {
  busy.value = true;
  try {
    if (!(await noteFlush())) { noteDeleting.value = null; notesMsg.value = "Not deleted: the note isn't saved yet (the line in its header says why)."; return false; }
    const cur = noteCur.value;
    const r = await api("/api/notes/delete", { path: n.path, base: cur && cur.path === n.path ? cur.base : "" });
    noteDeleting.value = null;
    if (!r || !r.ok || !r.card) { snack(oneLine((r && r.message) || "Not deleted.")); return false; }
    snack(oneLine(r.message));
    const unhold = () => { if (noteHeld.value === n.path) noteHeld.value = null; };
    noteHeld.value = n.path;                            /* read only while the card waits */
    const left = Date.parse(r.card.expires || "") - Date.now();
    const t = setTimeout(unhold, Number.isFinite(left) && left > 0 ? left : 30 * 60000);
    let done;
    try { done = await serverCardFlow(r.card, { onStale: unhold }); } finally { clearTimeout(t); unhold(); }   /* only Approve moves it */
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
  } finally { busy.value = false; }
}

/** What the toast says after Undo: back, back under another name, or not back (a note has the name). Exported for the tests.
    @param {any} u /api/undo's answer @param {string} title */
export function undoWords(u, title) {
  if (!u || !u.ok) return oneLine((u && u.message) || "Not undone");
  const moves = /** @type {string[]} */ (u.moves || []);
  const as = moves.map(m => /^restored .* as (.+): a note took its name$/.exec(m)).find(Boolean);
  if (as) return `Restored “${title}” as ${as[1]}: a note has its old name`;
  if (moves.some(m => m.startsWith("skipped moving"))) return "Not restored: a note with that name exists";
  return `“${title}” is back in its notes folder`;
}

/** The confirm box. */
export function DeleteNoteDialog() {
  const n = noteDeleting.value;
  const where = n && n.code === "_portfolio" ? "the portfolio's archive" : "this project's archive";
  return (
    <Dialog open={!!n} onClose={() => { if (!busy.value) noteDeleting.value = null; }} labelledBy="ndelH" describedBy="ndelP" id="noteDelDlg" focus="#ndelCancel" class="ndel">
      {n ? <div class="ndelbox">
        <h2 id="ndelH">Delete “{n.title}”?</h2>
        <p id="ndelP">It moves to {where}, not away for good. Restore it any time from Files › Archived. Anything that links to it shows the link as missing until it is restored.</p>
        <p class="sub">The move then waits on the approval card in ask creaite: nothing moves until you approve it there.</p>
        <div class="nnfoot">
          <button type="button" class="btn" id="ndelCancel" onClick={() => { noteDeleting.value = null; }} disabled={busy.value}>Cancel</button>
          <button type="button" class="btn danger" id="ndelGo" disabled={busy.value} onClick={() => deleteNote(n)}>{busy.value ? "Working…" : "Delete note"}</button>
        </div>
      </div> : null}
    </Dialog>);
}
