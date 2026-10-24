# #358 Say what the mail check is doing: design note

Written 24-10-2026 from origin/main (2.6.4, 5735c141); revised the same day after Cap's findings (21:04), see "Changes after review" at the end. Design only, no product code. Builds on Cap's scope comment on #358.

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

Not from the words typed, and not from the first step label (lost on a reattach). From the **run record**, which the server already sends: `summary()` (`/api/ask/running`, the catch-up status) carries `sweep` (true for a typed check, decided by `panel_sweep` from its word list, so the page keeps no copy of the words), `kind` (`"sweep"` for Close the day's catch-up), `plain`, `message` and `started`. The page treats a run as a mail check when `run.sweep || run.kind === "sweep"`. `askStream`/`attachRun` receive that record at every start and every reattach, so a reload, a closed panel and Close the day all know. Check now on Today sends the same typed words, so the record says `sweep` too. No guarded file changes: the record is already there; the page only has to keep it (a field on `shared.RUN`) and pass it to the line.

When it reattaches mid-run, the line is rebuilt from the replay: the page asks for events from 0 for a mail check (it draws only the line, not the log twice), so the places and counters are complete. If the run has ended, only the final line is drawn.

## 3. Files, and whether any is guarded

Page-only (all unguarded):

| File | Change |
|---|---|
| `system/templates/dashboard/src/core/mailCheck.js` (new) | Pure classifier on whole labels (allow-list): a label becomes a place (Outlook mail, Teams, calendar), a search, an item read, or nothing. Returns a set and two counters. Also `foundSince(rows, startedIso)`. |
| `components/closeday/CloseDay.jsx` | `cdSourceOf` is replaced by the classifier; its `reached` (highest index) becomes the set, and a script step ("Staging what the sweep found") no longer marks every place (it did at line 316). It shows the same line as the chat and the badge. |
| `src/ask.js` | In `askStream`/`attachRun`: while a mail check is live (from the run record), the true line replaces the quip; end line; `rbGuess` learns "check my mail", "check mail" and "please sweep"; the folded steps list of a mail check shows fixed phrases only (L1). |
| `dashboard/shell.html` | One new visually hidden status node for the line (section 5). |
| `style.css` | The badge label at 900 px (it is cut with an ellipsis today). |
| `src/review.js` / `core/irFold.js` | Read only: the "needs a project" rule (`!r.p`). |
| `system/templates/dashboard.html` | Rebuilt from source (the BUILT check). |
| `dev/tests/` | New tests (section 5); help text. |

**Guarded and not touched:** `live_server.py` and every other file in the guarded list.

**Cap's claim confirmed: no guarded file is needed.** The exact reason: everything the new text needs (a label per finished call, in order, plus the Review rows after the run) already reaches the page. The new line is built from fixed phrases and numbers in the page's own code. The only reason to touch `live_server.py` would be a true "n of 5" (a `phase` key on each step event and a progress event from the save step's result; with the new design it would still not tell Inbox from Sent Items). That would also change the pinned event list (`test_run_read_pinned.py`, `dev/tests/pinned/run_read/`) and still could not tell Inbox from Sent Items. Not recommended.

One correction to the brief: `draft_delivery.py` is also in the code's guarded list (`dev/tests/guarded_chain.py`, `GUARDED`). It is not touched either.

Two words stay as they are because they sit in guarded text: "Sweeping (stages proposals only)" and the catch-up ask. They appear only in the folded steps list and the catch-up line.

## 4. Diff shape if a guarded diff were needed

Not needed. For the record, the optional route would be one hunk in `Run._on_assistant`/`_on_tool_result` area of `live_server.py` (a `phase` field, about 15 lines) and one for a progress event (about 15 lines), laid on top of the 2.6.4 chain that main already carries (`GUARDED-2.6.4.chain`), as its own small chain with a new marker, pin and Alan's approval of the exact diff, plus re-recorded pins and a Full review. Roughly one more agent-day.

## 5. The end, Found N, accessibility, tests, tier, estimate, risks

**How a run ends.** One closing line in the chat and the badge, from fixed words and numbers:
- Finished: "Finished. Looked in Outlook mail, Teams, calendar. Found 7 new, 4 need a project."
- Stopped (Stop pressed) or stopped early (timed out or failed): "Stopped. Looked in Outlook mail, Teams. Found 2 new so far, 1 needs a project." Items the check had already saved are real, so they are counted; with none, "Nothing saved yet".
- A failure keeps the engine's own failure line; this line comes under it, never replaces it.

**Found N (M4).** Not a set of rows taken at the start, and not a count kept in memory. After the run ends the page forces `reloadData()` (the background reload is skipped while Alan edits, and a mail check is not a confirmed run, so it is not forced today), then counts the Review rows whose `file` is a check's own file, `proposed-YYYY-MM-DD-HHMM-sweep[-n].json` (`sweep.py` 403, written when the check saves its findings; a row made on the dashboard is `proposed-...-dashboard...` and never counts), stamped at or after the minute the run started (`started` from the run record). "Need a project" is the existing `!r.p` rule on those rows. This is a pure function of the data and the run record, so Alan's own rows made during the run are not counted, and a page reload or a reattach gives the same number. If the reload cannot run because an edit is open, the line says "Finished. Open Review to see what it found" with no number, and fills the number when the edit closes.

**Accessibility (M5).** The whole chat log is a polite live region (`shell.html` 139, `chLog`) and the badge is a polite status (146), and the working line is removed and drawn again on every step, so a true line inside them would be read out on every step. So:
- The line is drawn with `aria-hidden="true"` in the working line (as the quip is), and announced through one new visually hidden status node, written only when the **set of places changes** or the run ends (at most four announcements a run), never on a counter change.
- The badge keeps its clock in a separate node and rewrites its label only when the text differs (today `rbDraw` rewrites it every second).
- At 900 px the badge label is cut with an ellipsis (`style.css` 1731 to 1734): the visible badge shows the places short ("mail, Teams, calendar") with the full line in its title; tested.
- Reduced motion: the line is text and has no animation; the dots are unchanged.

**The steps list (L1).** The folded "n steps" list of a mail check already shows text BL-288 and the private-subject rule say must not show: the followed-people command and its output file name, and an "expected ... --subject" label with a mail subject. This exists before #358. Recommended in this change, page-only: for a run the record marks as a mail check, a label that is not one of the fixed phrases is drawn as "A creaite step". The folded list for other runs is unchanged. This is a visible change to the fold-out, so it is question 5.

**Unit (Node), the classifier:** every label kind (chat labels, plain labels, `ToolSearch`, calendar, a Bash label that carries a subject containing "mail", "Teams", "Channel" or "Calendar", the followed-people commands, "Staging what the sweep found"). Mutants: a classifier that scans free text (the subject case must fail); one that keeps the "highest index" instead of a set (Teams before mail must fail); one that counts a place switched off; one that lists a place from a failed call (a failed call has no event); one that counts `read_resource` as a place.

**Browser (1400 and 900 px),** using the stand-in `claude` of `test_run_badge.py` with a fake stream of real labels, including **a run with the followed-people stage first** (all three places within the first minute: the line must still say "Looked in so far", with no total, and the counters keep moving through the project search). Also: a run with error steps and a retry; "refresh calendar" and "check the X thread"; a reattach mid-run and after the end; a page reload; Close the day's catch-up (plain labels, a script step marking nothing); Found N with a row made on the dashboard and an edit open during the run; stopped, timed-out and failed endings (with and without saved items); the badge with the chat closed, at 1400 and 900 px; no subject or sender anywhere (line, badge, live nodes, the steps list); announcements counted (at most four) with a screen-reader stand-in; reduced motion. Mutants: show `ev.label`; draw a percentage; show a total; count rows that were already there; count a dashboard row; drop the live-node rule. `test_ask_quips_dots.py` and the Close the day tests still pass; no VIP word in any new string. **The leak test is a gate test and is never relaxed.**

**Review tier (M6): Light, on one condition.** The line is built from an allow-list of fixed phrases and numbers, so no label text reaches it; with the leak test above as a gate, no leak path is added. If the Head reads Team/04 as putting any label-derived text in Full, Full costs about 0.5 day more. Question 6.

**Estimate:** about **2 builder-days** (was 1.5). A = classifier, counters, Close the day and the run record 0.75; B = the line, end line and Found N, live node, badge at 900 px and the steps-list change 0.9; C = tests and help text 0.35.

**Risks.**
- Privacy: only fixed phrases and numbers; the steps-list change closes the existing fold-out gap for mail checks.
- The followed-people stage is never named or shown; its labels classify as nothing in a chat run, and in Close the day nothing a script step says marks a place. Its searches do count as searches and places, which is true ("looked in"), and the wording makes no claim of completion.
- No false progress: past tense, no total, no percentage, "Finished" in words.
- Replay: the line is rebuilt from the replayed events for a mail check; an ended run shows only the final line.
- Visible change: needs Alan's before-and-after sign-off.

## 6. Open questions for Alan

1. Drop "3 of 5 sources" for "Looked in so far: ..." with searches and items read, and no total? (Recommended: yes. A total cannot be made true without a guarded change.)
2. Replace the quip with the true line for a mail check only, or add a second line? (Recommended: replace; keep quips for other runs. The quip is his own FR, BL-259 and BL-261.)
3. Release: the issue body says 2.6.6, the plan said 2.6.5, and #199 Next does not list #358 under 2.6.5. Which release is Alan's call. The work is page-only either way. A true "n of N" would be its own small release with a guarded diff.
4. "Found N" counts the new items this check saved (recommended), or everything waiting?
5. The folded steps list of a mail check: show fixed phrases only (recommended, closes the subject and followed-people gap), or leave it as it is?
6. Review tier: Light with a permanent leak gate (recommended), or Full?

## Changes after review

Cap's findings on #358 (24-10-2026 21:04), each checked on origin/main 2.6.4 and answered.

| Finding | Change |
|---|---|
| H1: the line fills in a minute (followed people searched first, `SKILL.md` flow step 0), then sits still | Confirmed. The line says "Looked in so far", claims no place is finished, shows no total, and keeps moving with counters of finished searches and items read. Test with a followed-people run added. |
| M1: places and total do not match ("5 of 4"); "refresh calendar" and a thread check end as "1 of 4" | Total dropped; "Matching to projects" removed; three places only; short runs end "Finished" in words. |
| M2: how the page knows it is a mail check (word list drift, first step lost on reattach, Close the day has no marker) | From the run record the server already sends (`sweep`, `kind: "sweep"`, `started`); no copy of the word list; works on reattach, reload and Close the day. Replay from 0 for a mail check. No guarded change. |
| M3: plain labels turn every `sweep.py` command into "Staging what the sweep found"; Close the day's first step marks every place (`CloseDay.jsx` 316) | Confirmed. Classifier is an allow-list of whole labels; a script step marks nothing; Close the day uses the set and the same line. |
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

Not checked in this revision either: a real mail check, the connector's tool schemas (so whether Inbox and Sent Items can be told apart; the design no longer needs it), a browser, the suite.
