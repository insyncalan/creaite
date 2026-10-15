# v20-find-updates: BL-301 part E, Find updates (from a note to the tracker)

For the Scrum Master (Team 1). Branch `v20-find-updates`, from `origin/v20-base` (the one editor and the Notes server). Parts B, C
and D are built in parallel; this part does not build them.

## What's built

### The server engine (first)

- **`system/scripts/notes_find.py`**, a library (no command line). The engine is cx-minutes' and cx-edit's, given a note as the
  source:
  - `context(rel, only)`: the note's new or changed lines (`notes.unsent`), or one line; the project's open item IDs and titles,
    Planned milestones, health, sponsor, phase and the people register's names; plain code's "may close an item" guesses (BL-218's
    `passage_candidates`); as the prompt `system/templates/notes-find-prompt.md`. Nothing new: no model call.
  - `rows(ctx, reply)`: Claude's JSON rows checked by plain code. New actions, RAID items and decisions go through
    `minutes.Staging` (the project, rejected before, an exact open repeat becomes an update or is left, flags, workstreams), with
    the source `projects/<folder>/08 Notes/<title>.md#p<n>`. Updates: an open item of this project only, cx-minutes' fields plus
    the owner, `based_on` filled. Done: BL-218's closing update with its evidence and owner rule (`mark_meeting_update`). Then
    BL-221's repeats (`mark_repeats`: "Very likely" starts unticked, "Possible" is a flag) and BL-220's vague titles
    (`mark_vague`). Every row is dry-run (`propose.check`); a failure says why and is locked unticked.
  - The bulk rule: new risks, new decisions, milestone moves, health changes and memory lines start unticked; routine rows (a new
    action or issue, a due date, done, an owner, a new person) start ticked.
  - **Hedged lines** (`HEDGE`: probably, might, may, could, likely, to confirm, TBC, tentative…): a milestone move or health change
    from one is locked (shown, unticked, can't be ticked, "Tentative"), refused again at apply, and a confirm action linked to the
    milestone (`actions.milestone`, its early warning) is proposed beside it when Claude gave none.
  - `stage(rel, rows, mode)`: each ticked row rebuilt from the note as it is now (a changed line is refused: "run Find updates
    again"), merged updates to one item, one proposal `proposed-YYYY-MM-DD-HHMMSS-note.json`, `source_run: "note"`, approved
    (`apply`) or pending (`later`); people and memory lines as one `file_changes` block (people register write, project
    `CLAUDE.md` write, undone with the apply). A confidential note's new items get the Sensitive label. Mentions (BL-51) are logged
    for applied or saved updates only.
  - `record(rel, file, apply_id)` and `forget(rel, apply_id)`: `notes-sent.json` (paragraph, fingerprint, item IDs, and the apply's
    number so Undo can take it back; never text).
- **`notes.py`** (shared, additive): `paragraphs` now makes each top-level list item its own line (see the open question);
  `record_sent(…, apply_id=None)` and `forget_sent(rel, apply_id)`.
- **`minutes.py`** (additive, behaviour unchanged): `Staging.mention(ids)`, so Find updates can collect the mentions instead of
  logging them at preview.
- **`live_server.py`** (one block, BL-301 E): routes `/api/notes/find`, `/api/notes/apply`, `/api/notes/undo` in `DRAFT_ROUTES`; the
  run kind `notes-find`; `FindJob` (quiet: the raw reply is never streamed).

### The panel

- **`src/components/notes/FindUpdates.jsx`** (`FindUpdates`, `mountFindUpdates(path, el, {noteEl, p, onClose, onMarks})`) and
  **`src/stores/findUpdates.js`**. Grouped New / Updates to existing items / Milestones / Project information; numbered markers
  matching the note's lines (`data-p` → `data-fu-mk`, hover both ways); ticks; a row opens in the peek's layout (fields from the
  server; text on the one editor; dates DD-MM-YYYY); Apply (one apply, Undo in the snackbar, `/api/notes/undo`); Save for later
  (Review); without the live server, Apply saves for Review through the vault folder and says so; a confidential note asks once.
  CSS appended to `style.css` (tokens only). Exported from `main.js`.
- **Source links** (`core/fields.js`, additive): `srcParse` reads `#p<n>`; the link carries `data-noteline`; a click calls
  `NOTE_OPEN.fn(path, line)` when part B sets it, else opens the file.
- **`drafts.js`** (one token): `draftAsk` passes `confidential` through from a JSON reply.

### How part B hosts it

```js
import { mountFindUpdates } from "./components/notes/FindUpdates.jsx";
const fu = mountFindUpdates(note.path, rightColumnEl, { noteEl: editorEl, onClose: () => showRightColumnAgain() });
// one line (AI › Make this an action): mountFindUpdates(path, el, { p: 4, noteEl })
// the source link: NOTE_OPEN.fn = (path, line) => openNoteAt(path, line)   (core/fields.js)
```

With Tiptap, `data-p` attributes on the editor's blocks would be reset by ProseMirror; B should pass `onMarks(markers, hover)`
and draw the markers as decorations (markers: `{line: number}`), and set `fuHover.value = line` on hover. Line numbers are
`notes.paragraphs` of the note's Markdown body.

## Tests

- `dev/tests/test_notes_find.py` (10, the engine, no Chrome): the mockup note yields the mockup's 8 rows (5 ticked); hedged
  milestone locked with a confirm action (and one made when Claude gave none); a hedged row refused at apply; Apply as one apply
  and Undo; a second run skips sent lines and Undo makes them new again; notes-sent.json holds no text; Save for later pending in
  Review; repeats, vague titles, bad dates; confidential → Sensitive; one line only; paths outside a notes folder refused.
- `dev/tests/test_find_updates_panel.py` (7, Chrome, on a fixture note page of its own): groups, markers, ticks, hover; the row
  peek and Esc; Apply and Undo through the snackbar; Save for later and a second run; confidential asks first, text escaped; the
  source link opens the note at its line; 320 px, 24 px targets, Esc closes.
- Fixture: `dev/tests/notes_find_fixture.py` (a Falcon Data Platform project, the catch-up note, a stand-in Claude).
- `check.py` OK; typecheck 0.

## Security changes for Alan

1. **Three new live-server routes** (token and Host checked as every POST): `/api/notes/find`, `/api/notes/apply`,
   `/api/notes/undo`.
2. **A new run kind, `notes-find`**, with **no tools** and the same deny list as BL-286's closed run (`KIND_TOOLS["notes-find"] =
   []`, `KIND_DENIES["notes-find"] = KIND_DENIES["shape-closed"]`). Claude sees only the note's new lines, the project's open item
   IDs and titles, milestones and register names; it can't read or write anything. Not a guarded kind (it can't act).
3. **Apply and the record gate (BL-267):** Apply runs `tracker.py apply <one proposal>` in the live server on Alan's click, the
   same path as the dashboard's own applies (`/api/apply`); no Claude run is involved, so BL-267's gate (which watches Claude's
   runs) is neither crossed nor changed. Undo runs `tracker.py undo` only when that apply is still the latest (as `/api/undo`).
4. **No `reach.SCRIPT_COMMANDS` entry, no `reach.py` or `permissions.py` change**: `notes_find.py` has no command line.
   `test_guard_pinned` unchanged.
5. The apply writes the people register and a project `CLAUDE.md` only as the proposal's own file operations (backed up and
   undone by `tracker.py`), as cx-edit's people and memory changes do. No note file is ever written.

## Calls made here, for Alan

1. **A list item is a line.** `notes.paragraphs` (Decision 5 of the notes server: "a blank-line block") now splits a tight list
   into its top-level items, because the mockup's note is one list and its markers and "a second run skips sent lines" are per
   line. Plain paragraphs are unchanged; existing tests pass. B and the margin ticks use the same function.
2. **A hedged milestone or health row can't be ticked at all** ("never moves a milestone"), and the server refuses it again. Alan
   changes the milestone itself once it is confirmed.
3. **Only a "Very likely" repeat starts unticked**; a "Possible" one is a flag on a ticked row (the mockup's new action is
   "Possible" against the paper action it relates to).
4. **The memory line starts unticked** (as in the mockup); a new person starts ticked.
5. **"Linked to FAL-004"** is shown as a note, not staged as a link: a link needs both IDs and a new item has none until applied.
6. **Rows open in the peek's layout inside the panel**, not in the real side peek: the real peek edits a staged proposal from
   Review, and Find updates' rows aren't staged until Apply.

## What's left

- Part B: host the panel in the Notes tab (above), the ✦ Find updates button, the margin ticks (`notes.sent_ids`), and
  `NOTE_OPEN.fn` (open the note at a line, highlighted). C: "Done and find updates" mounts it. D: AI › Make this an action mounts it
  with `p`. The typing underline (a checklist line with `@person` and a date) is B's editor plus `mountFindUpdates(…, {p})`.
- BL-297's matching is already in `mark_repeats` (it is BL-297's `best_repeat`).
- Wide testing on Actions.
