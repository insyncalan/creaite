---
name: cx-setup
description: creaite setup, health check and repair. Checks the environment, database, bundled libraries, Microsoft 365 access and the docx skill; offers to restore the database (or the whole vault from a daily backup zip), create optional schedules, initialise git and tidy the root; rebuilds the dashboard and Excel export. Installs creaite updates from a release zip and undoes them. Use when Alan says "setup", "set up creaite", "check creaite", "health check", "repair creaite", "I've moved creaite to a new laptop", "update creaite", "update creaite from <file>", "undo update", "what version is creaite?", "restore creaite from backup", or when scripts or the sweep fail after the folder was copied or moved.
---

# cx-setup

Get creaite running on this machine, or repair it, using only what's in the vault plus Claude, Python and Microsoft 365. **Never delete or overwrite data.** Ask before making any change other than a rebuild.

**Projects by name (BL-101):** refer to a project by its full name in everything Alan reads (summaries, tables, messages, file names, drafts). The short code appears only inside a work item's ID (`ABC-A-003`) and in a command he can type; `tracker.project_label(code)` gives the name.

All paths are relative to the vault root (`system/scripts/paths.py`).

## First install (a vault made by new-vault)

When `doctor.py` shows **WARN First setup** (no projects, no name or no role yet), this is a new vault: run these in order, after the health check, **asking before each** and skipping any Alan declines. Each stands alone; Alan can stop and say "setup" again later.

1. **Git:** `git init`, then a first commit (local only, never a remote). The vault's `.gitignore` already keeps the database, Excel export, backups, history, release zips, `system/staging/` (ask creaite's chats and images, `vip.json`, the raw calendar, proposals), `system/logs/` and `system/branding/` out, because the daily backup zip carries the whole git history as a bundle: whatever is committed once is in every later zip and its OneDrive copy. The zip holds staging directly, minus the chats, their images, `vip.json` and the raw calendar.
2. **You:** ask Alan's name, the short forms people use for him (e.g. "Alan", "AC") and his company's email domains; show them, and on his yes save them with `system/scripts/run propose.py setting identity '{"name": …, "short_forms": […], "own_domains": […]}'` (written straight to settings, with a backup and a log line). Ask his role and fill "Role:" in the root `CLAUDE.md` (show before → after).
3. **Microsoft 365:** step 2 below. If it isn't connected, ask Alan to connect it, and carry on: minutes from `inbox/` work without it.
4. **Projects folder (BL-85).** Ask first: do Alan's projects live in a OneDrive folder (an Engagements folder, one folder per engagement), or stay inside the vault? If they stay, skip this step. Otherwise, one at a time, showing each result:
   1. Ask for the folder. Run `system/scripts/run locations.py check "<folder>"`. If it has a `refuse` (a personal OneDrive such as `OneDrive-Personal`, or another sync service), say why and stop: only the company OneDrive or a plain local folder may hold project files, never personal cloud storage. If it isn't reachable, ask Alan to check OneDrive is running and signed in. Note its `tenant`.
   2. Run `system/scripts/run locations.py inspect "<folder>"` and show Alan what it found: the template (`_Templates/_Skeleton`, else the first engagement), the engagement folders, and the `folders` mapping it proposes (transcripts, minutes, weekly reports, client reports, ad hoc documents, current-state images). Where a name is ambiguous it lists candidates: ask which. Alan's decisions: client reports file to `04 Reporting/Weekly` with the weekly reports (`04 Reporting/Steerco` is separate and creaite never writes to it), and current-state images to `04 Reporting/Content`, which creaite creates the first time an image is filed (the skeleton may not have it yet). Nothing is saved yet.
   3. On Alan's yes, save the `~` form `check` gave with `system/scripts/run propose.py setting locations.projects_root '"~/…"'`, then `locations.folders` (and `locations.skeleton` if it differs). Never write an absolute path.
   4. Run `system/scripts/run locations.py portfolio-spec`, stage it with `propose.py stage`, show it, and apply on his yes: it makes `_Portfolio` (PORTFOLIO.md, the registers, the cross-project minutes and transcripts folders) only where missing.
   5. List the engagement folders; for each Alan wants as a project use cx-edit's add project with `--folder "<the existing folder's name>"`, which adopts the folder as it is and adds the register row (code, name, matching signals). Folder names carry no project code.
   6. Existing meetings: for **each** project ask once whether to **mark the existing transcripts and minutes as already processed** (`system/scripts/run minutes.py baseline <CODE> --all`) or to **process the last N weeks** (`--keep-weeks N`, which marks only the older ones). Show the `--dry-run` counts first. Never process or mark them all silently.
   7. Claude Code reads that folder from outside the vault: with Alan's yes, add it to `permissions.additionalDirectories` in `.claude/settings.json`.
   8. Tell Alan to set the Engagements folder to **Always keep on this device** in Finder (OneDrive), so no file is online-only. Doctor lists any that are, and creaite never downloads them.
5. **Projects:** for each project Alan names, use cx-edit's "add project" (code, name, client, aliases, stakeholders, email domains, Teams channels, keywords), which creates `projects/<CODE> <Name>/` with its subfolders and the register row (with a projects folder outside the vault: the engagement folder by its own name, copied from the template skeleton, or adopted if it already exists).
6. **People:** the people who own items on those projects: full name, email, aliases, organisation, role (`propose.py people add`). Email and aliases can wait.
7. **Memory files (Step 5b):** one `CLAUDE.md` per project from `system/templates/project-CLAUDE-template.md`, and `projects/_portfolio/PORTFOLIO.md`: draft from what Alan has said and any `documents/`, ask him to fill the gaps, about one page each.
8. **Apply:** say what's staged, and on Alan's "apply" run `system/scripts/run tracker.py apply` (which also rebuilds the dashboard).
9. **Live server:** give the start command (`system/scripts/run live_server.py`) and the address; Alan starts it himself.
10. **First sweep:** offer cx-sweep for the look-back (`sweep.first_run_lookback_days`, 14), then the optional morning schedule (step 7 below).

Finish with the report (step 12), listing what's left for Alan.

## Steps

1. **Health check.** Run `system/scripts/run doctor.py` (on Windows: `python`) and show the results as a short pass/fail list. Until `doctor.py` exists (early build), check by hand:
   - Python 3.9 or later;
   - `system/scripts/vendor/` imports;
   - SQLite with FTS5;
   - `system/tracker.db` opens and passes `PRAGMA integrity_check`;
   - write access to `system/staging/`, `system/history/` and `system/backups/`;
   - no absolute paths in the database, proposals or templates;
   - extraction never reads documents or reports (only the minutes and transcripts folders);
   - `.claude/settings.json` and `system/config/schedules.md` exist.
2. **Microsoft 365.** Run one small test of each, limited to the last day with one result:
   - mail search (Inbox and Sent Items);
   - Teams chat and channel search;
   - calendar lookup;
   - transcript and chat retrieval for one recent meeting.

   If any fails, ask Alan to reconnect Microsoft 365. Report what still works: minutes from `inbox/` work without Microsoft 365.
3. **Claude Code CLI and browser.** Check that `claude --version` works and is signed in (it is needed by the live server's assistant). Remind Alan to use Chrome or Edge, not Safari.
4. **docx skill.** Confirm Anthropic's docx skill is available. If it isn't, show Alan the commands to type himself:
   ```
   /plugin marketplace add anthropics/skills
   /plugin install document-skills@anthropic-agent-skills
   ```
   Without it, minutes and reports can't be drafted; everything else works.
5. **Database.** If `system/tracker.db` is missing, offer to restore the newest copy from `system/backups/`, or, on a brand-new vault, to run `system/scripts/run tracker.py init`. Never overwrite an existing database.
6. **Git.** If `.git/` is missing, offer to run `git init` (local only, no remote) and make a first commit.
   - **Untrack private files in an existing vault (needs Alan's yes; an older vault committed `system/staging/`).** If `git ls-files system/staging` lists anything, or `.gitignore` lacks the `system/staging/` line, offer: (1) back up first (`system/scripts/run backup.py` for a fresh daily backup); (2) show the lines to add to `.gitignore` (`system/staging/`, `system/logs/`, `system/branding/`, copied from `system/templates/vault-gitignore`); (3) on his yes, `git rm -r --cached system/staging system/logs system/branding` (the files stay on disk), add the lines, and commit ("Stop tracking staging"). Say plainly: **earlier commits still contain those files, so every earlier backup zip's `vault.bundle`, and its OneDrive copy, still holds them** (ask creaite chats and images, `vip.json`, the raw calendar). creaite does not rewrite git history. Old zips are Alan's to delete (as for the raw calendar); the new zips carry the old commits too until he decides on a history rewrite himself, outside creaite (for example a fresh `git init` and first commit, keeping `.git` of the old one aside, which loses the history).
6a. **Rules and root `CLAUDE.md` (BL-36).** creaite's rules live in `system/creaite-rules.md` (replaced by updates); the root `CLAUDE.md` is Alan's and imports them with the line `@system/creaite-rules.md`. `doctor.py` reports "creaite rules imported":
   - **no root `CLAUDE.md`** (a new vault): offer to create it from `system/templates/vault-CLAUDE-template.md` and ask Alan for his role.
   - **not split yet** (the rules are still in the root `CLAUDE.md`, an older vault): offer the one-time split. Show before → after: the import line goes at the top; every section that `system/creaite-rules.md` now holds (Non-negotiables, Folder map, Starting a session, Skills and commands, Dashboard editing, Updates, Project documents, Portability rules, Memory rules, Retention, Conventions, the development guard and the opening description) is removed; so is Scheduled tasks, whose text now lives in `system/templates/creaite-reference.md`; **everything else stays exactly as Alan wrote it** ("About Alan" and any notes of his own, including lines he added inside those sections: list them and ask where they go). Write it only after Alan approves; git keeps the old version.
   - **the import line is missing** but the rules file exists: offer to add the line at the top, nothing else.
6d. **Projects folder (BL-85).** If `locations.projects_root` is set, `doctor.py` reports the projects folder: reachable, each registered project's mapped folders, online-only files, the vault not in a synced folder, and the last off-laptop backup copy. To move the projects, change `locations.projects_root` only (`propose.py setting`): stored paths use the logical `projects/` prefix and keep working. To start using a OneDrive folder on an existing vault, do first-install step 4.
6b. **Register columns.** If the register's Projects table lacks the **Senders** and **Exclude** columns (BL-28), offer to add them: `system/scripts/run propose.py register-columns` (staged, approved, written at the next apply).
6c. **People register (BL-55).** The register of people is `projects/_portfolio/people-register.md` (template: `system/templates/people-register-template.md`). If `settings.json` still has names in `people.added` or `people.hidden`, offer to move them into it, once: `system/scripts/run propose.py people migrate` stages the register change (names with a bracketed company become the full name, with the company as organisation and the old spelling as an alias; hidden names stay hidden); say "apply", then run `people migrate` again to clear the old lists (it never clears them while a name is missing). Email and aliases are added later on the dashboard's People page; incomplete entries are listed there under Needs attention. If there is no register and no old names, `people add` creates it from the template the first time someone is added.
6d. **Workstreams (BL-58).** `tracker.py migrate` (also run by every update) seeds each project's workstreams from its items and from the old `settings.json` `workstreams` lists, leaving leads and keywords for Alan. If those lists still hold names, show them and offer to clear them: `propose.py workstreams retire-settings` (it refuses while a name isn't yet in the table). Then suggest filling in leads and keywords in Settings › Workstreams.
6e. **Search summaries (BL-07).** `system/scripts/run search.py enrich --missing` lists the indexed meetings and reports that have no two-line summary and topic tags yet (cx-minutes and the report skills write them from now on). If there are any, offer a one-off backfill and **ask before starting**: say how many there are (it reads each file, so it takes a while and uses Claude), then, in batches of about ten, read each (`search.py query` or the file itself; transcripts and Word minutes via `minutes.py transcript` or `docx_tools.py text`), write the summary and tags and run `search.py enrich set --path <every path listed for it> --summary … --tags …`. Stop after any batch if Alan says so, and report how many remain. It never changes anything but `system/search/`. The index then folds the summaries in at its next rebuild (after the next apply, or `tracker.py index`).
7. **Optional schedules.** Read `system/config/schedules.md`, list the scheduled tasks that already exist in this app, and offer to create or update the optional morning sweep. Remind Alan that creaite doesn't depend on it: the session-start rule runs the sweep.
8. **Permissions.** Confirm `.claude/settings.json` is present. Note any permission prompts seen during steps 1 to 6, because they would block unattended runs, and propose the allow rule for `.claude/settings.json` (never personal settings). Write a script rule as `Bash(system/scripts/run <name>.py <subcommand> *)` (BL-237: the wrapper; an older vault's `Bash(python3 system/scripts/<name>.py …)` rules keep working), never with `:*`, and look in `.claude/settings.json` first: if the script is already allowed, the prompt came from the command's shape (a `cd … &&` prefix, a pipe, a redirect or a heredoc), so run the script on its own instead of adding a rule (BL-140).
9. **Location and tidy-up.** Warn if the vault is inside an iCloud- or OneDrive-synced folder (Desktop or Documents). Offer to hide `dev/` (Mac: `chflags hidden dev`; Windows: `attrib +h dev`). Never hide `system/`.
9b. **Launcher and project permissions (BL-86, BL-93).** Offer, and **ask first** (they are outside the vault): (a) a double-click launcher: `system/scripts/run launch.py make-launcher` makes a small macOS app named creaite in `~/Applications` (or `--where vault` for `creaite.command` in the vault); say that it opens creaite in a Chrome window, starts the live server if needed, and the server stops a minute after the window closes. Each vault has its own (BL-305): `creaite.app` here, `creaite (dev).app` in the development repository. If it answers that `creaite.app` opens another vault, tell Alan which folder and ask before running it again with `--replace`. (b) With the projects in a OneDrive folder, `system/scripts/run permissions.py projects-root --why "read the project documents"` lets Claude Code in a Terminal session read them (the dashboard's ask creaite doesn't need it). Show what each does before running it.
9c. **Start at sign-in (#300).** Ask one plain question: "Start creaite automatically when you sign in?" You cannot do it yourself (the login agent is outside the vault and on the never list, and `launch.py` is not run from here). If Alan says yes, point him to Settings › creaite and backups › "Start creaite when I sign in" (its own click, which asks first), or, for Terminal, give him `cd <his creaite folder>` and `system/scripts/run launch.py agent install` to run himself, with his real folder filled in. If he says no, say it can be turned on later in the same place; do not ask again this visit. macOS only; not in the development repository.
10. **Outlook rules.** Check whether mail carries project categories (search one recent `[CODE]` message). If not, point Alan to the "Outlook rules" section of `dev/SETUP.md`. Claude never creates mail rules.
11. **Live server and rebuild.** Check `http://127.0.0.1:<port>/health`; if the server isn't running, give the start command (`system/scripts/run live_server.py`). Then run `system/scripts/run build_dashboard.py`. Run `system/scripts/run excel_sync.py export` only if `changed` reports no unimported edits.
12. **Report.** One screen:
    - **passed;**
    - **fixed** (with Alan's approval);
    - **still to do by Alan,** with the exact step.

## Restore from a backup zip (BL-323)

"restore creaite from backup" (a lost or new laptop, or a damaged vault). `system/scripts/run backup.py` does the work; never unzip by hand.

1. `backup.py list` gives the daily zips by date, on this laptop and in the OneDrive backup folder (`_Portfolio/99 System/creaite backups`). On a new laptop, install the release first (`update.py new-vault`), set `locations.projects_root` (first-install step 4), then list. Show the dates (DD-MM-YYYY) and ask which.
2. `backup.py show <YYYY-MM-DD or the zip's path>` and show what it holds and whether it checks out (complete against its manifest, database and git history readable). If it doesn't, say so and offer an earlier one.
3. `backup.py restore <zip> --dry-run`, show each step, then ask "Restore this vault from the backup of DD-MM-YYYY?" and wait for Alan's yes. Ask separately before `--claude-md` (replacing an existing root `CLAUDE.md`; without it, CLAUDE.md is only restored when missing).
4. `backup.py restore <zip>` (`--claude-md` only on that second yes). It backs up the current database first, restores the configuration files (settings merged with this version's new keys, as an update does), staging, the flow files and `processed.txt`, and the git history into a vault that has none; each file it replaces is kept in `system/backups/restore-<time>/`. It never touches a project file. It refuses in the development repository.
5. Run `doctor.py`, then rebuild the dashboard (step 11). Say what was restored.

Settings › Health › Restore from a backup does the same from the dashboard. The restore check runs by itself once a week; `backup.py check` runs it now. `backup.py tidy` (Tidy up) runs by itself once a day; never run it or `restore` without Alan asking.

## Updates (BL-36)

Releases are zips (`creaite-X.Y.Z.zip`) attached to each GitHub release, not GitHub's "Source code (zip)". `system/scripts/run update.py` does the work; never copy engine files by hand. It can fetch the zip itself with the GitHub command-line tool (`update.py fetch`, BL-238), or Alan downloads it by hand. Never run `gh` yourself: only `update.py fetch` runs it.

- **"what version is creaite?"** `update.py version`.
- **"update creaite"**:
  0. **Fetch (BL-238).** `update.py fetch` downloads the newest release zip, pre-releases included (BL-280), from GitHub with `gh` into `system/releases/` and checks it against its checksums; it installs nothing. Its JSON says the version and whether it is newer than the installed one. If it says `gh` is missing or not signed in, or the download failed, pass that on in one line ("Couldn't fetch the release: … Download creaite-X.Y.Z.zip by hand into system/releases/ or Downloads.") and carry on with step 1, which finds a zip downloaded by hand. "update creaite from <file>" skips this step.
  1. `update.py find` gives the newest zip in `system/releases/` and in Downloads. Use the newer of the two; if it's in Downloads, say so ("Using creaite-1.2.0.zip from Downloads; it will be kept in system/releases/"). If neither is newer than the installed version, say "creaite X is up to date" and stop. "update creaite from <file>" names the zip instead.
  2. `update.py inspect <zip>` and show, briefly: the version change, the release date (DD-MM-YYYY), the release notes, the number of files replaced, added and removed (list removed ones), files left in place because no release shipped them, and the settings and permission rules it adds. If it refuses, pass on its message.
  3. Ask "Install creaite X now?" and wait for Alan's yes. Never install without it.
  4. `update.py install <zip>` (`--reinstall` only if Alan asked to reinstall the same or an older version). Pass on its summary, including any skipped Excel export, and ask Alan to restart the live server (`Ctrl+C`, then `system/scripts/run live_server.py`).
  5. If the install fails, it has already rolled back: say so with its reason, and that nothing else changed.
- **"undo update"**: confirm first ("Undo the update to X and go back to Y?"), then `update.py undo`. If it refuses because the database has changed since, explain that undoing the database would lose those changes and offer `update.py undo --keep-database` (engine and settings only).
- The root `CLAUDE.md` and all data are never touched by an update. In the development repository (`.creaite-dev` present) `update.py` refuses: use git there.

## Rules

- Never delete, move or overwrite data, proposals, backups or project files (the restore above, after Alan's yes, and the automatic Tidy up of old backups, BL-323, are the exceptions).
- Never install packages. Python libraries come from `system/scripts/vendor/`. Plugins are installed by Alan.
- Ask before every change except the rebuild in step 11.
- Use paths relative to the vault root only.
- Dates are `YYYY-MM-DD`.
