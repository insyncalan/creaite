# Work items v2: mockup and design-system notes

Mockup (draft, for Alan): `dev/mockups/work-items-v2-mockup.html`. Built on `dev/design-system/pages/work.html` (commit c237a088, VERSION 2.1.0) with the app's own classes. Research: `dev/sprints/work-items-ux-research.md`. Fictional data.

## What the mockup shows (research items 1 to 13)
1. Status and priority as marks, reusing the peek's own ring and bars (`PeekProps.jsx`), words kept for screen readers.
2. Two rows of chrome: search, a View menu with three pills, the filter button, density, layout, Display, New. Chips row appears only when a filter differs from the view.
3. Compact single-line row (ID on the title's line) and Comfortable (today's two lines), switched in the toolbar (it belongs in Display).
4. Actions grouped by due: Overdue, This week, Next week, Later, No date, Closed collapsed.
5. Quieter text: no dotted underlines, no leading check icon, tags as quiet chips.
6. One key per property on the cursor row (S O P T), C closes with Undo and moves the cursor on.
7. Peek v2: source link, client badge and workstream in the header; properties as a label/value list; one activity timeline with routine events folded.
8. The peek runs over the page (no squashing). Click selects; double-click or the ID opens; arrows move, right opens, left closes. A switch compares Today’s peek with v2 (open for discussion).

## Design-system additions this needs (all in one `/* NEW */` block)
- `.tg`: a small neutral tag chip (workstream, client, raised again); today these are plain text.
- `.pkl`: a label/value property list for the peek (replaces `.pk-props` columns).
- Row density classes `.cmp` and `.cmf` on the list table (40 px and 57 px rows).
- The app's existing marks, group heading `.wgh`, `.pk-fe` feed, `.pkstage` toast, `.kbd` and tokens are reused unchanged.

## Corrections to the research
- The peek title is already `--fs-2xl` (22 px); the research called it very large from a scaled screenshot. No change needed.

## Not shown
Board layout, RAID and Decisions tabs, the Chase step-through, a split view at 1440 px and wider, the slice panel.
