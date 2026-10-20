# Minutes view v2: build brief

Mockup (LOCKED, Alan signed off 20-10-2026): `dev/mockups/minutes-view-v2-mockup.html`. Built on the 2.5.0 stylesheet and the real Minutes classes. Replaces the BL-338 A4 view's row design. Related: #261 (approve with no items), #266 ('needs details' wording), #267 (headings and widths).

## What changes
1. **One version only.** Remove the "One version / Internal + distributed" switch, the Internal / Distributed / Side by side switch, Internal only marking in the view, and the distributed export. (Alan: "I only ever want one version of minutes".) The server's distributed code is left alone until Alan decides to retire it.
2. **Track column, three states per item.** Tick = register a work item. Cross = remove the line from the minutes. Neither = stays in the minutes, not tracked. Clicking a pressed button clears it. Defaults: actions and issues start ticked; decisions and risks start with neither (still recorded one by one). No legend, no "kept in the minutes" pill; the Track heading's hover text explains it. Summary in the bar: "n work items to register · n kept in the minutes only · n removed".
3. **Aligned tables.** One heading per column (Track, item, Owner, and for risks, issues and actions Due, Priority, Workstream). No source-arrow column.
4. **Inline editing, no popup.** The item text and the summary are edited where they stand (Enter or click away saves, Esc undoes). Owner, Priority and Workstream are in-row dropdowns. Due opens the app's deadline popover (typed words, quick picks with dates, month calendar, Not set), as in DeadlinePopover.jsx. The build uses the app's editor (Tiptap) for the summary and item text; selected text gets AI as elsewhere.
5. **Transcript highlight both ways.** Hovering a row lights its transcript turn; hovering a turn lights its rows. The transcript hides from the Transcript button or its close button, and the page rescales.
6. **Disappearing header.** Scrolling the sheet slims the bar and hides the app bar and page header, as Reporting does (`rpt-slim`). The slim bar shows the title.
7. **Zoom.** Keep fit-to-width and add trackpad pinch and Ctrl+scroll (50% to 250%), as well as the − and + buttons. Must not be lost.
8. **Icon toolbar.** Show as exported, Transcript (pressed state), Export and Re-extract are icon buttons with hover tips (the app's `.ib`); only Approve minutes keeps a label, as the one primary action. The bar fits one row.
9. **Export menu.** Word, PDF, HTML, each with its description line, plus "Draft the follow-up email". Word is an export only: editing the exported file never flows back.
10. **Approve minutes is one click.** No popup. A snack says "Minutes approved · n work items registered · Undo". A small "Before approving" box appears only when a ticked item has a real problem (an owner who needs details, a possible duplicate): it lists just those, with Go back and Approve anyway. Approving with nothing ticked is the "take no items" case (#261).
11. **Wording.** "Needs details" replaces "not in the people register" (#266).

## Not in scope
Re-extract, Show as exported, Coverage and the checks list keep their current behaviour unless Alan says otherwise.

## Tests (automated; nothing here needs a hand check)
Three states and their defaults; clearing a pressed button; summary counts; inline edit saves and Esc undoes; Due popover words and calendar; hover highlight both ways; transcript hide rescales; slim header on scroll; Ctrl+wheel zoom; export menu entries; approve with and without problems; approve with nothing ticked.
