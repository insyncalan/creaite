# Today as one home: design notes (not logged)

Alan, 13-10-2026: held out of the backlog until he has finished the design mockups (round two: https://claude.ai/artifact/L9LxcPjQeyJUHDCi3i6xiq, tab "Today, one home"). The number BL-319 is kept for it. What was written so far:

### BL-319 — Today as one home
Raised 2026-10-13 (Alan), from the UX review ("breadth over depth"). **Option A chosen** from the round-two mockups (https://claude.ai/artifact/L9LxcPjQeyJUHDCi3i6xiq, tab "Today, one home"); options B (two columns) and C (changes with the time of day) were not. **In v1.9.1 (Team 1, 13-10-2026).** (build it on the components, BL-256). No schema change.

**Alan's rules for it (13-10-2026):**
- **Keep his graphic at the top:** the day band as it is (the date, the greeting and brief, the day line with meetings as dots and the sun at now, the meeting chips, BL-270's door icon).
- **Open design, no boxes:** sections are divided by a hairline and their heading, as Today is now; nothing becomes a card. To decide is marked by a coloured rule, not a box.
- **Informative icons over buttons:** each row's actions are icon buttons (the components' `IconButton`) whose name says what they do on hover and to a screen reader: Approve and save, Reject with a reason (BL-315's bar), Dismiss, Make a work item (BL-296), Process the transcript, Draft a chase (BL-298), Move the date, Mark done, Make a prep page, Record the decision, Write an update. Every action has Undo.
- **Review stays on the rail**, with its count.

**Alan's further rules (13-10-2026, after the mockup):**
- **Keep all of the heading elements:** the date and greeting, the brief, the day line graphic, the meeting chips with their meeting information, the Prepare and prep-page links, the Close the day door (BL-270), and the move-between-days navigation through the calendar's week (BL-293). Nothing in the day band is removed or moved below the fold.
- **Portfolio keeps all its information:** everything the Portfolio section shows today (each project's health and reason, next milestone, counts, description on hover per BL-285, and its links) stays available on Today, not cut down to a summary.
- **Week ahead records and reports the urgent and critical items:** it lists, for the coming week, Urgent and High (critical) RAID items and actions, and every milestone due, as well as meetings; each row says why it is there (due, at risk, overdue). The Week ahead priorities setting (`dashboard.week_ahead_priorities`) defaults to Urgent and High for this; Alan's own value is kept if he has set one.
- **Health is not on the rail:** it lives inside Settings (BL-320), so More holds Intake, Files, Activity and Settings.

**Change.**
- **To decide**, first after the day band: what waits for Alan in Review, transcripts ready in Intake, and messages from people he follows (BL-288: never labelled), newest first, the top five with their icon actions, then "Open Review (n)".
- **Every current section kept**, in today's order below it: Decisions needed, Needs attention (with Done, Move date and Chase icons), Your commitments (with BL-125 A's You owe and Waiting on), Week ahead (Prepare and Open), Resolved (folded to one line by default), Portfolio.
- **The rail:** Today, Work, Review, Projects, People; **More** (folded, remembered) holds Intake, Files, Activity and Settings (Health is inside Settings, BL-320).
- Keyboard: the rows and their icons are reachable by Tab and arrows; BL-315's keys work on To decide's rows.

**Done when:** Today shows To decide under the unchanged day band with icon actions and Undo; every current section is still there in order, unboxed; Review is on the rail and Intake and the rest under More; BL-254's Today snapshot updated with Alan's agreement; a test for the queue, the icons' names and the rail.

**Touches:** `system/templates/dashboard/src/today.js` (or its components), `src/rail.js`, the components' `IconButton`, Help, `dev/dashboard-spec.md`, `dev/tests/`.

