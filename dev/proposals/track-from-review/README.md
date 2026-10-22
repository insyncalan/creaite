# #275 Track from Review: the one guarded change it would like (tracker.py)

Everything else in #275 is in unguarded code. The Track column is enforced on the server in `minutes_record.py` and `review.py`:

| Path | What enforces Track |
|---|---|
| Minutes view's Approve minutes, Review's Approve on the minutes (button, key A, menu) | `stores/minutes.trackApprove` (the view's changes, then `/api/minutes/approve`); `review.approve_minutes` brings the record in line with Alan's choices again (`minutes_record.track_reconcile`) and registers only rows not crossed or left with neither, never an item with no row (`track_rowed`) |
| `review.py approve <minutes>` (Claude Code, ask creaite, `/api/review`) | `review.decide_record` → `review.track_minutes`: the record reconciled, the ticked rows approved with the minutes (`track_ticked`) |
| `review.py approve <item>`, `review.py bulk` | refused or held ("not ticked in the minutes", `track_blocked`) |
| Review's bulk approvals in the browser (Approve routine, the bar's Approve, the group tick, Approve n routine) | `rvBulkOK` and `routineKid` leave out a row with `trk` (build_dashboard, from `track_blocked`) |

Intake's bulk approvals (`rvDecideMany`, the funnel for Approve routine, `irApproveRoutine`, and the meeting's Approve routine,
`approveRoutineTracked`; Review's page is retired) and, since round 3, the single row's Approve and the A key (`irApprove`, which
is `decide`) wait for a reload still bringing the Track choices (`TRKRELOAD`: leaving
the Minutes view reloads the data, `reloadForTrack`), then take each row as the data now has it: bulk leaves out any row with
`trk` and says how many it left out and why ("1 crossed in the minutes' Track column", `trkLeftOut`, `test_06`); the row path refuses it with
"Crossed in the minutes' Track column" (`test_07`). That closes the same-tab race Cap found on both paths (Intake first drawing the
old rows straight after the Minutes view). A bulk approval whose apply stops is never "Approved n": the summary says the apply
stopped, in plain words (`applyWords`: no tracker.py header, no proposal file name), and the batch goes back to pending, on
Intake again (`test_08`).

**Without the diff, two paths stay open.** Review's bulk approvals write decisions straight into the proposal (`editProposal`)
before `/api/apply`, and `tracker.py apply` never reads the Track column, so:

1. **A stale page in another tab or window:** one loaded before a Track choice was made elsewhere, whose rows carry no `trk` and
   whose data isn't reloaded, can still approve and apply a crossed item.
2. **A proposal edited by hand** (or any writer that sets `decision: "approved"` on a crossed or neither item) reaches apply.

`tracker-track-problems.diff` closes both. It adds `track_problems` to `_validate_work`, which calls
`minutes_record.track_apply_problems` (unguarded, tested without the diff):

- only an item **approved** and crossed or left with neither stops the apply (all or nothing); a pending one, the normal state
  between crossing a row and approving the minutes, never does;
- the stopped item goes back to **pending** (saved when the apply stops), so it is on Intake again, never stuck, and the
  message ("it is back on Intake: …") says how to clear it: "approve the minutes in the Minutes view (it clears crossed lines), or tick it there to register
  it" (Intake can also reject it);
- it **fails closed**: with an approved item not yet applied, a draft record that can't be read stops the apply, and so does one
  that is gone, has lost its data block, or whose `state` was changed by hand from draft (round 3);
- it holds after an **Undo outside the Minutes view** (`tracker.py undo`, Activity's undo): the items are pending again but the
  record's rows they had are in `meta.removed`; the check settles a copy of the record first, so the crossed item is still seen
  (as are `review.py bulk` and `review.py approve <item>`, round 3).

Apply (from the repository root): `git apply dev/proposals/track-from-review/tracker-track-problems.diff` (`git apply --check`
passes on `v26-track-from-review-3`, and `git apply -R --check` once applied). The diff is unchanged in round 3: the fixes are in
`minutes_record.track_apply_problems`, which it calls. Its docstring's "by any path" means the paths above; the one that stays open
is a write to the database that doesn't go through `tracker.py apply`, which the rules already forbid. In `dev/tests/test_minutes_track_review.py`,
`ServerTrack.test_apply_refuses_a_crossed_item_approved_by_hand` and `test_a_pending_crossed_item_never_stops_the_apply_of_another`
are skipped until it is applied, then run by themselves; the whole file passes with it applied.

`review.py approve <minutes>` says what it did to the lines ("1 crossed line taken out of the minutes, 1 line kept in the minutes
untracked"); for a record with no Track choices it says the rows ticked by default are registered, as the Minutes view's Approve
minutes does (Cap's LOW-MEDIUM note: a change from before #275, when it filed the minutes only; for Jarvis or Alan to confirm).
