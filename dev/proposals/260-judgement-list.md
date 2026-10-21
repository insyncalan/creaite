# 2.6.0 hand checks: what only you can judge

The sheet (`dev/handchecks/v2.6.0.md`, 99 checks, still a draft) marks **8 judgement** and **5 live-only** checks, as asked. The other 86 are run by the tests. Use a throwaway vault, never your live one. For the looks, use Chrome at 1400 and 900 px wide, light and dark. Fictional data only (Falcon Data Platform).
Reply per check with **pass**, or **fail + what you saw** (a screenshot helps). About 1 hour 15 minutes in all.

## Judgement (8): does it read well?

- **10** (Review, 5 min). Look at a mail or Teams proposal that changes an existing work item. Click it to open the peek. Good: the whole item shows and each changed field reads was → now, highlighted. Fail: a field changed with no was → now, or the highlight is hard to see.
- **11** (Review, 3 min). Open a proposal that changes the latest update. Good: old text struck through, new text highlighted, and an "If approved" line at the top of the activity. Fail: any of the three missing or confusing.
- **38** (Settings › Essentials, 5 min). Look at the Draft email card and its Outlook access row, then open any Draft email popup. Good: both read cleanly in light and dark, at 1400 and 900 px. Fail: clipped, cramped, unclear wording or poor contrast.
- **45** (Settings, 8 min). Click through the tabs (Essentials to Health) and Advanced's five sub-tabs. Good: a card per group, tidy, easy to tell where you are, in both themes and widths. Fail: overflow, crowding or a tab that looks unfinished.
- **52** (a project's settings page, 5 min). Scroll the page and use the side list. Good: it reads as one page, the side list shows where you are, and Archive and close sits last, set apart with a red-tinted edge. Fail: sections blur together or the set-apart section looks like the rest.
- **57** (People, 5 min). Look at the People page and its tabs. Good: clean columns and tabs, nothing cut off, "needs details" easy to spot. Fail: clipped columns, odd spacing, or a stray star or "not in the register".
- **89** (a drafted minutes view, 8 min). The test vault has no drafted minutes: process a demo transcript in Intake first, then open the minutes. Good: it reads as one page with the Track column, aligned tables, icon bar and transcript beside the sheet. Fail: misaligned tables, a crowded bar at 900 px, or a dark-mode paper that is not white.
- **99** (Help, 5 min). Open Help and read the 2.6 lines. Good: plain British English, easy to find, readable in both themes and widths. Fail: jargon, American spelling, or old wording ("makes an Outlook draft", old Settings paths).

## Live only (5): needs the real thing, with your real Outlook, OneDrive or calendar

- **27** (Outlook, 10 min, after release). Turn on Create drafts in Outlook. Draft a chase that has an overdue date, a table and a project heading, then open it in Outlook. Good: overdue in red, table and heading survive, subject and body match the Copy version; a person with no email still gets a draft with nothing in To. Fail: lost colours or table, or body differs from Copy.
- **39** (Settings › Essentials, 5 min). Press Check on the Outlook access row with a mailbox that can write drafts, then one that cannot. Good: "You can create drafts in Outlook" for the first; "drafts stay copy and paste" and the setting turns off for the second. Fail: a wrong answer for either.
- **63** (Intake after a sweep, 5 min plus the wait). With Fetch transcripts as they appear on (Settings › Sweep and Intake), run a real sweep. Good: a real ended meeting's transcript is fetched once and Intake shows Transcript ready. Fail: none fetched, fetched twice, or a confidential meeting fetched.
- **82** (your real OneDrive, then Files and Health, 5 min, with you). Health has no rename card (dropped on 20-10, #252): rename the real company OneDrive archive folder (`_Archive` or `zz Archive`) to `99 Archive` yourself, in Finder or OneDrive, once. Good: other people's files inside are untouched and still there; Files lists and opens them, search finds them, Move back works on an archived item, and Health offers no rename. Fail: anything missing, a Move back that cannot find its folder, or a rename offered anywhere.
- **95** (Intake, 8 min). Process a real Teams transcript, then Refresh your real calendar. Good: progress and Stop show on the row, the draft lands in Review, the meetings appear, and the saved calendar holds no join link or passcode. Fail: no progress or Stop, or a link or passcode saved.

## Results

| # | Check | Pass / fail | Note |
|---|---|---|---|
| 10 | Update peek: the look | [ ] pass  [ ] fail | |
| 11 | Latest update: the look | [ ] pass  [ ] fail | |
| 38 | Draft email card and popup: the look | [ ] pass  [ ] fail | |
| 45 | Settings tabs: the look | [ ] pass  [ ] fail | |
| 52 | Project settings: the look | [ ] pass  [ ] fail | |
| 57 | People page: the look | [ ] pass  [ ] fail | |
| 89 | Minutes view: the look | [ ] pass  [ ] fail | |
| 99 | Help's 2.6 lines: the look | [ ] pass  [ ] fail | |
| 27 | Live Outlook draft | [ ] pass  [ ] fail | |
| 39 | Outlook access Check, real mailbox | [ ] pass  [ ] fail | |
| 63 | Real sweep fetches a transcript | [ ] pass  [ ] fail | |
| 82 | OneDrive folder renamed by hand to 99 Archive | [ ] pass  [ ] fail | |
| 95 | Real Process and calendar Refresh | [ ] pass  [ ] fail | |
