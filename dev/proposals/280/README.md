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
