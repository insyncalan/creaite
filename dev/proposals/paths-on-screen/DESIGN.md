# File paths on screen (v2.6.8, Cap hand check 26)

Status: proposal, no code. Source: Cap's finding on issue #343 (Files `projects/_portfolio`, the project settings folder, Settings > Health launcher command).

## Rules that apply

- Projects by name (BL-101): a project is shown by its full name; a path or code appears only where a machine or a typed command needs it.
- Stored paths stay relative to the vault root (`projects/<folder>/...`). That is storage, not what a person reads.
- Plain words (`test_plain_words`, class `path`): `system/`, `projects/`, `inbox/`, `.claude/`, `_portfolio` and file extensions must not reach the screen. Baseline `dev/tests/plain_words_baseline.json`: 36 `path` entries, 38 offenders, and the count only falls.

## Where the dashboard draws a path or command for a person

All in `system/templates/dashboard/src/`.

| # | Place | Shown | Needed? | Recommendation |
|---|-------|-------|---------|----------------|
| 1 | `files.js:21` and `:22` (Files tree, tooltip `title=` from `FNAME`, defined `:18`) | `projects/_portfolio`, `projects/<folder>`, `inbox` on hover | No | Show the name: tooltip "Portfolio" / the project name / "Intake". Keep `FNAME` for the code that uses it as a key. |
| 2 | `components/project/ProjectSettings.jsx:127` (`#psFolder`, row "Folder") | `projects/<folder>` or "No folder yet" | No; the next button is the need | Show nothing but the project's name and "Where its minutes, transcripts and reports live." Keep **Open folder** (already there, `openPath`). Optional short label: "In your projects folder". |
| 3 | `core/page.js:79-80` `cmdBox()`, used in `settings.js:854` (Health: "Restart creaite") | `cd <vault> && python3 system/scripts/live_server.py` | Yes, only if the app cannot be reopened; must be pasteable | Keep the command, copy-only. Change the line so it is not a wall of text: hide it behind "Show the command" with the Copy button; the vault folder shown is the person's own, so it is theirs. Fix the words to use `system/scripts/run`. |
| 4 | `settings.js:855` with `today.js:168` `SU_LAUNCH` (Health: "Make the launcher") | `cd <vault> && python3 system/scripts/launch.py make-launcher` | Yes, one-off, in Terminal | Same treatment as 3 (collapsed, Copy). Better later: a button the live server runs (outside this release). |
| 5 | `core/keys.js:28` `#alertCmd` (red "creaite isn't running" alert) | the same start command | Yes: the server is down, so no button can run it | Keep. Copy only. This is the one place a command must stay visible. |
| 6 | `autostart.js:58`, drawn at `:88` (Settings, "Start creaite when I sign in", Terminal note) | `cd <folder>` and `system/scripts/run launch.py agent install\|remove` | Yes (a login agent cannot be made from the page, `reach.py` never list) | Keep, collapsed with Copy, as 3. |
| 7 | `ask.js:208` (Activity > What ask creaite changed) | `<code>` stored path of the changed file, and the target of a move | Partly: a person wants to know which file | Show the file name and project name ("Notes, Example Programme"); full path in the tooltip is still a path, so offer "Show in Finder" instead. Highest cost of the list (the table is also pinned by tests). |
| 8 | `components/prep/PrepPage.jsx:61`, `PrepShape.jsx:44,200` (`data-tip` "Opens <path>") | the file path in a tooltip | No | Tooltip: "Opens <file name> (<project name>)". |
| 9 | `meetings.js:90`, `:265` (snack "Prep page saved: <path>", "Saved: <path>") | the saved file's path | Slightly (where did it go) | "Saved in the Agendas folder" plus an **Open** action; the project name, no path. |
| 10 | `components/minutes/ApprovePopup.jsx:14` | last two folders, joined with ">" | Yes (where minutes are filed) | Already friendly; no change. |
| 11 | `files.js:34` Location column | `<project name> › <folder>` | Yes | Already friendly; no change. Row action "Open folder" already exists. |
| 12 | `help.md` (9 `path` offenders: lines about the launcher, Terminal command, backups, usage, permissions) rendered by `help.js` | `system/scripts/...`, `projects/`, `.claude/` | Terminal lines: yes, once | Rewrite prose to say "your creaite folder", "your projects folder", "creaite's permission settings". Keep the two Terminal lines (start, make launcher) as code samples, which the test class already tolerates only if allow-listed (needs checking). |
| 13 | `core/page.js:79` fallback "`~/creaite`" and `VAULT_PATH` | the person's own folder | Yes, inside commands only | Keep inside the commands; never on its own. |

Server messages (`live_server.py`, `permissions.py`, `reach.py`, `filechange.py`, etc.) also appear in the baseline but are chat and card wording, outside the screens Cap named. Treat separately (see question 4).

## Estimate (builder-days)

| Group | Items | Days |
|-------|-------|------|
| Names and labels, no behaviour change | 1, 2, 8, 9 | 1 to 1.5 |
| Commands collapsed behind Show / Copy | 3, 4, 6 | 1 to 1.5 |
| Activity table: name plus Show in Finder | 7 | 1 to 2 |
| Help rewrite and baseline refresh | 12 | 0.5 to 1 |
| Tests, goldens | all | 1 |
| **Total** | | **4.5 to 7** (Cap's three places alone: 1 to 2) |

## Plain-words baseline

The `path` class has 38 offenders in 36 entries. The dashboard and Help entries that this note would clear: `help.md` 9, `core/page.js` 1, `today.js` 1, `projects.js` 4 (backup, image and upload strings, if reworded), `core/server.js` 3, `ask.js` 1, `panel.js` 1, `help.js` 1 = about 21 of 38, so roughly 38 to 17. The remaining 17 are in Python messages (`live_server.py`, `permissions.py`, `reach.py`, `filechange.py`, `paths.py`, `search.py`, `sweep.py`, `tracker.py`, `update.py`) and are not touched. Items 1 to 6 on their own clear almost nothing from the baseline, because the file paths there are drawn from data (`FNAME`, `psFolder`) rather than literal strings; the test finds the Help and string-literal ones. The ratchet file is regenerated and only ever goes down.

## Risks

- Tests that pin the text: `test_project_settings.py:160` asserts `projects/ABC` inside `#psFolder`; Files, Health and Activity browser tests and any golden of the Files tree, Health and Activity table change. Search the tests for `title="projects`, `psFolder`, `alertCmd`, `data-copycmd` and `sucmd` before starting.
- Collapsing a command (3 to 6) must keep the copy button working with the page's `data-copycmd` / `data-sucopy` handlers, and the red alert (5) must stay fully visible.
- `help.md` is built into guides by `dev/tools/build_guides.py`; a test fails until they are regenerated.
- Tooltips with a name instead of a path remove a debugging aid used by hand checks; the debug log and Open folder cover it.
- Goldens are desktop 900px only (Alan, 15-10).

## Open questions for Alan

1. Is the project's folder ever something you need to read (to find it in Finder)? Recommendation: no. Show the project name and keep Open folder.
2. Health's "Restart creaite" and "Make the launcher" commands: keep visible, or hidden behind "Show the command" with Copy? Recommendation: hidden behind Show, Copy kept; the red "not running" alert stays visible.
3. Activity > What ask creaite changed: replace the path with file and project name plus "Show in Finder"? Recommendation: yes, but as a second step (1 to 2 days); do Cap's three places first.
4. Do the server's own messages (the Python `path` offenders in chat and cards) belong in this release? Recommendation: no, a later release, since they are wording in Python with their own tests.
