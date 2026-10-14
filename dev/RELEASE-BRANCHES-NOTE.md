# Release branches (Team 2 → Team 1), 14-10-2026

Alan asked Team 2 to stack the waiting branches into one branch per release, so Team 1 merges one green branch per
release instead of about fifteen. Each release branch is built from the one before with `git merge --no-ff` of the
listed `origin/` branches, in order; nothing was rebased or force-pushed, and main was not touched.

## How Team 1 uses them

Merge `release-190` into main, then `release-191`, then `release-192`, then `release-193`. Each is a superset of the
one before, so once main has `release-190` the next is a fast-forward-able merge of only its own release's work. If
one of the source branches moves again, merge it into the matching release branch (and the later ones) the same way.

Every merge commit names the branch and what it carries; every fix is its own small commit on the release branch.

## release-190 (v1.9.0)

From `origin/main` 4370a4e. Merged, in order:

| Branch | Head | Items |
|---|---|---|
| `dev-date-tests` | 1b7eaaa | main's three date-dependent tests |
| `v19-promises-data` | d6136a7 | BL-125 A |
| `v19-review-picker` | f68cd8b | BL-297 D |
| `v19-draft-chase` | 339e510 | BL-298 |
| `sprint-vip-ui` | 67a7216 | BL-288 part 2, BL-296 |
| `sprint-prep-shape` | a3b86d9 | BL-286 C (contains `sprint-prep-popup` d5d6e1e: BL-286 A, B, E and BL-287) |
| `sprint-today-days-ui` | dd241d0, then 218076e | BL-293 (218076e: the two CI fixes, test_motion and the prep brief's day) |
| `sprint-close-day-ui` | 88f90c0, then 856515d | BL-295 (856515d carries 218076e) |
| `sprint-prep-shape` (again) | 8e838a1 | test_prep_shape waits for the suggestion chips (its race) |
| `sprint-prep-page` | 6851691 | BL-286 D: Meetings › Prep (`#prep=<key>`), so Open prep page and the Open icon show the page |
| `sprint-panel-sweep` | 3b9074a | BL-309: "sweep" typed in ask creaite is its own confirmation |
| `fix-work-reload` | c4b3d10 | BL-318: a reload on Work keeps its view |

**Conflicts and how they were resolved**

- Generated files (`dashboard.html`, `guide-how-to.html`, `guide-first-day.html`) in most merges: either side taken,
  then rebuilt with `split_dashboard.py build` and `build_guides.py`.
- `dashboard-spec.md`, `help.md` (picker × promises): the picker's new BL-297 D entry kept, and the promises branch's
  "a promise that looks kept" wording kept in the BL-218 Looks done line.
- `panel.js`, `settings.js` (vip-ui), `ask.js` and `main.js`/`globals.json` (several): import or export lines only;
  the union kept.
- `drafts.js` (prep-shape × vip): the same fetch line; the side with BL-296's comment kept. `style.css`: two new
  blocks at the same place, both kept.
- **`sprint-today-days-ui` × `sprint-prep-popup`/`shape`** (built side by side off `v19-base`; this is where they
  first meet):
  - `components/Chip.jsx` (add/add): each branch made its own BL-256 Chip. Joined into one that takes both sets of
    props (`icon`, `name` read first on a span, `cls`; `tone`, `className`, `button`, `disabled`, `drawChip`).
    `test_block_chip.py` keeps both branches' tests (`ChipBlock`, `ChipBlockTones`).
  - `projects.js`: `openPrep`/`drawPrep` from the popup (it owns openPrep; its header writes any day).
  - `today.js`: `renderDay` and the day machinery from the day line; the popup's, VIP's and promises' changes kept
    (`renderSeeFirst`, promises, `prepGoHtml` for the Week ahead).
  - `components/today/DayMeetings.jsx`: the Prep pill's BL-287 Open icon and "Prep page made" now use the popup's
    markup and behaviour (`span.prepline`, `button.ib.prepgo[data-prepgo]`, going to Meetings › Prep inside creaite;
    `aria-disabled` without the live server) in place of the day line's own `.lk.open`, which opened the file.
  - `meetings.js`: `renderToday` after a prep page is saved (the band and the Week ahead), `PREPSAVED` kept.
  - `help.md`: the popup's Prep steps, with the day line's "any later day" and "Prepare" in step 1.
- `test_sweep_alerts.py` (218076e): release-190's check of the popup's header ("Tomorrow · Thursday … · 10:00 – …")
  kept; the branch's check was for the old popup's label.
- **`sprint-close-day-ui`**: Today's section counts in `test_dashboard_editing` and `test_today_brief` (First thing
  and You owe/Waiting on both add sections): 9 sections, heads First thing, Decisions needed, Needs attention, Your
  commitments, You owe, Waiting on, Resolved, Week ahead, Portfolio.

- **`sprint-prep-page`** (also built off `v19-base` beside the day line):
  - `components/Tabs.jsx` (add/add): the day line's Tabs (`items`, `controls`, `className`; stops at the ends) and the
    prep page's (`tabs`, `idBase` giving tab and panel ids, the `.tabs` class; wraps round as `#wtabs`) joined into one
    that takes either call. `test_block_tabs.py` keeps both branches' tests (`TabsBlock`, `TabsBlockIds`).
  - `components/Chip.jsx` (add/add): the prep page's is the popup's; release-190's joined Chip kept.
  - `stores/prep.js`: its private request counter `asked` renamed `pageAsked`. The popup's store has one of the same
    name, and in the one bundled script the two would have shared it (check.py JSDUP). Done in the merge commit.
  - `meetings.js`: the prep page's quiet build (`o.quiet`) with release-190's `PREPSAVED` and `renderToday`.
  - `help.md`: the popup's steps 1 to 5, then the prep page's "inside creaite" as step 6; the 1:1 line is now 7.
- `fix-work-reload`: release notes (both lines) and the generated page only. `sprint-panel-sweep` merged cleanly.

**Fixes (own commits)**

- 042b7ce: `ChasePane.jsx`'s private `Icon` renamed `ShapesIcon`. BL-298 and BL-286 each declared a top-level `Icon`;
  in the bundled script the later replaced the other everywhere (check.py JSDUP).
- 6cd861c: `test_today_days_ui` uses the joined popup's selectors (`#prepWhen` "Friday 16th October · 10:00 …",
  `#prepProjBtn`, `[data-prepview]`, `.prepgo`). Same checks.
- 1e5f983: Help's BL-309 line rendered its `**` (a code span inside bold, which Help's renderer doesn't take), so
  test_help failed. Now "**Typing sweep is your go-ahead:**"; the examples after it keep their code spans.

**Goldens**

- 3cbefcb: `settings-general` re-recorded: generated `sr#` ids only (prep-shape's AI drafts row sits above close-day's
  rows, so their numbers shift by one). Nothing else in the screen changed.

**Tests (local, python3.14)**: `check.py` OK. Passed: test_snapshots, test_dashboard_split, test_help,
test_help_loop, test_ui_sweep, test_today_brief, test_today_days, test_today_days_ui, test_close_day_card,
test_settings_page, test_meeting_hub, test_work_item_peek, test_motion, test_sweep_alerts, test_promises,
test_promises_page, test_smart_updates (BL-297 D), test_draft_chase, test_draft_chase_pane, test_vip_screens,
test_vip_private, test_prep_popup, test_prep_shape, test_block_chip, test_block_tabs, test_dashboard_editing,
test_insight, test_guard_pinned, test_reach, test_record_commands, test_script_policy. Under load, test_ui_sweep's
Reflow and one today_days_ui swipe test failed once and passed alone; test_prep_shape's test_3 timed out once and
passed on rerun (it does the same on `origin/sprint-prep-shape` alone: flaky, not from the merge).

**Security:** BL-309 changes `live_server.py` only: the server, never the model, recognises a plain typed sweep
(`panel_sweep`, a fixed list of cx-sweep's words; an image, a confirmed request, or another instruction makes it a plain
chat) and runs it under BL-295's existing guarded `sweep` mode. No change to `reach.py`, `SCRIPT_COMMANDS`, the tool
lists or the routes; test_guard_pinned, test_reach, test_record_commands and test_script_policy pass unchanged.

**Also passed after these four:** test_prep_page_content, test_prep_view, test_panel_sweep, test_chat_and_sweep,
test_work_reload_address, test_work_saved_views, test_block_tabs, and the whole set above (test_prep_shape now steady).

**BL-255 check:** `origin/dev-bl255-check` (8550693, tests only: `test_script_policy.py` and its note) was built on
release-191, so merging the branch would have brought v1.9.1 into release-190. Its one commit was cherry-picked
instead (`-x`, 81e6eb2 on release-190); release-191 gets it through release-190. It shows nothing is missing: the
script hashes are made per page by live_server, so BL-255 needs no re-hash.

**Missing from v1.9.0:** nothing. (sprint-prep-page, sprint-panel-sweep and fix-work-reload, listed missing at first,
are now in; BL-255's re-hash is not needed, above.)

## release-191 (v1.9.1)

From `release-190`. Merged, in order:

| Branch | Head | Items |
|---|---|---|
| `v191-ask-claims` | eb10695 | BL-314 (ask creaite's claims) |
| `v191-ask-routing` | cf62a1b | BL-314 (field changes through the dashboard's actions) |
| `fix-day-arrows` | 19ccf04 | BL-321 (the day arrows never move) |

**Conflicts:** `ask.js`'s `work.js` import (BL-314's `itemsMove`) beside release-190's `openCloseDay` import: both
kept. `dashboard.html` rebuilt after the ask pair, as `V191-ASK-ROUTING-NOTE.md` asks. `fix-day-arrows` merged cleanly.

**Fixes, goldens:** none.

**Security:** none of the three changes a guard file, tool list, `SCRIPT_COMMANDS` or route (their notes); the guard
tests pass unchanged.

**Tests (local):** `check.py` OK. Passed: test_ask_claims, test_ask_field_card, test_ask_change_card,
test_today_days_ui, test_today_days, test_snapshots, test_dashboard_split, test_help, test_help_loop, test_ui_sweep,
test_today_brief, test_close_day_card, test_settings_page, test_meeting_hub, test_work_item_peek, test_motion,
test_sweep_alerts, test_prep_popup, test_guard_pinned, test_reach, test_record_commands, test_script_policy.

After release-190's later merges came in (prep-page, panel-sweep, work-reload, BL-255 check; help.md's BL-314 and
BL-309 lines kept side by side), re-run: the set above plus test_panel_sweep, test_chat_and_sweep, test_prep_view,
test_prep_page_content, test_work_reload_address and test_block_tabs, all passed.

## release-192 (v1.9.2)

From `release-191` (5586acf, carried in as it moved). Merged, in order:

| Branch | Head | Items |
|---|---|---|
| `v192-settings-ui` | dd7101e | BL-320 screens; contains `v192-settings-server` (8d7a199), `v192-fixit` (887f8fd) and `sprint-close-day-ui` |
| `v192-work-reflow` | 85c9b13 | Work's table overlap at 648-680px |
| `v192-reject-reasons` | 03ac7f3 | BL-315 server side (then contained in `v192-reject-ui`) |
| `v192-sidebar` | c7ea3b4 | BL-319 part 6: the sidebar on Preact |
| `v192-settings-server` | 52a907d | Week ahead defaults to Urgent only (Alan) |
| `v192-reject-ui` | eb5374a | BL-315 screens (contains `v192-reject-reasons`) |
| `v192-today-home` | 7b17445 | BL-319: Today as one home (To decide wired to BL-315's menu) |

(`v192-reject-reasons` was merged before `v192-reject-ui` was pushed; the later merge brings only the screens.)

**Conflicts and how they were resolved**

- **`v192-settings-ui`** (built on main, so it meets release-190/191 here):
  - Goldens: `settings-general` and `settings-capture` deleted (BL-320's four replace them; Alan approved); `settings-health` from the branch.
  - `settings.js`: imports joined (BL-320's settings store, BL-296's `draftAsk`); BL-320's VIP section rows (only Browser notification is left there).
  - `help.md`: release-191's text (BL-288 part 2, promises, BL-297 D, BL-314) at BL-320's new places: Advanced › VIP alerts, AI drafts and Early warnings; Health › Advanced › Review spot-check; Health › creaite version; Shape the meeting's switch. BL-296's `alertDraftWhy` tooltip says Advanced › AI drafts too.
  - `test_settings_page`: BL-320's Essentials with BL-288's wording ("someone you follow closely"; no row says VIP).
  - `test_tracker`, `creaite-rules.md`: both script lists (claims.py with settings_catalogue.py, health.py, health_fixes.py).
- **release-191 into release-192:** `globals.json` regenerated; `PrepPage.jsx`'s private `let mounted` renamed `pageMounted` (BL-320's `settings.js` exports a `mounted()`, and the bundle is one script: check.py JSDUP).
- **`v192-reject-reasons`:** `quality.py` (BL-125 A's Promises type kept; BL-315's eight reasons); Review's "Or say" line (both).
- **`v192-sidebar`** (built on `v19-base`): `nav.js` uses `setRailView` and keeps the prep page under Today; `server.js` `renderBadge` through `setRailCount` and keeps the popup's redraw after an apply; `settings.js` keeps release-191's VIP block (Dismiss, Create work item, Messages to see first) with `vipBadge` through `setRailCount` in BL-288's words ("n messages to see first", title "(n) creaite"), not the branch's "(n VIP)"; Help's Settings text gets the branch's "The sidebar" line in place of "The left rail" (Customise from Advanced › Appearance › Sidebar).
- **`v192-reject-ui`** (built on main): `keys.js`/`panel.js` imports joined; `review.js` keeps BL-288's comment and adds BL-315's guesses load; `style.css` keeps BL-297 D's `.rtline` on the line BL-315 changed; Help's Review steps: 11 Update an existing item instead, 12-13 BL-315's reject steps, 14 Looks done; the Reference list takes BL-315's Select several / Reject with a reason / After a reject and release-191's other lines. `RejectMenu.jsx`'s private `menuItems` renamed `rjMenuItems` (the sidebar's `RailMore.jsx` has one: JSDUP). Rebuilt with `split_dashboard.py build`, `build_dashboard_js.py globals` and `build_guides.py`, as its note asks.

- **`v192-today-home`** (contains release-191, the sidebar and the reject branches, not BL-320): `settings.js` takes the
  branch's To decide alerts (`alertFocus`, `vipBadge` through `setRailCount`) in place of Messages to see first; Help's
  VIP steps are the branch's (To decide, the crossed-out eye, the +) at BL-320's places; `test_ui_sweep`'s comment names
  both closed `<details>`; `globals.json` regenerated; `style.css` both blocks.

**Fixes (own commits)**

- 4a6be64: BL-320's catalogue must cover every key in `settings-defaults.json`; three keys from branches built beside it had none (`drafting.shape` BL-286 C, `promises.from_sweep` BL-125 A, `dashboard.rail.more` BL-319). The catalogue raised a KeyError, so Settings never loaded its rows (7 test files failed). Entries added; Shape the meeting joins the Essentials AI drafts row.

**Goldens**

- `settings-general`, `settings-capture` deleted (BL-320; Alan approved).
- 0c8d127: `settings-advanced` and `settings-essentials` re-recorded where the screens combine: BL-288's wording (BL-320's golden said "VIP", which test_vip_screens refuses), the Shape the meeting switch, Promises from the sweep in More settings › Sweep, and the `ss#` ids after it.

**Security:** none from the merges. `v192-fixit`'s `reach.SCRIPT_COMMANDS['session.py']` gains `backup: DERIVED` (its own note, for Team 1 to confirm); `v192-reject-reasons` adds `review.py` read and record commands to `SCRIPT_COMMANDS` (its note). The four guard tests pass.

**Tests (local):** `check.py` OK. Passed (36 files): test_snapshots, test_dashboard_split, test_help, test_help_loop, test_ui_sweep (including the 640px Reflow with the sidebar), test_today_brief, test_today_days_ui, test_close_day_card, test_settings_page, test_settings_calmer, test_settings_catalogue, test_health_fixes, test_meeting_hub, test_work_item_peek, test_rail_customise, test_reject_reasons, test_rejects_real_life, test_quality, test_vip_screens, test_vip_private, test_promises, test_prep_popup, test_prep_view, test_panel_sweep, test_ask_claims, test_ask_field_card, test_motion, test_sweep_alerts, test_update, test_tracker, test_smart_updates, test_guard_pinned, test_reach, test_record_commands, test_script_policy.

After `v192-today-home`: 41 files passed, the set above plus test_today_home, test_rejects_ui, test_block_icon_button,
test_promises_page, test_dashboard_editing and test_insight (test_smart_updates' right-click picker test failed once
under load and passed alone). No golden changed with it.

**Missing from v1.9.2:** nothing. BL-319's Today page (`v192-today-home`) and BL-315's Review bar and menu (`v192-reject-ui`) are in.

## release-193 (v1.9.3: BL-322 Sneak peek, BL-323 backups, BL-275 PDFs in search)

From `release-192` (carried in as it moved, last with dde4343). Merged, in order:

| Branch | Head | Items |
|---|---|---|
| `dev-bl322-sneak-peek` | 14b1059 | BL-322 docs (BACKLOG, STATUS, mockup) |
| `dev-bl323-backups-archive` | ad370b0 | BL-323 and BL-09 docs |
| `dev-bl09-skeleton-archive` | 1ddb083 | BL-09 docs, the v1.9.4 group |
| `v193-sneak-peek-server` | 7097730 | BL-322 server (with the `@n` undo fix) |
| `v193-sneak-peek-ui` | d4759c6 | BL-322 the Sneak peek screen (contains `v19-draft-chase` and the server) |
| `v193-backups` | 58ebf1b | BL-323 backups that look after themselves (contains `v192-fixit`, `v192-settings-ui`) |
| `sprint-search-pdf-eml` | 37cf5df | BL-275 PDFs in search (pypdf 6.20.1 vendored; `INDEX_READERS` 3; BL-276's .eml code reconciled with release-191's) |

v1.9.3 is BL-322 and BL-323 (and BL-275); **BL-09 moved to its own v1.9.4** (Alan, 14-10-2026). There is no
`release-194` yet: it will hold the BL-09 build (`v193-archive` / BL-09's branch) when it is ready, from `release-193`.

**Conflicts and how they were resolved**

- The three docs branches merged cleanly.
- `v193-sneak-peek-server`: `test_tracker`'s script list (claims.py, settings_catalogue.py, health.py, sneak_peek.py: all).
- `v193-sneak-peek-ui`: `panel.js`'s Esc guard keeps release-190's `dialog:modal` (BL-286 E's Prep popup is non-modal while the peek is over it) and adds BL-322's `.sp-box`.
- `v193-backups`: `creaite-rules.md` (release-192's scripts list with claims.py, plus the branch's `backup.py` row); the `settings-advanced` golden (below).
- `sprint-search-pdf-eml`: clean.

**Fixes:** dde4343 on release-192 (test_draft_chase_pane expected the AI drafts switch under Settings › General; BL-320 moved it to Advanced). Nothing else.

**Goldens:** `settings-advanced` re-recorded in the `v193-backups` merge: BL-323's More settings › Safety card (backup retention) beside release-192's More settings › Sweep card (Promises from the sweep), in BL-288's wording; the `ss#` ids follow.

**Security (from the branches' own notes, for Team 1 to confirm; none from the merges):**

- BL-322 server: `reach.SCRIPT_COMMANDS` gains `sneak_peek.py: {read: READ}`; `tracker.py` takes a link end `@n` (the new item n in the same proposal).
- BL-323: `SCRIPT_COMMANDS` gains `backup.py` (`list`, `show` read; `check` derived; `tidy`, `restore` record; `test_record_commands`' list gains those two). `session.py start`/`backup` stay derived but now run the daily Tidy up (never during an ask creaite run). New token-checked routes `/api/backup/list`, `/preview`, `/restore`. The non-negotiable change: the daily zip leaves the vault for the company OneDrive (`creaite-rules.md` updated by the branch).
- BL-275: `INDEX_READERS` raised to 3.
- The guard tests (test_guard_pinned, test_reach, test_record_commands, test_script_policy) pass.

**Tests (local):** `check.py` OK. Passed: test_backups, test_backup_restore_ui, test_sneak_peek_read, test_sneak_peek_ui, test_search, test_search_pdf, test_search_eml, test_search_live, test_search_dashboard, test_onedrive_projects, test_portability, test_check_py39, test_new_vault, test_first_run, test_file_access, test_admin_card, test_snapshots, test_dashboard_split, test_help, test_ui_sweep, test_today_home, test_today_brief, test_today_days_ui, test_close_day_card, test_settings_page, test_settings_calmer, test_settings_catalogue, test_health_fixes, test_meeting_hub, test_work_item_peek, test_rejects_ui, test_rail_customise, test_vip_screens, test_promises, test_prep_popup, test_prep_view, test_ask_claims, test_ask_field_card, test_draft_chase_pane, test_motion, test_sweep_alerts, test_update, test_tracker and the guard tests.

**Open from the branches' notes:** `v193-backups` lists what it didn't do (missed OneDrive days aren't backfilled).
