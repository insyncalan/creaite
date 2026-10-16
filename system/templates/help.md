<!--
creaite help. The one source for the dashboard's Help page (press ?, or Settings › Help), which has three tabs, and for
the two printable guides, system/templates/guide-first-day.html and guide-how-to.html. Edit it here, then run
python3 dev/tools/build_guides.py (a test fails while the guides are out of date). It reads as plain Markdown;
`Cmd` on Mac, `Ctrl` on Windows. The few conventions the renderer understands:

- The three parts are the H1 headings "Start here", "How do I…" and "Reference". Each ## is a section or a task.
- A part's opening and any section may have: an all-italic line (the small label above the heading), an all-bold line
  (the heading to show, when it differs from the ## title) and plain paragraphs (the lead-in).
- Start here, The loop: a numbered list of five stages, "**Title** (Label): text", with optional indented bullets.
  {you: The only gate} on a stage marks the one step that needs you. The paragraph after the list is the return line.
- Start here, Your first hour: numbered "**Title**: text". Every day: bullets "**When**: **Title.** text".
  Where things are: bullets "**View**: what it shows", then a "Keys:" line. Say this: a table. Four rules: bullets "**Rule**: text".
- How do I…: a "### Group" line before its tasks. Each task has "Where:", numbered steps and "Or say:". Link to a task
  with [text](#its-title-in-lower-case-with-hyphens), and to another part with [text](#how-do-i) or [text](#start-here).
- Inline: **bold** is a button or label, `code` a command or path, ``double backticks`` a phrase to say. Single
  backticks are phrases too in "Or say:" lines and in the Say this table. [[K]] is a key.
- A line of --- at the end of a part, then lines of text, is its footer.
- {version} becomes the installed version. A paragraph that is only [start command] becomes this vault's server command.

Only this first comment is dropped: a comment anywhere else would show on the page.
-->

# Start here

*creaite {version} · first day*

**Claude drafts. You approve. creaite keeps the record.**

creaite reads your meetings, mail and Teams, proposes the actions, decisions, risks and issues it finds, and keeps them in one tracker once you approve. The tracker, the engine and your history stay in one folder on your Mac.

## The loop

Every piece of work follows the same five steps. Only step 3 needs you, and nothing reaches the tracker without it.

1. **Material arrives** (In):
   - Meetings you pick from your calendar (Intake › Calendar import)
   - Transcripts and minutes you drop in (Upload files)
   - A note from a call or your own thinking ([[⌘⇧N]]), turned into items with Find updates
   - The daily mail and Teams sweep
2. **Claude drafts** (Propose): Draft minutes and proposed items, each citing its source and matched to a project and owner.
3. **Review** (You) {you: The only gate}: In Review, approve, edit or reject each proposal. Routine items can be approved together; minutes, new decisions and new risks one at a time.
4. **Apply** (Record): Approved items go into the tracker and the minutes are filed. Edits you make yourself save at once; **Apply** is for what Claude proposed, and can be undone.
5. **See and report** (Out): The dashboard updates at once. Weekly and client reports are drafted from the tracker as creaite pages, and you approve them before they are filed.

The next meeting starts the loop again. When it discusses an open item, Claude proposes an update to it, never a duplicate.

## Your first hour

*Once*

About an hour, mostly telling creaite about your projects and the people on them. Three words first: the **vault** is creaite's folder on your Mac, the **launcher** is the creaite app that opens it, and the **live server** is the small program behind the page, which the launcher starts for you.

1. **Install**: Download **creaite-{version}.zip** from the release, not "Source code", and run it with Python 3 as the release page shows. Choose a folder outside OneDrive and iCloud.
2. **Say "setup"**: Open the folder in Claude Code, connect Microsoft 365, and say ``setup``. It asks before each step: your name, projects, people and the launcher (say yes).
3. **Open creaite**: Double-click the **creaite** app. It starts the live server and opens creaite in its own Chrome window.
4. **First sweep**: Let setup run it, or press **Run the first sweep** on Today. Then open **Review** and approve what's right. Until set-up is done, Today shows a checklist of these steps. **Settings › Health › Set-up** runs the health check.

No launcher yet? In Terminal run the command below, then open the address it prints in Chrome or Edge, not Safari.

[start command]

## Every day

*Every day*

**The rhythm**

- **First session after 07:00**: **It catches up.** creaite backs up the tracker, runs the mail and Teams sweep if it's due, and lists reminders and what's waiting.
- **After a meeting**: **Bring it in.** On Intake, pick the meeting in Calendar import or drop its transcript in Upload files, then process it into minutes and proposals.
- **Whenever it suits**: **Review.** Clear Review in minutes, then check Today for what's overdue, due and changed. In the evening, [Close the day](#close-the-day).
- **Friday from 12:00**: **Report.** A reminder to run the ``weekly report``. Client reports follow each project's own schedule.

## Where things are

*The dashboard*

Your edits save at once, with Undo.

- **Today**: your meetings, what needs attention, your commitments, the week ahead
- **Intake** (under **More**): Calendar import and Upload files
- **Projects**: each project's state, health with its evidence, milestones and notes
- **Reports**: every project's week at once, its internal report and each client's, with a count of what needs you
- **Work**: every action, risk, issue and decision, with filters and saved views
- **People**: each person's open work, Draft email and handover
- **Review**: Claude's proposals, grouped by project
- **Files** (under **More**): minutes, transcripts and reports, with search that answers with sources
- **Settings** (under **More**): sweep time, reminders, health rules, registers, themes. **Activity**, also under **More**, lists every change, with Undo.

Keys: [[⌘K]] search or jump anywhere · [[⌘J]] ask creaite · [[J]]/[[K]], [[A]], [[R]] move, approve and reject in Review

## Say this

*Phrasebook*

**Say this in Claude Code or ask creaite**

Plain English works. **ABC** stands for your own project code.

| Say | What happens |
|---|---|
| `process new minutes` | Transcripts become draft minutes and proposed items in Review. |
| `sweep` | Outlook and Teams since the last sweep become proposals. It also runs each morning. |
| `review` · `apply` | Go through what's pending, then write the approved items to the tracker. `undo last apply` reverses it. |
| `mark ABC-A-003 done` | Any change in plain words, shown before → after. |
| `weekly report` | Health with reasons and a report page for each project, filed when you approve. |
| `client report ABC` | A client-safe report page. Only items marked client-visible appear. |
| `actions register for ABC` | A one-off branded Word document from the tracker. |
| `how is ABC going?` | An answer from the project's memory, the tracker and the files, with sources. |
| `setup` · `update creaite` | Health check and repair. Install a new release, shown first. |

## Four rules

*Never bends*

- **Your data stays yours**: The tracker, engine and history stay on this laptop. Project files and one daily backup zip may sit in your company OneDrive. Nothing goes to any other service.
- **You approve every change**: Nothing reaches the tracker until you approve. Scheduled runs only propose.
- **Every item has a source**: The meeting, email or chat it came from is always shown.
- **Clients see only what you mark**: Client reports show only items marked client-visible. Confidential material stays out.

---

Dates are shown DD-MM-YYYY. Keep the live server running while you use the dashboard. If it stops, a red alert appears across the top with the command to start it and **Check again**, and your edits wait until it's back. When mail and Teams were last swept is in Settings › Health › Live server and backups.
[How-to: step-by-step for common jobs ›](#how-do-i)

# How do I…

*creaite {version} · how-to*

**How do I…**

The common jobs, step by step. Each card says where to go on the dashboard, and what to say instead in Claude Code or ask creaite ([[⌘J]]).

### Every day

## Start the day

Where: the creaite app · Today

1. Open creaite: double-click the **creaite** app. It starts the live server and opens the page.
2. Open the vault in Claude Code. The first session after 07:00 backs up the tracker, runs the mail and Teams sweep if it's due, and lists what's waiting.
3. Read **Today** from the top: **First thing**, **Decisions needed**, **Needs attention**, **Your commitments**, **Intake and Review**, **Week ahead** and **Resolved**.

Or say: `sweep` to run the sweep again at any time.

## Close the day

Where: Today · ⌘K

1. At the end of the day, press the door icon in Today's header, or type "close the day" in [[⌘K]]. A card opens with four short steps. [[Esc]] is **Not yet** and keeps your place.
2. **Catch up.** If the last sweep is more than 30 minutes old, a sweep of your Inbox, Sent Items and Teams starts. It only proposes items for Review; nothing in Microsoft 365 changes.
3. **Today and loose ends.** See what moved and what you promised, then give each open item a place: **Review now**, **First thing tomorrow** (the default) or **Leave**. Nothing is approved or rejected here.
4. **Tomorrow.** See tomorrow's meetings; **Make prep page** queues a prep page for each. On a Friday it adds the weekly report. Press **Close the day**.
5. Next morning, **First thing** on Today lists what you put there. To be reminded, set **Evening, offer Close the day from** in Settings › Essentials › Your day: a dot appears on the door icon after that time.

Or say: `what did I promise today?` `what needs prep for tomorrow's meetings?`

## Review and approve proposals

Where: Review

Nothing reaches the tracker until you approve it. About two minutes on a normal day.

1. Open **Review**. Proposals are grouped by project, with items from minutes under their minutes.
2. Narrow the list with the search, **Kind**, **Needs** and **Source**, or the funnel icon (**Add a filter**).
3. Press **Approve routine** (the double tick). It shows what it will approve first. Minutes, new decisions, new risks and anything that closes an item are never included: approve those one at a time.
4. Open anything you want to check. Change what's wrong, then **Save and approve** ([[⌘↵]] saves). On the list, [[J]]/[[K]] move, [[A]] approves and [[R]] rejects. Right-click a proposal ([[Shift]]+[[F10]]) for the same choices and more.
5. Select several (click, ⌘-click, Shift-click or the tick on a group). A bar floats at the bottom of the window, however far you have scrolled, to approve them together or set their project, owner or due date. It says what it left out, with **Undo**.
6. Not sure about one? Press **One at a time**: one proposal with its source beside it, guesses first. [[A]] approves, [[R]] rejects, [[E]] edits, [[J]] skips, [[K]] goes back and [[Esc]] returns to the list.
7. Draft minutes are approved with **Approve** on their row (it needs the live server). **Open draft** opens them as a page in creaite, where you edit them beside the transcript: see [Turn a meeting into minutes](#turn-a-meeting-into-minutes). Once filed, minutes are never saved over.

Then: [Reject, with a reason](#reject-with-a-reason) · [Fix the wrong project](#fix-the-wrong-project) · [When it looks like something you have](#when-it-looks-like-something-you-have) · [When creaite says Looks done](#when-creaite-says-looks-done).

Or say: `review` `approve minutes for the ABC steering` `apply`

## Reject, with a reason

Where: Review

1. Press [[R]], a row's ✕, or **Reject with a reason** on the bar. One menu opens for one row or many.
2. Pick why: **Not an action**, **Duplicate**, **Chatter**, **Already done**, **Wrong project**, **Doesn't need tracking** or **For another team** ([[1]] to [[7]]). **Use each guess** ([[G]]) rejects every highlighted row with creaite's own guess, shown in grey on each row. **No reason** is [[0]]. **Duplicate** records the item it repeats, or asks which.
3. Changed your mind? A message with **Undo** puts the batch back. A rejected row stays, greyed, with its reason (**Rejected · Chatter**) until you leave Review: the chip changes the reason, and **Approve instead** undoes the reject and approves in one step.
4. **Activity › Quality › What you rejected** lists recent rejects with the same buttons. The reasons are counted in **Why proposals were rejected**.

Or say: `reject 4 as a duplicate of ABC-A-009` `reject 3, 5 as chatter` `reject 2-6 with their guesses` `approve that reject instead`

## Fix the wrong project

Where: Review

1. Press **Project** on the item's row, or its Project value at the top of the open item, and choose another. The old project's milestone and workstream are cleared, and the item waits for your decision.
2. For draft minutes, **Project** on the minutes' row moves every item from them. If they cover several projects it asks whose items first, then says what will happen ("Move 9 items from Example Programme to Delta Rollout") before you press **Move**.
3. The files go to the new project's folders only when the minutes are approved. **Undo** moves everything back.

Or say: `9 is DEF` `minutes 3 is DEF`

## When it looks like something you have

Where: Review

1. A proposal that repeats something in the tracker says **Looks like ABC-A-009 (same project, open) · Very likely**, or **Possible**. Another project's name, or **closed**, shows where it is.
2. Open it and press **Compare** to see the two side by side, with the new source.
3. Choose **Merge as an update to ABC-A-009** (new dates or updates go to the existing item, and you approve them; with nothing new it is rejected as its duplicate), **Keep as new**, or **Reject as duplicate**. Merge is offered only for an open item in the same project.
4. Nothing flagged, but it is news about something you track? Open the proposal and press **Update an existing item instead** (or right-click its row). Choose the item from that project's open items, best matches first. The proposal becomes an update that waits for your approval; **Undo** in the message puts it back. It needs the live server.

Or say: `merge 4` `keep-new 4` `4 is an update to ABC-A-009`

## When creaite says Looks done

Where: Review

1. When a mail you sent, a reply, a Teams message or a meeting shows an open item is finished, the row leads with **Looks done** (or **Maybe done**, with the reason) and the evidence. **Open source** opens the message.
2. **Approve** closes it. **Reject** with a reason says why, and the extraction reads it next time. **Not done** re-dates an item that has moved.
3. Closing is always approved on its own, never by **Approve routine**.

Or say: `approve 4` `reject 4 as already done`

## Find anything

Where: ⌘K · Files › Search the vault

1. Press [[⌘K]] and type: a project, an item ID, a person, a view, a milestone or a file name.
2. To search inside meetings, reports and documents, use **Search the vault** at the top of Files. Codes, names, types and dates such as "last month" become filters.
3. Type a question ("what did we agree about the pilot?") and press Enter. Claude answers from your files, with a source on every point.
4. [[⌘K]] makes changes too: see [Change an item from ⌘K](#change-an-item-from-k).

Or say: `how is ABC going?`

## Change an item from ⌘K

Where: ⌘K, anywhere

1. Press [[⌘K]] and type the change in words: "move ABC-A-002 to fri", "mark the UAT room action done", "Omar owns the SOW action", "reopen ABC-A-004" or "add action for ABC: send the SOW, Sara, Friday". Name an item by its ID or by words from its title.
2. The change is listed first, marked **Change**, with each field before and after and what else it touches: items tied to a milestone, a weekend date, an owner creaite doesn't know. For a new action, chips suggest an owner, due date, workstream, milestone or priority read from your words. A click adds one.
3. If two items or people match, it asks which. Press Enter to make the change, with **Undo last** after it, or [[⌘↵]] to make it and open Review. Esc changes nothing.
4. Something it can't read as a change is offered to ask creaite. Nothing in ⌘K deletes. With an item open, [Change an item in words](#change-an-item-in-words-sneak-peek) is quicker.

Or say: `move ABC-A-002 to fri` `Omar owns the SOW action`

## Find a person's open work

Where: People

1. Open **People** and select the name. **With work** lists everyone who has an open item, you first.
2. Their page shows the actions, risks and issues they own, grouped by project, and the decisions you are waiting on from them.
3. **See all actions in Work** opens Work filtered to them. Or press [[⌘K]] and type their name.

Or say: `what's open for Omar?`

## See what changed on a project

Where: Activity · a project's page

1. Open **Activity**. It lists every change, newest first. Search by project, words, a person or a date, or use the **Kind** menu to narrow it.
2. On the project's page, **Flow** shows what opened, closed and went overdue each week, and how its milestones have moved.
3. Press **Undo** on any change in Activity to reverse it.

Or say: `how is ABC going?`

### Meetings

## Turn a meeting into minutes

Where: Intake › Calendar import or Upload files

1. **From the calendar:** in **Calendar import**, meetings with a Teams transcript are highlighted (**Transcript**). Press **Select with transcripts** (or tick meetings), then **Process n selected** to load each transcript and its meeting chat and go straight on to draft minutes, or **Load into inbox** to bring them in without processing.
2. **From a file:** drop the transcript or minutes on **Upload files** (.vtt, .docx, .txt, .md or .pdf). Tick it and press **Process selected**.
3. Wait for **Draft ready in Review**. You get draft minutes (a page in creaite's own format, filed as `YYYY-MM-DD <Meeting title>.html` when you approve them), new items, and updates to open items the meeting discussed.
4. Approve in [Review](#review-and-approve-proposals). Nothing is filed until you do.

5. **Was the agenda discussed?** If the meeting had an agenda in the project's Agendas folder, or a prep page, the minutes record each point as **Covered**, **Touched on** or **Not discussed**. Review shows it on the minutes' row, and the [meeting's page](#follow-a-meeting-from-invite-to-follow-up) has **Carry to the next agenda**, which puts a missed point on the next prep page of the same meeting, under "Not covered last time".

Or say: `process new minutes` `process Tuesday's ABC steering`

## Capture a note

Where: any page · [[⌘⇧N]] · ⌘K "New note" · Today › a meeting's **Note**

1. Press [[⌘⇧N]] on any page, or **N** when you aren't typing in a box. The note opens at the right and the page stays where it was.
2. Type. creaite guesses the project from the register and says why ("guessed from “Omar Ali”"). Change it in **Project** and it stays your choice. With no guess the note is **Unfiled**.
3. It is kept as a draft as you type. [[Esc]] or × closes it and keeps the draft: [[⌘⇧N]] carries on, and drafts are listed under **Recent notes**.
4. Press **Done** ([[⌘↵]]) to save it in the project's notes folder, named by its title. **Done and find updates** saves it and opens it on the project's Notes tab with Find updates.
5. **Confidential** keeps the note out of prep pages and client reports, and Claude reads its text only if you say yes. On Today, **Note** under a meeting starts a Working session note.

Or say: `note: Sara confirmed the pilot extends to 60 agents`

## Keep notes on a project

Where: Projects › a project › Notes · Projects › Portfolio notes

1. Open the project and choose the **Notes** tab, beside Overview. Press **New note**, give it a title and choose a template: **Blank**, **Stakeholder**, **Lessons learned** or **Working session**. **Make the note** saves it in the project's notes folder.
2. Click and type: there is no Edit, Save or Cancel. A formatting bar shows on one line while the cursor is in the note: **Heading**, bold, italic, strikethrough, code, **List**, a quote, **Link** and **Insert** (a note, a person, a work item, a table, a picture). Press Tab to reach the bar, then the arrow keys, and [[Esc]] to go back to the text. [[⌘⇧K]] adds a link. Your typing is kept as a draft at once, and the note is written when you leave it or after 30 seconds without typing. The header then says **Saved**.
3. Link as you type: two square brackets link another note, `@` a person, `#` a work item, and `/` opens a menu under the cursor (Text, Heading 1 to 3, lists, a checklist, a quote, code, a table, a picture, a link or a template). Type to narrow it. ⌥-click a link to put the cursor in it.
4. Change the title and the file is renamed to match when the note saves. Links to it in your other notes follow.
5. Select some text and press **AI** to rewrite it, shorten it and more ([Let creaite draft the wording](#let-creaite-draft-the-wording)). The ⋯ menu pins the note, marks it **Confidential** or shows the file.
6. **Delete note…**, last in the ⋯ menu, moves the note to the project's archive, never away for good. A box asks you to confirm, then the move waits on the approval card in ask creaite, and only **Approve** moves it. The toast's **Undo** brings it back, and **Files › Archived** has **Move back**, which never replaces a note that has taken its name (it comes back as "<name>-2"). Links to it show as missing until it is back.

Or say: `what do my ABC notes say about the sandbox?`

## Turn a note into tracker changes

Where: a note › ✦ Find updates · the note drawer's **Done and find updates**

1. In a project's note, press **✦ Find updates** (it needs the live server; an Unfiled note asks you to move it to its project first). Claude reads the lines that are new or changed since you last ran it, and **Found in this note** opens beside the note.
2. Each line that gave a change has a numbered marker, and its rows carry the same number. Rows are grouped **New**, **Updates to existing items**, **Milestones** and **Project information**.
3. Routine rows start ticked. New risks, new decisions, milestone moves, health changes and memory lines start unticked: tick them one at a time. A hedged line ("probably", "to confirm") is marked **Tentative** and can't be ticked. Click a row to edit it first.
4. Press **Apply n changes** to write the ticked rows as one change, with **Undo** in the message, or **Save for later** to put them in Review.
5. For one line only, select text on it, press **AI** and choose **Make this an action, a risk, a decision or an update**.

Or say: `note: Omar to send the paper by 20-10` (then Find updates on the note)

## Prepare for a meeting

Where: Today

1. On **Today**, press **Prep** under a meeting, today or any later day in the day line. Tomorrow's meetings also have **Prep** in the Week ahead. A meeting worth preparing for shows **Prepare** instead.
2. The popup shows the project, the series and who is invited, what has changed since the last meeting, and a brief: open actions, risks without a response, recent decisions, decisions still needed, revisit dates that have come and early warnings. What the invite is about comes first, and each line says why it is there.
3. Press a line to open its item over the popup and update it on the spot. Edits save at once, ↑ and ↓ step through the items, and [[Esc]] brings the popup back.
4. For more, see [The prep page](#the-prep-page). To run the meeting around one thing, see [Shape the meeting around one thing](#shape-the-meeting-around-one-thing). For text to paste into the invite, see [Draft an agenda](#draft-an-agenda).
5. For a 1:1, see what a person owes on their page, or [ask them for an update](#ask-someone-for-an-update).

Or say: `what's open for ABC?` `prep for the ABC steering`

## The prep page

Where: Today › Prep

1. Press **Open prep page** (it needs the live server). Claude reads the invite, recent minutes, mail and Teams, documents and your notes, never one marked **Confidential**. The page opens in creaite with its own address, so Back, reload and a bookmark bring it back.
2. It shows what the meeting is about, the urgent, overdue and due-soon items, the latest reporting, researched notes with a link to each source, and questions to ask. Tabs: **Prep**, **Invite** and **History** (the series).
3. **Refresh research** researches again. **Print** lets you take it with you. An icon beside **Prep** on Today goes straight to the last page.
4. It is saved in the project's Agendas folder, marked Internal. Nothing reaches the tracker.

Or say: `prep page for the ABC steering`

## Shape the meeting around one thing

Where: Today › Prep

1. Press **Shape this meeting**, first in the popup's toolbar (it needs the live server). Write the focus and what you want from the meeting. A suggestion (an item the invite puts first, an overdue item, a milestone due, or what wasn't covered last time) adds itself to your text.
2. Press **Shape**. Claude reads it read-only (**Stop** is there) and first says how it read you. If it misread you, press **change**, correct it and press **Regenerate**.
3. Draft notes appear in four boxes: **Objective**, **Talking points**, **Ask** and **Carried over**, each with its sources. Edit any box. **Regenerate** keeps your edits, and **let creaite redraft it** gives one back.
4. **What's in focus** lists the work items and documents linked to the focus, each with why. Untick one to leave it off the page, or press **Show everything instead** to show the rest after the focus.
5. **Accept** saves it for that meeting and the prep page shows your notes. **Discard** throws the draft away. Nothing reaches the tracker and nothing is sent. A confidential meeting is shaped from your text and the tracker only.

Or say: `prep for the ABC steering`

## Draft an agenda

Where: Today › Prep

1. Press **Draft agenda**, at the right of the popup's toolbar (it needs the live server), and choose **POAD** (Purpose, Objectives, Approach, Deliverables) or **POAD lite**, a short friendly paragraph.
2. creaite picks the points: the decisions that need the meeting, then overdue and urgent work, milestones due, and what wasn't covered last time (at most six, timed from the meeting's length). Claude words the invite text around them, and each sentence shows its sources. **Include who's invited** adds the attendee list.
3. **Copy** puts it on the clipboard formatted; **Copy as plain text** copies just the words. **Save to Agendas** keeps it in the project's Agendas folder, marked Internal unless you tick **Save it for attendees**. The minutes' coverage reads it later.
4. creaite never creates or changes an invite. For a confidential meeting Claude sees only its title and times.

Or say: `prep for the ABC steering`

## Follow a meeting from invite to follow-up

Where: Today · Intake · Files · Review · an item's source

1. Press **Meeting** beside a meeting on Today (or in the Week ahead), in Intake's meeting list, in the prep brief, beside its minutes in Files or Review, or in an item's source. Its page opens.
2. The strip shows where it is: **Invite**, **Prep page**, **Transcript**, **Draft minutes**, **Coverage**, **Review**, **Follow-up**, each done (✓), now (●), to do (○) or not needed (–).
3. **Next step** is one button: make the prep page, load or process the transcript, review the minutes and their items, or see the actions due.
4. Below: what the meeting produced (yours first), whether the agenda was covered, what was promised to you, and its files. Before the meeting, **Draft agenda** sits beside Make the prep page.
5. **Draft the follow-up email** (under What it produced) opens the follow-up: the attendees as **To** (from the invite, or the people register), a short thanks, the minutes' own summary paragraph, the decisions, and the actions grouped by owner. **Lead with** puts one person's actions first. Copy it into Outlook; nothing is sent.

Or say: `prep for the ABC steering` `process Tuesday's ABC steering`

## Why isn't my meeting in Intake?

Where: Intake › Calendar import

1. **The meeting isn't listed.** Calendar import lists meetings from Monday of this week to now. Press **Refresh** to read your calendar again. A private meeting is never listed.
2. **It is greyed and can't be ticked.** It hasn't ended yet, and becomes selectable by itself once it has.
3. **It says Not transcribed.** Transcription wasn't on, or the transcript isn't ready: one can appear hours after the meeting. Press **Check again** on its row.
4. **It says No transcript or No access.** An in-person meeting, or one with no Teams link, has no transcript, and **No access** means it can't be read. If you have the transcript, drop it in **Upload files**.
5. **You set it aside.** **Clear day** and a row's × hide a meeting. **Cleared (n)** under the list shows it, with **Restore**.
6. **Nothing is listed at all.** The calendar arrives with the sweep. Press **Refresh** or run `sweep`, and check Microsoft 365 is connected in Settings › Health.

Or say: `refresh calendar` `sweep`

### Keeping it right

## Move work on the board

Where: Work › Actions, RAID or Decisions › **Board**

1. Press the **Board** icon (columns) beside the **List** icon on the toolbar. The same items appear as cards in columns, with the same filters, search and views. **Display** (the sliders icon, or [[D]]) sets the columns with **Group by**. A **Sub-group** adds swimlanes, one row per owner, project or other value.
2. **Drag a card** to another column, or press **⋯** on the card and choose **Move to…**. Dropping on a Due column asks for the date. Status sets the status (closing fills today's date), Owner reassigns it (TBC clears it) and Milestone attaches it. **Overdue** isn't a place to drop: pick a date in another column. Esc cancels a drag.
3. The move saves like any edit, with **Undo** in the message. Click a card to open its details. Across a lane and a column, both changes are named first and it is one change with one Undo; **Move to…** offers the column and the lane separately.
4. **On the Decisions board** only a pending decision moves. Drag it to **Made** and the Record-the-decision form opens, filled in; to **Withdrawn** and creaite asks first; to another **Decision maker** to change who is asked; to a **Needed by** column to set the date. A decision that has been made or withdrawn stays where it is.

Or say: `move ABC-A-003 to 20-11-2026` `Sara owns ABC-A-003`

## Add or change an item

Where: Work · any item's panel

1. **New:** in Work, press the **+** tile at the right end of the toolbar (**New action**, **New RAID item**; on Decisions a menu offers **Record a decision** or **Ask for a decision**). The item opens over the page, empty. Type its title and set the values under it. The project is beside **New action** at the top, taken from the page when you are on a project.
2. **Change:** click a value in the list to change it there, or open the item (click its ID). It is ready to edit, with no Edit or Save: click the title or the text under it and type, or click a value (status, priority, owner, due date) to choose another. The rest (project, workstream, milestone, raised and closed dates, client-visible and client messaging) is under **Details**.
3. An owner is found by name, alias or email. A new name asks for their details. Dates take plain words: `fri`, `next week`, `+3d`, `15-10`. The field shows what it understood ("Friday 16-10-2026") before you save.
4. **A weekend due date is pointed out** ("Saturday 17-10-2026 is a weekend.") with the Friday before and the Monday after: one click sets that day. **Keep this date** saves the weekend day if you meant it. Dates that record what happened, and milestones, are never pointed out.
5. **Right-click** an action, RAID item or decision (in Work, a person's page, a project page, Today or Activity) for its common actions: **Open**, **Close** or **Reopen**, **Status**, **Owner**, **Due**, **Priority** (RAID: **Impact** and **Likelihood**), **Workstream**, **Milestone**, **Copy ID**, **Copy link** and **Draft email** to the owner. Each saves like a change in the list, with **Undo**. [[Shift]]+[[F10]] or the menu key opens it on the highlighted row.
6. **Change several at once:** highlight two or more rows and a bar appears with **Close** and **Reopen** and lists for status, owner, due date, priority, workstream and milestone. A field that doesn't apply to every selected item is greyed out and says why. Each item is checked on its own: any that can't take the change are named and the rest change, with one **Undo**. More than 25 asks first.

What waits, and what doesn't: [What staged means](#what-staged-means).

Or say: `mark ABC-A-003 done` `move ABC-A-003 to 20-11-2026` `log a risk for ABC: …`

## What staged means

Where: Work · any item's panel

1. **Staged** means saved to wait for **Apply**. With **Save my changes at once** on (the default, in Settings › Essentials › Saving and review), your own edits save as you make them, with **Undo**; what creaite suggests always waits in Review.
2. When changes do wait, the bar at the foot of the page counts them ("3 changes staged on 1 item"). **Apply** or [[⌘↵]] saves them and closes the item. **Undo last** takes back the newest before you apply.
3. A reload doesn't lose a change. Staged changes stay staged in every window or browser on this vault, and the bar comes back. A new item that isn't staged yet is kept in this browser as you type: open New again and choose **Restore** or **Discard**.
4. Leaving a new item early: [[Esc]], a click away or the close arrow on an empty one closes it with nothing staged. If it has a title, creaite asks **Keep** or **Discard**.

Or say: `apply` `undo last apply`

## Raise, record or withdraw a decision

Where: Work › Decisions · any decision's panel

1. **Raise one that is needed:** in Work › Decisions press the **+** tile and choose **Ask for a decision**. Say what is to be decided, who is asked and when it is needed by. It stays **Pending** until it is made.
2. **Record it:** open the pending decision and set its **Status** to **Made** (or choose **Mark as made** under **⋯**). The date made is today; change it, the maker or the reasoning if you need to. A made decision can't go back to pending: record a new one that replaces it.
3. **Withdraw it:** set its **Status** to **Withdrawn** to close it without a decision.
4. **A fuller record:** reasoning, the options considered, a revisit date (or a trigger in words) and the decision it replaces are optional. The old decision then shows **Replaced by** the new one.
5. **See what is waiting:** Work › Decisions has **Pending** and **Overdue** views, and Today, the project page and the person's page show them. A meeting's **Prep** lists them too.
6. **Decisions needed:** a pending decision with a decision maker and a needed-by date is listed under **Decisions needed** on Today, the project's page and a steering meeting's Prep. Yours come first, marked **Yours**, with **Decide**. **Chase** drafts an email to the decision maker (copy it into Outlook yourself; nothing is sent). **Open** opens it.
7. When a sweep finds a message that makes or withdraws a pending decision, Review shows it as an update to that decision for you to approve, never a second decision.

Or say: `decision needed from Sara by 16-10: pilot extension` `record the decision ABC-D-004: Sara agreed` `withdraw ABC-D-004`

## Update a project's state and health

Where: Projects › a project

1. **Current state:** press the pencil to edit in place, or the sparkle to **Generate** a draft from a period you choose. It is written as a short executive status. Nothing is saved until you save.
2. **Check where each sentence came from:** in a drafted status every sentence is underlined. Click one (or Tab to it) to see the facts and tracker items behind it and the line in the minutes, in a panel marked Internal. A sentence with no source says **No source**: edit it, or keep it with a note, before you save. A sentence you change loses its link until you press **Check sources**.
3. **Health:** press its pencil and choose On track, At risk or Off track, with a reason. If it's better than the evidence suggests, the reason is required. Under the form is the project's history: health and its reason, Current state edits and the weekly updates (All, Activity, Updates, Source).
4. Add an image in the editor with **Image**, or paste one in.
5. **The same facts in another form:** in **Generate**, choose a **Form**: a **Steering note**, a **Three-line update**, an **Email paragraph** or a **Teams message**, and an **Audience**: Internal, Client-safe, **Steering committee** or **Sponsor** (internal wording with nothing confidential, restricted or marked Client-safe: no). Press **Write it**: the text appears in the dialog with its sources and a length check, to **Copy**. Only the Current state form goes into the editor; the other forms are never saved.

Or say: `ABC is at risk because the data access is late`

## Let creaite draft the wording

Where: an open item · Work's bar · Today · a project's health · a milestone's forecast

1. **The latest update:** open an action and press **Draft** beside **Latest update**. creaite gathers what happened since the last update and Claude words one or two lines. With nothing new it says "Nothing new since …" and asks Claude nothing. For several at once, highlight actions in Work and press **Draft updates**, or use Today's line "n open actions have had no update for 7 days": each draft arrives in Review as a proposal.
2. **Read the card first.** Each sentence shows the sources it rests on (point at **S1**), and a sentence with none is marked **no source**. **Drafted from…** lists every source. Nothing is saved: **Use this** puts the text in the field for you to edit, and **Discard** drops it. Confidential or restricted sources are never read.
3. **Client wording:** on a client-visible item, **Draft** under **Client messaging** (in **Details**) writes plain wording from the item's own text only, and lists what it took out and anything to check. **Draft all** on a project's Client messaging card stages one proposal per item. A confidential item is never drafted.
4. **The thinking fields:** **Suggest** beside a decision's **Reasoning** and **Options considered**, and a RAID item's response, reads the meeting where it came up. A risk also gets **Set impact** and **Set likelihood**, with a reason. In Review a new risk with no response offers **Draft a response**. Who made a decision, and when, is never suggested.
5. **Health and forecast reasons:** **Draft the reason** in the health form, or in a milestone's forecast change, words one sentence from the evidence. Save is still yours.
6. **Meetings and email:** **Draft agenda** in a meeting's prep ([Draft an agenda](#draft-an-agenda)); **Polish** in a Draft email ([Ask someone for an update](#ask-someone-for-an-update)); Generate's **Form** writes the status as a steering note, a three-line update, an email paragraph or a Teams message.
7. **Sharpen a vague action:** as you type a new action's title, chips under it suggest an **Owner**, **Due** date, **Workstream**, **Milestone** and **Priority**. A click sets that one field. A vague title (under four words, or no verb) also offers **Sharpen**: Claude suggests a clear, verb-first title beside yours, and **Use this** or **Discard** decides.
8. **AI on selected text:** in any editor, select text and press **AI** on the small bar over it, or **Alt + /**. Choose **Rewrite clearly**, **Shorter**, **Longer**, **Make it executive**, **Fix spelling and grammar** or your own words. In a note, **Make this an action, a risk, a decision or an update** runs [Find updates](#turn-a-note-into-tracker-changes) on that one line. The answer is a suggestion: your text is unchanged until **Accept** ([[⌘Z]] undoes it). Claude sees only the selected text and the project's name, people and open item IDs, with no tools. A confidential note asks once before the text goes to Claude.
9. **Turn any of them off** in **Settings › Essentials › Look and help** (the AI drafts rows, or all at once). **Activity › Quality** shows how often each kind has been used, edited or rejected. Every draft needs the live server.

Or say: `what has happened on ABC-A-003 since its last update?`

## Manage milestones

Where: Projects › a project › Milestones (the pencil on the Milestones card)

1. The page **Milestones: Plan and Movement** opens. Press **+ Add milestone**: it opens beside the page with every field ready (name, state, agreed and forecast dates, progress, description, owner and client view). Fill in what you know and press **Create milestone** (or Enter in the name); nothing is saved before that, and **Undo** is in the message. Or click any milestone (a row, its marker or its label on the line) to open it beside the page.
2. Each change saves on its own, with **Undo** in the message. Pick its **State**; choose dates from the calendar (**Forecast** asks why it moves, for the history); set **Progress**, the **Owner**, the **Description** and whether it is **Visible to client**, with its client wording. Under **History** is everything that has changed on it, with the reasons (internal: not shown in the Client view).
3. To move the agreed date, press **Rebaseline…**: on **Movement**, choose the new date, who agreed it and why. It is staged for Review with a decision record.
4. **Internal view** and **Client view** switch what the card and the page show; the client sees only client-visible milestones in their own words. The Client view looks like any other card; the Internal view has a bright border and an **INTERNAL VIEW** pill.

Or say: `add milestone for ABC: UAT complete 20-11-2026`, `ABC go-live is at risk: security review open`, `rebaseline ABC go-live to 15-12-2026, agreed with Sara at steering`

## Hand over someone's work

Where: People › a person

1. Open the person's page and press **Hand over…**.
2. Tick the items to move, choose who takes them, and press **Hand over**.
3. It's one change: one **Undo** reverses all of it.

Or say: `Sara owns the SOW action` for a single item.

## Ask someone for an update

Where: People › a person

1. Open the person's page ([[⌘K]], then their name) and press **Draft email**. With nothing open for them the button is off and says so.
2. Check **To** and **Subject**. Each has its own **Copy** button.
3. Untick any item you don't want in it. Add **Include latest update**, or set **Please reply by**, if you need to.
4. Change the wording in the preview if you like, then press **Copy email** (or **Copy as plain text**) and paste it into Outlook.
5. For someone outside your own email domains, items not marked client-visible start unticked and are tagged "internal". creaite never sends the email or makes an Outlook draft.
6. **Chase overdue items** (at the top of the email) turns it into a reminder of what is overdue. The tone steps up with how often you have chased: a first reminder, a second, then a firmer one. After you send it, press **I sent it**: creaite notes the items and the date (nothing else), so the next chase knows ("chased 03-10-2026, once") and their page says so. Right-click an overdue item for **Chase** its owner.
7. **Polish** (with Warm, Neutral or Firm) rewords the opening paragraph only; the table, subject and addresses are never touched. Claude's version is shown beside yours: **Use this** or **Keep mine**.

Or say: `what's open with Sara Example?` to see the list first.

## Chase one item, or ask for help with your own

Where: Work › an item › the envelope (Draft chase)

1. Open an open action, risk, issue or decision and press the envelope in its top bar, left of **Copy link** (or press [[C]]). The chase opens inside the item, and **Back** (or [[Esc]]) returns to it. Closed or cancelled items and proposals have no envelope.
2. creaite reads whose item it is. **Someone else's** is a chase to its owner: a first reminder, a second, then a firmer one, stepped from how often you have chased it. **A decision** asks its decision maker for the decision by its needed-by date. **Yours** is a request for help, never a chase.
3. For your own item, choose who to ask. creaite suggests people from the item (those named in it, who raised it, the meeting it came from and the project's stakeholders), or **+ Anyone** from the people register. Fill in **To get … done** and **What I need from you**.
4. **Reply by** starts two working days ahead, **Tone** (First, Second, Firmer) starts from how often you have chased, and **Include the latest update** starts on. The email updates as you type.
5. Press **Copy for Outlook** (or **Copy as text**) and paste it into a new email. The subject keeps the project code in brackets, so your Outlook rules can file it. creaite never sends it or makes an Outlook draft.
6. After you send it, press **I sent it**: creaite notes the item, the date and the kind of chase (nothing else), so the next one steps up. **Polish the wording** (when AI drafts are on) rewords the opening in the tone you chose, shown beside yours: **Use this** or **Keep mine**. The table, subject and addresses are never sent to Claude.

Or say: `what's overdue with Sara Example?` to see their items first.

## Change an item in words (Sneak peek)

Where: Work › an item (or a milestone's editor) › the sparkle, or type `//`

1. With an action, risk, issue, decision or milestone open, type [[/]] [[/]] outside a text field, or press the sparkle in its top bar or **// Change this item in words** at its foot. A small box opens over the bottom of the item. One [[/]] still opens ask creaite, after a moment's wait for a second slash.
2. Type what you want: `owner to Tom`, `due Friday`, `push it out a week`, `priority high`, `close it`, `add an update: Northgate confirmed the dates`, `workstream to Testing`, `label it sensitive`, `forecast to 13-11`. The change shows as you type, from → to, with what was understood marked in your words: click a marked word to take it out. Type `@` for a person and pick from the list.
3. Press **Enter** to make it. It is saved in one step, with **Undo** straight after, and the field that changed is highlighted for a moment. A name that matches two people asks which one; a name nobody has changes nothing.
4. A few changes need a confirm, marked in amber: rewording the description or decision, cancel and withdraw, a decision made, client-visible on, removing Sensitive, a milestone's state, and a risk becoming an issue (`this has happened`). Press **⌘↵** or click: plain Enter never makes them.
5. It can also link items (`blocked by ABC-012`), add a follow-on action, raise a risk from an action, note a promise (`I promised Tom the terms by Friday`), answer quick facts (`when was this last chased?`), go to the source, and hand over to **Draft chase** (`chase Tom, firmer`). Nothing is ever sent from here.
6. With AI drafts on, Claude can draft a client message or tidy an update: its version shows beside yours, **Use this** or **Keep mine**. Esc closes the box, and ↑ in the empty box brings back your last instruction. Several items at once, health, settings and the people register are for ask creaite, the project page or Settings: the box says where.

Or say: `close all of Sara's overdue actions` to ask creaite to change several items at once.

### Reporting

## Write the weekly report

Where: Today's reminder · Claude Code

1. From Friday 12:00, Today reminds you, and the reminder opens **Reports**, where you see every project's week. Press **Draft weekly report** on the reminder (or **Weekly report** at the foot of the project page) (it needs the live server), or say the phrase below. **Open** on a project's row goes to its reporting space (also **Open reporting** on the project page's Reporting card, or [[⌘K]] and ``weekly report ABC``).
2. Clear Review first. A project with pending items is held back.
3. For each project, check the proposed health, its reasons and the current state, then approve. The report is filed in the project's `reports/` folder as a web page (`2026-10-16 Weekly report - <Project name>.html`) that opens in any browser. Approving is one apply, so **Undo** puts the earlier report back.
4. A filed report is never saved over. To correct one, edit it: that starts a new draft and the filed report stays as it was until you approve the new one.
5. To send it, export it as a web page, Word or PDF (a PDF needs Chrome). The export is made from the same report, so all three say the same and nothing you hid is in them. It is filed beside the report only if you turn on **Settings › Advanced › Reports and minutes › File report exports beside it** (off to start with); otherwise it is made in a temporary place and opened for you. creaite never sends it.

Or say: `weekly report` `weekly report ABC`

## Write a client report

Where: Item panel · Claude Code

1. Decide what the client sees. Turn on **Client-visible** on each item, and write its three-part client message: what it is, what it means for you, what is being done.
2. Approve that week's weekly report first: a client report is drafted from, and approved or exported only after, the internal week, and shows only the facts approved with it. If you approve the internal week again, the client drafts follow it, and only ever lose items.
3. Press **Draft client report** on Today's reminder (or **Client report** at the foot of the project page), or ask for the report. Only client-visible items appear. Anything labelled **Sensitive** or **Partner only** stays out whatever else is set, and confidential material is left out.
4. Approve the draft. creaite checks it for anything internal first and says what it found; if the check finds something, nothing is approved or exported. It files the report in `reports/` as a web page (`… Client report - <Project name> (<Client>).html`, one per client), never sends it, and, like the weekly report, never saves over a filed one. Export it as a web page, Word or PDF, as for the weekly report.

Or say: `make ABC-A-002 client-visible` `client report ABC`

## Draft a steering-committee one-pager

Where: Today › a steering meeting's Prep · ask creaite

1. For a meeting called SteerCo or Steering that belongs to a project, open its **Prep** and press **One-pager** (or **Client-safe one-pager**). Or say the phrase below.
2. Choose the version. **Internal** has everything, with sensitive items marked; **client-safe** has only items flagged client-visible, in their client wording, and leaves out anything labelled Sensitive.
3. Claude drafts a Word page: status and trend, what changed since the last one, milestones, top risks, decisions needed, blockers, flow and the next period. A section with nothing to say is left out.
4. Review the draft and approve it. creaite files it in the project's Steerco folder as `YYYY-MM-DD <Project name> Steerco one-pager.docx` (`… Steerco one-pager (client).docx` for the client-safe one), never replacing a file that is there, and never sends it.

Or say: `steerco one-pager ABC` `steerco one-pager ABC client-safe`

## Make a one-off Word document

Where: ask creaite

1. Ask for it in plain words, for example an actions register, a list of open risks, or a decision log.
2. Claude says what it will build. Confirm.
3. The branded draft lands in `system/staging/drafts/`. It's internal, and nothing is filed or sent.

Or say: `actions register for ABC` `a document of Omar's overdue actions`

### Admin

## Add a project or a person

Where: Claude Code · Settings › People and projects

1. **Project:** ask Claude with the phrase below, giving the code, name, client, people, email domains, Teams channels and keywords. It creates the folder and the register row. With projects in OneDrive it copies your template skeleton into a folder named after the engagement; an engagement folder that already exists is adopted as it is.
2. **Person:** in **Settings › People and projects › People**, add their full name, email, aliases, organisation and role. Or just type them as an owner.
3. **Workstreams:** in **Settings › People and projects › Workstreams**, add them for each project, with a lead and keywords.

Or say: `add project DEF Digital Enablement…` `add client.com to ABC's domains`

## Change a project's code or name

Where: Claude Code

1. Say what you want, with the old code, the new code and, if it changes, the new name. creaite shows what will change before it does anything: every item ID keeps its number under the new code, and history, links, promises and labels follow.
2. If the project's folder starts with its code, rename the folder yourself first and tell creaite its new name. creaite never renames a folder.
3. Say **yes**, then **apply**. It is applied on its own. The old code is retired and can't be used again. **Undo last apply** puts everything back.
4. creaite refuses while other proposals still mention the old code: apply or reject them first. It lists a few places it doesn't edit (the people register, `PORTFOLIO.md`, other lines of the project's memory) for you to check.

Or say: `change project ABC's code to XYZ, Example Plus`

## Never miss a VIP

Where: Settings › People and projects › People · Today

VIP is private to you. creaite never shows the word beside a person and never writes it, or who is one, into anything: reports, the steerco one-pager, prep pages, minutes, drafts, Review or the Excel export. They still work, unlabelled.

1. In **Settings › People and projects › People**, press **Edit** on the person and set **VIP** (Management, Client or Yes). Give every address they write from in **Email**, separated by commas. Apart from this page, that field, the register's VIP column and **Settings › Essentials › People I follow** are the only places the word appears.
2. Anything they send by mail or Teams is a row of **Intake and Review** on **Today**, marked only **Message**, newest first, with a count on Today in the left bar and in the window title. It shows even when it names no project or an ignore rule would skip it. The browser notification shows only the sender's name. Their calendar invites don't make a card.
   - **One card per conversation:** creaite reads the whole Teams chat or mail thread, not each message. The card has the conversation's own title, where it is from, **updated HH:MM**, a one- or two-line summary and the candidate items: actions, decisions and risks. When the conversation carries on, the same card updates. creaite waits up to 15 minutes for a conversation to go quiet. The project is matched from the title first, then the people, the attachment names and what was said.
   - **Looks done:** when the thread shows the matching work item is finished, the card offers **Looks done: close ABC-A-007**. One click stages the close for Review, where you approve it on its own. **Undo** on the card takes it back while it waits.
   - **Your promises:** when your own message makes a commitment in passing, the card shows **You promised Sara Example: Send the revised plan · by 16-10-2026** with **Add a promise** and **Dismiss**. Only your own promises are offered. When the thread shows an open promise kept, it offers **Looks kept: mark kept**. Nothing is added or marked until you approve it in Review.
   - **Nothing for you:** a conversation of greetings and chatter is one quiet line, with no buttons and no count.
   - Each candidate item has **Create work item** (the +, filled from the item) and **Dismiss**. The card goes once each is made or dismissed, and the sweep doesn't propose the same conversation again unless new messages came after the summary.
3. On a message (a private or confidential conversation shows only a neutral line): **Dismiss** (the crossed-out eye) has **Undo**. **Make a work item** (the +) opens a new item filled from the message: the subject as its title, its project (or **Choose a project**), you as owner, no due date, and the message as its source. **Action**, **Risk**, **Issue** or **Decision** switches the type, and **Draft from the message** suggests a sharper title and any date (never for a private or confidential message). **Save** ([[⌘↵]]) makes it and dismisses the message, and **Cancel** leaves it.

What they ask for is also proposed as usual, first in Review, with no label. In Work, the funnel's **People I follow** filter shows only their items. The early warning for an overdue item one of them owns is **Overdue item owned by someone you follow closely** in Settings › Advanced › Early warnings.

Or say: `make Mia Hale a VIP` `mark the VIP alerts seen`

## Keep noise out of the sweep

Where: Settings › Advanced › Sweep

1. Under **Ignore rules**, press **Add a rule**: give it a name, choose where it applies (mail, Teams, calendar) and what it looks at (subject or title, sender, or Teams channel), then how it matches and the text. Case doesn't matter.
2. Switch a rule off to pause it, or **Edit** or **Delete** it. The built-in rule for anything marked private can be switched off but not deleted.
3. After each sweep, the summary counts what each rule skipped ("Ignored 14: ToDo invites 9, humancapital 3, …"), so a rule that catches too much shows up.

Or say: `ignore calendar invites starting with ToDo in the sweep` `stop ignoring humancapital`

## Undo a mistake

Where: The message bar · Activity

1. Straight after a change, press **Undo** in the message at the bottom.
2. Later on, **Activity** lists every change: Undo there reverses the latest apply, and ticking older lines and pressing **Undo n** puts back just those changes (anything changed since is left as it is).
3. For anything older, say the phrase below. Every apply is logged, so it can be reversed.
4. A file ask creaite changed: **Activity › What ask creaite changed** lists the last seven days, each with its tier (Ordinary, Sensitive or High-risk) and **Undo**.

Or say: `undo last apply`

## Update creaite

Where: Settings › Health › creaite version · Claude Code

1. Say the phrase below in Claude Code. If the GitHub command-line tool (`gh`) is installed and signed in, it fetches the newest **creaite-X.Y.Z.zip** itself (pre-releases included), checked against its checksums. If not, it says so: download the zip from the GitHub release (the attached file, not "Source code") into `system/releases/` and say it again.
2. It shows what changes and waits for your yes. With a zip already in `system/releases/`, **Review** then **Install** in Settings does the same.
3. Restart the live server. Your data and your `CLAUDE.md` are never touched, and ``undo update`` goes back.

Or say: `update creaite`

## Archive a project

Where: Settings › People and projects › Projects and register

1. Press **Archive** beside the project. A finished project's folder moves to _Archive, and the project and its items leave Work, Today, the Excel export, the reminders and project matching.
2. If it has open items they are listed first. Choose **Cancel them all and archive**, or **Stop**.
3. The change waits on the approval card in ask creaite until you **Approve**. **Undo** reverses it.
4. To bring one back, press **Show archived projects**, then **Restore**. A restored folder whose name is taken gets a number, and an archived code is never reused.

Or say: `archive project ABC` `restore project ABC`

## What the words mean

Where: Help · when a word is new

1. Find the word below. Each page uses it the same way.
2. **Proposal**: something Claude suggests, which waits in Review until you approve it.
3. **Tracker**: the record of your actions, risks, issues, decisions and milestones, kept on your Mac.
4. **Vault**: creaite's folder on your Mac.
5. **Sweep**: the check of Outlook and Teams since the last one, which turns what it finds into proposals.
6. **Live server**: the small program behind the dashboard. The launcher starts it, and changes apply straight away while it runs.
7. **Staged**: saved to wait for **Apply**. With **Save my changes at once** on, your own edits don't wait.
8. **Applied**: written to the tracker. Every apply can be undone.
9. **Peek**: an item opened over the page.
10. **RAID**: risks, assumptions, issues and dependencies.
11. **POAD**: Purpose, Objectives, Approach, Deliverables, the shape of an agenda.

Or say: `what does staged mean?`

## Fix a stopped server and other problems

Where: Bottom of the left bar · Claude Code

1. **A hollow red dot under Settings, or a red alert:** the live server isn't running. Start it again in Terminal. Your edits are held until it's back.
2. **"Reconnect vault":** you opened the dashboard as a file. Use the live server's address instead.
3. **Something failed or looks wrong:** when there were errors in the last day, a quiet banner under the top bar says how many and what kind (one fault that repeats counts once: "1 error (30 times)"). **Investigate** opens Diagnostics; **ask creaite to look** (with the live server) asks it to read the log and explain, changing nothing; **×** dismisses it until a new error. With ask creaite open it stops at the chat's edge, its words shortened if need be, so these stay in reach. Or open **Settings › Health › Diagnostics** yourself. It lists the latest errors and how many commands ask creaite's guard refused in the last seven days, by shape (a pipe, a redirect, `cd … &&`; counts only, and a rise means its instruction isn't holding); press **Copy diagnostics** and paste the report into a chat with Claude. The report holds no mail, minutes, notes or names, and nothing leaves your laptop unless you paste it. The same log is in `system/logs/` (a file a day, the last seven kept), and ask creaite can read it.
4. **Anything else:** say the phrase below. It checks everything and offers each fix before making it.

Or say: `health check` `setup`

---

Press [[?]] on the dashboard for the full help. Dates are shown DD-MM-YYYY.
Nothing reaches the tracker until you approve it, and the tracker and engine stay on your laptop.
[First day: how creaite works ›](#start-here)

# Reference

Everything in creaite, by feature. For the short version see [Start here](#start-here); for a job step by step, see [How do I…](#how-do-i). A printable copy of those two guides is in `system/templates/` (`guide-first-day.html` and `guide-how-to.html`); open them in your browser, they work offline.

### Using the dashboard

## Keyboard shortcuts
| Keys | Does |
|---|---|
| ⌘K | Search or jump to anything: views, projects, items, milestones, files, Intake and commands. Type a change in words ("move ABC-A-002 to fri") to see it before and after; Enter saves it, ⌘↵ saves it and opens Review |
| / or ⌘J | ask creaite |
| ⌘⇧N or N | A new note from any page (N when you aren't typing in a box, in an ordinary Chrome tab). Esc closes the drawer and keeps the draft, ⌘↵ is Done |
| // | With an item open (outside a text field): **Sneak peek**, change it in words. Esc closes it; ↑ brings back the last instruction |
| ? | This help, on the tab you used last |
| Esc | Close the top thing: a picker or calendar, an open item, ask creaite or the palette. In a text field of an open item it puts the text back. In ask creaite's input it stops a running request |
| J / K | The next or previous row in Work and Review (on a Work board, the next or previous card). With an item open, the next or previous item |
| Space · Enter | Work and Review: select the highlighted row · open it (or click its ID). Shift+J extends the selection |
| C | With an open action, risk, issue or pending decision: **Draft chase** |
| D · F | Work: the Display menu · the filter picker (type to find a field) |
| Click · drag | Work's List: click a value to change it, a heading to sort, drag a column edge to resize (double-click resets). Work's Board: drag a card to another column, or use its **Move to…** menu |
| [ / ] | On a project page: the previous or next project. On Today: the previous or next day |
| T | Today: back to today |
| ⌘\ | Notes: hide or show the notes list |
| ⌘[ / ⌘] | Back and Forward: the last view, with its filters, open item and scroll position |
| Alt + / | In any editor, with text selected (⌘A for all of it): the **AI** menu. Esc discards the suggestion, Enter on **Accept** puts it in, ⌘Z undoes it |
| Enter | In an open item's title or a one-line field: keep the text. Shift+Enter starts a new line in the longer fields |
| ⌘↵ | In every editor that opens beside the page: do what its Save button does, then close it (each Save button shows ⌘↵). In Review's proposal it saves; it never approves |
| Shift+F10, the menu key | Work, a person's page and Review: the right-click menu for the highlighted row |
| A · R · X | Review: approve, reject, select |
| A · R · E · J · K | Review › One at a time: approve, reject, edit, skip, previous. Esc returns to the list |
| R or Shift+R | Review: reject with a reason. 1 to 7 choose a reason, G uses each row's guess, 0 is no reason |
| ⌘A | Review: select every proposal the filters show |
| ⌘Z | Work: undo your last change. Review: undo the last decision or batch. Not while you are typing in a box |

Press **?** from Work or Review to see their keys.

## What the icons mean

Point at any icon, or Tab to it, and its name shows in a tooltip, with its key when it has one. Esc hides the tooltip.

| Icon | What it does | Where |
|---|---|---|
| Lines / columns | **List** / **Board** | Work toolbar; the filled one is in use |
| Sliders | **Display**: grouping, order, properties (D in Work) | Work and Review toolbars |
| Funnel | **Add a filter** (F in Work), with a count when filters are on | Work and Review toolbars |
| + tile | **New action**, **New RAID item**, **New decision** (a menu: Record a decision, Ask for a decision) | Right end of the Work toolbar |
| Tick | **Approve** (with the word) | Review |
| Double tick | **Approve routine** (with the word) | Review toolbar |
| × | **Reject with a reason** (R), **Clear the selection** (Esc), **Close**, remove a filter | Review rows, bars, panels |
| Chevron | Collapse or expand (it turns); **Reject with a reason** (R); on a rejected row, **Change the reason** | Groups, Board columns, Review |
| Pencil | **Edit** (E in Review), **Edit details**, **Open draft** | Review rows, a person's page, Settings › People and projects › People |
| Arrow right / corners | **Close** / **Expand to full width** an open item | An item's toolbar |
| Up / down chevrons | **Previous item** (K) / **Next item** (J) | An item's toolbar |
| Sparkle | **Sneak peek** (/ /): change the item in words | An item's toolbar, a milestone's editor |
| Envelope with an arrow | **Draft chase** (C): a chase, or a request for help with your own item | An item's toolbar |
| Chain link | **Copy link** to the open item | An item's toolbar |
| Three dots | **More**: Mark done (or Mark as made), ask creaite about this, Copy ID | An item's toolbar |
| T | **Rename** | Settings › People and projects lists |
| Bin | **Remove from Intake**, **Remove from list**, **Retire** | Intake, Settings |
| Curved arrow | **Undo this change**, **Restore**, **Reset** | Activity, Settings |
| Circular arrow | **Refresh items**, **Check now** | Review rows, Settings |
| Two sheets | **Copy** (it ticks when done) | Settings |
| Open folder | **Open folder** | Files |
| Folder | **Browse files** | Project page |
| Eye | **Preview** | Intake |
| Arrow out of a box | **Open last prep page** | Meeting prep |
| Page | **Weekly report**, **Client report**, **One-pager** (with the word) | Project page, meeting prep |
| Envelope | **Draft email** (with the word) | A person's page |
| Bent arrow | **Hand over** (with the word) | A person's page |
| Spark | **Prep page** (with the word) | Meeting prep |
| Calendar | **Choose a date** | Every date field |
| Up arrow / square | **Send** (Enter) / **Stop** (Esc) | ask creaite |
| Moon / sun | Switch to the dark / light theme | Top bar |
| Gear | **Settings** | In More, at the foot of the sidebar |
| Triangle / shield | **Sensitive** / **High-risk** (with the word): how much a change on ask creaite's approval card matters | ask creaite's approval card; Activity › What ask creaite changed |

## Opening the dashboard
- Double-click the **creaite** launcher: it starts the live server and opens the dashboard in its own window (see Open creaite as an app). Or open it from a live server you started in Terminal: the address (`http://127.0.0.1:` and the port) is shown there.
- Opened as a file instead, the dashboard asks for the vault folder the first time you edit, and remembers it. If Chrome loses access, the top bar shows **Reconnect vault**. Use Chrome or Edge: Safari can only show the dashboard.

## Working with lists
- **Select and open:** a click highlights a row (an edge bar, a tick and a tint). To open the item over the list, click its **ID**, double-click the row, or press [[Enter]]. ⌘-click adds or removes a row; Shift-click highlights a range. [[Esc]] clears the highlight. With the details open, a single click on another row shows that item there, on the Board's cards, a person's page and Review too. [[J]]/[[K]] move the cursor, Shift extends, [[Space]] toggles, [[Enter]] opens.
- **Wide tables** show a fade and **more columns →** at the right edge. The first column stays in place while the others scroll.
- **Filters combine:** Status, Due, Owner (Me first), Project and Priority on the toolbar. The funnel (**Add a filter**, or [[F]]) opens a picker for more: workstream, RAID type, response, source, client-visible, **Stale**, **Last updated**, **Raised**, **Milestone** and dates. Each has **is** and **is not**. Applied filters are chips with a ×, then **Clear all** and "Showing 12 of 87 · 14 closed hidden". When nothing matches, the list names the filters and says how many items removing each would show. Actions, RAID and Decisions keep their own filters. Search finds dates as you type them (14-10-2026).
- **Views** (All open, Mine, Due soon, **Chase**, Delayed and your own) are presets. Change one and its chip gets a dot: **Update view** saves the change into it, **Save as new view** keeps both. A saved view's ▾ renames, moves or deletes it. **Chase** is open items owned by someone else that have gone quiet. **Settings › Advanced › Work and views** (Actions open on, RAID opens on, Decisions open on) chooses the view each tab opens with.
- **Display** (the sliders icon, or [[D]]): **Group by**, **Sub-group**, **Order by** (⇅ reverses it), **Properties** (the List's columns and a card's fields) and **Show**. **Reset to this tab's default** puts it back. Saved views keep the layout. Drag a heading to move a column, drag its edge to resize and double-click to reset. A group header shows its count and overdue count; click it to collapse, and its tick selects the group.
- **List or Board:** the two icons on the toolbar show the same items as rows or as cards in columns, on every tab. The Board's columns are its grouping and a Sub-group adds swimlanes. Closed shows the last 14 days, with **Show all**. Click a heading to sort, again to reverse, a third time for the default. Filters, sort and view are kept in the address, so Back, a reload or a bookmark keeps them.
- **Decisions** have a Status (Pending, Made, Withdrawn) and a Needed by date. **Pending** lists what is still to decide, soonest first, and **Overdue** the ones past their date.
- **All items**, the fourth tab, lists actions, risks, issues and decisions together, read-only. Its Type is always written out, and its Status has three choices: Open, Closed and Cancelled. Filter by status, due, owner, project, priority and (under the funnel) type, stale, last updated and raised. Click a row to open its own details, where you edit it.
- **Every count opens its list.** A number of actions, risks, issues or decisions anywhere in creaite (the Projects table, a project page, People, Today, a meeting's prep) is a link with a dotted underline. It opens Work on that tab, filtered to exactly those items, and **Back** returns. A figure that says "open" counts Open actions only; a figure by date also counts Delayed actions. A zero is plain text.
- **Projects are shown by their full name** everywhere. The short code starts an item's ID (ABC-A-003) and is what you type in commands, filters and search. A Draft email subject starts with it too, so your Outlook rules still match.
- To change values, edit an open item, work on several rows at once or right-click, see [Change an item](#add-or-change-an-item).

## How saving works
- Every save, new item, health change, current-state edit and Approve or Reject is written as a proposal, already approved, and applied straight away while the live server is running. Without it, changes wait and the top bar shows how many are held. A red alert shows the command to start the server and **Check again**. Say `apply` in Claude Code to apply them.
- **A change shows at once.** The row shows a small hollow dot while it is saving. Several quick changes to one item are applied in the order you made them. If one can't be applied (the item changed elsewhere, or a rule refused it), it is put back on screen and the message says why, with **Retry**. **Undo** works while it is still saving.
- **Undo** in the message removes a change that hasn't been applied yet. For an applied change, say `undo last apply`.
- Settings save straight away, with a backup and a log line each time.
- **Theme and mode:** **Settings › Essentials › Look and help › Style** picks the colour theme and **Theme** picks Follow my Mac, Light or Dark. The moon button flips light and dark, and [[⌘K]] › "Theme:" switches theme too.
- **Motion:** creaite uses a little motion to show what changed, and nothing moves on its own while you're idle. **Settings › Essentials › Look and help › Motion** chooses **Follow system** (the default), **Reduce** (no animation) or **Full**. Under Reduce everything still happens, at once.

### Features

## Today
- Today is one home: your day across the top (the day line, the headline, the meetings and **Close the day**), then one centred column of sections, unboxed: **First thing**, **Decisions needed**, **Needs attention**, **Your commitments**, **Intake and Review**, **Week ahead**, **Resolved** and **Portfolio**.
- **Row actions are icons.** Each names what it does when you point at it, and to a screen reader. They stay faint until you point at the row or tab into it. Every change has **Undo** in the message at the foot of the page.
- **Intake and Review** lists what waits in Review, transcripts ready in Intake and messages from people you follow, newest first. The top five show, **+n more** the rest, then **Open Review (n)**. On a proposal, **Approve and save** (the tick) approves it and **Reject, with a reason** (the cross) opens the reasons. Minutes, reports, file changes, new decisions, new risks and anything else approved one at a time never get the tick here: **Open in Review** takes you to them. A transcript has **Process the transcript**, and a message has **Make a work item** and **Dismiss**.
- **Other days:** the day line holds every working day in the saved calendar, from Monday of this week as far ahead as it goes, with **Next week** marking the break. Click a day, use the arrows at the band's sides, or press **[** and **]**; **T** comes back to today. Only the band changes: everything below stays as of today, and a line under the meetings says so. Past days show each meeting's follow-up: **Minutes made**, **Draft in Review**, **Transcript ready** with **Process**, **No transcript**, or **Not checked yet** with **Check**. On today and later days each meeting has one pill that opens its Prep: **Prepare** for one worth preparing for, **Prep** otherwise. A confidential meeting shows only its title and times, and a private one shows Busy.
- **First thing** lists what you put there when you last closed the day.
- **Decisions needed** lists each pending decision with a decision maker and a needed-by date. Yours come first, marked **Yours**, with **Decide**. Each row says the project, who it waits on, how many days it has waited, when it is needed and what slips if it stays open, from the links you have recorded (with no link, nothing is said). **Chase** drafts an email to the decision maker, and nothing is sent. **Open** opens the decision.
- **Needs attention:** the decisions waiting, your report reminders and a line counting open work with no owner or, for actions, no due date, by project. Each count opens Work filtered to those items. A report reminder has **Draft weekly report** or **Draft client report**, which asks ask creaite to draft it; or dismiss it for the session or for good.
- **Your commitments:** your overdue and due-soon actions, each with **Mark done** and **Move the date**, both with Undo. **You owe** lists the promises you made and haven't kept, soonest due first, overdue in red. **Waiting on** lists promises others made to you whose date has passed, with how long each has been quiet. **Chase view** opens Work's Chase view. Promises come from meetings (you approve them in Review) and from you ("add a promise: I told Sara Example I'd send the SOW by Friday"). The sweep doesn't propose them yet. A person's page lists the open promises between you.
- **Resolved** is folded to one line saying how many were closed since your last visit. Open it for the actions and RAID items, or press **See all activity**.
- **Week ahead:** day by day to next Monday, the meetings, the actions and RAID items of the priorities chosen in **Settings › Essentials › Saving and review › Week ahead shows** (Urgent unless you change it), every milestone and every decision needed. Each row says why it is there (**due**, **3 days overdue**, **needed by**) and has an icon: mark done, chase, write an update, record the decision, open a project, make a prep page. Work already late leads the first day, and Urgent work with no date leads the section. Weekends show only when you have a meeting. **Further ahead** lists the two weeks after. **Prepare** marks a meeting worth preparing for: one you organise, a steering or review meeting, or one whose project has overdue or Urgent work. Entries starting "ToDo", "Info:" or "FYI:" and anything the sweep's ignore list excludes are left out. It folds, like Resolved.
- **Portfolio:** each project's health with its evidence and a health trend. Select a project to open its page, and rest the pointer on its name for its description. Drag a column edge to resize it, and double-click to reset. Widths are remembered in this browser.
- **Close the day:** the door icon in the header opens a four-step shutdown: see [Close the day](#close-the-day). A footnote at the bottom right says when the calendar was last read, if that was on an earlier day.

## Project page
- **Getting around:** the breadcrumb (Projects › the project's name) and the switcher (‹ name ›) move between projects, and so do **[** and **]**. Each figure (Overdue actions, Urgent risks, Milestone slip, Due 7d, Early warnings) is one click to its detail. Each card heading and "All N …" link opens Work filtered to this project. A project code anywhere opens its page, and the address keeps your place.
- **Current state** comes first, with any images. The pencil turns the card into an editor with a formatting bar: bold, italic, strikethrough, three heading levels, lists, quotes and links ([[⌘⇧K]]). [[⌘↵]] saves, [[Esc]] cancels, and leaving with unsaved changes asks first. Saving keeps your text exactly as you wrote it. Pasting from Word or Outlook keeps only these formats. **Image** (or paste or drop a PNG or JPEG, up to 2 MB) lands after the paragraph you're in, with a caption and a × to remove it. Images are internal and never go into client reports unless you say so.
- **Two panes:** the card has two writing panes side by side with a divider you drag (double-click resets). They are one message, the left then the right, read as one piece by the reports, Generate and search. The button on the divider folds the right pane. **Generate** drafts the left pane only and never changes the right.
- **Generate** (the sparkle) drafts the current state with Claude from a period you choose (the last 7, 14 or 30 days, or dates): tracker changes and open items, minutes and transcripts, reports, weekly updates and swept mail and Teams items (project documents only if you tick them). Steer it with a note, and choose the **Audience** (Internal, or Client-safe, which uses only client-visible items in their client wording) and the **Length** (Short, Standard or Fuller). It writes an executive status from a ranked sheet of facts: the headline first (on track, at risk or off track, and the one thing that matters), the points that matter, the risks that count and the asks with who and by when. Notes under the draft say what to check and never stop you saving. **Facts it was written from** shows the sheet. Nothing is saved until you save, and **Stop** cancels.
- **Where each sentence came from:** a drafted sentence is underlined, dotted when it has a source and dashed with "No source" when it hasn't. Click one to see the facts, the tracker items and the quoted line behind it. Tab and Shift+Tab move between sentences, and [[Esc]] closes. Save waits on a sentence with no source until you edit it or choose **Keep it** (or **Keep all**). A sentence you change loses its link until **Check sources**. The panel never appears in a client report.
- **Make it executive** (the editor's **AI** menu) rewrites the whole Current state in that voice, keeping your facts. It appears in its own box, with notes on any date or number it lost or added, until you press **Use this version** or **Discard**.
- **Rename the card:** click its title to call it something else on this page (up to 40 characters; an empty title restores "Current state"). It is a label on this page only, so the reports still find the section. A copy is kept first and the message offers **Undo**. It needs the live server.
- **Milestones** shows the **Plan**: every milestone on one line with its name and date, achieved ones in green and a later forecast as a red dashed ring with its date. Under it, each milestone's state, agreed date, "Expected … (N days later)" and progress; **Hide milestone details** folds the rows away. Click a milestone to open it. The switch icon beside the pencil flips the card (and the Milestones page) between **Internal view** and **Client view**. Client shows only client-visible milestones, in the client's words. The Internal view carries a bright border and an **INTERNAL VIEW** pill, which show on a screenshot too.
- **No due date:** under "Actions due or overdue", a card lists every open action with no date and every open risk or issue with no response date. Each has **Set date**, and two links open Work filtered to "No date". Items raised in the last 3 days show dimmer with "new" (**Settings › Advanced › Work and views › New items without a date: grace (days)** sets the days).
- **Flow:** small charts drawn to scale, counts only and never about a person: actions and risks and issues opened and closed each week, overdue at the end of each week, how long open items have been open, the oldest three, open risks and issues by priority and milestone movement. A sentence at the top sums up the week, and the weekly report carries the same line. **Settings › Advanced › Work and views › Flow chart weeks** sets the weeks (8 by default).
- **Dependencies:** the project's open dependencies grouped by the milestone each blocks, nearest first, with owner, due date and any date warning. Ones with no milestone sit under **Not attached**, and a blocked milestone shows **waiting on ABC-005**. A dependency with a due date and no milestone suggests up to three milestones it could threaten. Nothing is attached until you choose one, and **None needed** is remembered. Work's RAID list has an **Unattached dependencies** view.
- **Decisions needed:** pending decisions and any decision whose revisit date has come: the same rows as Today's **Decisions needed**, then the rest, with who is asked. Each opens its panel, where you can record or withdraw it.
- **Reports:** the **Reporting** card opens the project's reporting space. **Weekly report**, **Client report** and the folder icon (**Browse files**) are at the bottom, with top risks and issues and recent decisions. See [Write the weekly report](#write-the-weekly-report).

## Notes
- **Where:** each project page has two tabs, **Overview** and **Notes**. Notes that cover several projects are under **Projects › Portfolio notes**. Notes are your own working thinking: internal, never in a client report, and never extracted by the sweep or on their own.
- **The list** on the left has a search box, your **Pinned** notes and the **Recent** ones. The double arrow by the **Notes** heading hides it ([[⌘\\]] too). The choice is remembered, and the note widens to fill the space.
- **A new note:** the **+** at the top right (**New note**), then a title and a template: **Blank**, **Stakeholder**, **Lessons learned** or **Working session**. It is saved in the project's notes folder, named by its title; a taken name gets a number. Changing the title renames the file when the note saves (**Activity › What ask creaite changed** can undo it), and links in your other notes follow.
- **An open note is editable:** click and type, with no Edit or Save. What you type is kept as a draft at once, and the note is written once per editing session: when you leave it or after 30 seconds without typing. **Saved** and the time show quietly at the right of the title. If the file changed elsewhere (Finder, OneDrive), creaite never overwrites it: your typing is kept and it asks which to keep.
- **Links as you type:** two square brackets link another note (one that doesn't exist yet shows red; click it to make it), `@` mentions a person, `#` links a work item (a chip with its live state, "ID · Action: title"; click it to open), and `/` on an empty line inserts a sub-heading, checklist, table or a template's headings. ⌥-click a link to put the cursor in it.
- **Pictures:** **Image** adds a PNG or JPEG (up to 2 MB) after the paragraph you're in, with its description as the caption. × removes it from the note; the file stays.
- **A Working session's header:** change its date and who it was with at any time. Type the date as DD-MM-YYYY or in words (today, yesterday, last monday, next friday, in 3 days): the pop-up says what it understood before you accept it, or pick a day on its calendar. Separate names with commas.
- **Tags** sit on their own line under the date, after the fixed **Internal** (or **Confidential**) chip. **+ Tags** adds one (commas add several), click a tag's text to rename it, and × removes it. A tag is never added twice and is cut at 40 characters.
- **The right column:** **Mentioned in**, **Linked work** (each item with its state) and **People**. An item's panel says when notes mention it, with a link to each.
- **The ⋯ menu:** pin or unpin, mark **Confidential** (kept out of Prep pages and out of what search gathers for Claude) and show the file.
- **One editor:** a note uses the same editor as Current state, an item's text fields and Prep's notes, with the same keys, Undo ([[⌘Z]], [[⌘⇧Z]]) and paste cleaning. For **AI on a selection**, see [Let creaite draft the wording](#let-creaite-draft-the-wording).
- **Turning lines into work:** notes are passive. Nothing reads them for the tracker until you press **✦ Find updates** ([Find updates in a note](#find-updates-in-a-note)). The sweep and the minutes never do.
- **ask creaite reads your notes:** a question finds and cites them, labelled "Note (internal)". A confidential note's text is never given to it, only that one matched.
- **Plain files:** each note is a Markdown file with a small header, readable in Finder and OneDrive without creaite. Search ([[⌘K]]) finds notes in their own **Notes** group, and **Files** lists each project's notes folder.

## Early warnings
- A lightning flag marks trouble before anyone reports it, and hovering shows the reason. It shows on the item in Work, Today and the project page, in the detail panel, in the project's **Early warnings** card and evidence row, in the portfolio's evidence and in the weekly report's facts.
- **The signals:** an action re-dated 3 or more times; a risk raised in 3 or more meetings or sweeps with no response; a milestone whose forecast has moved later 2 weeks running (and still is); an action open more than twice as long as the project's usual (at least 14 days); a pending decision past its needed-by date; one person owning more than half of a project's open items (at least 6; owners only, never in a client report); and a dependency attached to a milestone that is due after the milestone's forecast, or is overdue while the milestone is within 14 days ("ABC-M-002 is forecast for 20-11-2026, but dependency ABC-005 isn't due until 30-11-2026").
- **Weekend due date** (on unless you switch it off): an open action or RAID item due, or a pending decision needed, on a weekend day. The item's panel offers the Friday before or the Monday after.
- They are worked out from what creaite already holds each time the dashboard is built, and never stored as items. **Settings › Advanced › Early warnings** switches each off or changes its threshold. Warnings are evidence, not health: they never change a project's health on their own.

## Meeting prep
- **Prep on Today:** each of today's meetings, and any later day in the day line, has a **Prep** link (private meetings don't). It opens a short brief for the meeting's project: open actions (overdue first), risks and issues with no response, decisions since the last meeting in the series (or the last 7 days), decisions still needed (late first), revisit dates that have come, early warnings and the project's latest weekly report, client report and steering one-pager. Each line opens its item over the brief. In a steering meeting the decisions needed are Today's **Decisions needed** rows, with **Decide**, **Chase** and **Open**. The how-to pages: [Prepare for a meeting](#prepare-for-a-meeting), [The prep page](#the-prep-page), [Shape the meeting around one thing](#shape-the-meeting-around-one-thing), [Draft an agenda](#draft-an-agenda).
- **Which project:** the project comes from the meeting title, a code, name, alias or keyword in the register. A title that says "portfolio" or names several projects gets a cross-project brief. If creaite isn't sure, it asks you to pick the project (or Portfolio) and remembers the choice for that series (the title without numbers).
- **Ranked by the invite:** the items the invite makes relevant come first in each list, each with why (words it shares with the item, a workstream or milestone it names, an owner who is invited). The rest follow, so nothing is hidden. **Invite** (collapsed) shows what creaite read.
- **The prep page** is one file, light or dark, printable, marked **Internal** and never sent. It is saved in the project's Agendas folder (the portfolio's for a portfolio meeting). Pressing it again the same day replaces creaite's own page; a page you edited is left alone and the new one gets a number. With projects in OneDrive, creaite asks once before saving. **Settings › Essentials › Look and help › AI drafts: shape the meeting** turns shaping off.
- **Confidential:** a note marked **Confidential** is never given to Claude, not even its name, and any finding that cites it is dropped. A confidential meeting is prepared from its title, times and the tracker only. A private meeting isn't kept at all.
- **Times** show in your laptop's time zone. The sweep keeps each invite's text (without the join link, meeting ID, passcode or dial-in numbers), attendees and attachment names on this laptop.
- **Coverage:** when a meeting had an agenda (a file in the project's Agendas folder for that day, or creaite's prep page), the minutes mark each point **Covered**, **Touched on** or **Not discussed**; only the agenda's own words are kept. **Carry to the next agenda** puts a point that wasn't covered on the next prep page, under "Not covered last time".
- **Follow-up:** **Draft the follow-up email** from the minutes; see People › Draft email.
- The brief reads what creaite already holds, so it shows without the live server. Nothing on it is sent.

## Capture a note
- **[[⌘⇧N]] from any page** (or ⌘K "New note") opens the note drawer at the right, without leaving the page. Notes are saved in the project's Notes folder and become tracker changes through **Find updates** on the note, not through Review.
- **The project** is guessed from the register with the rules the minutes use: a code or a Teams channel; the project's name, an alias or client name; a stakeholder listed under that project only; a sender or client domain; or two keywords. One keyword isn't enough, a shared name never counts, a word in a project's Exclude column rules it out, and signals for two projects ask you to choose. The reason shows beside the project, and changing it makes it yours. No guess is **Unfiled**.
- Type [[/]] for the same menu as Notes (headings, lists, checklist, quote, code); short names work (`h1`, `ul`, `ol`, `todo`, `bq`). [[Esc]] closes the menu first, then the drawer.
- **Saved as you type:** the text is kept as a draft a moment after each pause ("Draft saved 10:42"). **Done** ([[⌘↵]]) writes the note, backed up, and **Activity › What ask creaite changed** can undo it. A taken name gets a number. Closing the drawer keeps the draft, and **Discard** drops it.
- **Done and find updates** saves the note and opens it on its project's Notes tab with Find updates beside it. **Recent notes** at the foot list drafts not yet saved first, then the newest notes.
- **Note for this meeting** (on Today, under any meeting but a private one) starts the Working session template with the meeting's title, date and who was invited. A confidential meeting gives only its title and date.
- In ask creaite, a message starting `note:` saves a note the same way. It needs the live server.

## Updates from meetings
- When Claude processes a meeting matched to a project, that project's **open items are expected** in it. For the ones the transcript (or a quick note) discusses, it proposes an **update** instead of a new item: a status, a new due date, a response to a risk or issue, or a latest update. Items not discussed are left alone.
- In Review the updates sit under the meeting's minutes, labelled **Update**, with the item's ID, each changed field as before → after and what was said. An update that **closes** an item is approved on its own: **Approve routine** and **Approve all from these minutes** skip it.
- **Probably done:** a passage in a meeting (or, from the sweep, a mail you sent, a reply or a Teams message) that shows an open item finished becomes a closing update marked **Looks done** or **Maybe done**, with the words that show it. It must come from the item's owner or you, or name the owner. Teams counts a little less than mail. **Settings › Essentials › Look and help › AI drafts: probably done** turns it off.
- It never changes an owner, title or project (use Review or ask creaite), and never proposes an open item again as new. Raising an open item again is still counted, so repeated risks show up in the early warnings. If you change an item before approving, the update is held as a conflict instead of overwriting your change.

## Find updates in a note
- **✦ Find updates** reads the lines that are new or changed since you last ran it and opens a panel beside the note until you close it (**Close**, or [[Esc]]). Each line that gave a change gets a numbered marker, and its rows carry the same number: pointing at either highlights the other.
- Rows are grouped: **New** (an action, risk, issue or decision), **Updates to existing items**, **Milestones** and **Project information** (a new person for the people register, a line for the project memory, a project detail). Lines with nothing in them are left alone and counted ("1 line left as a note").
- **Ticking a row is your approval.** Routine rows (a new action, a due date, done, an owner) start ticked. New risks, new decisions, milestone moves, health changes and memory lines start unticked. A hedged line ("probably", "might", "to confirm") never moves a milestone or changes health: its row is marked **Tentative** and can't be ticked, and an action to confirm it is proposed beside it.
- Click a row to edit it first. Each row is checked against the tracker's rules, and one that fails says why and stays unticked. Rows also carry **Looks like**, **Probably done** and **Vague title**.
- **Apply n changes** writes the ticked rows as one change, and **Undo** in the message reverses all of it. **Save for later** puts them in Review instead. Unticked rows are never kept. Without the live server, Apply saves them for Review and says so.
- Each item's source is the note and its line, and its source link opens the note there. creaite remembers what each line became (the line's number, a fingerprint and the item IDs, never your words), so running Find updates again looks only at new or changed lines. A line already sent shows a ✓ in the note's margin, and editing it takes the tick away. Undo makes the lines new again.
- Claude sees only the note's new lines, the project's open item IDs and titles, its milestones and the people register's names, with no tools. A **Confidential** note asks once before its lines go to Claude, and its new items are labelled Sensitive. Find updates only runs when you press it.

## Minutes view
Where: Review › Open draft on minutes · address `#minutes=`

- **Open draft** on a meeting's minutes in Review opens them as a page under Review (it needs the live server). The decisions, risks, issues and actions in them are the items under them in Review: a change to a row changes the item. Filed minutes are never saved over; a change is saved as a new version.
- **The bar:** the versions, **Internal**, **Distributed** or **Side by side**, **Transcript**, the checks, **Export** and **Approve minutes**. With the transcript open, a line's time tag jumps to the place it came from. Time tags are for you: they are never exported.
- **Each item row** has an owner and a deadline. A deadline said in words (Friday, next week, end of month) is worked out from the meeting's date and marked as a guess: click it to see the words and change the date. **Looks like** shows an item it repeats. **Remove** drops the item and its line, and **Keep the line** keeps the line as text; both have Undo.
- **Coverage:** an agenda point the meeting didn't cover can be carried on, made a separate session or marked no longer needed, with Undo, and optionally a line under "Not covered in this meeting".
- **Internal-only:** mark a line or row Internal-only and it stays out of the Distributed version, as does any Sensitive, partner-only or excluded item. **Distributed** shows what would be shared; **Side by side** shows both and levels them.
- **Approve minutes** shows what will be applied before it is: the minutes and the ticked items, in one apply with one Undo. Actions and updates are one tick; a new decision, a decision recorded or withdrawn, a new risk and an update that closes an item each need their own tick; a milestone change never goes with the minutes. Unticked items stay in Review. If the apply fails, nothing is kept.
- **Export** files the Distributed version as HTML, Word or PDF beside the minutes, under a new name each time; only approved minutes can be exported. **Draft the follow-up email** (also in Export) writes it from the version on screen: the Distributed one holds nothing the Distributed minutes leave out, and the Internal one is marked Internal. Attendees' addresses come from the people register. creaite never sends it; copy it into your mail.

## The report sheet
- Reports and minutes are edited on an A4 **sheet**. **Zoom** with the buttons, a pinch or [[⌘+]], [[⌘-]] and [[⌘0]] (40 to 80%); page breaks are marked.
- **Sections:** drag one (or [[Alt+↑]] and [[Alt+↓]]) to move it, **Hide** or show it, rename a heading and **Reset the heading**. A row or a figure has an eye to leave it out of the export, and figures can be reordered. A hidden section or row is never exported.
- **✦ on a section** finds the source of a line, runs its check, or suggests a fresh draft. Source tags and checks show as you write. Select text and press **AI** for the usual suggestions, plus **Polish** (spelling, grammar and light smoothing; facts and length kept).
- **Side by side** shows two versions, scrolling together and levelled. **≠** marks a difference, and **Match internal** copies the internal wording across for that section or all of them. **Show as exported** shows the page as it will be filed.
- It saves as you write (and [[⌘S]]). If the report changed somewhere else, the sheet says **This changed somewhere else** and offers **Reload**; it never overwrites.

## The client view
Where: Reports › a project › the client report · address `#client-report=`

- The client report is edited beside its internal week: **Client report** or **Side by side**. **Match internal** copies the client-safe wording, Current state and health across; tags are never copied, and a table only shows the rows marked client-visible.
- **Client health** can differ from the internal health, but you must give a reason. The reason is kept in the draft for you and never goes into the filed client report.
- Each item can be left out with its eye; **Not in this report** lists what is left out and why (not client-visible, Sensitive, partner-only or confidential).
- **Before every export** creaite checks what is left out and shows it: what was kept out and what is now client-visible and could be added. Nothing Sensitive or not client-visible reaches the file. The client report's **Approve** and **Export** wait for the internal week to be approved; **Refresh from the approved week** brings an earlier client draft up to date.
- It is never sent: file it and send it yourself.

## AI drafts
- **A draft is a suggestion, never a save.** It lands in a field you edit, a proposal in Review you approve on its own, or a box with Use and Discard. creaite chooses the facts from the tracker and the vault, and Claude only words them, one run at a time, with progress and **Stop**.
- **Sources on every draft:** each sentence carries the sources it rests on, and one with none is marked **no source** before you see it. Confidential or restricted sources are skipped, and client wording is written from the item's own text only.
- **Where:** see [Let creaite draft the wording](#let-creaite-draft-the-wording). Movement's slip range also has a one-line explanation worked out from its own numbers.
- **AI on selected text** gives a suggestion for just that text, with Accept, Discard, Try again and Show changes, and a plain-code check under it that names any date, number, name or item ID it lost or added. Claude runs with no tools at all.
- **Spotted by plain code at extraction:** a proposal that repeats an existing item (**Looks like**) and an open item that a message or meeting shows finished (**Looks done**). Claude, running the minutes or the sweep, judges only the close matches. Both are proposals you decide.
- **Counted, never read:** creaite keeps, for each kind, how many drafts were offered, used as written, used after an edit and rejected. Counts only. **Settings › Essentials › Look and help** turns each kind on or off, and **Activity › Quality** shows the counts.

## Reports
- **Reports** in the left menu shows every project's week, with a count of the projects that need you: a weekly report not yet drafted or still in Review, or a client report that is due. The week is the reminder's: Friday from 12:00 (Settings › Essentials › Your day), then the Friday before.
- **One row per project:** its health, the internal weekly report's state (**Not drafted**, **Draft**, **Filed**) and each client's report with its rhythm (**Due**, **Filed**, **Not due (fortnightly)**). **Needs me** keeps the projects with something to do; **All projects** shows everything, filed ones too. The week control goes back one week.
- **Open** goes to the project's **reporting space**, the same one the project page's **Reporting** card opens. The space has the weeks down the left, newest first, with both reports' state; the internal and the client report as two cards (state, who it is for, how the client version differs, **Open**, **Draft it**); **Edit both**, which opens the client report, where **Side by side** shows the internal page beside it; and the files filed for the week, each of which opens. A client not due that week says **Not due**, with **Make one anyway**. The client report's **Approve** waits until the internal one is approved.
- **Open** on the internal card goes to the weekly report (`#weekly=…`), on the client card to the client report (`#client-report=…`); the project page's Reporting card and ⌘K (**Weekly report: …**) go the same way. The space's own address keeps the project and the week. Approve and Export arrive with the report editor.
- It only reads: nothing here drafts, approves or sends a report by itself, and creaite never sends one.

## Review
- Claude's proposals wait here until you decide. An action, risk or decision opens over the page like a work item, with **Reject**, **Cancel**, **Save** and **Save and approve** at its foot; edits stay in the proposal until you choose. The jobs are in [Review and approve proposals](#review-and-approve-proposals).
- **New items arrive on their own.** When a sweep finishes, an open dashboard updates within about a second with a quiet "3 new items in Review". If you are editing, a chip says **New items arrived: refresh** and the page refreshes when you finish or click it. A page left open while the live server restarted says **This page is out of date**, with **Reload**. A dashboard opened as a file is a snapshot.
- **Approve routine** never covers draft minutes, reports, health changes, new decisions, a decision recorded or withdrawn, new risks, closing updates, conflicts or items without a project. (A promise marked Done or Dropped is the one closing update it covers, unless it only **Looks done**.) It acts on what the filters show and previews first, as does any batch over 25.
- **Select several** gives a bar at the bottom: how many can be approved together and why the others can't (point at the count to see each one named), **Approve**, **Reject with a reason**, **Set** project, owner, due date, workstream or milestone, and **Select all**. A change is checked item by item; any refused are named and the rest change, with one **Undo** ([[⌘Z]]).
- **Stale** proposals (older than the stale setting) carry a "Stale · 12 days" tag and are never removed. **Open source** opens the file or message an item came from. A promise that looks kept, and an item that **Looks done**, are approved on their own.
- **Marks and guesses:** the hints are **Looks like**, **Update an existing item instead**, **Looks done**, and the grey "guess" on each row. They can be turned off in **Settings › Essentials › Look and help** (the AI drafts rows); how close a match must be is **Settings › Advanced › Review › Duplicate likeness**. The jobs: [Reject, with a reason](#reject-with-a-reason), [When it looks like something you have](#when-it-looks-like-something-you-have), [When creaite says Looks done](#when-creaite-says-looks-done).
- **One at a time** shows one proposal with its source beside it ("n of m"): what creaite guessed first, then what needs you, then a spot-check of one routine item in ten. The rest are approved together at the end, by the same rule as **Approve routine**. Where you stopped is kept for that batch.
- Items from draft minutes sit indented under them (▾). **Approve all from these minutes** approves the routine ones; the minutes, new decisions and new risks still need approving one by one. Rejecting the minutes leaves their items for review, with an option to reject them too.
- Items without a project need one before approval. When you choose one, the panel may offer to **remember** the signal that decided it (a sender, domain, channel, alias or person), so similar items match next time. Undo removes it. See [Fix the wrong project](#fix-the-wrong-project).
- A **conflict** (an edit to something that changed after it was proposed) shows the tracker's current value and this one side by side, with **Keep current** and **Use this one**, both with Undo. Without the live server, say `keep 5` or `override 5` in Claude Code.
- When the queue is empty, it says what you did this session, with Undo for the last batch.

## Intake
- Intake has two sections, **Calendar import** (pick meetings from your calendar and process them) and **Upload files** (drop transcripts or minutes you already have). A note from a call with no transcript is a note ([[⌘⇧N]]). Only one ask creaite run goes at a time, and the Process buttons wait while one is busy. Everything here needs the live server.
- **Calendar import** lists your meetings from Monday of this week to now, by day, newest first: time, title, Teams or in person, organiser, likely project and whether it is processed. Change a project in its menu and creaite remembers it for that series. A meeting that hasn't ended is greyed and can't be ticked until it has.
- **Transcripts:** the daily sweep looks up each meeting, so a row says **Transcript available**, **Not transcribed**, **No transcript** or **No access**. **With transcripts** shows only the available ones, and **Check again** on a row looks that one up now. Attending doesn't matter: if the transcript can be read, it can be loaded.
- Tick meetings (or **Select new**; private meetings aren't listed) and press **Process n selected**. creaite loads each transcript and the meeting chat, drafts the minutes, and the row says **Draft ready in Review** or why it couldn't. A meeting with nothing to load is **Skipped**, and the others carry on. **Load into inbox** loads without processing, and **Remove** takes a loaded transcript and its chat out together, with **Undo**.
- **Clear day** and a row's **×** set meetings aside so they don't return after Refresh or the next sweep. **Cleared (n)** shows them with **Restore**. Clearing is not processing: nothing is written to the tracker. [[⌘K]] offers "Intake: process meeting …" too.
- **Upload files:** drop transcripts or minutes onto Intake, or choose files (.vtt, .docx, .txt, .md or .pdf, up to 25 MB each). A file with the same name is kept alongside. Each shows its likely project and a state: New, Processing, Draft ready or Already processed. **Preview** (the eye) shows its text, and the bin removes it from Intake, with **Undo**. Tick files and press **Process selected**. Nothing is filed until you approve.

## Files
- The files you work with, by project and folder: **minutes**, **transcripts**, **reports** (**Weekly** with the client reports, **Adhoc** and **Steerco**), **agendas**, and Intake. Steerco is only listed: creaite files nothing there. Quick views: **Latest reports** (the newest file in each report folder, for each project), **This week's meetings** and **Intake**.
- **Project documents are set aside:** not listed and not scanned, so the page opens quickly. Search still reads them. **Settings › Advanced › Work and views › Files: show documents** brings them back. Milestone files, images and the archive are left out too.
- **Agendas** are not documents. Each project's **agendas** folder has its own count and holds the prep pages creaite saved and any agenda you keep there. A prep page opens in the browser and the others in their own app.
- **Always current:** the list rescans when you open Files or Intake and when the window regains focus (at most every 10 seconds). **Refresh** does it at once. New files carry a **New** tag until the next time you open the page. If a scan fails, the old list stays with a message. A dashboard opened as a file keeps the list of its last build.
- A meeting's date comes from its name (`2026-10-01 Title`, or the Teams form `Title-20261001_093000-Meeting Transcript`). With no date in the name, creaite uses the file's own and Review says so.
- Filter by name, type and date. Word files open in Word, and the folder icon (**Open folder**) shows where the file is.

## Milestones: Plan and Movement
- **The page** (the pencil on a project's Milestones card, [[⌘K]]'s **Add milestone**, a milestone in search, an answer or Activity) has its own address, so Back, a reload and a link keep it, with its view and the open milestone. The breadcrumb returns to the project, and the switcher moves between projects.
- **Three dates and an actual:** **Original** (first agreed), **Agreed** (now, after any rebaseline) and **Forecast** (what you now expect), plus the date it was **Achieved**. Variance is measured against Agreed.
- **Five states, in shape, word and colour:** Achieved ✓, On track ●, At risk ▲, Slipped ◆, Overdue ✕, the same on the page, in the reports and in the one-pager. The dates suggest one: Overdue when the agreed date has passed and it isn't achieved, Slipped when the forecast is later than agreed, On track otherwise. At risk is only ever yours. Pick any state: creaite asks for a one-line reason only when you pick one better than the dates support, and **Use <suggested>** returns to the dates. Achieved asks for the date and sets 100%.
- **Plan** is the clean view of what is agreed, with **Internal view** and **Client view**. **Movement** is internal only: each open milestone on a shared month axis (◇ original when rebaselined, | agreed, the forecast shaped by its state, a red line for the distance past agreed) with "+7 d vs agreed", "+28 d vs original" and "Moved 3×". Select one for a chart of forecast and agreed date by reporting week, **What changed** (each move, rebaseline, state change and achievement, with its reason), its **slip range** and your **Internal note**.
- **The slip range:** from how your own milestones have slipped, creaite gives a likely range for an open one ("Likely 27-11-2026 to 11-12-2026"), the 50th to 80th percentile of how much later closed milestones that slipped finished. It shows only once 8 such closed milestones exist ("No range yet: 3 of 8 closed milestones with history") and says **Thin evidence** while fewer than five projects have them. Internal only.
- **Decide what to do:** **Hold** (with a reason, recorded as a decision), **Rebaseline** (a new agreed date, who agreed it and why; it records a decision), **Add recovery action** and **Escalate to steering**. Each is staged for Review, and nothing changes until you approve it there.
- **The milestone editor** opens beside the page. Each change saves on its own with Undo, and every date is a calendar pick. A click outside closes it, except on another milestone (it switches), while a calendar or the people list is open, or while a change waits for its reason. **Progress** is set by hand, never worked out from actions. **Cancel this milestone** keeps its history and hides it everywhere.

## Activity
- Every change, newest first: when, what changed and by whom. **Undo** reverses a change not yet applied, or the latest apply.
- **Quality** (the second tab) counts what you approved as proposed, approved after an edit and rejected over the last four weeks, by source and by type, with the reasons given, the fields your edits change most and how each kind of AI draft was used. Every figure is a count out of its total ("11 of 192"), and a group under 10 isn't rated yet. It counts extraction and drafts, never a person, and no report or export reads it.
- Each line starts with the item's icon (action, risk, issue, assumption, dependency, decision, milestone, project, weekly update, file); point at it for its name.
- **Search and filters:** the list shows the newest 300 changes. The box at the top (press **/**) looks through the newest 2,000 and narrows the list as you type, by an item's ID or words, the project, who made the change, the change itself or the date. It shows "12 of 340" and **Clear**. The type buttons and the **From** and **to** dates narrow it further, and dates take words such as "yesterday" or "15-10". The search stays in the address.
- **Undo several older changes:** tick the lines (click, ⌘-click, Shift-click; [[Esc]] clears), then press **Undo n**. creaite shows what will happen first: each field goes back to what it was, only where it still holds the value that change gave it. Anything changed since is skipped. Over 25 changes it asks again. It is one new apply, "Undid 3 changes", with its own **Undo**.
- **Item IDs are links:** click a work item's ID to see it in the side panel ([[Esc]] closes it). A milestone opens on its page, and a project name opens the project. ⌘-click opens the item in a new tab.
- **What ask creaite changed** (below the list): every file ask creaite created, changed, moved or deleted in the last seven days, with its tier (**Ordinary**, **Sensitive** or **High-risk**), why and **Undo**. Undo is refused if the file has changed since, so nothing you did is lost.

## People
- **People** in the rail has two tabs. **With work** (where it opens) lists everyone with an open action, an open risk or issue, or a decision waiting on them, with their counts and how many are overdue. You are first. **Nothing assigned** lists the other people creaite knows: those in the people register and anyone whose items are all closed. A made or withdrawn decision is history, not work. People move between the tabs by themselves, and each tab sorts on its own. Counts only: there are no scores or ratings.
- Select a name for their page: the actions, risks and issues they own, grouped by project; the decisions we are waiting on from them and the ones they made in the last 90 days; the workstreams they lead; early warnings; and what they closed in the last 14 days. The tables are Work's own rows, with your column choices and no Owner column. Select a heading to sort, a row to open it, double-click a cell to edit, and [[J]]/[[K]] to step. **See all actions in Work** and **See all risks and issues in Work** open Work filtered to this person.
- A name is a link wherever an owner appears, and your own opens My work. Press [[⌘K]] and type a name to go to their page.
- **Edit details** (the pencil, or **Settings › People and projects › People**) changes email, aliases, organisation and role. A "not in register" tag means the name is on items but not in the register yet: **Add details** puts it there.
- **Finding people** in Settings › People and projects › People: search by name, alias, email or role, or use the funnel ([[F]]): **Project**, **How they're involved**, **Organisation**, **People I follow**, **In the register**, **Needs attention** and **Removed people**. Ticks in one field mean any of them, and fields combine. Your filters are kept until you clear them. Removed people are hidden at first, and **Show** brings them back.
- **Hand over…** adds a tick column to the tables. Tick the rows, choose who takes them (a new name is checked against the register first) and press **Hand over**. It is one change, with one **Undo**.
- **Draft email** opens a ready-to-send email for you to copy into Outlook: creaite never sends mail or makes an Outlook draft. It has a greeting, their open actions and risks and the decisions we need from them by project (overdue in red, due soon in amber, always with the words too), a kind request for an update and a Subject starting with the project code. Tick the items, add a **Please reply by** date, and edit it in place. **Copy email** copies the table and colours with a plain-text version, and **Copy as plain text** copies just the text. For someone outside your own domains, or with no address on record, items that aren't client-visible start unticked and marked internal. Confidential or restricted items and anything from a project's documents are never included, and the latest update only if you tick it. Nothing is saved.
- **Three kinds of email, one builder:** **Update request**, **Chase overdue items** (the tone steps up with how often each was chased, and **I sent it** records the items and the date, never the text) and the meeting **follow-up**. **Polish** rewords the opening paragraph only. **Draft chase** (the envelope in an item's top bar) drafts one item's email: a chase to its owner, a decision request to its decision maker, or, for your own item, a request for help to someone you choose. See [Ask someone for an update](#ask-someone-for-an-update) and [Chase one item](#chase-one-item-or-ask-for-help-with-your-own).
- **People you follow** are private to you, so nothing marks them on screen or in what creaite writes. In Work the funnel can show only their items, and an overdue open item one of them owns is an early warning (**Settings › Advanced › Early warnings**). Anything they send is alerted at the top of Today, under **Messages to see first**, until you press **Dismiss** or **Create work item**; a private or confidential message is alerted too, and its text is never kept. Set it in the register (Management, Client or Yes) with **Edit**. See [Never miss a VIP](#never-miss-a-vip).

## Workstreams
- Each project has its own workstreams (FAL's Cut-over and TID's Cut-over are separate), each with a **lead**, **keywords**, **aliases** (e.g. UAT for Testing) and a Teams channel. creaite uses them to put items from minutes and mail in the right workstream, from the item's project only.
- **Settings › People and projects › Workstreams** lists them by project: **Add…** (creaite suggests keywords, aliases, lead and channel from the items that mention the name; change anything), **Edit**, **Close** or **Reopen**. Renaming one renames its items too; a closed one can't be chosen for new items, but items already on it keep it. Every change is a proposal, with Undo.
- In an item, the Workstream list (under **Details**) offers that project's workstreams. **Add workstream…** (or a new name typed in the list) opens its details, suggested from the project's items; **Add and use it** stages the new workstream with the item's change, so **Apply** adds both and **Undo last** removes both.
- Workstreams are managed in Settings (the project page doesn't list them). In Review, an item from minutes or mail that named a workstream its project doesn't have offers **Add workstream** or **Leave blank**.
- They're in the Excel export too, on the Workstreams sheet, editable like the others.

## Search
- **Search the vault** at the top of Files finds tracker items, meetings (minutes and transcripts), notes, reports and documents, in groups of up to 20, as you type. It needs the live server.
- It understands what you type. A project code, a person's name, alias or email, a type (risks, decisions, minutes, reports…) and a date (today, last week, since 01-09-2026, in September) become **chips**, and × drops one. The other words are what it looks for: "slip" finds "slipped", and the last word matches as a prefix.
- A result opens where it belongs: an item in its panel, a meeting in a preview scrolled to the match, a report or document in its own app. Documents are labelled "Document · internal".
- [[⌘K]] has a "Search the vault…" row once you've typed three characters, with the top five results. [[Esc]] clears the box and brings the file list back.
- **ask creaite** (the spark button beside the search bar) is dimmed until you type. It is highlighted with a small ↵ when what you type reads like a question (it ends in "?" or starts with what, why, how, when, who, did, has or is), and then Enter asks; for any other text Enter just searches. Claude answers in a few lines from the best passages and tracker rows, citing the file and section or the item ID for every point, as links. If your files don't answer, it says so. **Stop** cancels, and **Continue in ask creaite** carries the question on. Search answers aren't kept as chats unless you continue them.
- **Summaries and tags:** when minutes are processed, and when a weekly or client report is made, Claude writes a two-line summary and three to eight topic tags for it once. Search matches them, so you can find a meeting by what it was about. Say `setup` to fill them in for meetings and reports you already have; it asks first.
- **What it reads:** the text of Word, PowerPoint and Excel files, transcripts, text files, PDFs, creaite's own report and minutes pages (never what you hid) and emails saved as .eml (sender, recipients, date, subject, body and attachment names; drag a message from Outlook to Finder to save one). A scanned or password-protected PDF, and any other file, is found by its name only.
- The index is rebuilt after every apply, when the live server starts, and when a search finds it older than the newest file.

### Settings and housekeeping

## Settings
- **Four places:** **Essentials** (opens first: your name and weekend, when the morning sweep runs and what it reads, Close the day, the weekly report reminder, Save my changes at once, what the Week ahead shows, the people you follow, theme, style, motion and AI drafts, the daily backup), **People and projects**, **Advanced** (every other setting, each with its default and why) and **Health** (what needs you, then the live server, Set-up, Diagnostics, the creaite version and **Stop the live server**). Each change saves at once, with a backup and a log line, and a quiet **Saved** appears beside the row.
- **Changed and Reset:** a dot marks a setting that differs from its default, and **Reset** puts it back. A setting fixed at set-up (the folders, the port) shows its value and why, with no Reset.
- **Search** finds a setting by its label, its line, why its default was chosen or its old key, across every place. [[Esc]] clears it.
- **Reports and minutes** (Advanced): **File report exports beside it** (off to start with: an export of a weekly or client report stays out of the reports folder unless you turn it on) and **File minutes exports beside them** (on). An export never overwrites a file.
- **Ignore rules** (Advanced › Sweep): mail, Teams messages and calendar entries the sweep skips even when they name a project, such as invites beginning "ToDo" and, built in, anything marked private or personal. A thread or meeting you name is never skipped. Only counts are kept.
- **Health** checks creaite when you open it (**Check again** runs it again) and lists only what needs you, one line each, with **How to fix** (**Copy** for a command). A fix creaite can make itself (the launcher, Python under Rosetta, the OneDrive backup copy) says what it will do and has a button, **Fix it** or **Make it now**. **Folders still called zz Archive** (the old name for an archive folder; creaite now calls it _Archive and skips both): **Fix it** shows each rename on the approval card in ask creaite, and nothing moves until you **Approve**. **A sweep lock is held with no sweep running**: **Release** removes it. After every update creaite remakes the launcher, refreshes the icon and restarts the live server itself. What is fine folds into one line ("30 checks fine").
- **Archiving:** **Archive 14 reports and minutes older than 12 months** appears once a month while there are any. **Archive them** shows each move on the approval card, and on **Approve** they move into the engagement's own _Archive. Links keep working and nothing is deleted; they are no longer searched, ask creaite never reads them, and **Undo** moves them back. In **Files**, **Archived** shows them with **Move back**. Once a day creaite also archives closed or cancelled actions and RAID items and done or dropped promises six months after they closed. They leave Work, Today and the Excel export; search still finds them, marked Archived, and editing one un-archives it for another six months. Decisions, milestones and open items are never archived. The periods are in **Settings › Advanced › Archiving**.
- **The sidebar:** Today, Work, Review, Projects and People are at the top. **More** opens on Intake, Files, Activity and Settings, with **Customise sidebar…** at its foot, and a number on More adds up what is waiting inside. [[⌘\\]] collapses the sidebar to a rail of icons, and your choice is remembered. **Customise sidebar** (also [[⌘K]] › "Customise the rail", or a right-click on the sidebar) has two lists, **In the sidebar** and **In More**: drag a page by its handle or use its arrows. Today always comes first. **Reset to default** puts the lists back, and nothing changes until **Done**.
- **People and projects:** the **People** register (add, edit, rename, merge, remove from the owner list; a rename fixes every item, with Undo) and each project's **Workstreams**. **Projects and register** has **Archive** beside each project: a finished project's folder moves to _Archive, and it and its items leave Work, Today, the Excel export, the reminders and project matching. If it has open items they are listed first: **Cancel them all and archive**, or **Stop**. The change waits on the approval card, and **Undo** reverses it. **Show archived projects** brings them back, with **Restore**. A restored folder whose name is taken gets a number, and an archived code is never reused. Or say `archive project ABC` or `restore project ABC`.

## Client messaging
- Actions and RAID items use three headings: What it is, What it means for you, What is being done.
- Decisions use plain wording, with no fixed headings.
- Only needed when the item is client-visible, and checked when you make it client-visible or edit the messaging. You write it, or press **Draft** under it for a suggestion from the item's own text (see [Let creaite draft the wording](#let-creaite-draft-the-wording)); nothing is saved until you leave the field.

## Dates
- Dates are shown as DD-MM-YYYY. Every date field also takes plain words: `today`, `tomorrow`, `yesterday`; a weekday (`fri` is the next Friday, never today; `next fri` the one after); `+3d`, `+2w`, `+1m`; `next week` (its Monday), `end of week` (Friday), `end of month`; and a day and month such as `15-10` or `15 oct` (this year, or next year when a due date would be in the past). The field shows what it understood ("Friday 16-10-2026") and then holds DD-MM-YYYY; anything it doesn't understand is said in words, with examples. In a field with a calendar, ↓ opens it. The Today page writes them out instead ("Thursday 15th October"; the year only when it isn't this year). File names keep YYYY-MM-DD so they sort in order.

## Sources
- Minutes and document names open the file. Emails show From, Subject and Sent with Open in Outlook; Teams messages show channel, From and Sent with Open in Teams.

## Word documents and permissions in ask creaite
- **One-off Word documents:** ask for one ("make a Word document of open actions for ABC"). It looks at the tracker, says what it will build and asks you to confirm. The result is a branded internal draft: nothing is filed or sent.
- **Your files:** ask creaite can read anything in the vault, your projects folder and your home folder, except secrets (keys, keychains, password stores, browser profiles and saved logins) and the operating system. It changes files when you ask: a new file, your notes, drafts, project files you named. Each change is backed up first and can be undone: **Activity › What ask creaite changed** lists the last seven days with **Undo**.
- **The approval card:** some changes wait for you, listed on one card with the change itself: a change to ask creaite's own permissions or settings, anything outside the vault and the projects folder, a delete or a move, another person's file (a transcript, sent minutes or report, a client's document), more than ten files at once, and any change after it has read mail, Teams, a transcript, a document or a web page. **Sensitive** (a triangle) covers settings files. **High-risk** (a shield) covers permission files and any edit that adds or changes a permission rule, with the way back shown. **Approve** makes all of them exactly as shown, **Decline** none. The card waits 30 minutes and comes back after a reload. ask creaite can ask for a change but can't approve it.
- **Never, whatever is asked:** secrets, the operating system, the files that run commands at login, and the database, the engine and creaite's rules, which change only through their own commands (apply and an update). A permission change that would let it run anything or skip permissions is refused even if you approve it.
- **Project files:** reading is not extracting. It never reads archived, template or online-only OneDrive files, and creating never overwrites (a taken name gets a number). Project documents are internal: nothing from them goes into a client report unless you say so.
- **Images:** paste (⌘V), drop or attach up to four PNG or JPEG images. They are for discussion only, stay with the chat and are deleted with it.
- **Replies** are formatted text: headings, lists, tables and code with **Copy**. An item ID opens the item and a file name opens the file. Each bubble shows when it happened.
- **The running badge:** while it works on anything (a chat, a sweep, a report, Generate, a prep page), a badge at the bottom right says **ask creaite is working…**, what it is doing and for how long. When it ends it says **ask creaite has finished** and stays until you press **×** or open the chat. Press it to open the chat.
- **Runs creaite started itself** (a prep page, Generate, a draft, a transcript check, Close the day's catch-up) show the ask as one plain line, the steps in plain words and the outcome with a link. You never see the instructions or Claude's raw reply. They are kept in History as **Runs creaite started**.
- **Checked against the tracker:** before a reply is shown, every item ID in it is looked up. A wrong title or owner is corrected in place ("⚠ doesn't match the tracker"), and an unknown ID is marked "⚠ not in the tracker". This is plain code and changes only the words shown.
- **A plain "I can't":** ask creaite never sends, forwards or replies to email, posts in Teams, creates, moves or answers meeting invites, changes files in SharePoint or OneDrive online, or starts or stops the live server. It says so first and offers a button to where it can be done.
- **Changing items:** ask ("mark ABC-A-003 done", "Sara owns the SOW action") and it shows a card with each field's before and after, checked first. **Go ahead** saves it like a dashboard edit, with **Undo**. **Cancel** writes nothing. Any other change (add a risk, project details, memory, the register) shows one card, and **Approve** writes it at once.
- **Sweeping:** a message that is only a sweep ("sweep", "sweep mail for ABC") runs at once. It stages proposals only and can't apply or approve anything.
- **Queue, recall, edit:** type while it is working and your message is **queued**, then runs in order. **Edit** and **Remove** change a queued message, and **Stop** clears the queue. [[↑]] in an empty box brings back your last message, **Edit** on it puts it back in the box, and a stopped or failed run offers **Try again**. Your unsent draft stays in this browser for that chat.
- **Over the page:** ask creaite opens on top of the page without moving it, and its left edge resizes it. If a command is refused, the chat says why in one plain line, with **Show the command** for troubleshooting.

## Commands for Claude
As you type in ask creaite, suggestions appear from your skills and commands, with project codes, open item IDs and review numbers where a command needs one; type `/` to see everything. Nothing is chosen until you choose it: **Enter sends what you typed** (type `apply`, press Enter, and `apply` is sent). Press ↓ or ↑ to choose a suggestion, then Enter puts it in the box to finish and send; Tab puts the first one in; a click picks one; Esc closes the list. Drag the panel's left edge to make it wider or narrower (double-click to reset); it remembers the width. The clock icon lists your 10 most recent chats (older ones are deleted); + starts a new one. A request keeps running if you close the panel or reload the page (the ask creaite button shows a dot, and a note tells you when it's done); only Stop ends it. While a request runs, Send becomes **Stop** (or press Esc): a question stops at once, and a confirmed change stops once its current step has finished, so nothing is left half-done.

In ask creaite or Claude Code: `sweep`, `process new minutes`, `review`, `apply`, `undo last apply`, `weekly report`, `client report ABC`, `mark ABC-A-003 closed`, `move ABC-A-003 to 20-11-2026`, `add milestone for ABC: UAT complete 20-11-2026`, `make ABC-A-002 client-visible`, `set sweep time to 06:30`, `import excel`, `setup`, `health check`.

## Updating creaite
- Say **update creaite** in Claude Code: with the GitHub command-line tool (`gh`) installed and signed in, it fetches the newest `creaite-X.Y.Z.zip` (pre-releases included) into `system/releases/` itself and checks it against its checksums (it installs nothing until you say yes). Without `gh`, download the zip from the GitHub release (the attached file, not "Source code (zip)") into `system/releases/` yourself.
- Settings › Health › **creaite version** shows the installed version. **Review** shows what the update changes, with its release notes formatted (**Copy the notes** copies them as written); **Install** backs up, installs and checks it, then asks you to restart the live server. Or say **update creaite** in Claude Code.
- Your `CLAUDE.md`, the tracker, projects and settings values are never changed. **Undo update** goes back to the previous version.

## Open creaite as an app
- **Double-click the launcher.** It starts the live server if it isn't running and opens creaite in its own Chrome window (no tabs). In Chrome you can also use ⋮ › Cast, save and share › **Install page as app**, which gives it a Dock icon.
- **Make the launcher:** ask in Claude Code (`setup`); it offers a small **creaite** app in your Applications folder, or a `creaite.command` file in the vault, and asks first. From Terminal: `system/scripts/run launch.py make-launcher` (Settings › Health › Set-up has it to copy, and **Check again** confirms it's made). The page can't make it itself: it goes outside the vault.
- **One launcher per vault:** your vault's launcher is **creaite**; the development copy's is **creaite (dev)**, with DEV across its icon, so both can sit in the Dock and run side by side, each opening its own vault. If **creaite** in Applications opens a different folder, making it says so and leaves it alone until you ask to replace it (`make-launcher --replace`), and the health check warns about it.
- **It stops itself.** A server the launcher started stops a minute after the last creaite window closes, and never in the middle of a job. A server you started in Terminal is left running. Settings › Health › Live server and backups has **Stop the live server** for a manual stop.
- If the server is stopped when you open the app, it shows “The live server isn't running” with a **Check again** button.
- The app belongs to the port in Settings. If you change the port, install the app again and reconnect the vault. A development copy and a live vault use different ports, so both can run at once.

## Live server and backups
The dashboard runs from the live server on this Mac. Start it in Terminal with:

[start command]

- Leave the Terminal window open while you work, and close it to stop the server. Or open creaite with the launcher (see Open creaite as an app), which starts and stops it for you.
- If the server stops, a red alert appears at the top. Saves are held and applied when it's back.
- The tracker is backed up at the first session of each day and before every apply.
- Each day creaite also makes a closed **backup zip** of what rebuilds the vault: the day's tracker backup, your settings, your own notes file for Claude, the proposals and drafts waiting (never ask creaite's chats or their images, nor who you follow), the vault's history and the flow history, with a manifest. If your projects live in OneDrive the zip is copied there, written whole so OneDrive never syncs half a file. That zip is the only thing besides your project files that leaves the laptop. If OneDrive can't be reached, the copy is made the next day it can be, and Health warns after two days.
- To rebuild a vault, use **Settings › Health › Restore from a backup**: choose a backup, **Preview** shows what it will replace, then **Restore**. Or say `restore creaite from backup` in Claude Code. Either keeps the current database and every file it replaces first, and never touches a project file.
- **Old backups tidy themselves away** once a day: every daily backup for 30 days, then the Monday's for a year, then the first of each month for good, and the other copies for shorter times. Only creaite's own files go, never the newest of each, and it can't be undone. The numbers are in **Settings › Advanced › Safety**. Once a week creaite checks that it could restore. **Settings › Health** shows the last copy, check and tidy-up. The live database never leaves the laptop.

## Troubleshooting
- Red alert at the top (and a hollow red dot under Settings): start the live server (see Live server and backups). Saves are held until it's back.
- **Reconnect vault** in the top bar: you've opened the dashboard as a file. Open it from the live server address instead, or click it and allow access again.
- Something changed by mistake: Undo in the message, or **undo last apply**.
- Something failed: **Settings › Health › Diagnostics** lists the latest errors and has **Copy diagnostics** (a report with no mail, minutes, notes or names). The log itself is `system/logs/debug-<date>.log`, one file a day for the last seven days.
- Anything else: say `health check`.
