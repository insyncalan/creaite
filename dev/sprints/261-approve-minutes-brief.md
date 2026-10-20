# #261 Approving minutes after rejecting items (2.5.3): PM decisions

Cause (Team Cap, from the code): `review.py` `minutes_differences` drops rejected items before comparing the draft with the staged items, so with everything rejected every drafted line looks like a difference and the approval is refused ("the draft differs from the staged items"). A rejection is a decision about an item, not a difference from the draft.

## Proposed decisions (waiting for Alan's yes, 20-10-2026)
1. **A one-click "Approve minutes, take no items"** next to Approve routine on a minutes proposal: it rejects every item and files the minutes in one step. A plain Approve on the minutes also works after any items are rejected by hand.
2. **Wording.** All rejected: "Minutes approved. No items were taken into your work." Some rejected: "Minutes approved. 3 of 12 items taken; 9 rejected."
3. **Rejected items stay in Activity's rejected list** as today, so Quality still counts them.
4. **"Rebuild the items from the draft" never silently undoes a rejection:** it asks first.

## What the fix must do (Cap's list stands)
Match the draft against ALL staged items, rejected included; skip the owner, due and "not staged" differences for a rejected match; a line added to the draft in Word after staging, or a changed owner on an approved item, still stops the approval with today's message and buttons. The dashboard route and `review.py approve N` give the same answer. Not a guarded file. The Intake page in 2.6 (`rvDecideMany`) uses the same path: check it there too.

## Note line for 2.5.3 (draft)
"You can approve a meeting's minutes after rejecting some or all of its items; previously creaite refused if every item was rejected. A new 'Approve minutes, take no items' button does both in one click."
