# Proposal: a work item's complete history (#241 Part D), the guarded parts

For Jarvis to apply. The design is in [DESIGN.md](DESIGN.md). The unguarded parts are already on this branch:
`system/scripts/item_history.py` (the reader), `dev/tests/test_item_history.py` and `dev/tests/test_item_history_route.py`.
They work today without these diffs; the diffs make the route exact and durable, and add the read route.

## What

| Diff | File | Change |
|---|---|---|
| `schema.diff` | `system/scripts/schema.sql` | The new table `item_events` (references and fixed words only: no text), and indexes on `item_events(item_id)`, `item_events(change)` and `change_log(item_id)` |
| `tracker.diff` | `system/scripts/tracker.py` | `log()` calls the new `emit_event()`, which writes one event row per change_log row (never for `updated_at`). `cmd_apply` sets `EVENT_CTX` for each item. `cmd_undo` passes the rowid it reverses (`undoes`). A rejection of an update to an existing item becomes `kind: reject`. The recode rewrites `item_events`. `query` may read the table |
| `live_server.diff` | `system/scripts/live_server.py` | `GET /api/item/history?id=…`: token-checked and read only, one item ID only (anything else gets a 400), returning `item_history.history_of` |
| `tests-after.diff` | the two test files | Removes the five `@unittest.expectedFailure` decorators once the diffs are in |

## Why

- Today the route of a change can only be worked out from its proposal file, which may be gone or rewritten by an undo.
- The dashboard's place (peek, cell, bulk bar, menu) is never recorded.
- An undo is matched to what it reverses by inference.

The brief asks for "who, via where, what, when" and for each undo to strike the original. Storing the route with each change
makes that exact for good, at the moment it is written.

## Apply order and verified base (22-10-2026)

Base: `origin/v261-241` at `7f254b76` (the 2.6.1 line head plus #241). `live_server.diff` was regenerated with
shorter context (`git diff -U1`) because its route-table hunk no longer applied once `files_get` gained a trailing comment.
`schema.diff`, `tracker.diff` and `tests-after.diff` are unchanged.

Each of the four applies and reverses (`git apply --check`, then `-R --check`) on that base on its own. All four also
apply and reverse together with `291/update.py.diff`, `291/live_server.py.diff`, `300/live_server.diff`,
`261-inode-gap/tracker-inode.py.diff` and `261-low-notes/tracker-resolve-einval.diff`, in both orders tried:
the work-item-history diffs first, and the others first. No order dependence was found, because the hunks have distinct anchors.
Recommended: `schema`, `tracker`, `live_server`, `tests-after` in that order (tests-after last, as it needs the other three).

## Risk

- **Low; additive.** It adds a new table, so no existing row or rowid changes. `migrate` creates the table with the schema
  script (no table rebuild). A database not yet migrated has no `item_events`, and `emit_event` does nothing there.
- **An apply never fails because of history.** An IntegrityError on the event row is caught (SQLite rolls back only that
  statement) and logged to the debug log as a warning. The change itself stands.
- **No text is stored.** Before and after stay in change_log, as today. The event row holds CHECKed words and one reference
  of at most 300 characters on one line.
- **The engine.** `tracker.py` imports `item_history.py` lazily. If the module is missing (a test vault that copies only some
  scripts), the route falls back to the via alone.
- **Cost.** Each change_log row gets one INSERT and one sqlite_master lookup; an undo also gets an index lookup.
- **Recode.** `item_events` is added to `RECODE_OTHER`, and `_recode_events` follows the change_log rewrite, so
  `recode_unclassified` stays empty.
- `live_server.py`'s route returns the item's history to an authorised page only.

## How to apply and test

```sh
git apply --check dev/proposals/work-item-history/schema.diff dev/proposals/work-item-history/tracker.diff \
                  dev/proposals/work-item-history/live_server.diff dev/proposals/work-item-history/tests-after.diff
git apply dev/proposals/work-item-history/schema.diff dev/proposals/work-item-history/tracker.diff \
          dev/proposals/work-item-history/live_server.diff dev/proposals/work-item-history/tests-after.diff
python3 dev/tools/check.py                         # check: OK
python3 dev/tests/test_item_history.py             # 19 tests OK; before tests-after.diff: "unexpected successes=3"
python3 dev/tests/test_item_history_route.py       # 3 tests OK
python3 dev/tests/test_tracker.py; python3 dev/tests/test_activity_undo.py; python3 dev/tests/test_recode.py
python3 dev/tests/test_archive_items.py; python3 dev/tests/test_archive_items_marks.py; python3 dev/tests/test_reject_reasons.py
python3 dev/tests/test_rejects_real_life.py; python3 dev/tests/test_schema_sprint5.py; python3 dev/tests/test_record_commands.py
python3 dev/tests/test_history_feed.py; python3 dev/tests/test_live_server.py
```

All of these were run on 19-10-2026 against a copy of this branch with the four diffs applied, and all passed.
`git apply --check` passed on this branch and on `origin/main` at f92f440a (19-10-2026); see above for the 2.6.1 line. On a live vault the table appears at the next
`tracker.py migrate` (every update runs it). Older history keeps showing, worked out as before (`exact: false`).

## Not in these diffs

- The peek's UI. The A/B/C builder wires the Activity, Updates and Source tabs to the JSON in DESIGN.md.
- The dashboard writing `"place"` on its proposals (the front-end contract in DESIGN.md), which is unguarded.
