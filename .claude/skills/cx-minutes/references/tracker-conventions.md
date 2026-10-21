# Tracker conventions (`tracker.db`)

The record is a SQLite database at `system/tracker.db`, defined in `system/scripts/schema.sql`. Never write to it directly. All changes go through a proposal in `system/staging/`, approved by Alan and applied with `system/scripts/run tracker.py apply <file>`. The schema rejects invalid values, so a failed apply means a proposal needs fixing.

## Tables

| Table | Fields |
|-------|--------|
| projects | code · name · sponsor · phase · health · health_reason · next_milestone · milestone_date · active |
| milestones | id · project · name · description · baseline_date · forecast_date · status · sort_order · percent_complete · source |
| workstreams | id · project · name · lead · keywords · aliases · channel · status · created · source |
| actions | id · project · description · workstream · owner · priority · due_date · status · raised · closed · latest_update · client_visible · client_message · milestone · source |
| raid | id · project · type · workstream · description · owner · response_action · due_date · impact · likelihood · priority · status · raised · closed · client_visible · client_message · milestone · source |
| decisions | id · project · decision · made_by · client_visible · client_message · date · status · needed_by · reasoning · options · revisit · replaces · source |
| promises | id · project · promised_by · promised_to · description · due_date · status · raised · closed · source |
| links | from_item · to_item · kind · source · created |
| labels | name · colour · note · behaviour · default_choice · builtin |
| item_labels | item_id · label · added_by · added_at · reason · suggested |
| updates | week_ending · project · health · summary · key_changes |
| rejected | fingerprint · rejected_at · via · reason · duplicate_of (BL-133: the reason given and, for a duplicate, the item it repeats; both optional) |

## Allowed values

- **raised** (actions, RAID and promises, never decisions: a decision is dated by `date`, #280; BL-26): always written, as the source's date — the meeting date for minutes and transcripts, the Sent date for an email or Teams message — never the review date. If it's missing, `tracker.py apply` fills it the same way (the source's date, else the day the proposal was staged) and says so.
- **status:** actions `Open`, `Delayed`, `Closed`, `Cancelled` (Delayed counts as open); RAID `Open`, `Closed`, `Cancelled`. Closing or cancelling sets `closed` (YYYY-MM-DD, not before `raised`). "Done" in plain English means Closed.
- **decisions status (BL-53):** `Pending`, `Made`, `Withdrawn`. Every decision made before BL-53 is `Made`.
- **promises status (BL-50):** `Open`, `Done`, `Dropped` (Done and Dropped set `closed`).
- **links kind (BL-90):** `blocks`. **labels behaviour (BL-94):** `warn`, `exclude`; `default_choice`: `include`, `exclude`.
- **health:** `On track`, `At risk`, `Off track`
- **type:** `Risk`, `Assumption`, `Issue`, `Dependency`
- **impact, likelihood:** `High`, `Medium`, `Low`
- **priority:** `Urgent`, `High`, `Medium`, `Low`

## IDs

- `<CODE>` is the project code: 3 to 7 capital letters or digits, starting with a letter (e.g. `ABC`, `ORX2C`).
- Milestones `<CODE>-M-<3 digits>` (e.g. `ABC-M-002`).
- Promises `<CODE>-P-<3 digits>` (e.g. `ABC-P-001`). Links and item labels have no ID of their own: a link is `from_item|to_item|kind`, an item label `item_id|label` (in `change_log` and `id` fields of proposals).
- Format: actions `<CODE>-A-<3 digits>` (e.g. `ABC-A-014`, `ORX2C-A-003`), decisions `<CODE>-D-<3 digits>`, RAID items `<CODE>-<3 digits>` (e.g. `ABC-007`; the type is a field, not part of the ID). One number sequence per project is shared by actions, RAID items, decisions and promises, so a number is never used twice across them (`ABC-A-002` means there is no `ABC-002` or `ABC-D-002`). Milestones and workstreams count separately. IDs issued before this rule may repeat a number across types; they are not renumbered.
- `tracker.py` assigns IDs on apply. Proposals never include IDs for new items.
- **A project's code can change** (BL-111, `propose.py recode`): every ID keeps its number and takes the new code (`ORX-A-001` becomes `FAL-A-001`), and the history follows. The old code is retired for good. Never edit IDs by hand or with SQL.

## Milestones

- **status:** `Planned`, `Done` (Achieved) or `Cancelled` (removed: hidden from the timeline, kept in history; creaite never deletes). **Missed is retired** (1.5.0, BL-186): a late milestone stays Planned and its state is Overdue. `baseline_date` is the **Agreed** date (the current baseline); the first agreed date in `change_log` is the **Original**, so it has no column. `forecast_date` is the date now expected. Moving a milestone changes the forecast only.
- **Rebaseline** (BL-186): changing an existing `baseline_date` is a rebaseline. It needs the item's `rebaseline` block (`agreed_with`: one or more full names, `reason`, `source`; optional `date`), and the apply records a **decision** (Made, by those people, with the reason and source) in the same apply, so one undo takes both. Setting a first baseline where there was none is not a rebaseline. Never propose a rebaseline from a meeting unless the meeting agreed it; a forecast move is the usual change.
- **The five states** (BL-186), one vocabulary on the dashboard, in the Word reports and the one-pager: **Achieved** ✓ (status Done), **On track** ●, **At risk** ▲, **Slipped** ◆, **Overdue** ✕. `state` is NULL while creaite follows the dates (`state_set` 0); the dates suggest Overdue when the agreed date has passed and it isn't done, Slipped when the forecast is later than the agreed date, On track otherwise. At risk is only ever Alan's call. When Alan sets a state, `state_set` is 1; a state **better** than the dates suggest needs a one-line `state_reason`. Clearing `state` returns it to the dates. Clients read On track, At risk, Expected later, Late and Achieved.
- **Achieved:** status Done with `actual_date` (the date achieved; today if none is given; never after today). Reopening (status Planned) clears it.
- **owner:** a full name from the people register (BL-55), or empty.
- **client_visible** (0 or 1, off by default) and **client_message** (plain wording, required when visible). Only client-visible milestones with their wording reach a client report or a client-safe one-pager; their state is in the client's words.
- **internal_note** (BL-186): Alan's own words about the milestone, shown on the Milestones page's Movement view. **Internal only:** never in a client report, a client-safe one-pager, the Client view or any client output. Set it only when Alan gives the words.
- **percent_complete** (BL-29): 0–100, set by Alan. On the Milestones page it is shown as he set it, never calculated from actions (BL-186); older views and reports still fall back to linked actions when it is empty. Done sets 100; 100 doesn't mark it Done. Slips still come from dates, never from the percentage.
- **Slip** = forecast − agreed, in days. It feeds the health criteria (`settings.json` `health`).
- **Linking is optional.** An action or RAID item may carry `milestone` (an existing milestone ID) or leave it empty. Set it only when the source or Alan ties the item to that milestone; never guess.
- **Progress** of a milestone without Alan's figure = closed linked actions ÷ all linked actions (cancelled ones excluded), in older views only.

## Writing descriptions

- **Actions:** start with a verb, ≤ 100 characters. Example: `Send revised SOW to client`.
- **Decisions:** state the outcome. Example: `Go-live moves to 15 Nov`.
- **Risks:** `<event> → <impact>`. Example: `Data access delayed → MVP slips`.
- **Issues:** the current problem in plain words.

## Priority (raid)

| Impact and likelihood | Priority |
|-----------------------|----------|
| Both High | Urgent |
| One High | High |
| Both Low | Low |
| Anything else | Medium |

## Dates

- Store dates as `YYYY-MM-DD`; show them to Alan (messages, minutes and report text, dashboard) as `DD-MM-YYYY`. Accept `DD-MM-YYYY` (and relative dates) from Alan and convert. File names keep `YYYY-MM-DD Title`.
- Set a due date only when the source states one.
- Resolve relative dates ("next Friday") from the meeting date.

## Client visibility

`client_visible` is 0 by default. Never set it to 1 during extraction; only Alan sets it, through cx-edit or Excel.

## Owners

- **Alan's own items:** set `owner` to his full name from `system/config/settings.json` (`identity.name`) when he is named, or committed in his own sent mail, chat or transcript turn. There is no separate "mine" flag; My actions and the "You" chip match on the name.
- **Owner names (BL-55):** the **full name** from the people register (`projects/_portfolio/people-register.md`: full name, email, aliases, organisation, role). Map what a source says (a first name, nickname, initials, an email address) to the full name only on an exact match of the full name, an alias or the email; `propose.py people map <file>` does it for a draft proposal, and `propose.py people resolve "<text>"` answers one name. A name the register doesn't know stays as written, gets the `unknown-owner` flag, and is resolved in Review (never guessed from a likely match). No owner stated = `TBC`.
- **workstream (BL-58):** match the project first, then the workstream from **that project's list only** (`tracker.py read workstreams --project CODE`): by its name, a keyword or alias ("UAT" for Testing), its lead, or its Teams channel. Never use another project's workstream, even if the name matches. Write the name as the list spells it. If the source names a workstream the project doesn't have, write that name anyway: staging leaves it blank and flags it `new-workstream` with the name as a suggestion for Review (never invent one). If nothing fits, leave it blank. `tracker.py` refuses an item whose workstream isn't an Active workstream of its project.
- **priority (actions):** `Medium` unless urgency is stated (`Urgent`/`High`) or clearly low.
- **response_action (RAID):** fill only when the source states what is being done about it; otherwise leave empty (the dashboard flags it).
- **due_date (RAID):** the target date for the response action, only if stated.
- **latest_update (actions):** `DD-MM-YYYY: what happened` when a source reports progress on an existing action (proposed as an update).
- **client_message:** always the three headings `What it is:` / `What it means for you:` / `What is being done:`. **Never write the text** — the PM completes it. Required complete only when `client_visible = 1`; never propose client_visible = 1 yourself.

- Write `Name`, or `Name (Company)` for external people.
- If no owner is stated, use `TBC` and add the `no-owner` flag.

## Source

- Files: path relative to the vault root, e.g. `projects/ABC Example Programme/minutes/2026-10-01 Steering committee.docx — Actions`. `projects/` is a logical prefix: with a projects folder outside the vault (BL-85) it stands for that folder, so a source is `projects/<engagement folder>/<path inside it>` and keeps working if the folder moves (settings `locations`)
- Email: `Email: <subject>, <date>`
- Teams: `Teams: <chat or channel>, <date>`


## Decisions: source is required

Every decision records where it was made: the minutes file and section, the email (subject — sender, date) or the Teams message. A decision without an identifiable source is not proposed; ask Alan instead. Decisions added in the dashboard or with cx-edit must include a source reference (stored with "recorded by Alan …, YYYY-MM-DD").

## People and workstreams

People come from the people register (see Owners; the old `settings.json` `people` lists are moved into it by cx-setup). People are added, edited, renamed and merged in the dashboard's Settings › People or with cx-edit (`propose.py people add|edit|rename|merge`), applied to every item in one apply, with Undo; a merge keeps the old name as an alias. Workstreams live in the tracker's `workstreams` table (BL-58), each in its own project: name, lead (a full name from the people register), keywords, aliases, Teams channel, Active or Closed. They are added, renamed and closed through proposals (`table: "workstreams"`; a rename carries that project's items with it, and a closed one can't be newly set), from Settings › Workstreams, the picker, Review or cx-edit (`propose.py workstreams …`). `tracker.py migrate` seeded them from the items and the old `settings.json` `workstreams` lists, which cx-setup then clears. Never re-introduce a retired spelling.


## Updates from a meeting (BL-65)

- A meeting may update an **open** item of its own project: actions (`status`, `due_date`, `latest_update`) and RAID items (`status`, `response_action`, `due_date`). Never owner, title or project. Closed, other-project and missing items are refused by `minutes.py stage`, naming the item.
- `latest_update` reads `DD-MM-YYYY: what happened`. `status` is Closed only when the transcript says it's done, Delayed when it says it's late. `response_action` is only what the transcript says is being done about it.
- The expected items come from `minutes.py expected <CODE> --title "<title>"`. An item not discussed is left alone. A discussed item is never proposed again as new; a repeat is also logged as a mention (BL-51).

## Source references (format)

Every item's `source` is one of:
- **File:** `projects/<CODE> <Name>/<folder>/<file> — <section>` (e.g. `… /minutes/2026-10-01 Steering committee.docx — Actions`). The dashboard shows the file name as a link that opens the file.
- **Email:** `Email · From: <name> <address> · Subject: <subject> · Sent: YYYY-MM-DD HH:MM · Link: <Microsoft 365 message link>`.
- **Teams:** `Teams · Channel: <name>` (or `Chat: <name>`) ` · From: <name> · Sent: YYYY-MM-DD HH:MM · Link: <message link>`.

Store references only — never message content. The Link (from Microsoft 365) powers "Open in Outlook" / "Open in Teams"; if no link is available, omit it.


## Decision records and decisions needed (BL-53)

- **A decision can be Pending before it is made.** `status` is `Pending`, `Made` or `Withdrawn`; the D-number is assigned when it is first recorded and kept when it is made. `made_by` holds who it is asked of while Pending (or Alan himself, when it falls to him) and who made it once Made. `needed_by` is a date, optional.
- **`date` is the date it was made.** A Made decision has one (`tracker.py` and the schema refuse a Made decision without it); a Pending one has none (a date on a Pending decision is refused). Making it is an update on the same row: `{"status": "Made", "date": "YYYY-MM-DD", "made_by": …}`; withdrawing is `{"status": "Withdrawn"}`. A Made decision can't go back to Pending (record a new one that replaces it).
- **Fuller record:** `reasoning` (why), `options` (the alternatives considered), `revisit` (a date as YYYY-MM-DD, or a trigger in words: "revisit if adoption falls below 60%") and `replaces` (the D-number of an earlier decision of the **same project**; it can't loop). Fill them only where the source states them; never guess.
- **Raising one:** propose `op: new`, `table: decisions`, `status: Pending`, with `needed_by` and `made_by` only if the source says so. The source rule still applies.

## Promises (BL-50)

Commitments made in passing, lighter than actions: `promised_by` and `promised_to` (full names from the people register, mapped like owners), `description`, optional `due_date`, `status` (`Open`, `Done`, `Dropped`), `raised` (the source's date, as for actions), `source`. No priority, workstream or client visibility. Cancelling a promise sets it to `Dropped`.
- **Capture (BL-125 A):** cx-minutes and cx-sweep propose them, only when Alan made the promise or it was made to him, and only for a commitment in passing: anything agreed as an action stays an action, never both. A promise said again is a mention of the open one (an update if it gives a new date); one kept, dropped or moved is an update (`status` Done or Dropped, `due_date`).
- **Lists:** "You owe" is Alan's open promises; "Waiting on" is the open promises others made to him whose due date has passed, each with how long it has been quiet (days since it was raised or last mentioned in `mentions.jsonl`). `system/scripts/run tracker.py read promises --list owe|waiting` (with `--project`, `--search`). A promise with no due date is never overdue.

## Links (BL-90 part 2)

`from_item` blocks `to_item` (`kind` is `blocks`). Either end is an action, RAID item, milestone, decision or promise ID, in any project; both must exist, they must differ, and links can't loop (A blocks B blocks A). A link is proposed as `op: new, table: links` and removed with `op: cancel, id: "<from>|<to>|blocks"`. Extraction proposes links only as suggestions Alan approves in Review.

## Labels (BL-94)

- **A managed list.** `labels` holds each label's `name` (no commas or bars; names ignore case), `colour`, `note`, `behaviour` (`warn`: shown with a warning; `exclude`: always kept out of client reports) and `default_choice` (`include` or `exclude`: what the warning card preselects). **Sensitive** is built in (`builtin = 1`; warn, with exclude as the default choice): it can't be deleted or renamed, and a new label is never built in. A label still on items can't be deleted. A new label is `op: new, table: labels`; delete with `op: cancel, id: "<name>"`.
- **On items.** Actions, RAID items and decisions carry labels in `item_labels` (`item_id`, `label`, `added_by`, `added_at`, `reason`, `suggested`: 1 when Claude proposed it). A proposed item takes `labels` (a list, or comma-separated text) in `values`, with `label_reason` and `label_suggested` beside it; an update takes `labels` in `changes` as the **full set** the item should have (labels not listed are removed, `[]` or `null` removes all). **An unknown label is refused, never created**; the spelling stored is the label's own. Rows can also be proposed directly: `op: new, table: item_labels`, and `op: cancel, id: "<item>|<label>"`.
- **People labels** are a **Labels** column in `people-register.md` (comma-separated), read by `propose.py people` and the dashboard; they aren't in the schema.
- **Undo.** Labels, links and promises are logged and undone with their apply like any row. A deleted links, item_labels or labels row is recorded in `change_log` with field `(removed)` and the row as JSON in `old_value`, so undo puts it back.

## Decisions: client messaging

Decisions carry `client_visible` and a plain-text `client_message` (no fixed headings). It must hold a short explanation before a decision can be made client-visible; Claude never writes it. As for actions and RAID, the check applies when the item is made client-visible or its messaging is edited.

## Rejected items and their reasons (BL-133)

- A rejected proposal's fingerprint (project, type and normalised text) is stored in `rejected`, and the exact item is never proposed again.
- A rejection may carry a **reason** (`reject_reason` on the proposed item: Duplicate, Not mine to track, Not an action, Other or Alan's own words; one line, at most 200 characters) and, for a duplicate, **`duplicate_of`** (an existing action, RAID item or decision ID; apply refuses one that doesn't exist).
- `system/scripts/run tracker.py read rejected --project <CODE> [--days 90]` lists the project's rejections that carry a reason, newest first, each with the item's text. cx-minutes and cx-sweep read it before extracting, as guidance: avoid proposing the same kind of item again. It never blocks anything by itself; only the fingerprint does.
