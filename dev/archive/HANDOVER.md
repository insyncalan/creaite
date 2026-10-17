# Handover — creaite

This captures the design conversation (October 2026) so it can be resumed from any Claude login. Point Claude at this file together with `CLAUDE.md`. The full BRD should be exported alongside it as `dev/BRD.md`.

## What it is

**creaite** (all lowercase) is a personal reporting system for a portfolio of fewer than 5 projects:

- **Inputs:** meeting minutes and Teams transcripts, plus Outlook mail and Teams chats.
- **Processing:** Claude extracts actions, decisions, risks and issues, and proposes them for review.
- **Record:** approved items are written to `system/tracker.db` (SQLite), with `tracker-view.xlsx` as the Excel editing view.
- **Outputs:** a local HTML dashboard, plus per-project weekly status and client reports. Portfolio-level reporting is in the backlog.

## Final decisions

| Topic | Decision |
|-------|----------|
| Name | creaite (all lowercase). The folder is still called "the vault" in the docs; the database stays `tracker.db` |
| Folder structure | The root holds only `CLAUDE.md`, `dashboard.html`, `tracker-view.xlsx`, `inbox/`, `projects/`, `system/` and `dev/`, plus the hidden `.claude/` and `.git/`. `projects/` has one folder per project (memory, minutes, transcripts, documents, reports) and `_portfolio/` (cross-project meetings, `PORTFOLIO.md`, `project-register.md`). `system/` is the engine: the database, staging, history, backups, scripts, templates and `config/schedules.md`. `dev/` holds build material. All locations are defined in `system/scripts/paths.py` |
| Skills | All prefixed `cx-`. All seven active skills are specified: **cx-minutes**, **cx-sweep**, **cx-review**, **cx-edit**, **cx-weekly-report**, **cx-client-report**, **cx-setup**, and since v1.2.0 **cx-steerco** (the steering one-pager, BL-92) and **cx-prep** (BL-98). **cx-setup** brought into scope (was BL-05); **cx-chase** stays in the backlog |
| cx-minutes | Manual only. Three modes: new files (transcripts in `inbox/` first), a named file, or a calendar meeting (transcript and chat pulled from Microsoft 365). Draft minutes in Word from `system/templates/minutes-template.docx` via the docx skill, held for review. On approval, the minutes and transcript are filed in **every** matched project (duplicates are fine). The project is matched on meeting title and transcript. Private meetings and duplicates are skipped; you're told about duplicates. Your actions carry your full name as owner. "re-extract" after editing a draft. Alan will supply his own minutes template later |
| cx-sweep | Inbox, Sent Items, Teams chats and channels. Project signals only; weak matches go into a separate "Possible" section. References only, never copies. Minutes and transcripts attached to mail go to `inbox/`; other documents are listed for you to file. The first run looks back 14 days. **Creaite rule:** the sweep is due daily from 07:00 and runs at session start if overdue; the app's scheduler is optional. Server-side Outlook rules (category per project code) give it a strong signal |
| cx-review | Grouped by project, with "Needs a project" first. Bulk approval never covers draft minutes, new decisions or new risks. Explicit "apply". "undo last apply" can be repeated, and skips items changed since. Stale items (over 7 days) are flagged and never expire. The Excel Review sheet is kept as an alternative |
| cx-edit | Plain English for changing and adding items, project details (health needs a reason), several items at once (with a preview), memory, the register, and adding or closing projects (new projects get folders, a register row and a memory file). Before → after; your confirmation records approval; written at the next apply. Never deletes |
| cx-weekly-report | Week runs Monday to Friday, labelled by the Friday date. Manual, with a reminder from Friday 12:00. Blocks projects with pending review items. Quiet weeks still get a report. Proposes health with reasons, an updates row and a current-state memory rewrite; drafts a Word report (`weekly-report-template.docx`, to be refined by Alan) filed as `reports/YYYY-MM-DD Weekly report - <Project name>.docx`. `PORTFOLIO.md` untouched |
| cx-client-report | Client-safe Word report (`client-report-template.docx`) filed as `reports/YYYY-MM-DD Client report - <Project name>.docx`. Shows internal health. Risks, issues and decisions appear only if `client_visible`. Includes client-owned actions and our commitments. Never sends, never creates email drafts. Manual, with a per-project reminder rhythm in the project `CLAUDE.md` (default weekly) |
| Bulk approval | Never covers minutes, weekly, client or steering reports, health changes, new decisions, recording or withdrawing a decision, or new risks |
| Dashboard | Reference design in `dev/reference/dashboard-reference.html`. Files tab (a built-in file index: tree, quick views, filters, Open folder). Pending review copy buttons copy `approve <CODE>, then apply` and `approve all, then apply` |
| Executive Current state (BL-106, v1.2.0) | Generate writes a short executive status, not a list. `status_facts.py` (no model call) ranks the facts (position, movement, exposure, asks including decisions needed, candidate figures, trend); `system/templates/executive-style.md` is the one voice every status prompt reads (the weekly and client report skills too). The dialog has Audience (Internal or Client-safe: only client-visible items, in their client wording) and Length (Short about 40 words, Standard 150, Fuller 250). Notes under the draft (`status_checks.py`) never block a save. **Make it executive** rewrites Alan's own text as a draft he uses or discards. Plain code checks everything around the model; Alan judges the wording on real projects. FR-111 |
| Dashboard editing | In scope (was BL-01). Option B, browser folder access: verified in Chrome 154 on 2026-10-03; vault always connected. Inline editing of Actions, RAID and Decisions (multiline fields, a DD-MM-YYYY calendar picker, toggles, row undo); Edit and New forms; project edits; "Current state"; Approve/Reject in Pending review. All written as approved proposals to staging and applied as usual. Live mode (`live_server.py` on localhost) is **required**; Alan starts it himself |
| Settings | `system/config/settings.json` holds every tunable value. The dashboard's Settings tab saves instantly (with a backup and a log); cx-edit can change settings too. Register and other memory sections stay with cx-edit |
| Edited drafts | Close in Word, then approve individually. An automatic consistency check against the staged items or health; client reports re-scanned for internal content; tracked changes accepted and comments removed before filing |
| cx-setup | In scope (was BL-05). "setup" runs the health check and the Microsoft 365 and docx checks, and offers to restore the database, initialise git, create the optional morning sweep, add permissions and hide `dev/`; it then rebuilds. Asks before every change. Never installs packages or creates mail rules |
| Backups | Database copied at the first session of each day and before every apply |
| Platform | **macOS primary** (Terminal, `python3`, Chrome or Edge; FileVault; vault kept outside iCloud- or OneDrive-synced Desktop and Documents, for example `~/creaite`). Windows still supported |
| Design system | **Google Material 3**: seed-based colour roles (light and dark), Roboto, M3 shapes and components; collapsible navigation rail with pin; search bar opening the ⌘K palette; always-compact sortable tables with sticky headers; "Needs attention" cards; snackbar Undo; centred edit dialog showing all fields; WCAG 2.2 AA. Reference: `dev/reference/dashboard-reference.html` |
| Live mode | **Required** (localhost approved by IT). `live_server.py` on 127.0.0.1, started by Alan; red alert if it's unreachable |
| Assistant | "Ask creaite" panel (⌘J / Ctrl+J, app-bar button, floating button; Esc closes it). Live server runs Claude Code headless in the vault (stream-json, resumed sessions, strict tool list); writes confirmed in the panel. API key not needed (uses Claude sign-in) |
| Data model (v0.17) | Statuses: actions Open/Delayed/Closed/Cancelled, RAID Open/Closed/Cancelled ("Done" retired). Actions add workstream, priority, latest update, client messaging; RAID adds workstream, response action, due date, date closed, client messaging. "Mine" removed — ownership by name (settings identity) |
| Client messaging | One field, three fixed headings; PM writes it (Claude never does); required complete only for client-visible items; client reports use it instead of the description |
| Dashboard editing | Auto-apply on save (default), owner picker with people list, multi-select owner filter, Due soon filters, editable proposals in Pending review, 50-row list frames, resizable remembered columns, Data-as-of footer, Help page (`?`), `/` for Ask creaite; copy-command buttons removed |
| v0.18 | RAID IDs `<CODE>-NNN`; decisions must record a source; Settings: You, Defaults, People and Workstreams managers (rename/merge applied with Undo); table layout never overhangs its frame; Files tree collapsible per project |
| v0.19 | Reminders on Portfolio only, dismissable for the session or forever (per occurrence; restorable in Settings); live-server alert stays global; Copy path removed from Files |
| v0.20 | Sources: file names open the file; email sources store From, Subject, Sent (date and time) and a message link (Open in Outlook); Teams likewise (Open in Teams); references only, never content |
| v0.22 redesign | After a UX review (NN/g, Few, M3 density, PMO practice): Today home (briefing, decisions, commitments, changes, portfolio with evidence), project cockpit, Work with saved views and a non-modal detail panel (select → E/double-click to edit), Review triage keys and batch, Activity log with undo, calm colour, no floating buttons, status in top bar, Settings split. Replaces inline click-to-edit, the centred dialog, the collapsible rail and the footer. One complete reference file: `dev/reference/dashboard-reference.html` |
| v0.23 | Dates shown DD-MM-YYYY, stored and in file names YYYY-MM-DD; ID and Source columns selectable; decisions get plain client messaging; click outside closes Ask creaite and the detail panel (not while editing); copyable live-server start command |
| v1.8.0 | Out of Beta: a full release, not a pre-release (Alan, 12-10-2026). The dashboard's source is in `system/templates/dashboard/` (ES modules by area, bundled by a pinned esbuild into `dashboard.html`, which is generated and never edited by hand), with no in-place wrappers, `checkJs` at 0 errors and every value escaped by default (BL-231, BL-228 D; NFR-22, FR-227). Nothing changes on screen. Release notes: `dev/release-notes/1.8.0.md` |
| v1.9.0 | Meeting prep (Alan, 13-10-2026): the Prep popup reworked and the prep page inside creaite (Meetings › Prep, Briefing layout), with shaping on the server; Today across the calendar's days; Close the day as a guided shutdown with a guarded catch-up sweep; VIP private everywhere ("People I follow"); smarter updates, Draft chase, promises (BL-125 A). The first Preact components, built to `dev/COMPONENTS.md` (BL-256; NFR-23). A full release. FR-229 to FR-250. Release notes: `dev/release-notes/1.9.0.md` |
| v1.9.1 | ask creaite like the dashboard (Alan, 13-10-2026): every work-item ID in a reply checked against the tracker (`claims.py`), a plain "I can't" with a button to where it can be done, and field changes through the dashboard's own save with one Undo (Alan's guard decision, 14-10-2026: no new command or route; BL-141 and BL-267 unchanged); Today's day arrows never move (BL-321). A full release. FR-251, FR-252. Release notes: `dev/release-notes/1.9.1.md` |
| v1.9.2 | Calmer (Alan, 13-10-2026): Settings in four places (Essentials, People and projects, Advanced, Health), each setting with a line, a dot when changed and Reset; Health inside Settings with five Fix it buttons, and update.py's after-update steps (launcher, icon, restart) from the next update (Alan's guard decisions, 14-10-2026); Close the day offered from 17:30 by default, Week ahead Urgent only, saved values kept; seven reject reasons with creaite's guess and one menu (BL-315); Today as one home with To decide first, and the rail as a sidebar with More (BL-319). A full release. FR-253 to FR-255. Release notes: `dev/release-notes/1.9.2.md` |
| v1.9.3 | Sneak peek and safe backups (Alan, 14-10-2026): `//` or the sparkle in the peek changes the open item in plain words, plain code first, Claude only for wording, with a confirm for the bigger changes, an `@` list of people, Undo, and follow-on items linked by `@n` (BL-322); a closed daily zip of what rebuilds the vault to the company OneDrive (a non-negotiable changed, Alan's decision: never chats or `vip.json`), agreed retention with a daily Tidy up that never runs from ask creaite, a weekly restore check and Restore from a backup in Settings › Health (BL-323); search reads PDFs with pypdf 6.19.0 (Alan's two-week rule), the index rebuilt once (BL-275). Doctor 32 checks. A full release. FR-256 to FR-258, NFR-02. Release notes: `dev/release-notes/1.9.3.md` |
| Dates | Shown and typed as `DD-MM-YYYY` everywhere Alan reads or types; file names use `YYYY-MM-DD Title`; stored as `YYYY-MM-DD` in the database, staging, sources and settings (v0.23) |
| Project documents | `documents/` in each project (renamed from `reference/`). You manage the subfolders; every version is kept. Passive: never extracted, changes trigger nothing, read only on your question or instruction, internal by default |
| Retention | Nothing is pruned: reports, snapshots, backups and proposals are all kept. Archiving is backlog BL-03. Exception: Ask creaite keeps its 10 most recent chats (BL-32) |
| Portability | Copy the folder to move creaite. A new machine needs only Claude, Python 3.9 or later, and a Microsoft 365 reconnect, then say "setup". Python libraries are bundled in `system/scripts/vendor/`; schedules are in `system/config/schedules.md`; permissions are in `.claude/settings.json`; all paths are relative |
| Build and run environment | Claude Code in the Claude desktop app (Code tab), with the vault opened as the project |
| Storage | **Local only**, in a vault folder on the laptop. No OneDrive, cloud storage or SaaS |
| System of record | **Hybrid.** `tracker.db` (SQLite) is the record, with rules enforced, a change log and full-text search. `tracker-view.xlsx` is a two-way Excel editing surface: export after each apply; "import excel" stages edits and Review-sheet decisions, with conflict detection |
| Web interface | `dashboard.html`, generated from the tracker with the data embedded; opens offline in Edge |
| Review model | Every route (skills, Excel import, plain-English edits) writes proposals to `system/staging/`. Alan approves in Claude Code or the Excel Review sheet. Only `system/scripts/tracker.py apply` writes, in one transaction |
| Triggers | The daily sweep runs at session start when due (from 07:00), as a creaite rule; scheduled tasks are optional. cx-minutes is manual. Every write needs "apply" |
| Project matching | Project codes (3 to 7 capital letters or digits, starting with a letter; BL-08) plus `projects/_portfolio/project-register.md`, using strong, medium and weak signals; ambiguous items go to review |
| Scope | Per-project activity and reporting (weekly status, client reports). Portfolio-level reporting is backlog BL-02. Financials, resourcing and timesheets are out |
| Reused components | openpyxl, Jinja2 (bundled), Python standard library for transcripts and validation (MarkItDown, webvtt-py and pydantic not needed), Tabulator, Chart.js (inlined), SQLite with FTS5, Git for Windows |
| Memory | Everything lives in the vault: an "About Alan" section in the root `CLAUDE.md`, `projects/_portfolio/PORTFOLIO.md` for cross-project context, one `CLAUDE.md` per project, and the tracker for facts. Nothing goes in the user-level `~/.claude/CLAUDE.md` |
| Anthropic skills | xlsx, docx, pdf and skill-creator from day one; internal-comms when the reports skill is built |

## Options considered and rejected

- **A hosted work tracker as the backend.** Reviewed twice, and deferred for now. Its strengths are built-in project health updates, initiatives and an official Claude connector; Basic costs about $120 a year for one user. It would replace the tracker script and dashboard, but data would leave the laptop and IT approval would be needed. Revisit later.
- **Another hosted work tracker.** Weakest free tier for a solo user, and paid plans have a 3-seat minimum.
- **Moving the vault to OneDrive.** It would allow cloud scheduled tasks, but Alan chose local only.
- **Other trackers and wikis (Microsoft's, open-source and hosted).** All are hosted or a poor fit.
- **Excel as the record.** Superseded by the SQLite hybrid, because it was fragile under automation.
- **Markdown with Obsidian, or JSON with a live web app,** as storage.
- **Streamlit, Datasette, Evidence.dev and WeasyPrint.** They need a server, Node.js or a painful Windows install.

## Backlog

Full list with detail: `dev/BACKLOG.md` (the single home for backlog items).


- **BL-02:** portfolio-level reporting (a leadership report and a weekly portfolio report, with a portfolio reports folder).
- **BL-04: cx-chase.** Overdue chase-up email drafts.
- **BL-06: unattended cx-minutes.**
- **BL-03:** archiving and retention for reports, snapshots, backups and applied proposals.
- **BL-07: full-text content search** in the dashboard's Files tab. To decide later.
- **BL-08 to BL-14:** longer project codes, project archive and restore, age-based archiving, milestones, project page redesign, item icons, button placement (see `dev/BACKLOG.md`).

## On hold (Alan asked to park these)

- A monthly leadership report on a schedule, and client reports on a schedule.
- Automatic Friday chase-up email drafts.
- (Superseded: dashboard edits now auto-apply; Claude's extracted proposals still need review.)

## Open questions

Resolved 2026-10-04 (Step 0, `dev/tests/step-0-environment.md`): the build runs on the work laptop; Python is allowed; `claude` works and headless Claude Code reaches Microsoft 365; Microsoft 365 search works in Claude Code.

Resolved 2026-10-05 (Alan):
- **AI use on work data:** approved.
- **Retention:** a local-only vault with local backup is allowed.
- **Teams transcription:** enabled for the tenant.
- **Project tagging:** project codes from `project-register.md`, plus recognition from email sources, keywords and project names (aliases), as set out in `project-matching.md`.

Still open:
- Which client audiences need reports, and how often? To be decided later (leadership reporting is BL-02).

## Next steps

1. Fill in `projects/_portfolio/project-register.md` with the real projects, codes and key people.
2. Run `dev/BUILD.md` Step 0, the environment check.
3. Continue through the build steps in order.

## Preferences

Alan prefers concise, direct professional writing and short outputs. Use British English.
