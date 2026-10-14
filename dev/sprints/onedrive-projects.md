# Sprint: Project folders in OneDrive (BL-85)

Branch `sprint-onedrive-projects`, worktree `../creaite-onedrive`. Nothing else is running. Read BL-85 in `dev/BACKLOG.md` first; it holds Alan's decisions.

## Goal

creaite's engine and record stay on the laptop. Alan's engagement folders stay in the company OneDrive, where they live today, in his own folder template. creaite reads from them and files into them, so each engagement is one folder, creaite's files included.

## Decisions (Alan, 2026-10-08)

1. **Approval:** project files (minutes, transcripts, reports, project memory and the cross-project portfolio files) may live in the company OneDrive. **The database, staging, backups, history, search index, git and the engine never live in a synced folder.** Never personal cloud storage.
2. **One folder template for every engagement**, described below.
3. **`_portfolio` lives in OneDrive too**, beside the engagements.
4. **The daily database backup is also copied into OneDrive**, as a closed copy, never the live file.
5. **One machine only:** no multi-machine lock is needed.

## Alan's engagement template (consistent across all projects)

**Location:** `~/Library/CloudStorage/OneDrive-<tenant>/Documents/Engagements/<Engagement name>/`.

**The template folders:**
- `00 Admin` · `01 Inputs` · `03 Delivery` · `05 Governance` · `06 Closure` · `07 Growth`: these have subfolders, such as `Contract`, `Research`, `Design`, `RAID`, `Decisions` and `Change Requests`.
- `02 Meetings/Transcripts`, `02 Meetings/Minutes`, `02 Meetings/Agendas`.
- `04 Reporting/Weekly`, `04 Reporting/Steerco`, `04 Reporting/Adhoc`, `04 Reporting/Milestones`.
  - **Decided 2026-10-08:** client reports go in `Weekly` (with the weekly reports); `Steerco` is separate and creaite doesn't write to it; current-state images go in **`04 Reporting/Content`**, which isn't in the skeleton: create it on first use, and don't fail if it is missing.
- `zz Archive`.

**New engagements** start from `Engagements/_Templates/_Skeleton`.

**Folder names** are the engagement's name, with no project code.

**Transcripts keep Teams' own names:**
- `<Title>-YYYYMMDD_HHMMSS-Meeting Transcript.docx`;
- `<Title>-YYYYMMDD.docx`;
- sometimes a name with no date.

Mostly `.docx`, with some `.pptx`, `.pdf` and `.xlsx`.

**Never copy a real engagement name, file name or content into this repo:** it is pushed to GitHub. Tests build this template in temporary folders with fictional names (FAL, ORX and so on).

## Design

**The vault stays local** (`~/creaite`). A new setting, `locations`, points creaite at the projects root and describes the template:

```json
"locations": {
  "projects_root": "~/Library/CloudStorage/OneDrive-G42/Documents/Engagements",
  "portfolio": "_Portfolio",
  "skeleton": "_Templates/_Skeleton",
  "folders": {
    "transcripts": "02 Meetings/Transcripts",
    "minutes": "02 Meetings/Minutes",
    "weekly_reports": "04 Reporting/Weekly",
    "client_reports": "04 Reporting/Weekly",
    "adhoc_documents": "04 Reporting/Adhoc",
    "images": "04 Reporting/Content"
  },
  "never_index": ["zz Archive", "_Templates"],
  "offsite_backup": "_Portfolio/creaite backups"
}
```

**How the setting works:**
- **Default:** when `locations` is absent or `projects_root` is empty, everything works exactly as today: the vault's own `projects/`, with the `minutes/`, `transcripts/`, `documents/` and `reports/` subfolders. **This repo and the tests keep the default.**
- **`projects_root`** is stored with `~` (home-relative) and never as an absolute path, so a new laptop with the same OneDrive works.
- **Folder paths** are relative to each engagement folder.
- **Documents** are everything in the engagement folder outside the mapped meeting and report folders and `never_index`. They are indexed and cited, and never extracted, as now.
- **Agendas** (`02 Meetings/Agendas`) count as documents.

## Items

Commit each separately.

### 1. One place for every project path (`paths.py`)

**New functions in `paths.py`,** which every script uses instead of hard-coded folder names:
- `projects_root()`;
- `portfolio_dir()`;
- `project_dir(code)`;
- `folder(code, kind)`;
- `extract_dirs(code)`;
- `document_roots(code)`;
- `rel_project(path)` and `resolve_project(rel)`.

**Where they're used:** replace the roughly 60 hard-coded `minutes`, `transcripts`, `reports` and `documents` uses in:
- `tracker.py`, `minutes.py`, `report.py`, `review.py`, `search.py`, `build_dashboard.py`, `live_server.py`, `doctor.py`, `session.py`, `propose.py`;
- the dashboard's Files view;
- the cx-minutes, cx-weekly-report, cx-client-report and cx-document skills;
- `tracker-conventions.md`.

**Paths stored in the database and proposals:**
- **Sources** are stored as `projects/<engagement folder>/<path inside it>`. `projects/` is a logical prefix that `resolve_project` maps to `projects_root`. Existing rows keep working, and moving the root later is one setting change.
- **Proposals' file operations** use the same logical paths.
- **The live server's allow list** (`FS_RULES`) resolves them too, and allows the mapped folders only.

**Safety:** `safe_path` refuses anything that resolves outside the vault or the projects root.

### 2. The register maps codes to existing folders

- The register's "Folder under projects/" column holds the engagement folder name ("Falcon Data Platform", for example), with no code required.
- `project_dir` reads it.
- `add project` (cx-edit and `propose.py`) copies `skeleton` to create the folder when the root is OneDrive. Otherwise it creates the default subfolders, as now.

### 3. Reading Teams file names

**The meeting date** comes from:
- `YYYY-MM-DD Title` (creaite's own);
- `Title-YYYYMMDD[_HHMMSS][UTC]-Meeting Transcript|Recording`;
- `Title-YYYYMMDD`;
- failing those, the file's date. A dateless name is flagged in Review.

**Implementation:** in `minutes.py` (`meeting_key`, `stem`), `tracker.py` (`cmd_index`), `build_dashboard.py` (Files, Intake) and `search.py`.

**What creaite writes:** files it files keep creaite's `YYYY-MM-DD Title` form. Alan's own files are never renamed.

### 4. Settings, install and setup

- **`settings-defaults.json`:** gets the `locations` block with an empty `projects_root`.
- **`new-vault`:** still refuses a synced *vault* folder. After creating the vault, it may ask for an optional projects folder, and it accepts a company OneDrive (`Library/CloudStorage/OneDrive-*`) there.
- **cx-setup's first-install path** gets a "Projects folder" step. It asks first, then:
  1. points `projects_root` at the folder Alan names;
  2. checks it's reachable and is a company tenant (`OneDrive-<name>`, not `OneDrive-Personal`), warning otherwise;
  3. detects the template from `_Templates/_Skeleton`, or from the first engagement, and proposes the `folders` mapping, shown to Alan before it's saved;
  4. lists the engagement folders so each can be added as a project (code, name, matching signals);
  5. creates `_Portfolio` (`PORTFOLIO.md`, the registers, cross-project minutes and transcripts) if missing;
  6. tells Alan to set Engagements to **"Always keep on this device"** in Finder (OneDrive), so nothing is online-only.
- **Existing meetings:** setup asks once, per project, whether to **mark existing transcripts and minutes as already processed** (written to `processed.txt` without extracting) or to **process the last N weeks**. Never all of them silently.

### 5. Off-laptop backup copy

- After the daily backup (`session.py` and `tracker.py`), creaite copies the newest `system/backups/tracker-YYYY-MM-DD.db` into `offsite_backup` (`_Portfolio/creaite backups/`). The copy is written to a temporary name, then renamed, so OneDrive never syncs a half-written file.
- It keeps the latest 14 copies there. The local backups are never pruned, as now.
- `doctor.py` reports the last copy's date.

### 6. Doctor and online-only files

**`doctor.py` checks:**
- the projects root is reachable;
- the mapped folders exist for each registered project;
- the vault itself isn't synced;
- **online-only files**: a file in a meeting folder that is a OneDrive placeholder (on macOS, a dataless file: check `st_flags & SF_DATALESS`, or size 0 with blocks 0). These are warnings, with the fix.

**Indexing and extraction:** online-only files are skipped and listed. Reading them is never forced to trigger mass downloads.

### 7. Rules and docs

- **`system/creaite-rules.md`:**
  - the "Local only" non-negotiable becomes the decision above;
  - the folder map gains `locations`;
  - Project documents describes the mapped folders;
  - Portability notes OneDrive.
- **Also update:** `dev/SETUP.md` (first install with a OneDrive projects folder), Help, and `dev/dashboard-spec.md` (Files).
- **The development guard is unchanged:** this repo keeps local sample projects.

## Boundaries

- **May touch any file;** nothing else is running.
- **Development guard:**
  - sample data only;
  - tests use temporary folders that copy the template's **folder names** with fictional engagements;
  - never read or write Alan's real OneDrive from tests or tools;
  - the one exception is Alan running setup in his live vault after release.
- **Docs:** leave `BACKLOG.md` and `BRD.md` alone; they are updated at merge.

## Done when

**Tests:**
- **Default layout unchanged:** the whole existing suite passes untouched.
- **A temporary OneDrive-style root,** with the template, two fictional engagements and Teams-named transcripts:
  - project paths resolve to the mapped folders;
  - extraction reads only Transcripts and Minutes;
  - documents index the rest except `zz Archive`;
  - minutes and reports are filed into the mapped folders with creaite names;
  - sources resolve after moving the root;
  - dates are read from Teams names;
  - `add project` copies the skeleton;
  - the "mark existing as processed" baseline;
  - the off-laptop backup copy (atomic, keeps 14);
  - doctor's checks, including a simulated online-only file;
  - `safe_path` refuses paths outside the vault and the root;
  - `new-vault` still refuses a synced vault but accepts a OneDrive projects root.
- The full suite passes: `python3 dev/tools/run_tests.py`.

**Docs:** a short "Project folders in OneDrive" section in `dev/BUILD.md`.

**Commits:** each item committed separately on `sprint-onedrive-projects`, with the attribution lines from the session's instructions. Never push or merge.

**Then, for Alan:** after merge, a v1.1.0 release. In his live vault, he says "update creaite", then "setup" for the projects-folder step.

## Hand-offs

(None expected.)
