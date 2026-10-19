# #238 Usage and context monitor: the live server's two hooks (guarded file)

For Jarvis to apply: `git apply dev/proposals/usage-monitor/live_server.diff` (checked with `git apply --check` on `v252-usage`).

## What

Five added lines in `system/scripts/live_server.py`, nothing else changed:

1. **The daily job** (`backup_daily_job`, BL-323): after the backup steps and the archiving, `context_size.daily_line()` appends
   today's sizes of the always-loaded files to `system/staging/context-size.jsonl`, once a day, and its line joins what the job says.
2. **One POST route**, `POST /api/usage/review {date, saw, decided}`: `DRAFT_ROUTES.update(usage_reviews.routes(LOCK))`, beside
   `report_server.routes(...)`. It appends Alan's own review note to `system/staging/usage-reviews.jsonl` and answers with every note.

No GET route is needed: the tab's figures reach the page in `D.usage` through the existing `/api/data` and page build
(`build_dashboard.collect`, as Activity › Quality's `D.quality` does).

## Why

- The brief (Jarvis, 19-10-2026): the context-size record is appended by the live server's daily job through a plain module like
  `usage_log.py`; never by an ask creaite run, never by the page.
- Review notes are the tab's one write; `/api/fs` has no rule for a new staging file, and a dedicated route keeps only the three
  fields (`usage_reviews.clean`), so nothing but Alan's note and a date can be stored.

## Risk

- Low. `daily_line()` never raises (`record_daily` catches everything) and runs inside the job's existing guards: after the
  development-repository check, after `backup.ask_run()` (never from an ask creaite run), under the job lock. It reads file sizes and
  the skills' front matter only, and writes fixed group words and integers (`rules`, `claude_md`, `memory`, `skills`; never a path or
  a folder name, which might carry a client's name).
- The route is token-checked like every POST (`do_POST` → `authorised()`), takes the server's `LOCK`, and refuses a body without a
  `YYYY-MM-DD` date or without any note; each text is one line of at most 200 characters; other fields are dropped.
- Without the diff the page still works: the figures and the 30-day change are read at page build (the change shows "no earlier
  measure yet" until the record has days); "Save note" says "Saving a review note needs the live server's next update."
- `creaite-rules.md` (folder map) needs its lines for `context-size.jsonl` and `usage-reviews.jsonl` in a guarded pass, as the
  brief says. Both are in `system/staging/`, so the daily backup zip already carries them.

## How to test

```
git apply dev/proposals/usage-monitor/live_server.diff
python3 dev/tests/test_usage_monitor.py        # LiveServerHook stops skipping; UsageTab saves a note end to end
python3 dev/tests/test_archive_items.py        # the daily job's order is unchanged (backup, archive, then the context size)
python3 dev/tools/check.py                      # check: OK
```

Without the diff, `LiveServerHook` skips and `UsageTab.test_review_note_form_and_csv` checks the "next update" message instead.
Both paths were run on 19-10-2026.
