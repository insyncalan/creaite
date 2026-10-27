# #389: a meeting processed from a file leaves Intake's Arrived list

Ordinary code only (`system/scripts/build_dashboard.py`, `system/scripts/minutes.py`); no guarded file. Tests:
`dev/tests/test_intake_processed_389.py`.

## What it does

A meeting processed from a dropped or uploaded file is recorded as `fp:<day>|<title>|<hash>` (no event ID), which never matched
its calendar row's key (`calendar:<event id>`), so the calendar row stayed in Arrived ("Transcript ready") beside the Done or
Drafted row for the same meeting. Now a calendar meeting with an event ID takes that processing when it is the only meeting
that day with that title (`minutes.norm_title`; the count covers the whole day, meetings set aside with Not needed or Later
included):

- a draft waiting in Review joins the calendar row, which shows Drafted (the file's own row is not listed);
- a filing this week (#307) marks the calendar row Done instead of making a second row;
- a filing in an earlier week marks it processed (`minutes.processed_on_meeting`).

Never linked: two meetings with the same day and title (no guess), a title that normalises to nothing (`[ABC]`), rejected
minutes (`not filed | 0`), comment lines, and someone else's minutes (#232 E1, Jarvis 27-10-2026: their keys come from
`minutes.by_others_keys`, proposals waiting in Review or applied). A meeting processed under its own key keeps its own date.

## Stated limits

- **The processing must use the meeting's day and title.** A file processed under another title (its file name, say) or
  another day (a late-evening meeting whose transcript is dated the next day, or in UTC) is not tied to the meeting; it stays
  in Arrived, as before #389.
- **Rejected minutes with the transcript filed still count.** A line such as `… | fp:<day>|<title>|… | transcripts/x.vtt | 0`
  (minutes rejected, the transcript filed) marks the meeting processed, as the same line under the meeting's own calendar key
  always has. Only `not filed | 0` is treated as no processing.
- **Cost.** `minutes.by_others_keys` reads every proposal in `system/staging/` and `system/staging/applied/` (kept for good)
  on each build: measured 0.106 s for 3,000 files of about 14 KB (Stark, 27-10-2026). Fine now; a cache can come later.
