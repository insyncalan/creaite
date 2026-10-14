# v19-promises-data: BL-125 stage A, promises and Waiting on

For the Scrum Master. Branch `v19-promises-data`: the Python side (12-10-2026, `daeb42f`), then on 13-10-2026 main merged in (the dashboard as ES modules), the `promises.from_sweep` setting and the screens. No schema change: the FR-101 `promises` table holds everything stage A needs.

## Alan's decisions (13-10-2026, from BL-125 A in the backlog)

- **BL-125 A is in v1.9.0** (this replaces the 12-10-2026 note that moved it out).
- **Start small, measure the noise:** promises come first from cx-minutes and from Alan adding them by hand. The sweep's proposed promises are **off** behind `promises.from_sweep` (default `false`) until BL-233's quality data shows enough accepted unedited (bar: Alan's to set; suggested 70%).

## What's done

**The setting (13-10-2026).**
- `promises.from_sweep: false` in `system/templates/settings-defaults.json` (so an update adds it) and in the repo's sample `system/config/settings.json`.
- `sweep.py stage` reads it (`promises_from_sweep()`): while it is off, every promise item from cx-sweep, new or an update to an open one, is skipped, noted ("promises from the sweep are off") and counted as "promises off". Actions and the rest are staged as before.
- cx-sweep's skill: the Promises section opens with "Off unless the setting is on"; step 4 says that, while off, a commitment made in passing is an action, as before this branch (so the sweep's behaviour is unchanged from main until Alan switches promises on). `dev/staging-format.md` says the same.
- Promises from cx-minutes and those added by hand (ask creaite or cx-edit, which already know the `promises` table; the Excel Promises sheet) are not affected.

**Capture and readers (Python side, 12-10-2026; unchanged).**
- `minutes.py stage` and `sweep.py stage` take `{"table": "promises", …}`; raised on the meeting date or the message's Sent day; a minutes promise cites the transcript copy; no due date is flagged `no-due-date`; an open promise said again is a mention in `mentions.jsonl`; a meeting or message may mark one Done or Dropped or re-date it (a closing update, never approved in bulk).
- `propose.py` maps `promised_by` and `promised_to` like owners; Review shows **Promise** with "by → to"; Quality (BL-233) counts promises as their own type.
- `tracker.py read promises --list owe|waiting`, with `promise_lists`, `promise_line`, `who_of`.
- The weekly report: You owe in Next Week, Waiting on in Help Needed (never in a client report).

**The data on the page (13-10-2026).** `build_dashboard.promises_data` puts `D.promises` in the page: the open promises on active projects made by Alan or to him (`{id, p, t, by, to, due, raised, src, od, quiet, list}`). `list` ("owe", "waiting" or "") comes from `tracker.promise_lists`, so the page, `read promises --list` and the weekly report agree. A promise between two other people is left out.

**The screens (13-10-2026, in `src/`).**
- **Today › You owe** and **Today › Waiting on** (`renderPromises` in `today.js`; sections `#tOwe` and `#tWait` in `shell.html`), after Your commitments, each hidden when empty. You owe: soonest due first, undated last, "To <person> on <project>: 2 days late" (late in red), the heading's count adds "· n overdue". Waiting on: the overdue ones made to Alan, most overdue first, "From <person> on <project>: 3 days late, quiet for 10 days"; its heading links to Work's **Chase view** (BL-131). People link to their page; never labelled VIP (BL-288). Capped at the list cap with "+n more".
- **A person's page › Promises** (`personPromises` in `today.js`, added by `renderPerson` in `settings.js`), after Open work: "<First> promised you" (overdue first, quiet shown for the overdue ones) and "You promised <First>". Names go through the register's aliases. It shows even for someone who owns no items.
- All markup through `html` (no new HTML sinks); JSDoc types (a `PromiseRow` typedef); `tsc` 0.
- Help (Today: You owe, Waiting on, where promises come from and that the sweep's are off; Start the day) and `dev/dashboard-spec.md` (Today order and the two sections; person pages) updated.

**Tests.**
- `dev/tests/test_promises.py`: the 19 earlier tests pass after the merge (the sweep tests now switch the setting on first), plus a new one: the shipped default is off, and while off a sweep's new promise and promise update are skipped and counted, and an action beside them is staged. 20 tests, quick tier.
- New `dev/tests/test_promises_page.py` (Chrome tier, 3 tests): Today's two lists (order, wording, counts, overdue flagged, markup in a promise shown as text, no VIP chip, the promise between two others and a kept one absent, the Chase view link); both sections hidden when there are none and the Chase view opening Work; a person's page with promises both ways, one for someone who owns no items, and none for someone without.
- `test_today_brief.py`: two counts updated, because Today now has eight section headings (the two new ones are in the page, hidden when empty).
- `src/core/globals.json`: `renderPromises` added to the test names (`build_dashboard_js.py globals`).

**Golden changed (BL-254).** `dev/tests/snapshots/today.html` only, re-recorded on purpose: it gains the two empty, hidden sections (`#tOwe`, `#tWait`). The sample data has no promises, so nothing visible changes.

**Checks.** `check.py`: OK (the type check at 0). Local runs at `-j 2`: test_promises, test_promises_page, test_snapshots, test_today_brief, test_help, test_help_loop, test_new_vault, test_dashboard_split, test_dashboard_data_pinned, test_session_sweep, test_sweep_alerts, test_close_day, test_pages, test_people_dashboard all pass. Full suites on GitHub Actions.

**Alan's three changes (13-10-2026, decisions 5, 6 and 10 below).**
- **5. The quiet clock restarts on Alan's own edits.** `tracker.last_edited(con)`: the latest day each promise was changed by Alan (change_log updates whose `via` is one of `VIA_NAMES`: dashboard, cx-edit, ask creaite, the Excel import; undone applies left out). `tracker.last_touched(con)` takes the later of that and the mentions log; `promise_lists` (so `read promises --list`, the weekly report) and `build_dashboard.promises_data` use it. A change applied from a meeting's or the sweep's proposal is not Alan's edit (the meeting or message is already a mention). Help's Waiting on says so. Test: `test_promises` › `test_alans_own_edit_restarts_the_quiet_clock` (a meeting's change doesn't count, Alan's does, the later of edit and mention wins, an undone edit stops counting).
- **6. Approve routine covers a promise marked Done or Dropped.** `review.closes_individually` (split out of `individual_only`): an action or RAID item closed stays one by one; a promise marked Done or Dropped is routine, except a probably-done guess (a `suggested` done block, decision 10), which is judged on its evidence and approved on its own, as an action's is. Everything else in the bulk rule is unchanged. The dashboard's Approve routine, the minutes' group approve and Today's Approve n routine follow `indiv` from Python, so no page change. cx-review, cx-minutes and cx-sweep skills, Help (Review), `review.py`'s usage and `dev/dashboard-spec.md` updated. Tests: `test_promises` › `test_a_meeting_can_mark_an_open_promise_kept_and_approve_routine_covers_it` (bulk now approves it) and `test_the_bulk_rule_for_promises`.
- **10. Probably done scans promises.** `extraction.open_items` includes open promises (their maker, `promised_by`, is the owner for the owner rule: `owner_of`); `done_changes` sets a kept promise to **Done** (no latest update); minutes' `mark_done` and the sweep's `done_refusal` accept `promises`; `passage_candidates` now names each candidate's table. Same thresholds, same strengths, same Review display (`dn`, "Looks done"). From the sweep only while `promises.from_sweep` is on: `done-candidates` leaves promises out while it is off, and stage skips a promise update as for every swept promise. Skills (cx-minutes step 6, cx-sweep's Probably done step 4), Help and the spec updated. Tests: `test_probably_done` › `ProbablyKept` (3: a meeting passage marks one kept, approved on its own; the sweep scans promises only while they are on; a stranger can't mark one kept); the file's helpers moved into a `Base` class so the action tests run once.
- Also: `test_dashboard_editing` › `test_today_day_view` counts eight Today sections (You owe and Waiting on), as `test_today_brief` already does; it failed on the branch's Actions run.
- Checks: `check.py` OK (type check 0). Local: test_promises (22), test_probably_done (13), test_promises_page, test_dashboard_editing, test_dashboard_split, test_snapshots (no golden changed), test_today_brief, test_review_triage, test_review_focus, test_work_filters_live, test_minutes_review, test_prep_updates, test_bulk_edit, test_drafts_scaffold, test_looks_like, test_sharpen, test_quality, test_reject_reasons, test_help, test_spec_fields, test_session_sweep all pass.

## Not built yet (BL-125 A's write-up)

1. **Adding a promise by hand in the dashboard** (the peek, ⌘K, Quick capture). Today Alan adds one through ask creaite or cx-edit, or the Excel Promises sheet.
2. **Promises in meeting prep** (the Prep brief and `prep_page.py`): what the attendees and Alan owe each other.
3. **One click to turn a promise into an action** (a `propose.py` helper staging the action and closing the promise in one proposal), waiting on decision 4 below.
4. **Review rows:** an icon and label for kind `promise`, "by → to" in place of the owner, and `promised_by` / `promised_to` fields in the detail panel. Today Review shows promises through the generic row.
5. **Close the day's "You promised today"** (BL-295) still uses today's proposed actions owned by Alan (`build_dashboard.day_close`); it should read real promises.
6. **The Chase view linking back to Waiting on** (Waiting on links to Chase; the other direction is in Work, not touched here to keep off other branches' rows).
7. **Promises on Mine** (Alan's own page): Today has both lists; Mine doesn't yet.

## Alan's answers to the ten decisions (13-10-2026 22:05)

Seven keep what's built:
1. **Waiting on:** overdue promises made to Alan only. Those not yet due show on the person's page.
2. **Who:** only promises made by Alan or to him are captured.
3. **No due date:** never overdue, so never in Waiting on.
4. **Turning a promise into an action** marks the promise **Done**.
7. **What a meeting or message may change:** an open promise's status and due date only.
8. **Weekly report:** as built (You owe in Next Week, Waiting on in Help Needed, never in a client report).
9. **`--search`:** words only.

Three change the build:
- **5. The quiet clock: Alan's own edits restart it too**, as well as a meeting or message raising the promise again.
- **6. Bulk approval: "Approve routine" covers marking a promise Done or Dropped**, as well as a new promise.
- **10. Probably done (BL-218) scans promises too.** It flags open promises that look kept, as it does for actions.
