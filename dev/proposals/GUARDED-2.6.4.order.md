# Guarded diffs for 2.6.4: order and why

This note covers the first three diffs of the chain. The whole list, in order, is `GUARDED-2.6.4.chain` (seven diffs: these three, then
`line-reach/reach.diff`, the two `292-tracker` diffs and, last, `338/creaite-rules.after-chain.diff`); base: the 2.6.3 release commit e6389af8.

Order of the first three (each goes in on a clean tree at e6389af8 once the ones before it are in):

1. `dev/proposals/345/live_server.diff`: every route that decides an item names the item (`expect`).
2. `dev/proposals/346/live_server.diff`: the runs chat carries nothing; a failed run set-up leaves no record.
3. `dev/proposals/334/live_server.diff`: the weekly AI budget gate.

The three change only `system/scripts/live_server.py`, in separate places:

| Diff | Where in the file |
|------|-------------------|
| 345 | the Approve minutes route, a new block before the repeat route, and one short check in each of the repeat, retarget, reject and rejected routes |
| 346 | `carry_over`, and the start of `Run.__init__` (the old body becomes `_start`) |
| 334 | `Handler.ask` (before the busy check), a new `budget_gate` before `CARRY_TURNS`, and `queue_start` |

Why this order: 345 is the largest and touches the part of the file furthest from the others, so it goes first and is the easiest to
review alone. 346 follows because 334's `queue_start` hunk sits just above the `Run` class that 346 edits, and keeping the run engine
changes together reads best. 334 is last because it needs `ai_budget.py` (merged separately) and is the only one with a setting.

Checked (24-10-2026): in this order they pass git's patch check on origin/main, go in, and come out again in the reverse order; and each
goes in on its own and in every other order of the three (no hunk overlaps). 334 alone also goes in on a tree without 345 and 346.
