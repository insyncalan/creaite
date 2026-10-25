# Design note (#355 L1): the guard's file list has gaps

Status: a note only. Nothing here changes `dev/tests/guarded_chain.py` or any guarded file. A change to that check is guarded and
goes in by a chain diff and a Full review, on Alan's say.

## What is on the list and what is not

`guarded_chain.GUARDED` (line 15) names ten scripts: `tracker.py`, `filechange.py`, `reach.py`, `permissions.py`, `backup.py`,
`update.py`, `live_server.py`, `client_leak.py`, `edit_ai.py`, `draft_delivery.py`. `_is_guarded(f)` also requires the path to start
with `system/scripts/`.

The brief for this repository names more as guarded than the check covers:

| File | Why it matters | On the list? |
|------|----------------|--------------|
| `system/creaite-rules.md` | The rules every run reads; an extra line is an instruction | No (not a script) |
| `system/scripts/review.py` | Decides what an approval writes | No |
| `system/scripts/propose.py` | Writes the proposals and the settings | No |
| `system/scripts/build_dashboard.py` | Builds the page Alan reads and decides on | No |
| `system/scripts/paths.py` | Every location comes from it | No |
| `system/scripts/schema.sql` | The rulebook for the record | No |
| `VERSION`, `.claude/settings*.json`, `.github/` | Release and permission state | No |

So an extra line in any of these, inside a commit that carries the chain mark, passes the check: the check never looks at the file.
The 2.6.4 chain does list one diff for `creaite-rules.md` (`338/creaite-rules.after-chain.diff`), but nothing compares that file with
what the diff alone would make.

## A second gap: part of the chain

`_marked_chains` takes the files a marked commit changed (`own`) and asks `chain_explains` whether reversing the chain on those files
gives the parent. It never asks whether `own` is every file the chain's diffs touch. A marked commit that leaves out one file of the
chain, such as every `reach.py` change, passes: its remaining files reverse correctly and the missing file is not looked at.

## Why it is not yet closed

- Adding names to `GUARDED` changes what counts as guarded for every earlier range too. The 2.6.1 to 2.6.3 chains never touched
  `schema.sql`, `review.py` and the rest, but they did touch files under `.claude/` and `system/` in ordinary commits, so a naive
  widening would report old, approved work as unexplained.
- `_is_guarded` is a path test on `system/scripts/` only. The rules file, `VERSION`, `.claude/` and `.github/` are not under it.
- The pin (`CHAIN4_SHA256`) covers the diffs, not the list of files, so a wider list needs no new pin, but the base must be a commit
  from which the new files are unchanged or explained.

## The diff shape (one guarded file, `dev/tests/guarded_chain.py`)

1. Replace the tuple and the path test with two sets:
   - `GUARDED_SCRIPTS`: the ten now listed plus `review.py`, `propose.py`, `build_dashboard.py`, `paths.py`; matched under
     `system/scripts/`.
   - `GUARDED_OTHER`: exact paths `system/creaite-rules.md`, `system/scripts/schema.sql`, `VERSION`, `.claude/settings.json`,
     `.claude/settings.local.json`, and the prefix `.github/`.
   - `_is_guarded(f)` is true for either.
2. In `_marked_chains`, after computing `own`, require `own` to equal the set of files named in the `+++ b/` lines of the chain's
   diffs that are guarded (read from the parent's tree, as the pin is). A difference returns `(None, set())`, which already reports the
   net change as unexplained.
3. Keep the existing tests green by giving the 2.6.1 to 2.6.3 ranges a `since` base: the wider list applies from `BASE4` only
   (`GUARDED_FROM = {"BASE4": ...}`), so approved history is not re-judged.
4. New tests with a mutant each: an extra line in `creaite-rules.md` inside the marked commit is reported; a marked commit that omits
   one chain file is reported; the 2.6.4 chain itself still passes.

## Is it guarded?

Yes. `dev/tests/guarded_chain.py` is the check on the guarded files, so changing it needs a chain diff and a Full review. Ordinary
work must not edit it. Release it in 2.6.4b or later, on Alan's say; until then the review of each marked commit has to read the rules
file and the unlisted files by hand.
