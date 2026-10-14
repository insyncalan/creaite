# Design brief: a project as of any day (BL-203)

**Status:** design brief, not scheduled (low priority). Mockup: `dev/mockups/asof-mockup.html` (open it from the file system; fictional Falcon Data Platform data, today 12-10-2026). When it is built: branch `sprint-asof`, from the tip of `main`, with the UX baseline (BL-157) checked before it is called done.

## Goal

On the project page, Alan picks a day and sees the project as it stood then, and sees what changed between two days. For steering prep ("what changed since the last steering?") and for explaining why health moved. Read only.

## The screens

1. **As of control** at the top of the project page: a date field that takes words ("last Friday", "3 weeks ago", 01-10-2026; BL-147), quick stops (Last steering, Last Friday, Start of the month, 30 days ago, Today) and a slider from the first day on record to today, with the tracker's start day marked.
2. **The page on that day:** a banner ("Showing the project as it stood on Thursday 8th October (08-10-2026). Read only.", with **What changed since then** and **Back to today**); health from that week's update, or the last known value between weeks; five counts (open actions, open risks and issues, overdue, decisions made, decisions pending), each with today's figure and the difference; the open items with owner and due date as they were (today's due date beside a moved one); milestone forecasts then and today; decisions made and pending.
3. **What changed:** From and To (words or dates) and "Since last steering / last Friday / start of the month / 30 days ago". A summary line (health A → B, Go-live moved +21 days, n raised, n closed, n dates moved, n decided), then every event by day, newest first: raised, closed, due date moved, owner changed, forecast moved, health changed, decided. Each ID opens the item's peek.
4. **Honest limits:** a day before the tracker starts shows "Not recorded: the tracker starts 14-09-2026 for this project", with a button to show the first day. A field the log can't rebuild says "not recorded", never a guess. An undone apply never happened.

## In

- The project page only; one project at a time.
- Rebuilt on demand from `change_log` and `updates` (the last change on or before the day, else the old value of the first change after it), the way BL-91's overdue-over-time already works. No snapshots.
- `GET /api/asof?project=&date=` and `GET /api/changes?project=&from=&to=` on the live server, read only.
- Internal only: no report, one-pager, export or ask creaite answer reads it.

## Out

- A portfolio version (BL-02) and "Compare with the last steering" in the Prep page: later.
- Editing anything while viewing a past day. Items open in the peek as they are today.
- Rebuilding text fields (descriptions, updates, current state) as they were: only the fields listed above.
- Days before the tracker started, and dashboard history snapshots.

## Questions for Alan

1. **Last steering:** take it from the latest filed minutes with "steering" in the title (recommended), the calendar, or a project setting?
2. **Slider or not:** is the date field with the stops enough, or do you want the slider too? It is the costliest piece to make keyboard-friendly.
3. **Opening an item from a past day:** the peek shows the item today (recommended, simpler). Do you need its fields as they were?
4. **What changed:** include owner changes and new decisions needed, or only raised, closed, moved and health?
5. **Copy out:** should What changed have "Copy as text" for a steering pack, given it is internal?

## Files it touches

`system/scripts/build_dashboard.py` (an `asof()` and `changes()` next to `flow_data`), `system/scripts/live_server.py` (two read-only routes), `system/templates/dashboard.html` (the control, the banner, the read-only render, the What changed view, in a marked block), `system/templates/help.md`, `dev/dashboard-spec.md`, `dev/tests/` (a fixture log rebuilds a past day's counts and forecast; an undone apply is ignored; a day before the first record says "not recorded"; the date parser; no write happens; nothing in any report or export).

## Size

**M**, about three days: one for the rebuild and the routes with tests, one for the page and What changed, one for the date field, keyboard and the UX baseline. Drop the slider and it is nearer two and a half.
