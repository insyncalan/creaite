# #280 follow-ups (Cap's 2.5.4 review), for the 2.6 line

Not for 2.5.4. Every diff here applies **after** the #280 stack in `dev/proposals/280/` (on the 2.5.4 line; it reaches the 2.6 line
when 2.5.4 is merged in). `tracker.py` and `live_server.py` are guarded, so their changes are diffs; the rest are diffs only because
the code they change is not on `v26-line-4` yet.

## Apply order

1. The #280 stack, as its README says: `tracker.py.diff`, `tracker-held.py.diff`, `live_server.py.diff`, `live_server-held.py.diff`,
   `tracker-round5.py.diff`. They apply cleanly on `v26-line-4` (7b12ab33) too, and with them `tracker.py` and `live_server.py`
   are byte for byte the 2.5.4 ones (origin/v254-release e30d739f).
2. The 2.5.4 merge (brings `review.py`'s #280 half, `dev/proposals/280/` and the re-recorded pins).
3. Here, in this order:
   - `tracker-followup.py.diff` (guarded)
   - `live_server-followup.py.diff` (guarded)
   - `pinned-held0.diff` (tests; goes with `tracker-followup.py.diff`, never without it)
   - `review-discard.py.diff` (not guarded; needs the 2.5.4 `review.py`)
   - `280-README.diff` (the note in `dev/proposals/280/README.md`)

Verify (checked clean on line-4 + the stack + the 2.5.4 merge, in order; `-R --check` in reverse order; with the two guarded
diffs reversed after the stack, `tracker.py` and `live_server.py` are back byte for byte):

    for f in tracker-followup.py.diff live_server-followup.py.diff pinned-held0.diff review-discard.py.diff 280-README.diff; do
      git apply --check dev/proposals/280-followup/$f && git apply dev/proposals/280-followup/$f; done

## What each does

1. **No apply names a bare file (live_server-followup.py.diff).** `tracker.py apply` resolves a bare name in the vault root before
   `system/staging/` (`resolve_proposal`), so a root file of the same name would be applied instead. `/api/apply {only}` already
   passes `"system/staging/" + name`; now `edit_apply`, `confirmed_apply_one`, `page_move` and `notes_apply_now` do too. The
   card's marker (`card_moves_allowed(name)`) still binds the name, as before. Already on the branch (not guarded): the same fix
   in `review.py` (Approve minutes) and `report_server.py` (a report's Approve), and two tests' stand-in `run()` read
   `Path(args[1]).name` so they work with either form. Test: `dev/tests/test_apply_root_file.py` plants a namesake in the root
   just before each route's real apply and checks the staged change is written and the root file never read; the four route
   tests skip until this diff is in (`CREAITE_UNSKIP_280FU=1` runs them: all four fail without it), and its static check fails
   for any script that passes a bare name.
2. **No "held 0" (tracker-followup.py.diff).** The summary line says `held n,` only when something was held:
   `Apply 1: written 1, filed 0, rejected 0, 0 still pending.` The debug log line keeps `held 0` (diagnostics). The two callers
   that read `held (\d+)` from the output already treat a missing count as 0. `pinned-held0.diff` re-pins the 25 summary lines
   in 16 pinned files (`test_writer_pinned`); `test_tracker`, `test_excel` and `test_prep_updates` (`held 1`) are unchanged.
3. **Stale "All or nothing" (tracker-followup.py.diff, comments only).** `cmd_apply`'s docstring and the dry-run comment now say
   an invalid item, or minutes or a report whose file has gone, is held in Review and the rest applies, while a file block's
   problem still stops it all. Not guarded, on the branch: `dev/staging-format.md`'s Apply step 2. Nothing in `review.py`,
   `review.js` or `server.js` on line-4 says it; the 2.5.4 `server.js` comment "a save is all or nothing" is about the page's
   save (its own items undone when one is held) and is still right.
4. **`reject <not a number> --discard` (review-discard.py.diff).** A word, two numbers, a range or no number is refused with
   `…: not discarded — give one review number, as in "reject 4 --discard".` and exit code 2 (review.py's code for bad
   arguments), never a ValueError traceback. Test: `dev/tests/test_review_discard_args.py` (skips until `review.py` has
   `cmd_discard`; fails with the 2.5.4 `review.py` alone). Not fixed here: `review.py approve abc` (no `--discard`) still
   raises the same ValueError in `parse_numbers`, on line-4 and 2.5.4 alike.
5. **Keep the pairs together (280-README.diff, dev/tests/test_held_pair.py).** `tracker-held.py.diff` calls
   `review.hold_missing`, `live_server-held.py.diff` sends `--discard` and `--without-transcript`; all live in the 2.5.4
   `review.py`. `test_held_pair.py` fails when tracker calls `hold_missing` and review.py lacks it, when review.py has it and a
   #280 tracker.py doesn't call it, or when live_server sends a mode review.py doesn't know. Checked: line-4 + the stack alone
   fails two of its three tests; line-4 alone and line-4 + the stack + the 2.5.4 merge pass.
