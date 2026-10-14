# v192-reject-reasons: BL-315 server side (Team 2 → Team 1)

Branch `v192-reject-reasons`, from `origin/main`. Server side only; the Review UI is not touched. **No schema change**: `rejected.reason` and `rejected.duplicate_of` (BL-133) carry it, and `change_log` holds the old values for undo.

## What is built

**Reasons.** `tracker.REJECT_REASONS` is the seven: Not an action, Duplicate, Chatter, Already done, Wrong project, Doesn't need tracking, For another team. A reason typed in any case is stored as listed (`review.canonical_reason`); Alan's own words still pass (one line, at most 200 characters, BL-133). No reason stays allowed.

**Guesses** (`review.guess`, plain code, no model), per pending action, RAID item or decision:
- **Chatter:** a thank-you ("Thanks all for joining, great session"), or scheduling with no owner ("Check calendars for a workshop").
- **Duplicate** (with `of`): an open look-alike, from BL-221's `looks_like` mark or `extraction.best_repeat`. Off when Settings › AI drafts › Spot repeats is off.
- **Already done** (with `of`): a recently closed look-alike, or an update closing an item the tracker already has closed.
- **Doesn't need tracking:** a new action with no owner (or TBC).
- Not built: "an owner outside Alan's teams" (For another team). creaite has no definition of Alan's teams yet; the people register's organisation could supply one. Say if you want it.

**review.py commands** (all in `reach.SCRIPT_COMMANDS`):
- `reasons [--json]`, `guesses [CODE] [--json]`, `rejects [--json] [--limit=N]`: read.
- `reject <numbers> --guess`: each row rejected with its own guess (Duplicate records `duplicate_of`; no guess, no reason). `reject` also stamps `rejected_at`.
- `unreject <file>#<n> …`: back in Review, pending.
- `rereason <file>#<n> … [--reason=…] [--duplicate-of=ID]`: change the reason; none clears it.
- `approve-instead <file>#<n> …`: undo and approve in one step. An item approved only on its own (`individual_only`: a new decision, a new risk, a closing update and the rest), or one that needs a project, has a conflict or is invalid, goes back to Review pending and is listed in `open`. Minutes rejected but not yet applied go back to pending (`open`). Applied rejected minutes are refused, because their files moved; use "undo last apply".
- Each of the three takes `--json` and prints `{ok, done: [{key, was: {decision, reason, duplicate_of}}], open}`.

**Pending or applied.** If the reject hasn't been applied yet, only the proposal changes. If it has, the item goes back to its proposal in staging (out of `applied/`, the way undo returns one), with `applied` removed and `redecide: {fingerprint, apply_id}` added. At the next apply, `tracker.py` does one of two things:
- **Approved:** it removes the `rejected` row (logged as a REMOVED row, inside the item's savepoint, so a conflict keeps it).
- **Rejected again:** it updates the row's `reason` and `duplicate_of` in place, logged per field. No second row is added.

`_reverse_item` now undoes an insert, a removal and a reason change. "Undo last apply" therefore puts the row back as it was, and the item returns to Review pending, as for any undone reject.

**Live server routes** (all are in `REVIEW_WORK_ROUTES` behind `do_POST`'s token check and run through `review.py` under `LOCK`):
- `POST /api/review/guesses {}` → `{ok, reasons, guesses: [{n, file, ref, reason, why, of}]}`.
- `POST /api/review/reject {rows: [{file, ref}], reason, duplicate_of | guess: true}` → `{ok, message, rejected: [{file, ref, key}], gone}`.
- `POST /api/review/rejected {rows: [{file, ref}], how: "undo" | "reason" | "approve", reason, duplicate_of}` → `{ok, message, done, open}`.
- `POST /api/review/rejects {limit}` → `{ok, items: [{key, file, ref, applied, project, table, kind, text, reason, duplicate_of, at}]}`, newest first.

**Quality and Activity.**
- Quality counts each item's latest decision and reason. `quality.REASONS` is the seven plus BL-133's "Not mine to track". `quality.recent_rejects` feeds `rejects`.
- `build_dashboard.rejected_activity` now lists each reject once (its insert row) with its current reason. It leaves out a reject that is back in Review.

**Docs.** I updated cx-review's skill (two rows), Help's "Or say" line (and rebuilt `guide-how-to.html` with `build_guides.py`) and a `dev/dashboard-spec.md` paragraph. Help's UI text, including the Shift+R line with the old four reasons, is left for the UI item.

## What the UI needs (Team 1)

- **Menu.** Swap `#rvReason`'s four entries for the seven plus **Use each guess** (G) and **No reason** (0), with keys 1 to 7. Take the list from `/api/review/guesses`' `reasons` or hard-code it in the same order.
- **Rejecting.** Send one or many rows to `/api/review/reject`: `{reason}`, `{guess: true}` or neither. Today's reject writes `reject_reason` through `setDecision` and the vault file API. The route goes through `review.py` instead, so canonical spelling, `rejected_at` and guesses all apply. Then `applySoon()` if `S.autoApply`, as now.
- **Guess per row.** Fetch `/api/review/guesses` when Review renders or reloads, and show "guess: Chatter" in grey. "looks like X" comes from `why`/`of`. Guesses are not in `D.review` (`dashboard_data.json` is pinned), so a page opened from a file shows none.
- **Duplicate without an ID.** If the reason is Duplicate and there's no guess ID, ask for the item (BL-297's picker), then send `duplicate_of`. The server takes Duplicate with no ID too.
- **Undo after a reject.** Use one message for the batch. If the batch was applied and nothing has been applied since, `undoApply(apply_id)` works as in Work. Otherwise call `/api/review/rejected {how: "undo", rows}`, which works either way.
- **Rejected rows stay greyed.** Show a chip "Rejected · Chatter" until Review is left. The chip, or the row's ▾, reopens the menu and sends `{how: "reason", reason}`. Keep `done[].was` so the reason change can itself be undone (send `was.reason` back).
- **Approve instead.** Send `{how: "approve"}`. Open each key in `open` for its individual approval: the item panel, or the minutes for `#meeting`. Then apply as usual.
- **Activity › What you rejected.** Use `/api/review/rejects`. Each line gets the same chip, plus Approve instead and Undo, keyed by `key`.

## Tests

- `dev/tests/test_rejects_real_life.py` (new, 13 tests, no Chrome): the seven; each guess and the Spot repeats switch; Use each guess, then apply; many rejects with one reason in any case; undo and a reason change before apply; after apply, a reason change (the change_log row, then undo restores it), undo then reject again (one row, updated), and approve instead (row removed, action written, undo puts both back); a new risk opened instead of approved; minutes; Quality, `rejects` and Activity following the latest choice; the four routes with a fake `run`; reach's classification.
- Re-run and passing: `test_reject_reasons.Engine`, `test_quality`, `test_reach`, `test_smart_updates`, `test_tracker`, `test_dashboard_data_pinned`, `test_activity_undo`.
