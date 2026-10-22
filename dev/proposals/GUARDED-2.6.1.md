# Guarded changes for 2.6.1: what to apply, and in what order

Nothing here is applied on `v261-line2`. Each diff is Alan's (or Jarvis's, on his say) to apply. Paths are relative to the repo root.
Checked 22-10-2026: the first nine below apply one after another, in this order, with `git apply` on the assembled `v261-line2` head
(a throwaway detached worktree, not committed). The two 283 diffs also pass `git apply --check` on top of that chain.

## Order

| # | Diff | Guarded file | What it does | Tests that depend on it |
|---|------|--------------|--------------|-------------------------|
| 1 | `dev/proposals/261-low-notes/tracker-resolve-einval.diff` (branch `origin/v261-low-notes`; its paths.py change and test are already merged only if that branch is merged: the diff is the guarded part only) | `tracker.py` | A NUL byte in a path is refused with its own message ("path contains a NUL character") | `test_paths_resolved_low_notes` (on `v261-low-notes`) |
| 2 | `dev/proposals/261-inode-gap/tracker-inode.py.diff` | `tracker.py` | Closes the inode gap in the file checks | its README names them |
| 3 | `dev/proposals/work-item-history/schema.diff` | `schema.sql` | New table `item_events` and indexes | `test_item_history`, `test_item_history_route` |
| 4 | `dev/proposals/work-item-history/tracker.diff` | `tracker.py` | `emit_event()` writes an event row per change; undo and recode follow | same |
| 5 | `dev/proposals/291/update.py.diff` | `update.py` | The update refusals in plain words; carries the `test_update.py` hunk and the plain-words baseline hunk | `test_update`, `test_plain_words` (total 1,090 to 1,087 for this diff) |
| 6 | `dev/proposals/291/live_server.py.diff` | `live_server.py` | "check my mail ..." added to `PANEL_SWEEP_WORDS` | `test_the_plain_words_are_sweeps` (expected failure until applied) |
| 7 | `dev/proposals/300/live_server.diff` | `live_server.py` | Routes for Start creaite at sign-in | `test_autostart_300` (two tests skip until applied) |
| 8 | `dev/proposals/work-item-history/live_server.diff` | `live_server.py` | `GET /api/item/history?id=...` | `test_item_history_route` |
| 9 | `dev/proposals/work-item-history/tests-after.diff` | the two item-history tests | Removes the five `@unittest.expectedFailure` decorators; apply last | `test_item_history`, `test_item_history_route` |

Steps 3, 4, 8, 9 are the work-item-history set; its own recommended order is schema, tracker, live_server, tests-after.
The hunks have distinct anchors, so no order dependence was found between the groups.

## Until applied

- `test_item_history` and `test_item_history_route`: marked expected failures.
- `test_the_plain_words_are_sweeps`: expected failure.
- `test_autostart_300`: two tests skip.
- Plain-words total: `v261-line2` is at 1,087 (via #291b); step 5 takes it to 1,084 (the baseline file only falls).

## If it joins (not merged, not in the chain)

`dev/proposals/283-reextract/` on `origin/v26-283-2` (not copied here): `reach.diff` and `live_server.diff`, applied together in one
command (the README says so). Both pass `git apply --check` on the chain above. Until they join, Read again says it couldn't start.
