# #291 Tier 1: proposal for a guarded file

`live_server.py.diff` (verified: `git apply --check`, then applied, `git apply -R --check`, reverted) adds the plain words
"check my mail", "check my mail and Teams", "check mail for ABC" and "check my mail the last 7 days" to `PANEL_SWEEP_WORDS`, so
`panel_sweep` (BL-309) treats them as a sweep exactly as it treats "sweep ...". It changes nothing else: "sweep ..." still matches.

Why: Today's "Check now" button and the ask creaite panel's first chip still send the word "sweep" (it shows as the user's own
message bubble, walk row A3). Once this lands, `today.js` (`send("sweep")`, two places) and `shell.html` (`data-q="sweep mail"`)
can send "check my mail" and the bubble reads in plain words. Until then they send "sweep" so the run stays a sweep run.

Add a test beside `test_panel_sweep.py` for the new phrases (a "check my mail and apply" must stay a plain chat: `PANEL_SWEEP_NOT`
already refuses it).
