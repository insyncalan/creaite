# #300 Start creaite when I sign in: guarded proposal

For Cap / Jarvis to review and apply. Built and committed on branch `v261-300` (no guarded file touched): `launch.py agent status --json`
(`agent_state()`), Health's suggestion (`health.py`), the page (`system/templates/dashboard/src/autostart.js`, Settings card beside Stop,
Today's first-run question; the Terminal commands are in Help › Fix a stopped server, drawn by autostart.js with the user's own folder), the cx-setup step, tests (`dev/tests/test_autostart_300.py`).

## What is guarded and not built: `live_server.py` (`live_server.diff`)

Two token-checked POST routes, dispatched with the set-up routes (`SETUP_ROUTES.update(AUTOSTART_ROUTES)`), so `do_POST` is unchanged:

- `/api/autostart/status {}` -> `{ok, supported, installed, loaded, on, dev, folder}`, from `launch.py agent status --json` (read only).
- `/api/autostart/set {on: bool}` -> installs or removes the login agent (`launch.py agent install|remove`) under the job lock, then
  re-reads the state and answers in words (`message`), never the script's text. Refused (`ok: false`, plain words, nothing changed) while an ask creaite run is in progress or marked: `autostart_run_blocks()` reads `reach.RUN_FILE` (system/guard/run.json) and fails closed, so a file that is there but unreadable or unparseable also refuses; no file, or `{}`, goes through. Not a bool: 400. Development copy or not macOS: `ok: false`, a plain reason.

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
