# Sprint: Person rows (BL-68)

Branch `sprint-person-rows`, worktree `../creaite-person-rows`. Runs in parallel with `sprint-prep-updates` (BL-65) and `sprint-meetings` (BL-42 phase 2). Read BL-68 in `dev/BACKLOG.md` first; it holds Alan's decisions.

**Merge order:** this sprint merges **last**, because its change to Work's shared row code is the most likely to clash.

## Goal

A person's page shows their open actions and risks and issues in the same detail and layout as the Work lists, grouped by project, from the same code, so the two can't drift apart.

## Items

Commit each separately.

### 1. One row renderer for Work and other pages

- **The change:**
  - `rows()`, `cell()` and `orderedCols()` in `dashboard.html` read the Work tab's global (`WT`) today. Give them the item type as a parameter (`cell(k, x, t)`, `orderedCols(t)`, and a row-list function that takes a type and a list).
  - Work keeps calling them with `WT`.
- **Must not change:**
  - Work's behaviour and look: columns, order, widths, sorting, edit in cell, keyboard shortcuts, selection, the side panel;
  - the existing Work tests, which must pass unchanged;
  - existing lines' format, so only the signatures and the `WT` reads change.

### 2. The person page uses it

- **Open work:** grouped by project, with a heading for each (code and name). Under it, an **Actions** table and a **Risks and issues** table drawn by the shared renderer, each with its own heading row.
  - **No Owner column:** it's the person on every row. The project line stays under each title.
  - **Columns:** follow Work's column choice, order and widths for that type (shared with Work, remembered).
  - **Sorting:** by clicking a heading, as in Work. The default is overdue first, then by due date.
  - **Rows:** open the same side panel. Edit in cell and the keyboard shortcuts work as in Work. Early-warning flags (BL-51) show as in Work.
- **Decisions made in the last 14 days:** use the Decisions table's row (decision, made by, date, source).
- **"See all in Work":** for actions and for RAID, opens Work filtered to this owner (the Owner filter from BL-45), so the full controls are available.
- **Handover must keep working:** the "Hand over" mode (BL-56 phase 2: `HAND`, `#ppHand` and the wrapper around `renderPerson`) selects rows on this page. Its tick boxes become the shared renderer's selection column, or sit beside it.
- **Unchanged:** "My work" and the project page's cards stay short, as BL-68 says.

## Boundaries

- **Owns:**
  - in `dashboard.html`: Work's row code (`rows()`, `cell()`, `orderedCols()` and their helpers), `renderPerson`, and the handover wrapper;
  - the people dashboard tests.
- **Don't edit:**
  - **`sprint-meetings` owns:** the Inbox view, `sweep.py`, `build_dashboard.py`'s `meetings` data.
  - **`sprint-prep-updates` owns:** `minutes.py`, `review.py`, Review rendering, the cx-minutes skill.

  Note anything needed there under "Hand-offs".
- **Shared files** (`dashboard.html`, `help.md`, `dev/dashboard-spec.md`):
  - put new person-page code in its own marked section, `/* ===== Person rows (BL-68) ===== */`;
  - for the shared renderer, change the existing functions in place but don't move or reformat them, so the merge stays readable;
  - leave `BACKLOG.md` and `BRD.md` alone: they are updated at merge.
- **Development guard:** sample data only; test with temporary vaults.

## Done when

**Tests:**
- every existing Work test passes unchanged;
- in headless Chrome, a person page shows:
  - the Work rows grouped by project, with no Owner column;
  - Work's column choice applied;
  - sorting by a heading;
  - a row opening the side panel;
  - edit in cell saving a proposal;
  - "See all in Work" opening Work filtered to that owner;
  - handover still selecting and reassigning rows, with undo;
  - recent decisions as Decisions rows.

The full suite passes: `python3 dev/tools/run_tests.py`.

**Docs:** Help and `dev/dashboard-spec.md` updated, and a short "Person rows" section added to `dev/BUILD.md`.

**Commits:** each item committed separately on `sprint-person-rows`, with the attribution lines from the session's instructions. Never push or merge.

## Hand-offs

(Changes needed in files another sprint owns.)
