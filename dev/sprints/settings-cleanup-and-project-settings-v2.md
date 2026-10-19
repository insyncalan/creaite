# Settings clean-up, and Project settings v2 (for Alan to decide)

Written 19-10-2026 from the 2.5.0 build (a throwaway vault, fictional data), after Alan: "we've moved on from #103 by creating the project settings pages"; clean up Settings, then improve the project settings page. #103 is superseded by this. Mockup: `dev/mockups/project-settings-v2-mockup.html` (on the 2.5.0 snapshot; the older mockups keep the 2.1.0 look).

## Part 1: what stays in Settings, what moves, what goes

**Today's Settings:** Essentials (about 16 settings), People and projects (3 sections), Advanced (about 25 groups, about 140 settings, "Everything else" built from old categories, so many titles repeat), Health.

### Moves to the project settings page (it is per project)
| Today in Settings | Where it goes |
|---|---|
| Advanced › Reminders: "<project> client report" rhythm for each project | Already in each project's Reporting; **delete from Settings** (keep "Reminders on" and "Dismissed reminders") |
| People and projects › **Projects and register** (archive and restore each project, Show archived, "this project needs a …") | Each project's **Archive and close**; the Projects page gets a "Show archived" switch and restore on archived rows |
| People and projects › **Workstreams** (lead, keywords, rename, merge, retire, per project) | **A Workstreams section in each project's settings** (Alan reversed his 18-10 "stay in Settings" when he asked for this clean-up; confirm) |
| Advanced › Meeting prep and Intake › "Meeting series projects" | The project's settings (needs Stark to confirm what it does) |

### Moves to the People page (a global register, not a project thing)
**People and projects › People** (add, edit email, aliases, organisation, role; rename or merge; hide; VIP and remind switches; filters) moves to the **People page** and each person's page, with "Fix spellings" for merge. The project's "People on this project" opens a small form in place instead of "the register in Settings".

### Stays in Settings (global, not per project)
- **Essentials**, unchanged: You, Your day, Saving and review, People I follow, Look and help, Safety.
- **Advanced**, regrouped (below).
- **Health** (system: live server and backups, set-up, diagnostics, version, stop the server).

### Removed or merged
- **Legacy** (People, Hidden people, Workstreams, Hidden workstreams, "old list"): remove once Stark confirms nothing reads them.
- **Repeated groups merged into one each:** AI drafts (three places, one list), Sweep (two), People I follow (two; the browser notification joins the first), Close the day (two), Look and help (two), Safety (daily backup in Essentials, retention in Advanced: one place), Opening views and Work and views.
- "Help › Start here seen" is an internal flag; it becomes a quiet "Show the first-run help again".

### Settings after the clean-up
Sidebar: **Essentials · Advanced · Health** ("People and projects" retired). Advanced in nine groups: **Work** (opening views, board, project page, files, sort, Excel export), **Review and warnings**, **Sweep and Intake**, **AI drafts**, **Reports and minutes**, **Current state**, **Archiving and backups**, **Folders and OneDrive**, **Server, search and logging**. Settings search still finds every item and jumps to its new home.

## Part 2: Project settings v2

**What is wrong today** (six tabs, one small card each):
- Each tab is a little card in a mostly empty page; you click six times to see one project.
- No summary of the project, so you cannot tell which project you are in or what state it is in.
- People says "opens the register in Settings"; there is no Workstreams; Reporting and Logos are two tabs for one job; Archive and Close look like any other setting.

**The redesign (shown in the mockup):**
1. **One scrolling page**, with a sticky side list of anchors (it highlights where you are); the tabs go.
2. **A summary header:** name, code, Active, health, the client and the two people who matter, four numbers (open actions, risks and issues, next milestone, last client report), and Open project and Open reporting.
3. **Sections in order of use:** Project, People and partners (adds an open-items count per person), **Workstreams** (new here), Milestones, **Client report and logos** (together), then **Archive and close** last, set apart with a red-tinted border so it is clearly the serious one.
4. Each change still saves on its own, with Undo; nothing about saving changes.

**Decisions for Alan**
1. Settings clean-up as above (Workstreams and the register out of Settings; the category retired)?
2. One scrolling page instead of tabs?
3. Anything to add to the header (for example the weekly report status)?

## Build notes (once approved)
Settings: tests for the removed sections' pages and the settings search; a migration that keeps every saved value (Alan's "never reverse saved layout" rule applies to settings too). Project settings: the shared settings stay one setting with the reporting hub's cog (as today). Tests: the existing `test_project_settings*.py` updated, plus anchors and the sticky list.
