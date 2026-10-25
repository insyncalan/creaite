# File paths on screen (v2.6.8, Cap hand check 26)

Status: plan, no code. Updated after Alan's answers (25-10-2026).

## What Cap found

Check 26 (issue #343 in the plan repo; Cap's words): "file paths are still on screen (`projects/_portfolio` in Files, a project path in project settings, the launcher command in Health)". It gives no wording to aim for, only the three places. Alan has since decided what he wants to keep (below), so check 26 must be reworded to match, or it keeps failing for places that are now intended.

## Rules

- Projects by name (BL-101); stored paths relative to the vault root.
- Plain words (`test_plain_words`, class `path`). Baseline `dev/tests/plain_words_baseline.json`: 36 `path` entries, 38 offenders; the count only falls.

## Scope for 2.6.8: Cap's three places, plus Activity as a second step

Files are under `system/templates/dashboard/src/`.

| Place | Today | What actually changes | Days |
|-------|-------|-----------------------|------|
| 1. Files tree tooltips (`files.js:18`, `:21`, `:22`) | Hover shows `projects/_portfolio`, `projects/<folder>`, `inbox` | Only the two internal ones change: Portfolio's tooltip becomes "Portfolio" and Intake's "Intake" (`_portfolio` and `inbox` are codes, not folders a person sees). A project's tooltip keeps its folder (Alan 1a). | 0.25 |
| 2. Project settings Folder row (`components/project/ProjectSettings.jsx:127`) | `projects/<folder>` plus **Open folder** | **Nothing.** Path text and Open folder stay (Alan 1a). | 0 |
| 3. Health's two commands (`settings.js:854` Restart, `:855` launcher; `core/page.js:80` `cmdBox`, `today.js:510` `suCmd`) | The command in a box with a Copy button | **Nothing.** Stay visible with their Copy buttons (Alan 1b). Same for the red "not running" alert (`core/keys.js:28`) and the sign-in agent lines (`autostart.js:58`). | 0 |
| 4. Activity > What ask creaite changed (`ask.js:208`), second step | `<code>` stored path of the changed file and of a move's target | Show the file name and the project name, with **Show in Finder** (Alan 1c). Stored path stays in the data and the debug log. | 1 to 2 |
| Tests and goldens | | Reword Cap's check 26; Activity goldens and tests; Files tooltip test if any | 0.5 to 1 |
| **Total** | | | **1.75 to 3.25** (the first three places alone: 0.25 and a reworded check; item 4 is the second step) |

Not changing: Files Location column and the minutes filing popup (already show names), the Prep and "Saved:" wording, Help prose, and the Python server messages (Alan 1d, later).

## Plain-words baseline

The first three places are drawn from data or are commands the class allows, so they move the `path` count by about 0. Item 4 draws `c.path` from data, so it adds no literal either. Expect 38 offenders to stay at 38 for 2.6.8. The drop comes later with Help prose and the Python messages (about 21 and 17 of the 38).

## Risks

- `test_project_settings.py:160` pins `projects/ABC` in `#psFolder`: stays valid because the row is unchanged.
- Activity: its table is pinned by Activity tests and the `activity` golden; the golden changes. Alan signs off the new picture before regenerating (desktop 900px only).
- A tooltip is not in the golden, so item 1 should not move any picture; a test grep for `title="projects/_portfolio"` is the only likely pin.
- Check 26 will keep failing unless reworded to: "no `_portfolio` or `inbox` shown; project folder, commands and Copy buttons stay".

## Decided by Alan (25-10-2026: items 1a to 1d)

- **1a Yes:** he does need to read a project's folder. Keep the path and Open folder; do not swap for the name.
- **1b Keep visible:** Health's Restart and launcher commands, with their Copy buttons.
- **1c Yes:** Activity shows file and project name plus Show in Finder, as a second step after the three places.
- **1d Later:** the Python server messages are out of this plan.

## Remaining question for Alan

1. A project's Folder row shows the stored path `projects/<folder>`. With the projects in OneDrive that is not where the folder really is. Show the real location (a home-folder path such as `~/OneDrive.../<engagement>`) instead? Recommendation: yes, later (about 0.5 day, needs the server to send it); not in 2.6.8.
