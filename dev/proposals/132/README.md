# #132 AI models: guarded patches and how to land them

Nothing here edits a guarded file. Each patch is one file's diff, checked with `git apply --check` against the tip of `v27-132-build` (02 against the tip with 01 applied). Applied together in a scratch copy, the guard suites (`test_guard_pinned`, `test_reach`, `test_permissions`, `test_record_commands`, `test_vip_single_call`, `test_guarded_chain`, `test_guard_174`, `test_run_chat`, `test_run_tools_explicit`, `test_prep_guard_confidential`), the route and browser tests for AI models, the settings-page checks, `test_portability` and the rules tests passed.

| Patch | File | What it does |
|-------|------|--------------|
| 01-live_server-scrub-env | live_server.py | `run_env` removes Claude key, token and host names (`paths.claude_billing_env`) from every run. Lands on its own; its test is `test_v270_billing_env` (skips until it lands) |
| 02-live_server-ai | live_server.py | The `/api/ai/*` routes; the chosen model on every `claude -p` launch (G3); the direct call (G4) and the gate for confidential material (G5); the limit card and Ask me (G6); the quick-edit retry (G7); Search may not read the never list (S1); the test-fakes switch (G10). Re-based by a three-way merge onto 2.6.6 with three hand-resolved places (`Run._start` takes `route`, the launch uses `opener`, the edit-ai keys gain `limit_choice`) |
| 03-reach-providers-never | reach.py | `providers.py` refused in every guard mode (G1); the held-run never-list fix (G1c) |
| 04-permissions-no-key-rules | permissions.py | No rule may name `security`, the keychain, `creaite.ai.` or `providers.py` (G1) |
| 05-edit_ai-direct-call | edit_ai.py | The direct-call path and `made_by` for AI on selected text (G4) |
| 06-guard-decisions-rerecord | dev/tests/pinned/guard/decisions.json | The pins that G1c changes (re-recorded; `test_guard_pinned` passes with 03) |
| 07-creaite-rules-ai-models | creaite-rules.md | One paragraph: the gate, the keychain, the scrub (the rules tests pass) |

## Order

1. **01** alone (the scrub; useful today).
2. **03, 04, 06** (the guard first), then **02, 05** (the routes and runs), then **07**. `providers.py` holds the key store and is already in the branch, so 03 and 04 must land with or before 02: until then nothing can reach the key store but nothing yet protects the module either.
3. **08 (G8)** after the canary check: see PLAN.md, "G8 spike findings". Not built; its non-guarded design is in PLAN.md.

Tests that need a patch skip with a "GUARDED" reason until it lands: the route journey in `test_ai_models`, `test_ai_models_browser`, the scrub test in `test_v270_billing_env`, and the AI rows in the settings-page search and every-setting checks.

## Not ported yet (next)

- Help line and What's new for AI models (Cap's wording claims "Use an API key" for Claude, which is G8: write it when G8 exists).
- Cap's proposal test suites worth re-pointing at the patches: G1 key store, G2 lister, G5 gate with mutants, G6 limit, G7 retry, G10 review.
- `dev/handchecks/v2.7.0.md` and `test_v270` for the scriptable checks.
- G8 (the key and the cap) and the allow-list rewrite of the confidential gate (PLAN steps 3 to 5).
