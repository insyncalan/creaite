# v26-rc full suite (2.6.0 candidate 069a4f7f + v26-rc-fix)

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
