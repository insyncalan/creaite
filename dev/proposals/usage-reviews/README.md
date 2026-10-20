# #238 delta (v2.5.3): Your reviews on Activity › Usage, the live server's one route (guarded file)

For Jarvis to apply: `git apply dev/proposals/usage-reviews/live_server.diff` (checked with `git apply --check` on
`v253-usage-reviews`).

## What

Two added lines in `system/scripts/live_server.py`, beside `report_server.routes(...)`; nothing else changes:

```
import usage_reviews  # noqa: E402  #238 (v2.5.3): Your reviews on Activity › Usage
DRAFT_ROUTES.update(usage_reviews.routes(LOCK))   # POST /api/usage/review {date, saw, decided}: token-checked by do_POST, under LOCK
```

`POST /api/usage/review {date, saw, decided}` appends one note to `system/staging/usage-reviews.jsonl` and answers with every
note. All the logic is in the unguarded `system/scripts/usage_reviews.py`.

## Why

- Brief #238 scope item 6: Alan's own dated notes (what he saw, what he decided), saved as small records, with Download as CSV.
- The page must not write the file itself: `/api/fs` has no rule for it and should not get one. A route of its own keeps only
  the three fields (`usage_reviews.clean`), so nothing but a date and two short notes can be stored.

## How it is guarded

- **Token-checked:** the route sits in `DRAFT_ROUTES`, which `do_POST` dispatches only after `authorised()` (the right Host and
  this run's token). No token or a wrong token: 403, nothing written (tested).
- **Under the server's `LOCK`**, with a 15-second wait like the other routes; busy: "try again", nothing written.
- **What is kept:** `{date, saw, decided}` only. The date must be a real day (`YYYY-MM-DD`; the page sends it from DD-MM-YYYY);
  each text is made one line and cut to 200 characters; any other field is dropped. A note with neither text is refused. The
  file is only appended to, never rewritten. `load()` cleans every line again, so a hand-edited file shows no more.
- **What ask creaite still cannot do:** write the file. A write to `system/staging/*.jsonl` is a record write in `reach.py`
  (unchanged), so the guard hook refuses it for every run; ask creaite never holds the page's token, so it can't call the route.
  It can still read the notes, as it reads the rest of staging.
- **CSV:** built in the page from the notes it already has (no route). Every cell quoted, quotes doubled, dates DD-MM-YYYY, and a
  cell starting with `=`, `+`, `-`, `@`, a tab or a carriage return gets a leading apostrophe (formula injection); the same rule
  as `usage_reviews.csv_text`, and the browser test checks the two agree byte for byte.

## Before the diff is applied

`usage_reviews.REGISTERED` is set only when `routes()` runs, and `usage_report.json_report` passes it as `reviews_save`. Until
then the list and Download as CSV work, and "Add a review note" is held (`aria-disabled`) with the tooltip "Saving reviews needs
the next server update". A page newer than its server that posts anyway is told the same.

## Folder map (guarded, `creaite-rules.md`)

The `usage-reviews.jsonl` line in the `system/staging/` row is Jarvis's, in a guarded pass: Alan's own Usage review notes (a
date and two one-line notes of at most 200 characters; never anything else), written only by the live server's
`/api/usage/review`. It is in staging, so the daily backup zip already carries it. `usage_reviews.py` also wants a phrase in the
`system/scripts/` row.

## How to test

```
SP=<scratchpad>; git worktree add --detach $SP/scratch-rev HEAD && cd $SP/scratch-rev
git apply dev/proposals/usage-reviews/live_server.diff
python3 dev/tests/test_usage_reviews_browser.py   # ReviewsSave passes (no longer expected failures); ReviewsHeld skips
python3 dev/tests/test_usage_reviews.py
cd - && git worktree remove --force $SP/scratch-rev
```

In the branch itself (no diff) ReviewsSave's three tests are expected failures and ReviewsHeld checks the held button.
