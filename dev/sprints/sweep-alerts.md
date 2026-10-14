# Sprint: Mail, calendar and alerts (BL-97, BL-99, BL-98)

**Status (09-10-2026): merged into `main` (`d27e4a9`, 01:54); worktree removed.**

Branch `sprint-sweep-alerts`, worktree `../creaite-sweep`. Runs in parallel with `sprint-permissions` (`../creaite-permissions`) and `sprint-pages` (`../creaite-pages`). **Merge order: permissions, then this sprint, then pages.** Read BL-97, BL-99 and BL-98 in `dev/BACKLOG.md` first. They hold Alan's decisions; follow them, and where one says "to confirm", take its stated default.

## Goal

The sweep reads only what matters. Anything from a VIP is never missed. Meeting prep ranks what the meeting is about and can produce a Prep page.

## Items

Commit each separately, in this order.

### 1. BL-97: Sweep ignore list (S)

- **Settings:** `sweep.ignore` in `settings.json`, seeded with the two rules in BL-97 and edited in Settings › Sweep.
- **Applied in `sweep.py`:** to the window output, the stage backstop, the calendar filter and the summary counts.
- **cx-sweep skill:** steps 2 and 8 updated.
- **Never silent:** ignored items are counted, never silently dropped.

### 2. BL-99: VIPs (M)

- **Marking VIPs:** VIPs are marked in the people register (format and reader in `propose.py`).
- **The check:** a `sweep.py vip` subcommand holds the address list and the check, writes `vip.json`, and bypasses the matching and ignore rules.
- **Live server:** checks on a timer and has a notification route.
- **Today:** a VIP item always sits at the top of Needs attention.
- **Later:** this becomes a people label when BL-94 is built; keep the flag simple so it can migrate.

### 3. BL-98: Meeting prep, ranked brief and Prep page (L)

**Part 1, ranking:**
- **What changes:** the saved calendar keeps each meeting's invite **body, attendees and attachment names**. This rewrites the cx-sweep rule "never bodies", as BL-98 sets out; update that rule's wording in the skill and in `system/creaite-rules.md`. Private meetings stay "Busy", with no body.
- **The ranking:** `build_dashboard.prep` scores work items by relevance to the invite. The most relevant move to the top of each list, each with its reason ("invite mentions the cut-over"); the rest follow in today's order.

**Part 2, Prep page:**
- **The button:** a **Prep page** button in the Prep brief. In Ask creaite, "prep for the <meeting>" does the same.
- **What it does:** runs Claude through the run engine, as Generate current state does (BL-46), and builds one self-contained HTML page. It is saved in the project's Agendas folder (`paths.folder(code, "agendas")`, adding that key to `locations.folders` if needed) and opened in a new tab.
- **Build this last.** Writing into the project folder needs BL-93 from `sprint-permissions`. If that hasn't merged yet, have the **live server** write the file (it's the server's own write, not Claude's), or leave part 2 for after the merge and note it under Hand-offs.

## Boundaries

- **Owns:**
  - `system/scripts/sweep.py` and the cx-sweep skill;
  - `calendar.json`'s format;
  - in `build_dashboard.py`, `prep`, `prep_match` and the VIP data;
  - the people-register VIP column;
  - Settings › Sweep;
  - the Prep brief and dialog in `dashboard.html`.
- **Don't edit:**
  - **`sprint-permissions` owns:** `permissions.py`, `FS_RULES` and the allow lists in `live_server.py`, `.claude/settings.json`, the Ask creaite chat box, and the Chrome app and launcher.
  - **`sprint-pages` owns:** the Files page, the project page, `files()`, and the trends and flow code.

  Your new live-server routes (VIP notification, Prep page) go **at the end of the route map**, in a marked block. Note anything you need from the others under "Hand-offs".
- **Shared files** (`dashboard.html`, `build_dashboard.py`, `live_server.py`, `settings.json`, `help.md`, `dev/dashboard-spec.md`):
  - put new code in its own marked section, `/* ===== Sweep and alerts (BL-97, BL-99, BL-98) ===== */`;
  - add new data keys at the end of `collect()`'s dict;
  - add new settings keys in their own blocks;
  - don't reformat unrelated lines;
  - leave `BACKLOG.md` and `BRD.md` alone (updated at merge).
- **Help:** update `system/templates/help.md` (tasks and Reference), then run `python3 dev/tools/build_guides.py`; the guide test fails otherwise.
- **Development guard:** sample data only. Tests use fictional invites; never real Microsoft 365.

## Done when

**Tests:**
- the ignore rules at each point they apply, with the counts;
- the VIP check bypasses matching and ignore, and VIP items lead Today;
- the calendar keeps body, attendees and attachments but never a private meeting's;
- the ranking puts the relevant items first, with reasons;
- the Prep page route is refused without the live server, builds a self-contained file in Agendas, and Stop works.

The full suite passes: `python3 dev/tools/run_tests.py`.

**Docs:** the spec updated, and a short "Mail, calendar and alerts" section in `dev/BUILD.md`.

**Commits:** each item committed separately on `sprint-sweep-alerts`, with the attribution lines from the session's instructions. Never push or merge.

## Hand-offs

(Changes needed in files another sprint owns.)

- **sprint-permissions (BL-93, BL-96):**
  - `.claude/settings.json`: allow `Bash(python3 system/scripts/prep_page.py *)` (and the `python` form), so cx-prep runs from Claude Code without a prompt. `sweep.py *` is already allowed, which covers `sweep.py ignore` and `sweep.py vip`.
  - `permissions.py`: offer a narrow rule for the Agendas folder (`paths.folder_name("agendas")`) if Claude is ever to write prep pages itself. Today the **live server** writes them (BL-93 hadn't merged), so nothing is needed for the button.
  - The Ask creaite chat box: "prep for the <meeting>" could start the Prep page flow (`prepPage()` for the matched meeting) instead of the panel answering; until then cx-prep tells Alan to press **Prep page** in the brief.
  - `live_server.py`: the VIP check has its own read-only tool list (`VIP_TOOLS`, Microsoft 365 search tools only) and the Prep page run uses `READ_TOOLS` through `Run(kind="prep")`; both are in the marked "Sweep and alerts" block. `main()` gained one line starting the VIP timer.
- **sprint-pages (BL-87), confirmed by Alan 2026-10-08:** the Files page shows **Agendas** as its own group: `paths.folder(code, "agendas")` (`agendas/` in the default layout; `02 Meetings/Agendas` with projects in OneDrive, which already exists in his engagement template). Until then prep pages are reached from **Open last prep page**.
- **Merge notes:** `dev/tests/test_help.py`'s ⌘K test now counts the How-to tasks from the parsed Help rather than a fixed 18, so sprints adding tasks don't collide. `test_tracker.Vault` copies `prep_page.py`. `locations.folders.agendas` is `02 Meetings/Agendas` (confirmed by Alan, 2026-10-08).
