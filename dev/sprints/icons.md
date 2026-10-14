# Sprint icons: icons in place of words (BL-158 to BL-161)

**In v1.3.0 (Alan, 10-10-2026).** `VERSION` stays 1.3.0; the release notes go in `dev/release-notes/1.3.0.md` under "Changed".

Branch `sprint-icons`, worktree `../creaite-icons`, made from the tip of `main` **after `sprint-ux` has merged**. Both sprints work in `system/templates/dashboard.html`, and `sprint-ux` builds things this sprint must build on, not around: BL-146's shared auto-grow helper (the Display and chat markup), BL-150 (the panel), BL-154 (the edit panel's fields) and especially **BL-155 (the Keys chip, which sits at the end of the Work and Review filter bar)**. Read what `sprint-ux` actually built; where it differs from its backlog text, the code wins; say so in BUILD.

## The design is accepted

**`dev/mockups/icons-mockup.html` is the design; open it first** (six sections, each with Now beside Proposed, working tooltips, the three New-button styles, and the legend of all 29 icons). **Alan accepted all of it on 10-10-2026, with the New button as style A** (a soft tile that grows to show its label on hover and focus). Read "Icons in place of words" in `dev/BACKLOG.md` (BL-158 to BL-161) for each item's Today, The change and Not changed; the rule at the top of that section decides any button the list does not name.

Two points about the mockup, so they are not copied by mistake:
- **Its tooltips show shortcut keys that do not all exist.** The real ones are **D** (Display), **F** (the filter picker), **E** (edit), **A, R, X** (Review), **Shift+R** (reject with a reason), **J, K** and **Esc**. There is no **N**, **L** or **B**. A tooltip shows a key only if the dashboard already handles it; do not add the missing keys in this sprint.
- **The mockup draws its own SVG paths** in the style of an open-source set. In the dashboard, use the same shapes through BL-158's helper; if any path is taken from a published set, record the set and its licence in `BUILD.md`. No icon font, no external file.

## Before starting

1. `git worktree list` shows `sprint-ux` gone and `git log main` has it. If not, stop and say so.
2. Bring `main` in. Read `sprint-ux`'s Keys chip (BL-155), the panel (BL-150) and the shared textarea helper (BL-146).
3. Run the test files below before changing anything, to know what passes. Several look for button text and will need updating (see "Tests").

## Order

Commit each item separately, each in its own marked block (`/* ===== BL-1xx (sprint-icons) ===== */`). One stage; items 2 to 4 can be reviewed on their own after item 1.

1. **BL-158: the set, the tooltip, the glyphs.** The `ic(name)` helper and the 29 icons; the tooltip (hover 250ms, focus at once, Esc, scroll, `role="tooltip"`, theme colours); the typed glyphs replaced (📅, `×`, `✕`, `›` `⌄` `▸` `▾`, 🌙) with a rotating chevron and a theme icon that shows the destination. Move the existing rail, header and section icons onto the helper without changing how they look. Nothing else changes yet, so the page should look the same except the glyphs; check that before going on.
2. **BL-159: Work.** List/Board icon switch (remove the copy in the Display menu), Display sliders, funnel with count, New button style A, and one New button with a menu on Decisions (Record a decision, Ask for a decision; the separate `#newDecNeeded` button and its block go). `role="menu"`, arrow keys, Esc and focus return.
3. **BL-160: Review.** Funnel, Display, Approve routine; the bulk bar; row actions (icons shown on hover, focus and the cursor row).
4. **BL-161: everything else in the legend.** Project, person and Prep buttons; the Files, Intake, People, Activity and Settings rows; Send and Stop in the chat.

## Rules for every conversion

- **Name and tooltip:** an icon-only control has `aria-label` and `data-tip` with the same words, and `data-key` only if the key exists. A tooltip says the action ("Remove from Intake"), not the icon's name ("Trash").
- **Word or icon:** follow the rule at the top of the backlog section. A button that is not in the legend or the list keeps its word. When in doubt, keep the word and say so in BUILD.
- **State is never colour alone.** A pressed toggle uses `aria-pressed` and a filled background; Approve and Reject keep an icon and a word or a tooltip; health stays icon plus text.
- **Targets and contrast:** 28 to 32px, 3:1 for the icon against its background in all five themes, light and dark. Check the New tile's soft background in each theme; Brightwater's dark theme (green accent on charcoal) is the one most likely to fail.
- **Motion:** the New tile's growth and the chevron's turn use the existing motion tokens and stop under reduced motion (the `data-reduced` setting and `prefers-reduced-motion`).
- **Layout:** the toolbar must not wrap more than it does now at 1100px and at 900px; icons make it narrower, not wider.
- **Nothing else moves:** no behaviour changes, no new endpoints, no schema, no settings. This sprint changes how controls look and what they are called to a screen reader.

## Tests

Each sprint runs its own tests only (STATUS.md's rule); one full suite runs on the final `main`.

- **New:** `dev/tests/test_icons.py` in a real browser (as the other `test_work_*` files do): every icon-only button has an `aria-label` and `data-tip`; the tooltip shows on hover and on focus and goes on Esc; List/Board toggles layout and `aria-pressed`; the funnel opens the field picker and shows a count when filters are on; the New tile's label is the tab's own word and the tile opens the right form on Actions and RAID; on Decisions the menu offers two items, **Record a decision** opens the form as Made dated today and **Ask for a decision** as Pending (the same fields `openNew("decisions","needed")` fills today), and the old `#newDecNeeded` is gone; the theme icon swaps; the Display menu no longer repeats List/Board; the copy icon ticks.
- **Update (they look for button text or ids):** `test_work_display`, `test_work_layout_controls`, `test_work_filter_picker`, `test_work_filters_live`, `test_work_board`, `test_work_grouping`, `test_work_empty_state`, `test_decisions_board`, `test_decisions_dashboard`, `test_decisions_prep`, `test_decisions_sprint5`, `test_review_triage`, `test_reject_reasons`, `test_bulk_edit`, `test_cell_edit`, `test_row_selection`, `test_dashboard`, `test_dashboard_editing`, `test_chat_box`, `test_motion`, `test_today_brief`, `test_project_names`, `test_status_facts`. Where a test finds a control by its words, find it by `id`, `data-*` or `aria-label` instead, and keep the assertion about behaviour. Do not weaken an assertion to make it pass.
- **In the browser, by eye:** drive Work (three tabs, both layouts), Review, a project page, a person page, Files, Intake, Settings › People and Activity, in the creaite, Brightwater and Linear themes, light and dark, at 1440, 1100 and 900px. This is where an icon that is unclear or a toolbar that wraps shows up; tests will not find it. Fix it or write it in BUILD under "Open".

## Documents

- `help.md` and the first-day guide (`build_guides.py`, then regenerate): every sentence that names a button now an icon ("press Display", "choose List or Board", "Decision needed") says what the icon looks like and where its tooltip is. Add a "What the icons mean" table to Help's reference (the mockup's legend, which is the source).
- `dev/dashboard-spec.md`: the Work toolbar, Review, the New button and the tooltip; remove the "Decision needed button beside New decision" line (FR-100's text moves to the menu).
- **Don't edit `dev/BRD.md`, `dev/BACKLOG.md` or `dev/sprints/STATUS.md`** (the usual rule, Alan 10-10-2026). Write the FR text for the icon rule and the tooltip in BUILD; the scrum master adds it to the BRD and removes BL-158 to BL-161 from the backlog at the merge.
- `dev/BUILD.md`: a "Sprint icons" section: what was built, the icon source and licence, departures from this brief, and "Open".
- `dev/release-notes/1.3.0.md`: one paragraph under Changed, plain words: "Many buttons are now icons with a tooltip; New is a quiet tile; New decision and Decision needed are one button with a menu."

## Owns (other sprints must not edit while this is in flight)

`system/templates/dashboard.html`'s toolbar, Display menu, Review bar and row-action code, and the tooltip and icon blocks; the tests listed above. Nothing outside `dashboard.html`, the docs and the tests.

## Done when

- The mockup's six sections match the dashboard, checked side by side in the browser.
- Every button in the legend is converted and every button not in it is unchanged.
- The tests above pass (own files only; one pass is enough), `help.md` and the guides are current, and BUILD records what was built and what is open.
- **After the merge, not a condition of it** (Alan, 10-10-2026): Alan looks at Work, Review and one of each page type and agrees the icons are clear. It is one of his hand checks before publishing; list what to look at in your report.

## Out of scope

The left rail; the Today page's links and cards; field-name filter buttons; dialogs' Cancel/Save/Create/Discard; new keyboard shortcuts; a user setting to switch icons back to words (add it only if Alan asks after using it; it would be a Display-style setting, not a build now); animated icons.
