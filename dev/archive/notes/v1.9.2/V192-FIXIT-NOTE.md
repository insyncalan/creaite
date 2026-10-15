# v1.9.2 · BL-320: Fix it routes and update.py's after-update steps

Branch `v192-fixit`. Team 1 started it and paused it mid-task (`7170c67`, "WIP … not tested"). Another agent took it over on
14-10-2026, with Alan's approval, and finished it. The branch merges `origin/main`. It does not merge `origin/v192-settings-server`:
the fix map is keyed by that branch's check ids, read from its `health.py` and `doctor.py`. No page changes.

Alan's guard decisions (BL-320, 14-10-2026; commit `daf54fa`):
1. Each Fix it calls a fixed live-server route. The route runs exactly one known command, takes no arguments from the page, shows
   what it will do first and logs it. The Microsoft 365 reconnect only opens Claude's connector page.
2. update.py runs the after-update steps itself, reporting each one and rolling back on failure.

## What Team 1 had

- `system/scripts/health_fixes.py`, new:
  - five fixes (`launcher`, `rosetta`, `icon`, `m365`, `offsite`);
  - `run_fix()` and a log (`system/staging/health-fixes.jsonl` and the debug log);
  - a check-to-fix map keyed by doctor's function names and printed names.
- `launch.py`, new commands:
  - `make-launcher --if-present`: makes again only the launchers that already open this vault;
  - `refresh-icon`: writes `system/staging/app-icon.json`, so the manifest's icon addresses get a new `?v=`;
  - `restart`: sends SIGUSR1 to this vault's running live server, found through `system/staging/live-server.json`. It checks that
    the pid, the port's `/health` and `ps` all agree before it signals.
- `live_server.py`:
  - `POST /api/health/fixes` and `POST /api/health/fix/<id>`. Both are token-checked. A body or a query string is refused. The fix
    runs under `LOCK`.
  - The manifest's icon addresses are versioned.
  - The server writes `live-server.json` and restarts in place on SIGUSR1, once `busy()` is false.
- `session.py backup`: makes today's daily backup if it is missing, then the OneDrive copy.
- `update.py`:
  - `AFTER_STEPS` and `after_update()` run after doctor inside `install`'s try block, so a failed step rolls the update back.
  - The "Restart the live server" line is dropped when the server was asked to restart.
- `reach.py`: `session.py backup` was classified as `record`.
- `test_update.py`: the install test now asserts each step's line and an in-place restart (same pid, new token).
- Nothing was tested. The live server didn't start in any test vault, because `health_fixes.py` wasn't copied into it.

## What was finished

- **Test vaults:** `dev/tests/test_tracker.py` now copies `health_fixes.py`. This was the cause of every failing launcher and
  update test.
- **Fix map keyed by health.py's check ids:**
  - `CHECK_FIXES` maps each check id to its fix and the words in the check's detail that mean the fix applies:
    - `launcher_vault` → `launcher`, when the detail says "opens another vault";
    - `python_version` → `rosetta`, when the detail mentions "Rosetta";
    - `offsite_backup` → `offsite`, when the detail says "no copy yet" or "days ago". A "can't write" detail has no fix, because a
      copy can't mend it.
  - `fix_for(check_id, detail)` returns the fix id or None.
  - `STANDALONE = ("icon", "m365")` are the fixes no doctor check can see.
  - `catalogue()` returns `{fixes, checks, standalone}`. Each fix carries `built: true`, a `button`, a `does` line and either its
    `command` or its `url`.
- **`session.py backup`:**
  - It no longer copies twice or reports the wrong thing after making today's backup.
  - Its dispatch is `argv[:1] == ["backup"]`, so `test_record_commands` can see it.
  - It is reclassified as `derived` (see the security changes below).
- **Lint fixes for `check.py`:**
  - a reason comment on each swallowed exception;
  - no `except Exception: pass`;
  - `update.main`'s complexity is back under its limit, with the new `restart_hint()` taking the extra branch.
- **Restart:** the restart keeps the server's own arguments (`execv` with `sys.argv[1:]`).
- **Docs:** the two routes and SIGUSR1 are added to live_server.py's route list.
- **Tests:** the new tests are listed under Tests below.

## Each Fix it and its command

Every route is `POST /api/health/fix/<id>`. The body must be empty and the address must have no query string. The route needs
this run's token and runs under the job lock. Each run is logged as one line `{at, fix, ok, code}` in
`system/staging/health-fixes.jsonl` and as one line in the debug log (area `health`). The page gets `{ok, fix, message[, url]}`;
the message is the command's last line. `POST /api/health/fixes` lists all of them first, read only.

| id | Mends (health.py check id) | Runs |
|---|---|---|
| `launcher` | `launcher_vault`: the launcher opens another vault | `system/scripts/run launch.py make-launcher --replace` |
| `rosetta` | `python_version`: Rosetta, or an old launcher | `system/scripts/run launch.py make-launcher --if-present` |
| `icon` | none (Health offers it on its own): Chrome's copy shows an old icon | `system/scripts/run launch.py refresh-icon` |
| `m365` | none (Health offers it on its own): Microsoft 365 not connected | Nothing runs: returns `https://claude.ai/settings/connectors` for the page to open |
| `offsite` | `offsite_backup`: no OneDrive copy yet, or an old one | `system/scripts/run session.py backup` |

Not built, because the decision doesn't cover them (Health keeps `built: false` and the manual step for these):
- `tracker.py migrate`: it changes the record;
- reinstalling the release: it replaces the engine;
- `permissions.py` and `.claude/settings.json`: permission files;
- cx-setup: set-up steps.

"Run doctor" needs no fix, because Health's Check again already runs it.

**After an update** (`update.py install`, inside its rollback):
1. `launch.py make-launcher --if-present`
2. `launch.py refresh-icon`
3. `launch.py restart`

Each step is reported as "Launcher: …", "App icon: …" and "Live server: …". The first step that fails raises an error, and the
install rolls back.

Doctor already runs inside `install`. Health's own check after an update is the page's job, on Team 1's side.

The new steps take effect from the update *after* 1.9.2 is installed. That is because the installed (older) `update.py` runs the
install.

## Security changes for Team 1 to confirm

1. **`reach.SCRIPT_COMMANDS["session.py"]` gains `"backup": DERIVED`.**
   - `test_record_commands` requires every command a script dispatches to be classified.
   - Team 1's WIP had classified it `RECORD`, which would have changed the pinned list in
     `test_the_record_commands_are_the_ones_alan_named`.
   - `DERIVED` is the same class as `session.py start`, which already makes the same daily backup and OneDrive copy at every
     session start. So this command gives ask creaite no new reach, and the pinned record list is unchanged.
   - If Team 1 would rather have `record`, that needs Alan's yes, because it changes a pinned list.
2. **No other security list or pinned expectation changed.**
   - `launch.py` stays `{"": RECORD}` and stays on `_script_refused`, so ask creaite can never run any fix command for launchers,
     icons or restarts. `test_ask_creaite_still_cannot_run_any_fix_command` asserts this.
   - The fix routes are dashboard-only. They need the page token, which ask creaite never has.
   - No permission file, allow list, never list or deny list changed.
   - Nothing touches Microsoft 365 or the record.
3. **New effects outside the vault, all covered by decisions (1) and (2):**
   - `make-launcher` writes `~/Applications/creaite.app`. With `--if-present` it can also write `/Applications`, but only for a
     launcher that already opens this vault.
   - `session.py backup` writes to the OneDrive backup folder.
   - `restart` signals only this vault's own server, after checking its pid, port and process.

The guard tests passed unchanged: `test_guard_pinned`, `test_reach`, `test_record_commands`, `test_script_policy`,
`test_run_read_pinned` and `test_permission_panel`.

## Tests

- `dev/tests/test_health_fixes.py` (new, 25 tests), all in a temporary vault with a temporary HOME:
  - The catalogue is pinned: the five fixes and their exact commands. No fix is a record, permission or Microsoft 365 command.
  - The check-id mapping, with each detail case.
  - ask creaite is still refused every `launch.py` fix.
  - The routes, through a real live server:
    - no token: 403, and nothing runs;
    - a body, a query string or an unknown id: refused, and nothing runs;
    - a GET runs nothing.
  - Each fix working, and each with a forced fault:
    - `launcher` replaces another vault's launcher. Fault: `~/Applications` is a file.
    - `rosetta` remakes only this vault's launcher and leaves another vault's alone. Fault: the old app can't be removed.
    - `icon` gives the manifest new icon addresses, and those addresses still serve the PNG. Fault: the stamp can't be written.
    - `m365` returns only the URL.
    - `offsite`, through the route, with the projects in the vault.
  - `session.py backup` with a fake OneDrive: it makes the copy; run again, it reports already up to date; with OneDrive
    unreachable it fails; with daily backups off it makes nothing.
  - `after_update`: the steps run in order with their lines; a failed step raises and stops the rest; `restart_hint()`.
  - `launch.py --if-present` and `restart` with nothing to do. A stale `live-server.json` is never signalled.
- Passed: the six guard tests, `test_update`, `test_app_launcher`, `test_security_headers`, `test_live_server`,
  `test_debug_log*` and `test_health_fixes`.
- `python3.14 dev/tools/check.py`: `check: OK`.

## For whoever merges `v192-settings-server`

- `health.py`'s `fix_for(kind)` should consult `health_fixes.fix_for(problem["id"], detail)`. When it returns an id, put
  `health_fixes.describe(id)` (with `built: true`) in the problem instead of the `built: false` entry. Also offer
  `health_fixes.STANDALONE` on their own.
- Both branches add a script to `test_tracker.py`'s copy list. Keep both entries.
- Add `health_fixes.py` to the scripts row of `system/creaite-rules.md`'s folder map when that row is merged. It is left out here
  to avoid a certain conflict with Team 2's edit to the same row.
