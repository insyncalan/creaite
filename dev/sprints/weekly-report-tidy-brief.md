# Brief: Weekly report tidy (one issue: three defects and one feature)

Product Manager, 18-10-2026, from Alan's screenshots and requests. Mockup: dev/mockups/weekly-report-tidy-mockup.html (a fresh weekly report built on the real weekly snapshot; hover a section and use its menu, add a risk or action under its table, use Add a text section at the foot). It also carries the approved "Check this report" button from #170 as a button only. Nothing is built; not approved yet. Alan asked for these together in one issue, with the defects in release 2.3.2.

## 1. Defect: the section menu is obscured and huge

**Seen:** the menu from a section's chevron opens to the left of the page and is cut off by the side bar ("his section", "of the export", "up", "down"); its text is large.
**Fix:** a discreet menu inside the window: 13 px text, a small icon before each word, never wider than it needs, opening below the chevron and never under the side bar or off the page. Items: Leave out of the export, Move up, Move down, Add a text section below (and Delete this section for a text section). Opens as a popup above the page, not inside the scaled page, so zoom never clips it. Esc closes it.
**Done when:** at 80%, 100% and 120% zoom, and at 900 px wide, every item is fully visible and readable; keyboard: Enter opens, arrows move, Esc closes and returns focus to the chevron.

## 2. Defect: the health row's Change button is huge, and the six-week strip overruns the flag

**Seen:** the Change button is oversize; the six-week health strip and its dates are wider than the health flag above them.
**Fix, to the design standard:** Change is the small button (`.btn.sm`, 28 px); the health column has one width (168 px) and the flag, the six-week strip with its two dates and the button all stay inside it; the flag text is 12 px and never wraps. The plain app sparkle (as in the health suggestion item) sits beside the reason, not beside the flag.
**Done when:** the strip, dates and button never exceed the flag's width at any zoom; light and dark; both palettes.

## 3. Defect: no way to add a risk, issue or action from the report

**Seen:** Alan asks "how do I add risks, issues, actions?" and cannot.
**Fix:** a quiet "+ Add a risk or issue" under the Risks and issues table, and "+ Add an action" under Overdue actions. It opens one row of fields (what, type or owner, priority or due) with Add and Cancel. Add writes the item to the tracker the way the dashboard saves an edit (with Undo); the new row shows at once, marked New. An action that is not overdue shows in the report once it is.
**Done when:** each adds a real tracker item with the usual ID, a source and Undo; Cancel changes nothing; the report's saved version and exports are unchanged until Alan approves it.
**For Alan:** the report only lists overdue actions, so a new action due next week will not appear here. Should the report also get a "Next week's actions" list, or is a link to Work enough? I recommend a link to Work.

## 4. Feature: a free-text section, anywhere in the report

**What:** an "Add a text section" button at the foot of the report, and "Add a text section below" in every section's menu. The new section has its own heading (Alan names it) and a text box in the one rich editor (the same editor and toolbar as Notes and Current state: bold, italic, lists, link). It moves up and down like any section, can be left out of the export, and can be deleted. It is in the filed report and every export. In the client report it follows the rule for every section: only if Alan chooses to match or write it for the client.
**Done when:** a text section can be added anywhere, edited, moved, left out, deleted and exported to HTML, Word and PDF; its text is saved and filed with the report; the one editor's gate passes; no pasted style leaks.

## Client-safe

Added text sections are internal until Alan matches or writes them in the client report. Risks, issues and actions added here follow the usual client-visible flag (off by default).

## Release and size

Alan asked for the defects in 2.3.2, with #172 and #212, and for one issue. The three defects are small; the free-text section is the larger part (size M). If 2.3.2 cannot carry the feature, split it and keep the defects in 2.3.2.

## Test (standing rule)

Automated hand checks for this release's test file (Automation map in the release's sheet): menu fully visible at four zooms (scriptable), the health row's widths (measurable), add-a-row writes a tracker item (scriptable), a text section adds, saves and exports (scriptable); the look is judgement.
