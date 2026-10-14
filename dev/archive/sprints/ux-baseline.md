# Sprint: The UX baseline (BL-146 to BL-157)

**Goes into v1.3.0 (Alan, 10-10-2026).** `VERSION` is already 1.3.0 and stays; the release notes go in `dev/release-notes/1.3.0.md`, and v1.3.0 is not published until this sprint has merged. **The defaults below are accepted.**

Branch `sprint-ux`, worktree `../creaite-ux`, made from the tip of `main` when it starts. Read BL-145 and "UX review, 10-10-2026" in `dev/BACKLOG.md` first; they hold Alan's principle and each item's "Today", "The change" and "Not changed".

## Goal

Alan should not have to ask for the things a good tool does by default. This sprint closes the gaps the 10-10-2026 UX review found (a text box that does not show what is typed, dates that only take one format, a panel that covers the page, instructions to go and do it in Claude Code) and writes the baseline down so later sprints start from it (BL-157).

**The principle, from Alan:** more good user experience, not more accessibility or usability checklists. Judge every change by how the app feels to use in the real browser, not by whether a test passes.

## When it can start

- **BL-145 (`fix-chat-box`, worktree `../creaite-chat-box`) merges first.** It holds the chat box's auto-grow and `dev/tests/test_chat_box.py`; BL-146 builds its shared helper from that code, so there must be only one. If it has not merged, ask Alan.
- Nothing else is in flight (`dev/archive/sprints/STATUS.md`). Bring `main` in before starting and before the merge.
- Everything is in `system/templates/dashboard.html` apart from the few server routes in BL-149 and the docs. It is one big file: commit each item separately and keep each item's code in its own marked block (`/* ===== BL-1xx (sprint-ux) ===== */`).

## Order

Two stages. **Stage A can merge on its own.**

### Stage A: the gaps that are small and visible

1. **BL-146** one shared auto-grow helper, applied to every `textarea` (start from BL-145's; do not write a second).
2. **BL-147** one date parser behind every date field; the field shows what it understood.
3. **BL-148** copy a reply, ↑ recall, edit and resend, try again, the draft kept across a reload.
4. **BL-150** the panel makes room (1100px and over); nothing under the panel at any width.
5. **BL-151** Today's no-calendar band becomes one line with Refresh calendar.
6. **BL-152** the tab title.
7. **BL-153** *investigate first*: why Work opens on Overdue in a fresh browser; fix or explain on the page.

### Stage B: the larger ones and the baseline

8. **BL-149** no dead ends into Claude Code: reminder buttons; Approve on a draft in Review; Keep current / Use this one on a conflict; list any others found. Look first at what `review.py` and the live server already expose; call `review.py` rather than re-implementing approval. **Alan's click is the approval; the bulk rule and Undo are unchanged; nothing writes unattended.**
9. **BL-154** the edit panel: the fields that matter first, the rest under More fields.
10. **BL-155** the Keys chip replaces the permanent hint line.
11. **BL-156** first-run checklist on Today; Help and the first-day guide offer the launcher first.
12. **BL-157** write "UX baseline" into `dev/BUILD.md`, then run the one-off sweep of every page against it (the browser tool in `dev/tools/cdp.py`; screenshots at 1400px and 1100px, panel open and closed). Fix what takes under an hour; write the rest as BL-162 onwards (BL-158 to BL-161 are sprint-icons).

## Rules for this sprint

- **Look at it.** For each item, open the real dashboard in the browser (`dev/tests/live_browser.py` shows how: a throwaway vault and the live server) and look at the result at 1400px and 1100px, in light and dark and in at least two themes, before saying it is done. Put the screenshots' paths in the report.
- **Defaults (accepted by Alan, 10-10-2026)** where an item leaves a choice: 60% of the window height as the auto-grow cap; Monday as "next week"; "fri" means the next Friday, today included only when asked for as "today"; a day-and-month with no year means this year, or next year if a due date would be in the past.
- **Do not change:** the record's rules (approval before writes, one writer, source on every row), British English, DD-MM-YYYY shown and YYYY-MM-DD stored, the page's existing colour, type and spacing tokens, reduced motion (BL-136: new motion follows the existing tokens and stops under reduced motion).
- **Files other sprints own:** none are in flight. `live_server.py` and `review.py` change only in BL-149 and only as routes or small callable functions.
- **Help and the guides:** `system/templates/help.md` changes where a behaviour it describes changes (dates in plain words, the Keys chip, the launcher first); run `python3 dev/tools/build_guides.py` (a test fails while the guides are out of date).

## Tests

Per `dev/archive/sprints/STATUS.md`: the sprint runs **its own tests**, not the whole suite; one full suite runs on the final `main` before a release. Real-browser tests use `LiveBrowserCase`.

- `test_autosize_fields` (BL-146): the edit panel's Action and Latest update, Quick Capture and Steer it grow at three, six and thirty lines, stop at the cap with an inner scroll, shrink back, and are right after a paste and when a record is opened.
- `test_plain_dates` (BL-147): the parser against a fixed "today" (every form in the item, and the ones that must be refused), and one field in the browser showing "Friday 16-10-2026".
- `test_chat_conveniences` (BL-148): Copy on a reply, ↑ and ↓ recall, edit and resend, try again after Stop, a draft back after a reload.
- `test_panel_room` (BL-150): with the panel open at 1400px and at 1100px, no element in the main area has its right edge beyond the panel's left edge, on Intake and on Work.
- `test_today_brief` (BL-151) and a title test (BL-152); a fresh-profile test for BL-153.
- BL-149: one test each for the reminder button, Approve on a draft (and that Approve routine still skips minutes) and a conflict's two buttons.
- BL-154, BL-155, BL-156: one test each; update any test that looks for the old hint line or the old field order.
- Existing files to re-run: `test_chat_box`, `test_today_brief`, `test_dashboard_editing`, `test_cell_edit`, `test_work_filters_live`, `test_review_triage`, the help and guides test.

## Report

When done, say for each BL number what was done, what default was taken, and which of the ten UX baseline checks (BL-157) it passed, with the screenshot paths. Add the FR text for `dev/BRD.md` (do not edit the BRD until the merge), the release-notes lines for 1.3.0, and the hand checks for Alan (what to try in the live app). Do not push. Do not bump `VERSION` (it is already 1.3.0).
