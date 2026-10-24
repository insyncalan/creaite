# #358 Say what the mail check is doing: design note

Written 24-10-2026 from origin/main (2.6.4, 5735c141); revised the same day after Cap's findings (21:04) and again after his re-check (21:34) and a third time after his next one (23:35); see "Changes after review", "Changes after the second review" and "Changes after the third review" at the end. Design only, no product code. Builds on Cap's scope comment on #358.

## 1. Today and the ask

**Today.** Alan types "sweep" or "check my mail", or presses Check now on Today. Both open the chat and send the words to ask creaite. The chat shows three dots, a random quip ("Percolating coffee") and a hidden "Working". Each finished tool call adds a line to a folded "n steps" list. The Today strip and the run badge are hidden while the chat is open. So Alan sees a joke and a growing number, and nothing says what is being read.

**The issue wants** true, counted text while the check runs ("Reading Outlook ..."), and at the end "Found 7, 4 need a project". The dots stay. The quip is Alan's own choice (FR BL-259 and BL-261, `dev/BUILD.md` Item 4, tested by `test_ask_quips_dots`), so replacing it is his decision (question 2).

## 2. The engine count

- **One mail check has no fixed number of steps and no total.** It is a chat run that follows the cx-sweep skill. Its first step is the people Alan follows (`SKILL.md`, flow step 0 and "People you follow"): mail, Teams chats, channels and the calendar are searched for them before the project search. Then come the project searches (flow step 1), the ignore rules, thread reads, the save and the calendar (steps 2 to 8). Alan sees "searching mail" and "searching Teams" twice, once for each stage, and nothing tells the two apart.
- **Where the count comes from.** `live_server.py`, class `Run`: `_on_assistant` remembers each tool call with a label (`describe_tool` for a chat run, `plain_step` for a run creaite starts itself); `_on_tool_result` (2915) emits `emit("step", label=...)` only for a call that finished without error. A call in flight, a failed call and a retry are never reported. The first event of a typed check, "Sweeping (stages proposals only)" (`PANEL_SWEEP_STEP`, 2357, added at 2733), goes into the event list only.
- **Two label families.** A chat run (typed "check my mail", Check now) gets `describe_tool` labels: "Microsoft 365: outlook email search", and for Bash "Running " plus the first 80 characters of the command (which can hold a mail subject). A run creaite starts itself (Close the day's catch-up, kind `sweep`) gets `plain_step` labels: "Searching mail", "Searching Teams chats", "Reading Teams channels", "Reading the calendar", "Reading a meeting, a message or a chat", and every `sweep.py` command, whatever it does (window, lock, the followed-people commands, calendar, done), becomes "Staging what the sweep found" (`PLAIN_SCRIPTS`). In that family the followed-people step cannot be told from the rest.
- **How the page reads it.** `ask.js` `askStream` draws every `step` event into `stepGroup`. `/api/events` carries no labels. A reattach streams only the events after `after` (`attachRun`, `attachDraw`), so the first step is not seen again.
- **Answer.** The engine gives one label per finished call, in order, past tense, and no total. "3 of 5 sources" and "4 of 4 places" cannot be said truthfully: the followed-people stage fills every place in about a minute, one mail search for one project is not "Outlook mail finished", and Inbox and Sent Items share a tool. So the line makes **no claim that a place is finished and shows no total**. It says where Alan's check has looked so far, and keeps moving by counting finished searches, which are true numbers.

### What the line says

While a mail check runs (one line, replaces the quip):

`Looked in so far: Outlook mail, Teams, calendar · 14 searches, 6 items read`

- **Places** are three, not five: Outlook mail, Teams (chats and channels together, because we could not verify that the chat search leaves channels out) and calendar. "Matching to projects" is not a place and is dropped. A place is listed once its first search finishes; the words are "Looked in", never "Done" or "Finished".
- **Counters** are whole numbers of finished calls: searches (mail, Teams, calendar and SharePoint search calls) and items read (`read_resource`, which reads a meeting, a message or a chat; never counted as a place). They move through the whole project search, so the line does not sit still.
- **No total, no "of N", no percentage.** A place switched off in Settings is simply absent. This removes the "5 of 4" mismatch and the "1 of 4" ending of "refresh calendar" or "check the X thread" (these runs list one or two places and say "Finished" in words).
- Before the first search finishes: "Starting". The words "Finished", "Stopped" and "Stopped early" end the line (section 5).

### How the classifier reads a label

An allow-list on whole labels, never a search of free text. It knows only the fixed `describe_tool` form "Microsoft 365: <tool name>" and the fixed `PLAIN_M365` phrases, matched exactly; the tool names map to a place: `outlook email search` to mail, `chat message search`, `teams list chats`, `teams list channel messages` and the other Teams tools to Teams, `outlook calendar search` to calendar. Everything else gives nothing: "Running ..." (a Bash label, which may carry a subject), "Using ...", `ToolSearch`, Read and Write labels, "Staging what the sweep found", the followed-people commands. A subject that contains "mail", "Teams", "Channel" or "Calendar" therefore changes nothing (today's `cdSourceOf` gets such a label wrong: a node probe gave 1, 2 and -1).

### How the page knows it is a mail check

Not from the words typed (the page keeps no copy of the server's word list). Two sources, checked against `origin/main` 2.6.4:

- **A start from this page (typed words or Check now).** `POST /api/ask` streams events only: no run record and no header (`ask`, `follow` 2192 to 2215). But the server puts the marker step "Sweeping (stages proposals only)" first in the run's events when `panel_sweep` accepted the words (`Run` 2732 to 2733), and `follow` streams from event 1, so a fresh start always sees it. **The page keys off that marker on a fresh `/api/ask`.** It does not call `/api/ask/running` after the start: the run record exists only once the server has made the run, and the answer would race the first events. A start that is not a mail check has no marker and keeps the quip.
- **A reattach, a reload, a reopened panel and Close the day.** These go through `attachRun`/`/api/ask/running`, whose record (`summary()` 2760 to 2766) carries `sweep` (true for a typed check, decided by `panel_sweep`), `kind` (`"sweep"` for the catch-up), `plain` and `started`. The page treats the run as a mail check when `run.sweep || run.kind === "sweep"`, and keeps the record on `shared.RUN`. The marker cannot be used here: a reattach draws the saved chat first (`attachDraw`, up to `seq`) and the marker is event 1, inside that reach, and the saved chat does not hold it (`self.steps` never gets it).

Both paths set one flag, `shared.RUN.mailCheck`, before the first search label is read. For a reattach the page asks for the events again from 0 for a mail check and draws only the line, not the log twice, so the places and counters are complete. If the run has ended, only the final line is drawn. No guarded file changes.

## 3. Files, and whether any is guarded

Page-only (all unguarded):

| File | Change |
|---|---|
| `system/templates/dashboard/src/core/mailCheck.js` (new) | Pure classifier on whole labels (allow-list): a label becomes a place (Outlook mail, Teams, calendar), a search, an item read, or nothing. Returns a set and two counters. Also `foundSince(rows, startedIso)`. |
| `components/closeday/CloseDay.jsx` | **Close the day keeps its own list of four sources and shows no new line**; `test_close_day_card.py` (line 192, four source items) is unchanged. `cdSourceOf` is replaced by a small mapper of its own that matches whole labels exactly, as the classifier does, and gives one of the four rows: "Searching mail" and the mail tool to Mail, "Searching Teams chats" and the chat tools to Teams chats, "Reading Teams channels" and the channel tools to Teams channels, anything else to nothing. The calendar has no row today and gets none. **Drawing rule:** `reached` (highest index) becomes a set of rows; a row is drawn done once its own label has finished; the row shown as now is the first row not done, and only once the run has finished at least one step (before that every row waits; today Mail shows now before anything has run). **Now is only a claim about order, so the sub-line is a fixed "Working through the sources"** (`cu.label = READING[...]`, line 316, is not used for a set): it never says Mail is being read when Teams finished first. The mapper names the plain label "Reading Teams chats" (`teams_list_chats`, `live_server.py` 3601) as well as "Searching Teams chats". A script step ("Staging what the sweep found") marks nothing (it marked every place at line 316). **"Matching to projects" is never drawn done by a step** (the lock, the window and the save all give the same label, `live_server.py` 3598, 3614), and it never shows as now: `CloseDay.jsx` 103 draws the `ol.cdsrc` list only while the run is running, so it cannot show done at the end; it waits until the list goes. This is a visible change to the card: question 7. |
| `src/ask.js` | In `askStream`/`attachRun`: while a mail check is live (from the run record), the true line replaces the quip; end line; `rbGuess` learns "check my mail", "check mail" and "please sweep"; the folded steps list of a mail check shows fixed phrases only (L1). |
| `dashboard/shell.html` | One new visually hidden status node for the line (section 5). |
| `style.css` | The badge label at 900 px (it is cut with an ellipsis today). |
| `src/review.js` / `core/irFold.js` | Read only: the "needs a project" rule (`!r.p`). |
| `system/templates/dashboard.html` | Rebuilt from source (the BUILT check). |
| `dev/tests/` | New tests (section 5); help text. |

**Guarded and not touched:** `live_server.py` and every other file in the guarded list.

**Cap's claim confirmed: no guarded file is needed.** The exact reason: everything the new text needs (a label per finished call, in order, plus the Review rows after the run) already reaches the page. The new line is built from fixed phrases and numbers in the page's own code. The only reason to touch `live_server.py` would be a true "n of 5" (a `phase` key on each step event and a progress event from the save step's result; with the new design it would still not tell Inbox from Sent Items). That would also change the pinned event list (`test_run_read_pinned.py`, `dev/tests/pinned/run_read/`). Not recommended.

One correction to the brief: `draft_delivery.py` is also in the code's guarded list (`dev/tests/guarded_chain.py`, `GUARDED`). It is not touched either.

Two words stay as they are because they sit in guarded text: "Sweeping (stages proposals only)" and the catch-up ask. They appear only in the folded steps list and the catch-up line. **The page keys on that exact marker string, so a pin test holds it:** a test reads the string from `PANEL_SWEEP_STEP` in `live_server.py` and from the page's source and fails if they differ by a character (a mutant that changes one letter in either must fail). If a guarded change ever alters the wording, the page and the test change in the same release.

## 4. Diff shape if a guarded diff were needed

Not needed. For the record, the optional route would be one hunk in `Run._on_assistant`/`_on_tool_result` area of `live_server.py` (a `phase` field, about 15 lines) and one for a progress event (about 15 lines), laid on top of the 2.6.4 chain that main already carries (`GUARDED-2.6.4.chain`), as its own small chain with a new marker, pin and Alan's approval of the exact diff, plus re-recorded pins and a Full review. Roughly one more agent-day.

## 5. The end, Found N, accessibility, tests, tier, estimate, risks

**How a run ends.** One closing line in the chat and the badge, from fixed words and numbers:
- Finished: "Finished. Looked in Outlook mail, Teams, calendar. Found 7 new, 4 need a project."
- Stopped (Stop pressed) or stopped early (timed out or failed): "Stopped. Looked in Outlook mail, Teams. Found 2 new so far, 1 needs a project." Items the check had already saved are real, so they are counted; with none, "Nothing saved yet".
- A failure keeps the engine's own failure line; this line comes under it, never replaces it.

**Found N (M4).** Not a set of rows taken at the start, and not a count kept in memory. After the run ends the page forces `reloadData()` (the background reload is skipped while Alan edits, and a mail check is not a confirmed run, so it is not forced today), then counts the Review rows whose `file` is a check's own file, `proposed-YYYY-MM-DD-HHMM-sweep[-n].json` (`sweep.py` 403, written when the check saves its findings; a row made on the dashboard is `proposed-...-dashboard...` and never counts), stamped from the minute the run started to the minute it ended (`started` from the run record; the end is the page's own clock when the run ends; after a reload of an ended run, the `done_at` on the saved chat reply, which the run record itself does not carry). "Need a project" is the existing `!r.p` rule on those rows. This is a pure function of the data and the run record, so Alan's own rows made during the run are not counted, and a page reload or a reattach gives the same number. **A check that saves nothing (L-C).** "refresh calendar" and a check that finds nothing write no such file, so the count is 0 and the line says "Finished. Nothing new to review." (it never says "Found 0", and it does not say the calendar was refreshed, which the page cannot tell from the words). **Concurrent checks (L-C).** Only one check runs at a time (`sweep.py lock`, which records the run), so a second check from Alan's own Claude Code session would wait or be turned away; the window from start to end stops a later check's file being counted. A file written inside the window by another process would still be counted: named as accepted, and the leak is only a number. If the reload cannot run because an edit is open, the line says "Finished. Open Review to see what it found" with no number, and fills the number when the edit closes.

**Accessibility (M5, M-C).** The whole chat log is a polite live region (`shell.html` 139, `chLog`), the badge is a polite status (146), `#askLive` (`ask.js` 700 to 711) carries the finish mark from #231 (not the badge's words), and the working line is removed and drawn again on every step. Today, with the chat closed, the end already changes the badge text ("took m:ss", `rbT` and `rbL`, `ask.js` 678 to 679) and then writes `#askLive` (708; `rbEnd` calls `askMarkShow` at 690); with the chat open the log draws its own closing line. Those end announcements exist before #358 and stay as they are. So:
- The line is drawn with `aria-hidden="true"` in the working line (as the quip is), and announced through one new visually hidden status node. **The node sits inside `#chat` but outside `#chLog`** (`#chLog` is a polite live region cleared at `ask.js` 653, so a node inside it would be wiped and read twice): `#chat` is hidden when closed (`style.css` 974 to 975) and the badge is hidden when it is open (1732), so each place change is read from exactly one of the two, never twice. It is written only when the **set of places changes**, never on a counter change. **The log's closing line stays readable** (today's end announcement with the chat open is the reply text in `#chLog`, `ask.js` 807, and it carries the "Found N" line); **only the node's own end write is skipped**, so the end is read once, by the log (chat open) or by the badge and `#askLive` (chat closed), as today. **Chat closed:** the badge's end label stays "took m:ss" as today; the "Found N" line is the one added end announcement, written once to `#askLive` with the finish mark (#231), not into the badge label.
- **The badge shows the places only, never the counters.** Its label is "Mail check: mail, Teams" (short names), so it changes at most three times for places, plus today's end change, and the full line with the counters is in its `title` (a title is not announced). The badge's label and `#askLive` are written only when the text differs. During a mail check the badge's own label is not allowed to carry a counter: that would be read out after every finished search. Correction to the first note: `rbTick` (`ask.js` 681) changes only the clock, so the badge does not rewrite its label every second today.
- **The bound:** no more than three place-change announcements per open surface, plus today's end announcements, unchanged, plus one "Found N" line. **Test:** a screen-reader stand-in counts every change to the badge, `#askLive`, the log's closing line and the new node across a whole run of 20 or more searches, with the chat closed and again with it open. In each case the place-change announcements number at most three, none comes from both the node and the badge, and the end announcements equal what a run that is not a mail check gives today plus exactly one "Found N" line, readable with the chat open (compared in the same test). Mutants: put the node outside `#chat` or inside `#chLog`; draw the log's closing line `aria-hidden`; write the node on a counter change or at the end.
- At 900 px the badge label is cut with an ellipsis (`style.css` 1731 to 1734): short place names fit; tested.
- Reduced motion: the line is text and has no animation; the dots are unchanged.

**The steps list (L1).** The folded "n steps" list of a mail check already shows text BL-288 and the private-subject rule say must not show: the followed-people command and its output file name, and an "expected ... --subject" label with a mail subject. This exists before #358. Recommended in this change, page-only: for a run the record marks as a mail check, a label that is not one of the fixed phrases is drawn as "A creaite step". The folded list for other runs is unchanged. This is a visible change to the fold-out, so it is question 5.

**What this does not reach (M-B).** `remember_chat` (`live_server.py` 3509) saves the raw step labels in the chat's history with no mark that the run was a mail check, and `attachDraw` (`ask.js` 648 to 656) draws that history first on a reattach or a reload; an old chat reopened later is drawn only from it. The page has no way to tell those steps from any other chat's without keeping a copy of the server's word list, which section 2 rules out. So **the fixed-phrases-only rule covers live runs only**: steps drawn as they arrive, including those after the point a reattach resumes. Steps drawn from the saved chat keep today's text, as they do now. To cover them too, `remember_chat` needs a `sweep` field on the saved reply (about 3 lines in the guarded `live_server.py`, ready as `dev/proposals/358/live_server-saved-steps.patch`, not applied): a chain diff to the Head, Alan's approval of the exact diff, re-recorded pins and a Full review, roughly 0.5 day more. That is **not** in this design; it is the one thing in question 5 that would make a guarded diff necessary. With the live-only choice the design stays page-only.

**Unit (Node), the classifier:** every label kind (chat labels, plain labels, `ToolSearch`, calendar, a Bash label that carries a subject containing "mail", "Teams", "Channel" or "Calendar", the followed-people commands, "Staging what the sweep found"). Mutants: a classifier that scans free text (the subject case must fail); one that keeps the "highest index" instead of a set (Teams before mail must fail); one that counts a place switched off; one that lists a place from a failed call (a failed call has no event); one that counts `read_resource` as a place.

**Browser (1400 and 900 px),** using the stand-in `claude` of `test_run_badge.py` with a fake stream of real labels, including **a run with the followed-people stage first** (all three places within the first minute: the line must still say "Looked in so far", with no total, and the counters keep moving through the project search). Also: a run with error steps and a retry; "refresh calendar" and "check the X thread"; a reattach mid-run and after the end; a page reload; Close the day's catch-up (plain labels, a script step marking nothing); Found N with a row made on the dashboard and an edit open during the run; stopped, timed-out and failed endings (with and without saved items); the badge with the chat closed, at 1400 and 900 px; no subject or sender anywhere (line, badge, live nodes, the steps list); announcements counted (at most three place changes per open surface, end announcements unchanged) with a screen-reader stand-in, **with the chat closed and open**; a typed start (marker) and a Check now start; a reload mid-run (the saved chat's raw steps stay as today); Close the day's four-source list and its test unchanged, the rows drawn by the rule in section 3 (nothing running before the first step, Matching to projects only at the end); "refresh calendar" ending "Nothing new to review"; a check file outside the run's window not counted; reduced motion. Mutants: show `ev.label`; draw a percentage; show a total; count rows that were already there; count a dashboard row; drop the live-node rule. `test_ask_quips_dots.py` and the Close the day tests still pass; no VIP word in any new string. **The leak test is a gate test and is never relaxed.**

**Review tier (M6): Light, on one condition.** The line is built from an allow-list of fixed phrases and numbers, so no label text reaches it; with the leak test above as a gate, no leak path is added. If the Head reads Team/04 as putting any label-derived text in Full, Full costs about 0.5 day more. Question 6.

**Estimate:** about **2 builder-days** (was 1.5; unchanged by the second review, which only narrows scope: Close the day gets no new line, the badge shows places only). A = classifier, counters, Close the day set fix and the start marker/run record 0.75; B = the line, end line and Found N, live node, badge at 900 px and the steps-list change 0.9; C = tests and help text 0.35. Adding the saved-chat route (question 5) would add about 0.5 day and a Full review.

**Risks.**
- Privacy: only fixed phrases and numbers; the steps-list change closes the existing fold-out gap for mail checks.
- The followed-people stage is never named or shown; its labels classify as nothing in a chat run, and in Close the day nothing a script step says marks a place. **Accepted (L-B, BL-288):** its searches and the one read per conversation do move the counters and the places in the first minute. That shows activity and a rough number to Alan on his own screen, never who or what; starting the counters after that stage is not possible from the page (the labels do not mark where it ends). The wording makes no claim of completion.
- No false progress: past tense, no total, no percentage, "Finished" in words.
- Replay: the line is rebuilt from the replayed events for a mail check; an ended run shows only the final line.
- Visible change: needs Alan's before-and-after sign-off.

## 6. Open questions for Alan

1. Drop "3 of 5 sources" for "Looked in so far: ..." with searches and items read, and no total? (Recommended: yes. A total cannot be made true without a guarded change.)
2. Replace the quip with the true line for a mail check only, or add a second line? (Recommended: replace; keep quips for other runs. The quip is his own FR, BL-259 and BL-261.)
3. Release: the issue body says 2.6.6, the plan said 2.6.5, and #199 Next does not list #358 under 2.6.5. Which release is Alan's call. The work is page-only either way. A true "n of N" would be its own small release with a guarded diff.
4. "Found N" counts the new items this check saved (recommended), or everything waiting?
5. The folded steps list of a mail check: show fixed phrases only for the live run (recommended, page-only, closes the subject and followed-people gap while it runs), or leave it as it is? Steps drawn from the saved chat (after a reload, or an old chat) keep today's text unless a `remember_chat` change is added to the guarded `live_server.py` (about 0.5 day more, a chain diff, your approval of the exact diff, a Full review). Saved steps (after a reload, or an old chat) can show a mail subject in a "Running ..." label and the followed-people command (`describe_tool`, 80 characters of the command). A page-only option needs no word list and no flag: when drawing saved steps, cut every "Running <script>.py ..." label to "Running <script>.py". It works off the fixed `describe_tool` prefix and covers every chat, but it is a visible change to the fold-out of every chat. The cut also covers what `describe_tool` leaves: any "Running" label that is not "Running <name>.py" is drawn "Running a command", and Write and Edit labels (the followed-people output file is named in SKILL.md 74) are drawn "Writing a file"; the same rule applies to live mail-check steps. Choose: live only (recommended), live plus saved (guarded diff, ready as `dev/proposals/358/live_server-saved-steps.patch`, unapplied), the page-only cut for saved steps, or neither.
6. Review tier: Light with a permanent leak gate (recommended), or Full?
7. Close the day's card: its rows tick only from their own searches (a script step ticks nothing), nothing shows as running before the first step, and "Matching to projects" never ticks from a step? (Recommended: yes. Today the first script step sets reached=3 (`CloseDay.jsx` 316): Mail, Teams chats and Teams channels tick together and "Matching to projects" shows as now, which is not true. Or leave the card exactly as it is.)

## Changes after review

Cap's findings on #358 (24-10-2026 21:04), each checked on origin/main 2.6.4 and answered.

| Finding | Change |
|---|---|
| H1: the line fills in a minute (followed people searched first, `SKILL.md` flow step 0), then sits still | Confirmed. The line says "Looked in so far", claims no place is finished, shows no total, and keeps moving with counters of finished searches and items read. Test with a followed-people run added. |
| M1: places and total do not match ("5 of 4"); "refresh calendar" and a thread check end as "1 of 4" | Total dropped; "Matching to projects" removed; three places only; short runs end "Finished" in words. |
| M2: how the page knows it is a mail check (word list drift, first step lost on reattach, Close the day has no marker) | From the run record the server already sends (`sweep`, `kind: "sweep"`, `started`); no copy of the word list; works on reattach, reload and Close the day. Replay from 0 for a mail check. No guarded change. |
| M3: plain labels turn every `sweep.py` command into "Staging what the sweep found"; Close the day's first step marks every place (`CloseDay.jsx` 316) | Confirmed. Classifier is an allow-list of whole labels; a script step marks nothing. Close the day keeps its own four rows and no new line (section 3 gives its drawing rule). |
| M4: Found N is racy (no forced reload, own rows counted, lost on reload, stop and failure unspecified) | Counted from the check's own files (`...-sweep[-n].json`, `file` on each Review row) stamped at or after the run's start, after a forced reload; same number after a reload; stop, timeout and failure endings specified. |
| M5: announces on every step (polite log, working line redrawn; badge also polite) | Own hidden status node, written only when the set of places changes or the run ends; line `aria-hidden` in the log; badge rewrites its label only when it differs. |
| M6: tier Light is contestable | Light only with an allow-list design and a leak test that is a gate and never relaxed; Full as the alternative (question 6). |
| L1: the steps list shows the followed-people command and a subject | Proposed page-only fix for mail checks (fixed phrases only); question 5; estimate +0.25 day. |
| L2: chats vs channels, `read_resource` not mail | Teams is one place; `read_resource` is "items read", never a place. |
| L3: the quip is Alan's FR | Named (BL-259, BL-261, `test_ask_quips_dots`) in section 1 and question 2. |
| L4: release conflict | Stated as Alan's call (question 3). |
| L5: badge cut at 900 px | Short places in the badge, full line in its title; tested at 900 px. |
| L6: timed-out, failed and stopped endings | Specified in section 5. |
| Missing tests | Added: subjects with "Teams", "Channel", "Calendar"; followed-people run; error steps and retries; "refresh calendar" and thread checks; reattach; Close the day; Found N with a dashboard row or an open edit; announcement count; reduced motion; timeout and failure. |
| Estimate | 1.5 to about 2 builder-days. |

## Changes after the second review

Cap's re-check (24-10-2026 21:34) of `v265-358-note2` 4e417ee6, each checked on `origin/main` 2.6.4 (5735c141).

| Finding | Change |
|---|---|
| M-A: a typed start gets no run record | Confirmed (`/api/ask` streams events only). The page keys off the marker step "Sweeping (stages proposals only)", always first on a fresh start; the run record is used for reattach, reload and Close the day. No call to `/api/ask/running` after a start (it would race). Section 2 says so. |
| M-B: raw step text in the saved chat (`remember_chat`, `attachDraw`) | Confirmed. Choice: the fixed-phrases rule covers **live runs only**; the design stays page-only. Consequence stated: steps drawn from the saved chat (reload, old chat) keep today's text. Covering them needs a `sweep` field in `remember_chat`, a guarded `live_server.py` diff (about 0.5 day, Full review, Alan's approval); put to Alan in question 5. |
| M-C: the badge is a polite region; "at most four" false with the chat closed | The badge shows places only, never counters (full line in its title); label and `#askLive` written only when the text differs. Test counts changes with the chat closed and open. The wrong claim about `rbDraw` is corrected (`rbTick` changes only the clock). |
| L-A: Close the day's test expects four sources | Close the day keeps its own four-source list and shows no new line; the test stays as it is. Only the set fix (a script step no longer marks every place) changes it. |
| L-B: followed-people counters (BL-288) | Named as accepted (activity and a rough number, never who); starting after that stage is not possible from the page. |
| L-C: Found N after "refresh calendar" and with concurrent checks | No file means "Finished. Nothing new to review."; files counted only from the run's start to its end; one check at a time through the lock; an outside file inside the window is named as accepted. |
| Estimate and questions | Estimate unchanged (about 2 days). Question 5 now has the three choices; no other question changes. |

Not checked in this revision either: a real mail check, the connector's tool schemas (so whether Inbox and Sent Items can be told apart; the design no longer needs it), a browser, the suite.

## Changes after the third review

Cap's findings (24-10-2026 23:35) on `v265-358-note3` e7988e38, each checked in the code on 2.6.4.

| Finding | Change |
|---|---|
| MEDIUM-1: "at most four" counted announcements that already happen; the new node had no place | Node sits inside `#chat`; the log's closing line is `aria-hidden` for a mail check and the node's end write is skipped; the bound is "no more than three place-change announcements per open surface, plus today's end announcements, unchanged"; test and mutants reworded (section 5). |
| LOW-1: Close the day's list does not fit the classifier; no drawing rule; contradiction between the Close the day row and the Changes table; wrong row for "Staging what the sweep found" | Close the day has its own mapper for its four rows and no calendar row; the drawing rule is written (done on its own label, now is the first row not done, nothing running before the first step); "Matching to projects" ticks when the run ends; both rows now say the same thing; the visible change is question 7. |
| LOW-2: saved steps can show a subject and the followed-people command | Fourth choice in question 5: cut "Running <script>.py ..." to "Running <script>.py" when drawing saved steps (page-only). |
| Nit: the page keys on an exact guarded marker string | Pin test added (section 3). |
| LOW-3: references | `rbTick` is at 681; `#askLive` carries #231's finish mark; the run record has no `done_at` (the saved chat reply does); the repeated Inbox/Sent Items sentence in section 3 is removed. |
| Estimate and tier | Unchanged: about 2 days, Light. Question 7 added; the other six unchanged. |

## Changes after the fourth review

Cap's findings (25-10-2026 00:35) on `v265-358-note4` d21e7958.

| Finding | Change |
|---|---|
| MEDIUM-A: Found line lost to a screen reader with the chat open | Log closing line stays readable; only the node's end write is skipped; bound "plus one Found line"; chat closed, badge end label stays "took m:ss", Found goes once to `#askLive` (section 5). |
| LOW-A | "Matching to projects" never ticks from a step; question 7 describes today correctly (316). |
| LOW-B | Fixed sub-line; mapper names "Reading Teams chats" (section 3). |
| LOW-C | Other Running labels become "Running a command", Write/Edit become "Writing a file" (question 5); optional guarded patch ready, unapplied. |
| LOW-D | Node inside `#chat`, outside `#chLog`. |
| References | `rbT`/`rbL` 678 to 679; `askMarkShow` 690. |
