# #275 Track from Review: the one guarded change it would like (tracker.py)

Everything else in #275 is in unguarded code. The Track column is enforced on the server in `minutes_record.py` and `review.py`:

| Path | What enforces Track |
|---|---|
| Minutes view's Approve minutes, Review's Approve on the minutes (button, key A, menu) | `stores/minutes.trackApprove` (the view's changes, then `/api/minutes/approve`); `review.approve_minutes` brings the record in line with Alan's choices again (`minutes_record.track_reconcile`) and registers only rows not crossed or left with neither, never an item with no row (`track_rowed`) |
| `review.py approve <minutes>` (Claude Code, ask creaite, `/api/review`) | `review.decide_record` → `review.track_minutes`: the record reconciled, the ticked rows approved with the minutes (`track_ticked`) |
| `review.py approve <item>`, `review.py bulk` | refused or held ("not ticked in the minutes", `track_blocked`) |
| Review's bulk approvals in the browser (Approve routine, the bar's Approve, the group tick, Approve n routine) | `rvBulkOK` and `routineKid` leave out a row with `trk` (build_dashboard, from `track_blocked`) |

Review's bulk approvals (`rvDecideMany`, the funnel for Approve routine, the bar's Approve and Approve n routine) wait for a
reload still bringing the Track choices (`TRKRELOAD`: leaving the Minutes view reloads the data, `reloadForTrack`), then take
each row as the data now has it and leave out any row with `trk`. That closes the same-tab race Cap found (Review first drawing
the old rows straight after the Minutes view; `test_06`).

**Without the diff, two paths stay open.** Review's bulk approvals write decisions straight into the proposal (`editProposal`)
before `/api/apply`, and `tracker.py apply` never reads the Track column, so:

1. **A stale page in another tab or window:** one loaded before a Track choice was made elsewhere, whose rows carry no `trk` and
   whose data isn't reloaded, can still approve and apply a crossed item.
2. **A proposal edited by hand** (or any writer that sets `decision: "approved"` on a crossed or neither item) reaches apply.

`tracker-track-problems.diff` closes both. It adds `track_problems` to `_validate_work`, which calls
`minutes_record.track_apply_problems` (unguarded, tested without the diff):

- only an item **approved** and crossed or left with neither stops the apply (all or nothing); a pending one, the normal state
  between crossing a row and approving the minutes, never does;
- the stopped item goes back to **pending** (saved when the apply stops), so it is in Review's queue again, never stuck, and the
  message says how to clear it: "approve the minutes in the Minutes view (it clears crossed lines), or tick it there to register
  it" (Review can also reject it);
- it **fails closed**: a draft record that can't be read, with an approved item not yet applied, stops the apply.

Apply (from the repository root): `git apply dev/proposals/track-from-review/tracker-track-problems.diff` (`git apply --check`
passes on `v26-track-from-review-2`, and `git apply -R --check` once applied). In `dev/tests/test_minutes_track_review.py`,
`ServerTrack.test_apply_refuses_a_crossed_item_approved_by_hand` and `test_a_pending_crossed_item_never_stops_the_apply_of_another`
are skipped until it is applied, then run by themselves; the whole file passes with it applied.

`review.py approve <minutes>` says what it did to the lines ("1 crossed line taken out of the minutes, 1 line kept in the minutes
untracked"); for a record with no Track choices it says the rows ticked by default are registered, as the Minutes view's Approve
minutes does (Cap's LOW-MEDIUM note: a change from before #275, when it filed the minutes only; for Jarvis or Alan to confirm).
