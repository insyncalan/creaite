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
2. ~~A summary header~~ **Dropped by Alan, 19-10-2026.**
3. **Sections in order of use:** Project, People and partners (the register's own table, below), **Workstreams** (new here), Milestones, **Client report and logos** (together), then **Archive and close** last, set apart with a red-tinted border so it is clearly the serious one.
4. Each change still saves on its own, with Undo; nothing about saving changes.

**Decisions for Alan**
1. Settings clean-up as above (Workstreams and the register out of Settings; the category retired)?
2. ~~One scrolling page instead of tabs?~~ **Accepted by Alan, 19-10-2026.**
3. Anything to add to the header (for example the weekly report status)?

## Build notes (once approved)
Settings: tests for the removed sections' pages and the settings search; a migration that keeps every saved value (Alan's "never reverse saved layout" rule applies to settings too). Project settings: the shared settings stay one setting with the reporting hub's cog (as today). Tests: the existing `test_project_settings*.py` updated, plus anchors and the sticky list.

## People on the project page (Alan, 19-10-2026)
Alan wants the original People register view here: the columns **Name, Email, Organisation · role, Aliases, Actions, RAID**; edit and delete; search and the filter; a name opens that person's work page; right-click drafts an email to them with their work items. **No merge or rename** (Fix spellings is dropped for people).

**Who is shown.** A person is on a project when they own an item there or are named on it (as today's project memory does). Counts are for this project. A small project code beside a name shows they are also on another project. Email, aliases, organisation and role are one entry for the person, the same on every project (Alan, 19-10-2026: "save confusion"). Only the Actions and RAID counts are for the project.

**People on no project.** They are shown in a quiet group under the table, "Not on any project yet", on every project's page, each with **Add to this project**, until they are added to one. This keeps Alan's idea (nobody is missed) without mixing them into every project's table. Once a person is on a project they leave that group everywhere.

**Delete.** On a project the bin means **Remove from this project**, not delete from the register (a person's global record is never removed by accident). Deleting from the register is on the People page.

**Filter.** Everyone on this project, also on other projects, needs attention (no email); plus the search.

## More on the People view (Alan, 19-10-2026)
- **Richer filter:** today's two-pane panel: WHO (Project, How they're involved, Organisation, Followed) and TIDY UP (In the register, Needs attention), each with options, counts and a live "Showing x of y", Clear all and Done.
- **Edit a person** opens a form: Full name, Email, Aliases, Organisation and Role (one entry, the same on every project), On projects (tick the projects), and Follow this person (VIP alerts). Buttons: Remove from this project, Cancel, Save. A person with no email can still be saved and still gets a drafted email, with nothing in To.
- **A star beside the name** in the People list for a followed person, on Alan's screen only. Its accessible name is "Followed" (never "VIP"), and it never appears in a report, export, draft or shared page (BL-288). Caution: it does show on screen, so a screen share would reveal it; if Alan wants, a "Show stars" switch hides it.
- Workstreams: "Fix spellings: rename or merge" and "Show retired" are removed from the footer.

## Followed people (Alan, 19-10-2026)
A person marked as followed is visible **only to Alan, and only on the project settings page** (the star beside the name in People on this project, and the Follow tick in the edit form). The star **never shows anywhere else**: not in work items, not on the People page, Today, Review, Intake, a peek, a report, an export, a draft or a prep page. The existing alerts that depend on following keep working unseen, as before (BL-288). **No "Show stars" switch.**

## Decisions on the Settings clean-up (Alan, 19-10-2026)
1. **Workstreams move into each project's settings:** yes (this reverses 18-10).
2. **Duplicate people:** leave them to ask creaite; no merge in any People view.
3. **The People page is the home of the whole register:** yes, with the same columns and the same filter as the project page's People view.
4. **Delete:** on a project the bin removes the person from that project only; deleting from the register is on the People page: yes.
5. **Settings is tabs, not one long page; readable settings up front, the heavy ones in Advanced with sub-tabs** (Alan, 19-10-2026, second go). Top tabs: **Essentials** (You, Your day, Saving and review, People I follow, Look and help, Safety, plus the old "You" extras), **Work and reports** (Opening views, Work board, Project page, Files, Work and views, Reports and minutes, Reminders), **Look and help** (themes, appearance, help), **Advanced**, **Health**. Advanced has seven sub-tabs: **Review and warnings, Sweep and Intake, AI drafts, Current state, Archiving and backups, Folders and OneDrive, Server, search and logs**, with a line saying most people never open it. "People and projects" and Legacy are gone; per-project client report rhythms are removed from Reminders. Mockup: `dev/mockups/settings-v2-mockup.html`, built from the real cards. Project settings stays one scrolling page.

Still for Stark to confirm at build: nothing reads the Legacy lists, and what "Meeting series projects" does (it is not in the mockup's tabs yet).
