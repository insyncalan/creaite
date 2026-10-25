# #132 AI models: build plan for 2.7.0 (25-10-2026)

Planning only. No code is changed by this file.

## What it is

Settings > Essentials > AI models: providers as cards (Claude, OpenAI; Local model, Hosted free models and DeepSeek greyed "Available soon"), a connect journey with the key kept in the macOS keychain, four kinds of job each with a model choice, a weaker-model popup, and three limit choices. Plus the direct OpenAI call for text-only features, the confidential-only-to-Claude gate, and (G8) Claude by API key. Issue #132, labels `opus`, `review`, `v2.7.0`; the issue still carries the milestone name v2.3.0.

## Where the work stands (the key finding)

- Team Cap built nearly all of it on `origin/ai-models-132-apply` (23 commits, head 9d2cf531, 49 files, +8,600 lines): `providers.py` (1,169 lines), `AiModels.jsx`, four settings, G1 to G7, G9, G10 and S1 applied one commit each, ten pins re-recorded, tests green on that branch.
- That branch is cut from main `cdd76622`. **Main has since moved 1,462 commits.** Since then `live_server.py` changed by about 1,580 lines, `reach.py` by about 1,030, `edit_ai.py` by about 295, `settings_catalogue.py` by about 330, `health.py` by about 127. Nothing of #132 is on main (no `providers.py`). So the work is a **re-base onto 2.6.5**, not a fresh build, and the re-base is where most of the risk is.
- **G8 (Claude by API key) is not built.** Its proposal (`ai-models-proposal-r3`, 5aad678d) is not on origin; the apply branch has only `round2/G8-options.md`.
- Cap's independent paper review (20-10) and Jarvis's one-page security design raised gaps that are **not yet in any code**: see "Decided" and "Risks".

## Decided already (quoted from the issue)

- Alan, 17-10: all of rounds 1 and 2 approved, G1c (ten pinned decisions) included. IT approved the OpenAI egress; "no proxy is needed (IT)".
- Alan, 17-10: "API keys are an available option for ALL providers, Claude included" (reverses "keys only for non-Claude providers").
- Alan, 18-10: yes to the one-line `FORMAT_RULES[place]` change in G4.
- Alan, 20-10: "G8 'Claude by API key': YES, build it". "Confidential material never goes to a provider other than Claude: ENFORCED IN CODE (one gate on the one function that builds a provider request; fail closed on unknown sensitivity; tests with mutants)". "macOS Keychain is the intended store". "Still to settle with Alan: run-launch/fallback when a limit is hit, release placement."
- Default model for a kind of job stays today's launch (tool-less runs Sonnet) until Alan chooses (round 1, item 7, "Confirm").
- At a limit nothing is retried by itself; "Ask me" is the default.
- Only AI on selected text (10 of its options) may use OpenAI. No writing job (drafts, Current state, Shape) is declared clean.
- Order from Cap's review, which Alan has not yet answered: G8 before OpenAI.

## Files touched

Unguarded: `providers.py` (new), `settings_catalogue.py`, `settings-defaults.json`, `health.py`, `edit_ai.py` (direct-call path, `made_by`), `drafts.py` (chosen model for text-only kinds), `usage_log.py` and `usage_report.py` (billing kind "API key", provider/model in the counts), `ai_budget.py` (per-kind cap, see Risks), `AiModels.jsx`, `stores/settings.js`, `settings.js`, `style.css`, rebuilt `dashboard.html`, `help.md` and `whats-new.md`, `dev/dashboard-spec.md`, tests, `dev/handchecks/v2.7.0.md`.

**GUARDED (each a diff for review, not a direct edit):**

| File | Change |
|------|--------|
| `live_server.py` | `/api/ai/*` routes (about 150 lines, judged non-guarded by Alan, 17-10: token-checked, starts no run, writes only `ai.*` and the key store); the guarded part is G3 (`--model` on every `claude -p` launch, run engine and VIP check), G4 (`DirectProcess`, `Run` route), G6 (limit detection, the card, `Run._end`), G7 (retry), `budget_gate` interplay, and G8 (key delivered to the Claude run) |
| `reach.py` | G1: `providers.py` refused in every guard mode (confirmed included); G1c: held-run never-list fix; S1 Search deny rules; G8: no "get key" script command |
| `permissions.py` | G1: no rule may name `security`, keychain, `creaite.ai.` or `providers.py` |
| `.claude/settings*` | G8 only, if `apiKeyHelper` is chosen: the helper entry is a settings change (a card when ask creaite asks) |
| `creaite-rules.md` | one paragraph: first egress of vault text (OpenAI, selected-text options only), the keychain, the gate; its 2.6.4 size limit (#338) must hold |
| `tracker.py` | not expected. Only if a stored model id needs a schema field: avoid, keep it in `ai.*` settings |
| `dev/tests/pinned/guard/decisions.json` | re-record: ten G1c rows changed, in the diff for review |

## The work, in order

1. **Re-base (about 3 days).** Replay G1 to G10 and S1 hunk by hunk onto 2.6.5 as fresh guarded diffs (Cap's compare script checks each commit adds and removes exactly the approved lines). Expected conflicts: `reach.py` (rewritten since), `live_server.py` run launch (#126 `NO_CONTEXT_ARGS`, #334 `budget_gate`, #197 usage lines), `edit_ai.py`, `settings_catalogue.py`. Re-record the pins.
2. **Security design gaps into the note and the diffs (about 2 days).** Cap's review points 1 to 7 (below), decided by Alan first.
3. **G8 Claude by API key (about 3 days).** First the real-run check that Claude Code does not hand the key to its tool processes (canary key, `ps eww`, home-folder grep). Then `apiKeyHelper` or the chosen route; screen shows which account is billed; Usage shows API-key runs as their own kind; empty or wrong key never falls back silently.
4. **Allow-list for the confidential gate (about 2 days).** Rebuild `send_allowed` as an allow-list with structural provenance (Cap review 7), not a list of bad words.
5. **Cap before the run (about 1.5 days).** Per-kind caps reserved atomically, on top of the weekly gate (#334).
6. **Page follow-ups (about 1.5 days):** Ask me button, "Made by" and "tried twice" under a suggestion, Health lines on the page, key-shape refusal in chat.
7. **Tests, hand checks, help, review rounds (about 3 days).**

## Risks

- **Re-base drift.** Largest risk: three guarded files moved hugely. Mitigation: re-apply as new diffs, never merge the old branch; run the pinned guard suites after each hunk group.
- **Cost / budget.** An API key bills per token, not the subscription. The weekly budget gate (#334) counts dollars from `run-usage.jsonl` and is off by default, and it only holds typed `ask` runs. Cap's point 14: the hourly alert check alone cost about $8 a day on 19-10, so one low cap starves the user. Plan: caps per kind (interactive, sweep, alert check) plus a total; background kinds off on the API key by default; reserve before the run (parallel starts, retries, restart, midnight, a failed counter write stops rather than allows); the counter lives where a run cannot write it. The #334 gate stays as it is and fails open on a count fault; the new cap fails closed.
- **Privacy: nothing leaves the laptop.** This item is the first vault text to leave it (OpenAI, selected-text options, IT approved). Rules: the one function that builds a provider request; a static test that no other module uses `urllib`, `http.client`, `socket`, `ssl` or `curl` apart from the update fetch and it; host allow-list in code, exact match; no redirects, no proxy from the environment; TLS verified; size, time and token caps; `store: false`. Confidential only to Claude, from the document identity the server resolves, never a flag the page sends; unknown is refused; no fallback chain from Claude to OpenAI for any content.
- **The key.** Keychain item readable by any same-user process with the same Python binary (Cap 3): decide the access list and what happens after a Python upgrade ("re-enter the key", never a silent prompt). The key must never be in an environment, argument, log, backup zip, staging, chat history, diagnostics or git (canary test on the real path). A pasted key in ask creaite is refused. Error text redacted everywhere (a 401 can echo a prefix).
- **Model choice per run kind.** Four kinds map to the run engine's kinds; a bad stored id runs today's launch and says so in a step. Jobs that need tools only list tool-capable models. Guard hook and approvals unchanged for every model.
- **Defaults.** At the defaults every launch is byte for byte today's (a test). Recommended Opus / Sonnet / Haiku are marks on the page; the effective default for tool-less runs stays Sonnet until Alan says.
- **Usage log.** Stays counts only (no key, prompt or name); adds provider and billing kind. The limit signal formats were never seen in a real limited run (Claude Code may retry a 429 itself); one real check is needed or it ships as best effort.
- **Gates.** Pins: `test_guard_pinned` changes on exactly the ten G1c rows. Rules file size limit. `test_plain_words` and `test_no_real_names` scan the page, Help and messages: new strings must use plain words, no vendor-internal terms.

## Test plan

- Carry over Cap's suites, re-pointed at 2.6.5: `test_ai_models` (14), `test_ai_models_browser` (2, desktop and 900 px), the G1 to G10 and S1 proposal tests (about 120 in total, hunk by hunk: dropping any one hunk reddens its test), `test_guard_pinned`, `test_reach`, `test_permissions`, `test_record_commands`, `test_vip_single_call` (pin re-recorded for G3), `test_settings_page`, `test_settings_catalogue`, `test_health_fixes`, `test_ai_budget*`, `test_run_usage`, `test_backups` (Cap's note: the doctor's `import paths` check fails on `providers.py`: fix in the builder).
- New: canary key through enter, run, error, remove, crash (grep vault, staging, backup zip, git, logs, `~/.claude`, process list); second same-user process cannot read the item; confidential allow-list cases (item to source to meeting, selection origin, paste, project switch) with mutants (trust the page flag, accept unknown, second outbound caller, enable fallback); cap cases (parallel, restart, midnight, counter write fails); routes (token, Host, same-origin, ask creaite blocked with the real hook); pasted key in chat refused.
- `dev/tests/handchecks/test_v270.py` for scriptable checks; `dev/handchecks/v2.7.0.md` for judgement and live-only items (a real key on Alan's Mac, a real limit).
- Fake provider only in the dev repository or a temp vault. No real key in any test.

## Estimate

About 16 builder-days (range 12 to 22) with one Opus builder, plus 3 days of independent review (Cap on the key path, the gate under attack and the cap; fresh Opus reviewers on the guarded diffs). With two builders (re-base and G8 in parallel) about 10 calendar days. The low end assumes the old diffs re-apply cleanly; the high end assumes `reach.py` needs rework.

## Open questions for Alan (6)

1. **Release placement.** The issue is still marked v2.3.0 and the label says v2.7.0. Recommend: ship it all in 2.7.0 as one guarded chain, with Claude-only parts first so a slip does not hold the rest.
2. **Run limit fallback.** Recommend: ask each time, never automatic, background jobs stop; no Claude-to-OpenAI chain for any content.
3. **Default cap on an API key.** Recommend: a cap per kind plus a total, interactive modest (for example $5 a day), background kinds off.
4. **Per-project "never send to another provider" switch (default on for client projects) and a company-policy master switch (default off).** Recommend: yes to both; ask whether the firm's and each client's terms allow API use at all.
5. **Delivery of the Claude key.** Recommend `apiKeyHelper`, after the real-run canary check, over an environment variable; if the check fails, a per-run config folder.
6. **Build order.** Recommend G8 and the key and cap work first, then OpenAI (G8 adds no new recipient of confidential text), and the default model for tool-less runs stays Sonnet.

## If time is short, cut in this order

1. Page follow-ups (Ask me button, "tried twice", Health lines on the page): the logic ships, the polish moves to 2.7.1.
2. G7 quick-edit retry (it does nothing at the defaults).
3. G6 step-down and "another connected model" modes: keep wait and Ask me.
4. The per-project and company switches: ship the master switch off.
5. G4 and G2 OpenAI: ship provider cards, key store, model choice and G8 for Claude only. Never cut the key checks, the allow-list gate, the pre-run cap or the re-recorded pins.
