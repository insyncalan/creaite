# #363: unmerged branches of insyncalan/creaite, classified (read-only)

Made 27-10-2026 from `origin/main` a62fbb0a: **108 remote branches not merged into main**. The issue's 282 was counted before later clean-ups. Nothing was deleted, pushed or changed. Regenerate with `python3 dev/tools/branch_report.py --markdown` (read-only; `git fetch --prune origin` first). The JSON form is the default output.

**Summary:** delete 6 · delete only if the branch holding its commits is kept 4 · owner decides 19 · keep 79.

## How each branch was judged (`branch_report.classify`, tested in `dev/tests/test_branch_report_363.py`)

- **delete:**
  - its change is already in main. Either every commit's patch is there (`git cherry`, which catches cherry-picks and rebases), or main holds the branch's whole diff (a reverse-apply check against main's tree, which catches squash merges);
  - or every commit is also in a branch kept **as a live line or for an open PR**.
- **delete if kept:** every commit is in another branch that is "owner decides", or is kept only for being recent. Delete this one only if that one is kept.
- **keep:** a live release line or team branch (v269*, v2610*, v27*, team-*, ai-*), an open PR, or changed in the last 3 days.
- **owner decides:** commits that are in neither main nor another branch. Not safe to delete without its author's word.
- **Same commit:** branches whose tips are the same commit name each other ("keep one"); neither is deleted for that alone.

**Limits:**
- Only remote branches (origin/*) are reported; a local branch with no origin counterpart isn't.
- `git cherry` compares single-parent commits, so a merge commit on a branch is never counted "in main" by it. The whole-diff check still sees what it brought in.
- The whole-diff check reads "not in main" when main has since changed the same lines. So it never wrongly suggests a delete, but it may miss some that could go.

| Suggest | Branch | Last commit | Author | Ahead/behind main | Commits not in main | Files | PR | Why |
|---|---|---|---|---|---|---|---|---|
| delete | `dev-ci-free-plan` | 25-10-2026 | januscollab | 1/190 | 0 | 6 |  | its change is already in main (every commit's patch is there) |
| delete | `v261-line3` | 23-10-2026 | januscollab | 6/565 | 0 | 12 |  | its change is already in main (every commit's patch is there) |
| delete | `v262-line` | 24-10-2026 | januscollab | 4/481 | 0 | 4 |  | its change is already in main (every commit's patch is there) |
| delete | `v266-341fix` | 25-10-2026 | januscollab | 1/240 | 0 | 1 |  | its change is already in main (every commit's patch is there) |
| delete | `v266-358prop` | 25-10-2026 | januscollab | 1/233 | 0 | 1 |  | its change is already in main (every commit's patch is there) |
| delete | `v267-chain` | 25-10-2026 | januscollab | 7/167 | 0 | 19 |  | its change is already in main (every commit's patch is there) |
| delete if kept | `cdp-resize-waits` | 15-10-2026 | januscollab | 2/2799 | 2 | 5 |  | every commit is also in main-batch: delete this one only if that one is kept |
| delete if kept | `dev-test-speed-vault` | 25-10-2026 | januscollab | 2/314 | 2 | 5 |  | every commit is also in dev-test-speed: delete this one only if that one is kept |
| delete if kept | `rm-permission-panel-bak` | 15-10-2026 | januscollab | 1/2741 | 1 | 1 |  | every commit is also in main-batch: delete this one only if that one is kept |
| delete if kept | `v26-fetch-transcripts` | 20-10-2026 | januscollab | 9/1241 | 8 | 17 |  | every commit is also in v264-250: delete this one only if that one is kept |
| owner decides | `fix-cdp-resize` | 15-10-2026 | insyncalan | 1/2887 | 1 | 10 |  | 1 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `handchecks-v251c` | 20-10-2026 | insyncalan | 2/1317 | 2 | 4 |  | 2 commit(s) not in main, last 20-10-2026, no newer branch holds them |
| owner decides | `main-batch` | 15-10-2026 | januscollab | 14/2669 | 6 | 22 |  | 6 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `notes-136-focus` | 17-10-2026 | januscollab | 2/2258 | 2 | 7 |  | 2 commit(s) not in main, last 17-10-2026, no newer branch holds them |
| owner decides | `p250-e` | 19-10-2026 | insyncalan | 1/1481 | 1 | 7 |  | 1 commit(s) not in main, last 19-10-2026, no newer branch holds them |
| owner decides | `v20-rules-notes` | 15-10-2026 | januscollab | 6/3031 | 3 | 41 |  | 3 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `v210-int-notes` | 15-10-2026 | januscollab | 3/2816 | 3 | 1 |  | 3 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `v250-testfix` | 19-10-2026 | insyncalan | 4/1393 | 4 | 4 |  | 4 commit(s) not in main, last 19-10-2026, no newer branch holds them; the same commit as v250-teststale (keep one) |
| owner decides | `v250-teststale` | 19-10-2026 | insyncalan | 4/1393 | 4 | 4 |  | 4 commit(s) not in main, last 19-10-2026, no newer branch holds them; the same commit as v250-testfix (keep one) |
| owner decides | `v251-step3` | 21-10-2026 | januscollab | 3/1344 | 3 | 3 |  | 3 commit(s) not in main, last 21-10-2026, no newer branch holds them |
| owner decides | `v255-notes-delete-retry` | 22-10-2026 | januscollab | 1/1093 | 1 | 1 |  | 1 commit(s) not in main, last 22-10-2026, no newer branch holds them |
| owner decides | `v26-297` | 22-10-2026 | januscollab | 1/825 | 1 | 2 |  | 1 commit(s) not in main, last 22-10-2026, no newer branch holds them |
| owner decides | `v26-guard-174` | 20-10-2026 | insyncalan | 14/1317 | 13 | 9 |  | 13 commit(s) not in main, last 20-10-2026, no newer branch holds them |
| owner decides | `v26-notes-delete-retry` | 22-10-2026 | januscollab | 1/825 | 1 | 1 |  | 1 commit(s) not in main, last 22-10-2026, no newer branch holds them |
| owner decides | `v26-notes-inputs` | 22-10-2026 | januscollab | 1/825 | 1 | 1 |  | 1 commit(s) not in main, last 22-10-2026, no newer branch holds them |
| owner decides | `v261-release` | 23-10-2026 | januscollab | 51/566 | 35 | 77 | #26 CLOSED | 35 commit(s) not in main, last 23-10-2026, no newer branch holds them |
| owner decides | `v262-250b` | 23-10-2026 | januscollab | 3/556 | 3 | 18 |  | 3 commit(s) not in main, last 23-10-2026, no newer branch holds them |
| owner decides | `v262-f1c` | 23-10-2026 | januscollab | 3/556 | 2 | 8 |  | 2 commit(s) not in main, last 23-10-2026, no newer branch holds them |
| owner decides | `v264-250` | 23-10-2026 | januscollab | 23/614 | 20 | 39 |  | 20 commit(s) not in main, last 23-10-2026, no newer branch holds them |
| keep | `ai-models-132-apply` | 18-10-2026 | insyncalan | 23/1746 | 22 | 49 |  | a live release line or team branch |
| keep | `ai-models-proposal-r3` | 18-10-2026 | insyncalan | 11/2291 | 11 | 47 |  | a live release line or team branch |
| keep | `dev-box-known-failures` | 26-10-2026 | Wanda | 1/106 | 1 | 1 |  | changed 1 day(s) ago |
| keep | `dev-branch-audit` | 25-10-2026 | januscollab | 1/284 | 1 | 5 |  | changed 2 day(s) ago |
| keep | `dev-test-speed` | 25-10-2026 | januscollab | 6/314 | 5 | 9 |  | changed 2 day(s) ago |
| keep | `readme-drop-first-ten` | 25-10-2026 | januscollab | 2/314 | 2 | 1 | #38 OPEN | open PR #38 OPEN |
| keep | `team-cap-370-s1` | 27-10-2026 | insyncalan | 2/0 | 2 | 11 |  | a live release line or team branch |
| keep | `team-cap-goldens-266` | 25-10-2026 | insyncalan | 6/543 | 6 | 108 |  | a live release line or team branch |
| keep | `team-cap-reviewkit-26d` | 23-10-2026 | insyncalan | 5/1128 | 5 | 80 |  | a live release line or team branch |
| keep | `team-cap-tools` | 25-10-2026 | insyncalan | 4/543 | 4 | 50 |  | a live release line or team branch |
| keep | `team-cap-usage-87` | 24-10-2026 | insyncalan | 3/402 | 3 | 2 |  | a live release line or team branch |
| keep | `team-cap-v262-handchecks` | 23-10-2026 | insyncalan | 1/503 | 1 | 1 |  | a live release line or team branch |
| keep | `team-cap-v262-handchecks-2` | 23-10-2026 | insyncalan | 2/503 | 2 | 2 |  | a live release line or team branch |
| keep | `team-cap-v262-handchecks-3` | 23-10-2026 | insyncalan | 4/503 | 4 | 2 |  | a live release line or team branch |
| keep | `team-cap-v262-handchecks-4` | 24-10-2026 | insyncalan | 5/503 | 5 | 2 |  | a live release line or team branch |
| keep | `team-cap-v264-handchecks` | 24-10-2026 | insyncalan | 1/370 | 1 | 2 |  | a live release line or team branch |
| keep | `team-cap-v264-handchecks-2` | 24-10-2026 | insyncalan | 3/364 | 2 | 2 |  | a live release line or team branch |
| keep | `team-cap-v264-notes` | 24-10-2026 | insyncalan | 2/364 | 2 | 1 |  | a live release line or team branch |
| keep | `team-cap-v264-notes-2` | 24-10-2026 | insyncalan | 4/362 | 3 | 1 |  | a live release line or team branch |
| keep | `team-cap-v264-sheet` | 24-10-2026 | insyncalan | 4/364 | 3 | 2 |  | a live release line or team branch |
| keep | `team-cap-v264-sheet-2` | 24-10-2026 | insyncalan | 6/362 | 4 | 2 |  | a live release line or team branch |
| keep | `team-cap-v264b-handchecks` | 24-10-2026 | insyncalan | 1/301 | 1 | 2 |  | a live release line or team branch |
| keep | `team-cap-v264b-handchecks-2` | 25-10-2026 | insyncalan | 3/300 | 2 | 2 |  | a live release line or team branch |
| keep | `team-cap-v265-sheet` | 25-10-2026 | insyncalan | 2/299 | 2 | 4 |  | a live release line or team branch |
| keep | `team-cap-v266-sheet` | 25-10-2026 | insyncalan | 3/267 | 3 | 3 |  | a live release line or team branch |
| keep | `team-cap-wip-email-153-fix5` | 25-10-2026 | insyncalan | 2/2010 | 1 | 8 |  | a live release line or team branch |
| keep | `v2610-366-plan` | 26-10-2026 | januscollab | 1/0 | 1 | 1 |  | a live release line or team branch |
| keep | `v2610-370-plan` | 26-10-2026 | januscollab | 3/0 | 3 | 1 |  | a live release line or team branch |
| keep | `v2610-370s3` | 27-10-2026 | januscollab | 115/0 | 90 | 148 |  | a live release line or team branch |
| keep | `v2610-386s3` | 27-10-2026 | januscollab | 122/0 | 97 | 160 |  | a live release line or team branch |
| keep | `v2610-a` | 26-10-2026 | januscollab | 3/0 | 2 | 10 |  | a live release line or team branch |
| keep | `v2610-audit` | 26-10-2026 | januscollab | 13/0 | 11 | 40 |  | a live release line or team branch |
| keep | `v2610-b` | 26-10-2026 | januscollab | 1/0 | 1 | 4 |  | a live release line or team branch |
| keep | `v2610-c` | 26-10-2026 | januscollab | 4/0 | 3 | 16 |  | a live release line or team branch |
| keep | `v2610-chain` | 27-10-2026 | januscollab | 151/0 | 121 | 204 |  | a live release line or team branch |
| keep | `v2610-d` | 26-10-2026 | januscollab | 4/0 | 3 | 19 |  | a live release line or team branch |
| keep | `v2610-fetchtext` | 27-10-2026 | januscollab | 19/0 | 17 | 41 |  | a live release line or team branch |
| keep | `v2610-main` | 26-10-2026 | januscollab | 18/0 | 16 | 39 |  | a live release line or team branch |
| keep | `v2610-plan` | 26-10-2026 | januscollab | 1/4 | 1 | 1 |  | a live release line or team branch |
| keep | `v265-344-snapshot-tool` | 24-10-2026 | januscollab | 1/314 | 1 | 5 |  | changed 3 day(s) ago |
| keep | `v266-339` | 25-10-2026 | januscollab | 4/314 | 1 | 9 |  | changed 2 day(s) ago |
| keep | `v267-339c` | 25-10-2026 | januscollab | 1/210 | 1 | 6 |  | changed 2 day(s) ago |
| keep | `v268-358-accepted` | 25-10-2026 | januscollab | 1/197 | 1 | 1 |  | changed 2 day(s) ago |
| keep | `v268-amber` | 25-10-2026 | januscollab | 3/197 | 3 | 75 |  | changed 2 day(s) ago |
| keep | `v268-fuzz` | 26-10-2026 | januscollab | 1/157 | 1 | 2 |  | changed 1 day(s) ago |
| keep | `v268-paths-plan` | 25-10-2026 | januscollab | 2/197 | 2 | 1 |  | changed 2 day(s) ago |
| keep | `v269-371` | 26-10-2026 | januscollab | 2/0 | 2 | 7 |  | a live release line or team branch |
| keep | `v269-a` | 26-10-2026 | januscollab | 15/156 | 12 | 70 |  | a live release line or team branch |
| keep | `v269-adv2` | 26-10-2026 | januscollab | 52/7 | 40 | 103 |  | a live release line or team branch |
| keep | `v269-b` | 26-10-2026 | januscollab | 14/156 | 11 | 69 |  | a live release line or team branch; the same commit as v269-c (keep one) |
| keep | `v269-bundle` | 26-10-2026 | januscollab | 5/0 | 5 | 8 |  | a live release line or team branch |
| keep | `v269-bundle5` | 27-10-2026 | januscollab | 122/0 | 97 | 153 |  | a live release line or team branch |
| keep | `v269-c` | 26-10-2026 | januscollab | 14/156 | 11 | 69 |  | a live release line or team branch; the same commit as v269-b (keep one) |
| keep | `v269-chain` | 26-10-2026 | januscollab | 106/0 | 82 | 142 |  | a live release line or team branch |
| keep | `v269-d` | 26-10-2026 | januscollab | 22/157 | 20 | 85 |  | a live release line or team branch |
| keep | `v269-e` | 26-10-2026 | januscollab | 15/156 | 12 | 71 |  | a live release line or team branch |
| keep | `v269-e1-plan` | 26-10-2026 | januscollab | 2/157 | 2 | 1 |  | a live release line or team branch |
| keep | `v269-emailfix` | 26-10-2026 | januscollab | 76/0 | 59 | 116 |  | a live release line or team branch |
| keep | `v269-fix2` | 26-10-2026 | januscollab | 59/7 | 46 | 103 |  | a live release line or team branch |
| keep | `v269-fix3` | 26-10-2026 | januscollab | 66/7 | 53 | 104 |  | a live release line or team branch |
| keep | `v269-fix4` | 26-10-2026 | januscollab | 77/0 | 60 | 117 |  | a live release line or team branch |
| keep | `v269-fix5` | 26-10-2026 | januscollab | 100/0 | 77 | 123 |  | a live release line or team branch |
| keep | `v269-g12` | 26-10-2026 | januscollab | 3/0 | 3 | 10 |  | a live release line or team branch |
| keep | `v269-int` | 26-10-2026 | januscollab | 10/157 | 8 | 68 |  | a live release line or team branch |
| keep | `v269-main` | 26-10-2026 | januscollab | 113/0 | 88 | 143 |  | a live release line or team branch |
| keep | `v269-order` | 26-10-2026 | januscollab | 13/156 | 10 | 69 |  | a live release line or team branch |
| keep | `v269-release` | 27-10-2026 | januscollab | 121/0 | 96 | 150 | #49 OPEN | open PR #49 OPEN |
| keep | `v269-s1` | 26-10-2026 | januscollab | 4/157 | 4 | 6 |  | a live release line or team branch |
| keep | `v269-s1-spec` | 26-10-2026 | januscollab | 3/157 | 3 | 3 |  | a live release line or team branch |
| keep | `v269-s2` | 26-10-2026 | januscollab | 4/157 | 4 | 60 |  | a live release line or team branch |
| keep | `v269-s3` | 26-10-2026 | januscollab | 4/157 | 4 | 6 |  | a live release line or team branch |
| keep | `v269-s4` | 26-10-2026 | januscollab | 21/157 | 19 | 80 |  | a live release line or team branch |
| keep | `v269-scrub` | 26-10-2026 | januscollab | 7/4 | 7 | 6 |  | a live release line or team branch |
| keep | `v27-132-build` | 25-10-2026 | januscollab | 12/200 | 12 | 30 |  | a live release line or team branch |
| keep | `v27-132-plan` | 25-10-2026 | januscollab | 1/284 | 1 | 1 |  | a live release line or team branch |
| keep | `v27-132-scratch` | 25-10-2026 | januscollab | 9/200 | 9 | 20 |  | a live release line or team branch |
| keep | `v27-250-plan` | 25-10-2026 | januscollab | 1/284 | 1 | 1 |  | a live release line or team branch |
| keep | `v27-316-plan` | 25-10-2026 | januscollab | 1/284 | 1 | 1 |  | a live release line or team branch |
| keep | `v27-g8-spike` | 25-10-2026 | januscollab | 2/284 | 2 | 2 |  | a live release line or team branch |

## Worktrees with uncommitted changes

- **This box (creaite-banner):** all 11 worktrees of the creaite repo are clean.
- **Alan's laptop:** Wanda ran the read-only listing (her #363 comment, 27-10-2026): 177 worktrees, 20 with uncommitted files. Stark's notes on them for Alan:
  - (a) safe to remove: the four v210-* worktrees and creaite-preview;
  - (b) owner decides: p233-217, help-158b, notes-undo-175 and health-162.
  Nothing has been removed: a dirty worktree needs a forced removal, which is Alan's call.
- **To list them anywhere:** run `python3 dev/tools/branch_report.py --worktrees`. It shows every worktree with uncommitted changes, plus any that is locked or prunable (its folder gone), and removes nothing.
