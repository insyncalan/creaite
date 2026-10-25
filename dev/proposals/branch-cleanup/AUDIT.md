# Remote branch audit, insyncalan/creaite (25-10-2026)

Read-only. Nothing was deleted. `git branch -r --no-merged origin/main` lists **319** branches (330 remote branches in all; the rest are already merged into main). Open pull requests: #40 `v266-release`, #38 `readme-drop-first-ten`, #37 `dev-cleanup-rogue-md`. Branch name lists (no `origin/`) are beside this file: `keep.txt`, `superseded.txt`, `overtaken.txt`, `unique-review.txt`.

| Group | Branches | Meaning | Delete? |
|---|---|---|---|
| A. KEEP | 66 | Live lines and open pull requests: `v264b-*`, `v265-*`, `v266-*`, `v267-*`, `team-cap-*`, `dev-test-speed*`, `dev-ci-*`, `docs-*`, `dev-branch-audit`, and the heads of the three open PRs | No |
| B. SUPERSEDED | 58 | **Proven in main**: every commit is already there by patch-id (`git cherry origin/main <branch>` shows no `+`), or the branch's changed files are byte-identical in main | Yes, safe |
| C. ABANDONED (overtaken) | 172 | Not provably merged, but main has since changed **every** file the branch changed, and none of its changes sits on a file main left alone: the work moved on (old v25x/v26x feature, WIP, scratch, proposal and hand-check branches) | Yes, **after** a bundle backup |
| D. REVIEW | 23 | Has a change to a file that main never touched since the branch was cut: real unmerged work, or a rejected idea. Needs its owner's word | Not on this audit |

## How the groups were decided
- B: `git cherry origin/main <branch>` (patch-id) with no unmatched commit, or `git diff origin/main <branch> -- <files the branch changed>` empty.
- C/D: for each file the branch changed since its merge base, compare three blobs: merge base, main, branch. If the branch differs from main and main still equals the merge base, main never got that change (group D). If no such file exists, every change was either merged in changed form or overtaken (group C). This is a **heuristic**: it cannot tell "merged with edits" from "dropped", so C is bundled before deletion and D is left alone.
- No squash merges were found in main's history (it merges with merge commits), so patch-id is a fair test for B.

## Commands (run from a clone with all remotes fetched; nothing here has been run)
```bash
# B. safe: everything in these branches is already in main
xargs -n 20 git push origin --delete < dev/proposals/branch-cleanup/superseded.txt

# C. keep a backup first, then delete (the bundle holds every commit; restore with: git fetch <bundle> '<branch>:<branch>')
git fetch origin --prune
git bundle create ~/branch-backup-abandoned-2026-10-25.bundle $(sed 's#^#origin/#' dev/proposals/branch-cleanup/overtaken.txt | tr '\n' ' ')
git bundle verify ~/branch-backup-abandoned-2026-10-25.bundle
xargs -n 20 git push origin --delete < dev/proposals/branch-cleanup/overtaken.txt

# D. no command: ask each owner (list below), or bundle them too before deleting
```
Branch deletion on GitHub can be undone for a short time from the pull request page only if a PR existed; otherwise the bundle is the way back. The local `refs/remotes` copies go with `git fetch --prune`.

## Worktrees under /Users/alanmahon/dev.env with uncommitted changes (13 of 71)
Several belong to sessions that are working now (`wt-v266-release`, `wt-v266-peoplefit`, `wt-v266-ver`): do not clean those.

| Worktree | Branch | Holds |
|---|---|---|
| creaite-health-162 | health-162 | 2 modified: `dashboard.html`, `today.js` (an old Health item) |
| creaite-preview | detached cbbc5996 | `system/config/settings.json` changed (a preview copy's settings; nothing to keep) |
| creaite-wt-undo175 | notes-undo-175 | 1 untracked: `test_notes_undo_history.py` |
| creaite/.claude/worktrees/agent-acea4f7a77dad10e2 | p233-217 | 14 modified + 2 untracked: weekly-report tidy (spec, mockup, brief, `test_health_suggest.py`, dashboard files) |
| .../v210-fix-export, v210-fixes, v210-handchecks, v210-star | v210-* | untracked hand-check harness files (`hcbase.py`, `measure.py`, `sheet.py`, `handcheck.py`); also on main in final form |
| wt-help-158b | help-158b | 11 modified + 1 untracked: settings catalogue, snapshots, `build_dashboard.py`, `dashboard.html` (help item 158b) |
| wt-v261-291 | v261-291-tier1 | 3 untracked: `PLAIN-WORDS.md`, `plain_words_baseline.json`, `test_plain_words.py` |
| wt-v266-peoplefit | v266-peoplefit | 3 modified: `test_v265_341_structure.py`, `dashboard.html`, `style.css` (active) |
| wt-v266-release | v266-release | 3 modified: `test_capture_drawer.py`, `dashboard.html`, `CaptureDrawer.jsx` (active, the 2.6.6 release) |
| wt-v266-ver | v266-ver | 1 modified: `dev/tests/.mc_mut/m.mjs` (a mutation-test scratch file) |

None of mine (`wt-dev-test-speed`, `wt-bootstrap`, `wt-v267-guard-summary`, `wt-dev-ci-free-plan`, `wt-v266-347-fixes`, `wt-dev-branch-audit`) has uncommitted changes.

## Group D: review these first (23)
Several are one-line test or doc follow-ups that probably never landed (`v26-notes-delete-retry`, `v255-notes-delete-retry`, `cdp-resize-waits`, `fix-cdp-resize`, `v250-testfix`, `v250-teststale`); `pm-intake-briefs` is the PM's 188-commit sheet branch (PM material belongs in the private repo, not here); `ai-models-132-apply` carries #132 work.

| Branch | Tip | Commits ahead | Files with changes main never got | Last commit |
|---|---|---|---|---|
| `ai-models-132-apply` | 10-18 | 23 | `dev/tests/pinned/guard/decisions.json` | #132 G10: the test-fakes switch only in the development |
| `cdp-resize-waits` | 10-15 | 2 | `dev/tests/test_files_narrow.py` | Tests: drop the innerWidth/innerHeight waits cdp.Browse |
| `fix-cdp-resize` | 10-15 | 1 | `dev/tests/handchecks/measure.py`, `dev/tests/test_files_narrow.py` | cdp: resize waits for the page to draw a frame at the n |
| `handchecks-v251c` | 10-20 | 2 | `dev/handchecks/v2.5.1.md`, `dev/tests/test_handcheck_runner.py` (+1) | Hand checks 38 and 39: the quoted, spliced and run form |
| `main-batch` | 10-15 | 14 | `dev/tests/test_files_narrow.py`, `dev/tests/test_permission_panel.py.bak` | Merge remote-tracking branch 'origin/main' into main-ba |
| `notes-136-focus` | 10-17 | 2 | `dev/tests/test_permission_panel.py.bak` | #136: real-Chrome tests for the inert page, the Tab tra |
| `p250-e` | 10-19 | 1 | `dev/tests/test_intake_review_harden_model.py` | #232: Esc-in-chat test, Approve routine in-flight guard |
| `pm-intake-briefs` | 10-21 | 188 | `.gitignore`, `dev/design-system/README.md` (+84) | 2.5.3 hand-check sheet: final, #264 #265 #251 #97 added |
| `rm-permission-panel-bak` | 10-15 | 1 | `dev/tests/test_permission_panel.py.bak` | Remove dev/tests/test_permission_panel.py.bak, a stale  |
| `v20-rules-notes` | 10-15 | 6 | `system/templates/vendor/README.md` | Merge v20-docs (fa378a7: the help golden re-recorded fo |
| `v210-int-notes` | 10-15 | 3 | `dev/sprints/v210-contract.md` | Contract integration notes: P7's two renames are done ( |
| `v250-testfix` | 10-19 | 4 | `dev/tests/test_portfolio_table.py` | behaviour_expected_failures: the held-sections dialog ( |
| `v250-teststale` | 10-19 | 4 | `dev/tests/test_portfolio_table.py` | behaviour_expected_failures: the held-sections dialog ( |
| `v251-step3` | 10-21 | 3 | `dev/proposals/client-output-step3/README.md` | WIP: save all work (uncommitted changes at pause) |
| `v255-notes-delete-retry` | 10-22 | 1 | `dev/tests/test_notes_delete.py` | test_notes_delete: the page call asks again on a busy a |
| `v26-297` | 10-22 | 1 | `dev/proposals/c49/ISSUE.md`, `dev/tests/handchecks/hcbase.py` | #297: c49's three Undo lines were timing, not a leaking |
| `v26-fetch-transcripts` | 10-20 | 9 | `dev/tests/test_transcripts.py` | #250: the catalogue keeps the brief's help text word fo |
| `v26-guard-174` | 10-20 | 14 | `dev/tests/test_permission_panel.py.bak` | Proposal #174: README, v253 note and the default mutati |
| `v26-notes-delete-retry` | 10-22 | 1 | `dev/tests/test_notes_delete.py` | test_notes_delete: the page call asks again on a busy a |
| `v26-notes-inputs` | 10-22 | 1 | `dev/proposals/v26-line/NOTES-INPUTS.md` | NOTES-INPUTS.md: the 2.6.0 notes inputs from v26-line-4 |
| `v262-250b` | 10-23 | 3 | `dev/tests/test_transcripts.py`, `system/scripts/transcripts.py` (+1) | #250: a transcript URL named by a held event, or by two |
| `v262-f1c` | 10-23 | 3 | `dev/tests/test_archive_projects.py` | F1c: copy_rows helper keeps migrate_schema under the co |
| `v264-250` | 10-23 | 23 | `dev/tests/test_transcripts.py`, `system/scripts/transcripts.py` (+1) | #250 option 2: live_server.diff keeps _on_tool_result w |

## Group B: SUPERSEDED (58)
| Branch | Tip | Author | Commits ahead of main | Last commit |
|---|---|---|---|---|
| `ask-148-reopen` | 10-16 | januscolla | 1 | ask creaite: a finished run replayed on reattach appears as it is, no  |
| `ask-hook-fix` | 10-15 | januscolla | 4 | ask creaite refuses an unquoted # comment, ~+ ~- ~N and ** (the shell' |
| `ask-hook-fix-final` | 10-16 | januscolla | 5 | ask creaite: tracker.py validate takes A5's stricter rule in its own f |
| `ask-hook-fix-v3` | 10-16 | januscolla | 9 | creaite-rules: the guard hook's refusals named in one sentence (A5/A6  |
| `editor-134-v220` | 10-17 | januscolla | 3 | #134: the report sheets' one-line grouped toolbar (sheet profile); Wor |
| `esc-keeps-run-130` | 10-16 | insyncalan | 2 | ask creaite: accessible name on the working state, Esc from the Stop b |
| `evidence-195-shards` | 10-15 | januscolla | 1 | Evidence only: v1.9.5 cut + sharded workflow (tests.yml from ci-shards |
| `export-audit-doc` | 10-18 | januscolla | 1 | Weekly report export audit (18-10-2026) |
| `guard-backslash-fix` | 10-16 | januscolla | 1 | Guard: a backslash inside double quotes is refused, so an escaped back |
| `health-203-page` | 10-17 | januscolla | 2 | health-203 page: typed redrafter arguments, no assignment in an expres |
| `health-203-plain` | 10-17 | januscolla | 2 | Health suggest: test that a made-up health or evidence ref in the repl |
| `health-card-wording-r2` | 10-15 | insyncalan | 1 | Health: a fix that only raises the approval card says it is waiting on |
| `help-210-patch` | 10-17 | januscolla | 1 | Help: the passages that still described the retired meeting page (Foll |
| `help-acceptance-check` | 10-17 | januscolla | 1 | help_acceptance.py: split main into one function per check, docstrings |
| `perm-mcp-fix` | 10-15 | januscolla | 3 | doctor: also flags a refused connector or acting built-in allowed in . |
| `perm-mcp-fix-final` | 10-16 | januscolla | 4 | One list of built-in names: KNOWN_BUILTINS moves to permissions.py (li |
| `pm-261-docs` | 10-23 | januscolla | 1 | Hand-check sheet for 2.6.1 (14 judgement and live-only checks) |
| `pm-ds-snapshots-261` | 10-24 | januscolla | 1 | Design system: regenerate snapshots for 2.6.1 |
| `pm-mockups-110` | 10-17 | januscolla | 77 | Alan's morning list: Review age option A approved; nothing left waitin |
| `pm-readme-261` | 10-24 | januscolla | 1 | README: refresh for 2.6.1 |
| `review-177` | 10-17 | januscolla | 4 | Tests: review triage ages use the clock's time of day (09:00 read 0 da |
| `run-tools-explicit-final` | 10-16 | januscolla | 8 | test_run_tools_explicit: an unused import out (check.py's ruff limit) |
| `run-usage-plain` | 10-17 | januscolla | 1 | Run usage monitor, plain code: usage_log.py, usage_report.py, RUN_USAG |
| `save/release-195` | 10-15 | insyncalan | 1 | release-195: merge v194-page-inputs (plan #6, BL-327): page_inputs() w |
| `save/scratch-hc260-232` | 10-20 | insyncalan | 3 | Merge remote-tracking branch 'origin/p260-e' into scratch-hc260-232 |
| `settings-poll-repro-r2` | 10-15 | insyncalan | 1 | Settings: share the diagnostics, update and set-up reads while one is  |
| `sweep-146-calendar` | 10-16 | januscolla | 1 | Sweep reads the calendar from today forward; past days already held ar |
| `sweep-146b` | 10-16 | januscolla | 3 | Lookback cap: sweep.max_lookback_days in settings, defaults and catalo |
| `tool-less-context-126` | 10-16 | insyncalan | 3 | #126: pin --model sonnet for the tool-less runs (Jarvis/Alan's decisio |
| `v20-docs` | 10-15 | januscolla | 1 | test_snapshots: re-record the help golden for v20-docs' Help text: Not |
| `v210-p6-sheet` | 10-15 | januscolla | 1 | Remove a stray sed backup, style.css-e (came in with d19ac620) |
| `v210-rc3` | 10-17 | insyncalan | 1 | globals.json: RailIcon added to the tests list (python3 dev/tools/buil |
| `v220-release-cap` | 10-18 | insyncalan | 1 | Merge origin/v220-release into v220-release-cap |
| `v240-merge-check` | 10-18 | insyncalan | 1 | Merge p240-h1 into v240-merge-check |
| `v250-matchtext` | 10-19 | januscolla | 1 | v2.5.0: Match internal for every section skips internal text sections  |
| `v251-pagefinish` | 10-19 | insyncalan | 1 | v2.5.0 page subset: a logo drawn as its name (Firm, Client, a partner' |
| `v253-followups` | 10-20 | januscolla | 2 | #253 item 2: guarded proposal v2 covers the result routes (class only, |
| `v253-quiet-hours` | 10-20 | januscolla | 2 | settings-essentials golden: the two quiet-hours rows under People I fo |
| `v253-suggest-nothing` | 10-20 | januscolla | 4 | Merge remote-tracking branch 'origin/v253-release' into v253-suggest-n |
| `v253-usage-reviews` | 10-20 | januscolla | 4 | #238 delta: route tests checked with the diff applied in a scratch tre |
| `v254-281` | 10-21 | januscolla | 1 | WIP: autosave |
| `v254-282` | 10-21 | januscolla | 1 | WIP: autosave |
| `v254-handchecks` | 10-22 | januscolla | 9 | test_v254: 2.5.4 hand checks, one per item (#276, #277, #279 to #282,  |
| `v26-delete-note-card` | 10-20 | januscolla | 9 | #255 README: the review follow-up table, the corrected symlink claim,  |
| `v26-g5-merge-wip` | 10-21 | januscolla | 1 | WIP (stopped by Alan 21-10 ~10:00): settings-line merge into the 2.6 l |
| `v26-track-from-review-3` | 10-21 | januscolla | 1 | WIP: autosave |
| `v261-low-notes` | 10-22 | insyncalan | 1 | paths: _resolved falls back only for EINVAL and never for a `..` name; |
| `v261-vip-rules` | 10-23 | januscolla | 1 | VIP / follow flag rules wording: diff, README and code places (proposa |
| `v261-wih` | 10-22 | januscolla | 1 | #241 D: regenerate live_server.diff so it applies on the 2.6.1 line an |
| `v262-322` | 10-23 | januscolla | 1 | #322: Today hides the whole Needs attention section when nothing needs |
| `v262-emit` | 10-23 | januscolla | 3 | emit-event-txn: wrap the fallback line (check.py LONG limit) |
| `v262-f1b` | 10-23 | januscolla | 1 | F1 on release2: nullable-columns diff rebased and fixed per Cap's revi |
| `v262-small2` | 10-23 | januscolla | 6 | Cap note 1: File without transcript sends the row's fingerprint; a cha |
| `v262-wpfix` | 10-23 | januscolla | 1 | test_writer_pinned: old-code fixture built from plain CREATE statement |
| `v263-fix-report-exports` | 10-24 | januscolla | 1 | test_report_exports: the title block says Shareable |
| `v263-intake-lows` | 10-24 | januscolla | 1 | #325 Intake: document the state chip (.irchip) as an approved exceptio |
| `v264-292` | 10-24 | januscolla | 1 | Plain words (#292): server messages from the guarded files keep their  |
| `v264-lows2` | 10-24 | januscolla | 2 | guarded_chain: the 2.6.3 pin is set; comments say so |

## Group C: ABANDONED, overtaken by main (172)
| Branch | Tip | Author | Commits ahead of main | Last commit |
|---|---|---|---|---|
| `activity-by-12` | 10-17 | januscolla | 1 | Activity's By column says "You, in Claude Code", not "You, via cx-edit |
| `ai-models-132` | 10-17 | insyncalan | 8 | #132: check.py clean: providers.state split into card, job_view and li |
| `ai-models-132-tests` | 10-18 | insyncalan | 9 | providers.py: import paths at module level so doctor's 'Scripts take l |
| `ai-models-proposal-r1` | 10-17 | insyncalan | 9 | #132 round 1 proposal: G1 key store, G1c never list in held runs, G2 m |
| `ai-models-proposal-r2` | 10-17 | insyncalan | 10 | #132 round 2 proposal: G4 OpenAI direct call (AI on selected text), G6 |
| `ai-models-proposal-r3` | 10-18 | insyncalan | 11 | #132 round 3 proposal: G8 Claude by API key through Claude Code's apiK |
| `asm26-scratch` | 10-21 | insyncalan | 8 | asm26 scratch: rowOf renamed in peopleRegister (check.py JSDUP vs inta |
| `bl342-part3-plan` | 10-15 | januscolla | 1 | BL-342 Part 3 plan: two-stage polling in eight steps (stage 1 on Sonne |
| `bl342-part3b-plan` | 10-15 | januscolla | 2 | BL-342 Part 3 B plan: two-stage polling superseded by cost (empty Sonn |
| `bl342-part3b-plan2` | 10-15 | januscolla | 3 | BL-342 Part 3 B plan: close suggestions as step 9 (Looks done: close < |
| `bl342-probe` | 10-15 | januscolla | 4 | Revert "vip_probe: start the probe's claude with --tools "" like the l |
| `bl343-usage` | 10-15 | januscolla | 2 | BL-343 phase A: confirmed cache rates (5-minute write 1.25x, 1-hour wr |
| `bundle-134` | 10-16 | insyncalan | 3 | #134: TaskList and TaskItem in Current state's editor features; vendor |
| `ci-shard-times` | 10-15 | insyncalan | 1 | #89: rebalance shard_times.txt so the 3.14 shards finish together |
| `ci-shard-times-main` | 10-15 | insyncalan | 1 | #89: rebalance shard_times.txt so the 3.14 shards finish together |
| `ci-shards-4-mine` | 10-15 | insyncalan | 3 | #89: shard_times.txt weights Chrome-tier files by their seconds and qu |
| `ci-shards-balance` | 10-15 | januscolla | 2 | #89 shard balance: four Linux shards per Python (predicted 4.6 minutes |
| `current-state-refine` | 10-16 | insyncalan | 5 | Tests for the refine review fixes, and the spec lines (C1 rests on the |
| `current-state-refine-131` | 10-16 | insyncalan | 8 | Refine: tests for the four mutation survivors, and spec lines on the s |
| `dates-178` | 10-17 | januscolla | 1 | Tests (#178): every date helper follows CREAITE_NOW; page clock pinned |
| `design-132-open-points` | 10-21 | insyncalan | 2 | #132 open points for Alan: one line each, with recommendations (from d |
| `design-132-v2` | 10-21 | insyncalan | 1 | #132 security design v2: folds in the independent paper review (key de |
| `dev-repomigration` | 10-14 | januscolla | 1 | dev-repomigration: carried over from creaite-history cdfef7cd (14-10-2 |
| `edit-ai-proposal` | 10-17 | januscolla | 1 | Proposal only (not applied): combined edit_ai.py for ai-117 on the v2. |
| `editor-120-121-int` | 10-16 | januscolla | 15 | Fix CI: test_prep_shape switches the plain AI place on (built and off  |
| `editor-120-links` | 10-16 | januscolla | 2 | #120: link form over a select-all; renamed locals that clashed with pa |
| `editor-121-links-plain` | 10-16 | januscolla | 5 | #121: two local names renamed so the dashboard split check passes (hit |
| `editor-122c-item-links` | 10-16 | januscolla | 5 | Editor bar test: the item button is shared by both profiles |
| `editor-133-plain` | 10-16 | januscolla | 3 | #133: v2.2.0 hand check for an edited Draft email pasted into Outlook |
| `editor-134-chrome` | 10-16 | januscolla | 2 | #134: the capture drawer gets the selection bar (Improve, Structure, A |
| `email-153-sent` | 10-16 | januscolla | 6 | I sent it: Help and hand check say a decision's line goes into Reasoni |
| `email-153-sent-r` | 10-16 | januscolla | 7 | I sent it review fixes: Draft email wording in Help and the peek label |
| `email-153-sent-r2` | 10-17 | januscolla | 7 | Rename sentLine's local who to whom (the module-imports check reads wh |
| `esc-161` | 10-16 | januscolla | 1 | #161: one Esc closes an item's peek and clears its highlight in Review |
| `first-page-speed` | 10-15 | insyncalan | 1 | Search index: a short pause after each file and PDF page in the server |
| `fix-lost-click` | 10-15 | januscolla | 2 | Lost click: tsc-clean, 900 px variant of the regression test (#85) |
| `handcheck-palettes` | 10-17 | januscolla | 1 | Hand checks (v2.1.0): the judgement sheets use TEST_PALETTES (creaite  |
| `handcheck-v210` | 10-17 | januscolla | 1 | v2.1.0 hand checks: Results table from handcheck.py on v210-guard f9e9 |
| `handcheck-v210-rc5` | 10-17 | januscolla | 1 | v2.1.0 hand checks: Results table from handcheck.py on v210-rc5 0c2160 |
| `handchecks-v210` | 10-16 | januscolla | 2 | v2.1.0 hand checks: checks 75 to 121 for the other v2.1.0 items, expec |
| `handchecks-v232` | 10-18 | insyncalan | 1 | Hand checks for 2.3.2: test_v232.py automates the three checks (hover  |
| `handchecks-v251` | 10-19 | insyncalan | 1 | Hand checks for 2.5.1 (#212): test_v251.py and the v2.5.1 sheet for #2 |
| `handchecks-v251b` | 10-19 | insyncalan | 2 | Hand checks for 2.5.1: lines 23 to 35 for #240 (Work filter panel), #2 |
| `handchecks-v260` | 10-20 | insyncalan | 3 | Hand checks 2.6.0: notes only where they hold on a pass, unused import |
| `harness-timeout` | 10-17 | januscolla | 1 | Test harness: hard timeouts on Chrome start, DevTools calls and /json, |
| `hc260-judgement-list` | 10-21 | insyncalan | 2 | 260 judgement list: check 82 is a hand rename (the Health rename card  |
| `hc260-judgement-list-fix` | 10-21 | insyncalan | 2 | 260 judgement list: check 82 is a hand rename (the Health rename card  |
| `held-bash-fix` | 10-15 | januscolla | 1 | Held runs: tracker.py validate only on a file whose real path is in sy |
| `help-158a` | 10-17 | januscolla | 14 | Help: Notes say a note is saved about two seconds after you stop typin |
| `intake-179` | 10-17 | januscolla | 1 | Intake step 1 (#179): one queue, one decision per row, fewer buttons |
| `intake-179-fix` | 10-17 | januscolla | 4 | Intake (#179) review fixes: one age rule with Review, scoped quiet but |
| `jarvis-wip-v253-g` | 10-21 | januscolla | 3 | WIP archive: Jarvis old local merges (v253-g), superseded by the 2.5.3 |
| `notes-119-proposal` | 10-17 | januscolla | 2 | Proposal only (not applied): the live_server.py half of #119's notes a |
| `notes-136-r` | 10-17 | januscolla | 2 | #136: real-Chrome tests for the inert page, the Tab trap, Cmd/Ctrl+Shi |
| `notes-175-design-r3` | 10-17 | januscolla | 2 | #175 design r3: editor-level undo and redo for Notes (autosave never r |
| `notes-175-guarded-proposal` | 10-17 | januscolla | 1 | #175 guarded proposal r3: the Activity fold, 30-minute cap and old-dra |
| `notes-175-proposal` | 10-17 | januscolla | 1 | #175 proposal: notes autosave follow-up (session cap 30 min, one Activ |
| `notes-175-proposal-r2` | 10-17 | januscolla | 1 | #175 proposal: notes autosave follow-up (session cap 30 min, one Activ |
| `notes-autosave-119-srv` | 10-17 | insyncalan | 3 | #119 page: Notes save by themselves 2 s after the last key (editing-se |
| `notes-autosave-page` | 10-16 | insyncalan | 12 | #119 page (review round 2): reopening the open note while it is fetche |
| `notes-autosave-server-drafts` | 10-15 | insyncalan | 1 | #119: Notes keep no draft: the draft route, its files and the stale-dr |
| `p260-e` | 10-20 | insyncalan | 3 | #232 E1 round 6 (tracker proposal): the put-back never replaces (hard  |
| `pm-254-docs` | 10-22 | januscolla | 4 | 2.5.4 sheet: check 4 notes the fixed item is approvable again |
| `pm-260-docs` | 10-22 | januscolla | 2 | 2.6.0 notes: Find work items sits under Intake |
| `pm-262-docs` | 10-24 | januscolla | 2 | 2.6.2 notes and hand checks: wording nuances from the code check |
| `proposal-186` | 10-20 | insyncalan | 6 | #186 review follow-ups: tests that see the bar, help quotes, the selec |
| `proposal-262` | 10-20 | insyncalan | 10 | #262 review fixes: VIP in the selection, HTML inside IDs and names, no |
| `proposal-263` | 10-20 | insyncalan | 11 | #263 review fixes: a non-text field refused, the VIP selection pinned, |
| `rail-139-hover-flyouts` | 10-16 | januscolla | 1 | Rail hover flyouts on Projects, Work and More (#139): one shared hover |
| `rail-139b` | 10-16 | januscolla | 2 | Rail flyouts (#139 review): long project names cut with an ellipsis an |
| `rc2-globals` | 10-17 | januscolla | 2 | dashboard.html rebuilt with the globals list |
| `reopen-instant-148` | 10-16 | insyncalan | 2 | ask creaite reopen (#148): test names, node-identity check, spec |
| `reviewkit-253` | 10-21 | insyncalan | 1 | Review kit refreshed for 2.5.x: refusals are HELD not LEAK, 13 stale p |
| `reviewkit-26` | 10-21 | insyncalan | 2 | Review kit for 2.6: group k26, 24 probes (Draft email AI bar #186, cal |
| `reviewkit-26b` | 10-21 | insyncalan | 3 | Review kit: probe k26-b-idpass (a numbered ID label then a password wo |
| `reviewkit-26c` | 10-22 | insyncalan | 4 | Review kit: group k254, five probes for what 2.5.4 changed (#277, #282 |
| `reviewkit-26d` | 10-23 | insyncalan | 5 | Review kit: k26-b-outputs plants its meeting on the pinned CREAITE_NOW |
| `run-tools-explicit` | 10-15 | januscolla | 4 | Every run kind names its built-in tools (--tools allow list per kind;  |
| `run-usage-guarded-proposal` | 10-17 | januscolla | 2 | Run usage monitor, guarded part as a proposal only: live_server, reach |
| `run-usage-guarded-proposal-r` | 10-17 | januscolla | 2 | run-usage proposal README: say plainly at the top that the reach.py li |
| `run-usage-guarded-proposal-r2` | 10-17 | januscolla | 3 | Run usage monitor proposal: the hook also records skill names from eve |
| `save-v253-milestone-attention` | 10-20 | januscolla | 2 | #251: All items gains a Milestone filter; Today's Open all n in Work u |
| `save/first-page-speed-r2` | 10-15 | insyncalan | 1 | Search index: a short pause after each file and PDF page in the server |
| `save/fix-lost-click` | 10-15 | insyncalan | 1 | WIP #85 lost click: local edits kept, not for push (Team Stark owns #8 |
| `save/search-indexing-note` | 10-15 | insyncalan | 2 | Search: a quiet line when the server is still indexing (#95) |
| `scratch-hc260-183` | 10-20 | insyncalan | 11 | #183 round 2: wrap the over-long route line so check.py is OK with bot |
| `scratch-hc260-241` | 10-20 | insyncalan | 1 | scratch: mutation proof for 51 and 53 |
| `sprint-comms` | 10-15 | januscolla | 4 | SPRINTCOMMS (Jarvis): frozen; the board replaces it, and the teams wor |
| `sweep-from-today-146` | 10-16 | insyncalan | 1 | Sweep reads the calendar from today; saved past days are kept as they  |
| `team-stark-250-readorder` | 10-24 | januscolla | 1 | #250 read order: transcript reads are written only at finish(), wider  |
| `tests-178` | 10-17 | januscolla | 3 | Tests #178: milestone_data follows the test clock; debug-log diagnosti |
| `tests-desktop-900` | 10-15 | januscolla | 2 | Restore dev/handchecks v1.9.4 and v1.9.5 from main (branch is dev/test |
| `today-band-138-147` | 10-16 | insyncalan | 1 | WIP #138 weekend days in the day band (stopped: the day-band group is  |
| `v195-cdp-resize` | 10-15 | januscolla | 1 | Tests: cdp.Browser.resize waits for the new size and two frames (#84) |
| `v195-design-scale` | 10-15 | januscolla | 1 | v195-design-scale: carried over from creaite-history 56a6972e (14-10-2 |
| `v195-dialogs-main` | 10-15 | januscolla | 2 | Merge v195-dialogs-reach (#88) |
| `v195-dialogs-reach` | 10-15 | insyncalan | 1 | Shared behaviour test reaches #boardDlg, #llDlg and #searchPrev (plan  |
| `v200-polish-a` | 10-15 | januscolla | 2 | v2.0.0 polish A (1): the AI bar's menu opens upward when there is more |
| `v200-polish-b` | 10-15 | januscolla | 3 | v2.0.0 polish (2): the AI bar sits above the selection when there is r |
| `v220-int-gate2` | 10-17 | insyncalan | 20 | Regenerate dashboard, globals and guides after links-guard fix |
| `v250-232a-harden` | 10-19 | januscolla | 4 | #232-A hardening: review of p250-a (findings with file:line) |
| `v250-232b` | 10-19 | januscolla | 2 | 232-B (reference, superseded by Team Cap's p250-b): proposal row, acti |
| `v250-232b-harden` | 10-19 | januscolla | 1 | 232-B hardening: fail-first tests against p250-b (routine wording, inv |
| `v250-mdpath` | 10-19 | insyncalan | 1 | A Markdown picture line can't pull an outside file into a Word export  |
| `v250-pagefix` | 10-19 | insyncalan | 3 | v2.5.0 page subset: a logo drawn as its name (Firm, Client, a partner' |
| `v250-sbsfix2` | 10-19 | insyncalan | 1 | Match internal for every section: copy only the client report's own se |
| `v251-properties` | 10-19 | insyncalan | 2 | Client output: the property list for the export path (25 properties wi |
| `v251-reviewkit` | 10-19 | insyncalan | 2 | Client output: the review kit (66 probes, one runner, checklist of the |
| `v251-snapshot-design` | 10-19 | januscolla | 1 | dev/proposals/client-output-snapshot.md: design for the v2.5.1 structu |
| `v252-check09` | 10-19 | januscolla | 1 | test_word_export_227 check 9: reach.py's approved report refusal (6249 |
| `v252-handchecks` | 10-20 | januscolla | 3 | test_v252: import unittest for the struck check 16 |
| `v252-usage` | 10-19 | januscolla | 3 | #238: proposal for live_server.py (daily context-size line, POST /api/ |
| `v253-defects-261-260` | 10-20 | januscolla | 1 | #261: minutes approve after rejecting some or all of their items |
| `v253-handchecks` | 10-21 | insyncalan | 1 | dev/tests/handchecks/test_v253.py: 2.5.3 hand checks from Natasha's dr |
| `v253-intake-process` | 10-20 | januscolla | 5 | #264 R1 README: the review's delta mutants against the R1 tree |
| `v253-milestone-attention` | 10-20 | januscolla | 1 | #251: milestone rows in Today's Needs attention |
| `v253-milestone-attention-2` | 10-20 | januscolla | 2 | #251: All items gains a Milestone filter; Today's Open all n in Work u |
| `v254-280` | 10-21 | januscolla | 1 | WIP: autosave |
| `v26-276` | 10-21 | januscolla | 1 | WIP: autosave |
| `v26-291-walk` | 10-22 | januscolla | 1 | #291 Tier 1: live-app walk of the plain words on line 4 (79 offenders, |
| `v26-295` | 10-22 | januscolla | 1 | #295: the avatar takes More's place at the foot of the sidebar |
| `v26-295-2` | 10-22 | januscolla | 2 | #295: no rail flyout opens beside the avatar menu |
| `v26-archive-name-proposal` | 10-20 | januscolla | 10 | #252: no rename and no migration: Health's offer, propose.py old-archi |
| `v26-draft-delivery` | 10-19 | januscolla | 9 | #183: proposal README records Alan's markup decision and what stays a  |
| `v26-draft-delivery-fix` | 10-20 | insyncalan | 11 | #183 round 2: wrap the over-long route line so check.py is OK with bot |
| `v26-e1-rebased` | 10-21 | insyncalan | 2 | #232 E1 rebased: check.py clean (pipe check in its own helper), README |
| `v26-help-text` | 10-20 | januscolla | 1 | Help: the 2.6 items in plain words (#246 #247 #248 #241 #183 #250 #97) |
| `v26-intake-plan` | 10-19 | insyncalan | 1 | Intake (#232, v2.6): the build plan against the 19-10 locked mockup (1 |
| `v26-line` | 10-21 | januscolla | 1 | WIP: save all work (uncommitted changes at pause) |
| `v26-review-fixes-2` | 10-21 | januscolla | 1 | WIP: invite_clean.scrub fails closed on letter-only key values (Cap HI |
| `v26-v260-fix` | 10-22 | januscolla | 1 | v26-v260-fix: test_v260 follows #232 C2 (go('review')/go('inbox') land |
| `v261-307-identity-tests` | 10-23 | insyncalan | 1 | Tests: #307 identity and fix-pass checks (10 hand checks, red on line2 |
| `v261-307fix2` | 10-23 | januscolla | 30 | 307b: a rejection that still files the transcript is not an approved m |
| `v261-307h2` | 10-23 | januscolla | 18 | 307h2: held-editor test stub passes other routes through (guardFresh r |
| `v261-asrace` | 10-23 | januscolla | 2 | Lost clicks on a Mac: the boot status read is awaited by settle_boot ( |
| `v261-capa` | 10-23 | januscolla | 54 | v261-capa: reach.diff line within the limit, _clean split (complexity) |
| `v261-chainfix-goldens` | 10-23 | januscolla | 1 | Goldens after the chain: today and settings-health with the 300 routes |
| `v261-chaintests` | 10-23 | januscolla | 10 | Tests: re-record writer pins with item_events (work-item-history chain |
| `v261-gate3` | 10-23 | januscolla | 57 | Fingerprint ignores the engine-filled raised (an apply of another item |
| `v261-gatefixes` | 10-23 | januscolla | 51 | Merge origin/v261-307fix2 (final 9ac9cc0f) into v261-gatefixes |
| `v261-gatelabel` | 10-23 | januscolla | 10 | Snapshots: the server reads the login agent from a folder of its own,  |
| `v261-gateui` | 10-23 | januscolla | 15 | cdp click: inset in a helper (complexity limit) |
| `v261-h1m1-fix` | 10-23 | insyncalan | 52 | WIP, UNTESTED BEYOND test_reextract: fix drafts for H-1 (reextract hol |
| `v261-inode-gap` | 10-22 | januscolla | 1 | 2.6.1 proposal #261: the inbox remove holds the file open through the  |
| `v261-intake307-tests` | 10-23 | insyncalan | 1 | Tests: Intake reliability pass (#307): 26 browser checks for every Int |
| `v261-intake307-tests2` | 10-23 | insyncalan | 2 | Tests: #307 c43 accepts the new 'Not drafted yet' wording on bcc008f5  |
| `v261-known307` | 10-23 | januscolla | 3 | Known text: reworded for the corrected cause (card shifts content; no  |
| `v262-183` | 10-23 | januscolla | 12 | Merge origin/v26-draft-delivery-fix into v262-183 (#183 onto v261-line |
| `v262-183b` | 10-23 | januscolla | 16 | #183: popup test reads the register (PERS is not global on release2),  |
| `v262-183h` | 10-23 | januscolla | 19 | #183: README, RULES-FOR-ALAN item 6 and the rules diff say the hook is |
| `v262-183r` | 10-23 | januscolla | 17 | #183 rules: L3 wording describes only the built emails (no client-repo |
| `v262-chain` | 10-23 | januscolla | 5 | GUARDED-2.6.2.md: test count |
| `v262-discard-undo` | 10-23 | januscolla | 2 | test_record_commands: Discard's Undo is a record command once reach.py |
| `v262-discard2` | 10-23 | januscolla | 3 | Discard's Undo: split the restore check, tidy for check.py |
| `v262-f1` | 10-23 | januscolla | 2 | f2 README: sortkey rebased note |
| `v262-follow` | 10-23 | januscolla | 4 | test_follow_words_262: drop an unused import |
| `v262-followb` | 10-23 | januscolla | 4 | test_follow_words_262: drop an unused import |
| `v262-parked` | 10-23 | januscolla | 1 | PARKED.md: shared-database work (F1, F2, F3) paused by Alan, branches  |
| `v262-small` | 10-23 | januscolla | 5 | 2.6.2 C: --expect diffs within the complexity, docstring and line limi |
| `v263-338` | 10-24 | januscolla | 6 | #338: restore OneDrive-unreachable clause and 'one request at a time'; |
| `v263-notes` | 10-24 | januscolla | 1 | Draft 2.6.3 plain release notes, hand-check sheet and test_v263.py |
| `v264-f3` | 10-23 | januscolla | 7 | F3 README: Alan adopted all eight recommendations (23-10-2026) |
| `v264-sim` | 10-23 | januscolla | 4 | v264-sim: settled F3 re-run results, skills text diff, README updates |
| `wip-save/choose-project-204` | 10-21 | insyncalan | 1 | WIP save of the worktree choose-project-204 (Alan: save all work, 21-1 |
| `wip-save/email-153-fix5` | 10-21 | insyncalan | 1 | WIP save of the worktree email-153-fix5 (Alan: save all work, 21-10-20 |
| `wip-save/fix-lost-click` | 10-21 | insyncalan | 2 | WIP save of the worktree fix-lost-click (Alan: save all work, 21-10-20 |
| `wip-save/scratch-hc260-183` | 10-21 | insyncalan | 12 | WIP save of the worktree hc260-183 (Alan: save all work, 21-10-2026 09 |
| `wip-save/scratch-hc260-232` | 10-21 | insyncalan | 4 | WIP save of the worktree hc260-232 (Alan: save all work, 21-10-2026 09 |
| `wip-save/scratch-hc260-236` | 10-21 | insyncalan | 1 | WIP save of the worktree hc260-236 (Alan: save all work, 21-10-2026 09 |
| `wip-save/scratch-hc260-241` | 10-21 | insyncalan | 2 | WIP save of the worktree hc260-241 (Alan: save all work, 21-10-2026 09 |
| `wip-save/scratch-hc260-245` | 10-21 | insyncalan | 1 | WIP save of the worktree hc260-245 (Alan: save all work, 21-10-2026 09 |
| `work-144-cols` | 10-16 | januscolla | 2 | Work board: corrupt remembered column widths are dropped on load, neve |

## Group A: KEEP (66)
| Branch | Tip | Author | Commits ahead of main | Last commit |
|---|---|---|---|---|
| `dev-cleanup-rogue-md` | 10-24 | januscolla | 2 | dev: archive 15 finished handover and answer notes |
| `dev-test-speed` | 10-25 | januscolla | 6 | dev speed: clone the populated vault for test_reports and test_dashboa |
| `dev-test-speed-vault` | 10-25 | januscolla | 2 | dev speed: per-class template vault, per-test clone (vault_clone.py) i |
| `readme-drop-first-ten` | 10-25 | januscolla | 2 | README: remove the pilot users badge |
| `team-cap-goldens-266` | 10-25 | insyncalan | 5 | team-cap-goldens-266: goldens pictures re-shot for the 2.6.6 candidate |
| `team-cap-tests-266` | 10-25 | insyncalan | 76 | test: inbox_meetings rows for confidential meetings, behaviourally (#3 |
| `team-cap-tools` | 10-24 | insyncalan | 3 | team-cap-tools: smoke264, post-release probes for the closed 2.6.4 ite |
| `team-cap-usage-87` | 10-24 | insyncalan | 3 | BL-343 phase A: anonymous default laptop label, 3.9-safe timestamps, n |
| `team-cap-v262-handchecks` | 10-23 | insyncalan | 1 | Hand checks for 2.6.2: eleven checks (F1, emit, discard Undo, follow,  |
| `team-cap-v262-handchecks-2` | 10-23 | insyncalan | 2 | Hand checks: F1 and #250 move from 2.6.2 to 2.6.3 (test_v263.py, check |
| `team-cap-v262-handchecks-3` | 10-23 | insyncalan | 4 | Hand checks: #321 check drops the 320 px block (Alan's rule of 15-10:  |
| `team-cap-v262-handchecks-4` | 10-24 | insyncalan | 5 | Hand checks: check 11 for #312 (Your profile card and the first-run Ab |
| `team-cap-v264-handchecks` | 10-24 | insyncalan | 1 | v2.6.4 hand checks: test_v264.py (27 checks, 7 expected failures for T |
| `team-cap-v264-handchecks-2` | 10-24 | insyncalan | 3 | v2.6.4 hand checks: brought up to v264-line c62ff35b (#334 off by defa |
| `team-cap-v264-notes` | 10-24 | insyncalan | 2 | Release notes 2.6.4: Review page refresh after a rename (#346) |
| `team-cap-v264-notes-2` | 10-24 | insyncalan | 4 | Release notes 2.6.4: Milestones singular fixed (known issue gone), #35 |
| `team-cap-v264-sheet` | 10-24 | insyncalan | 4 | v2.6.4 hand-check sheet: finished against the plain release notes (#35 |
| `team-cap-v264-sheet-2` | 10-24 | insyncalan | 6 | v2.6.4 hand checks: H1 now a plain check, check 31 for #351 b (past da |
| `team-cap-v264b-handchecks` | 10-24 | insyncalan | 1 | 2.6.4 hand checks: check 31 follows the Intake waiting-tail fold (#340 |
| `team-cap-v264b-handchecks-2` | 10-25 | insyncalan | 3 | 2.6.4 hand checks after 2.6.4b (72de4a6a): checks 5 and 34 plain, chec |
| `team-cap-v265-sheet` | 10-25 | insyncalan | 2 | 2.6.5 hand-check sheet and test: the 36 checks of 2.6.4 (35 and 36 now |
| `v261-line3` | 10-23 | januscolla | 6 | Fingerprint ignores the engine-filled raised (an apply of another item |
| `v261-release` | 10-23 | januscolla | 51 | Merge origin/v261-307fix2 (final 9ac9cc0f) into v261-gatefixes |
| `v262-line` | 10-24 | januscolla | 4 | Wrap the last long docstring line in draft_delivery.py |
| `v265-341` | 10-25 | januscolla | 6 | #341: plain structure checks for the 2.6.5 look-and-feel items (no bro |
| `v265-344-snapshot-tool` | 10-24 | januscolla | 1 | #344 design-system snapshots: no review page; gallery.html and blank.h |
| `v265-347` | 10-25 | januscolla | 3 | #347: test wording follows tightened skills.diff |
| `v265-358-build` | 10-25 | januscolla | 12 | #358: Found N counts new items only, not updates (fixture and mutant) |
| `v265-358-final` | 10-25 | januscolla | 7 | #358 final: fourth-review fixes in the note (MEDIUM-A, LOW-A to D) |
| `v265-358-note` | 10-24 | januscolla | 2 | 358: design note wording |
| `v265-358-note2` | 10-24 | januscolla | 3 | 358: design note revised after Cap's findings (H1, M1 to M6, L1 to L6) |
| `v265-358-note3` | 10-24 | januscolla | 4 | 358: design note, third pass after Cap's re-check (M-A, M-B, M-C, L-A, |
| `v265-358-note4` | 10-24 | januscolla | 5 | #358 note4: third-review fixes (live node inside chat, Close the day r |
| `v265-362` | 10-25 | januscolla | 1 | #362: a project code in the meeting title always beats the remembered  |
| `v266-328-build` | 10-25 | januscolla | 5 | #328: the match chip (Matched, Likely, Not sure) with its reason, proj |
| `v266-328-note` | 10-25 | januscolla | 1 | #328 first step: calendar project matching finding and design note |
| `v266-339` | 10-25 | januscolla | 4 | #339: panel_kind routing patch, queue call site, plain 409/400 sentenc |
| `v266-341fix` | 10-25 | januscolla | 51 | #341 item 8 test: a .vtt List row is one line (intended; the meaning i |
| `v266-341fix2` | 10-25 | januscolla | 61 | #341 (Jarvis): the Intake Open source link sits at the right of the ce |
| `v266-347-fixes` | 10-25 | januscolla | 4 | #347 fixes (Cap's review): H2 retained-rules test follows the 347 word |
| `v266-358fix` | 10-25 | januscolla | 24 | #358 M2: an update-only check no longer ends as nothing new (mcFound c |
| `v266-358prop` | 10-25 | januscolla | 58 | #358: proposal to store the mail-check flag on the saved reply (docs o |
| `v266-checkfix` | 10-25 | januscolla | 24 | v266 check fixes: plural name clash, FileFacts compact prop type, spar |
| `v266-digits` | 10-25 | januscolla | 59 | #358: mcIsAsk reads with the u flag (digits, word edges, code points,  |
| `v266-fix358b` | 10-25 | januscolla | 48 | #358: mcIsAsk uses the server's own words (copy of PANEL_SWEEP_WORDS), |
| `v266-fixprep` | 10-25 | januscolla | 50 | #362: no project-named one-pager buttons in the Prep popup for a confi |
| `v266-line` | 10-25 | januscolla | 57 | Merge branch 'v266-341fix' into v266-line |
| `v266-merge` | 10-25 | januscolla | 71 | Merge origin/v264b-release (9d0bd4d6, the 2.6.5 leak backport round 2) |
| `v266-prephdr` | 10-25 | januscolla | 59 | #362: wrap a long comment line |
| `v266-release` | 10-25 | januscolla | 74 | Note drawer: a resumed meeting draft with no project never guesses one |
| `v266-resume` | 10-25 | januscolla | 74 | Note drawer: a resumed meeting draft with no project never guesses one |
| `v266-sec358` | 10-25 | januscolla | 33 | #358: globals.json lists mcIsAsk (rebuilt) |
| `v266-sec362` | 10-25 | januscolla | 31 | #362 security review: a confidential meeting gets no project on any pa |
| `v266-ver` | 10-25 | januscolla | 24 | 2.6.6: VERSION, plain notes, What's new, guides, hand-check sheet and  |
| `v266-withmain` | 10-25 | januscolla | 76 | test_minutes_export_choice polls for the exported file instead of trus |
| `v267-328` | 10-25 | januscolla | 82 | #328: Process all ready runs only Matched or remembered meetings; Like |
| `v267-328b` | 10-25 | januscolla | 104 | #328: the two source-text sensitivity tests follow the inbox_meetings  |
| `v267-339` | 10-25 | januscolla | 76 | #339 round 3: on the 2.6.6 base; per-diff landing, behaviour tests, ru |
| `v267-339b` | 10-25 | januscolla | 77 | #339 round 4: calendar-route re-cut (complexity helpers, refused queue |
| `v267-339c` | 10-25 | januscolla | 78 | #339 round 5: follow outside the start lock, refused queued refresh ke |
| `v267-339d` | 10-25 | januscolla | 104 | #339: the page draws a typed refresh as a plain run only if the server |
| `v267-347` | 10-25 | januscolla | 79 | Merge branch 'v266-release' into v267-347 |
| `v267-guard-summary` | 10-25 | januscolla | 98 | v267: retained-rules test follows the 339 sentence; one-page summary o |
| `v267-line` | 10-25 | januscolla | 97 | Merge branch 'v267-339' into v267-line |
| `v267-line2` | 10-25 | januscolla | 103 | Merge remote-tracking branch 'origin/v267-guard-summary' into v267-lin |
| `v267-line3` | 10-25 | januscolla | 106 | Merge branch 'v267-339d' into v267-line3 |
