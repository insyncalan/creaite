# 2.6.0 release notes: inputs for the PM

What 2.6.0 changes for Alan, one line each, from what has landed on `origin/v26-line-4` (7b12ab33, 22-10-2026) since v2.5.3,
and the board. Raw material for the plain release notes, not the notes themselves. Each group names its issue and the branch
head that carries it (merged into the line unless it says otherwise). Already shipped in 2.5.x and left out: #238, #245, #251,
#252, #255, #264, #265, #97 (quiet hours, 2.5.3). User lines follow the plain words (dev/PLAIN-WORDS.md on `v254-289`): no
file or script names; "check of mail and Teams", "suggestion", "save". Button and page names are quoted as they appear today.

## Intake: one page for everything that arrives and waits (#232; v26-232-next-2 6e4fc5ef, v26-intake-names ebd78591)

- Intake and Review are one page, **Intake**, with one entry in the sidebar and one number; the old Review and Intake addresses open it.
- Three views, remembered in this browser: List, Board and Two panes.
- Stage boxes across the top (Arrived, Drafted and so on, with Show all), each with its count.
- Suggestions are split into routine and needs-your-decision; **Approve routine** approves the routine group in one go, with one Undo.
- Click a meeting row to open it and again to close it; Enter, N (not needed) and H (later) work on the focused row.
- Process, Later, Not needed (with a reason) and Restore on each meeting row; **Process all ready** skips private meetings, and Stop ends it.
- Process and Refresh run on their own with progress and Stop; they no longer open ask creaite.
- **Add files**, or drop files anywhere on the page; each file shows its size, likely project and a kind (transcript, minutes, not sure), and a "not sure" file waits for you to choose.
- Minutes written by someone else can be added as minutes: **Find work items** suggests items from them without drafting new minutes (needs a guarded change, see Pending).
- A Search box finds meetings, files and suggestions by title, project name or source; Esc clears it.
- **Calendar read hh:mm** with a refresh icon replaces the separate Calendar import step.
- A suggestion that changes an existing item opens the whole item in the peek, each change marked "was → now", and you can edit what it changes.
- Previous and Next step through the suggestions in the peek.
- A confidential meeting shows its title and times only; a private conversation never names a project.
- The new-workstream offer is on the page's rows again.
- Today's Intake line, the sidebar number and Close the day's "Review now" all point at the one page and show the same number.
- A file dropped into the inbox gets its row at once; the page never scrolls sideways at 900 or 1440 pixels.

## Minutes view v2 (#268; v26-minutes-view-v2 983817ed)

- One version of the minutes: what you see is what is filed and exported (no separate Internal and Distributed tabs).
- A **Track** column on every table: a tick makes the line a work item, a cross removes it from the minutes, neither keeps it in the minutes only.
- Edit in place: click the words and type; Owner, Priority and Workstream are drop-downs in the row; Due opens the usual deadline box.
- "Needs details" (not "isn't in the people register") under an owner, with **Add details**.
- **Approve minutes** is one click with an Undo; a box appears only when a ticked item has a real problem, and says where.
- Minutes with nothing ticked can still be approved (covers the old "rejected every item" defect, #261).
- Undo of Approve minutes leaves the minutes exactly as they were.
- One continuous sheet with a thin page marker that never splits a table row; fit to width stops at 100%; table headers no longer stick over rows.
- Hover a row to light the transcript turn it came from; the transcript pane's open or closed state is remembered.
- Export as Word, PDF or HTML, and **Draft the follow-up email**, both follow the Track choices.
- A risk or issue keeps its workstream from the minutes.
- Esc on an AI suggestion keeps your words; reading a meeting again keeps any unsent text in ask creaite.

## Approving minutes from Intake follows Track (#275; v26-track-from-review-4 30e23a49, v26-track-tests-intake 7775810c, rounds 3 on the line b25022e8)

- Approve on a minutes row in Intake does exactly what Approve minutes does: ticked lines become work items, crossed are removed, neither stay in the minutes only.
- Approve routine and the group tick never approve a line you crossed or left with neither.
- If one is stopped, it says so plainly, says the item is back on Intake, and puts the batch and your Track choices back as they were.

## AI drafts and checks (#186, #262, #263; v26-186-262-3 bb60f4bb)

- Draft email: the AI bar (Improve, Tone, Ask) is back for recipients outside your own domains, working from client-visible facts only, with the client checks on its reply.
- AI on the minutes (the ✦, and a section redraft): a suggestion that adds something internal (an item not client-visible, a name, internal wording) is dropped with a message saying why.
- Client messaging field: AI suggestions use client facts only and get the same reply check.
- The item editor offers AI on selected text.
- A drafted reply such as "I can't give a firm date, but …" is no longer thrown away as a refusal (review fixes, v26-review-fixes-3 2729ef6b).

## People you follow on Today (#236; v26-236-next 4fdf0065)

- What the check of mail and Teams takes from a followed person's mail or chat (suggestions, a memory note) is a **From <name>** row in Needs attention, listing each item.
- From rows come last in Needs attention, after the milestone rows; a reply or forward (RE:, Fwd:, AW:) joins its thread.
- Dismissing a From row keeps it gone until the thread adds something new or changes an open item.
- A private conversation is a title and times only; a confidential or private thread saves nothing for review.
- No label anywhere says the person is followed.

## Messages: Seen on the quiet lines (#276; v26-276-4 3ab96180)

- A "Replied" or "nothing for you" line in Today's Messages now has **Seen** (the eye), with Undo; it stays gone after a reload and the next check.

## Settings, People and project settings (#246, #247, #248; v26-settings-line-2 e96a9594, v26-people-m2-m3-2 899375ce, v247-follow-fix 6878e6dd; all merged)

- Settings is reorganised into tabs, one card per group.
- People and projects leaves Settings: the People page is the home of the whole register (four tabs, search and filters, add, edit details, remove).
- Every link to a person opens the People page; old Settings addresses for People, Workstreams and Projects open their new homes.
- Remove from the register is refused, with the reason, while the person still owns items or is named as a stakeholder, milestone owner or workstream lead.
- Project settings v2: one scrolling page with General, People on the project, Workstreams, Logos, Reporting, and Archive and close.
- Add a person keeps the Follow tick; following someone is set on the project's settings page only.

## Page keys (#288; v26-288 d194145b)

- Single keys open pages from anywhere: T Today, P Projects, W Work, I Intake, F Files, A Activity, S Settings, R Reporting, E People.
- Work's filter picker moves from F to **Shift+F** (and on the People page); E no longer opens a row in Work (Enter does).
- On Intake, A and R still approve and reject the focused suggestion; an open peek, ask creaite, a menu or a dialog holds the page keys.

## Wording: "Actions" in item sources (#296; v26-296 e53b62d1)

- An item's source note says "— Actions" (was "— Action Items"); notes already written in the old words still link to the right section.

## Meeting invites: links and passcodes kept out (h3c; v26-invite-h3c bacb4003, v26-review-fixes-3 2729ef6b)

- A meeting's title, place or organiser that carries a passcode, password, join address or dial-in is shown as "Meeting", as in 2.5.3 (the 2.6 attempt to keep the words before it was withdrawn: it let some passcodes through).
- Net effect for Alan: the same as 2.5.3. Worth one line only if the notes mention it at all.

## Smaller fixes (hand checks and review, on the line)

- A week with no meetings in the calendar no longer stops Refresh (review fixes, v26-review-fixes-3).
- Colours on the minutes sheet: the green "done" colour on the white page shows again (#268; c1fa9d29); monospace text uses a monospace font.
- Today's Week ahead buttons are back to their normal height (7a83c8f2).
- The project settings page's people search box matches the People page's (7a83c8f2).
- Today's day band "?" is readable in every theme (6b3088e9; but see Ambiguous: #284 removes it in 2.5.4).

## Not in 2.6.0 yet / pending

**Needs guarded diffs Jarvis applies (on Alan's say):**
- **guard-small** (four diffs: tracker, live server x2, reach): small safety fixes from Cap's reviews; nothing visible. Pending on the line.
- **Find work items** (#232 E1): `intake-232-minutes` (live server, reach) and `E1-tracker.rebased-on-guard-small` (after guard-small). Without them, Find work items fails safe: the row says "Not staged" and nothing is saved. The Intake line above should not promise it until these are in.
- Already applied on the line (no action): review-fixes, minutes-view-v2 workstream, track-from-review, draft-ai-186, followed-needs vip-api, settings-line rules and scripts.

**On branches, not merged into v26-line-4:**
- 2.5.4 (`v254-release` 2635fc97, not tagged): #277, #279 (Prep page with no project), #280 (one bad item no longer blocks saving; held items say why), #281 (resizable Draft email preview), #282 (exports say "Actions"), #284 (Today's "?" removed), #285, #286, #287. 2.6.0 needs 2.5.4 merged in, or these go missing.
- #283 Read again (was Re-extract) as its own run, not an ask creaite message (`v26-283-design` ab4354f6): proposed for 2.6.1, with its own guarded diffs.
- #289 Plain words glossary (`v254-289` 9a62205f) and #290 the guard test (`v254-290` 60ec73d9): 2.6.1.
- #291 Plain words Tier 1 walk (`v26-291-walk` 5f5596dc): 79 screen texts found, no fixes yet: 2.6.1.
- #241 Work items refinement (`v26-work-items-abc` 532f9c3a, `v26-work-items-d` 131ae1f3), #183 Draft email into Outlook (`v26-draft-delivery-fix` 7e171d5e), #250 transcripts fetched as they appear (`v26-fetch-transcripts` d693a13f): still waiting, not on the line.
- `v26-help-text` (Help lines for #246-#248, #241, #183, #250, #97): not merged; Help on the line already covers the settings line.
- Keyboard check c49 (`v26-c49-fix`, merged): no regression; three order-dependent Undo lines left for 2.6.1 (tests only).

## For the PM: ambiguous or still to settle

- **#284 vs the "?" fix:** 2.5.4 removes Today's day-band "?"; the line made it readable. After 2.5.4 merges, drop the "?" line.
- **#282 and #296:** exports say "Actions" in 2.5.4 (#282), item sources in 2.6 (#296); one line in the notes may cover both.
- **Invite scrub:** no net change from 2.5.3; suggest leaving it out of Alan's notes.
- On-screen labels still say "Review" for what lives on Intake: "Draft in Review" (Today's day line), "Open in Review" (From rows), "n wait in Review" and "n left in Review" (minutes), "as proposals in Review" (Draft an update), "Open the staged update in Review". Help quotes them as shown. They and "proposal", "staged", "sweep" are #291's (2.6.1).
- The follow-up email's note still names "the Distributed version" and "Internal version" for a draft, though the minutes view has one version.
