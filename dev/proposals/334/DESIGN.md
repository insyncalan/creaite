# #334 Weekly budget for creaite's own AI runs: design (24-10-2026)

## What it is
A cap on what creaite's own Claude runs (ask creaite, drafts, sweep, alert check) may use in a week. Not the cost of building creaite (#87). It warns at 80%, and at 100% either asks or stops a new typed request, by a setting. Review, Apply and Undo are not runs and are never held.

## Where it is enforced
In the live server's run engine, in `live_server.py` (guarded): one small helper, `budget_gate(req)`, asked at the two places a typed request starts: `Handler.ask` (answers HTTP 429 with the counts and plain words, starts nothing) and `queue_start` (a queued message holds the queue instead of starting). Everything else is plain code in `ai_budget.py` (pure, no writes, unit-tested). A fault in the count holds nothing (fails open); the gate never raises.

Never held: a confirmed request (the answer to a question the last run asked, so a change in flight is not cut off), a sweep or alert check running on its own (unattended staging), drafts, Prep, Intake and the other run kinds, and anything that is not a run. Those still add to the week's total and show in the warning.

## What Alan sees
- Settings, Advanced, "creaite and ask creaite": Weekly AI budget (on/off), Budget counted in (dollars or tokens), the two amounts, At the limit (confirm or stop). Each with a reason for its default.
- Usage tab: a bar "$41.20 of $50.00 (82%)", the state and the week's last day (DD-MM-YYYY).
- From 80%: after each ask run, one plain line in the chat: "Heads-up: $41.20 of $50.00 used this week; the week ends on 25-10-2026."
- At 100%, confirm mode: a card "This week's AI budget is used up ($52.10 of $50.00). It starts again on Monday 26-10-2026. The buttons in the dashboard still work. Run this request anyway?" with a Run anyway button (the page resends with `over_budget: true`). Stop mode: the same words without the question, and a pointer to the setting. A queued message waits (Run now overrides in confirm mode only).

## What is counted
The usage monitor's own lines (`run-usage.jsonl`): `cost_usd`, or input + output + cache read + cache create tokens, summed for lines dated in the week. The week is Monday 00:00 to Sunday 23:59, local time (the file's own clock). A stopped run counts what it cost. Counts and dates only: the module never reads a label, model, skill, name or path, and the status holds none.

## Defaults
On, dollars, $50 a week, confirm at the limit (tokens: 50 million, cache reads included). Confirm is the issue's default and cannot lock Alan out; $50 is a first guess to be set from a few weeks of Usage.

## Failure modes
- Clock wrong: lines dated outside this week count nothing; a clock set back counts nothing extra; a future-dated line inside the week counts.
- Log missing, empty or unreadable: nothing used, nothing held (`counted` false, said on the Usage tab).
- Bad line (no date, NaN, negative, text): counts nothing. Hand-edited settings fall back to defaults and amounts are held between their limits.
- A resumed chat (Continue this chat) reports session totals, so it can over-count; fresh sessions (#327 B) make this rare. Over-counting only brings the warning forward.
- The development repository writes no usage file, so the budget is always zero there.

## Privacy
Counts only, as the usage monitor. Nothing new is stored: no new file, no log line with text. The 429 reply and the page card carry numbers, dates and fixed words.

## Open questions for Alan
1. Default amount and unit: $50 a week, dollars, on? Or off until you set it, or higher?
2. Which runs may be held at 100%: only typed ask creaite (as built), or also drafts, Prep and Generate? The sweep and alert check stay unheld either way.
3. Should confirm mode ask once per week (one "Run anyway" clears the rest of the week) instead of on every request? As built, it asks every time.
4. Is a 100% warning enough at the limit for scheduled runs, or should the unattended sweep stop too (the issue says staging must not be blocked)?
5. Tokens including cache reads (as the Usage tab counts them) or only fresh input and output?
