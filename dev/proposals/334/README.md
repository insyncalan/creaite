# #334 weekly AI budget: guarded part (live_server.py)

## What
`live_server.diff` (one file, +24 lines, `system/scripts/live_server.py`):
- `budget_gate(req)`: asks `ai_budget.gate("ask", ...)` and returns its reply, or None. Any fault returns None (nothing is held).
- `Handler.ask`: before the busy check, a held request is answered with HTTP 429 `{ok: false, budget, message}` and starts nothing. `confirmed` requests and `over_budget: true` (the page's "Run anyway", confirm mode only) pass.
- `queue_start`: over budget the queue is held (nothing lost); Run now (`prev is None`) overrides in confirm mode, not in stop mode.
Not guarded, in this commit: `ai_budget.py` (pure), settings defaults and catalogue entries (Advanced), `usage_report.json_report` (adds `budget`), the Usage tab bar, the Settings controls, the 429 card and the 80% line in ask.js, rebuilt `dashboard.html`.

## Why
No weekly cap exists; the audit found $9 to $16 single ask runs. See DESIGN.md for the rules and open questions.

## Apply order and checks
After the 2.6.2 chain (already in main), then `dev/proposals/327b/live_server.diff`, then `dev/proposals/324/live_server.diff` (it also applies before 324; it needs 327b first, its context is 327b's block). Checked 24-10-2026 on a scratch tree of origin/main with those two applied: `git apply --check` forward, apply, `git apply -R --check` all pass; orders 327b 334 324, 324 327b 334 and 327b 334 apply, 334 first does not.
Tests: `dev/tests/test_ai_budget.py` (always runs: week boundary, 80% and 100%, never-held kinds, counts only, settings, catalogue, page wiring); `dev/tests/test_ai_budget_gate_334.py` (10 tests; skip without the diff, pass on the scratch tree with it).

## Risks (for the reviewer)
1. A wrong count must never block the approval path: only the typed `ask` kind is ever gated, `confirmed` passes, Review/Apply/Undo are separate routes and never call the gate; a read fault fails open (tests).
2. Stop mode with a long queue: the queue holds until Monday or Stop; messages are not lost.
3. `over_budget` is a request flag from the page: it is Alan's click, but any client of the token-checked route could send it. The route is already token-checked and it only lifts a soft cap in confirm mode.
4. Resumed chats report session totals and can over-count (conservative).
5. `check.py` complexity/long-line limits: no line over 140, one `except Exception` that returns None by design (commented).
