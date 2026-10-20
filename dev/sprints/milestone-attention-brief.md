# Needs attention: open work items on a milestone due in the next week (2.6)

Requested by Alan, 19-10-2026: "other items that get put into Needs attention are any work items attached to a milestone due in the next week, that if not closed will delay the milestone. Include in 2.6." **Approved by Alan 20-10-2026 with one change: the row says "Milestone <name>".** Mockup: `dev/mockups/today-milestone-attention-mockup.html`, built on the 2.5.0 Today snapshot. Fictional data.

## What it does
For every milestone that is not yet achieved or dropped and is due within the **Due soon window** (the existing setting "Due soon means within (days)", 7 by default; a milestone already past due and still open counts too), Today's **Needs attention** gets **one row**:
- **Title:** the row says what it is: "Milestone <u>Pilot go-live</u> is due Thursday 22nd October: 3 open items must close for it to hold" (the word Milestone, then its name in bold underline, which opens the milestone; Alan, 20-10-2026) (singular: "1 open item must close").
- **Sub-line:** up to three of the attached items, the late ones first and in red ("DEF-A-003 Confirm licence count with procurement, 1 day late"), then the others with their due day; "and n more" if there are more; the project's name; and "Open all 3 in Work" (Work filtered to that milestone's open items).
- The title opens the milestone; the "…" menu works as on the other rows.
- The row counts in Needs attention's number.

## Which items count (proposed; Alan to confirm)
Open **actions**, open **issues** and **pending decisions** attached to the milestone, because each must close for the milestone to hold. **Risks are not counted** (a risk can stay open and the milestone still lands). Items with no owner or no date are included and say so.

## Which date
The milestone's **expected** date when it has one (the forecast), otherwise the agreed date.

## It goes away by itself
When every attached item is closed, or the milestone is achieved or dropped. An item attached later brings the row back.

## Order
Time-critical, so milestone rows sit first in Needs attention, soonest milestone first.

## Not guarded
Today's page and its data only (`build_dashboard.py`, the Today view); no guarded file; no write; nothing leaves the laptop.

## Decided (Alan, 20-10-2026)
1. **Risks are left out** (recommendation accepted): only open actions, open issues and pending decisions count.
2. **No dismiss** on the row: it clears itself when the work is done; the "…" menu is the same as on the other rows.

## Done when
A milestone due in 5 days with 3 open items gives one row with the right words and counts; a milestone due in 9 days (window 7) gives none; closing the items removes the row; late items are first and red; a milestone with no attached items gives no row; an achieved milestone gives none; the count and the page agree; light and dark; desktop and 900 px. Hand check: the row, its links, and clearing it by closing the items.
