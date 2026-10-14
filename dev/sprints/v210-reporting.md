# Sprint: Reporting (BL-335, BL-336, BL-337, BL-338, BL-339)

> **UX baseline first (BL-157).** Before it is called done, every screen this sprint touches is checked in the real browser against the ten checks in `dev/BUILD.md` › Sprint ux › UX baseline: (1) a text box shows what is typed; (2) a date field takes words; (3) nothing typed is lost (the peek stages each change; an unsent chat or note comes back after a reload); (4) nothing sends Alan to Claude Code that the app could do; (5) panels don't hide what you're working on (the chat opens over the page; an item panel's fields stay reachable); (6) an empty state says what to do next; (7) the tab title and the first thing seen are right; (8) the key fields come first (the peek's key row, the rest under Details); (9) hints are one tap away, not always on screen; (10) every "Today:" below states what Alan would see, checked in the real app. Look at 1400px and 1100px, light and dark, in at least two themes, with ask creaite open and closed. The report lists which checks were made, with screenshots.

**Goes into:** v2.1.0, the Reporting category, Priority High (Alan, 14 and 15-10-2026). **Ready (Alan, 15-10-2026: "v2.1.0 is ready"); the hold is lifted.** **Both teams, after v2.0.0.** Branch `sprint-reporting`, worktree `../creaite-reporting`, from the tip of `main`; merge v2.0.0's release branch in for the editor when phase 2 starts (merge, never rebase). Each part below is its own branch from `sprint-reporting` (`v210-p1-doc`, `v210-p2-exports` and so on), merged back in the order given. Written by the Product Manager on 15-10-2026.

**Two teams, work split to run in parallel (Alan, 15-10-2026): Team Cap (Team 1, laptop 1) and Team Stark (Team 2, laptop 2).**
- **Team Cap, reports:** P1 (the document format), P2 (exports), P3 (report data and server), P5 (the A4 sheet), P6 (the weekly report view), P8 (the client view), and `release-210`'s integration and cut.
- **Team Stark, minutes and the journey:** P4 (the minutes record and server), P7 (the minutes view), P9 (the reporting space and the Reports page), P10 (retire the meeting hub).
- **Contracts first, so neither team waits.** On day 1 Team Cap writes `dev/sprints/v210-contract.md`: `creaite_doc.py`'s read, write and version calls, the data block's shape, and the export call (P1 and P2). Team Stark builds P4 against it from the start. In phase 2, Team Cap adds `Sheet.jsx`'s props and slots (P5) to the contract before building it. Team Stark builds P7's parts (the transcript pane, item rows, the deadline popover, coverage) on a stub sheet, then moves them onto the real one; P9 and P10 need no sheet. A change to the contract is a SPRINTCOMMS entry.
- **Each team** runs its own parts' tests; Team Cap merges into `sprint-reporting` in the order below.

**Read first:** BL-335 to BL-339 in `dev/BACKLOG.md`: every decision is there, with its Done when and Touches. This plan only orders the work. The mockups are private artifacts in Alan's claude.ai (not committed, because they use the firm's real brand): "Weekly report redesign" (https://claude.ai/artifact/HqGogxJp2Y41tF1DXWFTyR), "Client report" (https://claude.ai/artifact/PFQ9xsVxhneMnajidsYFkN), "Reporting journey" (https://claude.ai/artifact/D1TGuMeqwPPZE1fDaQiPsy) and "Minutes editor" (https://claude.ai/artifact/12jbexbSjXGTAK8CfKTeuG). Build them as drawn.

## Goal

Weekly reports, client reports and meeting minutes are made, edited, approved and filed **in creaite**, as true A4 pages, instead of Word drafts reconciled at approval:
- They are saved in **creaite's own format**: one `.html` file holding the page and its data, versioned, and reopened in creaite with every option.
- They are exported to **HTML, Word or PDF** to share. Nothing is ever sent.
- Each project gets a reporting space, and the left menu gets a Reports page.
- The meeting hub is retired.

## When it can start

- **Phase 1 (P1 to P4: data, file format, exports, server) starts now,** from `main`. It needs no editor and no new screens.
- **Phase 2 (P5 to P10: the screens) starts when v2.0.0 is merged in.** It needs:
  - BL-301 part A's one editor (`creaiteEditor(el,{markdown,features,pickers,ai})`, Tiptap) and `/api/edit/ai` (part D);
  - the components base (`src/components/`, Preact signals, `dev/COMPONENTS.md`);
  - Sneak peek in the peek (BL-322, `src/components/peek/SneakPeek.jsx`, v1.9.3).

  If any of these isn't on `main` by then, stop and report; don't copy it in.

## Order

### Phase 1: no editor needed

1. **P1 (Team Cap): creaite's document format (shared by reports and minutes).** A new `system/scripts/creaite_doc.py`:
   - It writes and reads one `.html` file: the page as approved, plus a `<script type="application/json" id="creaite-data">` block holding the data (each section, its order, its text, the rows shown, the items as they stood, the layout).
   - Saving makes a new version and keeps the earlier one, through `filechange.py` (backup, log, Undo).
   - Search reads each section and figure (the `search.py` index).
   - File names come from `paths.py`: `report.py` `report_file()` gives `.html` for the weekly and client reports; minutes are `YYYY-MM-DD <Meeting title>.html` in the minutes folder.
   - Outside creaite, the file opens in any browser.
2. **P2 (Team Cap): exports (shared).** Every export is made from the data, so all three match:
   - **HTML:** the page without the editing data.
   - **Word:** through `docx_tools.py fill` (`weekly-report-template.docx`, `client-report-template.docx`, `minutes-template.docx`).
   - **PDF:** Chrome's print to PDF. Chrome is already required.

   **File the exports beside it** is on by default. Each export opens in the default viewer as soon as it's made (`/api/open`).
3. **P3 (Team Cap): report data and server (BL-335, BL-336).**
   - `report.py` `weekly_data` and `client_data` feed the editor's data model; `weekly_stage` and `client_stage`'s Word fill is retired for this flow.
   - Layout settings per project and per client: section order, hidden sections, renamed headings, logos, the milestone list, the row rules. Logos are kept in the git-ignored `system/branding/`.
   - The client leak check moves from `review.py` `client_findings` (which reads Word) onto the data. Nothing that isn't client-visible, is Sensitive or is partner-only can reach a client report.
   - **The baseline:** a client report is approved or exported only after that week's internal report; its facts then lock to the approved week.
   - Routes: `/api/report/draft`, `save`, `approve`, `export`. Approve is one apply with Undo, as today.
4. **P4 (Team Stark, from day 1 against the contract): the minutes record and server (BL-338).**
   - `minutes.py` `cmd_stage` writes the minutes record instead of the Word draft:
     - the sections of `minutes-style.md`;
     - each line's transcript position for the time tags (VTT cue times, else speaker turns);
     - agenda coverage;
     - the exact source line ("Teams transcript and meeting chat, <title>, <long date>, HH:MM–HH:MM (UAE time)").
   - **Deadlines in words** are worked out from the meeting's date: Friday, next week (that week's Friday), next Wednesday, end of month (the last working day), in 2 weeks, 30-10. One shared parser serves the dashboard and the scripts.
   - **Coverage actions:** carry a point to the series' next meeting (on its agenda and Prep, through the existing `/api/meeting/carry`), set up a separate session (adds an action for Alan), or drop it; each can add a line to the minutes.
   - **Approve minutes** (`review.py`) applies the minutes and the ticked items in **one apply**, and nothing goes to Review again:
     - actions and updates are one group;
     - a new decision, a decision recorded or withdrawn, a new risk and a closure each need their own tick (the bulk rule is unchanged; see the open point below);
     - unticked items wait in Review.

     A removed item drops its line from the minutes, or keeps the line only. **Update that one** turns a new item into an update of an existing one (BL-221). A milestone change is proposed on its own (BL-186).
   - Routes: `/api/minutes/draft`, `save`, `approve`, `export`. `cmd_refresh`'s Word reconcile and `minutes_differences` are retired for this flow.

### Phase 2: needs the editor and the peek

5. **P5 (Team Cap, its props in the contract first): the A4 sheet (shared).** `components/report/Sheet.jsx` and its parts, used by every report and the minutes:
   - a true A4 page at 80% of the width, zoomable from 40% to 80% of the width (− +, trackpad pinch, ⌘+ ⌘− ⌘0); Show as exported; page breaks marked;
   - **the scroll position kept on every redraw** (the mockup's first version jumped to the top);
   - sections that move and hide; renamable headings with Reset;
   - ✦ per section through `/api/edit/ai`; inline checks; selection actions (Shorten, Make it executive, Polish, Find the source);
   - source tags (creaite only, never exported);
   - **the standard peek with Sneak peek** on every item ID.
6. **P6 (Team Cap): the weekly report view (BL-335).** The header with logos, health with its trend, At a glance as a section, the scrolling timeline and the milestone list with its eyes, What we need from people, This week and Next week, decisions written out, risks and overdue actions with eyes, Current state in two panes, the footer.
7. **P7 (Team Stark): the minutes view (BL-338).**
   - The transcript pane, with time tags linking to it.
   - Checks against the transcript.
   - Item rows: ✕ Remove with Undo; Looks like, with Update that one and What changes; Looks done; the owner picker from the people register.
   - The deadline popover: calendar, quick picks and words.
   - Agenda coverage with Deal with it…; the milestone note opening the milestone in the peek.
   - One version, or internal and distributed: Side by side with matching sections levelled, Internal only, ≠ markers, Match internal, the check of what's left out.
   - The approve popup: 784px wide; Esc or a click outside closes it.
8. **P8 (Team Cap): the client view (BL-336).** The same sheet with the client's own layout, the client health and its reason, Match internal (one section or all), the check of what's left out before export, and Side by side with the internal report.
9. **P9 (Team Stark): the reporting space and the Reports page (BL-337).**
   - The cockpit's Reporting card.
   - One reporting space per project: weeks down the left; the internal and client reports as cards; Edit both side by side; the week's files.
   - **Reports** in the left menu, with a count of what needs Alan; Needs me or All projects; the Friday reminder on Today points to it; ⌘K reaches it.
10. **P10 (Team Stark): retire the meeting hub (BL-339).**
    - Remove `meetings.js` `HUB`, `HUBIX`, `hubFor`, `hubLink` and `renderMeeting` (`#v-meeting`).
    - An old `#meeting=` link (`core/nav.js` `hashOf`) opens the meeting's Prep before it, and its minutes after.
    - Change the call sites in `today.js`, `review.js`, `files.js`, `intake.js`, `projects.js`, `ask.js` and `core/fields.js`.
    - `/api/meeting/carry` stays, now used by the minutes' coverage.
11. **Docs, last (each team its own parts; Team Cap the rules text and the release notes):**
    - the FR text in `dev/BUILD.md`, `dev/release-notes/2.1.0.md`, Help and the regenerated guides;
    - the cx-minutes, cx-weekly-report and cx-client-report skills (they draft into the editor, not Word);
    - `system/creaite-rules.md`'s skills table and its Retention and Dashboard sections where they mention Word drafts;
    - `dev/staging-format.md`.

## Rules for this sprint

- **Read** each item's write-up in `dev/BACKLOG.md` before its part. Where this plan and the backlog differ, the backlog wins; say so in the report.
- **No schema change.** If one seems needed, stop that part and report.
- **The one writer stays** `tracker.py apply`. Every file change goes through `filechange.py`.
- **Microsoft 365 actions stay off:** creaite never sends, never makes an invite or a mail draft.
- **The bulk rule is unchanged:** minutes are approved on their own, and decisions, new risks and closures need their own tick.
- **No real names** anywhere: use the fictional sample data. The firm's brand and the logos stay in the git-ignored `system/branding/`.
- **Look at it** in the real browser (`dev/tests/live_browser.py`, `dev/tools/cdp.py`) at 1400px and 1100px, light and dark, in two themes. Keep the screenshots.
- **`check.py`** holds you: no figure may rise, so split as you go.
- **The usual edit rule:** don't edit `dev/BACKLOG.md`, `dev/BRD.md` or `dev/sprints/STATUS.md`, and don't change VERSION. Only the main session pushes; agents commit only. Clean up worktrees and branches once work lands.

## Tests

- **Quick tier, new:**
  - `test_creaite_doc.py`: round trip, versions and Undo, search.
  - `test_report_exports.py`: the same sections in the same order in HTML, Word and PDF; hidden sections and rows never exported.
  - `test_client_leak.py`: nothing Sensitive, not client-visible or partner-only reaches a client report or the distributed minutes.
  - `test_minutes_record.py`: time tags, the source line, coverage actions, deadlines in words from the meeting's date.
  - `test_minutes_approve.py`: one apply; the two groups; unticked items left in Review; Remove drops the line.
- **Chrome tier, new:**
  - `test_report_editor.py`: zoom held between 40% and 80%; the scroll kept after a click; move and hide; the layout remembered per project.
  - `test_minutes_editor.py`: Side by side headings stay level; popups close on Esc and on a click outside; Remove and Undo; the deadline popover.
  - `test_reports_page.py`.
  - `test_hub_retired.py`: no screen links to a meeting page; old links land on Prep or the minutes.
- **Update:** `test_reports.py`, `test_report_builders_pinned.py`, `test_minutes_draft.py`, `test_minutes_review.py`, `test_meetings.py`; `test_meeting_hub.py` is replaced by `test_hub_retired.py`.
- **Stand-in model replies** only; never a real model call in tests.
- **Then every test file** touching the areas changed, and the full suite before the release; tests also run on GitHub's Linux runner. Stop runs by their own process tree only; never `pkill` by name.
- **Hand checks** for Alan in `dev/handchecks/v2.1.0.md`: one week's report drafted, edited, approved and exported; one client report; one meeting's minutes from a transcript, approved with its items.

## Report

Per part:
- what was built, against its Done when;
- the UX baseline checks, with screenshots;
- the tests run and their result;
- anything that needed Alan or differs from the backlog.

Finally, the merge order for `release-210`.

**Open point for Alan (not blocking):** should a new decision, a new risk and a closure join "approve all" in the minutes popup? That would change the bulk rule in `system/creaite-rules.md`. Build the current rule; if Alan changes it, it's one switch in P4 and P7.
