# Sprint: Dashboard pages (BL-87, BL-88, BL-89, BL-95, BL-91, BL-90 part 1)

**Status (09-10-2026): merged into `main` (`5fd2ca2`, 09:54).** One commit on the branch (`258b086`, a test change) is not in `main`. See `STATUS.md`.

Branch `sprint-pages`, worktree `../creaite-pages`. Runs in parallel with `sprint-permissions` (`../creaite-permissions`) and `sprint-sweep-alerts` (`../creaite-sweep`). **This sprint merges last.** Read BL-87, BL-88, BL-89, BL-95, BL-91 and BL-90 in `dev/BACKLOG.md` first. They hold Alan's decisions; follow them, and where one says "to confirm", take its stated default.

## Goal

The Files page shows the real report folders and is fresh when you look. The project page gets a roomier Current state, undated work that can't hide, trends and flow, and dependencies. **There are no schema changes.**

## Items

Commit each separately, in this order.

### 1. BL-87: Files page, the real report folders (M)

- **What changes:** Steerco and the other report folders show by their real names, documents are set aside (not listed by default), and report sub-labels appear.
- **Fresh on view:** a files-only entry point, and a live-server `/api/files` route, so the list is current when the page opens.
- **Where:** `files()` in `build_dashboard.py`, plus `paths.py` (a `steerco_reports` folder and a way to skip documents). Respect the BL-85 `locations` layout and the default layout alike.

### 2. BL-88: Files search, a centred bar with an Ask button (S)

- **The new bar:** a centred search bar with an Ask creaite button beside it, and the hint line.
- **Removed:** the `vsAskRow` result row.
- **Updated:** the ⌘K row's wording, and FR-75's text at merge.

### 3. BL-89: Current state in two resizable panes (M)

- **The panes:** the Current state card's reading and editing views split into two resizable panes, as one message.
- **Where:** the divider, `startCurEdit`, `saveCurEdit`, `htmlToMd` and `mdHtml`, styled in every theme.
- **Reports:** `report.py` (`current_state`, `replace_current`) and the Word fill handle the pane marker, so reports still read as one piece.

### 4. BL-95: Undated open work always shows on the project page (S)

- **The project page:** a card in `renderCockpit`, plus the evidence row.
- **Projects table:** undated counts, from `build_dashboard.py`.
- **Settings:** a grace-days setting.
- **Docs:** FR-11 extended at merge.

### 5. BL-91: Trends and flow (M)

- **The measures:** in `build_dashboard.py`, with a daily snapshot.
- **Display:** a Flow card drawn as inline SVG, at scale, with theme-token colours.
- **Weekly report:** gets a line about flow.
- **Settings:** the period.
- **Tests:** fixed sample data with known opened and closed counts.

### 6. BL-90 part 1: Dependencies, no schema change (M)

- **What it uses:** what already exists. A milestone link on an item already means "this milestone depends on this".
- **What it adds:**
  - the date warning;
  - a Dependencies card;
  - suggesting a milestone;
  - the panel's suggestion chips and a Work filter.
- **Out of scope:** part 2 (the `links` table) waits for wave 5 with BL-50, so don't touch `schema.sql`.

## Boundaries

- **Owns:**
  - the Files page and `files()`;
  - the project page (`renderCockpit` and its cards);
  - the Current state editor;
  - `report.py`'s current-state handling;
  - the trends and flow code;
  - the dependency warnings and cards.
- **Don't edit:**
  - **`sprint-permissions` owns:** `permissions.py`, `FS_RULES` and the allow lists in `live_server.py`, `.claude/settings.json`, the Ask creaite chat box, and the launcher.
  - **`sprint-sweep-alerts` owns:** `sweep.py`, the cx-sweep skill, `calendar.json`, meeting prep and VIPs.

  Your `/api/files` route goes **at the end of the route map**, in a marked block. Note anything needed under "Hand-offs".
- **Shared files** (`dashboard.html`, `build_dashboard.py`, `live_server.py`, `paths.py`, `report.py`, `settings.json`, `help.md`, `dev/dashboard-spec.md`):
  - put new code in its own marked section, `/* ===== Dashboard pages (BL-87 to BL-95) ===== */`;
  - add new data keys at the end of `collect()`'s dict;
  - don't reformat unrelated lines;
  - leave `BACKLOG.md` and `BRD.md` alone (updated at merge).
- **Help:** update `help.md`, then run `python3 dev/tools/build_guides.py`.
- **Development guard:** sample data only. Test both the default layout and a temporary OneDrive-style projects root.

## Done when

**Tests:**
- Files shows the real report folders, documents set aside, and refreshes on view, in both layouts;
- the search bar and its Ask button in every theme;
- Current state's panes round-trip to `CLAUDE.md` and the Word report as one piece;
- the undated-work card and grace days;
- the flow measures on fixed data, with the SVG drawn to scale;
- the dependency date warning, card, suggestion and filter;
- headless Chrome checks of each page in light and dark.

The full suite passes: `python3 dev/tools/run_tests.py`.

**Docs:** the spec updated, and a short "Dashboard pages" section in `dev/BUILD.md`.

**Commits:** each item committed separately on `sprint-pages`, with the attribution lines from the session's instructions. Never push or merge.

## Hand-offs

(Changes needed in files another sprint owns.)

**Things to know at merge**
- **`live_server.py`:** `/api/files` is a **GET** (read-only, token), in a marked block just above the final 404 of `do_GET`, not in the POST route map; no other route changed.
- **Shared data and settings:** `collect()` gains `flow` at the end of its dict; each project gains `undated`; `ui_settings` gains `filesDocs`, `undatedGrace` and `flowWeeks`. `settings-defaults.json` (and this repo's `settings.json`) gain `dashboard.files_show_documents`, `dashboard.undated_grace_days`, `dashboard.flow_weeks`, `locations.folders.steerco_reports` and `warnings.dependency`. An update adds them to existing vaults.
- **`help.md` and the guides:** Files, Search, Project page (two panes, No due date, Flow, Dependencies) and Early warnings changed; `build_guides.py` has been run. Expect a conflict with other sprints' `help.md` edits; the guides are generated, so rebuild them after resolving.
- **Tests I changed because behaviour changed on purpose:** `test_dashboard.py` and `test_onedrive_projects.py` (documents set aside; Steerco is a report folder), `test_dashboard_editing.py` (the palette's file query), `test_search_dashboard.py` (the Ask button replaces the Ask row; "Ask creaite" in ⌘K).
- **For the BRD at merge:** FR-75 (the search answer is called Ask creaite; the button), FR-11 (undated work on the project page), FR-15 (trends and flow), FR-54 and FR-63 (two panes, one message), the Files requirement (report folders, documents set aside, fresh on view).

**For `sprint-sweep-alerts`:** BL-90 says blockers should appear in meeting prep. This sprint doesn't touch meeting prep. The data is there: `D.warnings` entries with `sig: "dependency"` (and `ms`), and `R` items of type Dependency with `ms`. Add a "blocked by" line to the prep brief if wanted.

**For `sprint-permissions`:** nothing needed. This sprint adds no tool, allow-list rule or permission.

**Not built (outside part 1):** BL-90 part 2 (the `links` table, attaching to actions, RAID items and other projects' items, suggestions from cx-minutes, cx-sweep and cx-edit) and the steering one-pager's use of flow and blockers (BL-92). A portfolio view of flow comes with BL-02.
