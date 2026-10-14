---
name: cx-steerco
description: creaite steering-committee one-pager (BL-92). Drafts a one-page Word summary of one project for its steering committee, in an internal or a client-safe version, and files it in the project's Steerco folder on approval. Never sends anything. Use when Alan says "steerco one-pager ABC", "steering one-pager for ABC", "steerco one-pager ABC client-safe", "draft the one-pager for the ABC steering", or presses "Draft the one-pager" in a steering meeting's Prep.
---

# cx-steerco

A Word one-pager for a project's steering committee, from the tracker: nothing is invented. It is drafted for approval like the weekly and client reports, and on approval filed in the project's Steerco folder. creaite never sends it, never creates an email, and never schedules it. Manual only.

## Which version

Alan picks one when he asks (or you ask, once):
- **Internal** (default): everything, with items carrying a label (Sensitive) marked beside them and a line in Overall Status. It is for Alan and the committee; never to the client.
- **Client-safe** ("client-safe", "for the client"): follows the client-report rules. Only items flagged client-visible with complete client messaging, in their client wording; no owners, priorities or IDs; no Flow or internal early warnings. An item carrying a label that excludes it (Sensitive, by default) is left out even if client-visible. Say so, and if Alan wants one kept ("include ABC-D-005"), pass it in `include_labelled`: Review then stops at it, and Alan decides there.

## Flow

1. **Pre-check.** If the daily sweep is due, run cx-sweep first. `report.py steerco-data <CODE>` (add `--version client`) is read-only JSON: `blocked` (pending items for the project: "Orion Bank migration has 4 items awaiting review — review first" (the project's name, not its code); `steerco-stage` refuses unless `force`), `since` (the date of the last one-pager in the Steerco folder, else the last 14 days; `--since` overrides), and every section.
2. **Read the facts.** Status and trend, what changed since the last steering (milestones moved, new risks, decisions, items closed), milestones with forecast against the agreed date and their state in the one vocabulary (Achieved, On track, At risk, Slipped, Overdue; the client-safe version holds only client-visible milestones, in the client's words: Achieved, On track, At risk, Expected later, Late, BL-186), top risks and issues with owners and responses, **decisions needed** (BL-53: for the committee and for Alan), **blockers** (BL-90: dependencies attached to a milestone, and the links table), **flow** (BL-91, one line), and the **next period** (actions overdue or due in 14 days). For the client-safe version, `omitted` lists what was left out and why (messaging to complete, labelled items): tell Alan.
3. **Optional summary.** You may add one to three short paragraphs under Overall Status (`summary` in the spec): what matters and what the committee is asked to do, in British English, leading with the answer. Only from the facts you read. Never invent an item, a date or a figure; never restate the tables.
4. **Stage.** Write the spec in `system/staging/drafts/` (`steerco-stage` deletes it itself once the one-pager is staged): `{"code": "ABC", "version": "internal" | "client", "summary": [..], "steerco_date": "YYYY-MM-DD" (default today), "since": "YYYY-MM-DD", "include_labelled": [ids], "force": false}`, then `system/scripts/run report.py steerco-stage <spec.json>`. It fills `steerco-template.docx` (a section with nothing to say is left out, never shown empty), writes the draft to `system/staging/drafts/YYYY-MM-DD <Project name> Steerco one-pager[ (client)].docx` and stages one proposal (`source_run: "cx-steerco"`) with a `report` block (`kind: "steerco"`, `version`). On approval it is filed as `YYYY-MM-DD <Project name> Steerco one-pager[ (client)].docx` in the project's Steerco folder (`locations.folders.steerco`), **never overwriting or renaming** a file already there (a second one the same day is numbered), and the status line becomes "Approved by Alan on <date>".
5. **Show Alan** the version, where it will be filed, what was left out and why, any sensitive items, and a link to the draft. Then stop: Alan decides with cx-review. Approving the client-safe version runs the client-report checks (internal IDs or wording, "Client-safe: no" memory lines, confidential or documents/ text) and BL-94's label check; "approve N --as-staged" files it anyway.
6. **Enrich for search (BL-07).** Write a two-line summary and three to eight topic tags, then `system/scripts/run search.py enrich set --path "<the filed path printed by steerco-stage>" --summary "<line 1>\n<line 2>" --tags "tag, tag, tag"`.

## Rules

- One project per page. A portfolio roll-up is BL-02, not this.
- Refer to the project by its full name in everything Alan or the committee reads; the code appears only inside an item ID or a command you quote (BL-101).
- The internal version is marked **Internal**; nothing from `documents/` goes into either version.
- Never send, never draft an email, never overwrite. If the document is open in Word, say so and wait.
