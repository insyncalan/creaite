# Sprint milestone-ui: the milestone view's two looks, and Add milestone in one step (BL-244, BL-245)

Branch `sprint-milestone-ui`, worktree `../creaite-milestone-ui`, from `main`. **For v1.6.1** (Alan, 11-10-2026; there is no 1.6.0). Read BL-244 and BL-245 in `dev/BACKLOG.md`, BL-186 and the "Sprint milestones" section in `dev/BUILD.md`. The mockup `dev/mockups/milestones-views-mockup.html` shows the page and card BL-186 built.

**Runs beside `sprint-ui-audit`**, whose BL-213 changes the milestone strip's text colour (`--muted`). Keep your CSS in marked blocks. When ui-audit merges, bring `main` in and keep both changes.

## Order: one commit per item, each in a marked block (`/* ===== BL-24x (sprint-milestone-ui) ===== */`)

1. **BL-244: client plain, internal marked.**
   - **Client view:** exactly the cockpit page's normal look, with no "CLIENT VIEW" pill or mark and no extra decoration.
   - **Internal view:** a bright border around the view, plus an "INTERNAL VIEW" coloured pill.
   - **Where:** the cockpit milestone card, the Milestones page (Plan and Movement), and any other surface that shows the Internal | Client switch.
   - **Rules:**
     - Keep BL-186's remembered choice of view. Alan's note says "client view (default)", so a first visit with nothing remembered opens on Client. Record this in BUILD.
     - The border and pill use theme tokens and must meet contrast in all nine themes, light and dark.
     - The internal mark must still reach a screenshot and a printout, as BL-186 required.
     - The client view is not made client-safe by styling alone: what it hides is unchanged.
2. **BL-245: Add milestone opens ready to edit.**
   - **Add milestone** (on the page and the card) opens the peek with every editable field ready at once: state, agreed date, forecast date, progress (slider and %) and description, plus the fields BL-186's editor already has.
   - No summary view first, and no second Edit click.
   - Saving, validation (the required reason and client message) and Undo work exactly as now.
   - Editing an existing milestone is unchanged unless it already behaves the same way.
3. **Docs:**
   - Help (Milestones);
   - the spec;
   - a BUILD "Sprint milestone-ui" section with the FR text;
   - two lines under "## Changes" in `dev/release-notes/1.6.0.md`, plus hand checks.

## Rules

- **Look at it:**
  - Use the real browser (`dev/tests/live_browser.py`, `dev/tools/cdp.py`).
  - Check at 1400 and 900px, light and dark, in at least three themes, with ask creaite open and closed.
  - Keep the screenshots in the scratchpad.
- **Tests:**
  - Your own tests.
  - Every test file that mentions milestones (`grep -l -i milestone dev/tests/*.py`).
  - Use `-j 2` at most, because other sprints are testing at the same time.
  - One pass is enough; a file that fails under load and passes alone counts.
  - Tests also run on Linux: wait for conditions, and don't rely on hover.
  - Stop only your own processes, by PID; never `pkill` by name.
- **The usual edit rule:** don't edit `dev/BACKLOG.md`, `dev/BRD.md` or `dev/sprints/STATUS.md`. Never push or merge. No schema change.
- **Style:** British English; "ask creaite" in lower case; DD-MM-YYYY shown.

## Done when

Both items are committed. Their tests and the milestone files pass. Help, the spec, BUILD and the notes are current. The report lists Alan's hand checks.
