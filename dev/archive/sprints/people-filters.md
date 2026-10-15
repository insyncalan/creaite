# Design brief: Settings › People filters (BL-264)

**Status:** design brief, revised after Alan's review (12-10-2026: "smarter and better designed filters like we have on work items… maybe just a single filter icon which caters for all sampled filters"). Placed in v1.9.0 by the Scrum Master. Mockup: `dev/mockups/people-filters-mockup.html` (open it from the file system; 14 fictional people from the sample vault). When it is built: branch `sprint-people-filters` (or a block in a v1.9.0 sprint), from the tip of `main`, with the UX baseline (BL-157) checked before it is called done. No schema change.

## Goal

Settings › People lists everyone with no way to narrow it. Give it the same filtering as Work and Review (BL-130, BL-133, BL-159, BL-160): one funnel, one picker, chips for what is on, so People feels like the same product and Alan can find a person, or a group of people, quickly.

## The screen

Settings › People, with one row above the existing table:

- **Search, always in view** (name, alias, email or role, as you type; matches highlighted; Esc clears; `/` jumps to it).
- **One funnel button** (Work's `#moreBtn` look: `.ib.bd`, the `funnel` icon), with a count badge (`.dot`) when filters are on and the accent border. Its name and tooltip say "Filter people: 2 on". `F` opens it.
- **The picker** (Work's field picker, `.fpmenu` / `.fpick`): fields on the left in two groups, the chosen field's choices on the right, each with its live count given the other filters.
  - **Who:** Project; How they're involved (owns items, named as a stakeholder; in the projects chosen, or any); Organisation (each one in the register, and "No organisation" if anyone lacks one); VIP (VIPs, not VIPs).
  - **Tidy up:** In the register (in, or not in the register: on items only); Needs attention (no email, no organisation or role); Removed people (hidden, the default; shown with everyone; removed only).
  - Choices are ticks and combine as "any of" within a field, "and" across fields. Project and Organisation also have Work's **is / is not**. Removed is a single choice with "default" marked.
  - **Smart:** only fields and choices that exist in the data are offered (no VIP field with no VIPs, no "No organisation" when everyone has one); a choice that would show nobody is greyed, as on Work; the field list marks what is set ("2", "not · 1", "default").
  - The footer says "Showing 9 of 14", with **Clear all** and **Done**.
  - Keyboard: focus lands on the first choice; ↑ ↓ move between fields, → or Enter goes to the choices, ← back; Esc or Done closes and returns focus to the funnel; a click or focus outside closes it.
- **Chips beside it** (Work's `.fchip`): one per field that is on ("Project: Falcon Data Platform, Orbit Customer App", "Organisation: not Brightwater" tinted as an exclusion, "Search: “sara”"), each with ×; clicking a chip's text opens the picker at that field. **"Removed: hidden"** shows as a quiet outlined chip from the start; its × shows removed people. **Clear all** appears once anything beyond the default is on and returns to the default.
- **The count line,** right-aligned as on Work: "Showing 13 of 14 people · 1 removed hidden **Show** · 4 need attention **Show**". The hints appear only when they apply; Show sets that filter in one click.
- **Nothing matches:** as Work's empty state (BL-132): each filter with how many removing it alone would show, a Remove button for each, and Clear all filters.
- With projects chosen, the Actions and RAID headings say "· this project" or "· 2 projects" and the counts are for those projects (they stay links into Work, BL-190). A person who is only a stakeholder there shows "named in the project's stakeholders". Project names are shown in full (BL-101).

Filters are remembered **until cleared** (Alan, 12-10-2026): they survive a reload and reopening the dashboard, stored the same way as Work's remembered filters. Clear all returns to the default (removed people hidden). The search box is not remembered.

## In

- The funnel, picker, counts, chips, Clear all, the count line and its hints, the empty state, filters remembered until cleared, the per-project counts, the keyboard and the phone layout (the picker spans the toolbar's width below 640 pixels).
- Project from items and stakeholders. The page already has stakeholders per project (`D.stakeholders`, from the project register's Key and Shared stakeholders, `build_dashboard.stakeholders()`), so nothing new is read.
- Reuse, not copy: the picker, chips and empty state should share Work's and Review's helpers where they can (`.fpmenu`, `.fpick`, `.fpf`, `.fchip`, `isNotSeg`, `funnelTip`), with a People field list in the same shape as `FDEFS`.

## Out

- Saved views (as Work's views): later if wanted.
- Per-field buttons beside the funnel (Work keeps Status, Project, Owner, Due as buttons; People has the funnel only, as Alan asked).
- The field picker's "Find a field…" box: seven fields don't need it.
- A project column, or editing people in bulk.
- Filters on the People view (BL-56) itself: this item is Settings only.
- Any change to the register file or schema.

## Decisions (Alan, 12-10-2026)

The design is approved ("mockup is perfect"), for **v1.9.0**, built on laptop 2 once BL-231's modules are merged.

1. **Stakeholders:** the project register's Key and Shared stakeholders (`D.stakeholders`). No `CLAUDE.md` reader.
2. **Remembered:** until cleared, not just for the session. The mockup still says "session"; the build follows this decision.
3. **Needs attention:** both choices, "No email" and "No organisation or role".
4. **Removed:** hidden by default, with the "Removed: hidden" chip and the "n removed hidden · Show" hint.

Answered by the design: several projects at once (ticks, "any of", plus "is not"); how the filters look (one funnel, as on Work).

## Files it touches

`system/templates/dashboard.html` (`renderPeopleMgr`; a People field list and picker in a marked block, reusing the BL-130 picker CSS and helpers, `.fchip`, `.ib .dot`, the `funnel` and `x` icons; the `F` and `/` keys scoped to Settings › People), `system/templates/help.md`, `dev/dashboard-spec.md`, `dev/tests/` (each field narrows correctly and they combine; is not; project from items and from stakeholders; how they're involved follows the chosen projects; only existing choices are offered; counts update; removed hidden by default and its chip and hint; Needs attention's Show; chips open the picker at their field; Clear all restores the default; empty state; Esc returns focus to the funnel; filters remembered across a reload until cleared; no horizontal scroll at 390 pixels).

## Size

**M, small end: about two and a half days.** One and a half for the picker, the fields, counts, chips, count line and empty state (most of it reuses Work's picker); one for tests, Help, the spec and the UX baseline (keyboard, both themes, phone width). Up from S (one and a half days) because the single picker, the smart hints, "is not" and the empty state are new for People.
