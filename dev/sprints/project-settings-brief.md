# Brief: project settings as a full page (#228, release 2.5)

Product Manager, 18-10-2026, for Team Stark. Mockup (approved and locked by Alan, 18-10-2026): `dev/mockups/project-settings-mockup.html` (built on the project page snapshot; click the cog at the foot). Nothing is built. Sample data only.

## What the user sees

1. **A Settings icon (cog) at the foot of the project page,** beside the Reports icon (#225) and Browse files, same size and style, name on hover. It opens a **full page**, not a side panel: breadcrumb (Projects › the project › Settings), "Project settings", the project's name and code, and "Each change saves on its own, with Undo."
2. **The app's own settings layout:** a search box and a vertical list of categories on the left, cards of labelled rows on the right (a label, a line of help, the control).
3. **Categories (no Workstreams here: Alan, 18-10-2026, workstreams stay in Settings › People and projects):**
   - **General:** name, client, code (changing it renames every item and asks first), status (Active, On hold, Closed), the project's folder with Open folder.
   - **People and partners:** the people on this project (name, role, organisation; add, edit, remove) and the partner organisations (name, people; add, edit, remove). People come from the people register; adding one here adds them to the register.
   - **Logos:** the firm's logo (shared by every project, always shown), the client's, and **one row for each partner organisation defined in People and partners** (Alan: the Logos page gets its partners from there; adding or removing a partner organisation there adds or removes its logo row here). Add, Change and Remove, as in the reporting hub's settings; the same files, the same names (`firm.<ext>`, `<CODE>-client.<ext>`, a partner's `<CODE>-partner-<n>.<ext>` or as Stark decides), kept out of git.
   - **Milestones:** the project's milestones (id, name, agreed and expected dates, state) with Add and Edit, and a link to the milestones page.
   - **Reporting:** the client report on or off (the same setting as the reporting hub's cog), how often, the reminder, the weekly report day, and Open reporting.
   - **Archive:** Archive this project and Close this project, each asking first; nothing is deleted.
4. **Search** filters the rows across all categories.

## Rules

Each change saves on its own, with Undo (as the milestones peek does today). A setting here and the same setting elsewhere (the client report, the logos, Settings › People and projects) is one setting. No guarded file should be needed; if one is, say so first. Related: #103 (review of Settings › People and projects). **Workstreams stays in Settings › People and projects (Alan, 18-10-2026)**: do not retire that card; if #103 later retires the rest of that page, the Workstreams card needs a home first.

## Open for Stark

How partner logos are named when a project has more than one partner (the mockup shows one); whether Settings › People and projects stays or is retired in favour of this page (Alan has not decided).

## Done when

The cog opens the page from the project page; each category shows and saves as described; Logos lists exactly the project's partner organisations; the setting changes appear in the reporting hub and the reverse; light and dark, both palettes; keyboard use; Undo works.

## Test (standing rule)

Scriptable: the cog's place, the categories (no Workstreams), each setting saves and undoes, Logos follows the partners, the shared settings agree with the hub; judgement: the layout on the screenshot sheet. Test file named by Stark.
