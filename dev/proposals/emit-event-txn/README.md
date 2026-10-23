# emit-event-txn (Cap's HIGH, carried over from 2.6.1)

`tracker.diff` applies on main's `system/scripts/tracker.py` (256fdcc2). It changes `emit_event`:
- a field of the wrong shape (TypeError, AttributeError, KeyError, ValueError while reading the route or source) is read by the via alone, before the insert, so a malformed note still never stops an apply;
- the item_events insert is no longer inside a catch-all: any database error propagates, so `cmd_apply` and `cmd_undo` roll back whole (rc 1, "Apply failed; nothing was written").

Tests: `dev/tests/test_emit_event_txn.py` (the repro is red on main, green with the diff; the fix tests skip until the diff is applied).
With the diff applied: test_emit_event_txn, test_malformed_note, test_item_history, test_item_history_route, test_guarded_chain, test_tracker all pass, and `dev/tools/check.py` says `check: OK`.

## Round 2 (Cap #275 MEDIUM, 23-10-2026)
A lasting item_events fault used to make the dry run hold every item as invalid and rewrite the proposal (approvals lost). Now the dry run
(`dry_run_all`) sets `EVENT_CTX["dry"]` and `emit_event` records nothing in a rolled-back trial. A lasting fault therefore stops the real
apply (rc 1, "Apply failed; nothing was written", proposal byte for byte as it was); `validate` flags nothing invalid. Also: the redundant
`isinstance(src, str)` guard is gone, the comment says what happens, and a test keeps the shape `except` narrow (a database error is not
swallowed). Cap's repro for 2.6.1 (`repro_2_6_1.py`, #275 comment 12:59) now ends "whole rollback on apply and undo".
