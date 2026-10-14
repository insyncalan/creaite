# Sprint rail: rename the Current state title, customise the left rail, and a better Activity page (BL-162, BL-163, BL-164)

Branch `sprint-rail`, worktree `../creaite-rail`, made from `main` **after `sprint-icons` has merged**. `sprint-icons` moves the rail's icons onto the shared `ic(name)` helper and adds the one tooltip; this sprint rebuilds the rail from a list and needs both. Three items, built in the order below. Rough size: six to eight days. **It is a post-1.3 sprint (Alan, 10-10-2026): it is not a gate for 1.3.0** and ships in the release after it.

Read **BL-162, BL-163 and BL-164 in `dev/BACKLOG.md`** first: they hold Alan's requests. Where the backlog says "to confirm", take the default in "Decisions taken" below and note it in BUILD. Before starting, run `git worktree list` (no `sprint-icons`) and `git log main` (it has `sprint-icons`); if it is not merged, stop and say so. Bring `main` in. Read what `sprint-icons` built: `ic()`, the tooltip, and the rail's markup as it now is. Where the code differs from the backlog text, the code wins; say so in BUILD.

## Items

Commit each separately, in this order.

### 1. BL-162: click the Current state title to rename it (S)

The project page's Current state card has a fixed heading ("Current state"). It becomes a heading Alan can click and change, per project.

- **Where it is kept:** a line in the project's `CLAUDE.md`, `**Current state title:** <words>`, beside `**Client report rhythm:**`. `build_dashboard.memory()` reads it (as it reads the rhythm: a regex on the line), trims it, strips Markdown and line breaks, caps it at 40 characters, and falls back to "Current state"; it goes to the page as the project's `cstitle`.
- **The section in `CLAUDE.md` keeps its name, `## Current state`.** The reports (weekly and client), Generate, Make it executive, search and the checks all find the section by that name, so none of them change. The title is a label for the dashboard only.
- **The heading:** the card's `<h2>` keeps its heading role and holds a button (pencil on hover and focus, tooltip "Rename this title" from BL-158's tooltip). Click or Enter turns it into a one-line text box with the words selected (`maxlength` 40, label "Title of this card"); **Enter or leaving it saves, Esc cancels**; empty, or the default words, put the default back. While the Current state editor is open the title is not editable (one thing at a time).
- **Saving follows `setRhythm`,** the existing way a project-header line is written: it needs the vault (`needVault`), saves a copy of the file to `system/backups/files/<CODE>-CLAUDE-<stamp>.md`, writes the line and logs it in `system/config/settings-log.jsonl` (`current_state_title.<CODE>`, old and new). If the line is missing it is added under the rhythm line (or, if that is missing too, directly above `## Current state`); a default title removes the line. The snack message offers **Undo**, which restores the backup. Without the live server's vault access, the heading is plain text.
- **Where the title shows:** the card heading, the Generate dialog's heading and labels for that project, the editor's accessible names, and the project page's own breadcrumbs or section links. Where text names the section for a technical reason ("`## Current state`", reports, Help) it keeps "Current state".
- **Tests (extend the cockpit tests):** rename, cancel with Esc, empty reverts to the default and removes the line, 40-character cap, Undo restores the file, a second project keeps its own title, the line is added when missing, the `## Current state` text and its images are untouched, the weekly report and Generate still find the section, the heading stays an `<h2>`, and a keyboard-only run works.

### 2. BL-163: customise the left rail (M)

Alan can hide rail items, put them in his own order, and choose icons only or icons with titles.

- **A list, not markup.** The rail is built from `RAIL_ITEMS`: `id`, title, icon name (from `ic()`), whether it carries a badge, its group (**main**: Today, Intake, Projects, Work, People, Review, Files; **foot**: Activity, Settings), and whether it can be hidden. `renderRail()` builds the buttons from the list and the saved choice. The current-page marker, the Intake and Review badges, the VIP dot on Today and every existing handler keep working (they find buttons by `data-v`, which stays).
- **The choice is kept in `settings.json`,** `dashboard.rail = {"order": [ids], "hidden": [ids], "display": "titles" | "icons"}`, defaults in `system/templates/settings-defaults.json` (all items shown, today's order, titles), written through `writeSettings` (a backup and a log line). Add the key to the live server's list of settings the page may write (find where `dashboard.*` keys are allowed in `live_server.py`). Unknown ids in the saved order are ignored and new items are appended, so a later item never disappears. Because it is in the vault, the Chrome app and the browser tab agree.
- **Customise control:** a button at the foot of the rail (the "sliders" icon from `ic()`, tooltip "Customise the rail") opens a popover listing every item with a **switch to show or hide it**, a **handle to drag**, and **Move up and Move down buttons** (also Alt with the arrow keys on a focused row), so reordering never depends on dragging. Items stay within their group: the foot group keeps Activity and Settings at the bottom. **Today and Settings cannot be hidden** (their switches are disabled, with the reason beside them). Below the list: **Display: Icons and titles / Icons only**, and **Reset to default**. The same panel opens from Settings › General › Appearance (a row "Left rail: Customise…"; add it to the Settings sections list, `SETSECTIONS`, `sprint-settings` having merged). Esc closes it and returns focus to the button that opened it.
- **Icons only:** the rail narrows (the column width is one CSS variable, `--rail-w`, about 48px against today's 60px); each button shows its icon only, with the name as its accessible name (`aria-label`) and the one tooltip from `sprint-icons` on hover and focus. Badges stay on their icons, readable at the smaller size. The current-page marker is unchanged.
- **A hidden item is still reachable and never silent:** ⌘K and the existing shortcuts still open it. When any item is hidden, a small "…" button appears in the foot group that opens a short list of the hidden items, each with its badge count; when a hidden item has something waiting (Intake files, Review proposals) the "…" button carries a dot. Choosing an item from the list opens it.
- **Not changed:** what each item opens; the order of the Settings and Activity entries within their group unless moved; the narrow-window layout (check the rail at the widths where it changes, with items hidden and with icons only).
- **Tests (new `test_rail_customise.py`, and the rail assertions in existing tests):** hide and show an item and the choice survives a reload and is in `settings.json`; reorder by mouse, by the buttons and by Alt+arrows; the foot group stays at the bottom; Today and Settings cannot be hidden; Reset restores the defaults; Icons only narrows the rail and every button keeps its accessible name and tooltip; a hidden Review with pending items shows its count and the dot on "…"; ⌘K opens a hidden view; an unknown id in the saved order is ignored and a new item is appended; the Settings row opens the same panel; focus returns on Esc.

### 3. BL-164: Activity, search, undo of several past changes, and a type icon on each entry (M–L)

Read **BL-164 in `dev/BACKLOG.md`**. Three additions to the Activity page (`#v-activity`, `renderActivity`, `actLine`), built in this order.

**a. A type icon on each entry** (S). `build_dashboard.activity()` adds the entry's `kind` (action, risk, issue, assumption or dependency by the RAID type, decision, milestone, project, weekly update, setting, file) and its `rowid` to each entry; the row shows the matching icon from `ic()` before the ID, with the type's name as its tooltip (`sprint-icons`' tooltip) and accessible name. Never colour alone. Settings and file entries get the icons the file and settings pages already use.

**b. Search and filters** (S–M). A search box above the table (the `/` key focuses it while Activity is open; it does not steal `/` anywhere else): filters as you type on the item's ID and text, the project's name, who made the change, the change itself and the date, all case-insensitive, with a count "12 of 340" and "Clear". Type chips (the same icons) and a date range narrow further; the filters live in the address (`#activity?q=…&type=…`) and survive opening an item and coming back. Empty result says what was searched and offers Clear. The view still shows the newest 2000 entries the builder returns; say so in the footer when the cap is reached.

**c. Select several and undo** (M). Tick boxes on each row and the Work lists' selection (click selects, Cmd or Ctrl adds, Shift takes a range, Esc clears; reuse the BL-122 helpers, do not write a second model) and a bar "3 selected: Undo 3" above the table.
- **The rule:** undoing a past change puts each field back to what it was before **only where it still holds the value that change gave it.** If the item has changed since, the entry is **skipped and listed** ("ABC-A-003 has changed since: left as it is") and the rest are undone. A change that created an item is undone by removing it only if nothing has been added to it since, as `cmd_undo` already decides (`changed_since`). Entries that are themselves undos, rejected-proposal records and settings lines (not in `change_log`) cannot be selected.
- **How (tracker.py, the single writer):** a new command, `tracker.py undo-changes <rowid> [<rowid> …]`, built from the same pieces as `cmd_undo` (`by_item`, `changed_since`, the restore of old values, `backup_db`, the single transaction). It does not touch the whole-apply undo. It records the result as **one new apply** whose rows are ordinary updates (the new value is the restored old value), with `via` set to `revert:<rowid>,<rowid>,…` so no schema change is needed. Because it is an ordinary apply, **the existing "undo last apply" reverses it**, and Activity shows it as one entry, "Undid 3 changes", with its own Undo. `activity()` reads the `via` to mark each reverted entry "undone" (struck through, with the Undo button replaced by "undone").
- **The latest apply keeps its exact whole-apply Undo** (the row button) as now; the new bar is for older entries and for several at once. Run the whole-apply check first so a selection that is the entire latest apply uses it.
- **The confirm:** before anything changes, a dialog lists each selected entry as "ABC-A-003 · status Closed → Open" or "skipped: changed since", with Undo n / Cancel; over about 25 entries it asks again with the count. The dashboard route (`/api/undo-changes`, token-protected, via the live server running `tracker.py undo-changes`) returns the done and skipped lists; the page shows the snack "Undid 3 changes, skipped 1" with Undo.
- **Tests (new `test_activity_undo.py`, plus the Activity assertions in existing tests):** the icon and its name for each kind; search by ID, text, project, person and date, the count, the address round trip and Clear; type chips; selecting with Cmd, Ctrl, Shift and Esc; undoing three past changes in three items restores them in one new apply; a later edit to one item skips it and lists it, the others still restore; an insert is removed only if untouched; the revert is itself undone by "undo last apply" and by its row's Undo; the reverted entries show "undone"; a selection of the whole latest apply uses the exact undo; the confirm's list matches what happens; `via` carries the rowids; the database backup exists; no schema change (`tracker.py migrate` run twice changes nothing).

## Decisions taken (defaults; Alan has not answered these yet)

| Question | Default |
|---|---|
| Is the Current state title per project or one for all? | Per project, in the project's `CLAUDE.md` (a label only; the `## Current state` section keeps its name) |
| Does the rename appear in Activity? | No: it is a header line, saved like the report rhythm, with a backup, a log line and Undo; Activity lists tracked items. (The backlog text said it would; take this and note it in BUILD) |
| Do the reports use the project's title? | No: they keep their own wording |
| Where is the rail choice kept? | `settings.json` (`dashboard.rail`), not the browser |
| Can an item move between the main and foot groups? | No: order within a group only |
| Can Today or Settings be hidden? | No: there is always a way back |
| What happens to a hidden item with something waiting? | A "…" button in the foot group lists hidden items with their counts and carries a dot |
| BL-164: is there a schema change for undoing past changes? | No: the revert is one ordinary apply with `via = revert:<rowids>`; `activity()` reads it to mark reverted entries |
| BL-164: what if an item changed since? | That entry is skipped and listed; the others still undo |
| BL-164: can an undo be undone? | Yes: it is an ordinary apply, so "undo last apply" and its row Undo reverse it |
| BL-164: how many entries does Activity show? | The newest 2000, as now; the footer says so when the cap is reached |

## Boundaries

- **Owns:** the Activity view (`#v-activity`, `renderActivity`, `actLine`, its toolbar, selection, confirm and dialogs), the `activity()` builder in `build_dashboard.py` (kind, rowid, reverted marks), the new `undo-changes` command in `tracker.py` and its live-server route; the rail (its markup, `.rail*` CSS, `--rail-w`, `renderRail`, the Customise popover and the "…" list); the Current state card's heading and its title editor in the cockpit; `build_dashboard.memory()` (the title line only); the new rail setting in `settings-defaults.json` and the live server's list of settings the page may write; the Appearance row for the rail in the Settings sections.
- **Don't edit:** the Current state editor itself, Generate, Make it executive, the reports and their skills, the Work, Review, Today, Files and People views, `propose.py`, the schema, `cmd_undo` and `cmd_apply` (the new command sits beside them and reuses their helpers), or the apply path for proposals. No schema change.
- **Shared files** (`dashboard.html`, `help.md`, `dev/dashboard-spec.md`, `build_dashboard.py`, `settings-defaults.json`): new code in marked sections (`/* ===== BL-162 (sprint-rail) ===== */`, `/* ===== BL-163 (sprint-rail) ===== */`) and no reformatting of unrelated lines. Regenerate the guides after Help changes (`python3 dev/tools/build_guides.py`).
- **Engine changes ship in a release:** all three items change the dashboard template and `build_dashboard.py`; BL-163 adds a settings default; BL-164 adds a `tracker.py` command and a live-server route. Add a line each to the release notes for the version after 1.3.0 (create `dev/release-notes/<next>.md` if none exists; don't change `VERSION`).
- **Don't touch `dev/BACKLOG.md` or `dev/BRD.md`;** they are updated at merge. Write the FR text you'd add in BUILD: BL-162 extends the project page requirement (FR-08); BL-163 is a new requirement beside the Settings page (FR-115); BL-164 extends FR-51 and FR-60 (Activity).
- **Colour is never the only cue** (the hidden-item dot also has a count and a name; the switches carry their state in words); check all five themes in light and dark, and with reduced motion.
- **Tests start from your own settings:** run them in the worktree, which has the committed `settings.json`. **Stop a test run by its process tree,** never with `pkill` by name.
- **Development guard:** sample data only; test with temporary vaults and fictional projects.

## Done when

- **Tests:** as listed per item; the existing cockpit, rail, Settings and Today tests pass or are updated for the list-built rail (not deleted).
- **The full suite passes once** on the final branch, after `main` is brought in: `python3 dev/tools/run_tests.py -j 4`.
- **Docs:** `dev/dashboard-spec.md`, Help (the project page, the rail and Settings) and the guides, a "Sprint rail" section in `dev/BUILD.md` (including the FR text and the decision on Activity), and the release-notes lines.
- **Alan checks, once, in the Chrome app:** rename a project's Current state title and undo it; search Activity for a person and an ID, tick three older changes (not the latest apply) and undo them, see one that was edited since skipped, then undo the undo; hide Files, move People above Work, switch to icons only, close and reopen the app and see it kept; hide Review while a proposal is pending and see the count on the "…" button; Reset.
- **Commits:** each item committed separately on `sprint-rail`, with the attribution lines from the session's instructions. Never push or merge into `main`.

## Hand-offs

(Changes needed in files another sprint owns.)
