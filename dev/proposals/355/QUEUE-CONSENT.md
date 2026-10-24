# Design note (#355 added (a)): who may start a held queue

Status: the page half is made (ask.js); the server half is guarded (`system/scripts/live_server.py`) and is a note only.

## The page

Run now (`ask.js`, the queue box's click handler) now sends `{op: "resume", run_now: true}`. The other callers (`queueResume`, which
runs after a card is answered) send `{op: "resume"}` as before, with no flag.

## The server (not edited)

`queue_route`, op `resume`, calls `queue_start(q)` with no `prev`; inside, `ask = {"over_budget": prev is None, ...}` treats a
start with no previous run as consent. So the page's own restart after a card is answered counts as "Run anyway" in confirm mode.

Diff shape, `live_server.py`, two small hunks:

1. `queue_start(q, prev=None, consent=False)` and `ask = {"over_budget": bool(consent), ...}` (a start after a run ends passes
   nothing, as before: `prev` is not consent).
2. In `queue_route`, op `resume`: `nxt = queue_start(q, consent=req.get("run_now") is True) if q["items"] else None`.

Until this is in, a page that sends no flag changes nothing on the server: the consent still follows "no previous run". The page
change is safe to ship alone. Guarded: chain diff and a Full review.

## Not done: the queue's reason line

Added (b): while the queue is held for the budget the page still says "n queued: waiting for your answer above". The server has the
reason (`q["why"]`) but `queue_public` does not pass it with the list; adding it is also a `live_server.py` change. The page can show
`q.why` once it arrives (`queueDraw`, the head line).
