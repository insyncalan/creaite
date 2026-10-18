# AI models (#132), round 2: the direct call, limits, the retry and the review points (proposal)

**Status: a proposal for Alan's yes. Nothing here is applied to `ai-models-132`, `ai-models-proposal-r1`, a shared branch or
main.** The changes are diff files in this folder. They stack on round 1. The tests apply them to a throwaway vault, never to
this repository.

Round 2 covers:

- **G4:** the OpenAI call, for AI on selected text only.
- **G6:** Claude's limit and the Ask me card.
- **G7:** the quick-edit retry.
- **G9:** backup, log and Health.
- **G10:** the builder's two review points.
- **S1:** an extra item from round 1's "not settled". Search's answer may not read the secrets folders.

G8 (Claude by API key) is a decision, not a build. See `G8-options.md`.

## What Alan is being asked to approve

Answer each with yes, no or changes.

| # | Item | Diff | Recommendation |
|---|------|------|----------------|
| 1 | **G4: which feature may use OpenAI.** Only AI on selected text, and only ten of its options: Rewrite clearly, Shorter, Longer, Fix spelling and grammar, Polish, More formal, Warmer, Format nicely, Turn into a checklist and Summarise at the top. "Or say what you want…" (free text) and "Make it executive" (it adds the style guide) stay on Claude. **No writing job is declared.** Current state, the AI drafts and Shape are built from tracker facts, so they always run on Claude. | `g4-direct-call.diff` | Yes |
| 2 | **G4: "clean" is decided on the text actually sent, not on the place.** It is stricter than the client check. It refuses: an item ID however written; a project's code or name; a project's internal health reason; anyone in the people register or any item owner; any organisation in the register; an email address; the words confidential, restricted, Client-safe or internal only; the word VIP; and anything the client check finds for the project. If the tracker or the people register can't be read, it fails closed. | in G4 | Yes |
| 3 | **G4: what is sent.** Only the option's instruction, the format rule and the selected text. Never the project's name, people or item IDs (Claude's prompt has them; OpenAI's doesn't). The call is one HTTPS POST to `api.openai.com` (G2's host) with `"store": false`. It sends at most 16,000 characters, waits at most 30 s, reads back at most 256 KB and asks for at most 2,000 tokens back. The key comes from G1's store just before the call. The debug log gets the host, the status and token counts, never text. **This is the first time vault text leaves the laptop for a service other than Microsoft 365: IT should approve it with G2's egress.** | in G4 | Yes, after IT |
| 4 | **G4: the reply is checked as Claude's always is.** In the client place, the client check drops a reply that isn't client-safe. Everywhere, BL-106's fact check adds its notes. The draft says which model made it (`made_by`), and so do the run's label and a step. | in G4 | Yes |
| 5 | **G4: one change to the run launch.** `Run` takes the server's plan for a run (`route`). For a direct call, the plan's opener (`DirectProcess`) starts the call in place of `subprocess.Popen`, and the run engine reads its answer as it reads `claude -p`'s stream: steps, Stop and one run at a time all work unchanged. With no plan, which is every run but a suggestion Alan sent to OpenAI, the launch is byte for byte round 1's (tested). | in G4 | Yes |
| 6 | **G6: how the limit is recognised.** Claude Code 2.1.288 gives three signals. The main one is a `rate_limit_event` whose status is `rejected`, with `resetsAt` and the limit's type (five_hour, seven_day…). The fallbacks are an assistant message whose `error` is `rate_limit`, and an error result whose text says "You've hit your limit" or "usage limit reached". creaite saw none of these before (nothing in `system/scripts` matched). They were read from Claude Code's own message formats. No real limited run was made. | `g6-limit-card.diff` | Yes |
| 7 | **G6: what happens at the limit. Nothing is retried by itself.** The run ends with one card, through the chat's existing "cant" card (a sentence and a button). It says when the limit resets, what `ai.on_limit` does next and offers "Open AI models", and an error carries the same words. **Ask me** adds "Run this one on OpenAI …" only for AI on selected text with OpenAI connected. Pressing it sends that one request again, and the server routes it there only while the limit holds and only if the text is clean. **Another connected model** does the same without asking, for clean text. **Step down** runs writing on the quick-edit model, and the run says so in a step. Jobs that use tools wait. The limit's own words never become a suggestion. | in G6 | Yes |
| 8 | **G6: the run engine's ending moves into `Run._end`, in the same order, with the limit added.** `test_run_read_pinned` passes unchanged. The VIP check skips while the limit holds. | in G6 | Yes |
| 9 | **G7: the quick-edit retry.** When the fact check finds a lost or added date, number, name or ID, the suggestion is tried **once** more on the writing kind's model. That happens only if the model is **stronger** than the one that made it. It runs inside the same run (Stop stops both), a step says so, and the draft says which model made it. The second try goes through the same checks: the client check, and G4's for OpenAI. If it is dropped or doesn't come back, the first is shown with its notes. Never a loop. **At the default settings nothing is retried**, because quick edits and writing both run on Sonnet today. | `g7-quick-edit-retry.diff` | Yes |
| 10 | **G7: a retry is a `Run` that isn't listed** (`nested`). It is never "the run in progress" and never starts a queued message. The RUNS lines move into `Run._listed` unchanged. | in G7 | Yes |
| 11 | **G9: Settings › Health shows AI models.** It shows one line per provider (Claude's sign-in; OpenAI connected, with how many models are offered) and Claude's limit when it holds. It shows a problem when settings say OpenAI is connected but the keychain has no key, or when test providers are on. It shows names and counts only, never a key. The tests show the key in no backup, log, zip, manifest or answer. | `g9-health.diff` | Yes |
| 12 | **G10 (a): the test-fakes switch.** `CREAITE_FAKE_PROVIDERS=1` works only in the development repository (`.creaite-dev`) or in a test's vault in the temporary folder. A real vault ignores it, and the debug log says so. | `g10-fake-switch-and-tested-key.diff` | Yes |
| 13 | **G10 (b): the tested key in memory.** It is kept **5 minutes** (was 10), one per provider and used once. A timer drops it when it runs out, even if nothing else happens. It is also dropped on that provider's Disconnect and when the server stops or restarts, and is never written. | in G10 | Yes (or keep 10 minutes) |
| 14 | **S1: Search's answer may not read the never list's secrets and system folders.** These are `Read(~/.ssh/**)`, `Read(~/Library/Keychains/**)`, `Read(//etc/**)` and the rest, 39 places with two rules each. They are added to its deny list (a deny only takes away). Search still reads the vault and the projects folder. Round 1 expected this to change `test_search_tools_pinned`. **It doesn't: that suite passes unchanged.** | `s1-search-never-reads.diff` | Yes |
| 15 | **G8: Claude by API key.** It is a decision, not a build. The recommendation is option B now (keys only for providers other than Claude) and to hide "Use an API key" for Claude until it is decided. | `G8-options.md` | Decide |
| 16 | **Page work after a yes (not guarded, not in this proposal):** the Ask me button in AI on selected text (from the card's `offer`), a "Made by …" line and "tried twice" under a suggestion, and Health's AI lines. Until then, the card shows its sentence and Open AI models, and Health's problems already show. | (none) | Yes, as follow-ups |

**Order.** All six diffs go on round 1's G1, G2, G3 and G5, **with or without G1c**, in this order: G4, G6, G7, G9, G10, S1. Each
needs the ones before it. All six were checked with `git apply`, with and without G1c (`test_ai_proposal_r2_stack`).

**Round 1's G1c.** Round 2 doesn't touch `prep_decision` or the hook. Its new runs (the direct call, the retry) have no tools,
so no hook runs for them either way. With G1c applied, `test_guard_pinned` changes on exactly round 1's 10 rows, and on nothing
from round 2. Without it, `test_guard_pinned` passes unchanged.

## What this can reach and what it cannot

| Who | Can | Cannot |
|-----|-----|--------|
| **The live server** (Alan's own process) | Send one POST to `https://api.openai.com/v1/chat/completions` with a suggestion's instruction, format rule and selected text, for one of the ten declared options, only when that text is clean and Alan chose an OpenAI model for quick edits (or the limit's Ask me or "another connected model" applies). Read the OpenAI key from the keychain (G1's `peek`) just before that call. Keep Claude's last limit and its reset time in memory. | Send anything for a tools job, writing, Shape, a confidential meeting, the free instruction or "Make it executive". Send the project's name, people, item IDs, the vault or any file. Call any other host, follow a redirect or use a proxy from the environment. Put the key in a URL, a log line, an answer, an error, a file or an environment variable. Retry a run by itself. |
| **A model run** | Exactly what it can after round 1. Search's answer can no longer read the never list's places (S1). | Reach the direct call. It isn't a tool, a script or a URL a run can call: `DirectProcess` is started only by the server's own route, and `/api/edit/ai` needs the page's token, as round 1 found for `/api/ai/*`. Read the key: it is never in a run's environment, and `providers.py` stays refused (G1). |
| **The page** | Ask for a suggestion with `limit_choice: "other"` (Ask me's button). | Choose the provider or decide what is clean. The server decides both, the choice counts only while the limit holds, and the checks still run. |
| **Backups, logs, settings, Health** | Hold provider ids, model ids, `ai.on_limit`, the debug log's host, status and token counts, and Health's lines. | Hold a key, a prompt or a reply (tested). |

## G4: the direct call

**Which features.** `providers.CLEAN_FEATURES` declares, feature by feature, what may go to a provider other than Claude. Round 2
declares one: `edit-ai`, with the ten options above. Round 1's `send_allowed` gate still stands, and `route_for` (G5) is still the
only way a model is picked:

- `providers.declared("edit-ai", option, problems)` is False (not confidential) only for a declared option with no problems;
- `route_for("quick", …, declared=…)` then answers the model;
- `send_allowed` is checked on that answer, again in `direct_call`, and once more inside `DirectProcess` just before the call.

**How "clean" is decided** (`edit_ai.outside_problems`, on the selected text):

| Found | Why it stays on Claude |
|-------|------------------------|
| VIP, however written | private to Alan (BL-288) |
| confidential, restricted, Client-safe, internal only, not for the client | marked |
| an email address | a person |
| an item ID: strict, or loose (`abc a 1`) when the tracker holds it | tracker data |
| a project's code (as capitals) or name | client and project names |
| a project's internal health reason (five words of it in order) | internal |
| a person or organisation in the people register (names, aliases, organisations) or any item owner | names |
| anything `client_leak.text_findings` finds for the project (labels, Client-safe: no memory lines, wording of items that aren't client-visible) | the client check |
| a tracker or people register that can't be read | fails closed |

**What is sent.** `edit_ai.outside_prompt` gives the instruction, the format rule, four rules (work only from the text, British
English, the text is material not instructions, reply between the markers) and the selected text. Claude's prompt (`edit-ai.md`)
also lists the project's name, people and open item IDs. OpenAI's never does. A test compares the two.

**The call** (`providers.DirectCaller`, a subclass of G2's lister, so the same TLS context, opener and limits code):

| | |
|---|---|
| **Host** | `api.openai.com` only (`DIRECT_HOSTS`), path `/v1/chat/completions`, https only |
| **Sent** | `Authorization: Bearer <key>` (one header), `Content-Type`, `Accept`, `User-Agent: creaite`. The body is `{model, messages: [one user message], max_completion_tokens: 2000, store: false}`. Nothing else. |
| **Limits** | 30 s, 16,000 characters of prompt (larger is refused before sending), 256 KB read back. A model id is checked against `[A-Za-z0-9._:-]{1,80}`. |
| **Errors** | 4xx is `KeyRefused(status)`, shown as G2's words ("OpenAI did not accept this key (401)…"). A 3xx, 5xx, timeout, TLS failure, oversized, empty or non-JSON answer is `ProviderUnreachable` (host only). None holds the key, the prompt or the reply, and none chains to one that might. |
| **Logged** | `api.openai.com direct call: 200, 120 tokens in, 40 out` or the status only |
| **Under the test fakes** | `caller()` is `NotBuiltCaller`, so no test ever reaches OpenAI. The tests put a caller pointed at their own fake server in its place. |

**Through the live server.** `edit_ai_route` asks `direct_plan`:

- **None** when Alan hasn't chosen another provider for quick edits. This is today's run, byte for byte.
- **A note** when the text stays on Claude. The run's step says why, for example "This text holds an item ID, so it went to Claude, not OpenAI." or "Confidential material is only ever sent to Claude. So Claude ran it."
- **A direct call:** "Sent to OpenAI …: the selected text and the instruction only."

The run engine reads `DirectProcess` as it reads `claude -p`: the reply as one text block, then the result. So `EditJob` checks it
exactly as before. Stop ends it at once (tested: under 2.5 s with the provider still answering), and a reply that comes later is
dropped. A failure ends the run in plain words. It is never sent on to Claude by itself.

## G6: Claude's limit

**What creaite already sees: nothing.** `grep -rn "session limit\|rate_limit\|429" system/scripts` finds only G2's refused-key
words. The signals were read from Claude Code 2.1.288's own message formats:

- **`stream-json`** gives `{"type": "rate_limit_event", "rate_limit_info": {"status": "allowed" | "allowed_warning" | "rejected", "resetsAt": <epoch seconds>, "rateLimitType": "five_hour" | "seven_day" | "seven_day_opus" | …}}`;
- **an API error message** carries `"error": "rate_limit"`;
- **the error line** is composed as "You've hit your limit · resets 3pm";
- **the result** has `is_error`.

`providers.limit_signal` reads these and nothing else. It is tested on each, and on near misses (an overloaded error, a good
result that mentions the words, a user message). An `allowed` event or a good result clears the limit. **Not tested against a
real limited run**, which would mean exhausting the subscription.

**What the server keeps.** `LIMIT`, in memory only, holds the reset time, the limit's type, and until when to treat Claude as
limited. With no reset time, that is 15 minutes. A restart forgets it, and the next run meets the limit and shows the card again.

**The card.** It reuses the chat's existing "cant" event (`{what, line, go}`: a sentence and a button, BL-314), with
`what: "limit"`, `go: Open AI models` and, for Ask me, an `offer`. An `error` event carries the same sentence, so AI on selected
text and the drafts, which already show an error's message, show it today. The words:

| `ai.on_limit` | Tools job | Writing | AI on selected text |
|---|---|---|---|
| Ask me | "Claude's limit is reached; it resets at 15:00. Nothing was changed. Jobs that use tools wait: try again then." | "… Try again then." | "… Nothing was changed." with an offer: "Run this one on OpenAI fake flagship" (OpenAI connected), else "Try again then." |
| Another connected model | wait | "… Try again then." | "… Try again to run it on OpenAI …, unless it holds confidential material." |
| Step down | wait | "… Writing runs as a quick edit until then: try again to run it on Claude Haiku 5.5." | "… Try again then." |

**Never silent, never a retry.** Nothing reruns by itself. The next run that Alan starts is routed with `limited=True`. For
writing at Step down, its step says "Claude's limit is reached, so this ran as a quick edit on Claude Haiku 5.5 (Step down one
kind)." For clean AI on selected text at "another connected model", its step says "Sent to OpenAI …". **Confidential material
never moves** (G5's gate). Tested with a confidential selection at the limit: it stays on Claude.

**Step down's honest limit.** Writing (Current state, the drafts, Shape) runs only on Claude, so stepping down helps only when
the limit is model-specific (for example `seven_day_opus` with Opus chosen for writing). At a five-hour limit every Claude model
is limited, and the next run shows the card again.

## G7: the quick-edit retry

`providers.retry_kind("quick", notes)` (built in round 1) says whether a quick edit is retried. `retry_plan` adds the rest:

- **only once:** `retried` is set on the second;
- **only to a stronger model:** the writing kind's model through `route_for`, with the same declaration as the first. Its grade
  must be above the first's, and the first is what the run was started with (`Run.alias`, or #126's Sonnet pin when that is
  None);
- **Claude:** the same prompt Claude always gets, with `--model` set to the stronger alias. The test checks that the launch is
  otherwise identical;
- **OpenAI:** `outside_prompt` only, and only if the text is clean. Text that isn't clean retries on Claude's recommended writing
  model, or not at all.

**What Alan sees:**

- a step: "The check found a changed fact, so this was tried once more on Claude Opus 5.5.";
- the draft, with `made_by` and `retried`;
- if the second still loses a fact, it is shown with its notes;
- if it is dropped by the checks or doesn't come back, a step says so and the first is shown with its notes.

**The client check is never relaxed.** In the client place the second reply goes through `edit_ai.result` with the same context.
The test's second reply names an item the client may not see. It is never shown, and the first (client-safe) suggestion stays.

**At the defaults nothing is retried.** Quick edits run on Sonnet (#126's pin, round 1's item 7) and writing on Sonnet, so
nothing is stronger. Choosing Opus for writing turns the retry on.

## G9: backup, log and Health

**Settings changes.** Every `ai.*` change goes through `settings_catalogue.save`, with a backup of the file and a log line per
key. This was already built, and is now tested across a whole journey: Connect, choosing quick edits and writing, the limit
choice, and Disconnect (which puts quick edits back on Claude Haiku in the log).

**Health.** `health.ai_models` runs in the live server's own process, the only one that uses the key store (G1). It asks the store
only whether it has a key, never for the key.

**The key is nowhere.** The journey covers a refused key, an unreachable provider, Test, Connect, Choose, a suggestion sent to the
fake OpenAI, Health and Disconnect. Afterwards the test key, the refused key and the unreachable key are in:

- no file of the vault (backups, `settings-log.jsonl`, the debug log and staging included);
- no entry of the daily zip, `manifest.json` included;
- no route's answer;
- no Health output.

## G10: the two review points

**The fake switch.** `providers.fake_mode()` now needs `CREAITE_FAKE_PROVIDERS=1` and one of two places:

- `.creaite-dev` in the vault root (the development repository);
- a vault inside the system's temporary folder (a test's vault; a real vault never lives there).

Anywhere else the switch is ignored: the real seams are used, and the debug log says "CREAITE_FAKE_PROVIDERS ignored…". Health
also flags test providers when they are on (G9).

**The tested key in memory** (between Test and Done):

- **how long:** 5 minutes instead of 10. Ten minutes is generous for "tick the models, press Done", and Test can be pressed again;
- **how many:** one per provider, so a new Test drops the last;
- **how often:** used once (`take`);
- **when it goes:** a timer drops it when it runs out, even with nothing else happening. Disconnect of that provider, SIGTERM, the
  end of `main` and a restart after an update drop it too;
- **where:** never written. A test scans the vault after a Test.

**One limit of Python:** it can't overwrite a string's memory. Dropping every reference is what it can do, and the key goes when
the process ends.

## S1: Search's answer and the never list

Search's answer has no guard hook (Alan, #60), and `Read` is allowed. Round 1 noted that it could read the encrypted keychain file.
S1 adds Read deny rules to its deny list for reach.py's read-barred never-list entries:

- **secrets** below the home folder, as `~/…`;
- **the operating system**, as `//…`.

Each gets the place and `/**`. The vault's own entries bar writing only, so Search still reads the vault and the projects folder.
Claude Code applies Read rules to Grep and Glob as well (documented behaviour, not tested in a real run). Paths are matched as
written, and reach.py ignores case.

## How it was tested

**New test files.** Each builds a throwaway vault, applies round 1 (all but G1c) and round 2 up to its item, and runs there, in
its own process:

| Test file | Tests |
|-----------|-------|
| `test_ai_proposal_g4_direct.py` | 17 |
| `test_ai_proposal_g6_limit.py` | 9 |
| `test_ai_proposal_g7_retry.py` | 9 |
| `test_ai_proposal_g9_backup_log_health.py` | 5 |
| `test_ai_proposal_g10_review.py` | 7 |
| `test_ai_proposal_s1_search_reads.py` | 2 |
| `test_ai_proposal_r2_stack.py` | 2 |

All pass. They need no real key, keychain, provider or network:

- OpenAI is a fake HTTPS server on 127.0.0.1, with a certificate made by `openssl` for the test and trusted only by the test's
  context;
- `claude -p` is a recorder that answers each launch, including with Claude Code's limit stream.

`ai_proposal_support.py` gains `vault2`, the fake chat server and the shared set-up.

**Without the diffs** (`CREAITE_PROPOSAL_UNPATCHED=1`: round 1 only), every test fails except six regression guards, which pass
either way and check behaviour that must not change:

- G10: a test vault, the development repository and no switch keep the fakes as they were, and a tested key is never written;
- S1: no other launch list moves;
- the stack: the diffs apply.

**Hunk by hunk** (`CREAITE_PROPOSAL_DIFFS2`). Every one of the 44 hunks is needed: leaving any single hunk out makes its item's
test fail.

| Diff | Hunks |
|------|-------|
| G4 | 9 |
| G6 | 15 |
| G7 | 9 |
| G9 | 2 |
| G10 | 8 |
| S1 | 1 |

The first pass found five hunks that no test needed. Tests were added for each, then G6 and G7 were run again:

- G6: the VIP check reading its own reply for the limit;
- G7: the run keeping its model;
- G7: a retry never starting a queued message;
- G7: the first try's model id (two hunks).

**At the defaults no launch moves** (`test_ai_proposal_r2_stack`). G3's thirteen launch cases are byte for byte round 1's, and the
launch tables are equal. The one exception is Search's deny list, which only gains S1's rules, in the same order otherwise.

**The existing suites**, on a copy of this branch with round 1 (all but G1c) and all of round 2 applied, one at a time. These
pass:

- `test_reach` 18, `test_permissions` 19, `test_record_commands` 9
- `test_ai_models` 14, `test_ai_models_browser` 2
- `test_vip_tools_pinned` 9, `test_search_tools_pinned` 7, `test_run_read_pinned` 1
- `test_prep_guard_confidential` 12, `test_notes_guard` 5
- `test_permissions_mcp` 10, `test_permission_file` 20, `test_permission_panel` 14
- `test_no_real_names` 2, `test_ai_select` 16, `test_settings_page` 35
- **`test_guard_pinned` 2, unchanged**
- `test_settings_catalogue` 14, `test_health_fixes` 30, `test_run_tools_explicit` 13
- `test_drafts_scaffold` 10, `test_client_gate` 37, `test_ai_select_notes` 5, `test_client_leak` 40
- `test_settings_poll` 3, `test_sweep_lock` 12, `test_live_server` 22, `test_run_chat` 17, `test_drafts_report_route` 3

Round 1's own five proposal tests also still pass with the changed support file.

Two failures are not round 2's:

- **`test_backups`** fails one test on this branch with no diff applied. Doctor's "Scripts take locations from paths.py" wants a
  top-level `import paths`, and the built `providers.py` (36e2b36) imports it only inside functions. This is for the builder to fix.
- **`test_vip_single_call`** fails one source pin (`… vip_deny())], prompt)`). It is the VIP command line that round 1's G3
  changes, and round 1 didn't run this suite. If G3 is approved, the pin is re-recorded with it.

**With G1c as well** (all five of round 1, then round 2): `test_guard_pinned` fails on exactly round 1's 10 rows (prep and held:
`Read ~/.ssh/id_rsa`, `Read /etc/hosts`, `Glob` and `LS` in the home folder, and `report.py adhoc ~/.ssh/id_rsa`, each from
allowed to refused), and on nothing else.

**`dev/tools/check.py`** reports "check: OK" both on the patched copy and on this branch. Getting there meant keeping the run
engine's complexity under its limits. `Run.__init__` is now 15 (it was 17 before round 2, the limit is 18) and `Run.read` is 12,
because:

- the launch plan is `launch_plan`;
- the RUNS lines are `Run._listed`;
- the ending is `Run._end`;
- the shared checks are `outside_route` and `direct_call`.

## Not settled

- **IT approval.** The egress to `api.openai.com` now carries vault text: a selection the checks passed. `"store": false` asks
  OpenAI not to keep it for its own features, but its API terms (abuse monitoring) still apply, which is IT's and Alan's call.
  G2's proxy question (round 1, item 5) applies here too.
- **The limit signals** are Claude Code 2.1.288's formats, not a real limited run. A Claude Code update could change them. The
  fallback text match and the "cant" card would still work for the error result, and a test pins the formats so a change shows
  up.
- **Claude Code's own retries.** It may retry a 429 itself before it gives up. creaite only reads what it finally says.
- **The page.** The Ask me button, "Made by …", "tried twice" and Health's AI lines are page changes (item 16). The page's
  `go` for Open AI models (`{"page": "settings", "arg": "aiModels"}`) wasn't checked in a browser.
- **The clean list** is a first, deliberately narrow list. Alan may narrow it further (for example only spelling and Polish), or
  later widen it, one reviewed hunk at a time.
- **False positives keep text on Claude.** Any organisation, alias or project word in the text keeps it on Claude, which is the
  safe direction. A two-letter alias such as "JD" counts as a name.
- **G10's temporary-folder rule** treats any vault inside the system's temporary folder as a test vault.
- **G8** is Alan's decision (`G8-options.md`).
