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
| test_clock_guard.py | stale baseline / merge artefact | drafts.js 4 → 6 (the AI check's back-off timer); test_calendar_refresh and test_followed_needs use test_dashboard.today() |
| test_decisions_needed.py | stale test | the Draft email now reads /api/edit/ai/caps (a read): allowed in the no-writes filter |
| test_drafts_scaffold.py | stale test | #246 puts the agenda style in the AI drafts tab: switches = features, rows = features + 1 |
| test_followed_needs.py | stale test | #232 C2: Today's proposal link lands on Intake › Review (no RHL); note: a sweep proposal has no meeting to open, so nothing is highlighted |
