# 232-A review of Team Cap's p250-a (Stark, 19-10-2026)

Read: `git diff origin/v250-hub...origin/p250-a` at a50952c1. Tests: `test_intake_review_harden.py` (browser, 18) and
`test_intake_review_harden_model.py` (pure, 12), both written fail-first against p250-a. File:line refer to a50952c1.

## Findings (each has a failing test unless marked "review only")

1. **A confidential meeting shows its project (brief, standing rule).** `build_dashboard.py` `inbox_meetings` never reads the
   calendar's `sensitivity`, so no row, card or pane can know; `rows.jsx:63`, `views.jsx:57` and `views.jsx:84` test only
   `m.private`. Cap's own rules test checks "Busy" (private), not a confidential meeting. Tests: `Findings.test_a_confidential_*`,
   `Confidential.*` (model). Fix in the reference branch (v250-232a, 99ac9767): read `sensitivity` in `inbox_meetings`, carry
   `confidential` through `_ir_calendar`, hide the project when `private or confidential`.
2. **N and H work on a meeting that is being processed.** `IntakeReviewPage.jsx:167-168` (`irCanSetAside` does not look at
   `irBusy`): the run goes on while its row is set aside. Test: `test_n_and_h_do_nothing_on_a_row_that_is_being_processed`.
   Fix: `irCanSetAside = ... && !irBusy.value.includes(m.id)` in `actions.js:23`.
3. **A processed file that leaves the inbox is reported "Couldn't: no draft came back".** `actions.js:61-62`: `done = !!after && ...`
   is false when the row has gone (the file was filed). Test: `test_a_processed_upload_that_leaves_the_inbox_*`. Fix: a missing
   row is success.
4. **Process all ready includes a private meeting** (`actions.js:25` `irReady`); the old Select new left it out. Test:
   `test_process_all_ready_leaves_a_private_meeting_alone`. Judgement call: say if Alan wants it.
5. **Buttons go stale against ask creaite.** `rows.jsx:36` and `IntakeReviewPage.jsx` `ProcessAll` read `mtgBusy()` (`shared.RUN`),
   which is not a signal, so a Process button stays disabled after ask creaite finishes until something else redraws. Test:
   `test_a_buttons_busy_state_follows_ask_creaite_without_another_redraw`. Fix: poll or mirror `shared.RUN` into a signal.
6. **Their `test_process_shows_progress_and_ask_stays_free` cannot pass as written** (`test_intake_review_intake.py`): it evaluates
   `GATE=new Promise(...)` and the harness awaits a promise result, so the run hangs for ever (no timeout); with `; 0` added it
   fails at `stage==='drafted'` because the stub's proposal has `items: []`, which the model calls approved/done, not drafted.
   The same pattern is in `RELEASE()`. Review only (their test).
7. **Fixed since 695b32d8, found by my first run:** a Later upload showed "Later 0" after the redraw (`irTick.value;` was dropped
   by the bundler). a50952c1 fixes it (`data-irtick`, `refreshAll`). My test `test_later_on_an_uploaded_file_*` is the regression.
8. **Later on a ready row or an upload says "Hide it until its transcript arrives" (`rows.jsx:44`) but never comes back by itself**
   (`seen`, `build_dashboard.py` `split_set_aside`; an upload has no transcript to wait for). The behaviour is defensible (Restore
   brings it back; the pure tests pin it) but the tooltip promises more. Review only: reword to "Hide it; Restore brings it back"
   for those rows, or keep Later to waiting meetings as the reference branch does.
9. **Duplicate code.** `actions.js:111` `irAddFiles` repeats `intake.js:32` `addInboxFiles` (types, 25 MB limit, upload call);
   two copies of the limits will drift. Reuse it, or move the limits to one place when 232-C retires intake.js. `RowActions`
   has an unused `live` prop (`rows.jsx:35` signature, passed at `rows.jsx:67`).
10. **Callers of the old code still live (not dead, 232-C owns them):** `ask.js:25` (⌘K processMeetings, MSEL, renderMeetings),
    `today.js:28`, `core/server.js:21` and `core/nav.js:19` (renderInbox), `files.js:12`, `review.js:22` and `work.js:23` (`kb`).
    Nothing may be deleted from `intake.js` before 232-C.
11. **Restore wording** says "meeting" for an uploaded file (`actions.js` `irRestore`). Cosmetic.

Held up (tests pass): XSS in titles (JSX text only), reason outside the four refused by page and route, `later`+reason refused,
note and title cut at 200, key at 300, non-string input, wrong type and a path-like name, a drop on another page, Esc closes the
reasons menu with nothing set aside, a double click starts one run, nothing in the debug log names a meeting, tokens
(`test_style_tokens` green).

## Better in the reference branch (v250-232a, `74ed1c20`), if wanted
- `confidential` end to end (point 1): `build_dashboard.py` diff in `99ac9767`.
- Process all ready skips private meetings; N and H refuse a running row; Check again (look the transcript up through the run
  engine from a waiting row, no chat opened); the status words from the sweep (No transcript, No access, Not transcribed) on the
  waiting row.
- Not needed menu keeps focus on the opener on Esc (theirs does too).

Not better: their `seen` rule for Later is a real improvement over mine (a ready meeting set aside would have come straight back);
keep it. Their Later on a ready row (mockup) is also closer to the locked mockup than my waiting-only rule.
