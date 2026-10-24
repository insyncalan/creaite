---
name: cx-weekly-report
description: creaite weekly report. For each active project, proposes health with reasons, an updates row and a refreshed current-state memory, and drafts a Word weekly report filed in the project's reports folder on approval. Use when Alan says "weekly report", "weekly report ABC", "weekly report for week ending 2026-10-02", or responds to the Friday reminder. Manual only. Never runs unattended.
---

# cx-weekly-report

A weekly picture of each project, drafted for review. Nothing is written or filed until "apply".

**Not from ask creaite (Alan, 19-10-2026).** Reports are the user's to edit in the Reporting hub. In an ask creaite chat (and in any run the live server starts) this skill never drafts, stages or writes a report or its draft: `reach.py`'s guard hook refuses `report.py weekly-stage`, an Edit or Write of a report file or draft, and a Bash call that names one. If asked there, say the report is made and edited in the Reporting hub (Generate, then edit) and offer to read it or answer questions about it. The steps below are for Alan's own Claude Code session only.


**Projects by name (BL-101):** refer to a project by its full name in everything Alan reads (summaries, tables, messages, file names, drafts). The short code appears only inside a work item's ID (`ABC-A-003`) and in a command he can type; `tracker.project_label(code)` gives the name.

Read these first:
- `system/config/settings.json` (`health` thresholds, `reminders`)
- `dev/dashboard-spec.md` (how the health criteria are applied)
- `dev/staging-format.md`
- `.claude/skills/cx-minutes/references/tracker-conventions.md`
- each project's `CLAUDE.md`

## Script

`system/scripts/run report.py weekly-data <CODE> [--week-ending YYYY-MM-DD]` gives the week's facts, whether the project is blocked or already filed, and the health the criteria suggest with its reasons. `report.py weekly-stage <spec.json>` fills the report and stages the proposal; the tables (milestones, overdue actions, top risks and issues, decisions) come from the tracker, and the project's current-state images are included (BL-12). Write the spec in `system/staging/drafts/`; `weekly-stage` deletes it itself once the report is staged. Spec: `{"code", "week_ending", "health", "health_reason", "summary": [paragraphs], "key_changes", "current_state", "progress": [..], "next_week": [..], "help_needed": [..]}`.

## Week

The week runs **Monday to Friday** and is labelled by its **Friday date** (`YYYY-MM-DD`). By default it's the current week; Alan can name another ("week ending 2026-10-02").

## Triggers

- **Manual:** "weekly report" (all active projects), "weekly report ABC", "weekly report for week ending …", "weekly report ABC for week ending …" (one project, a named week: what a reminder's Run sends).
- **Reminder only** (a session-start rule in `CLAUDE.md`): from Friday 12:00, one line per active project whose report for that week isn't approved yet: "ABC weekly report for week ending DD-MM-YYYY is due — say weekly report ABC for week ending DD-MM-YYYY". Never draft anything without being asked.

## Flow

1. **Pre-checks:**
   - if the daily sweep is due, run cx-sweep first;
   - **block projects with pending items:** `weekly-data` reports `blocked`; `weekly-stage` refuses ("ABC has 4 items awaiting review — review first"). Projects with nothing pending go ahead;
   - if a report for this project and week is already approved, say so and stop for that project.
2. **Gather the facts** per project with `report.py weekly-data` (read-only):
   - actions opened, closed and overdue;
   - open risks and issues, and priority movements this week (from `change_log`);
   - decisions dated this week, and the **decisions needed** (`decisions_needed`, BL-53: pending ones, with who is asked, when they are needed by and whether they are overdue) and any made decision whose revisit date has come (`decisions_to_revisit`). The Word report lists the pending ones under Decisions as "Needed: …"; mention an overdue one in the summary or help needed;
   - milestone changes (`projects` history in `change_log`);
   - status signals staged by cx-sweep and cx-minutes during the week;
   - last week's `updates` row;
   - the people Alan follows closely (`vip`, BL-99): those who own an overdue item or a top risk (`owners`), and messages from them about the project Alan hasn't marked seen (`unseen_alerts`). **Who Alan follows stays inside the app (BL-288):** the report, its file name, the staged spec and the search summary never contain the word "VIP" or any label of importance, never say who is followed and never say why an item is there. Put an overdue item one of them owns in help needed, as any other item, without the reason. If there are unseen messages from them, tell Alan before drafting, without the label ("2 messages about ABC you haven't marked seen yet: check them first?"), and never quote them;
   - promises (`promises`, BL-125 A): `you_owe`, Alan's open promises on the project (each with `overdue_days`), and `waiting_on`, the promises made to him that are overdue (with `overdue_days` and `quiet_days`, the days since anyone raised it). `weekly-stage` puts each as a line of its own first in Next Week ("Promised: …") and Help Needed ("Waiting on …"), so don't repeat them; mention a long-quiet one in the summary only if it matters to the position;
   - early warnings (`early_warnings`, BL-51): actions re-dated again and again, risks raised repeatedly with no response, milestones slipping week after week, actions open far longer than usual. Weigh them as evidence when proposing health, and name the ones that matter in the summary or help needed; they never set health on their own.
3. **Propose health** (BL-52: a health better than `suggested_health` must say why in `health_reason`; `weekly-stage` refuses it otherwise) starting from `suggested_health` and its `reasons` (the criteria in `dev/dashboard-spec.md`, thresholds from settings); check `check_blocking_issues` yourself (an issue blocking delivery makes it Off track). State the reasons, for example "Off track: go-live moved 21 days (20-11-2026 → 11-12-2026)". Never change health silently.
4. **Write the narrative** in the executive voice (BL-106): read `system/templates/executive-style.md` first, and run `system/scripts/run report.py facts <CODE> --from <week start> --to <week ending>` for the ranked facts sheet (position, movement, exposure, asks including decisions needed, candidate numbers, trend; item numbers sit in each line's `src:` tail, not in the prose). Write from the sheet, not from the raw lists: a 3–5 sentence summary that opens with the position and the one thing that matters, progress this week, focus for next week, help needed (the sheet's asks, with who and by when), key changes, and 3–5 sentences of current state. The dashboard's Generate uses the same guide and sheet, so the report and the page agree. Write the current state by the rules in `system/templates/current-state-prompt.md`. Current state is Markdown (BL-22, BL-47): keep each image line (`![caption](images/…)`) exactly as it is, where it is (BL-63), and keep any **bold**, *italics*, ~~strikethrough~~, `### ` sub-headings, `> ` quotes, `[links](https://…)` and `- ` or `1. ` lists (nested two spaces per level) already in the project's `CLAUDE.md`; they show in the dashboard and the Word report. **Flow (BL-91):** `weekly-data` has a `flow` line ("12 opened, 9 closed; 3 overdue, down from 5; the oldest open action is 31 days old"); `weekly-stage` puts it first in Progress This Week as "Flow: …", so don't repeat it in your own progress. It is counts only, never about a person. **Two panes (BL-89):** the dashboard's Current state can have a right pane. `current_state` in the weekly data then holds both panes, one message, with the line `<!-- creaite: second pane -->` between them. Treat them as one text: rewrite the left pane as above, and keep the marker line and the right pane's text exactly as they are unless Alan asks you to change them (the right pane is his own writing). If you give `current_state` without the marker, the existing right pane is kept for you. The Word report reads the two as one continuous piece. **Quiet week:** still produce it; the summary says "No change this week" (the default if empty) and the open position is still shown.
5. **Stage** with `report.py weekly-stage <spec.json>`. It fills `system/templates/weekly-report-template.docx` (house style) into `system/staging/drafts/YYYY-MM-DD Weekly report - <Project name>.docx` and stages one proposal (`source_run: "cx-weekly-report"`): the `updates` row, a `projects` health and `health_reason` change if any, and a `report` block (`kind: "weekly"`) whose file operations rewrite the "Current state" of the project's `CLAUDE.md` (keeping guidance and image lines), file the report to the project's weekly-reports folder (`projects/<CODE> <Name>/reports/` by default) as `YYYY-MM-DD Weekly report - <Project name>.docx` (the Friday date) and remove the draft. Approval stamps "Approved by Alan on <long date>".
5a. **Enrich for search (BL-07).** Write a two-line summary of the report (health and the one thing that matters) and three to eight topic tags, then run `system/scripts/run search.py enrich set --path "projects/<CODE> <Name>/reports/YYYY-MM-DD Weekly report - <Project name>.docx" --summary '<line 1>\n<line 2>' --tags "tag, tag, tag"` (the summary in single quotes and without an apostrophe: the guard refuses a backslash inside double quotes) (the path the staged report block files it to). Search then finds the report by what it says; the summary stays in `system/search/`, local and internal.
7. **Show** per project: the proposed health and reasons, a link to the draft, the summary, and the memory change. Then stop; Alan decides with cx-review.

## Rules

- **Individual approval:** weekly reports and health changes are excluded from bulk approval.
- **`PORTFOLIO.md` is never changed;** portfolio-level reporting is backlog BL-02.
- **Manual only;** never part of a scheduled task.
- **Undo covers it:** "undo last apply" reverses the report filing, the database rows and the memory change.
- **Dates:** DD-MM-YYYY in what Alan reads (long dates in the report header); YYYY-MM-DD stored and in file names.
- **Approval** checks the edited draft (health line, summary, current state) against what's staged; `review.py approve <n> --sync` carries the draft's wording into the staged items (current-state lists are kept; bold and italics edited in Word are not carried back).


## Status note

`Delayed` actions count as open (and as a slip signal). `Done` no longer exists; closed actions have status `Closed`.


## Dates in the report

Dates inside the report are DD-MM-YYYY (week ending shown as DD-MM-YYYY); the file name stays `YYYY-MM-DD Weekly report - <Project name>.docx`.
