# Sprint: live vault readiness (v1.0.0 Beta)

Branch `sprint-live-vault`, worktree `../creaite-live`. Refreshed from `main` on 2026-10-08, after every sprint to date had merged. Nothing else is running, so this sprint may touch any file.

## Goal

Alan creates his first live vault from the v1.0.0 release zip, cleanly and repeatably, in a folder he chooses at install time. The 1.0 release notes are ready.

## Decisions (Alan, 2026-10-08)

- **New vaults use the creaite standard theme.** This repo's own `settings.json` uses Brightwater and carries other trial choices; none of them ship.
- **v1.0.0 is a pre-release (Beta).** It becomes a full release after the trial.
- **No full code review before release:** it costs too many tokens. The tests and a click-through from a fresh vault are the gate.
- **Folder chosen at install time:** an argument, or asked for when left out. Synced folders (OneDrive, iCloud) are refused.

## Items

Commit each separately.

### 1. Clean defaults and starting files (`system/templates/`, shipped in the engine)

- **`settings-defaults.json`:**
  - every key the code uses, with neutral values: theme System, palette creaite standard, an empty identity, no dismissed reminders, no people, no saved views, no remembered series;
  - `build_release.py` ships it as the zip's `system/config/settings.json`, so updates add new keys with default values;
  - a test checks it has every key path this repo's settings have (data maps such as `prep.series` excepted).
- **Starting files for a new vault:**
  - `project-register-template.md`, `portfolio-template.md` and `schedules-template.md`: the current files with their sample rows removed;
  - `vault-gitignore`: for the vault's local git, so the database, Excel export, backups and history stay out of it (change control).

### 2. Create a new vault

**How it's started:**
- `python3 creaite-1.0.0.zip [folder]`: the release zip is runnable. A `__main__.py` at its root loads `update.py` from inside the zip and calls `new_vault`.
- `update.py new-vault <zip> [folder]` does the same from an existing install.

**What `new_vault` does:**
1. **Check the target:**
   - asks for the folder when none is given, suggesting `~/creaite`;
   - refuses a folder that exists and isn't empty;
   - refuses one inside OneDrive, iCloud Drive or `Library/CloudStorage`;
   - checks every checksum (`read_release`).
2. **Install and seed:**
   - writes the engine files and the two merged files;
   - creates the folder map from `paths.py`;
   - writes the starting files: root `CLAUDE.md`, the project register, people register, `PORTFOLIO.md`, `schedules.md`, `processed.txt` with its header, and `.gitignore`;
   - keeps the zip in `system/releases/` and writes `installed.json`, so later updates know what shipped.
3. **Build and check:** runs `tracker.py init`, `build_dashboard.py` and `doctor.py` in the new vault.
4. **Print the next steps:** open the folder in Claude Code and say "setup"; start the live server.

**What it never writes:** `dev/`, `.creaite-dev`, `system/branding/`, sample projects, the database or demo data. The zip doesn't hold them, and the install refuses anything outside the engine.

### 3. Release zip check (`dev/tools/build_release.py`)

- The zip holds:
  - `__main__.py`;
  - the engine, including the new templates;
  - `settings.json` built from the defaults;
  - `.claude/settings.json`;
  - `VERSION`.
- Nothing from `paths.DATA` or `dev/`.

### 4. `doctor.py`: new vault

Warnings, not failures:
- the project register has no projects yet;
- `identity.name` is empty;
- the root `CLAUDE.md` still has an empty "Role:".

Each warning says the fix in plain words ("say setup").

### 5. First install: cx-setup and `dev/SETUP.md`

- **cx-setup** gets a "first install" path for a vault made by `new_vault`. It asks before each change, in this order:
  1. git init;
  2. identity (name, short forms, own domains);
  3. the Microsoft 365 connection;
  4. the project register;
  5. the people register;
  6. memory files (Step 5b);
  7. the live server;
  8. an optional schedule.
- **`SETUP.md`** gets a "First install" section:
  - download the attached `creaite-1.0.0.zip`, not "Source code (zip)";
  - run it with `python3`, choosing a folder outside OneDrive and iCloud;
  - then follow the existing checklist.

### 6. Sample week in the demo calendar (hand-off from sprint-meetings)

`dev/tools/demo_data.py` writes a sample week in `calendar.json`, with event IDs and Teams flags, so the Inbox's Meetings section shows rows in the demo.

### 7. Release notes

`dev/release-notes/1.0.0.md` (tracked; `dev/releases/` is for local zips and is ignored), written for Alan as the person installing it:
- what's in 1.0;
- what you need;
- how to install, and how to update later;
- known limits:
  - Beta;
  - not yet proven on real data;
  - local only;
  - the live server needs starting by hand;
  - loading transcripts from meetings is the next release (BL-42 phase 3).

Kept short, in British English.

### 8. Tests (`dev/tests/test_new_vault.py`)

1. Build a release zip into a temporary folder and create a vault from it, both with `python3 <zip> <folder>` and with `new-vault`.
2. Check the vault:
   - `doctor.py` passes, with its new-vault warnings;
   - no `dev/`, `.creaite-dev`, sample projects or demo data;
   - the database is empty, but has every table, including workstreams and search;
   - settings are clean: creaite standard theme, empty identity;
   - the registers have no rows.
3. Reinstalling the same zip with `--reinstall` keeps the data.
4. Refusals:
   - a non-empty folder;
   - a synced folder;
   - a bad or changed zip;
   - "Source code (zip)".

The full suite must pass: `python3 dev/tools/run_tests.py`.

## Done when

- Every item is committed on `sprint-live-vault` with the session's attribution lines, and `dev/BUILD.md` has a short "Live vault readiness" section.
- The suite passes.
- A vault created from a locally built zip opens, sets up and shows an empty dashboard.
- Never push. Alan publishes the release.

## Hand-offs

(None: nothing else is running.)
