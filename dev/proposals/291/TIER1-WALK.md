# #291 Tier 1: the live-app walk (plain words)

Walked 22-10-2026 on the **line-4 build** (`origin/v26-line-4` at 7a900841), served by the live server, in real headless Chrome
driven over the DevTools protocol (`dev/tools/cdp.py`, the test harness). No fixes: they are 2.6.1 (#291). Fictional demo data only.

## Head

- **79 on-screen offenders** (76 distinct strings) across the six screens (Today, Close the day, Intake, the Apply/save errors,
  Settings, Health), plus the ask creaite panel that Today and the approval card open. Diagnostics is allowed and was left out.
- **35 are runtime-only (34 distinct): the static scan (#290, `dev/tests/test_plain_words.py`) misses them**, against the baseline
  (`origin/v254-290`) and on line 4 alike. They fall into seven gaps (below). The biggest: the Settings catalogue
  (`settings_catalogue.py`, 12 rows on screen) and the file names and paths in every Apply error and on the approval card.
  Three of them (E1, E2, E5) are mixed: their banned words are in the baseline, their file name or head line is not.
- **38 are in the baseline** (36 distinct); **6 are not in the baseline but the scan catches them on line 4** (strings new since
  v2.5.4: the Settings tab "Sweep and Intake", Intake's new page, the ask creaite chip). The guard reports those as NEW when line 4
  meets it.
- The worst single screen: the Apply-stopped toast, which shows the proposal's file name, a raw field list ("Valid: project,
  decision, made_by, …") and "Apply stopped:" twice. The missing-source variant shows an inbox path.

| Screen | Offenders | Runtime-only (scan misses) |
|---|---|---|
| Today (incl. first-run checklist and the server-down banner) | 13 | 3 |
| Close the day | 4 | 2 |
| Intake | 11 | 5 |
| Apply/save errors (incl. refused, server not running) | 9 | 6 |
| Settings (all tabs bar Health) | 21 | 13 |
| Settings › Health (incl. the archive approval card) | 18 | 5 |
| ask creaite panel (opened from Today / the card) | 3 | 1 |
| **Total** | **79** (76 distinct) | **35** (34 distinct) |

Three strings show on two screens and have a row on each: the server-down banner and "Connect vault" (T10, T11 on Today; I10,
I11 on Intake) and the proposals headline (T5, T13).

## How it was walked

- `dev/tools/handcheck.py`'s Session (release zip from this checkout, a new vault from it, `demo_data.load()`, the FAL, ORX, MER,
  TID registers, the stand-in Claude, a pinned clock of 22-10-2026 09:30), with the live server on a free port. A last-sweep time
  of 21-10-2026 18:05 put Today into its "sweep due" state.
- For each screen: every visible text block and every visible `title`, `aria-label`, `data-tip`, `placeholder` and `alt`,
  matched against the guard's own rules (`RULES` in test_plain_words.py). Each hit was outlined and screenshotted.
- Error paths provoked for real, through the dashboard:
  - **Apply stopped, unknown field / invalid item:** a mail-and-Teams proposal with a decision carrying `raised`; Approve in Intake.
    The same on a minutes item (`due`, `notes`).
  - **Missing source:** a minutes proposal whose transcript (`inbox/…vtt`) is not there; Approve the minutes, then "Keep the items
    as staged".
  - **Open source** on an item whose filed minutes are missing.
  - **Live server not running:** the browser's requests to the server blocked (the page's own health check then fails), Today,
    Intake (Approve) and Settings › Health.
  - **Refused:** a release zip in the vault's releases folder whose VERSION was changed; Settings › Health › Review 2.5.9.
  - **Make minutes** on the inbox transcript (the stand-in Claude stages nothing), **Archive them** (the approval card).
- **Screenshots** are not in the repository (it is public, and the hand-check rule keeps captures out of git). They are in the
  walk's scratchpad folder, `<scratchpad>/shots291/`, named in the Shot column; each `*-full.png` is the whole screen. The vault's
  absolute path was shortened to `~/creaite` on the page before each capture.

**Legend.** Guard: **B** in the v254-290 baseline; **L4** not in the baseline, but the scan catches it on line 4 (new string);
**R** runtime-only, the scan misses it (reason given). Severity: **High** an error or stop message, a file path, a script name or
a command shown to type, or "sweep" on a main control; **Medium** a heading, label, button or count line with a banned word;
**Low** a tooltip, an aria-label or a sentence of help text. Replacements are from `dev/PLAIN-WORDS.md`.

## Today

| # | Exact text | Produced by | Plain replacement | Sev | Guard | Shot |
|---|---|---|---|---|---|---|
| T1 | Sweep due since 07:00. | today.js:439 (renderSweepDue) | Mail and Teams not checked yet today. | High | B | today-due-02.png |
| T2 | Last swept 2026-10-21 18:05. | today.js:439 | Last checked 21-10-2026 18:05. (also shows YYYY-MM-DD, against the date rule) | Medium | B | today-due-03.png |
| T3 | Run sweep (button) | today.js:439 | Check now | High | B | today-due-04.png |
| T4 | Dismiss until the next sweep is due (aria-label, data-tip) | today.js:439 | Dismiss until the next check is due | Low | B | today-06.png, today-07.png |
| T5 | 7 proposals need your decision, 0 of your actions are overdue, … | today.js:146 (`<b>${n} proposal${s}</b> need…`) | 7 suggestions need your decision, … | Medium | **R**: the noun sits in a `<b>` fragment the lexer drops; only " need{} your decision" is read | today-due-01.png |
| T6 | Intake: 7 proposals to approve and 1 new file to process. | build_dashboard.py:2886 | Intake: 7 suggestions to approve and 1 new file to process. | Medium | **R**: Python string that is not under a message key | today-due-05.png |
| T7 | Run the first sweep (checklist step and its button) | today.js:411 | Run the first check | High | B | today-firstrun-04.png, -05.png |
| T8 | Connected in Claude itself, so the page can't: connect it there, then say "setup: check Microsoft 365" in Claude Code. The first sweep confirms it | today.js:408 | …The first mail and Teams check confirms it. (The typed command belongs in Diagnostics.) | High | B | today-firstrun-03.png |
| T9 | Approve what's right; nothing reaches the tracker until you do | today.js:412 | …nothing reaches your project record until you do | Low | B (tracker: warn) | today-firstrun-07.png |
| T10 | Live server isn't running. Saves are held and applied when it's back. Start it in Terminal: `cd ~/creaite && python3 system/scripts/live_server.py` [Copy] [Check again] | shell.html:33; the command from core/page.js and live_server.py | creaite has stopped. Reopen the creaite app. Your changes are kept and saved when it's back. (The command only in Diagnostics.) | High | B | down-today-03.png |
| T11 | Connect vault (top bar, server down) | core/server.js:334 | Connect your creaite folder | Medium | B | down-today-01.png |
| T12 | Needs the live server: start it in Terminal, then run the sweep. | today.js:439 | creaite isn't running. Reopen the creaite app, then check now. | High | B | down-today-08.png |
| T13 | 4 proposals … / 9 proposals need your decision (same as T5 with the server down) | today.js:146 | as T5 | Medium | **R** (as T5) | down-today-05.png |

## Close the day

| # | Exact text | Produced by | Plain replacement | Sev | Guard | Shot |
|---|---|---|---|---|---|---|
| C1 | It runs while you read on. It only proposes items for Review; nothing is applied, and nothing changes in Microsoft 365. | CloseDay.jsx:105 | It runs while you read on. It only adds suggestions to Review; nothing is saved, and nothing changes in Microsoft 365. | Medium | B (apply). "proposes" itself is **not** matched: the rule covers proposal(s)/proposed only | closeday0-01.png |
| C2 | The sweep only proposes; closing now closes when it finishes. (footer, while the catch-up runs) | CloseDay.jsx:471 | The check only suggests; closing now closes when it finishes. | Medium | B | closeday0-02.png |
| C3 | File in Intake · Recording - ORX design review (demo).vtt · Orbit Customer App (Loose ends) | close_day.py:125, 356 (type and the inbox file's name) | Transcript · ORX design review · Orbit Customer App | Low | **R**: the extension comes with the file's name at run time | closeday3-03.png |
| C4 | Place for File in Intake: Recording - ORX design review (demo).vtt (aria-label of the place picker) | CloseDay.jsx:194 with close_day.py's name | Place for transcript: ORX design review | Low | **R** (as C3) | closeday3-07.png |

Not provoked (the stand-in catch-up finished at once), in the same card: "Sweep now", "Sweep again" (CloseDay.jsx:134-135),
"The catch-up sweep didn't run. The next sweep picks up anything new." (126), "Reading mail and Teams since the last sweep" (99);
all four are in the baseline. Loose ends that read "staging" or "extract" are demo item titles, not words creaite chose.

## Intake

| # | Exact text | Produced by | Plain replacement | Sev | Guard | Shot |
|---|---|---|---|---|---|---|
| I1 | 1 ready to process · 7 proposals to approve · Calendar read 09:30 | IntakeReviewPage.jsx:142 (`irPlural(c.to_approve, "proposal")`) | 1 ready to process · 7 suggestions to approve · … | Medium | **R**: "proposal" is a bare lowercase argument to the plural helper, not a candidate | intake-01.png |
| I2 | 7 proposals to check (Drafted step) and "4 proposals to check · today" (meeting rows; also "1 proposals to check", a plural slip) | rows.jsx:15 (IR_STATE_WORDS), irFold.js:28 | 7 suggestions to check | Medium | L4 | intake-02.png, intake-06.png |
| I3 | From mail and Teams 3 proposals | views.jsx:5, 21 (irPlural) | From mail and Teams · 3 suggestions | Medium | **R** (as I1) | intake-09.png |
| I4 | Stages (aria-label of the Arrived, Drafted, Approved pipe) | IntakeReviewPage.jsx:46 | Steps | Low | L4 | intake-11.png |
| I5 | Approves every routine proposal here; the ones above stay for you (title) | proposals.jsx:188 | Approves every routine suggestion here; … | Low | L4 (the baseline has the old review.js copy) | intake-12.png |
| I6 | File ready · .vtt · 1 KB | rows.jsx:28, 37 (irFileFacts: the extension) | File ready · Teams transcript · 1 KB | Low | **R**: the extension is computed at run time | intake-04.png |
| I7 | Portfolio steering 20-10-2026 16:00–17:00 · _portfolio | rows.jsx:146 via `pName` (core/data.js:12 falls back to the code) | … · Portfolio | Medium | **R**: the portfolio's folder code shown as a project name | intake-08.png |
| I8 | 0 of 1 staged for Review; 1 not staged. (toast after Make minutes) | intake_process.py:331-335 (the run's closer) | 0 of 1 waiting in Review; 1 couldn't be read: process it again. | Medium | **R**: Python closer line, not under a message key | intake-mm-toast-01.png |
| I9 | Not staged: process it again, or ask creaite (row note) | components/intakeReview/actions.js:102 | Not in Review yet: process it again, or ask creaite | Medium | L4 | intake-makeminutes-02.png |
| I10 | Live server isn't running… (as T10, on Intake after Approve) | shell.html:33 | as T10 | High | B | down-intake-03.png |
| I11 | Connect vault (as T11) | core/server.js:334 | as T11 | Medium | B | down-intake-01.png |

## Apply/save errors

| # | Exact text | Produced by | Plain replacement | Sev | Guard | Shot |
|---|---|---|---|---|---|---|
| E1 | Apply stopped: Apply stopped. Nothing was written. · proposed-2026-10-22-0905-sweep.json item 1: unknown field(s) for decisions: raised. Valid: project, decision, made_by, client_visible, client_message, date, status, needed_by, reasoning, options, revisi… (toast after Approve) | core/server.js:120 ("Apply stopped: " + message); tracker.py:2532 (header), 2414 (`{p.name} item {n}: …`), 761 (the field list) | One suggestion (Pilot extended by two weeks, from Teams) couldn't be saved. It needs fixing in Review. Nothing was saved. | High | B for "Apply stopped", "unknown field", "Valid"; **R** for the file name (`p.name` at run time) and the doubled "Apply stopped:" | err-unknownfield-01.png |
| E2 | Apply stopped: Apply stopped. Nothing was written. · proposed-2026-10-22-0910-minutes.json item 1: unknown field(s) for actions: due, notes. Valid: project, description, workstream, owner, priority, due_date, … | as E1 | One suggestion (MER pilot check-in, action 1) couldn't be saved. It needs fixing in Review. | High | B for the words; **R** for the file name (as E1) | err-unknownfield2-01.png |
| E3 | Apply stopped: Apply stopped. Nothing was written. · proposed-2026-10-22-0910-minutes.json minutes_decision: copy: source not found (inbox/Recording - MER pilot check-in.vtt) | tracker.py:2510 (`{p.name} {field}: {e}`), 1415 (`copy: source not found ({src})`) | The minutes for MER pilot check-in couldn't be filed: the transcript isn't in your inbox any more. Nothing was saved. [Open Intake] | High | **R**: the file name, the key `minutes_decision` and the path all come at run time; "source not found" has no banned word | err-missingsource-01.png |
| E4 | can't open projects/MER Meridian Contact Centre AI/minutes/2026-10-22 MER pilot check-in.docx (toast after Open source) | live_server.py:1429 (`can't open {rel}`) | The minutes for MER pilot check-in aren't in the project's minutes folder. | Medium | **R**: the path at run time | err-opensource-01.png |
| E5 | 6: not approved — the draft differs from the staged items: … ("approve 6 --as-staged" to keep them) [Rebuild the items from the draft] [Keep the items as staged] (ask creaite panel, after Approve minutes) | review.py:1129, 1139 (head and hint); core/server.js:126 (the buttons) | These minutes don't match the items waiting in Review. [Rebuild from the minutes] [Keep the items as they are] (no typed command) | High | B for the hint, the item lines and the button; **R** for the head line (a `return` value, not a message key) | err-draftdiffers-04.png, -05.png |
| E6 | Refused: VERSION doesn't match its checksum; the zip is damaged or was changed. Download it again. (Settings › Health › Review 2.5.9) | update.py:312 | creaite can't install this update: the download is damaged. Download it again. | High | B | upd-1-30.png |
| E7 | creaite-2.5.9.zip in system/releases (Update row) | settings.js:319 (`${z.name} in ${where}`, `where` from /api/update/status) | creaite 2.5.9 is ready to install | Medium | **R**: the folder comes from the server at run time | upd-0-02.png |
| E8 | The health check needs the live server. (Health, server down) | components/settings/Health.jsx:194 | The health check needs creaite running. | Medium | B | down-health-02.png |
| E9 | Needs the live server (disabled buttons' title and the line under them, server down) | today.js:132, 314, 385, 420 | creaite isn't running | Low | B | down-health-26.png, -30.png |

Also seen, not a words offender but for 2.6.1: an item stopped by the checks is left approved and invalid, and drops out of
Intake's list (it is no longer pending), so after the toast nothing on the page says where it went.

## Settings (all tabs bar Health)

| # | Exact text | Produced by | Plain replacement | Sev | Guard | Shot |
|---|---|---|---|---|---|---|
| S1 | Settings save instantly to system/config/settings.json, with a backup and a log entry. (footer of every tab) | shell.html:121 | Settings save instantly, with a backup and a log entry. | High | **R**: the path is a single lowercase word inside `<code>`, so not a candidate | settings-essentials-10.png |
| S2 | Sweep and Intake (tab) | settings.js:44, 52; settings_catalogue.py:467 | Checking mail and Teams (and Intake) | Medium | L4 | settings-essentials-01.png |
| S3 | Morning sweep from: creaite catches up on mail and Teams when you first open it after this time. (Essentials) | settings_catalogue.py:42 | Daily check time | High | **R**: settings_catalogue.py is not scanned | settings-essentials-02.png |
| S4 | What the sweep reads | settings_catalogue.py:44 | What the check reads | Medium | **R** (catalogue) | settings-essentials-03.png |
| S5 | Catch up before closing: Starts a sweep if the last one was a while ago. | settings_catalogue.py:48 | Starts a last check of mail and Teams if the last one was a while ago. | Medium | **R** (catalogue) | settings-essentials-04.png |
| S6 | AI drafts: Suggestions you can use, edit or ignore. Never applied by themselves. | settings_catalogue.py:73 | …Never saved by themselves. | Low | **R** (catalogue) | settings-essentials-06.png |
| S7 | Daily backup, and a copy in OneDrive: …a closed zip (database, settings, staging, history) goes to your _Portfolio folder… | settings_catalogue.py:78 | …(your project record, settings, items waiting in Review, history) goes to your portfolio folder… | Medium | **R** (catalogue) | settings-essentials-08.png |
| S8 | Excel export: When tracker-view.xlsx is rebuilt. Default: immediate on every apply; … After every apply, paused only while it has edits not yet imported. (Work and reports) | settings_catalogue.py:299-300 | When the Excel view is rebuilt. Default: after every save; … | Medium | **R** (catalogue; .xlsx is not a banned pattern either) | settings-work-02.png |
| S9 | Sweep (section heading, Sweep and Intake tab) | settings.js | Checking mail and Teams | Medium | B | settings-sweep-02.png |
| S10 | When the sweep runs and what it reads are in Essentials › Your day | settings.js:139 | When the check runs and what it reads are in Essentials › Your day | Low | B | settings-sweep-04.png |
| S11 | Ignore rules: The sweep skips what these match, even when it names a project… | settings.js:623 | What creaite skips: the check skips what these rules match… | Medium | B | settings-sweep-05.png |
| S12 | Sweep looks back at most: The furthest back a sweep reads mail and Teams after a gap; "sweep the last 7 days" overrides it. | settings_catalogue.py:111 | Check looks back at most: …; "check the last 7 days" overrides it. | Medium | **R** (catalogue) | settings-sweep-08.png |
| S13 | Promises from the sweep: Let the sweep propose promises from mail and Teams… | settings_catalogue.py:106 | Promises from mail and Teams: let the check suggest promises… | Medium | **R** (catalogue) | settings-sweep-10.png |
| S14 | Catch up when the last sweep is older than (minutes): A sweep more recent than this says "Caught up" instead, with Sweep again. | settings.js:144 | Catch up when the last check is older than (minutes): a check more recent than this says "Caught up", with Check again. | Medium | B | settings-sweep-12.png |
| S15 | A draft is a suggestion, never a save: it fills a field, a proposal in Review or a box for you to edit. … Each needs the live server. (AI drafts) | drafts.js:446 | …a suggestion in Review… Each needs creaite running. | Low | B | settings-ai-02.png |
| S16 | Spot repeats of existing items: Marks a proposal that looks like an item already in the tracker… / Spot items that are probably done: The sweep and the minutes propose closing an open item… | drafts.js:387, 388 (drafts.py:62, 65) | Marks a suggestion that looks like an item already in your project record… / The mail and Teams check and the minutes suggest closing… | Low | B | settings-ai-04.png, -06.png |
| S17 | Review: move to the next proposal after a decision; …the share of words a proposal has in common…; Raised in at least (meetings or sweeps) (Advanced › Review and warnings) | settings.js:156, 157; projects.js:887 | …the next suggestion…; (meetings or checks) | Low | B | settings-advanced-review-02.png, -04.png, -05.png |
| S18 | Keep apply and undo copies for (days): The database copies made before each apply, undo, revert or migrate. (Advanced › Archiving and backups) | settings_catalogue.py:258 | Keep copies made before each save and undo for (days) | Low | **R** (catalogue) | settings-advanced-arch-02.png |
| S19 | Projects folder: Where the engagement folders live; empty is the vault's own. (Advanced › Folders and OneDrive) | settings_catalogue.py:379 | …empty is creaite's own folder. | Low | **R** (catalogue) | settings-advanced-folders-02.png |
| S20 | Live server and ask creaite (group); Live server required: The dashboard works through the live server. … IT approved live mode; it is what makes Apply and ask creaite work. Set at set-up: the dashboard needs the live server (IT-approved); not a choice (Advanced › Server, search and logs) | settings_catalogue.py:93, 272-273, 462; SettingRow.jsx:32 | creaite and ask creaite; "creaite must be running (IT approved); it is what saves your changes and runs ask creaite" | Medium | **R** (catalogue) | settings-advanced-server-02.png, -03.png, -05.png |
| S21 | Unwatched run stops after: …(a sweep or minutes); ask creaite reads up to: How much vault text a search answer may read. | settings_catalogue.py:287, 372 | (a mail and Teams check or minutes); How much of your creaite folder a search answer may read. | Low | **R** (catalogue) | settings-advanced-server-06.png, -08.png |

Judgement, not counted: Advanced › Folders shows the user's own OneDrive folder names, "Default: _Portfolio" and
"_Portfolio/99 System/creaite backups" (settings_catalogue.py:381, 403). They are names Alan sees in his OneDrive, so they may
stay; the path rule (`_portfolio\b`) flags them if they ever enter the scan.

## Settings › Health

| # | Exact text | Produced by | Plain replacement | Sev | Guard | Shot |
|---|---|---|---|---|---|---|
| H1 | Set-up isn't finished: your name isn't set (identity in settings); CLAUDE.md doesn't say your role yet. Say "setup" to fill them in / How to fix: Say "setup" in Claude Code | doctor.py:520-525 (through health.py) | Set-up isn't finished: add your name and role in Settings › Essentials. | Medium | **R**: doctor.py is allow-listed whole, yet its lines show in Health, not only Diagnostics; CLAUDE.md and the settings key match no rule | health-setup-problem.png |
| H2 | Each day a closed zip of the database backup, your settings, staging and the vault's history goes to your OneDrive backup folder… | Health.jsx:244 | …your settings, the items waiting in Review and creaite's history… | Medium | B | settings-health-02.png |
| H3 | Off-laptop backup copy: not used (the projects are in the vault) | doctor.py:798 (check name and value) | Copy in OneDrive: not used (your projects are in the creaite folder) | Medium | **R** (doctor.py allow-listed) | settings-health-03.png |
| H4 | Backup restore check: passed 22-10-2026 (tracker-2026-10-22.db, creaite-backup-2026-10-22.zip) | doctor.py:799 with backup.py's file names | Backup restore check: passed 22-10-2026 | Medium | **R** (doctor.py allow-listed; the .db name at run time) | settings-health-04.png |
| H5 | Puts this vault back as it was in a daily backup: the database, settings, staging and history… (Restore from a backup) | Health.jsx:75 | Puts creaite back as it was in a daily backup: your project record, settings, items waiting in Review and history… | Medium | B | settings-health-05.png |
| H6 | After every update: Makes this vault's launcher again / Restarts the live server on the new version, and runs the health check | Health.jsx:252, 254 | Makes creaite's launcher again / Restarts creaite on the new version… | Low | B | settings-health-07.png, -08.png |
| H7 | Live server and backups (card heading) | settings.js:164 | creaite and backups | Medium | B | settings-health-09.png |
| H8 | Mail and Teams last swept 21-10-2026 18:05 · data as of 22-10-2026 03:13 | settings.js:166 | Mail and Teams last checked … | Medium | B | settings-health-10.png |
| H9 | Port: The creaite app belongs to this port: if you change it, install the app again and reconnect the vault | settings.js:167 | …and reconnect your creaite folder | Low | B | settings-health-11.png |
| H10 | Start the live server · Paste into Terminal · `cd ~/creaite && python3 system/scripts/live_server.py` | settings.js:168; core/page.js; live_server.py | Move to Diagnostics; here: "If creaite stops, reopen the creaite app." | High | B | settings-health-13.png, -14.png |
| H11 | Health check: The same checks as "health check" in Claude Code (doctor.py): it only reads | today.js:481 | Health check: checks creaite's set-up; it only reads | High | B | settings-health-15.png |
| H12 | Rebuild the dashboard and Excel view: From the tracker; nothing in the tracker changes | today.js:483 | From your project record; nothing in it changes | Low | B (tracker: warn) | settings-health-17.png |
| H13 | This rewrites dashboard.html and tracker-view.xlsx from the tracker. If the workbook has edits you haven't imported, it is left as it is. (Rebuild… confirm) | today.js:484 | This rebuilds the dashboard and the Excel view from your project record… | Medium | **R**: the file names are in `<code>` and `.html`/`.xlsx` are not banned patterns; only "tracker" (warn) | health-rebuild-01.png |
| H14 | Microsoft 365: The sweep last read your mail 21-10-2026 | today.js:485 | The mail and Teams check last read your mail 21-10-2026 | Medium | B | settings-health-19.png |
| H15 | Launcher: A small app that opens creaite in its own window and starts the live server. It goes outside the vault, so the page can't make it: paste this into Terminal · `cd ~/creaite && python3 system/scripts/launch.py make-launcher` | today.js:487, 140 | …and starts creaite. It goes outside your creaite folder, so the page can't make it. (Command in Diagnostics.) | High | B | settings-health-21.png, -23.png |
| H16 | Update: Save a creaite-X.Y.Z.zip from GitHub in system/releases | settings.js:319 | Download the creaite-X.Y.Z.zip from GitHub; creaite finds it in Downloads | Medium | B | settings-health-29.png |
| H17 | Stop the live server (heading and row); title: Stops the live server; open creaite again from its launcher or Terminal | settings.js:171, 172 | Stop creaite; "Stops creaite; open it again from its launcher" | Medium | B | settings-health-30.png, -33.png |
| H18 | Archive old reports and minutes (approval card): Move file projects/FAL Falcon Data Platform/minutes/2025-09-02 FAL steering minutes.docx → projects/FAL Falcon Data Platform/99 Archive/minutes/2025-09-02 FAL steering minutes.docx (one line per file, incl. projects/_portfolio/…) | propose.py:147 (`file_op_lines`), shown by ask.js:273 | FAL steering minutes, 02-09-2025 → the project's Archive folder | High | **R**: a Python list value, not a message key; the paths at run time | health-archive-06.png, -09.png |

On the same card, "Nothing has been written yet. Approve writes all 4 changes to the tracker at once" (ask.js:273) is in the
baseline under tracker (warn).

## ask creaite panel (opened by Run sweep and by the approval card)

| # | Exact text | Produced by | Plain replacement | Sev | Guard | Shot |
|---|---|---|---|---|---|---|
| A1 | Claude Code on this laptop, working in your vault (panel header) | core/server.js:338 | Claude, working in your creaite folder | Low | B | ask-01.png |
| A2 | Sweep (quick-request chip; sends "sweep mail") | shell.html:137 | Check mail and Teams (sends "check my mail") | Medium | L4 | ask-02.png |
| A3 | sweep (your own message bubble, sent by Today's Run sweep) | today.js:448 (`send("sweep")`) | check my mail | Medium | **R**: a single lowercase word, not a candidate | ask-04.png |

The greeting "Hi Alan. I run your requests through Claude Code in the vault…" (ask.js:360) is in the baseline and is Tier 2.

## What the static scan missed, and why (35 rows)

| Gap | Offenders | What would catch it |
|---|---|---|
| 1. `settings_catalogue.py` is never read: its rows are tuples, not message keys | S3-S8, S12, S13, S18-S21 (12) | Add the catalogue's label and help fields to the Python sources the guard reads |
| 2. Values filled in at run time: file names, paths, the portfolio code, an extension | E1-E4, E7, I6, I7, C3, C4, H4, H18 (11) | A runtime check: the Apply, open and update messages and the approval card run through the banned patterns in a live-server test (the walk's error paths are a ready fixture) |
| 3. Python lines that reach the page but are not under a message key | T6 (build_dashboard.py), I8 (intake_process.py), E5 head (review.py return), H18 (propose.py) (4) | Read `return` f-strings and list items in the scripts whose output the dashboard shows (as PRINT_FILES does for print) |
| 4. doctor.py is allow-listed whole, but its lines show in Settings › Health | H1, H3, H4 (3) | Allow doctor.py only for Diagnostics; health.py's Health lines need the scan |
| 5. A banned word passed as a lone lowercase argument (plural helper, `send`) | I1, I3, A3, T5, T13 (5) | Treat the arguments of `irPlural`/`plur`/`send` as text; keep the fragment around tags in a template |
| 6. A path that is one lowercase word inside `<code>` | S1 (shell.html) (1) | Check the path patterns on every string, candidate or not |
| 7. Patterns the rules don't cover | H13 (1) as its only reason; it also widens H1, S8, E6 (`CLAUDE.md`, `tracker-view.xlsx`, `VERSION`) and C1, S13, S16 ("proposes", "propose") | Add `propos(e|es|ing)` and `\.(md|html|xlsx)\b` to the rules (glossary: no file names) |

Counts: 12 + 11 + 4 + 3 + 5 + 1 + 1 = 37; H18 (gaps 2 and 3) and H4 (gaps 2 and 4) are in two gaps, so 35 rows.
