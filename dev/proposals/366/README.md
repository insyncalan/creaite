# #366 slice README: the client-output review kit, tests landed by this slice

Tests only; no file under `system/` changed. No real defect found, so there is no FINDINGS.md.

## What landed

| File | Tests | Runtime | Protects | Kit probe it replaces |
|---|---|---|---|---|
| `dev/tests/test_calendar_client_outputs.py` | 5 | about 6 s | A saved calendar's title, place, organiser, body, attendee and attachment names, and a join link, meeting ID, passcode and dial-in, never reach the client report (draft, HTML, Word, filed), the client-safe Steerco data and Word one-pager, or the client-audience AI draft contexts. A confidential meeting keeps only title and times; a private one is Busy; their details are in no saved file and no client output. The follow-up email's facts carry the invite's attendees by design (recorded, and still free of join detail and held meetings). | `k26-b-outputs` (and the held/private lines of `k26-b-save`) |

Engine and local live server only (the report routes, `sweep.py calendar`, `report.py`, `drafts.py`); no browser, no Claude, no network.
`CREAITE_NOW` is pinned through `test_reports.NOW`; every address is `*.example`, the data is fictional. No kit helper is used.

## Groups already covered by Banner, or pending

- Group (1), the held reason absent from logs and exports: Banner's `test_k254_gaps_366.py` (branch `team-banner-366-track`, c4dbb972) already covers it, including the `held_reason_logged` mutant. It was written here first and then dropped as a duplicate.
- Group (2), the followed-person word in an outside email: pending Cap's answer; may arrive as Banner's `test_email_outside_gaps_366.py` (318851a9). Not written in this slice.
- Group (3), the 40 hostile `only` values: pending Cap's answer; may arrive as Banner's `test_k254_gaps_366.py`. Not written in this slice.
- Slice 1 (`test_track_crossed_366.py`) arrives separately.

## Python 3.9 floor

The file uses no 3.10+ syntax (no `match`, no `X | Y` annotations, no parenthesised context managers). `Path.unlink(missing_ok=True)` is 3.8+.

## --quick and the Chrome tier

`dev/tools/run_tests.py --quick` skips every Chrome-tier file, so a Chrome-tier file shows green there without having run. This file is quick tier (`run_support.is_chrome` is False): it imports only the class `ReportRoutes` from `test_reports`, which does not count as Chrome. It deletes that name after use so unittest does not collect the imported class's own tests. Other client-output tests (186, followed people, track review, save_not_blocked, held_missing_source, match_check, sweep_alerts, client_view) are partly Chrome tier: `--quick` alone does not prove them.

## How to run

    python3 dev/tests/test_calendar_client_outputs.py
    python3 dev/tools/run_tests.py --changed
