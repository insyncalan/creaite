# v20-base: BL-301 (v2.0.0 Notes) integration

Team 1, 14-10-2026. Branch `v20-base`: the one editor (part A, finished on `v20-a-finish`), the Notes server
(`v20-notes-server`), v1.9.3's cut (`cut-193`), the Notes tab (part B, `v20-notes-tab`), Find updates (part E,
`v20-find-updates`) and B's gaps (`v20-notes-gaps`: the Image button, renaming the file with the title, editable Working
session details), wired together here. Parts C (capture, Team 2) and D (AI on a selection) are not merged yet.

## What's built on v20-base

- **A:** Current state, the peek's text fields and Prep's notes on the one editor (Tiptap, vendored); the round-trip gate.
- **Notes server:** `notes.py` (format, paragraphs, sent lines), the notes folder in both layouts, search's Notes group,
  index version 2 (a vault built by an older release re-indexes once).
- **B:** the project page's Overview and Notes tabs, the portfolio's notes, `/api/notes/list|get|new|draft|save`, pickers,
  chips, backlinks, the peek's "n notes mention this".
- **B's gaps:** `/api/notes/image` (pictures in the notes folder's `_images/`), `/api/notes/rename` (the file follows the
  title, and `[[links]]` in other notes follow), the Working session's date and attendees in the header.
- **E:** `notes_find.py`, `/api/notes/find|apply|undo`, run kind `notes-find`, the panel.
- **Wiring (this branch):**
  - **✦ Find updates** sits in the note header's slot (`#noteFindSlot`). It writes the note first, then shows E's panel in
    the right-hand column. The column widens to 360 px, and the panel replaces Mentioned in, Linked work and People until
    it is closed. Close returns focus to the button.
  - **Markers.** The note's lines (`notes.paragraphs`, ported to the page as `noteLines`) are drawn on the editor's blocks
    as ProseMirror node decorations: `data-p`, the panel's numbered markers (`data-fu-mk`) and the hovered line
    (`data-fu-hl`). They are never written and never count as an edit. Each top-level block, and each item of a
    top-level list, is matched to its line by its text, in order.
  - **Addresses.** `#notes=ABC&n=<file>&find=1` opens Find updates at once (part C's "Done and find updates" navigates
    there). The address keeps `&find=1` while the panel is open.
  - **Source links.** A source `…/notes/<title>.md#p4` opens the note with line 4 in view, highlighted for 4 seconds
    (`NOTE_OPEN.fn`, and B's own click handler passes the line).
  - **Tests.** `InTheNotesTab` (3, in `test_find_updates_panel.py`) runs on the real Notes tab. E's other 7 panel tests
    keep their fixture page, because they test the panel's own behaviour (rows, peek, apply, undo, 320 px).

## Routes and run kinds new on v20-base, and what each may touch

Every route is a token- and Host-checked POST on 127.0.0.1, dispatched through `DRAFT_ROUTES`. Nothing changed in
`reach.py`, the guard hook, `permissions.py`, `reach.SCRIPT_COMMANDS` or BL-267's record gate. `test_guard_pinned` is unchanged.

| Route or kind | Reads | Writes | Notes |
|---|---|---|---|
| `/api/notes/list {code}` | the project's (or `_portfolio`'s) notes folder: front matter and references, never text | nothing | |
| `/api/notes/get {path}` | one note (a `.md` directly in a notes folder; `notes.note_of` refuses anything else), its staged draft | nothing | |
| `/api/notes/new {code, template, title, date?, with?}` | the templates | a new note through `filechange.perform` (`via: dashboard`, backed up, logged, undoable; a taken name gets a number) | ordinary change (Alan's own notes); after outside content in an ask creaite run it waits as "Needs approval" |
| `/api/notes/draft {path, body?, changes?, base}` | nothing | `system/staging/drafts/notes/<16 hex>.json` only | no project file |
| `/api/notes/save {path, body?, changes?, base}` | the note's fingerprint | the note through `filechange.perform` (edit); never if the file changed outside creaite (the draft is kept); an unchanged save writes nothing; the search index is refreshed in the background | as `new` |
| `/api/notes/image {path, name, data}` | nothing | a PNG or JPEG of 2 MB at most, created in the note's `_images/` through `filechange.perform` (create, `via: dashboard`, logged, undoable) | ordinary; `/api/notes/get` also returns the pictures the note shows, as data URLs (at most 40) |
| `/api/notes/rename {path, base, old}` | the note and every other note's links | the note moved to `<title>.md` in the same notes folder through `filechange.perform` (move: backed up, logged, undoable); each other note's `[[old]]` link changed as an ordinary `filechange` edit (a note with a draft, or one filechange refuses, is listed, never touched) | **approved by Alan, 14-10-2026:** the route issues its own one-time approval (`reach.APPROVALS`) for exactly this one move, used at once, and only when the note and the new name are each ordinary in `filechange.verdict`. It never does so after outside content in an ask creaite run, for a settings file, for someone else's file or outside the projects. Otherwise the file keeps its name |
| `/api/notes/find {path, p?, confirm?}` | the note's new or changed lines; the project's open item IDs and titles, milestones, health, sponsor, phase; register names | nothing (streams rows) | starts a run of kind `notes-find`; a confidential note asks first |
| run kind **`notes-find`** | only the prompt above | nothing | `KIND_TOOLS = []` (no tools); `KIND_DENIES` = `shape-closed`'s (every reading tool denied); quiet (the raw reply is never streamed); not a guarded kind |
| `/api/notes/apply {path, rows, mode}` | the note as it is now (a changed line is refused) | one proposal `system/staging/proposed-…-note.json` (`source_run: "note"`); with `mode: apply`, `tracker.py apply <that file>` in the live server on Alan's click (as `/api/apply`), whose `file_changes` may write the people register and the project's `CLAUDE.md` (backed up, undone with the apply); `system/staging/notes-sent.json` (paragraph, fingerprint, IDs, apply number; never text) | the bulk rule's rows start unticked; a hedged milestone or health row can't be ticked, and is refused again here |
| `/api/notes/undo {path, apply_id}` | the applies table | `tracker.py undo` only when that apply is still the latest; `notes-sent.json` lines made new again | as `/api/undo` |

The page also gains `D.notes` and `D.note_templates` from `build_dashboard.py`: summaries and references, never text.

## What's left

- **Part C** (Team 2): "Note for this meeting", the capture drawer, quick capture's merge, and "Done and find updates"
  (navigates to `&find=1`).
- **Part D:** AI on a selection. "Make this an action" is `mountFindUpdates(path, el, {p})`, or here the panel with `p`
  (the hook isn't built yet).
- **From B:** the margin ticks (`notes.sent_ids`) aren't drawn yet. (Pictures, renaming and the Working session fields
  are now built, on `v20-notes-gaps`.)
- **From A:** Alan's call on the Draft email preview, which stays a plain contenteditable for now (option (a)). The gate
  also needs re-running over Alan's real Current states on laptop 1.

## Open questions for Alan

1. **Tabs.** The project page has only Overview and Notes. Should Work, Milestones, Meetings and Files become tabs too? (B)
2. **Clicks in a note.** A click on a note link or item chip opens it, and ⌥-click edits inside it. Keep this, or open
   only on ⌘-click? (B)
3. **Note drafts in the backup zip (BL-323).** They sit in `system/staging/drafts/notes/` and so go into the backup zip.
   Undecided. (B)
4. **Outside content.** With the projects in OneDrive, reading a note marks an ask creaite run as having read outside
   content. Should notes be exempt? This would be a guard change, and it isn't made. (Notes server, decision 6)
5. **E's calls** (all made, open to change):
   - each list item counts as a line;
   - a hedged milestone or health row can't be ticked;
   - only a "Very likely" repeat starts unticked;
   - the memory line starts unticked;
   - "Linked to …" is shown as a note, not staged as a link;
   - rows open in the peek's layout inside the panel.
6. **Edits change a note's layout.** Once a note with a mixed list is edited (bullets with one checklist item), the
   exact writer saves the checklist item as its own list, with blank lines around it. Find updates still numbers one
   line per item, so markers and sent lines keep working. But the Markdown file's layout changes on the first edit. Is
   that acceptable for notes, or should the notes feature set keep a mixed list as written?
