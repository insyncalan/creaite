# #363: unmerged branches of insyncalan/creaite, classified (read-only)

Made 27-10-2026 from `origin/main` a62fbb0a: **106 remote branches not merged into main** (206 remote branches in all; the issue's 282 was before later clean-ups). Nothing was deleted, pushed or changed. Regenerate with `python3 dev/tools/branch_report.py` (read-only).

**Summary:** delete 7 · delete only if the branch holding its commits is kept 3 · owner decides 19 · keep 77.

**How each branch was judged:**
- **delete:** its change is already in main. Either every commit's patch is there (`git cherry`, which catches squash and cherry-pick merges), or main holds the branch's whole diff (a reverse-apply check against main's tree). Or every commit is also in another branch that is kept.
- **delete if kept:** every commit is in another branch that is itself 'owner decides'; delete this one only if that one is kept.
- **keep:** a live release line or team branch (v269*, v2610*, v27*, team-*, ai-*), an open PR, or a change in the last 3 days.
- **owner decides:** commits not in main and in no newer branch. Not safe to delete without its author's word.
- **Caution:** the reverse-apply check reads 'not in main' when main has since changed the same lines, so it never wrongly suggests a delete; it may miss some that could go.

| Suggest | Branch | Last commit | Author | Ahead/behind main | Commits not in main | Files | PR | Why |
|---|---|---|---|---|---|---|---|---|
| delete | `dev-ci-free-plan` | 2026-10-25 | januscollab | 1/190 | 0 | 6 |  | its change is already in main (every commit's patch is there) |
| delete | `dev-test-speed-vault` | 2026-10-25 | januscollab | 2/314 | 2 | 5 |  | every commit is also in dev-test-speed |
| delete | `v261-line3` | 2026-10-23 | januscollab | 6/565 | 0 | 12 |  | its change is already in main (every commit's patch is there) |
| delete | `v262-line` | 2026-10-24 | januscollab | 4/481 | 0 | 4 |  | its change is already in main (every commit's patch is there) |
| delete | `v266-341fix` | 2026-10-25 | januscollab | 1/240 | 0 | 1 |  | its change is already in main (every commit's patch is there) |
| delete | `v266-358prop` | 2026-10-25 | januscollab | 1/233 | 0 | 1 |  | its change is already in main (every commit's patch is there) |
| delete | `v267-chain` | 2026-10-25 | januscollab | 7/167 | 0 | 19 |  | its change is already in main (every commit's patch is there) |
| delete if kept | `cdp-resize-waits` | 2026-10-15 | januscollab | 2/2799 | 2 | 5 |  | every commit is also in main-batch (delete only if that branch is kept) |
| delete if kept | `rm-permission-panel-bak` | 2026-10-15 | januscollab | 1/2741 | 1 | 1 |  | every commit is also in main-batch (delete only if that branch is kept) |
| delete if kept | `v26-fetch-transcripts` | 2026-10-20 | januscollab | 9/1241 | 8 | 17 |  | every commit is also in v264-250 (delete only if that branch is kept) |
| owner decides | `fix-cdp-resize` | 2026-10-15 | insyncalan | 1/2887 | 1 | 10 |  | 1 commit(s) not in main, last 2026-10-15, no newer branch holds them |
| owner decides | `handchecks-v251c` | 2026-10-20 | insyncalan | 2/1317 | 2 | 4 |  | 2 commit(s) not in main, last 2026-10-20, no newer branch holds them |
| owner decides | `main-batch` | 2026-10-15 | januscollab | 14/2669 | 6 | 22 |  | 6 commit(s) not in main, last 2026-10-15, no newer branch holds them |
| owner decides | `notes-136-focus` | 2026-10-17 | januscollab | 2/2258 | 2 | 7 |  | 2 commit(s) not in main, last 2026-10-17, no newer branch holds them |
| owner decides | `p250-e` | 2026-10-19 | insyncalan | 1/1481 | 1 | 7 |  | 1 commit(s) not in main, last 2026-10-19, no newer branch holds them |
| owner decides | `v20-rules-notes` | 2026-10-15 | januscollab | 6/3031 | 3 | 41 |  | 3 commit(s) not in main, last 2026-10-15, no newer branch holds them |
| owner decides | `v210-int-notes` | 2026-10-15 | januscollab | 3/2816 | 3 | 1 |  | 3 commit(s) not in main, last 2026-10-15, no newer branch holds them |
| owner decides | `v250-testfix` | 2026-10-19 | insyncalan | 4/1393 | 4 | 4 |  | 4 commit(s) not in main, last 2026-10-19, no newer branch holds them |
| owner decides | `v250-teststale` | 2026-10-19 | insyncalan | 4/1393 | 4 | 4 |  | 4 commit(s) not in main, last 2026-10-19, no newer branch holds them |
| owner decides | `v251-step3` | 2026-10-21 | januscollab | 3/1344 | 3 | 3 |  | 3 commit(s) not in main, last 2026-10-21, no newer branch holds them |
| owner decides | `v255-notes-delete-retry` | 2026-10-22 | januscollab | 1/1093 | 1 | 1 |  | 1 commit(s) not in main, last 2026-10-22, no newer branch holds them |
| owner decides | `v26-297` | 2026-10-22 | januscollab | 1/825 | 1 | 2 |  | 1 commit(s) not in main, last 2026-10-22, no newer branch holds them |
| owner decides | `v26-guard-174` | 2026-10-20 | insyncalan | 14/1317 | 13 | 9 |  | 13 commit(s) not in main, last 2026-10-20, no newer branch holds them |
| owner decides | `v26-notes-delete-retry` | 2026-10-22 | januscollab | 1/825 | 1 | 1 |  | 1 commit(s) not in main, last 2026-10-22, no newer branch holds them |
| owner decides | `v26-notes-inputs` | 2026-10-22 | januscollab | 1/825 | 1 | 1 |  | 1 commit(s) not in main, last 2026-10-22, no newer branch holds them |
| owner decides | `v261-release` | 2026-10-23 | januscollab | 51/566 | 35 | 77 | #26 CLOSED | 35 commit(s) not in main, last 2026-10-23, no newer branch holds them |
| owner decides | `v262-250b` | 2026-10-23 | januscollab | 3/556 | 3 | 18 |  | 3 commit(s) not in main, last 2026-10-23, no newer branch holds them |
| owner decides | `v262-f1c` | 2026-10-23 | januscollab | 3/556 | 2 | 8 |  | 2 commit(s) not in main, last 2026-10-23, no newer branch holds them |
| owner decides | `v264-250` | 2026-10-23 | januscollab | 23/614 | 20 | 39 |  | 20 commit(s) not in main, last 2026-10-23, no newer branch holds them |
| keep | `ai-models-132-apply` | 2026-10-18 | insyncalan | 23/1746 | 22 | 49 |  | a live release line or team branch |
| keep | `ai-models-proposal-r3` | 2026-10-18 | insyncalan | 11/2291 | 11 | 47 |  | a live release line or team branch |
| keep | `dev-box-known-failures` | 2026-10-26 | Wanda | 1/106 | 1 | 1 |  | changed 1 day(s) ago |
| keep | `dev-branch-audit` | 2026-10-25 | januscollab | 1/284 | 1 | 5 |  | changed 2 day(s) ago |
| keep | `dev-test-speed` | 2026-10-25 | januscollab | 6/314 | 5 | 9 |  | changed 2 day(s) ago |
| keep | `readme-drop-first-ten` | 2026-10-25 | januscollab | 2/314 | 2 | 1 | #38 OPEN | open PR #38 OPEN |
| keep | `team-cap-370-s1` | 2026-10-27 | insyncalan | 2/0 | 2 | 11 |  | a live release line or team branch |
| keep | `team-cap-goldens-266` | 2026-10-25 | insyncalan | 6/543 | 6 | 108 |  | a live release line or team branch |
| keep | `team-cap-reviewkit-26d` | 2026-10-23 | insyncalan | 5/1128 | 5 | 80 |  | a live release line or team branch |
| keep | `team-cap-tools` | 2026-10-25 | insyncalan | 4/543 | 4 | 50 |  | a live release line or team branch |
| keep | `team-cap-usage-87` | 2026-10-24 | insyncalan | 3/402 | 3 | 2 |  | a live release line or team branch |
| keep | `team-cap-v262-handchecks` | 2026-10-23 | insyncalan | 1/503 | 1 | 1 |  | a live release line or team branch; also contained in team-cap-v262-handchecks-2, team-cap-v262-handchecks-3 |
| keep | `team-cap-v262-handchecks-2` | 2026-10-23 | insyncalan | 2/503 | 2 | 2 |  | a live release line or team branch; also contained in team-cap-v262-handchecks-3, team-cap-v262-handchecks-4 |
| keep | `team-cap-v262-handchecks-3` | 2026-10-23 | insyncalan | 4/503 | 4 | 2 |  | a live release line or team branch; also contained in team-cap-v262-handchecks-4 |
| keep | `team-cap-v262-handchecks-4` | 2026-10-24 | insyncalan | 5/503 | 5 | 2 |  | a live release line or team branch |
| keep | `team-cap-v264-handchecks` | 2026-10-24 | insyncalan | 1/370 | 1 | 2 |  | a live release line or team branch; also contained in team-cap-v264-handchecks-2, team-cap-v264-sheet |
| keep | `team-cap-v264-handchecks-2` | 2026-10-24 | insyncalan | 3/364 | 2 | 2 |  | a live release line or team branch; also contained in team-cap-v264-sheet, team-cap-v264-sheet-2 |
| keep | `team-cap-v264-notes` | 2026-10-24 | insyncalan | 2/364 | 2 | 1 |  | a live release line or team branch; also contained in team-cap-v264-notes-2 |
| keep | `team-cap-v264-notes-2` | 2026-10-24 | insyncalan | 4/362 | 3 | 1 |  | a live release line or team branch |
| keep | `team-cap-v264-sheet` | 2026-10-24 | insyncalan | 4/364 | 3 | 2 |  | a live release line or team branch; also contained in team-cap-v264-sheet-2 |
| keep | `team-cap-v264-sheet-2` | 2026-10-24 | insyncalan | 6/362 | 4 | 2 |  | a live release line or team branch |
| keep | `team-cap-v264b-handchecks` | 2026-10-24 | insyncalan | 1/301 | 1 | 2 |  | a live release line or team branch; also contained in team-cap-v264b-handchecks-2 |
| keep | `team-cap-v264b-handchecks-2` | 2026-10-25 | insyncalan | 3/300 | 2 | 2 |  | a live release line or team branch |
| keep | `team-cap-v265-sheet` | 2026-10-25 | insyncalan | 2/299 | 2 | 4 |  | a live release line or team branch |
| keep | `team-cap-v266-sheet` | 2026-10-25 | insyncalan | 3/267 | 3 | 3 |  | a live release line or team branch |
| keep | `team-cap-wip-email-153-fix5` | 2026-10-25 | insyncalan | 2/2010 | 1 | 8 |  | a live release line or team branch |
| keep | `v2610-366-plan` | 2026-10-26 | januscollab | 1/0 | 1 | 1 |  | a live release line or team branch |
| keep | `v2610-370-plan` | 2026-10-26 | januscollab | 3/0 | 3 | 1 |  | a live release line or team branch |
| keep | `v2610-370s3` | 2026-10-27 | januscollab | 115/0 | 90 | 148 |  | a live release line or team branch |
| keep | `v2610-a` | 2026-10-26 | januscollab | 3/0 | 2 | 10 |  | a live release line or team branch; also contained in v2610-audit, v2610-c |
| keep | `v2610-audit` | 2026-10-26 | januscollab | 13/0 | 11 | 40 |  | a live release line or team branch |
| keep | `v2610-b` | 2026-10-26 | januscollab | 1/0 | 1 | 4 |  | a live release line or team branch; also contained in v2610-a, v2610-audit |
| keep | `v2610-c` | 2026-10-26 | januscollab | 4/0 | 3 | 16 |  | a live release line or team branch; also contained in v2610-audit, v2610-chain |
| keep | `v2610-chain` | 2026-10-27 | januscollab | 151/0 | 121 | 204 |  | a live release line or team branch |
| keep | `v2610-d` | 2026-10-26 | januscollab | 4/0 | 3 | 19 |  | a live release line or team branch; also contained in v2610-audit, v2610-chain |
| keep | `v2610-main` | 2026-10-26 | januscollab | 18/0 | 16 | 39 |  | a live release line or team branch; also contained in v2610-chain |
| keep | `v2610-plan` | 2026-10-26 | januscollab | 1/4 | 1 | 1 |  | a live release line or team branch |
| keep | `v265-344-snapshot-tool` | 2026-10-24 | januscollab | 1/314 | 1 | 5 |  | changed 3 day(s) ago |
| keep | `v266-339` | 2026-10-25 | januscollab | 4/314 | 1 | 9 |  | changed 2 day(s) ago |
| keep | `v267-339c` | 2026-10-25 | januscollab | 1/210 | 1 | 6 |  | changed 2 day(s) ago |
| keep | `v268-358-accepted` | 2026-10-25 | januscollab | 1/197 | 1 | 1 |  | changed 2 day(s) ago |
| keep | `v268-amber` | 2026-10-25 | januscollab | 3/197 | 3 | 75 |  | changed 2 day(s) ago |
| keep | `v268-fuzz` | 2026-10-26 | januscollab | 1/157 | 1 | 2 |  | changed 1 day(s) ago |
| keep | `v268-paths-plan` | 2026-10-25 | januscollab | 2/197 | 2 | 1 |  | changed 2 day(s) ago |
| keep | `v269-371` | 2026-10-26 | januscollab | 2/0 | 2 | 7 |  | a live release line or team branch; also contained in v2610-370s3, v2610-chain |
| keep | `v269-a` | 2026-10-26 | januscollab | 15/156 | 12 | 70 |  | a live release line or team branch; also contained in v2610-370s3, v2610-chain |
| keep | `v269-adv2` | 2026-10-26 | januscollab | 52/7 | 40 | 103 |  | a live release line or team branch; also contained in v2610-370s3, v2610-chain |
| keep | `v269-b` | 2026-10-26 | januscollab | 14/156 | 11 | 69 |  | a live release line or team branch; also contained in v2610-370s3, v2610-chain |
| keep | `v269-bundle` | 2026-10-26 | januscollab | 5/0 | 5 | 8 |  | a live release line or team branch |
| keep | `v269-bundle5` | 2026-10-27 | januscollab | 122/0 | 97 | 153 |  | a live release line or team branch |
| keep | `v269-c` | 2026-10-26 | januscollab | 14/156 | 11 | 69 |  | a live release line or team branch; also contained in v2610-370s3, v2610-chain |
| keep | `v269-chain` | 2026-10-26 | januscollab | 106/0 | 82 | 142 |  | a live release line or team branch; also contained in v2610-370s3, v2610-chain |
| keep | `v269-d` | 2026-10-26 | januscollab | 22/157 | 20 | 85 |  | a live release line or team branch; also contained in v2610-370s3, v2610-chain |
| keep | `v269-e` | 2026-10-26 | januscollab | 15/156 | 12 | 71 |  | a live release line or team branch; also contained in v2610-370s3, v2610-chain |
| keep | `v269-e1-plan` | 2026-10-26 | januscollab | 2/157 | 2 | 1 |  | a live release line or team branch; also contained in v2610-370s3, v2610-chain |
| keep | `v269-emailfix` | 2026-10-26 | januscollab | 76/0 | 59 | 116 |  | a live release line or team branch; also contained in v2610-370s3, v2610-chain |
| keep | `v269-fix2` | 2026-10-26 | januscollab | 59/7 | 46 | 103 |  | a live release line or team branch; also contained in v2610-370s3, v2610-chain |
| keep | `v269-fix3` | 2026-10-26 | januscollab | 66/7 | 53 | 104 |  | a live release line or team branch; also contained in v2610-370s3, v2610-chain |
| keep | `v269-fix4` | 2026-10-26 | januscollab | 77/0 | 60 | 117 |  | a live release line or team branch; also contained in v2610-370s3, v2610-chain |
| keep | `v269-fix5` | 2026-10-26 | januscollab | 100/0 | 77 | 123 |  | a live release line or team branch; also contained in v2610-370s3, v2610-chain |
| keep | `v269-g12` | 2026-10-26 | januscollab | 3/0 | 3 | 10 |  | a live release line or team branch |
| keep | `v269-int` | 2026-10-26 | januscollab | 10/157 | 8 | 68 |  | a live release line or team branch; also contained in v2610-370s3, v2610-chain |
| keep | `v269-main` | 2026-10-26 | januscollab | 113/0 | 88 | 143 |  | a live release line or team branch; also contained in v2610-370s3, v2610-chain |
| keep | `v269-order` | 2026-10-26 | januscollab | 13/156 | 10 | 69 |  | a live release line or team branch; also contained in v2610-370s3, v2610-chain |
| keep | `v269-release` | 2026-10-27 | januscollab | 121/0 | 96 | 150 | #49 OPEN | open PR #49 OPEN |
| keep | `v269-s1` | 2026-10-26 | januscollab | 4/157 | 4 | 6 |  | a live release line or team branch; also contained in v2610-370s3, v2610-chain |
| keep | `v269-s1-spec` | 2026-10-26 | januscollab | 3/157 | 3 | 3 |  | a live release line or team branch; also contained in v2610-370s3, v2610-chain |
| keep | `v269-s2` | 2026-10-26 | januscollab | 4/157 | 4 | 60 |  | a live release line or team branch; also contained in v2610-370s3, v2610-chain |
| keep | `v269-s3` | 2026-10-26 | januscollab | 4/157 | 4 | 6 |  | a live release line or team branch; also contained in v2610-370s3, v2610-chain |
| keep | `v269-s4` | 2026-10-26 | januscollab | 21/157 | 19 | 80 |  | a live release line or team branch; also contained in v2610-370s3, v2610-chain |
| keep | `v269-scrub` | 2026-10-26 | januscollab | 7/4 | 7 | 6 |  | a live release line or team branch; also contained in v2610-370s3, v2610-chain |
| keep | `v27-132-build` | 2026-10-25 | januscollab | 12/200 | 12 | 30 |  | a live release line or team branch |
| keep | `v27-132-plan` | 2026-10-25 | januscollab | 1/284 | 1 | 1 |  | a live release line or team branch; also contained in v27-g8-spike |
| keep | `v27-132-scratch` | 2026-10-25 | januscollab | 9/200 | 9 | 20 |  | a live release line or team branch |
| keep | `v27-250-plan` | 2026-10-25 | januscollab | 1/284 | 1 | 1 |  | a live release line or team branch |
| keep | `v27-316-plan` | 2026-10-25 | januscollab | 1/284 | 1 | 1 |  | a live release line or team branch |
| keep | `v27-g8-spike` | 2026-10-25 | januscollab | 2/284 | 2 | 2 |  | a live release line or team branch |

## Worktrees with uncommitted changes

On this box (creaite-banner) all 11 worktrees of the creaite repo are clean. None of the ~10 named in #363 (creaite-health-162, creaite-preview, creaite-wt-undo175, the four v210-*, wt-v261-291, agent-acea.., wt-help-158b, wt-v262-sim) exists here: they are on another machine. Whoever holds them can run `python3 dev/tools/branch_report.py --worktrees` there, read-only, and post its table here; it lists each worktree with uncommitted changes (counts by status, and the files), and removes nothing.
