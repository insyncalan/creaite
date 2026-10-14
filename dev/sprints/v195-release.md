# Sprint: v1.9.5 release (BL-324, BL-325, BL-333, BL-334, BL-10, BL-03, BL-331, BL-316)

> **UX baseline first (BL-157).** Before it is called done, every screen this sprint touches is checked in the real browser against the ten checks in `dev/BUILD.md` › Sprint ux › UX baseline: (1) a text box shows what is typed; (2) a date field takes words; (3) nothing typed is lost (the peek stages each change; an unsent chat or note comes back after a reload); (4) nothing sends Alan to Claude Code that the app could do; (5) panels don't hide what you're working on (the chat opens over the page; an item panel's fields stay reachable); (6) an empty state says what to do next; (7) the tab title and the first thing seen are right; (8) the key fields come first (the peek's key row, the rest under Details); (9) hints are one tap away, not always on screen; (10) every "Today:" below states what Alan would see, checked in the real app. Look at 1400px and 1100px, light and dark, in at least two themes, with ask creaite open and closed. The report lists which checks were made, with screenshots.

**Goes into:** v1.9.5. Branch `release-195`, made from `release-194` once v1.9.4 is cut (stacked, `git merge --no-ff`, `dev/RELEASE-BRANCHES-NOTE.md`). Written by the Product Manager on 15-10-2026.

**Two teams, in parallel (Alan, 15-10-2026):**
- **Team Stark** (Team 2, laptop 2): the UI and design-scale branch with the conversation alerts, BL-316's shared test and half its screens; integrates `release-195` and cuts it.
- **Team Cap** (Team 1, laptop 1): archiving with move-back and the BL-323 follow-up, the other half of BL-316's screens, the hand checks and the full suite.

## Goal

Ship v1.9.5. Every screen looks the same and behaves the same; old items, reports and minutes archive themselves and can be moved back; and alerts read a conversation as a whole.

**In it:**
- BL-324: the UI audit's fix-first findings.
- BL-325: one design scale.
- BL-333: no screen scrolls past its bottom.
- BL-334: alerts read the conversation, not the message.
- BL-10: items archived by age.
- BL-03: old reports, snapshots and applied proposals archived into `_Archive/`.
- BL-331: move back an archived report. Added (Alan, 15-10-2026).
- BL-316: the consistency audit.

BL-326 moved to v1.9.4.

## When it can start

**Step 1 starts now,** in parallel with v1.9.4, after each laptop has re-cloned. Nothing merges into `release-195` until v1.9.4 is cut.

## Order

1. **Bring the built branches up to date with `release-194`** (merge, never rebase; rebuild the generated files):
   - **Team Stark:** `v195-vip-conversations` (`532ac4fb`). It already holds `v195-design-scale` (BL-324, BL-325, BL-333) under BL-334.
   - **Team Cap:** `v195-archiving` (`9e810e32`, BL-10 and BL-03). It already holds BL-09, so check nothing is doubled. Then:
     - **The BL-323 follow-up** (`dev/V195-ARCHIVING-NOTE.md`): BL-323 shipped in v1.9.3, so `archive.daily()` now runs after Tidy up in the live server's `backup_timer`, and the separate `archive_timer` is removed. Session start keeps its call after the daily backup.
     - Put `v196-move-back` (`88c6093b`, BL-331) on top.
2. **BL-316, the consistency audit, split by screen.** This is the largest piece left: it is frozen partway on `v195-consistency` (`6c364e1a`), which holds design-scale.
   - **Team Stark first** lands the shared behaviour test (keys, focus, Esc, Undo on every menu, picker and dialog) and `check.py`'s counter of old helpers. Both teams then work to the same check.
   - **Then by screen,** each on a branch per area from `v195-consistency`, against design-scale's tokens:
     - **Team Stark:** Today, Intake, Review, ask creaite, Help.
     - **Team Cap:** Projects and the project page, Work, Milestones, Files, Settings.

     The counter must reach 0.
3. **Build `release-195`.** Team Stark integrates, merging in this order:
   1. `release-194` (as cut);
   2. `v195-vip-conversations` (BL-324, BL-325, BL-333, BL-334);
   3. `v195-archiving` with move-back (BL-10, BL-03, BL-331);
   4. the BL-316 branches.

   Rebuild the generated files at each merge, and record each conflict and its resolution in `dev/RELEASE-BRANCHES-NOTE.md`.
4. **Docs.**
   - **Team Stark** finishes `dev/release-notes/1.9.5.md`.
   - **Team Cap** writes `dev/handchecks/v1.9.5.md`:
     - the UI fixes in light and dark;
     - the design scale on Today, Work, Review and Settings;
     - one card per conversation on Today;
     - an item closed long ago archived by age;
     - an old report archived, then moved back from Files;
     - a menu's keys and Esc on three screens.
5. **Team Cap: the full suite** on `release-195`, then Actions `tests.yml`, then `check.py`. Alan runs the hand checks.
6. **Team Stark cuts v1.9.5:** VERSION 1.9.5, merge to main, publish `v1.9.5`. Alan installs it with "update creaite".

## Rules for this sprint

- **No schema change.** BL-10 and BL-03 use BL-09's `archived` flag.
- **The one writer stays** `tracker.py apply`. Every file move goes through `filechange.py`; BL-331's move goes through the approval card.
- **No guard change.**
- **The archiving never runs** in the development repository or from an ask creaite run.
- **No real names:** use the fictional sample data.
- **Only the main session pushes;** agents commit only. Merge, never rebase. Clean up worktrees once work lands.
- **The usual edit rule:** don't edit `dev/BACKLOG.md`, `dev/BRD.md` or `dev/sprints/STATUS.md`.

## Tests

- **Each step:** its own tests, then every test file touching the areas changed, including the snapshots (design-scale re-recorded them in one pass).
- **Then the full suite** once on `release-195`, and Actions on Linux.
- **Under load:** a file that fails under load and passes alone counts.
- **Stop runs** by their own process tree.

## Report

- Each step: what was done and the tests.
- BL-316's counter at 0.
- The UX baseline checks, with screenshots.
- The hand-check result.
- Anything that needed Alan.
- `release-195`'s merge order.
