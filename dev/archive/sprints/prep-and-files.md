# Sprint prep-files: the meeting prep page, the Week ahead and the Files view (BL-126, BL-127, BL-135)

Branch `sprint-prep-files`, worktree `../creaite-prep-files`, made from the tip of `main`. Three small items that touch different parts of the product from the three sprints in flight (`sprint-polish`: Work, Review, Calendar Import, Current state and ask creaite; `sprint-settings`: the Settings view; `sprint-work-views`: the Work page, planned). It can run beside all of them and merges whenever its tests pass, after bringing `main` in. Rough size: three to five days.

Before starting, run `git worktree list` and `git status` in the worktree. Read BL-126, BL-127 and BL-135 in `dev/BACKLOG.md` first; they hold Alan's decisions. BL-98 (the Prep page), BL-113 (decisions in prep) and BL-87 (the Files page) are already built; read `prep_page.py`, `build_dashboard.week_ahead` and `paths.project_files` before changing them.

## Items

Commit each separately, in this order. The first two are independent; the third has the one small change to `paths.py`.

### 1. BL-127: the Week ahead drops the weekly and client report lines (S)

- In `build_dashboard.week_ahead` remove the two places that add `kind: "report"` lines: the weekly report line on the report day, and the client report line on the day the rhythm makes one due. Nothing else in the function changes (milestones, work items, meetings, the undated Urgent lead-in, "further ahead").
- The reminders in Today › Needs attention come from `build_dashboard.reminders` and are **not touched**: same wording, Draft button, dismiss and dismiss forever.
- If the dashboard's `weekHtml()` has code that only renders `report` lines, remove it too; if anything else produces `kind: "report"` (search the template and the builder), leave that alone and say so in BUILD.
- **Tests (in `test_today_brief.py` or beside it):** a Friday with an unfiled weekly report, and a project whose client report falls due in the window, have no report line in `D.week` and still have their reminders; filed or absent reports are unchanged; milestones, work items and meetings are as before. Update any existing Today test that expects a report line.
- Help and `dev/dashboard-spec.md`: the Week ahead description, if it names reports.

### 2. BL-126: the meeting prep page and popup (S–M)

All in `prep_page.py`, the prep data in `build_dashboard.py`, and the Prep popup (`drawPrep`) in `dashboard.html`.

**a. Only urgent, due and overdue work on the page.**
- `prep_page.context` lists an item only if it is **Urgent** priority, **overdue**, or **due within the "due soon" setting** (`review.due_soon_days`, 7 by default; the dashboard's `soon()` uses the same). Order: overdue (oldest first), then due soonest, then Urgent with no date. Decisions: a *Decision needed* when due soon or overdue; a *Decision to revisit* when its revisit date has come (BL-113). `MAX_ITEMS` stays as the cap.
- The invite ranking (`rank`) no longer decides what is listed. Claude is given only the listed items; its "why it matters" lines still appear on those. The researched notes and questions are unchanged.
- Under the table, one line: "n other open items are not listed", linking to Work filtered to the project (the same dashboard address the item links use). With nothing urgent or due, the page says so plainly instead of an empty table.

**b. "Latest from the project reporting" reads easily.** In `render` replace the flattened paragraphs with, per project:
- a small heading with the **health word and icon** (never colour alone) and "as of DD-MM-YYYY";
- the Current state's **headline** on its own line, then its **key points as a short bulleted list, the first five**, keeping the bold lead-ins; the weekly update as one or two short lines;
- the rest of the Current state behind a closed **"Show the full current state"** disclosure;
- a comfortable size and line length (about 70 characters), real spacing, never more than a few lines in a row. The Markdown structure (headline, bullets, bold) is kept, not flattened (replace `plain_paras` with a small renderer that handles only paragraphs, bullets, numbered lists and bold; everything is escaped). A Portfolio meeting gets one compact block per project: health and headline, the points behind the disclosure.
- The page stays one self-contained file: no external scripts, fonts or images, and it keeps its print style.

**c. Links to the recent reports, on the page and in the popup.**
- Which: the project's most recent **weekly report, client report and steering one-pager**, up to three in all per project, newest first, each as kind, date and file name. Ad hoc documents are left out. A Portfolio meeting shows the latest of each per project. Build the list once in `build_dashboard.py`'s prep data (`reports` per project, from `paths.project_files`; files only if they exist and are readable; an online-only OneDrive file is shown as unavailable, not linked), and use it for both the popup and the page. Mark a client report as such.
- Popup: a **Recent reports** section (the popup has no reporting section today). Each row opens the file with the same call the Files page uses (`/api/open`).
- **The page cannot call `/api/open`** (it is a POST with the session token, and the page is a saved file). So on the page a report link goes to a new dashboard address, `http://127.0.0.1:<port>/#openfile=<projects/… path>`, which the dashboard handles on load by calling `/api/open` once and then clearing the address. It accepts only paths that pass the same check as `/api/open` (`OPEN_OK`, no `..`, must exist); anything else shows "Can't open that file". If the live server isn't running, the link does nothing, as the page's other links; the page says so in its footer.
- Update `.claude/skills/cx-prep/SKILL.md` (the page no longer lists every ranked item; it lists urgent and due ones) and the research prompt to match.

**Tests (extend the existing prep tests: `test_decisions_prep.py`, `test_today_brief.py`, and a new `test_prep_page_content.py` if neither fits):** only urgent, overdue and due-soon items are listed, in the stated order, and the "n not listed" line is right; an undated non-urgent item is left out; the reporting block shows the headline, at most five points and a closed disclosure; health appears as a word; up to three report links, newest first, none for a missing file; the page is still one self-contained file; the popup lists the same reports; `#openfile=` opens an allowed path once, refuses `..` and a path outside the vault, and clears the address.

### 3. BL-135: an Agendas folder in the Files view (S)

- `paths.project_files` returns files in the project's agendas folder (`paths.folder(code, "agendas")`; `locations.folders.agendas`, `02 Meetings/Agendas` with an outside projects root, `agendas/` in the default layout) as their own kind, **`agendas`**, and keeps them out of the documents walk, so nothing is listed twice. The folder is listed **whether or not "Show project documents" is on**. Subfolders are walked one level, as Reports' are. Never-indexed folders and online-only files behave as for the other folders.
- `build_dashboard.files` passes the kind through; the Files tree in `dashboard.html` (`renderFiles`) shows **Agendas** at the same level as Minutes and Transcripts, with its own count, and the folder filter and the "All files" and project counts include it. Latest reports and This week's meetings are unchanged. Files in it open as everywhere in Files (a prep page in the browser, others in their own app).
- Search and ask creaite keep reading agendas as they read documents now (passive, never extracted, internal; the result still says "Document · internal"). Check that moving them out of the documents walk doesn't change what the search index covers: `search.py` must still index them.
- Portfolio gets no Agendas folder.
- `system/creaite-rules.md` (folder map and the Project documents section, which says agendas are included in documents) is updated to say Files lists Agendas as its own folder, still passive. This is an engine file: add a line to the release notes (below).
- **Tests:** agendas are listed with the Documents switch off; counted once; both the default layout and an outside projects root work; a prep page and a Word agenda both appear; nothing under Documents repeats them; search still finds an agenda.

## Boundaries

- **Owns:**
  - `prep_page.py`, the prep part of `build_dashboard.py` (the prep data, `week_ahead`, `files`), `paths.project_files`;
  - in `dashboard.html`: the Prep popup (`openPrep`, `drawPrep`, `prepInvite`, `prepPageBar` and the Recent reports section), the Files view (`renderFiles` and its tree), the Today Week ahead renderer (`weekHtml`) and the `#openfile=` address handler;
  - the cx-prep skill; the prep, Week ahead and Files parts of `help.md`; `system/creaite-rules.md`'s folder map and Project documents lines for agendas.
- **Don't edit** the Work, Review, Calendar Import, Current state, ask creaite or Settings parts of `dashboard.html`, `tracker.py`, `propose.py`, `permissions.py`, `sweep.py`, `review.py`, `live_server.py` (the existing `/api/open` is reused as it is) or the schema. No schema change.
- **Shared files** (`dashboard.html`, `help.md`, `dev/dashboard-spec.md`, `build_dashboard.py`, `creaite-rules.md`): put new code in marked sections (`/* ===== BL-126 (sprint-prep-files) ===== */`, and so on) and don't reformat unrelated lines, so the merges with `sprint-polish`, `sprint-settings` and `sprint-work-views` stay readable. Regenerate the guides after Help changes (`python3 dev/tools/build_guides.py`) rather than merging them by hand.
- **Engine changes ship in a release:** all three items change scripts or rules. Add a line each to the release notes for the next version (use the 1.3.0 file `sprint-polish` creates, or create `dev/release-notes/1.3.0.md`; don't change `VERSION`).
- **Don't touch `dev/BACKLOG.md` or `dev/BRD.md`;** they are updated at merge. Write the FR text you'd add in BUILD: BL-126 extends FR-70 (meeting prep and the Prep page), BL-127 extends FR-81 (Today as a brief, with its Week ahead), BL-135 extends FR-92 (the Files page) and FR-29.
- **Colour is never the only cue** (health on the page, a client report mark); check each in all themes and in light and dark. The page is drawn on white whichever theme is on.
- **Tests start from your own settings:** run them in the worktree, which has the committed `settings.json`, not the main folder's.
- **Stop a test run by its process tree,** never with `pkill` by name.
- **Development guard:** sample data only; test with temporary vaults and fictional meetings. Never connect to Microsoft 365 for real data.

## Done when

- **Tests:** as listed per item; the existing Today, prep, Files and onedrive-projects tests pass or are updated for the new behaviour.
- **The full suite passes once** on the final branch: `python3 dev/tools/run_tests.py -j 4`.
- **Alan checks by hand, once:** make a prep page for a real project's meeting and read it (the work table, the reporting block, the report links opening); look at Files with Documents off; look at Today on a Friday.
- **Docs:** `dev/dashboard-spec.md`, Help and the guides, a "Sprint prep-files" section in `dev/BUILD.md`, and the release-notes lines.
- **Commits:** each item committed separately on `sprint-prep-files`, with the attribution lines from the session's instructions. Never push or merge into `main`.

## Hand-offs

(Changes needed in files another sprint owns.)
