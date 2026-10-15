# v1.9.2 Work reflow: note for Team 1

Branch `v192-work-reflow` (from `origin/main` 4370a4e). Not pushed.

## The failure

`test_ui_sweep` › Reflow failed on the Work screen with "Sara's person link sits under the title cell":

- on main, at a 656 px window;
- on `v192-sidebar`, at 640 px. The page is the same width there, because the sidebar is 16 px narrower than main's rail.

## Cause

At these widths the Work table (596 px) is slightly wider than its frame (`#workWrap`, 533 px at 656). BL-165's `xcueOne` keeps the first column (Action, `td.title`, `min-width:260px`) fixed (`.xstick`) whenever it is no more than half the frame. At 640 on main, 260 px is just over half the frame, so the column scrolls with the rest and nothing goes wrong. From about 648 to 680 it is just under half, so it stays fixed.

When a control in Owner is brought into view, the frame scrolls and the Owner column slides under the fixed 260 px Action column. The probe does this with `scrollIntoView` (centre); in normal use it happens when the link gets keyboard focus. Sara's link wraps, so the middle of its first line ends up under the title cell.

Nothing is wrong with the column widths or the hiding rules. The frame simply didn't know that part of its scrollport is covered.

## Fix

One rule in `system/templates/dashboard/style.css`, BL-165 block:

```css
.tbl.xstick{scroll-padding-left:var(--xstick,0px)}
```

`--xstick` is already set by `xcueOne` to the fixed column's width (0 when nothing is fixed). With this rule, focus and `scrollIntoView` place a control to the right of the fixed column, never under it. It applies to every table with a fixed first column, not only Work.

Layout is unchanged at every width: the page and the view never scroll sideways, and the table still scrolls inside its frame, as BL-217 allows for data tables. `dashboard.html` was rebuilt with `split_dashboard.py build`.

## Test

New test: `Reflow.test_a_fixed_first_column_never_covers_a_control_brought_into_view` in `dev/tests/test_ui_sweep.py`.

- It runs Work at 656 and 664 px and checks that the case under test is real (`#workWrap.xstick`).
- It fails without the rule and passes with it.

A width sweep from 560 to 900 px (Work list, Work with the panel open, Work board) now shows nothing covered, nothing cut off and no sideways scroll of the page or the view.

## For `v192-sidebar`

The fix was checked on `origin/v192-sidebar` (c7ea3b4) in a temporary worktree, with the patch applied and the dashboard rebuilt. All four Reflow tests pass there, including the 640 px Work case that failed before.

Merging `v192-work-reflow` into the sidebar branch should merge cleanly: the fix is three CSS lines in the BL-165 block plus one test, and it doesn't touch `today.js`, `review.js`, `panel.js` or `ask.js`. After merging, rebuild `dashboard.html`.

## Goldens

None changed. `test_snapshots` passes unchanged, because the rule only moves the scroll position when a control is brought into view.
