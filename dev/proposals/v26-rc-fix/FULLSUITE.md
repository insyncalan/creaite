# v26-rc full suite (2.6.0 candidate 069a4f7f + v26-rc-fix)

**Head:** after the fixes on v26-rc-fix, every file that failed passes; 0 real failures left, 0 guarded diffs needed. 8 shards:
519 files passed first time, 18 real failures (16 stale tests or merge artefacts, fixed in the tests; 1 real 2.6 product bug,
fixed in non-guarded dashboard code; 1 clock read moved onto the shared helper at Jarvis's request), 5 flakes. The
re-run of all 23 files that failed (one go, -j 4, Chrome cap 2): 25/25 passed once a comment that named a page global was reworded.

Run: `CREAITE_BROWSER_SLOTS=2 CREAITE_CHROME_CAP=2 python3 dev/tools/run_tests.py -j 4 --shard I/8`, shards one after another.
A file that fails in its shard is run alone; "flake" = failed in the shard, passed alone.

## Step 1
- test_guard_small_copy_source.py: a NUL copy source is now held in Review under #280 ("Held in Review, not applied: … transcript
  no longer in the inbox"); the test asserts the held message, nothing filed, and the next apply runs. Stale test, fixed.

## Per shard

### Shard 1/8: 61 passed, 6 failed (all real, all failed alone too), 0 flakes
| File | Class | Fix |
|---|---|---|
| test_looks_like.py | stale test | #232 C2 retired llTag; looks for the peek note's `Looks like <a … data-open>` |
| test_dashboard_split.py | merge artefact | the guard-small test's comment "(FAT)" read as a page name; reworded |
| test_clock_guard.py | merge artefact | baseline kept at 4 (Jarvis): drafts.js's AI check now uses core/server.js's onceFor (in-flight read + 60 s cache) instead of two Date.now() reads; test_calendar_refresh and test_followed_needs use test_dashboard.today() |
| test_decisions_needed.py | stale test | the Draft email now reads /api/edit/ai/caps (a read): allowed in the no-writes filter |
| test_drafts_scaffold.py | stale test | #246 puts the agenda style in the AI drafts tab: switches = features, rows = features + 1 |
| test_followed_needs.py | stale test | #232 C2: Today's proposal link lands on Intake › Review (no RHL); note: a sweep proposal has no meeting to open, so nothing is highlighted |

### Shard 2/8: 67 passed, 5 failed (all failed alone too), 0 flakes
| File | Class | Fix |
|---|---|---|
| test_panel_drafts.py | **real product bug (2.6, B2 #232)**, non-guarded | a page opened on an item (`#work…&item=…`) threw in pkUpdReset (`#pkPSaveA` is added by a later boot step), stopping start-up: no staged bar after a reload. panel.js now skips it when it isn't there yet; dashboard.html rebuilt |
| test_intake_review_chrome.py | stale test (also fails on pristine v26-rc) | `self.setUp()` opens a new page; the test kept driving the old one (whose ASKED still held iteration 1's call). It now drives the new page and restores the chooser stub inline |
| test_intake_review_update_peek.py | stale test (date drift) | the sample's due date follows the day it runs: read from the live row, not "25-10-2026". Note: the saved row title reads "status Open → Open; due …" (an unchanged status in words) |
| test_project_settings_v2.py | stale test | #232 C2: go('review') / go('inbox') land on intake-review |
| test_day_past_and_sizes.py | stale test | #232 C2 left 7 controls on the checked screens: "at least one per selector" instead of "> 10" |

### Shard 3/8: 65 passed, 1 failed, 1 flake
| File | Class | Fix |
|---|---|---|
| test_field_names.py | stale test | #232: the rail's "review" item opens intake-review (rail.js railGo) |

Flake: test_intake_review_harden_b.py (Keys.test_arrows_and_esc_after_the_peek_was_closed_another_way: panel wait under load; passed alone in the shard and twice more alone).

### Shard 4/8: 65 passed, 1 failed, 0 flakes
| File | Class | Fix |
|---|---|---|
| test_run_tests_shard.py | merge artefact | dev/tools/shard_times.txt named three removed files (test_review_age, test_review_floating_bar, test_transcripts_ui): lines dropped (no effect on the split) |

### Shard 5/8: 66 passed, 1 failed, 0 flakes
| File | Class | Fix |
|---|---|---|
| test_icons.py | stale test | #288 moved the Work field picker's shortcut to Shift+F |

### Shard 6/8: 63 passed, 3 failed (all failed alone too), 0 flakes
| File | Class | Fix |
|---|---|---|
| test_word_export_227.py | stale test | its client_items stub took (code, fri); the 2.6 review passes `base=` too, so the stub raised and the facts failed closed (no milestones drawn). Check 9 now diffs guarded files against origin/v26-rc (the HOPD's approved diffs are on it) instead of origin/v234-final |
| test_propose.py | stale test | guard-small: a copy onto a different existing file is refused when staged (was: at apply); nothing staged, file untouched |
| test_people_page_v2.py | stale test | #232 C2: go('review') / go('inbox') land on intake-review |

Not in the suite but stale the same way: dev/tests/handchecks/test_v260.py lines 909-910 (VIEW==='review' / 'inbox').

### Shard 7/8: 65 passed, 2 failed in the shard, both flakes, no fix
- test_health_suggest.py (ClientHealthRow: focus on #crWhy) and test_instant_edits.py (forced apply failure then Retry): failed in the
  shard and in its alone re-run while other Chrome runs (this fix's own probes) were loading the machine; each passed 2-3 times
  alone afterwards, and both pass on pristine origin/v26-rc. Focus/timing under load.

### Shard 8/8: 66 passed, 0 failed, 1 flake
- test_archive_items_browser.py: its live server stopped answering /health for 6631 s (the machine was very likely asleep); passed alone in 9 s.

## Re-run of every file that failed (after the fixes)
25 passed (23 named files plus test_calendar_refresh_ui and test_health_suggest_e2e, which match the names); the one failure,
test_dashboard_split (a test comment naming `railGo` read as a page name), was reworded; it passes and check.py says `check: OK`.

## Flakes (failed in the shard, passed alone)
test_intake_review_harden_b.py (shard 3), test_health_suggest.py and test_instant_edits.py (shard 7), test_archive_items_browser.py (shard 8).

## Guarded diffs needed
None.
