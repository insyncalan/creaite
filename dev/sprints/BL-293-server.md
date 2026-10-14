# BL-293 — Today: move between the calendar's days: the server side (sprint-today-days-server)

The Python and live-server work behind the day line. The dashboard (`system/templates/dashboard/`, `dashboard.html`) is not
touched here; the screens sprint builds on the data and routes below. Built on `sprint-prep-server` (BL-286). No schema change.

## What changed

- **The saved calendar's span:** `sweep.calendar_span(today=None)` → `(first, last)` dates, or `None` without a
  `calendar.json`. It is `calendar_window()` (Monday of this week, or `inbox.meetings_from`, to seven days ahead), with the
  last day cut to the fetch date + 7 when the calendar was saved on an earlier day. `calendar_window` takes an optional
  `today` too.
- **Prep on any day the saved calendar holds** (`prep_page.py`):
  - `context(key)` accepts today and any later day up to the span's last day. Refusals, as Alan reads them:
    - a past day: "That meeting was on 12-10-2026, which has passed: prep is for today and the days ahead."
    - beyond the span: "21-10-2026 is beyond the saved calendar, which runs to 20-10-2026; refresh the calendar."
    - no calendar: "There is no saved calendar yet; refresh the calendar."
    - in the span but gone: "That meeting isn't in the saved calendar for 16-10-2026 any more; refresh the calendar."
      This replaces "…isn't in today's or tomorrow's calendar…" (the pinned expectation was re-recorded; `abc_weekly` is
      unchanged).
  - A dated key for today (`2026-10-13|14:00|title`) is read as the Prep brief's undated one (`brief_key`), so saved
    pages and the focus keep matching.
  - `meeting_entry(d, key)`: the Prep brief record. Today's and tomorrow's come from the dashboard data as before; a
    later day's is worked out on demand (`build_dashboard.prep_entry`, split out of `prep()`) and cached in that `d`.
    `prep_view` (brief, view, `page_for`), `prep_shape.chips` and `drafts._shape_context` look meetings up through it, so
    every BL-286 route works for a meeting three days out.
  - **`D.prep.meetings` is unchanged** (today and tomorrow only), so the Week ahead's Prep links don't change.
  - The live server's Prep page run (`/api/prep/page`) has no day check of its own: it calls `prep_page.context`, so it
    refuses and allows exactly as above. cx-prep's skill text and the rules' cx-prep line no longer say "today or tomorrow".
  - BL-98's rules unchanged: read-only research, the page is the server's own write (`prep_page.save`), a page Alan
    edited is never overwritten (it gets a number), pages are Internal.
- **The day data:** `build_dashboard.calendar_days(d, now)`, in `/api/data` as **`D.days`** and from the route below.
- **Week ahead:** `plan_reason`'s project counts moved into `hot_projects()`; no change in output.

## Route

`POST /api/today/days {day?}` (local, token-checked, read only; Claude never runs). Without `day`, every day; with `day`
(`YYYY-MM-DD`), just that one (`days` is `[]` when it isn't in the span). A bad `day` is a 400. Debug log (`prep` area):
`days: 8 day(s), 12 meeting(s)`, counts only.

Response (and `D.days`): `{ok, first, last, today, fetched, days: [day]}`; `first`/`last` are `null` and `days` `[]` without
a saved calendar.

### Shapes

- **Day:** `{date, date_shown (DD-MM-YYYY), dow ("Tuesday"), short ("Tue 13"), long ("Tuesday 13th October", the year added
  when it isn't this year), today, past, weekend, week (0 this week, 1 next week…: put "Next week" before the first
  day with week 1), meetings: [meeting] (by start), all_day: [title]}`. Every weekday from `first` to `last`, with or
  without meetings; a weekend day only when it has a timed meeting.
- **Meeting:** `{start, end, title, private, confidential, ended}` always (`ended`: a past day, or today by the clock).
  - **Private:** only those, with the title "Busy".
  - **Confidential:** those plus `id`, `prep` and `plan: null` (no where, Teams, organiser or project).
  - **Otherwise also:** `id` (calendar event ID or null), `where`, `teams`, `p` (code, for links and filters only),
    `how`, `project_name` (shown: the project's name, "Portfolio", or null), and:
  - **`follow`** (ended meetings):
    - `{state: "minutes", processed, processed_shown, draft, minutes, cleared}`: processed (processed.txt), a draft
      waiting in Review (`draft: true`), or minutes filed for that day and series (`minutes`: vault path);
    - `{state: "transcript", process: {id, loaded, day, start, title}, cleared}`: loaded into inbox/ (`loaded`: its
      path) or found by the sweep (transcripts.json `available`);
    - `{state: "none", why, checked, cleared}`: `why` is the sweep's status ("No transcript for this meeting", "Not
      transcribed yet", "No access to the transcript"), "Not a Teams meeting, so there is no transcript", "Not checked
      yet" (`checked: false`), or "No calendar ID: refresh the calendar" (`checked: false`).
    - `cleared: true` when it was set aside in Calendar Import (Clear day).
  - **`prep`** (today and later): `{key, page, page_at, page_at_shown, stored}`. `key` is the Prep brief's (undated
    today); `page` is the newest prep page creaite wrote for the meeting that is still there (prep-pages.json), for
    BL-287's Open icon; `stored` says BL-286 kept its content (Meetings › Prep can show it without a run).
  - **`plan`** (today and later): the Week ahead's reason it is worth preparing for, or null. Non-null means **Prepare**.

## What the screens sprint calls

1. **The day line:** `D.days.days` on first paint (no request); after a reload, `/api/data` brings it again.
   `/api/today/days` is there for a refresh of the band alone (for example after a transcript check or a Prep page run)
   without reloading everything.
2. **A past day's meeting:** show `follow.state`. **Process** = Calendar Import's flow for `follow.process.id`:
   `/api/transcripts/load {id}` unless `loaded`, then `process <loaded>` through ask creaite (as `processMeetings`).
   A row for it is also in `D.meetings.rows` by `id`. "Not checked yet" may offer Check (`/api/transcripts/check {id}`).
3. **Today and later:** the pill opens the Prep popup with `prep.key`. Every BL-286 route takes that key for any day in
   the span (`/api/prep/brief`, `/chips`, `/shape`, `/filter`, `/focus*`, `/view`); **Prep page** is
   `/api/prep/page {key}` then `/api/prep/build {run}` as before; on a refusal show `message`. **Open** =
   `/api/prep/open {path: prep.page}`.
4. **Labels:** `openPrep`'s "Today"/"Tomorrow" becomes the day's `long`. `prepKey(e, day)` already builds the dated key
   for any day other than today; it matches `prep.key`.
5. **Headline:** `dayShape` stays the dashboard's; nothing server-side was needed.

## Tests

`dev/tests/test_today_days.py` (quick tier): prep allowed or refused by day (past, today, a dated today key, three days
out, beyond the span, a calendar saved days ago, no calendar, the CLI); a prep page made for Friday's meeting, listed on its
day, and a second build keeping Alan's edited page; the day data over a fixture calendar from Monday to next Tuesday with a
Saturday (all-day only, left out) and a Sunday meeting (kept); each follow-up state; confidential and private meetings;
`D.prep.meetings` unchanged; the route (all days, one day, a bad day, the log line) and `/api/prep/page`'s refusal and a
build three days out.

## Questions for Alan

1. A **confidential** meeting shows only its title and times, so it has no project and no Prepare (even when Alan
   organises it). It still has a Prep pill and, when it has ended, its follow-up state. Right?
2. A past meeting the sweep **hasn't checked** for a transcript yet is `none` with "Not checked yet". Should the day line
   say "No transcript" there, or offer Check?
3. Draft minutes **waiting in Review** count as **Minutes made**. Or a separate "Draft in Review"?
4. The day line ends at the **fetch date + 7** when the calendar is older than today (so it never offers a day the
   calendar may not hold). Fine, or always seven days from today?
