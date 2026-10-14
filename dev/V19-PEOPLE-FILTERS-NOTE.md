# v19-people-filters: BL-264, Settings › People filters (laptop 2, 13-10-2026)

For the Scrum Master. Branch `v19-people-filters`, from `origin/main` (dd7bb9f), with `origin/main` merged in at aac20fb
(v1.8.0 and BL-231 phase 5's html helpers). Not pushed.

## Built

Built as the brief and mockup describe, following Alan's decisions of 12-10-2026.
- **Search box** (`#pmQ`): name, alias, email or role, as you type. Matches are marked, Esc clears it, and `/` jumps to it on Settings ›
  People only (a capture listener, as Activity's `/`; elsewhere `/` is still ask creaite). The search is not remembered.
- **One funnel** (`#pmFBtn`, Work's `.ib.bd` with the `.dot` count). `F` opens it. Its label and tooltip say "Filter people: n on".
  The picker uses Work's `.fpmenu/.fpick/.fpf` with two groups:
  - **Who:** Project (from items and `D.stakeholders`); How they're involved (Owns items, Named as a stakeholder, in the chosen
    projects); Organisation (with "No organisation"); **People I follow** (Followed, Not followed).
  - **Tidy up:** In the register; Needs attention (No email, No organisation or role); Removed people (Hidden is the default,
    then Shown with everyone, Removed only).
  - Ticks are "any of" within a field and "and" across fields. Project and Organisation have is / is not.
  - Each choice has a live count given the other filters, and a choice that leaves nobody is greyed. Only fields and choices
    that exist in the data are offered.
  - Footer: "Showing n of N", Clear all, Done.
  - Keyboard: ↑ ↓ ← → Enter. Esc or Done returns focus to the funnel. A click or focus outside closes the picker.
- **Chips**: a chip's words open the picker at that field, and its × removes it. "Removed: hidden" is a quiet outlined chip from
  the start. Clear all appears once anything beyond the default is on.
- **Count line**: "Showing n of N people · n removed hidden Show · n need attention Show".
- **Empty state**: Work's, naming each filter, what removing it alone would show, Remove, and Clear all filters.
- **With projects chosen**: the headings read "Actions · this project" or "· n projects", and the counts and their links cover
  those projects. With several projects, `openWork` now takes `extra.p` (core/nav.js, one line). A stakeholder-only person
  shows "named in the project’s stakeholders".
- **Remembered until cleared**: Work's *filters* live only in the address (`#work=…`), which a reload keeps but reopening the
  dashboard does not. So the People filters use the same storage as Work's remembered display choices (layout, grouping,
  columns, the People tab): `store` (localStorage), key `creaite-people-filters`.
- **BL-288**: nothing on the card says "VIP". The field is "People I follow", with the values "Followed" and "Not followed". The
  table's VIP chip in `renderPeopleMgr` is removed, which is one of BL-288 part 2's rows, so `sprint-vip-private` can drop that row.
- **Reuse**: `work.js` now exports `fchipHtml` (one chip) and `relaxHtml` (the empty state's markup), and Work's own chips and
  `emptyHtml` use them, with the markup byte for byte the same (Work's goldens are unchanged). `funnelTip(n, what)` and
  `isNotSeg(k, neg)` take a label and a state.
- **Code**: written in the html helper (`html`/`putHTML`, no new sinks). The listeners are bound once from `bootSettings0079`
  through `pfBind()`, so `main.js` is unchanged.
- **Docs**: Help (People, a new "Finding people in Settings › People" bullet; the VIP bullet no longer says the chip shows in
  Settings › People) and `dev/dashboard-spec.md` (Settings › People and projects › People).

## Goldens changed

- **`settings-people` only.** It changes for two reasons:
  - The filter row, chips, count line and live region are added.
  - The table has `id`s on the Actions and RAID headings and on `tbody` (`pmHA`, `pmHR`, `pmRows`), which the redraw needs.
- The sample vault has nobody removed and nobody followed, so it shows no "Removed: hidden" chip. Its count line reads
  "Showing 5 of 5 people · 1 needs attention Show".
- Every other screen's golden is unchanged (test_snapshots passes).

## Tests (local, -j 2, after merging main)

- **New:** `dev/tests/test_people_filters.py`, 10 tests in Chrome. They cover:
  - each field narrows the list, and fields combine;
  - is not;
  - project from items and from stakeholders (including a stakeholder named by alias);
  - involvement follows the chosen projects;
  - only existing fields and choices are offered;
  - the counts;
  - removed people hidden by default, with the chip and the hint;
  - Needs attention's Show;
  - search over name, alias, email and role, with the mark and Esc;
  - the empty state and Remove;
  - a chip opening the picker at its field;
  - F, the arrow keys, Esc returning focus to the funnel, a click outside closing the picker, and `/`;
  - remembered across a reload until cleared, and the search not remembered;
  - several projects' count links;
  - no VIP text;
  - no sideways scroll at 390 px.
- **Passed:**
  - test_snapshots, test_people_dashboard, test_people_filters, test_count_links;
  - test_work_empty_state, test_work_filter_picker, test_work_filters_live, test_work_opening_view;
  - test_motion, test_dashboard_split, test_hostile_text, test_scoped_lookups, test_settings_page.
- **check.py:** OK. **typecheck:** 0 errors. GitHub Actions has not been run (the branch is not pushed).
- **Hand check:** screenshots of the picker (light), search and empty state (dark), and the phone width. They look like the mockup.

## Left, and questions

- **Wording, settled (Alan, 13-10-2026):** keep the People list's "Followed" and "Not followed". Work keeps "Owned by someone
  I follow" and "Not followed".
- **Merge order:** the VIP chip row is already gone here. `sprint-vip-private` part 2 edits Help's VIP bullet too, so expect a
  small text conflict there.
- **Your own name** is treated as in the register, and never as "needs attention", as the table already did.
