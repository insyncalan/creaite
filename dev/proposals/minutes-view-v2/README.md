# #268 Minutes view v2: the one server change it would like (optional)

The Minutes view v2 is built without changing any server code. Every Track state maps onto the record's existing changes
(`minutes_record.change`), applied when Alan presses Approve minutes, then `/api/minutes/approve` as before:

| Track on a row | What Approve minutes does first | Then |
|---|---|---|
| tick, row pending | nothing | approved in the one apply (`group: true`, and its number in `own` if the bulk rule decides it one by one) |
| neither, row pending | `remove` with `keep_line` (the line stays, the item is rejected "Removed in the minutes") | |
| cross, row pending | `remove` (the line and the item go) | |
| tick, a kept line | `restore` | approved |
| cross, a kept line | `restore`, then `remove` | |

Nothing ticked is #261's "take no items": every item is rejected through `remove`, and `approve_minutes(group=True, own=[])` files the
minutes (checked: "Apply 2: written 0, filed 1, rejected 7").

## The one gap: a risk's or issue's workstream

`minutes_record.EDITABLE["raid"]` has no `workstream`, so the view's Workstream dropdown on a risk or issue row is refused by the
server ("workstream can't be changed from the minutes."). The view degrades gracefully: the refusal is said on the toast and the
dropdown goes back to its value (`dev/tests/test_minutes_view_v2.py` test_04 checks both ways). Actions' workstream already works.

`raid-workstream.diff` adds `workstream` to the RAID fields the minutes may edit. `tracker.py validate` already checks a RAID item's
workstream against the project's Active workstreams (BL-58), so nothing else changes.

Apply (from the repository root): `git apply dev/proposals/minutes-view-v2/raid-workstream.diff` (`git apply --check` passes on
`v26-minutes-view-v2`). After it, test_04's refusal branch is skipped by itself and the staged risk keeps the workstream.

A risk's Priority is worked out from impact and likelihood, so the view shows it and offers no dropdown; no change is proposed for it.
