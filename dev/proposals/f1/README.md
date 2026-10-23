# F1: nullable foundation columns (ships in 2.6.2)

Source: plan issue #314 ("Semi-shared database foundation") and #315 (migration and rollback). `schema.sql` and `tracker.py` are guarded, so the change is **diffs only**, nothing here is applied in the tree.

## What changes
- `schema.sql`: five nullable columns on `change_log` (author, origin, sequence, base_version, engine_version) and four on `applies` (author, origin, sequence, engine_version). All TEXT except sequence and base_version (INTEGER). No default, no constraint.
- `tracker.py`: `engine_version()` reads `VERSION`; `stamp_apply(con, apply_id)` sets `applies.engine_version`. It is called at every place a new apply row is made: `cmd_apply`, `cmd_undo_changes` and `retire_missed` (the migrate step). It does nothing if the column is missing, so a database that has not been migrated yet keeps working.
- Nothing reads the new columns. Only `engine_version` is written. Old rows keep NULL.
- Assumed (the plan names the columns, not the tables): which table gets which column. A base version belongs to a row change, so only `change_log` has it.

## Why
A later release needs to know who made a change, where, in what order, and against which row version, and which engine wrote it. Adding the columns first, empty, means that release changes no table layout.

## Diffs and apply order (rebased on release2, 23-10-2026)
Base: `origin/v261-release2` (27a6bc1d), the green 2.6.1 candidate: the 12-diff guarded chain is ALREADY applied there as one marked commit, so no chain step is needed. Apply, in this order, on that tree:
1. `f1-nullable-columns-after-chain.diff` (guarded: `schema.sql`, `tracker.py`). `git apply --check` and `-R --check` pass on release2.
2. `writer-pins-after-f1.diff` (not guarded: `dev/tests/pinned/*.json` re-recorded, plus a docstring note in `test_writer_pinned.py`). It is a companion: the pins hold only WITH F1 applied; on the unchanged tree the 2.6.1 pins stay as they are and pass. Apply it in the same change set as step 1.
3. Then F2 (`dev/proposals/f2/` on `origin/v262-f1`; its README has the order), then F3 (`dev/proposals/f3/` on `origin/v264-f3`).
The older `f1-nullable-columns.diff` (frozen line without the chain) is gone: release2 replaces that base.
Committed directly (not guarded): `dev/tests/test_f1_columns.py` (skips when F1 is not applied) and the `test_archive_projects.Migration` tweak that ignores the five F1 keys on `applies` and `change_log`.

F2 and F3 checked with `git apply --check` in order on release2 + F1 (23-10-2026): all six F2 diffs apply, F3 `schema.diff`, `tracker.diff`, `propose.diff` and `backup.diff` apply; **`f3/recode.diff` no longer applies** (hunk at `tracker.py:4623`: `RECODE_OTHER` now also lists `item_events`, from the chain). It does not apply on release2 alone either. Not fixed here.

## Rowid fix (Cap M-B, F1c, 23-10-2026)
`migrate_schema` rebuilt a table with `INSERT INTO t__new (cols) SELECT cols FROM t`, which gives a table with no INTEGER PRIMARY KEY (`change_log`) fresh rowids: after a gap (a row deleted by hand, a VACUUM) every later row is renumbered, and `item_events.change` and a revert's `via` string (`revert:<rowids>`) then name other rows. F1 is the first release that forces every vault to rebuild `change_log`. The diff now also changes the rebuild (`tracker.py`: a new helper `copy_rows`, which keeps `migrate_schema` under the complexity limit that `check.py` enforces): for a table without a single INTEGER PRIMARY KEY it copies `rowid` explicitly, in rowid order (`INSERT INTO t__new (rowid, cols) SELECT rowid, cols FROM t ORDER BY rowid`); a table with its own integer key (`applies`) is unchanged, its `apply_id` is a normal column. Test `test_migrate_keeps_change_log_rowids_when_there_is_a_gap` (gap in `change_log`, a deleted `applies` row, `item_events` links, `apply_id` links, foreign keys, second migrate a no-op, new rows after the highest rowid): red before the fix (row 12 became 11 etc.), green after; mutant "drop the rowid copy" fails it. `simulate_chain.py` now records `change_log_rowids_and_event_links_kept` for each step. The writer pins need no re-record: the rebuild output is the same.

## Chain and pin (check 09, Cap M-A)
F1 is part of the 2.6.2 chain: `f1-nullable-columns-after-chain.diff` is entry 1 of `dev/proposals/GUARDED-2.6.2.chain` (on `origin/v262-chain`, 7687ee67), followed by `writer-pins-after-f1.diff`. Changing this diff changes `CHAIN2_SHA256` in `dev/tests/guarded_chain.py`; the final assembly agent on v262-line recomputes the pin (`guarded_chain.py` prints it). This regeneration (F1c) changes it: the old pin does not hold for it.

## Review fixes (Cap, #314)
- M1: `engine_version()` catches `(OSError, ValueError)` (a non-UTF-8 `VERSION` is a `UnicodeDecodeError`) and keeps only a value of at most 32 characters matching `^\d+\.\d+\.\d+(?:[.+-][0-9A-Za-z.]+)?$`, else NULL. A NUL, a 200,000-character file, a directory or odd text all give NULL and the apply lands. L1 is covered by the same check. L2: a comment in `schema.sql` says `base_version` is the row version, not the dashboard's draft `base_version`.
- M2: `old_database()` rebuilds `applies` and `change_log` from the pre-F1 CREATE statements written out in the test, no `DROP COLUMN` on the new text.
- M3: new tests for the stamps in `undo-changes` and `retire_missed` and for the new engine on an unmigrated database (see Mutants below).
- M4: `test_writer_pinned` re-recorded deliberately (`CREAITE_PIN_RECORD=1`). Checked by script: with the five F1 keys removed from `applies` and `change_log`, each of the 16 re-recorded pin files equals the 2.6.1 pin. The record run also overwrites `old-code.sql` and `old-code-undo.json` (the code-before-the-split fixture); both were restored to their earlier text and are not in the companion diff.

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
- `dev/tests/test_f1_columns.py` (15 tests; 8 original, 6 new for M1 and M3, 1 new for Cap's M-B): the columns exist and are nullable with no default; an apply stamps the engine version and nothing else; no `VERSION` file gives NULL; undo and recode round trips; migrate from an old-shape database adds the columns, keeps every row and value, old rows keep NULL, a second migrate is a no-op, then new applies stamp; the previous engine's queries (explicit column lists) still read and write the migrated tables; rollback is the dated copy. It skips when the diff is not applied. To run it: apply the diff in a throwaway worktree on release2.
- `test_archive_projects.Migration` compared whole `applies` rows; it now ignores the five new columns (committed).
15 of 15 pass with F1 applied, on Python 3.14 and 3.9.

## The simulation
`python3 dev/proposals/f1/simulate_chain.py [--f1-only] [--no-chain]`. It builds a throwaway vault from the demo data in a temporary folder (never a real vault), applies the 2.6.1 chain to the copy (12 diffs), seeds project ABC through `tracker.py apply` (990 numbers), then for each step: dated backup, apply the diff, `migrate` (timed), `integrity_check`, `foreign_key_check`, row counts before and after, apply and undo, recode and undo, a rollback proof (dated copy plus the previous engine in a second throwaway vault) and the old engine on the new database. `simulation-results-release2.json` is the run with `--f1-only` on release2 (migrate 0.17 s, 11,519 change_log rows, integrity ok, no foreign-key problems, second migrate a no-op, doctor exit 0, rollback proof passes). `simulation-results-chain.json` is the earlier run on line plus chain (F1 then F2).

## What Cap must review
- Both guarded diffs (`schema.sql` table definitions; `tracker.py`: the two new functions and the three call sites). The rebuild of two tables with about 11,000 change_log rows in the simulation takes under a second.
- That every place that creates an apply row is stamped: three in `tracker.py`; no other script inserts into `applies` (grep).
- Unaudited: any `SELECT *` on `applies` or `change_log` that assumes a fixed column count (build_dashboard's `LOG_SQL` uses `c.*`; the simulation's dashboard rebuild and doctor pass).
- That `item_events` (new in the chain) is left alone: it has its own `origin` and `actor` words, no clash with the new column names.

## Mutants (against the revised diff, 23-10-2026)
Eleven mutants run against `test_f1_columns.py`; all killed: no stamp in `cmd_apply`, in `cmd_undo_changes`, in `retire_missed`; the "column missing" guard removed; `ValueError` not caught; no version pattern; no length bound; no `strip`; `base_version NOT NULL DEFAULT 0`; `sequence DEFAULT 0`; `author` stamped too.
