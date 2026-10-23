# emit-event-txn (Cap's HIGH, carried over from 2.6.1)

`tracker.diff` applies on main's `system/scripts/tracker.py` (256fdcc2). It changes `emit_event`:
- a field of the wrong shape (TypeError, AttributeError, KeyError, ValueError while reading the route or source) is read by the via alone, before the insert, so a malformed note still never stops an apply;
- the item_events insert is no longer inside a catch-all: any database error propagates, so `cmd_apply` and `cmd_undo` roll back whole (rc 1, "Apply failed; nothing was written").

Tests: `dev/tests/test_emit_event_txn.py` (the repro is red on main, green with the diff; the fix tests skip until the diff is applied).
With the diff applied: test_emit_event_txn, test_malformed_note, test_item_history, test_item_history_route, test_guarded_chain, test_tracker all pass, and `dev/tools/check.py` says `check: OK`.
