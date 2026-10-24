# review `expect` mandatory at the route (2.6.3)

2.6.2 made `expect` (the item's 12-hex fingerprint) opt-in at `POST /api/review`: sent, review.py refuses when item N is no longer that
item; not sent, it acted on the number. Every page path sends it (review.js x2, core/server.js `reviewViaServer`, stores/minutes.js), so
2.6.3 makes it required.

`live_server.diff` (guarded; review.py is unchanged):
- `Handler.expect_args` returns None for a missing `expect` as it already did for a malformed one. The route refuses before anything is decided.
- A missing `expect` gets its own plain message: "This page didn't say which item it meant, so nothing was decided. Reload the page and try
  again." A malformed one keeps "Review can't check which item that is...". "That proposal is no longer pending." still comes first.
- Covers every decision the route knows (approved, rejected, keep, override, discard).

Not affected (they use the command line, not the route): ask creaite's `review.py approve|reject ...`, the Excel import, `cx-review`.
`--expect` stays optional in review.py itself.

Risk: a dashboard tab left open from before 2.6.2 (no `expect`) gets the reload message. Nothing is decided.

Tests: `test_review_expect_routes.py` takes its throwaway copy to a chosen level (0 old route, 1 the 2.6.2 route, 2 mandatory) whatever this
tree has, so it passes with and without the diff; new `Mandatory` class (missing expect refused for every decision, nothing decided, plain
words, the same request with a matching fp works, a gone proposal still says so first) and a mutant (a route that lets a missing expect through
fails it). Existing route tests that posted without `expect` now send it (`test_live_server`, `test_held_missing_source`,
`test_discard_undo_routes`; green with and without the diff).
