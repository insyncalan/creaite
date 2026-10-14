# Sprint all-items: an All items tab across Actions, RAID and Decisions (BL-134), and the People page's two tabs (BL-138)

Branch `sprint-all-items`, worktree `../creaite-all-items`, from `main` **after `sprint-work-views` has merged** (and so after `sprint-polish` and `sprint-settings`). One main item (BL-134) in three stages, then one small second item (BL-138, the People tabs, added 10-10-2026 because it is dashboard-only like this sprint and nothing else in flight owns the People view). Rough size: five to seven days.

**The design is frame 7 of `dev/mockups/work-filtering-mockup.html`.** Open it first, with frames 1 to 3 (the Display menu, the field picker and the grouped list) beside it, because this tab is those components pointed at a merged list. Then read **BL-134 in `dev/BACKLOG.md`**, and BL-128 to BL-132 for what `sprint-work-views` built. Where the backlog says "to confirm", take the default in "Decisions taken" below and note it in BUILD. Alan confirmed on 10-10-2026 that this is wanted, as its own sprint; he has not yet answered the open questions, so those defaults are mine.

## Before starting

1. `git worktree list` shows `sprint-polish`, `sprint-settings` and `sprint-work-views` gone, and `git log main` has all three. If any is not merged, stop and say so.
2. Bring `main` in. Read what `sprint-work-views` actually built: the Display menu, grouping, the field picker, the saved views and the empty state. This tab uses them; it must not copy them.
3. **Find every place that assumes three tabs.** The Work code picks its list with ternaries such as `items()` (`WT==="actions"?A:WT==="raid"?R:DEC`), where an unknown tab silently falls through to Decisions. Run `grep -n 'WT===\|FDEFS\|COLS\[\|COLVIS\|DEFSORT\|SORTKEY\|TABSTATE\|WINIT\|WLAY\|WGRP\|SAVED\[' system/templates/dashboard.html` and list each one in BUILD with what it does for `all`. A missed ternary is the main risk in this sprint.
4. Run `test_work_board.py`, `test_work_filters_live.py`, `test_decisions_board.py`, `test_dashboard_editing.py` and the Work-views tests first, to know what passes.

## The build, in order

Commit each stage separately.

### 1. The merged read model (S–M)

One function returns the rows of All items from `A`, `R` and `DEC`, each row carrying `k` (its table: `actions`, `raid`, `decisions`), `type` (the one list: **Action, Decision, Risk, Issue, Assumption, Dependency**), and the shared fields:

| Shared field | Action | RAID item | Decision |
|---|---|---|---|
| Item | the action text | the risk or issue text | the decision text |
| Type | Action | its type | Decision |
| Owner | owner | owner | **Made by** (who is asked, or who made it) |
| Due | due date | due date | **Needed by**; a made decision shows its **Date**, not a due date |
| Priority | priority | priority (from impact and likelihood) | none (blank, sorted last) |
| Status | Open, Delayed, Closed, Cancelled | Open, Closed, Cancelled | Pending, Made, Withdrawn |
| Project, workstream, source, last updated | as the row | as the row | project, source, last updated (no workstream) |

- **One status filter, three native values:** the filter offers **Open** (Open, Delayed, Pending), **Closed** (Closed, Made) and **Cancelled** (Cancelled, Withdrawn); each row's cell still shows its own word. Counts per option as everywhere.
- **Default order:** overdue first, then due soonest, undated last; a made decision sorts by its date.
- **IDs are unique across types**, so a row is `k` plus `id`; every handler reads `k` from the row, never from the tab.
- Tests: the merged list has every item once, with the right shared fields for each type; the status buckets; a decision's owner and due mapping; the default order.

### 2. The tab (M)

A fourth tab **All items** after Decisions, using BL-128 to BL-132's components (not copies).
- **The list only.** No Board (columns of mixed statuses would mean little); the layout switch is hidden on this tab. **Display:** group by Project (default none), Type, Owner, Due, Status, Priority; order by; properties (ID, Type, Owner, Due, Priority, Status, Project, Workstream, Source, Last updated).
- **Filters** by the field picker: Status (the three buckets), Due, Owner, Project, Priority and **Type** (new: the six values), plus Stale, Last updated and Raised from BL-130. Fields that exist on only some types (Workstream, Response, Milestone) are not offered here.
- **Saved views and presets:** All open, Mine, Due soon, Overdue, **Chase**, Closed; saved views for this tab are kept with the others (`work.saved_views`, a fourth list). The default view is All open.
- **Selecting and opening:** a click highlights, the ID or a double-click opens the item's **own panel** (`openRecord(k, id)`), as BL-122 does. **Read-only:** no cell editing (BL-123) and no bulk bar (BL-124); the bar appears only on the three typed tabs. Hovering a cell says "Edit it on the Actions tab" (or RAID or Decisions).
- **The address:** `#work` with a tab key for All items, kept in step with the other tabs; Back, Forward and saved addresses work; every existing address is unchanged.
- **The empty state, the count line and "Chase"** work as BL-132 and BL-131 describe.
- Tests: every Work test for the three tabs still passes; the new tab's filters, grouping, display and saved views; a row opens the right panel for each type; no edit or bulk controls; the address round-trips; a keyboard path; the layout switch is hidden.

### 3. Links in (S)

- The project page's "All N …" links and Today's links into Work stay as they are. Add one **"All items"** link on the project page's work card that opens All items filtered to the project and open.
- ask creaite and search are unchanged.
- Tests: the new link opens the tab with the project filter.

### 4. BL-138: People, two tabs (S)

Read **BL-138 in `dev/BACKLOG.md`** first. It is separate from the Work page, so it is built last and can be merged on its own if the All items work is held up.

- `PERS` and `renderPeople` in `dashboard.html` split the People view into two tabs. **"With work"** (first and default): a person with at least one open action, one open risk or issue, or one *Decision needed* waiting on them; the existing columns plus **decisions waiting**; "You" stays at the top. **"Nothing assigned"**: the people creaite knows (register, attendees, mail, Teams, reports) with nothing open, including those whose items are all closed; columns name, organisation, role, the projects they appear in, closed items (a count) and a "not in register" tag; an empty tab says everyone has something assigned.
- Tab counts ("With work 12", "Nothing assigned 13"). Nobody is on both; hidden people are on neither. Sorting works on each tab. The chosen tab is remembered in this browser and kept in the address (`#people/none`); a plain link to People opens the first tab.
- Counts only: no scores, ratings or on-time percentages (BL-56). Opening a person, Edit details, Merge and Hide are unchanged; no new controls.
- Tests (`test_people_dashboard.py`): an open action, open RAID item or waiting decision puts a person on tab 1 with the right counts; only closed items, or only the register, puts them on tab 2; a made decision alone does not count; hidden people are on neither; the tab survives reload and the address; "You" stays first; closing someone's last item moves them.
- Help (the People section) and `dev/dashboard-spec.md`.

## Decisions taken (defaults; Alan has not answered these yet)

| Question | Default |
|---|---|
| Are promises (BL-125 A) a type here? | Not yet; they aren't built. The Type list is built from one place so a seventh value is a small change later |
| A decision's owner and due | Owner is Made by; due is Needed by, and a made decision shows its Date |
| One status filter | Three buckets (Open, Closed, Cancelled), native words in each cell |
| A Board on All items | No; the list only |
| Editing here | Read-only; the panel opens for the item's own type |
| A preset order | As on the Actions tab, with Chase |
| Does Today or the project page already answer it? | No: that was the case for building it. Judge on use after release |
| BL-138: does a made decision make someone "assigned"? | No; only a decision waiting on them (a *Decision needed*). Made decisions are history |
| BL-138: where is assigning done from tab 2? | On the person's page, as now; no new controls on the list |

## Boundaries

- **Owns:** the Work parts of `dashboard.html` (the tab list, `items()` and the code that branches on `WT`), and (item 4) the People view (`PERS`, `renderPeople`, its tab bar and the `#people` address), plus tests. Nothing else is in flight on them once `sprint-work-views` has merged; `sprint-motion` waits for this sprint too, so tell Alan if it has started.
- **No engine, schema or apply-path change.** The dashboard, Help, the spec and tests only.
- **Shared files** (`dashboard.html`, `help.md`, `dev/dashboard-spec.md`): new code in marked sections (`/* ===== BL-134 (sprint-all-items) ===== */`); don't reformat unrelated lines.
- **Don't touch `dev/BACKLOG.md` or `dev/BRD.md`;** they are updated at merge. Write the FR text you'd add in BUILD (it extends FR-44 and FR-89).
- **Help:** update `help.md`, then run `python3 dev/tools/build_guides.py`.
- **Colour is never the only cue** (the Type tag carries its word; the "not in register" tag its words); check each theme in light and dark.
- **Tests start from your own settings:** run them in the worktree, which has the committed `settings.json`.
- **Stop a test run by its process tree,** never with `pkill` by name.
- **Development guard:** sample data only; test with temporary vaults.

## Done when

- **Tests:** as listed per stage, and the existing Work tests still pass.
- **The full suite passes once** on the final branch, after `main` is brought in: `python3 dev/tools/run_tests.py -j 4`.
- **Docs:** `dev/dashboard-spec.md`, Help and the guides, a "Sprint all-items" section in `dev/BUILD.md`, including the list of every place that assumed three tabs and what each now does.
- **Alan sees it:** before asking to merge, walk the new tab against frame 7 and list any difference.
- **Commits:** each stage committed separately on `sprint-all-items`, with the attribution lines from the session's instructions. Never push or merge into `main`.
