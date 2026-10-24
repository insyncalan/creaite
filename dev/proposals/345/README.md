# Every route that decides an item names the item (2.6.4, #345)

2.6.3 made `expect` (the item's 12-hex fingerprint) required at `POST /api/review`. Five more routes still decided by (file, ref) with no
fingerprint, so a page left open could decide an item that had changed or moved since it was drawn. This closes them.

## What changes

`live_server.diff` (guarded; one file, `system/scripts/live_server.py`, +74 lines, 1 changed; `review.py` is not touched):

- One shared check, `expect_refusal(rows)` (with two small helpers for the reject and Approve instead routes, kept out of the routes so they
  stay under check.py's complexity limit), with `current_fp(file, ref)` (reads the very file the route is about to act on, under the same
  job lock, and fingerprints the item or the minutes block with `build_dashboard.item_fp` / `block_fp`, the functions review.py's own
  `--expect` uses).
- It runs after the route's existing "no longer pending" answer and before anything changes, on:
  - `/api/review/reject`: each row carries `expect`. All rows or none: one missing, malformed or different fingerprint declines the whole request.
    A row that is already gone is reported in `gone` as before and needs none.
  - `/api/review/rejected` with `how: approve` (Approve instead). Undo and a changed reason decide nothing new and need none.
  - `/api/review/repeat` (merge or keep as new).
  - `/api/review/retarget` (make it an update to an item). Undoing a retarget works on the file and item and needs none.
  - `/api/minutes/approve`: the fingerprint of the minutes block (`meeting`). It is checked before `minutes_destination.settle`, so a
    declined request never renames anything. The block's fingerprint does not change when the file is renamed. A file that is gone gets
    the route's own "no longer pending" answer; any file still waiting needs the fingerprint, even one with no minutes block.
- Three plain messages, none of which names a file or a script: "This page didn't say which item it meant, so nothing was changed. Reload
  the page and try again." (missing), "Review can't check which item that is..." (malformed), "That item has changed since you looked at
  it, so nothing was changed. Look at the list again." (different; the page already treats this sentence as its stale-row answer).

## Page side (unguarded, in the tree)

`review.js` sends `expect` on repeat, retarget, reject, Approve instead and the re-reject inside Approve instead's Undo, whose reply is now read (a declined one says "Not rejected again: ..." and marks nothing, via `rejectedAgainWords` in `core/say.js`); `stores/minutes.js`
sends the minutes' fingerprint with Approve minutes and, on the "changed" answer, reloads the list and says so; Activity's recent rejects now
carry `fp` (`quality.reject_row`), so Approve instead there names its item. Rebuilt `dashboard.html`.

## Not affected

ask creaite's `review.py approve|reject|merge|...` and the Excel import use the command line, not these routes, and still work without a
fingerprint. `--expect` stays optional in `review.py` itself.

## Known, for later

- `/api/review/assign` (moving an item to another project) has no fingerprint yet.
- Approve minutes' `own` item numbers still go by number; the fingerprint is the minutes block's, taken when the button was pressed.

## Risks (for the reviewer)

1. A tab left open from before the update has no `expect` to send: its first decision on one of these routes gets the reload message and
   nothing is changed (the same stale-tab rule as 2.6.3 for `/api/review`).
2. The check and the act are two steps under one lock. A change made by something that does not take the lock (the page writing a waiting
   file through `/api/fs`) between them is one request wide, as for every other route; review.py's own `--expect` closes that for the single
   decisions it covers, these routes cannot use it (many rows, merge, retarget).
3. Approve minutes checks the minutes block only. The ticked items (`own`) are still given by number, as before; the minutes view builds
   them from the same file in the same call.
4. Approve instead's Undo re-rejects after undoing the save; the fingerprint it sends is the one from before. If saving and undoing changed
   an item's content the re-reject is declined with the "changed" message and nothing is lost (the item stays approved-and-undone, pending).
5. The reject answer on a decline has `rejected: []`; a page that reads `res.ok` first, as ours do, is unaffected.

## Order and checks

First in the 2.6.4 chain (`dev/proposals/GUARDED-2.6.4.order.md`). Goes in on origin/main (e6389af8) and after 346 and 334, in any order.
Tests: `dev/tests/test_expect_routes_345.py` (23 tests on a real server over a throwaway copy, the diff put there when the tree lacks
it; a mutant per route and one for the shared check). The existing route tests now send the fingerprint
(`test_minutes_approve`, `test_minutes_destination`, `test_held_editor_307b`, `handchecks/test_v210`, `test_rejects_real_life`,
`test_smart_updates`) and pass with and without the diff.
