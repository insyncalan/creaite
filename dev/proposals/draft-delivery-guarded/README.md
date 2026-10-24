# draft_delivery.py joins the guarded list (2.6.3)

Why: `system/scripts/draft_delivery.py` holds the PreToolUse hook that lets the Outlook create-draft call through only with exactly
the arguments shown (the 2.6.2 blocker was found there), but it was not on `dev/tests/guarded_chain.GUARDED`. A later edit now has to come
through a commit marked `Guarded 2.6.x chain:`, like the other guarded scripts.

## What changes
1. `dev/tests/guarded_chain.py` (not itself guarded, edited in the tree):
   - `"draft_delivery.py"` added to `GUARDED`.
   - A third chain: `CHAIN3_MARKER = "Guarded 2.6.3 chain:"`, `CHAIN3_FILE = dev/proposals/GUARDED-2.6.3.chain`, `CHAIN3_SHA256`, `SPEC3`,
     and `pin3` on `guarded_touched`.
   - **`BASE` moves to the 2.6.2 release commit** (`BASE3 = 39c1060a...`, main's merge). Reason: draft_delivery.py was written in the 2.6.2
     range by unmarked commits, so a range from the 2.6.1 release (`BASE2`) would report the whole file as a new guarded change. 2.6.2
     is published, so the check starts from it, as 2.6.2's did from 2.6.1. `BASE2`, `BASE_261` stay for the older chains' tests. This is the one
     decision for Alan: the base of the guard check rolls forward.
   - `CHAIN3_SHA256 = ""` until the 2.6.3 chain list is cut. An empty pin matches nothing, so a marked 2.6.3 commit fails closed until the
     pin is set with the list (`python3 dev/tests/guarded_chain.py` prints the value; set it only on Alan's say).
2. `dev/proposals/draft-delivery-guarded/draft_delivery.diff`: the chain entry. A docstring sentence in draft_delivery.py ("Guarded since
   2.6.3 ... changes only in a commit marked ..."). It is the cleanest form: a real, applying diff of the guarded file, so the first
   marked commit exercises the mechanism end to end (the file is changed in a marked commit and the guard reverses it). A README-only or
   empty entry would leave the chain with nothing to reverse and prove nothing. Comment-only; no behaviour change.

## Chain list line (first in the 2.6.3 list; it touches no other guarded file)
```
# draft_delivery.py guarded
dev/proposals/draft-delivery-guarded/draft_delivery.diff
```

## Checks
- `dev/tests/test_guarded_chain.py` (87 tests): every case also runs for the 2.6.3 chain; `DraftDelivery` (plain edit fails, removal fails,
  edit inside the marked commit passes, same edit unmarked fails, extra edit in the marked commit fails, later plain edit fails, the 2.6.2
  marker does not excuse it, an empty pin fails closed); `Chains2And3` (both marked pass, 3rd unmarked fails, base after the 2nd).
- Real tree (scratch worktree): `test_word_export_227` check 9 passes now; a plain edit to draft_delivery.py in an unmarked commit makes it fail;
  the anchor diff in a simulated `Guarded 2.6.3 chain:` commit (with a temporary chain list and pin) passes.
- `git apply --check` forward and reverse on origin/main, and with the other 2.6.3 diffs in the order below.
