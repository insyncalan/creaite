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
