# F2: item numbers above 999 (target 2.6.3)

Guarded files, so **diffs only**. Apply in order, each on top of the last: F1, then
1. `f2-ids-above-999.diff` (guarded: `schema.sql`, `tracker.py`)
2. `f2-readers.diff` (not guarded: 12 Python readers and 8 dashboard source files; `dashboard.html` must be rebuilt from the source by the usual build, not done here)
3. `f2-readers-guarded-live_server.diff` (guarded: `live_server.py`, two patterns)

## Spec found vs assumed
- Found (issue #315): F2 = widen the six three-digit CHECKs (table rebuilds in `schema.sql` plus a migration), audit and fix every regex, sort and prose pattern that assumes three digits (dashboard, search, links, labels, `replaces`, milestone references, minutes text, Excel round trip, reports); rebuild each table in one transaction, row counts and foreign keys verified, `integrity_check`; test on realistic data with a project of 1,000+ items; rollback by restoring the dated copy and `update.py undo` before any number above 999 exists.
- Assumed: the new width. The check now allows 3 to 5 digits (up to 99,999 a project), digits only, code 3 to 7 capitals or digits as before; new numbers still print with at least three digits (`ABC-A-001`, `ABC-A-1000`). Numbers stay unique per project across actions, RAID, decisions and promises, as now. No change to the display or to who issues numbers (the temporary-ID idea in the design notes is a later step, not F2).

## What changes
- `schema.sql`: the `id` CHECK of `milestones`, `workstreams`, `actions`, `raid`, `decisions`, `promises` (one line each; the old `length(id) - 6` arithmetic is replaced by `instr` on the `-A-` style separator). Same primary keys and columns.
- `tracker.py`: `ITEM_ID` takes 3 to 5 digits; `next_id` looks at IDs 3 to 5 digits long (before: exactly 3, so it would have re-issued `ABC-A-1000`). The migration is the existing diff-driven rebuild: no new step.
- Readers: every ID pattern in `ID-SITES.md` section A moved from exactly three digits to 3 to 5; `build_dashboard.py` `seq` (took the last three characters of the next ID, wrong at 1000+); the dashboard's `nextId`, `msNextId` (took the last three characters). Section D and E (text sorts) are listed in `ID-SITES.md` and **not** changed: `ABC-A-1000` sorts before `ABC-A-999` as text, which affects tie-break order and the plain `ORDER BY id` lists; a numeric sort key is a follow-up decision.

## Rollback
Restore the dated database copy and `update.py undo`, **before** any number above 999 exists (the migration alone creates none). After that, restoring loses the items made since. Without a restore the old engine is unsafe: it re-issues `ABC-A-1000` (held, not written, because the key already exists) and its `migrate` refuses with a CHECK error and changes nothing.

## Check
`git apply --check` and `-R --check` pass on `origin/v261-line2` with F1 applied. Tests on the patched tree: test_tracker, test_codes, test_schema_sprint5, test_milestone_states, test_milestones, test_ask_claims, test_item_history, test_edit_ai_client_place pass. The ID check was kept on one line per table because `test_codes.v1_schema` rewrites it line by line. Run the full suite before approving.
Simulation: see `../f1/README.md`.
