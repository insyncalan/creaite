# v1.9.4: BL-304, changes appear at once (Team 2)

Branch `v194-instant`, from `origin/release-192` with `origin/dev-week-ahead-urgent` merged. Not pushed.

## What it does

- **On screen in one frame.** An edit in a Work cell, the board, the right-click menu, the bulk bar, the peek and ⌘K changes
  the in-memory record and redraws before anything is written. Measured in headless Chrome from the edit to the next
  `requestAnimationFrame`: Work cell 27.5 ms, ⌘K 27.9 ms, board 28.7 ms, peek 40.1 ms (one frame's wait; before, the screen
  waited for the proposal write, then the apply, about 3 s with auto-apply).
- **Saved in the background through the same path.** `writeProposal` (the same dashboard proposal), then `/api/apply`
  (`hold_peek`), so `tracker.py` is still the only writer and its validation, conflict holding, logging and Undo are
  unchanged; the bulk rule is untouched. The peek still only stages (BL-176). With auto-apply off the change shows with the
  staged dot until Apply.
- **Saving mark:** a hollow dot on the row while it saves (`.pkdot.saving`); it clears when applied.
- **Order:** background saves run one at a time in the order made; a later change to the same item takes its `based_on`
  from the item as the earlier one left it, so two quick edits are two applies, in order.
- **Failure:** a refused write or apply, or an item held as a conflict ("changed elsewhere"), puts the record back, fetches
  it again, removes the page's own proposal from staging (so it neither blocks later applies nor lingers in Review) and
  says `Not saved: <reason>` with **Retry**.
- **Undo** works while saving (nothing written, or the apply undone) and after.
- **Targeted refresh:** new `GET /api/records?ids=…` returns just those items plus Review, Activity and the latest apply.
  The live-updates `changed` event now carries `ids` from the change log; the page fetches only those. A single change
  makes no `/api/data` call (tested). Full reload stays the fallback: calendar changes, tables other than actions, RAID
  and decisions, a stream gap (no IDs), a failed fetch, server restart, Settings › Diagnostics.
- A change still saving is never clobbered by fresh data: overlays (`INFLIGHT`) are re-laid after every merge or reload.

## For Alan (decisions and guard notes)

- **live_server.py routes changed (no guard or reach.py change):** a new read-only GET `/api/records` (token-checked like
  every route, item IDs only, at most 200, read-only SQLite); `/api/events`' `changed` event gains `ids` (item IDs from the
  change log, never values; omitted past 100). `do_GET` now dispatches its token-checked GET routes from one table
  (complexity limit); `/api/files`' body moved into `files_get`, unchanged. The server reads `change_log` read-only.
- **Retry after "changed elsewhere"** rebases on the item as it now is, so pressing Retry keeps Alan's value over the other
  change. Without the rebase Retry could only conflict again. Say if you'd rather Retry sent it to Review as a conflict.
- **Undo while still saving**, once the apply has happened, is an ordinary undo of that apply, so (as with every undo of an
  apply) `tracker.py undo` returns the proposal to Review as pending.

## Not done (left for later)

- A refresh still redraws the current view (`refreshAll`), not only the changed rows: no network reload, but not yet
  per-component signals.
- Derived blocks built server-side from the whole tracker (Today's week ahead and day plan, early warnings, the meeting
  hub) refresh at the next full reload, not after a targeted one.
- Review Approve and Reject keep their own path (already marked done on screen before the apply); they still reload all
  data after applying. Milestones, workstreams, the register, health and Current state saves still wait and reload all,
  as before.

## Tests

`dev/tests/test_instant_edits.py` (11, Chrome): each Done-when point above. Regression runs listed in the report.
