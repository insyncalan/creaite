# Guarded changes for 2.6.1: what to apply, and in what order

Nothing here is applied on `v261-line2`. Each diff is Alan's (or Jarvis's, on his say) to apply. Paths are relative to the repo root.

## How the chain is committed (the test convention)

Apply the guarded diffs below in order (steps 1 to 9 and the 283 pair, 11 and 12) and commit them as ONE commit on the 2.6.1 release commit, with the subject starting exactly
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
committed files; run it after the commit that adds the final `.chain` and its diffs, and before the chain commit). Check 9 watches nine
files: tracker, filechange, reach, permissions, backup, update, live_server, client_leak and edit_ai (the client-safety gate on AI suggestions; no chain diff touches it). The reverse-apply is limited to the guarded
files that changed, with `git apply -R --include <path>` for each, so a diff that also touches other files (the `update.py` diff's test hunk,
the goldens in `snapshots-after-chain.diff`) is tolerated: the non-guarded hunks are skipped, not checked. Several diffs to one file
(live_server.py has three, four with 283) are reversed one after another, last first. `test_guarded_chain.py` covers this
(`test_multi_diff_chain_with_live_server_and_a_non_guarded_diff_passes`).

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
and again on 23-10-2026 on head 938f500e with steps 1 to 10 applied (test_reextract then has no expected failures; plain-words total 1,079). Until they are applied, Read again says it couldn't start.
