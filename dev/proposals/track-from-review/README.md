# #275 Track from Review: the one guarded change it would like (tracker.py)

Everything else in #275 is in unguarded code. The Track column is enforced on the server in `minutes_record.py` and `review.py`:

| Path | What enforces Track |
|---|---|
| Minutes view's Approve minutes, Review's Approve on the minutes (button, key A, menu) | `stores/minutes.trackApprove` (the view's changes, then `/api/minutes/approve`); `review.approve_minutes` brings the record in line with Alan's choices again (`minutes_record.track_reconcile`) and registers only rows not crossed or left with neither, never an item with no row (`track_rowed`) |
| `review.py approve <minutes>` (Claude Code, ask creaite, `/api/review`) | `review.decide_record` → `review.track_minutes`: the record reconciled, the ticked rows approved with the minutes (`track_ticked`) |
| `review.py approve <item>`, `review.py bulk` | refused or held ("not ticked in the minutes", `track_blocked`) |
| Review's bulk approvals in the browser (Approve routine, the bar's Approve, the group tick, Approve n routine) | `rvBulkOK` and `routineKid` leave out a row with `trk` (build_dashboard, from `track_blocked`) |

The one path the unguarded code can't close is a decision written into a proposal **file** and then applied: Review's bulk
approvals write decisions straight into the proposal (`editProposal`) before `/api/apply`, so a stale page (one loaded before a
Track choice was made in another window) or a proposal edited by hand reaches `tracker.py apply` with a crossed item approved.

`tracker-track-problems.diff` adds `track_problems` to `_validate_work`: the dry run stops the apply, all or nothing, and names the
item ("crossed in the minutes' Track column; tick it there to register it"). It calls `minutes_record.track_blocked(data,
decided=True)`, the same rule as everything above; nothing else in tracker.py changes.

Apply (from the repository root): `git apply dev/proposals/track-from-review/tracker-track-problems.diff` (`git apply --check` passes
on `v26-track-from-review`). `dev/tests/test_minutes_track_review.py` `ServerTrack.test_apply_refuses_a_crossed_item_approved_by_hand`
is skipped until it is applied, then runs by itself.
