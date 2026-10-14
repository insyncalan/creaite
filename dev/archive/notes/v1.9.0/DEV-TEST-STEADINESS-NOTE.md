# dev-test-steadiness: tests that failed only under load

Team 2, item 6 (tooling). Branch `dev-test-steadiness`, from `origin/main` at `00ef391`. Only `dev/tests/` and
`dev/tools/run_tests.py` change. No product code changes.

## How it was measured

`run_tests.py` has a new mode for this: `--repeat N [--stress N]`. It runs N copies of each file named, `-j` at a time
(Chrome files also share the machine-wide Chrome cap), side by side with each other, with **no re-run alone**. It
prints each copy's result, then the passes per file. `--stress N` keeps N processes busy on the processor meanwhile,
so a fast laptop slows down to something like a shared CI runner.

- **Load:** `CREAITE_CHROME_CAP=4 python3.14 dev/tools/run_tests.py --repeat 5 -j 4 <the six files>`, so each file runs
  5 times beside 3 others. The machine was already busy (load average about 20 on 12 cores, from two other agents'
  Chrome runs).
- **Stress:** the same command with `--stress 8` added.
- **Before** runs on a clean export of `origin/main` (`git archive`, with the new `run_tests.py` copied in). **After**
  runs on this branch.

The CI logs give the test names but not the tracebacks, because a file that passes alone isn't printed. Where the
race reproduced here, the cause below is confirmed. Where it didn't, the cause comes from reading the code: the test
now waits for the condition it needs, and the note says so.

## Results (passes out of 5 per file, under load)

| File | Before, load | Before, stress | After, load | After, stress |
|---|---|---|---|---|
| test_cell_edit | 5/5 | 5/5 | 5/5 | 5/5 |
| test_dashboard_milestones | **4/5** | **2/5** | 5/5 | 5/5 |
| test_review_triage | 5/5 | 5/5 | 5/5 | 5/5 |
| test_debug_log_wiring | 5/5 | 5/5 | 5/5 | 5/5 |
| test_clear_day | 5/5 | **4/5** | 5/5 | 5/5 |
| test_dashboard_editing | 5/5 | 5/5 | 5/5 | 5/5 |

The before failures were:
- milestones: `setUpClass: the page didn't finish the scripted edits`, 4 times.
- clear day: `ClearDayPageSunday.test_undo_brings_them_back: can't click #snackU: it has no size (hidden?)`.

A heavier before run (`--repeat 4 --stress 16`) of cell_edit, review_triage and clear_day passed 12 of 12. Those
three files fail on Actions and not on this Mac.

Extras converted to the same harness: test_meetings and test_people_dashboard passed 5/5 before and 5/5 after with `--stress 8`. Neither reproduced here; on Actions, test_meetings failed 5 times today (3 passed alone, 2 did not) and test_people_dashboard once, all in setUpClass with the same "didn't finish" message.

## Each file: the race and the fix

### test_dashboard_milestones (setUpClass), and the same harness in test_dashboard_editing, test_people_dashboard and test_meetings
**Race (confirmed here):** these tests ran a scripted page with
`chrome --headless --virtual-time-budget=N --dump-dom`. Under virtual time, the page's clock jumps ahead whenever the
renderer is idle. That includes the times the page is waiting for work done elsewhere in real time: a FileReader, a
Blob stream, a stub's `Response`, or the live server running the stand-in `claude` (test_meetings). Under load that
work was slower, so the budget ran out first, and Chrome dumped the page without `<pre id="result">`.

**Fix:** the new `dev/tests/page_result.py` opens the page with `dev/tools/cdp.py` in real time. It waits for the
result element itself, for up to 120 s, and returns its text, so there are no HTML entities to undo. It keeps the old
800×600 window and doesn't reduce motion. The script's own `await wait(n)` calls are now real waits, which only gives
async work more time. The page's script is unchanged, except in two cases where virtual time had been hiding a
fixed wait (next two sections).

### test_dashboard_editing (new chat and history)
**Race:** the History step clicked a chat, then waited a fixed 200 ms and put the real `fetch` back. The reopened chat
was read with `.textContent`. The page adds the "Edit and send again" button (`.msgedit`) a frame later
(`chDecorate`, from a MutationObserver through `requestAnimationFrame`). When that frame came first, the message read
"Close ABC-A-001Edit". In real time the frame always comes first, which reproduced it.

**Fix:** the step now waits until the reopened chat's session is `s-12` and its reply is shown. The messages are read
without their Copy and Edit buttons, as the attach step already did (BL-148). The attach step's fixed 300 ms wait is
now a wait for the run's end (finished badge, acknowledged, indicator off). The expected values don't change.

### test_debug_log_wiring (LiveServerLog: a request is logged…, a failed apply logs its reason…)
**Race:** `live_server.py` writes a request's debug-log line in a `finally` after the handler has sent the reply, so
that the time it records includes sending the reply. The test read the log the moment the reply arrived. Under load,
the read came before the write. (The `DIAG.loaded` problem in the brief was already fixed on main, in `c0e04e2`.)

**Fix:** `Server.wait_for(pattern, count)` polls the log, for up to 15 s, until the line is there. The request test
waits for its fs, health and both `/api/data` lines; the apply test waits for its apply line; the quick-capture test
waits for all four requests' lines. The "no canary" checks then run on a log that includes every request, which makes
them stronger. A streamed reply logs `-` as its status, and the pattern allows for that. The server's start-up wait is
also 30 s now, not 6 s, and fails clearly if the server exits.

### test_clear_day (ClearDayPage…: clear day removes…, undo brings them back)
**Race (confirmed here):** `mtgClear` re-renders through `reloadData()`, which removes the day's button, before it
shows its "Cleared n meetings" message with Undo. The test went on as soon as the button went, so it sometimes read a
blank message or clicked an Undo that wasn't there yet.

**Fix:** `clear()` clears the message, clicks, then waits for "Cleared …" (the last thing `mtgClear` does) and for the
button to go. Every Clear click in the file uses it: day, ×, and "Clear anyway".

### test_review_triage (auto-advance keys and its setting)
**Race (from the code; not reproduced here):** with auto-apply on, a decision is applied 600 ms later (`applySoon`),
and the apply ends with `reloadData()`. The test went straight from Reject to Shift+J and ⌘A. When the apply's reload
landed during those keys, it put back the selection it had saved when it began (see product note 1), and the
`RHL.size` checks failed. The Undo wait was 10 s, and an apply on a loaded runner can take longer.

**Fix:** after Reject, the test waits for "Applied 1 decision" and then for the page to settle (`PULSE.reloads===0`,
no stream flush queued, no pulse in flight). The Undo wait is 30 s. After ⌘Z, the test also settles. What the test
checks doesn't change.

### test_cell_edit (status and due-date edits)
**Race (from the code; not reproduced here, even at 16 spinning processes):** `saved()` took *any* message as the
save's own, then slept a fixed 0.5 s, and a step could click a cell while the page was still redrawing it. A live
update reload (`renderWork` sets `shared.CE=null`) that lands while a cell's calendar is open drops the edit (product
note 2). The usual sign is a 30 s timeout or the wrong value in the database.

**Fix:**
- `saved(expect)` waits for the save's own message ("saved and applied", or a refusal), and for the Undo, "Undone".
  On a timeout it reports what the page actually said.
- `settle()` waits for no reload in flight, no stream flush queued, no pulse in flight and no cell editor open.
- `ready(id, f)` settles, then waits for the cell's ▾ before it is clicked.
- The Undo in the message must be showing before it is clicked.
- The assertions don't change.

### Shared: live_browser.LiveBrowserCase.start_server
It waited 10 s for `/health` and then carried on **silently**, so a slow start showed up later as an unrelated
timeout. It now waits up to 30 s and raises if the server exits or never answers.

## Product bugs for Team 1 (not fixed here)

1. **A reload overwrites a selection made while it was in flight.** `reloadData()` (src/core/server.js) records Review's
   highlighted keys and cursor *before* it awaits `/api/data`. It then clears `RHL` and restores those keys.
   Anything selected during the fetch (Shift+J, ⌘A, a click) is lost. Auto-apply makes this likely: every decision
   is followed 600 ms later by an apply and its reload. Fix: take the keys after the fetch, or merge the two sets.
2. **A live update can close an open Work cell editor.** `pulseEditing()` counts a focused input or select, an open
   dialog and the panel, but not `shared.CE` or an open `.cal`. When a cell's calendar is open, focus is on the
   calendar button, so a pulse or stream reload runs `renderWork()`, which sets `shared.CE=null`. The date then
   chosen is not saved. Fix: count `shared.CE` (and `.cal`) as editing in `pulseEditing`.

Not bugs: the server logs a request's line after the reply on purpose (the time includes sending it), and Clear day's
row going before its message is harmless to a person.

## Still flaky on Actions, not covered here

The others `--flaky` lists from today's runs: test_drafts_update, test_activity_item_links, test_ask_queue,
test_activity_undo, test_activity_search, test_work_filters_live, test_peek_fixes, test_live_updates and
test_chat_and_sweep. The cell_edit and review_triage fixes are from the code alone. Two Actions runs will show
whether they hold.

`python3.14 dev/tools/check.py`: check: OK.
