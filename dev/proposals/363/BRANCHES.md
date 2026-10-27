# #363: unmerged branches of insyncalan/creaite, classified (read-only)

Made 27-10-2026 from `origin/main` db5adb2a (2.6.9), in Alan's laptop clone, with its worktrees (Stark): **310 branches not merged into main: 221 local only, 28 remote only, 61 on both** (the Where column). Nothing was deleted, pushed or changed. Regenerate with `python3 dev/tools/branch_report.py --markdown` and `python3 dev/tools/branch_report.py --worktrees` (read-only; `git fetch --prune origin` first). The JSON form is the default output. On this clone (about 330 branch refs, 183 worktrees) the run takes about three and a half hours: the "held by" check compares every branch with every other one. Paths are shown from the home folder (`~`).

**Summary:** delete 52 · delete only if the branch holding its commits is kept 26 · owner decides 127 · keep 105 (55 of the keeps are checked out in one of this laptop's worktrees; 44 are live release lines or team branches; 5 changed in the last 3 days; 1 has a local commit not on origin).

**Before deleting anything, check every machine's worktrees (Stark's re-check, 27-10-2026).** A worktree belongs to one clone, so this report sees only this laptop's 183 worktrees; branches checked out on the build boxes are not seen here. To include another machine, save its list there (`git worktree list --porcelain > worktrees.txt`) and run `python3 dev/tools/branch_report.py --markdown --worktree-list worktrees.txt` here: a branch checked out in any listed worktree is then keep, "checked out in <file>: <path>". This run was made after a plain `git fetch origin` (no `--prune`), so a branch already deleted on GitHub may still show as remote.

## How each branch was judged (`branch_report.classify`, tested in `dev/tests/test_branch_report_363.py`)

- **delete:**
  - its change is already in main. Either every commit's patch is there (`git cherry`, which catches cherry-picks and rebases), or main holds the branch's whole diff (a reverse-apply check against main's tree, which catches squash merges);
  - or every commit is also in a branch kept **as a live line or for an open PR**.
- **delete if kept:** every commit is in another branch that is "owner decides", or is kept only for being recent. Delete this one only if that one is kept.
- **keep:** checked out in a worktree (this clone's or a saved list's, never delete, whatever else is true); a local branch with commits not on origin; a live release line or team branch (v269*, v2610*, v27*, team-*, ai-*), an open PR, or changed in the last 3 days.
- **owner decides:** commits that are in neither main nor another branch. Not safe to delete without its author's word.
- **Same commit:** branches whose tips are the same commit name each other ("keep one"); neither is deleted for that alone.

**Limits:**
- Remote (origin/*) and local branches are both reported, and the Where column says which. A branch on both is judged by its origin tip; local commits not on origin make it keep. Local branches and worktrees are this laptop's clone only (see above).
- `git cherry` ignores merge commits, so a branch with a merge commit of its own counts as "in main" **only by the whole-diff check**, never by a zero cherry count (Stark's re-check; tested with a merge-only branch carrying content of its own).
- The whole-diff check reads "not in main" when main has since changed the same lines. So it never wrongly suggests a delete, but it may miss some that could go.

| Suggest | Branch | Where | Last commit | Author | Ahead/behind main | Commits not in main | Files | PR | Why |
|---|---|---|---|---|---|---|---|---|---|
| delete | `ask-148-reopen` | local only | 16-10-2026 | januscollab | 1/2699 | 0 | 3 |  | its change is already in main (every commit's patch is there) |
| delete | `ask-hook-fix` | local only | 16-10-2026 | januscollab | 5/2752 | 0 | 3 |  | its change is already in main (every commit's patch is there) |
| delete | `editor-133-gate` | local only | 17-10-2026 | januscollab | 3/2157 | 0 | 13 |  | its change is already in main (every commit's patch is there) |
| delete | `editor-134-v220` | local only | 17-10-2026 | januscollab | 3/2408 | 0 | 10 |  | its change is already in main (every commit's patch is there) |
| delete | `export-audit-doc` | local only | 18-10-2026 | januscollab | 1/1774 | 1 | 4 |  | its change is already in main (main holds the whole diff) |
| delete | `fix-125-close-day-clock` | local only | 16-10-2026 | januscollab | 1/2763 | 0 | 1 |  | its change is already in main (main holds the whole diff) |
| delete | `fix-delnote-focus` | local only | 16-10-2026 | januscollab | 1/2716 | 0 | 5 |  | its change is already in main (every commit's patch is there) |
| delete | `fix-main-ci` | local only | 16-10-2026 | januscollab | 1/2719 | 0 | 2 |  | its change is already in main (every commit's patch is there) |
| delete | `guard-backslash-fix` | local only | 16-10-2026 | januscollab | 1/2749 | 0 | 6 |  | its change is already in main (every commit's patch is there) |
| delete | `health-203-page` | local only | 17-10-2026 | januscollab | 2/2161 | 0 | 14 |  | its change is already in main (every commit's patch is there) |
| delete | `health-203-plain` | local only | 17-10-2026 | januscollab | 2/2161 | 0 | 4 |  | its change is already in main (every commit's patch is there) |
| delete | `help-158a` | local only | 17-10-2026 | januscollab | 14/2375 | 13 | 7 |  | every commit is also in help-158b, which is kept |
| delete | `help-210-patch` | local only | 17-10-2026 | januscollab | 1/2390 | 0 | 2 |  | its change is already in main (every commit's patch is there) |
| delete | `help-acceptance-check` | local only | 17-10-2026 | januscollab | 1/2262 | 0 | 1 |  | its change is already in main (main holds the whole diff) |
| delete | `perm-mcp-fix` | local only | 16-10-2026 | januscollab | 4/2763 | 0 | 6 |  | its change is already in main (every commit's patch is there) |
| delete | `perm-mcp-fix-v2` | local only | 16-10-2026 | januscollab | 7/2763 | 0 | 6 |  | its change is already in main (every commit's patch is there) |
| delete | `pm-261-docs` | local only | 23-10-2026 | januscollab | 1/674 | 0 | 1 |  | its change is already in main (main holds the whole diff) |
| delete | `pm-ds-snapshots-261` | local only | 24-10-2026 | januscollab | 1/670 | 0 | 28 |  | its change is already in main (main holds the whole diff) |
| delete | `rail-156-fix` | local only | 16-10-2026 | januscollab | 1/2692 | 0 | 2 |  | its change is already in main (main holds the whole diff) |
| delete | `replay2-f2-sonnet` | local only | 15-10-2026 | januscollab | 1/3078 | 0 | 1 |  | its change is already in main (every commit's patch is there) |
| delete | `review-177` | local only | 17-10-2026 | januscollab | 1/2408 | 0 | 9 |  | its change is already in main (every commit's patch is there) |
| delete | `review-177-fix` | local only | 17-10-2026 | januscollab | 3/2408 | 0 | 12 |  | its change is already in main (every commit's patch is there) |
| delete | `review-177-fix2` | local only | 17-10-2026 | januscollab | 4/2408 | 0 | 12 |  | its change is already in main (every commit's patch is there) |
| delete | `run-tools-explicit` | local only | 16-10-2026 | januscollab | 8/2763 | 0 | 11 |  | its change is already in main (every commit's patch is there) |
| delete | `run-tools-explicit-v3` | local only | 16-10-2026 | januscollab | 9/2763 | 0 | 11 |  | its change is already in main (every commit's patch is there) |
| delete | `run-usage-plain` | local only | 17-10-2026 | januscollab | 1/2264 | 0 | 4 |  | its change is already in main (every commit's patch is there) |
| delete | `sweep-146-calendar` | local only | 16-10-2026 | januscollab | 1/2699 | 0 | 5 |  | its change is already in main (every commit's patch is there) |
| delete | `sweep-146b` | local only | 16-10-2026 | januscollab | 3/2699 | 0 | 9 |  | its change is already in main (every commit's patch is there) |
| delete | `v194-side-panel` | local only | 15-10-2026 | januscollab | 5/3146 | 0 | 5 |  | its change is already in main (every commit's patch is there) |
| delete | `v210-p6-sheet` | local only | 15-10-2026 | januscollab | 1/2993 | 0 | 1 |  | its change is already in main (main holds the whole diff) |
| delete | `v235-release` | local only | 18-10-2026 | januscollab | 2/1773 | 0 | 3 |  | its change is already in main (main holds the whole diff) |
| delete | `v250-matchtext` | local only | 19-10-2026 | januscollab | 1/1522 | 0 | 4 |  | its change is already in main (every commit's patch is there) |
| delete | `v253-followups` | local only | 20-10-2026 | januscollab | 2/1364 | 0 | 10 |  | its change is already in main (every commit's patch is there) |
| delete | `v253-quiet-hours` | local only | 20-10-2026 | januscollab | 2/1359 | 0 | 13 |  | its change is already in main (every commit's patch is there) |
| delete | `v253-usage-reviews` | local only | 20-10-2026 | januscollab | 4/1365 | 0 | 12 |  | its change is already in main (every commit's patch is there) |
| delete | `v26-delete-note-card` | local only | 20-10-2026 | januscollab | 9/1395 | 0 | 12 |  | its change is already in main (every commit's patch is there) |
| delete | `v26-invite-h4` | local only | 21-10-2026 | januscollab | 1/1011 | 0 | 2 |  | its change is already in main (every commit's patch is there) |
| delete | `v261-inode-gap` | local only | 22-10-2026 | januscollab | 1/858 | 1 | 4 |  | its change is already in main (main holds the whole diff) |
| delete | `v261-line3` | local and remote | 23-10-2026 | januscollab | 6/696 | 0 | 12 |  | its change is already in main (every commit's patch is there) |
| delete | `v261-vip-rules` | local only | 23-10-2026 | januscollab | 1/754 | 1 | 3 |  | its change is already in main (main holds the whole diff) |
| delete | `v261-wih` | local only | 22-10-2026 | januscollab | 1/812 | 0 | 2 |  | its change is already in main (main holds the whole diff) |
| delete | `v262-322` | local only | 23-10-2026 | januscollab | 1/674 | 0 | 5 |  | its change is already in main (every commit's patch is there) |
| delete | `v262-emit` | local only | 23-10-2026 | januscollab | 3/674 | 0 | 3 |  | its change is already in main (every commit's patch is there) |
| delete | `v262-f1b` | local only | 23-10-2026 | januscollab | 1/687 | 0 | 7 |  | its change is already in main (every commit's patch is there) |
| delete | `v262-line` | remote only | 24-10-2026 | januscollab | 4/612 | 0 | 4 |  | its change is already in main (main holds the whole diff) |
| delete | `v262-small2` | local only | 23-10-2026 | januscollab | 6/674 | 0 | 17 |  | its change is already in main (every commit's patch is there) |
| delete | `v262-wpfix` | local only | 23-10-2026 | januscollab | 1/674 | 0 | 1 |  | its change is already in main (main holds the whole diff) |
| delete | `v263-intake-lows` | local only | 24-10-2026 | januscollab | 1/607 | 0 | 1 |  | its change is already in main (main holds the whole diff) |
| delete | `v263-line` | local only | 24-10-2026 | januscollab | 1/549 | 0 | 1 |  | its change is already in main (main holds the whole diff) |
| delete | `v264-292` | local only | 24-10-2026 | januscollab | 1/597 | 0 | 3 |  | its change is already in main (every commit's patch is there) |
| delete | `v264-lows2` | local only | 24-10-2026 | januscollab | 2/549 | 0 | 3 |  | its change is already in main (main holds the whole diff) |
| delete | `vip-deny-only` | local only | 15-10-2026 | januscollab | 1/2765 | 0 | 3 |  | its change is already in main (every commit's patch is there) |
| delete if kept | `bl342-part3-plan` | local only | 15-10-2026 | januscollab | 1/2913 | 1 | 1 |  | every commit is also in bl342-part3b-plan, bl342-part3b-plan2: delete this one only if that one is kept |
| delete if kept | `bl342-part3b-plan` | local only | 15-10-2026 | januscollab | 2/2913 | 2 | 1 |  | every commit is also in bl342-part3b-plan2: delete this one only if that one is kept |
| delete if kept | `cdp-resize-waits` | local and remote | 15-10-2026 | januscollab | 2/2930 | 2 | 5 |  | every commit is also in main-batch: delete this one only if that one is kept |
| delete if kept | `edit-ai-proposal` | local only | 17-10-2026 | januscollab | 1/2681 | 1 | 3 |  | every commit is also in notes-119-proposal: delete this one only if that one is kept |
| delete if kept | `editor-120-links` | local only | 16-10-2026 | januscollab | 2/2709 | 2 | 18 |  | every commit is also in editor-120-121-int: delete this one only if that one is kept |
| delete if kept | `email-153-sent` | local only | 16-10-2026 | januscollab | 6/2462 | 3 | 33 |  | every commit is also in email-153-sent-r: delete this one only if that one is kept |
| delete if kept | `fix-lost-click` | local only | 15-10-2026 | januscollab | 2/3073 | 1 | 4 |  | every commit is also in main-batch: delete this one only if that one is kept |
| delete if kept | `intake-179` | local only | 17-10-2026 | januscollab | 1/2161 | 1 | 31 |  | every commit is also in intake-179-fix: delete this one only if that one is kept |
| delete if kept | `notes-175-proposal-r2` | local only | 17-10-2026 | januscollab | 1/2359 | 1 | 4 |  | every commit is also in notes-175-design-r3: delete this one only if that one is kept |
| delete if kept | `rail-139-hover-flyouts` | local only | 16-10-2026 | januscollab | 1/2693 | 1 | 12 |  | every commit is also in rail-139b: delete this one only if that one is kept |
| delete if kept | `rm-permission-panel-bak` | local and remote | 15-10-2026 | januscollab | 1/2872 | 1 | 1 |  | every commit is also in main-batch: delete this one only if that one is kept |
| delete if kept | `tests-desktop-900` | local only | 15-10-2026 | januscollab | 2/3065 | 2 | 9 |  | every commit is also in main-batch: delete this one only if that one is kept |
| delete if kept | `v194-chat-copy` | local only | 15-10-2026 | januscollab | 1/3146 | 1 | 1 |  | every commit is also in release-194-stark-bdc3f1c: delete this one only if that one is kept |
| delete if kept | `v26-295` | local only | 22-10-2026 | januscollab | 1/956 | 1 | 22 |  | every commit is also in v26-295-2: delete this one only if that one is kept |
| delete if kept | `v26-draft-delivery` | local only | 19-10-2026 | januscollab | 9/1498 | 9 | 27 |  | every commit is also in v262-183, v264-250: delete this one only if that one is kept |
| delete if kept | `v26-fetch-transcripts` | local and remote | 20-10-2026 | januscollab | 9/1372 | 8 | 17 |  | every commit is also in v264-250: delete this one only if that one is kept |
| delete if kept | `v261-307fix2` | local only | 23-10-2026 | januscollab | 30/697 | 20 | 43 |  | every commit is also in v261-capa, v261-gate3, v261-gatefixes: delete this one only if that one is kept |
| delete if kept | `v261-307h2` | local only | 23-10-2026 | januscollab | 18/697 | 12 | 37 |  | every commit is also in v261-307fix2, v261-capa, v261-gate3: delete this one only if that one is kept |
| delete if kept | `v261-chaintests` | local only | 23-10-2026 | januscollab | 10/697 | 7 | 43 |  | every commit is also in v261-capa, v261-gate3, v261-gatefixes: delete this one only if that one is kept |
| delete if kept | `v261-gatefixes` | local only | 23-10-2026 | januscollab | 51/697 | 35 | 77 |  | every commit is also in v261-capa, v261-gate3: delete this one only if that one is kept; the same commit as v261-release (keep one) |
| delete if kept | `v261-gatelabel` | local only | 23-10-2026 | januscollab | 10/697 | 7 | 23 |  | every commit is also in v261-capa, v261-gate3, v261-gatefixes: delete this one only if that one is kept |
| delete if kept | `v261-gaterun` | local only | 23-10-2026 | januscollab | 7/697 | 4 | 21 |  | every commit is also in v261-307fix2, v261-307h2, v261-capa: delete this one only if that one is kept |
| delete if kept | `v261-gateui` | local only | 23-10-2026 | januscollab | 15/697 | 12 | 31 |  | every commit is also in v261-capa, v261-gate3, v261-gatefixes: delete this one only if that one is kept |
| delete if kept | `v261-release` | local and remote | 23-10-2026 | januscollab | 51/697 | 35 | 77 | #26 CLOSED | every commit is also in v261-capa, v261-gate3: delete this one only if that one is kept; the same commit as v261-gatefixes (keep one) |
| delete if kept | `v262-183` | local only | 23-10-2026 | januscollab | 12/745 | 11 | 30 |  | every commit is also in v264-250: delete this one only if that one is kept |
| delete if kept | `v262-183b` | local only | 23-10-2026 | januscollab | 16/687 | 16 | 30 |  | every commit is also in v262-183h, v262-183r: delete this one only if that one is kept |
| owner decides | `activity-by-12` | local only | 17-10-2026 | januscollab | 1/2681 | 1 | 3 |  | 1 commit(s) not in main, last 17-10-2026, no newer branch holds them |
| owner decides | `bl342-part3b` | local only | 15-10-2026 | januscollab | 14/2780 | 4 | 21 |  | 4 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `bl342-part3b-plan2` | local only | 15-10-2026 | januscollab | 3/2913 | 3 | 1 |  | 3 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `bl342-part3b-v2` | local only | 15-10-2026 | januscollab | 19/2750 | 7 | 26 |  | 7 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `bl342-probe` | local only | 15-10-2026 | januscollab | 4/2885 | 4 | 2 |  | 4 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `ci-shards-balance` | local only | 15-10-2026 | januscollab | 2/3061 | 2 | 2 |  | 2 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `dates-178` | local only | 17-10-2026 | januscollab | 1/2161 | 1 | 24 |  | 1 commit(s) not in main, last 17-10-2026, no newer branch holds them |
| owner decides | `day-band-138` | local only | 17-10-2026 | januscollab | 1/2228 | 1 | 1 |  | 1 commit(s) not in main, last 17-10-2026, no newer branch holds them |
| owner decides | `editor-120-121-int` | local only | 16-10-2026 | januscollab | 15/2709 | 13 | 49 |  | 13 commit(s) not in main, last 16-10-2026, no newer branch holds them |
| owner decides | `editor-121-links-plain` | local only | 16-10-2026 | januscollab | 5/2709 | 4 | 40 |  | 4 commit(s) not in main, last 16-10-2026, no newer branch holds them |
| owner decides | `editor-122b-slash-headings` | local only | 16-10-2026 | januscollab | 5/2739 | 3 | 12 |  | 3 commit(s) not in main, last 16-10-2026, no newer branch holds them |
| owner decides | `editor-122c-item-links` | local only | 16-10-2026 | januscollab | 5/2724 | 4 | 17 |  | 4 commit(s) not in main, last 16-10-2026, no newer branch holds them |
| owner decides | `editor-122c2` | local only | 16-10-2026 | januscollab | 6/2717 | 4 | 18 |  | 4 commit(s) not in main, last 16-10-2026, no newer branch holds them |
| owner decides | `editor-122c3` | local only | 16-10-2026 | januscollab | 7/2710 | 4 | 18 |  | 4 commit(s) not in main, last 16-10-2026, no newer branch holds them |
| owner decides | `editor-133-plain` | local only | 16-10-2026 | januscollab | 3/2709 | 2 | 17 |  | 2 commit(s) not in main, last 16-10-2026, no newer branch holds them |
| owner decides | `editor-134-chrome` | local only | 16-10-2026 | januscollab | 2/2709 | 2 | 8 |  | 2 commit(s) not in main, last 16-10-2026, no newer branch holds them |
| owner decides | `email-153-fix3` | local only | 17-10-2026 | januscollab | 1/2142 | 1 | 5 |  | 1 commit(s) not in main, last 17-10-2026, no newer branch holds them |
| owner decides | `email-153-sent-r` | local only | 16-10-2026 | januscollab | 7/2462 | 4 | 36 |  | 4 commit(s) not in main, last 16-10-2026, no newer branch holds them |
| owner decides | `email-153-sent-r2` | local only | 17-10-2026 | januscollab | 7/2409 | 4 | 29 |  | 4 commit(s) not in main, last 17-10-2026, no newer branch holds them |
| owner decides | `esc-161` | local only | 16-10-2026 | januscollab | 1/2468 | 1 | 6 |  | 1 commit(s) not in main, last 16-10-2026, no newer branch holds them |
| owner decides | `fix-cdp-resize` | remote only | 15-10-2026 | insyncalan | 1/3021 | 1 | 10 |  | 1 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `handcheck-palettes` | local only | 17-10-2026 | januscollab | 1/2390 | 1 | 1 |  | 1 commit(s) not in main, last 17-10-2026, no newer branch holds them |
| owner decides | `handcheck-v210` | local only | 17-10-2026 | januscollab | 1/2390 | 1 | 1 |  | 1 commit(s) not in main, last 17-10-2026, no newer branch holds them |
| owner decides | `handcheck-v210-rc5` | local only | 17-10-2026 | januscollab | 1/2380 | 1 | 1 |  | 1 commit(s) not in main, last 17-10-2026, no newer branch holds them |
| owner decides | `handchecks-v210` | local only | 16-10-2026 | januscollab | 2/2749 | 2 | 3 |  | 2 commit(s) not in main, last 16-10-2026, no newer branch holds them |
| owner decides | `handchecks-v251c` | remote only | 20-10-2026 | insyncalan | 2/1451 | 2 | 4 |  | 2 commit(s) not in main, last 20-10-2026, no newer branch holds them |
| owner decides | `harness-timeout` | local only | 17-10-2026 | januscollab | 1/2152 | 1 | 3 |  | 1 commit(s) not in main, last 17-10-2026, no newer branch holds them |
| owner decides | `health-203-both` | local only | 17-10-2026 | januscollab | 5/2161 | 0 | 19 |  | 0 commit(s) not in main, last 17-10-2026, no newer branch holds them |
| owner decides | `held-bash-proof` | local only | 15-10-2026 | januscollab | 1/2786 | 1 | 1 |  | 1 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `intake-179-fix` | local only | 17-10-2026 | januscollab | 4/2161 | 3 | 40 |  | 3 commit(s) not in main, last 17-10-2026, no newer branch holds them |
| owner decides | `main-batch` | local and remote | 15-10-2026 | januscollab | 14/2800 | 6 | 22 |  | 6 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `notes-115-focus-paused` | local only | 15-10-2026 | januscollab | 1/2781 | 1 | 7 |  | 1 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `notes-117-ai-select` | local only | 15-10-2026 | januscollab | 2/2781 | 2 | 11 |  | 2 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `notes-119-proposal` | local only | 17-10-2026 | januscollab | 2/2681 | 2 | 5 |  | 2 commit(s) not in main, last 17-10-2026, no newer branch holds them |
| owner decides | `notes-136-focus` | local and remote | 17-10-2026 | januscollab | 2/2389 | 2 | 7 |  | 2 commit(s) not in main, last 17-10-2026, no newer branch holds them |
| owner decides | `notes-136-r` | local only | 17-10-2026 | januscollab | 2/2387 | 1 | 6 |  | 1 commit(s) not in main, last 17-10-2026, no newer branch holds them; the same commit as notes-undo-175 (keep one) |
| owner decides | `notes-175-design-r3` | local only | 17-10-2026 | januscollab | 2/2359 | 2 | 5 |  | 2 commit(s) not in main, last 17-10-2026, no newer branch holds them |
| owner decides | `notes-175-guarded-proposal` | local only | 17-10-2026 | januscollab | 1/2158 | 1 | 5 |  | 1 commit(s) not in main, last 17-10-2026, no newer branch holds them |
| owner decides | `p234-export` | local only | 18-10-2026 | januscollab | 2/1790 | 2 | 3 |  | 2 commit(s) not in main, last 18-10-2026, no newer branch holds them |
| owner decides | `p250-e` | remote only | 19-10-2026 | insyncalan | 1/1612 | 1 | 7 |  | 1 commit(s) not in main, last 19-10-2026, no newer branch holds them |
| owner decides | `pm-254-docs` | local only | 22-10-2026 | januscollab | 4/1179 | 4 | 2 |  | 4 commit(s) not in main, last 22-10-2026, no newer branch holds them |
| owner decides | `pm-260-docs` | local only | 22-10-2026 | januscollab | 2/1171 | 2 | 2 |  | 2 commit(s) not in main, last 22-10-2026, no newer branch holds them |
| owner decides | `pm-intake-briefs` | local only | 21-10-2026 | januscollab | 188/2242 | 188 | 407 | #2 MERGED | 188 commit(s) not in main, last 21-10-2026, no newer branch holds them |
| owner decides | `r200-shared-behaviour` | local only | 15-10-2026 | januscollab | 2/3032 | 1 | 7 |  | 1 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `rail-139b` | local only | 16-10-2026 | januscollab | 2/2693 | 2 | 13 |  | 2 commit(s) not in main, last 16-10-2026, no newer branch holds them |
| owner decides | `rc2-globals` | local only | 17-10-2026 | januscollab | 2/2387 | 2 | 2 |  | 2 commit(s) not in main, last 17-10-2026, no newer branch holds them |
| owner decides | `release-194-stark-bdc3f1c` | local only | 15-10-2026 | januscollab | 9/3142 | 1 | 5 |  | 1 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `release-201` | local only | 15-10-2026 | januscollab | 3/2770 | 2 | 7 |  | 2 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `release-210-trial` | local only | 15-10-2026 | januscollab | 1/2724 | 0 | 129 |  | 0 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `replay-49-haiku` | local only | 15-10-2026 | januscollab | 1/3142 | 1 | 1 |  | 1 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `replay-49-sonnet` | local only | 15-10-2026 | januscollab | 1/3142 | 1 | 1 |  | 1 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `replay-54-sonnet` | local only | 15-10-2026 | januscollab | 1/3172 | 1 | 2 |  | 1 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `replay-57-sonnet` | local only | 15-10-2026 | januscollab | 1/3172 | 1 | 1 |  | 1 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `replay-78-sonnet` | local only | 15-10-2026 | januscollab | 1/3173 | 1 | 1 |  | 1 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `replay2-d1-haiku` | local only | 15-10-2026 | januscollab | 1/3172 | 1 | 2 |  | 1 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `replay2-d2-haiku` | local only | 15-10-2026 | januscollab | 1/2997 | 1 | 4 |  | 1 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `replay2-f1-sonnet` | local only | 15-10-2026 | januscollab | 1/3149 | 1 | 1 |  | 1 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `replay2-m1-sonnet` | local only | 15-10-2026 | januscollab | 1/3146 | 1 | 3 |  | 1 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `replay2-m2-sonnet` | local only | 15-10-2026 | januscollab | 1/3073 | 1 | 4 |  | 1 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `replay2-s1-haiku` | local only | 15-10-2026 | januscollab | 1/3073 | 1 | 3 |  | 1 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `replay2-s2-haiku` | local only | 15-10-2026 | januscollab | 1/3073 | 1 | 7 |  | 1 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `run-usage-guarded-proposal` | local only | 17-10-2026 | januscollab | 2/2264 | 1 | 9 |  | 1 commit(s) not in main, last 17-10-2026, no newer branch holds them |
| owner decides | `run-usage-guarded-proposal-r` | local only | 17-10-2026 | januscollab | 2/2260 | 2 | 5 |  | 2 commit(s) not in main, last 17-10-2026, no newer branch holds them |
| owner decides | `run-usage-guarded-proposal-r2` | local only | 17-10-2026 | januscollab | 3/2259 | 3 | 5 |  | 3 commit(s) not in main, last 17-10-2026, no newer branch holds them |
| owner decides | `search-strict-mcp` | local only | 15-10-2026 | januscollab | 1/2770 | 1 | 3 |  | 1 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `sprint-comms` | local only | 15-10-2026 | januscollab | 4/3172 | 4 | 1 |  | 4 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `tests-178` | local only | 17-10-2026 | januscollab | 3/2408 | 3 | 20 |  | 3 commit(s) not in main, last 17-10-2026, no newer branch holds them |
| owner decides | `v20-rules-notes` | remote only | 15-10-2026 | januscollab | 6/3165 | 3 | 41 |  | 3 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `v20-sheet44` | local only | 15-10-2026 | januscollab | 4/2814 | 4 | 1 |  | 4 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `v200-polish-a` | local only | 15-10-2026 | januscollab | 2/2801 | 2 | 4 |  | 2 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `v200-polish-b` | local only | 15-10-2026 | januscollab | 3/2801 | 3 | 7 |  | 3 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `v210-int-notes` | local and remote | 15-10-2026 | januscollab | 3/2947 | 3 | 1 |  | 3 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `v250-232a` | local only | 19-10-2026 | januscollab | 2/1522 | 2 | 10 |  | 2 commit(s) not in main, last 19-10-2026, no newer branch holds them |
| owner decides | `v250-232a-harden` | local only | 19-10-2026 | januscollab | 4/1626 | 4 | 6 |  | 4 commit(s) not in main, last 19-10-2026, no newer branch holds them |
| owner decides | `v250-232b` | local only | 19-10-2026 | januscollab | 2/1522 | 2 | 9 |  | 2 commit(s) not in main, last 19-10-2026, no newer branch holds them |
| owner decides | `v250-232b-harden` | local only | 19-10-2026 | januscollab | 1/1632 | 1 | 1 |  | 1 commit(s) not in main, last 19-10-2026, no newer branch holds them |
| owner decides | `v250-232c` | local only | 19-10-2026 | januscollab | 1/1511 | 1 | 2 |  | 1 commit(s) not in main, last 19-10-2026, no newer branch holds them |
| owner decides | `v250-int` | local only | 19-10-2026 | januscollab | 2/1559 | 0 | 55 |  | 0 commit(s) not in main, last 19-10-2026, no newer branch holds them |
| owner decides | `v250-testfix` | remote only | 19-10-2026 | insyncalan | 4/1527 | 4 | 4 |  | 4 commit(s) not in main, last 19-10-2026, no newer branch holds them; the same commit as v250-teststale (keep one) |
| owner decides | `v250-teststale` | remote only | 19-10-2026 | insyncalan | 4/1527 | 4 | 4 |  | 4 commit(s) not in main, last 19-10-2026, no newer branch holds them; the same commit as v250-testfix (keep one) |
| owner decides | `v251-snapshot-design` | local only | 19-10-2026 | januscollab | 1/1499 | 1 | 1 |  | 1 commit(s) not in main, last 19-10-2026, no newer branch holds them |
| owner decides | `v251-step3` | local and remote | 21-10-2026 | januscollab | 3/1475 | 3 | 3 |  | 3 commit(s) not in main, last 21-10-2026, no newer branch holds them |
| owner decides | `v252-check09` | local only | 19-10-2026 | januscollab | 1/1459 | 1 | 1 |  | 1 commit(s) not in main, last 19-10-2026, no newer branch holds them |
| owner decides | `v252-handchecks` | local only | 20-10-2026 | januscollab | 3/1448 | 3 | 2 |  | 3 commit(s) not in main, last 20-10-2026, no newer branch holds them |
| owner decides | `v252-usage` | local only | 19-10-2026 | januscollab | 3/1498 | 3 | 15 |  | 3 commit(s) not in main, last 19-10-2026, no newer branch holds them |
| owner decides | `v253-defects-261-260` | local only | 20-10-2026 | januscollab | 1/1309 | 1 | 2 |  | 1 commit(s) not in main, last 20-10-2026, no newer branch holds them |
| owner decides | `v253-g` | local only | 21-10-2026 | januscollab | 3/1327 | 1 | 46 |  | 1 commit(s) not in main, last 21-10-2026, no newer branch holds them |
| owner decides | `v253-intake-process` | local only | 20-10-2026 | januscollab | 5/1360 | 3 | 11 |  | 3 commit(s) not in main, last 20-10-2026, no newer branch holds them |
| owner decides | `v253-milestone-attention` | local only | 20-10-2026 | januscollab | 2/1372 | 2 | 8 |  | 2 commit(s) not in main, last 20-10-2026, no newer branch holds them |
| owner decides | `v253-suggest-nothing` | local only | 20-10-2026 | januscollab | 4/1328 | 0 | 9 |  | 0 commit(s) not in main, last 20-10-2026, no newer branch holds them |
| owner decides | `v254-g` | local only | 22-10-2026 | januscollab | 2/1183 | 0 | 3 |  | 0 commit(s) not in main, last 22-10-2026, no newer branch holds them |
| owner decides | `v254-handchecks` | local only | 22-10-2026 | januscollab | 9/1207 | 0 | 37 |  | 0 commit(s) not in main, last 22-10-2026, no newer branch holds them |
| owner decides | `v255-notes-delete-retry` | local and remote | 22-10-2026 | januscollab | 1/1224 | 1 | 1 |  | 1 commit(s) not in main, last 22-10-2026, no newer branch holds them |
| owner decides | `v26-291-walk` | local only | 22-10-2026 | januscollab | 1/964 | 1 | 1 |  | 1 commit(s) not in main, last 22-10-2026, no newer branch holds them |
| owner decides | `v26-295-2` | local only | 22-10-2026 | januscollab | 2/956 | 1 | 23 |  | 1 commit(s) not in main, last 22-10-2026, no newer branch holds them |
| owner decides | `v26-297` | local and remote | 22-10-2026 | januscollab | 1/956 | 1 | 2 |  | 1 commit(s) not in main, last 22-10-2026, no newer branch holds them |
| owner decides | `v26-archive-name-proposal` | local only | 20-10-2026 | januscollab | 10/1374 | 10 | 37 |  | 10 commit(s) not in main, last 20-10-2026, no newer branch holds them |
| owner decides | `v26-g5` | local only | 21-10-2026 | januscollab | 1/1033 | 0 | 89 |  | 0 commit(s) not in main, last 21-10-2026, no newer branch holds them |
| owner decides | `v26-g7` | local only | 21-10-2026 | januscollab | 4/1022 | 0 | 10 |  | 0 commit(s) not in main, last 21-10-2026, no newer branch holds them |
| owner decides | `v26-guard-174` | remote only | 20-10-2026 | insyncalan | 14/1451 | 13 | 9 |  | 13 commit(s) not in main, last 20-10-2026, no newer branch holds them |
| owner decides | `v26-help-text` | local only | 20-10-2026 | januscollab | 1/1434 | 1 | 2 |  | 1 commit(s) not in main, last 20-10-2026, no newer branch holds them |
| owner decides | `v26-line` | local only | 21-10-2026 | januscollab | 1/1259 | 1 | 2 |  | 1 commit(s) not in main, last 21-10-2026, no newer branch holds them |
| owner decides | `v26-notes-delete-retry` | local and remote | 22-10-2026 | januscollab | 1/956 | 1 | 1 |  | 1 commit(s) not in main, last 22-10-2026, no newer branch holds them |
| owner decides | `v26-notes-inputs` | local and remote | 22-10-2026 | januscollab | 1/956 | 1 | 1 |  | 1 commit(s) not in main, last 22-10-2026, no newer branch holds them |
| owner decides | `v26-v260-fix` | local only | 22-10-2026 | januscollab | 1/869 | 1 | 1 |  | 1 commit(s) not in main, last 22-10-2026, no newer branch holds them |
| owner decides | `v261-asrace` | local only | 23-10-2026 | januscollab | 2/687 | 2 | 5 |  | 2 commit(s) not in main, last 23-10-2026, no newer branch holds them |
| owner decides | `v261-capa` | local only | 23-10-2026 | januscollab | 54/697 | 38 | 85 |  | 38 commit(s) not in main, last 23-10-2026, no newer branch holds them |
| owner decides | `v261-chainfix` | local only | 23-10-2026 | januscollab | 1/762 | 1 | 2 |  | 1 commit(s) not in main, last 23-10-2026, no newer branch holds them |
| owner decides | `v261-gate3` | local only | 23-10-2026 | januscollab | 57/697 | 35 | 81 |  | 35 commit(s) not in main, last 23-10-2026, no newer branch holds them |
| owner decides | `v261-known307` | local only | 23-10-2026 | januscollab | 3/687 | 3 | 1 |  | 3 commit(s) not in main, last 23-10-2026, no newer branch holds them |
| owner decides | `v262-183h` | local only | 23-10-2026 | januscollab | 19/687 | 19 | 30 |  | 19 commit(s) not in main, last 23-10-2026, no newer branch holds them |
| owner decides | `v262-183r` | local only | 23-10-2026 | januscollab | 17/687 | 17 | 31 |  | 17 commit(s) not in main, last 23-10-2026, no newer branch holds them |
| owner decides | `v262-250b` | local and remote | 23-10-2026 | januscollab | 3/687 | 3 | 18 |  | 3 commit(s) not in main, last 23-10-2026, no newer branch holds them |
| owner decides | `v262-chain` | local only | 23-10-2026 | januscollab | 5/684 | 5 | 28 |  | 5 commit(s) not in main, last 23-10-2026, no newer branch holds them |
| owner decides | `v262-discard-undo` | local only | 23-10-2026 | januscollab | 2/697 | 2 | 10 |  | 2 commit(s) not in main, last 23-10-2026, no newer branch holds them |
| owner decides | `v262-discard2` | local only | 23-10-2026 | januscollab | 3/674 | 1 | 11 |  | 1 commit(s) not in main, last 23-10-2026, no newer branch holds them |
| owner decides | `v262-f1` | local only | 23-10-2026 | januscollab | 2/697 | 2 | 19 |  | 2 commit(s) not in main, last 23-10-2026, no newer branch holds them |
| owner decides | `v262-f1c` | local and remote | 23-10-2026 | januscollab | 3/687 | 2 | 8 |  | 2 commit(s) not in main, last 23-10-2026, no newer branch holds them |
| owner decides | `v262-follow` | local only | 23-10-2026 | januscollab | 4/745 | 4 | 26 |  | 4 commit(s) not in main, last 23-10-2026, no newer branch holds them |
| owner decides | `v262-followb` | local only | 23-10-2026 | januscollab | 4/684 | 4 | 26 |  | 4 commit(s) not in main, last 23-10-2026, no newer branch holds them |
| owner decides | `v262-parked` | local only | 23-10-2026 | januscollab | 1/674 | 1 | 1 |  | 1 commit(s) not in main, last 23-10-2026, no newer branch holds them |
| owner decides | `v262-small` | local only | 23-10-2026 | januscollab | 5/687 | 5 | 15 |  | 5 commit(s) not in main, last 23-10-2026, no newer branch holds them |
| owner decides | `v264-250` | local and remote | 23-10-2026 | januscollab | 23/745 | 20 | 39 |  | 20 commit(s) not in main, last 23-10-2026, no newer branch holds them |
| owner decides | `v264-f3` | local only | 23-10-2026 | januscollab | 7/763 | 7 | 13 |  | 7 commit(s) not in main, last 23-10-2026, no newer branch holds them |
| owner decides | `v264-sim` | local only | 23-10-2026 | januscollab | 4/763 | 4 | 15 |  | 4 commit(s) not in main, last 23-10-2026, no newer branch holds them |
| owner decides | `vip-tools-toolsearch` | local only | 15-10-2026 | januscollab | 1/2765 | 1 | 3 |  | 1 commit(s) not in main, last 15-10-2026, no newer branch holds them |
| owner decides | `work-144-cols` | local only | 16-10-2026 | januscollab | 2/2699 | 1 | 4 |  | 1 commit(s) not in main, last 16-10-2026, no newer branch holds them |
| keep | `ai-models-132-apply` | local and remote | 18-10-2026 | insyncalan | 23/1877 | 22 | 49 |  | a live release line or team branch |
| keep | `ai-models-proposal-r3` | local and remote | 18-10-2026 | insyncalan | 11/2422 | 11 | 47 |  | a live release line or team branch |
| keep | `dev-box-known-failures` | local and remote | 26-10-2026 | Wanda | 1/237 | 1 | 1 |  | checked out in ~/dev.env/wt-box-failures |
| keep | `dev-branch-audit` | local and remote | 25-10-2026 | januscollab | 1/415 | 1 | 5 |  | checked out in ~/dev.env/wt-dev-branch-audit |
| keep | `dev-ci-free-plan` | local and remote | 25-10-2026 | januscollab | 1/321 | 0 | 6 |  | checked out in ~/dev.env/wt-dev-ci-free-plan |
| keep | `dev-test-speed` | local and remote | 25-10-2026 | januscollab | 6/445 | 5 | 9 |  | checked out in ~/dev.env/wt-dev-test-speed |
| keep | `dev-test-speed-vault` | local and remote | 25-10-2026 | januscollab | 2/445 | 2 | 5 |  | checked out in ~/dev.env/wt-dev-test-speed-vault |
| keep | `docs-269` | local only | 27-10-2026 | januscollab | 1/0 | 1 | 1 |  | checked out in ~/dev.env/wt-docs269 |
| keep | `help-158b` | local only | 17-10-2026 | januscollab | 18/2375 | 17 | 36 |  | checked out in ~/dev.env/wt-help-158b |
| keep | `notes-undo-175` | local only | 17-10-2026 | januscollab | 2/2387 | 1 | 6 |  | checked out in ~/dev.env/creaite-wt-undo175; the same commit as notes-136-r (keep one) |
| keep | `p233-217` | local only | 18-10-2026 | januscollab | 1/1790 | 1 | 2 |  | checked out in ~/dev.env/creaite/.claude/worktrees/agent-acea4f7a77dad10e2 |
| keep | `pm-262-docs` | local only | 24-10-2026 | januscollab | 2/670 | 2 | 2 |  | changed 3 day(s) ago |
| keep | `readme-drop-first-ten` | local and remote | 25-10-2026 | januscollab | 2/445 | 2 | 1 | #38 OPEN | checked out in ~/dev.env/wt-readme |
| keep | `team-banner-132-05rev` | local only | 26-10-2026 | Bruce Banner | 51/131 | 49 | 71 |  | a live release line or team branch |
| keep | `team-banner-132-release` | local only | 27-10-2026 | push check | 4/14 | 4 | 5 |  | a live release line or team branch |
| keep | `team-banner-132-suites` | local only | 27-10-2026 | Bruce Banner | 50/131 | 48 | 70 |  | a live release line or team branch |
| keep | `team-banner-250-rev3` | local only | 27-10-2026 | Bruce Banner | 19/131 | 17 | 39 |  | a live release line or team branch |
| keep | `team-banner-329` | local only | 27-10-2026 | Bruce Banner | 27/131 | 25 | 54 |  | a live release line or team branch |
| keep | `team-banner-363-list` | local only | 27-10-2026 | Bruce Banner | 6/131 | 6 | 3 |  | a live release line or team branch |
| keep | `team-banner-366-track` | local only | 26-10-2026 | Bruce Banner | 5/288 | 5 | 3 |  | a live release line or team branch |
| keep | `team-banner-385` | local only | 27-10-2026 | Bruce Banner | 10/131 | 10 | 33 |  | a live release line or team branch |
| keep | `team-banner-ai117` | local only | 27-10-2026 | Bruce Banner | 91/10 | 84 | 137 |  | a live release line or team branch |
| keep | `team-cap-199-gaps` | local only | 27-10-2026 | insyncalan | 5/131 | 5 | 5 |  | a live release line or team branch |
| keep | `team-cap-370-fix` | local only | 27-10-2026 | Steve Rogers | 91/10 | 84 | 136 |  | a live release line or team branch |
| keep | `team-cap-370-s1` | local and remote | 27-10-2026 | insyncalan | 2/131 | 2 | 11 |  | the local branch has 1 commit(s) not on origin |
| keep | `team-cap-370-s2` | local only | 27-10-2026 | insyncalan | 6/131 | 6 | 22 |  | a live release line or team branch |
| keep | `team-cap-374-rebased` | local only | 27-10-2026 | Steve Rogers | 70/10 | 65 | 123 |  | a live release line or team branch |
| keep | `team-cap-374-reveal` | local only | 27-10-2026 | insyncalan | 12/131 | 12 | 25 |  | a live release line or team branch |
| keep | `team-cap-386-g` | local only | 27-10-2026 | Steve Rogers | 74/131 | 51 | 45 |  | a live release line or team branch |
| keep | `team-cap-386-s1` | local only | 27-10-2026 | Steve Rogers | 7/131 | 7 | 14 |  | a live release line or team branch |
| keep | `team-cap-386-s12` | local only | 27-10-2026 | Steve Rogers | 35/131 | 31 | 36 |  | a live release line or team branch |
| keep | `team-cap-386-s2` | local only | 27-10-2026 | Steve Rogers | 24/131 | 24 | 24 |  | a live release line or team branch |
| keep | `team-cap-386-s4-tests` | local only | 27-10-2026 | Steve Rogers | 5/10 | 4 | 16 |  | a live release line or team branch |
| keep | `team-cap-388-title-centre` | local only | 27-10-2026 | Steve Rogers | 92/10 | 85 | 137 |  | a live release line or team branch |
| keep | `team-cap-goldens-266` | remote only | 25-10-2026 | insyncalan | 6/677 | 6 | 108 |  | a live release line or team branch |
| keep | `team-cap-reviewkit-26d` | remote only | 23-10-2026 | insyncalan | 5/1259 | 5 | 80 |  | a live release line or team branch |
| keep | `team-cap-tools` | remote only | 25-10-2026 | insyncalan | 4/677 | 4 | 50 |  | a live release line or team branch |
| keep | `team-cap-usage-87` | remote only | 24-10-2026 | insyncalan | 3/536 | 3 | 2 |  | a live release line or team branch |
| keep | `team-cap-v262-handchecks` | remote only | 23-10-2026 | insyncalan | 1/637 | 1 | 1 |  | a live release line or team branch |
| keep | `team-cap-v262-handchecks-2` | remote only | 23-10-2026 | insyncalan | 2/637 | 2 | 2 |  | a live release line or team branch |
| keep | `team-cap-v262-handchecks-3` | remote only | 23-10-2026 | insyncalan | 4/634 | 4 | 2 |  | a live release line or team branch |
| keep | `team-cap-v262-handchecks-4` | remote only | 24-10-2026 | insyncalan | 5/634 | 5 | 2 |  | a live release line or team branch |
| keep | `team-cap-v264-handchecks` | remote only | 24-10-2026 | insyncalan | 1/504 | 1 | 2 |  | a live release line or team branch |
| keep | `team-cap-v264-handchecks-2` | remote only | 24-10-2026 | insyncalan | 3/495 | 2 | 2 |  | a live release line or team branch |
| keep | `team-cap-v264-notes` | remote only | 24-10-2026 | insyncalan | 2/495 | 2 | 1 |  | a live release line or team branch |
| keep | `team-cap-v264-notes-2` | remote only | 24-10-2026 | insyncalan | 4/496 | 3 | 1 |  | a live release line or team branch |
| keep | `team-cap-v264-sheet` | remote only | 24-10-2026 | insyncalan | 4/498 | 3 | 2 |  | a live release line or team branch |
| keep | `team-cap-v264-sheet-2` | remote only | 24-10-2026 | insyncalan | 6/493 | 4 | 2 |  | a live release line or team branch |
| keep | `team-cap-v264b-handchecks` | remote only | 24-10-2026 | insyncalan | 1/435 | 1 | 2 |  | a live release line or team branch |
| keep | `team-cap-v264b-handchecks-2` | remote only | 25-10-2026 | insyncalan | 3/434 | 2 | 2 |  | a live release line or team branch |
| keep | `team-cap-v265-sheet` | remote only | 25-10-2026 | insyncalan | 2/430 | 2 | 4 |  | a live release line or team branch |
| keep | `team-cap-v266-sheet` | remote only | 25-10-2026 | insyncalan | 3/398 | 3 | 3 |  | a live release line or team branch |
| keep | `team-cap-wip-email-153-fix5` | remote only | 25-10-2026 | insyncalan | 2/2144 | 1 | 8 |  | a live release line or team branch |
| keep | `team-stark-250-readorder` | local only | 24-10-2026 | januscollab | 1/643 | 1 | 4 |  | a live release line or team branch |
| keep | `v2610-344` | local and remote | 27-10-2026 | januscollab | 1/131 | 1 | 3 |  | checked out in ~/dev.env/wt-v2610-344 |
| keep | `v2610-344b` | local and remote | 27-10-2026 | januscollab | 3/131 | 3 | 3 |  | checked out in ~/dev.env/wt-v2610-344fix |
| keep | `v2610-366` | local and remote | 27-10-2026 | januscollab | 2/131 | 2 | 2 |  | checked out in ~/dev.env/wt-v2610-366 |
| keep | `v2610-366-plan` | local and remote | 26-10-2026 | januscollab | 1/131 | 1 | 1 |  | checked out in ~/dev.env/wt-v2610-366-plan |
| keep | `v2610-366-s1` | local only | 27-10-2026 | Bruce Banner | 3/131 | 3 | 1 |  | checked out in ~/dev.env/wt-v2610-366-s1 |
| keep | `v2610-370-plan` | local and remote | 26-10-2026 | januscollab | 3/131 | 3 | 1 |  | checked out in ~/dev.env/wt-v2610-370-plan |
| keep | `v2610-370s3` | local and remote | 27-10-2026 | januscollab | 2/18 | 2 | 5 |  | checked out in ~/dev.env/wt-v2610-370s3 |
| keep | `v2610-386s3` | local and remote | 27-10-2026 | januscollab | 2/10 | 2 | 11 |  | checked out in ~/dev.env/wt-v2610-386s3 |
| keep | `v2610-386s3b` | local and remote | 27-10-2026 | januscollab | 10/10 | 10 | 11 |  | checked out in ~/dev.env/wt-v2610-386s3b |
| keep | `v2610-386s4` | local only | 27-10-2026 | januscollab | 2/10 | 2 | 15 |  | a live release line or team branch |
| keep | `v2610-386s4b` | local and remote | 27-10-2026 | januscollab | 14/10 | 12 | 16 |  | checked out in ~/dev.env/wt-v2610-386s4 |
| keep | `v2610-a` | local and remote | 26-10-2026 | januscollab | 3/131 | 2 | 10 |  | checked out in ~/dev.env/wt-v2610-a |
| keep | `v2610-audit` | local and remote | 26-10-2026 | januscollab | 13/131 | 11 | 40 |  | checked out in ~/dev.env/wt-v2610-audit |
| keep | `v2610-b` | local and remote | 26-10-2026 | januscollab | 1/131 | 1 | 4 |  | checked out in ~/dev.env/wt-v2610-b |
| keep | `v2610-c` | local and remote | 26-10-2026 | januscollab | 4/131 | 3 | 16 |  | checked out in ~/dev.env/wt-v2610-c |
| keep | `v2610-chain` | local and remote | 27-10-2026 | januscollab | 90/10 | 83 | 135 |  | checked out in ~/dev.env/wt-v2610-chain |
| keep | `v2610-chain-fix` | local only | 27-10-2026 | januscollab | 63/10 | 58 | 103 |  | checked out in ~/dev.env/wt-v2610-chainfix |
| keep | `v2610-d` | local and remote | 26-10-2026 | januscollab | 4/131 | 3 | 19 |  | checked out in ~/dev.env/wt-v2610-d |
| keep | `v2610-fetchtext` | local and remote | 27-10-2026 | januscollab | 19/131 | 17 | 41 |  | checked out in ~/dev.env/wt-v2610-fetchtext |
| keep | `v2610-fix381` | local only | 27-10-2026 | januscollab | 74/10 | 69 | 110 |  | checked out in ~/dev.env/wt-v2610-fix381 |
| keep | `v2610-hc` | local only | 27-10-2026 | januscollab | 69/10 | 64 | 110 |  | checked out in ~/dev.env/wt-v2610-hc |
| keep | `v2610-main` | local and remote | 26-10-2026 | januscollab | 18/131 | 16 | 39 |  | checked out in ~/dev.env/wt-v2610-main |
| keep | `v2610-plan` | local and remote | 26-10-2026 | januscollab | 1/135 | 1 | 1 |  | checked out in ~/dev.env/wt-v2610-plan |
| keep | `v2610-red` | local only | 27-10-2026 | januscollab | 89/10 | 82 | 135 |  | checked out in ~/dev.env/wt-v2610-red |
| keep | `v263-338` | local only | 24-10-2026 | januscollab | 6/615 | 6 | 5 |  | changed 3 day(s) ago |
| keep | `v263-notes` | local only | 24-10-2026 | januscollab | 1/591 | 1 | 3 |  | changed 3 day(s) ago |
| keep | `v264-release-fix2` | local only | 24-10-2026 | januscollab | 1/454 | 1 | 1 |  | changed 3 day(s) ago |
| keep | `v265-344-snapshot-tool` | local and remote | 24-10-2026 | januscollab | 1/445 | 1 | 5 |  | changed 3 day(s) ago |
| keep | `v265-release` | local only | 25-10-2026 | januscollab | 1/428 | 0 | 1 |  | checked out in ~/dev.env/wt-rel265 |
| keep | `v266-339` | local and remote | 25-10-2026 | januscollab | 4/445 | 1 | 9 |  | checked out in ~/dev.env/wt-339 |
| keep | `v266-341fix` | local and remote | 25-10-2026 | januscollab | 1/371 | 0 | 1 |  | checked out in ~/dev.env/wt-v266-341fix |
| keep | `v266-358prop` | local and remote | 25-10-2026 | januscollab | 1/364 | 0 | 1 |  | checked out in ~/dev.env/wt-v266-358prop |
| keep | `v267-339c` | local and remote | 25-10-2026 | januscollab | 1/341 | 1 | 6 |  | checked out in ~/dev.env/wt-v267-339c |
| keep | `v267-chain` | local and remote | 25-10-2026 | januscollab | 7/298 | 0 | 19 |  | checked out in ~/dev.env/wt-v267-chain |
| keep | `v267-release` | local only | 25-10-2026 | januscollab | 2/249 | 0 | 6 | #43 MERGED | checked out in ~/dev.env/wt-v267-release |
| keep | `v268-358-accepted` | local and remote | 25-10-2026 | januscollab | 1/328 | 1 | 1 |  | checked out in ~/dev.env/wt-v268-358-accepted |
| keep | `v268-amber` | local and remote | 25-10-2026 | januscollab | 3/328 | 3 | 75 |  | checked out in ~/dev.env/wt-v268-amber |
| keep | `v268-fuzz` | local and remote | 26-10-2026 | januscollab | 1/288 | 1 | 2 |  | checked out in ~/dev.env/wt-v268-fuzz |
| keep | `v268-guard-summary` | local only | 25-10-2026 | januscollab | 1/245 | 1 | 1 |  | checked out in ~/dev.env/wt-v268-guard-summary |
| keep | `v268-paths-plan` | local and remote | 25-10-2026 | januscollab | 2/328 | 2 | 1 |  | checked out in ~/dev.env/wt-v268-paths-plan |
| keep | `v269-bundle` | local and remote | 26-10-2026 | januscollab | 5/131 | 5 | 8 |  | checked out in ~/dev.env/wt-v269-bundle |
| keep | `v269-bundle5` | local and remote | 27-10-2026 | januscollab | 1/10 | 0 | 5 |  | checked out in ~/dev.env/wt-v269-bundle5 |
| keep | `v269-diag` | local only | 27-10-2026 | januscollab | 2/10 | 2 | 3 |  | checked out in ~/dev.env/wt-v269-diag |
| keep | `v269-g12` | local and remote | 26-10-2026 | januscollab | 3/131 | 3 | 10 |  | checked out in ~/dev.env/wt-v269-g12 |
| keep | `v269-timing` | local only | 27-10-2026 | januscollab | 1/10 | 0 | 1 |  | checked out in ~/dev.env/wt-v269-timing |
| keep | `v27-132-build` | local and remote | 25-10-2026 | januscollab | 12/331 | 12 | 30 |  | checked out in ~/dev.env/wt-v27-132-build |
| keep | `v27-132-plan` | local and remote | 25-10-2026 | januscollab | 1/415 | 1 | 1 |  | checked out in ~/dev.env/wt-v27-132-plan |
| keep | `v27-132-scratch` | remote only | 25-10-2026 | januscollab | 9/331 | 9 | 20 |  | a live release line or team branch |
| keep | `v27-250-plan` | local and remote | 25-10-2026 | januscollab | 1/415 | 1 | 1 |  | checked out in ~/dev.env/wt-v27-250-plan |
| keep | `v27-316-plan` | local and remote | 25-10-2026 | januscollab | 1/415 | 1 | 1 |  | checked out in ~/dev.env/wt-v27-316-plan |
| keep | `v27-g8-spike` | local and remote | 25-10-2026 | januscollab | 2/415 | 2 | 2 |  | checked out in ~/dev.env/wt-v27-g8-spike |

## Worktrees with uncommitted changes

This laptop's clone: 183 worktrees, 16 with uncommitted changes (below; none locked or prunable). Nothing has been removed: a dirty worktree needs a forced removal, which is Alan's call. To list them anywhere, run `python3 dev/tools/branch_report.py --worktrees`; it removes nothing.

| Worktree | Branch | State | Changes | Files |
|---|---|---|---|---|
| `~/dev.env/creaite` | `main` |  | ?? 3 | b26.md, c29.md, c31.md |
| `~/dev.env/creaite-health-162` | `health-162` |  | M 2 | system/templates/dashboard.html, system/templates/dashboard/src/today.js |
| `~/dev.env/creaite-preview` | `(detached)` | detached | M 1 | system/config/settings.json |
| `~/dev.env/creaite-wt-undo175` | `notes-undo-175` |  | ?? 1 | dev/tests/test_notes_undo_history.py |
| `~/dev.env/creaite/.claude/worktrees/agent-acea4f7a77dad10e2` | `p233-217` |  | ?? 2, M 14 | dev/dashboard-spec.md, dev/mockups/weekly-report-tidy-mockup.html, dev/sprints/weekly-report-tidy-brief.md, dev/tests/test_health_suggest.py, system/templates/dashboard.html, system/templates/dashboard/src/components/report/SheetPage.jsx, system/templates/dashboard/src/components/report/weekly/Glance.jsx, system/templates/dashboard/src/components/report/weekly/Tables.jsx (+8 more) |
| `~/dev.env/creaite/.claude/worktrees/v210-fix-export` | `v210-fix-export` |  | ?? 4 | dev/tests/handchecks/hcbase.py, dev/tests/handchecks/measure.py, dev/tests/handchecks/sheet.py, dev/tools/handcheck.py |
| `~/dev.env/creaite/.claude/worktrees/v210-fixes` | `v210-fixes` |  | ?? 4 | dev/tests/handchecks/hcbase.py, dev/tests/handchecks/measure.py, dev/tests/handchecks/sheet.py, dev/tools/handcheck.py |
| `~/dev.env/creaite/.claude/worktrees/v210-handchecks` | `v210-handchecks` |  | ?? 5 | dev/tests/handchecks/hcbase.py, dev/tests/handchecks/measure.py, dev/tests/handchecks/sheet.py, dev/tests/handchecks/test_v195.py, dev/tools/handcheck.py |
| `~/dev.env/creaite/.claude/worktrees/v210-star` | `v210-star` |  | ?? 2 | dev/tests/handchecks/, dev/tools/handcheck.py |
| `~/dev.env/wt-g8-canary` | `dev-g8-canary` |  | ?? 1 | dev/tools/stub_anthropic.py |
| `~/dev.env/wt-help-158b` | `help-158b` |  | ?? 1, M 11 | dev/tests/snapshots/settings-essentials.html, dev/tests/test_snapshots.py, system/scripts/build_dashboard.py, system/scripts/settings_catalogue.py, system/templates/dashboard.html, system/templates/dashboard/src/core/nav.js, system/templates/dashboard/src/core/page.js, system/templates/dashboard/src/core/server.js (+4 more) |
| `~/dev.env/wt-v261-291` | `v261-291-tier1` |  | ?? 3 | dev/PLAIN-WORDS.md, dev/tests/plain_words_baseline.json, dev/tests/test_plain_words.py |
| `~/dev.env/wt-v266-release` | `v266-release` |  | M 3 | dev/tests/test_capture_drawer.py, system/templates/dashboard.html, system/templates/dashboard/src/components/notes/CaptureDrawer.jsx |
| `~/dev.env/wt-v266-ver` | `v266-ver` |  | D 1 | dev/tests/.mc_mut/m.mjs |
| `~/dev.env/wt-v269-bundle` | `v269-bundle` |  | M 1 | dev/tests/test_bundle_privacy.py |
| `~/dev.env/wt-v27-g8-spike` | `v27-g8-spike` |  | M 1 | dev/proposals/132/G8-SPIKE.md |
