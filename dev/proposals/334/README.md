# Weekly AI budget: the guarded part (2.6.4, #334)

## What
`live_server.diff` (one file, +19 lines, `system/scripts/live_server.py`), rebased on the 2.6.3 main (after the fresh-session and filing
changes) and after 345 and 346:
- `budget_gate(req)`: asks `ai_budget.gate("ask", ...)` and returns its reply, or None. Any fault returns None (nothing is held).
- `Handler.ask`: before the busy check, a held request is answered with HTTP 429 `{ok: false, budget, message}` and starts nothing.
  `confirmed` requests and `over_budget: true` (the page's "Run anyway", confirm mode only) pass.
- `queue_start`: over budget the queue is held (nothing lost); Run now (`prev is None`) overrides in confirm mode, not in stop mode.

Not in this folder (unguarded, merged separately): `ai_budget.py`, the settings defaults and catalogue entries, `usage_report.json_report`,
the Usage tab bar, the Settings controls, the 429 card and the 80% line in `ask.js`, the rebuilt `dashboard.html`. See `DESIGN.md` for the
rules and the open questions for Alan.

## Added after the first reviews
- A typed sweep (`panel_sweep`'s words: "sweep", "sweep mail for ABC", "refresh calendar") is never held: `budget_gate` asks `panel_sweep`
  first, in the ask handler and in `queue_start` (which now hands the first queued message's words to the gate). Tests with a mutant for each path.
- A queue held by the budget keeps its reason (`q["why"]`, the gate's own sentence: how much is used, "It starts again on Monday DD-MM-YYYY",
  and in stop mode where to raise it). Run now returns it as `message`, which the page already shows; a hold for another reason clears it.
- The usage file (up to 8 MB) is read in `queue_start` before the start lock is taken, not while it is held. Test with a mutant.
- The gate test does not depend on the card's wording (`ai_budget.py` / `ask.js` are unguarded and handled elsewhere); it checks the figures,
  the date and "AI budget is used up" only.

## Why
No weekly cap exists; the audit found single ask runs of $9 to $16.

## Order and checks
Third in the 2.6.4 chain (`dev/proposals/GUARDED-2.6.4.order.md`). Its hunks do not overlap 345 or 346, so it also goes in in any order
with them (checked). Tests: `dev/tests/test_ai_budget_gate_334.py` (10 tests; skip without the diff and without `ai_budget.py`; pass on a
scratch tree with the diff and the unguarded module).

## Risks (for the reviewer)
1. A wrong count must never block the approval path: only the typed `ask` kind is ever gated, `confirmed` passes, Review, Save and Undo
   are separate routes that never call the gate; a read fault lets the request through (tests).
2. Stop mode with a long queue: the queue holds until Monday or Stop; messages are not lost.
3. `over_budget` is a request flag from the page: Alan's click, but any client of the token-checked route could send it. It only lifts a
   soft cap in confirm mode.
4. Resumed chats report session totals and can over-count (conservative); fresh sessions make this rare.
5. `check.py` limits: no line over 140; one `except Exception` that returns None by design (commented).
