# Run usage monitor (brief for Team Stark, for v2.1.1; supports #195)

Product Manager, 17-10-2026. Sonnet, size S, plain code plus one guarded hook (Jarvis to agree). Alan (17-10-2026): record what each Claude run costs so later decisions about memory and the rules file rest on numbers.

## What exists today (checked in `live_server.py` on main, 2.1.0)

- The run engine (`claude -p --output-format stream-json`, line 2226, kinds ask, sweep, generate, prep, check, load and the drafts) **ignores usage**: `_on_result` reads only `result` and `permission_denials`.
- The VIP check (`claude -p --output-format json`, line 3587) reads `total_cost_usd` and logs **dollars only** in the debug log (`vip_check_line`), which keeps seven days.
- Nothing records tokens, and nothing records the cost of the other kinds.

## What to record

One line per finished run, appended to `system/staging/run-usage.jsonl` (counts only, like the debug log's rule: no message, subject, name, path or text):

`{"at": ISO time, "kind": "ask|sweep|generate|prep|check|load|draft|vip", "label": the kind's own short label if it has one, "model": from the init event, "seconds": wall time, "turns": num_turns, "input": n, "output": n, "cache_read": n, "cache_create": n, "cost_usd": n, "start_tokens": n, "stopped": bool}`

- `start_tokens` is the first assistant event's input plus cache tokens: what the run **loaded before doing anything**, which is the number #195 needs (CLAUDE.md, the 53 KB rules file, memory, skill descriptions).
- Take the figures from the result event's `usage` and `total_cost_usd`; the VIP call reads them from its JSON reply. **Confirm the exact field names on a real run first** (this brief names them from Claude Code's output; the first test must print one result event).
- A run that is stopped or fails still records what it used.

## The report

`system/scripts/usage_report.py` (read only, plain code): per day and per kind, runs, total and average tokens, `start_tokens` (min, median, max), cost, and the share of input that was the start load. `python3 system/scripts/usage_report.py --days 7`. A one-line "This week: n runs, $x, start load about y tokens a run" in Settings › Diagnostics is optional and can be a later item.

## Rules

- **Retention:** keep for good (a line is about 200 bytes); add the file to `creaite-rules.md`'s folder map and Retention (an update replaces that file) and to the backup zip's contents.
- **Privacy:** never the text of anything; nothing leaves the laptop; not shown to anyone but Alan.
- **Never in the development repository** (`.creaite-dev`): the monitor does not run there, as with the VIP check.
- **One writer for this file:** the live server appends; nothing else writes it.

## Tests

`test_run_usage_line_has_counts_only`, `test_run_usage_appended_for_each_kind`, `test_stopped_run_still_recorded`, `test_vip_cost_and_tokens_recorded`, `test_no_text_in_the_file`, `test_report_sums_by_day_and_kind`, `test_not_written_in_the_dev_repo`.

## Done when

- A real ask creaite run, a sweep and a VIP check each add one line with tokens and cost.
- The report prints a week's totals and the start-load figures.
- Guarded change (`live_server.py`, two hooks: the result handler and the VIP call) agreed with Jarvis; no other guarded file touched.
- Real-names test and `check.py` pass.

## Why now

#195 asks whether memory or the rules file is the cost. Without these lines the answer is a guess (my estimate: the 53 KB rules file is about 13,000 tokens on every run). A week of lines settles it and also shows the cost of each kind of run, which #87 (half the model cost per shipped item) needs.
