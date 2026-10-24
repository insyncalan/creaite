# #338 NEXT: what remains after the delivered rules cut (part C of #327)

Planning only (24-10-2026).

## What is asked

`creaite-rules.md` at least 50% smaller, nothing weakened: keep the non-negotiables, guard and approval rules, folder map and conventions; move the long reference to a file read only when needed; a table of what moved where; a retained-rules test; also check the root `CLAUDE.md` and the project memory template. Done when: rules at least 50% smaller with the test green; Alan has approved the exact diff; before and after start tokens measured and reported. Review tier Full (guarded). 2.6.3.

## What is already built (`origin/v263-338`, its `dev/proposals/338/README.md`)

- Rules 62,721 B to 31,282 B (−50.1%) on the 2.6.2 line; 66,315 B to 32,678 B (−50.7%) after the 2.6.2 chain. About 7,900 tokens lighter per run.
- `system/templates/creaite-reference.md` (62 KB) holds the old wording, read by section when a task needs it.
- Two diffs for approval (`creaite-rules.diff`, `creaite-rules.after-chain.diff`), checked forward and in reverse; a section-by-section table.
- `dev/tests/test_rules_retained_338.py` (25 tests, 44 named mutants plus 304 automatic ones).
- Root `CLAUDE.md` and the new-vault template are about 0.7 KB each: checked, nothing to trim. The README does not report the project memory template (task N1).

## What remains

| # | Task | Files | Guarded | Start now? |
|---|------|-------|---------|------------|
| N1 | Check the project memory template and the skill files for trimming; report sizes, trim only if clearly large | `system/templates/` (memory template), `.claude/skills/*/SKILL.md` (report only) | no | **Yes, report only** |
| N2 | Before and after start tokens: same fixed tasks with and without the slim rules, from `usage_report.py --days 7`; a small script to compare two windows | new script in `dev/tools/`, `dev/proposals/338/MEASURE.md` | no | **Yes** (script and baseline); "after" waits for the slim rules to be installed |
| N3 | Alan approves the exact diff (via Jarvis); the after-chain diff applies after the 2.6.2 chain | `system/creaite-rules.md` | **yes** (diff only) | No: Alan's decision |
| N4 | Pointer test: every pointer line in the rules names a real section heading in the reference | new file in `dev/tests/` | no | **Yes** |
| N5 | Folder map wording for `creaite-reference.md` in `dev/BUILD.md` | `dev/BUILD.md` | no | After N3 |
| N6 | Optional second pass (Skills table, Dashboard editing); could reach about −60% with more risk of dropping a rule | `creaite-rules.md` | **yes** | No: not asked; ask Alan |

Estimate: N1, N2, N4, N5 about 1 agent-day; N3 about 0.5 reviewer day on top of the 2 already spent. N6, if wanted: 1.5 plus 1.5 review.

## Risks

- The saving is small (about 8k of a 503k ask start, under 2%): the measurement should say so plainly; the big lever is part B.
- The reference is only read if a run chooses to; a run that misses a mechanism detail still cannot do what the code refuses.
- The reference holds the 2.6.2 wording; on a tree without the chain it describes more than is built. Apply the chain first.
- Skills are also loaded at run time: slimming them is a separate lever and was not asked.

## Open questions for Alan

1. Approve the exact diff (the after-chain one is the one that ships)?
2. Is a second pass (N6) wanted, given the small saving? Proposal: no.
3. Count only start tokens (the rules' real effect), not cost?

## Can start now

N1 (report), N2 (script and baseline) and N4 (pointer test): new or read-only files, none guarded, no overlap with the 2.6.3 assembly (no Intake files, no `guarded_chain.py`, nothing under `dev/proposals/GUARDED-2.6.3*`).
