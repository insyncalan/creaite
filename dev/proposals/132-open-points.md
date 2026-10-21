# #132 AI models: the open points for Alan (one line each)

Source: `dev/proposals/132-design-v2.md`, section 10, plus the two points the independent review of the design added. Release: 2.7. Nothing is built until these are answered. Each line has what is asked, the recommendation, and why it matters.

1. **Order.** Ship G8 (Claude by API key) first and OpenAI later? **Recommended: yes.** G8 adds no new place for confidential text to go; OpenAI does, so its gate must be proved first.
2. **Daily cap.** Which number, and per what? **Recommended: a cap per kind of job plus a total, with a low default (for example 5 dollars a day in total), adjustable.** The cap is counted from the provider's returned usage, reserved before each call, and kept where ask creaite cannot write it.
3. **When the Claude limit is reached.** Continue on the API key automatically, or ask each time? **Recommended: ask each time at first**, and the screen names the account that is billed. Never an automatic switch for confidential work.
4. **Firm and client policy.** Is API use allowed by the firm's policy and by each client (retention and terms differ from the subscription)? **Recommended: default off per project until it is set**, plus a company-wide switch.
5. **If the helper route is not possible.** The key reaches Claude Code through its `apiKeyHelper` (a one-use socket). If that cannot be made to work, accept the environment-variable fallback as a known limit (another process of yours can read it with `ps eww`), or stop and find another way? **Recommended: stop and find another way; do not accept the fallback silently.**
6. **Key entry and change.** Replacing or removing the stored key sends every later prompt elsewhere, so it needs a confirm that shows the provider and the last four characters of the old key. **Recommended: yes**, and a log line (provider name and result only).
7. **Keychain after a Python upgrade.** The stored key trusts the exact Python that wrote it; after an upgrade it becomes unreadable. **Recommended: show "re-enter the key" in Settings; never a silent macOS dialog on the headless server.**

Not for Alan: the build, the tests and the guarded diffs (`reach.py`, `live_server.py`, `permissions.py`) follow after these answers, each diff approved by Alan and independently reviewed before Jarvis applies it.
