# v1.9.0 — BL-286 C, Shape the meeting: takeover note

Taken over from Team 1 on 14-10-2026 (Alan approved; Team 1 out that morning). Branch `sprint-prep-shape`, from head 3ac9fb2
(a merge of main after e1583d1, "BL-286 C: Shape the meeting, inside the Prep popup").

## What Team 1 built (e1583d1)

- **Shape this meeting**, first in the Prep popup's toolbar, opens a panel inside the popup (`#prepShape`; the brief steps aside):
  a drag-larger instruction box, suggestion chips (`/api/prep/chips`) that add their item to the text, Shape and Regenerate through
  the run engine (`/api/prep/shape`, streamed through `draftAsk`'s new `url` option: progress, Stop, one run at a time).
- **"creaite read this as"**: focus chips, the aim, focus only or focus first; *change* corrects it and Regenerate sends it.
- **Draft notes**: Objective, Talking points, Ask, Carried over, as editable, resizable boxes with each line's citations (item → peek,
  file → `/api/open`, mail or Teams → web link). Regenerate keeps edited sections; "let creaite redraft it" gives one back.
  **Accept** → `/api/prep/focus/save` (`system/staging/prep-focus.json`, the server's format); **Discard** counted in `draft-stats.json`.
- **What's in focus** (`/api/prep/filter`): items and documents with why, tick out, "n of N" (N only what is listed, Alan 13-10-2026),
  Show everything instead; items open the full peek over the popup.
- Settings switch "Shape the meeting" (`drafts.FEATURES`, `settings-defaults.json`, the page's `DRAFTFEATURES`).
- Building blocks: `components/Chip.jsx`, `components/mount.js`; store `stores/prepShape.js`; component `components/prep/PrepShape.jsx`.
- Help, guides and the 1.9.0 release notes updated.

## What I checked

- `origin/main` had not moved past the branch's merge (4370a4e); no merge needed.
- Build not stale: `split_dashboard.py build` said "dashboard.html is up to date", `git diff --quiet` clean.
- A Chrome test of the Shape panel already exists: `dev/tests/test_prep_shape.py` (open Prep, Shape this meeting, the box and a chip,
  a stand-in Claude run, the reading and *change*, cited notes, Regenerate keeping an edit, Accept writing `prep-focus.json` through
  `/api/prep/focus/save` with edits, citations and ticked-out items, Discard counted, the peek over the popup, 320 px, the Settings
  switch, and a confidential meeting shaped with no tools and no invite text). No new test was needed.

## What I fixed

- `dev/tests/test_meeting_hub.py`, `test_links_in_from_today_intake_and_an_unknown_address`: failed every run on 14-10-2026, not
  because of BL-286 C. The fixture hard-codes "ABC Design review" on 2026-10-14 and the test adds "ABC Daily check" for today; on that
  date both are today, Today lists them in calendar order (Design review first), and the test clicked the first Meeting link. It now
  clicks the Daily check row's own link. No product change.

- `dev/tests/test_prep_shape.py`: under load (CI, and `run_tests.py --repeat 4 --stress 4`, 3 of 4 copies failing) a test timed
  out waiting for `#prepShape .shdraft`, with no page errors. Not slowness and not state left by an earlier test (each test has its
  own server and vault): the click on Shape did nothing (no run, no message, the button enabled, the stand-in Claude never called).
  The suggestion chips arrive from `/api/prep/chips` after the panel opens and share the Shape button's row; when they land after
  `b.click` has measured the button, the row wraps and the press hits empty space. `open_shape` now waits for the chips to render
  before anything clicks, and `shape()` reports the panel's state if no draft comes. After: 6/6 with `--repeat 6 --stress 4`,
  4/4 with `--repeat 4`. No product change.

## Tests (all at `-j 2`)

- test_prep_shape, test_block_chip, test_prep_popup, test_prep_reimagined, test_prep_context_pinned, test_prep_page_content,
  test_prep_updates, test_meeting_hub (after the fix), test_meetings, test_tracker: pass.
- test_snapshots, test_dashboard_split, test_help, test_ui_sweep, test_drafts_*: pass.
- test_draft_chase, test_panel_drafts, test_sharpen and the files that read `drafts.FEATURES` or `settings-defaults.json`
  (test_close_day, test_close_day_guided, test_debug_log, test_minutes_review, test_new_vault, test_motion, test_pages, test_reach): pass.
- `dev/tools/check.py`: `check: OK`.

## Goldens

- No golden re-recorded in the takeover. Team 1 re-recorded `settings-general` in e1583d1 for the new switch row only; test_snapshots
  passes against it.
