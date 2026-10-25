# #365: a transcript load that never got the calendar event

Branch v268-365. Frozen and approved by Alan (25-10-2026): `live_server-365.diff`, `tests-pins.diff`. Pending his word:
`live_server-365-tools.diff` (applies on top of the frozen diff) and `tests-tools.diff`.

Landing order: live_server-365.diff, live_server-365-tools.diff, tests-pins.diff, tests-tools.diff (see dev/proposals/GUARDED-2.6.8.chain).

## What the diffs do
- live_server-365.diff: a debug-log line per tool result of a job run (tool, ok or error, length); the load prompt searches the
  day's window, not the title, with one retry; `check` and `load` get their own prompt (no CLAUDE.md, no session start).
- live_server-365-tools.diff (M2, approved by Alan, bytes frozen): `KIND_TOOLS` and `KIND_ARGS` for check and load: the calendar
  search and read_resource only, ToolSearch the only built-in.
- Unguarded and already on the branch: transcripts.py says which way a load failed and logs counts; M1 (a read of the asked event
  clears `wrong`, a neighbour read after it changes nothing).

## Follow-up (not fixed here)
- `transcript_run` (live_server.py) checks `current_run()` without START_LOCK, unlike intake_process and calendar_refresh, so two
  clicks at once can start two runs. Pre-existing; fix in a later guarded chain.
- The root cause of the four failed loads is still unproven; the new log lines will name it on the next failure.

## Privacy
The day-window search returns every event of that day, confidential titles included, into Claude's context for that one run. Nothing
persists: the debug log keeps only the tool name, ok or error and the length of each result; no title, attendee or text.

## For the 2.6.8 notes
- Good to know: loading a transcript now searches the meeting's whole day, so that run sees the titles of the day's other meetings
  (including confidential ones) while it runs; creaite keeps none of them, and the run can use only the calendar search and
  read_resource.

## Follow-up delta (needs Alan's re-approval)
Four files are frozen at Alan's approved bytes (sha256, first 16): live_server-365.diff b63bce71ea0ff04a, tests-pins.diff
109f882b97752023, live_server-365-tools.diff ba75c4689af9ec93, tests-tools.diff e1a94f27732d5e01. Cap's three MEDIUMs go in a NEW
pair, applied after them:
- live_server-365-followup.diff (5687339225f38235): `CONTEXTLESS_JOBS`: check and load start in an empty folder
  outside the vault with `--setting-sources ""` (the vault CLAUDE.md no longer loads), no session saved, no `--add-dir`, as #183's
  draft run does; the prompt searches one hour either side of the meeting, then the whole day, then the exact start and end (three
  searches at most, then it stops and says so) and takes only the event whose id is exactly the asked one.
- tests-followup.diff (09a9d7264f7b79cd): dev/tests/test_job_followup_365.py (3 tests, skipped until the diff lands).
Applies on the branch base a10a7299 after the four frozen diffs (`git apply --check` clean there). On the current origin/main
(a505164f) the approved tools delta itself no longer applies (its run_dirs hunk, changed by #339 A), so a rebase of the tools delta
and this one is needed at the cut; it needs Alan's word again.

## Follow-up pair not in 2.6.8

`live_server-365-followup.diff` and `tests-followup.diff` are not part of the 2.6.8 tree or chain (removed from the release merge); only the four frozen diffs above travel (`live_server-365.diff`, `tests-pins.diff`, `live_server-365-tools.diff`, `tests-tools.diff`). The follow-up lines above describe files that are not in this tree.
