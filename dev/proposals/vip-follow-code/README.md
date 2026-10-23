# Follow wording: guarded code changes (proposal, not applied)

Alan accepted the VIP / follow rules (23-10-2026; `dev/proposals/vip-follow-rules/` on `origin/v261-vip-rules`). The non-guarded half is built on branch `v262-follow`. These are the guarded half; Jarvis applies them with the rules diff so text and behaviour agree.

Defaults taken for the README's open questions: (1) reading (a), the flag is shown in the app only; (2) internal names keep the word (`vip.*` keys, `vip.json`, functions, routes, the `vip` flag); (3) the register's `Follow` column replaces `VIP`, the old column is still read, and the app renames it to `Follow` on the next register save; (4) the old `management` / `client` values are kept as an unshown internal value (follow reads as yes/no); (6) "make X a VIP" and "mark the VIP alerts seen" are still understood for one release (the skills say never to repeat the word back); (7) `drafts.VIP_RE`, `edit_ai.VIP_LOOSE`, `live_server.ALERT_WORD` and `test_vip_private.py` stay.

## Files

| File | Guarded file | What it does |
|------|--------------|--------------|
| `propose.py.diff` | `propose.py` | `person_vip` reads the `Follow` column, else the older `VIP` column. Without it a person ticked **Follow this person** after the branch is merged is not alerted (the app writes `Follow`) |
| `live_server.py.diff` | `live_server.py` | the check's lines ("Follow check: n new or updated alerts", "the follow check didn't finish", "the follow check failed", "skipped: nobody followed"), the check prompt's first words ("creaite follow check."), and `VIP_PRIVATE_RULE` reworded (keeps the enforcing phrase "never call or label a person a VIP") |
| `test_follow_guarded_262.py` | none | Copy to `dev/tests/` when the two diffs are applied |

`propose.py.diff` must be applied with the `v262-follow` branch (the app side writes `Follow`). `live_server.py.diff` is independent of it.

## Apply order

1. The 2.6.1 guarded chain, as in `dev/proposals/GUARDED-2.6.1.md` (nine diffs, then 283 `reach.diff` and `live_server.diff`).
2. `propose.py.diff`, `live_server.py.diff` (either order; distinct hunks).
3. `creaite-rules.md.diff` from `origin/v261-vip-rules` (`dev/proposals/vip-follow-rules/`).
4. Copy `test_follow_guarded_262.py` to `dev/tests/`.

## Verified (23-10-2026, throwaway detached worktrees, nothing committed applied)

- On `v262-follow` head (line2 plus the non-guarded changes): both diffs `git apply --check`, apply, `-R --check` and reverse cleanly.
- On that head with the whole 2.6.1 chain applied in the order above: both diffs apply and `-R --check`; the rules diff applies after them.
- The tests that pin the check's prompt and lines accept both wordings (`creaite VIP check.` or `creaite follow check.`), so they are green before and after.
