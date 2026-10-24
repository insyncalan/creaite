# Guarded chain for 2.6.3 (24-10-2026)

Base: `39c1060aaeffa0c47a03a3c8e0e48208d3cb9ed6` (`BASE3`), main after the 2.6.2 release; the 2.6.1 and 2.6.2 chains are already applied there.
The chain is `GUARDED-2.6.3.chain` (apply order). Apply it as ONE commit whose subject starts `Guarded 2.6.3 chain:` (Jarvis, at the cut).
The guard is `dev/tests/guarded_chain.py` (`CHAIN3_MARKER`, `CHAIN3_FILE`, `CHAIN3_SHA256`, `BASE3`/`BASE`); `python3 dev/tests/guarded_chain.py` prints all three pins.
Change the chain list or any listed diff, and `CHAIN3_SHA256` must be re-set (Alan's say).

## Chain (apply order)
1. `dev/proposals/327b/live_server.diff` - #327 B, fresh ask creaite sessions by default (owner `origin/v263-327b`, edcb17d8).
2. `dev/proposals/324/live_server.diff` - #324 #326 #332, File the minutes box (owner `origin/v263-324`, bf4fba34).
3. SLOT (not written): the three follow-up diffs from `origin/v263-lows` (draft_delivery.py into `guarded_chain.GUARDED`; review-expect mandatory at the route; the reworded 'fails closed' comment). Add each path to the .chain after 324 and re-set the pin.
4. LAST, only after Alan's "AM: approved": `dev/proposals/338/creaite-rules.after-chain.diff` (owner `origin/v263-338`, 74e56de3). The variant list is `GUARDED-2.6.3.with-338.chain` (not read by the guard until it replaces the main list).

## Pins
| List | CHAIN3_SHA256 |
|------|---------------|
| `GUARDED-2.6.3.chain` (327b, 324), set in guarded_chain.py | `3ea88c0a0bf283a10fc7b51ded796dec770e110c36d7f6c226863eb4b0daa48b` |
| `GUARDED-2.6.3.with-338.chain` (327b, 324, 338 after-chain) | `0bc7e8932e3437e2d6fb3998430ae977a37e73de43b071e3f93b7cc0f9938522` |
The with-338 pin was computed with the 338 diff's bytes from `origin/v263-338` 74e56de3 (path plus bytes, the same way `chain_digest` does). To use it, copy the variant over the main list, add `dev/proposals/338/` to the tree, and set the pin.

## Which 338 diff
`creaite-rules.diff` does NOT apply to main's rules file (main has the 2.6.2 chain's rules diffs applied: "patch failed: system/creaite-rules.md:21").
`creaite-rules.after-chain.diff` applies to main, and still applies after the 327b and 324 diffs (they do not touch the rules). Use `after-chain`.

## Re-verified (24-10-2026), no diff regenerated
`git apply --check` forward and reverse, in chain order, on `origin/main` 39c1060a (a detached scratch worktree: 327b, 324 apply; 324, 327b reverse; clean tree after).
`live_server.py` is untouched on `v263-line`, so the same holds there. The 327b and 324 diffs are byte for byte the branch versions.

## Guard checks
`dev/tests/test_guarded_chain.py` now runs every case for the 2.6.3 chain too (`GuardedChain3`) and has `AllThreeChains` (all three marked pass, unmarked third, extra edit, pin mismatch, later unmarked edit, base after the second). 2.6.1 and 2.6.2 behaviour is unchanged.
