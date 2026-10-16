# UX review: Wallace baseline and Impeccable detector (17-10-2026)

Run for Alan (his yes, 17-10-2026) on a scratch clone of main at 884aaa75 (creaite 2.0.1, so none of v2.1.0 or v2.2.0). Read only: nothing was written to the repo. Desktop only, creaite theme, light mode, the tests' small fictional portfolio.

## The answer

The CSS is mostly tokenised already, with four loose ends: line heights (no tokens at all), radii, font sizes and a few raw z-indexes. The most visible usability problem is on Work: three stacked rows of filters say the same thing. The most common "AI-look" pattern in the detector is the left-border accent (23 places). The tools found little else, which says the 14-10 audit did its job.

## Step 1: Wallace baseline (style.css, 349 KB, 3,066 lines)

| Measure | Result | Reading |
|---|---|---|
| Font sizes | 19 unique; 8 are tokens (`--fs-*`, 640 uses in all), 11 are literals (12px ×18, 13px ×15, 11px ×14, 14, 15, 16, 20, 10px, .85em) | Near done: about 25 literal uses |
| Line heights | 19 unique, **no tokens**: a mix of unitless (1, 1.2, 1.3, 1.4, 1.5) and px (14 to 40) | The biggest gap |
| Border radii | 20 unique; tokens (`--r-md` ×197, `--r-sm`, `--r-lg`, `--r-pill`, `--ctl-r`) dominate; literals 8px ×13, 6px ×6, 4px, 3px, 10px, 12px, 7px | Fix the literals |
| z-index | 25 unique; 21 are tokens; raw 220, 47, 5, 1 | Four to move |
| Box shadows | 40 unique; about 12 tokens, many one-off focus rings and inset stripes | Decide a small set |
| Colours | 374 unique (1,092 uses), inflated by the nine themes' palettes | Not meaningful alone; the token audit covers it |
| Other | `!important` ×43; ID selectors 376; 48 specificity levels; 11,249 declarations, 2,753 unique (24%) | Healthy reuse |

## Step 2a: rendered pages (the project's own `ui_audit.py`, 12 pages)

- Same control, different looks: the base `button` is drawn 5 ways (height 26, 28, 30, 38); inputs 3 ways (32 and 40 px); the `.tag` chip 3 ways; h1 is 22 px on most pages and 34 px on Today and Help; h2 is 16 px on four pages and 22 px on Help.
- Rendered values across the app: 23 distinct spacings, 16 line heights, 10 font sizes, 6 radii.
- Targets under 24 px: Today 7, Work 4, Review 4, Projects 4, People 4 (mostly ID and count links).
- Axe: no violations. Console errors: none.

## Step 2b: Impeccable detector (`impeccable detect`, source files, 26 findings)

| Rule | Count | Where | Reading |
|---|---|---|---|
| side-tab (a coloured left border on a card or row) | 23 | `style.css` lines 685, 696, 698, 730, 887, 899, 1270, 1330, 1344, 2061, 2227, 2279, 2302, 2360, 2367, 2439, 2759, 3055; inset stripes at 658, 1438, 1471, 1482; `ChasePane.jsx` 80 | The most common tell. Many are deliberate status or quote marks, so this is a style decision, not a defect |
| border-accent-on-rounded | 1 | `style.css` 1202 | Same family |
| bounce-easing | 1 (advisory) | `style.css` 848 | Minor |
| broken-image | 1 | `ask.js` 774 | Probably a false positive: the image gets its source later. Check once |

The detector's critique step (an AI review of hierarchy and clarity) was done by me from the screenshots below. The Vercel interface guidelines pass has not been run.

## Ranked findings (from the screenshots, 6 of 12 pages looked at)

1. **Work: three stacked filter rows repeat "Status: Open".** A row of pills (Status, Due, owners, projects, priorities), a row of saved views ("All open" is the same filter), and an applied-filter chip row. Plus four unlabelled icon buttons on the right. Suggest one row of filters, with the active ones shown once. Usability, M.
2. **Review: "Stale · 12 days" sits on every row** and the header says "4 stale" of 4. When everything is stale the label tells you nothing. Show it only when it differs from the norm, or sort by age. S.
3. **Review: "Approve all from these minutes" beside "Approve" on the same row**, in near-identical outlined green buttons, and rows carry both a checkbox and an Approve button (two ways to act). Make the bulk action distinct and name what it affects. S to M.
4. **Review: meta text is 3 lines of 12 px per row** (owner, due, priority, match, source). Hierarchy is weak; a person scans for what to do, not for the source. M.
5. **Line heights have no tokens** (19 values). Add `--lh-*` tokens with the existing scale work (BL-325 follow-up). S.
6. **Radii, font sizes and raw z-indexes**: move the 11 literal font sizes, 11 literal radii and 4 z-indexes to tokens, then hold with stylelint rules. S to M.
7. **Page titles**: h1 is 34 px on Today and Help and 22 px elsewhere; h2 is 22 px on Help. Decide whether this is deliberate (a "home" scale) or drift. S.
8. **The same control drawn differently**: five button styles, three input heights, three chip styles. Unify under BL-316's follow-up. M.
9. **Intake: "Select new" and "Process selected" appear in both cards**, and "Process selected" is pale as if disabled even when nothing is selected, so it is unclear when it becomes active. S.
10. **Side-tab accents (23)**: decide whether the left-border accent is the house style for status and quotes, or replace it with a chip or icon. Judgement; no rush.
11. **Check:** the project cockpit rendered blank in the audit. It may be a capture timing issue (the page drew before its data), not a defect. Verify before logging.

Already planned and not repeated: "To decide" is renamed Intake and Review (#168); the 8 weeks bars and their legend (#162); the Review meeting-page link goes with the hub (v2.1.0).

## Caveats

- Main is 2.0.1. v2.1.0 changes Review's multi-select bar, Today, Notes and the minutes editor, so findings 3 and 4 should be re-checked on the cut.
- Sample data is sparse; a real vault with 200 items would stress Work and Review more.
- Part 1 covers 6 of the 12 screenshots (Today, Review, Work, Projects, the cockpit, Intake); Part 2 adds People, Files, Settings, Activity and Help. Milestones and the cockpit rendered blank.
- Only the detector's command line was used. The tool's install step writes hooks into Claude's own configuration, so I did not run it. The tools cached their packages in `~/.npm` (and possibly `~/.impeccable`); nothing is in the repo.
- Human usability sessions are still the other half; none of this tests whether a person finds the task easy.

## Part 2: the remaining screens (looked at on 17-10-2026)

People, Files, Settings, Activity and Help were looked at; Milestones and the project cockpit rendered blank (see 19). Ranked findings continue from 11:

12. **Activity shows "You, via cx-edit"** in the By column of every row. "cx-edit" is a developer word in reader text, against the plain-words rule. Say "You, by hand" or "You, in the dashboard". S, a clear fix.
13. **Help's heading reads "CREAITE X.Y.Z · FIRST DAY".** The version placeholder is showing. It may only happen in a development vault, but check it on the built app. S.
14. **People: zero is written two ways.** "Open RAID 0" shows a number, while "Decisions waiting" and "Overdue" show "—" for none; the counts are left-aligned and look like links (dotted underline) when they are not. Right-align counts and use one style for zero. S.
15. **Files has three ways to narrow the list at once**: a folder tree on the left, a row of chips (All files, Latest reports, This week's meetings, Intake, Weekly, Adhoc, Steerco) and a type menu with two date pickers; plus two search boxes (the vault search with ask creaite, and file names). "Intake" is both a chip and a tree entry. Recommend one navigation model. M.
16. **Activity: a Kind button and a filter icon beside it**, and the third row has no tick box where others do (the weekly update row), so the list reads unevenly. Same pattern as Work's filter icon. S.
17. **Settings is clean and consistent** (rows of label, one line of help, control; Reset where it can differ). Two notes: controls vary in height (time boxes, menus and checkboxes), and "Show changed only" is going in v2.1.0. No action.
18. **Help's "The loop" panel is the best-structured page** (one idea per column, the single gate highlighted). Its five columns are dense small text; fine for Reference, heavy for a first day. For the Phase A rewrite, not a defect.
19. **Milestones and the project cockpit rendered as empty pages** in the audit. Both need a project chosen, so this is probably the audit not choosing one. Unverified: open both in the running app before logging anything.

Looked at: 10 of 12 pages. Still to check on a real vault: Milestones and the cockpit. Not yet run: the Vercel interface guidelines pass.
