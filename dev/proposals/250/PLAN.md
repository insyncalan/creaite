# #250 Fetch transcripts as they appear: build plan for 2.7.0

Planning note, no code. Written 25-10-2026 on origin/main (v2.6.5, ce936941).

## What it is

A sweep step that fetches a meeting's transcript into `inbox/` once the meeting has ended. Alan's decisions (issue, 19-10-2026): "a setting, off by default (`sweep.fetch_transcripts`); skips confidential meetings only; read only, no AI, nothing written to the tracker." It uses the two read tools already allowed (`outlook_calendar_search`, `read_resource`). Nothing is extracted; Alan still presses Process.

Moved to 2.7.0 on 24-10 (Jarvis): "Cap: please re-review the branch when you have capacity". It ships only if Cap's re-review lands.

## Where the work stands

- The code is NOT on main. `transcripts.py` on main is the older "Calendar import" module (todo, record, show, Job). The fetch code (`SweepFetch`, `meeting_key`, `observe`) lives on the `v262-250b` line. Local branch `team-stark-250-readorder` (d3db0561, base c041c841) adds the read-order change (`finish()`; 121 hostile cases). `git merge-tree` of that branch into main conflicts in `transcripts.py`, and `dev/tests/test_fetch_transcripts.py` was deleted on main. So step 1 is a port, not a merge.
- Cap's last verdict (24-10 19:37): NOT READY as a fix for the leak, correct as a step.
  - H1 (HIGH): order c is the default flow. A confidential event is saved with `teams=False`, `todo()` records it "none" and never lists it, so the run never reads it and cannot know it is held. Two events naming one meeting with different sensitivity leak the confidential text into `inbox/`.
  - M1: the hook plan "finish() before `done`" cannot be built. `sweep.py done` is Claude's own Bash step; the server only sees the stream.
  - M2: a run stopped, timed out or failed before a held event is read is order c by construction.
  - L1 held reads are silent; L2 `meeting_key` over-merges on `@` and `_`; L3 `[` in a URL raises in `note_event`; L4 `finish()` empties `waiting` before settling, no re-check of the switch, no cap on queued text; L5 two surviving mutants (`finish()` idempotence; `open(vtt,"x")` to `"w"`) and a partial .vtt left on failure.
- Earlier findings already closed on the line: model-chosen result file (CRITICAL), second hop, `reach.py` classification, live-event sensitivity, dangling symlink, spooled-read race, lookalike tool name.

## Plan

1. **Port to main.** New branch off main; cherry-pick the 250b line and the read-order commit onto `transcripts.py`, `sweep.py`, the two test files and `dev/proposals/fetch-transcripts/`. Resolve against main's changes to `transcripts.py` (#265 record checks, confidential titles-only). Restore the deleted test file. Re-run the 121 + 30 + 22 tests.
2. **Fix order c with an independent sensitivity source (H1).** Decision for Alan below. Recommended: the held set is built before the run from the saved calendar data (`calendar.json` rows carry the sensitivity even when `teams=False`), keyed by `meeting_key` of each confidential row's join URL, plus the event's own `sensitivity` when the run does read it. A transcript whose key is in the set is not written. Fail safe: a missing or unreadable calendar file holds everything.
3. **Settle at the end of the run, not before `done` (M1/M2).** `finish()` is called once from the server when a run ends. Only a run that ended answered settles; stopped, timed-out or failed runs drop `waiting` and tally "left" (Process still works). The daily summary reports a fetch on the NEXT sweep's `done` as today, or is replaced by a server-side line (open question 2).
4. **Cap's LOWs:** exact `@` rule only outside the first path segment (L2); wrap `urlsplit` so a bad URL adds to `blocked` first (L3); settle each read in its own try, re-check `fetch_on()`, cap queued text at the 25 MB limit (L4); open with mode `"x"`, remove a partial .vtt (L5); visible outcome for held reads ("Held: confidential or same meeting") (L1); keep the two over-holds (case-only join ids, series occurrences) but show the reason.
5. **Setting and page.** `sweep.fetch_transcripts` default false (settings.json, `settings-defaults.json`, `settings_catalogue.py`, Advanced > Transcripts, Reset turns it off, only the exact value true turns it on). Outcome line in the sweep summary and Calendar import status.
6. **Guarded diffs** (prepared, not applied), see below.
7. **Docs.** `creaite-rules.md` transcripts paragraph (guarded text diff), help text, release note, `dev/BUILD.md` entry.

## Files touched

Not guarded: `system/scripts/transcripts.py`, `sweep.py`, `settings_catalogue.py`, `system/templates/settings-defaults.json`, `system/config/settings.json` (new key only), dashboard source for the Settings section, `dev/tests/test_fetch_transcripts.py`, `test_fetch_transcripts_hostile.py`, `test_transcripts.py`, a new `test_v270_fetch.py` hand-check automation, help and release notes.

## GUARDED parts (each a diff for review, not a direct edit)

- `live_server.py`: (a) feed tool results to `SweepFetch.observe()` (the existing `_on_tool_result` chain; the file already has `Run.__init__` and `_on_tool_result` at their complexity limits, so extract helpers in the same diff); (b) call `finish()` when a run ends in every way, with the stopped/timed-out/failed rule; (c) read the live event's `sensitivity` at fetch time. No tool list, `--add-dir` or allow-rule change.
- `reach.py`: only if `sweep.py transcripts record` or any new command needs a class. The plan avoids a new command: the write is the server's, not a script's. Cap's earlier finding 3 still applies if any script path can write `inbox/`; add a `reach.SCRIPT_COMMANDS` check that no transcripts command is DERIVED and writes.
- `creaite-rules.md`: the text for the setting, the inbox write and the hold. Kept short (the file was halved in #338).
- `.claude/settings*`, `permissions.py`, `tracker.py`: no change planned. Nothing reaches `tracker.db`.

## Risks

- Confidential text written to `inbox/` is the one content rule. Two failure modes remain until step 2 lands: order c, and any spelling of the join URL not folded by `meeting_key`. Mitigation: switch off by default, hold set from the calendar, fail safe, hostile suite in CI.
- The real Teams transcript URL form is unchecked (base64 vs thread id). One real run with Alan's live account is needed to confirm `meeting_key`.
- `sweep.py done` ordering (M1) may force a summary change.
- The port from a divergent line may drop a main fix. Mitigation: run the whole suite and `check.py`.
- Complexity limits in `live_server.py` (CC 18 and 15).

## Test plan

- Port: the existing 30 + 121 + 22 pass; `check.py` clean; `test_no_real_names`.
- New: order c (confidential event never read, same meeting by another event); calendar file missing or corrupt holds all; hold keys from calendar rows with `teams=False`; stopped, timed-out and failed runs write nothing; idempotent `finish()`; switch turned off mid-run; partial .vtt removed; `"x"` mode; `@`/`_` over-merge; `[` in URL; held read shows an outcome.
- Cap's 125-case script committed to `dev/tests/` (it is only in a session scratchpad today) and made to pass except the two documented over-holds, now with a visible reason.
- Mutation run (switch default on, hold skipped, `"x"` to `"w"`, `finish()` not clearing): all red.
- Hand check (Alan, live Microsoft 365, one meeting, throwaway): confidential meeting not fetched; normal meeting fetched; nothing in `tracker.db`.
- Independent Opus review of the guarded diffs and a fresh hostile re-run by Cap (Full tier).

## Estimate

About 5 builder-days (range 4 to 8): port and tests 1.5; calendar hold 1; end-of-run settle and server diff 1; LOWs and page 1; docs, mutation run and review fixes 0.5 to 3. Cap's re-review is extra wall time and may add a fix round.

## Open questions for Alan

1. **Hold source for order c.** Use the saved calendar data (sensitivity already there), or read every candidate event live at fetch time? Recommend the saved calendar plus the live event when read; reading live for each costs more calls and still leaves a gap if the run never reads it.
2. **Where the fetched count is shown.** Server-side line after the run ends, or keep it in the next sweep's summary? Recommend the server-side line (simpler, correct); the next-sweep report would be wrong by a day.
3. **Visible reason for held transcripts** ("held: same meeting as a confidential one"). Recommend yes, short, no meeting title for a confidential one.
4. **Over-holds** (case-only join ids, other occurrences of a series): accept them as fail safe? Recommend yes.
5. **Review.** Cap's Full-tier verdict required, or the fresh-Opus waiver used for 2.6.2/2.6.4? Recommend Cap if back, otherwise the waiver with a second hostile run, because this is a leak path.
6. **If order c cannot be closed in time:** ship #250 in 2.7.1 rather than 2.7.0 with the switch hidden? Recommend defer; never ship a known leak, even off by default.

## What to cut if time is short

Cut in this order: visible reasons for held reads (L1); the page section (leave the key in `settings.json`, off); the over-hold refinements; the daily-summary line. Do not cut the calendar hold, the end-of-run settle, the guarded diff review or the hostile tests. If those do not fit, defer the whole item to 2.7.1.
