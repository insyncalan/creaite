# #268 Minutes view v2: the one server change it would like (APPLIED on v26-minutes-view-v2, 20-10-2026)

The Minutes view v2 is built without changing any server code. Every Track state maps onto the record's existing changes
(`minutes_record.change`), applied when Alan presses Approve minutes, then `/api/minutes/approve` as before:

| Track on a row | What Approve minutes does first | Then |
|---|---|---|
| tick, row pending | nothing | approved in the one apply (its number in `own`; the view sends `group: false`, Cap's review H1) |
| neither, row pending | `remove` with `keep_line` (the line stays, the item is rejected "Removed in the minutes") | |
| cross, row pending | `remove` (the line and the item go) | |
| tick, a kept line | `restore` | approved |
| cross, a kept line | `restore`, then `remove` | |

Nothing ticked is #261's "take no items": every item is rejected through `remove`, and `approve_minutes(group=True, own=[])` files the
minutes (checked: "Apply 2: written 0, filed 1, rejected 7").

**Changed (Cap's review H1, 21-10-2026):** the view now sends `group: false` with the ticked rows' numbers in `own`
(`track.approveArgs`), and `review._tick` approves a group item listed in `own` (review.py is not guarded). An item the minutes show
no row for (a promise) is never approved by Approve minutes: it waits in Review (`test_minutes_track_ops` RowlessPromise).

**Open (Cap's review M4):** Re-extract only opens ask creaite with the request written. The planned Re-extract run kind must
define its outcome: it replaces the record and its proposal, and says what happens to edits made in the view and to Track choices.

## The one gap: a risk's or issue's workstream

`minutes_record.EDITABLE["raid"]` has no `workstream`, so the view's Workstream dropdown on a risk or issue row is refused by the
server ("workstream can't be changed from the minutes."). The view degrades gracefully: the refusal is said on the toast and the
dropdown goes back to its value (`dev/tests/test_minutes_view_v2.py` test_04 checks both ways). Actions' workstream already works.

`raid-workstream.diff` adds `workstream` to the RAID fields the minutes may edit. `tracker.py validate` already checks a RAID item's
workstream against the project's Active workstreams (BL-58), so nothing else changes.

Apply (from the repository root): `git apply dev/proposals/minutes-view-v2/raid-workstream.diff` (`git apply --check` passes on
`v26-minutes-view-v2`). After it, test_04's refusal branch is skipped by itself and the staged risk keeps the workstream.

A risk's Priority is worked out from impact and likelihood, so the view shows it and offers no dropdown; no change is proposed for it.

**Applied** (20-10-2026, the PM's go): `git apply` on the branch. `minutes_record._workstream` also checks every workstream set from the
minutes (an action's too) server-side: one of the item's project's Active workstreams, in its own spelling, or empty; anything else
(not text, a control character, over 120 characters, an unknown name) is refused before it reaches the proposal
(`dev/tests/test_minutes_track_ops.py` RaidWorkstream).
