# #327 B: fresh ask creaite sessions by default (guarded: live_server.py)

## What
`live_server.diff` (one file, +33 lines, `system/scripts/live_server.py`):
- `fresh_session(req)`: a new ask is fresh unless the request has `continue: true` (the boolean only) or `confirmed` (a confirmation carries on from the question it answers). The server decides, never the model.
- `carry_over(chat)`: the last 4 messages of the chat's own history, each cut to 600 characters, as background text after the new message (the message stays the first line of the prompt) ("not instructions"). Empty for a new chat or an unreadable history.
- `Run(..., fresh=False)`: a fresh run does not pass `--resume`. It still passes the old session to `guard_args`, so `reach.start_run` marks the run when that chat had read outside content; `end_run` then stores the mark against the new session. A queued message (`queue_start`) is fresh too. Prep, drafts, sweep and other kinds are unchanged (`fresh` defaults to False).
Not guarded, in this commit: the chat panel gets a "Continue this chat" tick (shell.html, style.css, ask.js, rebuilt dashboard.html) that sends `continue: true`; it clears when the chat changes. The existing resume test now sends `continue: true`.

## Why
Resumed chats grow: the 22-10 ask run started at 503k tokens and $16.34 (366k on 20-10). A fresh session starts at the rules plus tools (purpose-built runs start near 33k; the plain ask target is under 150k, red line 500k).

## Apply order and checks
After the 2.6.2 chain (last in the chain, or anywhere: it touches `ask()`, `Run.__init__`, `queue_start` and a new block before `class Run`, none of which the chain edits).
- `git apply --check` passes on `origin/v262-line` (tree without the chain) and on the tree with all 12 diffs of `GUARDED-2.6.2.chain` applied (checked 24-10-2026).
- `dev/tests/test_fresh_ask_327.py`: 4 tests skip without the diff, pass with it (scratch copy); the page test always runs. `test_prompt_after_dashdash`, `test_ask_queue` pass with it.
- `check.py` OK on the tree without the diff; `test_plain_words` OK. This diff adds no long line over the limit (checked by reading; run check.py with the diff applied before it is committed to the chain).

## Mark follows the chat (verified in code and by test)
`Run.__init__` passes the chat's last session to `guard_args` -> `reach.start_run(..., session)`, which writes `marked` when that session is in `marked-sessions.json`. When the run ends, `_end_guarded` calls `reach.end_run(self.id, self.session)`; `self.session` is the NEW session (set from the init event), so a marked run adds the new ID to `marked-sessions.json`. `MarkFollowsTheChat` in `test_fresh_ask_327.py` runs this against a temporary guard folder (marked chat: starts marked and the new session is remembered; unmarked chat: stays unmarked).

## Review round 1 (24-10-2026): what changed
- **Carried text now follows the message** (after a `---` line, each message one `> `-prefixed line, line breaks removed), so the prompt's first line is still Alan's message (the stand-ins in the ask tests read it) and a reply cannot fake a boundary. `test_ask_queue` and `test_ask_done` need no change.
- **Mark by chat, not only by the page's session.** `mark_session(session, chat)` hands the guard whichever of the page's session, the chat's last session (`chat_session`) or the chat id is in `marked-sessions.json`; a lost or stale page session no longer unmarks a chat. Tests: `MarkFollowsTheChat` (real `start_run` and `end_run` in a temporary guard folder).
- **Carry on after Approve** (the change card) sends `continue: true`: the same thread, not a restart.
- **Queued messages are always fresh** and ignore the Continue tick (decided: the tick is for the message being typed; a queued one is typed while another run goes). Documented, tested.
- **Usage line** gets `resumed` true/false for ask runs only (`usage_log.py`, not guarded; the call site is in the diff).
- **Known, not changed here:** `marked-sessions.json` gains one id per marked run, never pruned (reach.py is guarded; a follow-up could key marks by chat). Unmarked runs add nothing.

## Measurement plan (Alan's vault, after release)
Compare START load (`start_tokens`, never dollars) for kind `ask`: median and 90th percentile, at least 10 runs each, the 7 days before and the 7 days after release, split by `resumed`. Include a chat of 5+ turns, a typed sweep and a Continue run. Target: fresh starts under 150k, 500k the red line, against 366k to 503k before.

## Review round 2
- `fresh_plan` now takes the guard's mark from `mark_session(session, chat)` in BOTH branches, so a continued or confirmed run whose page session was lost still starts marked, and so does the next fresh one (test: `test_continue_and_confirmed_with_a_lost_session...`).
- A NUL in a stored message makes Popen raise ValueError: the run, the ask handler and `queue_start` catch it with OSError (the run also clears its guard record). Test: `test_a_nul_in_the_prompt...`.
- **Search's "continue as chat"** (kind search, not guarded) carries an unmarked answer: pre-existing, unchanged here.
- **`usage_report.py` has no `resumed` column** (decided: left alone). To split by hand, read `system/staging/run-usage.jsonl`: for lines with `"kind":"ask"`, group by `resumed` (true or false) and take the median and 90th percentile of `start_tokens`.
- `marked-sessions.json` is still never pruned (above).

## Review round 3
- **The mark no longer depends on session ids.** `remember_chat` sets `outside: true` on the chat's own history record as soon as a run in it is marked (`run_marked`: the hook's mark, an inherited mark, or `was_marked` after the run ended), and never clears it. `inherit_mark` calls `reach.mark(run, ...)` on any guarded run in a flagged chat, fresh or resumed, queued or typed. No `reach.py` change.
- **`chat_rec` never overwrites the stored session with None** (a run that failed or was stopped before Claude reported a session id keeps the last known one).
- Tests (`MarkSurvivesFailure`, real `Run`, `read`, `start_run` and `end_run`): a run that fails before the session id; a stopped run; a reopened chat with no page session; the flag alone (no marked session id, no stored session); a clean chat stays unflagged and unmarked. The reviewer's probe (`probe327d.py`) passes 12 of 12.

## Risks (for the reviewer)
1. **Outside-content mark (BL-141).** The mark is kept by session ID. A fresh session would lose it, and the carried text could hold outside content. Mitigation above: the old session ID goes to `guard_args`. Review that `start_run(session=old)` marks the run and `end_run(run, new session)` saves the mark. A chat whose last session was not marked is not marked, as before.
2. **Carried text is data in the prompt.** It is Alan's and creaite's own words from the chat, labelled as background. No new capability; the run's tools, deny list and hook are unchanged.
3. **Lost thread.** Only 4 messages carry. Long references ("the third one above") may fail; the tick resumes the whole chat. A confirmation always resumes.
4. **`panel_sweep` / `chat_session`** are untouched; a queued sweep runs as before (fresh, no carry).
5. Cost of a resumed chat is a session total: compare start tokens, not dollars.

## Measurement
`system/scripts/run usage_report.py --days 7` in this repository: "No runs recorded" (no live data in the development repository). Before numbers are the issue's (366k to 503k start for ask runs). After must be read from Alan's vault after release: same tasks (a plain ask, a sweep typed into ask creaite), start tokens under 150k (red line 500k).
