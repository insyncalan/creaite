# Sprint decisions-needed: what waits on a named person (BL-210)

Branch `sprint-decisions-needed`, worktree `../creaite-decisions-needed`, from `sprint-drafts-writing`, because it builds on BL-224's chase emails. **For v1.7.0.** Read BL-210 in `dev/BACKLOG.md`, BUILD's "Sprint drafts-writing" (BL-224's chase mode and `system/staging/chases.json`) and BL-209's meeting hub.

## Build
1. **BL-210, as written:** a band on Today of pending decisions that have a decision maker and a needed-by date.
   - **Order:** by how late or how soon they are, with yours first, marked "Yours" and with a **Decide** button that opens Record the decision.
   - **Each row:** the decision, the project (by name), the decision maker, days waiting, and what slips if it stays open.
   - **Chase** uses BL-224's chase mode. It drafts only and never sends.
   - **Open** opens the decision.
   - **The same list** appears on a project page and in a steering meeting's Prep, sharing the code, not copying it.
   - **The pattern notice is not built:** it waits for labels (BL-125 C).
2. **Docs:** Help, the spec, a BUILD "Sprint decisions-needed" section with the FR text, lines in `dev/release-notes/1.7.0.md`, and hand checks.

## Rules
- **`check.py`:** `python3 dev/tools/check.py` must pass strictly. Never use `--allow-worse`. Reuse existing renderers rather than adding HTML-string sinks.
- **Tests:**
  - run your own tests, plus test_today_brief, test_decisions_dashboard, test_decisions_board, test_decisions_prep, test_meeting_hub and every file your change touches;
  - use at most `-j 2`;
  - pin the page clock (`live_browser.pin_page_clock`) so "days waiting" doesn't depend on today's date.
- **Look at it:** in the real browser at 1400px, light and dark. Keep the screenshots in the scratchpad.
- **Never push or merge.** No Actions runs unless told. Stop only your own processes, by PID.
- **The usual edit rule:** don't edit `dev/BACKLOG.md`, `dev/BRD.md` or `dev/sprints/STATUS.md`. No schema change.
