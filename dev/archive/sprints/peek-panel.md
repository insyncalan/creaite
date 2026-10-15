# Sprint peek: the work item peek (BL-176, BL-177) and the Work toolbar (BL-175)

> **UX baseline first (BL-157).** Before it is called done, every screen this sprint touches is checked in the real browser against the ten checks in `dev/BUILD.md` › Sprint ux › UX baseline: (1) a text box shows what is typed; (2) a date field takes words; (3) a draft survives a reload; (4) nothing sends Alan to Claude Code that the app could do; (5) no panel covers content; (6) an empty state says what to do next; (7) the tab title and the first thing seen are right; (8) a form shows what matters; (9) hints are one tap away, not always on screen; (10) every "Today:" below states what Alan would see, checked in the real app. Look at 1400px and 1100px, light and dark, in at least two themes, with ask creaite open and closed. The report lists which checks were made, with screenshots. (Checks 3 and 8 change meaning here: nothing sits unsaved in the peek, and the key row is the form.)

**Goes into:** v1.4.0. Branch `sprint-peek`, worktree `../creaite-peek`, from the tip of `main` **after `sprint-polish-2` has merged** (see "When it can start").

## Goal

An action, RAID item or decision opens over the page at half width, **already editable**, with its key fields as a row of chips under the title, the way Plane's work item view works. No Edit button, no form, no Save or Cancel. Every edit is staged on its own and nothing reaches the tracker until Alan applies. Review's proposals get the same layout with an explicit footer (BL-177).

**The mockup is the spec: `dev/mockups/work-item-peek-mockup.html`.** Open it in Chrome, click through every item type and every picker, and build what it does. Where this brief and the mockup differ, the mockup wins. Read BL-176 and BL-177 in `dev/BACKLOG.md` for the full list of behaviour and rules, and the UX baseline in `dev/BUILD.md`.

Alan's decisions (10-10-2026), which are not open:
- **Each edit is its own staged proposal.** Do not merge edits to one item into one proposal.
- **No Comments tab.** The activity tabs are All, Activity, Updates and Source.
- **Review proposals keep an explicit footer** (BL-177).

## When it can start

After `sprint-polish-2` has merged. That sprint changes the same panel (BL-169's save hint, BL-167's unsaved draft, BL-173 which says the item panels stay as they are) and this sprint replaces it for work items. Bring `main` in at the start and again before the merge. BL-167 and BL-169 stay in force only for the panels this sprint doesn't change (new items, milestones, project health); for work items they are retired with the Edit button.

## Order

Commit each separately, each in its own marked block (`/* ===== BL-176 (sprint-peek) ===== */`).

1. **The shell (BL-176).** The panel overlays the page at half width (min 520px), slides in, closes on outside click and Esc, swaps on another row, J and K, expand to full width. With ask creaite open it stops at the chat's left edge and takes half of what is left. Retire BL-80's widen-on-edit and BL-136's width snap for work items. Before changing anything, take screenshots of today's panel to compare.
2. **Title, key row and free text (BL-176).** Plain-text editing with no boxes (tint on hover and focus), the chips and their pickers (list, owner search, date month), the three item types' rows, empty prompts, the overdue tag, the Type chip. Keyboard use throughout; accessible names on every chip and text area (`role="textbox"`, the field name, the current value).
3. **Staging (BL-176).** Each commit writes one proposal through the route the panel's Save uses today, with the validation that route already does applied to the one changed field. The pill, the save state, the "Last edited" line, the dot on staged rows, **Undo last** and **Apply**. If nothing removes an unapplied dashboard proposal, add a live-server route that removes only the dashboard's own newest unapplied proposal, and never one that has been applied or one the sweep or minutes made.
4. **Rules (BL-176).** Closed date, made decisions, client-visible needing messaging, empty title, bad date, recalculated Priority, Esc behaviour, and **⌘↵ (Ctrl+↵): commit the field you are in, apply everything staged, close the panel** (Alan, 10-10-2026, "like before"; the mockup's `saveAndClose`). Each as in BL-176.
5. **Details and Activity (BL-176).** Details (opens by itself for a client-visible item, remembers the rest), the feed with its four tabs from `change_log`, `updates` and the source, and the "staged" then "applied" marks.
6. **Review (BL-177).** `openProposal` in the same layout with Cancel, Save, Save and approve and Reject, and the proposal notes kept. Last, so the layout is settled.
7. **The Work and Review toolbar (BL-175).** As BL-175 sets out: the Keys chip (BL-155) goes from Work and Review; the toolbar icons (Display, the filter and the rest) are right-aligned; every menu that opens from a right-aligned icon opens leftwards or is kept inside the window, never clipped. Check at 1400px, 1100px and 900px, with the peek and ask creaite open and closed. The keys stay working; where the chip was the only place they were listed, Help lists them.
8. **Clear-out and docs.** Remove what the peek retires for work items (the Edit button and E, Save and Cancel, the editing banner, "More fields" for these three kinds, the always-on "⌘↵ saves and closes" line; the ⌘↵ key itself stays and now applies, and the Apply button shows it). Help, the guides (`python3 dev/tools/build_guides.py`), `dev/dashboard-spec.md`. Write the FR text in BUILD.

## Rules for this sprint

- **ask creaite and the peek open together (Alan, 10-10-2026):** the chat sits over the peek, and the peek's fields stay reachable: what the chat covers can be scrolled into view, or the peek's visible part still takes clicks and keys. Closing the chat leaves the peek exactly as it was. Test it at 1400px and 1100px.
- **Don't change what the mockup doesn't show:** new items keep the Create form, and the milestone, rebaseline and project-health panels, Review's draft-minutes flow, Current state, the Work, Mine and person lists and their inline cell edits stay as they are. If a new item needs the peek layout to feel right, take the conservative default (keep the form), note it in BUILD under "Open" and carry on.
- **No schema change.** A change to `tracker.py` or the database is out of scope; if one looks needed, stop and report it.
- **Shared files** (`dashboard.html`, `help.md`, `dev/dashboard-spec.md`, `build_dashboard.py`, `live_server.py`): new code in marked sections, and don't reformat unrelated lines. `sprint-rail` owns the left rail, Activity and the Current state title. Never hand-merge the generated guides; regenerate them.
- **Don't edit** `dev/BACKLOG.md`, `dev/BRD.md` or `dev/archive/sprints/STATUS.md`. The Scrum Master records the FR at merge. Create `dev/release-notes/1.4.0.md` entries only if the file exists or is yours to create; don't change `VERSION`.
- **Development guard:** sample data only; test with temporary vaults; never connect to Microsoft 365. Tests set `CREAITE_NO_LAUNCH=1`.
- **Stop a test run by its process tree,** never with `pkill` by name.
- **Never push or merge from the sprint session.**
- Where something is left open, take the most conservative sensible default, note it in BUILD and carry on.

## Tests

The sprint runs **its own tests**; one pass is enough (`dev/archive/sprints/STATUS.md` › Testing rule). A file that fails under load and passes alone counts; name it. Start from the mockup's own checks, which already pass in headless Chrome, and port them to the real page (`dev/tests/live_browser.py`, screenshots with `dev/tools/cdp.py`).
- **Opens editable:** opening an item shows the title, key row and free text live, with no Edit, Save or Cancel in the DOM.
- **Overlay:** with the panel open the page's width and first row's position are unchanged; with ask creaite open the two never overlap; at 1100px the panel is not under 520px; outside click and Esc close it; J and K move; another row swaps it.
- **Each edit is its own proposal:** three edits to one item write three proposals; Undo last removes only the newest unapplied dashboard one; Apply applies them all through the existing route; nothing reaches `tracker.db` before Apply.
- **Rules:** closing sets the closed date and reopening clears it; a made decision can't go back to pending; Made fills Date made; client-visible without messaging doesn't save, then saves with messaging; clearing a client-visible item's messaging is refused; an empty title is refused; a bad date says so; Impact or Likelihood changes recalculate Priority.
- **Pickers:** keyboard use (arrows, Enter, Esc) and staying inside the window at 1100px with the chat open.
- **Types:** the key row and free-text label are right for an action, each RAID type and a decision.
- **Details and Activity:** Details opens for a client-visible item; the four tabs filter; a change shows "staged" and then "applied".
- **Review (BL-177):** a proposal opens in the same layout; Save, Save and approve and Reject do what they did; the project, duplicate and Learn notes remain.
- **⌘↵:** with the cursor in the title, the free text or a Details field, ⌘↵ commits that field, applies all staged changes through the existing apply, and closes the panel; with a picker open it closes the picker first; with a client-visible item waiting for messaging it stays open; with nothing staged it closes and says so; Ctrl+↵ does the same on Windows.
- **Retired and kept:** the Edit button, its E key, "More fields" and the always-on ⌘↵ line are gone for work items; the new item form, milestone and project panels are unchanged.
- **Update, don't delete,** the tests that asserted the old read-then-edit panel (`test_panel_room`, the side-panel and editing files): change them to the new behaviour and say which in the report.

## Report

List the ten UX baseline checks and which were made, with screenshot paths (1400px and 1100px, light and dark, two themes, chat open and closed, one of each item type, a picker open, the staging pill, Review's proposal); the commits per item; the test files run and their result; anything left open and the default taken; any difference from the mockup and why. Do not merge or push.
