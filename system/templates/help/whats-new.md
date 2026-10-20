# What's new

What changed for you in each release of creaite, newest first. Written in plain words; the technical notes are separate.

## creaite 2.5.2

Client exports are now made from one checked copy of the report, so nothing can slip in between checking and exporting. Activity gets a Usage tab, and Intake becomes a quiet line on Today.


- **Client exports come from one checked copy.** When you approve a client report, creaite freezes the checked copy, and every client file (Word, HTML and PDF) is made from that one copy, then checked again after it is made. Nothing can slip in between checking and exporting.
  - A page posted with a client export is never used, and a client report is always treated as a client report, whatever its file says.
  - The header, the logos and the audience come from the project at the moment you export. Only the project's own logo files and the report's own pictures can be drawn, and any extra fields are dropped.
  - The older Word report route goes through the same check. Words hidden in look-alike letters or escapes are caught, and so are another project's words and owners.
  - The minutes export refuses a client report, and a typed export name can't claim another report's filing name.
  - This closes the client-export items listed as "still to come" in 2.5.1.
- **A Usage tab on Activity.** It shows what each Claude run costs and what it loads before it starts, over time: summary cards, a 14-day chart (cost per day, and what each run loads at the start, in two aligned panels), a table by kind of run, what every run loads (the always-loaded files, measured once a day) and the skills used. It counts only: it never records what anything said.
- **Intake is a quiet line on Today.** The Intake and Review section on Today is replaced by one small line at the foot of Your commitments saying how many meetings are ready to process and how many proposals wait. Its links go to Intake and Review, and a small x hides it until something new arrives. With nothing waiting there is no line. The quick Approve and Reject on Today's rows are gone: approve in Intake and Review.
- **Messages from people you follow** sit in their own Messages section on Today, above Week ahead, only when there are any: each is a card with Make a work item and Dismiss.

- **No Reporting card on the project page.** The Reporting card is gone from the project page; Reports (the icon beside Browse files), Project settings › Open reporting, the Reports page and Today's reminder still open the project's reporting.
- **Intake line dismiss is exact.** The small x on Today's Intake line now remembers which items you dismissed, so something new always brings it back.
- **Quieter debug log.** The sweep's log line now holds counts only.


Nothing.


- The Settings tabs, Project settings, the People page, the new Work list and Draft email in Outlook are in 2.6, not in this release.
- The Usage tab's "Your reviews" notes (your own dated notes, with a CSV download) are planned for the release after this one.

## creaite 2.5.1

A release of fixes: you can clear health items and dismiss the Sweep banner, the filter panel is no longer cut off, weekly report rows left out by mistake are fixed, and ask creaite no longer writes reports. Client exports are safer.


- **Clear health items.** In Settings › Health each problem has a Dismiss button (with an optional reason). A dismissed problem stops counting in the number in your menu; it comes back by itself if its detail changes, and "Dismissed" lists them with Restore. Problems that mean creaite itself is not safe to use cannot be dismissed.
- **Dismiss the Sweep banner.** A small close icon on the "Sweep due" banner on Today hides it for the day without running a sweep. It returns the next day, or when the last-swept time changes.
- **The Work filter panel is never cut off.** On a short list the filter panel used to be clipped near the bottom; it now stays fully visible.
- **Weekly report rows left out.** A work item that showed blank with "Click to write" and the left-out eye now keeps its text; a row you leave out and save says it is left out, and its eye refills it from the tracker.
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
- **Safer settings and exports.** Settings that change a project's memory file refuse a file that changed in another window, keep the rest of a line, and never show full file paths in messages. Client exports drop more kinds of hidden content (unclosed styles, damaged pictures, GIF and WebP pictures).


- With a project's client report switched off, creaite now refuses to create, save, export or approve a client report for it; existing client reports can still be opened.
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
- **Add from the tracker.** Under Risks and issues, Overdue actions and Decisions, you can pick open items that are already in the tracker and add them to the report, including actions not yet due. The client report offers only client-visible items. Nothing in the tracker changes until you approve.
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
- **A reminder when the sweep is late.** A "Sweep due since 07:00" banner on Today, with a Run sweep button.
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
- **Health with a ✦.** The sparkle beside a project's health, on its page and on the weekly report's health row, suggests the health and its reason from the tracker's facts, with the evidence shown. It is a draft; nothing changes until you accept it.
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
- **Calendar import and the sweep are tidier.** The sweep reads only today and the future for meetings, finished meetings no longer say "Not happened yet", and a window left open past midnight keeps today's date.
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
- **Search answers read your vault's text only.** They cannot reach Microsoft 365 or change anything.
- **Drafting runs cannot edit or write files.** That covers Prep pages, Current state, the AI drafts, Shape this meeting and the transcript checks.

## creaite 2.0.0

Notes arrive, with one editor everywhere, and AI on text you select.

- **One editor.** Current state, an item's text fields and Prep's notes and questions share one editor, with Undo and the same keys.
- **Notes on every project.** Each project has Overview and Notes tabs, and the portfolio has notes of its own.
- **A note from any page.** Press ⌘⇧N, or N when you aren't typing, to jot a note without leaving what you're doing.
- **Find updates in a note.** ✦ Find updates reads a note's new lines and proposes the tracker changes they state, for you to approve.
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
- **Smaller fixes.** A sweep's lock no longer outlives the sweep, opening creaite twice quickly starts one server not two, and a remembered chat that has gone is handled cleanly.

## creaite 1.9.3

Sneak peek and safe backups.

- **Change an item in words.** With an action, risk, decision or milestone open, type // and say what should change ("Sara owns this, due Friday"). You see the change as you type; Enter makes it, Undo takes it back.
- **A daily backup you can restore from.** One closed daily zip of everything needed to rebuild the vault goes to your OneDrive backup folder. Old copies are tidied on an agreed schedule, and a weekly check proves a restore would work.
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
- **Updates finish themselves.** From the next update, creaite remakes the launcher, refreshes the app's icon and restarts the live server for you.

## creaite 1.9.1

A small update for ask creaite and Today.

- **ask creaite checks what it says.** Every work item it names is checked against the tracker before you see the reply.
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
- **Looks like an item you already have.** When the minutes or the sweep propose something you already track, Review says so.
- **Probably done.** When a mail or meeting shows an open item is finished, creaite proposes closing it.
- **Sharpen on capture.** As you type a new action, chips suggest the owner, due date and wording.
- **Activity › Quality** shows what you approve as proposed, approve after an edit and reject, by source.
- **ask creaite reopens at once,** queues what you send while it works, and applies a change from one card.
- **Changes show within a second** on an open dashboard, and a new wordmark sits at the top of the rail.
- **Two security fixes.** ask creaite now asks before it changes the record, and Word files written from the command line go to drafts only.

## creaite 1.6.1

The largest update so far. creaite drafts the wording and you decide.

- **Drafts that show their sources.** A Draft or Suggest button sits beside slow-to-write fields. A Current state drafted by creaite arrives with every sentence underlined; click one to see the facts behind it.
- **A page for each meeting,** from invite to follow-up, with a strip showing where it is. The minutes record whether each agenda point was covered, touched on or not discussed.
- **Close the day.** A one-minute card: what moved today, what you promised, what is still waiting, and the next working day.
- **⌘K makes changes.** Type "move ABC-A-002 to fri" or "Omar owns the SOW action" and it does it.
- **Right-click a work item** for a menu of the common actions, wherever the item appears.
- **Review one at a time,** with the source beside each proposal, and a way to move a proposal, or a whole set of minutes, to another project.
- **The live server can start when you log in,** and "update creaite" can fetch the release itself.
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

- **Open an item and just change it.** An action, risk or decision opens over the page, already editable. Each change is staged with Undo; ⌘↵ applies and closes. New items open the same way.
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
- **Followed people, an ignore list and Prep pages.** Alerts come first in Today and Review, the sweep skips what you tell it to, and a Prep page for a meeting is saved in the project's Agendas folder.

## creaite 1.1.0

Project files can live in your company OneDrive.

- **Project folders in OneDrive (optional).** creaite reads from them and files into them; the engine and the record stay on your laptop.
- **Today as a brief:** short numbered sentences for what needs attention, your commitments, what resolved, the week ahead and the portfolio.
- **Draft email.** On a person's page, a ready-to-copy message asking where their items stand. creaite never sends mail.
- **Roomier editing.** The side panel is wider while you edit, and ⌘+Enter saves and closes it.
- **Inbox is now Intake,** Help has three tabs, and there is a new teal theme.
- **One-off Word documents** from the tracker, such as an actions register or a decision log.

## creaite 1.0.0

The first release for real use (Beta).

- **Meetings to minutes.** A Teams transcript becomes draft Word minutes and proposed actions, decisions, risks and issues. Nothing is filed until you approve.
- **A daily sweep** of Outlook and Teams proposes items from your mail and chats.
- **Review and apply.** Proposals are grouped by project, bulk approval covers routine items only, and every apply can be undone.
- **A dashboard:** Today, project pages, Work, People, Intake, Review, Files and Activity, with search that cites its sources and ask creaite, the assistant.
- **Weekly and client-safe reports in Word,** and an Excel export you can browse and edit.
- **Safe by design.** One writer for the record, approval before every write, a daily backup and updates that roll back if a step fails. Everything stays on your laptop.
