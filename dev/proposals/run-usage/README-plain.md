# Run usage monitor (#197): the guarded part, for your yes or no

**Read this first: one item is outside what Alan asked for.** The brief asked for two hooks in `live_server.py`. The proposal also contains a one-line change to `reach.py` (`reach-197.diff`), a guarded file, which was not in the brief. It is only there so the existing test `test_record_commands` passes once `usage_report.py` exists. It is its own yes or no (item 4 below); say no and everything else still works, but that test will fail until the line or an equivalent is added.

**This widens the hook.** Before, the run engine's hook looked only at the first message of a run (to note what it loaded at the start). Now it looks at every message in a run, to note which skill was used: the skill's name only (for example `cx-review`), never what was asked of it. Alan's reason: retire the cx-* skills nobody uses, with data rather than a guess. It is its own yes or no (item 2 below).

Proposal only. Nothing here is applied. The plain code (`usage_log.py` with `skills_of`, `usage_report.py`, `paths.RUN_USAGE`) is on branch `run-usage-plain-r2`; these diffs go on top of it.

## What is measured

One line per finished Claude run in `system/staging/run-usage.jsonl`: when, the kind of run (ask, sweep, generate, prep, check, load, draft, vip), a fixed label (the engine's own kind, or the draft's kind such as `update`), the model, seconds, turns, input, output and cache tokens, the start load (what the run read in before doing anything), dollars, whether it was stopped, and the names of the skills it called (once each, in order; `[]` when none; the VIP check has no tools, so always `[]`). **Counts and names only:** never the text of a prompt, a reply, a skill's arguments, a person's name, a subject or a path. Nothing leaves the laptop. Nothing is written in the development repository.

## Where it is kept

`system/staging/run-usage.jsonl`, kept for good (about 200 bytes a run). It goes into the daily backup zip with the rest of `system/staging/` already, so `backup.py` needs **no change**. `usage_report.py --days 7` sums it by day and kind and shows the days since each skill ran.

## What changes (four diffs)

| File | Change |
|---|---|
| `live_server-197.diff` | The run engine: `Run.read` passes each event to a new `Run._usage_seen`, which notes the model (system init event), the start load (first assistant event) and, from every assistant event, the skill names (`usage_log.skills_of`, kept once each in order); `Run._on_result` keeps the result event; `Run._done` writes the line via a new `Run._usage_record`, so finished, failed and stopped runs all record. The VIP check: `vip_check` keeps the `claude -p` reply and calls a new `vip_usage` after the call (a timeout records as stopped; no skills). New helpers `usage_kind` and `run_usage`. Every part is wrapped on its own: a fault is swallowed and the run carries on unchanged. |
| `reach-197.diff` | One line: `usage_report.py` classified as read only in `reach.SCRIPT_COMMANDS`. Without it `test_record_commands` fails today. |
| `creaite-rules-197.diff` | Folder map (`run-usage.jsonl` with its skill names, `usage_log.py`, `usage_report.py`) and Retention (kept for good, counts only). |
| `tests-197.diff` | New `dev/tests/test_run_usage_hooks.py`: 14 tests. Without the hooks 12 fail; with them all pass. The 2 that pass both ways are safety checks (a monitor fault never changes the run; nothing in the dev repo); the skills-fault and malformed-event tests also check that a line is still written, so they fail without the hooks. |

## What could go wrong, and the way back

- **A run behaves differently.** Unlikely: the hooks only read events and append a line, each part inside its own try/except. Checked: the pinned Run.read test and the VIP tests pass unchanged. Way back: revert the one commit.
- **A little more work per message.** The skills check now runs on every assistant message: one loop over that message's parts, looking for a Skill call. Negligible next to the model call itself.
- **A stopped run under-counts.** A run killed before its result event has no totals from Claude Code, so its line holds the start load, seconds and skills but zero output and cost. Accepted for v2.1.1.
- **The file grows.** About 200 bytes a run; a heavy month is well under 1 MB. Way back: delete the file; nothing reads it but the report.
- **Text leaks into the file.** The line is built from numbers, fixed words and skill names only; tests check that no reply, message, skill argument or path text appears.

## YES / NO

1. **Run engine hook** (`Run.read`, `_on_result`, `_done`). Risk: low. Recommendation: **yes**.
2. **The widened hook: skill names from every message.** Risk: a little more work per run message; a fault is swallowed and the run is unchanged. Recommendation: **yes** (it is what makes retiring unused skills a decision on data).
3. **VIP check hook** (`vip_check`, one call after the `claude -p` call; still one launch). Risk: low. Recommendation: **yes**.
4. **`reach.py` line for `usage_report.py` (read only).** Risk: very low; needed for the existing classification test. Recommendation: **yes**.
5. **`creaite-rules.md` folder map and Retention.** Risk: none (documentation). Recommendation: **yes**.
6. **`backup.py` change.** Not needed: staging is already in the zip. Recommendation: **no change**.
7. **Tests (`test_run_usage_hooks.py`).** Risk: none. Recommendation: **yes**.
