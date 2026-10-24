# 2.6.4 candidate chain: lists and pins (for the cut)

Not the real chain: `GUARDED-2.6.4.chain` stays empty and `CHAIN4_SHA256` unset until Jarvis cuts it. These are the candidate lists and what
their pins would be, computed with `guarded_chain.chain_digest` (sha256 over each listed diff's path and bytes, in order, read from the commit).
The pin changes if any listed diff changes by one byte: compute it again at the cut (`python3 dev/tests/guarded_chain.py` prints it once
the real list is in place).

Base: main (799da01c and the docs commits after it; engine files identical to the 2.6.3 release e6389af8). The order is the order of use:
345, 346, 334, line-reach, 292-tracker (`tracker.diff`, then `live_server.diff`), then 338 last.

| List | Files | Pin (sha256) |
|---|---|---|
| `GUARDED-2.6.4.candidate.chain` (345, 346, 334, line-reach, 292-tracker x2) | `GUARDED-2.6.4.candidate.chain` | `f9b05ae23346d23b4878731bdc69c998ab9a476f33d571dab32763fee3ea89e0` |
| `GUARDED-2.6.4.with-338.candidate.chain` (the same, then 338) | `GUARDED-2.6.4.with-338.candidate.chain` | `46c5fd81e62ef6d2b9b915db910277977652f879b84e4575b975fdc4824d84b3` |
| without the tracker diffs (345, 346, 334, line-reach): drop the last two diff lines of the first list | -- | `6cf5b3c879149f4951067b82768bd2107bf09a3ae93c994252b219546822a0ee` |
| without the tracker diffs, with 338 (drop the two 292-tracker lines of the second list) | -- | `4738653c44fbf4ff8b28cf33d962869006fa2ffaf9720e9b9f397a48eff5cb0d` |

The first two pins were checked with `chain_digest` on the committed candidate files; the last two were computed the same way over the
shorter lists (no file holds them).

## Checked on main 799da01c (scratch tree)

Each list, in order, with `git apply --check` before every diff and then applied; then reversed in the opposite order: all four lists
apply and reverse clean (no file left changed). The guarded files touched: `live_server.py`, `reach.py`, `tracker.py`, and with 338
`system/creaite-rules.md`. 338 applies unchanged on main (66,315 B to 32,736 B, a 50.6% cut, about 8,180 tokens a run).

## Goes in with the chain, not in it

- `system/scripts/ai_budget.py` and `start_tokens_report.py` (from v264-line): the line-reach entries and the 334 gate need them, same release.
- `system/templates/creaite-reference.md` (in this branch): the rules slimming moves long text there; same release.
- `dev/proposals/292-tracker/plain_words_baseline.diff` (an ordinary file, not a guarded diff): `test_plain_words` fails in the other
  direction until it is in; it was made against the v264-line baseline.
