# #132 AI models: security design v2 (for 2.7)

Status: design only, no code. Version 2 folds in the independent paper review of the one-page design (20-10-2026). Nothing here is built until Alan decides the open points at the end and the diffs (guarded files) have had an independent review.

Scope: G8 (Claude by API key), the key store, other providers (OpenAI first), the confidential gate, the daily cap, and what happens when the Claude limit is reached.

## 1. What can go wrong

1. **The key leaks:** into the vault, settings, backups, logs, chat history, a command line, the process environment, a file under the home folder, or anything the model can read or run.
2. **Confidential text reaches another provider.**
3. **Cost runs away** once Claude is billed per token.
4. **The key is swapped:** every later prompt then goes to someone else's account.
5. **A hostile invite, mail, transcript or provider reply steers a run** (all of it is untrusted text).

## 2. Key storage: macOS Keychain

- One item per provider (service `creaite`, account = provider). Nothing about the key is written to the vault, `settings.json`, staging, the daily backup zip, git, or the debug log. Settings holds only "a key is stored: yes/no" kept in memory from the last successful read, never a probe on page load.
- **Written without a command line.** `security add-generic-password -w <key>` puts the key in the process list. Use the Keychain interface from Python directly (ctypes, no install) or `security -i` with the command on standard input. A test watches the process list during the write.
- **Access list (gap 3).** An item written by a python binary trusts that binary, so any script run by the same python could read it with no prompt. Therefore:
  - no creaite script command prints, copies, returns or exports the key; `reach.SCRIPT_COMMANDS` has no "get key" command; the reader is a function inside the live server process only, not importable from a script the model can run with arguments;
  - the item's access list names the live-server python binary; `system/scripts/run` picks the newest python each time, so after a python upgrade the item is unreadable: that state is "re-enter the key" in Settings, never a silent macOS dialog on a headless server (read with the "no UI" flag so it fails instead of prompting).
- **Read only by the live server**, in memory, at the moment a run starts. The page never receives it (only "connected" and the model list). It is never shown again after entry.

## 3. Delivering the key to Claude Code (gap 1, gap 2)

The key must reach the `claude` process without being readable by the model, by another process of the same user, or by a file.

- **Not acceptable on its own:** an environment variable on the child. On macOS any process of the same user can read another's environment (`ps eww -p PID`, `ps -E`), and Claude Code's own tool subprocesses inherit it unless scrubbed.
- **Preferred:** Claude Code's `apiKeyHelper` setting, given in a per-run settings file (`--settings`) that names a helper which prints the key. The helper is itself a read path, so it must be callable only by that process: it connects to a one-use, mode-0600 socket the live server opens for the run and closes after the first read (or reads a one-use token the server revokes after one use). It is not a creaite script command and is not on any permission allow list.
- **Fallback if the helper route is not possible:** the environment variable, with these conditions all tested: the child is the only process that has it; every tool subprocess it starts has it removed; a same-user second process cannot read it with `ps eww`/`ps -E` (this fails on macOS, so the fallback needs Alan's explicit acceptance as a known limit).
- **Claude Code may store a fragment of a key it is given** (an approval record with part of the key under its own config in the home folder, which ask creaite may read). Verify on the installed version with a canary key; if it does, use a per-run config folder inside a mode-0700 temporary directory deleted at the end of the run, outside the home folder's readable config.
- Before and after every run: grep the vault, staging, backups, the git history, logs, `~/.claude`, the chat history, the process list and the environment for the canary.

## 4. Entry, change and removal of the key (gap 4)

- A page-only route, like #255's: token header, Host, same-origin, OPTIONS refused. ask creaite cannot call it (the guard hook refuses `curl`, `python -c`, `launch.py <url>`), and it is not a script command.
- Never logged: not the body, query, headers or exception text. `autocomplete="off"`; the field is cleared from page state at once; the field must not appear in images attached to ask creaite (clear before any attach).
- **Replace and remove are the same route and are the dangerous ones** (a swapped key sends every later prompt elsewhere): replace needs a confirm that names the provider and shows the last four characters of the old key only, writes a log line with the provider name and the result only, and sets "key changed" on the Usage tab.
- Removal deletes the Keychain item and says so.

## 5. Redaction everywhere (gap 5)

One redactor on the debug log, run output, staging records, chat history and the Usage tab, for the key itself (exact and in common encodings) and the usual prefixes. Provider errors and the CLI's stderr can echo part of a key. Test: an error carrying the canary is stored masked in every one of those places.

## 6. The confidential gate: an allow-list with taint (gap 7)

- **One function builds every request to a non-Claude provider.** Nothing else may open a network connection to a provider (a test greps every module for `urllib`, `http.client`, `socket`, `ssl`, `curl`, with an allow-list of exactly one).
- A payload is a list of parts. Each part carries a **provenance** set where the text is read (never guessed from the words). A part is sendable only if its provenance is in a fixed set of "may go" kinds (for example: text the user typed in the request itself; a public template). Everything else is refused: confidential notes, meetings and projects, client-restricted items, **and anything whose provenance is unknown** (fails closed).
- **Taint:** the payload's provenance is the lowest of its parts; one unknown part refuses the whole payload.
- Places confidential text can be laundered into a sendable part, to be tested fail-first: a summary or tag in `system/search/`; a proposed item, tracker row or the Review sheet derived from a confidential meeting; a note Alan copied from a confidential meeting; a project that becomes confidential after items exist; the followed-people gist; text pasted into ask creaite; a file attached by hand; the model's own earlier reply quoting confidential text.
- Same property tests and mutants as the client-export check: a mutant that treats "unknown" as sendable must go red.
- **Network rules for the one function:** host allow-list is exact (not suffix: `api.provider.example.evil.test`, `host@evil`, trailing dot, IPv6, port, punycode) and lives in code, not in settings; TLS verified; no redirects; proxy environment variables ignored or fixed; timeouts; response size cap; the reply is text only and is **data**, never run as instructions (a provider reply fed into a run with tools is an injection route and is treated as untrusted input).
- A job that needs tools never goes to a provider that cannot use them.

## 7. The cap (gap 6)

- Counted from the provider's returned usage, in dollars, per local day (the vault clock).
- **Reserve before a call:** every request sets `max_tokens`; the largest possible cost is reserved, so parallel runs and retries cannot overshoot. An agentic run checks between turns. A crash mid-run counts the reserve.
- The counter lives where ask creaite cannot write it (not in `settings.json`'s run-writable folders). A failed counter write stops the run (never allows).
- Per **kind of job** caps plus a total, a low default, adjustable; cap zero is a valid setting; the run stops with a plain message and the reset time when reached.
- API runs are their own kind on the Usage tab, with dollars.

## 8. When the Claude limit is reached

- Never an automatic switch for confidential work.
- With an API key configured and under its cap: **ask each time at first** (Alan's decision to confirm); the screen says which account is billed.
- Otherwise stop with the reset time and offer to wait.
- Per-project and company-policy switches: some clients or the firm may not allow API use at all (retention and terms differ from the subscription). Default off per project until set.

## 9. Test list for the build

- **Network:** the one-function grep; exact host allow-list cases; redirects refused; proxy variables ignored; size and time caps; a hostile reply is data.
- **Key:** canary through enter, run, error, crash, change and remove; grep of the vault, staging, backups zip, git, logs, `~/.claude`, chat history, process list and environment; a same-user second process cannot read it; ask creaite's Bash, file reads and loopback HTTP cannot reach the item (real hook, as for #255); no script command returns it; python-upgrade state shows "re-enter the key".
- **Gate:** the laundering list above as fail-first cases; mixed payloads; encoding tricks that hide provenance text; a mutant on every branch.
- **Cap:** parallel runs, retry storm, a stream aborted mid-reply, day rollover, a failed counter write (must stop), cap at zero, per-kind and total.
- **Limit reached:** the switch happens only after Alan's yes; the screen names the billed account; the per-project and company switches.

## 10. Open for Alan

1. Order: G8 (Claude by API key) first, OpenAI later. Recommended: yes (G8 adds no new place for confidential text to go).
2. Cap: per kind of job plus a total, low default (a number Alan picks).
3. Limit reached: ask each time at first.
4. Is API use allowed by the firm's policy and by each client? Default off per project until set.
5. If the helper route in section 3 is not possible: accept the environment fallback as a known limit, or stop and find another delivery.

Guarded files (`reach.py`, `live_server.py`, `permissions.py`) change only as diffs for Jarvis to apply after Alan's approval of the exact diff and an independent review.
