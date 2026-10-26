# #375 E1: readers migration recipe for slice S4

For `calendar_gateway` (S3, `system/scripts/calendar_gateway.py`). Line numbers are on the S3 base (418c1da4); the plan's numbers (v268-bare21) have drifted, the table below gives both. No reader is changed in S3. Each reader changes by **one line**: replace `invite_clean.read_calendar(paths.CALENDAR)` (or the direct JSON read) with `calendar_gateway.read("<purpose>")`, and add `import calendar_gateway  # noqa: E402` beside the existing `import invite_clean` (drop that import only if nothing else in the file uses it). `read` raises `OSError` / `ValueError` exactly like `read_calendar`, so the existing `except` clauses stay. An unknown purpose raises `calendar_gateway.UnknownPurpose` (a `LookupError`), deliberately not caught by those clauses.

Rows come back with the same keys as before, minus what the purpose does not allow (fields table in the gateway's docstring). A reader that needs a field its purpose lacks must change purpose, not read the file.

| # | Plan ref | Reader (file:line on this base) | Today | One-line change | Purpose |
|---|---|---|---|---|---|
| 1 | build_dashboard 2043 | `build_dashboard.py:2043` (`calendar()`, Today's day view) | `cal = invite_clean.read_calendar(paths.CALENDAR)` | `cal = calendar_gateway.read("day")` | `day` |
| 2 | build_dashboard 2590 | `build_dashboard.py:2590` (`saved_calendar_days()`) | `return invite_clean.read_calendar(paths.CALENDAR).get("days") or {}` | `return calendar_gateway.read("prep_panel").get("days") or {}` | `prep_panel` |
| 3 | build_dashboard 2844 | `build_dashboard.py:2844` (Intake meeting rows) | `cal = invite_clean.read_calendar(paths.CALENDAR)` | `cal = calendar_gateway.read("day")` | `day` |
| 4 | build_dashboard 3159 | `build_dashboard.py:3159` (`fetched`, bypasses) | `fetched = json.loads(paths.CALENDAR.read_text(encoding="utf-8")).get("fetched")` | `fetched = calendar_gateway.read("meta").get("fetched")` (keep the `except (OSError, ValueError, AttributeError)`) | `meta` |
| 5 | close_day 347 | `close_day.py:347` | `cal = invite_clean.read_calendar(paths.CALENDAR)` | `cal = calendar_gateway.read("day")` | `day` |
| 6 | transcripts 222 | `transcripts.py:222` (`calendar_rows`) | `cal = invite_clean.read_calendar(paths.CALENDAR)` | `cal = calendar_gateway.read("day")` (uses `id`, `all_day`, `end`, `title`, `private`: all in `day`) | `day` |
| 7 | drafts 1301 | `drafts.py:1301` (`calendar_event`; body used at 1140, the 400-char source line at 1162) | `days = invite_clean.read_calendar(paths.CALENDAR).get("days") or {}` | `days = calendar_gateway.read("agenda").get("days") or {}` | `agenda` |
| 8 | drafts 1693 | `drafts.py:1693` (`_meeting_attendees`) | `days = invite_clean.read_calendar(paths.CALENDAR).get("days") or {}` | `days = calendar_gateway.read("day").get("days") or {}` (attendee names are in `day`: plan Q4 default; the gateway also keeps `type` and `response`) | `day` |
| 9 | prep_page 70 | `prep_page.py:70` (`_event`; body goes on at 360 via `_prep_meeting`) | `days = invite_clean.read_calendar(paths.CALENDAR).get("days") or {}` | `days = calendar_gateway.read("prep_page").get("days") or {}` (first migration; corrected in fix4: `read("prep_panel")`, see below) | `prep_panel` |
| 10 | prep_shape 342 | `prep_shape.py:342` (`body = ctx["meeting"]["body"]`, cut to 600 at 344) | no read of its own: the row comes from `prep_page._prep_meeting` (`prep_page.py:199`) / the dashboard's `prep_entry` (`build_dashboard.py:3374`), both built from reader 2 or 9 | no edit in `prep_shape.py`. Reader 9 and 2 already hand over a body of at most 1,500 whole lines; to make the 600 bound a property of the data, change `prep_page.py:199` to take `ev` from `calendar_gateway.read("shape")` for the shape path only, or leave the existing `short(body, 600)` (it cuts mid-line; the gateway's `shape` view cuts whole lines). Recommended: leave, and add the S4 test that the Shape prompt holds no more than 600 characters of body | `shape` (optional) |
| 11 | calendar_refresh 91 | `calendar_refresh.py:91` (`outcome`, bypasses) | `held = json.loads(paths.CALENDAR.read_text(encoding="utf-8")).get("days") or {}` | `held = calendar_gateway.read("meta").get("days") or {}` (counts `days` and `meetings` only) | `meta` |
| 12a | sweep 656 | `sweep.py:656` (`calendar_start`: `fetched`, `to`) | `data = json.loads(paths.CALENDAR.read_text(encoding="utf-8"))` | `data = calendar_gateway.read("meta")` | `meta` |
| 12b | sweep 671 | `sweep.py:671` (`calendar_span`: `fetched`, `to`) | `data = json.loads(paths.CALENDAR.read_text(encoding="utf-8"))` | `data = calendar_gateway.read("meta")` | `meta` |
| 13 | sweep 760 | `sweep.py:760` (`keep_held_past_days`, inside the save lock) | raw JSON, then `invite_clean.clean_row` per row at ~765 | **stays a raw read (it is a writer path)**; change only the per-row call to `calendar_gateway.stamp_row(r)` so a stamped row is kept as stored and an unstamped one is filtered and stamped | writer |
| 14 | sweep 821/834 | `sweep.py:816-838` (`_clean_calendar_file`, `rescrub_calendar`) | raw JSON, `clean_row`, atomic write | stays the one rewrite path: replace the cleaning by `calendar_gateway.stamp_calendar(cal)` (stamps every row and the top level); the lock, retry and compare-before-write logic is untouched | writer |
| 15 | sweep 875 | `sweep.py:875` (`saved_meetings_from`, counts) | `held = json.loads(paths.CALENDAR.read_text(encoding="utf-8")).get("days") or {}` | `held = calendar_gateway.read("meta").get("days") or {}` | `meta` |
| 16 | sweep 1012-1020, 1240-1250 | `sweep.py:989` (`calendar()` save, lock at ~1012) and `sweep.py:898` (`calendar_row`) / `:1236` (`invite_details`) | `row.update(invite_details(ev))`, `invite_details` uses `invite_text(ev.get("body"))` | the row written must carry `clean`: in `calendar_row` end with `return calendar_gateway.clean_row(row)` (or `invite_details` returns the filtered body and `calendar_row` sets `row["clean"] = calendar_gateway.CLEAN`); before the atomic write of the whole file call `calendar_gateway.stamp_calendar(saved)` so the top level is stamped too; `with calendar_gateway.lock():` may replace `sweep.calendar_lock()` (same lock file) | writer |
| 17 | live_server 4754, 4828 | `live_server.py:4754`, `:4828` | `stat` only (cache stamps) | no change (guarded file) | none |
| 18 | capture 338 | `capture.py:336-338` (sensitivity of one event, through `build_dashboard.saved_calendar_days()`) | no read of its own | no edit: reader 2 serves `sensitivity` and `private` (HEAD fields, forced for private and confidential rows) | none |

## Other callers of `saved_calendar_days()` (all follow reader 2)

`build_dashboard.py:2568` (prep entries), `:3148` (the Prep line; strips `PREP_ONLY` = body, attendees, attachments, organiser_email at 3335 before the page), `prep_page.py:264` (`_entry_for`), `capture.py:336`. They need the body / attachments for ranking (`build_dashboard.py:3399`), so `prep_panel` is the right purpose for the one shared function; nothing else changes.

## Order and checks for S4

1. Add the import and change the lines above, files in the table's order; run each file's own tests.
2. Update the tests that write `calendar.json` by hand: add `"clean": 1` to a row you want served as written, or leave it unstamped and expect the in-memory filter (body lines with a URL or a long digit run go).
3. Add the plan's grep test: no file in `system/scripts` other than `calendar_gateway.py`, the sweep writer lines (13, 14, 16) and the `live_server.py` stat lines reads `paths.CALENDAR` content or `calendar.json`.
4. `test_calendar_readers_purpose.py`: for each reader, `day` and `meta` rows have no `body`; `prep_*` and `agenda` bodies are at most 1,500 characters; `shape` at most 600; the Today and Intake output is unchanged for an unstamped calendar of normal rows with no body.
5. Not in scope here: `invite_clean.read_calendar` keeps working until S5.

## Purpose table and reader audit (emailfix, 26-10-2026)

Found by `test_drafts_email.py` (first failing commit e633e5fd, drafts migrated): the `day` view dropped attendee addresses, which the 2.6.8 read kept. Three readers used them. Fix: the field `attendees_addr` (output key `attendees`, with `email`) and the purpose `intake`.

| Purpose | Fields returned | Body |
|---|---|---|
| meta | id | none |
| day | HEAD + where, teams, organiser, recurrence, attendees (name, type, response) | none |
| intake | day, attendees with email | none |
| prep_rank | day + attachments | 1,500 |
| prep_panel | day, attendees with email, attachments, organiser_email | 1,500 |
| prep_page | day + attachments | 1,500 |
| agenda | day, attendees with email | 1,500 |
| shape | HEAD | 600 |

A private or confidential event returns HEAD only in every purpose (no attendee, no address).

| Reader (file:function) | Purpose | Fields it reads | Result |
|---|---|---|---|
| build_dashboard.calendar | day | title, start, end, id, private, sensitivity, where, teams, organiser, recurrence (body, attendees, attachments, organiser_email are popped) | OK |
| build_dashboard.saved_calendar_days (prep entries, Week ahead, capture) | prep_panel | body, attachments, organiser, recurrence, attendees name/type/response, attendee email (prep_match_ev, meeting_answer domain match, #328) | was LOST (email), fixed |
| build_dashboard.inbox_meetings | intake | where/teams/organiser/private/sensitivity/id, attendee email (meeting_answer, offer_signal) | was LOST (email), fixed |
| build_dashboard.calendar_days (fetched) | meta | fetched | OK |
| close_day.Lookup.meeting | day | id, private, title | OK |
| transcripts.calendar_rows | day | id, all_day, end, start, teams, private, title | OK |
| drafts.calendar_event (followup_facts) | agenda | sensitivity, attendees name and email, id, day, start, title | was LOST (email), fixed |
| drafts._meeting_attendees | day | sensitivity, title, attendee name | OK |
| prep_page._event (also prep_view.people / brief at prep_view.py:196 and :488, which read `organiser_email` and fall back to it when the organiser has no name) | prep_panel | title, start, end, where, organiser_email, attendee email | was LOST (organiser_email; Banner H1), fixed in fix4 |
| calendar_refresh.outcome, sweep.calendar_fetch_from / calendar_span / saved_meetings_from | meta | fetched, to, days (counts) | OK |

Guarded by `dev/tests/test_calendar_readers_golden.py`: each reader's output on a fixture calendar equals the 2.6.8 output stored in `dev/tests/fixtures/readers_golden_268.json`, except the differences listed in its ALLOWED table.

## fix4 (Banner's review of 08:10)

- H1: `prep_page._event` reads `prep_panel`, so `prep_view.people` / `brief` get `organiser_email` again. The golden test now runs `prep_view.brief` people for an address-only organiser and has no allowance for it.
- H2: the stamp is now `clean` (>= CLEAN) plus `clean_v` (`invite_filter.VERSION`, `calendar_gateway.fingerprint()`). A row without the right `clean_v`, or not well formed, is filtered in memory when the cache is filled (once per file version) and the rescrub writes it back stamped. A filter fix therefore reaches saved rows by bumping `invite_filter.VERSION`; no CLEAN bump is needed. Re-filtering every row on every cache fill was measured and rejected: the body filter costs about 8 ms cpu a row (short fields 0.6 ms), so 3,000 rows would take tens of seconds. Trusted rows cost no filtering (test: 3,000 rows under 3 s cpu on a loaded laptop).
- M1: `keep_row` works out sensitivity before trimming; a bare `confidential: true` becomes `sensitivity` and the body is dropped. M2: the sweep's `_stamped` is `calendar_gateway.stamp_row` (stamped AND well formed).
- Left as is, by decision: L1 a private row keeps head fields only, so its `teams` flag is not served (Intake may say "Not a Teams meeting" for a private meeting); L2 meeting counts fall when the file holds junk rows (they are not meetings); L3 the attendee `registered` flag is dropped (no reader uses it); L4 a nameless attendee's address is shown as the name in day views, as in 2.6.8.
