# Guarded changes for 2.6.1: what to apply, and in what order

Nothing here is applied on `v261-line2`. Each diff is Alan's (or Jarvis's, on his say) to apply. Paths are relative to the repo root.

## Order (the one to use; one source of truth)

Apply in this order, with `git apply`, on the assembled `v261-line2` head. Checked 23-10-2026 on a throwaway detached worktree off `236e6ed4`:
all nine apply one after another, all nine reverse in the opposite order, and `python3 dev/tools/check.py` prints `check: OK` with the whole chain applied.

| # | Diff | Guarded file | What it does | Tests that depend on it |
|---|------|--------------|--------------|-------------------------|
| 1 | `dev/proposals/261-low-notes/tracker-resolve-einval.diff` (branch `origin/v261-low-notes`; the diff is the guarded part only) | `tracker.py` | A NUL byte in a path is refused with its own message | `test_paths_resolved_low_notes` (on `v261-low-notes`) |
| 2 | `dev/proposals/261-inode-gap/tracker-inode.py.diff` | `tracker.py` | Closes the inode gap in the file checks | its README names them |
| 3 | `dev/proposals/work-item-history/schema.diff` | `schema.sql` | New table `item_events` and indexes | `test_item_history`, `test_item_history_route` |
| 4 | `dev/proposals/work-item-history/tracker.diff` | `tracker.py` | `emit_event()` writes an event row per change; undo and recode follow | same |
| 5 | `dev/proposals/291/live_server.py.diff` | `live_server.py` | "check my mail ..." added to `PANEL_SWEEP_WORDS` (the code check is `panel_sweep_code_ok`) | `test_the_plain_words_are_sweeps` (expected failure until applied) |
| 6 | `dev/proposals/291/update.py.diff` | `update.py` | The update refusals in plain words (`refuse()`); carries the `test_update.py` hunk and the plain-words baseline hunk | `test_update`, `test_plain_words` (takes three entries off the baseline) |
| 7 | `dev/proposals/300/live_server.diff` | `live_server.py` | Routes for Start creaite at sign-in (`autostart_set_route` split into small helpers) | `test_autostart_300` (two tests skip once applied), `test_autostart_300_routes` |
| 8 | `dev/proposals/work-item-history/live_server.diff` | `live_server.py` | `GET /api/item/history?id=...` | `test_item_history_route` |
| 9 | `dev/proposals/work-item-history/tests-after.diff` | the two item-history tests | Removes the five `@unittest.expectedFailure` decorators; apply last | `test_item_history`, `test_item_history_route` |
| 10 | `dev/proposals/snapshots-after-chain.diff` | `dev/tests/snapshots/today.html`, `settings-health.html` (not guarded) | The two goldens that change once the 300 routes exist | `test_snapshots` |

Steps 5 and 6 may swap and 8 may come before 7 (distinct anchors); 7 comes after 5 and 6.
The 291 and 300 diffs were reworked on 23-10-2026 so `check.py` stays at its limits with them applied (two functions under the complexity limit, long
lines wrapped, no `except Exception: pass`); behaviour and the tests' expectations are unchanged.

## The goldens go in together with the chain (step 10)

With the 300 routes present the page shows its Start-at-sign-in switch (Settings, Health) and Today's first-run question, so the `today` and
`settings-health` goldens differ (15 diff lines). Without the routes the old goldens are right, so the new ones must never land on their own.
Apply them after step 9: `git apply dev/proposals/snapshots-after-chain.diff`, then check with
`python3 dev/tests/test_snapshots.py` (passes only with the chain and this patch; without the chain the old goldens are the ones that pass).
The same two files are on the branch `v261-chainfix` in their own commit ("Goldens after the chain"); take that commit only together with the chain.

## Until applied

- `test_item_history` and `test_item_history_route`: marked expected failures.
- `test_the_plain_words_are_sweeps`: expected failure.
- `test_autostart_300`: two tests skip.
- Plain-words total: `v261-line2` has the baseline file at its own total (1,082 at 23-10-2026); step 6 only lowers it (the baseline file only falls).

## Last pair: #283 Read again (merged here as `v261-283`, 23-10-2026)

| # | Diff | Guarded files | What it does | Tests that depend on it |
|---|------|---------------|--------------|-------------------------|
| 11 | `dev/proposals/283-reextract/reach.diff`, then 12 `dev/proposals/283-reextract/live_server.diff` | `reach.py`, `live_server.py` | The `reextract` mode and the Read again routes and run kind | `test_reextract` (six expected failures until applied) |

Apply the pair together, in one command (its README says so), after steps 1 to 10. Both passed `git apply --check` on the chain on 22-10-2026,
before the 291 and 300 rework; recheck on the final head. Until they are applied, Read again says it couldn't start.
