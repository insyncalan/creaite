# Guarded changes for 2.6.1: what to apply, and in what order

Nothing here is applied on `v261-line2`. Each diff is Alan's (or Jarvis's, on his say) to apply. Paths are relative to the repo root.
Checked 22-10-2026: the first nine below apply one after another, in this order, with `git apply` on the assembled `v261-line2` head
(a throwaway detached worktree, not committed). The two 283 diffs also pass `git apply --check` on top of that chain.

## How the chain is committed (the test convention)

Apply the nine diffs below in order and commit them as ONE commit on the 2.6.1 release commit, with the subject starting exactly
`Guarded 2.6.1 chain:` (for example `Guarded 2.6.1 chain: tracker, update, live_server, schema`). `dev/tests/test_word_export_227.py`
check 9 (`dev/tests/guarded_chain.py`) lets a commit with that prefix change guarded scripts only if all of this holds:
- the chain list `dev/proposals/GUARDED-2.6.1.chain` (one path per line, apply order) and the diffs it names are read from the marked
  commit's PARENT, never its own tree, and their sha256 (`CHAIN_SHA256` in `guarded_chain.py`; `python3 dev/tests/guarded_chain.py`
  prints it) matches the pin, so a commit cannot bring its own proof; the chain and the pin are therefore in the line before the chain
  commit, and changing either takes Alan's say;
- the marked commit itself touches every guarded file that changed over the release, and reverse-applying the pinned diffs to them gives
  each file's parent content (an extra edit, an unlisted guarded file, a diff that doesn't reverse, or an unmarked earlier edit fails).
The check diffs against the v260 release commit (`BASE`, a sha, not a branch name), with renames shown as delete plus add. If the
history is missing the test skips, except when `CI=true`, where it fails. If a diff joins or leaves the chain (for example 283's
`reach.diff`), change the `.chain` file and the pin in the same step. `dev/tests/test_guarded_chain.py` proves all this on a throwaway
repo, including the forgeries. CI needs `fetch-depth: 0`: `dev/proposals/guardtest/tests-yml-fetch-depth.diff`.

### The pin, and what the assembler does

The final `.chain` is the nine diffs below, the 283 pair (`reach.diff`, `live_server.diff`) and `snapshots-after-chain.diff`, in apply order.
Once it is in, the assembler recomputes the pin and puts it in `CHAIN_SHA256` (`python3 dev/tests/guarded_chain.py` prints it from the
committed files; run it after the commit that adds the final `.chain` and its diffs, and before the chain commit). Check 9 watches eight
files: tracker, filechange, reach, permissions, backup, update, live_server and client_leak. The reverse-apply is limited to the guarded
files that changed, with `git apply -R --include <path>` for each, so a diff that also touches other files (the `update.py` diff's test hunk,
the goldens in `snapshots-after-chain.diff`) is tolerated: the non-guarded hunks are skipped, not checked. Several diffs to one file
(live_server.py has three, four with 283) are reversed one after another, last first. `test_guarded_chain.py` covers this
(`test_multi_diff_chain_with_live_server_and_a_non_guarded_diff_passes`).

## Order

| # | Diff | Guarded file | What it does | Tests that depend on it |
|---|------|--------------|--------------|-------------------------|
| 1 | `dev/proposals/261-low-notes/tracker-resolve-einval.diff` (branch `origin/v261-low-notes`; its paths.py change and test are already merged only if that branch is merged: the diff is the guarded part only) | `tracker.py` | A NUL byte in a path is refused with its own message ("path contains a NUL character") | `test_paths_resolved_low_notes` (on `v261-low-notes`) |
| 2 | `dev/proposals/261-inode-gap/tracker-inode.py.diff` | `tracker.py` | Closes the inode gap in the file checks | its README names them |
| 3 | `dev/proposals/work-item-history/schema.diff` | `schema.sql` | New table `item_events` and indexes | `test_item_history`, `test_item_history_route` |
| 4 | `dev/proposals/work-item-history/tracker.diff` | `tracker.py` | `emit_event()` writes an event row per change; undo and recode follow | same |
| 5 | `dev/proposals/291/live_server.py.diff` | `live_server.py` | "check my mail ..." added to `PANEL_SWEEP_WORDS` | `test_the_plain_words_are_sweeps` (expected failure until applied) |
| 6 | `dev/proposals/291/update.py.diff` | `update.py` | The update refusals in plain words; carries the `test_update.py` hunk and the plain-words baseline hunk | `test_update`, `test_plain_words` (total 1,090 to 1,087 for this diff) |
| 7 | `dev/proposals/300/live_server.diff` | `live_server.py` | Routes for Start creaite at sign-in | `test_autostart_300` (two tests skip until applied) |
| 8 | `dev/proposals/work-item-history/live_server.diff` | `live_server.py` | `GET /api/item/history?id=...` | `test_item_history_route` |
| 9 | `dev/proposals/work-item-history/tests-after.diff` | the two item-history tests | Removes the five `@unittest.expectedFailure` decorators; apply last | `test_item_history`, `test_item_history_route` |

Steps 3, 4, 8, 9 are the work-item-history set; its own recommended order is schema, tracker, live_server, tests-after.
The hunks have distinct anchors, so no order dependence was found between the groups.

## 300 order (verified on 5369ebd1 and with the work-item-history diffs in either order)

Apply the 300 diff after both 291 diffs: 291 `live_server.py.diff`, 291 `update.py.diff`, then 300 `live_server.diff`
(`dev/proposals/300/live_server.diff` and its README were updated by `v261-300c`). The table above is in that order. `test_autostart_300_routes` runs in both states: when the routes are
absent it applies the diff to a throwaway copy and tests that, so it is green before and after the diff is applied.

## Until applied

- `test_item_history` and `test_item_history_route`: marked expected failures.
- `test_the_plain_words_are_sweeps`: expected failure.
- `test_autostart_300`: two tests skip.
- Plain-words total: `v261-line2` is at 1,087 (via #291b); step 5 takes it to 1,084 (the baseline file only falls).

## If it joins (not merged, not in the chain)

`dev/proposals/283-reextract/` on `origin/v26-283-2` (not copied here): `reach.diff` and `live_server.diff`, applied together in one
command (the README says so). Both pass `git apply --check` on the chain above. Until they join, Read again says it couldn't start.
