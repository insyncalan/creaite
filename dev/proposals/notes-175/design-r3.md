# #175 design r3: Notes undo and redo, one Activity row per session

Design only (Alan, 17-10-2026 08:02Z). Supersedes r2's "Undo steps back one session". M1 (one Activity row per editing session)
is approved. Code read at `notes-136-r` b2908a5a (it holds #119's `notes-119-own` 629c599e).

## 1. Where undo lives today

- The note body is `NoteEditor.jsx` on `creaiteEditor()` (`core/editor.js`): Tiptap 3 / ProseMirror, vendored from
  `dev/tiptap/editor.js`. Undo and redo are StarterKit's history (`depth: 100`, `newGroupDelay: 500` ms); ⌘Z and ⌘⇧Z already work.
- **Autosave does not reset the stack now.** `noteFlush` (`stores/notes.js`) only posts `/api/notes/save` and replaces
  `noteCur` with the new `note`, `base` and `body`; `load` is unchanged, so `<NoteEditor key="n{load}">` and its
  `useEffect([loadKey])` keep the same editor. The redraws it triggers are zero-step `addToHistory: false` transactions, which
  ProseMirror's history ignores. The rename already keeps the editor (`test_a_title_rename_does_not_remount…`).
- **What gives a new, empty stack:** anything that bumps `load` (`openNote`: switching notes, reopening, "Open the file's version",
  Discard; `createNote`) and a page reload.
- **The gap against Alan's example:** ProseMirror merges a change into the previous step when it comes within 500 ms and touches
  it. "Delete a line, then retype at once" is therefore **one** step, and one ⌘Z takes back both.

## 2. The design (page only; nothing guarded)

1. **Step boundaries** (`NoteEditor.jsx`, a small `cxUndoSteps` extension passed only by Notes): a new undo step starts when
   - the change switches between deleting and inserting (Alan's case);
   - it is a paste, cut, drop, a picker choice (`[[`, `@`, `#`, `/`), an image, a template or an AI replacement (each its own step);
   - as today, after a 500 ms pause or a jump of the cursor.
   It calls ProseMirror's `closeHistory(tr)`, which the vendored bundle must export: one line in `dev/tiptap/editor.js`, rebuilt
   by `dev/tools/tiptap.py` (the pin and the round-trip gate unchanged).
2. **Depth** 100 → 500 steps for Notes (the `starterKit` configure in `creaiteEditor`, as `headShift` does today).
3. **Autosave never touches the editor.** Kept as a rule: `noteFlush`, `noteFlushOnExit`, `renameToTitle` and `noteMeta` must
   never change `load` or call `setValue`. An undo or redo is an ordinary change: it marks the note dirty and is autosaved in
   the same session (same id, same backup).
4. **Reopen and reload:** a reload loses the stack (as Word and Google Docs do; keeping it would put note text in browser
   storage, which creaite never does). Recommended: switching notes and back **within the page** keeps it: a cache of the last
   5 notes' editor states in memory, used only when the reopened file's `base` is the one last saved from that state; otherwise
   it is dropped and the stack starts empty.
5. **After an Activity Undo of the open note** (`ask.js` handler): flush first, undo, then reopen the note
   (`openNote(path, true)`), so the editor shows the restored file and its stack starts empty. Today the editor would keep the
   old text and hit a conflict on the next save.

## 3. Undo on a folded Activity row

The editor's ⌘Z is the everyday undo. Activity's Undo is a **file-level restore**: "Put back the note as it was before this
session (14:02)". It is what is left once the editor's stack is gone (a reload, the next day). It uses #119's existing
`filechange.py undo <id>` on the row's latest save, unchanged. The row reads "12 saves, 14:02 to 14:31" and its button
"Restore 14:02" (wording open, below). Per-save restore points would need a backup per save, which #119 removed: not proposed.

**Guarded surface (exact):**
- `live_server.changes_list_route`: the fold, as r2 hunk 2 (M1). **The only guarded change this design needs.**
- Unchanged by this design: `filechange.perform`, `session_backup`, `_same_session`, `session_saves`, `_undo_edit`, `cmd_undo`;
  `reach.py`, `permissions.py`, `tracker.py`, `backup.py`, `update.py`.
- Carried from r2 only if Alan keeps them: the cap (`filechange.SESSION_MAX_AGE`, `_age`, `_session_first`, `session_backup`)
  and the draft clean-up (`filechange.NOTE_DRAFT`, `retire_note_drafts`; `live_server.main`, `live_server.retire_note_drafts`).

## 4. Tests in real Chrome

New `dev/tests/test_notes_undo_browser.py`, `NotesUndo(LiveBrowserCase)` (`dev/tests/live_browser.py`; keys by
`dev/tools/cdp.py` `b.key("z", MOD)`, `MOD | SHIFT`, as `test_one_editor`), with `notes_tab_browser.NotesTab`'s `make`,
`type_end`, `notes_dir`, `log`:
1. **Delete a line, then retype at once** (< 500 ms): one ⌘Z removes only the retype; a second brings the line back.
2. **Several undos:** three bursts 700 ms apart go one ⌘Z each; more ⌘Z stop at the opened text, never an empty note.
3. **Redo:** ⌘⇧Z puts them back in order; typing after an undo clears redo.
4. **Undo after an autosave tick:** wait for the file and "Saved"; the same editor view (`cxed.editor.view`) and
   `editor.can().undo()` true; ⌘Z works; the undone text is autosaved with the same session id and one backup.
5. **Redo after an autosave tick**, and across a title rename and a pinned toggle.
6. **Reopen:** switch notes and back, ⌘Z undoes the last change; with the file changed outside creaite meanwhile, nothing to
   undo and the text equals the file. **Reload:** nothing to undo.
7. **Paste, a picker choice and an AI replacement** are one step each.
8. **Activity:** one row per session with its count; Restore with the note open reloads it to the session's start.
Each test must fail with its piece taken out (1 and 7 without `cxUndoSteps`; 4 if a save bumps `load`). The server fold keeps
r2's `test_notes_175` cases.

## 5. Risks

- The vendor rebuild touches every editor's bundle; the round-trip gate and `test_one_editor` must pass unchanged.
- Undo back to the opened text saves the writer's form (`touched` stays true). The round-trip gate says it is byte-identical for
  the sample vault; an odd file could differ in whitespace.
- The in-memory cache holds note text in the page only; a confidential note's state must be dropped when the note closes, if
  Alan prefers.
- Two undos mean two meanings; the button wording has to make the file-level one clearly different.

## 6. Open for Alan

1. The 30-minute session cap: keep, change, or drop (it now only limits how far one Activity Restore goes back).
2. Confidential leftover drafts: leave in place (r2) or delete with no copy.
3. The page wording ("12 saves, 14:02 to 14:31"; "Restore 14:02" rather than "Undo").
4. Activity's Undo on a notes row: file-level restore to the session's start (recommended), or no button on notes rows.
5. Keep the ⌘Z history when switching notes within the page (recommended), or always start empty on reopen.
