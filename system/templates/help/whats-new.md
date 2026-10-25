# What's new

What changed for you in each release of creaite, newest first. Written in plain words; the technical notes are separate.

## creaite 2.6.5

2.6.5 (also called 2.6.4b) contains all of 2.6.4. The headline: Intake leads with the work you have to do, People gets the same Display menu as Work, and a round of smaller design fixes makes the screens calmer and easier to read.

### Intake
- **The work comes first.** The decisions to approve can be reached without scrolling in all three views. Meetings still waiting for a transcript fold away under "Waiting for the transcript". Mail and Teams shows five and a Show all. (#340)
- **A clear Intake names the next job** with one button. The Week ahead offers tomorrow. Later and Not needed appear only when they hold something. (#356)
- **Ticks no longer hide behind a folded waiting meeting.** Folding it, pressing Esc in the search box and changing Group by all clear them.

### People
- **A Display menu like Work's.** Group by, sub-group, order by (with reverse) and properties, and press D to open it. People fits at 900 px. (#360)

### Saving and asking
- **A calm confirmation on a bulk save.** It says "Saved N changes" with one Undo, and the note about the backup is a hover. (#357)
- **The ask creaite box** has a plain accent border when you click into it, with no turning gradient. (#359)

### Design fixes
- **Larger click targets.** The help button, evidence, row ID and source links are 24 px, and nothing is under 12 px on the screens that changed. (#343)
- **Fewer stray words.** No one-word last lines, no stray dots in Review's line, Work hides empty groups and says "overdue" once, the health numbers on the cockpit sit in one row, top risks show an owner, and Step 1 is shorter. (#343)
- **Files** says Word, Transcript or Excel for a file's type. (#343)

### What's fixed
- **A confidential meeting's Prep page and agenda no longer land in a project folder you didn't choose.** Until you pick the project, they go to the portfolio folder, and Claude isn't told which project it is.

### Behind the scenes
- A failed Track change clears the Filed note, and renaming minutes follows an update item's source. (#355)

- Update from the release zip as usual.
- Reload any dashboard tab that was open before the update.
- Walk Today, Intake, Review, Work, People, Files and the cockpit once, looking for anything crowded or oddly worded.

### Good to know
- A file path still shows in a few places, for example the hover on the portfolio folder in Files and the folder on a project's Settings page.
- Help still says past days on Today show each meeting's follow-up. That has been out of date since 2.6.4; use Intake for those jobs.
- After you edit an item, the top can still say "Saved for Review" while the bar below says nothing is saved until you press Save.
- The figure check does not look at the year when the transcript gives a date as a day and month in words.
- The count in the toast after Approve minutes can say more than was saved when a ticked row is held back in Review.
- In a rare crash recovery (a stopped run that started its work in the same minute as an earlier suggestion), the earlier minutes can drop out of Review with nothing on the page showing it.
- Not in this release: the design decisions and one more fix. They come later.

## creaite 2.6.4

2.6.4 contains all of 2.6.3. The headline: the words on screen and in Help are plain (suggestions, save, your project record, your creaite folder, a mail and Teams check), there is a weekly budget for creaite's own AI use that stays off until you switch it on, a set of design fixes, rules for each run that are half the size, and a page that has gone stale is now turned away instead of deciding the wrong item. A few older wordings and paths are still on screen in places; they are listed under Good to know.


### Plain words
- **The words on screen are plain.** What creaite puts forward is now called a suggestion, and it waits for you in Review. Approving a change now says save. The record creaite keeps is your project record, the folder it all lives in is your creaite folder, and looking through your mail and Teams is called a check: Today says "Mail and Teams not checked yet today" with a Check now button, and Settings says "Daily check time". A message that says creaite isn't running says that, in those words. Your own change reads "Saved" with Undo. (#292)
- **Health speaks plainly.** Every title and Fix it button in Settings › Health is written for a person. For example the message about the app showing an old icon now reads "The creaite app shows an old icon", and the one about the launcher now reads "Your creaite app opens a different copy of creaite". The Release button on a stuck check is now "Clear it". (#292)
- **Help and What's new are rewritten in the same words.** The pages and the chat wording now match what the screens say. (#293)
- **Commands.** You can say "check my mail", "check my mail and Teams", "check mail for ABC" or "check my mail the last 7 days" to ask creaite for a mail and Teams check. It runs at once and saves suggestions only. These words already worked; Help and the screens now use them. The older words you used before still work exactly as before. (#292, #293)

### Design fixes
- **Settings.** The tick rows (for example Weekend and "Week ahead shows") keep room for their label, so it no longer squeezes to one word beside the tick boxes. (#337)
- **Activity.** The By column keeps "Rejected in review" on one line at 900 px, so the rows are shorter. (#337)
- **Pencils and charts.** The edit pencils are easier to see (less faint), the small text on the charts is no smaller than 12 px, and the click targets are at least 24 px. (#337)
- **People.** At 900 px the table is tighter and its headings can wrap, so the Overdue column, which it sorts by, is on screen without sideways scrolling. (#337)
- **Milestones in Client view.** When none of a project's milestones are shown to the client, Client view says so, and that Internal view shows them, with Add milestone beside it, instead of "0 achieved, 0 to come". With one milestone it reads "The milestone is not shown to the client yet"; with several, "None of the 3 milestones are shown to the client yet" (the number is how many there are). (#337)

### Minutes
- **Three smaller fixes (#333).** The transcript pane says "1 turn", not "1 turns". A date shown as 20-11-2026 is no longer flagged as a figure the speaker never said when the transcript says "the 20th of November" (or the date in numbers). A possible duplicate from another project is marked only when it is a close match, so there are fewer false matches.

### Chats with ask creaite
- **A weekly budget for creaite's own AI use, off until you switch it on.** Settings › Advanced, in "creaite and ask creaite", has "Weekly AI budget". Switched on, it counts the week's AI use (ask creaite, drafts, the mail and Teams check and the alert check), Monday to Sunday, in dollars (50 to start) or tokens. From 80% a quiet line in the chat warns you. At 100% a request you type either asks first ("Run anyway" or "Cancel") or is turned away until Monday, whichever you chose in "At the limit". The Usage tab shows used against the budget and the date the week ends. With it off, the Usage tab says so and where to switch it on, and nothing is ever held or warned about. It holds only a request you type to ask creaite: the buttons in the dashboard (Review, Save, Undo), the daily check and the alert check are never held. It keeps counts and dates only, never any text, and an ask creaite run cannot raise or reset it (changing Settings needs your approval card). (#334)

### Lighter rules
- **The rules every run reads at the start are about half the size.** The rules file went from 66,315 to 32,736 bytes, about 8,400 fewer tokens each time a run starts, so runs start cheaper. The full wording moved to a reference file that a run reads only when it needs a section. The part with the never list and the approval rules is unchanged, and a test checks that every other "never" is still in the short file or in the reference. What ask creaite may read, change or never touch is decided in code, and that is not changed. You see nothing different and need do nothing. If you want to check: ask ask creaite to delete something inside the .git folder and it still says no. (#338)

### Review
- **A stale page is turned away.** Every way of deciding on a suggestion from the page now says which item it means, and checks it is still the version you saw. If the list changed behind an open page, you read "That item has changed since you looked at it, so nothing was changed. Look at the list again." and nothing is decided on the wrong item. This now covers reject, Approve instead, repeat, make it an update, and moving an item to another project. (#345)
- **Approve minutes checks the items too.** It now checks the minutes and every item you ticked, not only the minutes, so minutes that were read again behind an open page are not approved with different items than you saw. (#345)

### Today and your profile
- **No "no update for 7 days" line on Today.** The line and its Draft updates button are gone from My Commitments. The draft is still there: in Work, select two or more actions and the bar offers Draft updates. (#352)
- **Past days on Today are plainer.** When you look at a day that has passed, the meetings are listed with their times, titles and projects and nothing under them: the labels "No transcript", "Transcript ready", "Not checked yet" and "Minutes made" (and "Draft in Review"), and the Check and Process links, are gone. Check and Process are still in Intake for the same meetings (Intake offers Process and Check again). Today and later days are unchanged: a meeting's title still opens its Prep peek. (#351)
- **A colleague's name no longer shows their details as yours.** If you set your name in Your profile to someone in the people register, the card no longer shows their email, organisation or role as yours. Add my details asks "Is that row you?" before it changes their row. (#348)

### Behind the scenes
- The chat of runs creaite started itself ("Runs creaite started") no longer carries what a run read into your next question. A run that fails to set up leaves nothing behind, and creaite no longer answers "busy" afterwards. (#346)
- If you rename minutes while approving them, the Review page you are on carries on with the new name. A second Review tab that was already open is not brought up to date: its next decision on those items is turned away with "That item has changed since you looked at it" until you reload it. (#345)
- New reports for the team that measure how big each run is at the start, and the size of the rules files. They change nothing on screen. (#87)
- Tests for the draft routes now run in the release checks (#350), and several tests that failed now and then no longer do (#349).


- Update from the release zip as usual.
- Reload any dashboard tab that was open before the update.
- If you want a weekly limit on creaite's AI use, switch on "Weekly AI budget" in Settings › Advanced and set the amount and what happens at the limit. It does nothing until you do.
- Walk Today, Intake, Review, Work, Settings and Health once, looking for old wording or a file path.


- A dashboard tab left open from before the update gets a "reload the page" message instead of deciding anything. Reload it.
- The weekly budget is off by default. Once on, a count that goes wrong never blocks Review, Save or Undo, a mail check or an alert check.
- Not in 2.6.4 (minutes): only the three #333 fixes above are in. The other six wait, among them the count in the toast after Approve minutes (it can say more work items registered than were saved when a ticked row is held back in Review) and the long dates ("23 October 2026") in the minutes headers, which need your decision.
- Still on screen in a few places: a file path or a command (the hover on the portfolio folder in Files, the folder shown on a project's Settings page, the detail lines of some Health checks).
- Help still says past days on Today show each meeting's follow-up ("Transcript ready", "Minutes made", "Check", "Process"). That is out of date since the change above; use Intake for those jobs.
- Still wrong in one place: after you edit an item, the top says "Saved for Review" while the bar below says nothing is saved until you press Save.
- On the People page at 900 px, a long word can still break in the middle.
- The figure check does not look at the year when the transcript gives a date as a day and month in words: "20-11-2027" passes against "the 20th of November". A month word that is a verb ("may") can also pass as the month.
- In a rare crash recovery (a stopped run that started its work in the same minute as an earlier suggestion), the earlier minutes can drop out of Review with nothing on the page showing it.
- Older words you type still work. Help's command table still lists them.
- Not in 2.6.4: fetching transcripts as they appear, the shared-database work (paused).

## creaite 2.6.3

2.6.3 contains all of 2.6.2. The headline: Intake is easier to work through (tick several meetings, one right-click menu, Group by, nested items), the minutes can be exported as Shareable or Internal, the Word minutes carry the project name, date and attendees, and ask creaite starts each question fresh so chats stay cheap. Some older wording is still on screen in a few places; it is replaced in 2.6.4.


### Minutes
- **Export offers Shareable and Internal.** Export now has two groups. Shareable (for sending): Word, PDF, HTML and the follow-up email. Internal (colleagues only): the same, each marked Internal. On minutes you have not approved yet the Shareable files are greyed out, with the reason "Approve the minutes first". The Shareable files say "Sensitive items left out; check the Updates text", because the check covers the item rows, not free wording in the Updates section (see Good to know). (#330)
- **The Word minutes match the page.** The title block shows the project name (with the client), the When line and the attendees, as the page, the PDF and the HTML already did. Shareable and Internal alike. (#331)
- **File the minutes.** Approve minutes now asks first where they will be filed (project and folder, in words) and what they will be called; you can change the name, or cancel and nothing is filed. If the name is taken, it is numbered, for example "Title (2)", instead of stopping with an error. After approving, a note says where the minutes went, with Open file and Open folder; Approved this week has Open folder too. (#324, #326, #332)
- **Keyboard for the minutes.** J and K move from row to row. Y keeps the row as Tracked, M as Minutes only, N drops it. E edits its words, S shows its source in the transcript, Z undoes your last Track choice (keys and clicks, in order). Keys never act while you are typing, and nothing on screen advertises them. (#302)

### Intake
- **Tick boxes and one right-click menu.** Tick several meetings, then right-click: Later, or Not needed because (with a reason), done for all of them, with one Undo. Ticks hidden by a filter are never acted on; the bar says "n selected, m hidden" when some are. (#323)
- **Group by and Show.** Group by None, Day, Project, Meeting state or Transcript. Show picks one meeting state, including "Waiting for the transcript". (#323)
- **A state on each meeting, and items nested under their minutes.** Each meeting shows Waiting for the transcript, Suggestions to check or Done. Its items sit indented beneath it with a count; the row folds and unfolds with the mouse or Left and Right. (#325)
- **The work to decide comes first.** Drafted and Approved sit above the long tail of meetings waiting for a transcript, so the first approvals are in the first screen. (#340)

### Chats with ask creaite
- **A fresh start by default.** Each new question starts a fresh session, carrying only the last four messages of the chat as background, so long chats stop growing in cost. A "Continue this chat" tick in the panel carries on the whole thread; carrying on after Approve does so automatically. Messages queued while a run goes are always fresh. A chat that has read outside material stays marked as before. (#327)
- **A warning when a chat gets long.** After 30 of your messages (a setting) a quiet line offers "Continue fresh with a summary": a new chat with a short summary in the box. Nothing is sent until you add your question and press Send; "Not now" hides it for that chat. (#335)

### Today
- **The "start on sign-in" question no longer shifts the page.** Its place is reserved before the answer arrives on a Mac, so the cards never jump.

### Behind the scenes
- Deciding on a suggestion from the page now always says which item it means; a page without that is told to reload and decides nothing.
- The Outlook draft code is now on the list of files that change only with Alan's say.


- Update from the release zip as usual.
- Try File the minutes on one meeting, and Export Shareable on an approved one.
- Reload any dashboard tab that was open before the update.


- A dashboard tab left open from before the update gets a "reload the page" message instead of deciding anything. Reload it.
- Shareable minutes: a line in the Updates section that repeats a Sensitive decision's words stays in the Shareable files unless you mark it Internal only. This is why those files say "check the Updates text". The Shareable follow-up email's summary has the same gap and shows "Draft: check before sending" on a draft.
- Minutes approved from a Word draft, and ask creaite's own approve command, still stop on a name that is taken; only the page's Approve numbers it.
- Search's "continue as chat" carries an answer that has not been marked as read from outside material.
- The list of chats marked as having read outside material is never tidied; it grows by one entry per marked run.
- The "Routine" grouping in Intake is not built yet.
- Some messages still say "Distributed" where the page says "Shareable".
- The usage report cannot yet split runs by fresh or continued; read the usage log by hand to compare start sizes (aim: under 150,000 tokens to start a plain question, 500,000 is the red line).
- Not in 2.6.3: fetching transcripts as they appear, the shared-database work (paused), and the plain-words pass (2.6.4).

## creaite 2.6.2

2.6.2 contains all of 2.6.1. It adds a way to put an email draft in Outlook, a short "About you" card, an Undo for set-aside minutes, a wider notes drawer, and a handful of fixes that make approving and undoing safer. Some older wording is still on screen in a few places; it is replaced in 2.6.4.


### Email and drafts
- **Create draft in Outlook (off until you switch it on).** In Settings you can turn on a choice that puts a draft email in your Outlook Drafts folder from the Draft email window. It only ever makes a draft: it never sends, changes or deletes anything. With the setting off, or if the draft cannot be made, the window says so in words and gives you a Copy button. (#183)

### You and your people
- **Your profile.** Settings › Essentials has a new "Your profile" card: your name (kept on this laptop), and your email, aliases, organisation and role from your own entry in the people register, with "Edit my details" or "Add my details". Your email is a label only: it checks nothing and gives no access. Which person is you stays on this laptop. (#312)
- **"About you" on first run.** On a fresh install, Today's Getting started asks about you once, before the start-on-sign-in question. "Not now" is remembered in that browser.
- **The follow flag has plain wording.** The People page and Settings say "Follow" and "Follow check" instead of the old name.

### Minutes and approvals
- **Undo for set-aside minutes.** Discard on minutes that were held can now be undone: Undo puts the suggestion back exactly as it was, and it appears in Review again. If the set-aside file has changed, cannot be read, or a suggestion with that name is already waiting in Intake, it says why in one line and does nothing. (#320)
- **Safer approving.** When a list changes behind an open page, approving a row you saw earlier now says no and saves nothing, with the "already approved or changed" message, in the page and in the command. A repeated or malformed check is turned down with what is wrong.
- **A failed save no longer half-saves.** If the history cannot be written (a full disk, for example), an approval or an undo now stops cleanly with a plain message and nothing half written. Before, the change could save without its history.
- **No half-uploaded files.** A file that fails part-way through Add files leaves nothing behind in Intake.

### Notes and Today
- **A wider New note drawer.** Drag its edge, or use the arrow keys on the handle (a bigger step with a modifier key); End goes to the full page width; double-click, Home or Enter puts it back to the default, and a "Reset width" button appears when the width differs from the default. Creaite remembers your width. (#321)
- **Today hides an empty "Needs attention".** When there is nothing in the section, the heading goes too, and comes back when something appears. (#322)
- **The first-run card no longer shifts Today** on a Mac as the page loads.

### Behind the scenes
- A held-minutes marker file over 1 MB is never read, and a pipe or link cannot hang or bypass the check.
- A link in a draft goes through the same address check as everywhere else.


- If you want email drafts in Outlook, switch on the draft setting in Settings, then try it once on a person with an overdue item and check the draft sits unsent in Drafts with its table and colours (Outlook may strip some formatting).
- Answer "About you" or choose Not now.
- Update from the release zip as usual.


- The only setting added is the Outlook draft switch, and it is off by default.
- Not in 2.6.2: the shared-database work (paused), fetching transcripts as they appear (2.6.4 at the earliest), the work on Intake and minutes coming in 2.6.3, and the plain-words pass (2.6.4).
- Shareable minutes: a line in the Updates section that repeats a sensitive decision's words stays in the shareable copy unless you mark it Internal only. This is a known gap to be decided.
- In a rare crash recovery (a stopped run that started its work in the same minute as an earlier suggestion), the earlier minutes can drop out of Review with nothing on the page showing it.
- Someone with write access to your own files can still place a fake held-minutes marker. This is rated low and no further protection is planned.
- Your own live Outlook test is still to be done.

## creaite 2.6.1

2.6.1 contains all of 2.6.0. It fixes the problems found in the first day of using 2.6.0, closes the last places where internal material could reach a client copy, and adds a few things you asked for. Some older wording is still on screen in a few places; it is replaced in 2.6.2.


### Approving and filing minutes
- **Approve minutes no longer fails on an item you already approved.** It skips that item, says which one and why, and carries on with the rest. The message names the item in words, never "Item 6". (#308)
- **Minutes held because the transcript is gone can now be filed.** In the minutes view, Approve minutes offers **File without the transcript copy** in place: one click, Undo, and it says what was saved. "Approve without the transcript" on a held row now really files the minutes (it used to do nothing), and a failed attempt no longer changes the minutes. (#306)
- **Intake can no longer approve the wrong item.** If the list changed behind an open page (you approved in Claude Code, in another tab, or a check ran), a button used to act on a different item. Each row is now tied to its own item; a stale click says "already approved or changed, nothing saved" and refreshes the list. Approve routine does the same and leaves changed items for you. (#307)
- **Every Intake message says what happened in plain words** ("Saved 1 action", "Not saved because …", with no internal file names in them). Add files names each file it could not add and why, and the note stays until you dismiss it. Approved this week now counts minutes made from a dropped transcript, and Restore says so when the file has gone.

### Minutes editor
- The Done buttons are gone. **Track** is three icon buttons (tick, document, cross) that name the chosen one; **Approve minutes** says how much it tracks ("tracks 3 actions"); an attention strip shows how many tracked items still need an owner or a date, with a Next button; Decisions have more room. (#302)
- A **source time chip** on each row opens the transcript at that point and lights the line. (#302)
- The minutes in **HTML and PDF carry the firm's look** (wordmark, colours, fonts, headings and tables), like the Word minutes, and still say Internal or Distributed. (#303)

### Keeping internal material out of client copies
- **Draft the follow-up email** from the minutes is now the shareable version by default; the internal one is a separate, marked choice. Sensitive items stay out of the shareable follow-up, Word, HTML and PDF, including a decision kept in the minutes only.
- A Sensitive item is never pre-ticked for outside attendees, even when it is client-visible, and the follow-up summary comes only from the shareable version.
- The internal Word, HTML and PDF export say "Internal, not for distribution"; the shareable ones say "Distributed". The text the client report writer gets no longer includes Sensitive or held items. (#309)

### Today, Work and Settings
- **Today shows no item twice** across Decisions needed, Your commitments, Needs attention and Week ahead; Week ahead says how many are already listed above. (#313)
- **The day line always runs to the Friday of next calendar week** (Monday 11 days ahead, down to Sunday 5). A day you have not read yet says "has not been read yet" with a Refresh button, never "No meetings". (#318)
- **A Week ahead milestone shows how many open work items it depends on** and opens the milestone, and from there Work filtered to it. (#310)
- **Work items**: marks, compact rows, keys, one-click client-visible, full history. (#241)
- **Read again** on the chat re-reads a meeting's transcript and keeps your Track choices. (#283)
- **Start creaite when I sign in**: a switch in Settings (with a note in Help) so creaite is running after a restart. (#300)
- An avatar menu replaces More at the foot of the sidebar (#295); a switch in Settings turns the single-key shortcuts off (#298); the milestone strip can be made taller by dragging its corner (#301); the People page shows one pencil and a flag saying what is missing (#304); the health Change button is a small icon (#305); internal file names and commands are off the screens that showed them, with a test that keeps them off (#289-#291).


Nothing is required. To have creaite start by itself, turn on Start creaite when I sign in in Settings, then check it once after signing out and in.


- Not in 2.6.1: Your profile on first run, the Outlook draft button, fetching transcripts as they appear, and the rest of the plain-words pass (2.6.2 and later).
- The hardened Add files button is not proven to fix the one case seen on a real Mac; if it still shows no file picker in the app window, open the dashboard in a normal Chrome tab and tell us.

## creaite 2.6.0

2.6.0 contains all of 2.5.4; those items are not repeated here. Old words ("Review", "suggestion", "saved", "check") stay on screen until 2.6.1, so the lines below quote the labels as they appear today.

A bigger release: Intake becomes one page for everything that arrives and waits, the Minutes view is rebuilt as one clean document, approving minutes follows your Track choices, and Settings and People are reorganised.


### Intake: one page for everything that arrives and waits
- Intake and Review are now one page, **Intake**, with one entry in the sidebar and one number. The old Review and Intake addresses open it.
- Three views, remembered in this browser: List, Board and Two panes. Save boxes across the top (Arrived, Drafted and so on, with Show all), each with its count.
- Suggestions are split into routine and needs-your-decision. **Approve routine** approves the routine group in one go, with one Undo.
- Click a meeting row to open it, and again to close it. Enter, N (not needed) and H (later) work on the focused row.
- Each meeting row has Process, Later, Not needed (with a reason) and Restore. **Process all ready** skips private meetings, and Stop ends it. Process and Refresh run as their own jobs with progress and Stop.
- **Add files**, or drop files anywhere on the page. Each file shows its size, its likely project and a kind (transcript, minutes, not sure); a "not sure" file waits for you to choose.
- Minutes written by someone else can be added as minutes: **Find work items** suggests items from them without drafting new minutes.
- A Search box finds meetings, files and suggestions by title, project name or source; Esc clears it.
- **Calendar read hh:mm**, with a refresh icon, replaces the separate Calendar import step.
- A suggestion that changes an existing item opens the whole item in the peek, each change marked "was → now", and you can edit what it changes. Previous and Next step through the suggestions.
- A confidential meeting shows only its title and times; a private conversation never names a project.
- Today's Intake line, the sidebar number and Close the day's "Review now" all point at the one page and show the same number. A file dropped into the inbox gets its row at once, and the page never scrolls sideways at 900 or 1440 pixels. (#232)

### Minutes view v2: one clean document
- **One version of the minutes:** what you see is what is filed and exported. There are no separate Internal and Distributed tabs.
- A **Track** column on every table: a tick makes the line a work item, a cross removes it from the minutes, and neither keeps it in the minutes only.
- Edit in place: click the words and type. Owner, Priority and Workstream are drop-downs in the row; Due opens the usual deadline box. Under an owner who isn't in your people list it says "Needs details", with **Add details**.
- **Approve minutes** is one click with an Undo. A box appears only when a ticked item has a real problem, and it says where. Minutes with nothing ticked can still be approved. Undo leaves the minutes exactly as they were.
- One continuous sheet with a thin page marker that never splits a table row; fit to width stops at 100%; table headers no longer stick over rows. The "done" green and the monospace text show correctly on the page.
- Hover a row to light the transcript turn it came from. Whether the transcript pane is open or closed is remembered.
- Export as Word, PDF or HTML, and **Draft the follow-up email**; both follow your Track choices. A risk or issue keeps its workstream from the minutes.
- Esc on an AI suggestion keeps your words, and reading a meeting again keeps any unsent text in ask creaite. (#268, which also covers #261)

### Approving minutes from Intake follows your Track choices
- Approve on a minutes row in Intake does exactly what Approve minutes does: ticked lines become work items, crossed lines are removed, and lines with neither stay in the minutes only.
- Approve routine and the group tick never approve a line you crossed or left with neither.
- If an approval is stopped, it says so plainly, says the item is back on Intake, and puts the batch and your Track choices back as they were. (#275)

### AI drafts and checks
- Draft email: the AI bar (Improve, Tone, Ask) is back for recipients outside your own domains. It works from client-visible facts only, and its reply gets the client checks.
- AI on the minutes (the ✦, and a section redraft): a suggestion that adds something internal (an item not client-visible, a name, internal wording) is dropped, with a message saying why.
- The client messaging field gets AI suggestions from client facts only, with the same reply check. The item editor offers AI on selected text.
- A drafted reply such as "I can't give a firm date, but …" is no longer thrown away as a refusal. (#186, #262, #263)

### People you follow, on Today
- What the check of mail and Teams takes from a followed person's mail or chat is a **From <name>** row in Needs attention, listing each item. From rows come after the milestone rows; a reply or forward joins its thread.
- Dismissing a From row keeps it gone until the thread adds something new or changes an open item. A private conversation is a title and times only; a confidential or private thread saves nothing for review. No label says the person is followed. (#236)

### Settings, People and project settings
- Settings is reorganised into tabs, one card per group.
- **People** is now the home of the whole register: four tabs, search and filters, add, edit details and remove. Every link to a person opens the People page, and the old Settings addresses for People, Workstreams and Projects open their new homes.
- Removing someone is stopped, with the reason, while they still own items or are named as a stakeholder, milestone owner or workstream lead.
- Project settings is one scrolling page: General, People on the project, Workstreams, Logos, Reporting, and Archive and close. Following someone is set on the project's settings page only. (#246, #247, #248)

### Page keys
- Single keys open pages from anywhere: T Today, P Projects, W Work, I Intake, F Files, A Activity, S Settings, R Reporting, E People. Work's filter picker moves from F to **Shift+F**, and E no longer opens a row in Work (Enter does).
- On Intake, A and R keep approving and rejecting the focused suggestion and never jump to Activity or Reports there (on every other page A opens Activity and R opens Reports). An open peek, ask creaite, a menu or a dialog holds the page keys. (#288)

### Smaller fixes
- A week with no meetings in the calendar no longer stops Refresh.
- The project settings page's people search box matches the People page's.
- An item's source note says "— Actions" (it was "— Action Items"); notes already written in the old words still link to the right section. (#296)


Nothing is required. Find your project's people on the new People page, and try the page keys.


- Some words you will still see are being replaced in 2.6.1 ("Review" on labels that now point at Intake, "suggestion", "saved" and the mail check's old name).
- Not in 2.6.0: Re-read for items on the chat as "Read again" (2.6.1), Plain words (2.6.1), the avatar menu (2.6.1), the work-item refinements (#241), Draft email into Outlook (#183) and fetching transcripts as they appear (#250).

## creaite 2.5.4

A release of fixes and small tidy-ups: Prep opens for any meeting, one stuck item no longer stops your saves, and several menus, icons and pages are clearer. Written only from what landed.


- **Prep opens for any meeting, with or without a project.** If a meeting has no project, the Prep page opens anyway and the Project chip becomes a picker: choose a project, or "No project (general meeting)". Your choice is remembered for that meeting. A "No project" meeting files to the portfolio's Agendas folder and looks across all your projects. If earlier research was done for another project, the page says so and offers Refresh research instead of showing old text. (#279)
- **One stuck item no longer stops everything else from saving.** Saving a work item or approving items used to fail with an error about a field or a missing source because of an older, unrelated item. Now a save only saves its own change. An older item that can't be saved is held in Review and says why on its own row, for example "Can't be saved as it is: … Edit it or reject it" (Approve is switched off until it's fixed), or "Held: transcript no longer in the inbox". For held minutes you can approve without the transcript copy, discard them, or edit the item. Minutes no longer write a field that a decision doesn't have. (#280)
- **The Draft email preview can be resized.** Drag the grip in the bottom corner to make the mail window taller or shorter, in every Draft email window (the dialog and the chase pane). (#281)
- **Exports say "Actions", not "Action Items".** The Word, PDF, HTML and follow-up email exports use the same word as the Minutes view. (#282)
- **The type icon names its type when you point at it.** Actions, decisions, risks, issues, assumptions, dependencies and milestones show a tooltip in Work, Review, search, project pages, the person page and Week ahead, including the milestone markers on the Milestones page and the project's Milestones card. (#286)
- **The health "Change" menu is readable.** It is a compact menu like the others, inside the window, with the current choice marked, in every palette. (#287)
- **A tidier project page and Milestones page.** The project dropdown, the ‹ › arrows and the [ ] keys are gone from both; open a project from the Projects list or search, and its Milestones from the project's Milestones card. (#285)
- **The "?" button is gone from Today's header.** The ? key still opens Help for Today, and Close the day is unchanged. (#284)
- **The "Replied" and "nothing for you" lines on Today can be cleared.** Both get a Seen action. A new ask reopens the line. (#276)
- **A document with a list as its project code no longer breaks the match check.** It is stopped with a clear message instead of failing. (#277)


Nothing is required. Any minutes that were stuck before this release (they failed with an error about a field or a missing source) now show in Review as held items: approve them without the transcript copy, or discard them.


- Each item's source note still ends "— Action Items" in the item's own record; that changes in 2.6.
- Single-key page shortcuts are planned for 2.6.0, and Re-read for items on the chat for 2.6.1.

## creaite 2.5.3

A release of fixes and follow-ups: Process and Refresh calendar run as their own jobs, the last client-export gaps are closed, milestones show on Today, and the alert check pauses overnight. Written only from what landed.


- **Process in Intake runs as its own job.** Pressing Process no longer ends with "I've drafted the files but haven't saved them". It runs in the background with progress and a Stop button, and the minutes and items arrive in Review. The ask creaite panel is used only if a transcript has to be loaded first. (#264)
- **Refresh calendar runs as its own job, and keeps no join links.** Refresh has progress and Stop on the button. The saved calendar no longer keeps meeting join links or passcodes, and a confidential meeting keeps only its title and times. (#265)
- **Milestones on Today.** Needs attention lists a milestone that is due or overdue ("Milestone Pilot go-live is due …"), and "Open all n in Work" opens Work > All items already filtered by that milestone. The Milestone filter is also under More fields. (#251)
- **The alert check pauses overnight and at weekends.** It skips 19:00 to 07:00 and weekends by default (set under Essentials > People I follow), about two thirds fewer checks. The first check after a quiet spell looks back to the last one, so nothing is missed. (#97)
- **The last client-export gaps are closed.** A section's stored "client" audience is no longer trusted (it is worked out each time); words hidden in stored fields that are not drawn, odd spellings of item IDs and unknown extra keys can no longer reach a filed client report; and a missing test is added. This closes the items listed as known in 2.5.2. (#259)
- **The Work page no longer crashes on partly saved columns.** If your saved column choices were missing one of the tabs (Actions, RAID, Decisions), the Work page could fail to open; it now fills in what is missing and keeps what you saved. (#256)
- **Delete note needs no approval card.** Pressing Delete note on the Notes tab is the approval: the note moves to the archive at once, is backed up and logged, and Undo brings it back. (#255)
- **The archive folder has one name, "99 Archive".** It replaces `_Archive` and the older `zz Archive`, so it sorts last in OneDrive beside `99 System`. creaite does not rename your existing archive folders: the old names keep working for one release, and you rename them yourself when you like. (#252)
- **The Review list no longer grows wider when you open a minutes row.** Expanding "n items" used to stretch the list and show a "more columns" button; long source lines now shorten, and the buttons stay in view. Intake rows get the same check. (#271)
- **Suggest no longer writes "I can't suggest" into a field.** When there is nothing to base a suggestion on, the field stays as it was and a short note says so. This covers the mitigation, decision and update suggestions. (#272)
- **Your reviews on the Usage tab.** Add your own dated notes (what you saw, what you decided), and download them as a CSV. (#238 follow-up)
- **Minutes are saved for the right project.** A meeting file in another project's folder is saved only for that project, and ask creaite says plainly that a chat cannot save a retrieved transcript: use Intake's Load into inbox. (#269)
- **Stricter limits on ask creaite, and quieter logs.** More ways of phrasing a forbidden path are stopped, and a failure that used to be logged without its cause now says why (an error kind and where; never any text). Nothing you see changes. (#174, #253)


Nothing is required. To use the new archive name on your existing archives, rename those folders to "99 Archive" yourself; until then the old names still work.


- The CI changes (#152, #89) are behind the scenes: no change for you.
- Approving minutes after rejecting every item (#261) is not in this release; it comes with the new Minutes view in 2.6.

## creaite 2.5.2

Client exports are now made from one checked copy of the report, so nothing can slip in between checking and exporting. Activity gets a Usage tab, and Intake becomes a quiet line on Today.


- **Client exports come from one checked copy.** When you approve a client report, creaite freezes the checked copy, and every client file (Word, HTML and PDF) is made from that one copy, then checked again after it is made. Nothing can slip in between checking and exporting.
  - A page posted with a client export is never used, and a client report is always treated as a client report, whatever its file says.
  - The header, the logos and the audience come from the project at the moment you export. Only the project's own logo files and the report's own pictures can be drawn, and any extra fields are dropped.
  - The older Word report route goes through the same check. Words hidden in look-alike letters or escapes are caught, and so are another project's words and owners.
  - The minutes export stops a client report, and a typed export name can't claim another report's filing name.
  - This closes the client-export items listed as "still to come" in 2.5.1.
- **A Usage tab on Activity.** It shows what each Claude run costs and what it loads before it starts, over time: summary cards, a 14-day chart (cost per day, and what each run loads at the start, in two aligned panels), a table by kind of run, what every run loads (the always-loaded files, measured once a day) and the skills used. It counts only: it never records what anything said.
- **Intake is a quiet line on Today.** The Intake and Review section on Today is replaced by one small line at the foot of Your commitments saying how many meetings are ready to process and how many suggestions wait. Its links go to Intake and Review, and a small x hides it until something new arrives. With nothing waiting there is no line. The quick Approve and Reject on Today's rows are gone: approve in Intake and Review.
- **Messages from people you follow** sit in their own Messages section on Today, above Week ahead, only when there are any: each is a card with Make a work item and Dismiss.

- **No Reporting card on the project page.** The Reporting card is gone from the project page; Reports (the icon beside Browse files), Project settings › Open reporting, the Reports page and Today's reminder still open the project's reporting.
- **Intake line dismiss is exact.** The small x on Today's Intake line now remembers which items you dismissed, so something new always brings it back.
- **Quieter debug log.** The check's log line now holds counts only.


Nothing.


- The Settings tabs, Project settings, the People page, the new Work list and Draft email in Outlook are in 2.6, not in this release.
- The Usage tab's "Your reviews" notes (your own dated notes, with a CSV download) are planned for the release after this one.

## creaite 2.5.1

A release of fixes: you can clear health items and dismiss the Check banner, the filter panel is no longer cut off, weekly report rows left out by mistake are fixed, and ask creaite no longer writes reports. Client exports are safer.


- **Clear health items.** In Settings › Health each problem has a Dismiss button (with an optional reason). A dismissed problem stops counting in the number in your menu; it comes back by itself if its detail changes, and "Dismissed" lists them with Restore. Problems that mean creaite itself is not safe to use cannot be dismissed.
- **Dismiss the Check banner.** A small close icon on the "not checked yet" banner on Today hides it for the day without running a check. It returns the next day, or when the last-checked time changes.
- **The Work filter panel is never cut off.** On a short list the filter panel used to be clipped near the bottom; it now stays fully visible.
- **Weekly report rows left out.** A work item that showed blank with "Click to write" and the left-out eye now keeps its text; a row you leave out and save says it is left out, and its eye refills it from your project record.
- **No cog on the Projects list.** The cog beside each project name in the Projects list is gone; project settings open from the project page (the cog beside Reports and Browse files) and from Settings.
- **Today.** The permanent "How Today works" box under an empty Needs attention is gone.
- **ask creaite no longer writes reports.** Reports are yours to edit in the Reporting hub; ask creaite can read them and answer questions about them, but cannot create or change a weekly or client report or its draft.
- **Safer client exports.** A client export is checked on exactly the report it was made from, a client report is always treated as a client report whatever its file says, weekly reports stay internal, the minutes export no longer accepts a client report, a page posted with a client export is used only when its words are the saved report's own, typed export names can no longer claim another report's filing name, and client logos come only from the project's own logo files.


- Some client-export hardening is still to come in the next release (a single checked snapshot that every client export reads from).
- The usage monitor and the Intake and Review pages are not in this release.

## creaite 2.5.0

Project settings get a page of their own, both reports can be edited side by side, and the report logos can be added by clicking their place in the header.


- **Project settings on one page.** A cog on the project page (beside Reports and Browse files) and in the Projects list opens it, and Settings › People and projects stays as a list that links in. It has General (name, client, status), People and partners, Milestones, Reporting, Logos and Archive. Each change saves on its own. Workstreams stay where they were.
- **Partners and their logos.** List a project's partner organisations once; each gets its own logo row, and every logo you tick prints in the header of that project's reports. Add or change a logo from this page, from the cog panel, or by clicking its place in the report header (an empty place shows a dashed "Add … logo" tile; nothing shows for a logo you have turned off, in Show as exported or in an export). The firm's logo is shared by every project, so it asks before it is replaced or removed. A "Logos not used" list lets you remove a logo left behind when a partner is renamed.
- **Both reports editable side by side.** In the reporting hub's Side by side view you can edit the internal and the client report at the same time. Each keeps its own edits, autosave and save line ("Saved · version 2 · Client: Saved · version 1"); ⌘S saves the pane you are in; the menus, pickers and shortcuts belong to that pane; the panes share one zoom and scroll together. Nothing from the internal report reaches the client report except through "Match internal" or "Add to the client report". An approved internal report no longer locks the client page.
- **Match internal checks first.** Before it copies internal text into the client report, it checks the wording the way export does: a section with internal wording is held back and named, and the rest is copied. Internal-only text sections are never copied by "every section".
- **ask creaite shows when it has finished.** With the panel closed, a small mark appears on the ask creaite button when a run ends (a tick for done, a different mark for stopped or failed). It goes after 30 seconds, or when you open the panel.
- **A tidier report hub.** The label row (name, status, Match internal, Refresh, Edit again) sits inside each grey pane and scrolls with it, and the weeks in the week menu show their real health colours.
- **A roomier Add actions picker.** The picker in the report no longer feels cramped.
- **Safer settings and exports.** Settings that change a project's memory file stop a file that changed in another window, keep the rest of a line, and never show full file paths in messages. Client exports drop more kinds of hidden content (unclosed styles, damaged pictures, GIF and WebP pictures).


- With a project's client report switched off, creaite now stops to create, save, export or approve a client report for it; existing client reports can still be opened.
- Partner names are 1 to 60 characters (letters, digits, spaces and . , & ' - ( )); other names on the Partners line are ignored.
- Intake and Review are still two separate pages in this release.
- In Side by side, only one click-to-edit summary box is open at a time (clicking into the other pane closes it), and the section menu is one popup.

## creaite 2.4.1

A security fix for client exports; nothing else changes.


- **Client exports can no longer carry hidden words, or load outside pictures, through stylesheet tricks.** If you exported a client report from 2.4.0 and a hidden item mattered, export it again.

## creaite 2.4.0

Weekly reporting is rebuilt as one place for the internal and the client report, what you export now looks like what you see and is saved where you can find it, and you can add logos and your own text sections.


- **One reporting hub for each project.** Internal, Client or Side by side, with the week chosen from a list (with each week's health and status). A Reports icon beside Browse files at the bottom of the project page opens it, and the Reports page, the project card, the search palette and the Today reminders all land in it. The two old report buttons at the foot of the project page are gone.
- **Side by side shows both reports, for now with the internal report read-only.** You can edit the client report there; editing both at once follows in the next release.
- **A client report only where you need one.** A cog beside Export turns the client report on or off for a project. The setting holds for every future report until you change it, deletes nothing, and is the same setting in Settings › Projects. A new project starts with the client report off. With it off you see only the internal report, there is no client reminder, and the Client and Side by side switches are not shown.
- **The same editing in both reports.** One report sheet is used for both, so every improvement reaches both. The client report keeps what is special to it: client-visible items only, "Not in this report", and "Matching internal / Edited for the client" with a Match internal button for each section.
- **One title block and your logos.** The repeated page title is gone: the header reads "Weekly report · Internal" or "Client report · Client", with the project and the week. Add or change the firm's, the client's or a partner's logo in the cog panel. Logos sit straight on the page, keep their transparency, and print in every export. JPEGs work, but a transparent PNG or SVG looks better.
- **A tidier report page.** The section menu is small, with an icon for each item, and always fully on screen. The health indicator is narrower, with its six-week strip and the Change button inside it. The include or leave-out switch is an eye everywhere (a crossed-out eye when left out).
- **Add from your project record.** Under Risks and issues, Overdue actions and Decisions, you can pick open items that are already in your project record and add them to the report, including actions not yet due. The client report offers only client-visible items. Nothing in your project record changes until you approve.
- **A free-text section, anywhere.** Add a section of your own at the foot or from any section's menu, with its own heading and the same editor as Notes (headings, lists, checklists, code, tables, pictures, links). Move it, leave it out of the export or delete it. A text section is internal until you write or match it in the client report.
- **Exports look like the report.** HTML and PDF are made from the report's own "Show as exported" page, so the header and logos, the health block with its six weeks, the figures, the milestone timeline as a picture with its table, the full tables and your text all come out as you see them, with dates as DD-MM-YYYY. If that is not possible you get a plain version and are told so. Word is rebuilt the same way: one title, one health label, the strip and timeline as pictures, full tables, no empty headings.
- **Exports are saved, and you are told where.** Every export is saved in the project's Reports folder first; the message names the folder (a link that opens it) with Show in Finder and Open. If a file with that name is already there, you choose whether to add a number, rename it or overwrite it. Before a report is filed, the first HTML export is offered a numbered name so it never gets in the way of "Approve and file". The Advanced setting "File report exports beside it" is gone, because reports always save into the Reports folder (the one for minutes stays).
- **A scrolling header and an icon toolbar.** Scroll the report down and the search bar and title block go; they return at the top. The controls are one line of icons (zoom, Show as exported, Export, Approve, and the cog last), and pinching on the trackpad zooms the report. Export asks Internal, Client or Both only when the client report is on.
- **Review: each row's detail is now one line;** the owner, priority and due date show on hover and in the peek. The owner's name on the row is no longer a link.
- **Activity: the Kind button is gone;** filter by kind from the filter bar.


- In Word, a link shows as the words plus the address (not clickable), a table, code block or picture inside a list item or quote shows as plain text, and Decisions is a table rather than the report's quoted lines.
- The pictures in Word are drawn from the same data as the report, not screenshots, so they are close but not identical.
- A milestone you leave out of the milestone list still appears in the timeline picture, as on screen.
- "Check this report" is not in this release.

## creaite 2.3.4

A small fix-up for two places where something was hard to read: a pinned note's title in Notes, and the project names on the People page.


- **A pinned note shows its title.** In a project's Notes list, a pinned note's card used to show a blank where the title should be, even though the note opened fine. The card now shows the title, a long title ends in "…", and it works for a confidential pinned note too.
- **Project names on the People page read as links.** They are now in the link colour, at the table's normal text size and a little bolder, instead of small faint text. Clicking one still opens the project.

## creaite 2.3.3

A small clean-up of two buttons that were easy to get wrong, in Review and in Intake.


- **Review: approving a meeting's routine items is no longer a lookalike.** The button is now plain, not green, and reads "Approve 3 routine" (the number of routine items under those minutes). Only a row's own Approve stays green. Hover it and it tells you that minutes, new decisions and new risks still need approving one by one.
- **Intake: "Process selected" says why it is switched off.** With nothing ticked, hover it and it says "Tick a file first" (or "Tick a meeting first"); tick one and it switches on.

## creaite 2.3.2

A small fix-up to 2.3.1 for three annoyances on Today and the side bar.


- **A hover card no longer sticks.** Choose Prep from a meeting's hover card, then go back to Today: the card is gone, and you don't need to refresh.
- **The Evidence column on Today's Portfolio table follows when you resize it.** The text wraps to the new width, and the width is kept.
- **The More menu no longer repeats "Labels when collapsed".** It stays in Customise sidebar.

## creaite 2.3.1

A small fix-up to 2.3.0, mostly for Draft email: a chase email to someone outside your team no longer shows things it shouldn't, and the "I sent it" step understands more of the ways you might type or paste your list.


- **A chase email to an outside recipient stays clean.** It no longer prints who else was chased or which reminder it is. The same internal lines are also kept out of the steering and sponsor views.
- **"I sent it" reads your list more forgivingly.** Lines in lower case, with bullets, or with odd spaces are now recognised.
- **A person with no items can now get "Add details".**
- **A few words in Help now say "Draft email"** where they used to say "Chase".

## creaite 2.3.0

The screens you use every day become calmer and more consistent: one set of sizes everywhere, a top bar that gets out of the way, a quieter Today, a clearer Files page, and a choice of icon size in the side bar.


- **The top bar hides when you scroll down, on every page,** and comes back when you return to the top of the page.
- **Choose how big the side bar icons are.** Small, Medium or Large, in the existing Customise sidebar dialog. Small is what you have today.
- **Files, easier to find your way around.** A Filter button sits beside four view pills, and the date filter opens as a popup calendar.
- **A calmer Today.** What is waiting in Intake and Review is one quiet line, not a list.
- **A reminder when the check is late.** A "Mail and Teams not checked yet today" banner on Today, with a Check now button.
- **Right-click a note in the Notes list** to get that note's menu without opening it.
- **"Choose a project"** appears on Cockpit and Milestones, instead of a blank page, when no project is chosen.
- **Draft email is clearer.** Both Review items read "Draft email". "I sent it" updates every item you sent and keeps the email internal. Right-click a person's name to draft an email to them.
- **Activity is tidier.** Entries say "You, by hand" when you made the change yourself, rows are evenly spaced, and every row has a tick box.
- **People lines up.** One kind of zero, and the counts are right-aligned.
- **One design scale across the app.** Fields are 32 px high, chips are 26 px pills, and headings are 22 px and 16 px, so the same thing looks the same on every page.

## creaite 2.2.0

Notes become a place you can write in freely, creaite's AI reaches the text you select and the health you set, Help is rewritten short and searchable, and the screens you use all day get calmer.


- **Help is shorter and you can find things in it.** One search over all of Help, a home of the twelve jobs, a ? key that opens help for the screen you are on, a one-line pointer the first time you visit each screen, a What's new tab with the notes for every release, and a one-page first-day card.
- **AI on the text you select.** A small sparkle in the margin, and a bar that appears when you hover, with Turn into and Format as well as the AI actions. It works in Notes and in Current state.
- **Notes save by themselves** about two seconds after you stop typing. There is no draft step, and Undo and the Activity list stay tidy.
- **Notes focus mode.** A quiet writing view, with the same note and cursor, and clear rules for how it closes.
- **Links in every editor.** Add, change and remove a link anywhere you write text, and see links wherever text is shown.
- **One editor everywhere.** The plain version and Draft email, report pages and the capture drawer join the same editor and toolbar; Current state gets a checklist and a focus mode.
- **Generate current state, further.** Steer a draft again and again, keep versions and refine.
- **Health with a ✦.** The sparkle beside a project's health, on its page and on the weekly report's health row, suggests the health and its reason from your project record's facts, with the evidence shown. It is a draft; nothing changes until you accept it.
- **The weekly report gets out of your way.** Scroll down and the search bar and title block go at once, leaving one slim bar with zoom, Export and Approve and file; they return only at the top of the report. The report has nearly the whole window.
- **Meeting Prep on one page.** A single prep page, a peek when you hover on a meeting, and the agenda as a document you can edit.
- **A calmer Today.** Saturday and Sunday hide unless something is planned, past days fold into one small icon, the Note link and Prepare pill are gone, a meeting's title opens its Prepare popup, and dates are smaller. Your commitments shows five items, then "Show more". The section that was called "To decide" is now Intake and Review, and folds like the others.
- **Review shows age that means something,** in quiet text, and marks only the one that is different.
- **Friday's Close the day card shows the weekend.** Anything planned for Saturday and Sunday appears under the next working day.
- **A left side bar you can read.** Visible labels, a clear current page, grouped pages, a narrower and tighter bar, the wordmark as its toggle, and hover flyouts on Projects and Work.
- **One hover standard.** Every tooltip, card and menu that opens on hover waits the same time.
- **Health bars on Portfolio** have a legend and a tooltip showing the week and its reason.
- **Work board.** You can resize the board's width, and the choice is remembered.
- **ask creaite is steadier.** Esc closes the panel but never stops a running request (only Stop does), and a long old reply no longer rewrites itself on screen when you reopen it. One Esc now closes an item's peek (it took two).
- **Calendar import and the check are tidier.** The check reads only today and the future for meetings, finished meetings no longer say "Not happened yet", and a window left open past midnight keeps today's date.
- **creaite keeps a counts-only record of what each AI run costs,** so decisions about cost rest on numbers. It stores no text from your mail, notes or chats.

## creaite 2.1.0

Reports, minutes and notes now live inside creaite, and the editor, Today and a handful of annoyances got better.

- **The weekly report, in creaite.** A proper A4 page you edit in place, with twelve sections you can move, hide and rename. You export it to HTML, Word or PDF. Nothing is ever sent.
- **The client report.** The same week as the client sees it: only client-visible items, in the client's words, never anything marked Sensitive. A check before every export lists what is left out, and why.
- **Meeting minutes, in creaite.** A processed transcript becomes draft minutes on a page, with the transcript beside them and a time tag on every line. Type a deadline in words ("next Friday") and it works out the date. Approving is one step, with Undo.
- **A Reports page and a reporting space on each project,** with a card on the project page and a Friday reminder.
- **The meeting page is gone.** Its jobs moved to the meeting's Prep, its minutes and Review. Old meeting links still land somewhere sensible.
- **Notes.** A tidier header, a "+ New note" button, dates you can type in words, Delete note (restorable from Files › Archived), checklist boxes that line up, a "/" menu that opens where you typed, and three heading levels.
- **Today, Review and the small things.** Today keeps its content at 80% width; Week ahead can be hidden; Generate current state is wider; Review's multi-select bar follows you as you scroll; ⌘↵ saves any dialog.
- **Safer.** Anything creaite reads from outside, such as mail or a document, can no longer make it write files, and tools that need no tools start in a neutral folder instead of reading your own notes as background.

## creaite 2.0.2

A security patch. Nothing for you to do.

- **A hidden second command can no longer slip past the safety check** that decides which commands ask creaite and the background runs may use.

## creaite 2.0.1

A security patch that narrows what creaite's background runs can do, so a message or document they read cannot make them run commands or change files.

- **The check for messages from people you follow can only read Microsoft 365.** It has no file, command or web tools.
- **Search answers read your creaite folder's text only.** They cannot reach Microsoft 365 or change anything.
- **Drafting runs cannot edit or write files.** That covers Prep pages, Current state, the AI drafts, Shape this meeting and the transcript checks.

## creaite 2.0.0

Notes arrive, with one editor everywhere, and AI on text you select.

- **One editor.** Current state, an item's text fields and Prep's notes and questions share one editor, with Undo and the same keys.
- **Notes on every project.** Each project has Overview and Notes tabs, and the portfolio has notes of its own.
- **A note from any page.** Press ⌘⇧N, or N when you aren't typing, to jot a note without leaving what you're doing.
- **Find updates in a note.** ✦ Find updates reads a note's new lines and proposes your project record changes they state, for you to approve.
- **Pictures in notes,** and changing a note's title renames its file and keeps the links to it in your other notes working.
- **AI on selected text.** Select words in Current state, an item's title or longer fields, or Prep's notes, and press AI: rewrite clearly, shorter, longer, make it executive, fix spelling, or say what you want. It is a suggestion; nothing changes until you press Accept, and ⌘Z undoes it.

## creaite 1.9.5

One look, and less to wade through.

- **One design scale.** Every screen draws its buttons, fields, headings and spacing from the same set, and the worst findings from a full screen-by-screen check were fixed: faint text, missing borders and screen-reader labels.
- **No screen scrolls past its own bottom.** On Today, Intake and the Prep popup the window could scroll into empty space; it no longer does.
- **Menus, pickers and dialogs behave the same everywhere.** They take the same keys (arrows, Enter, Esc, Tab), hand focus back to what opened them, and offer Undo after a change.
- **One card per conversation.** Messages from people you follow arrive as one card per chat or thread, saying what it came to.
- **Items closed long ago archive themselves.** Closed actions and risks, and done or dropped promises, are archived once a day after the backup.
- **Old reports and minutes move into _Archive on your yes.** Settings › Health offers it once a month, and Files › Archived lets you move one back.

## creaite 1.9.4

Archive, and no waiting.

- **Archive a whole project.** A finished project, with its folder, its register row and its items, can be archived and brought back exactly. Settings › People and projects lists each project with Archive.
- **Changes appear at once.** An edit in Work, on the board, from the right-click menu, the bulk bar, the peek or ⌘K shows on screen immediately and saves in the background.
- **Saves and the first page no longer wait** for the search index or the OneDrive copy.
- **ask creaite shows what creaite started.** A Prep page or a Generate run appears in ask creaite as one plain request, its steps and its outcome.
- **Smaller fixes.** A check's lock no longer outlives the check, opening creaite twice quickly starts one server not two, and a remembered chat that has gone is handled cleanly.

## creaite 1.9.3

Sneak peek and safe backups.

- **Change an item in words.** With an action, risk, decision or milestone open, type // and say what should change ("Sara owns this, due Friday"). You see the change as you type; Enter makes it, Undo takes it back.
- **A daily backup you can restore from.** One closed daily zip of everything needed to rebuild your creaite folder goes to your OneDrive backup folder. Old copies are tidied on an agreed schedule, and a weekly check proves a restore would work.
- **Restore from a backup.** Settings › Health lists the backups by date and restores from the one you choose.
- **Search reads PDFs.** PDFs exported from Word or PowerPoint are now searched by their text, not only their name.
- **Worth knowing:** a copy of your backup now leaves the laptop, into your company OneDrive folder only. Old backups are now removed automatically.

## creaite 1.9.2

Calmer.

- **Settings opens on sixteen things you actually set,** in plain words. Everything else is under Advanced, searchable. A dot marks anything you've changed, and Reset puts it back.
- **Health lives inside Settings.** It lists only what needs you, each with what to do, and five problems mend themselves with Fix it.
- **Rejecting asks for a reason.** One menu of seven reasons, with creaite's own guess, works from Review and from Today.
- **Today becomes one home,** with To decide first: what waits in Review, transcripts ready in Intake and messages from people you follow.
- **A sidebar that collapses to icons,** with Today, Work, Review, Projects and People at the top and the rarer pages under More.
- **Updates finish themselves.** From the next update, creaite remakes the launcher, refreshes the app's icon and restarts creaite for you.

## creaite 1.9.1

A small update for ask creaite and Today.

- **ask creaite checks what it says.** Every work item it names is checked against your project record before you see the reply.
- **A plain "I can't".** When something is outside what it can ever do, such as sending mail, it says so first.
- **Field changes use the dashboard's own save.** Changing an owner, due date or status shows a card with the change, the same rules and Undo.
- **Today's day arrows stay put.** The ‹ › controls sit in the same place on every day.

## creaite 1.9.0

Meeting prep, reimagined.

- **A better Prep popup.** Wider, with a tidy header, a facts line and Draft agenda as one menu. Every item opens the full peek.
- **Shape this meeting.** Say the focus and the aim in your own words and the prep follows.
- **The prep page opens inside creaite,** in a Briefing layout, with dated reporting, the meeting's series and every source a link. Prep works for any day the calendar holds.
- **Today moves between days.** Go back to follow up on Monday's meetings, or forward to prepare for next week's.
- **Close the day is a guided shutdown** that catches up on mail and Teams first and gives every loose end a place.
- **You owe, and Waiting on.** What you have promised, and what others have promised you, show on Today.
- **Followed people are private to you.** Nothing on screen or in anything creaite writes says who you follow closely.
- **Smarter updates.** A message that moves an open item forward now updates it instead of raising a new one. Draft chase works from any item.
- **Settings › People has filters,** and search reads emails saved in a project folder.

## creaite 1.8.0

The first full release, out of Beta.

- **Nothing to relearn.** The dashboard was rebuilt underneath, but every screen, key and button is where it was.
- **On-track milestones are always green,** in every theme, and read "On track" for clients too.
- **Top risks and issues show at most five lines each.**
- **Every AI drafts switch is honoured.** A switch you turned off greys its control and says why.
- **"update creaite" finds the newest release again.**
- **Fifteen smaller fixes** from hand checks and live diagnostics, including undo after approving a change, screen-reader names for Settings switches and the wordmark in high contrast.

## creaite 1.7.0

creaite's drafts reach your meetings and your Review.

- **Draft the agenda and the invite text,** and follow-up and chase emails, from a meeting or an item.
- **Decisions needed.** A band on Today lists each pending decision that has a decision maker and a needed-by date.
- **One set of facts, many forms.** Generate can write the project's status as a Current state, a steering note, a three-line update, an email paragraph or a Teams message, each sentence with its sources.
- **Looks like an item you already have.** When the minutes or the check propose something you already track, Review says so.
- **Probably done.** When a mail or meeting shows an open item is finished, creaite proposes closing it.
- **Sharpen on capture.** As you type a new action, chips suggest the owner, due date and wording.
- **Activity › Quality** shows what you approve as suggested, approve after an edit and reject, by source.
- **ask creaite reopens at once,** queues what you send while it works, and saves a change from one card.
- **Changes show within a second** on an open dashboard, and a new wordmark sits at the top of the rail.
- **Two security fixes.** ask creaite now asks before it changes the record, and Word files written from the command line go to drafts only.

## creaite 1.6.1

The largest update so far. creaite drafts the wording and you decide.

- **Drafts that show their sources.** A Draft or Suggest button sits beside slow-to-write fields. A Current state drafted by creaite arrives with every sentence underlined; click one to see the facts behind it.
- **A page for each meeting,** from invite to follow-up, with a strip showing where it is. The minutes record whether each agenda point was covered, touched on or not discussed.
- **Close the day.** A one-minute card: what moved today, what you promised, what is still waiting, and the next working day.
- **⌘K makes changes.** Type "move ABC-A-002 to fri" or "Omar owns the SOW action" and it does it.
- **Right-click a work item** for a menu of the common actions, wherever the item appears.
- **Review one at a time,** with the source beside each suggestion, and a way to move a suggestion, or a whole set of minutes, to another project.
- **creaite can start when you log in,** and "update creaite" can fetch the release itself.
- **Smaller things.** Undo waits for you, the open item follows your click, and ask creaite sends exactly what you typed.

## creaite 1.5.2

A one-line fix.

- **ask creaite no longer trips its safety check just by looking inside a file.**

## creaite 1.5.1

Themes, and a clearer approval card.

- **Four new themes,** bringing the total to nine: a warm cream one, a pale grey one, a 1980s arcade one and a thermal-camera one.
- **Customise the left rail with a right-click.** Settings is now a gear.
- **ask creaite's approval card shows how risky each change is,** yellow for settings and red for permission rules, with the way back.

## creaite 1.5.0

Milestones get a page of their own.

- **Plan and Movement.** The pencil on a project's Milestones card opens a page with the plan and the history of every move.
- **Five clear states:** Achieved, On track, At risk, Slipped and Overdue, each with its own shape.
- **Internal view and Client view.** A switch shows what the client sees: only the milestones you have made visible to them, in their words.
- **A likely date range,** once there is enough history, based on how your own milestones have slipped.
- **Client reports list only client-visible milestones.** Mark the ones a client should see.
- **Smaller things.** A page left open across a restart tells you to reload, and one Esc leaves a table cell.

## creaite 1.4.0

Items open for editing, and every count is a link.

- **Open an item and just change it.** An action, risk or decision opens over the page, already editable. Each change is saved with Undo; ⌘↵ saves and closes. New items open the same way.
- **Every count opens its list.** A number of actions, risks or decisions anywhere opens Work showing exactly those.
- **ask creaite opens over the page** instead of squeezing it.
- **Rename a project's Current state card,** arrange the left rail, and search Activity and undo several older changes.
- **A weekend date is pointed out,** and errors show as a banner you can dismiss.

## creaite 1.3.0

Work is far quicker, Review triages in bulk, and ask creaite can administer.

- **Work, faster.** Click to select, edit a value in the table, change several items at once, group the list or use swimlanes on the board, better filters and saved views you can keep up to date, and an All items tab.
- **Review as a triage queue.** Select several, approve or change them together, give a reason when you reject, and possible duplicates are flagged.
- **ask creaite as the administrator.** It reads and writes widely, but every sensitive change waits on one card you approve.
- **Settings is one page** with categories and search.
- **The meeting prep page shows only what needs attention.**
- **A little motion,** with a Motion setting that follows your Mac's Reduce motion.
- **Fixes.** An item number is never used twice in a project, an item ID in Activity opens the item, and two edits made in the same second no longer overwrite each other.

## creaite 1.2.0

Transcripts load themselves, Work has a board.

- **Transcripts, from the calendar.** Intake shows which meetings have a transcript and brings the transcript and the meeting chat in for you.
- **A Work board.** A List | Board switch for Actions and RAID, with cards in columns you can drag.
- **Projects are called by their name** everywhere, with the short code only inside item IDs like ABC-A-003.
- **Clear day** sets a day's meetings aside, with Undo and a list you can restore from.
- **ask creaite can read all of Microsoft 365** (calendar, mail, Teams, SharePoint, OneDrive), while writing is still confirmed and sending or changing anything there stays off.
- **Followed people, an ignore list and Prep pages.** Alerts come first in Today and Review, the check skips what you tell it to, and a Prep page for a meeting is saved in the project's Agendas folder.

## creaite 1.1.0

Project files can live in your company OneDrive.

- **Project folders in OneDrive (optional).** creaite reads from them and files into them; the engine and the record stay on your laptop.
- **Today as a brief:** short numbered sentences for what needs attention, your commitments, what resolved, the week ahead and the portfolio.
- **Draft email.** On a person's page, a ready-to-copy message asking where their items stand. creaite never sends mail.
- **Roomier editing.** The side panel is wider while you edit, and ⌘+Enter saves and closes it.
- **Inbox is now Intake,** Help has three tabs, and there is a new teal theme.
- **One-off Word documents** from your project record, such as an actions register or a decision log.

## creaite 1.0.0

The first release for real use (Beta).

- **Meetings to minutes.** A Teams transcript becomes draft Word minutes and suggested actions, decisions, risks and issues. Nothing is filed until you approve.
- **A daily check** of Outlook and Teams proposes items from your mail and chats.
- **Review and save.** Suggestions are grouped by project, bulk approval covers routine items only, and every save can be undone.
- **A dashboard:** Today, project pages, Work, People, Intake, Review, Files and Activity, with search that cites its sources and ask creaite, the assistant.
- **Weekly and client-safe reports in Word,** and an Excel export you can browse and edit.
- **Safe by design.** One writer for the record, approval before every write, a daily backup and updates that roll back if a step fails. Everything stays on your laptop.
