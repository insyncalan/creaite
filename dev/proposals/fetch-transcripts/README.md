# Proposal: fetch transcripts as they appear (#250, #181 C2) — guarded parts

Branch `v26-fetch-transcripts`. The unguarded parts are built (setting, `transcripts.py` fetch step, `sweep.py done`, cx-sweep text,
Settings card, tests in `dev/tests/test_fetch_transcripts.py`). Two guarded files need Jarvis.

## 1. `live_server.py` — `live_server.diff` (`git apply --check` passes on main dcd8a7b6)

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

## 2. `system/creaite-rules.md` — `creaite-rules.diff` (`git apply --check` passes)

The staging row records `transcripts.json`'s new `fetched` time and the new `sweep-fetched.json` (event IDs by outcome, cleared by
`done`/`fail`); the cx-sweep row mentions the off-by-default fetch.

## Points for the guard check

- **Claude Code sessions (no live server):** the text is read only from the file Claude Code saved a large result to
  (`result_file` in the facts), and only under `~/.claude/**/tool-results/` (`transcripts.result_file_text`). An inline result is
  never re-typed: the meeting stays "Transcript available" and is fetched on Process. The path sits in a drafts JSON file, not a
  Bash argument, so the hook doesn't see it; the script's own folder check is the guard. Jarvis: confirm that's acceptable, or
  have the fetch run only from the live server.
- **What is skipped:** confidential (the brief's only content rule), plus what can't be Processed anyway: private, not ended, outside
  the Calendar import window, not online, cleared, processed, in Review, already in `inbox/`, fetched before, No transcript or No access.
- **Later until a transcript arrives (#232):** there's no store for it on main yet; `transcripts.snoozed_ids()` returns nothing
  until #232 adds one.
- Nothing reaches `tracker.db` and nothing is staged (the tests check both); the debug log gets counts only.
