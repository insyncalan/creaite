# Brief: #227 repair the Word writer so it matches the report as edited

Product Manager, 18-10-2026, for Team Stark. Approved direction (Alan, 18-10-2026): keep the separate Word writer (the firm's template) and close the gaps; do not convert HTML to Word. LibreOffice is added to the development tools so the file can be rendered and compared. Evidence: dev/sprints/weekly-report-export-audit-2026-10-18.md.

## What the user must see

A Word file that reads as the same report as the screen: the same parts, in the same order, with the firm's template styling, nothing doubled, nothing missing, and nothing left out that the user hid.

## Acceptance checks

1. **Title block** from the template, once: project, "Weekly report", status, week ending; no empty "WEEKLY REPORT" heading and no duplicate title; the chosen logos in the header (the report's logos, not only the template's), keeping their transparency (an SVG logo becomes a PNG).
2. **Health:** one coloured label (not "OFF TRACK Off track"), the reason, "Last week: <state> (<date>)", and the six-week strip as a picture made from the same exported sheet.
3. **At a glance:** four cells in a small table, not "Label: value" lines; overdue in red.
4. **Milestones:** the timeline as a picture, then the table with Milestone, Agreed, Expected (with "+14"), Progress and State; DD-MM-YYYY dates; a done milestone reads "achieved <date>".
5. **Tables:** Risks and issues with the Response column and the priority labels; Overdue actions with the Late column; headers in the template's style; an empty table becomes the screen's sentence.
6. **Text:** headings, emphasis, lists and checklists (as boxes) kept; **no empty heading**; images present (placed from the picture files), never dropped silently.
7. **Left out:** hidden sections, rows and figures absent; a milestone left out of the milestone **list** is absent from the table but, as on screen ("Leaving one out tidies the list only; the timeline always shows every milestone"), still appears in the timeline picture. (Corrected 18-10-2026 after Stark's question.)
8. **Client report:** the same writer and rules, client-visible items only.
9. **No guarded file changed** (the audit: `creaite_doc.py`, `docx_tools.py`, `dev/tools/build_templates.py`).
10. **Open in Word:** the file opens without a repair prompt; page 1 and a later page checked, not only page 1.

## Test (standing rule)

Automation map: 1, 3 to 8 and 10 scriptable (the .docx's XML; a LibreOffice render to PDF and image for the page checks); 2 and 4 measurable plus judgement on the screenshot sheet (the pictures); Word itself on the laptop is live only. Test file named by Team Stark.
