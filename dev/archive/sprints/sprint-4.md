# Sprint 4: Transcripts, the Work board, project names, and release v1.2.0 (in two parts: 4a now, 4b after the merges)

**Two parts (Alan, 2026-10-09: start what can run in parallel now).**

- **Sprint 4a.** Branch `sprint-4a`, worktree `../creaite-sprint4a`. **Starts now**, in parallel with `sprint-permissions`, `sprint-sweep-alerts` and `sprint-pages`, and touches none of their files. Its items are marked **[4a]** below:
  - item 1, without retiring the deny rules;
  - item 3, Clear day only;
  - item 4.

  **Merges after the three running sprints.**
- **Sprint 4b.** Branch `sprint-4b`, worktree `../creaite-sprint4b`. **Starts after `sprint-permissions`, `sprint-sweep-alerts`, `sprint-pages` and `sprint-4a` have merged**; Claude in the main checkout creates the worktree then. Its items are marked **[4b]**:
  - item 1's deny rules;
  - Ask creaite's full access (item 1b);
  - item 2;
  - item 3's highlight;
  - items 5, 5b and 6.

**Before starting either part,** read BL-42 (phase 3), BL-104, BL-103 and BL-101 in `dev/BACKLOG.md`, and `dev/reference/spike-transcripts-2026-10-08.md`. They hold Alan's decisions and the test results this design rests on.

**Sprint 4a's boundaries:**
- **Don't edit:**
  - **`sprint-permissions` owns:** `.claude/settings.json`, `permissions.py`, and `FS_RULES`, `READ_TOOLS` and the allow lists in `live_server.py`.
  - **`sprint-sweep-alerts` owns:** `sweep.py`, the cx-sweep skill, `calendar.json` and meeting prep.
  - **`sprint-pages` owns:** the Files page, the project page and `files()`.
- **Your own work:** the Work board goes in its own marked section of `dashboard.html`. Clear day goes in the Calendar Import section with its own marked block. New live-server routes go at the end of the route map, in a marked block.

## Goal

Alan picks this week's meetings in Calendar Import and their transcripts and chats load themselves, with creaite showing which have one. Work gets a board. Screens show project names, not codes. Release checks run on Linux and stop failing by chance. Everything since v1.1.0 ships as **v1.2.0**.

## Already built, ships with this release

**Per-project weekly report reminders** (on `main`, 89cf1ae):
- one "ABC weekly report for week ending … is due" per project still owed, each cleared when its report is filed;
- **Run** sends that project's command.

Nothing to build: check it still works after BL-101 changes the wording to project names.

## Items

Commit each separately, in this order.

### 1. Release hygiene (S) [4a; the deny rules 4b]

- **Release check on Linux:** `.github/workflows/release.yml` runs on `ubuntu-latest`, because GitHub's macOS runners failed to start twice for v1.1.0.
  - **Finding Chrome:** the browser tests find Chrome through one helper: `CREAITE_CHROME`, then `shutil.which("google-chrome", "chromium", "chromium-browser")`, then the macOS path. Today `test_dashboard.CHROME` hard-codes the macOS path, and `live_browser.py` and others import it.
  - **macOS-only checks:** any check that only makes sense on macOS (OneDrive placeholder flags, `open`) is skipped on Linux with a reason, never failed.
  - **Python:** the runner's default Python 3, so state the version in the workflow.
  - **Proof:** after merge, Claude in the main checkout runs the workflow once on a test tag (for example `v1.2.0-rc1`, marked pre-release and deleted afterwards). Sprint sessions never push. In the sprint, check that the workflow file is valid and that the suite passes with `CREAITE_CHROME` pointing at the Chrome binary.
- **Steadier Ask creaite tests:** `test_ask_creaite_stream_and_confirmation` and `test_stop_a_running_request` in `test_dashboard_editing.py` failed under load and passed alone. Wait for the state rather than a fixed time, as in `test_review_nesting.py`. Then run the suite four at a time, five times in a row, with no failure.
- **Retire the two noisy deny rules:**
  - remove `Write(.claude/settings.json)` and `Write(.claude/settings.local.json)` from `.claude/settings.json`. They warn on every run, and `Edit(…)` already covers all file edits;
  - give `update.py`'s permissions merge a **retired-rules list**, so an update removes them from existing vaults too. Retiring applies only to rules creaite itself shipped; Alan's own rules are never removed;
  - add a test.

### 1b. Ask creaite is the big boss: full read access, all the time [4b]

**Alan, 2026-10-09:** "I want Ask creaite to be the big boss… access to everything all the time."

- **Reading, always allowed** (no prompt):
  - every Microsoft 365 reading tool: calendar, mail search and read, Teams chats and channels, SharePoint and OneDrive search, `read_resource` (transcripts included), people;
  - every file in the vault and the projects root;
  - every creaite script's read commands.
- **Writing, still confirmed in the panel first** (the non-negotiable "approval before writes"):
  - tracker changes (apply and undo);
  - files in the vault and project folders;
  - drafts.

  The panel shows exactly what will change. Never a skip-permissions mode.
- **Microsoft 365 actions stay off** unless Alan decides otherwise: sending, deleting, or changing mail, calendar or Teams. They act outside the laptop and can't be undone.
- **Where it's recorded:** `system/creaite-rules.md` (Dashboard editing, the assistant).
- **Where it's built:** the allow lists in `live_server.py` and `.claude/settings.json`, with `permissions.py`'s checks updated so doctor doesn't flag these as too broad.
- **What changes for transcripts:** the transcript runs no longer need their own narrower list.

### 2. BL-42 phase 3: Loading transcripts (M–L) [4b]

The design comes from the live-vault test (`dev/reference/spike-transcripts-2026-10-08.md`). Follow it.

**The only route to a transcript, three calls:**
1. `outlook_calendar_search` finds the event;
2. `read_resource` on `calendar:///events/<id>` gives `onlineMeeting.joinUrl` and `meetingTranscriptUrl`;
3. `read_resource` on that `meeting-transcript:///…` URL **exactly as returned, with the occurrence's `start`/`end`** returns `transcripts[].content` as WebVTT.

SharePoint and OneDrive search are **not** a fallback.

**Checked by the daily sweep, not when Intake opens** (Alan's decision):
- **Which meetings:** for each meeting in the Calendar Import window, the sweep reads the event and records a status in `system/staging/transcripts.json`. The status is keyed by event ID and holds the transcript URI and the dates. It never holds the body, passcode, PIN or transcript text.
- **The statuses**, from the test:
  - **Transcript available:** at least one transcript for the occurrence;
  - **Not transcribed:** an online meeting in the past, the transcript URL present, and an empty list;
  - **No transcript:** no online meeting, or no transcript URL;
  - **No access:** a permission or not-found error for an online meeting in the past.
- **When it looks again:** only new meetings, and those still "Not transcribed" or unchecked today, because transcripts can appear hours later. "Check again" on a row runs one check.
- **Dropped connections:** retry once (the test saw a connection reset). The organiser comes from `isOrganizer`, never address matching.

**Loading, which a script does and Claude never re-types:**
- **The buttons:** Calendar Import gets **Load into inbox** and **Load and process**, through the run engine.
- **The file comes from the run itself:**
  - the live server takes the transcript from the run's **tool result** in the `stream-json` events;
  - if the result was spooled to a file by Claude Code, it reads that file;
  - it then writes `inbox/YYYY-MM-DD <Title>.vtt` itself.
  - **Claude never re-types a transcript.** Test with a stubbed stream carrying both an inline result and a spooled one.
- **Tidying the WebVTT:**
  - line endings made LF, and cues sorted by start time;
  - a `NOTE` header from the event: title, date, start time, organiser name, attendee names;
  - names kept as given;
  - `minutes.py transcript` must read it unchanged.
- **The chat:**
  - the chat ID is the `19:meeting_…@thread.v2` thread ID inside the join URL;
  - read `teams:///chats/<id>/messages`, keep only messages sent within the meeting's window, and read each one's full body;
  - leave out system events and join and leave messages;
  - write `inbox/YYYY-MM-DD <Title> - chat.txt`.
- **Never processed twice:** the event ID travels with both files, so the meeting is `calendar:<id>` in `processed.txt`.
- **Permissions:** the Microsoft 365 tools the transcript runs need (`outlook_calendar_search`, `read_resource`, `teams_list_chats`, `chat_message_search`) are passed with `--allowedTools` **only to the transcript-check and load runs**, not to Ask creaite in general.
  - **Decided by Alan (2026-10-09):** Ask creaite has full read access, item 1b, so the transcript runs use the same allow list. There is no special case for them.
- **Help and the cx-minutes and cx-sweep skills:** describe the route, the statuses and the files.

### 3. BL-104: Highlight meetings with transcripts; Clear day (S–M) [Clear day 4a; highlight 4b]

As BL-104 sets out:
- **Highlight:** rows whose transcript exists and isn't processed get a tint, an accent bar and a **Transcript** badge, with a "With transcripts" chip.
- **Clear day:** a button on each day's heading, remembered in `system/staging/intake-cleared.json`.
  - Cleared is not processed: nothing is written to `processed.txt` or the tracker.
  - A safeguard asks first when unprocessed transcripts would be cleared.
  - Undo, the "Cleared (n)" list with Restore, and per-meeting ×. The per-meeting × is assumed; take it.

### 4. BL-103: The Work board (M) [4a]

As BL-103 sets out:
- **Layout:** a List | Board toggle for each tab (Actions, RAID), sharing filters, search, saved views and sort.
- **Grouping:** Due, Status, Owner and Milestone, with the defaults given.
- **Moving a card:** drag, or "Move to…", saves through the same path as a cell edit. A due date is asked for, and Overdue is not a drop target.
- **Cards, columns, keyboard and themes:** as specified.
- **Not built:** the Decisions board waits for BL-53. Swimlanes and hand-ordering are out.
- **Reuse the Work row code** (`rows()`, `passes()`); don't fork it.

### 5. BL-101: Project names everywhere, codes only in item IDs (M) [4b]

As BL-101 sets out, across the dashboard, the reminders (the per-project weekly ones included), the warnings, the Word reports and drafts, and the guides. Do it **last**, because it touches text on every screen built above.

### 5b. "ask creaite" [4b]

The lower-case pass (BL-105) moved to Sprint 5, which merges last (Alan, 2026-10-09). Here, write any **new** text as "ask creaite", lower case, and leave existing text for Sprint 5.

### 6. Release v1.2.0 [4b]

- **The basics:** `VERSION` set to 1.2.0, `dev/release-notes/1.2.0.md` written for Alan (what's new since 1.1.0, from Sprints 1 to 4), and the guides regenerated.
- **Leave publishing to Claude in the main checkout** after merge, using `gh`.

## Boundaries

- **May touch any file:** nothing else is running when this sprint starts. Put new code in marked sections, and don't reformat unrelated lines.
  - **Update (09-10-2026): debug log part 2, stage A runs beside this sprint** (`debug-log-2.md`). It keeps to its own marked blocks and one-line additions, and doesn't touch `READ_TOOLS`, `DENY_TOOLS` or the assistant prompt. Keep your new code in marked blocks too, and whoever merges second brings `main` in first.
- **Development guard:**
  - sample data only;
  - Microsoft 365 is **never** called from this repo or its tests;
  - transcript runs are tested with a stubbed `claude` whose stream carries fixture tool results built from the shapes in the test note, with fictional meetings;
  - the real check happens in Alan's live vault after release.
- **Docs:** leave `BACKLOG.md` and `BRD.md` alone; they are updated at merge.

## Done when

**Tests:**
- the release workflow green on Linux (one rc run);
- the Ask creaite tests stable (five parallel runs);
- deny rules retired on update, with Alan's own rules kept;
- the transcript statuses from fixture events;
- the URL with `start`/`end`;
- the file written from the tool result, both inline and spooled, byte-for-byte, then tidied;
- the chat filtered to the meeting window;
- the event ID carried, and nothing processed twice;
- Ask creaite's full read access, with writes still confirmed and Microsoft 365 send, delete and change actions still refused;
- BL-104's highlight, Clear day, Undo, Restore and safeguard;
- BL-103's board for each grouping, with real drag events, the date prompt, the Overdue refusal, Undo and shared filters;
- BL-101's names everywhere, with codes only in IDs;
- the full suite: `python3 dev/tools/run_tests.py`.

**Docs:** Help (then `build_guides.py`), the spec, and a "Sprint 4" section in `dev/BUILD.md`.

**Commits:** each item committed separately on `sprint-4`, with the attribution lines from the session's instructions. Never push or merge.

## Hand-offs

(Anything for Alan to decide or do.)
