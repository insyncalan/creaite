# BL-295 — Close the day, a guided shutdown: the server side (sprint-close-day-server)

The Python and live-server work behind the stepper (Catch up, Today, Loose ends, Tomorrow, the end line). The dashboard
(`system/templates/dashboard/`, `dashboard.html`) is not touched here; the card is built on the routes below. Built on
`sprint-today-days-server` (BL-286, BL-293). No schema change. Nothing in this flow approves, rejects or applies anything, and
nothing is sent.

## What changed

- **`system/scripts/close_day.py`** (new, plain code): the catch-up decision, Loose ends, Tomorrow, the day's plan and First thing
  tomorrow. It writes only `system/staging/day-closed.json` (`record`).
- **Settings** (`settings-defaults.json`; `update.py merge_new` adds them to an existing vault, keeping Alan's values):
  - `day.catchup_sweep`: `"start"` (default: the sweep starts as the card opens), `"offer"` (ask first) or `"off"`;
  - `day.catchup_after_minutes`: `30`.
  - Settings › General's rows are the dashboard's (`0078-…settings-row.js`): **the screens sprint adds them** (a three-way choice
    and a number). `day.` is in Copy diagnostics' allow list (`SAFE_SETTINGS`).
- **The catch-up sweep is a guarded run** (`Run(kind="sweep")`): cx-sweep through the run engine (progress, Stop, one run at a
  time), with the guard hook in a new mode, **`sweep`** (`reach.py`): a plain chat's rules (every record command refused: apply,
  undo, approve, reject, `propose.py stage`…; direct writes only in `system/staging/drafts/`), plus the one step cx-sweep needs that
  a plain chat lacks, `propose.py people map` on a file directly in `system/staging/drafts/`. Its tools: the read tools (Microsoft
  365 reading included), `sweep.py *`, `people map`, Write/Edit in drafts; no `filechange.py` changes. Its own system prompt says it
  only stages and needs no CONFIRM. It is marked like any chat when it reads mail (BL-141's card rules apply). **This is narrower
  than "sweep" typed in the panel**, which runs as a confirmed request. Never in the development repository (`.creaite-dev`):
  the route answers `cant`.
- **`day-closed.json`** keeps BL-206's `{"days": {YYYY-MM-DD: "HH:MM"}}` (the last 30) and adds
  `{"plans": {YYYY-MM-DD: {"first": [ref], "review": [ref], "left": n, "prep": n, "swept": "HH:MM"|null}}}`. References only,
  never text:
  - `p:<proposal file>#<n | meeting | report | file_changes>`;
  - `i:<tracker ID>`;
  - `t:<calendar event ID>` (a transcript ready);
  - `f:<12 hex>` (an inbox file, by the SHA-256 of its stored path).
  Closing a day keeps only that day's plan, so the earlier First thing list is **cleared when its tomorrow is closed**. Nothing
  rolls over by itself: an item still open shows again in the next Loose ends.
- **Today's brief reads it:** `D.day.first` (in `/api/data`) is the newest plan before today, each reference read afresh:
  `{day, day_shown, items: [{ref, kind, type, t, p, open}]}` or `null`. `open` is false once it was decided, closed, processed
  or has gone. `D.day.catchup` is `{mode, after}`.

## Routes (local, token-checked)

| Route | Body | Does |
|---|---|---|
| `POST /api/day/card` | `{}` | The steps' facts in one read; nothing starts |
| `POST /api/day/catchup` | `{force?}` | Start the catch-up sweep, or say why not. `force: true` is **Sweep again** |
| `POST /api/day/catchup/status` | `{}` | The catch-up's state and what it found |
| `POST /api/day/catchup/skip` | `{}` | **Skip**: drops a waiting catch-up, stops a running one |
| `POST /api/day/close` | `{choices?, prep?}` | Close the day (BL-206's route, extended; `{}` still works) |
| `POST /api/day/prep` | `{op: list\|add\|clear, keys?}` | The prep queue |

### Shapes

- **Card:** `{ok, now ("HH:MM"), last_sweep, day, catchup, loose: [loose end], tomorrow, prep}`.
  - `day` is `D.day` (BL-206's `moved`, `promised`, `closed`, `last`, `from`, `friday`, plus `first` and `catchup`).
  - **Loose end:** `{ref, kind (proposal | intake | item), type ("Action", "Risk", "Update", "Minutes", "File in Intake",
    "Transcript ready", "Action due today"…), t, p, project (the name, or null), new (found by today's catch-up), place: "first"}`.
    Order: the catch-up's new items, the other pending proposals (one per item or block, as Review lists them), Intake (inbox
    files not processed; meetings with a transcript ready, not loaded or processed), then open actions and RAID items due today.
  - **Tomorrow:** `{day, day_shown, long ("Wednesday 14th October"), in_calendar, friday, meetings: [{start, end, title,
    confidential, key, page, plan, make, p?, project?}]}`, from BL-293's day data for the next working day. A private meeting is
    left out; a confidential one has no `p` or `project`. `make` is true when it has a Prep key and no prep page.
  - `catchup` and `prep`: as below.
- **Catch-up:** `{ok, status, message, last, last_shown, run?, catchup: {state, run, started, ended}}`.
  - `status`:
    - `start`: started now; `run` is the run's summary (attach to it);
    - `offer`: stale, but `day.catchup_sweep` is "offer";
    - `recent`: "Caught up at 17:41.";
    - `off`;
    - `busy`: another run is going; the server **waits** for it, then starts the sweep (or finds it recent);
    - `sweeping`: a sweep already holds the lock; `run` is the run going, if any;
    - `cant`: the development repository, or Claude Code couldn't start.
  - `message` is the line to show, in Alan's terms. `last_shown` is "17:41" today, else "DD-MM-YYYY HH:MM".
  - `catchup.state`: `null` (none today), `waiting`, `running`, `done`, `stopped`, `skipped`, `failed`, `gave_up` (waited 30
    minutes).
- **Status:** `{ok, state, run, started, ended, found: [{ref, type, t, p, project}]}`; `found` is what the catch-up staged.
- **Close request:** `choices` is `{ref: "review" | "first" | "leave"}` (at most 200; a reference not in the shapes above, or
  another place, is a 400); `prep` is up to 10 Prep keys (`tomorrow.meetings[].key`).
- **Close answer:**
  - closed now: `{ok, pending: false, at, counts: {review, first, left, prep}, open: {review: [{file, ref}], work: [ID],
    intake: bool}, queued}`;
  - while the catch-up runs: `{ok, pending: true, run, queued}`. The day closes when the sweep ends, and anything it found that
    has no choice goes to **First thing tomorrow**. A catch-up still waiting to start is dropped instead.
- **Prep queue:** `{ok, items: [{key, state (queued | running | made | failed | stopped), run, path, message}], running}`.
  Pages are made one at a time, each through the run engine (read-only research, as BL-98) and written by the server
  (`prep_page.build`; an edited page is never overwritten). A Stop on one stops the rest. The queue lives in memory: a server
  restart forgets it.

## What the card must call

1. **On open:** `/api/day/card` (draw steps 2 to 4), then `/api/day/catchup`.
   - `start` or `busy`: show the progress. Attach to `run.id` with `/api/ask/attach {run, after}` for steps (as Prep page does),
     or poll `/api/day/catchup/status`.
   - `recent`: show `message` and a quiet **Sweep again** (`/api/day/catchup {force: true}`).
   - `offer`: a **Sweep now** button (`force: true`).
   - `off` or `cant`: one quiet line, or skip the step.
2. **Stop and Skip:**
   - **Stop** is the run engine's own `/api/ask/stop {run}`;
   - **Skip** is `/api/day/catchup/skip`, which also drops a waiting catch-up.
3. **When the sweep ends:** `/api/day/catchup/status` gives `found`. Draw it in step 1, then call `/api/day/card` again so Loose
   ends include it (`new: true`, listed first).
4. **Loose ends:**
   - each row's choice defaults to `place` ("first");
   - show the first eight and "and n more", with one control for all;
   - **Review now** for `kind: proposal` opens Review filtered to `open.review` after closing;
   - for `item` it opens Work filtered to `open.work`;
   - for `intake` it opens Intake.
5. **Tomorrow:** `make` meetings offer **Make prep page**. The chosen keys go in the close request's `prep` (or
   `/api/day/prep {op: "add"}` at once). `/api/day/prep {op: "list"}` shows progress.
6. **Close:** `/api/day/close {choices, prep}`.
   - The end line is built from `at` and `counts`: "Day closed at 18:04. Everything has a place." with "n for Review now, n
     first thing tomorrow, n prep pages being made" (`counts.prep`).
   - `pending: true`: show "Closing when the sweep finishes". Wait for the run's `done` (or poll the status), then `/api/data`
     brings `D.day.closed`.
7. **Next morning:** Today's brief lists `D.day.first.items` where `open` is true (closed items can show ticked or be left out).

## Debug log

The area is `day`, with steps, run IDs and counts only:
- `catch-up: started s-…, 4 proposal(s) before it`;
- `card: 7 loose end(s) (1 new), 3 meeting(s) tomorrow`;
- `closed 2026-10-13 at 17:30: 1 review now, 2 first thing, 1 left, 2 prep page(s)`;
- `prep queue: 2 added, 2 queued`.

Never a title or a message's text.

## Tests

`dev/tests/test_close_day_guided.py` (quick tier, a stand-in Claude) covers:
- the catch-up decision: stale, recent, off, offer, busy, sweeping, the dev repository and Sweep again;
- the settings defaults, odd values, and `update.merge_new` adding both keys and keeping Alan's;
- the Loose ends shape and order, and the plan;
- the guard's `sweep` mode: record commands refused, `people map` only on a drafts file, writes only in drafts, a plain chat
  unchanged;
- through the server:
  - the card;
  - off and the dev repository start nothing;
  - a busy run makes the catch-up wait, then the guarded sweep runs (`--settings` with `--mode sweep`, no `tracker.py apply`,
    no `filechange.py` changes), stages only and lists what it found;
  - "Caught up at 17:31.";
  - closing keeps references only, and the tracker and the proposals are unchanged;
  - bad references and places are refused;
  - the prep queue makes two pages one at a time;
  - closing during a sweep closes when it ends, with its find on First thing tomorrow;
  - the next day's `D.day.first` resolves each kind;
  - closing that day clears the list;
  - the log has counts only.

`test_tracker.make_vault` copies `close_day.py`.

## Questions for Alan

1. **Review now for something that isn't a proposal.** A tracker item due today or an Intake file has nothing to send to Review
   without inventing a change. Here, it opens Work (filtered to the IDs) or Intake after closing, and nothing is staged. Right, or
   should an item due today get a pending "re-date" proposal?
2. **Due today:** only open actions and RAID items due **today**, not every overdue one. Include overdue too?
3. **Session start:** First thing tomorrow is read by Today (`D.day.first`) only, as the write-up says. Should the Claude Code
   session-start status line list it as well?
4. **The catch-up sweep runs in a narrower mode than "sweep" typed in the panel** (no CONFIRM, but no record commands at all).
   Keep the panel's as it is?
