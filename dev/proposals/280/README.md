# #280: one invalid item must not block Apply

`tracker.py` is a guarded file, so the change is given as a diff (`tracker.py.diff`, made against origin/main 2.5.3).

Verify: `git apply --check dev/proposals/280/tracker.py.diff` and `git apply -R --check dev/proposals/280/tracker.py.diff`
(both checked clean). Apply with `git apply dev/proposals/280/tracker.py.diff`.

What it does: in `_validate_work`, an invalid item (not a file block) no longer stops the whole apply. It is flagged
`invalid` with its reason, its decision goes back to `pending` (so it is in Review with the reason), and Apply prints
`Held in Review, not applied: <proposal> item n: <reason>`. The other approved items are written as normal.

Already in place, so no `live_server.py` change is needed: `review.py` refuses to approve an invalid item (approve, edit,
Approve routine, minutes popup) and Review lists the reason.

Tests: `dev/tests/test_minutes_decision_raised.py` (the "one invalid item does not block" test skips until this lands);
`dev/tests/test_tracker.py::test_invalid_proposal_rejected_with_reason` accepts both messages.
With the diff applied all of test_tracker, test_minutes_decision_raised, test_minutes_stage_spec, test_minutes_approve,
test_propose, test_cell_edit, test_minutes_draft and test_card_only_moves pass. test_workstreams (2), test_schema_sprint5 (13),
test_debug_log_stage_b (1) and test_archive_items (1) fail the same way without it (not caused by this change).

## Second round: a save is never stopped by an older staged proposal

`live_server.py` is a guarded file too: `live_server.py.diff` (made against origin/main 2.5.3 at this branch's base).
Verify: `git apply --check dev/proposals/280/live_server.py.diff` and `git apply -R --check dev/proposals/280/live_server.py.diff`
(both checked clean, also together with `tracker.py.diff`).

What it does: `POST /api/apply {only: "proposed-….json"}` applies that one staged proposal only (`tracker.py apply <name>`),
before the hold_peek rule; a name that isn't one proposal directly in `system/staging/` is refused, nothing applied. The page's
save (`saveApply` in `core/server.js`, already changed) sends `only` with its own proposal, so an older proposal with an invalid
item (Alan's Supplier checkpoint and Budget review, a decision carrying `raised`) stays out of the save path. An older server
ignores `only` and applies everything, as before.

Already in the page (no diff needed), for an older server or any apply that stops on other files: the message says it is not
his edit, names every blocking proposal by its meeting title and date with each file and item (`applyBlockers`,
`proposalLabel`, `blockerWords`), and its button is **Open in Review** (those proposals' rows picked, the first open) in place
of Retry.

Tests: `dev/tests/test_save_not_blocked.py`: the server tests skip until this diff lands; the page's message test runs now.
With both diffs applied: test_save_not_blocked, test_minutes_decision_raised, test_hold_peek, test_live_server and
test_instant_edits pass.

## Third round: a proposal whose file operation can't run is held, never a blocker

Alan's vault: three approved minutes proposals (Pilot readiness review, Supplier checkpoint, Budget review) failed every Apply with
"copy: source not found": their transcripts had left the inbox, their drafts were still in `system/staging/drafts`.

Two more diffs, each made on top of the one before it, so all four apply **in this order**:
`tracker.py.diff`, `tracker-held.py.diff`, `live_server.py.diff`, `live_server-held.py.diff`.
Verify (checked clean, in order, and `-R --check` in reverse order):

    for f in tracker.py.diff tracker-held.py.diff live_server.py.diff live_server-held.py.diff; do git apply --check dev/proposals/280/$f && git apply dev/proposals/280/$f; done

- `tracker-held.py.diff`: `cmd_apply` calls `_hold_missing_sources(work)` (full and named applies). For each proposal it asks
  `review.hold_missing` (already in `review.py`): a decided minutes or report block whose file operations would copy a file that
  has gone (not the draft's own copy, which stays BL-260's) goes back to pending with `held` (the reason, "transcript no longer in
  the inbox (inbox/…)"), the proposal is saved and left in staging, and Apply prints
  `Held in Review, not applied: <proposal> minutes (<title>): <reason>. In Review: …`. The rest applies. A block still pending and
  held keeps its proposal back while the file is missing, so its approved items wait for the minutes.
- `live_server-held.py.diff`: `POST /api/review` takes decision `discard` (runs `review.py reject N --discard`) and mode
  `without-transcript` on an approve; an unknown decision is refused instead of raising.

Already in place (not guarded): `review.py` (`held_reason`, `hold_missing`, `approve N --without-transcript` drops the transcript's
copy and its inbox removal, records `transcript_dropped`, and is refused while the transcript is still there; a plain approve of
held minutes is refused with both ways out; `reject N --discard` moves a held proposal to `system/staging/discarded/`, kept,
nothing written; `reject --discard` stays a `reject`, so `reach.SCRIPT_COMMANDS` needs no change), `build_dashboard.py` (the Review
row carries `held`), and the page (the held row's reason, **Approve without the transcript** and **Discard** in place of Approve,
the same in the right-click menu, A on the row says why, and Apply's snack counts held proposals).

Tests: `dev/tests/test_held_missing_source.py`: the apply and server tests skip until the diffs land; Review, discard, the
dashboard row and the page run now. With all four diffs applied every test in it passes.

Unblock Alan's vault once this lands: in Review, each of the three shows "Held: transcript no longer in the inbox"; choose
Approve without the transcript (the minutes are filed from the draft) or Discard. Supplier checkpoint and Budget review also need
item 1 (the decision with `raised`) edited or rejected; with `tracker.py.diff` that item is held on its own and no longer blocks.

Not changed (guarded): `system/creaite-rules.md`'s folder map does not yet list `system/staging/discarded/`.
