# v1.9.5: BL-326, ask creaite shows the ask, the activity and the outcome

Branch `v195-run-chat` (from `origin/release-193`, with `origin/dev-bl326-v210` merged for the backlog entry). Team 2, approved by Alan 14-10-2026. Not pushed.

## The defect

A run creaite starts itself (the Prep page first) showed in ask creaite as a chat: the prompt (`prep_page.PROMPT`, the meeting's context as JSON) as Alan's message, and Claude's JSON reply with the page's HTML in it. It appeared whenever the panel reattached to the run: on opening the page while it ran, or at the next load, because nothing acknowledged the finished run.

## What ask creaite shows now

For every run creaite starts (a run of the run engine whose kind isn't `ask` or `search`), wherever ask creaite shows it, exactly three things, for success, failure and Stop:

1. **The ask:** one plain line as if Alan had typed it (the run's label, never its prompt).
2. **The activity:** the working line and "✓ n steps", each step in plain words (`plain_step`).
3. **The closure:** one `closure` event with the outcome and a link into the dashboard, or what went wrong and what to do.

| Run (kind) | Started by | Ask line | Closure on success (link) |
|---|---|---|---|
| Prep page (`prep`) | Prep page button, BL-307's Go ahead, the Close the day prep queue | Prep page for ABC weekly, Thursday 15th October 10:00 | Saved the prep page in <project> › <folders> (Open: `#prep=…`) |
| Generate (`generate`) | Current state's Generate | Draft the current state for <project> | Drafted the current state … (Open: `#cockpit=CODE`) |
| Make it executive (`generate`) | Current state | Make the current state for <project> executive | Rewrote the current state … (`#cockpit=CODE`) |
| AI drafts (`generate`) | `/api/draft`: update, update-bulk, client, client-bulk, thinking, health, forecast, sharpen, agenda (Draft agenda), polish and polish-help (Polish), status-form, sneak-update | `drafts.RUN_LINES`, e.g. Draft client wording for ABC-A-001 | the kind's line (`#item=ID`, `#cockpit=CODE`, `#prep=…`, `#review` for a draft of several) |
| Shape this meeting (`generate` / `shape-closed`) | Prep page's Shape | Shape <meeting, day time> | Shaped the meeting … (`#prep=…`) |
| Draft from the message (`generate`) | an alert's Create work item | Draft an action from the message | Drafted the action from the message … |
| Transcript check and load (`check`, `load`) | Intake's Calendar Import | Check / Load the transcript of “…” (DD-MM-YYYY at HH:MM) | the job's own outcome (Intake: `#intake`) |
| Catch-up sweep (`sweep`) | Close the day | Catch-up sweep: mail and Teams since the last sweep | The catch-up sweep has finished … (Review: `#review`) |

Failure: "Couldn't finish: Claude Code stopped with a problem. Try again; if it happens again, Settings › Diagnostics has the details." (never the stderr line); a draft whose reply can't be read: "Couldn't finish: the draft couldn't be read. Try again."; a page that wasn't written: "Couldn't finish: the prep page wasn't written. …". Stop: "Stopped: nothing was saved. Start it again when you're ready." (the Prep page: "Stopped: no prep page was written. Press Prep page to start again."; the watchdog: "Stopped: nobody was watching for too long …").

**The VIP check** is not a run of the run engine (`vip_check` makes its own `claude -p … --output-format json` call) and never appears in ask creaite, so nothing changed there.

A chat Alan types, a typed sweep (BL-309) and a search answer are unchanged.

## How

- `live_server.py`: `Run.plain`; `_plain_setup` (the label is never the prompt; `PLAIN_ASK` when none is given; the debug log's start record); `plain_step` for the steps; `_closing`, `_closer`, `_close` (the closure event, the history entry, the end record); `failed` set by `_end_failed`; the `done` event of a plain run carries no chat or session. Each route gives its run a label and closure lines (`current_lines`, `transcript_ask`, `draft_lines`, `prep_run`). The Prep page is now built by the run's closer as it ends (`prep_close`, still the server's own write, `prep_page.build`, under `LOCK`); `/api/prep/build` and the prep queue hand that result on, and build as before only when a run has none. `remember_chat` takes `title`, `keep_session` and `extra`.
- `prep_page.py`: `long_day`, `ask_line`, `dated_key`, `closure`.
- `drafts.py`: `RUN_LINES`, `run_lines` (in `context`'s result as `run`), `run_closure`.
- `ask.js`: `attachRun` draws every run (no longer skips `generate`, `check`, `load`) and passes `run.plain`; `askStream(…, plain)` draws only steps, the closure, the cards and done; `runClosure` and the `[data-runhref]` link; `loadChat` draws a kept run's closure. `intake.js`: `jobLive` streams plainly. `meetings.js` (`prepPage`) and `projects.js` (`runGen`) ack their run. `CloseDay.jsx`: `cdSourceOf` also reads the plain step words.
- History: the day's runs go in one chat, `runs-YYYY-MM-DD` ("Runs creaite started, DD-MM-YYYY"), so they never push Alan's own chats out of the ten kept (BL-32): the ask as his message, the closure as the reply, the plain steps.

## Security

No change to the guard, the hook, `reach.py`, the tool lists (`READ_TOOLS`, `DENY_TOOLS`, `KIND_TOOLS`), the permission rules or the routes' checks. test_guard_pinned and test_reach pass unchanged. One behaviour moved: the Prep page file is written by the server in the run's reader thread as the run ends, rather than when the page posts `/api/prep/build`; it is the same function (`prep_page.build`), under the same lock, after the same checks (a stopped or failed run writes nothing).

## Tests

- New `dev/tests/test_run_chat.py`: through the real routes against a stand-in Claude (three tool calls with JSON results, then a JSON and HTML reply): the Prep page (success, failure, Stop), Generate, Make it executive, a draft (success, failure), Draft agenda, a transcript check and load, the catch-up sweep (success, Stop). Each has a plain label (not the prompt), plain steps, one closure just before done with no `{`, `<`, script, tool or prompt text, and a `#` link; the history file holds the plain lines only; the debug log has the run record and no text. Plain code: `plain_step`, and every draft kind's lines. In the browser: a Prep page run (success with the link followed, failure, Stop), a draft and a transcript check each draw exactly the ask, "✓ n steps" and the closure; the history chat draws the same; a typed chat is unchanged.
- `dev/tests/pinned/run_read/a_check_job_has_no_chat.json` re-recorded: a check job now ends with a `closure` event before `done` (reviewed; the other pinned streams are unchanged).
- Help (`system/templates/help.md`) and `dev/dashboard-spec.md` say what ask creaite shows for a run creaite started.
