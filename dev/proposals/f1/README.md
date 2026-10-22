# F1: nullable foundation columns (target 2.6.2) and the F1 -> F2 -> F3 simulation

Guarded files, so **diffs only**: nothing here is applied in the tree. `f1-nullable-columns.diff` touches `schema.sql` and `tracker.py`.

## Spec found vs assumed
- Found (plan issue #314, "Semi-shared database foundation"): F1 = additive nullable columns (author, origin, sequence, base_version, engine version on applies and change_log), a migration and rollback test, nothing reads them yet, one guarded diff set.
- Assumed: which table gets which column. `applies`: author, origin, sequence, engine_version. `change_log`: author, origin, sequence, base_version, engine_version (a base version belongs to a row change, not a whole apply). Only `engine_version` is written (on each new apply row, by `tracker.stamp_apply`); the others stay NULL. Column types: TEXT, INTEGER for sequence and base_version.

## What changes
- `schema.sql`: five nullable columns on `applies`, five on `change_log`, added after the existing columns.
- `tracker.py`: `engine_version()` (reads VERSION) and `stamp_apply()` (sets `applies.engine_version`, and does nothing if the column is not there yet), called by `apply` and `undo-changes`.
- No other reader was found that needs a change (every INSERT into the two tables names its columns); not exhaustively audited for `SELECT *` on them. Simulation: apply, undo and recode round trips, doctor and the dashboard/Excel rebuild after each apply all pass.

## How migration works today (read from the code)
There is **no schema version number**. `tracker.py migrate` compares each stored `CREATE TABLE` with `schema.sql` (`outdated_tables`, spaces and comments ignored). For each table that differs it takes a database copy (`backup_db("migrate")`, kept 14 days), then in one transaction with foreign keys off: creates `<t>__new`, copies the shared columns, drops the old table, renames, checks row counts per table and `PRAGMA foreign_key_check`, and commits (or rolls back and changes nothing). A new table is just created by `executescript(schema.sql)`. `update.py` backs up the engine (last three kept) and runs `migrate` after an install; `doctor.py` reports "schema up to date" or the stale tables. So F1 needs no new migration step: changing `schema.sql` is the migration, and it rebuilds the two tables (`applies`, `change_log`).

## Rollback
Restore the dated database copy (`system/backups/tracker-<time>-migrate.db`, or the manual dated copy) and `update.py undo` (engine back). Simulation: the previous engine reads, applies, undoes and recodes against the restored copy. If the old engine is run on the new database without a restore, apply and undo still work (the new columns are nullable); an old `migrate` quietly rebuilds the two tables without the new columns (the stamps are lost, nothing else).

## Check
`git apply --check` and `git apply -R --check` pass on a clean checkout of `origin/v261-line2`. Tests run on the patched tree: test_tracker, test_codes, test_schema_sprint5, test_milestone_states pass.

## The simulation
`python3 dev/proposals/f1/simulate_chain.py [--f3 diff ...]` builds a throwaway vault from the demo data in a temporary folder (never a real vault), seeds project ABC through `tracker.py apply` (990 numbers), then for each step: dated backup, apply the diffs to the copy, `migrate` (timed), integrity and foreign-key checks, row counts, apply/undo and recode/undo round trips, a rollback proof (dated copy plus previous engine in a second throwaway vault), and the old engine run on the new database. `simulation-results.json` is the last full run (F1, F2, and F3 with `f3-recode-other.diff`).
`f3-recode-other.diff` is a one-line fix F3 needs: its new `people` table makes `propose.py recode` refuse ("doesn't know how to recode people") until `people` is added to `RECODE_OTHER` in `tracker.py`.

## Settled F3 re-run (F3 branch v264-f3 at 0ea75180) and the extras
Run: `python3 dev/proposals/f1/simulate_chain.py --f3 <schema/tracker/propose/backup/recode diffs> --f3-copy people_table.py --f3-copy person_id.py --f3-fixture <fixture> --f3-cmd "tracker.py people-import --file system/staging/drafts/people-fixture.md" ...` (the register files are copied into the copy; the engine will not read files outside the vault). `simulation-results.json` holds the result. Without `recode.diff` the F3 step's recode refuses ("doesn't know how to recode people"), with it the round trip passes (both runs done).
`f1-test-archive-projects.diff`: `test_archive_projects.Migration` compared whole `applies` rows and failed on the five F1 columns; it now ignores them.
