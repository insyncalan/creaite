# #324 / #326 / #332: one guarded diff for the minutes destination (proposal for Jarvis)

**Status: a proposal. `live_server.py` is guarded; nothing here is applied.** One diff, `live_server.diff`, serves all three items.
`tracker.py` is NOT touched (the never-overwrite rule there stays the backstop; see "Why no tracker.py diff").

## What the diff does (9 added lines, all in `system/scripts/live_server.py`)
1. Docstring: one entry for the four new routes.
2. `minutes_approve_route`: under the existing `LOCK`, call `minutes_destination.settle(file)` before `review.approve_minutes`, and add
   `numbered` (what was numbered) to a successful answer.
3. After `REVIEW_WORK_ROUTES.update(MINUTES_ROUTES)`: `import minutes_destination` and
   `REVIEW_WORK_ROUTES.update(minutes_destination.routes(LOCK))` (same shape as `report_server.routes(...)`; dispatched with Review's
   work, so token and Host checks are the existing ones and `do_POST` gains no branch).

Everything else is in the tree and unguarded: `system/scripts/minutes_destination.py` (new library, no command line),
`stores/minutesFiling.js`, `components/minutes/FilingDialog.jsx`, the Approved-this-week Open folder button, tests, `dashboard.html`.

## Why (items)
- **#332** a second meeting with the same title and day could not be approved ("Apply stopped"): the filed name (and the transcript
  copy's) is taken and is never overwritten. `settle` numbers both ("Title (2)") before the apply, so every web approve path (Minutes
  view, Intake row, A key; they all post `/api/minutes/approve`) files both meetings. Of two pending meetings with one name the earlier
  keeps it, the later is numbered, whichever is approved first.
- **#324** Approve minutes now asks first (File the minutes: project and folder in words, the name in a field with the extension
  fixed, the transcript beside it, Cancel files nothing). A changed name goes to `/api/minutes/destination/name`, which rewrites the one
  pending proposal: the draft copy's `to`, the `source_map` key and every item's `source` prefix (and the transcript copy when it
  carried the same stem). After the approve a note says where they went with Open file and Open folder.
- **#326** Approved this week: Open folder on a Done row. `/api/minutes/destination/open {key|path, what}` finds the filed minutes
  (the meeting key in processed.txt, or the filed path of a row that has one), accepts only a file in a project's own Minutes folder,
  and answers moved / missing / online-only in words. No path is ever in an answer or sent to open.

## Why no tracker.py diff
Numbering is decided before the apply, in the proposal, so `tracker.py apply` is unchanged and still refuses to overwrite (tested: a
second meeting stopped without `settle`; the mutant test removes the call and the approve must stop again). Moving the numbering
into the apply would have meant editing `_op_copy`, `source_map`, item sources and the processed line together in the one writer; not
needed. If Jarvis would rather have the numbering inside tracker.py, say so and it becomes a second diff.

## Apply order
After the 2.6.2 chain (`GUARDED-2.6.2.chain`), as the last guarded diff (it is independent of every diff in the chain: different
hunks, and it applies before or after). `minutes_destination.py` must be in the tree before the diff (it is: unguarded). Do NOT add it
to `.chain` without Alan's say: the chain pin (`CHAIN2_SHA256`) covers the listed diffs. If it is to go in the 2.6.2 chain, the pin
needs re-setting; if it ships as a 2.6.3 chain, it is the first diff of that chain.

## How verified
- `git apply --check` on `origin/v262-line` (fc694fd5): ok. With the whole 2.6.2 chain applied in order: ok. Forward then `-R`: ok;
  applied after the chain and the chain reversed (last first) with this diff still on: ok, tree clean after reversing this diff.
- `dev/tests/test_minutes_destination.py` (quick tier, 20 tests): the library (view, names, rename rewrite, settle, second meeting
  end to end through `tracker.py apply`, where/open with moved, missing, online-only and outside-folder refusals) and the routes. The
  route tests apply this diff to a throwaway vault when the tree has not (as `test_discard_undo_routes.py` does), so they pass in both
  states; one mutant removes the `settle` call and the approve must stop. `dev/tests/test_tracker.py`'s `make_vault` copies
  `minutes_destination.py` (live_server imports it).

- `dev/tests/test_proposal_324.py` (quick): the diff touches only live_server.py, adds no line over 140 characters, and applies
  forward and back on the file as it is and with the chain's live_server diffs applied first (skipped once it has landed).
- `dev/tests/test_minutes_filing_ui.py` (Chrome, 5 tests): the File the minutes box, Cancel files nothing, a refused name stays in
  the box, a new name files and the items cite it, Open file / Open folder, a second meeting numbered, Approved this week's Open
  folder with the moved-file message. It applies the diff to its throwaway vault (`CREAITE_TEST_DIFFS`, a new env var in
  `make_vault`: the listed diffs, applied to the throwaway copy only), so it is the same in both states.
- Existing Chrome tests that approve minutes were run with the diff applied (`CREAITE_TEST_DIFFS=dev/proposals/324/live_server.diff`):
  test_minutes_view_v2, v261, track_review, editor, held_live_306, held_editor_307b, held_stale_262, a302 all pass. Four needed to press
  File and approve (`LiveBrowserCase.wait_filing`, `test_minutes_view_v2.file_box`); without the diff the page asks nothing (the route is
  absent, the page goes on), so they pass in both states. The handcheck `approve_in_view` helper was updated the same way. Not run:
  the other handchecks, test_shared_behaviour, test_ui_sweep, the full suite.

## Risk (for the reviewer)
- The approve route now does one extra write before the apply: the proposal file (a rename of destination paths only). If the apply
  then fails, the proposal keeps the numbered name (harmless; the next try uses it).
- The Word-draft approve path (`/api/review`, `reviewViaServer`) is not covered: Word drafts are the older path and are unchanged.
- ask creaite's `review.py approve` is unchanged (it names no popup); it still stops on a taken name. 324-C in the scope, not done.
- The open routes launch `open`/`xdg-open`/`explorer` on a path the server derived itself from a project's minutes folder; the
  extension is `.html` or `.docx`; a symlink or a missing file is refused; with `CREAITE_NO_LAUNCH` nothing starts.
- No answer holds a path or a proposal's name (tested). Online-only placeholders count as existing for numbering and are never read.
