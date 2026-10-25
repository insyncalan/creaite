# #316 Release plan v2.7.0: build plan

Planning note, no code. Written 25-10-2026 on origin/main (v2.6.5, ce936941). #316 is the release plan; this note turns Alan's decisions into build work and an order.

## What it is

Alan's decisions (issue, "Update 23-10-2026"): "**2.7.0 = F4 (projects into the database) + G8 (Claude by API key, Keychain, cap, limit-reached; no other provider, no confidential gate).** Providers and the confidential gate are 2.8.0." #183 went to 2.6.2. #250 was moved to 2.7.0 on 24-10 (own plan in `dev/proposals/250/PLAN.md`). The shared-model answers (trust levels Starter / Trusted / Full, follow flag shared, hub wins, shared folder `_Portfolio/99 System/creaite shared`) are design input for F4's schema, not 2.7.0 build, except that "shared processed-meeting records (F4) must exist BEFORE contributor Intake is enabled". F5/F6 stay out unless the proof of concept converges (and "I would not put F5 and F6 in the same release as F4").

Prerequisites from the issue: 2.6.3 F2 (IDs above 999), 2.6.4 F3 (people table), 2.6.2 F1 (nullable columns) live and soaked on Alan's real database. On 23-10 Alan paused the shared-database work and the HEAD-LOG says F1 to F3 are "not built and the branches are parked unmerged". main (2.6.5) has `applies`, `change_log`, `item_events` but no author/origin/sequence/base_version. So F4 cannot start until Alan says which of F1 to F3 come back (question 1).

## Scope and sequence

### A. F4: projects into the database (L)
1. Schema, additive only, no table rebuild: `projects.uid` (stable, unique), `project_aliases` (old codes; recode becomes an alias), `project_register` fields (name, client, domains, signals, status, folder, partners), `project_settings` (client report on/off, rhythm, reminder, logos), `processed_meetings` (replaces `system/processed.txt`; keyed by meeting key plus content hash; author/origin when F1 exists). A migration: dated copy of `tracker.db`, one transaction, integrity check, rollback by restoring the copy plus `update.py undo`.
2. One reader/writer: `tracker.py apply` writes; `project-register.md` and each project `CLAUDE.md` setting lines become generated copies after each save (a header "generated, do not edit"). The rules say memory files describe context, so the lines move, the prose stays.
3. Readers move to the database with the Markdown as fallback during one release: `paths.py` (folder lookup), `build_dashboard.py` (partners_of, settings), `propose.py` (project add/recode/close), `review.py` (matching on signals), `minutes.py`/`sweep.py` (processed records), `excel_sync.py`, `doctor.py` (database and copy agree), `capture.py`, `locations.py`.
4. Recode: code stays a display name; items keep `ABC-A-003` ids as now (ID work is F2's).
5. Migration of Alan's real register and processed.txt, with a verify command and an Undo.

### B. G8: Claude by API key through `apiKeyHelper` (M)
Alan approved #132's five points (23-10): "apiKeyHelper preferred for key delivery, and if it is not possible I stop and tell Alan rather than accept the environment fallback silently"; a cap per kind of job plus a total with a low default; ask each time when the Claude limit is reached; API use off per project until set.
1. **Spike first (half a day, with a throwaway key):** does Claude Code hand a helper's key on to the programs its tools start? If it does, stop and tell Alan.
2. Key store: the Keychain entry (round 1 G1 diff `g1-key-store.diff` on branch `ai-models-132-apply`; check it against main, the branch is far behind).
3. The helper: a small script printed by `apiKeyHelper` in the run's `--settings`, refused to every model run by name (hook, wrapper, permission rules, never list).
4. Cap and counting: per kind of job plus a total, low default, counted from `run-usage.jsonl`; stops the run with a card.
5. Limit card (G6 `g6-limit-card.diff`): when the subscription limit is reached, ask each time, offer "run this one on the API key"; API use off per project until set (project setting, so it uses F4's `project_settings`).
6. Settings page (AI models, Health lines G9), backup/log/zip tests that no key appears (G9, G10 diffs).
No OpenAI path (G2, G4, G7 stay parked) and no confidential gate.

### C. #250 transcripts (M): see `dev/proposals/250/PLAN.md`; a separate branch.

### D. Small items: only what is already filed and cheap (leak residuals, #355 LOWs, Help text). Alan runs /code-review ultra on the assembled line.

## Files touched

Not guarded: `dev/` docs and tests, `system/scripts/{minutes,sweep,capture,locations,doctor}.py`, dashboard source, `settings_catalogue.py`, templates, help text, release notes, a new `apikey.py` (key store; cf. `providers.py` on the old branch) and helper script.

## GUARDED parts (each a diff for review, Alan approves one at a time)

- F4: `schema.sql`, `tracker.py` (migration, apply for the new tables), `propose.py`, `review.py`, `build_dashboard.py`, `paths.py`, `excel_sync.py`, `doctor.py`: the issue estimates 5 to 8 diffs plus migration and rollback tests.
- G8: `live_server.py` (run launch: `apiKeyHelper` in `--settings`, cap check, limit card, ending moved into `Run._end`; extract helpers because of the complexity limits), `reach.py` (the key store and the helper on the never list for runs; `SCRIPT_COMMANDS` entries), `permissions.py` (refuse any rule that would allow the helper or the Keychain), `.claude/settings.json` (only if the helper needs an entry; plan says none).
- `creaite-rules.md`: F4 (records now in the database), G8 (the key never in an environment), the VIP wording only if Alan gives his go.
- #250 adds its own `live_server.py`, `creaite-rules.md` diffs; merge the guarded chain as one marked commit as in 2.6.x.

## Risks

- Biggest: a data migration on Alan's real database (register and processed records) with readers in many files. Mitigation: additive, dated copy, Markdown copies kept in sync, one release of fallback readers, trial on a copy first.
- The F1 to F3 dependency is unmet and paused; scope could double.
- The `apiKeyHelper` may leak the key to child programs; if so G8 is stopped (Alan's rule).
- A cost cap that fails open would spend real money; the cap must fail closed.
- `live_server.py` is 9,269 lines at its complexity limits; every guarded change needs extraction.
- Review capacity: Cap was offline and waived for 2.6.2 and 2.6.4; F4 and G8 are both Full-tier.

## Test plan

- Migration: from the 2.6.5 schema, from a copy of a real-shaped fixture, idempotent, rollback restores byte for byte, integrity check, `update.py undo`, interrupted run.
- F4 round trip: register edit -> database -> Markdown copy; recode keeps old code resolving; archive/restore; Excel export; dashboard and reports unchanged for the example project (golden check of outputs before and after); doctor flags a hand-edited copy.
- Processed-meeting records: same transcript twice does not duplicate items.
- G8: key never in any environment, log, backup, zip, manifest, process argument or reply (G9/G10 tests); hook, wrapper and permission rules refuse the helper by name; cap fails closed; limit card; off per project by default; fake-provider switch dev-only.
- Hand check automated as `dev/tests/handchecks/test_v270.py`; Alan's live checks: one real key run, one limit event.
- Full suite, `check.py`, `test_no_real_names`, mutation runs on the cap and the helper refusal, Opus reviews per guarded diff.

## Estimate

F4 about 14 builder-days (range 10 to 20). G8 about 6 (range 4 to 9) after the spike. #250 about 5 (4 to 8). Small items 2. Total about 27 (range 20 to 39) builder-days, plus Cap's review and a soak on Alan's real database. With two builders in parallel (F4 and G8 are independent except for the per-project switch) the calendar is roughly 2 weeks, so 2.7.0 lands later than "about Fri 6-11" unless F1 to F3 are already in; with them still to build add about 2 to 3 weeks.

## Open questions for Alan

1. **F1 to F3 are paused and unbuilt.** Does F4 wait for them (the plan), or does 2.7.0 carry only the F4 tables without author/origin/sequence? Recommend the second: build F4 with nullable author/origin columns now, so it needs no later rebuild, and leave IDs above 999 and the people table to their own releases.
2. **Proof of concept:** is the three-database convergence result needed before F4 starts? Recommend no; F4 is single-user useful (recode as alias, one source of truth) and additive.
3. **Is #250 in 2.7.0 at all?** It carries a known leak path until order c is closed. Recommend: in 2.7.0 only if Cap's re-review is clean by the freeze; otherwise 2.7.1.
4. **G8 stop rule:** if the spike shows the key reaches child programs, drop G8 to 2.8.0 (your 23-10 rule), not use the environment. Recommend confirm.
5. **Default cap numbers** (per kind and total), and whether the cap is in dollars or tokens. Recommend dollars, low default, e.g. 5 per week total, off until set.
6. **Release date.** Fixed 6-11, or when the gates are green? Recommend when green, F4 first on the board, G8 and #250 as separable branches so either can drop out.

## What to cut if time is short

Order of cuts: small items; #250 (to 2.7.1); Health/settings polish for G8 (keep the key store, helper, cap, limit card); the Excel and dashboard readers' database path for settings (keep the register and processed records, leave client-report settings in Markdown). If F4 cannot finish with its rollback proven, ship G8 alone as 2.7.0 and F4 as 2.7.1. Never cut the migration backup, the rollback test, the never-in-environment test or the cap's fail-closed rule.
