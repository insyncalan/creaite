# Sprint final: the last of v1.3.0 (BL-137, BL-139, BL-142, BL-143)

Branch `sprint-final`, worktree `../creaite-final`, from `main` after every other v1.3.0 sprint merged. It is the only sprint in flight. Read BL-137, BL-139, BL-142 and BL-143 in `dev/BACKLOG.md` first; they hold Alan's decisions. Where one says "to confirm" or "assumed", take the stated default and note it in BUILD.

## Items

Commit each separately, in this order.

### 1. BL-142: Five themes; "creaite" is the default (S)

**The list:** Brightwater, creaite, Notion, Linear, Cursor.

- **Remove two themes:** `creaite standard` and `Minimals`. Remove their entries in `THEMES` in `dashboard.html` and their light and dark token blocks.
- **Rename one:** `creaite teal` becomes `creaite`. Keep its tokens and its own touches (the teal ask creaite button and panel heading), now keyed to the new name.
- **The default:** `creaite`, in `settings-defaults.json` (`dashboard.palette`) and wherever the page falls back when no palette is saved.
- **Old saved values open as `creaite`:** a saved palette of `creaite standard`, `Minimals` or `creaite teal`, and any name the page doesn't know.
  - **In the page:** one small map, for both the value from `settings.json` and the browser's own saved copy.
  - **In the vault:** `update.py tidy` changes the saved value to `creaite`, logged in the settings log, the same way as the label setting. Add it to `tidy()` and to `merged_changes`, plus a test in `test_update.py` (`TestTidyAfterAnOlderInstaller` shows the pattern).
- **Update everywhere themes are listed:**
  - Help and the guides;
  - `dev/dashboard-spec.md`;
  - `build_dashboard.py`, if it names a theme;
  - the theme tests: they count themes with `theme_count()`, so check them rather than hard-coding five.
- **Contrast:** all five themes, light and dark, still pass.

### 2. BL-143: No Live dot in the left bar (S)

**Remove** `#railLive`, its styles (`.raillive`), `railLive()`, `railLiveGo()` and their listeners.

**The live server check replaces it:** the red `#liveAlert` with the restart command and **Check again**. Make sure every state the dot showed is still covered:
- **Server stopped:** the alert.
- **Server running:** nothing needs showing.
- **The file version of the dashboard while the server runs:** the alert's existing message.

**The dot's tooltip** (when mail and Teams were last swept, when the data was built) goes to **Settings › System › Live server and backups**, as one plain line, if it isn't already there.

**Help:** remove the "Live light" and "dot at the bottom of the left bar" text (two places in `help.md`, and the guides), and describe the alert as the way to see the server is down. Update the tests that look for `#railLive` or count it per theme.

### 3. BL-137: Upload Files lists only uploads (S)

As BL-137 sets out. A file that Calendar Import loaded is known only by its recorded event ID (`f.event`), never by its name. Its state, Preview and Remove move to its meeting row. The Intake badge still counts a loaded transcript that is waiting.

### 4. BL-139: ask creaite's running and finished badge (S–M)

As BL-139 sets out:
- **Where:** fixed at the bottom right.
- **When:** for every run the run engine makes.
- **Finished:** the finished state stays until it's dismissed, the chat is opened, or the next run starts. Stopped and failed runs say so in words.
- **Hidden** while the chat panel is open.
- **The tab title** gets a mark only while the tab is hidden.
- **Accessibility:** `role="status"`.

**Motion (BL-136, merged):** use its tokens and helpers:
- the badge enters as banners do;
- its pulse stops under reduced motion;
- tests run with reduced motion, as the suite now does.

The top-bar dot stays.

## Boundaries

- No other sprint is running. Shared files (`dashboard.html`, `help.md`, `dev/dashboard-spec.md`): put new code in marked sections and don't reformat unrelated lines. Regenerate the guides with `python3 dev/tools/build_guides.py`; never hand-edit them.
- **Engine changes:** item 1 changes `update.py` (and possibly `build_dashboard.py`); item 3 changes `build_dashboard.py`. Add a line for each user-visible change to `dev/release-notes/1.3.0.md` under its headings. `VERSION` stays 1.3.0.
- **Release notes:** the "Check once by hand" list mentions themes and "the Live light"; bring it in line.
- **Don't touch** `dev/BACKLOG.md`, `dev/BRD.md` or `dev/archive/sprints/STATUS.md`; they're updated at merge. Write the FR text in BUILD (FR-57 for the themes; extensions for Intake and ask creaite).
- **Tests:** run them in the worktree, never the main folder, whose `system/config/settings.json` holds Alan's dev values. Stop a run by its process tree, never with `pkill` by name.
- **Development guard:** sample data only; test with temporary vaults.

## Done when

- **Tests:** as listed per item, plus each backlog item's "Touches" tests.
- **The full suite passes once** on the final branch: `python3 dev/tools/run_tests.py -j 4`.
- **Docs:** `dev/dashboard-spec.md`, Help and the guides, a "Sprint final" section in `dev/BUILD.md`, and the 1.3.0 notes.
- **Commits:** each item committed separately on `sprint-final`, with the attribution lines from the session's instructions. Never push or merge into `main`.
