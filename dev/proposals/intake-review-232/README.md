# #232 Intake and Review on one page: the skeleton (232-0) and its seams

Release 2.5.0. Branch `p250-skeleton` (off `v240-r2`). No guarded file is changed and none is proposed: the Not needed reason
and Later go through the existing clear route (`live_server.py` passes each item to `build_dashboard.clear_meetings` unchanged).

## The row model (server, read only)

`build_dashboard.intake_review(meetings, inbox, review, today)` → `D.intake_review`, built after `meetings`, `inbox` and `review`.
The pure part is `intake_review_model` (tests: `dev/tests/test_intake_review_model.py`).

```json
{"v": 1,
 "meetings": [{"id": "m3f1c0a9b2e", "src": "calendar", "key": "ev-1", "mkey": "calendar:ev-1", "path": null,
               "title": "Example steering", "day": "2026-10-05", "start": "09:00", "end": "10:00", "p": "ABC",
               "private": false, "teams": true, "tx": "available", "later_back": false,
               "stage": "drafted", "state": "proposals", "age": 3, "stale": false,
               "files": ["proposed-2026-10-05-steering.json"], "groups": {"needs": [1, 2], "routine": [3, 4]}}],
 "mail":  {"needs": [9], "routine": [8]},
 "other": {"needs": [10], "routine": []},
 "later": [{"key": "ev-6", "title": "Supplier call", "day": "2026-10-07", "start": "16:00", "since": "2026-10-07"}],
 "not_needed": [{"key": "ev-5", "title": "Catch-up", "reason": "Informal chat", "note": ""}],
 "counts": {"arrived": 3, "ready": 2, "drafted": 3, "approved": 1, "to_approve": 10, "badge": 12}}
```

- **Rows**: calendar meetings in the window, uploaded files (new or drafted; a loaded transcript is its calendar row), and
  drafts whose meeting is in neither (`src: "draft"`). Newest day first, each day in time order.
- **stage / state**: drafted/proposals when it has pending proposals; approved/done when processed or all decided; else
  arrived/ready (transcript available or loaded, or a new upload) or arrived/waiting. `running` is the page's (`irBusy`).
- **Proposals are Review numbers** (`n`, the rows of `D.review`): the page joins by `n` and drops the ones it has decided
  (`irDone`), so an apply or a decision never needs a new model to redraw.
- **Join**: a proposal's meeting block key (`calendar:<event id>`), else its transcript path (an upload), else `cx-sweep` is
  mail, anything else (cx-edit, reports, weekly updates, file changes) is `other`.
- **Routine** is `review.hold_reason(item)` (new; `cmd_bulk` now uses it, same result): no project or a possible match,
  a conflict, `invalid` (Alan, 18-10-2026), or anything `individual_only` names. Each Review row carries it as `hold`
  ("" is routine; minutes, reports and file changes are always held).
- **Later and Not needed** live in `system/staging/intake-cleared.json`: an entry may carry `kind: "later"`, and for Not needed
  `reason` (Informal chat, No decisions, Duplicate of another meeting, Other) and `note` (one line, 200 characters).
  Request: `POST /api/intake/clear {op: "clear", items: [{key, day, start, title, kind?, reason?, note?}]}`; undo with
  `{op: "restore", keys}`. A bad reason or kind is refused (400, today with the route's "That day isn't valid" words).
  A Later meeting returns (`later_back`) once its transcript is available or loaded; nothing else brings it back.

## The page

| File | What |
|---|---|
| `src/core/irFold.js` | the folding rules and live counts, pure (tests: `test_intake_review_fold.py`, Node) |
| `src/stores/intakeReview.js` | the signals: view (localStorage `creaite-ir-view`, try/catch), open meeting, stage filter, folds, peek, busy |
| `src/components/intakeReview/IntakeReviewPage.jsx` | the shell: title, view switch, stage counts, Later and Not needed, keyboard stubs |
| `src/components/intakeReview/views.jsx` | List, Board, Two panes (minimal) and the mail and other sections |
| `src/components/intakeReview/rows.jsx` | `MeetingRow`, `ProposalGroups` (group heads, Approve routine), `ProposalLine` (placeholder) |

Address `#intake-review`; `#review`, `#intake` and `#inbox` open it (`nav.js parseHash`). `go("review")` and `go("inbox")` still
draw the old pages, so the existing tests and Today's links work until they are replaced. The sidebar has one entry, id
`review` (its button, its badge `#revBadge` and saved sidebars keep the id), titled Intake and Review; `rail.js railGo` opens
the new page. The Intake entry is gone from the sidebar (a saved sidebar that names it drops it).

## Who replaces what

- **232-A (Intake side)**: `MeetingRow`'s actions (Process with progress via `irBusy` and `mtgBusy`, Later, Not needed with a
  reason and Undo, through the clear route above), Process all ready, Upload files (drop anywhere), Restore in Later and Not
  needed, keys Enter (process), N, H. Replaces `intake.js` and the Intake parts of `meetings.js`; the files' Not needed (L4).
- **232-B (Review side)**: `ProposalLine` becomes the full row (kind pill, title, the emphasised line, quote, source, Approve,
  Reject with a reason via `RejectMenu`), Approve routine through `rvDecideMany` (one apply, one Undo; `irBulk` gives the
  numbers), the peek for mail and Teams (`irPeek`; Save, Save and approve, previous and next), keys arrows and Esc. Replaces
  `review.js`, `components/review/*` and `core/keys.js`'s Review block; `rvBulkOK` should read `hold` (the invalid mismatch).
- **232-C**: the rail badge (`renderBadge` in `core/server.js`) and Today's Intake and Review block from `irLiveCounts().badge`;
  ⌘K's Go to (still Intake and Review as two entries); retire `go("review")` and `go("inbox")` (alias to `intake-review`);
  rewrite the intake, meeting and review tests and the snapshots; the screenshot sheet.

## Open risks

1. The badge number changes meaning (ready meetings and files plus proposals) when 232-C wires it; `test_chat_and_sweep`
   counts proposals only.
2. `other` proposals (cx-edit, reports, weekly updates) are not in the mockup; the skeleton lists them as Other proposals.
3. A minutes block filed under two projects is one row with its first project.
4. `D.intake_review` is rebuilt with the data; the live server's quicker file refresh (`files`/`inbox`) does not rebuild it.

## 232-A (Intake side) as built

- `components/intakeReview/actions.js` (re-exported by `IntakeReviewPage.jsx`): Process (loads the transcript if needed, then `process <file>` through `askLive`; progress on the row via `irBusy`; the ask panel is not opened), Process all ready, Later, Not needed (four reasons, Undo), Restore, Upload files (choose, or drop anywhere on the page). `stores/intakeReview.js` has a `#232-A` section (`irNotes`, `irAside`, `irNote`, `irSetBusy`).
- Keys Enter, N, H are the page's own, bound in capture so N on a meeting does not also open the note drawer (`core/keys.js` is untouched).
- Later: shown on ready and waiting rows. A Later entry now carries `seen` (its transcript was already here): it stays in Later until Restore; without it, it returns when a transcript arrives. A file set aside (Not needed or Later) is listed with its reason and leaves the rows (`aside` in `intake_review_model`).
- `core/server.js refreshAll` redraws an open Intake and Review (one line); 232-C needs nothing more there.
- Tests: `test_intake_review_intake.py` (browser and model), `_keys_intake.py`, `_rules.py` (meetings part), shared set-up `ir_intake_support.py`. The old pages and their tests are untouched (232-C retires them).
