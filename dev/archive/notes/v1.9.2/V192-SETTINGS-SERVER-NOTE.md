# v1.9.2 · BL-320 server side: settings catalogue, Reset, Health

Branch `v192-settings-server`, from `origin/main` (`2c4c42f`). For Team 1. Server side only; no page changes, no golden changes.

## What was built

- **`system/scripts/settings_catalogue.py`** (library, no command line):
  - The catalogue: each of the 132 settings in `settings-defaults.json` has a group, a tier (`essentials` or `advanced`; `developer` exists but is empty, since no development-only setting exists yet), a label, one line on what it does, and the reason for its default. The defaults' values stay only in `settings-defaults.json`.
  - The Essentials are 16 rows in six sections, taken from the accepted mockup. They cover 30 keys, because the sweep's sources and the AI drafts switches are one row each. The other 102 settings are Advanced, in 17 groups.
  - Each setting reports whether it is changed (its value differs from the default; order is ignored for lists where order means nothing) and when it was last changed (from `settings-log.jsonl`). The catalogue also counts the settings never changed once the log is over 30 days old (`retire_candidates`).
  - `reset(keys)` saves through `save()`, the same steps as the dashboard's `writeSettings`:
    - a backup in `system/backups/settings-<stamp>.json`;
    - the whole file written with two-space indents;
    - one compact `{at, key, old, new}` line per key in `settings-log.jsonl`.
  - Reset refuses unknown keys and set-up-only keys before writing anything (`FIXED`: folders and OneDrive, the port, `live_mode.required`, `assistant.enabled`, `excel.export`, and the old people and workstream lists). A key already at its default writes nothing.
- **`system/scripts/health.py`** (library):
  - It runs doctor in a child process with `--read-only --json`.
  - It returns only the problems: failures first, in plain words, each with the Fix it it would offer, marked `built: false`, and the manual step meanwhile (`how`).
  - It also returns the count of checks that passed, and the errors that kept coming back but have stopped (BL-263).
- **`doctor.py`:**
  - `--read-only`: the four write probes (`writable`, `search_index`, `debug_log`, the OneDrive copy folder) check permissions with `os.access` instead of writing test files, and create no folders.
  - `--json`: prints one object instead of the lines.
  - Without flags, the output is unchanged. The checks now run from `run_checks()`.
- **Routes in `live_server.py`** (token-checked like every POST; dispatched through `SETUP_ROUTES`, so `do_POST`'s complexity is unchanged):
  - `POST /api/settings/catalogue`
  - `POST /api/settings/reset {key | keys}`: answers 200 `{reset, unchanged, catalogue}`, 403 when refused, 400 with no key.
  - `POST /api/health`: runs only if the read allow list already permits `doctor.py`, as BL-166 does.
- **Docs:** `dev/dashboard-spec.md` (new section, "Settings, calmer, and Health: the server side"), and the scripts row of `system/creaite-rules.md`'s folder map.

## Fix-its NOT built (BL-141 guard decisions for Alan)

Each would run a command, change a permission, write outside the vault or touch Microsoft 365. Health shows each one with `built: false` and the manual step.

| Problem (doctor check) | Fix it would run | Why it waits |
|---|---|---|
| Launcher opens another vault (`launcher_vault`); Python under Rosetta or an old launcher (`python_version`) | `system/scripts/run launch.py make-launcher --replace` | A command that writes to `~/Applications`. `launch.py` is on no allow list (RECORD in `reach.SCRIPT_COMMANDS`) |
| Chrome's copy shows the old icon (no doctor check yet) | A change to the manifest's icon URLs (new icon file names), so Chrome offers its "app icon changed" update | Changes what the installed app is. It needs a doctor check first, then a decision |
| Microsoft 365 not connected (no doctor check; `setup/status` only knows "swept") | Open Claude's connector settings (a URL or app open); creaite can't sign in | Touches Microsoft 365 |
| No backup copy in OneDrive yet (`offsite_backup`) | `tracker.offsite_copy()`, which copies the newest daily backup into the OneDrive folder | Writes outside the vault |
| Database or search index needs repair (`database`, `search_index`) | `system/scripts/run tracker.py migrate` | Changes the record (RECORD, BL-267) |
| Bundled libraries, version file or script imports (`vendored`, `vendor_manifest`, `version`, `scripts_use_paths`) | `update.py install` of the installed release again | Replaces the engine |
| ask creaite's permissions or guard (`assistant_permissions`, `assistant_guard`) | An edit to `.claude/settings.json` (`permissions.py`) | Changes a permission file |
| Set-up not finished, config file missing, people register, old workstream lists, rules import (`new_vault`, `config_files`, `people_register`, `workstreams_moved`, `rules_imported`) | The cx-setup skill | Set-up steps change files |
| **After every update** (BL-320 §4; `update.py` not touched) | 1. `launch.py make-launcher --replace` for this vault. 2. Ask Chrome to refresh its copy (the manifest change above). 3. `doctor.py --read-only --json` once, with the problems shown in Health | Changes what an update does. Steps 1 and 2 write outside the vault |

Everything else (writable folders, online-only files, a synced vault, missing project folders, repeating errors, minutes without a draft) is a step only Alan can take, and Health says so.

## What the dashboard UI needs (Team 1)

- **Settings opens on Essentials.**
  - Draw `essentials` in order by `section`. Each row shows its `label` and `line`, and a control for its `keys`, read from `settings` by key. Multi-key rows: the sweep's sources are five switches; AI drafts is one switch that sets every `drafting.*` boolean (the per-kind switches stay in Advanced).
  - Save each change with `writeSettings`, as now.
- **Advanced:**
  - Lists `settings` where `tier === "advanced"`, grouped by `groups`, searchable by `label`, `line`, `reason` and `key` (the old key).
  - Shows `fixed_why` instead of Reset when `resettable` is false.
  - **Developer** appears only when a `developer` setting exists.
- **Dots, Show changed only and Reset:**
  - Show a dot where `changed` is true, and on a row when `essentials[i].changed`.
  - Show changed only filters on `changed`.
  - Reset posts `/api/settings/reset {key}` (or `{keys}` for a multi-key row), then redraws from the answer's `catalogue`. Update `S` too, or reload the data, so open views pick up the change.
  - On a 403, show the message.
- **Health, a section of Settings:**
  - Post `/api/health` on open and on Check again. It takes a few seconds, so show a spinner.
  - One line per `problems[i]` (`title`, `detail`), with `fix.button`. While `fix.built` is false, it opens `fix.how` (with Copy where `how` is a command). Never run `would_run`.
  - Fold the rest into "`fine` checks fine". List `stopped` as "stopped" lines.
  - Keep Diagnostics' Copy diagnostics.
- **The count on Settings in the rail:** `problems.length` from the last Health check. It needs a cheap source (a cached last result, or a check at start-up); nothing polls yet.
- **Help:** shrink Settings' help to match.
- **BL-254:** the Settings snapshots need updating with Alan's agreement.

## Alan's decisions, applied (14-10-2026, via the Product Manager)

- **Close the day from 17:30:** `day.close_from` defaults to `"17:30"` (was `null`, off), as the accepted mockup has it. The catalogue's reason says why; `test_close_day.py` asserts the new default.
- **Week ahead stays Urgent only:** `dashboard.week_ahead_priorities` defaults to `["Urgent"]`, unchanged. Alan, 14-10-2026, replacing his earlier decision the same day to take the mockup's Urgent and High.
- **Existing vaults keep their own values:** an update only adds missing keys (`update.merge_new`), so a saved `close_from` (including `null`) or a saved priorities list is never overwritten. `test_update.TestNewDefaultsKeepSavedValues` checks both ways with the real defaults file.
- Help (Close the day), the Advanced row's hint, `ask.js`'s comment and `dev/dashboard-spec.md` now state the new defaults. One golden re-recorded on purpose: `settings-system` (BL-254), only the Advanced row's hint, now "Empty: no nudge. The default is 17:30". The values shown didn't change: the test vaults use the committed sample `settings.json`, which has neither key.

## Open points for Alan

- **"critical" in Week ahead:** BL-319 reads it as High; that still needs Alan's confirmation.

## Tests

- `dev/tests/test_settings_catalogue.py` (new, 14 tests):
  - Catalogue coverage both ways, entries written out, the Essentials' shape.
  - "Changed" with a missing key and with reordered lists.
  - Reset in a real temporary vault: backup content and name, log lines, no write when already default, refusals writing nothing.
  - Health mapping, every doctor check having plain words, and `doctor --read-only` creating nothing while the usual run is unchanged.
  - The three routes through a real live server, with and without the token.
- `dev/tests/test_tracker.py`: the test vault copies the two new scripts.
- Results:
  - `run_tests.py -j 2 --quick --changed`: 56 passed, 0 failed.
  - Run by name: `test_setup_dashboard`, `test_debug_log*`, `test_new_vault`, `test_portability`, `test_script_policy`, `test_minutes_draft`, `test_app_launcher` and `test_onedrive_projects`, 10 files: all passed.
- `python3.14 dev/tools/check.py`: `check: OK`.
