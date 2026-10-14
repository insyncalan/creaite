# Sprint board

State on **10-10-2026** (every v1.3.0 sprint merged; worktrees removed), checked against `git` (merges, worktrees, commits ahead and behind `main`). Update this file whenever a sprint starts or merges; the briefs hold the plans, this holds where each one stands. A "worktree" is the separate folder a sprint is built in (`git worktree list` shows them).

## Merged into `main`

| Sprint | Items | Merged | Notes |
|---|---|---|---|
| `sprint-onedrive-projects` | BL-85 | 08-10 | creaite 1.1.0 |
| `sprint-permissions` | BL-93, BL-96, BL-100, BL-86 | 09-10 00:51 | worktree removed |
| `sprint-debug-log` | BL-102 part 1 | 09-10 00:58 | worktree removed |
| `sprint-sweep-alerts` | BL-97, BL-99, BL-98 | 09-10 01:54 | worktree removed |
| `sprint-pages` | BL-87, BL-88, BL-89, BL-95, BL-91, BL-90 part 1 | 09-10 09:54 | follow-up test `258b086` merged 09-10; worktree removed |
| `sprint-4a` | release hygiene, Clear day (BL-104), the Work board (BL-103) | 09-10 10:31 | worktree removed |
| `sprint-timezone` | BL-107 meeting times in the laptop's time zone | 09-10 | worktree removed |
| `sprint-debug-log-2` (stage A) | BL-102: every script run, the live server and the dashboard log; Settings › Diagnostics | 09-10 (`242e15c`) | worktree removed |
| `sprint-4b` | the deny rules retired and Ask creaite's full read access, BL-42 phase 3 loading transcripts, the transcript highlight (BL-104), BL-101 project names, v1.2.0 basics | 09-10 14:02 (`828ea5d`) | not published; VERSION is 1.2.0 and the notes grow with each later merge. The real check of transcript loading is in Alan's live vault after release. `main` is 12 commits ahead of `origin` (not pushed) |
| `sprint-chat-sweep` | BL-110 sweep rebuilds the dashboard and the open page refreshes itself, BL-109 markdown in the chat, BL-108 times on bubbles | 09-10 (`a250e23`) | Merged without the full suite (Alan asked for the merge while other sessions were running theirs); its own tests and the chat-related files passed. Worktree removed |
| `sprint-backup-folder` | BL-112 backups to `_Portfolio/99 System/creaite backups`; `99 System` always skipped | 09-10 (`000d24c`) | Merged at Alan's request after bringing `main` in. Its related tests pass; the full suite on the merged branch had 10 failing files, 9 of which fail the same way on `main` before this merge (the search, milestone, editing, side-panel, current-state, work-filter, workstream, project-name and pages dashboard tests: a page script error since chat-sweep), and the tenth (`test_debug_log_wiring.py`) passes alone. Worktree and branch removed. |
| `sprint-5` | one schema migration (BL-53, BL-50, BL-90 part 2, BL-94), BL-53 decisions needed, the steering one-pager (BL-92), the "ask creaite" lower-case pass (BL-105) | 09-10 (`8b2b34b`) | Merged at Alan's request after `main` had been brought in four times (sprint-pages, 4b, chat-sweep, backup-folder), the lower-case pass re-run on chat-sweep's text, and the conflicted files' tests (help, the guides, the name check, the BL-112 backup test) run. **No full suite on the merged state:** the last attempt (partial, three files at a time under load) had `test_pages`, `test_current_state_live` and `test_work_filters_live` failing, which are among the nine dashboard files that already fail on `main` since chat-sweep; they were not re-run alone. The sprint's own files (`test_schema_sprint5`, `test_decisions_sprint5`, `test_decisions_dashboard`, `test_steerco`, `test_steerco_dashboard`, `test_ask_creaite_name`) passed on the branch and on `main` after the merge. Worktree `../creaite-sprint5` removed, branch deleted. Hand-offs became **BL-113** |
| `sprint-recode` | BL-111 recode a project: its code and name everywhere, with exact undo (FR-104) | 09-10 | Brought Sprint 5 in and extended the registry for `promises`, `links`, `item_labels` and `decisions.replaces`. Full suite once: 55 of 56 passed, the other a Chrome start-up flake that passed alone. Worktree removed |
| `sprint-debug-log-2b` | BL-102 stage B (the working scripts write to the debug log; rules text, Help, FR-98), BL-113 (meeting prep and the sweep learn decisions needed; FR-109), BL-103's Decisions board (FR-110) | 09-10 | Full suite once, as Alan asked: 59 files, 0 failed (two passes on the same tree; the first stopped at 40 files when its loop was cancelled). Brought `main` in at the merge (BRD and backlog renumbered: 4b took FR-105 to FR-108). Worktree removed |
| `sprint-exec-state` | BL-106 executive-ready Current state: the facts sheet, the executive style guide, Audience and Length, notes under the draft, Make it executive, decisions needed in Asks, the weekly and client skills (FR-111) | 09-10 (`9f2ebc8`) | Full suite: two clean runs (59 files each), then once more after the final `main` merge-in: 63 of 63 passed. The feature has not been read on real projects yet (Alan's acceptance step). Not pushed. Worktree and branch removed |
| `sprint-polish` | the apply defect fix, BL-118, BL-121, BL-116 and 117, BL-119, BL-120, BL-114, BL-122 to BL-124 | 10-10 01:20 (`a7d4ae3`) | Full suite on the branch: 67 of 69. `test_cell_edit` (timing under load) fixed after the run and passes alone; `test_sweep_alerts` VipEverywhereTests (2) fails the same on the base commit, so not this sprint's. No conflicts at the merge. Worktree removed |
| `sprint-prep-files` | BL-127 the Week ahead drops report lines, BL-126 the meeting prep page, BL-135 Agendas in Files | 10-10 01:45 (`fdc65a5`) | Full suite on the branch: 64 of 65 (the date-fragile VIP test, fixed on main in `b4a90e6`). Conflicts in BUILD, the 1.3.0 notes and the generated guide, resolved; the affected files' tests passed on a clean copy of main. Worktree removed |
| `sprint-settings` | BL-115 the Settings page: categories, search, one list of sections, Advanced | 10-10 (`sprint-settings` at `b113889`) | Full suite on the branch after bringing main in twice: 72 of 72. Clean merge. Two small departures from the agreed plan, in BUILD: Advanced leaves out `files_show_inbox` and `files_show_portfolio` (nothing reads them); the VIP interval, notify and log level stay in VIP alerts and Diagnostics. Worktree removed |
| `sprint-work-views` | BL-128 Display, BL-129 grouping and swimlanes, BL-130 filters, BL-132 empty state, BL-131 saved views and Chase, BL-133 Review triage (stage B with `rejected.reason` and `rejected.duplicate_of`, pre-approved) | 10-10 (`ac772f3`) | Built by a background agent. Full suite: 77 of 79; the two (click timing under load) fixed to wait for their target and passed alone and under load. Clean merge. Alan to walk Work and Review against the mock-ups and check the seven themes |
| `sprint-all-items` | BL-134 the All items tab (merged read model, the tab, a link from the project page), BL-138 People in two tabs | 10-10 (`4b69c4a`) | Built by a background agent; brought `main` in after work-views merged. Full suite: 79 of 80; the one (`test_work_filters_live`, read cells by position) fixed to find columns by heading. Clean merge. Alan to walk All items against frame 7 and check the People tabs |
| `sprint-admin` | BL-140 the permission dead-end, BL-141 ask creaite as the administrator | 10-10 | Built by a background agent; brought `main` in. Full suite 83 of 83. Clean merge. Removed the permission-file run and its cards (not bound to the exact change shown); edited two BL-93 lines in creaite-rules. Open: the hook is tested with a stand-in `claude`, so Alan's hand check 4 (read `~/.ssh/config` is refused) confirms it in real Claude Code |
| `sprint-motion` | BL-136 restrained animation, Stages A to C, with sprint-admin's card | 10-10 (`cf87c0a`) | Built by a background agent; Stage A started early, B and C after work-views and all-items merged, admin's card after admin merged. Full suite on the branch: 84 of 84 |
| `sprint-final` | BL-142 five themes (creaite the default), BL-143 no Live dot, BL-137 Upload Files lists only uploads, BL-139 ask creaite's run badge | 10-10 (`b55b64c`) | Full suite on the branch 85 of 86 (`test_review_triage` timed out under load, passes alone). Worktree removed |
| fixes for 1.3.0 | Quick Capture project list, inline date on the project page, BL-144 Activity item links, milestone description (schema: `milestones.description`), one number sequence per project | 10-10 | Each on its own branch, its tests passing, merged and its worktree removed; the RAID numbering fix is checked by the final full suite |
| `sprint-ux` | BL-146 to BL-157, the UX baseline | 10-10 (`c11bd2f`) | Built by a background agent (resumed after a network drop). Full suite 97 of 98 (`test_dashboard_editing` under load; fixed to ignore the new Edit button and passes). Sweep items BL-165 to BL-169 added to the backlog. Worktree removed |
| `sprint-icons` | BL-158 to BL-161, icons in place of words | 10-10 (`27414a4`) | Built by a background agent. Own tests: test_icons plus 57 files, one pass each (three passed alone after load). Every icon 3:1 or better in all five themes. Alan's look at Work, Review and each page type is a hand check before publishing |
| fixes BL-170, BL-171 | a stale file change stops the apply first; the tests never open Word | 10-10 | Each on its own branch, merged; BL-172 (tests leave vaults behind) logged |
| `sprint-polish-2` | BL-165 to BL-169, BL-172, BL-173 | 10-10 (`a3d04ea`) | Built by a background agent; own tests (19 files) one pass; merged after v1.3.0 was re-tagged; for 1.4.0 |
| `sprint-rail` | BL-162 Current state title, BL-163 the rail, BL-164 Activity search and undo of several | 10-10 (`41774c0`) | Built by a background agent; five additive conflicts with polish-2 resolved (both kept); 12 overlapping files' tests pass on merged main; for 1.4.0 |
| `sprint-peek` | BL-175 toolbar, BL-176 the work item peek, BL-177 Review in the peek | 11-10 (`c2c891a`) | Built by a background agent |
| `sprint-peek-new` | BL-179 new items in the peek, BL-180 errors banner, BL-181 weekend dates, BL-185 cockpit | 11-10 (`eead2a9`) | Built by a background agent |
| fixes for 1.4.0 | the undo of a field changed twice; BL-187 owner suggestions, BL-188 staged changes in every window, the banner beside the chat; stale tests | 11-10 | Each on its own branch, merged |
| `sprint-links` | BL-190 every count opens Work | 11-10 (`417ec50`) | Built by a background agent |
| `sprint-polish-themes` | BL-192 gear, BL-191 rail by right-click, BL-40a to d (Claude, Apple, Retro Arcade, Thermo Scan), colour audit | 11-10 (`a09f647`) | Built by a background agent; nine themes pass contrast; the five existing proven unchanged (50,875 computed styles identical) |
| `ask-quips` | BL-195 ask creaite's office-humour status, steps folded | 11-10 (`dc760c8`) | Built in another session on its own branch |
| `sprint-review-work` | BL-200, BL-198, BL-197 | 11-10 | for 1.6.1 (one release) |
| `sprint-chat-text` | BL-199, BL-201, BL-196 | 11-10 | for 1.6.1 (one release) |
| `sprint-ask-creaite-access` | BL-194 | 11-10 | v1.5.1 |
| `fix-as-proposed` | BL-232 | 11-10 (`7f73d7f`) | for 1.6.1 (one release) |
| BL-235 (direct) | Week ahead priorities, default Urgent (Alan) | 11-10 (`d08ff59`) | left uncommitted by another session; the Settings control is still to build |
| `sprint-login-agent` | BL-243 | 11-10 (`d3ecd83`) | rule paragraph added to creaite-rules.md |
| `tooling-check` (creaite-c1) | check.py ratchet, run_tests --changed/--flaky, Work board split | 12-10 (`80e790c`) | local suite 122 OK; its 8 failures were all main's |
| fix-clear-day-monday, fix-main-tests | main's date-dependent and load-sensitive tests | 12-10 (`22dec45`, `2f07e6c`) | test-only |

## In flight (refreshed 14-10-2026)

v1.9.0, v1.9.1 and v1.9.2 are published (14-10-2026; tags v1.9.0 `d689f89`, v1.9.1 `d011799` and v1.9.2 `9a5ea19`). v1.9.3 (BL-322, BL-323, BL-275) is ready to publish: see **v1.9.3 (ready to publish 14-10-2026)** below; its branches are on `release-193`.

## Planned, not started

| Release | Items |
|---|---|
| v1.9.4 | BL-09 archive and restore whole projects, BL-304 changes appear at once, BL-326 ask creaite shows the ask and the outcome (moved from v1.9.5), BL-327 fast saves, BL-328 the sweep lock, BL-329 one server, BL-330 a remembered chat that's gone. `release-194` (WIP: `test_fast_save`). Team Cap fixes and integrates, Team Stark cuts. Plan: `dev/sprints/v194-release.md` |
| v1.9.5 | BL-324 UI fixes, BL-325 one design scale, BL-333 no scroll past the bottom, BL-334 alerts read the conversation, BL-10 and BL-03 archiving, BL-331 move back an archived report, BL-316 the consistency audit (split by screen between the teams). Team Stark integrates and cuts. Plan: `dev/sprints/v195-release.md` |
| v2.0.0 | BL-301 Notes: A, B, D, E and the Notes server on `v20-base`; C on `v20-capture`; left: D wired into Notes, B's margin ticks, the notes guard change, the `review` snapshot fix, the real-data gate. Plan: `dev/sprints/v200-notes-release.md` |
| v2.1.0 | Reporting (Priority High): BL-335 the weekly report, BL-336 the client report, BL-337 the reporting space and the Reports page, BL-338 the minutes editor, BL-339 retire the meeting hub. Plan: `dev/sprints/v210-reporting.md` |

## Not scheduled

BL-02, BL-06 (after the trial; BL-04 removed 12-10-2026, replaced by BL-224's Chase mode) and BL-331 (move back one archived report; after v1.9.5). BL-113 and the Decisions board (BL-103) are now in `sprint-debug-log-2b`.

**On hold:** BL-313 (plain words; Alan, 14-10-2026, review in `dev/reviews/BL-313-review.md`), BL-40 (more named themes; Alan, 14-10-2026), BL-183 (health evidence and calibration; on hold again, Alan, 14-10-2026, out of v1.9.4), BL-317 (reports you live in; design paused, Alan, 14-10-2026); (Alan, 13-10-2026) BL-59 (minutes edited in Review), BL-60 (the transcript pane), BL-203 (a project as of any day), BL-204 (contact rhythm and 1:1 prep), BL-125 B (links) and C (labels), BL-182 C and D (no one-click reject reasons for now).

**BL-275** (PDF search, pypdf) is in v1.9.3 (Alan, 14-10-2026). BL-09 is in v1.9.4 and BL-10 with the rest of BL-03 in v1.9.5 (Alan, 14-10-2026). **BL-326** (ask creaite shows a run's machine text, a defect) is not scheduled. **BL-276** (.eml search) is in v1.9.0.

## Paused again (Alan, 11-10-2026, late evening): resourcing; resumed 12-10-2026

**12-10 (Alan): full suites now run on GitHub Actions** (the repo is public, so it's free; about 26 min a suite). Sprint branches are pushed, and local runs are single files only.

**Resumed 12-10-2026 (Alan; 266 GB free after his clean-up):** the tooling session (now creaite-c1) rebased its branches onto main 8d22c72 (tooling-check `1f52cf8`, tooling-extras `6c65fa4`, creaite-tooling `bb3c804`, where BL-246 is complete apart from the suite) and is running tooling-check's clean suite at -j 3. Insight (docs, two failures) and portability (BL-241, BL-242, docs) are resumed with one-file test runs only, until that suite ends.


Development is paused while Alan sorts out resourcing. The earlier pause in the evening was for the spend limit; this one is for disk and CPU load. Tonight's disk-full (118 MB free) and load problems came from seven sprints testing at once, with test runs leaving vaults, live servers and Chromes behind (BL-246 and BL-247 fix this). Main is pushed. Every branch below is committed, and no test runner of ours is left running.

**Merged into `main` since the first pause:** the login agent (BL-243, with its rule paragraph in creaite-rules.md); BL-235; BL-232; and test isolation (vaults copy the committed `.claude/settings.json`). In the backlog: BL-244 to BL-247, and creaite-44's BL-234 and BL-242 updates (the repo is public, so Actions minutes are free).

| Branch (worktree `../`) | Built | Left before merging |
|---|---|---|
| `sprint-ui-audit` (`creaite-ui-audit`) `6371ab3` | BL-211 to BL-215, docs, main merged | re-run alone: settings_page, cell_edit, chat_box, activity_undo, dashboard_milestones, chat_and_sweep, reject_reasons, rail_customise (failed under load) |
| `sprint-insight` (`creaite-insight`) `c15435f` | BL-205 to BL-209, main merged; spec and release-note lines | test_settings_page and test_prep_updates failed (not looked at); the rest of the full run; Help, guides, BUILD and FR text; screenshots (script in `dev/sprints/wip-insight/`); delete that folder |
| `sprint-drafts-fields` (`creaite-drafts-fields`) `e74a331` | scaffold, BL-219, BL-222, BL-225, BL-226; main merged | run stopped at 38 of 60 (26 OK, 12 failed, 22 not run). Look first at test_new_vault and test_no_dead_ends (failed fast); re-run the others alone: help, minutes_review, milestones_page, milestone_states, panel_drafts, new_item_peek, pages, review_triage, row_selection |
| `sprint-milestone-ui` (`creaite-milestone-ui`) `9eca053` (WIP) | BL-244: Client is plain and opens by default on a first visit; Internal has a bright `--warn` border and an INTERNAL VIEW pill; test_milestone_ui (4: contrast in nine themes, print) passes; Help text | **test_dashboard_milestones, test_milestones_page and test_side_panel_live fail even alone** (not looked at); test_pages to re-run; BL-245 written, not wired in (`dev/sprints/wip/milestone-ui-bl245-draft.js`); spec, BUILD, notes, guides, screenshots |
| `sprint-portability` (`creaite-portability`) `db7884c` | BL-240 `5aea115`, BL-239 `bce2ec6` (doctor now 25 checks), BL-238 `e6689b5` (17 tests pass); WIP `41bf6c0`: BL-237 wrapper `system/scripts/run` (own tests and escape tests pass), BL-242 matrix (untested) | BL-241 (rules draft in `dev/sprints/wip-portability/`; SETUP, Help, README to write; delete that folder); the full related-file run (reach, permissions, update, doctor, launch); BL-242 needs a run on Actions |
| `sprint-debt-safety` (`creaite-debt-safety`) `dd4d893` | BL-228 A `a91c9e9` (fails closed in review's client_findings and report's project_labels), C (each swallowed exception has a reason or is narrowed; `tracker.connect_or_raise`); BUILD and notes | test_debt_safety passes (14). Re-run: adhoc_docs, admin_card, as_proposed, ask_access, chat_and_sweep, activity_undo, codes, dashboard_milestones (failed during the disk-full period; not looked at) |
| `tooling-check` (`creaite-tooling`, session "tooling", once creaite-41) `61c1d71` | check.py, run_tests.py --changed/--flaky, Work board split; Python 3.9 fix | **not a valid suite result:** 103 of 113 OK, and 10 failed in a burst while the disk was nearly full. Re-run cleanly, then merge first |
| `tooling-extras` (`creaite-tooling-extras`) `25297c7` | BL-228 part B (per-rule ratchets) `b6c7c83`; dev justfile and pyright config | after tooling-check |
| `creaite-tooling` (`creaite-tooling-sprint`) `19f1392` | WIP BL-246: 94 Chrome and 35 quick files; machine-wide flock slots in `/tmp/creaite-chrome-slots`, cap 3, freed when a holder dies; a private TMPDIR per test file, removed at the end | BL-246's tests and docs; BL-247; BL-229 |

**Notes for the record:**
- Several sessions used `pkill` by name tonight (creaite-62 earlier; the tooling session's `pkill -9 -f run_tests.py`), which killed other sessions' runs and probably left some of the orphans. Agents also reported runs "stopped" that were still running (portability, debt-safety, tooling). On resume: stop only by PID, check the working folder, and confirm the process has gone.
- Portability deleted every `creaite-release-*` temp folder, which may have broken another sprint's `test_update` run. Re-run `test_update` before relying on it.
- About 21 `creaite-test-*` vaults are left in `$TMPDIR` with no owner. Remove any not open by a process (`lsof +D`) once nothing is running.

**Resume order:**
1. Re-run tooling-check's suite on a quiet machine (no other runs), then merge it.
2. Merge tooling-extras. Finish BL-246 and BL-247 and merge them early: they make parallel testing safe.
3. Then finish and merge ui-audit, insight, drafts-fields, milestone-ui, portability and debt-safety, at most three testing at once.
4. Then BL-229; drafts-extraction and drafts-writing (after drafts-fields); debt-safety part D; ui-sweep; debt-docs.
5. Release v1.6.1. The push window runs to 16-10-2026 02:04.

## v1.6.1: what is built or being built (Alan, 12-10-2026)

**Scope (Alan, 12-10-2026):** v1.6.1 is everything merged, finished or being built on 12-10 at about 12:30. Sprints not started move to v1.7.0 (below). There is no 1.6.0.

**In v1.6.1:**
- **Merged:**
  - review-work, chat-text, insight;
  - BL-232, BL-235, BL-243 (login agent), BL-251;
  - tooling-check and tooling-extras (BL-228 B);
  - the main test fixes.
- **Being finished:**
  - ui-audit (BL-211 to BL-215);
  - debt-safety (BL-228 A and C);
  - creaite-tooling (BL-246, BL-247);
  - portability (BL-237 to BL-242, BL-248);
  - BL-249 (fix-field-names);
  - BL-250 B and C (fix-history-feed);
  - drafts-fields (the scaffold, BL-219, BL-222, BL-225, BL-226);
  - milestone-ui (BL-244, BL-245, BL-250 A);
  - BL-229 (creaite-c1, the writer split).

**Code health (Alan, 12-10-2026):** branches built before `check.py` merged have their figures accepted once, at merge (`check.py --update-baseline --allow-worse`, with the reason in the commit). The ratchet holds strictly for anything started after it.

**Release steps:**
1. Merge each branch when its Actions suite passes.
2. One full suite on final main, on Actions.
3. Rename `dev/release-notes/1.6.0.md` to `1.6.1.md` and finish the notes; update the BRD and backlog; set VERSION to 1.6.1.
4. Branch `release-1.6.1`, push, publish, then test the zip (fresh, and an update from 1.5.2).

**Estimate:** 12-10-2026, 19:00 to 21:00.

## v1.7.0 (scope approved by Alan, 12-10-2026)

Approved: the sprints below, plus BL-252 and insight's screenshots. BL-231 moves to v1.8.0. BL-234 is unparked: automatic CI (PR and push to main, report-only first), switched on after v1.6.1 ships.

| Sprint | Items | Order |
|---|---|---|
| `sprint-drafts-extraction` | BL-221, BL-218, BL-220, BL-233 (last) | first, beside drafts-writing |
| `sprint-drafts-writing` | BL-223, BL-224, BL-227 | first, beside extraction |
| `sprint-debt-safety` part D | BL-228 D: escaping by default | after the two drafts sprints |
| `sprint-debt-docs` | BL-230 | after BL-229 has merged |
| `sprint-ui-sweep` | BL-216, BL-217, BL-270 (Today header, door icon), BL-273 (the Stage wordmark; Alan), BL-274 (⌘↵ saves and closes every editor, the milestone editor included) | last, over every screen |
| `bl-229` (rest) | BL-229 step 4 and the under-60 target, plus hub_record | non-overlapping parts in wave 1; minutes and build_dashboard parts after the drafts sprints |
| BL-252, BL-234 | ask creaite and grep; automatic CI | wave 1; BL-234 after v1.6.1 ships |
| `fix-small-17` | BL-235 the Week ahead priorities in Settings; BL-252's last part, a count of pipe refusals in Diagnostics (Alan, 12-10-2026) | wave 1, now |
| `sprint-decisions-needed` | BL-210 Decisions needed on Today (Alan, 12-10-2026) | **started 12-10 16:20** from `sprint-drafts-writing` |
| `sprint-ui-sweep` | BL-216, BL-217, BL-273 (wordmark; Retro Arcade and Thermo Scan keep their lettering), BL-274; **BL-270 after escaping-2 merges** | started 12-10 about 21:40 from main, beside escaping-2 (Alan); CSS-first, guided by `dev/sprints/ui-sweep-audit.md` |
| `fix-handcheck-161` | BL-278 to BL-283 (v1.8.0) | **merged 13-10 00:20** (BL-283 added by the Product Manager) |
| `sprint-live-updates` | BL-253 server-sent events, pulse as fallback | started 12-10 about 20:05 from `sprint-ask-flow` (Alan: parallel) |
| `sprint-debt-docs` (part 1) | BL-230 docstrings, every script no open branch is changing | started 12-10 about 20:05 from main |
| `sprint-escaping` (step 1) | BL-228 D: the hostile-text test and the `html` helper only; the conversions wait for the dashboard sprints | started 12-10 about 20:05 from main |
| `fix-docx-writes` (creaite-c1) | BL-271 | started 12-10 about 20:00, while BL-229 wave 2 waits for BL-210 |
| `fix-ask-record-guard` (creaite-c1) | **BL-267 priority security defect:** in ask mode the guard refuses every record-changing subcommand (one list, a test that every subcommand is classified, a doctor count) | started 12-10 about 19:40; ahead of BL-229 wave 2; merges before ask-flow |
| `fix-minutes-approve` | BL-260 point 4: approving a minutes row with no draft is refused (tracker.py and Review) | started 12-10 about 19:40 |
| `bl-265` (creaite-c1) | BL-265 security-pinned split of the guard files (Alan, 12-10-2026) | started 12-10 about 17:20 from main; pauses for BL-229 wave 2 at about 19:00; merges before debt-safety D |
| `fix-doctor-errors` | BL-263 | **merged 12-10 about 20:15 (moved back to v1.7.0 by Alan)** |
| `sprint-ask-flow` | BL-257 queued messages, BL-258 one card that applies on Approve, BL-262 the chat shown at once on reopen, plus BL-259 quips and BL-261 coloured dots (folded in: same lines) | **started 12-10 16:20** from `fix-search-read` (Alan: parallel where clash-free) |
| BL-254 | screen snapshots (golden HTML of every screen of the sample vault) | wave 1, so BL-228 D and ui-sweep run with it; ui-sweep commits its new goldens |
| BL-253 | live updates pushed over server-sent events; the pulse becomes the fallback | after the two drafts sprints, before ui-sweep (it edits the pulse block of `dashboard.html`) |

**Added 12-10-2026 (Alan, the dashboard tooling review):** BL-253 and BL-254 in v1.7.0; BL-231 revised for v1.8.0; BL-255 and BL-256 not scheduled.

**v1.9.1 (Alan, 13-10-2026).** BL-314 ask creaite like the dashboard, BL-321 Today's day arrows never move (moved out of BL-293 so v1.9.0 doesn't wait). Starts after v1.9.0 ships.

**v1.9.2 (Alan, 13-10-2026).** BL-320, BL-315 (rejects in real life: every reject undoable, its reason changeable or turned into an approval) and BL-319 (Today as one home; redesign accepted). BL-320: Settings, calmer, with Health inside (L, on the components; mockups accepted): Essentials and Advanced, changed dots and Reset, Health as a Settings section with Fix it buttons, update.py doing the after-update steps. Any Fix it that runs commands or changes permissions is a guard matter for Alan's direct confirmation.

**v2.0.0: Notes (Alan, 13-10-2026).** BL-301 alone, all five parts. On laptop 2: the Tiptap groundwork is merged (`dev-notes-tiptap`, dev only); the server side is built and **parked** on `v20-notes-server` until v2.0.0 (Alan) (BL-125 A moved to v1.9.0; BL-304 back to the backlog; Alan, 13-10-2026). BL-301 (Alan): A, the one editor (Tiptap, with its beta Markdown extension pinned and the byte-for-byte round-trip gate on every Current state); B, Notes on the project page (`08 Notes`); C, the capture drawer (⌘⇧N), which replaces Quick capture (FR-71); D, AI on selected text in every editor; E, Find updates from a note. Waves, after v1.9.0 ships: (1) A alone, because every editor changes and Tiptap is bundled (vendored JavaScript, pinned); (2) B and C in parallel; (3) D and E. Server-side parts of B, C and E (the `08 Notes` folder, search indexing, notes-sent.json, the rules text) can start early on branches, as v1.9.0's did.

**v2.1.0 (Alan, 13-10-2026): Reporting, Priority High (Alan, 14 and 15-10-2026).** BL-335 the weekly report (L), BL-336 the client report (L), BL-337 the reporting space and the Reports page (M–L), BL-338 the minutes editor, replacing today's minutes (XL), BL-339 retire the meeting hub (S). Team Cap (reports) and Team Stark (minutes, the journey, the hub), after v2.0.0. Plan: `dev/sprints/v210-reporting.md`; phase 1 (data, file format, exports, server) can start now, phase 2 (screens) needs v2.0.0's one editor. BL-313 went on hold (Alan, 14-10-2026).

**v1.9.0: Meeting prep (Alan, 13-10-2026).** BL-286 is the headline, with BL-287, BL-285, BL-264, BL-255, BL-256, BL-293 (Today: move between the calendar's days) BL-295 (Close the day, a guided shutdown), BL-297 (Smarter updates), BL-298 (Draft chase from the peek), and BL-125 A moved in from v2.0.0, all 13-10 by Alan (18 items with BL-305, BL-306, BL-308 and BL-309; BL-304 back to the backlog, Alan, 13-10-2026). BL-125 A stays parked on `v19-promises-data`. The plan:

| Wave | Sprint | Items | Starts | Where |
|---|---|---|---|---|
| 0 (running) | `sprint-prep-server` | BL-286's server and Python side: shaping (C), the stored page, dated reporting, the series and sources (D), the popup's facts (A) | started 13-10 09:15 | laptop 1 |
| 0 (running) | `sprint-csp-report` | BL-255 report-only: hashes of the served page, the report endpoint, the setting | started 13-10 09:15 | laptop 1 |
| 1 | `sprint-preact` | First `dev/COMPONENTS.md`, the component guide, agreed by Alan before anything is built (BL-256's write-up); then BL-256's foundation: Preact with signals vendored and bundled by esbuild, one small component and its test pattern | as soon as BL-231 phase 3 (modules) is on main | laptop 1 |
| 1 | `v19-people-filters` | BL-264 (built on laptop 2, `50125d9`; Actions running; a small Help clash expected with BL-288 part 2) | merge after its suite | laptop 2 |
| 1 | `sprint-portfolio` | BL-285 (Today › Portfolio: description on hover, resizable columns) | after phase 3; beside BL-286 | laptop 2 (DEV2), as `v19-portfolio` |
| 0 and 1 | `sprint-vip-private` | BL-296 in part 2 (Dismiss and Create work item on a followed person's message in Needs attention; the same rows). BL-288 (widened, S): VIP is private, so no VIP label anywhere on screen or in anything creaite writes; VIP keeps working, unlabelled. Part 1 now: reports, Excel, the skills, ASK_PROMPT, help.md. Part 2 after BL-231 phase 3: the dashboard's surfaces (Work, Today, Review, person, Settings › People, Draft email, early warning, the Work filter's name, which Alan approves) | part 1 started 13-10; part 2 after phase 3 | laptop 1 |
| 2 | `sprint-prep-popup` | BL-286 A, B and E, plus BL-287: the 960 px popup, Draft agenda dropdown, full peek; on Preact | after `sprint-preact` and `sprint-prep-server` | laptop 1 |
| 2 | `sprint-prep-page` | BL-286 D's view: Meetings › Prep in the Briefing layout; on Preact | beside the popup | laptop 1 |
| 2 | `sprint-today-days` | BL-293: Today's day line across the saved calendar, swipe and `[` `]` `T` (Help only, never hinted on screen; no hide), past days' follow-up, Prep on any later day (`prep_page.py`, cx-prep, the live server's day check) | after phase 3 and `sprint-prep-server` (both touch `prep_page.py`); beside the popup, which owns `openPrep` (proposed: Scrum Master to confirm) | laptop 1 |
| 0 and 3 | `sprint-close-day` | BL-295 (M): Close the day as a guided shutdown (Catch up with a sweep, Today, Loose ends, Tomorrow), replacing BL-206's card. Server side now (settings `day.catchup_sweep` and `day.catchup_after_minutes`, the catch-up sweep through the run engine, the First thing tomorrow list in `day-closed.json` read by tomorrow's brief), on `sprint-today-days-server`; the card on the modules with Preact after BL-293's screens, since both change Today | server 13-10; card in wave 3 | laptop 1 |
| 0 and 2 | `sprint-smart-updates` | BL-297 (L): mail, Teams and minutes update an existing item instead of raising a new one. Python side now (A the sweep reads expected items; B plain-code matching in extraction.py; C the model's `repeat: same` mark; E date-and-update-only changes routine; review.py retarget; Quality counts), built on `sprint-vip-private` because both change the cx-sweep and cx-minutes skills; D, Review's "Update an existing item instead" picker, on the modules in wave 2 | Python side 13-10; picker after phase 3 | laptop 1 |
| 2 | `sprint-draft-chase` | BL-298 (M): Draft chase from the work-item peek (key C): BL-224's chase for someone else's item, a new help mode for Alan's own, the decision maker for a decision; Copy for Outlook, Copy as text, I sent it records the chase. Peek and drafts modules, `/api/chases`, help.md | after phase 3; after `sprint-prep-popup` if both change the peek | laptop 1 |
| 0 | `sprint-search-eml` | BL-276: saved emails (.eml) in search, standard library only; split from `sprint-search-pdf-eml` (BL-275 stays in the backlog, parked there) | 13-10 | laptop 1 |
| 3 | `sprint-prep-shape` | BL-286 C's screens: the instruction box, the reading, cited notes, the focus list | after the popup | laptop 1 |
| 3 | BL-255 re-hash | the hashes on the bundled script; report-only for a week from its merge before enforcing | after phase 3 | laptop 1 |
| 1 | `v19-pane-marker-fix` | BL-310: the pane splitters ignore a marker inside another HTML comment (laptop 2, built; Actions running) | merge after its suite | laptop 2 |
| 3 | `sprint-panel-sweep` | BL-309 (guard, S): the live server, never the model, recognises "sweep" typed in the panel and starts it under BL-295's `sweep` mode (staging allowed; apply, undo, approve, reject and `propose.py stage` refused; direct writes only to drafts). approved by Alan, 13-10-2026 ("if i type sweep assume it's committed request"; relayed, no separate confirmation wanted) | after `sprint-close-day` (BL-295's mode) is on main | laptop 1 |
| 1 | `sprint-launch-apply` | BL-305 (one launcher per vault: "creaite" and "creaite (dev)" with a DEV-marked icon, side by side; a doctor warning) and BL-306 (a confirmed change applies in one step, BL-258), moved from v1.8.1 to v1.9.0 by Alan, 13-10-2026. Mostly `launch.py`, `doctor.py`, `live_server.py`; can start now | 14-10 | laptop 1 |
| 1 | `sprint-portfolio` (added) | BL-308: the wordmark loses its dashed draft copy (word and saffron bar only; BL-291's contrast rule becomes moot); `dev/reference/logo/` updated to match | with BL-285 | laptop 2 (DEV2), as `v19-portfolio` |
| – | `fix-bl307` | BL-307 (ask creaite's Prep page offer): in v1.9.0, no separate v1.8.1 (Alan, 13-10-2026); merged on main 13-10 | done | Team 1 |
| 1 | `v19-promises-data` | BL-125 A (L, moved in from v2.0.0 by Alan, 13-10-2026), **on laptop 2 (DEV2)**: bring the parked `v19-promises-data` (`daeb42f`) up to main, then its screens (Today, a person, Waiting on) on the modules; the sweep's promises behind `promises.from_sweep`, off | after v1.8.0 ships | laptop 2 (DEV2) |

**v1.9.0 estimate (Scrum Master, 13-10-2026, from today's pace):** done already: the server sides of BL-286, BL-293, BL-295, BL-296, BL-297, BL-298, BL-255 (report-only), BL-288 part 1, BL-276. Left: wave 1 (Preact and COMPONENTS.md, which waits on Alan's agreement; BL-264 on laptop 2; BL-285, BL-287, BL-288 part 2 with BL-296's rows, BL-297's picker, BL-125 A) about 1 day; wave 2 (BL-286's popup and page, BL-293, BL-298's pane) about 1 day; wave 3 (BL-286 shaping, BL-295's card, BL-255's re-hash) about half a day; release, hand checks and the final suite about half a day. **Total about 3 working days from v1.8.0's publish (BL-304 out, Alan, 13-10-2026): 16-10-2026 at the earliest, 17-10 realistic** (today's overhead: Chrome slots limit wide testing to 4 to 5 agents; each wave's integration costs 2 to 3 h). If it's still too long, moving BL-125 A out saves about half a day. **Push window:** extended by Alan to the end of Friday 16-10-2026.

v1.9.0 can ship with BL-255 report-only; enforcing follows after its week (Alan decides). Release after wave 3, the full suite, hand checks in Chrome, and the docs.

**v1.8.0: leaves Beta (Alan, 12-10-2026): not marked pre-release, no "(Beta)" in its notes.** BL-231 (phase 2 onwards now on laptop 1, from `v18-fold`; laptop 2 holds) plus the small defects from laptop 2's v1.6.1 hand checks (BL-278 to BL-282, `fix-handcheck-161`). Originally BL-231 only (Alan, 12-10-2026), built on a second laptop following `dev/V18-LAPTOP-GUIDE.md`: phase 1 (tools in `dev/`) now, the folding only after v1.7.0 ships. The guard-files split is no longer a v1.8.0 candidate (not scheduled).

**Carried into v1.7.0 from v1.6.1's one-time code-health acceptance** (creaite-c1's audit, 12-10-2026):
- **BL-229, the rest:** step 4 for minutes.cmd_stage (86, 188 lines), build_dashboard's flow_data and review_queue (77), prep_page.context, live_server.read and docx_tools.fill_xml, plus the "fewer than 60 functions at 25 or more" target (73 now).
- **New with insight:** `build_dashboard.hub_record` is now the most complex function (131, 104 lines); `meeting_hub` is 79 and `day_close` 38.
- **Dashboard JS (for BL-228 D and BL-231):** HTML-string sinks 316 to 337, innerHTML 243 to 251, in-place wrappers 203 to 241, empty catch 36 to 39; Biome noFunctionAssign 135, noAssignInExpressions 46.
- **Swallowed exceptions with no reason:** +3 in build_dashboard, +2 in minutes, +1 in review.

## v1.8.0 (in progress, 13-10-2026)

- **Merged:** BL-277 (Stage icon in the guides and the Help tab), BL-278 to BL-283 (`fix-handcheck-161`). Settings goldens re-recorded for BL-279.
- **In flight:** BL-231 phase 2 on `v18-fold` (folding the wrappers in batches, snapshots byte for byte).
- **Logged:** BL-284, an intermittent `/api/pulse` 500 on busy CI runners.

## v1.9.3 (ready to publish 14-10-2026): Sneak peek, backups and PDFs in search

**Release state: READY TO PUBLISH (not published; VERSION still 1.9.2).** The main session merges `release-193` and `release-prep-193` into main, sets `VERSION` to 1.9.3, rebuilds the guides, runs the full suite once and publishes when release-193 is green and Alan's hand checks pass (a full release, not a pre-release), then changes this heading and this line to "published DD-MM-YYYY" with the suite and zip results, as v1.8.0's below.

Built: BL-322 (Sneak peek: `//`, the sparkle, plain code first, the confirm list, the `@` list and the changed-field flash, `@n` link ends; nothing sent), BL-323 (the daily zip to OneDrive, retention and the daily Tidy up, never from an ask creaite run, the weekly restore check, Restore from a backup in Settings › Health; Alan's four decisions of 14-10-2026) and BL-275 (PDFs in search with pypdf 6.19.0, Alan's two-week rule; the index rebuilt once). On `release-193`: the BL-322, BL-323 and BL-09 docs branches, `v193-sneak-peek-server`, `v193-sneak-peek-ui`, `v193-backups` and `sprint-search-pdf-eml`, on top of `release-192`. Nothing is missing; BL-09 is v1.9.4. No schema change. **A non-negotiable changed** (Alan, 14-10-2026): the daily zip leaves the vault for `_Portfolio/99 System/creaite backups/` (never ask creaite's chats or `vip.json`). Guard (confirmed by Alan): `sneak_peek.py read` READ; `backup.py` list/show READ, check DERIVED, tidy/restore RECORD; `tracker.py`'s `@n` link ends. Goldens: `work-panel`, `settings-essentials`, `settings-advanced`. Doctor: 32 checks (30 before; fresh vault from a release build of `release-193`). Hand checks: the four in the notes (Alan, live). Notes: `dev/release-notes/1.9.3.md`; BRD FR-256 to FR-258, NFR-02.

## v1.9.2 (published 14-10-2026): Settings, rejects and Today as one home

Published as a full release (not a pre-release), tag v1.9.2 `9a5ea19` (`cut-192`: main, `release-prep-192`, the Needs attention change from `v192-today-home` `7d12e23`, `VERSION` 1.9.2 and the guides rebuilt).

Built: BL-320 (Settings with Essentials, Advanced and Health; Fix it; update.py's after-update steps, on Alan's guard decisions of 14-10-2026), BL-315 (seven reject reasons, guesses, the one menu, changing a reject before or after apply) and BL-319 (Today as one home, parts 1 to 5, and the sidebar, part 6), plus the Work reflow fix and the Week ahead default of Urgent only (Alan, 14-10-2026). On `release-192` (`dde4343`): `v192-settings-ui` (with `v192-settings-server` and `v192-fixit`), `v192-work-reflow`, `v192-reject-reasons`, `v192-sidebar`, `v192-settings-server` (Urgent only), `v192-reject-ui` and `v192-today-home`, on top of `release-191`. Nothing is missing. No schema change. New default: Close the day from 17:30 (saved values kept). Guard: `session.py backup` DERIVED and the reject commands classified (confirmed by Alan); `launch.py` stays record. Goldens: BL-320's four Settings goldens (Alan agreed); Today's golden re-recorded for BL-319. Doctor: 30 checks (unchanged; fresh vault from a release build of `release-192`). At the cut (Alan): Needs attention's per-meeting proposal groups dropped (`v192-today-home` `7d12e23`), so proposals appear only in To decide and Today never shows a staging file name; the Today golden is re-recorded for it. Hand checks: the short list in the notes (Alan, live). Notes: `dev/release-notes/1.9.2.md`; BRD FR-253 to FR-255.

## v1.9.1 (published 14-10-2026): ask creaite like the dashboard

Published as a full release (Latest, not a pre-release), tag v1.9.1 `d011799` (`cut-191`: `release-191`, `release-prep-191`, `VERSION` 1.9.1 and the guides rebuilt). The cut is green on Python 3.9 and 3.14.

Built: BL-314 (claims checked, the plain "I can't", field changes through the dashboard's own save, on Alan's guard decision of 14-10-2026) and BL-321 (the day arrows never move). On `release-191` (`5586acf`): `v191-ask-claims`, `v191-ask-routing` and `fix-day-arrows`, on top of `release-190`. Nothing is missing. No schema change, no new setting or route; guard unchanged. Doctor: 30 checks (unchanged). Hand checks: the five in the notes (Alan, live). Notes: `dev/release-notes/1.9.1.md`; BRD FR-251, FR-252.

## v1.9.0 (published 14-10-2026): Meeting prep

Published as a full release (not a pre-release), tag v1.9.0 `d689f89` (`release-190`, `release-prep-190`, `VERSION` 1.9.0 and the guides rebuilt). The cut is green on Python 3.9 and 3.14.

Built: BL-286 (A to E, the headline) and BL-287, BL-285, BL-264, BL-255 (report-only), BL-256, BL-288 (parts 1 and 2), BL-293, BL-295, BL-296, BL-297 (with D), BL-298, BL-125 stage A, BL-276, BL-305 to BL-312 and BL-318. Server sides through `v19-integrate` (merged `ff9b6e0`); `sprint-preact` merged (`4c43624`); the screens on `release-190`: `v19-promises-data`, `v19-review-picker`, `v19-draft-chase`, `sprint-vip-ui`, `sprint-prep-shape` (with `sprint-prep-popup`), `sprint-today-days-ui`, `sprint-close-day-ui`, `sprint-prep-page` (BL-286 D), `sprint-panel-sweep` (BL-309), `fix-work-reload` (BL-318) and the BL-255 policy tests (`release-190` at `c39d1fa`). Nothing is missing from v1.9.0; BL-255 needs no re-hash (live_server hashes each page as sent). Doctor: 30 checks (28 before: the script-policy reports and the launcher). Hand checks: `dev/handchecks/v1.9.0.md` (scratch vault) and the short real-Mac list in the notes. Notes: `dev/release-notes/1.9.0.md`; BRD FR-229 to FR-250, NFR-23. BL-255's enforcing waits for a week of reports (Alan); BL-321 (the day arrows) moved to v1.9.1.

## v1.8.0 (published 13-10-2026, about 21:00): out of Beta

Final suite on `0af493b`: 192 of 192 on Linux Python 3.9 and 3.14. Published as a full release (Latest, not a pre-release). The zip installs fresh (doctor 28 of 28 on 3.14 and 3.9) and updates a 1.7.0 vault (28 of 28; 17 files replaced; a backup first).

BL-231 complete (the fold, ES modules with the pinned esbuild, checkJs at 0 errors, HTML sinks 240 to 4) and the defects BL-277 to BL-284, BL-289 to BL-294, BL-299, BL-300, BL-302 and BL-303. Notes: `dev/release-notes/1.8.0.md`; BRD FR-213 to FR-228, NFR-22.

## v1.7.0 (published 13-10-2026, about 01:35)

The first final suite on `43e08f9` failed on Linux only: at 320 px, Activity's search and Quick Capture's title have a font-set minimum width, and Linux fonts are wider (test_ui_sweep, BL-217). Fixed on `fix-reflow-170` (`f10ec8e`, CSS `min-width:0`), with Today's snapshot no longer holding the day the vault was built (`50aa40d`, the last visit pinned in the test). `release-1.7.0` moved to `50aa40d`; full suite green on Linux Python 3.9 and 3.14 (run 38303388746); both merged into main. The published zip installs fresh (doctor 28 of 28 on 3.14 and 3.9) and updates a 1.6.1 vault (28 of 28; 44 files replaced, 7 added, eight settings added; a backup first). Notes: `dev/release-notes/1.7.0.md`.

## v1.6.1 (published 12-10-2026)

One release for everything since 1.5.2 (no 1.6.0). Final suite on main: 154 of 154 on Linux Python 3.9 and 3.14. The first release build failed (the guides print the version and weren't rebuilt after VERSION changed); they were rebuilt on `release-1.6.1` and the release re-created. The published zip installs fresh (doctor 25 of 25 on 3.14 and 3.9) and updates a real 1.5.2 vault (25 of 25; the wrapper rules and new settings added; a backup first). Notes: `dev/release-notes/1.6.1.md`. BL-234's automatic CI switched on afterwards (pull requests and pushes to main, report-only).

## v1.5.2 (published 11-10-2026)

A hotfix from `release-1.5.2` (on 1.5.1): BL-202, ask creaite's prompt says to look inside files with Read, Grep and Glob, never Bash; with a test. The local zip installs fresh and updates 1.5.0 (doctor 24 of 24). Main carries the same line (`4551f7a`) and test for 1.6.1 (one release). GitHub's build passed (121 tests); the published zip installs fresh and updates 1.5.1 (doctor 24 of 24).

## v1.5.1 (published 11-10-2026)

sprint-polish-themes (BL-192 gear, BL-191 rail by right-click, BL-40a to d: nine themes, the colour audit), BL-195 ask-quips, BL-194 risk tiers on ask creaite's card. Full suite on main 120 of 120; published from `release-1.5.1` (`6c532f6`); GitHub's build 120 of 120 (`test_clear_day` passed alone). The downloaded zip (SHA-256 `339a682f…8594`) installs fresh and updates 1.5.0 (doctor 24 of 24).

## v1.5.0 (published 11-10-2026)

The milestones sprint (BL-186 Plan and Movement with the approved DDL and Missed retired, BL-184, BL-174, BL-189, BL-178, tidy-ups) and the All open = Open only alignment (Alan). Published from `release-1.5` (`c3acb84`); GitHub's build passed first time (two files passed alone after failing under load). The downloaded zip (SHA-256 `767a96d2…a558`) installs fresh and updates 1.4.0, turning a Missed milestone into Overdue (doctor 24 of 24). Found on the way: a commit had put the dev permission file and settings into git (templates restored, `2cac3ad`) and the runtime `files-log.jsonl` (untracked, `895eafe`).

## v1.4.0 (published 11-10-2026, overnight)

Every 1.4.0 sprint and fix merged: polish-2, rail, peek, peek-new, links, and the fixes. Published from `release-1.4` (`e665f73`). GitHub's first build caught two real failures that the re-runs on `main` had missed (they weren't in the files re-run after the late merges): an undone peek change showing as staged again (BL-188; fixed in `build_dashboard.py`) and a stale filter test (BL-190). After the fix, GitHub's build passed 113 of 113. The downloaded zip (SHA-256 `4bef24d4…92be`) installs fresh and updates the published 1.3.0 (doctor 24 of 24). Lesson: after merging branches that weren't in the full suite, re-run every file they touch, not a sample.

## v1.3.0 (published 11-10-2026)

Published from the `release-1.3` branch (`f93e02a`: the tested 1.3.0 plus test-only fixes for GitHub's Linux runner, and the runner's re-run-alone rule). GitHub's build: 99 of 99 (`test_settings_page` passed alone after failing under load). The downloaded zip (SHA-256 `16d3b570…4db7`) installs fresh and updates a 1.2.0 vault (doctor 24 of 24). Keep `release-1.3` for any 1.3.x patch; `main` carries 1.4.0.

## Merge order from here, and the release (Alan, 09-10-2026)

**v1.2.0 carries everything below, as one release (BL-106 included, Alan 09-10-2026).** Nothing is published until the last of these has merged.

1. **`sprint-4b`:** merged 09-10 (`828ea5d`). Not published: its VERSION and release notes stay, and the notes grow as each later sprint merges.
2. **`sprint-chat-sweep`:** merged 09-10 (`a250e23`). The full suite is still to run (twice, on a quiet machine).
3. **`sprint-5`:** merged 09-10 (`8b2b34b`), with the BL-105 pass re-run on chat-sweep's text.
4. **`sprint-recode`** (BL-111): merged 09-10.
5. **`sprint-exec-state`** (BL-106): merged 09-10. Alan still to read Generate and Make it executive on real projects.
5b. **Debug log part 2, stage B** (`sprint-debug-log-2b`, merged 09-10): it owns `tracker.py`, `excel_sync.py`, `minutes.py`, `review.py`, `report.py` and `sweep.py` for its log calls; with BL-113 and the Decisions board.
6. **Release v1.2.0:**
   - finish `dev/release-notes/1.2.0.md` to cover all of the above;
   - regenerate the guides;
   - run the full suite once on a quiet machine;
   - Alan pushes;
   - Claude in the main folder publishes the release with `gh` and test-installs the zip (built locally if GitHub's macOS runners are stuck).

## Fixed on main (09-10-2026)

- **The dashboard script error since chat-sweep** ("mdBlocks(...).map is not a function", nine dashboard test files failing): the chat's markdown functions (BL-109) had the same names as the page's own `mdInline`/`mdBlocks` and replaced them. They are now `chatMdInline`/`chatMdBlocks` (`f086503`). The editing, search, chat, milestones, side-panel, Current state, Work-filter, workstream, project-name and pages test files all pass. **Bring `main` in before merging.**

## Testing rule (Alan, 09-10-2026; the standing rule from 10-10-2026)

**One full suite pass is enough.** Never a second run to confirm a pass.

- **Each sprint runs its own tests** (the files its brief names) before it asks to merge.
- **At each merge,** run only the test files for code that had conflicts, not the full suite.
- **One full suite pass on the final `main`,** just before the release, is the signal that all the sprints pass. No full suite after every merge, and no repeated runs to confirm a pass. If that single run fails, find the cause from the merge log and the failing file, fix it on `main`, and re-run only that file.
- **A sprint that runs a full suite needs one pass too.** A file that fails under load and passes when run alone counts as passing; name it in the report.
- **A fix after the full suite** re-runs only the files it touches, not the suite again.

## Things to know

- **FR numbers:** FR-89 (the board), FR-90 (Clear day) and FR-91 (time zone) are taken; FR-92 to FR-98 are the pages sprint and the debug log. When two sprints add a requirement at the end of the list, the merge shows a clash at that line: keep both and renumber the later one.
- **Machine load:** the browser tests drop their connection to Chrome when several sessions run tests at once. Run a full suite when no other session is running one.
- **Never push or merge from a sprint session.** Merging is Claude in the main folder, after the checks in each brief.
