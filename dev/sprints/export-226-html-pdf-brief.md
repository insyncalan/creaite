# Brief: #226 one renderer for the HTML and PDF weekly report

Product Manager, 18-10-2026, for Team Stark. Approved direction (Alan, 18-10-2026): the sheet's own "Show as exported" view becomes the HTML export, and the PDF prints that same page. Evidence: dev/sprints/weekly-report-export-audit-2026-10-18.md. Reporting hub brief: dev/sprints/reporting-hub-brief.md (Round 7). The Python renderer stays as the fallback when no browser or live server is available.

## What the user must see

The exported HTML, opened on its own in any browser, and the PDF made from it, look like the report on screen in "Show as exported": same header, same health block, same figures, same timeline, same tables, same text. Nothing a person left out (eye closed, section hidden) appears; nothing on screen that belongs to the report is missing. Screen-only controls (grips, eyes, counts, add links, menus) are not in the file.

## Acceptance checks (all from the audit's lost-content list)

Each is checked on the demo report with every kind of content, in HTML and in the PDF's page images:
1. **Header:** the title block ("Weekly report · Internal", project name, "Week ending Friday 16 October 2026 · for <client>") and the chosen logos at its right (the firm's always; client and partner as ticked). No duplicate "Weekly report" title and no empty heading.
2. **Health:** the coloured flag block, the six-week strip with its two dates, "Last week: <state> (<date>)" and the reason; colour is kept in print.
3. **At a glance:** the figures strip with the same cells, the red overdue figure, in the report's order.
4. **Milestones:** the timeline **as a picture** (today marker, slip line, month ticks), then a 16 px gap, then the table with Milestone, Agreed, Expected (with "+14"), Progress and State chips; dates as DD-MM-YYYY; a done milestone reads "achieved <date>".
5. **Tables:** Risks and issues with the Response column and the priority chips; Overdue actions with the Late column in red; Decisions as on screen; an **empty table shows the screen's sentence** ("Nothing is needed from anyone this week."), not a header row.
6. **Text:** headings with the accent square and their style; text sections with their formatting; **no empty heading** for an untitled pane; images and pictures present, never dropped silently.
7. **Left out:** hidden sections, rows, figures and milestones are absent (and not in the file's source either).
8. **Client report:** the same renderer, client-visible items only; a client export is possible only from the locked data; the server re-checks hidden and client content before writing (as `creaite_doc.clean` and the leak findings do today).
9. **Dates everywhere DD-MM-YYYY** (the "Today" style long dates stay as written on screen).
10. **Light print theme** fixed for the file (no dark theme leaks into an export); A4; sections do not split across pages where avoidable; the picture and its table stay together.
11. **PDF** equals the HTML apart from page breaks; page numbers optional, not required.
12. **Fallback:** with no live server or browser the Python renderer still produces a file, and the user is told it is the plain version.

## Not in this item

Word (#227), the save location and name-clash (#220), the hub (#221). The free-text section is #218.

## Test (standing rule)

Automation map: 1 to 7, 9 and 12 scriptable (the exported HTML's structure, classes and text; Chrome-rendered image comparison against "Show as exported"); 2, 4, 10 and 11 also judgement on the screenshot sheet; Word is not here. Test file named by Team Stark for the release.
