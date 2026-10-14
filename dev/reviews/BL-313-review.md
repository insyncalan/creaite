# BL-313 Plain words: review pack

**Status:** in v2.1.0 (Alan, 13-10-2026; moved from v1.9.1). **On hold:** Alan reviews all of this before BL-313 is committed to a sprint. Nothing here is agreed until he does. The backlog entry (`dev/BACKLOG.md`, BL-313) stays as written until then.

## What was found (13-10-2026, main)

| Where | What reaches Alan |
|---|---|
| Dashboard source (`system/templates/dashboard/src/`) | About 118 visible strings with staged, apply or proposal: panel 31, review 21, server messages 15, ask 13, settings 10, milestones 9, activity 6, today 4, the rest 1 or 2 each |
| `system/templates/help.md` | About 120 uses: apply 53, proposal(s) 33, staged 20, applied 14 |
| Server messages shown on the page (`live_server.py`) | Some, e.g. "that proposal has already been applied or removed" |
| ask creaite | ASK_PROMPT and CONFIRMED_PROMPT are clean; cx-edit (4 lines) and cx-review (6) say "at the next apply", and the model repeats them |

Examples: "Nothing to apply", "Staged: … Nothing reaches the tracker until you apply", "saved; press Apply to write it", "Applying needs the live server", "Filter the proposals", "Keep the items as staged".

**Size:** M rather than S. Each change is mechanical, but they're spread across most screens.

## Proposed glossary (first deliverable, as `dev/WORDS.md`)

| Today | Auto-apply on | Auto-apply off |
|---|---|---|
| staged (Alan's edit) | saving… → Saved · Undo | Ready to save |
| proposal (creaite's) | suggestion, waiting in Review | same |
| Apply / applied | not shown | Save / saved |
| Approve a suggestion | Approved (saved, no second step) | Approved, ready to save |
| "Applying needs the live server" | "Not saved yet: creaite's server isn't running" + how to start it | same |
| Undo last apply (Activity) | Undo the last save | same |
| "Nothing to apply" | not shown | "Nothing to save" |

Sibling items write their new text in these words from the start.

## Open questions in the write-up

1. **One save, many changes.** "Approve routine" on 12 items is one apply, so its Undo undoes all 12. The wording should say so, e.g. "Undo: 12 changes saved at 14:02".
2. **Settings search.** Typing "apply" should still find the auto-apply switch. Keep the old words as hidden synonyms, on the allow list.
3. **Skills are shared with the terminal,** where "apply" is a real command. Skills keep their wording; ASK_PROMPT adds a vocabulary rule for the panel only. A prompt can't guarantee the result, so BL-314's reply check should also flag the three words. That makes BL-313 and BL-314 worth building together.
4. **Help documents typed commands.** "Apply" stays only in an "In Claude Code" section, on the allow list.
5. **Excel's Review sheet** isn't mentioned in the write-up. Proposed: in scope. The debug log and doctor output stay out.
6. **Code identifiers** (e.g. `data-rv="as-staged"`) must not count. Strings with no space in them are treated as identifiers.

## Proposed check

- **Static ratchet (the gate):** check.py scans string literals in the dashboard source, help.md, the prompt constants and server messages. It counts banned words outside an allow list where each entry gives its reason. The baseline only goes down and must reach 0 before release.
- **Rendered text (the truth):** a test scans the visible text of BL-254's snapshots with auto-apply on. It covers the click-through in "Done when" for the states that have snapshots.

## Order and clashes

- Glossary first (about half a day); then the sweep of old strings in one short sprint; the check lands last as the gate.
- The sweep edits panel.js and review.js heavily. Schedule it so the other v2.x work on those files rebases onto it rather than the reverse.
- BL-304 supplies the "saving" dot; BL-313 only names it. No dependency.

## Decisions for Alan

| # | Question | Proposed | Alan's decision |
|---|---|---|---|
| 1 | Keep auto-apply off at all? If nobody uses it, hiding the switch in the dashboard halves the copy and tests | Hide it in the dashboard; leave it in settings.json for Claude Code | |
| 2 | Is "suggestion" right for everything creaite proposes, including ask creaite's ideas and AI drafts? Or do drafts stay "draft"? | "suggestion"; drafts stay "draft" | |
| 3 | Excel export in scope? | Yes | |
| 4 | Size M and glossary as the first step? | Yes | |
| 5 | Build with BL-314 (reply check flags the three words)? | Yes | |
| 6 | Glossary table above as written? | Yes, after edits | |
