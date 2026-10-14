# Sprint ui-audit: fixes from the UI audit (BL-212, BL-213, BL-214, BL-215, BL-211)

Branch `sprint-ui-audit`, worktree `../creaite-ui-audit`, from `main`. **For v1.6.0**; `VERSION` changes only at the release. Read BL-211 to BL-215 in `dev/BACKLOG.md` (Alan's UI audit, 11-10-2026). Where an item says "to settle in the build", take the option below or its recommended one, and record the choice in BUILD.

**Three sprints run beside this one:**
- `sprint-review-work`: Review, row clicks, the right-click menu;
- `sprint-chat-text`: ask creaite's input, refusals, markdown;
- `sprint-insight`: ⌘K, Close the day, evidence, Review focus, the meeting hub.

Keep to your items' code, in marked blocks (`/* ===== BL-21x (sprint-ui-audit) ===== */`). BL-216 and BL-217 (target sizes, reflow, high contrast) are a separate sprint at the end, so leave app-wide sizing alone.

## Order: one commit each

1. **BL-212: security headers and a narrower `/health`** (`live_server.py`).
   - Every response carries the headers BL-212 lists.
   - `/health` gives away no vault name.
   - **The CORS choice:** find who reads `/health` from another origin (the launcher, the installed app's offline page, a dashboard opened from a file). Keep `Access-Control-Allow-Origin` only for them, or drop it if nothing needs it.
   - Prove the page can't be framed from another origin.
2. **BL-213: the milestone strip text meets contrast** in all nine themes and both modes, checked against the rendered colours, so a new theme is covered automatically.
3. **BL-214: every field has a name a screen reader can read:** every visible `input`, `select` and `textarea` in each Settings category and each view (start with the Files filters).
4. **BL-215: the Undo message stays long enough.**
   - At least 8 seconds.
   - Hovering or focusing holds it, leaving restarts the clock, and Esc hides it.
   - **Also add ⌘Z (Ctrl+Z)** in Work to undo the last change, as Review already has, when focus isn't in a text field. That's the better fix for keyboard users.
5. **BL-211: ask creaite returns focus to where you were when it closes.**
   - Do this **after `sprint-chat-text` has merged** (the scrum master will tell you; or check `git log main --oneline | grep "Merge sprint-chat-text"`), then `git merge main` first. It changes the same `openChat` and `closeChat`.
   - If it hasn't merged by the time items 1 to 4 are done, report that, and leave BL-211 for the scrum master to restart.
6. **Docs:** Help (Undo and ⌘Z), the spec, a BUILD "Sprint ui-audit" section with the FR text, and lines in `dev/release-notes/1.6.0.md`.

## Rules

- **No schema change, and the guard is unchanged.** BL-212 changes headers, not what is allowed.
- **Look at it** in the real browser at 1400px and 1100px, light and dark, in two themes. Keep the screenshots.
- **Tests:**
  - each item's "Touches" tests;
  - then every file that mentions `live_server`'s headers or `/health`, `snack`, the Milestones strip, Files or Settings, and `openChat`.

  One pass is enough; a file that fails under load and passes alone counts. Tests also run on GitHub's Linux runner. Stop runs by their own process tree only; never `pkill` by name.
- **The usual edit rule:** don't edit `dev/BACKLOG.md`, `dev/BRD.md` or `dev/sprints/STATUS.md`. Never push or merge.
