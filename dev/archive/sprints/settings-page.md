# Sprint settings: the Settings page, one page with categories and search (BL-115)

Branch `sprint-settings`, worktree `../creaite-settings`, from `main` after v1.2.0. It runs alongside `sprint-polish` (`polish.md`), which **merges first**. Read BL-115 in `dev/BACKLOG.md` first; it holds Alan's decisions (option B), the categories, the behaviour and the tests. Where it says "to confirm", take its stated default and note it in BUILD.

## Items

Commit each separately, in this order.

### 1. Show Alan the plan (no code)

Walk the current Preferences and Data admin tabs, and list every setting the page shows today. Then show Alan:
- **The categories:** each setting placed in one of BL-115's six categories, with the section it sits in;
- **Advanced:** the file-only settings proposed for it;
- **Old addresses:** how each old `STAB` value and link maps to a new address (`prefs`, `admin`, `people`, `projects`, the status line's Diagnostics link, Help's links).

Build only after Alan agrees.

### 2. One list of sections (M)

**The list:** `SETSECTIONS` replaces `renderSettings` and its four wrappers (early warnings, ignore rules, VIPs, Diagnostics). Each entry has an id, a category, a title, search keywords and a render function.

**Layout:** the category list on the left, the settings on the right, and Stop the live server at the bottom of System.

**Keep exactly as now:**
- each setting's key in `settings.json`;
- how it saves: the backup, the log entry and the live server's checks;
- the People, Workstreams, Projects and Diagnostics managers. They move, they don't change.

**Add:** a quiet "Saved" beside a row when it saves.

### 3. Addresses, search and narrow windows (S–M)

- **Addresses:**
  - `#settings/<category>` opens that category;
  - the old addresses and `STAB` values open the category agreed in item 1;
  - the status line's Diagnostics link and Help's links open the right place.
- **Search:** filters sections and rows by label, help text and keywords. It jumps to the match, and with no match it says so.
- **Narrow windows:** under about 700px the category list becomes a drop-down above the settings.
- **Themes:** every theme looks right in light and dark.

### 4. Advanced, collapsed (S)

The file-only settings Alan agreed in item 1. Never `live_mode.required`, `assistant.enabled` or the permission rules.

### 5. Bring `main` in, then the tests that find cards by heading (S–M)

1. **Bring `main` in** after `sprint-polish` merges, and resolve the conflicts.
2. **Fix the existing tests** that set `STAB` or find a card by its heading, listed in BL-115: `test_dashboard_editing`, `test_debug_log_wiring`, `test_pages`, `test_people_dashboard`, `test_project_names`, `test_sweep_alerts`, `test_today_brief`, `test_workstreams`. Plus any from `sprint-polish` that do the same.
3. **Add the new tests:**
   - the categories;
   - search;
   - deep links and old addresses;
   - **every setting on the page appears in exactly one category;**
   - the narrow layout;
   - a save still writes the same key, with its backup and log entry.

## Boundaries

- **Owns:** the Settings view in `dashboard.html`. That covers `renderSettings` and its wrappers, the cards, the `#settings` addresses and the status line's Diagnostics link. It also owns the Settings sections of `help.md`.
- **`sprint-polish` owns** the Work, Review, Calendar Import, Current state and ask creaite parts of `dashboard.html`, plus the engine scripts. Don't edit those.
  - **The Word label setting:** BL-121 (in `sprint-polish`) removes it. Don't carry it into the new page. If it is still on the page when you bring `main` in, drop it then.
- **Shared files** (`dashboard.html`, `help.md`, `dev/dashboard-spec.md`):
  - put new code in its own marked section, `/* ===== Settings page (BL-115, sprint-settings) ===== */`;
  - don't reformat unrelated lines.
- **No engine or schema change:** the dashboard, Help, the spec and tests only.
- **Leave `dev/BACKLOG.md` and `dev/BRD.md` alone;** they're updated at merge. Write the FR text you'd add in BUILD.
- **Help:** update `help.md`, then run `python3 dev/tools/build_guides.py`.
- **Running tests:**
  - run them in the worktree, never in the main folder: the main folder's `system/config/settings.json` has Alan's uncommitted dev values, and the worktree has the committed copy;
  - stop a run by its process tree, never with `pkill` by name.
- **Development guard:** sample data only; test with temporary vaults.

## Done when

- **Tests:** as listed in item 5.
- **The full suite passes once** on the final branch, after `main` is brought in: `python3 dev/tools/run_tests.py -j 4`.
- **Docs:**
  - `dev/dashboard-spec.md`;
  - Help and the guides;
  - a "Sprint settings" section in `dev/BUILD.md`.
- **Commits:** each item is committed separately on `sprint-settings`, with the attribution lines from the session's instructions. Never push or merge into `main`.
