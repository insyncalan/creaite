# A work item's complete history (#241 Part D): design

The brief, under "A complete history in Activity", asks for every change to a record to become an event, newest first, saying
who, via where, what and when. The peek's tabs filter that one list. This note covers the event model, where events are stored,
how each write path emits one, the read API, performance, and what is not covered. Built and tested: `system/scripts/item_history.py`,
`dev/tests/test_item_history.py` and `dev/tests/test_item_history_route.py`. Guarded and proposed: `schema.diff`, `tracker.py`'s
`tracker.diff` and `live_server.diff` (see README.md).

## Event model: the JSON the peek wires to

`item_history.history_of(id)` returns this, and `GET /api/item/history?id=ABC-A-001` returns it with `"ok": true`:

```json
{"id": "ABC-A-001", "exact": false, "events": [
  {"id": "c189", "k": "change", "who": "You", "route": "dashboard", "place": "peek", "origin": null, "via": "the peek",
   "field": "due_date", "label": "Due", "before": "2026-10-12", "after": "2026-10-14", "at": "2026-10-13 09:12",
   "apply_id": 10, "src": "system/staging/applied/proposed-….json", "struck": false, "struck_by": null, "undoes": null,
   "exact": false}]}
```

- **`k`** (the icon, and the tab filter): `create`, `change`, `cv` (client-visible), `label`, `link`, `reject`, `undo`,
  `archive` and `chase` go on the **Activity** tab. `update` (latest update, reasoning, response) goes on **Updates**.
  `source` (a change of source) and `again` (raised again) go on **Source**. **All** shows every kind.
- **`who`** is `You` or `creaite` (the archiving, a migration, raised again). **`route`** is one of `dashboard`, `review`,
  `cx-edit`, `note`, `assistant`, `excel`, `undo`, `activity` (Activity's undo several), `archive`, `migrate`, plus `minutes` and
  `sweep` (raised again) and `chase`. **`place`**: for the dashboard it is `peek`, `cell`, `bulk`, `menu`, `board`, `today` or
  `card` (ask creaite's card). For Review it is where the item was decided: `dashboard`, `excel` or `minutes`, or `null` for
  cx-review. **`origin`** is what fed Review: `sweep`, `minutes`, `drafts` or `report`. **`via`** puts all of this in words
  ("the bulk bar", "Review (from the sweep)"). It never names a command (#188).
- **`field`/`label`/`before`/`after`**: the stored values, so dates are YYYY-MM-DD (the page shows DD-MM-YYYY), Client-visible is
  `"0"`/`"1"`, a milestone is its ID, a link is `from|to|kind` and a label is its name. `at` is `YYYY-MM-DD HH:MM` (a chase
  has only a day).
- **One event per change.** Each change_log row is one event, with four exceptions: a created item is one `create`, carrying
  `made` {owner, due_date, priority, type, status}; a link or label row is one event on each item it touches; `closed` rides on
  its status event as `closed` {before, after}; and a history-only reason (`item.note`) becomes the event's `note`. A rejection
  keeps a `note` only when it is one of the seven reasons. `updated_at` never appears.
- **Undo.** Each reversed field gets its own `undo` event (just one for a created item, link or label). `undoes` names the
  original. The original gets `struck: true` and `struck_by`, unless that undo has itself been undone (an Activity revert
  undone by Undo).
- **`src`** is one reference of at most 300 characters on one line: the item's source (a path, `…#p4` for a note, or a mail or
  chat reference as the tracker keeps it), else the proposal file. It is never text.
- **`exact`** is true when the route came from a stored event and false when it was worked out. The top level is true only
  when every event is exact.

## Where it is stored

There is a **new table, `item_events`** (schema.diff), beside change_log. It is not new columns on change_log, because
`tracker.py migrate` rebuilds a changed table by copying it. That copy could renumber change_log rowids, and Activity's
reverts (`via` "revert:12,15", `reverted_rowids`) depend on those rowids. A new table is created by the schema script without
touching a row. Its columns are `event_id`, `at`, `apply_id`, `item_id`, `change` (the change_log rowid, or the `rejected` row),
`kind` (change/reject), `route`, `place`, `origin`, `actor`, `src_ref` and `undoes`. Every word column is CHECKed against the
lists above, and `src_ref` is limited to one line of 300 characters. **No text:** before and after stay in change_log, where
they are today. Indexes: `item_events(item_id)`, `item_events(change)` and `change_log(item_id)`.

**Migration:** none for existing rows, and nothing is rewritten. `migrate` (run by every update) creates the table. Older rows
have no event row, and item_history.py works their route out with the same rule (`derive`).

## How every write path emits one

`tracker.py` is the only writer and `log()` is its one call per change_log row. The diff makes `log()` call `emit_event()`, inside
the same transaction:

| Path | How it gets its route |
|---|---|
| `apply`: dashboard edits (peek, cell, bulk bar, menu, Board, Today), ask creaite's card | `cmd_apply` sets `EVENT_CTX` (the proposal, the item and its file) for each item. `derive()` reads `source_run`, `place` and `applied_on_card` |
| `apply`: Review (dashboard, Excel sheet, minutes record, cx-review) of sweep, minutes, drafts and report proposals | the item's `decided_in`, plus the proposal's `source_run`, its `meeting` or `report` block, or its file name tag |
| `apply`: cx-edit, ask creaite (`assistant`), the Excel import, a note's Find updates (`source_run: note`), the daily archiving | the via or the proposal's `source_run` |
| labels (`set_labels`, `delete_row`) and links (new or cancel) | already logged through `log()` inside the item's apply |
| a rejection of an update to an existing item | `kind: reject`, with the item's ID (`_record_rejection` logs through `log()`). A rejected *new* item has no record and no event |
| `undo` | `log(..., undoes=rowid)`: the event records the event it reverses |
| `undo-changes` (Activity) | its rows are logged with a `revert:` via, so the route is `activity`. The reader finds the target from the rowids in the via |
| `migrate` (`retire_missed`) | the via `migrate` (actor creaite) |
| recode | `_recode_events` rewrites `item_id` the way the change_log rows are rewritten |

**Front-end contract (the A/B/C builder):** every dashboard proposal adds a top-level `"place"`: `peek`, `cell`, `bulk`, `menu`,
`board` or `today`. Today `panel.js` writes only `peek` meta, so the place is `null` and the event reads "the dashboard". Nothing
breaks without it.

**Outside the database, read as they are:** chases (`system/staging/chases.json`: IDs, a date and the mode) and raised again
(`mentions.jsonl`: a date, the ID, the run and the source).

## Read API

`item_history.py` is a library with no command line. A command line would need a `reach.SCRIPT_COMMANDS` entry, which is
guarded and not needed. `history_of(id)` opens tracker.db read only. `live_server.diff` adds
`GET /api/item/history?id=ABC-A-001`. It is token-checked, takes one item ID (anything else gets a 400) and is read only. The peek
can fetch it when the Activity tab opens, and again on the change stream's `changed` event for that item.

## Performance

Reading one item takes one change_log query (by `item_id`; links and labels by a LIKE over those rows), plus the proposals of
that item's applies only (each file read once per call), plus two small staging files. Measured: about 8 ms for an item among
50,000 change_log rows, with or without the diff. Writing adds one INSERT per change_log row. Each emit also runs one
sqlite_master lookup and an `item_events` index lookup (on an undo). An IntegrityError is logged and never stops the apply.

## What is not covered, and how it degrades

- **Before the diff:** the route is worked out from the applied proposal. A proposal that is gone or unreadable leaves only the
  via. That is still exact for dashboard, cx-edit, ask creaite, Excel, undo and archive. A file name gives note, sweep or
  Review, with no place and no source. An undone rejection drops out, because its proposal item went back to pending. The tests
  that need the diff are expectedFailure and give their reason.
- **Not item history:** settings (settings-log.jsonl), the people register, memory and Current state (files-log.jsonl and
  Activity's file lines), the notes themselves, and Review's still-pending proposals (shown in Review, not as events).
- **`who`** has only two values, because creaite has one user. Places before the front end writes `place` stay `null`.
- **Raised again** from a confidential source shows its reference (the peek is internal; drafts leave such sources out). This
  is for Alan to decide if he wants it hidden.
