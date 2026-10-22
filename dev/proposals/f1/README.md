# F1: nullable foundation columns (ships in 2.6.2)

Source: plan issue #314 ("Semi-shared database foundation") and #315 (migration and rollback). `schema.sql` and `tracker.py` are guarded, so the change is **diffs only**, nothing here is applied in the tree.

## What changes
- `schema.sql`: five nullable columns on `change_log` (author, origin, sequence, base_version, engine_version) and four on `applies` (author, origin, sequence, engine_version). All TEXT except sequence and base_version (INTEGER). No default, no constraint.
- `tracker.py`: `engine_version()` reads `VERSION`; `stamp_apply(con, apply_id)` sets `applies.engine_version`. It is called at every place a new apply row is made: `cmd_apply`, `cmd_undo_changes` and `retire_missed` (the migrate step). It does nothing if the column is missing, so a database that has not been migrated yet keeps working.
- Nothing reads the new columns. Only `engine_version` is written. Old rows keep NULL.
- Assumed (the plan names the columns, not the tables): which table gets which column. A base version belongs to a row change, so only `change_log` has it.

## Why
A later release needs to know who made a change, where, in what order, and against which row version, and which engine wrote it. Adding the columns first, empty, means that release changes no table layout.

## Diffs and apply order
Two variants of the same change, because the 2.6.1 guarded chain edits the same lines of `schema.sql` and `tracker.py`:
1. `f1-nullable-columns.diff`: on the frozen line (`origin/v261-line2`, bcc008f5) without the chain.
2. `f1-nullable-columns-after-chain.diff`: on the line with the 2.6.1 chain applied (`GUARDED-2.6.1.chain`, 12 diffs, in order). **This is the one that ships**: 2.6.1 is line plus chain, F1 comes after it.
Then F2 (`../f2/`, stacks on F1, order in its README), then F3. The non-guarded test change `f1-test-archive-projects.diff` is already committed on this branch; it is kept for F2's list.
`f3-recode-other.diff` is the one-line fix F3 needs (`people` in `RECODE_OTHER`); not touched here.

## Migration (read from the code)
There is no schema version number. `tracker.py migrate` compares each stored `CREATE TABLE` with `schema.sql`, and for each table that differs takes a dated copy (`backup_db("migrate")`), rebuilds it in one transaction (new table, copy the shared columns, drop, rename), checks row counts and foreign keys, and commits or changes nothing. So changing `schema.sql` is the migration: it rebuilds `applies` and `change_log`. `update.py` runs `migrate` after an install; `doctor.py` reports "schema up to date". A second `migrate` does nothing.

## Rollback
Restore the dated copy (`system/backups/tracker-<time>-migrate.db`, or the manual one) and `update.py undo`, **before anything else writes**: anything written after the migration is lost by a restore. Running the old engine on the new database without a restore also works (apply and undo both do, the columns are nullable), but an old `migrate` quietly rebuilds the two tables without the new columns, so the stamps are lost and nothing else.

## Safe procedure on a real database
1. Dated backup first (`update.py` does this; or copy `system/tracker.db` yourself).
2. Trial on a copy: a throwaway vault with the copied database, run `tracker.py migrate`, then `doctor.py`. Look at the row counts (the tool prints applies and change_log), `PRAGMA integrity_check`, `PRAGMA foreign_key_check`.
3. Only then update the real vault. If anything looks wrong, restore the dated copy and `update.py undo` before the next apply.
`simulate_chain.py` does steps 1 and 2 on demo data (below).

## Tests
- `dev/tests/test_f1_columns.py` (8 tests): the columns exist and are nullable with no default; an apply stamps the engine version and nothing else; no `VERSION` file gives NULL; undo and recode round trips; migrate from an old-shape database adds the columns, keeps every row and value, old rows keep NULL, a second migrate is a no-op, then new applies stamp; the previous engine's queries (explicit column lists) still read and write the migrated tables; rollback is the dated copy. It skips when the diff is not applied. To run it: apply the diff in a throwaway worktree (line2 variant on the frozen line, after-chain variant on line plus chain), copy the test in.
- `test_archive_projects.Migration` compared whole `applies` rows; it now ignores the five new columns (committed).
Both variants: 8 of 8 pass.

## The simulation
`python3 dev/proposals/f1/simulate_chain.py [--f1-only] [--no-chain]`. It builds a throwaway vault from the demo data in a temporary folder (never a real vault), applies the 2.6.1 chain to the copy (12 diffs), seeds project ABC through `tracker.py apply` (990 numbers), then for each step: dated backup, apply the diff, `migrate` (timed), `integrity_check`, `foreign_key_check`, row counts before and after, apply and undo, recode and undo, a rollback proof (dated copy plus the previous engine in a second throwaway vault) and the old engine on the new database. `simulation-results-chain.json` is the run on line plus chain (F1 then F2; migrate 0.17 s and 0.16 s, integrity ok, no foreign-key problems, second migrate a no-op, rollback proof passes, doctor exit 0). `simulation-results.json` is the earlier run on the old base, with F3.

## What Cap must review
- Both guarded diffs (`schema.sql` table definitions; `tracker.py`: the two new functions and the three call sites). The rebuild of two tables with about 11,000 change_log rows in the simulation takes under a second.
- That every place that creates an apply row is stamped: three in `tracker.py`; no other script inserts into `applies` (grep).
- Unaudited: any `SELECT *` on `applies` or `change_log` that assumes a fixed column count (build_dashboard's `LOG_SQL` uses `c.*`; the simulation's dashboard rebuild and doctor pass).
- That `item_events` (new in the chain) is left alone: it has its own `origin` and `actor` words, no clash with the new column names.
