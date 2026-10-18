# Brief: one Reporting hub for the internal and the client weekly report

Product Manager, 18-10-2026, from Alan's requests and screenshots. Mockup: dev/mockups/reporting-hub-mockup.html (built on the real weekly snapshot; use the Internal, Client and Side by side switch; the week control; "Client report" settings at the top right; Export and Approve menus; the foot bar switches "Client report: required / not required", opens the settings and the export name-clash dialog). **No development on reporting until Alan gives the go-ahead after a complete UI review.** Alan's plan: reporting moves into release 2.4; the defects are for the next patch (he wrote 2.3.1, which is already out, so I read it as the next patch, 2.3.4; Jarvis to confirm). This brief supersedes dev/sprints/weekly-report-tidy-brief.md where they differ; that brief's items stay as the detail for the defects.

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
- **One shared toolbar:** zoom, Show as exported, Check this report, Export, **Approve** (Approve the internal report; Approve the client report, available once the internal one is approved). Actions apply to the report in view, or both when side by side (Export asks which, or exports both).
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

## Everything else in the mockup (from the earlier brief, now in both reports)

Discreet section menu; eye icons; "Add from the tracker" (existing open items, client-visible only for the client report); the free-text section with the whole editor (v2.4.0, still subject to the export gaps named in the earlier brief); export fidelity for the health block, the figures, the timeline picture and the milestone list in HTML, Word and PDF; exports that save to the Reports folder and say where, with the **name-clash choice (Add a number, Rename, Overwrite)** as drawn; and the approved Check this report (#170).

## Client-safe

Unchanged: the client report holds only client-visible items; its text sections and edits are separate from the internal report's until "Match internal"; the internal report's notes and the check's findings never appear in the client report or any export.

## Release

Reporting moves into 2.4 (hub, one sheet component, client switch, text section). The small defects (header, 96 px indicator, eyes, menu, export, save to disk) are patch-sized and can ship in the next patch, but Alan has said no reporting development until his UI review is complete.

## For Alan (open questions)

1. **Default for a new project:** client report on or off? I recommend off.
2. **Side by side: export both together?** I recommend Export asks "Internal, Client or Both".
3. **Where the client switch lives:** the hub's settings and Settings › Projects (same setting). OK?
4. **Retire the separate client report page?** I recommend yes: one hub, reached by the same links.
