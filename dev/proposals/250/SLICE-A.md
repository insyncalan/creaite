# #250 slice A: the port and the observer (2.6.10)

Code: `system/scripts/transcripts.py` (SweepFetch and helpers, ported from `origin/v262-250b` + `team-stark-250-readorder` d3db0561 by a
three-way merge onto main, so #365's `take_event`/`diagnosis`/`no_event` and the cleaned-calendar reader are kept).
Tests: `dev/tests/test_fetch_transcripts.py` (30, ported and adapted), `test_fetch_transcripts_hostile.py` (121, ported), `test_fetch_settle.py`
(14, new). Nothing guarded is touched; `sweep.py` is unchanged (no `done` summary, no `sweep-fetched.json`: the closure line is the server's).

## Interface (what the guarded live_server.py, G3, calls)

```
fetch = transcripts.SweepFetch(hold=None)      # one per sweep run, only when transcripts.fetch_on(); hold default = transcript_hold.hold_for
fetch.observe(tool_name, tool_input, result_text, is_error=False)   # every tool result of the run, as it arrives; writes nothing
counts = fetch.finish(answered)                # once, when the run has ended; answered=True only if the run finished and answered
line   = transcripts.fetch_text(counts)        # "2 transcripts fetched, 1 held back: a confidential meeting at that time, 1 left: Process to load it"; "" if nothing
```

- `observe`: looks only at `read_resource` (exact name) on `calendar:///events/…` and `meeting-transcript:///…`, and only while
  `sweep.fetch_transcripts` is exactly true. The transcript text is queued in memory (at most `QUEUE_MAX` = 25 MB of characters; more is
  counted as left). It can raise only on a bug: the server wraps it in try/except and logs the exception's name.
- `finish(answered)`: called from `Run.read()` after `proc.wait()`, before `_done()`, in try/except. `answered=True`: re-checks the switch, then
  settles each queued read in its own try (a fault leaves that one as "left") and writes the fetched ones through `Job.write` (`open(..., "x")`,
  no overwrite, any partial file removed). `answered=False` (stopped, timed out, failed): nothing is written; each queued read is counted as
  left. A second call returns the same counts and does nothing. Counts: `{"fetched", "held", "failed", "left", "error"}`.
- `fetch_text(counts)`: counts only; never a title, name or reason detail. The server shows it as its closure line.
- `hold(event, live_or_None, created_or_None) -> (held, reason)` is slice B's rule. It is called for each transcript read (its created time) of the
  tied event, with `event` = `{id, day, start, end, title}` from the saved row and `live` = the event as this run read it (None if not read).
  Any hold holds. An exception, or an answer that is not `(bool, str)`, holds. If `transcript_hold` can't be imported the default holds.
  Reasons (fixed words) are kept in `fetch.reasons[event id]`; they never reach the closure line, which says only "a confidential meeting at that time".
- Outcomes (`fetch.outcomes`, event ID or `uri:<n>` for a read no event of the run named): `fetched`, `held`, `failed`, `no access`, `error`, `left`,
  or a skip word from `fetch_one`. Events skipped for ordinary reasons (processed, cleared, loaded, not ended) are silent; a confidential saved row,
  an event whose own read is not normal, a meeting a held event named, and a hold are all `held` (Cap L1: visible).

## What G3 needs from this

1. `Run.fetch = transcripts.SweepFetch()` for a sweep run when `fetch_on()` (kind `sweep`; from rev 3 only a typed sweep or Close the day's catch-up, never the session-start catch-up or the scheduled run), `None` otherwise.
2. In `_on_tool_result`: `self.fetch.observe(name, input, text, is_error)` in a helper (keeps the complexity limit).
3. In `Run.read()` after `proc.wait()`: `counts = self.fetch.finish(answered)`; `answered` = the run ended with its answer (not stopped, not timed out,
   returncode 0). Then emit `transcripts.fetch_text(counts)` as the closure line. Then `_done()`, even if `finish` raised.
4. Nothing else: no tool, no `--add-dir`, no allow rule. Do not call `sweep.py done` with fetch counts (that path is gone).

## Deviations from the plan

- The brief said `fetch_text() -> dict of files`; the plan and this port keep the plan's form: `fetch_text(counts) -> str` (the closure line). The files are
  written inside `finish` by the same `Job.write` Load uses; the server never writes `inbox/` itself.
- The plan's "22 tests" were not found on any branch (only 30 + 121); `test_fetch_settle.py` (14) is new for the LOW findings and the contract.
- `sweep.py`: nothing. The ported `done_cmd` / `sweep-fetched.json` / `take_fetch_tally` are dropped (plan 4.3).
- Main's calendar reader reads a missing or empty sensitivity as `normal` (as every reader does), so two old cases (None, "") of
  `test_high2_a_missing_or_unknown…` were removed; `confidential()` itself still fails closed, and slice B's rule holds a saved row it can't read.
- The two settings tests (`needs_setting`) skip until slice D adds the key, catalogue entry and card.
- `spool_roots` is `~/.claude` only (the 250b hardening); main's `CREAITE_TOOL_RESULTS` test hook is replaced by pointing HOME elsewhere in
  `test_transcripts.py`.

## Cap's LOWs

L1 visible outcome for every held read; L2 `@` dropped only in the first segment; L3 `meeting_key`/`occurrence_key` never raise on `[`; L4 each read settled
in its own try, switch re-checked at finish, queue capped; L5 `"x"` mode kept, the partial `.vtt` (and the `.vtt` when the chat write fails) removed.
