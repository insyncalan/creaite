# Parked shared-database work

Status of every branch below: parked, unmerged, 23-10-2026. The shared-database
work (F1, F2, F3) was paused by Alan. F1 was cut out of the 2.6.2 line. Nothing
here is on main; the branches stay on origin untouched.

| Branch | Head | Holds |
|--------|------|-------|
| `v262-f1` | `7cc26d06` | First F1 for 2.6.2: nullable foundation columns as guarded diffs (line 2 and after-chain), `test_f1_columns`, chain simulation, F2 sort key rebased on line 2, plus F2 drafts under `dev/proposals/f2/`. |
| `v262-f1b` | `ca07d772` | F1 rebased onto release 2 and fixed after Cap's review (version stamp cannot fail an apply, old-shape fixture, undo cases). Adds `simulation-results-release2.json` and `writer-pins-after-f1.diff`. |
| `v262-f1c` | `957fcfd2` | Latest F1: migrate keeps `change_log` rowids across a gap, `copy_rows` helper keeps `migrate_schema` under the complexity limit, regenerated diff, `simulation-results-f1c.json`. |
| `v262-chain` | `7687ee67` | The 2.6.2 guarded chain. F1 entries only: `dev/proposals/f1/README.md`, `f1-nullable-columns-after-chain.diff` and `writer-pins-after-f1.diff`. The rest of the branch is not F1. |
| `v264-sim` | `a664afc4` | F1 and F2 draft diffs, `simulate_chain.py`, F2 diffs and `ID-SITES.md` (every ID site), numeric sort key with tests, F3 fixture and a 1,000-person register; settled F3 re-run results and simulation timings in `simulation-results.json`. |
| `v264-f3` | `1f15ad70` | F3 people table: guarded diffs (schema, tracker, propose, backup, recode), `people_table.py`, `person_id.py`, tests. README records "Decided by Alan, 23-10-2026": all eight recommendations adopted. |

## Files worth knowing

- `dev/proposals/f1/`: README, nullable-columns diffs, `simulate_chain.py`, simulation results.
- `writer-pins-after-f1.diff` (on `v262-f1b`, `v262-f1c`, `v262-chain`): the companion that re-pins the writer after F1, about 2.4 MB (103,023 lines). Generated; do not review by hand.
- `dev/proposals/f2/`: ID-sites list, readers, sort key and above-999 ID diffs, `test_f2_ids.py`.
- `dev/proposals/f3/` (on `v264-f3`): the Decided-by-Alan README.

## To resume

Start from `v262-f1c` for F1 and `v264-f3` for F3. Rebase onto the then-current
release line first; the diffs were written against 2.6.1 and the 2.6.2 chain.
