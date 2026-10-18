# Brief: Minutes confidence label (#169, release v2.4.0)

Product Manager, 18-10-2026. Mockup: dev/mockups/minutes-confidence-mockup.html (built on the minutes snapshot of the v2.2.0 line; click a label to see its transcript line, use the foot bar to hide the Clear labels or open the Approve dialog). Team Stark's read-only scouts (facts and cost) are to be added below when they arrive. Nothing is built; not approved yet.

## What the person sees

- **A quiet label on every proposed row and every drafted line:** **Clear**, **Check** or **Guess** (three levels, as the issue recommends; a percentage would look more exact than the AI is). Clear is plain muted text; Check is the amber pill; Guess is the red pill. Pills are the app's 22 px quiet size.
- **A one-line "why" under the row, only when it is not Clear:** owner not named, date only implied, decision maybe not agreed, speaker unclear, no transcript line found. Written from what the transcript says, in plain words.
- **The label is a link.** Click it and the transcript pane scrolls to and highlights the line it rests on (the same highlight the time tag uses). A row with no source line says "No transcript line found for this row" and is at least Check.
- **A count in the toolbar,** beside "1 check open": "2 Guess · 4 Check · 5 Clear".
- **In the Approve dialog,** Guess rows are listed first, then Check, then Clear. The list says: "Guess and Check rows are listed first. Clear rows are approved as they stand unless you remove them. Nothing is approved for you."

## Where and when

- In the minutes editor (the page under Review), for a draft not yet approved. Labels are made when the minutes are drafted, and refreshed if the extraction is run again.
- Not on approved, filed or exported minutes: the labels are working marks and are never in the Word or HTML export, the client report or any share.

## How a label shows its evidence

The why-line and the link are the evidence: the transcript line and its time tag. A label with no evidence is shown as Guess, never as Clear. creaite does not invent an owner or a date to make a row look sure.

## What Alan approves

- Nothing changes because of a label. He edits, removes or approves each row exactly as today.
- **Existing rule kept:** Clear rows stay approved unless he removes them; new decisions, new risks, closures and health changes still need their own tick.
- **Proposed change to the dialog (for Alan to decide):** the "Approve all as reviewed" box covers Clear rows only; Check and Guess rows are ticked one by one.
- **Learning from his edits:** an edit or a removal of a Check or Guess row counts toward the next extraction. Counts only (kind of row, label, kept or changed or removed); never minute text, as for Quality today.

## Client-safe rules

Labels and why-lines are internal. They never appear in a filed or exported minute, a client report, a steerco one-pager or a prep page. A why-line quotes only the minutes' own transcript, which is already internal. No VIP wording, no named person labelled for confidence: the label is about the row, never about who said it.

## Done when

1. Every proposed row and drafted line in a draft has a label; Check and Guess have a why-line.
2. A label opens its transcript line; a row without a source says so and is never Clear.
3. The toolbar count and the dialog order match the labels, and the dialog still approves exactly what is ticked.
4. Approved and exported minutes are identical with and without labels.
5. Light and dark, both palettes; keyboard: labels are buttons in tab order; Enter shows the transcript line.
6. Counts only are recorded (label, kept, changed, removed).

## Overlap with #165

This item takes the label. #165 keeps the rest (the "what did we miss" pass, tracker checks, read-back). The label's data is the first piece #165 would build on.

## For Alan (open questions)

1. **Three levels or a percentage?** I recommend three levels.
2. **Should "Approve all as reviewed" stop covering Check and Guess rows?** I recommend yes: it is the point of the label.
3. **Hide Clear labels by default?** The mockup shows them (as the issue says "every row"); a quieter screen would show only Check and Guess. I recommend showing Clear as plain muted text, with a switch to hide them.
4. **May his edits feed the next extraction (counts only)?** I recommend yes.
