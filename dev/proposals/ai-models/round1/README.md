# AI models (#132), round 1: storage and routing (proposal)

**Status: a proposal for Alan's yes. Nothing here is applied to `ai-models-132`, a shared branch or main.** The guarded changes
are diff files in this folder. The tests that check them are in `dev/tests/` and apply the diffs to a throwaway vault, never to
this repository.

Round 1 covers G1 (the key store), G2 (the model list), G3 (the chosen model in Claude runs) and G5 (confidential material only
to Claude). It also adds one item found while checking G1: G1c, the never list in the runs creaite starts itself. Round 2 is
G4, G6, G7, G9 and G10, plus the G8 options note.

## What Alan is being asked to approve

Answer each with yes, no or changes.

| # | Item | Diff | Recommendation |
|---|------|------|----------------|
| 1 | **G1 key store.** A provider's key is kept in this Mac's login keychain. The live server writes, reads and deletes it through Apple's Security framework, in its own process. No program is started, so the key never appears on a command line. | `g1-key-store.diff` | Yes |
| 2 | **G1 rules.** A model run may never run `providers.py`, in any mode, confirmed runs included, and nor may `system/scripts/run`. No permission rule may name `security`, the keychain folders, creaite's keychain items or `providers.py`, whatever is approved. No pinned guard decision changes. | `g1-key-store.diff` | Yes |
| 3 | **G1c (found while checking G1; changes 10 pinned guard decisions).** The runs creaite starts itself (Prep page, Current state, AI drafts, Shape, a transcript check or load) are refused the never list (secrets, the operating system), as ask creaite already is. Today the hook lets them read `~/.ssh`, `/etc` or the keychain file. | `g1c-never-list-held-runs.diff` | Yes, and re-record the pins |
| 4 | **G2 model list.** One HTTPS GET to `api.openai.com` or `api.anthropic.com` asks which models a key can use. These are the only hosts. The key goes in one header, TLS is verified, redirects are never followed, the call stops after 10 s and reads at most 1 MB. **This is creaite's first call to a service other than Microsoft 365, so IT may need to approve the egress.** | `g2-model-list.diff` | Yes, after IT |
| 5 | **G2: ignore proxy settings in the environment.** The call goes direct, so an `HTTPS_PROXY` left in the environment can never see the key. If IT requires a proxy, this needs a change. | in G2 | Yes, unless IT needs a proxy |
| 6 | **G3: the chosen model in every `claude -p` launch.** `--model opus\|sonnet\|haiku` is added for a kind of job Alan has changed. At the default settings every launch is byte for byte today's. The hook, approvals, tools, folders and cwd don't move. | `g3-chosen-model.diff` | Yes |
| 7 | **G3: "default" means today's launch.** The page recommends Haiku for quick edits, but today the tool-less runs (AI on selected text, Find updates) run on Sonnet (#126's pin). This proposal keeps Sonnet until Alan picks a model. The alternative is to make the default follow the page, which moves those runs to Haiku and gives tool runs an explicit `--model sonnet`. | in G3 | Keep today's (as built) |
| 8 | **G5: confidential material only to Claude, in the server.** `providers.route_for` is the server's only way to pick a model, and `send_allowed` is the gate every call to another provider must pass. The check fails closed: in round 1 no feature is yet declared "checked and not confidential", so every writing and quick-edit job stays on Claude. G4 (round 2) adds those declarations one feature at a time. | `g5-confidential-only-claude.diff` | Yes |
| 9 | **G5: a fix to the built routing policy.** At a limit, "Step down one kind" could send confidential writing to a quick-edit model of another provider. The new gate caught this in testing. | in G5 | Yes |
| 10 | **The `/api/ai/*` block in `live_server.py` (+150 lines) as non-guarded.** It can't start a run, read a key back or reach the record (see below). | (built) | Yes |
| 11 | **A test change committed on this branch:** `test_ai_models`' "not built" test now pretends to be off a Mac. With G1 applied, the test would otherwise write a fake key into the real keychain. It passes before and after the diffs. | committed | Yes |

**Order.** G1, G1c and G3 each apply to `origin/ai-models-132` (36e2b36) on their own. G2 needs G1 first, and G5 needs G3 first.
All five apply together in either order of the two pairs. Each was checked with `git apply --check` on a clean copy of the base.

## What this can reach and what it cannot

| Who | Can | Cannot |
|-----|-----|--------|
| **The live server** (Alan's own process) | Write, read and delete `creaite.ai.<vault id>.<provider>` items in the login keychain (account `creaite`). Call `https://api.openai.com/v1/models` and `https://api.anthropic.com/v1/models` with a key Alan pasted (G2). Start `claude -p` with `--model` set to one of three aliases (G3). | Read any other keychain item, call any other host or follow a redirect, use a proxy from the environment, or pass `--model` anything but `opus`, `sonnet` or `haiku`. It never puts a key in a URL, a log line, an answer, an error, a file, an environment variable or a command line. |
| **A model run** (ask creaite, a sweep, Prep, drafts, edit-ai, search, the VIP check) | Exactly what it can today, less G1c's change: Prep and the other runs creaite starts itself lose the never list. | Run `security`, `defaults`, `osascript`, `python -c` or any program other than one creaite script. Run `providers.py` by name or through `system/scripts/run`. Pass a creaite script the keychain's path. Read `~/Library/Keychains`: refused in ask, confirmed and sweep today, and in Prep and the held runs once G1c is applied. Search is covered under "Not settled". Call `/api/ai/*`: it has no web tool, no `curl` and no script that makes an HTTP call. Have a key in its environment: no key is ever in one. |
| **A permission rule** (any settings file, whatever is approved) | Everything it could before. | Name `security`, `Library/Keychains`, "keychain", `creaite.ai.` or `providers.py`. These are refused by `permissions.rule_refusal`, and so by `settings_problem`. |
| **Backups, logs, settings, the repo** | Hold provider ids and model ids (`ai.providers`), and debug lines with a host and an HTTP status. | Hold a key. The keychain is outside the vault, so the daily zip never contains one. The debug log gets status and host only, which is tested. |

## G1: the key store

**What it does.** `providers.KeychainStore` keeps one generic password per vault and provider:

- service `creaite.ai.<vault id>.<provider>`, where the vault id is the first 12 hex characters of a SHA-256 of the vault's real
  path, so two vaults never share a key;
- account `creaite`;
- label `creaite AI key (OpenAI)`.

It talks to the Security framework through `ctypes` (`SecItemAdd`, `SecItemCopyMatching`, `SecItemDelete`). `ctypes` is in the
standard library and the framework ships with macOS, so nothing is installed. `backend()` uses this store only on a Mac (`sys.platform == "darwin"`).
Elsewhere it keeps the not-built stand-ins, and tests keep their in-memory fake.

**Why not the `security` command.** `security add-generic-password … -w <key>` puts the key in the process table, where `ps`
shows it for the life of the call. Two other options were looked at:

- the prompt form (`-w` last, answered through a pseudo-terminal);
- `security -i` with the command on stdin.

Both avoid argv but still start a program and pass the key through a pipe. The ctypes route starts nothing. I ran a real round
trip on this Mac (add, read, exists, delete) with a fake key under a unique test name, and deleted it at once. It worked without
any prompt. The answer is therefore: **a safe pure-stdlib way exists**, and it is this one.

**How a key gets in.**

1. Alan pastes the key on the page.
2. The page POSTs it once, in the body, to `/api/ai/test` on 127.0.0.1 with the page token. The page then clears the field.
3. The server calls the provider (G2) and holds the key in its own memory until Done. That is 10 minutes at most; reviewing
   this window is G10, in round 2.
4. On Done, `/api/ai/connect` calls `store.put`, which first checks the key's shape (`[A-Za-z0-9._~+/=:-]{8,400}`), then
   deletes any earlier item and adds the new one.

The key never goes in a URL, a log line (only "openai key tested: 2 models"), a backup, an environment variable or a command line.

**How it is read back.** `store.peek(provider)` is the only way back. It is called by the live server immediately before a
provider call. No script other than `live_server.py` calls it, and a test enforces this. In round 1 nothing calls it yet: G2's
Test uses the key Alan just pasted. G4's direct call will be the first reader.

**Disconnect.** `store.remove` calls `SecItemDelete`. If the keychain refuses, the route answers in plain words and changes no
settings.

**`has()` never reads the secret.** It asks only whether the item exists. A keychain that can't answer (locked, refused) counts as
not connected, so nothing is sent. `connected()` and the page ask the keychain only about a provider that settings say is
connected. At the default settings the keychain is never asked, which matters for every page load, every run launch and every
test.

**How it interacts with the never list.** `reach.py`'s never list already names `~/Library/Keychains` (and `/Library`) for every
operation, so no tool may read the keychain files. That stays as it is. The store doesn't touch those files either: it asks
`securityd` through the framework.

The command `security` was not on any list. It is refused today only because the hook refuses every Bash call that isn't one
creaite script. G1 adds three explicit locks:

- `providers.py` is refused by name in the hook (`_script_refused`), in every mode including confirmed. Before G1, a confirmed
  run could run `system/scripts/run providers.py`, because an unclassified script is allowed when confirmed. It is harmless
  today, since the script has no command line, but it is now closed;
- the wrapper refuses `providers.py` (`wrap_problem`);
- `permissions.keychain_problem` refuses any rule naming the keychain command, folder, items or `providers.py`.

**What a model run could do to reach the key: nothing.** This is tested through `reach.decide` in modes ask, confirmed, sweep,
sweep held, prep and held. Each of these is refused in every mode:

- `security …` and `/usr/bin/security …`;
- `defaults read …`;
- `osascript -e '…security…'`;
- `python3 -c …`;
- `system/scripts/run providers.py` and `python3 system/scripts/providers.py`;
- `cat ~/Library/Keychains/login.keychain-db`;
- `env | grep KEY` and `printenv`.

Reading the keychain file is refused in ask, confirmed and sweep. In prep and held it is G1c's job.

**Belt and braces.** On the file-based login keychain, macOS trusts the program that created an item. For the store, that is the
Python that runs the live server. Another program asking for the secret, such as `/usr/bin/security` or Claude Code itself,
makes macOS ask Alan first. I did not trigger that dialog here, so this is macOS's documented behaviour, not something tested.

The same Python runs creaite's scripts, so the real protection is the one above: no script reads a key, and a run can't run
arbitrary Python. The wrapper refuses `-c`, paths and anything outside `system/scripts/`.

**Risks.**

- When Python is upgraded, macOS asks once whether the new Python may read the item. "Always Allow" answers it.
- A locked keychain answers "unlock your Mac and try again".
- Search's answer has no guard hook and `Read` is allowed. It could read the encrypted keychain file today, which is a
  pre-existing gap: the file can't be decrypted without the login password. See "Not settled".

## G1c: the never list in the runs creaite starts itself (found while checking G1)

Ask creaite's hook checks the never list first. The other runs creaite starts itself go through `reach.prep_decision`, which
checks only confidential notes and the form of a Bash call. These are the Prep page (mode "prep") and Current state, the AI
drafts, Shape and a transcript check or load (mode "held").

So the hook lets those runs read `~/.ssh/id_rsa`, `/etc/hosts` or the keychain file, list the home folder, or hand a creaite
script a secret's path. `system/scripts/run` still refuses that last one. `test_guard_pinned` records all of this as allowed.
These runs read mail, transcripts and documents, which are the places a prompt injection would come from.

The diff adds `never_reason_for`, the same check `hook_decision` makes, at the top of `prep_decision`.

**Pinned decisions that change** (`dev/tests/pinned/guard/decisions.json`; 10 rows, every one from allowed to refused; nothing
else changes):

| Mode | Call | Now |
|------|------|-----|
| prep, held | `Read <HOME>/.ssh/id_rsa` | refused: it holds secrets |
| prep, held | `Read /etc/hosts` | refused: part of the operating system |
| prep, held | `Glob **/*.md` in `<HOME>` | refused: the folder holds ~/.ssh |
| prep, held | `LS <HOME>` | refused: the folder holds ~/.ssh |
| prep, held | `Bash python3 system/scripts/report.py adhoc <HOME>/.ssh/id_rsa` | refused: it holds secrets |

With Alan's yes, the pins are re-recorded (`CREAITE_PIN_RECORD=1 python3 dev/tests/test_guard_pinned.py`). Without G1c, G1, G2,
G3 and G5 together leave `test_guard_pinned` passing unchanged.

## G2: the model list

`providers.HttpsLister` makes one GET with the standard library's `urllib`:

| | |
|---|---|
| **Hosts** | `api.openai.com` (`/v1/models`) and `api.anthropic.com` (`/v1/models?limit=1000`) only. They are fixed in `LIST_HOSTS`, and the address must be https. |
| **What is sent** | OpenAI: `Authorization: Bearer <key>`. Anthropic: `x-api-key: <key>` and `anthropic-version: 2023-06-01`. Also `Accept` and `User-Agent: creaite`. Nothing else. The key is never in the address. A key outside `[A-Za-z0-9._~+/=:-]{8,400}` is refused before any call, so it can't break a header. |
| **TLS** | The Mac's trust store, hostname checked, TLS 1.2 or later. |
| **Redirects** | Never followed. A 3xx is "couldn't reach", and exactly one request is made. |
| **Proxy** | None from the environment (`ProxyHandler({})`). |
| **Limits** | 10 s, at most 1 MB read back (`LIST_CAP`), at most 500 ids, and ids of 200 characters or less. |
| **Errors** | 401, 403, 429 or any other 4xx → `KeyRefused(status)`, which the page shows as "OpenAI did not accept this key (401)…". A 5xx, a 3xx, a timeout, a TLS or network failure, an oversized answer or one that isn't a model list → `ProviderUnreachable`, shown as "Couldn't reach OpenAI…". Errors carry the host and a status only, never the key or the body, and are raised `from None` so no chained error carries either. |
| **Logged** | `<host> model list: <status>` or `… unreachable (<error type>)` only. |

Tests use a local fake HTTPS server on 127.0.0.1, with a certificate made by `openssl` for the test and trusted only by the
context the test passes in. There is no real provider and no network.

## G3: the chosen model in every Claude run

**Where the flag goes.**

- `Run.__init__` (the run engine): after `launch_context(policy)`, `with_model(more, run_model(policy)[0])`. For a tool-less
  kind this replaces #126's pinned `--model sonnet`. For every other kind it adds `--model <alias>` before the `--add-dir`
  folders.
- The VIP check's own launch gets `with_model([], run_model("vip")[0])`.
- These are the only two `claude -p` launches. A test counts them.

**Which runs are which kind of job** (`KIND_JOB`):

- **tools:** ask creaite, a sweep, Search, Prep, a transcript check or load, the VIP check;
- **write:** Current state, the AI drafts, Shape, a closed meeting's Shape;
- **quick:** AI on selected text, Find updates.

No in-app run is "guard". That kind of job is the build work on creaite's own guard files.

**At the default settings nothing changes.** `run_model` returns None while a job's choice equals its default, and `with_model`
then returns the arguments untouched. The test builds a real `Run` for 13 cases in an unpatched vault and a patched one, with
`subprocess.Popen` replaced by a recorder. The 13 cases are:

- a chat, a confirmed request, a typed sweep and Close the day's sweep;
- Search, Prep, a Current state draft, a transcript check and load, and an alert draft;
- edit-ai, a closed Shape and Find updates.

It compares the command, the cwd, the environment creaite adds and the run's steps, byte for byte. It also compares
`TOOLLESS_KINDS`, `NO_CONTEXT_ARGS`, `NO_CONTEXT_ENV`, `KIND_ARGS`, `KIND_TOOLS`, `KIND_DENIES`, `run_policy`,
`launch_context` and `guard_mode`. Every one of these is equal, including the guard hook's `--settings`. Approvals
(`reach.APPROVALS`, the card routes) are not in the diff at all.

**A chosen model** adds only `--model <alias>`, or replaces the pin. The test checks that the rest of each command is identical,
and that choosing a model for writing moves only Current state, the drafts and Shape.

**A bad choice fails closed.** In each case below, the run starts today's launch and the run says why in a step, with a debug
line that holds ids only:

- an unknown id (`claude:--dangerously-skip-permissions`, `claude:../../x`, `nosuch`);
- a model not on offer;
- another provider's model (`claude` runs only Claude; direct calls are G4);
- a model that can't use tools for a job that needs them;
- anything not in `opus`, `sonnet` or `haiku`;
- a settings file that can't be read.

## G5: confidential material only to Claude

**Where "confidential" is decided today:**

- a meeting marked confidential in the calendar (`sensitivity`): Shape then runs as the tool-less `shape-closed`, and drafts
  keep only its title and times;
- a note with `confidential: true`: `notes.held`, the hook's confidential check in modes prep and held, and
  `prep_page.hold_confidential`;
- text marked confidential or restricted: `drafts.SECRET_WORDS` and `secret()`, which refuse a draft;
- `client_leak`'s gate: `Client-safe: no`, labels, and the words confidential, restricted and documents/.

**The single choke point.** `providers.route_for(job, settings, text, declared)` works in three steps:

1. It decides confidentiality with `confidential_job`, which fails closed:
   - a tools job is always Claude's;
   - `declared=True` is confidential;
   - `declared=None` (nobody checked) counts as confidential;
   - text marked confidential, restricted or `Client-safe: no` is confidential;
   - only `declared=False` with clean text is not.
2. It calls `route`.
3. It checks the answer with `send_allowed`, which raises for any non-Claude model unless the material is shown to be clean.

The server's call site is `model_choice` in `live_server.py`, which every run launch goes through. A test checks that
`live_server.py` never calls `route` directly.

**Round 1 declares nothing clean.** Every writing and quick-edit job is "unchecked", and a closed Shape is "declared". If Alan sets
writing to OpenAI, the run still starts on Claude and says either "OpenAI isn't used for this yet. So Claude ran it." or, for a
closed meeting, "Confidential material is only ever sent to Claude. So Claude ran it." G4 adds, feature by feature, the server's
own check that lets a clean job go elsewhere. Each of those is its own reviewed hunk.

**Tested.** With OpenAI "connected" (test stand-ins) and chosen and accepted for writing and quick edits, confidential material
routes to Claude in every case: declared, unchecked, marked confidential and `Client-safe: no`. That holds at no limit and at a
limit with each of Ask me, another connected model and Step down. Clean, declared material does reach OpenAI, so the gate is not
a blanket.

The Step down case found the gap fixed in item 9. Before the fix, `route` stepped confidential writing down to OpenAI, and
`send_allowed` raised.

## Is the `/api/ai/*` block (+150 lines in `live_server.py`) acceptable as non-guarded?

**Yes.** These are the facts from `git diff origin/v210-combined origin/ai-models-132 -- system/scripts/live_server.py`.

**What the block is.** Eight POST routes dispatched with the set-up routes. `do_POST` checks `authorised()` first: the Host header
must be local, and `X-Creaite-Token` must equal this server's `TOKEN`. `TOKEN` is random at every start, kept in memory and given
only to the page; it is never written to a file.

| Route | Reads | Writes | Key |
|-------|-------|--------|-----|
| `state` | settings `ai.*`, `store.has` | nothing | none |
| `test` | the key in the body | holds key and ids in server memory until Done or Cancel (10 min max) | in, once, in the body. The answer has a one-time id, model ids, labels and grades only. |
| `connect` | the held key | `store.put`; `ai.providers` via `settings_catalogue.save` (a backup and a log line per key) | to the store only |
| `forget` | | drops the held key | none |
| `offer` | settings | `ai.providers`, and `ai.jobs.*` / `ai.accepted_weaker` / `ai.on_limit` resets | none |
| `disconnect` | settings | `store.remove`, then the same settings | none |
| `choose` | settings | `ai.jobs.<job>`, `ai.accepted_weaker` | none |
| `limit` | settings | `ai.on_limit` | none |

**What it does not touch.** It starts no run, changes no permission file and touches nothing in the record (`tracker.py`, the
database, staging, approvals). It reads no file but `system/config/settings.json`. No route returns a key, and nothing is
logged but ids, counts and statuses.

**Could a model run call it? No.**

- `WebFetch` is denied in every run.
- Bash runs only one creaite script, and `curl` is denied by name as well.
- The only creaite script that makes an HTTP call is `launch.py`, which runs are refused.
- Microsoft 365 tools can't reach 127.0.0.1.

G1 changes two of its routes, to answer a keychain refusal in plain words. They remain non-guarded.

## How it was tested

- **Five new test files**, one per item, plus `dev/tests/ai_proposal_support.py`. Each builds a throwaway vault, applies its
  diffs with `git apply` and runs its checks there in a subprocess:
  - `test_ai_proposal_g1_keystore.py`: 16 tests, 15 run (the real keychain test is opt-in);
  - `test_ai_proposal_g1c_held_never.py`: 2;
  - `test_ai_proposal_g2_lister.py`: 13;
  - `test_ai_proposal_g3_run_model.py`: 7;
  - `test_ai_proposal_g5_confidential.py`: 6.

  All pass.
- **Opt-in real keychain round trip.** `CREAITE_KEYCHAIN_LIVE=1` runs it on a Mac with a fake key and a unique test name, then
  deletes it. I ran it once and it passed.
- **Without the diffs, they fail.** `CREAITE_PROPOSAL_UNPATCHED=1` builds the same vaults with no diff. Every test fails except
  four regression guards that check behaviour which must not change:
  - G1: reading the keychain file is refused in ask, confirmed and sweep, as today;
  - G1c: ordinary reads still pass;
  - G3: the default launches and the launch tables equal the unpatched ones.
- **Hunk by hunk.** Each diff was applied with one hunk left out at a time (`CREAITE_PROPOSAL_DIFFS`), and the item's test was
  run. The results are in the "Hunk-by-hunk" section below.
- **The existing suites on a copy with all five diffs applied:** see "Existing suites" below.
- **`dev/tools/check.py`** on the patched copy: see "Existing suites" below.

### Hunk-by-hunk

Every one of the 28 hunks is needed. Leaving any single hunk out makes its item's test fail:

| Diff | Hunks |
|------|-------|
| G1 | 15 |
| G1c | 2 |
| G2 | 3 |
| G3 | 4 |
| G5 | 4 |

Two gaps were found and closed on the way:

- G1's two small `peek` stubs now have a test.
- G5 no longer passes the run's text into the launch, because nothing reads it until G4.

### Existing suites

These were run one at a time on a copy of `origin/ai-models-132` with all five diffs applied. All pass:

- `test_reach` 18
- `test_permissions` 19
- `test_record_commands` 9
- `test_ai_models` 14
- `test_ai_models_browser` 2
- `test_vip_tools_pinned` 9
- `test_search_tools_pinned` 7
- `test_run_read_pinned` 1
- `test_prep_guard_confidential` 12
- `test_notes_guard` 5
- `test_permissions_mcp` 10
- `test_permission_file` 20
- `test_permission_panel` 14
- `test_no_real_names` 2
- `test_ai_select` 16
- `test_settings_page` 35

`test_guard_pinned` fails only on G1c's 10 rows listed above, and is unchanged with G1c left out. There is no
`test_guard_backslash` in this tree.

`dev/tools/check.py` reports "check: OK" both on the patched copy and on this branch. Getting there meant splitting
three functions to stay under the complexity limit: `HttpsLister.models` into `fetch` and `ids`, `route`'s step-down into
`stepped_down`, and `card`'s Claude sign-in into `claude_auth`. `run_model` reads its inputs through `model_choice`.

## Not settled

- **IT approval of the egress** to `api.openai.com` and `api.anthropic.com` (G2), and whether a proxy is required (item 5).
- **Search's answer** has no guard hook and `Read` is allowed (Alan, #60), so it could read the encrypted keychain file. It can't
  decrypt it. Whether Claude Code reads outside the vault and `--add-dir` folders with a bare `Read` allow wasn't tested, because
  that would need a real run. A small round 2 item could add the never list's `Read(…)` denies to Search's deny list, which
  would change `test_search_tools_pinned`.
- **The keychain's "allow this program?" prompt** for a program other than the creating Python wasn't triggered, deliberately,
  to avoid a dialog. The claim relies on macOS's documented behaviour.
- **Claude by API key (G8)** is a decision, not a build. G1 can store a Claude key, but nothing uses it, and no key goes into any
  run's environment.
