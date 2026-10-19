# Work items v2: mockup and build rules

Mockup (for Alan): `dev/mockups/work-items-v2-mockup.html`, built on `dev/design-system/pages/work.html` (commit c237a088, VERSION 2.1.0) with the app's own classes. Research: `dev/sprints/work-items-ux-research.md`. Fictional data.

## Alan's decisions (19-10-2026)
- **Keep today's peek** (four property chips, Details, tabs All/Activity/Updates/Source). The v2 peek is dropped.
- **Keep today's Filter panel** (the funnel: Find a field, Status, Due, Owner, Project, Priority and More fields, is / is not, counts, Result, Clear all, Done) and the five quick filter buttons. The view-pill row and the applied-chips row are **not** brought back (the list has the tabs and one toolbar row above it); Mine, Due soon and Chase are reached through the panel. Open question: whether the saved views (All open, Mine, Chase...) need a home.
- **Keep the underlines** on the owner and the ID: the owner opens their page and workload (and the right-click menu offers Draft email and Chase); the ID opens the peek.
- **Keep the context menu** (right-click, Menu key, Shift+F10).
- **The peek runs over the page** (never squashes it). A single click opens another row in the peek only while the peek is already open; otherwise a click selects, and double-click, the ID, Enter or Right opens it. Left closes the peek, or opens the context menu when no peek is open. Up and Down move.
- **Density icons** (compact, comfortable) sit beside the list and board icons, on the right.

## What changes in the list
1. Status and priority as marks (the peek's own ring and bars); words stay for screen readers.
2. A compact single-line row as the default, today's two-line row as Comfortable.
3. Actions grouped by due (Overdue, This week, Next week, Later, No date, Closed folded); RAID by priority; Decisions Pending then Made.
4. One key per property on the cursor row: S, O, P, T, and C to close with Undo. V toggles Client-visible.

## New in the peek
- **One-click Client-visible switch**: an eye button in the peek bar (key V), also in the right-click menu. It is on or off at a glance (tinted when on), with a badge beside the ID, a tag in the list, and an Undo toast. Turning it on means the item can appear in client reports.
- **A complete history in Activity.** Every change to a record becomes an event, newest first, in the form "who, via where, what, when": created; every field changed with its before and after (status, owner, due, priority, workstream, milestone, project, title, impact, likelihood, response, client-visible, labels, links); updates; chases drafted; raised again by a later meeting; source added; approvals and rejections from Review; Find updates from a note; bulk changes; and every undo, which strikes the original event through and adds its own. Each event carries the route it came by (the dashboard, Review, cx-edit, a note, the sweep, ask creaite) and a source reference where there is one. The tabs filter the same list: Activity (everything about the record), Updates, Source.
  - Acceptance: a test that changes each field through each route (peek, cell, bulk bar, context menu, Review, cx-edit, undo) and checks one event with the right before and after; and that no event stores message text.

## Must not undo anyone's layout (acceptance rule for every change here)
Today's saved settings are kept exactly as they are: `creaite-colwidths` (resizing), `creaite-colorder`, `creaite-cols`, `creaite-worklay`, `creaite-workgrp`, `creaite-listgrp`, `creaite-worksub`, `creaite-boardhide`, `creaite-boardcoll`, `creaite-boardclosedall`, `creaite-listcoll`, and saved views.
- New defaults (compact density, grouping by due) apply only where nothing is saved. An explicit "no grouping" must be stored as a choice, so it is not mistaken for unset.
- No migration rewrites a saved value; an update adds keys, never resets them.
- Test: a fixture with every key above set, run through the update and a reload, must come back identical, and a board resize must survive it.

## Design-system additions (one `/* NEW */` block)
`.tg` tag chip; row density classes `.cmp` and `.cmf` (40 px and 57 px rows); the density switch (a `.seg.ico`). Everything else is existing: marks, `.wgh`, `.pk-*`, `.pkpop.cxmenu`, `.pkstage`, `.kbd`, tokens.

## Not shown
Board layout, Display, column sorting and resizing, bulk selection, cell editing, the funnel's extra fields (Milestone, Raised, Closed, Source, Type, Label: unchanged), the Chase step-through, split view, slice panel.
