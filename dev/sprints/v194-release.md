# Sprint: v1.9.4 release (BL-09, BL-304, BL-326, BL-327, BL-328, BL-329, BL-330)

> **UX baseline first (BL-157).** Before it is called done, every screen this sprint touches is checked in the real browser against the ten checks in `dev/BUILD.md` › Sprint ux › UX baseline: (1) a text box shows what is typed; (2) a date field takes words; (3) nothing typed is lost (the peek stages each change; an unsent chat or note comes back after a reload); (4) nothing sends Alan to Claude Code that the app could do; (5) panels don't hide what you're working on (the chat opens over the page; an item panel's fields stay reachable); (6) an empty state says what to do next; (7) the tab title and the first thing seen are right; (8) the key fields come first (the peek's key row, the rest under Details); (9) hints are one tap away, not always on screen; (10) every "Today:" below states what Alan would see, checked in the real app. Look at 1400px and 1100px, light and dark, in at least two themes, with ask creaite open and closed. The report lists which checks were made, with screenshots.

**Goes into:** v1.9.4, branch `release-194` (`deba7023` on the new repo, WIP), built on `v1.9.3`. Releases are stacked (`dev/RELEASE-BRANCHES-NOTE.md`): `git merge --no-ff`, never a rebase or a force-push. Written by the Product Manager on 15-10-2026.

**Two teams, in parallel (Alan, 15-10-2026):**
- **Team Cap** (Team 1, laptop 1): fixes `test_fast_save`, checks BL-09 on the release, runs the full suite, and owns the integration.
- **Team Stark** (Team 2, laptop 2): merges BL-330 and BL-326, writes the release notes and the hand checks, and cuts the release.

## Goal

Ship v1.9.4 quickly. It is the critical path: v1.9.5 and v2.0.0 are built on it. Everything in it is already built; what's left is one failing test, one merge, the checks and the cut.

**In it:**
- BL-09: archive and restore whole projects, with `_Archive` throughout.
- BL-304: changes appear at once.
- BL-326: ask creaite shows the ask, the activity and the outcome. Moved in from v1.9.5 (Alan, 15-10-2026).
- BL-327: fast saves and a fast first load.
- BL-328: a sweep's lock no longer outlives the sweep.
- BL-329: only one server starts.
- BL-330: a remembered chat that's gone.

**Decided (Alan, 15-10-2026):** Retry after "changed elsewhere" keeps Alan's value, as built.

## When it can start

As soon as each laptop has re-cloned the new repository. Steps 1 to 4 run at the same time.

## Order

1. **Team Cap: fix `test_fast_save`.** It failed after the names-scrub merge.
   - Find whether the test or the code broke. BL-327 moves the search index and the OneDrive copy into the background.
   - Fix the cause, then run `--repeat 3` and `--stress` once.
2. **Team Stark: merge `v195-run-chat-bl330` (`6a7c4ee7`) into `release-194`.** It carries BL-330 and BL-326.
   - Rebuild the generated files (`split_dashboard.py build`, `build_guides.py`).
   - Run test_live_server, the ask creaite tests and the run-engine tests.
3. **Team Cap: check BL-09 on the release.**
   - `test_archive_projects`, including its migration from v1.9.3's schema. The schema change is Alan's own commit.
   - The `_Archive` rename, in the skeleton for new projects too.
   - The agreed guard exception, via `test_guard_pinned` and `test_reach`.
4. **Team Stark: release notes and hand checks.**
   - Finish `dev/release-notes/1.9.4.md`: add BL-326, BL-09 and BL-304 to the fixes already there.
   - Write `dev/handchecks/v1.9.4.md`:
     - an instant edit and its Undo;
     - Retry after "changed elsewhere";
     - a save under 2 s with a changed document;
     - opening creaite twice quickly;
     - stopping a sweep, then starting another at once;
     - archiving and restoring a project;
     - a Prep page run seen in ask creaite (ask, activity, outcome only).
5. **Team Cap: the full suite** on `release-194`, then Actions `tests.yml` on `insyncalan/creaite`, then `check.py`.
6. **Release.**
   - Alan runs the hand checks.
   - **Team Stark cuts it:** VERSION 1.9.4, merge to main, publish the `v1.9.4` release (the workflow attaches the zip).
   - Alan installs it with "update creaite".

## Rules for this sprint

- **No schema change** beyond BL-09's, which is Alan's own.
- **The one writer stays** `tracker.py apply`.
- **No guard change** beyond BL-09's agreed exception.
- **No real names:** use the fictional sample data.
- **Only the main session pushes;** agents commit only. Merge, never rebase. Clean up worktrees once work lands.
- **The usual edit rule:** don't edit `dev/BACKLOG.md`, `dev/BRD.md` or `dev/archive/sprints/STATUS.md`.

## Tests

- **Each step:** its own tests, then every test file touching the areas changed.
- **Then the full suite** once on `release-194`, and Actions on Linux.
- **Under load:** a file that fails under load and passes alone counts.
- **Stop runs** by their own process tree; never `pkill` by name.

## Report

- What was fixed, and why `test_fast_save` failed.
- The tests.
- The hand-check result.
- Anything that needed Alan.
