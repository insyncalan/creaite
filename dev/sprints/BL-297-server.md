# BL-297 server side: what the Review picker calls (sprint-smart-updates)

The Python side of BL-297 (parts A, B, C, E and D's server) is on `sprint-smart-updates`. The dashboard's picker, "Update an
existing item instead", comes later on BL-231's modules; this is what it needs. Nothing here touches the tracker: every call
changes a proposal in `system/staging/`, and apply stays the only writer.

## Routes (live server, `REVIEW_WORK_ROUTES`)

| Route | Body | Returns | Through |
|---|---|---|---|
| `POST /api/review/candidates` | `{file, ref}` (the Review row's) | `{ok, items: [{id, t, owner, due, score, strength, why, marked}], message}` | `review.py candidates <n> --json` |
| `POST /api/review/retarget` | `{file, ref, id}` | `{ok, message}` | `review.py retarget <n> <id>` |
| `POST /api/review/retarget` | `{file, ref, undo: true}` | `{ok, message}` | `review.py unmerge <file>#<ref>` |

- **candidates** lists the open items of the row's project **and table** (an action lists actions, a risk RAID items, a decision
  pending decisions), raised on or before the message's day, the "Looks like" item first (`marked: true`), then by score.
  `strength` is "Very likely", "Possible" or null, never a percentage; `why` names the signals ("Same thread · Dana · due this
  week") and is empty below Possible. `due` is YYYY-MM-DD (show DD-MM-YYYY). Empty `items`: nothing to offer, so hide the
  picker. Offer it on any pending **new** action, RAID item or decision with a project (`r.op === "new"`, `r.p` set).
- **retarget** turns the row into an update to `id` carrying the new item's due date and latest update (a RAID item's due date
  and response; a pending decision made: status and date; reasoning and options), exactly as Merge. `ok: false` with a message
  for: not a pending new item, no project, not an ID, not that kind of item, another project, a closed item. When the new item
  carries nothing new it is **rejected as a duplicate** of `id` instead (`ok: true`; the message says so). Reload the data after.
- **undo** puts back the new item as proposed, after a retarget **or a Merge** (BL-221's Merge is now undoable too), including one
  rejected as a duplicate. It works by file and item number, so the row's `{file, ref}` from before the change is enough. Offer
  it in the snack ("Now an update to FAL-A-007 · Undo").

## What the rows already carry

- `dup` (BL-221's mark) as before; its `strength` and the new signal `why` come from the staged `looks_like`.
- An update row from a retarget or merge has `op: "update"`; the staged item holds `was` (the new item) and, for a retarget,
  `retargeted: {to, marked, at}`. `review_queue` does not pass `was` to the page yet: if the picker wants an Undo on the row
  itself (not only in the snack), add a boolean such as `undoable: bool(item.get("was"))` in `build_dashboard.review_queue`
  (it changes `dev/tests/pinned/dashboard_data.json` only where a row was merged).
- `indiv` now also marks an update that changes anything but the due date and latest update (`review.individual_only`, part E):
  its `why` reads "Owner change", "Status change", "Response change", "Title change", "Project change" or "Change to <field>",
  so `rvWhyNot` and Approve routine follow it with no page change.

## Activity › Quality

`quality.measure()["repeats"]` (in `D.quality`): `{merged, retargeted, total, unmarked: {n, of, text, rated}, other_mark, missed:
[IDs]}`. `unmarked` is how often Alan pointed a proposal at an item nothing marked; `missed` lists those items' IDs (and those
where another item was marked). Counts and IDs only. A suggested line for the Quality page: "Pointed at an existing item: 6
(merged 4, updated instead 2); not marked: 1 of 6 · FAL-A-007".

## Tests

`dev/tests/test_smart_updates.py` covers the routes with a fake `run`; a page test for the picker belongs with it.
