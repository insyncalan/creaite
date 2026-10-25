# G8 spike: Claude by API key (offline, read-only; 25-10-2026)

For Alan and Jarvis. Written from the code on `origin/v267-chain2` (line numbers are for `live_server.py`, `reach.py`, `ai_budget.py` there), the two plans (`dev/proposals/132/PLAN.md`, `#316`) and what the installed `claude` 2.1.300 says about itself (`claude --help` and a read of the strings in its binary). **Nothing here made an API call, read a key, or wrote code.** Where a fact comes from my reading of Claude Code and not from a test, it is marked **verify**.

## The answer
1. **Deliver the key with `apiKeyHelper`, on a per-run opt-in, and only after the canary check.** Never in an environment (the plans' rule). A keychain read by the live server is not an alternative: the only place the server can put the key for `claude` is its environment or a file, and both are what the rule forbids.
2. **The canary check can be done with no spend**, with a stand-in for the Anthropic API on 127.0.0.1 (section 2). One real run with a throwaway key and a spend cap on the account (a few cents) is then a confirmation, not the test.
3. **Three things the plans do not mention** and the build must cover: `run_env` copies the whole environment, so an `ANTHROPIC_API_KEY` or `ANTHROPIC_BASE_URL` in the shell that started the server would silently switch every run to API billing or to another host (section 3); `--bare` turns the guard hook off and must never be used (3); a per-run dollar ceiling already exists, `--max-budget-usd` (4).
4. **Limits and cost interplay:** the weekly gate (`ai_budget.py`) is off by default, counts dollars from `run-usage.jsonl` without telling subscription from API, and holds only typed asks; G8 needs its own pre-run cap that fails closed, plus `--max-budget-usd` on every API-key run.
5. **Size:** about 6 builder-days as #316 says, once the check passes; the live_server.py part is one funnel function plus four small hunks (section 5).

## 1. How the key would be delivered
| Route | What it is | Verdict |
|---|---|---|
| **A. `apiKeyHelper`** (option C in `G8-options.md`) | The run's `--settings` (already built by `guard_settings`, 404, and passed by `guard_args`, 2647) gets one more key, `apiKeyHelper`: a command Claude Code itself runs, whose output it uses as the key. The key is never in the run's environment or arguments | **Recommended**, after the canary check |
| B. Keychain read by the live server | The server reads the key and hands it to `claude` | **Rejected**: the only hand-over routes are the environment (inherited by every tool the run starts) or a file. Both break the rule. (The server may still read the keychain for its own direct HTTPS calls: that is G2/G4 for OpenAI, 2.8.0, and is not this spike.) |
| C. Local relay in the live server (option D) | A 127.0.0.1 listener adds the key | Not recommended (most code, a second outgoing path and a port, `#132` wants Jarvis's agreement) |
| D. Per-run config folder with the key in a file | The plan's fallback if A fails | Only if A fails the check and Alan agrees; a file on disk with a key is what the rule says never |

What the installed `claude` supports (from `claude --help` and its binary, version 2.1.300): `--settings <file-or-json>` takes the helper; the settings key `apiKeyHelper` and the variable `CLAUDE_CODE_API_KEY_HELPER_TTL_MS` (how long a fetched key is reused) exist; `--max-budget-usd` exists (print mode only); `--bare` exists and "Anthropic auth is strictly ANTHROPIC_API_KEY or apiKeyHelper (OAuth and keychain are never read)" which also says that **without `--bare` the login (subscription) is what is read**. The init event of the stream carries `apiKeySource` (24 mentions): the server can read it from the first event of each run and **check that a run says it uses the helper when it should and the login when it should**. **verify:** its exact values, and the order Claude Code prefers when a login and a helper are both present (I expect the helper wins, which is why it must be added to a run only when that run is chosen for the API).

## 2. The canary check, with no spend
The question: does Claude Code give the helper's key to the programs its tools start (their environment, arguments, files)? A fake key cannot answer it against the real API (the call fails before any tool runs), so:
1. **Stand-in API** (dev only, in the development repository, throwaway; written like the existing stand-in `claude` of the tests): a 127.0.0.1 server that answers `POST /v1/messages` (streaming) with a scripted reply that calls the Bash tool once ("print the environment, the process list with its environment, and search the home folder and the vault for the canary") and then ends. The run is started with `ANTHROPIC_BASE_URL` pointing at it (set by the test only; the server never sets it).
2. **Canary key** (`sk-ant-canary-<random>`, never a real key) from a helper script that prints it. Run `claude -p` with `--settings '{"apiKeyHelper": "<script>"}'` and the real guard hook in front.
3. **Assertions:** the canary is in no tool's environment or `ps eww` output, in no argument, in no file under the home folder, `~/.claude*`, the vault, staging, the backup zip or logs, not in the stream-json output or the run-usage line, and appears in the stand-in's request headers only as the key. Also check that `apiKeySource` names the helper.
4. **If it appears anywhere other than the headers: stop and tell Alan** (the 23-10 rule); no environment fallback.
5. **Confirmation only, with a real throwaway key** (account spend cap set first, an Anthropic-side key limited to one workspace): one short run on `claude-haiku`, costing cents. Needs Alan's yes and the key; this is the one place money moves.
Cost of building the stand-in: about 1 day; it also becomes the fake for the cap and limit tests.

## 3. What the guard must refuse
**`reach.py`** (never list at 43; `SCRIPT_COMMANDS` at 968; the modes and gates at 2046 to 2509)
- Put the key-store module and the helper script on the never list for every mode (as `providers.py` is in G1): Read, Edit, Write, Bash arguments, `--add-dir` roots, and inside a script's arguments.
- `SCRIPT_COMMANDS`: no command that prints a key (the plans' "no get key command"); the helper is not under `system/scripts/<name>` that `system/scripts/run` can start by bare name (keep it outside, or classify it NEVER so the wrapper refuses it).
- Add `~/.claude/settings*.json` keys to the sensitive/never classes for the new key names (`apiKeyHelper`, an `env` block naming `ANTHROPIC_*`): an ask creaite run may never change them; `.claude.json` and `.credentials.json` are already on the never list (and `.claude.json` holds `customApiKeyResponses`, the list of approved key endings).
- The hook cannot see the helper run (Claude Code runs it outside the tool calls), so the refusal is for the model's own attempts to read or run it, not for Claude Code's.

**`permissions.py`** (`tool_problem` at 637, `settings_problem` at 819)
- No allow rule may name `security`, the keychain item (`creaite.ai.`), the key-store module or the helper (G1 already requires this for providers); no settings file may carry `apiKeyHelper`, an `env` block with `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_BASE_URL` or `CLAUDE_CODE_*` provider switches (`CLAUDE_CODE_USE_BEDROCK/VERTEX/GATEWAY/FOUNDRY`). Refuse whatever is approved, like the other safety entries. The helper is only ever in the server's own per-run `--settings`.

**`live_server.py`**
- `run_env` (351) starts from `dict(os.environ)`: **scrub** `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_BASE_URL`, `CLAUDE_CODE_OAUTH_TOKEN`, `CLAUDE_CODE_USE_*` and the helper TTL variable from every run's environment, so a key in Alan's shell can never reach a tool or flip a subscription run to API billing, and make `doctor.py` and Health say when the server itself was started with one set.
- Never pass `--bare` or set `CLAUDE_CODE_SIMPLE`: `--bare` skips hooks, so the guard would not run. Add a test that no launch contains it.
- The three launch sites (2777 run engine, 4290 VIP check, 7669 AI on selected text) must use one function for every extra argument, so G3's `--model` and G8's `--settings` extras and `--max-budget-usd` cannot differ between them.

## 4. Budget gate, caps and limits
- **Weekly gate** (`ai_budget.py`, `budget_gate` at 2669): `DEFAULTS` enabled False, weekly dollars 50, at-limit "confirm"; counts `total_cost_usd` from `run-usage.jsonl` (the usage line has `cost_usd`, `model`, `kind`; no billing kind); holds only typed `ask` runs, never a sweep, the alert check, drafts or a confirmed request. On a subscription `total_cost_usd` is notional; on the API it is real money. G8 needs a **billing kind** in the usage line so the two can be told apart, and the gate must count API runs separately.
- **G8 pre-run cap** (new, fails closed): per kind and a total, in dollars, low default (the plan suggests 5 a week total, off until set), reserved before the run starts and released at its end, so two runs cannot both pass. An unreadable usage file or a missing setting means **no API run**, never "unlimited".
- **Per-run ceiling:** pass `--max-budget-usd <remaining>` on every API-key run. It is a second wall: a run cannot overspend the cap even if the count is wrong. **verify:** what it does mid-turn (stops after the turn that crosses it).
- **Run limits today:** `assistant.run_timeout_minutes` (default 30) ends an unwatched run; one run at a time; a stopped run cannot be told from a finished one by cost. The server reads no subscription-limit signal: the binary emits `rate_limit_event` messages (with `resetsAt`, five-hour and seven-day windows) in its stream; the limit card (G6) should read those, not text. **verify** on one recorded stream (no API call is needed to find an existing one in a past session, but the format at a real limit has never been seen).
- **Order of checks when a run starts on the API:** project setting allows API use (default off) → G8 cap reserve → budget gate (typed ask) → add helper and ceiling to the run's settings → start; the card "run this one on the API key" is the only way the helper is ever added (a click is the go-ahead, like the sweep word).

## 5. The live_server.py diff in outline (no code written)
1. `run_env`: the scrub list above (4 lines + a constant). Guarded; a test that the environment of a started run holds none of them even when the server's does.
2. `launch_extras(kind, billing)`: one function returning the extra `claude` arguments for every launch site; for billing "api" it returns `--settings` merged with the helper entry (merge into `guard_settings` output, never a second `--settings`) and `--max-budget-usd`; for "subscription" nothing. The three sites call it.
3. `Run.__init__`/`_start` (about 2777): choose billing from the request's field `billing` set only by the limit card's route (not by words, not by the message), read `apiKeySource` from the init event and fail the run if it does not match what was chosen; record billing in the usage line.
4. `cap_reserve(kind)` / `cap_release(run)` around the start and `Run._end` (extracted helpers, the file is at its complexity limits).
5. A route `/api/ai/claude-key/...` for enter, test and remove: not guarded per the plan (token-checked, starts no run); stores nothing outside the keychain; never echoes the key.
6. `doctor.py` / Health: a server started with `ANTHROPIC_*` in its environment, and a helper present with no key.
Tests: the canary harness above, mutants on the scrub, the helper refusal and the cap (fail closed), `test_guard_pinned` re-recorded only on the rows G8 adds.

## 6. What I could not settle offline (all marked verify)
The preference order between a login and `apiKeyHelper`; the exact `apiKeySource` values; whether Claude Code logs the key or its ending anywhere under `~/.claude` (the canary grep answers it); `--max-budget-usd` behaviour mid-run; the real shape of a limit event. None needs an API key except the single confirmation run.

## Decisions for Alan
1. Go for the stand-in-API canary check (about 1 day, no spend)? 2. Then one real throwaway-key confirmation (cents) with an Anthropic-side spend cap you set? 3. Cap numbers (the plan: 5 a week total, off until set) and whether the unit is dollars. 4. API use off per project until set (default), confirmed.
