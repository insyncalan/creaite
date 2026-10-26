# #370 plan: production log review 19-25 Oct 2026 (2.6.10)

Planning only. Base: origin/main a62fbb0a (2.6.8 + docs). Compared with the 2.6.9 candidate v269-main eb32046b (G1 #382, G2 #371, bundle). Line numbers are origin/main unless marked. Nothing was run against the live vault; findings 4 to 7 causes marked "hypothesis" need the live logs.

## 1. Open or fixed

| # | Finding | State | Where |
|---|---------|-------|-------|
| 1 | Load fails 6 of 10, 0 steps | **Mostly fixed.** 2.6.8: #365 narrow prompt, #371 start logging. 2.6.9 candidate: #382 (check/load start context-less, bounded three-search day window, `init_summary`, ToolSearch count). **Still open:** no automatic retry on a 0-step failure (grep of eb32046b finds none); `transcripts.py:595-604` (`no_event`) only says "Press Process to try again". Wording is already honest (three cases), so the old "couldn't be read" is gone. | live_server.py, transcripts.py |
| 2 | Missed scheduled sweep (21-10, 15-10) | **Open.** | see A |
| 3 | Guard refusals (~90 of 124 WARNs) | **Open.** By design the guard is correct; the prompts are what is wrong. | see B |
| 4 | `review: "…" is not valid JSON (promise:0)` | **Open**, and mis-described: it is a page-side error, not review.py. | see C |
| 5 | `POST /api/settings/catalogue` 500 and `GET /api/events` 403 at first load | **Part fixed.** 2.6.8 gate: first load served from built data (calendar lock backdated), so the page-build race is closed. The 403 is the stale-token path, by design (`authorised`, live_server.py:1185-1196, BL-269). The 500 cause is unknown. | see D |
| 6 | Events 403 each morning; chat 404 | **403 explained, 404 fixed in code.** 404 is logged at info (`log_request`, live_server.py:9161, BL-330); ask.js:577 already says "Couldn't open that chat" or clears quietly. | D |
| 7 | ConnectionReset/BrokenPipe tracebacks; DEBUG 81% | **Code fixed, residue left.** `CLIENT_LEFT` (live_server.py:242, 1243, 1254, 1309, 9115, 9307) covers handlers; 7 tracebacks remain, most likely from socketserver's own `handle_error` (no override found) in a thread outside those `try`s. DEBUG share is the vault's `logging.level` (default `info`, settings.json:257) set to debug, plus GETs and `/api/here` logged at debug (`QUIET_ROUTES` 8978, `log_request` 9163-9167). | D |
| 8 | Smaller (title in "not approved" log, stale lock, one 2-step check fail) | Partly. review.py:1409-1419 logs file name, item number and a `rule()`d reason, no title; the title in the log is probably from the route that echoes `review.py:1350` (`d["msg"]`). Unverified. | C |

2.6.10 scope: A, B, C, D.

## 2. Plans

### A. Missed scheduled sweep (rec 2)
**Root cause.** The 07:00 sweep is the Claude desktop app's scheduled task (`system/config/schedules.md`), not creaite code. When it cannot see the connector it calls `sweep.py fail` (sweep.py:2806-2811), which writes only a run-log line and the debug log; `last-sweep.txt` is left alone by design. So nothing structured records "tried and failed". Today already has a "Mail and Teams not checked yet today" banner (`sweep_due_info`, build_dashboard.py:1673-1682; today.js:472-477), but it fires for "not yet", is dismissible, and cannot tell "didn't run" from "hasn't been tried". Health (health.py:79 area) never reads the run log. The session-start rule (session.py:225) catches it only when Alan opens Claude Code. creaite has no retry: the live server's only sweep starter is Close the day's `start_catchup` (live_server.py:7306-7321).
**Change.**
1. `sweep.py fail` also writes `system/staging/sweep-failed.json` `{at, retry_at|null, day}`; `sweep.py done` clears it. Counts and times only. (ordinary: sweep.py)
2. `build_dashboard.sweep_due_info` adds `failed: {at, retry}`; today.js shows Alan's approved wording (issue comment 26-10): "Today's mail and Teams check didn't run. [Check now]", not dismissible while failed; `health.py` adds a row "A mail and Teams check didn't run" with the approved detail line and a Check now Fix-it (new id in `health_fixes.py`, which is not guarded). Clears when `last-sweep.txt` passes the day's `due_from`. (ordinary)
3. Retry. DECIDED (Jarvis): no automatic retry; R1 only. Option R1: none in code; the banner plus Check now button (`/api/day/catchup`, existing) is the retry. Option R2: live server starts `start_catchup` once, 5 minutes after a recorded failure, only if the app is open (guarded, live_server.py, ~25 lines in the catch-up waiter near 7339). R2 starts an unattended M365 read, so it needs Alan's yes.
**Cannot test here:** the real connector-missing failure; a scheduled run. Tests simulate `sweep.py fail` and assert the state file, banner flag and Health row.

### B. Guard refusals (rec 3)
**Root cause.** `reach.bash_problem` (reach.py:854-870) allows exactly one creaite script per Bash call, by design, so `grep`, `date`, `tail`, and any script not in the run kind's allow list are refused; so is `Read` outside the kind's files. The model reaches for them because the kind prompts (live_server.py:2280-2319, `KIND_PROMPTS` for process and calendar; check/load at 2491) never say what exists or what today is, and the process/calendar runs load the cx-sweep and cx-minutes skills, whose text tells the model to search. Refused `propose.py people map` in Process, `minutes.py stage` outside the spec, `search.py` and `backup.py` all point at skill steps that the kind may not run.
**Change.**
1. Count first: log refusals per run kind and tool class (a short summary line at run end; log text already carries kind, never arguments) and show "refused tool calls, 7 days" in doctor beside `record_refusals` (doctor.py:699-702). doctor.py is ordinary; the run-end line is live_server.py (guarded).
2. Prompts: add to process, calendar, sweep, check, load a fixed paragraph: today's date (`{today}` filled by the server), the exact commands allowed, "never grep, tail, date or read a file not named in the message". Guarded (live_server.py).
3. Skills: a "Run limits" note in `.claude/skills/cx-sweep` and `cx-minutes` for headless runs (ordinary; `.claude/skills` is not on the guarded list, only settings are).
4. Do not widen any allow list or the hook. Success measure: refused calls per calendar refresh down from 2 to 0 on the live vault; calendar refresh median 182 s down.
**Live only:** the refusal rate and the time saved. Test: a unit test builds each kind's prompt and asserts it contains the date and no phrase naming a tool the kind lacks.

### C. Traceable errors (rec 4)
**Root cause (verified).** `"…" is not valid JSON` is V8's `JSON.parse` message for a non-string; `(promise:0)` is the `unhandledrejection` hook (server.js:560 `diagHook(reason.message, "promise", 0)`), which posts no stack; the server then logs `view: message (source:line)` (live_server.py:9201). The text is `"…"` because `redact` strips quoted text. So it is the page, view "review", an un-caught `JSON.parse(await shared.VW.read(path))`-style call without `try` (candidates: settings.js:755, panel.js:714; a parsed object passed twice). It cannot carry an item id because the page never had one in scope.
**Change.** (all ordinary, templates/dashboard/src, then rebuild dashboard.html)
1. `diagHook` takes `e.reason.stack`: send the top frame's function name and line (no path, no text) as `source:line`; the unhandled-rejection path logs `promise` plus that frame. Server (`browser_error`) needs no change.
2. Fix the cause once the frame is known; until then wrap the two candidate parses in `try`. Test: a jsdom/headless test that rejects with a JSON.parse error and checks the posted body has a frame.
3. Keep titles out of the log: audit the route that echoes `review.py:1350` messages to the debug log (live_server.py:1450 is the only reader found); log the item number only. If that route is in live_server.py, it goes in the guarded patch.

### D. First load, logging, residue (recs 5, 6)
1. **catalogue 500 (hypothesis).** `settings_catalogue.catalogue()` (settings_catalogue.py:627) reads settings.json and `last_changes()` (the log); a 500 one second before the first events call fits a read of settings.json or settings-log.jsonl while the server's start-up saves were mid-write, or `import settings_catalogue` raised. First step: read `live-server.log` / the `log_fault` line (class and frame, #253) for 20-10 09:20:32 in the live vault. Fix candidates: catch `OSError/ValueError` in `catalogue()` and return 503 plus `Retry-After` (route, guarded) with the page retrying once (ordinary). Do not build the fix before the class is known.
2. **events 403 (by design).** A tab left open across a server restart holds the old token. Fix on the page side (ordinary): on a 403 with `stale: true` from `/api/events`, reload once instead of the silent retry loop, and say the existing `STALE_PAGE` text if the reload does not clear it. Check what `evOpen` (server.js ~500-516) does now.
3. **Tracebacks.** Override `handle_error` on the server class to swallow `CLIENT_LEFT` at info, as `log_fault` does (live_server.py:9113-9117). Guarded, ~10 lines. Test: raise each in a fake request.
4. **Log volume.** Not a code bug: the vault runs `logging.level: debug`. Ordinary: Health notes "debug logging has been on for more than 7 days" (health.py, a Settings fix to info); optionally log `/api/here` and `/health` only at a level below debug (`QUIET_ROUTES`, guarded, skip unless Alan wants it).

## 3. Guarded and ordinary split

| Guarded (patch files only) | Ordinary |
|---|---|
| live_server.py: prompt paragraph (B2), refusal summary line (B1), catalogue 503 (D1), `handle_error` (D3) | sweep.py, build_dashboard.py, health.py, health_fixes.py, doctor.py, today.js, server.js, settings.js, panel.js, Essentials/health components, dashboard.html (built), `.claude/skills/cx-*`, transcripts.py, tests, creaite-reference.md |

Guarded list in this release: live_server.py only (no reach.py, permissions.py or settings change is needed; the hook and allow lists stay as they are).

## 4. Slices and tests

**Agent 1, sweep notice (A), ordinary only, 1.0 to 1.5 days.** sweep.py, build_dashboard.py, health.py, health_fixes.py, today.js, Health component. Owns: `test_sweep_failed_370` (fail/done state file, banner flag, Health row, wording exact, no names or paths), a plain-words/no-vendor-terms check on the new strings (existing wording tests), golden for `sweep_due`.
**Agent 2, page errors and first load (C, D2, D4 note), ordinary, 1.0 to 1.5 days.** server.js, settings.js, panel.js, health.py debug-level row. Owns: `test_page_errors_370` (frame sent, no text), `test_stale_events_370`, `test_log_level_health_370`; rebuilds dashboard.html. (Agents 1 and 2 both touch health.py and today.js; agree order: agent 1 first.)
**Agent 3, guarded patch (B, D1, D3), 1.5 to 2.5 days.** Produces `GUARDED-2.6.10.patch` against live_server.py only, plus B3 skill notes and doctor row (ordinary). Owns: `test_job_prompts_370` (date and allowed list in each prompt; no tool the kind lacks), `test_handle_error_370`, `test_catalogue_503_370`, a refusals-per-run counter test.
Total 3.5 to 5.5 agent-days. Gate: existing `test_job_prompts_365`, `test_job_tools_365`, the 2.6.8 first-load test and the guarded-chain pin test must stay green; the patch must apply on v269-main's live_server.py, not origin/main (it carries the #371/#382 hunks).

## 5. Risks
- Live_server.py is touched by 2.6.9's chain: rebase the 2.6.10 patch on the released 2.6.9, never before.
- Prompt changes can make the model skip a legitimate step; each kind needs one live run (calendar refresh, Process, check, load) after install.
- (R2, not built) would make creaite start an M365 read without Alan pressing anything; same rules as Close the day's catch-up but unattended.
- The stale-token reload could loop if the new server issues another token; reload at most once per page.
- Wording: the notice must be exactly the approved text; any change returns to Alan.

## 6. Open questions
1. Alan: should creaite retry a missed check by itself (R2), or is the notice plus Check now enough (R1, recommended)?
3. Jarvis: Health row for debug logging left on more than 7 days: yes or no (it is Alan's setting).

## 6a. Decisions recorded (Jarvis)
- No automatic retry of a missed check: the notice plus Check now is enough (R1; R2 dropped).
- YES to the Health row for debug logging left on: informs only, changes no setting, ordinary code.
- Slices 1 and 2 are ordinary and can start after the 2.6.9 verdicts.
- Slice 3 (live_server.py only) is a GUARDED diff: build it rebased on RELEASED 2.6.9, independent review by Cap (never the builder), then to Alan as its own diff with sha256. Not in a release without his words.

## 7. Needs the live vault (one ask for Alan)
Alan can answer by pasting log lines (counts and error class only; no mail or Teams text):
1. The real connector-missing sweep failure: what `system/staging/run-log.txt` and the debug log show for a 07:00 scheduled sweep when the Microsoft 365 connector is missing (the `sweep FAILED` line and the lines around it).
2. The 20-10 09:20:32 `POST /api/settings/catalogue 500`: the debug-log lines around it and the `live-server.log` fault line (error class and frame).
3. Which `JSON.parse` threw (`promise:0`): the page console message for it with the failing route or URL, from the browser's developer console, if it recurs.
