---
name: cx-edit
description: creaite plain-English changes. Changes or adds tracker items, project details, projects themselves, project memory and the project register, from a plain-English instruction. Every change is shown before and after, confirmed by Alan, then waits for "apply". Use for requests like "mark ABC-A-003 done", "Sara owns the SOW action", "add an action for ABC…", "log a risk…", "record a decision…", "move ABC go-live to 2026-11-20", "ABC is at risk because…", "close all of Omar's ABC actions due before 2026-10-01", "add to ABC memory…", "add client.com to ABC's domains", "add project DEF…", "close project ABC", "archive project ABC", "restore project ABC", "change the code ABC to XYZ", "make ABC-002 client-visible", "ABC client report fortnightly".
---

# cx-edit

Turn a plain-English instruction into a staged, approved change. It is written only on the next "apply".

**Projects by name (BL-101):** refer to a project by its full name in everything Alan reads (summaries, tables, messages, file names, drafts). The short code appears only inside a work item's ID (`ABC-A-003`) and in a command he can type; `tracker.project_label(code)` gives the name.

Read these first:
- `dev/staging-format.md`
- `.claude/skills/cx-minutes/references/tracker-conventions.md`
- `projects/_portfolio/project-register.md`
- `projects/_portfolio/people-register.md` (BL-55)

**Dates:** show and accept DD-MM-YYYY; store YYYY-MM-DD.

**Script:** `system/scripts/run propose.py` does the exact parts: `preview <spec.json>` (validate and show before → after, writes nothing), `stage <spec.json>` (after Alan confirms), `new-project --code … --name … [--sponsor …] [--client …] [--rhythm …] [--objective …] --out <name>.json` and `close-project <CODE> --out <name>.json` (a spec to review and stage), `recode <OLD> <NEW> [--name …] [--folder …] [--dry-run]` (BL-111; stages itself), `setting <dotted.key> <value>` (settings, saved at once with a backup and a log line). `people list | resolve "<text>" | add | edit | rename | merge | map | migrate` is the people register (BL-55). For `new-project` and `close-project` always add `--out <name>.json`: the spec is saved in `system/staging/drafts/` (never `>` or `/tmp`) and the command says where, ready for `preview` and `stage`. Write other specs in `system/staging/drafts/`; `stage` deletes its spec itself once the proposal is written (BL-118), and `preview` keeps it so you can reuse it. A write's previous content and an update's `based_on` are filled in automatically. Run `propose.py` on its own, exactly `system/scripts/run propose.py …` (no `cd … &&`, pipe, redirect or heredoc; write the spec with the Write tool): it is already allowed in that form, so a refusal means the command's shape, not a missing rule (BL-140).

## Field names (BL-249)

Use each table's field names exactly; never guess one (a milestone has `name` and `description`, not `title` or `note`). Before writing a spec for a table you haven't written in this chat, run `python3 system/scripts/propose.py fields <table>` (read only): it lists the fields, the values each allows and which a new item needs. Run `preview` before saying a spec is ready, and fix any problem it reports before asking Alan anything. A change's reason is the item's own `note` (beside `changes`, not inside it); a milestone rebaseline is the item's `rebaseline` block. The writable fields, from `schema.sql` (`id` and `updated_at` are set by `tracker.py`):

<!-- BL-249 fields: generated from schema.sql by `python3 dev/tools/skill_fields.py`; don't edit by hand -->
| Table | Fields (`*` needed for a new item) |
|-------|--------|
| projects | `code`*, `name`*, `sponsor`, `phase`, `health`, `health_reason`, `next_milestone`, `milestone_date`, `active`, `archived` |
| milestones | `project`*, `name`*, `description`, `baseline_date`, `forecast_date`, `status`, `sort_order`, `percent_complete`, `state`, `state_set`, `state_reason`, `owner`, `actual_date`, `client_visible`, `client_message`, `internal_note`, `source`*, `archived` |
| workstreams | `project`*, `name`*, `lead`, `keywords`, `aliases`, `channel`, `status`, `created`, `source`*, `archived` |
| actions | `project`*, `description`*, `workstream`, `owner`, `priority`, `due_date`, `status`, `raised`*, `closed`, `latest_update`, `client_visible`, `client_message`, `milestone`, `source`*, `archived` |
| raid | `project`*, `type`*, `workstream`, `description`*, `owner`, `response_action`, `due_date`, `impact`, `likelihood`, `priority`, `status`, `raised`*, `closed`, `client_visible`, `client_message`, `milestone`, `source`*, `archived` |
| decisions | `project`*, `decision`*, `made_by`, `client_visible`, `client_message`, `date`, `status`, `needed_by`, `reasoning`, `options`, `revisit`, `replaces`, `source`*, `archived` |
| promises | `project`*, `promised_by`*, `promised_to`*, `description`*, `due_date`, `status`, `raised`*, `closed`, `source`*, `archived` |
| links | `from_item`*, `to_item`*, `kind`, `source`*, `created` |
| labels | `name`*, `colour`, `note`, `behaviour`, `default_choice`, `builtin` |
<!-- end BL-249 fields -->

## What it handles

| Kind | Examples | Proposal |
|------|----------|----------|
| Change an item | "mark ABC-A-003 done", "Sara owns the SOW action", "close the data access risk", "push ABC-A-007 to 2026-11-15" | `op: update` (status, owner, due date, description, impact, likelihood, priority and similar fields) |
| Add an item | "add an action for ABC: Omar to send data spec by Friday", "log a risk for DEF: …", "record a decision for ABC: …" | `op: new`. Your own actions get your full name as owner. Source: `Alan (cx-edit), YYYY-MM-DD` |
| Project details | "move ABC go-live to 2026-11-20", "ABC sponsor is now Fatima", "ABC is at risk: data access slipping" | `op: update` on `projects`. A health change **requires a reason**; if it's better than the evidence suggests, the preview shows the evidence and the reason must say why (BL-52; staging refuses it without one), which is stored as `health_reason`. cx-weekly-report still writes its own weekly row |
| Several items at once | "close all of Omar's ABC actions due before 2026-10-01" | One `op: update` per item, after a preview |
| Settings | "set sweep time to 06:30", "stale after 10 days", "turn reminders off" | Change to `system/config/settings.json`, applied instantly with a backup and a log entry, the same as the dashboard Settings tab |
| VIPs (BL-99) | "make Mia Hale a VIP", "Ben is a management VIP", "Mia isn't a VIP any more", "add Ben's second address b.ito@example.com" | A people-register change (`propose.py people edit`): the **VIP** column holds `management`, `client` or `yes` (blank: not a VIP); **Email** may hold several addresses, comma-separated. VIP alerts on or off, the check interval and the browser notification are settings (`vip.enabled`, `vip.check_minutes`, `vip.notify`) |
| Sweep ignore rules (BL-97) | "ignore calendar invites starting with ToDo in the sweep", "ignore mail from newsletters@vendor.com", "stop ignoring humancapital", "switch off the private rule" | A settings change to `sweep.ignore`: add a rule `{name, where: [mail, teams, calendar], field: subject \| sender \| channel, how: begins \| contains \| equals \| address \| domain, text, on}`, switch one off (`on: false`) or delete it. The built-in private rule (`builtin: "private"`) is switched off, never deleted. Show the rule before → after, as for other settings |
| New decision | "log a decision for ABC: … (source: 2026-10-01 steering minutes)" | Source is required; ask for it if missing. Add `reasoning`, `options`, `revisit` ("revisit if adoption falls below 60%" or a date) and `replaces` (an earlier decision's ID of the same project) only when Alan gives them |
| Decision needed (BL-53) | "decision needed from Sara by 16-10: pilot extension", "we need to decide the UAT venue" | `op: new` on `decisions` with `status: "Pending"`, no `date`, `made_by` the person asked (Alan's own name when it falls to him), `needed_by` if given. Source required: `Alan (cx-edit), YYYY-MM-DD` is fine |
| Record or withdraw a decision (BL-53) | "record the decision ABC-D-004: Sara agreed", "ABC-D-004 is made, 12-10", "withdraw ABC-D-004" | `op: update` on the same row (it keeps its D-number): `{"status": "Made", "date": "YYYY-MM-DD" (today if not said), "made_by": …}`; or `{"status": "Withdrawn"}`. A Made decision needs its date; a made one can't go back to Pending (record a new one that replaces it) |
| Workstreams (BL-58) | "add workstream Integration to ORX", "Sara leads ABC Data", "rename ABC Data to Data and analytics", "close ABC Testing", "add UAT as an alias of ABC Testing" | New: suggest first (`propose.py workstreams suggest ORX "Integration"`), show it, and on yes `propose.py workstreams add ORX "Integration" --lead … --keywords …`. Changes: `op: update` (or `cancel` to close) on `table: "workstreams"` by its ID (`propose.py workstreams list --project ORX`); a rename carries the project's items with it. The lead must be in the people register |
| New fields | "set ABC-A-003 workstream to Data", "priority urgent", "latest update: chased Omar", "mitigation for ABC-002: …", "due 2026-10-20" | Change on the item, written at the next apply (straight away with auto-apply) |
| Milestones | "add milestone for ABC: UAT complete 20-11-2026", "move ABC UAT milestone to 27-11-2026", "ABC UAT is done", "ABC UAT was achieved on 08-10-2026", "rebaseline ABC go-live to 15-12-2026, agreed with Sara at steering", "ABC go-live is at risk: security review open", "ABC UAT state back to the dates", "Will owns ABC UAT", "make ABC-M-002 client-visible", "link ABC-A-004 to UAT", "unlink ABC-A-004", "ABC UAT milestone is 60% complete", "clear the ABC UAT percentage" | `op: new` on `milestones` (baseline and forecast both set to the date); moving changes `forecast_date` only (record why as the item's own `note` key, beside `changes`, which goes to the Movement log); **a rebaseline** changes `baseline_date` and needs the item's `rebaseline` block, `{"agreed_with": [full names], "reason", "source"}`: ask for any that's missing, confirm explicitly, and say that it records a decision (BL-186); "done" or "achieved" sets `status` Done, `percent_complete` 100 and `actual_date` (the date said, else today; never a future date); **state** (BL-186): `state` On track, At risk, Slipped or Overdue (`state_set` follows); the preview says what the dates suggest, and a state better than that needs a one-line `state_reason` (ask for it); "back to the dates" clears `state`; **owner** is a full name from the people register; **client-visible** needs `client_message` (plain wording Alan gives; never write it for him); a percentage sets `percent_complete` (0–100), and "clear" sets it to null; linking sets or clears `milestone` on the action or RAID item. Linking is optional. Missed no longer exists: a late milestone is Overdue |
| Client visibility (requires complete client messaging; Claude never writes the messaging) | "make ABC-002 client-visible", "hide ABC-D-004 from clients" | `op: update` setting `client_visible` to 1 or 0 |
| Client-report rhythm | "ABC client report fortnightly", "ABC client report off" | File change to the `Client report rhythm:` line in the project's `CLAUDE.md` |
| Client report needed | "ABC needs no separate client report", "ABC needs a client report again" | File change to the `Client report: on \| off` line in the project's `CLAUDE.md` (a missing line is on; a new project starts off). The same setting is in the hub's Client report settings and Settings › Projects |
| Project memory | "add to ABC memory: sponsor prefers one-page updates" | File change to `projects/<CODE> <Name>/CLAUDE.md` or `projects/_portfolio/PORTFOLIO.md` |
| Register | "add client.com to ABC's domains", "add Omar as a DEF stakeholder" | File change to `projects/_portfolio/project-register.md` |
| People register (BL-55) | "add Sara Khan to the people register, sara.khan@northgate.example, Northgate, sponsor", "Sara K is also SK", "Sara's role is programme sponsor", "rename Sara Kahn to Sara Khan", "merge S. Khan into Sara Khan" | `propose.py people add \| edit \| rename \| merge` stage a file change to `projects/_portfolio/people-register.md` (a rename or merge also updates every item that person owns, and a merge keeps the old name as an alias) |
| New project | "add project DEF, Digital Enablement, sponsor Omar" | Creates the folder `projects/DEF Digital Enablement/` with `minutes/`, `transcripts/`, `documents/` and `reports/` (with a projects folder outside the vault: a copy of its template skeleton, under the engagement's name); a `CLAUDE.md` from `system/templates/project-CLAUDE-template.md` with the brief filled from what Alan said; a register row; and a `projects` row (`op: new`) |
| Recode a project (BL-111) | "change ORX to FAL, Kestrel Energy AI", "rename the ORX project and its code" | Changes the code (and name) everywhere in one step: every item ID keeps its number under the new code, history and links follow, the old code is retired. Run `propose.py recode ORX FAL --name "Kestrel Energy AI" --dry-run`, show Alan the preview and the "Check:" lines, then (after his yes) run it without `--dry-run`; it stages an approved proposal that is applied **on its own**. Creaite never renames the engagement folder: if Alan renames it, add `--folder "<new name>"`. Relay the "Check:" lines (people register, `PORTFOLIO.md`, dismissed reminders, the old name as an alias). Undo is "undo last apply" |
| Archive a project (BL-09) | "archive project ABC" | `propose.py archive ABC --out archive.json`: the folder moves to `99 Archive/`, the register row to Retired codes, the project closes and it and its items are marked archived (they leave the views, the export, the reminders and matching; search still finds the items, marked Archived). With open items it stops and lists them: show them and ask **Cancel them all and archive** (then `--cancel-open`, which cancels them in the same proposal) or **Stop**. Preview, confirm, stage, apply; undo reverses it. Never move a folder into or out of `99 Archive` (or the old `_Archive`, `zz Archive`) any other way, and never put `archived` (in the field lists below) in a spec: only archive and restore set it |
| Restore an archived project (BL-09) | "restore project ABC" | `propose.py restore ABC --out restore.json`: the folder back (a number if its name is taken), the register row back, its items live again, `active` as it was. Preview, confirm, stage, apply |
| Close a project | "close project ABC" | Sets `active = 0` on `projects`. Nothing is deleted or moved, and the register row stays. Open items are listed so Alan can decide whether to close them too |

## Flow

1. **Interpret.** Resolve relative dates ("Friday", "end of month") against today, and always show the result as `DD-MM-YYYY` (store `YYYY-MM-DD`).
2. **Find the target** by ID or description, using the database read-only: `system/scripts/run tracker.py read <table> --id ID`, or by its words `system/scripts/run tracker.py read <table> --project CODE --search "SOW"` (case-insensitive; add `--status open` for open items only; BL-252). Never read a whole table and filter it, and never pipe the output. If more than one item could match, list the candidates and ask. Never guess.
3. **Show before → after:**
   - **one change:** `ABC-A-003 · Status: Open → Closed` ("done" means Closed; "delayed" sets Delayed);
   - **several items:** a preview table of every affected item, with its current and new values. Alan can say "all", "all except 3", or pick numbers;
   - **new items and projects:** every field in full;
   - **file changes** (memory, register, new project): the exact lines added or changed, or the files and folders to be created;
   - **memory files:** if the change would push a file past about one page, suggest a trim as part of the same change.
4. **Preview** with `propose.py preview <spec.json>`: it validates and prints before → after (file changes as added and removed lines). Show any rule failure at once.
5. **In ask creaite (the dashboard panel, BL-258, BL-314):** don't ask for a confirmation and don't stage. A change to fields of existing actions, risks and issues or decisions (status, owner, due date, priority, description, latest update, response, impact, likelihood, type; a decision's maker, date made, needed by, reasoning), at most ten, goes through the dashboard's own edit: write no spec, and end your reply with one line per field, exactly `EDIT: <item ID> | <field> | <new value>` (dates DD-MM-YYYY); the server checks each against the tracker and Alan's Go ahead saves it as the dashboard does, with Undo. For anything else, write the spec in `system/staging/drafts/<name>.json`, preview it, and end your reply with exactly one line: `CHANGE: system/staging/drafts/<name>.json | <short title>`. The server shows Alan one card with the exact before and after from `propose.py preview`; Approve stages and applies it at once, Reject discards it. Never run `propose.py stage` or `tracker.py apply` for it yourself. A recode and a setting are not for the card (see below).
6. **Elsewhere, on Alan's confirmation:** `propose.py stage <spec.json>` writes `system/staging/proposed-YYYY-MM-DD-HHMMSS-edit.json` (`source_run: "cx-edit"`, approved). Say "Staged and approved; it'll be written at your next apply" (with the live server and auto-apply, the dashboard applies it at once). **In a confirmed ask creaite run** (Alan pressed Go ahead on this change, BL-306): stage it and don't run `tracker.py apply`; the server applies what you staged once when you finish (with auto-apply on) and tells Alan, so say only that it is staged. Memory, register, rhythm and new-project file changes go in the spec's `file_changes` block; settings use `propose.py setting` instead.

## People in an owner (BL-55)

Before previewing a change that names an owner (or a decision's maker), run `propose.py people resolve "<name>"`. `known`, `alias` or `email`: use the full name it returns (`preview` and `stage` also do this and say so on a `Person:` line). `likely`: ask "Is 'Sara' Sara Khan?" and, on yes, offer to remember the alias (`people edit "Sara Khan" --add-alias Sara`). `unknown`: ask for the full name (required), and the email, aliases, organisation and role if Alan has them, then `people add` (a separate staged change, written at the same apply). Never guess; never stage an owner the register doesn't know without telling Alan.

## Rules

- **Never delete.** Items become `Cancelled`; projects become inactive.
- **Nothing is written until "apply".** "undo last apply" reverses cx-edit changes, including file changes.
- **New project codes** must be 3 to 7 capital letters or digits, starting with a letter, and not already used, including retired codes. Check the register.
- **Never change** IDs, sources, or the `change_log`.


## Dates

Accept dates as DD-MM-YYYY (or relative: "next Friday"); show the result as DD-MM-YYYY before confirming; store YYYY-MM-DD. Decisions can carry plain client messaging ("client messaging for ABC-D-004: …").
