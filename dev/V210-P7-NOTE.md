# v2.1.0 P7, the minutes view: handover note (Team Stark, 15-10-2026)

Branch `v210-p7-minutes-view` (P4 + sprint-reporting merged at 1ea00a3a). WIP commit 6dfa3d3c, then resumed (Team Stark, 15-10-2026 afternoon): **done on the stub sheet**; only the move to P5's Sheet.jsx is left. Nothing pushed.

## Done (built; typecheck 0; dashboard.html rebuilt; not yet run in a browser)

- `src/stores/minutes.js`: the view's state; P4's `/api/minutes/draft`, `save` (page or `op`), `approve`, `export`.
- `src/components/minutes/`, all on `report/SheetStub.jsx`'s props, SectionCtx and RowCtx (move to P5 by changing the import):
  - `MinutesView.jsx`: `#minutes=<stored path>` (`go('minutes', {file}|{path})`), under Review in the rail (no new top-level page);
    the bar: versions (an earlier version opens its kept copy), One version / Internal + distributed, Internal | Distributed |
    Side by side, Transcript, "n checks open", Export, Approve minutes. A row change saves unsaved page edits first.
    `levelPair()` levels matching sections and `ctx.level` blocks in Side by side (the stub doesn't).
  - `TranscriptPane.jsx`: turns with times, search (count, Enter goes to the next), close; `jumpTo(turn)` highlights and scrolls the pane only.
  - `TextLines.jsx`: text sections line by line, each with its time tag (✕ removes it), inline checks, Internal only; topics are level blocks; Edit opens the sheet's Text.
  - `ItemRow.jsx`: what the row does (IDs open the peek, Open opens the staged item in Review's peek), words edited in place (`edit` op),
    owner picker from the register (remembers an unknown owner as an alias through `regAddAlias`), deadline, raid type,
    Looks like (Update that one, What changes, Keep as new), Remove menu (the item and its line, or Keep the line only) with Undo on the toast.
  - `DeadlinePopover.jsx`: words through `core/datewords.js` deadline mode from the meeting's date, shown before being set; quick picks with dates; a calendar; Not set.
  - `Coverage.jsx` (an extra after Open questions): verdicts, Deal with it… (carry, session, drop, enough) with Add a line, Undo; milestone notes open the milestone.
  - `ApprovePopup.jsx`: the Dialog block, 784px; the group's one tick (on), one tick each (off), waiting and removed items, open checks; one apply, Undo on the toast; then opens the filed minutes.
  - `Checks.jsx`, `Pop.jsx` (popover: Esc, click outside, focus back), `context.js`, `minutesDoc.js` (plain-code checks: unknown owner, no owner, deadline not as said, a figure the turn doesn't say, a refused item; the distributed preview; what it leaves out).
- Wiring: `shell.html` `#v-minutes`; `core/nav.js` (address, rail key, tab name); `panel.js` `openProposal`: Open draft on a minutes record opens the view (the live server is needed; without it, the old message).
- CSS: one block at the end of `style.css` (tokens only).
- `dev/tests/test_minutes_editor.py`: written (6 tests: opens and tags; Side by side level; popups close on Esc and outside with focus back; Remove and Undo, Keep the line only; the deadline popover; checks, coverage, ## Resumed (15-10-2026 afternoon), with Jarvis's 12:45 answers on #70

- Contract §4.5: time tags are P4's shape `{ref: "transcript", turn, time, text}` (the stub's chip takes it too).
- `/api/minutes/export` takes `version: "distributed"`: `minutes_record.distributed_of` builds the distributed record (no Internal only
  line or row, no withheld item), written as a working copy in drafts/ and exported through `creaite_doc.export` into the minutes'
  folder (a create, a new name each time; the working copy then goes). Refused until the internal minutes are approved.
- `/api/minutes/draft` returns each item's `labels` (its own and the tracker's) and `withheld` (Sensitive, partner-only or
  labelled to exclude); the view's preview, Internal only marks and "leaves out" check use them.
- A row marked Internal only as a draft ("@3") stays marked once filed (matched by its number).
- test_minutes_editor (6) passes; test_ui_sweep has the minutes, approve popup and deadline popover screens; shots in
  `~/dev.env/team-stark-shots/p7/`. check.py back to its 12 (board tools).
- test_snapshots' settings-advanced golden differs from P2's "File the exports beside it" setting (upstream, not P7).

## Left

1. Move onto P5's Sheet.jsx when it lands (change the import; drop `levelPair` if the sheet levels extras itself).

o_real_names.
5. Then per part commits are already folded into the WIP commit; split no further.

## Commands

    python3 dev/tools/split_dashboard.py build && python3 dev/tools/typecheck.py
    python3 dev/tools/run_tests.py dev/tests/test_minutes_editor.py   (or python3 dev/tests/test_minutes_editor.py)
    python3 dev/tools/run_tests.py dev/tests/test_minutes_record.py dev/tests/test_minutes_approve.py dev/tests/test_minutes_draft.py dev/tests/test_minutes_review.py dev/tests/test_creaite_doc.py dev/tests/test_dashboard_split.py dev/tests/test_ui_sweep.py dev/tests/test_snapshots.py dev/tests/test_no_real_names.py
    python3 dev/tools/check.py

## Decided, and questions

- Built to the decisions in force: saving over filed minutes stays refused (approved minutes open read only); the bulk rule unchanged (the popup mirrors `minutes_plan`, MINUTES_GROUP_JOINS empty); Polish isn't P7's (it's the sheet's AI bar).
- **Not on this branch, so not used:** Picker, Toast, Combobox blocks and the design-scale tokens (v1.9.5, BL-316/BL-325); `test_shared_behaviour.py` and `SCREEN_AREAS` don't exist here. Used Dialog, Menu, IconButton, `snack`, and a local `Pop` (a candidate Popover block).
- **Contract question 1:** P4's time tags are `{ref: "transcript", turn, time, text}`; §4.5 says `{ref: "t:00:14:32", text}`. The view draws its own tags; P5's sheet should accept P4's shape (or P4 change).
- **Question 2:** the distributed version has no route: it is a preview made on the page (`distributedOf`), with Internal only marks kept in `layout.internal_only` and the switch in `layout.distributed` (saved with the page). Filing or exporting a distributed record needs a P4/P2 route (`audience: "distributed"`).
- **Question 3:** "remembered for the meeting series" (BL-338 point 13) is per record for now.
- **Question 4:** Sensitive on a staged item is read from its flags or values; tracker labels aren't in the page data.
- **Question 5:** reading an earlier version in the view needs a route (`creaite_doc.read_version`); for now an earlier version opens its kept copy in the browser.
- The stub saves only on ⌘S or Save (P5 adds the 1.5 s autosave); a row change saves unsaved page edits first.
