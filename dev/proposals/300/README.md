# #300 Start creaite when I sign in: guarded proposal

For Cap / Jarvis to review and apply. Built and committed on branch `v261-300` (no guarded file touched): `launch.py agent status --json`
(`agent_state()`), Health's suggestion (`health.py`), the page (`system/templates/dashboard/src/autostart.js`, Settings card beside Stop,
Today's first-run question; the Terminal commands are in Help › Fix a stopped server, drawn by autostart.js with the user's own folder), the cx-setup step, tests (`dev/tests/test_autostart_300.py`).

## What is guarded and not built: `live_server.py` (`live_server.diff`)

Two token-checked POST routes, dispatched with the set-up routes (`SETUP_ROUTES.update(AUTOSTART_ROUTES)`), so `do_POST` is unchanged:

- `/api/autostart/status {}` -> `{ok, supported, installed, loaded, on, dev, folder}`, from `launch.py agent status --json` (read only).
- `/api/autostart/set {on: bool}` -> installs or removes the login agent (`launch.py agent install|remove`) under the job lock, then
  re-reads the state and answers in words (`message`), never the script's text. Refused (`ok: false`, plain words, nothing changed) while an ask creaite run is in progress or marked: `autostart_run_blocks()` reads `reach.RUN_FILE` (system/guard/run.json) **inside `START_LOCK`**, the lock every run start takes (review L3), and fails closed, so a file that is there but unreadable or unparseable also refuses; no file, or `{}`, goes through. The job lock is taken without waiting (as the Health fixes): "Something else is running". Not a bool: 400. **The open page's own call only (review L1):** `page_call(handler)` (loopback peer, `Sec-Fetch-Site: same-origin`, an `Origin` naming this server) as the Health fixes and the Notes moves, else 403 "Not allowed". **Logged (review L2):** `debuglog` area `autostart`: on, off, refused (a run is working) and failed (exit code and the state, never the script's text or a path). Development copy or not macOS: `ok: false`, a plain reason.

`git apply --check` passes on the base file; the reverse check passes after it is applied (both done). The proposal's routes are exercised
by `test_autostart_300.Proposal` against a stubbed launcher run.

## Guard questions for the reviewer

1. The guards are the token check every POST has, the run.json refusal above (tested: absent, in progress, marked, bad JSON, not a dict, unreadable), plus `launch.py` staying RECORD in `reach.SCRIPT_COMMANDS` (the guard hook refuses it in any
   ask creaite run) and `~/Library/LaunchAgents` staying on `reach.py`'s never list. No change to `reach.py` or `permissions.py` is proposed or
   needed.
2. `launch.py agent status --json` is a new argument form of an existing command: `{"": RECORD}` already covers it, so no `SCRIPT_COMMANDS` entry changes.
3. The page degrades until the routes exist: the card says "Not available yet", no switch, the Terminal commands in Help still work, Today's question is not shown.

## Not in this diff

Health's suggestion needs no server change: `health.py` reads `launch.agent_state()` itself. "Answer remembered" for the first-run question is kept
in the browser (`creaite-autostart-asked`), not in `settings.json`, to avoid a new settings key; the real state is always the agent itself.

## Review of #300 (22-10-2026): what changed

- **H1 (agent removing its own server).** `launch.py agent remove` now deletes the plist first, and does not unload the job when this process
  is the agent's own server (`XPC_SERVICE_NAME` equals the agent's label, which launchd sets): that unload would stop the server that is
  answering. `agent install` from the agent's own server likewise skips the unload and load (the new file is read at the next sign-in).
  `agent status --json` carries `own`; the route's reply for "off" from an agent-started server says "This copy keeps running until you stop
  it"; the page's confirm text no longer says it keeps running without saying which copy. Hand check still wanted on a real Mac:
  turn it off from an agent-started server, and from a hand-started one.
- **M1 (tests).** `dev/tests/test_autostart_300_routes.py` exercises the real routes through a live server (the diff applied to a throwaway
  copy when this tree hasn't it): token 403, Host 403, GET 404, not the open page 403, non-bool 400, run.json refusal (in progress, marked,
  unreadable, not a dict, bad JSON), dev refusal, on/off round trip, failure logged, the check inside START_LOCK, an agent-started server;
  and the launcher with a stub `launchctl` (own and not own). Mutants: each guard removed from a throwaway copy must turn its check red.
  `test_autostart_300`'s page test no longer lets the real status overwrite its stub.
- **Apply order.** 291 (`live_server.py.diff`, `update.py.diff`), then this one; it applies and reverses on top of both, and either side of
  the work-item-history diffs.
