# Sprint links: every count of work items opens Work, filtered (BL-190)

Branch `sprint-links`, worktree `../creaite-links`, from `main`. For v1.4.0; `VERSION` unchanged. It runs beside `fix-peek-140` (the peek's owner picker, staged changes in every window, the errors banner), which owns the peek, the pill and the banner; this sprint doesn't touch those. Read **BL-190** in `dev/BACKLOG.md` first; it holds Alan's request and the verified gaps.

## The build, one commit each, in marked blocks (`/* ===== BL-190 (sprint-links) ===== */`)

1. **The Projects table's Evidence column:** each figure becomes its own link.
2. **The project page's Flow card:** the bars, the ageing buckets and the priority bar open Work filtered to those items.
3. **The People list:** Open actions, Open RAID and Decisions waiting open Work filtered to that person and kind.
4. **The audit:** every other count of work items (Today, the prep page, Review, Activity). Link each one Work can reproduce exactly; list in BUILD any it can't, and why.
5. **Docs:** Help (a line that every count opens Work), the spec, BUILD ("Sprint links" with the FR text), and a line under "## Changes" in `dev/release-notes/1.4.0.md`.

## Rules

- **Extend, don't replace,** the existing mechanism: `data-nav="<tab>:<view>:<code>"` into `openWork(code, tab, view, extra)`. Add any filter `openWork` needs through `extra`, not a second router. BL-185 already made the cockpit status line's metrics clickable; leave that line alone.
- **The number shown equals the rows Work lists,** checked by a test for each kind of link. Link only what Work can reproduce exactly.
- **A zero is plain text, not a link** (the default; Alan can change it).
- **Accessibility:** a link names what it opens ("3 overdue actions in Example Programme"), not just the number. It's keyboard-reachable, and colour is never the only cue.
- **No schema change, no `tracker.py` change, no new server route.**
- **Look at it** in the real browser at 1400px and 1100px, chat open and closed, light and dark, in two themes. Keep the screenshots.
- **Tests:** one pass is enough; your own tests plus `test_pages`, `test_people_dashboard`, `test_today_brief`, `test_work_filters_live` and `test_activity_undo`. They also run on GitHub's Linux runner, so wait for conditions.
- **The usual edit rule:** don't edit `dev/BACKLOG.md`, `dev/BRD.md` or `dev/sprints/STATUS.md`. Never push or merge.
