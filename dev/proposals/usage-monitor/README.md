# #238 Usage and context monitor: what Jarvis applies (live_server.py is guarded)

`live_server.diff` is a unified diff against `system/scripts/live_server.py` on `v251-usage-monitor` (base `v251-release` 26990edf).
Apply: `patch -p0 system/scripts/live_server.py < dev/proposals/usage-monitor/live_server.diff` (or `git apply` after fixing the header
paths). Three small hunks, no other file:

1. **`GET /api/usage`** (read only, in `do_GET`'s `api_get` table, so the Host and `X-Creaite-Token` checks of `authorised()` apply as for
   `/api/data` and `/api/files`): `usage_get()` answers `usage_report.json_report()` plus `ok: true`; a fault is a 500 with only the
   exception's name. No POST route, no body, nothing written.
2. **`usage_context_job()`** (next to `backup_daily_job`): `usage_log.daily()`, which measures the always-loaded files and appends
   `system/staging/context-size.jsonl` once a day (idempotent per day; refuses in the development repository; never raises).
3. **`backup_daily_job()`** calls it after the archiving step and adds its log line. That job already returns early in the development
   repository and while an ask creaite run is in progress, and runs under the job lock, so the one writer is the live server's daily job
   and never an ask creaite run or the page (`usage_log.py` has no command line, and is not in `reach.SCRIPT_COMMANDS`).

The page works without any of it: `D.usage` is built into the page (`build_dashboard.py` calls `usage_report.json_report()`), and the tab
only refreshes from `/api/usage` when the route answers (a 404 or 405 is remembered and not asked again).

Tests that apply this diff to a throwaway vault's own copy (never committed): `dev/tests/test_usage_wiring.py` and the `UsageRoute` class
of `dev/tests/test_activity_usage.py`. If `live_server.py` has moved on, re-cut the diff: the hunks anchor on the `"/api/files"` table row,
`def do_POST`, `BACKUP_EVERY` and the `archived = archive_after_backup()` line.

## Also for Jarvis

- `creaite-rules.md` (folder map, `system/staging/` row, after the `run-usage.jsonl` entry): add
  `` `context-size.jsonl` (#238: what every run loads before it starts, measured once a day by the live server's daily job through `usage_log.py`: one row per always-loaded group and day, with `file` one of `rules`, `claude_md`, `memory` or `skills`, its bytes, estimated tokens (bytes ÷ 4) and the date; counts only, never the text or the name of a file; never in the development repository; in the daily backup zip with the rest of staging; kept for good, about 80 bytes a row) ``
  and in the `system/scripts/` row extend the `usage_log.py` and `usage_report.py` entries (`usage_log.py` also measures and appends that file; `usage_report.py --json` gives the Activity › Usage tab's figures, read only).
- `backup.py` needs no change: the zip takes every file under `system/staging/` except `LEFT_OUT` (the ask chats, their images and `vip.json`), and `RESTORABLE` lists `system/staging/` as a prefix, so `context-size.jsonl` is in the zip and restored with the rest.
