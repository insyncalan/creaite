# Brief: Check this report (#170, release v2.4.0)

Product Manager, 18-10-2026. Mockup: file:///Users/alanmahon/dev.env/pm/dev/mockups/report-check-mockup.html (built on the weekly report snapshot of the v2.2.0 line; press **Check this report**, accept or ignore a card, use the state buttons at the foot). Team Stark's read-only scouts (facts and cost) are to be added below when they arrive. Nothing is built; the mockup is not approved yet.

## What the person sees

- **A button, "Check this report"** (the app's plain sparkle) in the report's toolbar, left of Export. It is the only way to run the check in the first version.
- **A one-line result** where the toolbar shows status: "5 gaps: 2 to fix, 3 to check". With nothing left: "All checked, nothing left open".
- **A margin panel** on the right of the report. One card per gap: a Fix or Check chip, the section, a one-line headline, the evidence (each fact links to the tracker row or report section it comes from), a suggested fix, and two buttons: the action (for example "Add to the summary") and Ignore.
- **A numbered mark on each section** (red for Fix, amber for Check). Click a mark or a card and the other scrolls into view and is outlined.
- **After you change the report,** the line says "Changed since the check" and the button reads "Check again". Nothing re-runs by itself.

## Where and when

- On the **weekly report** (internal) only, in version one. It appears when a draft is open; it is not on the filed or exported report, the client report or the minutes.
- **Only when Alan presses the button.** Recommendation (from the issue): button first, automatic later once he trusts it. Cost is one run per press; Team Stark's cost scout sets the number.

## What it looks for (version one)

Each is a tracker or report fact, never a judgement about a person:
- a section empty or thin while the facts say otherwise (summary empty while health is Off track);
- an open risk or action with no owner or no response;
- an overdue action with no update since it fell due;
- a plan stated in the report that no action records;
- a health reason that names fewer causes than the facts show (shares ground with #167);
- an item named in the report that changed after the draft was made;
- a project with meetings this week and nothing said about it;
- a milestone slipping with no reason written; a decision needed with no date.

## How a suggestion shows its evidence

Every card lists the facts it rests on, each a link to its source (an item ID, a report section, a dated minute). A card with no evidence is not shown. Suggested wording is a draft built from those facts only; creaite does not invent an owner, a date or a response (card 2 says so).

## What Alan approves

- **Accept** does exactly what the button says, and only that: adds the suggested sentence into the section for a text fix (shown highlighted, not yet saved), or opens the item for him to edit. He still saves and approves the report as today.
- **Ignore** hides the card for this report. Nothing is remembered about him and nothing is changed.
- The check **never blocks "Approve and file"**, never edits the text by itself and never writes to the tracker.

## Client-safe rules

- The panel and its evidence are internal: they are never in the filed report, an export, the client report or any link Alan shares.
- Version one runs on the internal weekly report. A check of the client report is a separate step and would read client-visible items only.
- Evidence and wording never carry confidential or sensitive items into a client-facing sentence; a suggested sentence that would is not offered. No VIP labelling anywhere.

## Done when

1. The button runs the check on a draft and shows the one-line result and one card per gap with evidence links.
2. Accept makes only its stated change, unsaved, and marks the check out of date; Ignore changes nothing.
3. Approve and file works at every point; the filed report and exports are identical with and without a check.
4. A run that finds nothing says "All checked, nothing left open".
5. Counts only go to the usage record (kind, seconds, cost; never text).
6. Works in light and dark and both palettes; keyboard: the button, each card's buttons and Esc to leave the panel.

## For Alan (open questions)

1. **Button first, or automatic on every draft?** I recommend the button.
2. **Is five to eight gaps the right ceiling?** More than that and the panel becomes a to-do list; I would show the top eight by severity and a "more" line.
3. **Should "Ignore" be remembered for the same report next week?** I recommend no.
