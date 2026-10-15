# Sprint milestones: Plan and Movement, the slip range, and loose ends (BL-174, BL-189, BL-178, BL-186, BL-184, tidy-ups)

Branch `sprint-milestones`, worktree `../creaite-milestones`, from `main` after v1.4.0. **For v1.5.0**; `VERSION` stays 1.4.0 until the release. Read in `dev/BACKLOG.md`: BL-174, BL-178, BL-184, BL-186 and BL-189. Read in `dev/BUILD.md`: the "UX baseline", "Sprint peek", "Sprint peek-new", "Fixes before 1.4.0" and "Sprint links". **For BL-186, the mockup `dev/mockups/milestones-views-mockup.html` is the spec**; where the backlog text and the mockup differ, the mockup wins.

## Alan's decisions (11-10-2026), not open

- **The BL-186 DDL is approved as written:**
  - `milestones.state`: TEXT, CHECK in ('Achieved','On track','At risk','Slipped','Overdue') or NULL. NULL means creaite suggests it.
  - `state_set`: INTEGER 0/1, default 0. It records that Alan set the state.
  - `state_reason`: TEXT, required when Alan sets a better state than suggested.
  - `owner`: TEXT, a full name from the people register.
  - `actual_date`: TEXT, YYYY-MM-DD, the Achieved date.
  - `client_visible`: INTEGER 0/1, default 0.
  - `client_message`: TEXT, required when `client_visible`.
  - **Original** comes from `change_log`, so it gets no column.
- **Missed is retired.** `status` becomes Planned, Done or Cancelled. The migration turns every existing Missed milestone into status Planned with state Overdue, and logs it in `change_log` so undo and Activity show it. It is idempotent (running it twice changes nothing) and keeps every row.
- **A late milestone that the client owns reads "Late" to the client.**
- **One vocabulary:** the five states replace Complete and Delayed in the Word weekly and client reports and in the one-pager.
- **Settled earlier** (see BL-186):
  - Movement is a page of its own, and the cockpit card shows Plan only.
  - The card's switch changes only the milestone card.
  - The chosen view is remembered.
  - The look of the two marks (INTERNAL VIEW and CLIENT VIEW).

## Order: one commit per item, each in a marked block (`/* ===== BL-1xx (sprint-milestones) ===== */`)

1. **BL-174: a page opened before a server restart says "reload".**
   - Your worktree already holds Alan's draft, moved from `main`: `live_server.py`'s `STALE_PAGE` 403, and a test in `test_app_launcher.py`. A copy is also in `dev/archive/sprints/stale-page.patch`.
   - Finish it: the page shows that message (not a bare refusal) with a **Reload** button, and the test passes.
2. **BL-189: other applies leave the peek's staged changes alone.**
   - A cell edit, a bulk change or a Review approval (with auto-apply on) applies only its own proposals.
   - The peek's staged proposals wait until Apply or ⌘↵.
   - Do it in the apply path the dashboard calls (which proposals it passes to `tracker.py apply`), not by changing `tracker.py`'s rules, unless that is the only way. If so, say why in BUILD.
3. **BL-178: one Esc leaves Work's cell editor on Windows and Linux.**
   - The native list opened by `showPicker()` takes the first Esc. Make one Esc close the editor in every browser.
   - Test it the way `test_cell_edit` handles Linux.
4. **BL-186 stage A: the data, under change control.**
   - Change together: `schema.sql`, `tracker.py` (validation including the required reason and client message, apply, undo, recode, migrate with the Missed migration), `propose.py`, `excel_sync.py` (the Milestones sheet's new columns), the conventions file and `dev/staging-format.md`.
   - **The rebaseline rule:** a rebaseline writes the new `baseline_date` and a decision (agreed with, reason, source).
   - `build_dashboard.py`: the suggested state and the history Movement needs.
   - `report.py` and `status_facts.py`: the one vocabulary and the client-visible filter.
   - The skills: cx-edit, cx-minutes, cx-client-report and cx-steerco.
   - **Tests:**
     - the migration on a copy of a populated database: rows kept, Missed becomes Overdue, a second run does nothing;
     - each field through propose, apply and undo;
     - the required reason and client message;
     - Excel export and import;
     - the rebaseline makes a decision.
5. **BL-186 stage B: the page and the card,** exactly as the mockup and BL-186 set out:
   - the Milestones page: its address, breadcrumb, Plan | Movement and Internal | Client;
   - the shared Plan component, used by both the card and the page;
   - the Movement ladder, chart, log and "Decide what to do";
   - the milestone editor in the peek layout, with **Add milestone**;
   - the cockpit card: its pencil opens the page, the switch icon, the details toggle on the left, the INTERNAL VIEW and CLIENT VIEW marks;
   - the palette, search and citation openers.

   Run every test BL-186's "Touches" lists.
6. **BL-184: the slip range on the Movement page.**
   - `forecast.py` (new, read-only), shown on Movement as BL-184 sets out.
   - It is internal only and never reaches client output.
   - **The live vault has no slip history yet,** so the page will say "No range yet: n of 8…". Prove the range with fixtures.
7. **Tidy-ups from 1.4.0:**
   - UX baseline checks 3 and 8 (in BUILD and `dev/sprints/TEMPLATE.md`) describe the peek, not the old panel;
   - remove the unused Create form code for work items (milestones and project health keep theirs);
   - Activity's search covers more than the newest 300 lines: search the 2000 rows read, and show the cap's note only when that limit is reached.
8. **Docs:** Help (Milestones, the five states, the two views), the spec, a BUILD "Sprint milestones" section with the FR text, and `dev/release-notes/1.5.0.md` (create it with a "# creaite 1.5.0 (Beta)" heading and a draft line).

## Rules

- **Never loosen validation.** The schema change is the approved DDL only; anything beyond it, stop and report.
- **Look at it:**
  - In the real browser (`dev/tests/live_browser.py`, `dev/tools/cdp.py`), at 1400, 1100 and 900px, chat open and closed, light and dark, in at least three themes.
  - Compare the page and the card with the mockup side by side.
  - The INTERNAL VIEW and CLIENT VIEW marks must reach a screenshot.
  - Keep the screenshots.
- **Tests:**
  - **Your own tests, plus every existing file each item touches.** After stage A and after stage B, run every test file that reads milestones (`grep -l -i milestone dev/tests/*.py`), not a sample. Last release showed that a narrow re-run misses real failures.
  - One pass is enough; a file that fails under load and passes alone counts.
  - Tests also run on GitHub's Linux runner: wait for conditions, and don't rely on hover, macOS scrollbars or a native list's keys.
  - Stop a test run only by its own process tree; never `pkill` by name.
- **The usual edit rule:** don't edit `dev/BACKLOG.md`, `dev/BRD.md` or `dev/archive/sprints/STATUS.md`. Never push or merge.
- **Style:** British English, plain and concise; "ask creaite" in lower case; DD-MM-YYYY shown, YYYY-MM-DD stored.

## Done when

All eight items are committed. Their tests pass, plus a run of every test file that mentions milestones, the peek or Review. Help, the guides, the spec, BUILD and the 1.5.0 notes are current. The report lists Alan's hand checks.
