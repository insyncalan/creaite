# Run usage monitor (#197): the guarded part, for your yes or no

**Read this first: one item is outside what Alan asked for.** The brief asked for two hooks in `live_server.py`. The proposal also contains a one-line change to `reach.py` (`reach-197.diff`), a guarded file, which was not in the brief. It is only there so the existing test `test_record_commands` passes once `usage_report.py` exists. It is its own yes or no (item 3 below); say no and everything else still works, but that test will fail until the line or an equivalent is added.

Proposal only. Nothing here is applied. The plain code (`usage_log.py`, `usage_report.py`, `paths.RUN_USAGE`) is on branch `run-usage-plain`; these diffs go on top of it.

## What is measured

One line per finished Claude run in `system/staging/run-usage.jsonl`: when, the kind of run (ask, sweep, generate, prep, check, load, draft, vip), a fixed label (the engine's own kind, or the draft's kind such as `update`), the model, seconds, turns, input, output and cache tokens, the start load (what the run read in before doing anything), dollars, and whether it was stopped. **Counts only:** never the text of a prompt, a reply, a name, a subject or a path. Nothing leaves the laptop. Nothing is written in the development repository.

## Where it is kept

`system/staging/run-usage.jsonl`, kept for good (about 200 bytes a run). It goes into the daily backup zip with the rest of `system/staging/` already, so `backup.py` needs **no change**. `usage_report.py --days 7` sums it by day and kind.

## What changes (four diffs)

| File | Change |
|---|---|
| `live_server-197.diff` | The run engine: `Run.read` notes the model (system init event) and the start load (first assistant event) via a new `Run._usage_seen`; `Run._on_result` keeps the result event; `Run._done` writes the line via a new `Run._usage_record`, so finished, failed and stopped runs all record. The VIP check: `vip_check` keeps the `claude -p` reply and calls a new `vip_usage` after the call (a timeout records as stopped). New helpers `usage_kind` and `run_usage`. Every hook is wrapped: a fault is swallowed and the run carries on unchanged. |
| `reach-197.diff` | One line: `usage_report.py` classified as read only in `reach.SCRIPT_COMMANDS`. Without it `test_record_commands` fails on `run-usage-plain` today. |
| `creaite-rules-197.diff` | Folder map (`run-usage.jsonl`, `usage_log.py`, `usage_report.py`) and Retention (kept for good, counts only). |
| `tests-197.diff` | New `dev/tests/test_run_usage_hooks.py`: 10 tests. Without the hooks 8 fail; with them all pass. The 2 that pass both ways are the safety ones (a monitor fault never changes the run; nothing in the dev repo). |

## What could go wrong, and the way back

- **A run behaves differently.** Unlikely: the hooks only read events and append a line, inside try/except. Checked: the pinned Run.read test and the 76 VIP tests pass unchanged. Way back: revert the one commit.
- **A stopped run under-counts.** A run killed before its result event has no totals from Claude Code, so its line holds the start load and seconds but zero output and cost. Accepted for v2.1.1; could sum the per-step usage later.
- **The file grows.** About 200 bytes a run; a heavy month is well under 1 MB. Way back: delete the file; nothing reads it but the report.
- **Text leaks into the file.** The line is built from numbers and fixed words only; a test checks that no reply, message or path text appears.

## YES / NO

1. **Run engine hook** (`Run.read`, `_on_result`, `_done`). Risk: low. Recommendation: **yes**.
2. **VIP check hook** (`vip_check`, one call after the `claude -p` call; still one launch). Risk: low. Recommendation: **yes**.
3. **`reach.py` line for `usage_report.py` (read only).** Risk: very low; needed for the existing classification test. Recommendation: **yes**.
4. **`creaite-rules.md` folder map and Retention.** Risk: none (documentation). Recommendation: **yes**.
5. **`backup.py` change.** Not needed: staging is already in the zip. Recommendation: **no change**.
6. **Tests (`test_run_usage_hooks.py`).** Risk: none. Recommendation: **yes**.
