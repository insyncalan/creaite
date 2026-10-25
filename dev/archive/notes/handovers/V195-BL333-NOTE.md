# BL-333 (v1.9.5): the page scrolled past its own bottom

Built on BL-325's branch (`v195-design-scale`, checked out in another worktree, so on `v195-design-scale-bl333` from `origin/v195-design-scale`).

**Cause, confirmed** (headless Chrome, snapshot sample vault plus a fixture calendar, 1400 px and 320 px). `.vh` is `position:absolute`; every screen's scroll box (`.view`) and the Prep popup's (`.prepbody`) were `position:static`, so a hidden element took `body` as its containing block and stretched the window:

- **Today**, 1400 px: `span#pfd-ABC.vh` (the Portfolio table's project description) at y 2058 in a 900 px window. The Prep popup over Today showed the same.
- **Intake**, 1400 px and 320 px: `label.vh` "Quick capture notes" (`#qcNotes`'s label), page 965 and 1499 px tall.
- Every other screen and Meetings › Prep was already fine. At 320 px Today's hidden spans had a positioned table cell as their containing block, so nothing escaped there. The Prep page files the write-up names (`PrepPage.jsx`, `PrepFacts.jsx`) aren't on this branch: here Prep is `meetings.js` and the `#prepDlg` popup.

**Fix.** One rule in `style.css`, beside `.view`: `.view,.prepbody{position:relative}`. It adds no numbers and doesn't hide overflow on html or body. Nothing moves: no descendant positioned absolutely has its containing block changed (checked on every screen; the popups are `position:fixed`), and the snapshot goldens are unchanged. Afterwards the window is exactly `innerHeight` tall on every screen, at both widths.

**Test.** `test_ui_sweep.py` `ScrollEnd` checks every screen in the sweep's list (Today, Work and its states, Review, Intake, Files, Activity, Projects, the project page, Milestones, People, the person page, Help, each Settings tab), Meetings › Prep (a meeting page from a fixture calendar) and the Prep popup, at 1400 and 320 px. On each, the window can't scroll (1 px allowed), and every scroll box ends at its last visible content plus its bottom padding (1 px allowed). With the rule removed, it fails on Today, Intake and the Prep popup.

**Unrelated, already failing:** `test_meeting_hub` `test_links_in_from_today_intake_and_an_unknown_address` fails with or without this change. It adds a meeting on the real today, and today (14-10-2026) is also the fixture's day that already holds "ABC Design review".
