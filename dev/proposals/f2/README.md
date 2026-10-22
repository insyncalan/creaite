# F2: item numbers above 999 (target 2.6.3)

Guarded files, so **diffs only**. Apply in order, each on top of the last: F1, then
1. `f2-ids-above-999.diff` (guarded: `schema.sql`, `tracker.py`)
2. `f2-readers.diff` (not guarded: 12 Python readers and 8 dashboard source files; `dashboard.html` must be rebuilt from the source by the usual build, not done here)
3. `f2-readers-guarded-live_server.diff` (guarded: `live_server.py`, two patterns)
4. `f2-sortkey.diff` (not guarded: 38 SQL sorts in 12 Python files, the JS comparator `core/idsort.js` and 9 dashboard sort sites in 6 files; 18 files, about 68 lines changed)
5. `f2-sortkey-guarded.diff` (guarded: `tracker.py` 5 sorts, `propose.py` 2 sorts)
6. `f2-skills-text.diff` (`tracker-conventions.md`: "3 digits" becomes "3 to 5 digits")
7. `../f1/f1-test-archive-projects.diff` (a test that compared whole `applies` rows now ignores the five F1 columns)

Tests for the patched tree: `test_f2_ids.py` (8 tests: next number 1003, 5 digits allowed and 6 refused, numeric SQL order, no bare `ORDER BY id` left, JS comparator, no JS text compare left, reader patterns, Excel export and import with `ABC-A-1000`). Three of them fail without the sort diffs. Copy it to `dev/tests/` when the diffs are applied.

## Spec found vs assumed
- Found (issue #315): F2 = widen the six three-digit CHECKs (table rebuilds in `schema.sql` plus a migration), audit and fix every regex, sort and prose pattern that assumes three digits (dashboard, search, links, labels, `replaces`, milestone references, minutes text, Excel round trip, reports); rebuild each table in one transaction, row counts and foreign keys verified, `integrity_check`; test on realistic data with a project of 1,000+ items; rollback by restoring the dated copy and `update.py undo` before any number above 999 exists.
- Assumed: the new width. The check now allows 3 to 5 digits (up to 99,999 a project), digits only, code 3 to 7 capitals or digits as before; new numbers still print with at least three digits (`ABC-A-001`, `ABC-A-1000`). Numbers stay unique per project across actions, RAID, decisions and promises, as now. No change to the display or to who issues numbers (the temporary-ID idea in the design notes is a later step, not F2).

## What changes
- `schema.sql`: the `id` CHECK of `milestones`, `workstreams`, `actions`, `raid`, `decisions`, `promises` (one line each; the old `length(id) - 6` arithmetic is replaced by `instr` on the `-A-` style separator). Same primary keys and columns.
- `tracker.py`: `ITEM_ID` takes 3 to 5 digits; `next_id` looks at IDs 3 to 5 digits long (before: exactly 3, so it would have re-issued `ABC-A-1000`). The migration is the existing diff-driven rebuild: no new step.
- Readers: every ID pattern in `ID-SITES.md` section A moved from exactly three digits to 3 to 5; `build_dashboard.py` `seq` (took the last three characters of the next ID, wrong at 1000+); the dashboard's `nextId`, `msNextId` (took the last three characters). Numeric sort key (decided): no schema change and no new column. Every `ORDER BY ... id` becomes `ORDER BY ..., project, length(id), id` (within one project the IDs of a table share a prefix, so shorter means smaller; same order as before for three-digit IDs). `search.py` line 286 is left as it was: its query joins several tables with no `project` column to lead with, so it keeps the text order as a tie-break only. JS: `idCmp(a, b)` compares the prefix, then the number; replaces `a.id.localeCompare(b.id)` at 9 sites. A generated column was rejected: it would be a second rebuild of the six tables.

## Rollback
Restore the dated database copy and `update.py undo`, **before** any number above 999 exists (the migration alone creates none). After that, restoring loses the items made since. Without a restore the old engine is unsafe: it re-issues `ABC-A-1000` (held, not written, because the key already exists) and its `migrate` refuses with a CHECK error and changes nothing.

## Check
`git apply --check` and `-R --check` pass on `origin/v261-line2` with F1 applied. Tests on the patched tree: test_tracker, test_codes, test_schema_sprint5, test_milestone_states, test_milestones, test_ask_claims, test_item_history, test_edit_ai_client_place pass. The ID check was kept on one line per table because `test_codes.v1_schema` rewrites it line by line. Run the full suite before approving.
Simulation: see `../f1/README.md`.
