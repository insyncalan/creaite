# v20-notes-tab: BL-301 part B, Notes on the project page

Team 1, 14-10-2026. Branch `v20-notes-tab` from `origin/v20-base` (parts A and the notes server).

## What's built

- **Server** (`live_server.py`, one block "BL-301 B", dispatched through `DRAFT_ROUTES`; `do_POST` unchanged):
  `/api/notes/list {code}`, `/api/notes/get {path}`, `/api/notes/new {code, template, title, date?, with?}`,
  `/api/notes/draft {path, body?, changes?, base}`, `/api/notes/save {path, body?, changes?, base}`. A note is created and
  saved only through `filechange.perform` (`via: "dashboard"`, backed up, logged, undoable); a draft goes to
  `system/staging/drafts/notes/<16 hex>.json`. A save checks the file's fingerprint (`base`): a note changed outside creaite is
  never overwritten (the draft is kept, `stale` on the next open). Unchanged saves write nothing. The search index is refreshed
  in the background after each write. Paths must be a `.md` directly in a notes folder (`notes.note_of`).
- **notes.py** (additive block): `summary`, `listing`, `refs` (links, items, people), `kind_of`, draft helpers, `clean_changes`,
  `saved_text`, `text_sha`. No text in summaries.
- **build_dashboard.py:** `D.notes` (each project's and the portfolio's note summaries), `D.note_templates`; Files lists the
  portfolio's notes too.
- **Dashboard:** `components/notes/NotesPage.jsx`, `NoteEditor.jsx`, `components/project/ProjectTabs.jsx`, `stores/notes.js`,
  `notes.js`; small hooks in `core/nav.js` (view `notes`, `#notes=ABC&n=<file>`, leaving flushes the note), `projects.js` (the
  tabs on the cockpit), `panel.js` (`drawPeekNotes`: "n notes mention this"), `files.js` (`notes` folder), `ask.js` (Notes group;
  a found note opens in its tab), `shell.html` (`#v-notes`, Projects › Portfolio notes), `core/state.js`, `style.css` (one block).
- **The Find updates slot** (part E): `#noteFindSlot` (`data-slot="find-updates"`) in the note header beside Saved. Empty; not built.
- **Tiptap bundle:** `dev/tiptap/editor.js` now also exports `Decoration` and `DecorationSet` (the note's link and chip drawing);
  rebuilt with `tiptap.py vendor` (`vendor --check` fresh; the round-trip gate passes). **Merge note:** if another part also
  rebuilds the bundle, resolve `tiptap.module.js` and its `manifest.json` by re-running `python3 dev/tools/tiptap.py vendor` after
  merging `dev/tiptap/editor.js`.

## Tests

- `dev/tests/test_notes_tab.py` (5, live server): templates through filechange (logged, numbered names), draft then one save and
  undo, never overwriting an outside change, list and portfolio and refusals, dashboard data and Files.
- `dev/tests/test_notes_tab_browser.py` (4, Chrome): tabs; make, type, draft, save once on leaving; list collapses and stays
  collapsed after reload (⌘\); `[[` and `#` pickers, chips, backlinks, the peek's mention; 320 px.
- check.py OK, typecheck 0. Also passing here: test_dashboard_split, test_snapshots, test_one_editor_gate, test_one_editor,
  test_vendor_tiptap, test_tiptap_roundtrip, test_notes_server, test_search, test_search_live, test_search_dashboard,
  test_agendas_files, test_work_item_peek, test_help (counts one more reference section), test_help_loop, test_ui_sweep.
- **Goldens re-recorded:** `cockpit` (the Overview and Notes tabs), `projects` (Portfolio notes button), `work-panel` (the peek's
  empty `#pkNotes`), and `settings-advanced` (the Notes folder setting from v20-notes-server: the golden on v20-base predated it,
  so the test already failed there; separate commit, easy to drop if another part re-records it).

## Left

- ~~Pictures, renaming on a title change, editing a Working session's date and with~~: closed on `v20-notes-gaps` (below).
- "Note for this meeting", the capture drawer and quick capture's merge are part C; AI on selection part D; Find updates part E.
- ask creaite citing notes is the server branch's search context (labelled "Note (internal)"); not re-tested in the browser here.

## Security changes for Alan

- **New live-server routes** `/api/notes/list|get|new|draft|save` (token-checked like every POST). They write a project file only
  through `filechange.perform` (ordinary for a note: Alan's own notes; a run marked by outside content makes the save wait as
  `Needs approval` and the draft is kept), and staging drafts directly. No change to `reach.py`, the hook, `permissions.py`,
  `SCRIPT_COMMANDS` or the record gate; `test_guard_pinned` unchanged.

## Gaps closed (v20-notes-gaps, Team 1, 14-10-2026)

- **Image button:** `/api/notes/image {path, name, data}` checks PNG or JPEG and 2 MB (as BL-63) and creates the picture in the notes
  folder's `_images/` through `filechange.perform` (create, `via: "dashboard"`, logged, undoable); Part A's image node shows it.
  `/api/notes/get` also returns `images` (data URLs of the `_images/` pictures the body or draft shows, at most 40).
- **Rename on title change:** after a save that changed the title, the page calls `/api/notes/rename {path, base, old}`. The file
  moves to `<title>.md` (a taken name gets `-2`) through `filechange.perform` (move: backed up, logged, undoable), and `[[old]]` /
  `[[old|shown]]` links in every other note become the new title, each an ordinary `filechange` edit. A note with a draft (being
  typed), or one filechange refuses, is listed on the page, never touched. A title with `[ ] |` lists every link instead.
  Case-only title changes keep the name (macOS file names ignore case). A save sent while the page closes (`keepalive`) doesn't
  rename; the next title change will.
- **Working session header:** date (DD-MM-YYYY) and with are fields in the header, saved with the note (`noteMeta`; the server
  already accepted both).
- Tests: `dev/tests/test_notes_gaps.py` (3, server), `dev/tests/test_notes_gaps_browser.py` (3, Chrome). No golden changed.

### Security changes for Alan (gaps)

- **A move without a card.** `filechange.perform` makes a move only with a one-time approval from the live server's own memory
  (`reach.APPROVALS`), because BL-141 classes every move as sensitive ("it moves or renames a file that exists"). `/api/notes/rename`
  **issues that approval itself**, bound to exactly this move's fingerprint and used at once, on the grounds that changing the
  title in the dashboard is Alan's own act (not ask creaite's). It does so only when the move's sole reason for approval is the
  move: the note (as a change) and the new name (as a create) must each be **ordinary** in `filechange.verdict` (so never while an
  ask creaite run has read outside content, never a settings file, someone else's file or outside the projects); otherwise
  nothing moves and the page says the file keeps its name. Both paths must be notes directly in one notes folder (`notes.note_of`,
  `paths.free_path` in the same folder). No change to `reach.py`, the hook, `permissions.py`, `SCRIPT_COMMANDS` or the record gate;
  `test_guard_pinned` unchanged. **Alan to confirm** this self-approval, or say the rename should go on the one card instead.
- **New routes** `/api/notes/image` and `/api/notes/rename`, token-checked like every POST; pictures and link edits are ordinary
  `filechange` creates and edits.

## Open questions

1. There was no Meetings tab on the project page, so the tabs are Overview and Notes. Add Work, Milestones, Meetings and Files
   as tabs later?
2. A click on a note link or item chip opens it (⌥-click edits inside it). Keep, or open only on ⌘-click?
3. BL-323: note drafts sit in `system/staging/drafts/notes/` (in the backup zip as proposed); decision pending, unchanged here.
