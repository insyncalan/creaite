# Design brief: minutes edited in Review, and the transcript side pane (BL-59, BL-60)

**Status:** design brief, not scheduled. Mockup: `dev/mockups/minutes-review-mockup.html` (open it from the file system; the fictional Falcon Data Platform steering committee of 08-10-2026, and a quick note with no transcript). When it is built: two sprints, `sprint-minutes-record` (BL-59) then `sprint-transcript-pane` (BL-60), each from the tip of `main`, with the UX baseline (BL-157) checked before it is called done.

## Goal

The minutes stop being a Word file Alan edits and creaite reconciles. They become a record (the meeting plus its proposed items) that Alan edits in Review, as a page; the Word copy is made from it on approval. While he edits, the transcript sits beside the minutes and each line shows where it came from.

## The screens

1. **Review › Minutes page (BL-59):** a header with ← Review, the meeting, "Saved to staging · …" with **Undo**, and **Transcript**, **Open in Word**, **Re-extract**, **Reject minutes**, **Approve minutes**. Below, the minutes as a page, in the Word file's order and with no frame: title, date and attendees, Summary, Updates by topic, Decisions, Actions, Risks and issues, Open questions.
2. **Editing in place:** text has a faint outline on hover; clicking it edits it, and the BL-47 toolbar (bold, italic, lists, link, clear, undo, redo) sticks to the top while editing. Item rows are editable cells as in Work: the text, owner (people picker), due date (words or a date), priority and workstream, with ✓ and ✕ on each row. **+ Add action / risk or issue / decision.** Every change saves to staging as it is made; the change is the proposal, so nothing needs reconciling.
3. **Approve minutes:** a confirm card that says what will happen (the Word copy made from `minutes-template.docx` and filed in the project's minutes folder, the meeting recorded in `processed.txt`, n approved and n rejected items going to the next apply, n undecided staying in Review). Minutes are approved on their own, never by "Approve routine".
4. **Open in Word:** a confirm card: the Word draft becomes the master for that meeting and today's consistency check applies.
5. **Transcript pane (BL-60):** speaker turns with times, a search box with a match count, read only, closable. **↗** beside a line, or a click on an item row, scrolls the pane to the passage it came from and highlights it.
6. **No transcript** (a quick capture, or minutes only): the pane is titled Source and shows the note whole, or says there is none.

## In

- The record format (an extension of `meeting.json`), staged edits with Undo, approval producing the Word copy, Re-extract keeping decided items.
- cx-minutes recording the source position of each section line and item (speaker turns; timestamps for `.vtt`).
- Removing the Word lock-file wait and the draft-versus-staged sync for this flow, and `documents.require_sensitivity_label` (Alan, 06-10-2026: labelling is unnecessary).

## Out

- **Phase 2, reports:** weekly and client reports edited the same way. A later sprint on the same pattern.
- Editing the transcript, or playing audio.
- Tracked changes in the dashboard (Open in Word covers it).
- Several people editing the same minutes.

## Questions for Alan

1. **Undecided items on approval:** should Approve minutes leave undecided items in Review (as in the mockup) or approve them too?
2. **Where the approved record is kept:** beside the Word copy in the project's minutes folder (it travels with OneDrive), or in the vault under `system/` (local, never synced)? Recommended: the vault.
3. **Back from Word:** once a meeting has gone to Word, may it come back to the page (creaite reads the Word file into the record), or does it stay in Word until Re-extract? Recommended: it stays in Word.
4. **A Word preview before approving:** wanted, or is the page close enough?
5. **The pane by default:** open whenever there is a transcript, or closed until asked for?

## Files it touches

BL-59: `system/scripts/minutes.py` (record format, stage, refresh), `system/scripts/review.py`, `system/scripts/docx_tools.py` (fill from the record), `system/scripts/live_server.py` (save the record), `system/scripts/build_dashboard.py`, `system/templates/dashboard.html` (the minutes page in Review), `.claude/skills/cx-minutes/` and `cx-review/`, `system/config/settings.json` defaults, `dev/staging-format.md`, Help, `dev/tests/`.
BL-60: `minutes.py` and cx-minutes (source positions), `live_server.py` (read the transcript), `dashboard.html` (pane, links, highlight, search), Help, `dev/tests/`.

## Size

**BL-59: L**, about seven days (record and staging two, the page and its cells three, approval and the Word fill one, the removed checks, skills and tests one). **BL-60: M**, about three days, mostly cx-minutes recording positions reliably. Together about two weeks; BL-60 can follow BL-59 in the next release.
