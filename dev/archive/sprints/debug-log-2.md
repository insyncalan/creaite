# Sprint: Debug log, part 2 (BL-102)

Branch `sprint-debug-log-2`, worktree `../creaite-debug-log-2`, made from the tip of `main` when it starts. Read BL-102 in `dev/BACKLOG.md` and `dev/archive/sprints/debug-log.md` (part 1) first; they hold Alan's decisions. Part 1 is merged: `system/scripts/log.py`, the `logging` setting, `paths.LOGS`, the `doctor.py` check and the session-start status line. **Nothing writes to the log yet** except `doctor.py`: this sprint wires it in.

## Stage B: set up (09-10-2026) — three items

Stage A merged (`242e15c`). Stage B runs on branch `sprint-debug-log-2b`, worktree `../creaite-debug-log-2b`, made from `main` after Sprint 4b, chat-sweep, backup-folder, Sprint 5 and recode merged. Alan (09-10-2026) added two more items, both in files this sprint already touches, so the sprint carries **three items**, each committed separately:

1. **BL-102 stage B: the debug log's calls inside the scripts, the rules text and Help.** B1 and B2 below, with A4 (the panel reads `system/logs/` and is refused a write there) in the tests. Don't re-wrap what stage A wrapped (`session.py`, `build_dashboard.py`, `doctor.py` and the other entry points use `log.main`): add the calls **inside** the scripts at the points listed. Keep `import log as debuglog`, guarded so a script still runs if `log.py` is missing. Recode's code (`recode_project`, `rewrite_project`) logs one line: the old and new code and the row counts, nothing else.
2. **BL-113: meeting prep and the sweep learn decisions needed** (Sprint 5's hand-offs). Read BL-113 and BL-53 in `dev/BACKLOG.md` and the hand-offs in `dev/archive/sprints/sprint-5.md`.
   - **Prep (BL-49, BL-98):** a meeting's prep brief and its Prep page list the project's **pending decisions** (`status` Pending, who is asked, the needed-by date) and the **made decisions whose revisit date has come** (`revisit` as a YYYY-MM-DD date; a revisit written in words has no date and is not listed). In `build_dashboard.py` (the prep data) and `dashboard.html` (the prep brief); the Prep page prompt gets the same two lists.
   - **`sweep.py stage`:** stop defaulting `date` for a pending decision (today it runs `v.setdefault("date", …)` for every new decision, around line 207), and support `op: update` on a pending decision, as `minutes.py` does, so a message that makes a pending decision updates it instead of leaving a note. The cx-sweep skill drops its `"date": ""` workaround.
   - **Tests:** extend `test_sweep_alerts.py`, `test_decisions_sprint5.py` and `test_decisions_dashboard.py` (or a new file): prep lists both kinds and omits a withdrawn or made-without-revisit decision; a staged pending decision keeps its empty date; a sweep that makes a pending decision updates it and the apply fills the date.
3. **BL-103's Decisions board.** The Work board (sprint-4a, FR-89) covers Actions and RAID; Decisions stay a list until now. Read BL-103 in the backlog and the Work board section of `dev/dashboard-spec.md`.
   - **Board for Decisions:** the **List | Board** switch appears on the Decisions tab. The columns group by **Status** (Pending, Made, Withdrawn; the default, setting `work.board.group`, already names Decisions by Status) or **Owner** (the person asked, `made_by`), **Due** (the needed-by date, `due`; a made decision has none, so it sits under No date) and **Milestone**, with the same filters, search, chips, saved views and sort as the list. Cards show the title, the ID, the project, who is asked, the needed-by date in words ("3 days late" in red) and the status.
   - **Dragging:** to **Made** opens the Record-the-decision form (the date made, today, filled in; the same record and number), never a silent status change; to **Withdrawn** asks for confirmation (and a reason if the form has one); a Made decision is not dragged back to Pending (offer nothing, refuse with the message); to an **Owner** column sets who is asked; to a **Due** column asks for a needed-by date (never a past one; only a Pending decision has one). Each move is one change, saved as the panel saves, with **Undo**; **Move to…** does the same without dragging. A refusal shows its message and returns the card.
   - **Not in this item:** swimlanes, hand-ordering, a work-in-progress limit.
   - **Tests:** a new `test_decisions_board.py` (real drag events through `dev/tools/cdp.py`): the switch, each grouping, the Made form on drop, Withdrawn confirmation, the refusals, Undo, shared filters, both themes.

**Owns (others must not edit):** the log calls in `tracker.py`, `excel_sync.py`, `sweep.py`, `minutes.py`, `review.py` and `report.py`; the prep blocks of `build_dashboard.py` and `dashboard.html`; the Decisions parts of the Work board code in `dashboard.html`; the cx-sweep skill; `system/creaite-rules.md` (folder map, Retention) and `help.md`. `sprint-exec-state` works in the Current state code of `dashboard.html` and in new files: keep to marked blocks and bring `main` in before merging.

**Done when:** each item's tests, the stage B list below, the full suite (the bar is two clean runs, Alan 09-10-2026; run when no other session is running tests), a section in `dev/BUILD.md` per item, FR-98 extended in the BRD, new FRs for items 2 and 3, `dev/dashboard-spec.md` (the Decisions board; the "Not built" line removed), `help.md` and the guides (`python3 dev/tools/build_guides.py`), and the board updated. Never push or merge.

## Goal

Every script run, every live-server request and run, and every error the dashboard hits leaves a line in the log, with nothing from mail, minutes, notes or chats in it. Alan and Claude can read the log, and Settings › Diagnostics shows the latest errors and copies a report to paste into a chat.

## When it can start: now, beside sprint 4b (Alan, 2026-10-09)

Stage A runs **beside `sprint-4b`**, which is changing `live_server.py`, `dashboard.html`, `build_dashboard.py`, `update.py`, `sweep.py` and `minutes.py`. Two sprints in the same files stays safe only if this one keeps to the rules below. Stage B waits.

- **Stage A: scripts, the live server and the dashboard.** Starts now, from the tip of `main`.
- **Stage B: the files Sprint 5 owns** (`tracker.py`, `excel_sync.py`, `minutes.py`, `review.py`, `report.py`), plus `sweep.py`, the rules text and Help (which 4b and Sprint 5 are editing). Starts when **Sprint 5 and 4b have merged**.

**Rules for working beside 4b** (4b's own brief says it may touch any file, because nothing else was running when it was written; `sprint-4.md` now points here):
1. **Everything new goes in its own marked block** (`# ===== Debug log (BL-102) =====` in Python, `/* ===== Debug log (BL-102) ===== */` in `dashboard.html`), at the end of a file or section, never in the middle of 4b's code.
2. **Where a call has to sit inside existing code, it is one added line** that doesn't move or reformat its neighbours. Before adding a line to a function, check what 4b has done to it: `git -C ../creaite-sprint4b diff main...HEAD -- <file>`. Where 4b has rewritten the function, use a wrapper in the debug-log block instead (for example, wrap the handler's request method at the end of the file) and leave the function alone.
3. **The entry-point wrappers (A1) are one-line changes at the bottom of each file**, so they merge cleanly even in files 4b is editing.
4. **Don't touch `READ_TOOLS`, `DENY_TOOLS` or the assistant prompt:** 4b is rewriting them (Ask creaite reads everything). A4 is therefore a check after 4b merges, not a change.
5. **No Help, no rules text, no BRD or BACKLOG edits** in stage A: they are updated at merge, or in stage B.
6. **Whoever merges second brings `main` in first** and re-runs the full suite.
7. **Merge order:** whichever of 4b and stage A finishes first merges first.

## Alan's decisions (BL-102, 2026-10-09)

Unchanged from part 1 (one file a day, the last seven days, one line per entry, `logging.level`, a size cap, a write never raises). Added here:

- **Never in the log:** the text of mail, Teams messages, transcripts, minutes or invites; pasted images or notes; Ask creaite chat text; Current state; client names beyond the project name. Item IDs, file paths, project names, counts, durations and exit codes are fine.
- **Ask creaite and Claude Code can read the log** (read only). **Settings › Diagnostics** shows the last errors, opens the log folder, switches the level, and has **Copy diagnostics**.

## Items

Commit each separately. Stage A first.

### Stage A

#### A1. Script runs
Wrap each entry point in `log.main(...)`, **imported as `debuglog`** (`import log as debuglog`): `permissions.py`, `filechange.py` and `tracker.py` already have a function called `log`, and importing the helper under that name replaces it. `with log.run(<script>, <command>):` (the last lines of the file, `sys.exit(main(sys.argv[1:]))`, become `with log.run(...): code = main(...)` then `sys.exit(code)`; keep the exit code). The command is the sub-command and flag names only, **never their values** (a file name or a note is a value). Scripts: `update.py`, `prep_page.py`, `filechange.py`, `permissions.py`, `launch.py`, `locations.py`, `search.py`, `build_dashboard.py`, `session.py`, `doctor.py`, `live_server.py`'s `main`. (`tracker.py`, `excel_sync.py`, `minutes.py`, `review.py`, `report.py` and `sweep.py` are stage B.)

#### A2. The live server
In `live_server.py`, in a marked block (`# ===== Debug log (BL-102) =====`):
- **Start and stop** (port, version), and every error the handler catches (with a traceback).
- **Each request:** route, HTTP status and milliseconds. **Never the body, a query value, a file name from a request or a header.** `log_message` is replaced by this, still quiet on the console; health checks (`/health`) and the "still here" route are logged only at debug level.
- **Ask creaite, Generate, search and Intake runs:** started (run ID, kind), stopped, ended (how long), the names of the tools it used, any permission denial or `PERMISSION:` request (the rule, not the reason text), and timeouts. **Never the message, the prompt, the reply or the context.**
- **Apply, undo and review calls:** the route and the result (ok or the failure's one-line reason as the script returns it, with item IDs), the proposal file name.
- **The browser error route** `POST /api/log/error` (token-checked like the others): `{message, view, source, line}`, each cut at 300 characters, at most 20 per minute (extra ones are counted in one line), logged as `dashboard` errors. It never accepts element text or state.

#### A3. The dashboard
- **The error hook** (`window.onerror` and `unhandledrejection`) posts to that route (and does nothing if the live server isn't running).
- **Settings › Diagnostics** (a card in Settings, in its own marked section): the last 10 errors (time, area, message; the traceback opens under a click); **Open the log folder** (the existing open route; `system/logs` joins `OPEN_OK`); a **Log level** switch (info or debug) that writes `logging.level` through the Settings writer, as every other setting; and **Copy diagnostics**.
- **Copy diagnostics** builds one plain-text report: creaite version and the date; the `doctor.py` results; the settings **from an allow-list of safe keys** (levels, switches, counts and intervals; not a deny-list, so a new private setting is hidden by default); and the last 200 log lines. **Removed:** identity (name, short forms, own domains), the people register, the sweep ignore rules, the OneDrive path and any value that looks like an email address. It goes to the clipboard, never to a server.
- **A line in the status** area only when there are errors in the last 24 hours (as `session.py` does), linking to Diagnostics.

#### A4. Ask creaite and Claude Code can read it: a check, after 4b merges
4b makes Ask creaite read every vault file and script read command, so `system/logs/` is covered without a new rule. After 4b has merged, confirm it (a test asks the panel's tool list to read `system/logs/debug-*.log`), and make sure **writing** to `system/logs/` stays refused. If 4b leaves a gap, add one narrow read rule through `permissions.py`. Until then nothing changes here.

### Stage B

#### B1. Calls inside the scripts
Short entries at the points that matter, each following the privacy list above:
- `tracker.py`: apply and undo (proposal files, counts per table, each validation failure as the rule and item ID, the backup taken, the result); `excel_sync.py`: export and import (sheet counts).
- `sweep.py`: the window, counts searched, proposed and skipped and **why** (the ignore rule's name, "already proposed"), each Microsoft 365 call with its result or error, the calendar save and the time zone conversion's result. **Never subjects, senders or bodies.**
- `minutes.py`: stage, refresh and file steps (counts, the meeting key, skipped reasons); `review.py`: decisions made (counts, item IDs); `report.py`: stages and files written (paths).
- `session.py`: the daily backup and the off-laptop copy; `build_dashboard.py`: build time and counts.

#### B2. Rules text and Help
`system/creaite-rules.md`: the folder map gains `system/logs/`, and Retention says the log is the one thing pruned (seven days), beside the Ask creaite chats. `system/templates/help.md`: a short "If something goes wrong" entry for Diagnostics. `dev/BRD.md`: FR-98 is extended to the full requirement.

## Boundaries

- **Stage A owns:** the entry points of the scripts listed in A1; the debug-log blocks in `live_server.py`, `dashboard.html` and `build_dashboard.py`; the Diagnostics tests. Beside 4b: only the rules above.
- **Stage B owns:** the calls in `tracker.py`, `excel_sync.py`, `sweep.py`, `minutes.py`, `review.py`, `report.py`, and the rules and Help text.
- **Don't edit** what another running sprint owns (see `dev/archive/sprints/STATUS.md`).
- **Shared files:** put new code in its own marked block; add lines, never reformat or move existing ones, so the merge stays readable. Leave `BACKLOG.md` alone (updated at merge).
- **Development guard:** sample data and temporary vaults only; never connect to Microsoft 365.

## Done when

**Tests** (temporary vaults, fixed clock, in `dev/tests/test_debug_log.py` and a new `test_debug_log_wiring.py`):
- each script in A1 writes a start and an end line, an error in it writes a traceback, and its exit code is unchanged;
- the live server logs a request's route, status and time, a run's start and end, a permission denial, and an error, and logs **nothing from a request body**;
- **canary test (the main one):** run the sweep, minutes, Ask creaite, Quick capture and Intake paths with distinctive strings (`CANARY-MAIL`, `CANARY-NOTE`, `CANARY-CHAT`, `CANARY-TRANSCRIPT`, a client name) in every kind of input, then assert none of them is anywhere in `system/logs/` or in the Copy diagnostics report;
- the browser error route accepts a short report, cuts long text, ignores the 21st in a minute (with one summary line) and needs the token;
- Diagnostics lists the last errors, switches the level in `settings.json`, and Copy diagnostics holds the version, doctor results, safe settings and the last 200 lines and **none** of the removed settings (identity, people, ignore rules, the OneDrive path, an email address);
- (after 4b merges) the headless panel can read `system/logs/` and is refused a write there;
- stage B: apply, sweep, minutes, review and report write their entries, with item IDs and counts and nothing else.

The full suite passes: `python3 dev/tools/run_tests.py` (run it when no other session is running tests: the browser tests drop their connection when the machine is busy).

**Docs:** a "Debug log, part 2" section in `dev/BUILD.md`, `dev/dashboard-spec.md` (Diagnostics), Help, and the rules text.

**Commits:** each item committed separately on `sprint-debug-log-2`, with the attribution lines from the session's instructions. Never push or merge.

## Hand-offs

(Changes needed in files another sprint owns.)
