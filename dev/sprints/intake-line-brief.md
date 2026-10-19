# Intake as a quiet line on Today (for 2.5.2): brief

Mockup (for Alan): `dev/mockups/today-intake-line-mockup.html`, built on the Today snapshot with the app's real classes. Fictional data. Requested by Alan, 19-10-2026.

## What changes
- The **"Intake and Review" section on Today goes** (its own heading, its count, its "new" marker, its fold/toggle and its list of rows).
- In its place, **one quiet line at the foot of Your commitments**: an inbox icon, then "Intake: 1 meeting ready to process and 4 proposals to approve." in muted small text, and a small **x** at the right edge ("Dismiss until something new arrives"). No heading, no toggle, no list, no buttons.
- The two phrases are links: the meetings open Intake at the meetings ready to process; the proposals open Review at the proposals to approve (once #232 lands, both open the one Intake page). Nothing is approved or rejected from Today any more.
- **Nothing waiting: no line at all.**

## Dismissing (proposed; Alan to confirm)
The x hides the line until something new arrives (a new meeting ready or a new proposal), or the next morning, whichever comes first, remembered in the browser, as the Sweep due banner does (#243). It never changes anything in Intake or Review.

## Consequences to confirm
- The quick Approve and Reject on Today's rows (and "Open in Review" icons) go. Approving happens in Intake and Review, as the other pages already allow.
- The rail badge and the Intake and Review pages are unchanged.

## Done when
Today has no Intake and Review section or fold; with items waiting there is exactly one quiet line under Your commitments with correct counts; the links open the right page and section; the x hides it and a new arrival brings it back; with nothing waiting there is no line; light and dark; desktop and 900 px; the Today snapshot test is updated; hand check: the line, its links, the dismiss and the return.
