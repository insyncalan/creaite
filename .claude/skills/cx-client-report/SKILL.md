---
name: cx-client-report
description: creaite client report. Drafts a client-safe Word status report for one project, filed in that project's reports folder on approval. Never sends anything and never creates email drafts. Use when Alan says "client report ABC", "client report ABC since 2026-09-01", or responds to a client-report reminder.
---

# cx-client-report

A client-safe status report for one project, drafted for review. Claude **never sends it and never creates an email draft**. Alan distributes it himself.

**Projects by name (BL-101):** refer to a project by its full name in everything Alan reads (summaries, tables, messages, file names, drafts). The short code appears only inside a work item's ID (`ABC-A-003`) and in a command he can type; `tracker.project_label(code)` gives the name.

Read these first:
- the project's `CLAUDE.md` (sensitivities, `Client-safe: no` lines, client-report rhythm)
- `dev/staging-format.md`
- `.claude/skills/cx-minutes/references/tracker-conventions.md`

## Script

`system/scripts/run report.py client-data <CODE> [--since YYYY-MM-DD]` gives the client-safe facts (the filter below, already applied), what's excluded and what needs client messaging. `report.py client-stage <spec.json>` fills the report and stages it; the tables, decisions and risks come from the tracker's client messaging, never from Claude. Spec: `{"code", "period_start", "summary": [..], "progress": [..], "next_steps": [..], "input_needed": [..], "force": false}`. Write it in `system/staging/drafts/`; `client-stage` deletes it itself once the report is staged.

## Triggers

- **Manual:** "client report ABC", "client report ABC since 2026-09-01".
- **Reminder only** (a session-start rule in `CLAUDE.md`): each project's `CLAUDE.md` holds `Client report rhythm: weekly | fortnightly | monthly | off` (default **weekly**). When the last approved client report (the latest `* Client report.docx` in the project's client-reports folder: `reports/` by default) is older than the rhythm, open with "ABC client report due (last: YYYY-MM-DD) — say client report ABC". Never draft anything without being asked.

## Flow

1. **Period:** from the day after the last approved client report to today, or the period Alan names. For the first report, ask Alan for the start date.
2. **Pre-check:** if the project has items pending review, say so and recommend reviewing first. Alan may go ahead anyway.
3. **Gather,** read-only from `tracker.db` and the latest approved weekly report: health and reason, progress, milestones, actions, decisions.
4. **Apply the client-safe filter.** Include only:
   - **health:** the internal rating and its reason (as Alan decided);
   - **progress and summary:** written for the client, from tracker facts;
   - **milestones:** only client-visible ones with their client wording (BL-186: the same filter as the Milestones page's Client view), with the agreed date (and the expected one when later), % complete (milestone-level only; the linked actions behind a calculated figure stay internal) and the state in the client's words: Achieved, On track, At risk, Expected later or Late (Overdue). A milestone left out because its wording is missing is listed for Alan, never invented. No movement history, notes or internal milestones;
   - **actions:** those owned by client people (the owner names the client organisation, or the person is a client stakeholder in the register) **and** our commitments to the client. Each also needs `client_visible = 1`, or must be clearly addressed to the client;
   - **decisions:** only `client_visible = 1`;
   - **risks and issues:** only `client_visible = 1`.

   **Always exclude:**
   - anything from `documents/` (with a projects folder outside the vault: anything outside the mapped report folders);
   - lines marked `Client-safe: no` in memory;
   - anything marked confidential;
   - internal commentary and internal owners' remarks.
5. **Write** the summary, progress, next steps and input needed in a professional, client-facing tone, in British English, from tracker facts only. Use the executive voice (BL-106): read `system/templates/executive-style.md` (its client-safe audience: the same shape, plainer, no internal remarks) and run `system/scripts/run report.py facts <CODE> --audience client` for the ranked client-safe sheet (only client-visible items in their client wording, including any decision the client is asked to make). Open the summary with the position and the one thing that matters; put what the client must do, by when, under input needed. The dashboard's client-safe Generate uses the same guide and sheet.
6. **Stage** with `report.py client-stage <spec.json>`: it fills `system/templates/client-report-template.docx` (house style) into `system/staging/drafts/YYYY-MM-DD Client report - <Project name>.docx` and stages a `report` block (`kind: "client"`, `source_run: "cx-client-report"`) that files it to `projects/<CODE> <Name>/reports/YYYY-MM-DD Client report - <Project name>.docx` on approval and removes the draft. Then enrich it for search (BL-07): a two-line summary and three to eight topic tags, with `system/scripts/run search.py enrich set --path "projects/<CODE> <Name>/reports/YYYY-MM-DD Client report - <Project name>.docx" --summary "<line 1>\n<line 2>" --tags "tag, tag, tag"`; the summary is internal (kept in `system/search/`, never in the report). It refuses while items are pending unless `"force": true` (Alan's choice), and asks for a start date for the first report.
7. **At approval** `review.py` scans the (possibly edited) draft for internal content: IDs or wording of items not client-visible, lines marked `Client-safe: no`, "confidential", "restricted" and `documents/`. Show each finding; only on Alan's say-so use `approve <n> --as-staged` to file it anyway.
8. **Show:**
   - a link to the draft;
   - a **client-visible inclusion list:** every flagged item included, so nothing surprises Alan;
   - anything excluded that he might expect to see, such as Urgent risks not flagged client-visible.

   Then stop; Alan decides with cx-review.

## Rules

- **Never send. Never create Outlook drafts.**
- **Individual approval:** excluded from bulk approval.
- **Undo covers the filing.**
- **Dates:** DD-MM-YYYY in what Alan and the client read (long dates in the report header); YYYY-MM-DD stored and in file names.


## Client messaging (applies to actions and RAID items)

- For each client-visible action or RAID item, use its **client_message** (What it is / What it means for you / What is being done) **instead of the internal description**. Keep the PM's wording; light tidying only.
- If a client-visible item's messaging is incomplete, do not invent it: list the item under "Needs your client messaging" in the inclusion list at review, and leave it out of the draft until completed.
- Status wording: Open and Delayed are "In progress" / "Delayed"; Closed is "Complete" (actions and RAID items). Milestones use the five states in the client's words (above), never Complete or Delayed.


## Dates and decisions

Dates inside the report are DD-MM-YYYY; the file name stays `YYYY-MM-DD Client report - <Project name>.docx`. Client-visible decisions are described with their plain client messaging; leave out any without it and list them for Alan.
