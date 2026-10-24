# #339 Lighter runs, part A: a purpose-built run per request kind (build plan)

Status: plan only. Review tier Full. Everything that touches the run engine is guarded; it goes to Jarvis as a diff, not as a commit.

## What exists
- `panel_sweep()` (BL-309) already recognises a typed sweep by words; `Run._start` then uses policy "sweep" (own tools, own prompt, guard mode "sweep"). It still runs with `kind="ask"` (chat history, home-folder `--add-dir` via `reach_dirs()`, the full Microsoft 365 tool list loaded) and `launch_context` loads the vault's CLAUDE.md and auto-memory.
- Purpose-built kinds already exist for buttons: "calendar" (#265, `calendar_refresh.build_prompt`), "process" (#264), "reextract" (#283), "search" (#7), tool-less kinds (#126). #327 B (fresh session, `fresh_session`/`fresh_plan`) is in.
- A typed "refresh calendar" is recognised by `PANEL_SWEEP_WORDS` but runs as the heavy sweep, not as the "calendar" kind.

## Plan (steps, smallest first)
1. Request-kind table in `live_server.py`: `panel_kind(message, images, confirmed)` returns "sweep", "calendar", "process" (typed "process the <meeting>", later), "lookup" (later) or None. Words only, never the model; same exclusions as `panel_sweep` (image, confirmed, over 120 characters, another instruction). `panel_sweep` stays as the sweep branch.
2. Typed "refresh calendar" starts `Run(..., kind="calendar", ...)` with `calendar_refresh.build_prompt()` (its own two-tool allow list, `run_dirs` empty): about 33k start tokens instead of the sweep's.
3. Typed sweep: keep policy "sweep" and its prompt; drop the home-folder `--add-dir` (`run_dirs`: "sweep" only needs the vault and projects folder) and keep `ToolSearch` only for the Microsoft 365 reads. Measure with `usage_report.py --days 7` before and after.
4. Status question and simple lookup: route to the existing "search" kind (Read, Grep, Glob; no Bash, no MCP) when `panel_kind` returns "lookup" (question words, no action verbs); "Continue in ask creaite" stays a chat. Needs Alan's word list: not clearly specified, so held.
5. Budget gate, confirmation, guard modes, outside-content marks: unchanged. Each new kind keeps a `KIND_ARGS` entry (fail closed), a guard mode in `reach.py` only if it needs one (calendar and sweep already have theirs).

## Files
- `system/scripts/live_server.py` (guarded): `panel_kind`, `Run._start` routing, `run_dirs`, usage kind mapping `USAGE_KIND`.
- `system/scripts/calendar_refresh.py`: reuse only (precheck for a typed request).
- `system/scripts/reach.py`, `.claude/settings*`, `creaite-rules.md` (guarded): none expected; rules line to describe the routing goes as a diff.
- `dev/tests/test_lighter_runs_339.py` (new): word recognition table (each kind, near-misses fall to chat), no routing with image or confirmed, calendar kind has no add-dir and no Bash write outside drafts, sweep run has no home folder.
- Existing tests to keep green: test_panel_sweep, test_chat_and_sweep, test_run_usage, test_plain_words, test_no_real_names, test_ask_creaite_name.

## Targets (from the issue)
Typed sweep under 60k tokens and $1.50; plain ask under 150k start tokens (500k red line, with part B).

## Pinned tests (checked against the plan)
- `test_panel_sweep` test_2 pins a typed "refresh calendar" as a sweep (guard `--mode sweep`, the sweep's tools). Step 2 (route it to the "calendar" kind, guard mode "calendar") contradicts it. Not loosened: `dev/proposals/339/calendar-route.diff` is HELD until Alan decides; if he agrees, test_2 changes in the same chain.
- `test_panel_sweep` test_1 pins a typed sweep as kind "ask" (chat history kept). Step 3 keeps that: only `--add-dir` changes. No pinned test names the sweep's --add-dir.
- Step 4 (status question and lookup to "search") is unchanged and still held for a word list.

## Patches (dev/proposals/339/, guarded, each `git apply --check` clean alone and together)
- `sweep-no-home.diff`: a sweep's --add-dir drops the home folder.
- `sweep-followed-rule.diff`: both sweep prompts (Close the day's and the typed one) end with the followed-people rule (`VIP_PRIVATE_RULE`).
- `calendar-route.diff` (HELD, above): no chat, 409 while a sweep runs (the existing busy check answers 409 for any other run), 400 if the calendar precheck fails.
