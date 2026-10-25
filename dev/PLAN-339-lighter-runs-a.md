# #339 Lighter runs, part A: a purpose-built run per request kind (build plan)

Status: plan only. Review tier Full. Everything that touches the run engine is guarded; it goes to Jarvis as a diff, not as a commit.

## What exists
- `panel_sweep()` (BL-309) already recognises a typed sweep by words; `Run._start` then uses policy "sweep" (own tools, own prompt, guard mode "sweep"). It still runs with `kind="ask"` (chat history, home-folder `--add-dir` via `reach_dirs()`, the full Microsoft 365 tool list loaded) and `launch_context` loads the vault's CLAUDE.md and auto-memory.
- Purpose-built kinds already exist for buttons: "calendar" (#265, `calendar_refresh.build_prompt`), "process" (#264), "reextract" (#283), "search" (#7), tool-less kinds (#126). #327 B (fresh session, `fresh_session`/`fresh_plan`) is in.
- A typed "refresh calendar" is recognised by `PANEL_SWEEP_WORDS` but runs as the heavy sweep, not as the "calendar" kind.

## Decisions folded in (Jarvis, answers to Cap's H1 to H3 and M1 to M4, Cap's review of 01:52 on #339)
1. `panel_sweep` KEEPS "refresh calendar" in its words, so the budget gate (`budget_gate`) and the queue exemption stay as they are. `panel_kind` is added for routing only ("calendar", "sweep" or None, with panel_sweep's own exclusions: image, confirmed, over 120 characters, another instruction; a kind or mode in the request is never read). Call sites: `ask()` and `queue_start()` (the second one Cap found).
2. A typed calendar run is the button's own run: `Run(id, calendar_refresh.build_prompt(), None, None, None, kind="calendar", ...)`: no session, no chat, so nothing is carried (`carry_over`) and no outside-content mark is inherited. A run already going is the existing 409. A sweep running: 409 "A mail check is running; try again when it ends." A precheck failure (development repository, calendar source off): 400 with the precheck's own reason. In the queue it falls back to the old typed-sweep run.
3. It is recorded in chat history like any plain run (BL-326: the fixed label and the fixed closure line, in the day's "Runs creaite started" chat), so the page draws it normally. Page side (not guarded, in this build): `ask.js` `typedCalendar()` passes `plain` to `askStream`, so only steps, the closure and done are drawn, and the 409 and 400 sentences are said as they come. Nothing from an invite reaches chat history: the calendar run's prompt forbids quoting it, its reply is not recorded, and the closure line is counts only.
4. Re-baseline after #327 B (fresh session, already in) before judging the 260k to 352k figures. Dropping the home `--add-dir` is a security narrowing, not a token fix (Cap M1): what shrinks the load is the start context itself (CLAUDE.md and the rules, auto-memory, skills, the Microsoft 365 tool list). Part A promises the calendar run's small start (about 33k); the sweep's 60k target is measured, not promised.
5. Followed-people rule (BL-288, `VIP_PRIVATE_RULE`) added to both sweep prompts (Close the day's and the typed one): `sweep-followed-rule.diff`, one pin test per prompt kind.
6. Step 4 (status question and lookup to the "search" kind) is OUT of part A: held; needs Alan's word list and a security note (the search kind runs without the guard hook, #60). The plain-ask target (under 150k start tokens) belongs to part B (#327), not A.
7. Measuring: per run, `start_tokens` and `cost_usd` for label "chat", kind "sweep" (a typed sweep): `system/scripts/run usage_report.py --days 7 --label chat --kind sweep` (the new `--label` and `--kind` flags, counts only; the per-day table cannot show it, as tokens are cumulative over turns). Before and after.

## Plan (steps)
1. `panel_kind`, `calendar_run`, the `ask()` and `queue_start()` routes: `calendar-route.diff` (guarded). Typed "refresh calendar" starts the small calendar run.
2. Typed sweep: kind stays "ask" (chat history kept, pinned); `--add-dir` drops the home folder (`sweep-no-home.diff`, guarded). This also narrows Close the day's and the catch-up sweep (run_dirs is keyed on policy "sweep"), by design.
3. Both sweep prompts end with the followed-people rule (`sweep-followed-rule.diff`, guarded).
4. Page: `typedCalendar` and the two sentences in `ask.js`; `dashboard.html` rebuilt (not guarded, committed).
5. `usage_report.py --label/--kind` (not guarded, committed).

## Pinned tests the chain rewrites on purpose (`dev/proposals/339/tests-pins.diff`, applies after the live_server diffs)
- `test_panel_sweep` test_2 (lines 185-189): "refresh calendar" now runs `--mode calendar` with the fixed prompt, no add-dir, no resume; "sweep mail for ABC" still `--mode sweep`. Why: the route changes the kind.
- `test_calendar_refresh` test_5 (lines 577-593): the typed refresh is the calendar run (was "BL-309, unchanged"); the ordinary-message and model-supplied kind or mode checks above it are untouched and stay.
- `test_ai_budget_gate_334` lines 144-145: a typed "refresh calendar" must not be held (not 429); it either starts or stops at the calendar run's own checks (400 or 409; the test vault fails the precheck before a Run starts), so a 500 no longer passes. The exemption itself and the exact `if panel_sweep(...)` line pin (SKIP_ASK) are unchanged.
- `test_mail_check` `test_refresh_calendar_ends_with_nothing_new` (Chrome, found by the full run on the 2.6.6 base): the typed refresh no longer ends with the mail check's "Finished. Nothing new to review."; it is the calendar run and ends with its plain closure (renamed `test_refresh_calendar_is_the_calendar_run`).
- Checked and left alone (they stay green with the patches): `test_panel_sweep` line 83 (the recogniser: panel_sweep keeps the words), `test_calendar_refresh` line 284 (mode sweep's guard decisions: the mode still exists), `test_run_badge` line 108 (the page's label for the typed words: unchanged). With all patches and the pin diff applied temporarily, test_panel_sweep, test_calendar_refresh, test_ai_budget_gate_334, test_run_badge and test_run_tools_explicit pass; then reverted.

## Files
- Guarded patches, not applied: `calendar-route.diff`, `sweep-no-home.diff`, `sweep-followed-rule.diff` (all `system/scripts/live_server.py`), plus `tests-pins.diff` (three test files).
- Committed: `system/templates/dashboard/src/ask.js`, `system/templates/dashboard.html`, `system/scripts/usage_report.py`, `dev/tests/test_lighter_runs_339.py`.
- Tests to add when the chain lands (Cap): the calendar kind via /api/ask and via queue_start with args showing `--mode calendar`, exact tool list and no add-dir; 409 while a sweep runs; the precheck message; mutants for each routing line, the 409 guard, chat=None and the home removal. Today's structure tests read the patched text; the behavioural ones need the chain.

## For Alan (each needs his yes; HOW-WE-WORK.md:38)
1. Guard mode: a typed "refresh calendar" moves from mode `sweep` to mode `calendar` (narrower: two calendar reads, two input files, five sweep.py commands, no add-dir). `calendar-route.diff`.
2. Reading: every sweep run (typed, queued, Close the day's) loses the home folder from its readable places; the projects root stays. `sweep-no-home.diff`. Whether Claude Code's bare Read rule already allows reads outside --add-dir is not checked; if it does the saving is nominal.
3. Visible change: a typed refresh is drawn as a plain run (steps and closure) and kept in "Runs creaite started"; a sweep running reads "A mail check is running; try again when it ends." (409); a calendar that cannot be read shows its own reason (400). In the queue a typed refresh that cannot start falls back to the old typed-sweep run.
4. Rules wording: `creaite-rules.diff` (one sentence added to the ask creaite section). Wording is Alan's.
5. Followed-people rule on both sweep prompts: `sweep-followed-rule.diff` (decided; included for completeness).
Chain: add the chosen diffs to the 2.6.5 or 2.6.6 GUARDED chain file and recompute the pin in dev/tests/guarded_chain.py; land `tests-pins.diff` in the same step. Landing a subset is supported by `test_lighter_runs_339` (it decides per diff whether it has landed).

## Review findings (Cap 02:25 and 03:01)
Fixed here: H1 (landing decided per diff, pins skip when landed), N1 (globals.json), M3 (behaviour tests through the patched server: sweep --add-dir, prompt text, the 409 guard, chat=None, queue route, fixed prompt; mutants killed), M4 (rules diff), L1 (one plan), L4 (the budget pin no longer passes a 500). Left: L2 (calendar route catches only OSError; the prompt is fixed), L3 (a different sentence in the queue fallback, by decision), L5 (typed and button calendar runs both record as calendar/calendar), the full Chrome look at the page.
