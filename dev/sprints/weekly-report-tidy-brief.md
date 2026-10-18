# Brief: Weekly report tidy (defects, a free-text section and export fidelity)

Product Manager, 18-10-2026, from Alan's screenshots and requests; revised the same day after his comments. Mockup: dev/mockups/weekly-report-tidy-mockup.html (a fresh weekly report built on the real weekly snapshot: hover a section for its menu, "Add from the tracker" under a table, "Add a text section" at the foot, and the toolbar's "Show as exported"). It also carries the approved "Check this report" button from #170 as a button only. Nothing is built; the revised mockup is not approved yet. **Alan's intent: all of this goes into release 2.3.4** (it replaces the earlier 2.3.3 and v2.4.0 placement; Jarvis to confirm). Alan said the free-text section ("add free text action") is cool as drawn.

## 1. Defect: the section menu is obscured and huge

**Seen:** the menu from a section's chevron opens to the left of the page and is cut off by the side bar; its text is large.
**Fix:** a discreet menu inside the window: 13 px text, a small icon before each word, as wide as it needs. Items: Leave out of the export, Move up, Move down, Add a text section below (and Delete this section on a text section). It opens as a popup above the page, not inside the scaled page, so zoom never clips it. Esc closes it.
**Done when:** at 80%, 100% and 120% zoom and at 900 px wide, every item is fully visible; Enter opens, arrows move, Esc closes and returns focus to the chevron.

## 2. Defect: the health row

**Seen:** the Change button is huge, and the six-week health strip is wider than the health indicator above it.
**Fix (Alan: the indicator's original width was fine, so the strip follows the indicator):** the indicator keeps its original width (120 px at 100%). The six-week strip and its two dates are the same width as the indicator and never wider. Change is the small button (`.btn.sm`, 28 px). The plain app sparkle sits beside the reason.
**Done when:** the strip's width equals the indicator's at every zoom; the button is `.btn.sm`; light and dark; both palettes.

## 3. Defect: the "in the report" switch is a dot

**Seen:** every figure, row and milestone has a grey dot to include or leave it out.
**Fix:** an **eye** icon (16 px, the app's line style): open eye = in the report; eye with a slash = left out, the row dimmed. Same switch, same names, same keyboard use (Space), same tooltip. Everywhere the dot is used today: At a glance, the milestone list, Risks and issues, Overdue actions, Decisions, Asks.
**Done when:** no "◉" remains in the sheet; screen readers still hear "In the report: on/off".

## 4. Change: "Add" means bring in items that are already in the tracker

**What I got wrong:** my first mockup made new items inline. Alan meant: add more of the tracker's existing work items to the report.
**Fix:** under the Risks and issues and Overdue actions tables, "+ Add from the tracker" opens a picker of **open items not yet in the report**: a search box, tick boxes, each row ID, title, owner and priority or due date. "Add to the report" puts the ticked items in the table, marked "Added by you", each with its eye; the count line updates ("Showing 4 of 5"). Nothing in the tracker changes. To make a new item, use Work.
**Effect on the report:** the Actions table can then hold actions that are not overdue (shown "not due yet"). This also answers the earlier open question about listing non-overdue actions: yes, by this route.
**Done when:** the picker lists only open, not-yet-included items that Alan may see in this report; Add changes only the report (saved with it); an added item follows the item's later changes in the report; client report: only client-visible items are offered.

## 5. Defect: export to HTML loses the report's formatting and structure

**Seen (Alan's screenshot of an HTML export):** the report comes out as a plain document. The health flag, the six-week strip and its dates are gone (only the words "Off track" and the reason remain, as a bare heading and paragraph); a stray second "Weekly report" heading sits under the title block; At a glance is four loose boxes without the figures strip; the Milestones section is a bulleted list of names and dates with no timeline and no table; Summary is a heading with nothing under it; headings look like body text with a rule. The on-screen report and "Show as exported" look right; the exported file does not match them.
**Alan:** on export the health, at a glance, the visible milestone timeline and the milestone list must keep their look and structure, and the same goes for every other part of the report.
**Fix:** HTML, Word and PDF export reproduce: the **health block** (flag colour, six-week strip, dates, reason); **At a glance** as its figures strip with the same cells and colours; the **milestone timeline drawn as a picture** (the same marks, dates and today line as on screen, as it is now when it is visible); and the **milestone list as a table** with the same columns (Milestone, Agreed, Expected, Progress, State), the state colours and the slipped dates in red. The mockup's "Show as exported" shows the target: screen controls (handles, eyes, hints, add links) disappear, the content stays.
**Done when:** the exported HTML, opened on its own, looks like "Show as exported" for the whole report (no stray headings, no empty sections that are filled on screen); for the demo report, each of the four parts is checked in the HTML, the Word file and the PDF against the on-screen "Show as exported" view; a part Alan has left out stays out.

## 6. Feature: a free-text section, anywhere, with the whole editor

**What:** an "Add a text section" button at the foot of the report, and "Add a text section below" in every section's menu. It has its own heading (Alan names it) and a text box in **the one editor with everything it has in Notes, no exception**: heading menu (levels 1 to 3), bold, italic, strikethrough, code, list menu (bulleted, numbered, checklist), quote, link, Insert (table, picture, code block), undo and redo, the `/` menu, and AI on selected text (the sparkle and the hover bar). It moves up and down like any section, can be left out of the export, and can be deleted.
**Export:** the text keeps its formatting in HTML, Word and PDF: headings, emphasis, lists, checklists as boxes, quotes, links, tables, pictures, code.
**Release (Jarvis, 18-10-2026): this feature is #218 in v2.4.0, not 2.3.4.** Team Stark's scout: about 7 to 8 Sonnet days (about 4 in parallel): the editor profile, a Markdown-to-HTML renderer, Word table and code blocks, a picture route (guarded), tests. It shares the export path with the two export defects, so it follows them.
**Gaps for Alan's decision:** (1) **Picture:** there is no picture route for a report; it needs a new guarded route, which is Alan's decision (guard). (2) **Code block, table and picture** each have export gaps today in HTML, Word and PDF. Options for Alan: build all three with the section (7 to 8 days); or ship the text section first with headings, emphasis, lists, checklists, quotes and links, and add table, code and picture once their export works; Alan's rule so far is "no exception", so this needs his explicit yes if the second route is chosen.
**Dependency for Team Stark to confirm:** today's report sheet profile has no checklist, code, table or Insert menu because the Current state storage can't hold them and Word shows some of them poorly. This section needs its own storage that can, and an export path for each. If any element cannot be exported faithfully, say which, and Alan decides. **Alan's rule: no exception.**
**Done when:** every button of the Notes toolbar is present and works in a text section; a document using all of them exports identically (to the eye) in HTML, Word and PDF; the text is saved and filed with the report; the one editor's round-trip gate passes.

## 7. Defect: an export seems only to open, not to save to disk

**Seen (Alan):** choosing HTML opens the page in the browser, and PDF opens in Adobe. He cannot tell that a file was saved, or where.
**What the code does today (read, not run):** the Export menu calls `exportWeekly`, and the only message afterwards is a brief toast, "Exported: <file name>", with no folder. The viewer then opens (the live server's open call). I have not run an export, so whether the file reaches the project's Reports folder is for Team Stark to confirm.
**Fix:** after an export the toast names the folder and has two actions, **Show in Finder** and **Open**; the file is saved first, into the project's Reports folder (as the filed report is), and opening is a separate choice, not the only visible result. Word, HTML and PDF behave the same. A failed save says so plainly.
**Done when:** each of HTML, Word and PDF leaves a real file in the stated folder with the report's name and date; the toast shows the path and both actions work; nothing is overwritten silently (a taken name gets a number).

## Client-safe

A text section is internal until Alan matches or writes it in the client report. Tracker items added by the picker follow the client-visible flag (off by default); the client report offers only client-visible items.

## Test (standing rule)

Automation map for the release's sheet: menu fully visible at four zooms (scriptable); the strip equals the indicator's width (measurable); no "◉" in the sheet and the eye toggles (scriptable); the picker lists and adds only existing items and changes nothing in the tracker (scriptable); the exported HTML contains each of the four parts with their classes and colours (scriptable); Word and PDF fidelity (judgement on the screenshot sheet, since Word and a PDF viewer are live only); the text section adds, saves and exports (scriptable).
