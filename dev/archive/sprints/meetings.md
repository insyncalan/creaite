# Sprint: Meetings in the Inbox (BL-42 phase 2)

Branch `sprint-meetings`, worktree `../creaite-meetings`. Runs in parallel with `sprint-prep-updates` (BL-65) and `sprint-person-rows` (BL-68). Read BL-42 in `dev/BACKLOG.md` first; it holds Alan's decisions, including those for phase 3.

**Merge order:** this sprint merges second, after `sprint-prep-updates` and before `sprint-person-rows`.

## Goal

The Inbox page lists this week's meetings from Alan's calendar, above the files. He can see which were Teams meetings, which are already processed and which project each belongs to, and send the ones he picks to cx-minutes. Phase 3 (transcript checks and loading) comes later, in the live vault, and this sprint leaves room for it.

## What phase 3 will add (don't build it; leave room)

- The sweep checks each meeting for a transcript and saves the answer.
- A per-row indicator: *Transcript available*, *No transcript*, *Not transcribed*, *No access*, *Already processed*.
- "Check again", "Select with transcripts", Load into inbox, Load and process.
- **Attendance doesn't matter:** a readable transcript can be loaded whether or not Alan attended.

Phase 3 needs a spike in the live vault first, and the development guard bars real Microsoft 365 data here.

## Items

Commit each separately.

### 1. The saved calendar covers the week, with event IDs

- **`sweep.py calendar`** keeps:
  - past days back to Monday of the current week. The window starts at `inbox.meetings_from`, default `"monday"`; it could also be a number of days;
  - each meeting's calendar event ID (`id`);
  - `teams` (true or false, from the event's online-meeting flag, not the "where" text);
  - `organiser` (true, as now, or the organiser's display name when Alan isn't the organiser).
- **What it still never keeps:** attendees, message text, join links or bodies. Private meetings stay "Busy", with their ID kept so they can still be selected.
- **The skill:** the cx-sweep `SKILL.md` instructions for building the calendar spec change to match.
- **Older calendars:** `calendar.json` from before this change still loads, without IDs (rows then can't be ticked; "Refresh" fixes it).

### 2. Processed state per meeting

- **The data:** `build_dashboard.py` adds `meetings` to the page data: each meeting in the window, with day, start and end, title, Teams, organiser, private, ID, likely project and whether it's processed.
  - The likely project comes from the same matching as meeting prep (`prep_match`, with `prep.series`).
  - Processed means the `processed.txt` key `calendar:<id>`, via `minutes.meeting_key` and `processed_on`.
- **What it doesn't do:** read files or call Microsoft 365.

### 3. The Meetings section on the Inbox page

- **Where:** above the file list. Rows are grouped by day (DD-MM-YYYY), newest day first.
- **Each row:**
  - a tick box;
  - time;
  - title;
  - a Teams icon or "In person";
  - organiser;
  - likely project, changeable from a menu, remembered for the meeting's series as meeting prep does;
  - state: *Already processed* with its date, or *Not processed*;
  - a transcript column showing "Checked in the live vault" (a placeholder until phase 3).
- **"Select new":** ticks unprocessed meetings that aren't private. Private ones can be ticked by hand.
- **"Process selected":**
  - runs cx-minutes as "process <meeting>" with the meeting's date, title and event ID, through the run engine, one meeting after another. This is today's route, in which cx-minutes fetches the transcript itself;
  - each row shows its progress and then its result (Draft ready, or the reason it couldn't);
  - needs the live server, and is held while Ask creaite is busy.
- **"Refresh":** asks Ask creaite to "refresh calendar" (cx-sweep's existing command), then reloads the data.
- **Empty and stale states:**
  - "No calendar yet: it comes in with the sweep";
  - "Calendar read DD-MM-YYYY HH:MM", with Refresh.
- **⌘K:** "Inbox: process meeting <title>" for unprocessed meetings.

## Boundaries

- **Owns:**
  - `sweep.py` (`calendar`) and the cx-sweep skill's calendar section;
  - `build_dashboard.py`: the `meetings` data, appended at the end of `collect()`'s dict;
  - the Inbox view's Meetings section in `dashboard.html`;
  - Inbox routes in `live_server.py`, only if one is needed (avoid a new route if the run engine's existing `/api/ask` does the job);
  - `settings.json`: a new `inbox` block.
- **Don't edit:**
  - **`sprint-prep-updates` owns:** `minutes.py` stage and update logic, `review.py`, Review rendering, and the cx-minutes skill. Read `meeting_key` and `processed_on`; don't change them.
  - **`sprint-person-rows` owns:** Work's row code (`rows()`, `cell()`, `orderedCols()`) and the person page.

  Note anything needed there under "Hand-offs".
- **Shared files** (`dashboard.html`, `build_dashboard.py`, `help.md`, `dev/dashboard-spec.md`):
  - put new code in its own marked section, `/* ===== Meetings in the Inbox (BL-42 phase 2) ===== */`;
  - don't reorder lines;
  - leave `BACKLOG.md` and `BRD.md` alone: they are updated at merge.
- **Development guard:** sample calendar only (`dev/tools/demo_data.py` may add a sample week with IDs); no real Microsoft 365 data; tests use temporary vaults.

## Done when

**Tests (new `dev/tests/test_meetings.py`):**
- the calendar keeps past days back to Monday, IDs and Teams, and never attendees or bodies;
- private meetings are "Busy" with an ID;
- an old calendar without IDs still loads;
- the processed state comes from `processed.txt` by event ID;
- the likely project and its remembered series;
- in headless Chrome: the Meetings section, Select new, Process selected sends the right "process <meeting>" requests one by one (with a stubbed run engine, as the Inbox tests do), and Refresh.

The full suite passes: `python3 dev/tools/run_tests.py`.

**Docs:** Help and `dev/dashboard-spec.md` updated, and a short "Meetings in the Inbox" section added to `dev/BUILD.md`.

**Commits:** each item committed separately on `sprint-meetings`, with the attribution lines from the session's instructions. Never push or merge.

## Hand-offs

(Changes needed in files another sprint owns.)

- **cx-minutes skill (sprint-prep-updates):** "Process selected" asks for `process the meeting "<title>" on DD-MM-YYYY at HH:MM (calendar event ID <id>[, project ABC])`. The skill's "process <meeting>" mode should use a given calendar event ID: find the meeting by it, and pass it on (`minutes.py key --event-id <id>`, `"event_id"` in `meeting.json`), so the processed key is `calendar:<id>` and the Inbox row shows "Already processed" after approval. A given project is a strong hint, not a reason to skip matching. Without that, a processed meeting still shows "Draft ready" (by its proposal) until the next sweep.
- **`dev/tools/demo_data.py` (paused sprint-live-vault):** a sample week in `calendar.json` with IDs would let the demo show the Meetings section; not added here.
