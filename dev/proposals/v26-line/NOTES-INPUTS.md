# 2.6 release notes: inputs for the PM

What 2.6 changes for Alan, one line each, from the commit history of `origin/v26-g5-wip` (since v2.5.3) and the board.
Raw material for the plain release notes, not the notes themselves. "On the line" = merged into `v26-g5-wip` (34224dac);
"Waiting" = on its own branch, not yet merged: check before the cut. Already shipped in 2.5.x and left out: #238, #245,
#251, #252, #255, #264, #265, #97 (quiet hours, 2.5.3).

## Intake: one page for everything that arrives and waits (#232, on the line)

- Intake and Review are one page with one entry in the left bar and one badge; the old Review and Intake addresses open it.
- Three views, remembered in this browser: List, Board and Two panes.
- Stage boxes across the top (Arrived, Drafted and so on, with Show all), each with its count.
- Proposals are split into routine and needs-your-decision; **Approve routine** approves the routine group in one apply with one Undo.
- Click a meeting row to open it and again to close it; Enter, N (not needed) and H (later) work on the focused row.
- Process, Later, Not needed (with a reason) and Restore on each meeting row; **Process all ready** skips private meetings.
- **Add files** button, or drop files anywhere on the page; each file shows its size, likely project and a kind tag (transcript, minutes, not sure), and a "not sure" file waits for you to choose.
- Minutes written by someone else can be added as minutes: **Find work items** proposes items from them without drafting new minutes.
- A Search box finds meetings, files and proposals by title, project name or source; Esc clears it.
- **Calendar read hh:mm** with a refresh icon replaces the separate Calendar import step.
- A proposal that updates an existing item opens the whole item in the peek, each change marked "was → now", and you can edit what it changes.
- Previous and Next step through the proposals in the peek.
- A confidential meeting shows its title and times only; a private conversation never names a project.
- Today's Intake line, the badge and Close the day's Review now all point at the one page.

## Minutes view v2 (#268, on the line)

- One version of the minutes: what you see is what is filed and exported (no separate Internal and Distributed tabs).
- A **Track** column on every table: tick registers the line as a work item, cross removes it from the minutes, neither keeps it in the minutes only.
- Edit in place: click the words and type; Owner, Priority and Workstream are drop-downs in the row; Due opens the usual deadline box.
- "Needs details" (not "isn't in the people register") under an owner, with **Add details**.
- **Approve minutes** is one click with an Undo; a box appears only when a ticked item has a real problem.
- Minutes with nothing ticked can still be approved (covers the old "rejected every item" case, #261).
- One continuous sheet with a thin page marker; fit to width stops at 100%; table headers no longer stick over rows.
- Hover a row to light the transcript turn it came from; the transcript pane's open or closed state is remembered.
- Export as Word, PDF or HTML, and **Draft the follow-up email** from the Export menu, both follow the Track choices.
- A risk or issue keeps its workstream from the minutes.

## Approving minutes from Intake follows Track (#275, on the line)

- Approve on a minutes row in Intake does exactly what Approve minutes does: ticked registered, crossed removed, neither kept untracked.
- Approve routine, the group tick and `review.py approve` never approve a line you crossed or left with neither.

## AI drafts and checks (#186, #262, #263, on the line)

- Draft email: the AI bar (Improve, Tone, Ask) is back for recipients outside your own domains, working from client-visible facts only, with the client checks on its reply.
- AI on the minutes: a suggestion that adds something internal (an item not client-visible, a name, internal wording) is dropped with a message saying why.
- Client messaging field: AI suggestions use client facts only and get the same reply check.
- The item editor offers AI on selected text.

## People you follow on Today (#236, on the line)

- What the sweep takes from a followed person's mail or chat (proposals, a memory note) is a **From <name>** row in Needs attention, listing each item.
- Dismissing a From row keeps it gone until the thread adds something new or changes an open item.
- A private conversation is a title and times only; a confidential thread stages nothing.
- No label anywhere says the person is followed.

## Settings, People and project settings (#246, #247, #248, waiting: settings line)

- Settings is reorganised into tabs, one card per group.
- People and projects leaves Settings: the People page becomes the home of the whole register (add, edit, rename, merge, remove).
- Every link to a person opens the People page.
- Remove from the register is refused while the person still owns items or is named as a stakeholder, milestone owner or workstream lead.
- Project settings v2: one scrolling page with General, People on the project, Workstreams, Logos, Reporting, Archive and close.
- Old Settings addresses for People, Workstreams and Projects redirect to their new homes.

## Work items refinement (#241, waiting: v26-work-items-abc and -d)

- Work list is compact by default (one line, ID beside the title), with a Comfortable option.
- Status and priority marks beside the columns; a client tag beside the ID.
- Closed items are folded by default where you have saved nothing.
- Keys on the cursor row: arrows move and open, S, O, P and T change a property, C closes (with Undo), V toggles client-visible.
- One-click Client-visible: the eye in the peek bar, the row menu or V.
- A work item's complete change history in the peek (every field, every route, undo).
- Your saved layout (widths, order, grouping, board collapse, saved views) survives the update.

## Draft email delivery (#183, waiting: v26-draft-delivery-fix)

- A setting (off by default) to put a Draft email straight into Outlook as a draft, under Essentials' new Draft email card.
- The preview, Copy email and the Outlook draft use the same Outlook-safe formatting.
- A chase you drafted is marked sent when the sweep sees it in Sent Items (subject, To and time only).
- Settings shows an Outlook access Check row.

## Transcripts fetched as they appear (#250, waiting: v26-fetch-transcripts)

- A sweep step (off by default) fetches a meeting's transcript once the meeting has ended, so it is ready on Intake.
- Never fetches a meeting that hasn't ended; a confidential meeting fails closed.

## Smaller fixes on the line

- Intake never scrolls sideways at 900 or 1440 px.
- A file dropped in the inbox gets its row at once, and Today's line and the badge show the same number.
- Esc on an AI suggestion keeps your words; Re-extract keeps unsent text in ask creaite.

## For the PM: wording still to settle

- Several on-screen labels still say "Review" for what now lives on Intake: "Draft in Review" (Today's day line), "Open in Review" (From rows), "n proposals in Review", "n left in Review" (minutes bar), "n new items in Review" (snack), "Save for later puts them in Review" (Find updates tip), "for Review" (Close the day). Help quotes them as shown.
- The minutes' AI message still says "the Distributed version would carry", though the view now has one version.
- Help on this line still describes Settings › People and projects; it changes when the settings line merges (that branch carries its own help commit).
