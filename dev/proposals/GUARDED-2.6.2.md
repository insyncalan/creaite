# Guarded chain for 2.6.2 (23-10-2026)

Base: `5bf7da29e22e9b5b9b5c6b494c357280df4e4c4b`, the published 2.6.1 release commit (the 2.6.1 chain is already applied there).
The chain is `GUARDED-2.6.2.chain` (apply order). Apply it as ONE commit whose subject starts `Guarded 2.6.2 chain:`.
The guard is `dev/tests/guarded_chain.py` (`CHAIN2_MARKER`, `CHAIN2_FILE`, `CHAIN2_SHA256`, `BASE2`/`BASE`); `python3 dev/tests/guarded_chain.py` prints both pins.
Change the chain list or any listed diff, and `CHAIN2_SHA256` must be re-set (Alan's say). Owners of the listed diffs: f1 `origin/v262-f1b`,
small `origin/v262-small`, discard-undo `origin/v262-discard-undo`, draft-delivery `origin/v262-183h` 68eb5391 (live_server 0fb173ec and rules-and-skill b1fb8d96), fetch-transcripts `origin/v262-250b`, follow code `origin/v262-followb` (identical to `v262-follow`),
follow rules `origin/v261-vip-rules`. Rebuilt on `v262-line` (23-10-2026): every diff is byte for byte the version in the tree; none was regenerated. The review-expect diffs and the discard-undo review.py/reach.py/live_server.py diffs are the later versions (not the ones the first chain listed); the .chain list order is unchanged.

## Order (chosen)
1 f1 nullable columns (schema.sql, tracker.py); 2 writer-pins-after-f1 (not guarded); 3 inbox-upload live_server; 4 review-expect review.py;
5 review-expect live_server; 6 discard-undo review.py; 7 discard-undo reach.py; 8 discard-undo live_server; 9 draft-delivery live_server;
10 fetch-transcripts live_server; 11 emit-event-txn tracker.py; 12 follow propose.py; 13 follow live_server; 14 183r rules-and-skill; 15 VIP/follow rules; 16 250 rules after-vip.
F1 is the F1c version (`origin/v262-f1c` 957fcfd2); emit is `origin/v262-emit` 9b1f7f30; discard-undo's live_server diff says "suggestion", not "proposal" (plain words).

## Orders tried on v262-line (rerun 23-10-2026 on the line's tree: the chain order forward and reversed, all 720 permutations of the six live_server.py diffs, review.py in both orders: all apply and reverse, clean tree after). Earlier table (throwaway detached worktree off release2; forward `git apply`, then `-R` in reverse order; clean tree after)
| Group | Orders tried | Result |
|-------|--------------|--------|
| live_server.py: inbox, review-expect, discard-undo, draft-delivery, fetch-transcripts | all 120 permutations | all apply and reverse |
| the same plus follow's live_server | all 720 permutations | all apply and reverse |
| review.py: review-expect, discard-undo | both orders | both apply and reverse |
| F1 (schema.sql, tracker.py) and writer pins | f1 then pins; pins then f1; f1/pins at start and after the rest | all apply and reverse |
| rules: 183r, VIP, 250av | 183r,VIP,250av; VIP,183r,250av; 183r,250 | apply and reverse |
| rules: plain 250 after VIP; 250 first; 250av before 183r | 183r,VIP,250; VIP,183r,250; 250,183r; 250av,VIP,183r; 250,VIP,183r | FAIL (250 needs 183r first; after VIP use the after-vip diff) |
| full chain, four orders (chosen order; code first then F1, pins, rules; review.py/reach.py/discard first) | forward and reverse | all apply and reverse |

So ordering was enough; the only constraint is the rules order (183r, then VIP, then 250 after-vip). reach.py: only discard-undo.

## check.py on the full chain
Merged throwaway (release2 + non-conflicting branches f1b, small, 183r, 250b, follow, + the chain applied): `check: OK`. Nothing over a complexity or line limit.
Note for main: `origin/v262-small` and `origin/v262-discard-undo` conflict in `system/templates/dashboard/src/review.js` (non-guarded); not touched here.

## Tests per diff (each green with the chain applied)
| Diff | Tests |
|------|-------|
| F1 | test_f1_columns (14 tests skip without F1), test_archive_projects, test_writer_pinned (needs the pins diff) |
| inbox-upload | test_inbox_upload_oserror |
| review-expect | test_review_expect, test_review_expect_routes, test_held_stale_262, test_held_editor_307b |
| discard-undo | test_discard_undo, test_discard_undo_routes (fail without the chain: 7 and 10 errors), test_record_commands |
| draft-delivery | test_draft_delivery, test_draft_delivery_popup, test_tracker, test_settings_* |
| fetch-transcripts | test_fetch_transcripts, test_transcripts |
| follow | test_follow_words_262, test_follow_guarded_262, test_vip_* , test_sweep_alerts, test_alert_actions |
Browser tests and handchecks were not run. Only discard-undo's two test files turned from red to green; the others also pass without the chain
(they skip or accept both wordings).

## Guard checks (dev/tests/test_guarded_chain.py: 52 tests)
Every 2.6.1 case now runs for the 2.6.1 chain and again for the 2.6.2 chain (extra edit in a marked commit, unmarked edit, forgeries a, b, c,
missing chain file, pin mismatch, live pin). Six more mix the two chains. Real check 9 (test_word_export_227): passes on the branch (release2 + guard),
on a simulated 2.6.2 commit (chain applied, `Guarded 2.6.2 chain: simulated`), against `BASE` and against `BASE_261`; an extra unmarked tracker.py edit then fails.

## Changed on the line after the first assembly (23-10-2026)
- 183r/183b replaced by 183h (hook-only create tool). `RULES-ORDER.md` is gone with 183r: the rules order is unchanged (183h, VIP/follow, 250 after-vip).
- emit-event-txn/tracker.diff regenerated (Cap #275 MEDIUM: the dry run records no events, a lasting history fault refuses the apply).
- review-expect/review.py.diff regenerated (a repeated --expect is refused). Everything else in the chain is byte for byte its branch.
- The 250 URL fix is in transcripts.py (not guarded); the live_server diff is unchanged.
- Left open, with reasons: Cap's H-1a (reextract: a manifest with valid fields still acts) is closed only by a ledger under system/guard/
  (a never-list place: reach.py and the guard, so a guarded diff and Alan's decision; Cap's draft ef4471b9 exists), and any check on `at`
  would also refuse a genuine hold left by a crash after a long downtime. Not taken. H-1b (size cap) is done in reextract.py.
