# AI models (#132), round 3: Claude by API key (proposal)

**Status: a proposal for Alan's yes. Nothing here is applied.** The guarded changes are diff files in this folder; the tests are
in `tests-g8.diff`. **Nothing is applied until the real-run check below has been run on a real Mac and has passed.**

Alan's decision (17-10-2026): API keys are an option for every provider, Claude included. This round is how a Claude API key is
used without the key ever being where a run's tools could see it. It uses Claude Code's own `apiKeyHelper` setting (option C in
round 2's `G8-options.md`), with G1's keychain store holding the key.

Your Claude subscription stays the default. With no Claude key connected, nothing changes: every run starts exactly as it does
after rounds 1 and 2 (tested).

## What Alan is being asked to approve

| # | Item | Diff | Recommendation |
|---|------|------|----------------|
| 1 | **The key helper and the key desk.** A small creaite script that Claude Code runs to get the key, and the live server's side that answers it. The helper has no key of its own; the live server hands it over a private local socket, only to the helper, only for a run it started. | `g8a-key-helper-and-desk.diff` | Yes |
| 2 | **The guard refuses both by name.** No model run may run the helper or the desk, in any mode, confirmed runs included, nor through `system/scripts/run`. No permission rule may name them or `apiKeyHelper`. This only narrows: the never list, the hook and the approvals don't move. | `g8b-guard-refuses-the-helper.diff` | Yes |
| 3 | **Claude runs on the key once you connect one.** Connecting a Claude key in Settings › AI models makes every Claude run (ask creaite, the sweep, Prep, drafts, AI on selected text, the VIP check) use it, until you Disconnect. | `g8c-claude-runs-on-the-key.diff` | Yes |
| 4 | **On the key, five variables are taken out of the run's environment** (`ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN`, `ANTHROPIC_BASE_URL`, `ANTHROPIC_CUSTOM_HEADERS`). Any of them would replace your key or send it somewhere else. | in G8c | Yes |
| 5 | **A key Anthropic refuses (wrong, revoked, expired) or can't bill (no credit, spend limit reached):** the run stops with one card in plain words, and later runs go back to your subscription, each saying so, until you connect the key again. The alternative is to stop every Claude run until it is fixed. | in G8c | Yes (back to the subscription) |
| 6 | **A rate limit on the key, or the helper refused:** the run stops with one card. Nothing is set aside and nothing is retried by itself. | in G8c | Yes |
| 7 | **On the key, round 2's subscription-limit card (G6) doesn't apply to that run**, because the subscription's limit isn't what it hit. | in G8c | Yes |
| 8 | **The run's ticket is in Claude Code's command line** (inside `--settings`). It is not the key. It only lets the helper ask, it ends when the run ends, and the desk refuses anyone else who shows it (see "Why it is safe"). | in G8a, G8c | Accept |
| 9 | **Set a spend limit on the Anthropic account before connecting the key.** Your step in the Anthropic Console, not creaite's. | — | Yes |
| 10 | **The real-run check first.** Nothing is applied until Alan or Jarvis has run it and it has passed. | below | Yes |
| 11 | **One pinned list changes: `test_record_commands`' list of commands that change the record gains `keyhelper.py`** (as `permissions.py` is there). Every new script with a command line must be classified (BL-267); the helper is classed "record", the strictest, and is refused by name in every run anyway. Needs your yes and a re-record of that pin. | in G8b | Yes, and re-record the pin |

Not built, for later (not guarded): the page's words for a Claude card on the key ("Runs use your API key, billed to your
Anthropic account") and for a set-aside key (`key_set_aside` is in the state already); an option to use the key **only when the
subscription's limit is reached** (#132 scope (c)); a Health line for the desk.

**Order.** On `origin/ai-models-132` 36e2b36 with round 1 (G1, G1c, G2, G3, G5) and round 2 (G4, G6, G7, G9, G10, S1) applied in
their order: G8a, G8b, G8c. G8b also applies without G8a; G8c needs G8a. Each was checked with `git apply --check` on a clean
copy with rounds 1 and 2 applied.

## How it works

1. You connect a Claude key on the AI models page, as for OpenAI. G2 checks it with Anthropic; G1 keeps it in this Mac's login
   keychain. Nothing new here.
2. When the live server starts a Claude run and a Claude key is connected, it opens its **key desk** (once): a Unix socket in a new
   private folder (owner only, `0700`). At the default settings it is never opened.
3. It makes a **ticket** for that run (32 random bytes), kept in its own memory only, and adds one line to the run's `--settings`
   (the same settings that carry the guard hook, which is otherwise unchanged):
   `"apiKeyHelper": "<this server's Python> -I <vault>/system/scripts/keyhelper.py <desk> <ticket>"`.
4. Claude Code, at the start of the run (and every five minutes, and after a 401), runs that command itself. This is not a tool
   call, so it never goes through the hook. The helper sends the ticket to the desk.
5. The desk asks macOS who is on the other end of the socket (no program is started), and answers the key only when all of these
   hold:
   - the ticket is a live run's;
   - the asking program is the helper itself: this server's Python, with exactly `-I keyhelper.py <desk> <ticket>`;
   - it was started under that run's Claude Code (the process the live server started for the run);
   - it hasn't asked more than 3 times this minute, or 12 times in all.
6. The helper prints the key on stdout. Claude Code reads it, keeps it in its own memory and sends it to Anthropic.
7. When the run ends, its ticket is deleted. When the server stops or restarts, the desk closes.

Claude Code's documented behaviour, confirmed in the installed 2.1.288: `apiKeyHelper` is a shell command whose output is the key
(at most 16,384 printable characters). It is read from the `--settings` given on the command line without the folder-trust check,
which applies only to project and local settings files. The key is cached and asked for again after 5 minutes or a 401. A key from
the helper takes priority over your claude.ai sign-in. The stream's first event says where the key came from
(`"apiKeySource": "apiKeyHelper"`); creaite checks it and adds a step if it says anything else.

## What it can and cannot reach

| Who | Can | Cannot |
|-----|-----|--------|
| **The live server** | Read Claude's key from the keychain (G1's `peek`) at the moment the helper asks, and send it on its own socket. | Put the key in a command line, an environment variable, a file, a log line, a backup or any answer to the page. |
| **The helper** (`keyhelper.py`) | Connect to the desk named in its arguments and print what it is given. | Read the keychain, read or write a file, read an environment variable, import any creaite module (it runs `python -I`, standard library only: `re`, `socket`, `sys`). |
| **Claude Code** | Run the helper and use the key for its requests to Anthropic. | Get the key outside a run the live server started: the desk refuses the helper unless it was started under that run's Claude Code. |
| **A model run's tools** (Bash, Read and the rest) | What they can after rounds 1 and 2. | Run the helper or the desk (the hook refuses them by name in every mode, and `system/scripts/run` refuses them). Run any other program (Bash runs only creaite scripts). See the key in their environment: it is never in one. Read it from a file: there is none. **Whether Claude Code itself passes the key on to the programs its tools start is what the real-run check checks.** |
| **Another program on the Mac with the ticket** | Connect to the desk (if it runs as Alan). | Get the key: it isn't the helper, or isn't under the run's Claude Code, and the ticket ends with the run. |
| **A permission rule or a settings change** (whatever is approved) | What it could before. | Name `keyhelper.py`, `keydesk.py`, `apiKeyHelper` or the desk's folder. Add `apiKeyHelper` to a Claude Code settings file (refused already, since creaite changes only the permission lists; now pinned by a test). |
| **The never list** | Unchanged. The keychain stays on it for every model run. | — |

## Why it is safe

- **The key never goes where a run's tools can read it.** It goes from the keychain, to the live server's memory, to the desk's
  socket, to the helper's memory, to the helper's stdout (a pipe to Claude Code), to Claude Code's memory. None of these is an
  environment variable, a command line, a file, a log or the model's context.
- **The helper is useless on its own.** It holds nothing. The desk answers only the exact helper command, under the Claude Code
  that the live server started for that run, while the run lasts. A model run can't start it (refused by name), and a Bash call
  can't start any other program.
- **The ticket is not a secret that unlocks the key by itself.** It is in Claude Code's command line, because Claude Code takes
  its settings there; a program that read it still isn't the helper under the run.
- **The guard only gets stricter.** Two names are added to the refusals; the never list, the hook's settings, the approvals and
  every pinned guard decision are unchanged (tested).
- **At the default settings nothing moves.** No desk, no ticket, no keychain question, the same launches byte for byte (tested).
- **Failures fail towards your subscription or a stop, never towards sending more.** A refused key stops the run and sets the
  key aside. A rate limit stops the run. Nothing is retried by itself, and confidential material rules (G5) are unchanged: this
  is still Claude.

## What happens when something goes wrong

| What | What Alan sees | What changes |
|------|----------------|--------------|
| Wrong, revoked or expired key (Anthropic: 401, `authentication_failed`, "Invalid API key") | The run stops: "Anthropic refused your Claude API key: it may be wrong, revoked or expired. Nothing was changed. Until you connect the key again in Settings › AI models, Claude runs use your subscription." | Later runs use the subscription, each with a step saying so, until the key is connected again or disconnected. The server's memory only, so a restart tries the key again. |
| No credit, or the account's spend limit reached (`billing_error`, "Credit balance is too low") | The run stops: "Anthropic won't take more requests on your Claude API key: …" | As above. |
| Rate limit on the key (`rate_limit`, 429, after Claude Code's own retries) | The run stops: "Your Claude API key is over Anthropic's rate limit for now. Nothing was changed: try again in a minute." | Nothing. The subscription's limit (G6) isn't touched. |
| The helper is refused, or the keychain is locked | The run stops: "creaite couldn't hand your Claude API key to Claude Code, so the run stopped. …" (Claude Code also shows the desk's plain reason, such as "unlock your Mac and try again".) | Nothing. |
| Claude Code didn't use the helper (its first event says another key source) | A step: "Claude Code didn't use your API key for this run (its key came from: …)." | Nothing; logged. |
| The key can't be set up for a run (an error in creaite) | A step: "Claude's API key couldn't be used (…), so this ran on your subscription." | That run uses the subscription. |
| The VIP check | Its existing "didn't finish" line. | A refused or unbillable key is set aside, as above. |

## The real-run check (not run: no agent may run a real Claude run)

**Nothing in this round is applied until this check has been run on a real Mac and has passed.** It checks the one thing the tests
can't: that Claude Code doesn't pass a helper's key on to the programs it starts (tools and hooks), in a run with tools and in a
tool-less run. It costs a few cents on Haiku. Run it in Terminal (zsh), on the Mac that runs creaite, with Claude Code at the
version creaite uses (`claude --version`; write it down).

**0. A throwaway key.** In the Anthropic Console, create a key named `creaite-g8-check` in a workspace with a $5 spend limit.
Copy it.

**1. Keep it in the keychain.** You are asked for it twice. Paste it each time; it is never on a command line.

```sh
D="$HOME/g8check"; mkdir -p "$D" && cd "$D"
security add-generic-password -s creaite-g8-check -a check -w
```

**2. The helper, two probes and the settings.**

```sh
cat > helper.sh <<'EOF'
#!/bin/sh
exec /usr/bin/security find-generic-password -s creaite-g8-check -a check -w
EOF
cat > probe.sh <<'EOF'
#!/bin/sh
{ echo "== env"; env; echo "== processes"; ps -axwwE -o pid,ppid,command; } > "$HOME/g8check/probe.out" 2>&1
echo probe-done
EOF
cat > hookprobe.sh <<'EOF'
#!/bin/sh
{ echo "== env"; env; echo "== processes"; ps -axwwE -o pid,ppid,command; } >> "$HOME/g8check/hook.out" 2>&1
exit 0
EOF
chmod 700 helper.sh probe.sh hookprobe.sh
printf '{"apiKeyHelper":"%s","hooks":{"PreToolUse":[{"matcher":"*","hooks":[{"type":"command","command":"%s"}]}]}}' \
  "$D/helper.sh" "$D/hookprobe.sh" > settings.json
```

**3. Two runs: one with a tool (as ask creaite), one tool-less (as AI on selected text).**

```sh
U=(-u ANTHROPIC_API_KEY -u ANTHROPIC_AUTH_TOKEN -u CLAUDE_CODE_OAUTH_TOKEN -u ANTHROPIC_BASE_URL)
env $U claude -p --output-format stream-json --verbose --model haiku --max-turns 3 \
  --settings "$(cat settings.json)" --allowedTools "Bash($D/probe.sh)" \
  -- "Run $D/probe.sh once with the Bash tool and reply with its output only." > run1.jsonl
env $U claude -p --output-format stream-json --verbose --model haiku --setting-sources "" --no-session-persistence \
  --settings "$(cat settings.json)" -- "Reply with the word ok." > run2.jsonl
```

**4. The checks.** The expected answer is in brackets.

```sh
grep -o '"apiKeySource":"[^"]*"' run1.jsonl run2.jsonl     # [both: "apiKeySource":"apiKeyHelper"]
grep -c probe-done run1.jsonl                               # [1 or more]
test -s hook.out && echo hook-ran                           # [hook-ran]
security find-generic-password -s creaite-g8-check -a check -w | grep -c -F -f - probe.out hook.out run1.jsonl run2.jsonl
                                                            # [every file :0]
security find-generic-password -s creaite-g8-check -a check -w | grep -r -l -F -f - ~/.claude 2>/dev/null
                                                            # [nothing printed]
grep -c 'sk-ant-' probe.out hook.out                        # [both :0]
```

**Pass:** every line gives the answer in brackets. Post the `claude --version` and "G8 real-run check passed" on #132.

**Stop (do not apply G8), and post the line on #132:**
- any count above 0, or any file listed under `~/.claude`: Claude Code passes the key on (to a tool, a hook or a file). Round 3
  must not be applied as designed;
- `apiKeySource` is anything but `apiKeyHelper`: Claude Code didn't use the helper from `--settings` (a managed policy, or a
  different version), so the design doesn't hold on this Mac.

**Inconclusive (run step 3 again once):** no `probe-done`, or no `hook-ran`: the tool or the hook didn't run, so nothing was
checked.

**5. Tidy up (always).** Revoke the `creaite-g8-check` key in the Anthropic Console, then:

```sh
security delete-generic-password -s creaite-g8-check -a check
cd ~ && rm -rf "$HOME/g8check" ~/.claude/projects/*g8check*
```

`probe.out` and `hook.out` hold your processes' environments, so they are deleted here. Worth repeating after a major Claude Code
update, as the behaviour checked belongs to Claude Code, not creaite.

## How it was tested

Fake only: a stand-in key (`fake-good-…TESTONLY`), an in-memory key store, a recorder in place of `claude -p`, and stand-in
"Claude Code" processes the test starts itself. No real key, keychain, provider, Claude run or network: the desk is a Unix socket
in a temporary folder. Each test builds a throwaway vault, applies rounds 1 and 2 and then round 3's diffs, and runs there.
`dev/tests/test_ai_proposal_g8_claude_key.py` (in `tests-g8.diff`), 21 tests, all pass:

- **Helper and desk, with real processes and macOS's real answers about them** (7): the run's helper gets the key on stdout only;
  refused with plain words on stderr, exit 1 and no key: another Claude Code with the ticket, the helper outside its run, a program
  that isn't the helper (even with the ticket), the helper without `-I`, a revoked ticket, a fourth ask in a minute, a keychain
  that says no, no key; the desk's folder is 0700 and its socket 0600, both gone after stop; its log lines hold no key and no
  ticket.
- **The helper's source** (1): standard library only (`re`, `socket`, `sys`); no environment, file or print.
- **Launches** (9): at the default settings all 13 launches are byte for byte rounds 1 and 2's and the desk is never opened. With
  a Claude key, all 12 kinds of run carry `apiKeyHelper` (the hook's settings otherwise equal, or a `--settings` of its own just
  before the prompt), naming this server's Python, `-I`, `keyhelper.py`, the desk and a ticket per run; the key is in no command,
  environment or event; the five variables are dropped even when the server has them; each ticket ends with its run; a direct
  call gets no helper. A refused key and an unbillable key: one card, set aside, the next run on the subscription with a step and
  the card's words, the key used again once connected again. A rate limit and a failed helper: one card, nothing set aside, the
  subscription's limit untouched. Another key source: a step. The VIP check: the helper, no key variables, its ticket ended,
  a refusal set aside. No vault file holds the key after runs on it.
- **Guard** (4): every guard mode refuses the helper and the desk (by name, not because the file is missing), as does the wrapper;
  permission rules naming them, `apiKeyHelper` or the desk's folder are refused, `doctor.py`'s still allowed; a settings file
  change adding `apiKeyHelper` is refused; the never list and the hook's settings equal rounds 1 and 2's; doctor's paths check
  doesn't flag the helper.

**Without round 3's diffs** (`CREAITE_PROPOSAL_UNPATCHED=1`) every test fails except three regression guards that pass either way
(the never list and hook unchanged, doctor's paths check, no key in the vault).

**Existing suites on a copy with rounds 1 (G1c included), 2 and 3 applied** (one at a time): test_reach 18, test_permissions 19,
test_ai_models 14, test_run_read_pinned 1, test_vip_tools_pinned 9, test_search_tools_pinned 7, test_prep_guard_confidential 12,
test_notes_guard 5, test_permissions_mcp 10, test_permission_file 20, test_permission_panel 14, test_ai_select 16,
test_settings_page 35, test_live_server, test_run_chat 17, test_no_real_names 2, test_health_fixes 30: all pass. Three fail, none
because of round 3 alone:
- `test_guard_pinned`: only G1c's ten rows (approved 17-10-2026, to re-record). Round 3's guard decisions are identical to rounds
  1 and 2's (compared row by row);
- `test_vip_single_call`: one source pin on the VIP command line, which round 1's G3 already changes (round 2's README); round 3
  adds two lines under it;
- `test_record_commands`: item 11 above (`keyhelper.py` in the record list).

`python3 dev/tools/check.py` passes on the branch and on the patched copy.

## Not settled

- **The real-run check** above: not run, by design. Everything waits on it.
- **The ticket in `ps`.** While a run lasts, any program running as Alan can see the ticket in Claude Code's arguments. It can't
  get the key with it (it isn't the helper under the run), and a model run can't run `ps`. Moving it out would need Claude Code to
  read its settings from a file creaite writes, which is a bigger change.
- **The desk trusts macOS's answer about who is asking.** A program running as Alan that could start the exact helper command
  under the run's Claude Code would get the key; nothing a model run can start can do that.
- **A refused key is remembered in memory only**, so a server restart tries the key again (one more failed run).
- **Claude Code's error words** for a refused key and for billing are matched from 2.1.288's stream and messages; a later version
  may word them differently (the run would then end as an ordinary failure, nothing set aside).
- **Claude Code may retry a 429 itself** before giving up; the card then comes after its retries.
