# #291 Tier 1: proposal for a guarded file

`live_server.py.diff` (verified: `git apply --check`, then applied, `git apply -R --check`, reverted) adds the plain words
"check my mail", "check my mail and Teams", "check mail for ABC" and "check my mail the last 7 days" to `PANEL_SWEEP_WORDS`, so
`panel_sweep` (BL-309) treats them as a sweep exactly as it treats "sweep ...". It changes nothing else: "sweep ..." still matches.

Why: Today's "Check now" button and the ask creaite panel's first chip still send the word "sweep" (it shows as the user's own
message bubble, walk row A3). Once this lands, `today.js` (`send("sweep")`, two places) and `shell.html` (`data-q="sweep mail"`)
can send "check my mail" and the bubble reads in plain words. Until then they send "sweep" so the run stays a sweep run.

Add a test beside `test_panel_sweep.py` for the new phrases (a "check my mail and apply" must stay a plain chat: `PANEL_SWEEP_NOT`
already refuses it).

## update.py (guarded by test_word_export_227 check 9)
`update.py.diff` changes `system/scripts/update.py`, `dev/tests/test_update.py` and `dev/tests/plain_words_baseline.json` together; apply all three at once
(`git apply dev/proposals/291/update.py.diff`; verified with `git apply --check` and `-R --check` on the branch, whose update.py and
test_update.py equal origin/v260-release's). Without the baseline hunk `test_plain_words` fails, because three baselined "Refused" lines go.
- The "Refused: …" messages become one plain line each, naming the real reason and no file: outside creaite's own files, a file the list doesn't show,
  a file the list shows but the zip lacks, a version that doesn't match, a failed checksum. Only the checksum line says "checksum".
- The real reason and up to five member names go to the debug log (`release refused: …`), so a zip reaching outside the engine is still visible to Alan.
- `test_refuses_bad_zips` has seven cases (new: missing member, wrong version). Each expects its own message, and asserts none of the other
  messages and no `.py` file name appears.
- Baseline: 1,090 to 1,087 (hunk is in the diff). If the baseline moves again before this lands, refresh it with
  `CREAITE_UPDATE_PLAIN_BASELINE=1 python3 dev/tests/test_plain_words.py` after applying.

## live_server.py (second revision)
`live_server.py.diff` also carries a guard: the word after "for" must read as a project code. A code typed in capitals or holding a digit is
accepted; a lower-case one is accepted only when it is 3 letters or fewer and not a common word (the, all, any, now, ...), so
"check my mail for urgent" and "sweep for today" stay plain chats (ask first) while "check mail for ABC" and "sweep mail for abc" run.
`test_panel_sweep.test_the_plain_words_are_sweeps` covers both ways (it skips until the diff is applied). The Settings hint for
`sweep.max_lookback_days` now says "check my mail the last 7 days", which the new words match. Docs: `system/templates/help.md` (Typing sweep).
Still to do when it lands: `system/creaite-rules.md` (BL-309 line) and `.claude/skills/cx-sweep/SKILL.md` list "cx-sweep's words" only; add the plain words there.
