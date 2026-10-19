# Brief: Intake and Review, one page (release 2.5)

**Update 19-10-2026: the build spec is now `dev/mockups/intake-review-combined-v2-mockup-2026-10-19.html`, approved and locked by Alan (#232, 2.6).** It adds to this brief: the page and rail are called **Intake** (inbox icon); **Add files** (icon button, full-page drop, file rows told apart as transcript or minutes); **Refresh the calendar** with the time it was last read; an update proposal in the peek shows the whole work item with the changed fields highlighted; each stage box has an icon and Show all is a box; the instructional banner is gone. See the sections at the foot of this file.

Size (Stark's scout, #232): about 14 Sonnet-agent days, about 7 elapsed with two agents; it replaces `intake.js`, `meetings.js`, `review.js` and `components/review/*`; no guarded file is strictly needed (the Not needed reason is stored by `build_dashboard.clear_meetings` in `intake-cleared.json`, so a reason field needs no guarded change for a first cut).

Product Manager, 18-10-2026, for Team Stark. Mockup (approved and locked by Alan, 18-10-2026; the current copy with corrected wording is `dev/mockups/intake-review-combined-v2-mockup-2026-10-18b.html`, approved by Alan on 18-10-2026 and locked: this is the mockup for 2.5): `dev/mockups/intake-review-combined-v2-mockup.html` (built on the real Review snapshot with the app's own classes; open it and click through: the List | Board | Two panes switch, a meeting row, a mail or Teams row, the peek). Background and decisions: `dev/sprints/intake-review-2026-10-17.md`; earlier step 1 brief `intake-step1-brief.md` (#179) and step 2 (#180) are folded into this item. Nothing here is built. The mockup uses sample data only.

## What the user sees

1. **One page, one side-bar entry, one badge: "Intake and Review".** It replaces the separate Intake and Review pages. The badge counts what needs the user: meetings ready to process plus proposals to approve. Old addresses open the new page.
2. **One pipeline with three stages.** **Arrived** = a meeting or an uploaded file creaite has seen but not turned into proposals (transcript ready, waiting for the transcript, or being drafted). **Drafted** = processed, proposals waiting for the user. **Approved** = every proposal decided this week. Mail and Teams proposals are not a stage; they sit in their own group, "From mail and Teams", below.
3. **Three views, chosen by each user:** **List** (default: the stages as clickable counts, one list below), **Board** (three columns, a card per meeting; Process moves a card across) and **Two panes** (meetings on the left, the selected one on the right). A List | Board | Two panes switch in the toolbar; the choice is remembered per person (browser, never shared).
4. **A meeting row** has: its name, when, project, state (Transcript ready, Waiting for the transcript, Drafting in the background, N proposals to check, Done), age (a "Stale" marker for old ones, as Review does), and actions: **Process** (a plain row button), **Later** and **Not needed** (an ✕ with a reason). Process runs in the background with progress on the row; ask creaite stays free.
5. **A meeting with proposals opens in place.** A single click anywhere on its row opens it and a second click closes it (Check them and Close do the same). Opened, its row is tinted and everything that comes from it hangs under it on a coloured rail, so it is plain which items belong to which meeting.
6. **Routine and not routine are split into two labelled groups** under the meeting's name. **Needs your decision** comes first: everything the app already approves one at a time (minutes, reports, new decisions, new risks, health changes, weekly updates, closing updates, decisions made or withdrawn, rebaselines, drafted and client text, and updates that change more than the due date or the latest update). **Routine** follows, with one "Approve routine (n)" button that never covers the first group. **The rule (Stark, from `review.py` and `review.js`, 18-10-2026):** an item is routine when it is pending, has a project, has no conflict, and is not on the approve-one-at-a-time list. An owner, a date or evidence are never tested. The page words it plainly: "Each has a project and no conflict, and none is a change you approve one by one."
7. **Every proposal looks the same:** a kind pill (Minutes, Decision, Risk, Issue, Dependency, Action, Update), the title, then what it is in larger semibold type (owner, date or priority, and "approve individually" or "Routine"), then the evidence quote with a rail, then a source line naming the meeting with Open source. Approve, and an ✕ to reject with a reason.
8. **Mail and Teams proposals** use the same rows, split the same way (Needs your decision, Routine), and each says what changes: a new action or risk, or for an update the change in words ("Closes ABC-A-014 · status Open → Closed · Looks done") with the evidence and the source.
9. **Click a mail or Teams proposal to open it in the peek** (the app's right-hand panel): an editable title; the key fields (Status for an update, Owner, Due date, Priority, Project; Impact and Likelihood for a risk); a "What changes" box for an update; the Source quote with Open source; a description; and Reject, Cancel, Save and Save and approve, with arrows to the previous and next proposal. Nothing reaches the tracker until it is approved.
10. **Upload files** stays on the page (drop files anywhere); uploaded files become rows with the same actions.

## Rules and decisions already made (Alan, 17 and 18-10-2026)

Load and Process happen together (no "Load into inbox"); Organiser and Where move to the row's detail; a normal Process does not open ask creaite; Later is a snooze (the meeting leaves the ready list and returns when a transcript arrives); Not needed asks for a reason (Informal chat, No decisions, Duplicate of another meeting, Other) and is undoable; auto-load and drafting by series stay in the backlog for the 13-11-2026 review.

## Alan's answers to the open questions (18-10-2026)
1. **A guessed field does not make an item non-routine** (as today).
2. **The routine wording is approved:** "Each has a project and no conflict, and none is a change you approve one by one."
3. **A Later meeting comes back when a transcript arrives** (nothing else brings it back).
4. **An "invalid" proposal is held back in the list, for now;** to be reviewed in production.
5. **Open source opens the whole file;** there is no jump to a time, so the source lines show no times (removed in the dated mockup copy).

## Open points for Stark (not decided by Alan)

- **The Later group** is specified in the step 1 brief but not drawn in the mockup; build it as that brief says (a group below Waiting; a way to bring a meeting back).
- **Guarded files.** A first cut needs none: the reason for Not needed goes in the cleared-meetings file. The optional guarded tweak to the clear route is a proposal for Jarvis, not needed first.

## Done when

The one page replaces Intake and Review; the three stages and counts match the definitions; each of the three views works and the choice is remembered per person; a meeting opens and closes with one click and its items read as one block on a rail with the meeting's name in each group heading; routine and not routine are split and "Approve routine" never covers the first group; every proposal has its pill, emphasised line, quote and source; mail and Teams proposals open in the peek and Save and approve, Reject and next and previous work; the badge is one number; old addresses still work; light and dark, both palettes; keyboard (arrows, Enter to process, N Not needed, H Later, Esc closes the peek).

## Test (standing rule)

Automation map: the counts and stage membership, the view switch and its memory, the open and close by click, the groups and the bulk button's reach, the pills and lines, the peek's fields and buttons, the badge and the old addresses are scriptable; the look (rail, emphasis, indent), dark theme and the Board and Two panes layouts are judgement on the screenshot sheet. Test file named by Team Stark for the release.

## Change for #232 (19-10-2026, draft for Alan): files and calendar refresh
The 18-10 mockup lost the file import and the calendar refresh. Draft copy: `dev/mockups/intake-review-combined-v2-mockup-2026-10-19.html`.
- **Add files** button in the toolbar (all three views), plus a full-page "Drop to add files" target (.vtt, .docx, .txt, .md, .pdf, up to 25 MB each).
- An uploaded file is a row in Arrived with a file icon, "Likely project", and the same Process, Later and Not needed actions; an already-processed copy is marked, as today.
- **Refresh the calendar** icon beside the page's counts, with "Calendar read hh:mm".
- Not brought back: Select new, Select with transcripts, Load into inbox (Process loads and processes together).

### Added 19-10-2026: an update proposal shows the whole work item, the change highlighted
When a mail or Teams proposal changes an existing work item, the peek shows that item as it is now, not just the change:
- Title, ID and source in the header; all key fields (Status, Owner, Due, Priority, Project) plus Workstream, Milestone and Client-visible; the latest update and when it was last updated; the item's recent activity.
- Each field the proposal changes is highlighted with "was → now" (for example Status Open → Closed, Due 20-10-2026 → 23-10-2026). A changed latest update shows the old text struck through and the new text highlighted. The activity list gets an "If approved" line at the top.
- A "What changes if you approve" note states it in words; the rest of the item is plainly unchanged.
- Add files is an icon button (upload arrow), with the words in its tooltip and accessible name.

### Added 19-10-2026: what a file is, and the rail
- **A file is told apart.** A file you add is a transcript or minutes someone else wrote. creaite says which (a .vtt or "transcript" in the name is a transcript; "minutes" or "notes" is minutes; anything else asks) and the row says what will happen, with a one-click way to change it. A **transcript** is turned into minutes (a draft for approval) and then checked for work items; its button reads **Make minutes**. **Minutes** from another person are only checked for work items and no new minutes are drafted; its button reads **Find work items**. An unsure file waits for Transcript or Minutes and is left out of Process all ready.
- **The rail entry is called Intake**, with the inbox icon (the tray), and keeps the badge. The page keeps its heading "Intake and Review" (open: whether the heading should match).

### Changed 19-10-2026: the page is called Intake; each stage box gets an icon
- The page heading and the rail are both **Intake** (inbox icon, badge kept).
- The three stage boxes stay as approved on 18-10-2026, and "Show all" becomes a fourth box like them (a layers icon, the total count, "meetings and files"), separated by a thin rule, instead of a button (clickable counts; the "quiet flow" strip was tried and rejected by Alan). Each box now has an icon beside its count: **Arrived** the inbox tray, **Drafted** a document, **Approved** a ticked circle, in the accent, warning and ok colours.
