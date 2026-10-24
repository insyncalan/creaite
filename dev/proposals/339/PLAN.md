# #339 PLAN: lighter runs part A, a purpose-built run per request kind (v2.6.5)

Planning only (24-10-2026). No product code. Source: #339, split from #327; read with #327 (B) and #338 (C).

## What is asked

Route each request kind the server already recognises **by its own words** (a sweep, refresh calendar, process the meeting, a status question, a simple lookup) to its own small run with only the tools and context that kind needs, as `panel_sweep` does. Everything else stays a plain chat. Recognition is never by the model; confirmation and guard rules do not change.
Targets (measured with `usage_report.py` before and after): a sweep typed into ask creaite under 60k tokens and $1.50; a plain ask under 150k start tokens, red line 500k (with part B).
Review tier: **Full** (heavy guarded `live_server.py` chain diff). Placement: v2.6.5, nothing committed, no date.

## What is already built

- `panel_sweep()` and `PANEL_SWEEP_WORDS/FOR/NOT/PROMPT/STEP` in `live_server.py` (BL-309, #291): the model for a recognised kind. The server decides from a short fixed word list, runs a chat under BL-295's `sweep` mode (stage only; no apply, undo, approve, reject, `propose.py stage`; writes only in `system/staging/drafts/`), and a queued sweep gets it too. `dev/tests/test_panel_sweep.py` covers it.
- The calendar refresh words are already inside `PANEL_SWEEP_WORDS`; #265 added a `calendar` run kind with `NO_CARD_KINDS` and its own prompt.
- Held mode (#60) for runs that read files; `run_args(policy, ...)` builds the tool and permission arguments; `Run(... sweep=...)` carries the kind.
- Measurement: `usage_report.py` (per day and kind), `run-usage.jsonl` (#197), the Usage tab (#238).
- Part B (fresh sessions by default, `origin/v263-327b`) and part C (rules −50.1%, `origin/v263-338`) are in the 2.6.3 line. Both cut the start load every kind inherits.

## What remains

1. **Measure first.** Run the same tasks (a sweep typed in the panel, a status question, a lookup, a meeting process) on the 2.6.3 build and record start tokens per kind. This decides how much A is still worth: with B and C landed, a typed sweep may already be near its target, because most of the 260k to 352k came from resuming a long session. Build only the kinds still over target.
2. A kind table: for each recognised kind its words (bounded length, no second instruction, no image, not confirmed), mode, tool list, skill, prompt, step label and card rule.
3. A recogniser per new kind, built and tested like `panel_sweep` (accept and reject lists: "and", "then", apply, a second instruction, an image, a confirmed request).
4. One function maps kind to `run_args` policy and prompt, so `Run.__init__`, the queue (about line 3229) and the follow path stay one code path.
5. Per-kind result checks: `claims.py` on a status answer; a lookup run reads the tracker only.
6. Rules wording (guarded), usage reporting by the new kinds, a before and after table.

## Task breakdown

| # | Task | Files | Guarded |
|---|------|-------|---------|
| A0 | Baseline and after measurement (read only; start tokens per kind from `run-usage.jsonl`) | new script in `dev/tools/`, report in `dev/proposals/339/` | no |
| A1 | Kind registry (data only): words, mode, tools, prompt per kind | `live_server.py` | **yes** |
| A2 | Recognisers: status question, simple lookup, process meeting | `live_server.py` | **yes** |
| A3 | Run construction and queue wiring; kind in the usage line | `live_server.py`, `usage_log.py` | **yes** (live_server); usage_log is not |
| A4 | Tests: recogniser accept and reject lists, mode refusals per kind, hook refusals unchanged | new `dev/tests/test_panel_kinds.py`, `test_panel_sweep.py` | no |
| A5 | Guard parity test: each new kind's allow list is a subset of today's read plus sweep lists; none reaches `tracker.py apply`, `propose.py stage` or a Microsoft 365 action | new file in `dev/tests/` | no |
| A6 | One rules sentence for the new kinds | `system/creaite-rules.md` (and the reference file) | **yes** |
| A7 | Hand check (live only) | `dev/tests/` | no |
| A8 | Before and after report | `dev/proposals/339/` | no |

## Guarded files

`live_server.py` (A1 to A3, heavy: diffs only, through the chain), `creaite-rules.md` (A6; Alan approves the exact diff). `reach.py` only if a new mode is needed: avoid, reuse `sweep` and `held`. `permissions.py` and `.claude/settings*.json` should need nothing (reuse the existing lists); confirm in A5. `usage_log.py`, tests and docs are not guarded.

## Review tiers

Full on A1 to A3 and A6 (guard hook parity, mode refusals, recogniser abuse cases, a mutation-style test per recogniser). Standard on tests and the measurement script. `/security-review` and `/code-review high` before the gate.

## Estimate (agent-days)

Measurement 0.5, registry and recognisers 2, run construction and wiring 1.5, tests 1.5, rules wording 0.25, hand check and report 0.5: **about 6 Stark agent-days and 3 reviewer days (Full)**. If the baseline leaves only one or two kinds over target: about 3.5 and 2.

## Risks

- A recogniser too loose runs a request on a narrow tool list and fails oddly; too tight gains nothing. Mitigation: short word lists, reject any extra instruction, fall back to a plain chat.
- A narrow run cannot take a follow-up ("and apply it"): the reply says so and the next message is a plain chat.
- Guard bypass through a new mode: reuse the two existing modes only; A5 proves parity.
- The 2.6.3 line is still changing `live_server.py`: start A1 to A3 only on a tree with 2.6.3 merged, or the chain diffs conflict.
- One prompt per kind is more text to keep in step with the skills.

## Open questions for Alan

1. Is A still wanted at full scope once B and C are measured? Proposal: decide after A0 on the 2.6.3 build and keep only the kinds still over target.
2. Which kinds first? Proposal: status question and simple lookup (read only, safest), then process the meeting.
3. May a quick run offer "go deeper" as a plain chat, or must it end on its own?
4. A cheaper model for the read-only kinds now, or kept for D (#132)?

## Can start now

- **A0** (measurement script and the 2.6.3 baseline): new files, read only, no guarded file, clearly specified.
- **A4/A5 scaffolding** (accept and reject word lists, guard parity as a spec) in new test files against `panel_sweep` as it stands; worth it only once Alan keeps the scope.
- Everything touching `live_server.py` or the rules waits for 2.6.3 to merge.
