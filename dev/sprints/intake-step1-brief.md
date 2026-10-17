# Intake step 1: one queue, one decision per row (brief for Team Stark, #179)

Product Manager, 17-10-2026. Sonnet, size M, labels `sonnet`, `review`, `UI`; v2.3.0. No code in this brief. Decisions are Alan's (17-10-2026); the approved mockup is `dev/mockups/intake-final-mockup.html` (step 1 view). The why is in `dev/sprints/intake-review-2026-10-17.md` (sections 3 A and B, 5 and 7). Step 2 (#180: the result on the row, Review opens on just those, Today shares the rows) is a separate item and needs this one; do not build any of it here. Later ideas (#181, auto-load and draft by series) are not built.

## The decisions the build must record

1. **One queue.** Meetings that have ended and files you dropped are one list in Review's row shape: title, when, project (editable, once), transcript state, age. Groups: **Ready**, **Upload files**, **Waiting**, **Later**, **Done recently**.
2. **Three actions per ready row:** **Process** (primary), **Not needed** (asks for a reason: Informal chat, No decisions, Duplicate of another meeting, Other), **Later** (stays, set aside; comes back to Ready when a transcript arrives). A Waiting row has only Not needed.
3. **One bulk button:** **Process all ready (n)**, disabled and looking disabled at 0. **Refresh** stays, quiet.
4. **These go:** Select new, Select with transcripts, Process selected, **Load into inbox** (loading is an automatic first step of Process; Alan: no standalone use). The word "inbox" is removed from every button and state ("in the inbox, not processed yet" becomes plain words).
5. **Organiser and Where** are not columns; they sit under a **Details** control on the row.
6. **Upload files stays** (Alan, 17-10-2026): files dropped become rows in the same list with the same three actions; a drop works anywhere on the page.
7. **Process runs in the background.** Progress shows on the row; ask creaite does not open by itself and stays free to use. (The result line with counts and **Review them** is step 2; in step 1 a processed row moves to Done recently with "Draft ready in Review" and an **Open Review** button.)
8. **Keys as in Review:** arrows move, Enter processes, N Not needed, H Later.
9. **Count:** Intake's badge counts ready meetings plus files, the same number Today shows for what is ready (one count, one meaning).
10. **Empty states** say the next step and link "How Intake works" (the link target arrives with Help Phase B; until then leave the link text out rather than a dead link). The live-server need is said **once**, in one quiet line on the page, not in every button's tooltip.
11. **Age** is quiet text on every row; an outlier (3 days or more) turns amber, as in Review (#177). Match #177's component if it has landed.

## The parts

**1. The list and the row** (`system/templates/dashboard/src/intake.js`, 231 lines, today a nine-column table in `#mtgBody` plus an Upload files card). One row component for a meeting and a file; groups as above; the project select keeps "Not sure". Keep the existing preview, remove and restore behaviour for files (`/api/inbox/preview`, `/api/inbox/remove`, `/api/inbox/restore`) and the transcript check and load (`/api/transcripts/check`, `/api/transcripts/load`), which Process now calls in order before processing.

**2. Not needed and Later.** Today **Clear day** sets meetings aside "now and in every later intake" (BL-104; `/api/intake/clear`, `system/staging/intake-cleared.json`, undoable, Cleared (n) list). Not needed replaces the per-row × and Clear day's button and keeps that behaviour and its undo; the reason is added. **Open point for Jarvis:** saving the reason means a change to the clear route in `live_server.py`, which is guarded. If Jarvis would rather not touch it in this item, store the reason in the existing `skipped:<reason>` text the meeting state already carries and show it as Review shows rejection reasons; say which was chosen on the issue. Later is a client-side set-aside that survives a reload (a small saved list, like other per-person view settings), not the cleared record.

**3. Process and Process all ready.** One path for a row and for all: load the transcript, then run the same processing the buttons run today; one at a time or in parallel exactly as today (do not change the engine). The running state is the row's progress, not the ask creaite panel.

**4. Keys.** Reuse Review's keyboard handler rather than a second one; focus ring on the current row; N opens the reason menu; Esc closes it.

**5. Wording and counts.** Page copy per the decisions. The More-menu and rail badge use the new count.

## Tests (named; put them in `dev/tests/test_intake_queue.py` unless a file for the page exists)

- `test_one_queue_groups`: a mixed sample gives Ready, Upload files, Waiting, Later and Done recently, in that order, and no group renders when empty.
- `test_three_actions_per_ready_row`: Process, Not needed, Later on a ready row; only Not needed on a waiting row.
- `test_removed_controls_are_gone`: the page text contains none of "Select new", "Select with transcripts", "Process selected", "Load into inbox", and the word "inbox" appears in no button or state.
- `test_process_all_ready_count_and_disabled`: the label carries n; at 0 it is disabled and has the disabled style.
- `test_not_needed_asks_for_a_reason_and_undoes`: the four reasons; the row leaves the queue; Undo (and the Cleared list) puts it back.
- `test_later_survives_reload_and_returns`: Later hides the row from Ready, shows it under Later, survives a reload.
- `test_upload_files_become_rows`: a dropped file becomes a row with the same three actions and counts in Process all ready and the badge.
- `test_process_runs_in_background`: a Process does not open the ask creaite panel; the panel opens and works while a row is processing.
- `test_keys_match_review`: arrows, Enter, N, H, and Esc closes the reason menu.
- `test_badge_matches_today`: Intake's badge equals the count Today shows for ready meetings plus files.
- `test_details_holds_organiser_and_where`: neither is a column; both appear under Details.
- `test_empty_state_and_live_server_line`: the empty state names the next step; the live-server line appears once; no button carries it as a tooltip.
- Update `dev/tests/snapshots/intake.html` and any text assertions in `test_meetings.py`, `test_run_badge.py` and `test_today_brief.py` that mention the old controls, then run the dashboard and snapshot tests.

## Files

`system/templates/dashboard/src/intake.js`, `style.css` (row and group styles; reuse Review's tokens, add none), `src/main.js` and `src/stores/` only if the badge or the Later list needs a store entry, the page's text in `system/templates/help.md` (the Intake pages; keep word counts under Help Phase A's budget), `dev/tests/` as above. **Guarded, do not touch:** `live_server.py`, `reach.py`, `permissions.py`, `filechange.py`, `tracker.py`, `edit_ai.py`. Rebuild the dashboard with the project's build tool after the source change.

## Dependencies and risks

- Sits after **#168** (Today's "Intake and Review" block) and **#177** (Review's age), so the row and age pattern is shared; if either is not merged, build the row to Review's current anatomy and note it.
- **#180** (step 2) builds on the row from this item; keep the row component small and reusable.
- Everything needs the live server; behaviour without it is unchanged ("needs the live server" once, not per button).
- Existing cleared meetings and `intake-cleared.json` must keep working (no migration).

## Done when

- The page is one queue with the five groups, three actions per ready row, Process all ready, Details, and Upload files kept.
- The four removed controls and the word "inbox" are gone from every button and state.
- A Process runs in the background with ask creaite free; a processed row moves to Done recently with "Draft ready in Review" and Open Review.
- Not needed asks for a reason and can be undone; Later survives a reload.
- Keys match Review; the badge matches Today.
- The named tests pass, the snapshot is updated, `check.py` and the real-names test pass, and no guarded file is changed (or Jarvis has agreed the one change in part 2).
