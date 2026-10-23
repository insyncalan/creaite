# Guarded chain for 2.6.2 (23-10-2026)

Base: `5bf7da29e22e9b5b9b5c6b494c357280df4e4c4b`, the published 2.6.1 release commit (the 2.6.1 chain is already applied there).
The chain is `GUARDED-2.6.2.chain` (apply order). Apply it as ONE commit whose subject starts `Guarded 2.6.2 chain:`.
The guard is `dev/tests/guarded_chain.py` (`CHAIN2_MARKER`, `CHAIN2_FILE`, `CHAIN2_SHA256`, `BASE2`/`BASE`); `python3 dev/tests/guarded_chain.py` prints both pins.
Change the chain list or any listed diff, and `CHAIN2_SHA256` must be re-set (Alan's say). Owners of the listed diffs: small `origin/v262-small`, discard-undo `origin/v262-discard-undo`, draft-delivery `origin/v262-183h` 68eb5391 (live_server 0fb173ec and rules-and-skill b1fb8d96), follow code `origin/v262-followb` (identical to `v262-follow`),
follow rules `origin/v261-vip-rules`. Rebuilt on `v262-line` (23-10-2026): every diff is byte for byte the version in the tree; none was regenerated except the ones named under "Changed on the line" below. The review-expect diffs and the discard-undo review.py/reach.py/live_server.py diffs are the later versions (not the ones the first chain listed); the .chain list order is unchanged.

## Order (chosen)
1 inbox-upload live_server; 2 review-expect review.py; 3 review-expect live_server; 4 discard-undo review.py; 5 discard-undo reach.py;
6 discard-undo live_server; 7 draft-delivery live_server; 8 emit-event-txn tracker.py; 9 follow propose.py; 10 follow live_server;
11 183h rules-and-skill; 12 VIP/follow rules. Emit is `origin/v262-emit` 9b1f7f30 as regenerated on the line (round 2);
discard-undo's live_server diff says "suggestion", not "proposal" (plain words).
F1 (nullable columns, writer pins) and #250 (fetch transcripts) were cut from the line (23-10-2026); their branches are untouched.

## Orders tried on v262-line (rerun 23-10-2026 on the line's tree: the chain order forward and reversed, all 120 permutations of the five live_server.py diffs, review.py in both orders: all apply and reverse, clean tree after). Earlier table (throwaway detached worktree off release2; forward `git apply`, then `-R` in reverse order; clean tree after)
| Group | Orders tried | Result |
|-------|--------------|--------|
| live_server.py: inbox, review-expect, discard-undo, draft-delivery | all 24 permutations | all apply and reverse |
| the same plus follow's live_server | all 120 permutations | all apply and reverse |
| review.py: review-expect, discard-undo | both orders | both apply and reverse |
| rules: 183h, VIP | either order | apply and reverse |
| full chain (chosen order) | forward and reverse | apply and reverse |

So ordering was enough. reach.py: only discard-undo. tracker.py: only emit.

## check.py on the full chain
Merged throwaway (release2 + small, 183h, follow, + the chain applied): `check: OK`. Nothing over a complexity or line limit.
Note for main: `origin/v262-small` and `origin/v262-discard-undo` conflict in `system/templates/dashboard/src/review.js` (non-guarded); not touched here.

## Tests per diff (each green with the chain applied)
| Diff | Tests |
|------|-------|
| inbox-upload | test_inbox_upload_oserror |
| review-expect | test_review_expect, test_review_expect_routes, test_held_stale_262, test_held_editor_307b |
| discard-undo | test_discard_undo, test_discard_undo_routes (fail without the chain: 7 and 10 errors), test_record_commands |
| draft-delivery | test_draft_delivery, test_draft_delivery_popup, test_tracker, test_settings_* |
| follow | test_follow_words_262, test_follow_guarded_262, test_vip_* , test_sweep_alerts, test_alert_actions |
Browser tests and handchecks were not run. Only discard-undo's two test files turned from red to green; the others also pass without the chain
(they skip or accept both wordings).

## Guard checks (dev/tests/test_guarded_chain.py: 52 tests)
Every 2.6.1 case now runs for the 2.6.1 chain and again for the 2.6.2 chain (extra edit in a marked commit, unmarked edit, forgeries a, b, c,
missing chain file, pin mismatch, live pin). Six more mix the two chains. Real check 9 (test_word_export_227): passes on the branch (release2 + guard),
on a simulated 2.6.2 commit (chain applied, `Guarded 2.6.2 chain: simulated`), against `BASE` and against `BASE_261`; an extra unmarked tracker.py edit then fails.

## Changed on the line after the first assembly (23-10-2026)
- 183r/183b replaced by 183h (hook-only create tool). `RULES-ORDER.md` is gone with 183r: the rules order is unchanged (183h, VIP/follow).
- emit-event-txn/tracker.diff regenerated (Cap #275 MEDIUM: the dry run records no events, a lasting history fault refuses the apply).
- review-expect/review.py.diff regenerated (a repeated --expect is refused). Everything else in the chain is byte for byte its branch.
- F1 and #250 removed in the recut; `CHAIN2_SHA256` re-set with the shorter list.
- Left open, with reasons: Cap's H-1a (reextract: a manifest with valid fields still acts) is closed only by a ledger under system/guard/
  (a never-list place: reach.py and the guard, so a guarded diff and Alan's decision; Cap's draft ef4471b9 exists). The smaller fix is in
  reextract.py (recover() puts a hold back instead of settling by `at`). H-1b (size cap, regular file only) is done in reextract.py.

## Known (not fixed in 2.6.2)
- reextract.py `_move_back` (Cap LOW): if a crash-recovered run left a new draft staged in the same minute as the earlier proposal, the earlier
  minutes' file name is taken, so they stay in the hold folder (state `kept_aside`) and are not in Review. Nothing is lost, the new draft is
  in Review, and the debug log has the line, but the dashboard shows nothing about it. A fix means renaming the earlier proposal and
  re-pointing its record, which is not small; for the release notes' Known list.
