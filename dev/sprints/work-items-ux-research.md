# Work items and the peek: UX research and recommendations

Date: 19-10-2026 · Branch read: `pm-intake-briefs` · Scope: the Work page (Actions, RAID, Decisions, All items) and the work-item peek · Desktop and 900 px only.

## 1. Verdict

- **What already works:** the engine is first rate. Combined filters with counts and "is not", saved views that keep layout, group and order, a Linear-style Display menu, list and board, inline cell edits, Shift/Cmd range selection with a bulk bar and one Undo, J/K that the peek follows, optimistic saves, good empty states that suggest which filter to relax. Few products give one user this much control.
- **The problem is the surface, not the plumbing.** Four rows of chrome sit above the first item and say the same thing three times ("Status: Open" button, "All open" pill, "Status: Open" chip). Rows are 57 px, two lines, all words and dotted underlines, and the list does not use the status and priority marks the peek already draws.
- **Opportunity 1: a calmer, glanceable row.** One mark for status, one for priority, a single line, the overdue state carried by the due date. Reuse the peek's own marks.
- **Opportunity 2: say it once.** Fold views, filters and chips into two rows of chrome, and give Actions a default grouping by when things are due, so the list reads as a plan rather than a table.
- **Opportunity 3: a peek that leads with what matters.** A smaller title, a property list rather than four cramped columns, the source and the client-visible flag in the header, and one quiet timeline instead of four tabs.

## 2. Current state in brief

**Layout** (`system/templates/dashboard/shell.html` lines 68 to 87; `dev/design-system/shots/work-light.png`, `work-900-light.png`)
- `h1` Work, then tabs (Actions, RAID, Decisions, All items), then the toolbar: search, five filter buttons (Status, Due, Owner, Project, Priority), the funnel (+ Filter), List/Board switch, Display, New.
- Then a row of view pills (All open, Mine, Due soon, Chase, Delayed, Closed, More views), then a row of applied-filter chips with "Clear all" and "Showing 3 of 3". About 170 px of controls before the first row at 1400 px.
- Table rows are 49 to 59 px (DESIGN-SYSTEM.md section 5). The title cell holds a checkbox-style kind icon, the title, then a sub-line with the ID (dotted underline) and the project. Owner (dotted underline), Due (date plus "3 days late"), Priority as a word (Urgent in red), Status as a word.

**Behaviour** (`system/templates/dashboard/src/work.js`)
- Filters: `FDEFS` (lines 48 to 62), "is not" through `NEG`, date ranges for due, raised and closed. Views: `PRESETS` (line 82) plus saved views written to settings.
- Default order: actions overdue first, then soonest due; RAID by priority; decisions pending first (`DEFSORT`, line 75). The list has no grouping by default (`WLGRP`, "none"); the board groups actions by due bucket (`BDEFG`, line 317).
- Display menu (lines 484 to 520): group, sub-group, order with reverse, properties (columns), empty groups, reset. Key `D`.
- Selection (lines 821 to 872): click highlights, Cmd/Shift extend, J/K move, Space toggles, Enter or the ID opens, Esc clears. Bulk bar (lines 964 to 1031): Close, Reopen, status, owner, due, priority, workstream, milestone, "Select all n matching", Draft updates.
- Inline edit (lines 889 to 963): a ▾ on each editable cell opens a list or calendar in place; one proposal, Undo.
- No single-key property changes on the cursor row and no right-click menu on rows.

**The peek** (`src/components/Peek.jsx`, `src/components/peek/PeekProps.jsx`, `src/panel.js` lines 354 to 760; `dev/design-system/components/peek-panel-light.png`)
- An overlay on the right, `min(max(520px,50vw), …)` wide (`style.css` line 1828), not modal, closes on click outside or Esc, expands to full width, steps with J/K or the arrows, copies a link.
- Header: ID · project (and RAID type). Title is an inline editor in the display font at a large size. A row of four property chips (status ring, priority bars, owner initials, due date) separated by vertical rules. Then the free-text field (Latest update, Response or Reasoning) with a Draft button, "Last updated", a collapsed **Details** (project, workstream, milestone, raised, closed, client-visible, client messaging), and a feed with four tabs: All, Activity, Updates, Source. The source sits at the bottom of the feed. Sneak peek ("// Change this item in words") sits at the foot.

## 3. What the best do

| Theme | What they do | Takeaway for creaite | Source |
|---|---|---|---|
| Row anatomy | Linear draws one small status mark and one priority mark per row, then the ID and title on a single line; status glyphs fill as work progresses; priority is signal bars, Urgent a filled badge | Marks, not words, for the two properties scanned most | [Linear priority](https://linear.app/docs/priority), [third-party anatomy note](https://github.com/alexj11324/orvilo1/pull/237), [priority icon set](https://github.com/ApollosProject/bug-board/pull/669) |
| Calm and hierarchy | Linear's redesigns cut "visual noise", reduced coloured chrome, dimmed the sidebar so content stands out, and aimed to make information "easier to scan" | Spend colour only on exceptions (late, urgent); quieten chrome | [How we redesigned the Linear UI](https://linear.app/now/how-we-redesigned-the-linear-ui), [UI refresh 2026](https://linear.app/changelog/2026-03-12-ui-refresh) |
| Display options | Group, sub-group, order within groups, show empty groups, choose properties; status order puts done after active work | creaite has parity; the gap is the default chosen, not the feature | [Linear display options](https://linear.app/docs/display-options) |
| Peek | Linear's peek is Quick Look: tap or hold Space, J/K moves and the peek follows; keyboard only | creaite's follow-the-cursor peek is right; keep it light | [Linear peek](https://linear.app/docs/peek), [why Space](https://linear.app/changelog/2019-09-23-improved-peek) |
| Peek modes | Notion lets each view open records as side peek, centre peek or full page | Offer the choice only if it is used; side peek is the right default | [Notion release 20-07-2022](https://www.notion.com/releases/2022-07-20), [Notion shortcuts](https://www.notion.com/en-gb/help/keyboard-shortcuts) |
| Detail layout | Jira splits description fields from context fields, lets people pin the few they use and moves the rest under "More fields" | Pin a small fixed set; fold the rest | [Jira issue view](https://developer.atlassian.com/cloud/jira/platform/issue-view/), [making the new issue view work](https://community.atlassian.com/t5/Jira-Software-articles/Making-the-new-issue-view-work-for-you/ba-p/2223109) |
| Record header and timeline | Attio put the name, key facts and actions top-left, attributes where the eye lands first, and collapsed automated events in the timeline to cut noise | Header carries identity and provenance; timeline hides the routine | [Attio record page redesign](https://attio.com/changelog/2026/record-page-redesign) |
| Density | Airtable defaults to its shortest row ("maximum density") with taller heights on request; Primer offers condensed, normal and spacious | A density choice in Display, with a denser default for a long list | [Airtable row height](https://support.airtable.com/docs/row-height), [Primer data table](https://primer-docs-preview.github.com/product/components/data-table) |
| Scannability | NN/g: tables serve find, compare, view/edit one row, act; hover highlight and light separators help users keep their place | Keep the hover row; drop decoration that does not help those four tasks | [NN/g data tables](https://nngroup.com/articles/data-tables) |
| Slicing | GitHub Projects' slice panel lists a field's values beside the view; one click narrows the list | A quick "by project" or "by owner" pivot without opening menus | [GitHub table layout](https://docs.github.com/en/enterprise-server@3.17/issues/planning-and-tracking-with-projects/customizing-views-in-your-project/customizing-the-table-layout), [slice changelog](https://github.blog/changelog/2023-08-10-github-issues-projects-august-10th-update/) |
| Keyboard-first edits | Linear: X selects, S status, A assign, P priority, on one or many issues | One key per property on the cursor row or the selection | [Linear select issues](https://linear.app/docs/select-issues), [shortcut list (third party)](https://www.pie-menu.com/shortcuts/linear) |
| Triage | Superhuman: one key per outcome, next item appears at once, optimistic UI with Undo; triage kept apart from doing | A step-through mode for Chase and stale items | [Superhuman design analysis (third party)](https://blakecrosley.com/de/guides/design/superhuman), [a user's workflow](https://philmorle.substack.com/p/how-i-use-superhuman-in-venture-capital-1b75ca904b17) |
| Feeling fast | Linear writes locally first and reconciles later; perceived speed is how fast the UI reacts | creaite already does this (BL-304); protect it in any redesign | [What makes Linear feel instant](https://performance.dev/what-makes-linear-feel-instant) |
| Calm lists | Things is praised for restraint, "never messy or overbearing", and animations that keep your place | Few options visible at once; motion that explains where an item went | [Things 3 (App Store)](https://apps.apple.com/us/app/-/id904244226), [Cultured Code](https://culturedcode.com/) |
| List and detail | Design systems put detail beside the list when there is room and overlay it when there is not | At wide widths, push rather than cover, so the open row stays visible | [Vaadin master-detail](https://vaadin.com/docs/latest/components/master-detail-layout), [Azure DevOps master-detail](https://developer.microsoft.com/en-ca/azure-devops/components/master-detail) |

## 4. Recommendations (ranked by impact over effort)

### Quick wins for the next point release

| # | Change | Why (evidence) | Where | Effort | Risk |
|---|---|---|---|---|---|
| 1 | **Status and priority as marks in the list.** Reuse `PeekProps.jsx`'s status ring and priority bars at 16 px. Status column becomes a ring (word in the tooltip and accessible name); Priority shows bars, with the word only for Urgent | Linear's one-mark-per-row; list and peek then speak one visual language; frees about 120 px of width | `work.js` `cell()` for `st` and `pr`; export the marks from `PeekProps.jsx` | S | Low. Keep the words for screen readers; check the 9 palettes |
| 2 | **Say each filter once.** When the active view explains a filter, do not repeat it as a chip; the chip row shows only what differs from the view ("+ Owner: Sara Example"). Put "Showing 3 of 3" in the tab row or toolbar end | Three statements of "Open" today; Linear "simplified headers and filters" | `renderApplied()` (line 158) compares with the view's `f`; `#wapplied` collapses when empty | S | Low. Clear all stays when any deviation exists |
| 3 | **Drop the Status column by default where the view fixes it.** In All open, Mine, Due soon, every row says "Open". Show Status only when the view mixes statuses (Closed, Delayed, All) | Removes a column of identical words; NN/g compare task | `DEFCOLS` (line 490) plus a rule in `orderedCols()` | S | Low. A chosen column always wins |
| 4 | **Default grouping for Actions by due.** Overdue · This week · Next week · Later · No date, collapsed "Closed" at the foot; RAID by priority; Decisions Pending then Made | Turns a table into a plan; the board already groups this way (`dueBucket`); Linear orders done after active | `WLGRP` default per tab; `wgGroups()` exists | S | Medium. Changes what users see on first open; a saved preference survives |
| 5 | **One key per property on the cursor row or selection.** S status, O owner, P priority, T due date, C close (with Undo). The same list opens as the inline editor; on a selection it is the bulk change | Linear's S/A/P on one or many; creaite has the editors already (`ceOpen`, `bkApply`) | `hlKey()` in `work.js` line 862; `core/keys.js`; HINTS line 496 and Help's key table | S | Low to medium. Check clashes with global N, F, D, ?, / |
| 6 | **Quieter rows.** Remove the dotted underline on the ID and owner (underline on hover only), drop the leading check icon on actions (the tab says what they are), and lower the sub-line contrast. Keep the hover highlight | Linear "reduce visual noise"; NN/g hover row helps keep place | `style.css` lines 670, 974; `cell()` `t` | S | Low. Links stay discoverable on hover and focus |
| 7 | **Peek: smaller title, property list.** Title at `--fs-2xl` (22 px) not display size; properties as a two-column label/value list (Status, Priority, Owner, Due, then Workstream, Milestone) with no vertical rules | At 520 px the four chips cramp and wrap; Jira and Linear show properties as a list; Attio "where the eye lands" | `#pkTitle` CSS; `pk-props` grid in `style.css` around line 1868 | S | Low |
| 8 | **Peek: provenance and client flag in the header.** Under the ID line: source as a link ("From 12-10-2026 Steering minutes"), and a "Client-visible" badge when on | Source on every item is a non-negotiable, but it sits at the bottom of the feed; the client flag hides in collapsed Details | `pkDrawId()` (panel.js line 418) | S | Low |
| 9 | **Peek: one timeline.** Replace the four tabs with one list; show tabs (or a filter) only past ten entries; fold routine lines ("created", "applied") into one | Attio collapses automated events; most items have two to five events | `pkFeed()` (panel.js line 755) | S | Low |
| 10 | **Keep the peek's row visible.** When the peek opens, scroll the row into view on the left and give it the selected tint; at 900 px show the title column only beneath the peek | The overlay hides Owner and Due of the very row being read | `openRecord()` and `pkStep()`; CSS for `body:has(#panel.peek.on)` | S | Low |

### Bigger moves needing a mockup

| # | Change | Why (evidence) | Where | Effort | Risk |
|---|---|---|---|---|---|
| 11 | **Compact single-line row** as the default, with "Comfortable" (today's two lines) in Display › Density. Anatomy: status ring · priority bars · title · quiet chips (workstream, early-warning flag, client eye) · right-aligned owner initials · due (relative, red when late) · ID in muted mono | Airtable and Primer density tiers; Linear's single-line rows; about 36 to 40 px rows doubles what fits above the fold | `cell()`, `rowHtml()`, new Display control, CSS | M | Medium. Column resize and drag assume today's cells; keep the table semantics for screen readers |
| 12 | **Two rows of chrome, not four.** Row 1: tabs on the left, views as a compact menu ("All open ▾") with the three most used as pills, search and New on the right. Row 2: Filter, Display, layout, and only the deviation chips | Linear and Notion keep views and filters in one header; Things' restraint | `shell.html` lines 70 to 82; `renderViewBar()`; `FilterBar.jsx` | M | Medium. BL-150 folding at 900 px must still work |
| 13 | **Peek v2.** Header: ID · project › workstream, source link, client badge, actions (Draft, Chase, More). Body: title, the update field first, properties as a list, Details only for the rare fields, single timeline. Footer: Sneak peek as one keycap "//" | Jira's description vs context split; Attio's header; consolidates 7 to 10 | `panel.js` BL-176 blocks; `PeekProps.jsx` | M | Medium. Many tests touch `#pk*` ids; keep ids |
| 14 | **Push, not cover, at wide widths.** At 1440 px and above, the list narrows (title, owner, due) and the peek sits beside it; below that, today's overlay | Master-detail pattern: split when there is room, overlay when not | `#panel.peek` CSS, `sizeList()` | M | Medium. Interaction with ask creaite's panel width (`--chatw`) |
| 15 | **Triage mode for Chase and stale items.** Open the Chase view as a step-through: one item, its last update and owner, and single-key outcomes (Chased · Done · New date · Skip), next item appears at once | Superhuman's one key per outcome and triage apart from doing; creaite already tracks chases (BL-224) | New mode over the peek, reusing `pkCommit` and Draft chase | L | Medium. Must not blur into sending; nothing leaves the laptop |
| 16 | **Completion that keeps your place.** When an item is closed in a filtered view, tick it, keep it for a moment, then let it slide out with "Closed · Undo"; the cursor moves to the next row | Things' "animations keep your place"; avoids rows vanishing under the pointer | `mFlipRows`/`mSnapRows` in `core/motion.js`; render after commit | M | Low. Respect reduced motion |
| 17 | **Slice by project or owner.** A narrow left list of projects (with counts) that filters the view in one click, toggled from Display | GitHub Projects' slice panel; under 5 projects it is a cheap, visible pivot | New panel beside `#workWrap` | M | Low. Could duplicate the Project filter; one must win |

## 5. Things not to copy

- **Workspace-wide defaults, assignees' avatars stacks, comments, mentions, followers.** Linear's "Set as default for the workspace" and Notion's per-view settings for everyone solve team problems that a single user does not have.
- **Monday-style colour fields.** Up to 40 coloured status labels per column make every row loud; creaite's four statuses need no palette beyond late and urgent ([Monday status column](https://support.monday.com/hc/en-us/articles/360001269685)).
- **ClickUp-scale customisation** (custom fields, many view types, nested sub-tasks). The tracker schema is the rulebook; more knobs add setup, not decisions.
- **Manual drag ordering of rows.** It invents an order nobody else uses; due date and priority already rank the list. The board's drag to change a field is fine.
- **Centre peek and full-page record as equal options.** One side peek plus Expand is enough; a third mode is a setting to maintain.
- **Hold-Space Quick Look as a separate preview.** creaite's peek already follows J/K, and Space selects; remapping would break a learnt habit for little gain.
- **Cycles, estimates, sprints, story points.** Not part of a programme manager's actions, risks and decisions.
- **Infinite scroll and virtualised lists.** Fewer than five projects; the 50-row cap with internal scroll is enough.
- **Mobile layouts.** Out of scope: desktop and 900 px only.

## 6. Suggested mockups to build next

1. `work-calm-row-mockup` (recommendations 1, 3, 6, 11)
2. `work-two-row-chrome-mockup` (2, 12)
3. `work-due-groups-mockup` (4, 16)
4. `work-item-peek-v2-mockup` (7, 8, 9, 13)
5. `work-split-view-mockup` (10, 14)
6. `work-chase-triage-mockup` (15)
7. `work-slice-panel-mockup` (17)

Each starts from `dev/design-system/pages/work.html` and the real stylesheet, per DESIGN-SYSTEM.md section 1; new parts in one `/* NEW */` block; fictional data only.
