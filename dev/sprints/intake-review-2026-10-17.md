# Intake: review and a better way to operate it

Product Manager, 17-10-2026. For Alan. Nothing here is built or on the board; it is for discussion before any mockup. Screenshot of the page today: `dev/sprints/intake-review-2026-10-17/intake-today.png` (fictional data; the audit vault has no calendar, so the meeting table's nine columns are read from `intake.js`, not seen).

## The short answer

Intake works, but it is a toolbox rather than a process. You arrive, find the meeting, tick it, choose between five buttons, wait, then go to Review. creaite already knows which meetings have a transcript (the sweep checks), so most of that is creaite asking you to do its bookkeeping. The better question is not "how should Intake look" but "what is the one decision Intake asks of you, and can creaite have everything ready before you ask?"

Recommended model: **one queue, one decision per row, prepared in advance, ending in Review.**

## 1. The page as it is

What it does well: sentence-case section headings like the rest of the app; the primary button, tick targets and tokens match; nothing is processed without you; Clear day is undoable; skipped meetings carry a reason.

Where it falls short of our own standards:

| # | Finding | Standard it misses |
|---|---|---|
| 1 | **Five verbs for one job.** Refresh, Select new, Select with transcripts, Load into inbox, Process selected. "Load" is an internal step (Process already loads first). | One obvious next action |
| 2 | **Select new and Process selected appear twice** (Calendar import and Upload files), and Process selected looks disabled even when it is not (UX review finding 9, #172). | Same control, one place; disabled must look disabled |
| 3 | **Tables, where Review uses rows.** The meeting table has nine columns; State and Transcript overlap; Where and Organiser rarely change a decision. Review and Today use one row anatomy. | Consistent row pattern |
| 4 | **Four words for "not this one"**: Clear day, ×, Remove, Skipped. Review asks for a reason when you reject; Clear asks for none. | One verb, with a reason (Review's pattern) |
| 5 | **Old word leaks.** The page says Intake; the buttons and states say "inbox" ("Load into inbox", "in the inbox, not processed yet"). | One name |
| 6 | **Counts disagree.** Today counts meetings with a transcript ready; Intake's badge counts files only. The More badge can say 2 while Intake looks empty. | One count, one meaning |
| 7 | **Empty states are dead ends** ("No calendar yet…", centred plain text). No link to how it works, no next step beyond Refresh. | Empty state names the next step (Help Phase B) |
| 8 | **No age, no order of urgency.** Review is getting age that means something (#177); Intake rows have none. A transcript waiting four days looks like one from this morning. | Age as quiet text, outliers marked |
| 9 | **No sense of finished.** Processing opens ask creaite, the row says "Draft ready in Review", and you leave. Nothing tells you what came out. | Say what happened and where it went |
| 10 | **Two homes for the same job.** Today's "Intake and Review" (#168) already lists transcripts ready and has Process the transcript. Intake the page does it again, from More. | One job, one primary place |
| 11 | **Project chosen twice.** A dropdown per meeting here ("Not sure"), then "Needs a project" in Review. | Decide once |
| 12 | **Keyboard.** No row focus, no Enter to process. Review has One at a time and shortcuts. | Same keyboard story across queues |

Everything needs the live server; that is correct but the page says so in each button's tooltip rather than once.

## 2. What other tools teach (and what I could not confirm)

- **Linear's Triage** ([docs](https://linear.app/docs/triage)): an inbox for things that arrive from outside, with a fixed small set of decisions, each on a key: Accept (1), Duplicate (2), Decline with a comment (3), Snooze (H). Snooze returns the item at a chosen time or when it has new activity. Triage can have a rotating owner. Lesson: **few decisions, the same every time, reasons optional but offered, snooze built in.** Our equivalent: Process, Not needed (with reason), Later.
- **GTD's clarify step** ([two-minute rule](https://gettingthingsdone.com/2011/06/when-to-use-gtds-two-minute-rule/)): processing is a pass in sequence, deciding what each thing means, not doing the work; the two-minute rule is for processing, not for living. Lesson: **Intake should be a quick pass of decisions, with the heavy work (the AI draft, your review) happening elsewhere.**
- **Superhuman's triage question** ([onboarding](https://blog.superhuman.com/inbox-zero-in-7-steps/)): for each message, is it for today, for another day, or done? Plus processing at set times and splits by type. Lesson: **three outcomes, a regular ritual, and grouping by kind.** creaite already has the ritual (Close the day lists Intake in Loose ends).
- **AI meeting-note practice** ([general guidance](https://www.lowcode.agency/blog/ai-meeting-notes-and-action-items), [staged trust](https://cc-archos-labs.onrender.com/blog/ai-meeting-minutes)): review before sharing because extraction misses owners and dates; one accountable reviewer per meeting; start with a few weeks of checking everything, then a short owner check, then drop review for low-stakes recurring meetings. Lesson: **trust should be earned per meeting series, from your own approval history.** That is exactly what Activity › Quality already measures.

Not found: how Fellow, Granola or Fireflies hold action items before syncing. I would not copy a vendor behaviour I have not seen. The search for Things and Sunsama also returned nothing usable.

## 3. Five changes to how Intake operates

**A. One queue, one decision per row.** Meetings that have ended and dropped files become one list, same row anatomy as Review and Today: title, when, project guess, transcript state, age. Three actions: **Process** (primary), **Not needed** (with the Review-style reasons: "Informal chat", "No decisions", "Duplicate of another meeting", "Other"), **Later** (stay, come back when a transcript arrives). Groups: Ready (transcript there), Waiting (no transcript yet), Done recently. Kills findings 1, 2, 3, 4, 8.

**B. Buttons that match the work.** One **Process all ready (n)** and a per-row Process. "Select with transcripts", "Select new" and "Load into inbox" go (Load stays an automatic first step). Refresh stays, quieter. Keyboard: arrows, Enter to process, N for Not needed, H for Later, as Review does. Kills 1, 2, 12.

**C. Prepared before you arrive.** Three stages, each a separate decision for you:
1. *Now:* the sweep already finds transcripts. Show them with age and the project guess.
2. *Optional, load only:* when a transcript appears, creaite fetches it into Intake (a read, no AI, nothing written to the tracker). Process is then instant to start.
3. *Optional, by series, later:* "Draft minutes for this series automatically" for a recurring meeting you have approved many times. The result is only proposals in Review; nothing is filed. Offered per series from your own approval numbers, never on by default. This touches unattended runs, so it needs Jarvis and your approval before anyone designs it, and it belongs after the 13-11-2026 review of the AI ideas, which is where Triage and routing (#163) and Meeting to RAID log (#165) already wait.

**D. Say what came out, and finish in Review.** After a row is processed it reads "7 proposals: 4 actions, 2 risks, 1 decision" with **Review them** (opens Review on just those). The ask creaite panel stops opening by itself for a normal run; progress shows on the row. Kills 9.

**E. Give the two places two jobs.** Today's Intake and Review is the **daily pass**: what is ready, one line each, Process or open. The Intake page is the **workshop**: the full list and history, uploads, set-asides and Cleared. Both use the same queue data and the same row, so a change in one shows in the other. Fix the count (6): Intake's badge counts ready meetings plus files, as Today does. Kills 6, 10, and most of 11 (the project guess shows once, editable, and travels to Review).

Smaller items that ride along: a "How Intake works" link in empty states (Help Phase B), the word "inbox" removed from every button and state, age as quiet text (the Review age pattern, #177), a drop target that works anywhere on the page, and one line for the live-server need instead of a tooltip on every button.

## 4. A bigger idea, not recommended yet

One page with a **pipeline**: Arrived (3) → Drafted (4) → Approved, replacing Intake and Review as separate destinations. It is the cleanest picture of the work, but it re-cuts the sidebar and the names you just settled (#168, #156), and Review's rows carry far more weight than Intake's. Revisit after the 13-11 review, when we know whether auto-drafting is real.

## 5. How I would stage it

| Step | What | Size | Needs |
|---|---|---|---|
| 1 | A and B: one queue, one decision, reasons, fewer buttons, wording and badge | M, `review` | Nothing guarded. Sits well after #168 and #177 so the row pattern is shared |
| 2 | D and E: result on the row, Review opens on just those, Today and Intake share the row | M | Step 1; Help Phase B for empty-state links |
| 3 | C2: load a transcript when it appears | S to M | Alan's yes (a read, but unattended) and Jarvis's check on the guarded files |
| 4 | C3: auto-draft by series | L | After 13-11-2026; Alan's decision; ties to #163 and #165 |

Step 1 alone removes most of today's friction without changing what creaite does.

## 6. Questions for you (recommendations first)

1. **Is "Load into inbox" ever useful on its own?** Recommend no: load and process happen together; drop the button. If you sometimes load now and process later, "Later" covers it.
2. **Are Organiser and Where worth a column?** Recommend no: show them in the row's detail, not the row.
3. **Should the ask creaite panel stay shut while a normal Process runs?** Recommend yes, with progress on the row and the panel one click away.
4. **Which first: step 1 alone, or steps 1 and 2 together?** Recommend step 1, then step 2 as its own item, so the row pattern can be checked before it is shared with Today.
5. **Stage C2 (auto-load): interested, later, or never?** Recommend later, decided with the 13-11 review.

Next, if you agree the direction: a mockup of the queue (Ready, Waiting, Done recently) with the three actions and the result line, in the same style as the Review age mockup, with a state switch for "all ready", "mixed ages", "nothing waiting" and "just processed".
