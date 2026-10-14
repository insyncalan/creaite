# Sprint review-work: project changes in Review, the peek follows a click, and a right-click menu (BL-200, BL-198, BL-197)

Branch `sprint-review-work`, worktree `../creaite-review-work`, from `main` after v1.5.1. **For v1.6.0**; `VERSION` changes only at the release. It runs beside `sprint-chat-text` (ask creaite's box and messages, and markdown rendering). That sprint owns those parts; this one owns Review's project changes, the row click handlers and the new context menu. Both change `live_server.py`, in different functions: put new code in marked blocks. Read BL-200, BL-198 and BL-197 in `dev/BACKLOG.md` first. They hold Alan's decisions; BL-200's open questions are settled.

## Order: one commit per item, each in a marked block (`/* ===== BL-1xx (sprint-review-work) ===== */`)

1. **BL-200 (Alan's priority): change the project in Review,** for one item or for a whole set of minutes (moving every item in them), exactly as BL-200 sets out. Read `review.py`'s `cmd_assign`, the meeting block (`meeting.projects`, `file_ops`) and the dashboard's Review panel first.
2. **BL-198: with the peek open, a single click on another work item shows it in the peek** (Work, Review, the person page, the board), as BL-198 sets out. With no peek open, a click still only highlights.
3. **BL-197: right-click a work item for a menu of its common actions,** as BL-197 sets out.
   - **The menu is a component** with per-kind action lists, wired to the existing save paths (the peek, the cell editor, BL-124's bulk bar). Nothing that deletes.
   - **Several highlighted rows:** the menu acts on all of them and offers only what applies to every one.
   - **Keyboard:** Shift+F10 and the context-menu key open it.
   - **Outside items:** the browser's own menu still appears (as on the rail, BL-191).
4. **Docs:** Help and the guides, `dev/dashboard-spec.md`, a BUILD "Sprint review-work" section with the FR text, and `dev/release-notes/1.6.0.md` (create it with a "# creaite 1.6.0 (Beta)" heading and a draft line, or add to it if `sprint-chat-text` created it first).

## Rules

- **The record's rules stand:** approval before writes, `tracker.py` the only writer, bulk approval's exclusions unchanged (minutes, new decisions, new risks). No schema change.
- **Look at it** in the real browser (`dev/tests/live_browser.py`, `dev/tools/cdp.py`) at 1400px and 1100px, chat and peek open and closed, light and dark, in two themes. Keep the screenshots.
- **Tests:**
  - each item's "Touches" list;
  - then every test file that mentions Review, the peek, `hlRow`, `openProposal` or `review.py`, not a sample.

  One pass is enough; a file that fails under load and passes alone counts. Tests also run on GitHub's Linux runner: wait for conditions, and don't rely on hover or a native list's keys. Stop runs by their own process tree only; never `pkill` by name.
- **The usual edit rule:** don't edit `dev/BACKLOG.md`, `dev/BRD.md` or `dev/sprints/STATUS.md`. Never push or merge.
