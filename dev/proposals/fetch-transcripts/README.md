# Proposal: fetch transcripts as they appear (#250, #181 C2) — guarded parts

**Option 2 chosen by Jarvis/Alan 23-10-2026; Alan can overrule.** The live server's observer (`transcripts.SweepFetch`, fed by
`live_server.diff`) is the only path that fetches. `fetch_after_record`, the saved-result-file reader and the tie rules are gone:
`transcripts record` only records statuses, a `result_file` in a fact is refused as an unknown field, and no script path can write
`inbox/` (tests: `test_record_never_fetches_stamps_or_follows_a_result_file`,
`test_no_script_command_writes_into_the_inbox_even_with_the_setting_on`). A sweep run from Claude Code therefore never fetches; the
meeting is fetched on Process, as today. Rebased on `v261-line2` (v264-250, off v262-183).

**Apply order for the rules:** `draft-delivery/rules-and-skill.diff` (#183) first, then `creaite-rules.diff` here; if the VIP-follow
rules diff lands first, use `creaite-rules.after-vip.diff` instead. `live_server.diff` applies to line2 on its own and `check.py` is OK
with it (the fetch call sits in a small `_fetch_observe` helper, so `_on_tool_result` stays within its complexity limit).

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
(`sweep.py *` already covers `sweep.py transcripts record`, which cannot write `inbox/`). `permissions.py` and `reach.py` need **no change**.
`Guard.test_the_sweep_runs_tool_list_has_no_write_tool` asserts this against the live lists.

## 2. `system/creaite-rules.md` — `creaite-rules.diff` (regenerated on main 4e564fcf after #238/#239 changed the staging row; `git apply --check` passes)

The staging row records `transcripts.json`'s new stamps (`fetched`, `left`, `fetch_error` times and a `fetch_tries` count) and the
new `sweep-fetched.json` (event IDs by outcome, cleared by `done`/`fail`); the cx-sweep row mentions the off-by-default fetch, the
fail-closed sensitivity and the observer-only tie (no result-file tie: option 2 has none).

## Points for the guard check

- **In the live server** the observer ties each transcript read to its event by the URL the event read returned (`SweepFetch.uris`),
  and holds back any event whose own read says its sensitivity isn't `normal`. **Only that map ties a read (Cap's HIGH, 23-10):** a URL
  recorded in `transcripts.json` (typed by Claude through `record`) is never a tie; an unknown URL, or a read in a run that did not
  read the event, is refused. The observer takes only the exact read tool name, and writes with `open(..., "x")` (a planted link is refused).
- **Claude Code sessions (no live server):** nothing is fetched (option 2). `transcripts record` takes the same facts as before, minus `result_file`.
- **Sensitivity fails closed:** only `normal` is fetched; a missing or unknown value counts as confidential (the sweep writes the
  key for every row that isn't private).
- **What is skipped:** confidential (the brief's only content rule), plus what can't be Processed anyway: private, not ended, outside
  the Calendar import window, not online, cleared, processed, in Review, already in `inbox/`, fetched before, No transcript or No access.
- **Later until a transcript arrives (#232):** there's no store for it on main yet; `transcripts.snoozed_ids()` returns nothing
  until #232 adds one.
- Nothing reaches `tracker.db` and nothing is staged (the tests check both); the debug log gets counts only.
