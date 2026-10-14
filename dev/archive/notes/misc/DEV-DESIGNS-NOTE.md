# dev-designs: note for the Scrum Master

From the second laptop, 12-10-2026, for item D of `dev/LAPTOP-2-WORK.md`. It's mockups and briefs only, all under `dev/`, with nothing in `system/`, so it can merge at any time. `check.py` said OK before each commit.

## Alan's decisions (12-10-2026), for the backlog

Alan has reviewed the five designs. This laptop doesn't edit `dev/BACKLOG.md`, so please record the following:

| Item | Today in BACKLOG | Alan's decision |
|---|---|---|
| BL-203, a project as of any day | Not scheduled, low priority | Out of any sprint, **low priority** (no change) |
| BL-204, contact rhythm and the 1:1 prep page | Not scheduled, low priority | Out of any sprint, **low priority** (no change) |
| BL-59 and BL-60, minutes edited in Review and the transcript pane | Not scheduled ("can be planned") | Out of any sprint, **low priority** |
| BL-125 B and C, links and labels | Not scheduled | Out of any sprint, **low priority** |
| BL-264, Settings › People filters | v1.9.0 | **Redesigned and approved ("mockup is perfect", 12-10-2026):** one filter icon and picker like Work's (`96bc57b`; brief revised to M, about 2.5 days). **Alan: in v1.9.0, built on laptop 2** (12-10-2026), as the first item once BL-231's modules are merged. Alan has answered the brief's four questions (see its Decisions): register stakeholders, filters remembered until cleared, both Needs attention choices, removed hidden by default |

BL-125 A (promises) is also moving out of v1.9.0, to low priority; see `dev/archive/notes/v1.9.0/V19-PROMISES-NOTE.md` on `v19-promises-data`.

## What's in it

The commits are one per item. Each item has a self-contained HTML mockup (no network, light and dark themes, sample-vault data, today 12-10-2026, no console errors in headless Chrome) and a one-page brief.

| Item | Mockup | Brief | Size |
|---|---|---|---|
| BL-203, a project as of any day | `dev/mockups/asof-mockup.html` | `dev/sprints/asof.md` | M, about 3 days (2.5 without the slider) |
| BL-204, contact rhythm and the 1:1 prep page | `dev/mockups/contact-rhythm-mockup.html` | `dev/sprints/contact-rhythm.md` | M, about 3 days (+0.5 if mail and Teams count) |
| BL-59 and BL-60, minutes edited in Review and the transcript pane | `dev/mockups/minutes-review-mockup.html` | `dev/sprints/minutes-review.md` | BL-59 L (about 7 days) + BL-60 M (about 3 days): two sprints |
| BL-125 B and C, links and labels | `dev/mockups/links-labels-mockup.html` | `dev/sprints/links-labels.md` | B M (about 4 days) + C L (8–10 days): best as two releases |
| BL-264, Settings › People filters | `dev/mockups/people-filters-mockup.html` | `dev/sprints/people-filters.md` | S, about 1.5 days |

`links-labels.md` is named that way because `dev/sprints/links.md` already exists for BL-190.

## Questions for Alan

Each brief lists all of its questions. The main ones, with the recommendation where there is one:

- **BL-203:**
  - "Last steering" comes from the latest filed steering minutes (recommended), the calendar or a setting.
  - Is a slider needed, or are the date field and quick stops enough?
  - An item opened from a past day shows as it is today (recommended).
- **BL-204:**
  - What counts as a contact: meetings only (recommended), or mail and Teams too?
  - For someone on several projects, the prep page is filed under the project with most of their items (recommended).
  - Does the gap turn amber at twice the usual gap, or at fixed thresholds?
- **BL-59 and BL-60:**
  - Does Approve minutes leave undecided items in Review, or approve them too?
  - The approved record is kept in the vault (recommended).
  - A meeting stays in Word until Re-extract (recommended).
- **BL-125 B and C:**
  - Which comes first, B or C?
  - The sensitivity read runs on client-facing outputs only (recommended).
  - Does an item that merely names a labelled person count as sensitive?
  - How strict should cross-project link suggestions be?
- **BL-264:**
  - Removed people are hidden by default.
  - Stakeholders come from the project register's Key and Shared lists, which the page already holds through `build_dashboard.stakeholders()` (recommended), rather than each project's `CLAUDE.md`, as BL-264 says.
  - Are filters remembered for the session, or until cleared?

Nothing here changes the backlog. Record the sizes and decisions in BACKLOG and STATUS as you see fit.
