# Sprint: Notes release (BL-301, v2.0.0)

> **UX baseline first (BL-157).** Before it is called done, every screen this sprint touches is checked in the real browser against the ten checks in `dev/BUILD.md` › Sprint ux › UX baseline: (1) a text box shows what is typed; (2) a date field takes words; (3) nothing typed is lost (the peek stages each change; an unsent chat or note comes back after a reload); (4) nothing sends Alan to Claude Code that the app could do; (5) panels don't hide what you're working on (the chat opens over the page; an item panel's fields stay reachable); (6) an empty state says what to do next; (7) the tab title and the first thing seen are right; (8) the key fields come first (the peek's key row, the rest under Details); (9) hints are one tap away, not always on screen; (10) every "Today:" below states what Alan would see, checked in the real app. Look at 1400px and 1100px, light and dark, in at least two themes, with ask creaite open and closed. The report lists which checks were made, with screenshots.

**Goes into:** v2.0.0. Branch `release-200`, made from `release-195` once v1.9.5 is cut. Releases are stacked, as `dev/RELEASE-BRANCHES-NOTE.md` describes: `git merge --no-ff`, never a rebase or a force-push, and each merge commit says what it carries. Merged in this order: `v20-base`, `v20-capture`, then the finishing branches below. Written by the Product Manager on 15-10-2026, from `dev/V20-INTEGRATION-NOTE.md`, `dev/V20-CAPTURE-NOTE.md` and `dev/V20-AI-SELECT-NOTE.md`.

**Read first:** BL-301 in `dev/BACKLOG.md`, including Alan's decisions of 15-10-2026: no new tabs; click opens and ⌥-click edits; note drafts stay in the backup zip; notes are exempt from outside content.

## Goal

Ship Notes, all five parts, as built:
- A: the one editor (Tiptap).
- B: Notes on the project page.
- C: the capture drawer (⌘⇧N and N).
- D: AI on selected text.
- E: Find updates.

The sprint closes the remaining gaps and applies Alan's 15-10 decisions.

## When it can start

- **Now (no wait):** steps 1 to 5, on branches from `v20-base`, after each laptop has re-cloned the new repository (SPRINTCOMMS, 15-10-2026 00:10).
- **The release itself** (steps 7 and 8) waits for v1.9.4 and v1.9.5 to be cut. `release-194` is still WIP: `test_fast_save` fails.

## Order

1. **Bring the branches level (Team 1).**
   - Merge the latest `v20-base` into `v20-capture`, keeping both sides as Team 2 did before (test_tracker's script list, main.js's exports, Help's keyboard table, the rules' scripts rows).
   - Rebuild the generated files (`split_dashboard.py build`, `build_guides.py`).
   - Run test_capture_drawer, test_dashboard_split, test_tracker and test_help_loop.
2. **Finish D (Team 2, `v20-ai-select`).**
   - Test and finish the WIP commit that wires D into Notes (the top of `v20-base`).
   - Build the hook "Make this an action / risk / decision / update" on a selected line: `mountFindUpdates(path, el, {p})`.
   - `/api/edit/ai` keeps no tools; counts only go to `draft-stats.json`.
3. **B's last gap (Team 1):** draw the margin ticks on lines already sent (`notes.sent_ids`).
4. **The guard change: notes exempt from outside content (Team 1, its own branch `v20-notes-guard`).**
   - **What changes:** reading a note no longer marks an ask creaite run. A note here is a `.md` file directly inside a project's or the portfolio's notes folder, as `notes.note_of` accepts it. The marking is in `live_server.py` `OUTSIDE_CONTENT` and in the hook in `reach.py`.
   - **What still marks:** everything else in OneDrive, including a note's pictures (`_images/`), other files, transcripts, documents and `inbox/`.
   - **Tests:**
     - update `test_reach` and `test_live_server`;
     - re-pin `test_guard_pinned` deliberately, with the reason in the commit;
     - a new test that a note doesn't mark and a transcript in the same project still does.
   - `creaite-rules.md`'s BL-141 lines say so.
   - **No other guard change** in this release.
5. **Fix the `review` snapshot (Team 1).** After the `v20-a-finish` merge, a "Possible match" row loses BL-315's reject guess ("guess: Doesn't need tracking"). Find and fix the cause; don't re-record the golden.
6. **A's gate on real data (Alan, read only, on laptop 1).**
   - Re-run the round-trip gate over Alan's real Current states (`--private --exact`).
   - The comment node must close the fourth pane (one holding only an HTML comment).
   - No release until every pane round-trips byte for byte.
7. **Rules and docs (Team 1).** `system/creaite-rules.md`:
   - `08 Notes` and `notes-sent.json` in the folder map;
   - the Find updates panel as a place Alan approves;
   - notes passive until Find updates;
   - Tiptap named as the editor;
   - quick capture merged into the drawer (FR-71 retired);
   - the notes exemption (step 4).

   Also `dev/release-notes/2.0.0.md` (already started on `v20-base`), Help, the guides and `dev/dashboard-spec.md`.
8. **Release (Team 1 integrates, the main session pushes).**
   - Run the full suite on `release-200` (`dev/tools/run_tests.py`), then Actions `tests.yml` on `insyncalan/creaite`.
   - Run `check.py`, and the vendor manifest check (the Tiptap bundle, its licence).
   - Alan runs the hand checks in `dev/handchecks/v2.0.0.md` (to write):
     - a note made, edited and renamed (its file follows);
     - ⌘⇧N and N from any page;
     - "Note for this meeting" on Today;
     - AI on a selection, accepted and undone;
     - Find updates applied and undone;
     - a Current state edited and saved unchanged elsewhere;
     - ask creaite reading a note with no approval card.
   - Set VERSION to 2.0.0, merge to main, and publish the `v2.0.0` release; the workflow attaches the zip.
   - Alan installs it on the live vault with "update creaite".

## Rules for this sprint

- **No schema change.** If one seems needed, stop and report.
- **The one writer stays** `tracker.py apply`. Every file change goes through `filechange.py`.
- **No guard change other than step 4.** `reach.py`, the hook, `permissions.py`, `reach.SCRIPT_COMMANDS` and BL-267's record gate are otherwise unchanged.
- **No real names:** use the fictional sample data (Brightwater, Kestrel Group, Northgate, FAL, MER, ORX, ABC, Alan Carter).
- **Look at it** in the real browser at 1400px and 1100px, light and dark, in two themes.
- **`check.py`** holds you: no figure may rise.
- **The usual edit rule:** don't edit `dev/BACKLOG.md`, `dev/BRD.md` or `dev/sprints/STATUS.md`. Only the main session pushes; agents commit only. Clean up worktrees and branches once work lands.

## Tests

- **Each step** runs its own tests, then every test file touching the areas changed, not a sample:
  - Notes: test_notes_server, test_find_updates_panel, test_capture_drawer;
  - the editor: test_one_editor_gate, test_tiptap_roundtrip, test_tiptap_pin;
  - the guard: test_reach, test_guard_pinned, test_live_server, test_record_commands;
  - the snapshots.
- **Then the full suite** once on `release-200`, and Actions on Linux.
- **Stand-in model replies only;** never a real model call in tests.
- **Stop runs** by their own process tree; never `pkill` by name.
- **Under load:** a file that fails under load and passes alone counts (`--repeat` and `--stress` when in doubt).

## Report

- Each step: what was done and the tests run.
- The UX baseline checks, with screenshots.
- The real-data gate's result.
- The hand-check result.
- Anything that needed Alan.
- The merge order of `release-200`.
