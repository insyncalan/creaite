# Staging format — `system/staging/proposed-YYYY-MM-DD-HHMM.json`

The single contract between everything that proposes changes (skills, Excel import, plain-English edits) and the one thing that writes them, `system/scripts/tracker.py apply`.

```json
{
  "created": "2026-10-02T08:30:00",
  "source_run": "cx-minutes | cx-sweep | cx-weekly-report | cx-client-report | excel-import | cx-edit | dashboard",
  "files": ["ABC Example Programme/minutes/2026-10-01 Steering committee.docx"],
  "items": [
    {
      "n": 1,
      "op": "new",
      "table": "actions",
      "values": {"project": "ABC", "description": "Send revised SOW to client", "owner": "Alan Carter", "workstream": "Commercial", "priority": "High",
                 "due_date": "2026-10-09", "raised": "2026-10-01",
                 "source": "ABC Example Programme/minutes/2026-10-01 Steering committee.docx — Actions"},
      "match": "strong",
      "flags": [],
      "decision": "pending"
    },
    {
      "n": 2,
      "op": "update",
      "table": "raid",
      "id": "ABC-001",
      "changes": {"status": "Closed", "closed": "2026-10-03"},
      "based_on": "2026-10-01 17:04:00",
      "match": "strong",
      "flags": [],
      "decision": "pending"
    }
  ],
  "status_signals": ["Client sponsor concerned about go-live date"]
}
```

## Field rules

| Field | Rule |
|-------|------|
| `op` | `new`, `update` or `cancel` (used for rows deleted in Excel). New items carry no ID; `tracker.py` assigns it (one number sequence per project across actions, RAID items, decisions and promises; milestones and workstreams count separately), and records it as `result_id`. A proposal never predicts an ID: anything an item refers to (`replaces`, a link, a milestone) must already exist, except a link's end written `@n` (below). `recode` (table `projects` only) is made by `propose.py recode`; see "Recode" below. |
| `based_on` | For updates, the row's `updated_at` when the change was made. If the database row has changed since, the item becomes a **conflict**, and review shows both versions. |
| `match` | `strong`, `medium`, `possible` (weak match from cx-sweep; shown in a separate section) or `unresolved`. Possible and unresolved items need a project before they can be applied. |
| `flags` | Any of: `no-owner`, `unknown-owner` (the owner isn't in the people register, BL-55; Review shows the likely matches), `no-due-date`, `low-confidence`, `naming`, `conflict`, `invalid` (fails a schema rule; shown with the reason), `vip` (BL-99: sourced from a message a VIP sent; set by `sweep.py stage`; sorts first in Review, labelled VIP). |
| `signals` | Optional, on items whose project wasn't certain (`medium`, `possible`, `unresolved`, or two candidate projects): the signals that pointed to a project, for learning (BL-28): `[{"kind": "sender", "value": "sara.khan@northgate.example"}]`. Kinds: `sender`, `domain`, `channel`, `alias`, `stakeholder` (`keyword` is recorded but never learnt). |
| `decision` | `pending`, `approved` or `rejected`. Set by Alan in Claude Code or in the Excel Review sheet. |
| `reject_reason` | Optional, on a rejected item (BL-133): why, in one line of at most 200 characters (Duplicate, Not mine to track, Not an action, Other or Alan's words). Written by Review's reason menu or `review.py reject <n> --reason=…`; stored in `rejected.reason` at apply. Cleared if the item goes back to pending. |
| `duplicate_of` | Optional, on a rejected item (BL-133): the existing action, RAID item or decision it repeats (`review.py reject <n> as a duplicate of ABC-A-009`). Stored in `rejected.duplicate_of`; the reason defaults to Duplicate. An ID that doesn't exist stops the apply. |

## New fields and tables (Sprint 5: BL-53, BL-50, BL-90 part 2, BL-94)

All are validated by `tracker.py` at apply (and by `validate`), written under the apply's `apply_id`, logged in `change_log` and undone with it. The full rules are in `.claude/skills/cx-minutes/references/tracker-conventions.md`.

**Decisions** take `status` (`Pending`, `Made`, `Withdrawn`; default `Made`), `needed_by`, `reasoning`, `options`, `revisit` and `replaces`. `date` is required only for a Made decision and must be empty for a Pending one. A decision needed:

```json
{"op": "new", "table": "decisions", "values": {"project": "ABC", "decision": "Extend the pilot by two weeks", "status": "Pending",
 "made_by": "Sara Example", "needed_by": "2026-10-16", "source": "…"}}
```

Making it, on the same row: `{"op": "update", "table": "decisions", "id": "ABC-D-004", "changes": {"status": "Made", "date": "2026-10-12"}}`; withdrawing it: `{"status": "Withdrawn"}`.

**Promises** (`table: "promises"`): `project`, `promised_by`, `promised_to`, `description`, `raised`, `source` required; `due_date` and `status` (`Open`, `Done`, `Dropped`) optional. `op: cancel` sets `Dropped`. **Proposed by cx-minutes and cx-sweep (BL-125 A)** like actions (cx-sweep only when settings `promises.from_sweep` is on; it ships off, Alan 13-10-2026): `raised` is the meeting date or the message's Sent day, a minutes promise cites the transcript copy (it isn't in the minutes), a promise with no `due_date` is flagged `no-due-date`, and one already open becomes a mention (or an update when it carries a new date). Their updates (`{"op": "update", "table": "promises", "id": "ABC-P-004", "changes": {"status": "Done"}, "why": "…"}`) may change `status` and `due_date`; one marking it Done or Dropped is a closing update, approved on its own. `tracker.py read promises --list owe|waiting` gives "You owe" (Alan's open promises) and "Waiting on" (the overdue ones made to him, with `overdue_days` and `quiet_days`).

**Links** (`table: "links"`): `{"op": "new", "table": "links", "values": {"from_item": "ABC-001", "to_item": "ABC-A-004", "source": "…"}}` (`kind` defaults to `blocks`); both IDs must exist (any project) and must not loop. Remove with `{"op": "cancel", "table": "links", "id": "ABC-001|ABC-A-004|blocks"}`. **BL-322:** either end may be `@n`, the ID `tracker.py` gives item `n` of the same proposal, a new action, RAID item, decision, milestone or promise written before it (Sneak peek's follow-on action and its link: one apply, one undo). After the apply the real ID is in `values` and the `@n` under `refs`; an `@n` that names anything else stops the apply. An undo puts `refs` back into `values` (the item returns as `@n`), so a re-apply links the item it creates then, never one that has since taken the undone ID.

**Labels** (`table: "labels"`): `name` (required), `colour`, `note`, `behaviour` (`warn` or `exclude`), `default_choice` (`include` or `exclude`); `builtin` can't be set. Delete with `op: cancel, id: "<name>"` (never Sensitive, never one in use). **On an item,** `labels` is a field of `values` (new) or `changes` (update: the full set), with `label_reason` and `label_suggested` (0 or 1); an unknown label is refused. Individual rows: `table: "item_labels"` (`item_id`, `label`, `reason`, `suggested`) and `op: cancel, id: "<item>|<label>"`.

**Excel:** the Decisions sheet carries the new decision fields; a **Promises** sheet is editable; **Labels** is a comma-separated column on Actions, RAID and Decisions (compared as a set; an unknown label makes the item `invalid`); **Links** is read-only at first, and the sheet says so.

## Minutes proposals (cx-minutes)

A cx-minutes proposal also carries a `meeting` block:

```json
"meeting": {
  "key": "calendar:AAMkAD… | fp:2026-10-01|abc steering|9f3c…",
  "title": "ABC Steering committee",
  "date": "2026-10-01",
  "projects": ["ABC", "DEF"],
  "draft": "system/staging/drafts/2026-10-01 ABC Steering committee.docx",
  "transcript": "inbox/Recording 2026-10-01.vtt",
  "minutes_decision": "pending",
  "file_ops": [
    {"op": "copy", "from": "draft", "to": "projects/ABC Example Programme/minutes/2026-10-01 ABC Steering committee.docx"},
    {"op": "copy", "from": "transcript", "to": "projects/ABC Example Programme/transcripts/2026-10-01 ABC Steering committee.vtt"},
    {"op": "copy", "from": "draft", "to": "projects/DEF …/minutes/2026-10-01 ABC Steering committee.docx"},
    {"op": "copy", "from": "transcript", "to": "projects/DEF …/transcripts/2026-10-01 ABC Steering committee.vtt"},
    {"op": "remove", "path": "inbox/Recording 2026-10-01.vtt"},
    {"op": "remove", "path": "system/staging/drafts/2026-10-01 ABC Steering committee.docx"}
  ]
}
```

- **`minutes_decision`** (pending, approved or rejected) is separate from the item decisions.
  - If the minutes are rejected, only the transcript copies run; the draft is discarded.
  - If both the minutes and the transcript are rejected, nothing moves.
- **On approval,** the draft's status line changes to "Approved by Alan on <date>" before copying.
- **`system/processed.txt`** records the meeting key once, with every project it was filed under. Copies are never re-extracted.
- **`inferred`** on an item (BL-208, written by cx-minutes and cx-sweep): `[{"field", "why"}]`, the fields extraction guessed and why (`review.clean_inferred` keeps well-formed ones). Review's One at a time puts these items first and underlines the fields. It is never applied to the tracker.
- **`coverage`** (BL-209, only when the meeting had an agenda or a prep page): `[{"point", "verdict"}]`, each point in the agenda's own words (never transcript text), the verdict `Covered`, `Touched on` or `Not discussed`; with `agenda`, the file the points came from. Stage refuses a point that isn't on the agenda. Points Alan carries to the series' next meeting are kept in `system/staging/carried.json` (`{"points": [{series, point, key, day, title, projects, carried}]}`), which the next prep page lists as "Not covered last time".
- **Moved in Review (BL-200):** `review.py assign <n> <CODE>` on the minutes entry (or the dashboard's Project button) moves one project's items and filing to another. Each moved `new` item gets the new `values.project`, `match: "strong"`, `moved_from` (the project it came from), `edited_in: "review"`, its `source` path rebased to the new project's folder, and its old project's `milestone` and `workstream` cleared (kept in `moved_cleared`, keyed by that project, and put back if the item moves back there, as Review's Undo does, BL-281); an approved, unapplied item goes back to `pending`. `update` items stay (they name one tracker row). The `meeting` block gets `projects` with the old code replaced (or removed, when the new project is already listed), every `copy` op into the old project's minutes or transcripts folder pointed at the new project's (`paths.folder`; dropped when the new project already has its own), a copy of a transcript that sat in the old project's own folder added for the new one (Alan's file is never moved or removed), `source_map` rebased, and a `moved` list (`{"from", "to", "at", "items"}`). The processed line follows the copies at apply. One item moved on its own (`assign <n> <CODE>` on the item) gets the same item fields but keeps its `source`.

### Someone else's minutes (#232 E1, Find work items)

A file added in Intake that is another person's minutes is staged by `minutes.py stage` from a spec with `"as": "minutes"` and `"file": "inbox/<file>"` (never with `draft`, `minutes`, `transcript` or `note`: stage refuses, so BL-260 holds for every transcript). No Word draft and no minutes record are made. The `meeting` block differs from a minutes proposal:

```json
"meeting": {
  "key": "fp:2026-10-12|vendor call|9f3c1a2b4d5e",
  "title": "Vendor call", "date": "2026-10-12", "projects": ["ABC"],
  "draft": null, "transcript": null,
  "kind": "minutes by others", "source_file": "inbox/Vendor call minutes.txt",
  "note": "projects/ABC Example Programme/minutes/2026-10-12 Vendor call.txt",
  "minutes_decision": "approved",
  "file_ops": [
    {"op": "copy", "from": "inbox/Vendor call minutes.txt", "to": "projects/ABC Example Programme/minutes/2026-10-12 Vendor call.txt"},
    {"op": "remove", "path": "inbox/Vendor call minutes.txt"}
  ]
}
```

- **Approved like a quick note:** `minutes_decision` is `approved` from the start (there is no minutes record to approve; the items are decided as usual) and `note` is set (the first project's filed copy), which is how `tracker.py` knows there is no draft to file (BL-260 point 4). The apply runs the `file_ops` and records the key in `processed.txt` with the filed path.
- **When the file moves, today:** staging itself moves and writes nothing, but because `minutes_decision` is `approved` from the start, `tracker.py apply` files the copy, removes the inbox copy and writes the `processed.txt` line (0 items) the next time it reaches the proposal, whatever the items' decisions: also from a full apply for an unrelated proposal, and also when every item is rejected. **Proposed (`dev/proposals/intake-232/E1-tracker.diff`, a guarded change for Jarvis):** a block of `kind: "minutes by others"` is filed only by an apply that writes at least one of its approved items (with every item rejected, or every approved item held, nothing is filed; a rejected-only proposal finishes); its `copy` and `remove` are refused unless the source is a regular file (never a link or a hard link) in `inbox/` or the matched project's minutes folder whose SHA-256 is the op's `src_sha256`; `check_file_op` also refuses a copy onto a different existing file at validation; and a full apply leaves a proposal whose file can't be filed in staging with a line saying why, instead of failing for the whole queue. Tests: `dev/tests/test_minutes_by_others_filing.py`.
- **`file`:** a plain relative path (no `..`, backslash, NUL or leading `/`), in `inbox/` or already in a matched project's minutes folder once symlinks are followed (neither folder, nor one between it and the vault or projects root, may itself be a link); `.vtt`, `.srt` and a calendar event ID in the header are refused as transcripts. Only relative paths are stored.
- **Key:** `fp:<day>|<normalised title>|<first 12 hex of the file's SHA-256>` (`minutes_key`, `minutes.py key --minutes <file>`): never an event ID. The same file again is "Already processed" (exit 3); `process new minutes` does not offer the filed copy again (it matches on day and title).
- **Filing:** one `copy` per matched project to `<minutes folder>/YYYY-MM-DD <Title><ext>` (`<ext>` lower case, one of `.txt`, `.md`, `.docx`, `.pdf`; numbered `(2)` when a different file has the name on disk or as another staged proposal's destination), then one `remove` of the inbox copy (only for a file in `inbox/`). Both ops carry `"src_sha256"`, the SHA-256 of the file when it was staged. The same file can't be staged twice ("Already staged in …"). A file already in a matched project's minutes folder is Alan's own: no operation. Review's `assign` moves the copy to another project like any minutes copy (the `note` is not rebased).
- **Items:** actions, decisions and RAID items and updates to open ones; a promise is skipped with a note. Each item's `source` is the filed copy plus its section.

### The minutes record (v2.1.0 P4, BL-338)

When the meeting spec carries `"minutes"` (an object; never with `"draft"`), `minutes.py stage` drafts the minutes itself as a creaite document (`creaite_doc.py`, kind `minutes`; `system/scripts/minutes_record.py` builds it) instead of a Word draft. The proposal is a minutes proposal as above, with these differences:

- **`meeting.draft`** is `system/staging/drafts/<stem>.html` (never over another file). It is saved as version 1 through `filechange.py` before the proposal is written, and saved again when the staging checks (BL-221, BL-218) change an item's mark.
- **Filing:** each project's `copy` from `draft` goes to `creaite_doc.target("minutes", <code>, <date>, <title>)`: `<the project's minutes folder>/YYYY-MM-DD <Meeting title>.html`, the title without `[CODE]` tags or reserved characters, at most 80 characters. Each item's `source` is that copy plus its section (`… .html — Actions`; notes written before 2.6.0 say `— Action Items`, and both are read, #296).
- **Spec fields** (cx-minutes): `minutes` is `{"start", "end"` (`HH:MM`, UAE time)`, "attendees", "summary": [<paragraph>], "updates": [{"heading", "items": [<line>]}], "open_questions": [<line>], "chat"` (default `true`)`, "partial"` (default `false`)`, "milestones": [{"id", "note", "turn" | "at"}]}`; a `<line>` or paragraph is text or `{"text", "flag", "turn" | "at"}` (`flag` one of minutes-style's ten, else dropped). A spec item may carry `"turn"` (a speaker turn, from 1) or `"at"` (a `.vtt` cue time, `HH:MM:SS`) for its row's time tag. None of these reach the proposal's items.
- **`due_words`** on a new action or promise (on the item, or in its `values`): the deadline as said ("Friday", "next week", "next Wednesday", "end of month", "in 2 weeks", "30-10"). Stage removes it and sets `values.due_date` from the meeting's date (`date_words.deadline`; one parser, `core/datewords.js`, shared word for word with the dashboard) unless a `due_date` was given, adding `inferred: [{"field": "due_date", "why": "said “Friday”, from the meeting's date"}]` (BL-208). Words it can't read leave no date and print a note. On an `update` it is dropped.
- **Re-extract** (`minutes.py refresh`) is refused for a minutes record: its rows are the staged items. **Review** approves it as it approves Word minutes (`minutes_decision`), with nothing to compare or clean.

**The record** (the creaite-data block; the shape is `dev/sprints/v210-contract.md` §1):

- **Sections**, in order: `header` (type `header`: the status line, when, the attendees; `data.status`, `data.when`, `data.attendees`), `summary`, `updates` (`data.topics`), `decisions`, `raid` and `actions` (tables), `open_questions`, `not_covered` (only once a coverage line is added) and `source` (the source line: "Teams transcript and meeting chat, <title>, <long date>, HH:MM–HH:MM (UAE time)"). Text sections carry their time tags in `tags`: `{"ref": "transcript", "turn", "time", "text"}`.
- **Rows** of `decisions`, `raid` and `actions` are the proposal's own items: `{"ref": "@<n>", "n", "cells", "shown": true, "does", "at": {"turn", "time"}}`, where `n` is the item's number in the proposal and `does` says what it does ("New action", "Decision needed", "Closes ABC-A-002", "Records ABC-D-003 as made", "Updates ABC-A-001", "New risk · Looks like ABC-R-006"). Columns: decisions `decision`, `by`; RAID `type`, `description`, `owner`; actions `owner`, `action`, `due` (DD-MM-YYYY or "Not set"). Promises and milestones have no row. **`items`** holds each staged item as it stands, keyed by its `@<n>` (`table`, `op`, `n`, `id`, `values`, `changes`, `flags`, `looks_like`, `decision`).
- **This `@n` is the record's own**, not a link's `@n` (above): `tracker.py`'s link resolution never reads it. When the minutes are approved, `tracker.py apply` marks the record approved (`state`, `approved_at`, the status line "Approved by <name> on <long date>") and turns each `@<n>` of an item that apply wrote (its `result_id`) into that ID, in the rows and in `items`, before copying it; `meta.transcript` then names the filed transcript.
- **`meta`**: `proposal` (the proposal's file name), `key`, `projects`, `transcript`, `timed`, `turns`, `start`, `end`, `source_line`, `status_line`, `coverage` (the meeting's, each point later with `action: {"how": "carry" | "session" | "drop" | "enough", "line", "item"}`), `agenda`, `milestones` (notes only, never a change: BL-186) and `removed` (rows taken out, kept for Undo while a draft; emptied at approval).

**Changes from the minutes view** (`minutes_record.change`, `/api/minutes/save` with `op`) write the record (a new version) and the proposal (validated) together, while the record is a draft:
- `remove` rejects the item (`decision: "rejected"`, `reject_reason: "Removed in the minutes"`, `decided_in: "minutes"`) and drops its row, or with `keep_line` leaves `{"ref": null, "cells", "shown": true, "kept_line": true, "was": "@<n>"}`; `restore` puts it back. `update` (Update that one, BL-221) is `review.py retarget`'s change with `decided_in: "minutes"`; `keep_new` drops a Looks like mark or undoes a merge. `edit` and `deadline` change a new item's own fields (`edited_in: "minutes"`; a deadline may be words). `cover` with `how: "session"` adds an action for Alan, due Friday from the meeting's date (`added_in: "minutes"`); `carry` writes `carried.json` as `/api/meeting/carry` does; `uncover` undoes either.
- **Approve minutes** (`review.approve_minutes`, `/api/minutes/approve {file, group, own}`) sets `minutes_decision: "approved"` and `decided_in: "minutes"` on the meeting and on each ticked item, then runs `tracker.py apply` on this proposal alone: one apply, one undo. Actions and updates are one group (`group`); whatever `review.individual_only` names (a new decision, a decision recorded or withdrawn, a new risk, a closing update and the rest of the bulk rule) needs its number in `own`; a milestone change and an item that needs a project or is invalid are never approved here. Unticked items stay `pending` in Review; removed items are recorded as rejections in the same apply. If the apply fails every decision is put back.
- **Filed minutes are never saved over.** A save to a record in a project folder is sensitive (BL-141) and no approval is issued for it: `creaite_doc.save` answers code 3 (`needs_approval`); the filed minutes and `files-log.jsonl` are untouched, and the version that wasn't saved is left in `system/staging/drafts/` (Alan, 15-10-2026: it stays refused; no card is offered for it). <!-- moving: exports (/api/minutes/export) wait for creaite_doc.export (P2); the distributed version (audience "distributed", based_on) for P7. -->

### Updates from a meeting (BL-65)

A cx-minutes proposal may also hold `update` items for the open items of the meeting's project that the meeting discussed (never re-proposed as new items). `minutes.py stage` builds them from the meeting spec:

```json
{"op": "update", "table": "actions", "id": "ABC-A-003", "set": {"status": "Closed"}, "why": "Omar said it was sent",
 "section": "Actions"}
```

becomes, in the proposal:

```json
{"n": 4, "op": "update", "table": "actions", "id": "ABC-A-003", "changes": {"status": "Closed"},
 "based_on": "2026-10-05 09:14:03.512", "why": "Omar said it was sent",
 "source": "projects/ABC …/transcripts/2026-10-07 ABC Steering.vtt — Actions", "match": "strong", "flags": [], "decision": "pending"}
```

- **Fields:** actions may change `status`, `due_date` and `latest_update`; RAID items `status`, `response_action` and `due_date`. Never the owner, title or project (cx-edit and Review do those); an update naming any other field is refused whole.
- **`based_on`** is filled by `stage` from the row's `updated_at`, so an apply holds a **conflict** if the item changed after the proposal was made.
- **Refused, naming the item:** an item that is closed (only open items: actions Open or Delayed, RAID Open), in another project than the meeting's, or not in the tracker. The refusal is a `Note:` line; nothing is staged for it.
- **Dedupe:** a new item that matches an open item of the same project becomes an update to it when it carries a changed due date, response or latest update, and is otherwise only a mention. It never becomes a second item. Two updates to one item in a meeting are merged.
- **Mentions:** each item a meeting discussed, and each duplicate, is logged in `system/staging/mentions.jsonl` (BL-51's "raised repeatedly" signal).
- **`why`** (one line) and **`source`** show in Review. A change to status Closed or Cancelled is approved individually, never by "Approve routine".

## Apply

`tracker.py apply` runs these steps, under a new `apply_id`:

1. Back up `tracker.db` to `system/backups/`.
2. Write the approved items in a single transaction: all or nothing.
3. Log every field change to `change_log`, and add rejected items to `rejected`.
4. Run approved file operations, then record meeting keys in `system/processed.txt`.
5. Move the file to `system/staging/applied/`.
6. Rebuild `dashboard.html` and save a snapshot to `system/history/`, then re-export `tracker-view.xlsx` (unless there are unimported edits; see below).

A file that still has pending items stays in `system/staging/`. Pending items older than 7 days are flagged as stale at review.

## File operations

Proposals can carry `file_ops`, which run on apply in order and are reversed by undo:

| op | Fields | Used by |
|----|--------|---------|
| `copy` | `from`, `to` | cx-minutes (filing minutes and transcripts) |
| `remove` | `path` | cx-minutes (clearing `inbox/` and drafts). The removed file is kept in `system/backups/files/` so undo can restore it |
| `mkdir` | `path` | cx-edit (new project folders) |
| `write` | `path`, `content`, `previous` (null for a new file) | cx-edit (memory, register, new project `CLAUDE.md`), cx-weekly-report (current state) |

`write` stores the previous content, so undo restores the file exactly.

## Dashboard proposals

The dashboard (option B, browser folder access) writes:
- **Edits and new items** (inline, form, project details, "Current state"): one file per save burst, `proposed-YYYY-MM-DD-HHMM-dashboard.json`, with `source_run: "dashboard"` and `decision: "approved"`. "Current state" is a `write` file operation on the project's `CLAUDE.md`.
- **Decisions on existing proposals:** the `decision` (or `minutes_decision` and `report_decision`) field in the original proposal file, plus `"decided_in": "dashboard"`.
- **Settings:** not proposals. Written straight to `system/config/settings.json`. The previous version is copied to `system/backups/settings-YYYY-MM-DD-HHMMSS.json`, and one line is appended to `system/config/settings-log.jsonl` (time, key, old, new).

The dashboard validates before writing (YYYY-MM-DD dates, required fields, allowed values). `tracker.py` validates again at apply.

## Undo (`tracker.py undo`)

Each apply gets an `apply_id`, stored in the `applies` table with its proposal files and file operations, and on every `change_log` row. `undo` reverses the most recent apply that hasn't been undone:
- inserted rows are deleted and changed fields restored;
- file operations are reversed;
- the proposal moves back from `applied/`, with the undone items set to pending; a change Alan approved on ask creaite's card (`applied_on_card`, set only by the live server, BL-289) was never in Review, so it stays in `applied/` marked `undone`.

Any item changed by a later apply or edit is skipped and reported. The undo is itself logged (`op: undo`).

## Bulk approval rule

"approve all", "approve all strong" and "approve <CODE>" set `decision: approved` only on routine items with a project and no conflict. They never cover meeting minutes (`minutes_decision`), weekly or client reports (`report_decision`), health changes (`table: projects` with `health`), new decisions (`op: new`, `table: decisions`) or new risks (`op: new`, `table: raid`, `type: Risk`).

AI drafts (sprint-drafts-fields): an item carrying `drafted` (a drafted latest update or client wording) and any `update` that changes `client_message` is approved on its own, never by "approve all" or the dashboard's Approve routine (`review.individual_only`: "drafted update", "client wording").

Edited drafts: at individual approval, cx-review checks the draft against the staged values, re-scans client reports, and accepts tracked changes and removes comments before filing (see the cx-review skill).

Report proposals (cx-weekly-report, cx-client-report) carry a `report` block with `draft`, `report_decision` and `file_ops`, like the `meeting` block.

## Excel round-trip (`system/scripts/excel_sync.py`)

**Export** writes `tracker-view.xlsx`:
- one sheet per table, with drop-downs from the allowed values;
- locked `id`, `source` and `updated_at` columns;
- a Review sheet listing every pending item, with a Decision column (Approve, Reject, Edit).

It records the export time and a hash of the file in `system/staging/export-state.json`.

**Import** runs when Alan says "import excel", or at 08:30 if the file's hash has changed. It compares each sheet with the database and stages only the differences, with `source_run: excel-import`:
- a new row (blank id) becomes `op: new`;
- an edited cell becomes `op: update`, with `based_on` set to the exported `updated_at`;
- a deleted row becomes `op: cancel`, flagged for confirmation;
- Review sheet decisions update the matching pending items in their own proposal files.

**Safety:** the export refuses to overwrite a workbook whose hash differs from the last export, so unimported edits are never lost. It tells Alan to import first.

## Plain-English edits (cx-edit)

"Mark ABC-A-003 done", "move ABC go-live to 2026-11-20" or "add project DEF…" become a proposal with `source_run: cx-edit`. Alan confirms it before it's staged, so it arrives with `decision: approved` and is written at the next apply.


## Field notes (v0.17)

- Actions: `workstream`, `priority` (Urgent/High/Medium/Low), `latest_update`, `client_visible`, `client_message`; status Open/Delayed/Closed/Cancelled. No `mine`.
- RAID: `workstream`, `response_action`, `due_date`, `closed`, `client_visible`, `client_message`; status Open/Closed/Cancelled.
- `client_message` always holds the three headings; it must be complete before `client_visible` can be 1 (tracker.py rejects otherwise). Claude never fills the text.
- Proposals edited in the dashboard carry `"edited_in": "dashboard"`. With auto-apply, dashboard saves are applied immediately (`via: "dashboard"` in change_log).
- **`as_proposed` (BL-232):** the first time a pending item's `values` (a `new` item) or `changes` (an `update`) are edited, the item gets `"as_proposed"`: a copy of them as they were before that edit. It is **write-once**: later edits never change it, and once an Undo has taken it away it isn't given again. It is set in one place per side: `tracker.stamp_as_proposed` (compares the file on disk before each write, with Raised filled on both sides, so a filled Raised or a decision alone isn't an edit; reached by `review.py`'s `save`, so `edit`, `assign` and approve's `--sync`, and by `minutes.py refresh`) and the page's `editProposal` (the panel, the peek, Review's rows, the weekend-date buttons, the workstream suggestion and BL-200's project change). The page's Undo of a Review row edit restores it with the values. `tracker.py apply` never reads it and it stays on the applied proposal (for BL-233). An item added by a refresh has none (nothing was proposed before it). An item with `edited_in` and no `as_proposed` was edited before BL-232: "edited, before-value unknown", never guessed.


## Source format (v0.20)

See "Source references (format)" in the tracker conventions: file path plus section; or `Email · From: … · Subject: … · Sent: YYYY-MM-DD HH:MM · Link: …`; or `Teams · Channel|Chat: … · From: … · Sent: … · Link: …`.


## Dates (v0.23)

All dates in proposals, sources and settings are stored YYYY-MM-DD (times HH:MM). The dashboard and documents display DD-MM-YYYY. Decisions gain `client_message` (plain text).


## tracker.py behaviour (Step 1)

- **`apply` with no file** applies every `proposed-*.json` in `system/staging/` that has decided items, under one `apply_id`. A dry run comes first: if any approved item is invalid, nothing is written and the item is flagged `invalid` with `invalid_reason`.
- **Applied items** gain `"applied": <apply_id>` (and `"result_id"` for new rows). A file moves to `applied/` only when every item and block is applied; otherwise it is saved back in `staging/`.
- **Conflicts** (`based_on` differs from the row's `updated_at`) are held: flag `conflict`, `conflict_reason`, `decision` back to `pending`, and `current` holds the database row so review can show both versions.
- **Possible / unresolved matches** are held until Alan assigns a project; cx-review then sets `match` to `strong`.
- **RAID `priority`** is always recalculated from impact and likelihood; a supplied value is ignored. Closing or cancelling fills `closed` with today unless given; reopening clears it.
- **`cancel`** sets actions and RAID to Cancelled and projects to `active = 0`; decisions and updates can't be cancelled.
- **`recode`** (BL-111) changes a project's code everywhere: `{"op": "recode", "table": "projects", "id": "<OLD>", "changes": {"code": "<NEW>", "name": "<optional new name>"}, "folder": {"from": "<old engagement folder>", "to": "<new one>"}}` (`folder` only when the folder was renamed). It is written inside the apply's transaction by `tracker.recode_project`: the project, every item ID (numbers kept), the milestone links, the `source` paths (with `folder`), the history in `change_log`, the rejected fingerprints and the search index. It logs `recode` rows (`code`, and `name`, `folder`, `rejected_map` when they apply), which `undo` reverses exactly. It is applied **on its own** (other proposals wait for the next apply; other items in its proposal stop the apply), and refused while another pending proposal mentions the old code, if the new code exists or is in the register (retired codes too), or if the schema has a table the recode doesn't know. The proposal's `file_changes` carry the register, the project's `CLAUDE.md` heading, `mentions.jsonl` and the search sidecars (`system/search/` is writable for this).
- **Key for `projects`** updates is `id: "<CODE>"`; for `updates` it is `id: "<week_ending>|<CODE>"`.
- **Rejected minutes:** transcript copies and the inbox transcript removal still run, and the draft is removed. An optional `"transcript_decision": "rejected"` in the meeting block stops all file operations.
- **File operations** may only touch `projects/`, `inbox/` and `system/staging/`. `copy` never overwrites; `write` checks the file still equals `previous`. Removed and status-changed files are kept in `system/backups/files/<apply_id>/` for undo.
- **`system/processed.txt`** gets one line per filed meeting: `YYYY-MM-DD | <meeting key> | <filed paths; …> | <items written>`. Undo removes it.
- **Undo** skips any item whose current value differs from what the apply wrote (changed since, by any route) and leaves that item applied in its proposal.


## excel_sync.py behaviour (Step 2)

- **Sheets:** Review first, then Projects, Actions, RAID, Decisions, Updates. Headers are plain labels (ID, Owner, Due…); import maps them back by label, so columns can be reordered.
- **Locked columns** (ID, source, updated time; RAID priority; project code; existing Updates keys) are grey and refuse typing through data validation. Sheet protection isn't used, because Excel won't delete a row containing protected cells. Import ignores changes to locked columns and rows with IDs it didn't export.
- **Dates** are real Excel dates formatted `dd-mm-yyyy`; text typed as DD-MM-YYYY is accepted too. Client-visible and Active show as Yes/No.
- **Import compares the workbook with the export snapshot** in `system/staging/export-state.json` (not with the live database), so changes made elsewhere since the export are never proposed for reversal; they surface as conflicts through `based_on`.
- **Imported items are `pending`** and reviewed like any proposal. Deleted action and RAID rows become `cancel` with the `low-confidence` flag and `"confirm": "row deleted in Excel"`. Deleted decisions and updates, and new project rows, are ignored with a message.
- **New rows:** `raised` defaults to today (Excel and dashboard items only; proposed items use the source's date, see `tracker-conventions.md`); `source` is `Recorded by Alan in Excel, YYYY-MM-DD`.
- **Review sheet:** Approve and Reject set `decision` (and `minutes_decision` / `report_decision` for draft rows) with `"decided_in": "excel"`; Edit leaves the item pending with `review_note`.
- **Safety:** export refuses (exit 3) while the workbook is open (`~$` lock file) or has unimported edits; `tracker.py apply` passes that message on. `changed` exits 1 when there are unimported edits.
- **Timestamps:** `updated_at` and change-log times are stored to the millisecond (`YYYY-MM-DD HH:MM:SS.fff`), so `based_on` catches changes made within the same second.
- **Schema changes (Step 2b):** `tracker.py migrate` rebuilds any table whose definition differs from `schema.sql`, copying every row in one transaction after a backup (`tracker-…-migrate.db`), then adds any new tables. `init` on an existing database and `doctor.py` both report when a migration is due.
- **Undo order:** items are reversed newest first, so rows are removed before the project they belong to.


## Step 3 additions

- **`meeting.source_map`** (written by `minutes.py stage`): minutes copy → transcript copy for each project. If the minutes are rejected, `tracker.py apply` rewrites item sources to cite the transcript copy instead.
- **`system/processed.txt`** columns are separated by `" | "` (with spaces); meeting keys contain `|` without spaces.
- **Review numbers** from `review.py list` are saved in `system/staging/review-index.json` (file and item for each number), so "approve 1–6" acts on exactly what Alan saw.
- **Draft approval** (`review.py approve <n>`): minutes are compared with the staged items first; `--sync` copies the draft's owners and due dates into the staged items, `--as-staged` keeps them. The draft is then cleaned with `docx_tools.py clean` (tracked changes accepted, comments removed) before `minutes_decision` is set.
- **Conflicts:** `review.py override <n>` refreshes `based_on` to the row's current `updated_at`, clears the flag and approves; `keep <n>` rejects the edit.
- **Minutes format (2026-10-05):** Alan's layout (`system/templates/minutes-template.docx`, built by `dev/tools/build_minutes_template.py`; writing rules in `.claude/skills/cx-minutes/references/minutes-style.md`). Sections: Executive Summary, Updates (topics with coloured labels), Decisions, Risks & Issues, Action Items (Owner | Task | Deadline, DD-MM-YYYY or "Not set"), Open Questions / Escalations. Item sources cite `— Actions` (`— Action Items` before 2.6.0, #296), `— Decisions` or `— Risks & Issues`.
- **Sensitivity labels:** creaite never applies them and approval never checks for one (BL-121); `docx_tools.py clean` keeps a label a draft carries.

## Milestones (Step 4, BL-11)

- `table: "milestones"`, IDs `<CODE>-M-NNN` assigned on apply; required: `project`, `name`, `source`; `status` Planned / Done / Cancelled (Missed is retired, BL-186); dates `baseline_date` (the Agreed date), `forecast_date`; optional `description` (free text, may run over several lines; blank is stored as null).
- **BL-186 fields** (all optional; a blank is stored as null): `state` (Achieved, On track, At risk, Slipped or Overdue; empty: creaite follows the dates) with `state_set` (0/1, set to 1 by itself when a `state` is given) and `state_reason` (required when the state is better than the dates suggest); `owner` (a full name from the people register); `actual_date` (the achieved date, only with status Done; filled with today when Done is set without one; never after today); `client_visible` (0/1) and `client_message` (plain wording, required when visible); `internal_note` (Alan's own words for Movement; internal only, never in client output).
- **A rebaseline** (a change to an existing `baseline_date`) carries a `rebaseline` block on the item, beside `changes`: `{"agreed_with": ["Sara Khan", "Rashid Al Suwaidi"] (or one string), "reason": "…", "source": "…", "date": "YYYY-MM-DD" (optional; today)}`. Without it the item is invalid. The apply writes the new date and a Made decision ("<name>: agreed date moves from … to …", made by the people who agreed it, with the reason and source) in the same apply, records the decision's ID in the block (`"decision": "ABC-D-012"`) and a `note` in the milestone's history. The dashboard's Rebaseline stages it as one proposal, so Review shows it once.
- Actions and RAID items carry an optional `milestone` (an existing milestone ID); validation rejects a link to a milestone that doesn't exist.
- Excel: a Milestones sheet (BL-186 adds Owner, State, State set by you, State reason, Achieved on, Client-visible and Client wording; a Baseline change on an existing row is ignored on import with a note, as a rebaseline records a decision), and a Milestone column on Actions and RAID (drop-down of milestone IDs while the list fits Excel's limit).

## Dashboard proposals (Step 4b)

- **Edits, new items, health:** one file per save, `proposed-YYYY-MM-DD-HHMMSS-dashboard.json` (`-2`, `-3`… if several in the same second), `source_run: "dashboard"`, every item `decision: "approved"`. Updates carry `based_on` = the row's exact `updated_at`, so a change made elsewhere since the page was built becomes a conflict.
- **File changes** (memory, register, current state): a `file_changes` block, like `meeting`/`report`: `{"title", "project", "file_changes_decision", "file_ops": [{"op": "write", "path", "content", "previous"}]}`. The dashboard writes it already approved; cx-edit can stage it pending. `tracker.py apply` runs the operations and undo restores the file.
- **Decisions on existing proposals:** `decision` (or the block's `minutes_decision` / `report_decision` / `file_changes_decision`) set in the original file, with `"decided_in": "dashboard"`; edited values add `"edited_in": "dashboard"`.
- **Not from the dashboard until the live server exists (Step 4c):** approving draft minutes or reports (cx-review checks the label, compares the draft with the items, accepts tracked changes and removes comments) and resolving conflicts (keep or override). The dashboard says so.
- **Undo** in the dashboard's message deletes the proposal file while it is still in `system/staging/`; once applied, use "undo last apply".
- **Settings** go straight to `system/config/settings.json` (backup `system/backups/settings-YYYY-MM-DD-HHMMSS.json`, one line per key in `settings-log.jsonl`). A project's client-report rhythm is written to its `CLAUDE.md` (backup in `system/backups/files/`, logged as `client_report_rhythm.<CODE>`). Forever-dismissed reminders and the People and Workstreams lists are settings; renames and merges are proposals updating every item.

## Step 5: minutes RAID section and re-extract

- The minutes' RAID section is **Risks, Issues, Assumptions & Dependencies**; each line starts with its type (`Risk: …`). RAID item sources cite that section name.
- **Re-extract** (`minutes.py refresh <proposal>`, or the live dashboard's Refresh items): unapplied new items in a meeting proposal are matched to the draft by wording. Matched items take the draft's wording, owner (keeping a staged "(Company)" suffix when the name matches), due date and RAID type, and keep their decision; staged items no longer in the draft are removed; new draft lines become pending items with `"edited_in": "refresh"`. A RAID line without a type becomes a Risk with `low-confidence`.

## Step 5: sweep and session start

- `sweep.py` keeps the timestamp in `system/staging/last-sweep.txt` (`YYYY-MM-DD HH:MM`, the run's start; normal sweeps only), the lock in `sweep.lock` (its start time; stale after 30 minutes) and one line per run in `run-log.txt` (`YYYY-MM-DD HH:MM | sweep ok (normal) | summary` or `| sweep FAILED | message`). Sweep proposals are `proposed-YYYY-MM-DD-HHMM-sweep.json` and carry the searched `window`.
- `session.py start` makes the daily backup `system/backups/tracker-YYYY-MM-DD.db` (once a day), reports whether the sweep is due, the reminders (as on the dashboard, minus those dismissed forever) and the status line; sweep failures since the last success come from the run log.

## Step 5: reports

- **Weekly** (`report.py weekly-stage`): `proposed-YYYY-MM-DD-HHMM-weekly-<CODE>.json`, `source_run: "cx-weekly-report"`: items `updates` (new, or update `id: "<week_ending>|<CODE>"`) and, if health or its reason changed, a `projects` update; a `report` block `{"kind": "weekly", "project", "week_ending", "draft", "report_decision", "health", "health_reason", "summary", "current_state", "file_ops": [write CLAUDE.md current state, copy draft → reports/<Friday> Weekly report.docx, remove draft]}`. Approval compares the draft with `health`/`health_reason`/`summary`/`current_state`; `--sync` copies the draft's values into the block, the items and the memory write.
- **Client** (`report.py client-stage`): `proposed-…-client-<CODE>.json`, `source_run: "cx-client-report"`, no items; a `report` block `{"kind": "client", …, "file_ops": [copy → reports/<date> Client report.docx, remove draft]}`. Approval scans the draft for internal content; `--as-staged` files it anyway.
- Templates are built by `dev/tools/build_templates.py` from Alan's sample (house style); `docx_tools.py fill` embeds images (`{"image": path, "caption"}`) and supports `ON TRACK` / `AT RISK` / `OFF TRACK` labels.

## AI drafts (BL-219, BL-225; sprint-drafts-fields)

Draft updates (BL-219) and Draft all for client wording (BL-225) stage `proposed-YYYY-MM-DD-HHMMSS-drafts.json` (`-2`, `-3`… in the same second), written by `drafts.py` (`proposal_file`) when the live server's draft run ends, `source_run: "drafts"`, every item `decision: "pending"`:

```json
{"n": 1, "op": "update", "table": "actions", "id": "ABC-A-003", "changes": {"latest_update": "Sara booked the environment for 14-10-2026."},
 "based_on": "2026-10-05 09:14:03.512", "why": "Drafted from 09-10-2026, Weekly sync: “…”", "source": "AI draft (BL-219), 11-10-2026",
 "drafted": "update", "drafted_text": "Sara booked the environment for 14-10-2026.", "draft_sources": ["09-10-2026, Weekly sync: “…”"],
 "match": "strong", "flags": [], "decision": "pending"}
```

- **`drafted`** is the feature (`update`, `client`); **`drafted_text`** the text as drafted, so a decision can be counted as used (approved as drafted), edited (approved after an edit) or rejected in `system/staging/draft-stats.json` (counts only); **`draft_sources`** the source lines it rests on, shown in Review. tracker.py ignores all three.
- **Fields:** a drafted update changes `latest_update` only (actions); drafted client wording changes `client_message` only (actions, RAID items, decisions). `based_on` holds a conflict if the item changed after the draft. A sentence with no source puts `low-confidence` in `flags`; for client wording, a note from the wording check does.
- Never in place: a draft is a proposal like any other until Alan approves it; the single-item drafts in the peek are not proposals at all until the field is left (then they are the peek's usual staged edit).

## Writing drafts (BL-223, BL-224; sprint-drafts-writing)

None of these is a proposal and none reaches the tracker.

- **`system/staging/chases.json`** (BL-224, written only by **I sent it** in a chase, through `drafts.py chase record`): `{"chases": [{"ids": ["ABC-A-003", "ABC-A-007"], "date": "2026-10-03", "mode": "chase"}]}`. Item IDs (checked against the ID pattern), the day and the mode only: never the email's text, subject or address. `drafts.py chases` gives `{id: {"n", "last"}}` for the next chase's tone and the person page.
- **`system/staging/agendas.json`** (BL-223): the agendas the server saved with **Save to Agendas**, `{"projects/…/agendas/2026-10-12 Agenda - ABC weekly.md": {"key", "day", "for_attendees", "at"}}`. The file is Markdown; its "- " lines are the agenda's points, which `minutes.py agenda` reads for Coverage.

## Extraction suggestions (BL-221, BL-218, BL-220; sprint-drafts-extraction)

`minutes.py stage` and `sweep.py stage` finish with `extraction.after_stage` (`system/scripts/extraction.py`), which marks the proposal and then validates it as before. tracker.py ignores every field below; each is counted for BL-233 in `draft-stats.json` (counts only).

- **`looks_like`** on a `new` item (BL-221): `{"id": "ABC-A-009", "t": "<its text>", "state": "open" | "closed", "same": true, "project": "ABC", "strength": "Very likely" | "Possible", "why": "…"}`, the existing item it most closely repeats (title words, with the same owner and workstream counting a little; the project's open items, then those closed in the last 60 days, then another project's open items with the same owner). Never a percentage. On the spec item, `"repeat": {"id", "judged": "same" | "different"}` is the skill's judgement of a close pair ("different" drops the mark, "same" makes it Very likely). `review.py keep-new <n>` adds `"kept": true`. `review.py merge <n>` replaces the item with an `update` to that ID (same project and open only) carrying `due_date`, `latest_update` or `response_action` where they differ (a pending decision made: `status`, `date`; `reasoning`, `options`), `based_on` its `updated_at`, `merged_from: {"values": …}` and `looks_like.merged`; with nothing new the item is rejected instead (`reject_reason: "Duplicate"`, `duplicate_of`).
- **Smarter updates** (BL-297; sprint-smart-updates). A sweep spec may hold `{"op": "update", "table": "actions" | "raid", "id", "set": {…}, "why", "source"}` for a message that moves an open item forward: an action may change `latest_update` and `due_date`, a RAID item `due_date` and `response_action` (never `status`, owner, title or project); `sweep.py stage` checks it as a meeting's update (open, a tracker project) and stages an ordinary `update` item. `looks_like.why` now names the signals ("Same thread · Dana · Same owner · due this week", or "Names ABC-A-007"), and candidates raised after the message's Sent day (a meeting's day) are never marked. `repeat: {"judged": "same"}` makes a Very likely mark on its own (`why` "Judged the same at extraction") when the ID is an open, or recently closed, item of the item's project and table; otherwise `stage` prints a note and ignores it. A merged item (and a retargeted one) carries **`was`**: the new item as it was, which `review.py unmerge <n>` (or `<file>#<n>`) puts back. `review.py retarget <n> <ID>` gives the same result as merge onto an ID Alan picks, plus **`retargeted`**: `{"to": "<ID>", "marked": "<the looks_like ID, or null>", "at": "YYYY-MM-DD"}` (on the rejected item when nothing new was carried), which Activity › Quality counts. Bulk approval (`review.individual_only`): an update to an action, RAID item or decision is routine only when its `changes` hold nothing but `due_date` and `latest_update` (a decision's `needed_by`).
- **`done`** on a spec update (BL-218): `{"strength": "Looks done" | "Maybe done" | "Not done", "quote": "<the words>", "who", "at", "folder", "reason", "project", "due_date"}`. The sweep stages `actions` and `raid` updates from it (`changes`: `status: "Closed"`, and for an action `latest_update` "Done: Mail 09-10-2026 15:02 by …: “…”"; Not done: `due_date` only), refused, with a note, for another project, a closed item, an item raised after the message, a message neither from the owner nor Alan that doesn't name the owner, an unstructured source, or the switch off; Teams' Looks done becomes Maybe done unless the quote names the ID. The minutes attach it to the closing update the meeting proposed (a passage not from the owner or Alan becomes Maybe done). The staged item carries **`suggested`**: `{"feature": "done", "strength", "reason", "evidence": {"kind": "mail" | "teams" | "meeting", "at", "who", "quote", "source"}}`, `why` "Looks done: <evidence>", and `low-confidence` unless Looks done. A closing update is individually approved (`review.individual_only`).
- **Vague titles** (BL-220): a new action whose description has under four words or no verb gets `inferred: [{"field": "description", "why": "Vague title (no verb): Sharpen offers a clearer one"}]` (BL-208's field), so Review puts it first and offers Sharpen.
- **`done-candidates`** (read-only helpers for the skills): `sweep.py done-candidates <messages.json>` (`{"messages": [{source, folder, from, to, sent, text, attachments}]}`, removed once read) and `minutes.py done-candidates <CODE> <transcript>` print `{"candidates": …}` with each item's hint and reasons.
