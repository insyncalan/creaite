# #307 identity guard: what to say under Known (2.6.1)

## A. For the release notes (Known, plain words)

- Every Approve, Reject, edit, Save in the peek, Approve routine and bulk action on Intake now checks what the item says, not its number, against the file at that moment. If the item has changed or was already approved, nothing is saved and you are told so.
- A change made in a second window, by a sweep or by an apply in between is refused rather than overwritten.
- A Save without approving keeps your edit and any newer edit to other fields of the same record. Approving is stricter: nothing is approved on content you have not seen.
- Known limit: a few actions are handed to the server as a reference (the drafts and conflict choices, Reject with a reason, repeats, retarget, and the held-minutes Approve and Discard). The page checks just before the call, but the check and the action are two steps. A second window, or a fast renumbering within that one request, could in rare cases act on a different item of your own pending list. A fully atomic check is planned for 2.6.2.
- Known limit: Discard on held minutes has no Undo until 2.6.2.
- Known limit: with an older live server, the content check still works but the write is no longer atomic.

## B. Design notes for reviewers

**Fingerprint.** First 12 hex of SHA-256 over a canonical JSON (sorted keys, NFC strings, fixed number form; spec in `core/identity.js`, twin `build_dashboard.item_fp`/`block_fp`, vector-tested). Item: `[op, table, id, changes, values]`. Block (minutes, report, file changes): `[key, title, draft, project, projects]`. Left out: the item number, the decision, and `values.raised`. The engine fills `raised` on new risks and issues and rewrites it whenever an apply saves the file, so including it made an item "change" when another item was applied (Save and approve then said already changed).

**Matching (`findGuarded`).** Block rows: the block must exist and match. Item rows: the item at the row's number if its fingerprint matches; otherwise the single other item with that fingerprint (the row's ref is moved to it); two or more other matches, or none, means refused. If the item at the number matches, it wins even where an identical twin exists elsewhere, so two identical items in one file are not told apart by content, only by position. A row with no fingerprint (older model) is trusted at its number, with only the server's changed-file check.

**Writes (`editProposal`).** One queued read, check, mutate, write per edit. The write carries `expect_text` to `/api/fs`, so a file that changed between read and write is refused ("already approved or changed"). After a saved edit the row's fingerprint is refreshed and the Intake model's remembered fingerprint follows (`snapFollowEdit`), so an edited row does not vanish until a rebuild. Model rows are remembered as file, number and fingerprint (`SNAP`); `rowFor` resolves them on the freshly loaded list the same way.

**Relaxed plain Save.** Peek Save without approving passes `same={table,id}`: an update still at its number for the same record counts as the same item even if other columns moved. Only the columns Alan edited are merged into the file's `changes`. Approve passes no `same`, so it needs an exact fingerprint match.

**Routes.** Page-side writes (approve, edit, peek save): atomic as above. Server-side by-reference routes (`/api/review`, `/api/review/reject`, draft, conflict, repeat, retarget, held minutes): `guardFresh` reads each file and keeps rows whose content is still there, then calls the route with file and ref. Check and act are two steps.

**Known limits.**
1. By-reference routes are not atomic. A raw call with no or a wrong fingerprint, a second window or a renumbering inside that one request can act on another item of the user's own pending list. Cap's check c55 (`/api/review` with a stale `expect`) is an expected failure. Fix planned for 2.6.2 (#314, approved): a guarded `review.py --expect <fp>` and a pass-through in `/api/review`.
2. An older server that ignores `expect_text` keeps the content check but loses atomicity.
3. Discard of held minutes has no Undo until 2.6.2 (needs a guarded restore route; added to #314).
4. Rows without a fingerprint (older model) are matched by number only.
5. Two identical items in one file cannot be told apart after a renumbering (refused, not guessed). Before one, the position decides.
6. Reported but not re-verified here: a stale minutes view whose held flag is out of date may still bump a minutes version on a failed approve. The claim comes from the brief, not from a check of the code.
7. Check again (calendar row) shows no outcome on the page, and the Chrome app-window file picker is unproven; both are in NEEDS-ALAN.md and are not part of the guard.

## C. What a user sees

- "That one was already approved or changed, so nothing was saved. The list has been refreshed." and the list reloads.
- Approve routine or a bulk Reject: the rows still the same go through; "n changed since you looked, left for you" names the rest. If none are left, the message above.
- A Save in the peek keeps your edit and does not undo a newer edit to other fields of the same record.
- If the page cannot find the row any more after a refresh, there is nothing to press, and nothing is saved.

## D. Known (autostart card on Macs; added 24-10-2026)

For the release notes, if the page fix is not in 2.6.1:

- On a Mac, the first-run "Start creaite when you sign in?" card can appear just after Today opens and move what is below it by a line. A click made in that moment can land on something else. Nothing is lost, and approvals are still checked against the item itself.

Reviewer note (corrected): the late status answer from the autostart route inserts the question card at the top of Today about 40 to 60 ms after first paint, which shifts the content below it, so a coordinate click measured just before can land elsewhere (the panel itself is not reset). Measured on a Mac: the first bad commit is the guarded-chain commit that adds the route; the failure rate is the same at low and high machine load. CI does not see it because Linux reports "Only on a Mac" and the card never appears there. The fix is page-side (branch v261-asrace, planned for 2.6.2): the late status updates only the question card's own node, and the boot status read is awaited by the test harness; a product-level fix (reserve the space, or await the status before the first Today paint) is part of the 2.6.2 item.
