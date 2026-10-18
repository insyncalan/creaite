# Brief: one Reporting hub for the internal and the client weekly report

**Status: the mockup is LOCKED, approved by Alan on 18-10-2026 (first approved version: commit 88ad88e1; revised for the header logos, Rounds 8 and 9, and re-approved by Alan on 18-10-2026 at commit d752dbd4). All reporting items are in release 2.4. No reporting development starts until Alan gives the go-ahead.**

Product Manager, 18-10-2026, from Alan's requests and screenshots. Mockup: dev/mockups/reporting-hub-mockup-2026-10-18b.html (the current copy, without the Check this report button; the approved original c6f549ed stays as history in dev/mockups/reporting-hub-mockup.html) (built on the real weekly snapshot; use the Internal, Client and Side by side switch; the week control; "Client report" settings at the top right; Export and Approve menus; the foot bar switches "Client report: required / not required", opens the settings and the export name-clash dialog). **No development on reporting until Alan gives the go-ahead after a complete UI review.** Alan's plan: reporting moves into release 2.4; the defects are for the next patch (he wrote 2.3.1, which is already out, so I read it as the next patch, 2.3.4; Jarvis to confirm). This brief supersedes dev/sprints/weekly-report-tidy-brief.md where they differ; that brief's items stay as the detail for the defects.

## What Alan asked for in this round

1. The report does not need the repeated "Weekly report / <project>" header: "Internal" in the header is enough.
2. The health indicator is reduced in width by 20%.
3. The editing experience must be **identical** in the internal and the client report: every defect and improvement for reporting applies to both.
4. What are the "firm, client, partner" check boxes on the client report?
5. **One editing hub** for both reports: review or edit one, the other, or both side by side.
6. **A setting for whether a separate client report is needed**: client reporting is not mandatory for every project.

## 1 and 2: the sheet

- The page's top title block (title, project name, "Internal") is removed; the title block that remains reads "Weekly report · Internal" (client: "Client report · Client"), the project, and the week or period. One header, not two.
- The health indicator is 96 px wide (was 120 px). The six-week strip, its two dates and the Change button (`.btn.sm`) stay inside that width; the flag text is 12 px and never wraps.

## 3: identical editing

Today the client report has its own renderer (different health flag, figures, tables, match controls) from the internal one, so fixes made to one miss the other. The mockup uses **one sheet for both**: the same sections, section menu (discreet, with icons), eye switches (not dots), "Add from the tracker", text sections, "Check this report", "Show as exported", Export and Approve. What differs is only the audience: the client report's wording, its smaller set of figures, its client-visible-only items, and a per-section **"Matching internal / Edited for the client" with a "Match internal" button**, which already exists for the client report and is kept.
**Done when:** a change to the sheet component is visible in both reports; both pass the same tests.

## 4: the "firm, client, partner" boxes

They choose which **logos print in the header of this client's reports**: the firm's (always on, so greyed), the client's, and a partner's. They were three bare check boxes in the report header with no logo shown, which is why they read as meaningless. In the mockup they move into the client report settings as three labelled tiles (a logo mark, a name, a line saying what each is) and leave the page.

## 5: the Reporting hub

One page for a project's weekly reporting, replacing the separate weekly and client pages:
- **Switch: Internal | Client | Side by side.** Side by side shows both sheets at a readable size with their scrolling kept together, so a client section can be compared with the internal section it came from.
- **Week control** (earlier and later week) and **status chips**: "Internal: draft", "Client: waits for the internal report" (the client facts lock when the internal report is approved, as today).
- **One shared toolbar:** zoom, Show as exported, Export, **Approve** (Approve the internal report; Approve the client report, available once the internal one is approved). Actions apply to the report in view, or both when side by side. Export asks Internal, Client or Both only when the project's client report is on; with it off it exports the internal report without a question.
- Reached from the project's reporting space, from Reports, and from the weekly report reminder.

## 6: client report on or off, per project

- **Client report settings** (top right of the hub; the same setting as Settings › Projects): "This project needs a separate client report" (on or off), how often (weekly, fortnightly, monthly: exists today), the client's name on the report, a reminder on the due day, and the logo tiles.
- **When it is off:** the hub shows only the internal report; the Client and Side by side switches are disabled with a tooltip; a quiet note says "This project has no client report"; no client reminders; Approve offers only the internal report; the Reports page lists only internal reports. Nothing already written is deleted, and turning it on again restores it.
- Default for existing projects: on (as today), so nothing changes until Alan switches a project off. Default for a new project: Alan's choice (my recommendation: off, and turn it on when the first client report is wanted).

## Round 2 changes (Alan, 18-10-2026)

- **Rename field:** in the name-clash dialog the Rename box is the full width of the dialog and shows the whole file name.
- **Folder link:** "Example Programme › Reports" is a link, in the dialog and in the saved message, and opens the Reports folder in Finder on click.
- **No client report, no selectors:** when the project has no client report the Internal | Client | Side by side switch is not shown at all (not disabled), nor any client status; the page is just the internal report.
- **Tidier controls:** one control height (32 px) across the bar and the toolbar; the week control is one joined control with real arrows; the zoom is one joined control; the status moves from chips in the bar to a quiet label on each report ("Draft", "Waits for the internal report"); the client settings button reads "Client report: on" or "Client report: off", the detail living in its panel; Export and Approve are full-size buttons and their menus have an icon, a name and one line each, aligned, with the unavailable item greyed and its reason shown.

## Round 3 changes (Alan, 18-10-2026)

- **Client report settings is a cog icon only**, no text (tooltip and screen-reader name "Client report settings: on" or "off").
- **All controls on one line:** view switch, week navigation, zoom, Show as exported, the cog, Export and Approve. When the window is too narrow for the words, "Show as exported" and "Check this report" fall back to icons (the page measures its own line; no wrapping).
- **The scrolling header is shown as in the live version** (the approved #202 and #207 behaviour): scroll the report down and the search and ask creaite bar and the title block go at once, leaving the one line of controls with a short title ("Weekly reporting, project, week"); they come back only when you are at the very top, and no button on the line brings them back. The report gets the freed room.
- **Week navigation options** (the foot bar switches them): **Stepper** (what we had: arrows and a date), **Menu** (the date opens a list of weeks, each with its health dot and the internal and client status, and a jump-to-date box) and **Ribbon** (the last six weeks as small pills, each with its health dot, today's draft dashed, the open week dark, plus a chevron that opens the Menu for older weeks). **Recommendation: the Ribbon with its Menu.** The six pills are the same six weeks as the health strip, so the health trend and which weeks are approved show without opening anything; one click moves to a week. It needs width, so on a narrow window it falls back to the Stepper with the Menu.

## Round 4 changes (Alan, 18-10-2026)

- **Space under the milestone picture:** in the report, and in "Show as exported", the milestone list starts 16 px below the timeline picture, never touching it. The same rule in the HTML, Word and PDF export (a gap between the picture and the table).
- **The client report setting is persistent:** it is stored on the project and holds for every future report until Alan changes it (no per-week question). Reports already written are kept as they are; turning it off deletes nothing and turning it on again restores the client side. The panel says so in one line.

## Round 5 changes (Alan, 18-10-2026)

- **The cog is the right-most control** (after Approve).
- **Week navigation, Menu option:** just the date with a drop-down list; no "<" and ">" arrows. (The Stepper option keeps its arrows; the Ribbon has none.)
- **Trackpad zoom stays:** a pinch (or Ctrl or Cmd with the scroll wheel) over the report zooms it in and out, as in the live report, in the internal, client and side-by-side views; the zoom control shows the percentage, the buttons step it, and clicking the percentage returns to Fit. In the mockup, pinch over the report to try it.
- **Do all exports match the report as edited?** Not verified, and for HTML we know they do not (the defect in item 5). From the code, not from a test: an export is made on the server (`/api/report/export`, `report_server.py` and `report.py`) by a renderer separate from the on-screen sheet, so the two can drift; PDF is labelled "printed from the page", so it likely inherits the HTML's gaps; Word uses the firm's template, a third renderer. Team Stark's scout also found code block, table and picture have gaps in all three. **Needed before any build: a read-only export audit** that, for the demo report with every kind of content, lists per section what each of HTML, Word and PDF loses compared with "Show as exported". The fix direction to decide on after the audit: **one renderer** (the sheet's own markup and styles) for HTML and PDF, and a checked mapping for Word, with an automated comparison as the test.

## Round 6 (Alan, 18-10-2026)

- **Approved:** the icon controls on the hub's toolbar (Show as exported, the cog) as drawn.
- **Defect: remove the "Weekly report" and "Client report" buttons from the bottom of the project page.** They are two bare buttons that open the two separate report pages. With one hub they are redundant. **Alan: at the bottom of the project page, beside the Files icon, a Reports icon opens reporting for the project (the hub).** Other ways in: the project page's Reporting card, the Reports page, and the weekly report reminder. Done when neither button is on the project page, the Reports icon sits beside the Files icon (same size and style, a name on hover, opens the hub for that project), and every link to a report still works. It touches reporting, so it waits for the hold with the rest.

## Round 7: the export audit (Team Stark, read-only, 18-10-2026)

Full audit: dev/sprints/weekly-report-export-audit-2026-10-18.md (on branch export-audit-doc, with three screenshots). **Answer: no, the exports are not faithful to the report as edited.**

- **Why:** the screen is drawn by the dashboard's components; all three exports are drawn by a separate Python renderer that knows only five simple section types. **The PDF is the HTML export printed by Chrome**, so HTML and PDF match each other (apart from page breaks); Word is a third rendering through the firm's template.
- **Lost in HTML and PDF:** the header's logos, title block and client line (and a duplicate "Weekly report" title with an empty heading); the health flag block, the six-week strip and "Last week"; the At a glance boxes' look; the milestone timeline picture and the Agreed, Expected and State table (replaced by a bullet list in ISO dates, which also breaks the DD-MM-YYYY rule); the Response and Late columns and priority chips in the tables; empty tables show a header row instead of the screen's sentence; an empty heading for an untitled pane; images dropped silently. Hidden sections and rows are correctly absent.
- **Lost in Word:** the same, with the health flag printed twice, the At a glance boxes as "Label: value" lines, and the firm's logo instead of the report's chosen logos. Checked on page 1 only (LibreOffice is not installed here).
- **Not run:** the client report and minutes exports use the same code and probably lose the same things.

**Recommendation (for Alan's decision):**
1. **HTML and PDF: one renderer, the sheet's own "Show as exported" view** becomes the export (the page's DOM, cleaned, with its stylesheet inlined and logos embedded; the PDF prints that same page). About **5 to 6 Sonnet days**, no guarded file. The Python renderer stays as the fallback when no browser is available. The alternative, porting the missing drawing into Python, is 3 to 4 days but keeps two renderers that will drift again.
2. **Word: keep the separate writer and close the gaps** (timeline and health strip as pictures made from the same exported sheet, logos, full tables, one title, DD-MM-YYYY, no empty sections). About **3 to 4 days**. Converting HTML to Word is not recommended (a new library, ignores the firm's styles, a worse result).
3. **Risks to manage:** re-check hidden and client content on the server before writing a file; a fixed light print theme; the fallback path needs its own tests; hand checks 16 and 74 change. Word can only be checked by XML here; add LibreOffice to the development tools (Brewfile) or accept hand checks on the laptop.
4. **Order:** the export work is the foundation for the hub, the free-text section (#218) and the HTML export defect (#219); it should come first. Total about **8 to 10 Sonnet days** across HTML, PDF and Word.
**Alan's decision (18-10-2026): approved.** One renderer for HTML and PDF (the sheet's own exported mode, with the Python renderer kept as the fallback), and a repaired Word writer. **LibreOffice may be added to the development tools** (dev/Brewfile; development only, never needed to run creaite) so Word and PDF output can be rendered and compared in tests. Still no reporting development until Alan gives the go-ahead.

## Round 8 (Alan, 18-10-2026): logos in the report header

The report header carries the **firm's logo** (always), and the client's and a partner's logo when they are ticked in the client report settings, at the right of the title block, in both the internal and the client report. The mockup shows placeholder tiles ("Firm logo", "Client logo"); ticking or unticking a logo in the settings panel changes both headers at once. **Where logos are added today (read from the code, not run):** by hand, as files in the live vault's `system/branding/logos/` (kept out of git, never committed): `firm.png` for the firm (also .jpg, .jpeg or .svg), and per project `<CODE>-client.png` and `<CODE>-partner.png`. The server only reads them (`report_doc.logos`, `POST /api/report/logo`); I found no screen that adds one (a code comment mentions "Settings › Projects › Report logos", which I could not find in the settings code). **Alan's requirement (18-10-2026): click the logo's place in the report header and upload the logo there**; the file is then saved into the logos folder under the right name (`firm.<ext>` for the firm, `<CODE>-client.<ext>` and `<CODE>-partner.<ext>` for the project) and appears at once in both reports and every export. In the mockup an empty logo place reads "Add firm logo" or "Add client logo" and opens a file chooser (nothing is saved or kept by the mockup); a filled one shows the picture and "Change the … logo" on hover. The settings panel's logo tiles carry the same Add or Change button. **So the hub's settings panel needs an "Add logo" control on each logo tile** (choose a file, see it, replace or remove it), saving the file into `system/branding/logos/` under that name through the same file-change route as other files. Logos never go in the repo, the mockups or the design system: mockups show a placeholder only. The logos are the real picture files the user has set (not drawn by the mockup), they print in every export (HTML, PDF and Word: today none of them do; see the export audit), and a missing logo file shows nothing, not a broken picture.

## Round 9 (Alan, 18-10-2026): logos and transparency

How the logos keep their transparency and sit well on the page:
- **Draw them straight on the page:** a filled logo has no box, border or background (the mockup removes them), so a transparent PNG or SVG shows the page through. The picture keeps its own proportions, at most 36 px high and 180 px wide, aligned to the title block's baseline.
- **Prefer PNG with transparency, or SVG.** A JPEG has no transparency, so it shows a white rectangle on any tinted page; when a JPEG is added, say so ("A transparent PNG or SVG sits better") and offer to keep it as it is.
- **Trim empty margins on upload** (the transparent or white border round the artwork) so logos of different shapes line up and get the same visual weight; keep the original file untouched and trim only the copy that is drawn.
- **Dark theme:** a dark logo on a dark page would vanish, so on dark it sits on a small light plate (shown in the mockup). The exports use the light print theme and need no plate.
- **Exports keep transparency:** PNG and SVG carry it into HTML and PDF; Word keeps a PNG's transparency; an SVG is converted to a PNG for Word. Check this in the export audit's tests.
- **Optional later:** a light and a dark variant of each logo (two files), chosen by the theme.

## Round 10: final choices (Alan, 18-10-2026)

- **Week navigation is the Menu**: the week's date with a drop-down list of weeks (health dot, internal and client status, jump to a date); no "<" or ">" arrows. The Stepper and Ribbon options are dropped from the spec.
- **The toolbar uses icons**, always: zoom (− Fit +), Show as exported, Export, Approve, and the cog last. The words appear as tooltips and screen-reader names.
- The mockup's foot bar keeps only what demonstrates behaviour (client report required or not, settings, the export dialog); there are no design option switches.

## Round 11 (Alan, 18-10-2026, via Jarvis): #170 is out of 2.4.0

"Check this report" (#170) stays out of v2.4.0 and its button is removed from the hub toolbar. The current mockup is the dated copy `reporting-hub-mockup-2026-10-18b.html`, identical to the approved one (c6f549ed) except for that button; the approved original stays as history. **Approved by Alan on 18-10-2026**: the copy is the current locked mockup.

## Round 12 (corrected 18-10-2026): deferred after 2.4.0, checked by Stark (his comment on #135, 22:10)

Differences between the build and the locked mockup. None holds the release. **Correct as written:**
1. **Click the logo's place in the report header to add or change the logo** (Alan's requirement, Round 8). Not built: in 2.4.0 a logo is added or changed in the cog panel only. Size M. **First.**
2. **Partner logo tile default.** The build has it ticked by default; the mockup has it unticked. Size S. **Needs Alan's call:** the build reads "no logos line = every logo on", so changing the default would change what existing projects print. Options: (a) new projects start with the partner unticked and existing projects are unchanged (my recommendation); (b) every project's partner logo is unticked until chosen.
3. **Section menu width:** 288 px in the build, 300 px in the mockup. Size S.

**Struck from my earlier list (wrong or already done):** the toolbar is icons only, always (tested); Export asks Internal, Client or Both only when the client report is on (tested); the sparkle beside the health reason is built (by H2); #170 is a different feature and is out.

**Added by Stark and Cap:**
4. **Editable Side by side** (#230): both reports editable at once. **Built by Stark on branch p241-sbs (45741385), not in 2.4.0; ships in the next release after Cap's client-leak re-review.** Each pane is its own report (own edits, autosave, save line, AI bar and Match internal); ⌘S saves only the pane in focus; zoom is one shared control; the panes scroll together; Esc closes only the active pane's menu. An approved internal report no longer locks the client page. Limits: only one click-to-edit summary editor is open at a time, and the section menu is one popup, so an AI bar menu can't be open together with it.
5. **Grey pane and label-row layout** (Cap #6): the report's pane and the label row differ from the mockup. Size M.
6. **Cap's low findings on the client-report setting (L4 to L7 and L10)**, from Team Cap's comment on #135 (20:25), in plain words. Sizes S to M together; none touches client data; L6 and L7 are older than 2.4.0:
   - **L4:** the setting line is found by the first match anywhere in a project's CLAUDE.md, including inside a code block or another section. A fenced "Client report: off" gets toggled instead of a real line being added (the Python reader takes the same first hit, so both agree). Fix: read and write only the project's own settings section.
   - **L5:** no lock or version check, so changing settings in two browser tabs at once can lose one change (within one tab the page keeps them in order). Fix: a version check on save.
   - **L6:** when a settings save fails, the message shows an absolute file path (the older generic handler). Fix: say what failed without a path.
   - **L7:** the file-save route accepts `projects/<anything>/CLAUDE.md`, so it can create a CLAUDE.md under `_Archive`, `_portfolio` or a made-up folder (older; token-checked only, no origin check). Fix: accept only a real project's folder. This may touch a guarded file, so Jarvis applies it.
   - **L10:** the server does not refuse to build a client draft when the setting is OFF; it is hidden on the screen only. Fix: refuse on the server too.
7. **Neutral week-list dots** for weeks the open report does not hold. Size S.
8. **Side by side readable at about 310 px a page at 900 px wide:** Alan accepted this (18-10-2026); no action.

### Scope proposal for the next release (one release, no point release per defect)

Item 1 first, then 4, then 5; items 2, 3 and 7 are small and ride along once Alan decides 2; item 6 is sized when Cap's details are in. Recommendation: one release containing 1, 4, 5, 6, 3 and 7, with 2 as option (a). Hand checks follow the release and never hold it.

## Everything else in the mockup (from the earlier brief, now in both reports)

Discreet section menu; eye icons; "Add from the tracker" (existing open items, client-visible only for the client report); the free-text section with the whole editor (v2.4.0, still subject to the export gaps named in the earlier brief); export fidelity for the health block, the figures, the timeline picture and the milestone list in HTML, Word and PDF; exports that save to the Reports folder and say where, with the **name-clash choice (Add a number, Rename, Overwrite)** as drawn; (the Check this report button, #170, is out of 2.4.0).

## Client-safe

Unchanged: the client report holds only client-visible items; its text sections and edits are separate from the internal report's until "Match internal"; the internal report's notes and the check's findings never appear in the client report or any export.

## Release

Reporting moves into 2.4 (hub, one sheet component, client switch, text section). The small defects (header, 96 px indicator, eyes, menu, export, save to disk) are patch-sized and can ship in the next patch, but Alan has said no reporting development until his UI review is complete.

## For Alan (open questions): answered 18-10-2026

1. **Default for a new project: client report OFF.** Decided (as recommended). Existing projects stay on, as today.
2. **Export and the choice of report:** the Export menu asks **Internal, Client or Both only when the project's client report is ON**. With it OFF, Export just exports the internal report, with no question. (This replaces my recommendation to always ask.) The locked mockup's Export menu shows only the formats, so the visible mockup does not change; this is the rule for the build. With the client report on, the question comes after the format is chosen; "Both" saves two files (each with its own name-clash choice if needed) and one message naming both.
3. **Where the client switch lives:** in the hub's cog panel and in Settings › Projects, **one setting**, whichever is used. Decided.
4. **The separate client report page is retired.** One hub, reached by the same links. Decided.
