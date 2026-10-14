# Backlog

> **Read-only export of the board on insyncalan/creaite-plan; edit the board, not this file.**
> Made by `python3 dev/tools/board_import.py export`. One issue per open item; a pull request in the code repo closes one
> with "closes insyncalan/creaite-plan#N". Sizes are rough: XS an hour or two, S under a day, M one to three days, L more,
> XL a sprint on its own.

## Summary

### v1.9.4

| ID | Item | Size | State | Priority | Team | Issue |
|----|------|------|-------|----------|------|-------|
| BL-09 | **Archive and restore whole projects**, into `_Archive/` (and **zz Archive is renamed _Archive throughout**) | M–L | In review | High | Team Cap | #4 |
| BL-304 | **Technical: changes appear at once, and only what changed is redrawn.** An edit shows on screen immediately and is staged and applied in the background (put back, with the reason, if it fails); the page keeps its data in memory and BL-253's events update just the changed records instead of reloading `/api/data` | L | In review | High | Team Cap | #5 |
| BL-326 | **Defect. ask creaite shows a run's machine text:** pressing Prep page shows the run in ask creaite with its whole prompt ("creaite prep page. Research one meeting … reply with ONLY a JSON object"), the meeting's context as JSON and the reply's JSON and HTML. Show only the ask, the activity and the outcome | S | In review | High | Team Stark | #10 |
| BL-327 | **Defect.** Saving is sometimes slow (14 to 24 s instead of about 1) and the first page load after a start takes 5 to 14.5 s: after an apply, the OneDrive backup copy and a full search-index rebuild run before the save returns | S–M | Building | High | Team Cap | #6 |
| BL-328 | **Defect.** A sweep that ends abnormally (stopped, timed out, or cut off when the server stops) leaves its lock, so the next sweep waits until the lock is 30 minutes old | XS | In review | High | Team Cap | #7 |
| BL-329 | **Defect.** Two servers start at once: the launcher starts a second while the first is still starting, which fails with "exit 1" (three times on 13-10) | XS | In review | High | Team Cap | #8 |
| BL-330 | **Defect.** The page asks for a remembered ask creaite chat that no longer exists (only 10 are kept): a 404 logged as a warning, six times on 13-10 | XS | In review | High | Team Stark | #9 |

### v1.9.5

| ID | Item | Size | State | Priority | Team | Issue |
|----|------|------|-------|----------|------|-------|
| BL-03 | Archiving old reports, snapshots and applied proposals (the backup half split out as BL-323) | S–M | Building | Normal | Team Cap | #14 |
| BL-10 | Age-based archiving of older items | M | Building | Normal | Team Cap | #13 |
| BL-316 | **Consistency audit after the move to components:** every screen on BL-256's building blocks; one shared behaviour test (keys, focus, Esc, Undo) on every menu, picker and dialog; check.py counts the old helpers down to 0 | M | Building | Normal | Both | #15 |
| BL-324 | **UI audit: fix first:** the ten points Alan approved from the 14-10-2026 UI/UX audit: its eight P1 findings (dark-mode logo bar, an undefined border token, unreadable dark-mode count badges, faint-text and past-time contrast, the column-resize handles' and sortable headers' ARIA, dead tokens) and three P2 items (control drift across pages, Help's fonts, the prep page's fonts and colours) | S–M | Building | Normal | Team Stark | #11 |
| BL-325 | **One design scale:** type, spacing, corner-radius, shadow and z-index tokens under the colour tokens, the near-duplicate values merged and the outliers moved, so every control looks the same on every page (the audit's wider P2/P3 work) | M–L | Building | Normal | Team Stark | #12 |
| BL-331 | **Move back one archived report:** in Files, a report or minutes shown as archived gets **Move back**, which returns it to its place through the approval card | S | Building | Normal | Team Cap | #18 |
| BL-333 | **Defect.** The page scrolls past its own bottom: on Today and the Prep page the whole window scrolls down into empty space, and the rail and content scroll away with it | XS | Building | Normal | Team Stark | #16 |
| BL-334 | **Alerts from people Alan follows read the conversation, not the message:** one card per Teams chat or mail thread since the last check, saying what came out of it (a short summary plus proposed actions, decisions and risks), never one card per line of to and fro | M | Building | Normal | Team Stark | #17 |

### v2.0.0

| ID | Item | Size | State | Priority | Team | Issue |
|----|------|------|-------|----------|------|-------|
| BL-301 | **Notes:** a Notes tab on each project (files in `08 Notes`), a capture drawer (⌘⇧N), Tiptap as the one editor everywhere, AI on selected text, and **Find updates**, which turns a note into tracker changes applied from a panel beside it | XL | Building | Normal | Both | #3 |

### v2.1.0

| ID | Item | Size | State | Priority | Team | Issue |
|----|------|------|-------|----------|------|-------|
| BL-335 | **The weekly report, redesigned and built in creaite:** drafted, edited and approved on the project's Reports tab as a true A4 page; filed as a creaite report (`.html` with the report's data inside, reopened to edit, versioned); exported to Word (the firm's template), PDF and HTML to share. New layout that leads with health and the asks; sections you move and hide, rows you choose, a layout remembered per project, up to two client and partner logos, inline AI checks and suggestions, the standard peek on every item | L | Ready | High | Team Cap | #19 |
| BL-336 | **The client report, as a Client view of the week's report:** one per client, with its own layout and renamable headings remembered per client; client health may differ, with a required reason; client-visible items only, in their client wording; Match internal per section or for all; a check of what's left out before export; a baseline (approved or exported only after the internal week is approved, its facts locked to it); HTML, Word or PDF | L | Ready | High | Team Cap | #20 |
| BL-337 | **Reporting space and journey:** a Reporting card on the project cockpit; one reporting space per project (weeks down the left, the week's internal and client reports as cards, the files filed); the editor with Internal, Client and Side by side views (≠ Client indicators, the difference on hover); a top-level **Reports** page listing every project's week, for Fridays; creaite drafts the client reports with the internal one | M–L | Ready | High | Team Stark | #21 |
| BL-338 | **The minutes editor, replacing today's minutes experience:** draft minutes from the transcript on a true A4 page, edited in place, with the transcript beside them (time tags on every line), checks against the transcript, the proposed items as rows in the page (approved unless removed), deadlines picked or typed in words, agenda coverage you act on, one version or an internal and a distributed version, saved in creaite's own format and exported to HTML, Word or PDF | XL | Ready | High | Team Stark | #22 |
| BL-339 | **Retire the meeting hub** (BL-209's page for each meeting, FR-167): its links go to the Prep popup before a meeting and to the minutes after it; Coverage and Carry move into the minutes editor (BL-338) | S | Ready | High | Team Stark | #23 |

### Unscheduled

| ID | Item | Size | State | Priority | Team | Issue |
|----|------|------|-------|----------|------|-------|
| BL-02 | Portfolio-level reporting | L | Idea | Normal | Unassigned | #32 |
| BL-06 | Unattended cx-minutes | M | On hold | Normal | Unassigned | #2 |
| BL-40 | More named themes | S | On hold | Low | Unassigned | #1 |
| BL-125 | Promises, links and labels: the features on the tables Sprint 5 built | XL | On hold | Normal | Unassigned | #28 |
| BL-182 | Extraction quality, the rest: learn patterns from reject reasons (step C) and spot-check what was missed (step D). Steps A and B were built as BL-233 (FR-191, v1.7.0) and BL-232 (FR-182, v1.6.1) | M–L | On hold | Normal | Unassigned | #31 |
| BL-183 | Health evidence and calibration: a banner when the declared health is better than the evidence, and your own health calls scored afterwards | S | On hold | Normal | Unassigned | #26 |
| BL-203 | A project as it stood on any day: an "as of" date on the project page, and what changed between two dates | M | On hold | Low | Unassigned | #30 |
| BL-204 | People with contact rhythm, and a one-click 1:1 prep page | M | On hold | Low | Unassigned | #29 |
| BL-255 | **A hash-based script policy:** a `Content-Security-Policy` that allows only the app script's hash, in a header and a `<meta>` tag; report-only shipped in v1.9.0 (FR-230) | S | Needs decision | Normal | Unassigned | #33 |
| BL-313 | **Plain words:** with automatic apply on, nothing on screen or in ask creaite says "staged", "apply" or "proposal"; your own change is "Saved" (with Undo); what creaite suggests "waits for you in Review" | M | On hold | Normal | Unassigned | #25 |
| BL-317 | **Reports you live in:** one living Status page per project (health, Current state, milestones, top risks, help needed), edited in place with evidence; each week a snapshot; Client view; Export to Word from it | L | On hold | Normal | Unassigned | #27 |
| BL-340 | **Notes transcripts in the minutes editor:** how a transcript of Alan's own notes (a dictated or recorded note, beside v2.0.0's Notes) is drafted, edited and approved with BL-338's editor, and what differs from a meeting's minutes | M | On hold | Low | Unassigned | #24 |

## Write-ups

### BL-02 — Portfolio-level reporting

**Plan (as imported):** After the trial, with portfolio workstream categories

A leadership report and a weekly portfolio report across all projects, a portfolio reports folder in `projects/_portfolio/`, and automatic refresh of `PORTFOLIO.md`. The dashboard's portfolio view stays as is meanwhile.
- **Depends on:** per-project reporting stable after the trial.
- **Related:** the parked monthly leadership report on a schedule (see On hold).

### BL-03 — Archiving old reports, snapshots and applied proposals

**Plan (as imported):** **In v1.9.5 (Alan, 14-10-2026)**, with BL-10, after BL-09 (v1.9.4). Archived reports and minutes move into the engagement's `_Archive/`; **ready for a sprint** (decisions below)

Rules for archiving the files that build up over time: reports, dashboard snapshots and applied proposals. **Split on 14-10-2026 (Alan):** the backup and retention half is now **BL-323**, in v1.9.3; what is left here follows **with BL-10**, after BL-09 (v1.9.4), using its `_Archive/` and archived flag.
- **In v1.9.5 (Alan, 14-10-2026)**, with BL-10, after BL-09 (v1.9.4).
- **Depends on:** BL-09 (the `_Archive/` folder and the archived flag) and BL-323 (which already prunes backups and dashboard snapshots).
- **Decided (Alan, 14-10-2026):** archived **reports and minutes move into the engagement's own `_Archive/`**, keeping their place below it (`<engagement>/_Archive/04 Reporting/Weekly/…`), so restoring is a move back. As in BL-09: stored paths never change (`paths.resolve` finds a moved file under `_Archive/`), the files are no longer indexed and ask creaite can't read them, and only `tracker.py apply` moves them (BL-09's agreed guard exception). Nothing is deleted.
- **Decided (Alan, 14-10-2026):**
  - **Age:** weekly and client reports, minutes and Steerco one-pagers older than 12 months, by the date in their file name. Transcripts, agendas and documents stay where they are.
  - **How:** a monthly Health line, "Archive 14 reports and minutes older than 12 months", one click on the confirm card. These are Alan's own files in OneDrive, so they're moved on a yes, not automatically (unlike BL-10's flag).
  - **Applied proposals** (`system/staging/applied/`) aren't archived: BL-323 keeps them all as the audit trail. Dashboard snapshots are already handled by BL-323's retention.
  - **Portfolio minutes** are archived on the same 12-month rule, into `_Portfolio/_Archive/<same folder>/` (Alan, 14-10-2026, directly to Team 1). This widens the approved `reports` move shape to the portfolio's own `_Archive`; the exact new shape is shown to Team 1 before it merges.
  - **Security:** all six security points in `dev/V195-ARCHIVING-NOTE.md` approved (Alan, 14-10-2026, directly to Team 1).
  - **Moving one report back** is a follow-up, BL-331.
- **Related:** BL-10 (age-based archiving of items); build the two together.

**Guard change approved (Alan, 14-10-2026, directly):** the widened `reports` move shape for portfolio minutes (`v195-archiving` fbc05da, `reach._report_archive`): one dated minutes file in the portfolio's own minutes folder may move into the portfolio's own `_Archive`, keeping its place (`<projects root>/<portfolio>/<minutes folder>/<file>` → `<projects root>/<portfolio>/_Archive/<minutes folder>/<file>`). Still refused: the portfolio's transcripts or any other folder, any other destination, symlinks, `..`, an existing destination, anything but a file. `classify()` is unchanged; only `tracker.py apply` calls it. Team 1 reviewed it as technically sound.

### BL-06 — Unattended cx-minutes

**Plan (as imported):** After the trial

Allow minutes processing (drafting and staging) to run unattended, like the morning sweep. Approval and filing stay manual.
- **Depends on:** confidence in draft quality after the trial; transcript retrieval working (Step 0 item 5 is still unconfirmed).

### BL-09 — Archive and restore whole projects

**Plan (as imported):** **In v1.9.4 (Alan, 14-10-2026)**, on its own (moved from v1.9.3 the same day; before that "after the trial"). The guard exception and the four open points agreed (Alan, 14-10-2026): **ready for a sprint**, after BL-320's Health

Archive a finished project completely, so it disappears from the dashboard, the sweep and reminders, and restore it if needed. **In v1.9.4 (Alan, 14-10-2026)**, on its own: a schema change and migration, a guard exception and folder moves are easier to check and roll back alone (moved from v1.9.3 the same day; before that "after the trial"). BL-10 follows. **Ready for a sprint (Alan, 14-10-2026):** every point below is decided. **Depends on BL-320** (Health, v1.9.2) for the Fix it lines. Size M–L.
- **Today:** cx-edit "close project ABC" sets `active = 0`; the folder, register row and items stay where they are. Closed projects can still appear in Files and search.
- **"archive project ABC":** closes it if it's still active; moves its folder to **`_Archive/`** (Alan, 14-10-2026): `<projects root>/_Archive/<engagement folder>` with the projects in OneDrive (BL-85), `projects/_Archive/<CODE> <Name>/` with the vault's own projects folder; moves its register row to **Retired codes**; marks its items **archived** in `tracker.db` (a flag, not a second database: still searchable, covered by the backups, undoable), so they leave the default views, Work, Today, the Excel export, the reminders and project matching. Nothing is deleted. An archived code is never reused.
- **"restore project ABC":** reverses each step: the folder moves back (a number is added if the name is taken, never overwriting), the row returns to the register, the items are live again.
- **Decided (Alan, 14-10-2026):**
  - **Links keep working:** stored paths never change. `paths.resolve` maps `projects/<folder>/…` to `_Archive/<folder>/…` for an archived project, so every item's source, report and minutes link still opens, and restore needs no rewrite.
  - **Search:** an archived project's items stay searchable (marked Archived); its files in `_Archive/` are not indexed and ask creaite can't read them. Restore brings them back.
  - **Open items:** archiving lists the project's open items and offers **Cancel them all and archive** or **Stop**; nothing is archived with an item still open.
  - **Where:** "archive project ABC" (cx-edit) and an **Archive** button in Settings › Projects beside Close, on the existing confirm card; **Restore** in the same place for an archived project (shown with Show archived). No mockup needed.
- **Both** are shown first and confirmed, then go through a proposal and `tracker.py apply`, so they're logged and undoable. The folder moves are file operations of the apply (a `move` op), backed up and logged like every other file change.
- **Rename zz Archive to _Archive throughout (Alan, 14-10-2026).** One name for every archive folder creaite knows of:
  - `paths.py` (`never_index` default and `ALWAYS_NEVER_INDEX`), `settings-defaults.json`, `locations.py`, `live_server.py`, `permissions.py`, `reach.py`, `creaite-rules.md`, `help.md`, the BRD, BUILD, the dashboard spec and the tests (49 mentions in 20 files on 14-10-2026).
  - **The update** replaces `zz Archive` with `_Archive` in a saved `locations.never_index`, keeping every other value (the only time an update changes a saved value; it says so).
  - **The project skeleton (Alan, 14-10-2026):** each engagement's own archive folder, copied from `_Templates/_Skeleton` (`locations.skeleton`) for a new project, is `_Archive` too. If `_Templates/_Skeleton` exists, Alan renames its `zz Archive` to `_Archive` himself, in Finder (creaite never writes in `_Templates`); without a skeleton, setup uses the first engagement as the template and the engagements' own `zz Archive` folders are the ones Health offers to rename. As a safeguard, creating a project from the skeleton names any `zz Archive` it copies `_Archive`, and Health says if the skeleton still holds a `zz Archive` (a folder listing only, as setup already reads the skeleton). The test fixtures' sample engagement (`test_onedrive_projects.py`) uses `_Archive`.
  - **Folders already called `zz Archive`** in Alan's OneDrive keep being skipped for one release (both names are never indexed), and Health lists them with a **Fix it** that renames each one to `_Archive` (a move, so it goes on the approval card). After that only `_Archive` is known.
- **The guard (agreed, Alan, 14-10-2026; BL-141):** `_Archive/` stays on ask creaite's never list for reading and writing, as `zz Archive` is today. The only thing that may move a folder into or out of it is `tracker.py apply` running an approved archive or restore, never a model and never `filechange.py` on its own. `reach.py` gains that one exception, with a test that ask creaite still can't read, write or move anything there.
- **Security (Alan, 14-10-2026, directly to Team 1)**, on the build's note `dev/V194-ARCHIVE-NOTE.md` › Security changes:
  - **Points 1, 2, 3, 4, 6 and 7 approved:** `reach.archive_move_problem` as the one guard exception (whole-folder moves in the archive, restore and rename shapes only; called only by tracker.py's `move`); `propose.py old-archives` as a read command; the `old_archive` Health fix waiting on the approval card; the stricter `tracker.safe_path`; the rename on the BL-258 change card; and no new guard exception in part 2.
  - **Point 5, changed:** the deny lists and permission patterns name **only `_Archive`**, never `zz Archive` beside it. `classify()` still treats `zz Archive` as never, so ask creaite stays out of an old folder until it's renamed. The two exact-list tests follow.
- **Touches:** a project state (`active` / `closed` / `archived`) and an `archived` flag on items in `schema.sql` (with `tracker.py migrate`); `paths.py` (`_Archive/`); `tracker.py` (the `move` op, archive and restore); cx-edit; cx-sweep and project matching (ignore archived codes); the dashboard's and the Excel export's filters ("Show archived"); search (archived items found, marked Archived); `reach.py`; Health; Help.
- **Done when:** archiving and restoring a sample project round-trips exactly (folder, register, items, search), with undo; nothing in `_Archive/` is read by ask creaite or indexed; an existing `zz Archive` folder is skipped and Health offers to rename it; a new project made from the skeleton has `_Archive`, never `zz Archive`; the update renames the saved setting and nothing else.

### BL-10 — Age-based archiving of older items

**Plan (as imported):** **In v1.9.5 (Alan, 14-10-2026)**, after BL-09 (v1.9.4), with the rest of BL-03. **Ready for a sprint** (decisions below)

Archive information older than a set period, for example closed actions and RAID items closed more than 6 months ago, and decisions older than 12 months.
- **Proposed:** a setting per item type in `settings.json` (`archive.after_months`); archived rows keep their IDs and history but drop out of default views, the Excel export and the weekly report; "show archived" brings them back; un-archiving is automatic if an archived item is edited.
- **Overlaps BL-03** (files) and BL-09 (whole projects); one archiving design should cover all three.
- **Decided by BL-09 (Alan, 14-10-2026):** a flag in the database, the same archived flag BL-09 adds (still searchable, covered by the backups, undoable), never a second database file.
- **In v1.9.5 (Alan, 14-10-2026)**, after BL-09 (v1.9.4), with the rest of BL-03.
- **Decided (Alan, 14-10-2026, accepting the recommendations):**
  - **Periods, from the closed date:** closed or cancelled actions and RAID items, 6 months; done or dropped promises, 6 months. **Decisions and milestones are never archived** (Alan, 14-10-2026), nor is any open item. Each period is a setting (`archive.after_months`, Settings › Advanced).
  - **Automatic,** once a day after BL-323's Tidy up: the flag is reversible, so no review list. Health shows the last run ("Archived 12 items"); "Show archived" brings them back, and editing an archived item un-archives it.
  - **Client reports:** an item is archived on the same rule whether or not a client report cited it. The report is a saved Word file and doesn't change; the item stays searchable, marked Archived.
  - **Editing an archived item** un-archives it, and it stays live for a full period from that edit (Alan, 14-10-2026, directly to Team 1).
  - **Restoring a whole project** (BL-09) clears only the flags the project archive set; items archived for their age stay archived (Alan, 14-10-2026, directly to Team 1).
- **Security (Alan, 14-10-2026, directly to Team 1):** all six security points in the build's note `dev/V195-ARCHIVING-NOTE.md` approved (shared with BL-03).

### BL-40 — More named themes

**Plan (as imported):** **On hold (Alan, 14-10-2026)**

**On hold (Alan, 14-10-2026).**

Raised 2026-10-05. Alan names further dashboard themes; each is added as a token set (FR-57), in light and dark, beside the five there are now (Brightwater, creaite, Notion, Linear, Cursor; v1.3.0).
- **Rules kept:** health colours stay icon plus text with sufficient contrast in every theme and mode; no external resources.
- **Touches:** `system/templates/dashboard.html` (a token set per theme under `[data-palette=…]`), the Settings choice and swatches, the theme tests.

### BL-125 — Promises, links and labels: the features on the tables Sprint 5 built

**Plan (as imported):** **B (links) and C (labels) on hold (Alan, 13-10-2026).** Stage A built in v1.9.0 (FR-229)

Replaces BL-50 (promises and waiting on), BL-90 part 2 (links) and BL-94 (labels), Alan's decisions kept. **Built already (FR-101, FR-97, FR-102):** the `promises`, `links`, `labels` and `item_labels` tables with validation, apply and undo; the Excel Promises, Links and Labels sheets and columns; the people register's Labels column; **Sensitive** as the built-in label (warn, exclude as the default choice); the dependency part 1 (milestone attach, suggestion, Dependencies card, date warning, Work filter); and the client-safe one-pager and `review.client_findings` honouring an excluding label. **What is left is below, in three stages that can be built and released one at a time.** They share the same hand-offs (the sweep, cx-minutes and Review), so stage A goes first; B and C can follow in either order.

#### A. Promises and waiting on
**Built in v1.9.0 (FR-229; moved from v2.0.0 by Alan, 13-10-2026).** **Stages B and C are on hold (Alan, 13-10-2026).**
- **Start small, measure the noise (Alan, 13-10-2026):** promises come first from cx-minutes and from Alan adding them by hand (the peek, ⌘K, Quick capture). The sweep's proposed promises (Sent Items, Teams, incoming mail) are switched off (`promises.from_sweep`, default off) until BL-233's quality data shows enough of them accepted unedited; the bar is Alan's to set (suggested 70%). Close the day's "You promised today" (BL-295), Draft chase (BL-298) and Smarter updates (BL-297) read real promises once they exist.
- **Build after BL-233 (formerly BL-182 step A, 11-10-2026):** the sweep and cx-minutes will propose promises, and their precision is the main risk; measuring accepted, edited and rejected proposals from the first sweep makes it visible. Also from the research: **silence is the signal**, so extend the `mentions.jsonl` matching to promise IDs and flag an overdue promise as "quiet for N days".
Commitments made in passing ("I'll send the SOW by Friday"), kept apart from formal actions: what Alan has promised, and what others have promised him. Lighter than actions: no priority or workstream.
- **Capture:** the sweep proposes them from Sent Items and Teams (Alan's promises) and from incoming mail and chats (others' promises to Alan); cx-minutes may propose them from meetings. They go through Review like any other item (who to whom from the people register, what, by when, project, source).
- **Where they show:** "You owe" and "Waiting on" lists on Alan's page and each person's page, in meeting prep, and as counts on Today. Overdue promises are flagged.
- **One click to turn a promise into a formal action** if it grows, keeping its source and people.
- **Replaces BL-04 (cx-chase, removed 12-10-2026, Alan):** Alan chases from Waiting on rather than from drafted emails; chase emails themselves are BL-224's Chase mode.
- **Alignment with the Work views (BL-128 to BL-134):** promises stay their own lists, not a Work tab; the Chase view (BL-131) covers formal items that have gone quiet and Waiting on covers promises, and each links to the other so there is one place to chase from at a glance. BL-134 may add promises as a type.
- **Touches:** `sweep.py`, `minutes.py`, `build_dashboard.py`, `system/templates/dashboard.html` (the lists, the Today counts, prep), cx-sweep and cx-minutes, cx-review, `dev/staging-format.md`, Help, tests.

#### B. Links: attach a dependency to an action or RAID item, and across projects
**On hold (Alan, 13-10-2026).**
A dependency can be attached to a milestone (built), and now also to **actions and RAID items, in the same project or another**. Attaching is **never mandatory**: a dependency stands on its own, and creaite only suggests.
- **"Attach to…" picker** beside the milestone field in the detail panel, for one or several targets. The target depends on the dependency (it blocks it); both ends show the link: the dependency lists what it blocks, and the target lists what it is waiting on.
- **Suggestions** (up to three one-click chips, plus "None needed") extended beyond the milestone suggestion that exists: open actions and RAID items in the same workstream or sharing key words, and items or milestones in other projects named in the text by ID or project code. When a dependency is created in the dashboard, with cx-edit, or proposed by cx-minutes or cx-sweep, **extraction proposes links only as suggestions in Review**. Nothing is attached until accepted; a declined suggestion is not raised again unless the text changes.
- **The links now do what a milestone link does:** the date warning (dependency due after what it blocks, or overdue while the target is near), "waiting on MER-005" and an at-risk marker in Work, on the milestone and on the project page; the Dependencies card lists open dependencies by what they block, and cross-project ones show both projects. Blockers appear in meeting prep; a client report shows a dependency only if flagged client-visible. (The one-pager already reads the table.)
- **Not in scope:** an automatic critical-path calculation, and dates that move targets automatically.
- **Touches:** `build_dashboard.py` (warning and cards), `system/templates/dashboard.html` (the picker, chips, card, tags), cx-minutes, cx-sweep and cx-edit (suggestions), Help, `dev/dashboard-spec.md`, tests.

#### C. Labels: warnings, exclusion and the sensitivity read
**On hold (Alan, 13-10-2026).**
Items and people can carry labels; **Sensitive** is built in. Anything shared or reported that includes a labelled item shows a **warning**, and a label can **exclude** items from client reports. (Word's own sensitivity label, which Review no longer needs, is unrelated: BL-121.)
- **Managing labels:** a Settings page and cx-edit phrases to add, rename and remove labels other than Sensitive ("add a label *Legal review*"), each with a colour, a note and a behaviour; and to label items and people ("label ABC-A-004 Sensitive", "remove the Sensitive label from ABC-002").
- **Behaviours:** **warn** (a banner in every output that includes the item, and a card before building: "This includes 3 sensitive items: include, exclude or cancel"; Alan can proceed; Word documents and drafts show the label beside the item and a line at the top) and **exclude from client reports** (Sensitive: warn, with exclude as the default choice). Reminder-or-review behaviours come later, once labels have been used.
- **Double catch:** an item that is both Sensitive and client-visible is not blocked. The client report stops at review, shows each such item with both flags, defaults to **exclude**, and Alan's choice to include it is logged against the report. Setting the second flag raises a one-line notice in the editor.
- **Interpreting, not only matching:** sensitivity is judged from intent and tone (blame of a named person, a dispute, pricing or contract terms, a delay attributed to a client principal, a threat to the relationship). Claude does the reading, in two places: **at extraction** (cx-minutes, cx-sweep: a proposed item can carry `labels` and a one-line reason, approved in Review like any field; nothing is labelled unseen) and **before anything is shared** (a **sensitivity read** over the items going out: "2 items look sensitive and aren't labelled", each with its reason, so Alan can label, exclude or proceed; never stored unless approved). **The deterministic floor stays**: the label check, the people-label check and the word scan always run, and the reading cannot remove a warning. Draft email, which has no Claude, uses stored labels only and says so.
- **Labels on people:** an item owned by or naming a labelled person shows it ("owner is a client principal") and counts as sensitive for warnings without a Sensitive label being written; a delay, issue or risk attributed to a labelled person is treated as sensitive by extraction and the sensitivity read, and a client report naming that person negatively stops at review; Draft email to a labelled person warns about internal-only or sensitive items.
- **Where the check runs (every route that carries an item out):** client and weekly reports (`report.py`, `review.py`; the client-safe one-pager is done), one-off documents (`report.adhoc`, whose filters also gain `label`), Draft email, the Excel export (labelled rows marked, a warning line on the sheet), the dashboard (a chip on rows and in the panel, a filter by label), Today and project views, the live server's ask creaite (told which items are labelled so its answers carry the warning), and search results.
- **In the Work lists (BL-122 to BL-132):** **Labels** is a property (shown in the Display menu, BL-128), a group (BL-129), a filter with is and is not (BL-130: "Label is not Sensitive"), and an editable cell and bulk change (BL-123, BL-124: add or remove a label). The double-catch notice applies to any inline or bulk change that would make a Sensitive item client-visible, so BL-123 and BL-124 never offer Client-visible alone.
- **Proposals:** `labels` as a field on proposed items and edits (`dev/staging-format.md`); unknown labels are refused on Excel import (done in the schema work).
- **Tests:** every output route is built with a sensitive item and asserted to warn (a route that skips the check is the main risk); the double-catch card; a people label flowing to the owner's items; label changes undone with an apply; a client report excluding a Sensitive item that the word scan alone would miss; the sensitivity read skipped cleanly when Claude is unavailable, with the floor checks still running.
- **Touches:** `tracker.py`, `propose.py`, `report.py`, `review.py`, `build_dashboard.py`, `excel_sync.py`, `live_server.py`, `system/templates/dashboard.html`, the people register reader, the skills (cx-minutes, cx-sweep, cx-client-report, cx-weekly-report, cx-document, cx-review, cx-edit), the conventions file, `system/creaite-rules.md` (the Confidential material rule is rewritten around labels), `dev/BRD.md` (new FR; NFR-04), Help, `dev/tests/`.

### BL-182 — Extraction quality, the rest (steps C and D)

**Plan (as imported):** **C and D stay on hold (Alan, 13-10-2026).** On hold (Alan, 11-10-2026): revisit step C after about a month of BL-233's data

Raised 2026-10-11 (Alan), from research into modern dashboards and project tools; **on hold**. **Steps A and B were taken out and are now BL-233 and BL-232.** What stays here waits for about a month of BL-233's data. **Steps C and D both stay on hold (Alan, 13-10-2026);** note that the live vault had 36 rejections and none with a reason on that day, so C has nothing to learn from until reasons are given (Shift+R in Review).
- **C. Learned patterns (M).** A "Suggest patterns" button runs headless Claude read-only over the reject reasons (as Prep page runs) and proposes short patterns ("vague intentions with no object", "scheduling chatter"). Accepted ones are written to `system/config/extraction-guidance.md`, which cx-minutes and cx-sweep read, each switchable. BL-233 shows whether there is enough to learn from.
- **D. Recall spot-check (M).** After extraction, a sampled second pass lists commitment-like passages that became no item. Stored as a transcript path and offset in `system/staging/spotcheck.json`, never the text (the quote is read from the file when shown). Today offers one at a time ("Should this have been an item?"); the answer goes to a small log, and "Yes" stages a normal proposal. Shows counts ("6 of 8"), never a percentage, until there are at least 10 answers. The sampling rate is a setting (each sample costs one extra model call per meeting).
- **Rules kept:** nothing here writes to `tracker.db`; `tracker.py apply` stays the only writer; proposals still need approval.
- **Open decisions:** the spot-check sampling rate.
- **Touches:** `system/scripts/quality.py`, `live_server.py`, `minutes.py`, `.claude/skills/cx-minutes/` and `cx-sweep/`, `system/templates/settings-defaults.json`, Help, `dev/dashboard-spec.md`, `dev/BRD.md`, `dev/tests/` (the patterns file is read only when switched on; the spot-check shows no percentage under 10 answers).

### BL-183 — Health evidence and calibration

**Plan (as imported):** **On hold again (Alan, 14-10-2026)**, out of v1.9.4: not buildable as written (where calibration shows is undecided; no Done-when). Eight recommendations recorded in its write-up for when it resumes

**On hold again (Alan, 14-10-2026)**, out of v1.9.4 (it was moved in earlier the same day). A readiness check found it can't be built as written: the write-up leaves where calibration shows undecided, and it has no Done-when.

**Recommendations from the readiness check (14-10-2026), not yet decided by Alan, for when it resumes:**
1. Calibration shows only on Activity › Quality.
2. Add a Done-when (one was proposed with the check).
3. A miss is a declared On track followed by Off track within 21 days.
4. Calibration covers a fixed 10 weeks.
5. The banner shows only when the declared health is better than the evidence.
6. "Keep, add a reason" is remembered in a staging file.
7. One Needs attention row on Today (BL-319's design).
8. Worked out in `quality.py`, reusing `healthEvidence()` (one evidence function, never a second copy).

Raised 2026-10-11 (Alan), from the same research; **on hold**. BL-52 already checks a health edit against the evidence (the same criteria as the weekly report, in `dashboard.html` near `evidence(p)`), but only when Alan edits health.
- **Banner (S).** Reuse that one evidence function (do not write a second copy in Python) for a passive note on the project cockpit and in Today's Needs attention: "Health is On track; the evidence suggests At risk: <reasons>", with **Change health** and **Keep, add a reason**. creaite never changes health itself.
- **Calibration (S).** Score Alan's own weekly health calls from the `updates` table (week ending, project, health): a green counts as a miss when a red follows within three weeks; weeks with less than three weeks of later data are not scored. Shown only once there are enough scored weeks (about 10 across the portfolio). **Private:** no report, one-pager, client output or Excel export reads it. No schema change.
- **Open decision:** whether calibration shows on screen at all, or only in a private view.
- **Touches:** `system/templates/dashboard.html`, `build_dashboard.py`, Help, `dev/dashboard-spec.md`, `dev/tests/` (the banner matches BL-52's rule; the score on a fixture; nothing leaks into any report or export).

### BL-203 — A project as it stood on any day

**Plan (as imported):** **On hold (Alan, 13-10-2026).** Low priority

Raised 2026-10-11 (Alan), from the UX ideas mockups (idea 4); **low priority**. **Read only.** On the project page, an **As of** date shows the project as it was on that day, and a **What changed** view compares any two dates. Useful for steering prep ("what changed since the last steering?") and for explaining why health moved. **On hold (Alan, 13-10-2026).**
- **Source: rebuild it, don't depend on snapshots.** `system/history/dashboard-YYYY-MM-DD.html` only goes back to the first build and is whole-page; `flow-YYYY-MM-DD.json` holds counts only. The data is rebuilt from `change_log` and `updates` the way BL-91's overdue-over-time already does (the last change on or before the day, else the old value of the first change after it; an undone apply never happened). Shown: health (from the weekly `updates`, with the last known value between weeks), open actions and RAID items and their status, overdue count, milestone forecast dates, and decisions made or pending.
- **Stops:** a slider with quick stops (last steering, last Friday, start of the month, 30 days ago) and a date field (typed in plain words, BL-147). **What changed since** lists the item events between the stop and the one before (raised, closed, due date moved, owner changed, forecast moved, health changed), each linking to the item.
- **Honest limits:** before an item was in the tracker it isn't shown, and the view says so ("tracker starts 05-10-2026 for this project"). Anything the log can't rebuild says "not recorded", never a guess.
- **Served on demand** (`GET /api/asof?project=&date=`, live server, read-only) rather than embedding every day in the page. Internal only: no report, one-pager or export uses it unless a later item says so.
- **Later, not now:** a portfolio version (BL-02) and a "Compare with the last steering" button in the Prep page.
- **Touches:** `build_dashboard.py` (an as-of function next to `flow_data`), `live_server.py` (the route), `system/templates/dashboard.html` (the project page control, the slider, the change list), Help, `dev/dashboard-spec.md`, `dev/tests/` (a fixture log rebuilds a past day's counts and forecast; an undone apply is ignored; a date before the first record says "not recorded"; no write happens).

### BL-204 — People with contact rhythm, and a one-click 1:1 prep

**Plan (as imported):** **On hold (Alan, 13-10-2026).** Low priority

Raised 2026-10-11 (Alan), from the UX ideas mockups (idea 6); **low priority**. A person's page (BL-56) shows their open work. Add **how long since you last spoke**, against your usual rhythm with them, and a **1:1 prep page**. **On hold (Alan, 13-10-2026).**
- **Contact rhythm (private).** Derived from what creaite already holds: meetings you both attended (the saved calendar and the minutes' attendees) and, where the sweep recorded them, mail and Teams references. A small bar chart of the last eight weeks, "Usual rhythm: weekly", and "21 days since last contact" in amber when the gap is well beyond the usual. Shown only with enough history (about four contacts); otherwise nothing.
- **Private by rule:** about you and a person, so no report, client output, one-pager or Excel export reads it (as BL-183's calibration). The people page is the only place.
- **1:1 prep page.** A button runs the Prep page engine (BL-98: headless, read-only research, the server renders and saves the page in the agendas folder) for a person: their open and overdue items, what they have promised you and you them (when BL-125 stage A exists), the last meetings you both attended, the contact gap, and three suggested talking points. Internal, never sent.
- **To settle in the build:** what counts as a contact (meetings only first, or mail and Teams too); where the prep page is filed for a person in several projects (recommended: the project with most open items, or the portfolio folder).
- **Touches:** `system/templates/dashboard.html` (the person page), `build_dashboard.py`, `live_server.py` and `prep_page.py` (the person variant), the cx-prep skill, Help, `dev/dashboard-spec.md`, `dev/tests/` (rhythm from fixture meetings; nothing shown on thin history; the gap flags correctly; nothing in any report or export).

### BL-255 — A hash-based script policy

**Plan (as imported):** Unscheduled. **Turning on enforcement is Alan's** (security), after a week of reports

Raised 2026-10-11 (Alan) as BL-231 step 3; **split out 12-10-2026.** **Report-only built in v1.9.0 (FR-230); enforcing follows after a week of reports, when Alan decides.** No schema change.

After BL-212's headers, add `Content-Security-Policy` for the page. It is within reach because the page has **no inline `on*=` attributes, no `eval` or `new Function`, no external scripts or links, and two inline scripts** (the data block, which is not executed, and the app). The build computes the hash of the app script when the page is rendered and the policy is `default-src 'self'; script-src 'sha256-…'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'`.
- `style-src` keeps `'unsafe-inline'` because the page uses about 200 `style=""` attributes.
- A page saved to disk and opened as a file cannot carry the header; give it the same policy in a `<meta>` tag (without `frame-ancestors`, which a meta tag ignores).
- Check Help's fonts, the service worker, the installed-app launcher, BL-253's event stream and every image source (Current-state images, Agendas) before turning it on, and ship it first in report-only mode for a week.

**Touches:** `live_server.py` (headers), `build_dashboard.py` (the hash and the meta tag), a test.

**Decisions (Alan, 13-10-2026).** The report endpoint is answered before the token check (local only, rate-limited, counts only): acceptable (relayed by the Product Manager; confirmed by Alan to the Scrum Master, 13-10-2026). Style hashes are sent once BL-231 removes the page's run-time `<style>`.

### BL-301 — Notes

**Plan (as imported):** **In v2.0.0 (Alan, 13-10-2026), all five parts.** Scrum Master to place in waves; A (the editor switch) first, since every other editor change waits on it

Raised 2026-10-13 (Alan): "a light wiki in the project structure, to capture ad hoc notes stored in a structured way and searchable by creaite; a rich text editor we could use throughout the app." Mockup `dev/mockups/wiki-notes-mockup.html` (published: https://claude.ai/artifact/M5fWZ8FDnXe1vPbentNZLJ). **In v2.0.0 (Alan, 13-10-2026), all five parts.** No schema change; one new folder kind in `locations`, one new staging record and one new `vault_search` kind.

**Decided (Alan, 14-10-2026): plain-text fields stay plain text.** With one editor (part A), the peek's fields (title, latest update, response, reasoning, source, options, revisit, client messaging) and the Prep boxes use the editor in its `plain` form: one paragraph a line, saved exactly as typed, no Markdown or marks, because Work's table, the Word reports and the Agendas page show them as plain text. Only Current state is rich. Markdown in those fields would be a separate, later change.

**Why.** Alan's working thinking (stakeholder observations, negotiation positions, how a client works, lessons, notes from a conversation with a colleague) has no home. Project memory is a one-page brief changed by proposal; quick capture (FR-71) is for extraction only. Notes give it a home that search, ask creaite and Prep can read, and a way to turn it into tracker changes.

**Principles.**
- **Notes never hold the record.** Actions, risks, decisions, milestones and health stay in `system/tracker.db`. A note points at them with live item chips; **Find updates** (part E) turns its lines into tracker changes.
- **Memory and notes stay separate.** `CLAUDE.md` is the short brief Claude reads every run; notes are Alan's longer material, read when a question needs them.
- **Plain files.** Markdown with a small front matter, readable in Finder and OneDrive without creaite.
- **Internal.** Never in a client report, like documents (BL-93). Never extracted by the sweep or unattended.

**A. One editor: Tiptap everywhere.**
- Tiptap 3 (MIT core, ProseMirror) with the official `@tiptap/markdown` extension, pinned to an exact version at least two weeks old, built in dev into one ESM file in `system/templates/vendor/` and committed (nothing built at run time; listed in the vendor manifest).
- One wrapper, `creaiteEditor(el, {markdown, features, pickers, ai})`, replacing the BL-47 `contenteditable` and `execCommand` editor. It keeps creaite's own toolbar, keys, paste cleaning, the "Discard changes?" guard and images (BL-63); the BL-207 claim marks become a ProseMirror mark.
- Each place switches on what it needs: Current state (no tables or checklists, which the Word reports can't take yet), the Draft email preview (BL-224, no wiki links), Prep focus notes (BL-286), item descriptions in the peek, and Notes (everything).
- Pickers: `[[` a note, `@` a person from the people register, `#` a work item, `/` an insert menu (sub-heading, checklist, work item, person, table, template).
- **Gate:** every existing Current state in the vault's project `CLAUDE.md` files loads and saves back byte for byte before the switch. The Markdown extension is labelled beta upstream, which is why the version is pinned and the round-trip is tested.

**B. Notes on the project page (option A).**
- A **Notes** tab on each project, after Meetings. Left: the list (search, pinned, recent), **collapsible** with « and », or ⌘\, remembered per browser; the note widens when it is hidden. Centre: the note. Right: Mentioned in (backlinks), Linked work (live state), People.
- **An open note is editable**: no Edit, Save or Cancel. The toolbar shows while the cursor is in the note. It saves a draft to `system/staging/drafts/` as Alan types and writes the file through `filechange.py` (backed up, logged, undoable) once per editing session: on leaving the note, or after 30 seconds without typing. "Saved" shows in the header.
- **Storage:** a new folder kind `notes`, `locations.folders.notes`, default **`08 Notes`** in each engagement folder (`notes/` in the default layout). Flat, one file per note named by its title (a taken name gets a number), pictures in `08 Notes/_images/`. Portfolio notes in `_Portfolio/08 Notes`, shown under Portfolio. Added to the skeleton for new projects; an existing project gets the folder on its first note. Files lists it as its own folder, outside Documents, as it does Agendas (BL-135).
- Front matter: `title`, `created`, `updated`, `tags`, `pinned`, `confidential`, and, for a Working session note, `date` and `with`.
- Templates: Blank, Stakeholder, Lessons learned, Working session.
- **Search and Claude:** indexed in `vault_search` as kind `note`, refreshed on save; a Notes filter in search (⌘K); ask creaite and Prep read notes and cite them. A note mentioning an item shows on that item's peek ("2 notes mention this").
- A note marked Confidential is excluded from Prep pages and asks once before its text goes to Claude (parts D and E).

**C. Capture drawer (⌘⇧N).**
- Opens from any page without leaving it. The project is guessed from the project register's signals (the matching rules cx-minutes uses), shown with its reason and changeable; no guess means Unfiled (`_Portfolio/08 Notes`). Saved as Alan types.
- Two endings: **Done** keeps the note; **Done and find updates** opens the full note with the part E panel. Recent notes are listed at the foot.
- "Note for this meeting" on a Today meeting opens the drawer with the Working session template, the date and the attendees filled in.
- ⌘K stays search. **Quick capture merges into Notes (Alan, 13-10-2026):** the drawer replaces FR-71's quick capture form; quick notes are saved in `08 Notes`, not the project's `minutes/`, and become tracker changes through Find updates instead of a trip through Review. Old quick notes stay where they are. "note: …" in ask creaite saves a note the same way.

**D. AI on selected text, in every editor.**
- Selecting text shows a small bar with **AI ▾**: Rewrite clearly, Shorter, Longer (adds no facts), Make it executive (the BL-106 voice; today's button becomes this option), Fix spelling and grammar (British English), Format nicely, Turn into a checklist, Summarise at the top, and a free "Or say what you want…" box. ⌘A first applies it to the whole note.
- The result is a **suggestion** with Accept, Discard, Try again and Show changes; it never replaces the text by itself, and ⌘Z undoes an Accept.
- One live-server route, `/api/edit/ai`. Claude runs headless with **no tools**: it sees the selected text, the option, and the project's name, people and open item IDs (so it can make chips). It cannot read files or mail and cannot write.
- The BL-106 plain-code check runs on every suggestion: a date, number, name or item ID lost or added is noted under it.
- Each place chooses its options (the Draft email adds More formal and Warmer). Counts only (offered, accepted, discarded) go to `draft-stats.json`, never text.

**E. Find updates: from a note to the tracker.**
- **✦ Find updates** on a note opens a panel **beside the note, on the same screen** (it takes the right-hand column's place until closed). Each line that gave a change gets a numbered marker matching its row; hovering one highlights the other.
- Rows are grouped: **New** (action, risk, decision, issue), **Updates to existing items** (due date, done, owner, latest update), **Milestones**, **Project information** (people register, a project memory line, project details). Lines with nothing in them are left alone and counted.
- **Apply, not Send to Review (Alan, 13-10-2026).** Ticking a row is the approval. **Apply** writes the ticked rows as already-approved proposals (`source_run: "note"`, as dashboard edits are today) and runs `tracker.py apply` through the live server, as one apply, so **Undo** in the snackbar reverses all of it. **Save for later** sends the ticked rows to Review instead; without the live server, Apply does the same and says so. Unticked rows are never staged.
- **The bulk rule holds.** New risks, new decisions, milestone moves and health changes always start **unticked** and are ticked one at a time. Routine rows (a new action, a due date, done, owner) start ticked.
- Clicking a row opens it in the peek layout Review uses (BL-177) to edit it first. Every row passes the schema's validation; a row that fails says why and stays unticked.
- **Hedged words** ("probably", "might", "to confirm") never move a milestone or change health: the row is shown unticked, with a confirm action proposed beside it that shows as an early warning on the milestone.
- The same engine as quick capture (cx-minutes) and cx-edit, given a note as the source, with the staging checks: repeats of an existing item (BL-221), probably-done evidence (BL-218), vague actions (BL-221); BL-297's matching when it lands.
- Each item's source is the note and paragraph (`projects/<folder>/08 Notes/<title>.md#p4`); its source link opens the note at that line, highlighted.
- What was applied is recorded beside the note, not in it: `system/staging/notes-sent.json` (path, paragraph fingerprint, item IDs). The note text stays as written; a margin tick shows lines that became items, and running Find updates again only looks at new or changed lines.
- Also from one line (select, then AI › Make this an action, a risk, a decision or an update) and while typing (a checklist line with an `@person` and a date gets a faint dotted underline; a click opens the panel for that line). Never unattended, never from the sweep. A Confidential note's items are marked Sensitive.

**Rules text.** `creaite-rules.md` changes with this item: the folder map gains `08 Notes` (and `notes-sent.json` in staging); "Approval before writes" names the Find updates panel as a place Alan approves; Project documents notes that notes are passive until Find updates; the editor line in Dashboard editing names Tiptap.

**Done when:**
- A: every Current state round-trips unchanged; Current state, the Draft email, Prep notes and the peek description use the one editor; the BL-207 marks and images work as before.
- B: a note is created, edited and autosaved through `filechange.py` (undoable) in `08 Notes`; the list collapses and stays collapsed after a reload; links, backlinks and item chips work; search finds the note and ask creaite cites it.
- C: ⌘⇧N captures from any page, guesses the project with its reason, and falls back to Unfiled.
- D: each AI option returns a suggestion that changes nothing until Accept, with the fact check shown; the route has no tools.
- E: the mockup's catch-up note yields the rows shown there; Apply writes the ticked rows in one apply and Undo reverses it; new risks and milestone moves start unticked; hedged lines don't move milestones; a second run skips sent lines; each item's source opens the note at its line.
- Tests for each part, Help updated, `dev/dashboard-spec.md` updated.

**Touches:** `system/templates/vendor/` (the Tiptap bundle, its licence, the manifest), `dev/tools/` (the bundle's build script), the dashboard modules (the editor wrapper, `0056-current-state-edited-in-place-bl-47.js` and the other editors, the project page's tabs, a Notes module, the drawer, the panel), `system/scripts/paths.py` (`notes` in `LOCATION_DEFAULTS` and `DEFAULT_FOLDERS`, `folder`, the Documents skip list), `filechange.py`, `search.py` and `tracker.py index` (kind `note`), `live_server.py` (`/api/notes/*`, `/api/edit/ai`, `/api/notes/find`), `minutes.py`, `extraction.py`, `propose.py` (a note as source), `reach.py` (`08 Notes` as Alan's own notes: ordinary), `system/templates/notes/` (the four templates), `system/creaite-rules.md`, `system/templates/help.md`, `dev/dashboard-spec.md`, `dev/tests/`.

**Decisions (Alan, 13-10-2026).** Called Notes, not Wiki. Options A (Notes in the project) and C (capture drawer); B (a Notes page of its own) not chosen, though it can be added later on the same files. Tiptap for every editor. Stored with the project, in `08 Notes`; portfolio notes in the portfolio folder. The notes list is collapsible. An open note is editable, with no Edit button. AI options on selected text. Find updates applies from the panel beside the note rather than sending to Review. Quick capture (FR-71) merges into Notes. Tiptap's Markdown extension is accepted while labelled beta upstream, with the version pinned and the byte-for-byte round-trip of every Current state as the gate. **Release: v2.0.0, all five parts.**

**Decisions (Alan, 13-10-2026, via laptop 2).** Tiptap's Markdown escaping: a custom exact writer, re-checked by the round-trip gate on every Tiptap upgrade, not a one-time rewrite of Current states. Italic and nested numbering: the writer learns creaite's style (`_italic_`, 2-space nesting), so stored text never changes. The notes server: all seven decisions in `dev/V20-NOTES-SERVER-NOTE.md` accepted as written (confidential notes searchable but kept out of ask creaite; reading a note in OneDrive counts as outside content; notes have their own search group). `v20-notes-server` is parked until v2.0.0 ships BL-301 whole. Before the notes switch, run the round-trip gate over Alan's live Current states (read-only, on laptop 1, with Alan).

**More decisions (Alan, 13-10-2026, Tiptap).** HTML comments in a Current state are **kept**, by a custom node that hides them while editing and saves them back byte for byte. Notes use **Tiptap's own** table and checklist format as standard, gated on idempotence (save, load and save again gives the same bytes). The round-trip gate runs over Alan's **real** Current states **now** (read-only, on a copy, with Alan). The page-size cost (about 488 KB raw, 154 KB compressed) is **fine as is**: the full feature set stays.

**Decision (Alan, 14-10-2026, directly to Team 1): a note's file is renamed with its title.** Renaming a note in the Notes tab moves its file through `filechange.py`, and `/api/notes/rename` issues the one-time approval for that single move itself, with no card. Alan starts it by retitling the note, as Find updates' Apply is his approval. It applies only to a note-to-note move inside the notes folder, never in a run that has read outside content; no guard file changes.

**Real-data gate (13-10-2026, run by Alan, read-only, `--private --exact`):** 3 of 4 Current state panes round-trip exactly; the fourth is a pane holding only an HTML comment, which the writer still drops. The comment node (Alan's decision) closes it.

**Decided (Alan, 15-10-2026), the integration note's open questions** (`dev/V20-INTEGRATION-NOTE.md` on `v20-base`):
1. **Tabs:** not in v2.0.0. The project page keeps Overview and Notes; Work, Milestones, Meetings and Files as tabs wait for BL-317 (on hold).
2. **Clicks in a note:** a click on a `[[note]]` link or an item chip opens it; ⌥-click edits inside it. Kept as built.
3. **Note drafts** (`system/staging/drafts/notes/`) stay in the daily backup zip (BL-323).
4. **Notes are exempt from outside content.** Reading Alan's own note, a `.md` directly inside a project's or the portfolio's notes folder as `notes.note_of` accepts, no longer marks an ask creaite run (`live_server.py` `OUTSIDE_CONTENT`, the hook in `reach.py`). Everything else in OneDrive still marks: a note's pictures, other files, transcripts and documents. **This is a guard change**, made on its own branch with its own tests, and `creaite-rules.md`'s BL-141 lines say so.

**Recommended by the Product Manager, 15-10-2026 (Alan may change them):** E's calls stay as built (each list item is a line; a hedged milestone or health row can't be ticked; only a "Very likely" repeat starts unticked; the memory line starts unticked; "Linked to …" is a note, not a staged link; rows open in the peek's layout inside the panel). The Draft email preview stays a plain contenteditable in v2.0.0 (option a); it moves to the one editor later.

The release plan is `dev/sprints/v200-notes-release.md`.

### BL-304 — Changes appear at once, and only what changed is redrawn

**Plan (as imported):** **In v1.9.4 (Alan, 14-10-2026)**, beside BL-09

**In v1.9.4 (Alan, 14-10-2026)**, beside BL-09.

**Decided (Alan, 15-10-2026): Retry keeps Alan's value.** After "changed elsewhere", Retry applies his edit on top of the item as it now is (as built); the other change stays in the history, and Undo works.

**Decided (Alan, 14-10-2026): Retry after "changed elsewhere" overwrites.** When an instant save is refused because the item changed elsewhere, **Retry** re-applies Alan's value on top of the item as it now is, so his value wins; it doesn't go to Review as a conflict. The other change stays in Activity and can be undone.

Raised 2026-10-13 (Alan), from research into how Linear, Asana and Plane are built (Linear's local-first object pool and optimistic updates; Asana's LunaDb subscriptions; Plane's MobX stores). **Technical. In v1.9.0 (Alan, 13-10-2026; moved from v2.0.0), after BL-256 in the same release** (it needs signals and the component store). No schema change.

**Why.** Today an edit waits for the server to stage and apply it (about 3 seconds with auto-apply) before the screen changes, and many actions reload all of the page's data (`/api/data`) and redraw whole sections. The tools Alan compares creaite with feel instant because the screen never waits: the change shows at once and is saved in the background. creaite is already local (SQLite on the laptop), so it can have the same feel without their sync machinery.

**1. Changes appear at once (optimistic updates).**
- An edit in the peek, Work's cells and lists, the board, ⌘K, Review's Approve and Reject, and the right-click menu updates the in-memory record and the screen **immediately**, marked as saving (a quiet dot, like the peek's staged dot), then is staged and applied through the live server as now.
- On success the mark clears; on a refusal or a failed apply the record is **put back** and a message says what happened and why ("Not saved: FAL-A-007 changed elsewhere; reloaded it"), with the failed change kept for Retry.
- **The rules don't move:** `tracker.py apply` stays the only writer; approval before writes holds (a change Alan makes is his approval, exactly as auto-apply today); with auto-apply off the screen shows the change as **staged** until Apply. Undo works on an unsaved change as on a saved one.
- One change at a time per record: a second edit to a record still saving waits for the first.

**2. Load once, then update only what changed.**
- The page loads its data once into a store (signals, per BL-256 and the component guide), keyed by item ID.
- **BL-253's live-updates stream** carries what changed (the IDs and tables after an apply, a sweep, minutes, Quick capture, a save from another window), and the page fetches **just those records** (a new read-only, token-checked `/api/records?ids=…`), updating the store; only the components that show them redraw.
- A full reload stays as the fallback: on start, after a server restart (BL-269), when the stream has a gap, and from Settings › Diagnostics ("Reload all data"). The 30-second pulse stays as the safety net.

**Done when:** an edit in the peek, a Work cell, the board and ⌘K shows on screen within a frame and is applied in the background; a forced apply failure puts it back with the reason and offers Retry; with auto-apply off it shows as staged; an apply from another source updates only the changed rows (a test counts `/api/data` calls: none for a single change); a gap in the stream falls back to a full reload; scroll, focus and text being typed survive an update (BL-262's rule, for every screen); BL-254's snapshots unchanged.

**Touches:** `system/templates/dashboard/` (the store, the save path for every edit, the saving mark), `live_server.py` (`/api/records`; the live-updates events carry IDs), `build_dashboard.py` (one record's data by ID), `dev/COMPONENTS.md` (the store section), `dev/tests/`.

### BL-313 — Plain words

**Plan (as imported):** **On hold (Alan, 14-10-2026)**; the review is in dev/reviews/BL-313-review.md

**On hold (Alan, 14-10-2026).** The review is in `dev/reviews/BL-313-review.md`.

Raised 2026-10-13 (Alan), from the UX review against Linear, Asana and Plane: the dashboard's code uses "proposal" about 230 times, "apply" about 230 and "staged" over 100, and much of it reaches Alan. **In v2.1.0 (Alan, 13-10-2026; moved from v1.9.1), on hold for Alan's full review before it is committed; the review pack is `dev/reviews/BL-313-review.md`.** No schema change.

**One model, in Alan's words:** what you change is saved (with Undo); what creaite suggests waits for you in Review.
- **With auto-apply on (the default):** your own edits read "Saved", with Undo; the peek's staged dot means "saving"; no "staged", "apply", "Apply", "pending apply" or "proposal" in the dashboard, its messages or Help.
- **creaite's suggestions** (minutes, sweeps, drafts, ask creaite's ideas) are "suggestions" waiting "in Review". Approve and Reject stay.
- **ask creaite's replies** use the same words: ASK_PROMPT and the skills' panel lines never say "at the next apply" when auto-apply is on; they say "Saved" or "waiting for you in Review".
- **With auto-apply off:** "Ready to save", a count with one Save button. "Apply" survives only as a command typed in Claude Code.
- **Unchanged underneath:** proposals, staging and `tracker.py apply` stay as they are, in code and dev docs.
- **A check:** check.py or a test counts user-facing strings (the dashboard's text, Help, the panel prompt) containing staged, apply or proposal outside an allow list; the ratchet stops new ones.

**Done when:** with auto-apply on, a full click-through (peek, Work cell, board, ⌘K, Review, an ask creaite change) shows none of the three words and Help reads the same; with it off, "Ready to save" and one Save appear; the string check passes. **Touches:** `system/templates/dashboard/src/`, help.md, live_server.py (ASK_PROMPT, CONFIRMED_PROMPT), the cx-edit, cx-review and cx-sweep panel lines, check.py, tests. Pairs with BL-304 whenever that's scheduled; doesn't depend on it.

### BL-316 — Consistency audit after the move to components

**Plan (as imported):** **In v1.9.5 (Alan, 14-10-2026)**, after BL-325, so every screen is checked once the shared scale is in

**In v1.9.5 (Alan, 14-10-2026)**, after BL-325, so every screen is checked once the shared scale is in.

Raised 2026-10-13 (Alan). **Not scheduled; after BL-256's screens.** Each sprint built its own filter bar, menu, picker, dialog and toast; BL-256's guide (`dev/COMPONENTS.md`) is the fix, and this audit checks it delivered.
- **Inventory** every screen against the blocks (Menu, Dialog, Picker, Combobox, FilterBar, Tabs, Toast, Peek, StatusDot, Chip); **move or retire** each own copy, one screen at a time.
- **Behaviour, not just code:** the same keys, focus return, wording, empty states and Undo everywhere; a Chrome test runs one script (open, ↑ ↓, Enter, Esc, Tab) on every menu, picker and dialog on every screen.
- **Ratchet:** check.py counts the old helpers (newMenu, pkList, drawPicker, snackAdd and the rest), falling to zero.

**Done when:** every screen uses the blocks, the shared behaviour test passes everywhere, and the old-helper count is 0.

### BL-317 — Reports you live in: a living status page per project

**Plan (as imported):** **On hold (Alan, 14-10-2026): design paused, to revisit later; in no release.** Mockup so far: the project page as six tabs, with Milestones worked through (`dev/mockups/project-page-mockup.html`; published https://claude.ai/artifact/Xk2SGW7fz6AJGCr45bPjfL)

Raised 2026-10-13 (Alan). **On hold (Alan, 14-10-2026): design paused, to revisit later; in no release.**

**Design so far (14-10-2026), to pick up from:** mockup `dev/mockups/project-page-mockup.html` (published https://claude.ai/artifact/Xk2SGW7fz6AJGCr45bPjfL). The project page becomes six tabs (Status first, then Overview, Milestones, Work, Files, Reports), regrouping today's cockpit (the mockup maps each part). Alan's direction on **Milestones**: every function of today's Plan and Movement page and the milestone editor lives on the Milestones tab unchanged, including the Client and Internal views; new, the tab chooses what Status shows, either the **full picture** or **3 or 4 milestones as tiles**. Open when it resumes: the default for a new project (suggested: tiles, the next 3 open), whether a tile stays when its milestone is achieved (suggested: it stays), which tab opens first (suggested: Status), and the four Status choices in the mockup. Overview, Work, Files and Reports are drawn but not yet reviewed.

Earlier: **Not scheduled (Alan, 13-10-2026).** Mockup: the calm mockups, tab 8, option A (B, the Friday composer, and C, a portfolio page with BL-02, were not chosen). Overlaps BL-59 (on hold).
- **One Status page** per project, always current: health, Current state, milestones, top risks, help needed; edited in place, every sentence keeping its evidence (BL-207).
- **Each week is a snapshot:** a timeline of past weeks; Friday's report is "this week", not a new document.
- **Client view** shows the client-safe version (client-visible flags; BL-288's privacy). **Export to Word** makes the branded weekly or client report from it, so the report builders take the page as their source.

**Touches:** a new Status area (on the components), report.py, the weekly and client skills, tests.

### BL-324 — UI audit: fix first

**Plan (as imported):** **In v1.9.5 (Alan, 14-10-2026); being built by Team 2 on `v195-ui-fixes`**

Raised 2026-10-14 (Alan), from the UI/UX consistency and design-token audit (`dev/reviews/ui-audit-2026-10-14.md`, branch `dev-ui-audit`; verdict amber). **In v1.9.5 (Alan, 14-10-2026)**, beside BL-10 and BL-03; Team 2 started building it on `v195-ui-fixes` the same day, at Alan's request. No schema change.

**The ten points (Alan approved building all ten, 14-10-2026).** The handover counts the faint-text and past-time contrast findings (4 and 5) as one point, so it's the eight P1 findings plus three P2 items.

**The eight P1 findings:**
1. The Saffron logo bar is wrong in system dark mode: `--saffron` has only an explicit-dark rule (`style.css:2274`).
2. `--line-strong` is undefined in the creaite, Brightwater and Notion palettes and read without a fallback, so those borders disappear (`style.css:2118`).
3. Count badges are unreadable in dark mode: white `--bad-ink` on the pale dark `--bad` is 1.71:1, in five palettes (the rail badges).
4. `--faint` text is under 4.5:1 in most palettes: check where it's used; fine only for placeholders and disabled text.
5. Today's past-time marks (`--day-past`, `--day-sun`) are below 3:1 in every palette; Brightwater's now-line is 2.95:1.
6. The column-resize handles (`.colrz`, `work.js`) have `role=separator` without `aria-valuenow`: 220 axe-critical nodes on Work, Projects and Today. Add the value attributes or drop the role.
7. The sortable headers on People and Settings (`th[data-psort]`) use ARIA attributes `th` doesn't allow.
8. Dead or invalid tokens: `--pc` is never set (`.ms i.pc` never draws); the guides read the undefined `--d2`.

**The three P2 items:**
9. Control drift: `.btn`, inputs and section headings are styled differently from page to page (a button is 32px on five pages, 28 or 30px on Today; six input sizes; four heading styles). Bring them to one style each.
10. The Help page ignores the theme's fonts.
11. The prep page uses the system font and its own status colours instead of the theme's.

**Not in this item, and not being built:** the rest of the audit's P2 and P3 work, above all a shared type, radius, spacing, shadow and z-index scale under the colour tokens. It is for Alan to place.

**Done when:** each point is fixed in every palette, light, dark and system; buttons, inputs and section headings measure the same on every page; the audit's tools (`dev/tools/token_audit.py`, `ui_audit.py`) report none of the eight; axe reports no critical node on Work, Projects, Today, People or Settings; any snapshot that changes is re-recorded with Alan's agreement (BL-254).

### BL-325 — One design scale

**Plan (as imported):** **In v1.9.5 (Alan, 14-10-2026)**, after BL-324. **Ready for a sprint:** Alan's three choices made (below)

Raised 2026-10-14 (Alan), from the UI/UX audit's wider findings (`dev/reviews/ui-audit-2026-10-14.md`, "Token and scale drift" and "Consistency across pages and surfaces"). **In v1.9.5 (Alan, 14-10-2026)**, after BL-324 (the same files; BL-324 fixes the worst drift, BL-325 removes its cause). No schema change.

**Why.** The colour tokens are sound, but nothing sits beneath them. `style.css` has 47 font sizes (17 px values and 30 rem values from the embedded guide), 23 radii, about 60 spacing values, 45 box shadows and 20 z-index values (0 to 210, ad hoc). So the same control is drawn differently from page to page: `.btn` in three sizes, `.ib` in two, inputs at 30, 32, 36, 40 and 58px with radii of 6, 8 and 10px, `h2` in four styles, `.tag` in two fonts.

**What it does.**
- **Tokens:** a type scale (about six sizes, near-duplicates merged: 11, 11.5 and 12px; 13 and 13.5px; 14 and 14.5px), a spacing scale (a 4px base), three or four radii, three shadow levels and named z-index layers. Every palette keeps its colours; the scale is shared by all nine.
- **Controls on the scale:** `.btn`, `.linkbtn`, `.ib`, `.mini`, inputs and selects, `h1`/`h2`, `.tag`, one height and radius each (Today's 34px title stays, by design).
- **Literals to tokens:** the ten hard-coded colours that exactly equal an existing token become `var(--x)`; the 23 near-duplicate token pairs are merged where the values match.
- **Surfaces:** the Help page's rem scale moves onto the shared scale (BL-324 already fixes its fonts); the offline page uses the theme's font and the dashboard's dark accent.
- **Touch targets** of at least 24px: checkboxes (13 to 16px on Review, Intake and Activity), the column-resize handles and the Settings toggles.
- **Small wording fix:** Projects' "(In 24 days)" becomes "(in 24 days)". The written-out dates there stay (decided, Alan, 14-10-2026).
- **Out of scope (decided, Alan, 14-10-2026):** Word templates stay in the Brightwater brand; email drafts stay in Calibri. The audit's taste-rule findings (the Impeccable detector, P3) are weighed against creaite's own design, not treated as defects.

**Decided (Alan, 14-10-2026):**
1. **Section headings, one pattern:** sentence case at one size, as Settings does; Today's uppercase labels and Intake's Title Case with icons change to match.
2. **Primary actions stay as they are:** BL-325 doesn't change which treatment each page uses for its main action (Today's and Intake's filled button, Review's outlined Approve, Work's tinted "+"). They move onto the shared size and radius only.
3. **Snapshots:** re-recorded in one agreed pass at the end, with a before-and-after view per screen for Alan to look through (BL-254).

**Done when:** `dev/tools/token_audit.py` finds no font size, radius, spacing, shadow or z-index outside the scale (bar listed exceptions); `ui_audit.py` finds one variant of each control across pages; every palette still passes its contrast checks; no page scrolls sideways at 320px; touch targets are at least 24px; Alan has agreed the re-recorded snapshots.

**Touches:** `system/templates/dashboard/style.css` (tokens, every control), the components (`dev/COMPONENTS.md`), the guides' embedded CSS, the offline page, `dev/tools/token_audit.py` (exceptions list), the snapshots, Help where it shows controls.

### BL-326 — ask creaite shows the ask, the activity and the outcome, never a run's machine text

**Plan (as imported):** **In v1.9.4 (Alan, 15-10-2026)**, with BL-330: both built on `v195-run-chat-bl330`. (Earlier placed in v2.1.0, then v1.9.5, on 14-10-2026.)

Raised 2026-10-14 (Alan), a defect. No schema change. (Placed in v2.1.0, then v1.9.5, on 14-10-2026.)

**In v1.9.4 (Alan, 15-10-2026)**, with BL-330, because both are built and approved on `v195-run-chat-bl330`. The release plan is `dev/sprints/v194-release.md`.

**What happens now.** Pressing **Prep page** for a meeting in the dashboard starts a run through the run engine (`/api/prep/page`, `kind="prep"`), and ask creaite shows it as a chat. That chat shows the whole working copy: the prompt (`prep_page.PROMPT`: "creaite prep page. Research one meeting for Alan and reply with ONLY a JSON object, nothing else. Read-only: …"), the meeting's context as JSON, and Claude's reply, the JSON with the finished page's HTML in it.

**What Alan sees instead (Alan, 14-10-2026): the ask, the activity and the closure.**
- **The ask:** one plain line, as if Alan had typed it: "Prep page for FAL weekly with Northgate, Thursday 15th October 10:00".
- **The activity:** the run's working status as it is today (the rotating line and "✓ n steps", BL-195), with the research steps in plain words ("Reading the project's open items", "Searching mail for the Northgate environment dates"). Never a prompt, JSON, HTML or a tool's raw output.
- **The closure:** one line with the outcome and a link: "Saved the prep page in FAL › 02 Meetings › Agendas · Open", or, when it fails, what went wrong and what to do ("Couldn't finish: the meeting has no project. Choose one and try again").
- **The rest stays where it is:** the server keeps the full prompt and reply for troubleshooting in the debug log's run record (counts and IDs only, as BL-102 requires) and behind Settings › Diagnostics, never in the chat.

**The same rule for every run creaite starts itself,** not only the prep page: Generate (Current state), Draft agenda, Shape this meeting, the meeting checks and loads, Polish and the other AI drafts, and the VIP check, wherever they appear in ask creaite. A chat Alan types keeps showing his words and the reply as now.

**Done when:** a Prep page run in ask creaite shows exactly three things (the ask line, the activity, the closure line), with no `{`, `<`, prompt text or JSON in the panel, for success, failure and Stop; the same for each kind of run listed above; the chat history file keeps the plain lines, never the prompt; a test checks each kind of run; Help says what ask creaite shows for a run creaite started.

**Touches:** `live_server.py` (the run engine's chat record for `kind` other than "ask"), `system/templates/dashboard/src/ask.js` (how a run's messages are drawn), `prep_page.py` (the ask and closure lines), the drafts module, `help.md`, `dev/tests/`.

### BL-327 — Defect: slow saves and a slow first load

**Plan (as imported):** **Defect. In v1.9.4 (Alan placed it in v1.9.2 on 14-10-2026; v1.9.2 and v1.9.3 were already cut, so it moved to the next open release).**

Raised 2026-10-14 (Alan), from the live debug log (1.8.0, 13-10-2026, logging at debug). **Defect. In v1.9.4 (Alan placed it in v1.9.2 on 14-10-2026; v1.9.2 and v1.9.3 were already cut, so it moved to the next open release).** No schema change.

**What happened.** Most applies took about 1 s, but four took 14 to 24 s (10:38 23.9 s; 11:15 19.2 s and 14.2 s; 11:35 19.6 s) and an approval 21.8 s (11:06). At 10:38 the tracker write finished at 10:38:27 and nothing was logged until `build_dashboard` started at 10:38:48. The first page load after each server start took 5 to 14.5 s (nine times). `tracker.after_apply()` runs `offsite_copy()` (the backup copy into OneDrive) and `refresh_index()` (a **full** `build_index()` whenever anything changed, re-reading every document in the OneDrive project folders) before the dashboard rebuild and the Excel export, all before `/api/apply` answers. Neither step logs its time, so the log can't say which took the 21 s.

**Fix.**
1. **Log each step** of `after_apply` (offsite copy, index, dashboard, Excel) with its duration, and the page build's parts on a first load.
2. **Incremental index:** re-index only the files whose modification time or hash changed since the last build (the stamp in `system/search/`), and records changed by the apply; a full rebuild only when the index version changes.
3. **Don't make the save wait:** `/api/apply` answers once the tracker is written and the dashboard data is rebuilt; the index refresh and the offsite copy run after, in the background (one at a time), and the debug log records them. Search may be a few seconds behind; nothing else changes.
4. **First load:** the page is served from the last built data at once; anything slow (the index state, the OneDrive file list) is fetched after, not before.

**Done when:** an apply returns in about 1 to 2 s on the sample vault with a changed document (a timed test), the index catches up within seconds, the log shows each step's time, and a first page load after a start is under 2 s.

**Note (Team 1, 14-10-2026):** BL-323 (v1.9.3) makes `offsite_copy` the daily zip; build this on it.

**Touches:** `tracker.py` (`after_apply`, `refresh_index`, `build_index`), `live_server.py` (`/api/apply`, background steps, the page), `build_dashboard.py`, `dev/tests/`.

### BL-328 — Defect: a sweep's lock outlives the sweep

**Plan (as imported):** **Defect. In v1.9.4 (Alan placed it in v1.9.2 on 14-10-2026; v1.9.2 and v1.9.3 were already cut, so it moved to the next open release).**

Raised 2026-10-14 (Alan), from the live debug log. **Defect. In v1.9.4 (Alan placed it in v1.9.2 on 14-10-2026; v1.9.2 and v1.9.3 were already cut, so it moved to the next open release).** No schema change.

**What happened.** A sweep started about 08:39 on 13-10 took the lock and never released it (the server stopped at 09:25 with no unlock). The next sweep, at 10:54, logged "a stale sweep lock (over 30 minutes old) was replaced" and only then ran. The 30-minute recovery works, but a sweep in those 30 minutes would have been refused.

**Fix.** Release the sweep lock whenever a sweep run ends, however it ends: finished, stopped by Alan, timed out, refused by the guard, or the server stopping (on shutdown the server releases any lock its own runs hold). The lock records the run's ID, so the server knows it is its own. Doctor and Settings › Health show a lock held with no sweep running, with Release.

**Done when:** stopping a sweep, its timing out and stopping the server each leave no lock (tests); a held lock with no run shows in the health check.

**Touches:** `sweep.py` (`lock`, `unlock`, the run ID), `live_server.py` (run end, shutdown), `doctor.py`, `dev/tests/`.

### BL-329 — Defect: two servers start at once

**Plan (as imported):** **Defect. In v1.9.4 (Alan placed it in v1.9.2 on 14-10-2026; v1.9.2 and v1.9.3 were already cut, so it moved to the next open release).**

Raised 2026-10-14 (Alan), from the live debug log. **Defect. In v1.9.4 (Alan placed it in v1.9.2 on 14-10-2026; v1.9.2 and v1.9.3 were already cut, so it moved to the next open release).** No schema change.

**What happened.** At 18:12:19 a server started; at 18:12:33 the launcher started another, which found the port taken and exited 1 ("exit 1 after 0.0s"). The same at 21:45:02 and 21:47:56 (around the 1.8.0 update's restart). Harmless, but it's noise, and the window can wait on the wrong server.

**Fix.** The server writes a "starting" mark (its process ID and port) as it starts and clears it once it answers `/health`. The launcher, finding a server starting, waits for its `/health` (up to about 20 s) instead of starting another. A server that finds the port already taken by this vault's own server logs "already running" at INFO and exits 0, not a warning.

**Done when:** two launches in quick succession give one server and one window (a test with a slow-starting server); the log shows no "exit 1" for it.

**Touches:** `launch.py`, `live_server.py` (the starting mark, the port check), `dev/tests/`.

### BL-330 — Defect: a remembered chat that's gone

**Plan (as imported):** **Defect. In v1.9.4 (Alan placed it in v1.9.2 on 14-10-2026; v1.9.2 and v1.9.3 were already cut, so it moved to the next open release).**

Raised 2026-10-14 (Alan), from the live debug log. **Defect. In v1.9.4 (Alan placed it in v1.9.2 on 14-10-2026; v1.9.2 and v1.9.3 were already cut, so it moved to the next open release).** No schema change.

**What happened.** Six times on 13-10 (08:39 twice, 09:40, 09:44, 11:14, 18:12) the page asked `POST /api/chat` for the chat it remembers and got 404: the chat had been removed (only the 10 most recent are kept, BL-32) or belonged to another vault. The page recovered quietly (a new chat), but each was logged as a WARN.

**Fix.** On 404 the page forgets the remembered chat at once (so it isn't asked for again on the next load), and the server logs a missing chat at INFO, not WARN. The remembered chat is kept per vault.

**Done when:** a removed chat is asked for once and then forgotten; the log shows no WARN for it; a test for each.

**Touches:** `system/templates/dashboard/src/ask.js` (`loadChat`), `live_server.py` (`/api/chat`), `dev/tests/`.

### BL-331 — Move back one archived report

**Plan (as imported):** **In v1.9.5 (Alan, 15-10-2026)**, after BL-10 and BL-03; built on `v196-move-back`

Raised 2026-10-14 (Alan, directly to Team 1), a follow-up to BL-03. No schema change.

**In v1.9.5 (Alan, 15-10-2026)**, on BL-10 and BL-03's archiving; built on `v196-move-back`. The release plan is `dev/sprints/v195-release.md`.
- In Files, a report, minutes or Steerco one-pager shown as archived (in the engagement's or the portfolio's `_Archive/`) gets a **Move back** action.
- It returns that one file to its place (the same folder below `_Archive/`), never overwriting: a name already taken gets a number.
- It goes on the approval card, with the move shown, and is applied by `tracker.py apply` through BL-09's agreed `move` exception; ask creaite can't do it. Logged and undoable.
- **Done when:** a moved-back file is indexed and searchable again, its stored links still open, Undo puts it back in `_Archive/`, and ask creaite still can't read or move anything there.

### BL-333 — Defect: the page scrolls past its own bottom

**Plan (as imported):** **Defect. In v1.9.5 (Alan, 14-10-2026).**

Raised 2026-10-14 (Alan, screenshot of the Prep page), via the Product Manager. **Defect. In v1.9.5 (Alan, 14-10-2026).** No schema change.

**Cause** (reproduced on sample data in headless Chrome, v1.9.1): `.vh` (visually hidden text) is `position:absolute`, and each screen's scroll box (`#v-today` and the rest, `overflow:auto`) is `position:static`. So a hidden span lower down a long screen takes `body` as its containing block, escapes the screen's clipping, and sits at its natural place below the window, growing the window's scroll height to reach it.
- **Today:** `span.vh#pfd-ABC` (the project's description in the Portfolio table, today.js:318) sits at y 1635 in a 913 px window, so the document is 1636 px tall while the shell is 913.
- **Prep page:** the same, from the `.vh` label for `#pp-q` (PrepPage.jsx:240) and the "not in the people register" spans (PrepFacts.jsx:63).
- **Other screens:** Work, Review, Settings and Activity were fine in the probe, but any long screen with a `.vh` can do it.

**Fix.** Give every screen's scroll box `position:relative`, so hidden text is clipped inside it: one rule beside the screen styles; nothing moves visually. Don't hide overflow on html or body, which would hide the next case too.

**Done when:** on every screen and in Prep, with long sample data, `document.scrollingElement.scrollHeight === innerHeight` and the window never scrolls; a browser test checks every screen (test_ui_sweep.py's screen list extended).

**Touches:** the dashboard CSS for the screens (`[id^=v-]` or the view class), `dev/tests/test_ui_sweep.py`.

### BL-334 — Alerts read the conversation, not the message

**Plan (as imported):** **In v1.9.5 (Alan, 14-10-2026).**

Raised 2026-10-14 (Alan, from live Today), via the Product Manager. **In v1.9.5 (Alan, 14-10-2026).** No schema change. (Live names are left out of this repository: sample data only.)

**Problem.** `VIP_PROMPT` (live_server.py) asks for "one object per message", so every message becomes its own Today card with a gist of up to 140 characters, and none says what the conversation came to.
- One chat between a followed person and a colleague became 3 cards: a greeting, a commitment ("her team will take the solution from production to live") and a decision (go-live work falls under the existing contract). All three said "no project", although the chat's title named the client.
- One group chat became 3 cards: a greeting, "shares the UAT schedule", and a follow-up, all titled "Group chat" and all "no project".

**Change.**
1. **The unit is the conversation:** grouped by the Teams chat ID or mail conversation ID, covering everything since the last check. A conversation that carries on updates the same card ("updated HH:MM") instead of adding one.
2. **Read the whole conversation:** everyone's messages, not only the followed person's, plus a few earlier ones for context; and the chat or thread title, the participants and any attachment names.
3. **Report the outcome, not the to and fro:** a one- or two-line summary, then the candidate items: actions (owner and due date where stated), decisions and risks. Greetings and chatter never become a card or a line.
4. **Quiet line:** a conversation with nothing actionable gets one quiet line ("<person> with <person>: nothing for you"), not a card with buttons.
5. **Wait for quiet:** if a conversation's last message is under 15 minutes old, wait at most 15 minutes so the card covers the whole exchange.
6. **Match the project from the whole conversation:** the title first, then the participants, attachment names and content, against the project register's signals as the sweep does.
7. **Card title:** the chat's or thread's own title where it has one, never a generic "Group chat"; without one, the people in it.

**Alan's decisions (14-10-2026).**
- **A.** Nothing goes to Review unless he asks: the candidates sit on the card; **Create work item** stages that item as a proposal for Review; **Dismiss** sends and records nothing.
- **B.** Nothing actionable: the quiet line (point 4).
- **C.** Overlap with the sweep: the sweep skips a conversation the check has already summarised, unless new messages arrived after that summary, so the same items are never proposed twice.
- **D.** Mail threads: the same rules.

**Unchanged.** No message text is kept: the summary and items are in Claude's own words (the gist limit rises to about 300 characters for the summary). Private and confidential messages still get only a neutral line. The word VIP never appears on screen (BL-288). Nothing reaches the tracker without approval; the check stays read-only on Microsoft 365. The existing Create work item and Dismiss buttons stay, per candidate item.

**Done when:**
- with a stand-in claude, a three-message chat (greeting, commitment, decision) gives one card with one summary, one action and one decision, its project matched from the chat title;
- a greeting-only chat gives one quiet line and no buttons;
- a later message updates the same card;
- Dismiss stages nothing, and Create work item stages one proposal;
- a later sweep proposes nothing from a conversation already summarised;
- vip.json still holds no message text.

**Touches:** `VIP_PROMPT` and `vip_check` (live_server.py); `sweep.py`'s vip record and the vip.json shape (conversation ID, summary, candidates, updated time) and the sweep's skip for summarised conversations; the Today alert card (today.js); test_vip* and the BL-296 alert-action tests.

### BL-335 — The weekly report, redesigned and built in creaite

**Plan (as imported):** **In v2.1.0 (Alan, 14-10-2026). Priority High: the Reporting category, with BL-336 and BL-337.** Needs v2.0.0's one editor

Raised 2026-10-14 (Alan). **In v2.1.0 (Alan, 14-10-2026). Priority High (Alan, 14-10-2026: "log the entire reporting category in backlog as a priority"): the Reporting category, with BL-336 (the client report) and BL-337 (the reporting space and the Reports page).** Mockup: a private artifact (Alan's claude.ai, "Weekly report redesign"), not committed here because it uses the firm's real brand. Depends on v2.0.0's one editor (BL-301 part A). No schema change expected; the filed report is a file, the layout a per-project setting.

**Decided (Alan, 14-10-2026):**
1. **Built in creaite,** with exports, not drafted in Word.
2. **Filed as a creaite report:** `YYYY-MM-DD Weekly report - <Project name>.html` in the project's weekly reports folder. One file with two parts: the page as approved, and the report's data (each section, its order, its text, which rows show, the items as they stood that Friday). creaite reopens it in the report view to edit again; saving makes a new version and keeps the earlier one, with Undo. Outside creaite it opens in any browser. Search reads each section and figure.
3. **Exports to share, on demand:** Word (`.docx`, the firm's template), PDF (printed from the page by Chrome, already required) and HTML (one read-only page without the editing data). An export is filed beside the report only when Alan ticks it. Nothing is ever sent.
4. **Current state at the end,** as context.
5. **The client report uses the same layout,** as a Client view of the same week's report (BL-336).

**The page.** A true A4 page shown at 80% of the window, zoomable from 40% to 80% (trackpad pinch, ⌘+ ⌘− ⌘0, or − + in the toolbar), with page breaks marked, so what Alan sees is what exports. **Show as exported** previews it without any editing controls. Body text 14px (about 10.5pt), tables 12.5px (about 9.5pt).

**Layout, top to bottom (the default; every section can move):**
1. **Header, one row:** "Weekly report · Internal", the project's name, the week ending and the client on the left; the firm's logo then up to two logos (client, partner) on the right.
2. **Health:** the flag with six weeks of trend flush under it (dates under the first and last), and the reason written as a one-sentence headline, then what it was last week and why.
3. **At a glance:** the next milestone and its slip, overdue actions, high risks open, decisions needed.
4. **Summary:** 3 to 5 sentences in the executive voice (BL-106): the position, the one thing, progress, focus.
5. **Milestones:** a timeline that scrolls sideways and opens at today; drag its bottom edge to make it taller, which zooms in. The milestone list toggles in under it and is exported only when it's showing. The export starts the line just before today, shows what fits at a comfortable size and says what follows ("2 more milestones to March 2027 →"); it never squeezes the whole line in.
6. **What we need from people:** a table of ask, from whom, by when and why it matters. Asks come from decisions needed, overdue promises made to Alan (waiting on), and risk responses or overdue items that hold up a milestone; each row shows its source and can be edited or hidden; **+ Add an ask** adds Alan's own.
7. **This week and Next week,** side by side; promises first in Next week. A ✦ beside each heading asks Claude for a fresh fill from the week's tracker changes, with its sources, and Keep mine, Add the new lines or Use this.
8. **Decisions made this week,** written out: the decision, made by whom, on what date, and its source, all editable. No item IDs.
9. **Risks and issues:** top 5 by priority by default, each row with an eye to show or hide; "Showing 5 of 8".
10. **Overdue actions:** all by default, each with an eye.
11. **Current state:** the project's Current state, the same text as the cockpit's card, with its two panes side by side and their titles; when the second pane is empty the first takes the full width. Editing it here edits the project's Current state.
12. **Footer:** the page number on the right, nothing else.

**Editing.** Everything is editable in place with the one editor (rich in the Summary and Current state; plain in table cells). creaite drafts every section when the report is made. Inline AI: creaite's checks underline a claim it can't find in the week's facts, with the last recorded figure and a way to fix it; selecting words offers Shorten, Make it executive, Polish and Find the source, shown beside Alan's words. Every item ID and milestone opens the **standard work-item peek** (the same component as Work, not a copy), so a last-minute change to an item updates the report at once.

**Also decided (Alan, 14-10-2026):**
- **Headings are renamable,** remembered for the project, each with Reset to creaite's default.
- **✦ on Summary and Current state** as well as This week and Next week: a fresh draft in the executive voice from the week's facts, with its sources, and Keep mine or Use this (for Current state, using it updates the project's Current state, as editing does).
- **Source tags** on lines drawn from work items (This week, Next week, the Summary): click to open the item, hover for ✕ to remove one, Remove all tags beside the heading. Shown in creaite, never exported.
- **At a glance is a section** like the others, movable and hideable; each figure can be dragged to reorder or hidden. Default order: next milestone, overdue actions, high risks, decisions needed.
- **The milestone list:** an eye on each milestone picks which appear in the list, for a tidy report; the timeline always shows every milestone. Remembered with the layout.

**Per-project layout.** The section order, the renamed headings, the order of At a glance, hidden sections (hidden from a section's handle; a thin "Hidden" bar holds its place while editing), the milestone list, the logos shown and the row rules (for example "top 5 risks") are saved as the project's report layout, so next week's draft starts the same way. Each project can differ. Hiding a single row applies to that week only.

**Logos.** Set once per project in Settings › Projects › Report logos: a client logo and a partner logo (PNG, JPG or SVG). Every logo set for the project shows by default; clicking the logos on a report unticks any, and that becomes the project's layout. The firm's logo always comes first. The files live in the vault's local branding folder, which is kept out of git, so no real logo reaches the public repo.

**Approve and file** files the creaite report with the health change and the week's update in one apply, with Undo, as today's weekly report does. cx-weekly-report drafts into this view instead of a Word draft.

**Done when:** a week's report is drafted into the view, edited in place, approved and filed as a creaite report that reopens and re-edits; Word, PDF and HTML exports match the page's sections and order (a test compares them); hidden sections and rows never reach a filed report or an export; the layout is remembered per project; the timeline export starts near today; the peek is the standard one; search finds a report by a section's words; the client report can reuse the layout.

**Touches:** a new report view on the project's Reports tab (on the components), `report.py` (the data model, the creaite report file, the three exports), the weekly template, `docx_tools.py`, the cx-weekly-report skill, search, Settings › Projects (logos, layout), `paths.py` (the branding folder for logos), Help, tests.

### BL-336 — The client report, as a Client view of the week's report

**Plan (as imported):** **In v2.1.0 (Alan, 14-10-2026). Priority High: the Reporting category.** With BL-335; replaces cx-client-report's Word draft

Raised 2026-10-14 (Alan). **In v2.1.0, Priority High (Alan, 14-10-2026): the Reporting category, with BL-335 and BL-337.** Mockup: a private artifact (Alan's claude.ai, "Client report"), not committed. Replaces cx-client-report's Word draft; depends on BL-335 and v2.0.0's one editor. No schema change expected: the client layout is a per-client setting and the report is a filed creaite report.

**Decided (Alan, 14-10-2026):**
1. **The same week's report in a Client view,** not a separate document. Each client of a project has its own Client view and remembered layout: section order, hidden sections, renamed headings, logos, the milestone list and row choices.
2. **Every feature of the internal report:** move and hide sections, renamable headings, ✦ drafts (from client-safe facts only), eyes on rows, zoom, the standard peek, the exports.
3. **Health may differ from the internal health.** Clicking the client flag changes it and asks for a reason; **Match internal health** takes the internal flag and headline. The internal report shows the difference and the reason; the internal health and the cockpit never change.
4. **What it contains:** client-visible milestones, risks, issues and decisions, in their client wording (milestones in the client's words: On plan, At risk, Expected later, Late, Achieved); asks only where the client is asked; overdue actions the client owns by default, the others greyed with an eye to show them. Showing a risk that isn't client-visible opens the peek to make it client-visible, with its wording. A Sensitive item can never be shown; partner-only items never appear.
5. **A separate client summary,** drafted by creaite from the client-safe facts only. Summary and Current state are edited for the client; the internal text and the cockpit's Current state never change.
6. **Match internal** on each section copies the internal section in, then Alan edits from there (labelled Matching internal or Edited for the client); **Match internal for every section** does them all, keeping the client-only choices. No lasting link back to the internal text.
7. **Logos:** the firm, the client and the partner by default; untick any for this client.
8. **Check before export:** a list of what's left out and why (items not client-visible, Sensitive items, hidden sections, internal notes and source tags, any logo unticked, the health difference). Exports: HTML, Word or PDF; filed as a creaite report beside the internal one.
9. **Baseline:** the Client view can be drafted and edited at any time, but approved or exported only after that week's internal report is approved; its facts (items, dates, milestones, figures) then lock to the approved internal week, and a later tracker change doesn't alter it. A fortnightly or monthly client uses the latest approved internal week, and the report says which.
10. **Rhythm:** each client's rhythm (weekly, fortnightly, monthly) as today; creaite drafts the client report with the internal one, for each client due that week.
11. **Client At a glance** (default): next milestone, what we need from the client, points to watch.

**Done when:** a client report is drafted with the internal one, edited in its own view, checked and exported in all three formats; nothing not client-visible or Sensitive can reach it (a test); it can't be approved before the internal week; its health difference and reason show on the internal report; its layout and headings are remembered per client; Match internal copies one section or all.

**Touches:** the report view (BL-335), `report.py` (the client view's data, the check of what's left out, the lock to the approved week), the per-client layout settings, the cx-client-report skill, Help, tests.

### BL-337 — Reporting space and journey

**Plan (as imported):** **In v2.1.0 (Alan, 14-10-2026). Priority High: the Reporting category.** With BL-335 and BL-336

Raised 2026-10-14 (Alan). **In v2.1.0, Priority High (Alan, 14-10-2026): the Reporting category, with BL-335 and BL-336.** Mockup: a private artifact (Alan's claude.ai, "Reporting journey"), not committed. No schema change expected.

- **Project cockpit:** a **Reporting** card for the week: the internal weekly report and each client's report, with its state and rhythm; **Open** goes straight to a report, **Open reporting** to the space. It sits on today's cockpit; BL-317's tabbed project page (on hold) would host it later.
- **Reporting space, one per project:** weeks down the left, newest first, each with both reports' state; the week's internal and client reports as cards (state, thumbnail, who it's for, how the client version differs, Open, Approve, Export); **Edit both side by side**; the files filed for the week. A client not due that week shows Not due, with Make one anyway. The client card's Approve reads "Approve the internal report first" until it is.
- **The editor:** one page with three views, **Internal**, **Client** and **Side by side**, switched without leaving it. Side by side puts the internal page beside the client page, section beside section, with Scroll together; the internal page shows a small **≠ Client** marker on each section the client version changes (health included: "≠ Client: On track"), with both versions on hover; Match internal is on the client page. Markers are creaite only, never exported.
- **Reports page:** **Reports** in the left menu, with a count of what needs Alan; one row per active project for the week: health, the internal report's state and each client report's state; **Needs me** or **All projects**; earlier weeks one click back; **Open** goes to the project's reporting space. The Friday reminder on Today points here.
- **Other ways in:** ⌘K ("weekly report FAL"), ask creaite and Review reach the same space.

**Done when:** every way in reaches the same reporting space; the space shows each week's reports and their files; the three views switch without losing place; the Reports page lists every active project's week and what needs Alan.

**Touches:** the cockpit (a Reporting card), a reporting space view, the left menu (Reports), the Today reminder, ⌘K, Help, tests.

### BL-338 — The minutes editor, replacing today's minutes experience

**Plan (as imported):** **In v2.1.0 (Alan, 15-10-2026). Priority High: the Reporting category.** Replaces BL-59 and BL-60; on BL-335's editor

Raised 2026-10-15 (Alan). **In v2.1.0, Priority High (Alan, 15-10-2026): the Reporting category, with BL-335 to BL-337.** Mockup: a private artifact (Alan's claude.ai, "Minutes editor"), not committed because it uses the firm's real brand. **Replaces today's minutes experience** (cx-minutes' Word draft, edited in Word and reconciled at approval) and **BL-59 and BL-60**, which leave the backlog (their write-ups are in git history). Built on BL-335's report editor, so it reuses the A4 page, zoom, the one editor, the inline AI, the standard peek and the exports rather than building them twice. No schema change expected: the minutes are a filed creaite file and their items are the staged proposal.

**Decided (Alan, 14 and 15-10-2026):**
1. **After the transcript is processed,** cx-minutes drafts the minutes into the editor instead of a Word draft (the sections of `minutes-style.md`: header, executive summary, updates by topic with flags, decisions, risks, issues, assumptions and dependencies, action items, open questions and escalations, source). The source line names the meeting exactly: "Teams transcript and meeting chat, <meeting title>, <long date>, HH:MM–HH:MM (UAE time)".
2. **The page:** a true A4 page shown at 80% of the window's width, zoomable from 40% to 80% of the width (− +, trackpad pinch, ⌘+ ⌘− ⌘0), as on the reports; Show as exported; scrolling or clicking never moves the page back to the top.
3. **Everything is edited in place,** with the one editor. ✦ beside a heading redrafts that section from the transcript (Keep mine or Use this); selected words offer Shorten, Make it executive, Polish and Find the source; flags are chosen from a click on a line (the ten flags of `minutes-style.md`, used sparingly).
4. **The transcript beside the minutes:** a pane of speaker turns with times, searchable and closable. Every line drawn from the transcript has a **time tag**; clicking it scrolls the pane to what was said and highlights it; hover for ✕ to remove a tag. Tags are shown in creaite only, never exported.
5. **Checks against the transcript:** a claim, date, figure or owner the transcript doesn't support is underlined, with what was said and who said it, and Use that, Keep mine or Show in the transcript. A check left open is listed when approving.
6. **The proposed items are rows in the page,** not a second list: decisions, risks, issues, assumptions and dependencies, and actions are the staged items themselves, so editing a row edits the item and nothing needs reconciling. Each row shows what it does: New action, New risk, Records FAL-D-004 as made, Closes FAL-A-003 · Looks done (with the evidence), Looks like FAL-R-006 (BL-221), Sensitive. An owner the people register doesn't know is picked from the register in the row (BL-55), and the alias is remembered. Every ID opens the **full standard peek**, with **Sneak peek** (BL-322) to change the item in words.
7. **Looks like an existing item:** **Update that one** turns the new item into an update of the existing one and shows exactly what changes (latest update, due date; title, owner, priority and response unchanged; the earlier update kept in the history; the minutes added as a source). **Keep as new** leaves it a new item. Both are also in the full peek, with the meeting's quote and the changes shown before and after.
8. **Items are approved unless removed:** Alan doesn't tick each one. **✕ Remove** on a row removes the item and its line from the minutes (Keep the line in the minutes keeps the line only), with Undo.
9. **Deadlines:** clicking a deadline opens a calendar and quick picks (Friday, Next week, Next Wednesday, End of month, each with its date shown), and Alan can type words instead ("Friday", "next week", "next Wednesday", "end of month", "in 2 weeks", "30-10"). Words are worked out from the meeting's date (`minutes-style.md`), and the date is shown before it is set; "next week" is that week's Friday; "end of month" the last working day. Not set stays possible.
10. **Approve minutes** opens one popup (wider than today's, about 784px; Esc or a click outside closes it) that says what will be filed and lists the items in two groups: **Actions and updates**, approved together with one tick ("Approve all n as reviewed in the minutes", ticked by default); and **one tick each** for a new decision, a decision recorded or withdrawn, a new risk and an update that closes an item, as the bulk rule requires. Whatever is ticked is applied **with the minutes, in one apply with Undo, and doesn't go to Review again**; anything left unticked waits in Review. The minutes are always approved on their own, as now. Approved minutes reopen with **Edit again**, which makes a new version and keeps the earlier one.
11. **Agenda coverage** (BL-209's Coverage, moved here): where the meeting had an agenda or a prep page, a section shown in creaite only lists each point as Covered, Touched on or Not discussed. **Deal with it…** on a point that wasn't covered offers: **Carry it to the next meeting of the series** (on its draft agenda and Prep, marked "carried from <date>"); **Set up a separate session** (adds an action for Alan, due Friday by default, to set it up; creaite never creates the invite, since Microsoft 365 actions stay off); or **No longer needed** / **Covered enough**. With "Add a line to the minutes" (on by default) it writes a line under **Not covered in this meeting** ("Training plan was not discussed; it is carried to the next steering committee on 27 October 2026"). Undo on each.
12. **Milestones are never changed from minutes** (BL-186): a milestone the meeting moved gets a note in creaite only, and **Review the Go-live milestone** opens it in the peek with the change filled in (expected date, state, the reason from the transcript, an optional rebaseline), proposed on its own to Review.
13. **One version, or internal and distributed (Alan, 15-10-2026: minimise the work when one is enough).** One version by default. **Internal + distributed** turns on a distributed version for attendees or the client, remembered for the meeting series. It works like BL-336's Client view: Internal, Distributed and Side by side views; a line can be marked **Internal only**; a Sensitive item never reaches it; ≠ Distributed markers on the internal page with both versions on hover; Match internal per section; a check of what's left out before export; its facts lock to the approved internal minutes. Side by side keeps matching sections and topics the same height, so their headings stay level as both pages scroll together.
14. **Saved in creaite's own format** as Alan goes (a version shown in the bar), filed on approval in the project's minutes folder as `YYYY-MM-DD <Meeting title>` in creaite's format (the page and its data in one file, as BL-335's reports), with the transcript in Transcripts. Reopening it brings back every option: versions, the transcript pane, time tags, checks, coverage and the item rows. Search reads it.
15. **Export for distribution:** HTML, Word (the firm's minutes template, `minutes-template.docx`) or PDF, all ticked by default; **File the exports beside the minutes** is on by default; each export opens in the default viewer as soon as it's made. Nothing is ever sent.
16. **Feeds the weekly report:** the approved minutes' decisions and updates feed BL-335's "Decisions made this week" and "This week".

**Done when:** a processed transcript opens as draft minutes in the editor with the transcript pane and time tags; edits to a row change its staged item; Remove, Update that one and the owner picker work with Undo; a deadline typed in words sets the right date from the meeting's date; Approve applies the minutes and the ticked items in one apply and sends nothing else to Review; agenda coverage can carry a point, add the action or note it; the distributed version never contains an Internal only line or a Sensitive item (a test); the minutes reopen from creaite's format with every option; HTML, Word and PDF exports match the page and open in the default viewer; scrolling side by side keeps headings level; the page never jumps to the top.

**Touches:** a minutes view on BL-335's editor; `minutes.py` (the minutes record, stage, the source positions for time tags, coverage carry and actions); cx-minutes (draft into the editor, no Word draft); cx-review and `review.py` (approving minutes and their items in one apply); `docx_tools.py` (Word from the record); `report.py` (the shared creaite file, HTML and PDF); `live_server.py` (save, the transcript, opening an export); `paths.py`; `minutes-style.md`; `creaite-rules.md` (the cx-minutes row, the Word draft); Help; tests.

### BL-339 — Retire the meeting hub

**Plan (as imported):** **In v2.1.0 (Alan, 15-10-2026). Priority High (Alan, 15-10-2026), like its siblings**, with BL-338. Ready (Alan, 15-10-2026: "this release is ready")

Raised 2026-10-15 (Alan). **In v2.1.0 (Alan, 15-10-2026)**, with BL-338. Alan: the page is too complex and not needed now. No schema change.

- **Remove** BL-209's page for each meeting (`#meeting=<token>`, its strip of steps and its next-step button, FR-167) and its "Meeting page" links from Today, the Week ahead, Intake, the Prep brief, Files, an item's source and Review.
- **Where the links go instead:** before a meeting, its Prep popup; after it, its minutes in BL-338's editor (the draft or the filed minutes). An old `#meeting=` link opens the same place.
- **Coverage and Carry to the next agenda** move into BL-338's Agenda coverage; carried points still appear on the series' next prep page under "Not covered last time".
- **Done when:** no screen links to a meeting page; old links land on Prep or the minutes; coverage and carry work from the minutes; the BRD retires FR-167 and moves its coverage part to BL-338's requirement.
- **Touches:** `meetings.js` (`hubLink` and the page), Today, the Week ahead, Intake, Prep, Files, Review, `build_dashboard.py`, cx-minutes (the coverage step's wording), Help, tests.

### BL-340 — Notes transcripts in the minutes editor

**Plan (as imported):** **Not scheduled. Priority Low (Alan, 15-10-2026):** to look at after BL-338

Raised 2026-10-15 (Alan). **Not scheduled, Priority Low (Alan, 15-10-2026).** To look at after BL-338: how a transcript of Alan's own notes (a dictated or recorded note, beside v2.0.0's Notes and BL-54's quick notes) is drafted, edited and approved with BL-338's editor, and what differs from a meeting's minutes (no attendees or agenda, one speaker, perhaps no Word export). Design first; nothing decided yet.
