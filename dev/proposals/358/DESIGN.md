# #358 Say what the mail check is doing: design note

Written 24-10-2026 from origin/main (2.6.4, 5735c141). Design only, no product code. Builds on Cap's scope comment on #358.

## 1. Today and the ask

**Today.** Alan types "sweep" or "check my mail", or presses Check now on Today. Both open the chat and send the words to ask creaite. The chat shows three dots, a random quip ("Percolating coffee") and a hidden "Working". Each finished tool call adds a line to a folded "n steps" list. The Today strip and the run badge are hidden while the chat is open. So Alan sees a joke and a growing number, and nothing says what is being read.

**The issue wants** true, counted text while the check runs ("Reading Outlook ..."), and at the end "Found 7, 4 need a project". The dots stay.

## 2. The engine count

- **One mail check has no fixed number of steps.** It is a chat run that follows the cx-sweep skill: look for each project's signals in mail, Teams and the calendar, drop what the ignore rules match, read threads, write the findings, then save them. The number of tool calls grows with the number of projects and threads. Nothing in the engine knows the total in advance.
- **Where the count comes from.** `live_server.py`, class `Run`: `_on_assistant` (about 2832) remembers each tool call with a label (`describe_tool` for a chat run, `plain_step` for a run creaite starts itself, such as Close the day); `_on_tool_result` (about 2894) emits `emit("step", label=...)` only when the call finished without error. The first event of a typed check is the fixed step "Sweeping (stages proposals only)" (2357). `run-usage.jsonl` only gets one line per run after it ends (turns and tokens), so it cannot feed a live count.
- **How the page reads it.** `ask.js` `askStream` (791) draws every `step` event into `stepGroup` (775), which counts its own list items. `/api/events` carries kinds and sequence numbers, not labels. So the only live signal is: one label per finished call, in order, past tense. A call in flight is never reported. A replay of a finished run sends the same events again.
- **Answer.** The engine emits one step event per finished tool call and no total. "3 of 5 sources" cannot be said truthfully: Inbox and Sent Items use the same tool (identical labels), and the skill searches by project signal, not source by source. What can be said is "Done so far: Outlook mail, Teams chats (2 of 4 places)", where the total is the places Settings has switched on.

## 3. Files, and whether any is guarded

Page-only (all unguarded):

| File | Change |
|---|---|
| `system/templates/dashboard/src/core/mailCheck.js` (new) | Pure classifier: a label becomes a place (Outlook mail, Teams chats, Teams channels, Calendar, Matching to projects) or nothing. Returns a set. |
| `components/closeday/CloseDay.jsx` | `cdSourceOf` uses the classifier. |
| `src/ask.js` | In `askStream`: while a mail check is live, a truthful line replaces the quip; end count; `rbGuess` learns "check my mail" and "check mail". |
| `src/review.js` / `core/irFold.js` | Read only: the "needs a project" rule (`!r.p`). |
| `system/templates/dashboard.html` | Rebuilt from source (the BUILT check). |
| `dev/tests/` | New tests (section 5); help text. |

**Guarded and not touched:** `live_server.py` and every other file in your list.

**Cap's claim confirmed: no guarded file is needed.** The exact reason: everything the new text needs (a label per finished call, in order, plus the Review rows after the run) already reaches the page. The new line is built from fixed phrases and numbers in the page's own code. The only reason to touch `live_server.py` would be a true "n of 5" (a `phase` key on each step event and a progress event from the save step's result). That would also change the pinned event list (`test_run_read_pinned.py`, `dev/tests/pinned/run_read/`) and still could not tell Inbox from Sent Items. Not recommended.

One correction to the brief: `draft_delivery.py` is also in the code's guarded list (`dev/tests/guarded_chain.py`, `GUARDED`). It is not touched either.

Two words stay as they are because they sit in guarded text: "Sweeping (stages proposals only)" and the catch-up ask. They appear only in the folded steps list and the catch-up line.

## 4. Diff shape if a guarded diff were needed

Not needed. For the record, the optional route would be one hunk in `Run._on_assistant`/`_on_tool_result` area of `live_server.py` (a `phase` field, about 15 lines) and one for a progress event (about 15 lines), applied after the 2.6.4 chain that main already carries (`GUARDED-2.6.4.chain`), as its own small chain with a new marker, pin and Alan's approval of the exact diff, plus re-recorded pins and a Full review. Roughly one more agent-day.

## 5. Tests, tier, estimate, risks

**Unit (Node):** every label kind through the classifier: chat labels, plain labels, `ToolSearch` (nothing), calendar, a Bash label that carries a mail subject (must be nothing), the followed-people command (nothing). Mutants: a classifier that scans free text (a subject containing "mail" must fail the test); one that keeps "highest index" instead of a set (Teams before mail must fail); a count that includes an off source.

**Browser (1400 and 900 px),** using the stand-in `claude` of `test_run_badge.py` with a fake stream of real labels: the line grows place by place; no subject or sender anywhere (line, badge, live region); ends with "Found N new, K need a project"; survives a reattach and a replay; a stopped run says "Stopped" with the places so far; the badge shows the same text with the chat closed. Mutants: show `ev.label`; draw a percentage; count rows that were already there. Also: `test_ask_quips_dots.py` and the Close the day tests still pass; no VIP word in any new string.

**Review tier:** Light (page only). Full only for the guarded route.

**Estimate:** about 1.5 builder-days. A = classifier and Close the day 0.5, B = the line, badge, end count and accessibility 0.75, C = tests and help text 0.25.

**Risks.**
- Privacy: build text only from fixed phrases and numbers, never from a label. The folded steps list can already hold a subject (80 characters of a command); the new line must not copy it.
- The followed-people step must not be counted, named or shown.
- A false progress bar: past tense, a set, no percentage, "Finished" in words at the end. A place switched off in Settings is not in the total.
- Accessibility: the quip is hidden from readers, so announce the new line politely only when the set of places changes, not every 500 ms.
- Replay: rebuild the line from events; an ended run shows only the final count.
- Visible change: needs Alan's before-and-after sign-off.

## 6. Open questions for Alan

1. Drop "3 of 5 sources" for "Done so far: ..." in past tense? (Recommended: yes.)
2. Replace the quip with the true line for a mail check only, or add a second line? (Recommended: replace; keep quips for other runs.)
3. Release: 2.6.5 as planned, page-only (the issue body says 2.6.6). A true "n of 5" would be its own small release with a guarded diff.
4. "Found N" counts new Review rows since the run started (recommended), or everything waiting?
