# v26-line-2: merge conflicts

Base: `origin/main` (cfe9b56c, 2.5.3 published). Commit only, never pushed. Generated files (dashboard.html,
globals.json, guides, snapshot goldens) are never hand-merged: one side taken, then rebuilt.

Order: v26-track-from-review-2, v26-232-next (contains p260-r-fix), v26-review-fixes, v26-186, v26-236-next,
v26-test-v260, then the settings line: v26-settings-line-2, v26-people-m2-m3-2, v247-follow-fix.

## 1. origin/v26-track-from-review-2 (ff96eda8)

Clean. Rebuilt; nothing changed.

## 2. origin/v26-232-next (bea9de16, the Intake line)

The Intake line (#232 C2/C3) retires the old Review page (select bar, `#reviewBody`, routine groups under minutes, old
Review keys, `rvHold`/`rvRestore`), and its new Intake page approves through review.js's `decide` and
`rvDecideMany`. #275 (track-from-review) had added Track-column enforcement to the old page. Rule: the later feature keeps
its own behaviour; #275 is ported onto what survives.

| File | Resolution | Why |
|------|-----------|-----|
| `system/scripts/review.py` | both | #232's `hold_reason` is the one rule; #275's `bulk_reason` now calls it, then adds "not a strong match" and "not ticked in the minutes" (`track_blocked`) |
| `system/templates/dashboard/src/review.js` | theirs + #275 ported | `decide` gains `g` and the two #275 lines (record minutes go through `approveTracked`; a crossed/neither row is refused); `isRecordMin`, `approveTracked` kept; `rvBulkOK` and `rvWhyNot` read `r.trk`; `rvDecideMany` waits for `TRKRELOAD`. `approveGroup`/`trackGroup`/`approveGroupTracked`/`routineKid` dropped with the routine-under-minutes group they served (gone in #232) |
| `system/templates/dashboard/src/core/keys.js` | theirs | the old Review key block is gone (#232-C2); ours' only change was `decide(..., g)` inside it |
| `system/templates/dashboard/src/core/nav.js` | theirs + `reloadForTrack` import | both imports needed (theirs `reloadData`, #275 `reloadForTrack`) |
| `system/templates/dashboard/src/core/server.js` | theirs; main's gate-fix-2 `hold=rvHold()` line removed | `rvHold`/`rvRestore` no longer exist in the Intake line |
| `system/templates/dashboard/src/intake.js` | theirs | the run helpers moved to `core/intakeApi.js` |
| `core/intakeApi.js`, `components/intakeReview/rows.jsx`, `actions.js`, `dev/tests/test_intake_review_routes.py` (not conflicted) | 2.5.3 gate fix c0351517 ported | one `runId` clock read for `jobLive` and `runRoute`; lowercase "ask creaite about this" (product-name rule) |
| `dev/tests/test_review_triage.py` | theirs | the bar tests (and main's gate-fix-2 renumbering test on `#bulkApprove`) test the retired select bar |
| `system/templates/help.md` | ours + theirs' "Open draft … in Intake" line | ours rewrote the Minutes view lines (#268 v2); theirs renamed Review to Intake on one line |
| `dashboard.html`, `globals.json` | theirs, rebuilt | generated |

Judgment call: the Intake page's "Approve routine" group comes from the server's `hold`, which does not know `r.trk`; a
crossed/neither row may be listed as routine but `rvBulkOK`/`rvDecideMany` skip it, so it is never approved.
