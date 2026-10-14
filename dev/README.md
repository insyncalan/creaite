# creaite

creaite is a personal portfolio reporting system. It reads meeting minutes, Teams transcripts, Outlook mail and Teams chats, and proposes actions, decisions, risks and issues for your approval. It keeps the record in `tracker.db`, lets you edit it in `tracker-view.xlsx`, and shows everything in `dashboard.html`.

Everything lives in this folder: data, memory, skills, scripts and history. To move creaite to another computer, copy the whole folder.

## Setup on a new machine

1. Install the Claude desktop app and sign in.
2. Install Python 3. All other libraries are bundled in `system/scripts/vendor/`.
3. Open this folder in the Code tab, reconnect Microsoft 365, and say **"setup"**. The full checklist is in `dev/SETUP.md`.


## What's in the root

- `dashboard.html`: open in Edge or Chrome.
- `tracker-view.xlsx`: browse, edit and review in Excel.
- `inbox/`: drop files that don't yet have a project.
- `projects/`: one folder per project, plus `_portfolio/` for cross-project material.
- `system/`: the engine. Don't edit it by hand.
- `dev/`: build and design material (this file).

## Daily use

Say "review", approve, then say "apply". The rest is in `CLAUDE.md`.

## Development tools (BL-240)

`dev/Brewfile` lists the tools used to build and test creaite: `gh`, `git` and the Python the tests run on (3.14). Install them with `brew bundle --file=dev/Brewfile` (Homebrew in `~/homebrew` needs no admin rights). They are for development only: creaite itself runs with Python 3.9 or later and nothing else, and the Brewfile is never in a release zip.

## Running the tests

`python3 dev/tools/run_tests.py` runs every file in `dev/tests/` in parallel (about 2 minutes, against over 10 one by one) and prints each file's result, then the end of any failure's output. `run_tests.py people` runs only the files whose name contains "people"; `-j 4` sets how many run at once. Each file builds its own throwaway vault, but some read the repo's sample data (for example `projects/_portfolio/people-register.md`), so uncommitted test edits there can fail them.

`run_tests.py --changed` runs only the files that can reach what you changed since `main` (`--list` shows them without running; `--deep` follows every import, which for an engine script is the whole suite; `--flaky` lists files that failed under load and passed alone). Quick selection can miss a dashboard test when you change a script the dashboard imports, so the full run still comes before a merge.

## Development commands

`dev/justfile` lists the everyday commands: `just -f dev/justfile` shows them all (from `dev/`, plain `just`). `test`, `test-only`, `test-changed`, `test-list`, `flaky`; `check`, `check-fast`, `report`, `baseline`, `watch` (reruns the fast check on every save); `types` (pyright, advisory), `ruff`, `dead` (vulture); `dashboard`, `serve`, `doctor`; `db` and `db-query` (the database opened read-only, so a query can never write: only `tracker.py apply` writes). Test recipes run at `-j 3`, because other sprints test on this machine at the same time. The tools (`just`, `watchexec`, Biome from Homebrew; ruff, vulture, coverage, pyright, sqlite-utils from `uv tool install`) are for development only; creaite never needs them.

**Sharing the machine (BL-246, Alan 11-10-2026).** Several worktrees and sessions test at once, so the runner keeps them from starving each other and from filling the disk. Each test file is in the quick tier or the Chrome tier, read from the file itself; `--quick` runs the quick tier alone and `--list` marks the Chrome files. Chrome files run under a **machine-wide cap of 3** (`CREAITE_CHROME_CAP`), shared by every run on the Mac through lock files in `/tmp/creaite-chrome-slots`; a run that crashes, is stopped or is killed lets its slots go at once. Each file gets a **private temporary folder** (`/tmp/cr<pid>/<n>`) for its vaults, Chrome profile and fake home, removed when the file ends, pass or fail; Ctrl+C or a stopped task ends every test still running, with its live server and Chrome, and removes the run's folder; a run killed outright is cleaned up by the next run. Stop a run by its PID, never with `pkill` by name: that ends other people's runs too.

**No orphans (BL-247).** Every live server and headless Chrome a test starts ends when its test ends, however it ends. `dev/tools/proc_guard.py` starts each in its own process group with a small watchdog: the test's clean-up stops the group; so do exit, Ctrl+C and SIGTERM; and if the test process is killed outright, the watchdog sees its parent go and stops the group itself. The runner starts each test file the same way and, when the file ends, stops anything it left in its group (a server started with a plain `Popen` included), so killing a runner mid-test leaves nothing running. `run_tests.py --clean` (and the start of every run) stops orphaned test servers and Chromes, meaning parent gone and running over 15 minutes, only when they run from a temporary test vault or a test Chrome profile (never your own browser or live server). It also removes `creaite-test-*`, `creaite-cdp-*` and `creaite-chrome-*` folders that nothing has changed for an hour and nothing has open.

**Screen snapshots (BL-254).** `test_snapshots.py` compares every screen's HTML with its golden in `dev/tests/snapshots/`; record them again on purpose with `run_tests.py --update-snapshots [screen …]` and say why in the commit (`dev/BUILD.md`).

## Static check

`python3 dev/tools/check.py` (standard library only, about 3 seconds; 6 with the Chrome compile of the dashboard's script, `--no-js` skips it). It fails on a syntax error or invalid escape, grammar newer than Python 3.9 in `system/scripts`, an unused import (mark an intended one `# noqa: F401`), a name that is never defined, a function defined twice and a bare `except:`. It also holds the numbers in `dev/check-baseline.json` where they are: a function's complexity and length, long lines, `except Exception: pass`, missing docstrings, and the dashboard script's `innerHTML` and empty `catch` counts. A number may fall, never rise; a new function may score at most 15 and run at most 100 lines. After you improve something, `check.py --update-baseline` records it (it refuses to raise a number; `--allow-worse` is for a deliberate decision). The pre-commit hook runs it as advice and never blocks a commit. Development tools may be installed on this machine (Alan, 11-10-2026), but nothing in `system/` may depend on them.

To run it after every edit in a Claude Code session, put this in `.claude/settings.local.json` (not the shared `settings.json`): `{"hooks": {"PostToolUse": [{"matcher": "Edit|Write", "hooks": [{"type": "command", "command": "python3 dev/tools/check.py --no-js | tail -n 8"}]}]}}`.

