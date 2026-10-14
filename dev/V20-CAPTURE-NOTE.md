# v20-capture: BL-301 part C, the capture drawer (⌘⇧N)

Branch `v20-capture`, from `origin/v20-base` (parts A and the notes server). Team 1, 14-10-2026. **Handed over to Team 2 on
14-10-2026 (WIP).**

## State (Team 2, 14-10-2026: finished; not pushed)

- **Finished by Team 2** on top of Team 1's WIP (259e8b1):
  - The related run (below) passes; `check.py` OK.
  - **Alan's two answers (14-10-2026), built:**
    1. **N, the second key.** N on its own opens the drawer (after the typing check, so typing an n in a box stays typing; not
       while a dialog is open). ⌘⇧N stays (it works in a text field and in the app window, but in an ordinary Chrome tab it is
       Chrome's incognito window). N is used by nothing else: Chrome and macOS have no bare N, and creaite's keys are `/`, ⌘K, ⌘J,
       ⌘\, ?, J K F D C T [ ] A R X E, Space and Enter. Shown only in Help's keyboard table (and the capture card's step 1); ⌘K's
       "New note" hint stays ⌘⇧N; nothing else on screen names N.
    2. **Confidential switch.** `#capConf` (a `.switch` checkbox, `role="switch"`, off for every new note) under the title. On,
       Done writes `confidential: true` in the note's front matter (`capture.text_of`), the field notes.py already records, so
       `notes.is_confidential`, search's `file_passages` (keeps its text from Claude, so ask creaite too), Prep and client output
       treat it as confidential material, as `creaite-rules.md` says for notes. Only a JSON `true` sets it (`capture.clean`). The
       draft keeps it (`/draft`, `/recent`). A confidential meeting's note still starts off (Alan: default off).
  - `origin/v20-a-finish` (b78aba9) merged (its Actions run was still in progress when merged: see the report); release notes
    kept both bullets; generated files rebuilt (unchanged).
  - Goldens re-recorded for C only: `cmdk` ("New note" ⌘⇧N), `intake` (Quick Capture gone), `help` (the first-day list and
    Intake's line). `today` is unchanged (the sample has no meetings). **`settings-advanced` fails and is not C's:** the notes
    server's "Notes folder" row (`locations.folders.notes`, from v20-base) moves the rows below it; left for its owner. **`review`
    fails after the v20-a-finish merge, not before it**, and is not C's either: a "Possible match" row loses its BL-315 reject
    guess ("guess: Doesn't need tracking"); left for Team 1 to judge.
  - Related run after the merge (`-j 2`, Chrome): test_capture_drawer (17), test_cmdk_change, test_today_home, test_today_brief,
    test_help, test_help_loop, test_ui_sweep, test_motion, test_dashboard_split, test_one_editor_gate, test_block_texteditor,
    test_insight, test_autosize_fields, test_plain_dates, test_ux_sweep_fixes, test_debug_log_wiring, test_live_server,
    test_notes_server, test_tracker, test_guard_pinned, test_reach, test_record_commands: all OK. test_snapshots: only `review`
    and `settings-advanced` (above). There is no test_cmdk.py or test_intake*.py.
- **Security:** none. `reach.py`, the hook, `permissions.py`, BL-267's list and test_guard_pinned unchanged; N is page-side; the
  switch only adds a field the note's front matter already had.
  - Help (keyboard row for N; capture card steps 1 and 5), `dev/dashboard-spec.md` and the 2.0.0 release notes updated.
- **v20-base f14b77a merged (4e40524).** Conflicts kept both sides (test_tracker's script list, main.js's exports, Help's
  keyboard table with Sneak peek's `/ /`, creaite-rules.md's scripts row and backup.py's row); generated files rebuilt; no Tiptap
  bundle clash. After it: test_capture_drawer, test_dashboard_split, test_tracker, test_help_loop OK; `settings-advanced` now
  passes; **`review` still fails (not C's, as above)**; test_help's `test_command_palette_finds_help` failed twice under a load
  average over 100 and passes alone (a scroll-timing check).
- **Next:** push (the main session) and run Actions: `gh workflow run tests.yml -R insyncalan/creaite --ref v20-capture`.

## What's built

- **Server** (`system/scripts/capture.py`, a library with no command line, so no `reach.SCRIPT_COMMANDS` entry):
  - `guess(text, active)`: cx-minutes' matching rules over the register (strong: code token, `[CODE]`, Teams channel; medium: name, alias, stakeholder of one project only, a first name only one project's stakeholders have, sender, client domain, two or more keywords; weak: one keyword, never assigns; Shared names and words inside them never count; Exclude rules a project out; two projects is a conflict). Returns the code (or None: Unfiled) and a reason to show.
  - Drafts as Alan types: `system/staging/drafts/notes/capture-<id>.json` (not stamped by the change stream, so typing never reloads the page); removed once the note is written.
  - `save`: the template's front matter (`notes.template`) over the typed body, **created through `filechange.perform`** (`via: "dashboard"`) in the project's notes folder, or Unfiled (`_portfolio`); a taken name gets " (2)".
  - `meeting`: title, date, attendees (without Alan; none for a confidential meeting) and the project `prep_match` finds, from the saved calendar.
- **Routes** (`live_server.py`, dispatched through `DRAFT_ROUTES.update(NOTE_CAPTURE_ROUTES)`, so `do_POST` is unchanged): `POST /api/notes/capture/guess | start | draft | done | recent | discard`. `done` with `code: "auto"` guesses (for "note: …"). **BL-54's `/api/capture` and `Handler.capture` are removed.**
- **Dashboard:**
  - `src/components/notes/CaptureDrawer.jsx` (`openCapture`, `closeCapture`, `captureDone`, `openNoteFull`) and `src/stores/capture.js` (`capOpen`, `noteRequest`, `noteHref`).
  - ⌘⇧N in `core/keys.js` (before the typing check); ⌘K "New note" replaces "Quick capture"; `#capDrawer` added to `OPENERS`.
  - Today: **Note** (`.mnote`) under every non-private meeting, any day (`DAYACTS.note`, `DayActs.note` in DayMeetings.jsx).
  - "note: …" in ask creaite (`ask.js handle`) posts to `/done` with `code: "auto"` and says where it went. Page-side only: BL-314's routing and the guard are untouched.
  - **FR-71's Quick capture form is gone:** the Intake section, `meetings.js` `qc*`/`captureNote`/`openCapture`, the BL-220 chips on it (`qcLine`, `qcChipsDraw`), BL-157's browser-kept draft. Old quick notes stay in `minutes/`; cx-minutes still processes them.
- **Done and find updates** (for parts B and E): saves, then sets `noteRequest = {code, path, find: true}` and goes to the project (Unfiled: Projects) with **B's note page as the address** (coordinator, 14-10-2026; B is `v20-notes-tab` d511fd9): `#notes=ABC&n=<encoded file name>&find=1` (`#notes=_portfolio&n=…` for Unfiled; `noteHref` in stores/capture.js). **B and E: read `noteRequest` (or the address), open the note and the panel, then clear it.** This branch has no `notes` view, so `openNoteFull` still calls `go("cockpit", code)` (Unfiled `go("projects")`) and then sets the address; **when B is merged, change that `go` to B's notes view** (B's `parseHash` already reads `#notes=…&n=…` and ignores `&find=1`). A recent note in the drawer opens the same way with `find: false`.
- Help (task card and reference "Capture a note", keyboard table, Intake), `dev/dashboard-spec.md` (new section; the Quick capture sections marked retired), `creaite-rules.md` (`capture.py`), the cx-minutes skill (quick notes are pre-2.0 only), release notes.

## Tests

- New `dev/tests/test_capture_drawer.py`: `Guess` (3), `Routes` (5), `Drawer` (6, Chrome against the live server): ⌘⇧N from Work without moving, the guess and its reason, the choice sticks, Done through filechange.py (logged, undoable), Esc keeps the draft and returns focus, ⌘⇧N carries on, Unfiled, recent notes, Done and find updates' address and `noteRequest`, Note for this meeting (attendees, date, project; none on a private meeting), ⌘↵, "note: …", ⌘K "New note", the form gone, 320 px, dark.
- Changed for the removed form: `test_insight` (the quick-capture class keeps only "an old quick note still stages"), `test_today_brief` (Intake has two sections; the Quick Capture date tests removed), `test_autosize_fields`, `test_plain_dates`, `test_ux_sweep_fixes`, `test_debug_log_wiring` (its canary now goes through `/api/notes/capture/done`), `test_help` (heading "Capture a note"), `test_tracker` (`capture.py` copied into test vaults).

## Security changes for Alan

**None to the guard.** `reach.py`, the hook, `permissions.py`, BL-267's list and `test_guard_pinned` are unchanged. New routes are the page's own (token-checked like every POST); a note is written only through `filechange.perform` (ordinary: Alan's own notes). One behaviour to know: if an ask creaite run is in progress **and** has read outside content, `reach` marks every change sensitive, so Done can't write the note; the drawer keeps the draft and says to press Done again later (no card is raised for a dashboard save).

## Left / open questions

1. ~~⌘⇧N in a normal Chrome tab~~ Answered (Alan, 14-10-2026): N added as a second key; ⌘⇧N kept.
2. The project picker is a native `select` (COMPONENTS.md's `Picker` block isn't built yet); swap it when it is.
3. Search indexing on save (kind `note`) is part B's refresh; the drawer doesn't trigger it.
4. ~~Confidential flag~~ Answered (Alan, 14-10-2026): the drawer has a Confidential switch, off by default.
5. Snapshot goldens re-recorded: `cmdk`, `intake`, `help` (commit 956b006). `settings-advanced` is the notes server's.
