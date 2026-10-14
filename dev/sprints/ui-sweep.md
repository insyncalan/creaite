# Sprint ui-sweep: target sizes, narrow windows and high contrast across the whole app (BL-216, BL-217)

Branch `sprint-ui-sweep`, worktree `../creaite-ui-sweep`, made from `main` **after every other v1.6.0 sprint has merged** (review-work, chat-text, insight, ui-audit), so the sweep covers the final screens. For v1.6.0, the last sprint before the release. Read BL-216 and BL-217 in `dev/BACKLOG.md`.

## Order: one commit each

1. **BL-216: click targets of at least 24 by 24 pixels.** Settle first which small controls the WCAG spacing exemption already covers (neighbours clear of a 24-pixel circle), so only what needs work changes. Then fix the rest: tick boxes, ▾ editors, small links, and any controls the 1.6.0 sprints added. Add a size check that runs over every visible control in each view.
2. **BL-217 (low priority): a narrow window reflows** (no horizontal page scroll at 320 pixels in any view), **and high-contrast mode keeps borders and focus rings** (under emulated `forced-colors: active`).
3. **Docs:** the spec, a BUILD "Sprint ui-sweep" section with the FR text, and lines in `dev/release-notes/1.6.0.md`.

## Rules

- **Don't change any view's look beyond what the fixes need:**
  - compare before-and-after screenshots of every view in the default theme and one other;
  - spacing grows only where a target was too small;
  - the existing contrast and theme tests still pass.
- **Tests:** the new size, reflow and forced-colours checks, plus every browser test file (this sweep touches every view). One pass is enough; a file that fails under load and passes alone counts. Stop runs by their own process tree only.
- **The usual edit rule:** no schema change. Never push or merge.
