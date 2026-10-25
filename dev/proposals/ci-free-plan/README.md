# CI on the GitHub Free plan: use all 20 jobs (patch, not applied)

For Alan and Jarvis. `.github` is guarded, so the workflow change is a patch: `tests.yml.diff` (apply with `git apply dev/proposals/ci-free-plan/tests.yml.diff`). The rest is already on this branch: `dev/tools/ci_plan.py` (the sizing), `dev/tests/test_ci_plan.py` (6 tests), the refreshed `dev/tools/shard_times.txt` (639 files, from run 40154289412) and a team rule in `dev/HOW-WE-WORK.md`.

## 1. Shard counts that fill the plan
The Free plan runs 20 jobs at once (Pro 40, Team 60); a run that uses fewer leaves capacity idle, one that uses more queues. A new `plan` job runs `ci_plan.py` and feeds the matrix:

| Run | Python 3.14 shards | Python 3.9 (quick) | macOS | Total |
|---|---|---|---|---|
| ordinary (PR, main push, hand-started) | **17** | 3 | 0 | 20 |
| macOS also runs | **14** | 3 | 3 | 20 |

The `plan` job ends before the shards start, and "Tests passed" starts after they end, so neither counts. The 12 and the 3 in the workflow are no longer written in two places: `ci_plan.py` is the one.

**Finding: macOS does not run at the gates today.** Its condition is `startsWith(head_ref || ref_name, 'release-')`, but the release branches are named `vNNN-release`; in run 40154289412 (v264b-release) the macOS job shows as skipped (0.0 min). It only runs when hand-started with `macos=true`. The patch keeps that condition as it is and sizes N from the same expression. If you want macOS at gates, change it to `endsWith(..., '-release')`; then each gate holds 3 slots for about 2 hours after Linux ends (macOS is not waited for), and N is 14.

**Estimated slowest shard** (from run 40154289412, 12 shards, -j 4): the real shard times were 11.3 to 24.6 minutes (mean 18.0); the old split was balanced on stale weights. With the refreshed weights every shard sums to within a second of the others (12 shards: 4,322 s; 14: 3,705 s; 17: 3,051 s per shard):

| Shards | Slowest shard today / expected | Gate wall |
|---|---|---|
| 12, old weights | 24.6 min | about 25 min |
| 12, new weights | about 18 min | about 18 min |
| 14 | about 15.5 min | about 16 min |
| **17** | **about 13 min** | **about 13.5 min** |

(Scaled from the mean time, assuming about 2 minutes of fixed set-up per job. A straight fit of wall time against file-time sums only explains 66% of the variation, so these are estimates; the first run will tell.) The Python 3.9 quick tier is the next wall: its three shards ran 8.7 to 17.2 minutes, and with the new weights they sum equally (about 13 minutes each), so it matches the 17-shard run.

## 2. Superseded pushes: already in place
`tests.yml` already has `concurrency: group tests-<PR number or ref>, cancel-in-progress: true`: a newer push to the same pull request or branch cancels the older run and frees its jobs. Hand-started runs get their own group (run id) on purpose. What it cannot do, and no workflow setting can without losing the cancel: two different branches (a PR on v266-release and one on v267-line, a main push, a hand-started run) each hold their own jobs, so the second queues behind the first. That is what rule 3 is for.

## 3. Team rule (added to dev/HOW-WE-WORK.md)
- Only **one CI-triggering push on a release line at a time**; batch fixes and push once, because every push restarts the run (about 14 to 25 minutes).
- Never overlap two gates (a release PR and a v26x-line PR, or a PR and a main push). Check `gh run list --workflow tests.yml --status in_progress` before pushing; wait for it to finish or cancel your own older run.
- A push to **main** also triggers a full run, so merge to main only when no gate is running.
- No hand-started full run while a gate is running (it takes its own 20 slots).

## 4. paths-ignore: keep as it is
It skips `README.md`, `dev/*.md`, `dev/release-notes/**`, `dev/sprints/**` and `dev/mockups/**`. Do not add `dev/proposals/**`: tests read those diffs (`test_lighter_runs_339`, `guarded_chain` pins a digest over their bytes), so a change there must run the tests. A pull request whose files are all ignored starts no run, so if "Tests passed" were a required check it would stay pending on a docs-only PR; today it is not required.

## Risk
The workflow change is the only fragile part: `fromJSON` of the whole matrix is supported, the YAML parses, and `ci_plan.py` is tested, but I cannot run Actions from here. Try it on a throwaway branch first (a hand-started run with `files` empty). If the `plan` job fails the tests are skipped and "Tests passed" is red, so it fails closed.
