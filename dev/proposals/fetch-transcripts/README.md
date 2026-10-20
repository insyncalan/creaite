# Proposal: fetch transcripts as they appear (#250, #181 C2) — guarded parts

Branch `v26-fetch-transcripts`. The unguarded parts are built (setting, `transcripts.py` fetch step, `sweep.py done`, cx-sweep text,
Settings card, tests in `dev/tests/test_fetch_transcripts.py`). Two guarded files need Jarvis.

## 1. `live_server.py` — `live_server.diff` (`git apply --check` re-checked on main 4e564fcf, 20-10-2026: passes)

A sweep run (Close the day's catch-up, `kind="sweep"`, and a panel sweep, `self.sweep`) gets `self.fetch = transcripts.SweepFetch()`.
`_on_tool_result` hands it each tool call and result, as a transcript Job is handed today. It only looks at `read_resource` on
`calendar:///events/…` and `meeting-transcript:///…`, and only when `sweep.fetch_transcripts` is true; it writes the transcript
into `inbox/` from Microsoft 365's own result (`Job.write`, the same writer as Load), never from Claude's text. Any exception is
swallowed and logged by name only, so a fetch never stops a sweep.

**No tool list changes.** The fetch uses exactly these Microsoft 365 reading tools, the ones Process (Load) uses:

- `mcp__claude_ai_Microsoft_365__outlook_calendar_search`
- `mcp__claude_ai_Microsoft_365__read_resource`

Both are already in `permissions.M365_READ`, so already in `READ_TOOLS` and `KIND_TOOLS["sweep"]` and in `.claude/settings.json`.
**No write tool is added**: no Microsoft 365 action, no `Write`/`Edit` outside `system/staging/drafts/`, no new Bash rule
(`sweep.py *` already covers `sweep.py transcripts record`). `permissions.py` and `reach.py` need **no change**.
`Guard.test_the_sweep_runs_tool_list_has_no_write_tool` asserts this against the live lists.

## 2. `system/creaite-rules.md` — `creaite-rules.diff` (regenerated on main 4e564fcf after #238/#239 changed the staging row; `git apply --check` passes)

The staging row records `transcripts.json`'s new stamps (`fetched`, `left`, `fetch_error` times and a `fetch_tries` count) and the
new `sweep-fetched.json` (event IDs by outcome, cleared by `done`/`fail`); the cx-sweep row mentions the off-by-default fetch, the
fail-closed sensitivity and the result-file tie.

## Points for the guard check

- **In the live server** the observer ties each transcript read to its event by the URL the event read returned (`SweepFetch.uris`),
  and holds back any event whose own read says its sensitivity isn't `normal`.
- **Claude Code sessions (no live server):** nothing records which read a saved file came from, so `transcripts record` reads the
  file Claude Code saved a large result to (`result_file`) only when the file itself ties it to that meeting
  (`transcripts.tie`): every transcript began inside that meeting's own times (from 10 minutes before), the subject it names, if
  any, is that meeting's, and no other meeting in the saved calendar (confidential and private ones included) fits those times;
  otherwise `not tied`, stamped `left`, and fetched on Process. The file must resolve (symlinks followed) into a `tool-results`
  folder under `~/.claude`, be at most 25 MB and UTF-8; its text is parsed directly and a path inside it is never followed. An
  inline result is never re-typed. The path sits in a drafts JSON file, not a Bash argument, so the hook doesn't see it; the
  script's own checks are the guard. Residual: a confidential meeting the saved calendar doesn't hold at all (dropped by an ignore
  rule) at the same time as an eligible one with the same subject can't be told apart. Jarvis: confirm that's acceptable, or have
  the fetch run only from the live server (drop `fetch_after_record` from `record`).
- **Sensitivity fails closed:** only `normal` is fetched; a missing or unknown value counts as confidential (the sweep writes the
  key for every row that isn't private).
- **What is skipped:** confidential (the brief's only content rule), plus what can't be Processed anyway: private, not ended, outside
  the Calendar import window, not online, cleared, processed, in Review, already in `inbox/`, fetched before, No transcript or No access.
- **Later until a transcript arrives (#232):** there's no store for it on main yet; `transcripts.snoozed_ids()` returns nothing
  until #232 adds one.
- Nothing reaches `tracker.db` and nothing is staged (the tests check both); the debug log gets counts only.
