# Sprint work-views: the Work page's display, grouping, filters, saved views and empty state, and Review's triage (BL-128 to BL-133, with BL-133's stage B)

Branch `sprint-work-views`, worktree `../creaite-work-views`, from `main` **after `sprint-polish` and `sprint-settings` have both merged**. One sprint, built in the order below, because every item reshapes the same Work-page functions in `dashboard.html` (`renderWork`, `renderApplied`, the filter and board code). Rough size: ten to fourteen days. If that is too long for one sprint, item 6 (Review) can split off as its own sprint once items 1 to 3 have merged, because it reuses their components and touches a different part of `dashboard.html`.

**The designs are `dev/mockups/work-filtering-mockup.html` (seven frames, items 1 to 5) and `dev/mockups/review-triage-mockup.html` (eight frames, item 6), each with notes.** Open them first. Then read BL-128 to BL-133 in `dev/BACKLOG.md` (and BL-134 for what is *not* in this sprint), and BL-114, BL-122, BL-123 and BL-124 for what `sprint-polish` built under it. They hold Alan's decisions; where one says "to confirm", take the default in "Decisions taken" below (Alan agreed that table on 09-10-2026) and note it in BUILD.

**Out of this sprint:** BL-134 (the All items tab), which has its own sprint, `sprint-all-items` (`all-items.md`), after this one is an option Alan hasn't confirmed. Don't build it. BL-125 (promises, links, labels) is separate; leave hooks only where this brief says.

## Before starting

1. `git worktree list` shows `sprint-polish` and `sprint-settings` gone, and `git log main` has both. If either is not merged, stop and say so.
2. Bring `main` in. Read what `sprint-polish` actually built for BL-114 and BL-122 to BL-124 (the selection model, the cell editor, the bulk bar, the hint lines) and build on it. Where it differs from the backlog text, the code wins; say so in BUILD.
3. Read the Settings page (BL-115) to find where the Work defaults live now (`work.board.group.*`, the default status filters).
4. Run `test_work_board.py`, `test_work_filters_live.py` and `test_decisions_board.py` before changing anything, to know what passes.

## Items

Commit each separately, in this order.

### 1. BL-128: one Display menu (M–L)

The popover in the mock-up's frame 2: Layout, Group by, Sub-group (the control only; BL-129 makes it work), Order by with a reverse button, Properties, Show. Replaces the List | Board switch's neighbours (Group by, Sort, Hide empty columns, Columns). The switch itself stays.
- Properties are the editable columns, **Milestone** included (BL-123 edits it; no column showed it). The Board card shows at most four.
- **Show** has *Empty groups* on both layouts and the Closed column's window on the Board only. The List has no Closed toggle: the Status filter decides.
- `D` opens Display. One function builds each layout's key-hint line, so it can't drift from the controls that exist.
- Saved views keep layout, group, order (sub-group arrives with item 2).
- Tests: each tab and layout shows only its own options; changes update the list, board and address; reset restores the tab's default; focus returns to the button on close; keyboard and screen-reader operation.

### 2. BL-129: group by in the List, sub-groups and swimlanes (M–L)

Collapsible group headers on the List with counts and the overdue count; one sub-group level; swimlanes on the Board (frames 1 and 4).
- **Selection with groups** is the part most likely to go wrong: follow BL-129's rules exactly (a range never reaches collapsed rows; the header tick; "Select all N matching" is the one explicit exception and states N including collapsed groups; J and K step over headers; Shift on the Board follows J and K order).
- A cross-lane **and** cross-column move shows both changes in the move dialog and saves one proposal with one Undo. Move to… offers column and lane as two steps.
- **Decisions keep FR-110's rules** per column; a lane move reassigns who is asked.
- Applies to Work and Mine. A person's page and the project page are not changed.
- Tests: each grouping on each tab with right counts; collapse remembered; a Shift range skipping a collapsed group; select-all-matching message; sub-group on both layouts; a cross-lane move on Actions and on Decisions; keyboard path to every lane; filters, search and saved views still apply.

### 3. BL-130: field picker, "is not", new fields (M)

Frame 3. A searchable field picker (`F`), is / is not on every field (stored with a `!` prefix so old views and addresses load unchanged), and the new fields: **Stale**, **Last updated**, **Raised**, **Milestone** on Actions and RAID, per BL-130's table. Label and Blocked arrive with BL-125; leave the picker able to take them.
- The chip for an exclusion is tinted and says "not".
- Today and project-page links into Work (`openWork`, the `dueor` and `undated` views, a project's open items) keep working untouched.
- **Data:** `upd_at` and `raised` already reach the page. If **stale for Decisions** needs a field `build_dashboard.py` doesn't export, add it and note it in the release notes.
- Tests: is and is not on every field of every tab; an exclusion saves and restores in a view and the address; an old saved view and an old address load unchanged; each new field filters correctly; counts and the "Result" line; the picker's search and `F`; keyboard and screen-reader operation.

### 4. BL-132: the empty state and the hidden count (S)

Frame 6. Names the filters, counts what removing each alone would show, one-click Remove, Include closed items, Clear all filters. The count line says what the Status filter (List) or the Closed window (Board) hides. A polite live region announces the count and the empty state (WCAG 4.1.3); check what exists first.
- Tests: zero results with one, two and three filters give the right counts; Remove restores items; the count line is right on both layouts; the announcement fires.

### 5. BL-131: saved views (M)

Frame 1's chip row. The unsaved dot, **Update view** and **Save as new view** (presets can only be saved as new), rename, reorder, delete in the chip's menu, **More views (n)** overflow that keeps the active view visible, a default view per tab (the control on the Settings page), and the new built-in view **Chase** on every tab. Saved views keep layout, group, sub-group and order.
- **Chase:** open (Pending for Decisions), owned by someone else, and stale. RAID keeps "No response yet". "Overdue" moves under More views on Actions.
- Last, because it saves everything the earlier items add.
- Tests: change a saved view and the dot shows; Update and Save as new each behave; a preset can't be overwritten; rename, reorder and the default survive a reload; overflow keeps the active view in sight; Chase returns the right items on each tab.

### 6. BL-133 stage A: Review triage and mass change (M–L)

The Review pane, using the components built in items 1 to 5. **The design is `dev/mockups/review-triage-mockup.html`** (frames 1 to 6 and 8 are stage A, 7 is stage B, item 7). Read BL-133 in full first; the build is its "Stage A" list. The pieces, in the order to build them:
1. **Concurrency first.** Bulk decisions are written one proposal file at a time and applied once. Write the failing test (twelve approvals across three files, none lost) before changing anything, to learn whether the current loop loses any.
2. **The selection and the Review bar:** header ticks per project, Select all N, the bar with its count and the "can be approved together" split, Approve and Reject on what the bulk rule allows, the summary that names what was left out with **Show them** and one **Undo**. The bulk rule does not change; test every excluded kind.
3. **Mass change before approval:** Set project, owner, due date, workstream, milestone on the selected proposals (through `editProposal`, tagged edited, validated per item, refusals listed). One signal offered per distinct sender after a bulk project choice.
4. **Filters, sort and grouping** with BL-130's picker and BL-128's Display menu; **stale** shown (`build_dashboard.review_queue` adds the age) with its filter.
5. **Approve all routine** scoped to what the filters show, with the preview and the over-25 prompt.
6. **Auto-advance** with its Review setting (on by default), the empty-queue summary, **Open source** where one exists, `Cmd/Ctrl+Z`.
- BL-122 built Review's click-to-highlight; keep its clicks exactly as they are and build on its selection.
- **Leave out the reason menu here:** Reject is a plain button (no arrow) and `Shift+R` and its hint are not added; item 7 adds them. Frames 2 and 7 of the mock-up show them.
- Tests: those listed under BL-133's "Touches"; `test_review_nesting.py` and `test_minutes_review.py` still pass.

### 7. BL-133 stage B: reject reasons and duplicate hints (M)

The one item in this sprint with a **schema change**, so it follows the change control in `dev/BUILD.md` and is built last, on a tree where everything else passes. Read BL-133's "Stage B" in full; the design is the Review mock-up's frame 7.
1. **Stop and show Alan the DDL first.** Two nullable columns, `rejected.reason TEXT` and `rejected.duplicate_of TEXT`. Wait for his yes before writing `schema.sql`, as Sprint 5 did.
2. **Then, together:** `schema.sql`; `tracker.py` (apply writes the two columns from `reject_reason` and `duplicate_of` on a rejected item; undo removes the row as it does now; a migration adds the columns to an existing database, following how `migrate_workstreams` runs); `excel_sync.py` (check; no sheet exports `rejected`, say so in BUILD); `tracker-conventions.md`; `dev/staging-format.md`; `dev/BUILD.md`.
3. **The reason and the link in the page and the server:** the Reject arrow and `Shift+R` (single item and the Review bar), the reason in Activity, `live_server.py` carrying a reason on the review decision, `review.py` and cx-review taking "reject 4 as a duplicate of ABC-A-009".
4. **The duplicate hint:** a deterministic match in `build_dashboard.review_queue` (open items, same project and type, token overlap at or above `review.duplicate_overlap`, default 0.6; add the setting to `settings-defaults.json`, and to the Settings page's Review section built by BL-115), shown on the row and in the panel, with **Reject as duplicate of ABC-A-009**.
5. **Extraction reads the reasons:** the cx-minutes and cx-sweep "never re-propose" steps also read the project's recent reasons (`tracker.py read` on `rejected`) as guidance. Nothing automatic beyond the fingerprint.
- **Engine change, ships in a release:** a line in the release notes naming the migration; `update.py` runs it on an existing vault, and `doctor.py` checks the columns.
- Tests: those listed under BL-133's "Touches (stage B)". The migration test starts from a **copy of a database made before this change** and checks every row survives, the columns exist and an apply, an undo and a re-apply all behave.

## Decisions taken (defaults; Alan agreed this table on 09-10-2026)

| Question | Default |
|---|---|
| A row that no longer matches the view after an edit | It leaves at once, the message says so, Undo returns it. A row that changes group moves and keeps its highlight |
| Collapsing a group that holds highlighted rows | Those rows leave the highlight; the bar says how many |
| Key for Display | `D` |
| "Overdue" on Actions | Moves under More views, so the chip row fits |
| Default view setting | Replaces the two default status filters; Decisions gains one |
| Stale for a Decision | Days since its last change, else since its date |
| One sub-group level | Yes; never more |
| Display's properties on a card | At most four |
| Bulk reject in Review | May include items that need individual approval (rejecting writes nothing to the tracker); minutes and reports are still rejected one at a time |
| Auto-advance in Review | On by default, a Review setting turns it off |
| Preview before bulk approve | For "Approve all routine" and any batch over about 25; smaller batches apply and offer Undo |
| Saved Review views | Not built; revisit if the filters are used a lot |
| What a reject reason does | Stored, shown in Activity and given to extraction as guidance; the fingerprint stays the only automatic block |
| Duplicate match | Same project, same type, open items, token overlap at or above 0.6 (`review.duplicate_overlap`) |

## Boundaries

- **Owns:** the Work and Mine parts of `dashboard.html`, and (item 6) its Review part (`renderReview`, `revRow`, `decide`, the bulk handlers and the Review toolbar) (`renderWork`, `renderApplied`, `renderFilterBar`, `drawMore`, `renderLayoutBar`, the board code, `PRESETS`, the saved-view code), and their tests. `sprint-polish` (which also builds Review's click-to-highlight, BL-122) and `sprint-settings` have merged, so nothing else is in flight on them; if another sprint has started on the Work page by then, ask before editing.
- **Don't change** what is saved, applied or proposed, **except item 7**: it adds two nullable columns to `rejected` and the code that writes and migrates them. Nothing else changes in the schema, `tracker.py`, `propose.py` or the apply path. Edits and moves go through the existing save path, one proposal and one Undo each.
- **Shared files** (`dashboard.html`, `help.md`, `dev/dashboard-spec.md`, `build_dashboard.py`): new code in marked sections (`/* ===== BL-128 (sprint-work-views) ===== */`, and so on); don't reformat unrelated lines.
- **Engine changes ship in a release:** `build_dashboard.py` (items 3 and 6: the stale field and the proposal's age; item 7: the duplicate hint) and item 7's schema, `tracker.py`, `live_server.py`, `review.py`, `doctor.py`, `update.py` and skills. A line for each in the release notes, naming the migration. Add a line to `dev/release-notes/` for the next version (use whichever file `sprint-polish` created; don't change `VERSION`).
- **Don't touch `dev/BACKLOG.md` or `dev/BRD.md`;** they are updated at merge. Write the FR text you'd add in BUILD: BL-128 to BL-132 extend FR-44, FR-89 and FR-110, and need one new requirement for Display, grouping and the empty state; BL-133 stage A extends FR-43 and FR-59, and stage B needs its own requirement.
- **Help:** update `help.md`, then run `python3 dev/tools/build_guides.py`.
- **Colour is never the only cue** (the "not" chip, the unsaved dot, the highlight); check each in all seven themes and in light and dark.
- **Tests start from your own settings:** run them in the worktree, which has the committed `settings.json`, not the main folder's.
- **Stop a test run by its process tree,** never with `pkill` by name.
- **Development guard:** sample data only; test with temporary vaults.

## Done when

- **Tests:** as listed per item, plus each item's "Touches" tests in the backlog, and `test_work_board.py`, `test_work_filters_live.py`, `test_decisions_board.py` `test_dashboard_editing.py`, `test_review_nesting.py`, `test_minutes_review.py` and `test_propose.py` still pass.
- **The full suite passes once** on the final branch, after `main` is brought in: `python3 dev/tools/run_tests.py -j 4`.
- **Docs:** `dev/dashboard-spec.md`, Help and the guides, a "Sprint work-views" section in `dev/BUILD.md`.
- **Alan sees it:** before asking to merge, walk Actions, RAID and Decisions in both layouts against the mock-up's frames, and walk Review with a mixed queue (unmatched, individual-approval, conflict and routine items) and list any difference. Walk Review against the Review mock-up's frames 1 to 8.
- **Commits:** each item committed separately on `sprint-work-views`, with the attribution lines from the session's instructions. Never push or merge into `main`.
