# Sprint polish 2: the UX sweep's follow-ups and test hygiene (BL-165 to BL-169, BL-172, BL-173)

Branch `sprint-polish-2`, worktree `../creaite-polish-2`, made from the tip of `main` **after v1.3.0 is published**. It runs alongside `sprint-rail` (`rail-and-titles.md`), and either may merge first. Read BL-165 to BL-169, BL-172 and BL-173 in `dev/BACKLOG.md`, the "Sprint ux" section and the **UX baseline** (ten checks) in `dev/BUILD.md`, and BL-171's note in BUILD (`CREAITE_NO_LAUNCH`). Where something is left open, take the most conservative sensible default, note it in BUILD and carry on.

**Alan's principle (from `sprint-ux`):** judge each change by how it feels in the real browser. For every item, open the dashboard (`dev/tests/live_browser.py`; screenshots with `dev/tools/cdp.py`) at 1400px and 1100px, with ask creaite open and closed, light and dark, in at least two themes, and keep the screenshot paths for the report.

## Items

Commit each separately, in this order, each in its own marked block (`/* ===== BL-1xx (sprint-polish-2) ===== */`).

### 1. BL-172: tests clean up their vaults (S–M), first

About 180 throwaway vaults (`creaite-test-*` in the temp folder) are left behind by test runs.
- **Find where they leak:** count the vaults before and after each test file (`run_tests.py` can do it per file), and fix the helpers that don't remove theirs (the `Vault` helpers, `LiveBrowserCase`, and anything that copies a vault). Keep a vault on failure only if a test already does that on purpose.
- **Count check:** `run_tests.py` reports any file that leaves a vault behind (a warning line, not a failure).
- **Never** delete a vault another run may be using. A cleanup only removes what its own test made.

### 2. BL-169: the save hint shows only when it helps (S)

The "⌘↵ saves and closes · Esc cancels" line shows for the whole time the panel is in edit mode. Show it once a field has changed (or on focus of the first field for a new item), and keep it out of the way of the fields. Use the Keys chip's pattern (BL-155) if that reads better.

### 3. BL-167: an unsaved side-panel edit survives a reload (S)

Keep the draft of the open side panel (the item and the changed fields) in the browser, per item, the same way `sprint-ux` (BL-148) keeps the chat draft. After a reload, opening that item offers **Restore unsaved changes** or **Discard**. Nothing is written to the vault until Save, and a draft older than 7 days, or for an item that has since changed, is dropped with a note.

### 4. BL-173: ask creaite opens over the page (S)

As BL-173 sets out. **Only the ask creaite panel changes:** it overlays the page at every width, and the page no longer narrows or reflows for it (this undoes BL-150 for the chat). **The work item view and edit panels keep exactly their current behaviour,** including any room the page makes for them and any folding they cause; compare them before and after with screenshots. With both open, the chat sits above and leaves the item panel's Save visible. Do this before BL-165.

### 5. BL-165: wide tables show that they scroll (S)

On narrow screens and beside ask creaite, Projects, Work and Settings › People cut off columns with no sign. Give each scrolling table a visible edge fade and a "more columns →" cue that goes when scrolled to the end, and keep the first column (the ID or name) fixed while it scrolls sideways. Check at 1100px with the chat open and at 900px.

### 6. BL-168: Help's loop diagram fits beside ask creaite (S)

At 1100px with the chat open, the loop diagram is cramped. Let it reflow (stack its steps) below a width, rather than scale its text down. Regenerate the guides.

### 7. BL-166: setup in the dashboard where it can be (M), last

Connecting Microsoft 365, running setup and making the launcher still send Alan to Claude Code.
- **First, find out what the dashboard can do itself through the live server:** the launcher (`launch.py`), the setup steps `cx-setup` runs with scripts, and doctor. Build those as buttons in the first-run checklist (BL-156) and Settings › System, using routes that call the existing scripts. Alan's click is the go-ahead; a step that changes something is shown first.
- **What can't be done from the page** (the Microsoft 365 connection is authorised in Claude itself): the checklist row explains it in one line, with a **Copy** button for the exact thing to say, and a **Check again** that confirms when it's done.
- **No new permissions, and no skip-permissions mode.** Any route that runs a script goes through the live server's existing run engine and allow list. If a step needs more than that, leave it as a copyable step and note it under "Open".

## Boundaries

- **`sprint-rail` owns:**
  - the rail, the Activity view and its `activity()` builder;
  - the Current state title;
  - the new `undo-changes` command in `tracker.py`.

  Don't edit those.
- **Shared files** (`dashboard.html`, `help.md`, `dev/dashboard-spec.md`, `build_dashboard.py`, `live_server.py`): new code in marked sections, and don't reformat unrelated lines. Regenerate the guides with `python3 dev/tools/build_guides.py`; never hand-merge them.
- **No schema change.** Engine changes (BL-166's routes, BL-172's test runner) go in the next release's notes: create `dev/release-notes/1.4.0.md` if it doesn't exist, and don't change `VERSION`.
- **Don't edit** `dev/BACKLOG.md`, `dev/BRD.md` or `dev/sprints/STATUS.md` (the usual rule). Write the FR text in BUILD; the scrum master records it at merge.
- **Development guard:** sample data only; test with temporary vaults; never connect to Microsoft 365. Tests set `CREAITE_NO_LAUNCH=1` (BL-171), so nothing opens Word or other apps.
- **Stop a test run by its process tree,** never with `pkill` by name.

## Tests

The sprint runs **its own tests**; one pass is enough (`dev/sprints/STATUS.md`). A file that fails under load and passes alone counts; name it.
- **BL-172:**
  - a test run leaves no `creaite-test-*` folder behind;
  - the runner's per-file count names a leaking file.
- **BL-169:** the hint is hidden until a field changes, then shown.
- **BL-167:**
  - an edit, a reload, then Restore brings the changed fields back;
  - Discard drops them;
  - a draft for an item that has since changed is dropped with a note;
  - nothing is staged before Save.
- **BL-173:**
  - with the chat open at 1400px and 1100px, the main area's width and its first row's position are unchanged;
  - with an item panel open, the layout is exactly as before (ask creaite only changes);
  - the side panel's Save stays visible with both open;
  - `test_panel_room` and `test_work_filters_live`'s folding case are updated to match.
- **BL-165:**
  - at 1100px with the chat open, each table shows the cue;
  - the cue goes at the end;
  - the first column stays fixed.
- **BL-168:** at 1100px with the chat open, the diagram's steps stack and no text is under 12px.
- **BL-166:**
  - each new route runs only its script, through the run engine;
  - each checklist row's Copy and Check again work;
  - the guard and allow list are unchanged (`test_permissions`, `test_admin_card`).
- **Re-run the existing files that touch these areas:**
  - `test_dashboard_editing`, `test_side_panel_live`, `test_first_run`;
  - `test_help`, `test_pages`, `test_people_dashboard`;
  - `test_work_filters_live`, `test_live_server`, `test_app_launcher`.

## Done when

- **Built:** each item is built, looked at in the browser and committed.
- **Tests:** the tests above pass.
- **Docs:**
  - Help and the guides are current;
  - BUILD has a "Sprint polish 2" section (decisions, departures, FR text, "Open", Alan's hand checks);
  - the 1.4.0 release notes have a line per item.
- **Never push or merge into `main`.**
