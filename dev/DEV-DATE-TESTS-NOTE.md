# Date-bound tests: note for Team 1 (dev-date-tests, 14-10-2026)

Three tests failed on a clean main on 14-10-2026 because of the real date. Only `dev/tests/` changed; no product code.

## The three fixes

| Test | Why it depended on the real day | Fix |
|------|----------------------------------|-----|
| `test_meeting_hub` (`HubBrowser.test_links_in_from_today_intake_and_an_unknown_address`) | The server's clock is pinned to `NOW` (14-10-2026 15:00), but the page's Today was the machine's day. The fixture added "ABC Daily check" on `date.today()`. On 14-10-2026 that day already held the design review (e2), and the test clicked the first `.mhlink` on Today, which was the design review's. | `HubBrowser.setUp` pins the page's clock to `NOW` (`pin_page_clock`, as `test_transcripts_ui` and `test_clear_day` do). The daily check goes on `NOW`'s day, and the test clicks the link in the daily check's own row. |
| `test_settings_page` (`test_week_ahead_ticks…`) | The Week ahead runs from today to the next Friday. `populate`'s only non-Urgent dated actions are due in 3 and 5 days. On a Wednesday the first is a Saturday, which moves to a Monday outside the window, and the second is that Monday. So "every priority" listed no more than "Urgent only" (0 = 0). | `SettingsPage.load` adds a Medium action due on the server's own day (`CREAITE_NOW` if set, otherwise the machine's day). It is always in the Week ahead: on that day, or on the Monday when the day is a weekend. |
| `test_work_item_peek` (`Rules.test_empty_title_bad_date_and_priority`) | "+3d" from a Wednesday or Thursday lands on a weekend. The due-date picker then asks about the weekend instead of staging, so `PKS.length===1` timed out. | The test types `+Nd`, where N is the first number from 3 that lands on a working day different from the item's current due date. It now checks the exact staged date, not just its format, so the check is stronger than before. |

## Proof on other days

The suite pins the server with `CREAITE_NOW` and the page with `live_browser.pin_page_clock`. It has no way to change the test process's own `date.today()`. For this work I used a scratch harness (not committed). It ran a test file with `date.today()` and `datetime.now()` faked in the test process, `CREAITE_NOW` set for the server and scripts, and the page clock pinned in every `LiveBrowserCase`.

- All three files pass normally on 14-10-2026 (Wednesday).
- `test_work_item_peek` Rules passed with the page clock on 14, 15, 16 (Friday), 18 (Sunday) and 31-10-2026 (a Saturday month end) and on 31-12-2026, and passed under the full harness on 16, 18 and 31-10.
- The `test_settings_page` Week-ahead test passed with `CREAITE_NOW` set to 16-10 (Friday), 18-10 (Sunday), 31-10 (Saturday, month end) and 30-11-2026 (Monday), and under the full harness on 18-10.
- `test_meeting_hub` passed under the full harness on 15-10 and 31-10-2026. Its clocks are now all pinned.

**One harness artefact:** `test_settings_page`'s two-saves-in-one-second backup test fails when `CREAITE_NOW` freezes the server's clock to the minute. Under the real clock it passes, so this is not a defect.

## Other at-risk tests (grep for 2026-10-1x and 1x-10-2026 in `dev/tests`)

Most files with hard-coded October dates also pin the clock (`CREAITE_NOW`, `FIXED`, `pin_page_clock`, or `today=` passed in), and they are safe. The rest:

- **Server pinned but page on the machine's day** (the same shape as the meeting hub bug): `test_close_day` (16-10-2026 17:30), `test_evidence` and `test_status_live_browser` (09-10-2026), and `test_quality` (12-10-2026). Under the harness with the page on 16-10 and 19-10-2026 all four pass, so nothing on their pages reads Today in a way that breaks. Not changed.
- **Fixed dates used only as data** (an edit's value, a file name, a log line) with no comparison to today: `test_excel`, `test_alert_actions`, `test_ask_change_card`, `test_ask_confirmed_apply`, `test_review_nesting`, `test_minutes_review`, `test_decisions_prep`, `test_spec_fields`, `test_search_eml`, `test_setup_dashboard`, `test_first_run`, `test_markdown_views`, `test_activity_undo`, and the date-of-decision comments in `test_work_board`, `test_work_grouping`, `test_work_filters_live` and `test_record_commands`. Safe.
- **`test_new_item_peek`** types 15-10-2026 as a new item's due date. From 16-10 that date is in the past. Under the harness on 20-10-2026 it passes, so the form accepts a past date. Watch it if a "due date in the past" check is ever added.
- **`test_dashboard_editing` and `test_people_dashboard`** failed only under the harness. They build pages in their own way (`file://` or their own runner), which the harness cannot pin, so the failures are mixed-clock artefacts, not evidence of a real-date bug. They pass on the real day.
- The date-heavy files that pin their own clock (`test_pages`, `test_today_days`, `test_today_brief`, `test_close_day_guided`, `test_draft_chase`, `test_plain_dates`, `test_smart_updates`, `test_insight`, `test_prep_updates`, `test_schema_sprint5`, `test_status_facts`) were run under the harness on 19-10-2026. `test_today_days`, `test_today_brief`, `test_close_day_guided`, `test_draft_chase`, `test_plain_dates`, `test_smart_updates`, `test_prep_updates` and `test_status_facts` pass. There were three harness artefacts, none of them a real-date bug: `test_schema_sprint5`'s Excel tests (openpyxl rejects the faked datetime class), `test_insight`'s `test_brief_in_chrome`, and `test_pages`' `DependencyPageTests` (both are `file://` pages the harness cannot pin, so the page used the real day while the fixture used the faked one).

## Pattern to follow

- Pin both clocks together: `server_env` → `{"CREAITE_NOW": NOW}`, and `pin_page_clock(self.b, NOW)` in `setUp`.
- If a fixture uses `populate` (real-day relative), add the rows a test depends on itself, dated from the same clock the server reads.
- Never type a relative date ("+3d", "fri") and assume it lands on a working day, or on a date the item doesn't already have.
