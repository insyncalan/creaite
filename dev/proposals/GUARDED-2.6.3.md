# Guarded chain for 2.6.3 (24-10-2026)

Base: `39c1060aaeffa0c47a03a3c8e0e48208d3cb9ed6` (`BASE3`), main after the 2.6.2 release; the 2.6.1 and 2.6.2 chains are already applied there.
The chain is `GUARDED-2.6.3.chain` (apply order). Apply it as ONE commit whose subject starts `Guarded 2.6.3 chain:` (Jarvis, at the cut).
The guard is `dev/tests/guarded_chain.py` (`CHAIN3_MARKER`, `CHAIN3_FILE`, `CHAIN3_SHA256`, `BASE3`/`BASE`); `python3 dev/tests/guarded_chain.py` prints all three pins.
Change the chain list or any listed diff, and `CHAIN3_SHA256` must be re-set (Alan's say).

## Chain (apply order)
1. `dev/proposals/327b/live_server.diff` - #327 B, fresh ask creaite sessions by default (owner `origin/v263-327b`, edcb17d8).
2. `dev/proposals/324/live_server.diff` - #324 #326 #332, File the minutes box (owner `origin/v263-324`, bf4fba34).
3. `dev/proposals/draft-delivery-guarded/draft_delivery.diff` (docstring anchor; draft_delivery.py is in `guarded_chain.GUARDED`), 4. `dev/proposals/expect-mandatory/live_server.diff` (/api/review refuses a missing `expect`; a dashboard tab left open from before 2.6.2 gets a reload message), 5. `dev/proposals/draft-comment/live_server.diff` (comment only); all from `origin/v263-lows` 467c86f4.
6. LAST, only after Alan's "AM: approved": `dev/proposals/338/creaite-rules.after-chain.diff` (owner `origin/v263-338`, 74e56de3). The variant list is `GUARDED-2.6.3.with-338.chain` (not read by the guard until it replaces the main list).

## Pins
| List | CHAIN3_SHA256 |
|------|---------------|
| `GUARDED-2.6.3.chain` (327b, 324, draft-delivery-guarded, expect-mandatory, draft-comment), set in guarded_chain.py | `6208c3068e72f16b154a3360ac09586c7cecb3a8602679af9882a3984e99b14a` |
| `GUARDED-2.6.3.with-338.chain` (the five above, then 338 after-chain) | `618b5fc27e15ea16914a3618d6f18caaa3e1d21691b0b7796359978f966a4c6a` |
The with-338 pin was computed with the 338 diff's bytes from `origin/v263-338` 74e56de3 (path plus bytes, the same way `chain_digest` does). To use it, copy the variant over the main list, add `dev/proposals/338/` to the tree, and set the pin.

## Which 338 diff
`creaite-rules.diff` does NOT apply to main's rules file (main has the 2.6.2 chain's rules diffs applied: "patch failed: system/creaite-rules.md:21").
`creaite-rules.after-chain.diff` applies to main, and still applies after the 327b and 324 diffs (they do not touch the rules). Use `after-chain`.

## Re-verified (24-10-2026), no diff regenerated
`git apply --check` forward and reverse, in chain order, on `origin/main` 39c1060a (a detached scratch worktree: all five apply in chain order, 338's after-chain diff applies after them and reverses; the five reverse last first; clean tree after).
`live_server.py` and `draft_delivery.py` are untouched on `v263-line`, so the same holds there. No diff was regenerated. `guarded_chain.py` and `test_guarded_chain.py` are `origin/v263-lows`' versions (it already holds the 2.6.3 machinery); this line adds only the list, the pin and BASE3 agreement.

## Guard checks
`dev/tests/test_guarded_chain.py` now runs every case for the 2.6.3 chain too (`GuardedChain3`) and has `AllThreeChains` (all three marked pass, unmarked third, extra edit, pin mismatch, later unmarked edit, base after the second). 2.6.1 and 2.6.2 behaviour is unchanged.
