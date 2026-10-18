# Brief: Health that argues back (#167, release v2.4.0)

Product Manager, 18-10-2026. Mockup: dev/mockups/health-argues-mockup.html (built on the cockpit and weekly report snapshots of the v2.2.0 line; the foot bar switches the three states and the two placements). Team Stark's read-only scouts (facts and cost) are to be added below when they arrive. Nothing is built; not approved yet. Alan's note on the issue: a review is planned for about 13-11-2026 with the Activity > Quality numbers; this brief is the design, not a decision to build.

## What the person sees

- **When the declared health and the tracker's facts disagree,** a quiet note under the health line on the project page: "The facts point to At risk, and you set On track", the facts it counted (each a link to its item: overdue action, urgent risk with no owner, milestone slip), and three buttons: **Change to At risk**, **Keep On track, and say why**, **Not now**.
- **Keep, and say why** opens a one-line reason box. The reason is saved as the health reason and **the weekly report's Health row uses it**. The note then shrinks to one grey line: "You kept On track against the facts. Your reason is used in the weekly report: ...".
- **Change to At risk** sets it through the same path as the existing health editor, with the reason box offered; nothing else moves.
- **Not now** hides the note until the facts change.
- **When they agree, nothing shows at all.**

## Where and when

- On the **project page**, under the health line, when the page opens and the facts disagree; and in the **weekly report draft** as the same quiet note beside the Health row (the #203 sparkle suggests a health; this note compares the one already set). Option for Alan: **only inside the health editor** (the second placement in the mockup), so the project page stays clean.
- Evaluated from the tracker each time the page or draft opens. No model call is needed for the comparison; the sentence is built from counts by plain code, so it costs nothing and cannot invent a fact.

## How it shows its evidence

Every fact in the note is a count from the tracker with its link, and the note says which rule fired. Rules (version one, plain code): declared On track with an overdue action older than N days; with an urgent or high risk with no owner or response; with a milestone slipped by more than N days; no steering decision for N weeks. Declared Off track with nothing overdue, no high risk and no slipped milestone gets the opposite note ("The facts look better than Off track"). N are settings, with defaults Team Stark names.

## What Alan approves

- The note never changes health, never blocks anything and never writes the tracker. Only his button does, through the existing health save.
- His reason, when he keeps his call, is the report's wording. creaite's own note is **never in the report**, an export, the client report or any share.
- **Later (not in this brief):** privately scoring his past health calls. Needs its own decision.

## Client-safe rules

Internal only. The facts counted may include items marked sensitive or not client-visible, so the note is never shown in the client report, never exported and never filed; the report keeps only Alan's reason, which he writes and can see. No VIP wording.

## Done when

1. Disagreement shows the note with facts and links; agreement shows nothing.
2. Keep saves his reason as the health reason and the weekly report's Health row shows it; Change uses the existing save; Not now hides until the facts change.
3. Filed and exported reports are identical with and without the note.
4. The sentence and counts come from plain code, with no model call; the rules and N values are settings with their reason.
5. Light and dark, both palettes; the buttons are in tab order; the note is announced politely.

## Link to other items

#26 (BL-183, on hold) is the earlier, smaller form of this; at review extend #26 or keep #167 linked. #203's sparkle (suggest a health) and #170's "health greener than the evidence" check share the same rules, so build the rules once.

## For Alan (open questions)

1. **On the project page, or only when you open the health editor?** The issue asks this. I recommend the project page, quiet, because a hidden warning is not read.
2. **Plain-code facts or a model-written sentence?** I recommend plain code: free, fast, never invents.
3. **Should Not now hide the note for good, or until the facts change?** I recommend until the facts change.
