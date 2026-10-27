# #250 slice B: the calendar hold (2.6.10)

Code: `system/scripts/transcript_hold.py` (new, plain code, not guarded). Tests: `dev/tests/test_transcript_hold.py`, cases in
`dev/tests/fixtures/transcript_hold_hostile.json` (156). Closes Cap's HIGH (H1, order c): a confidential event saved with `teams=False` is
never read in the run, so nothing marked it held. The saved calendar now decides, whether or not the run read the event.

## Interface

```
calendar_hold(event, saved_calendar, live=None, created=None, tz=None) -> (held: bool, reason: str)
same_meeting(a, b) -> bool
read_saved_calendar(path=None) -> dict | None        # the only file read; invite_clean.read_calendar today
hold_for(event, live=None, created=None, tz=None)     # calendar_hold(event, read_saved_calendar(), ...)
```

- `event`: dict `{id, day, start, end, title}` (start/end `HH:MM` local, or an ISO stamp; an offset or Z is turned into `tz`, default the
  machine's), or just the event ID (a string, `calendar:` prefix allowed). `saved_calendar`: calendar.json as loaded. `live`: the event as
  the run read it (`{"sensitivity": ...}`), or None. `created`: the transcript's created time, when known.
- Pure: no I/O, no clock, inputs never changed, same answer twice. Only `re`, `unicodedata`, `datetime` are imported.
- To point at another reader later (the 2.6.9 calendar gateway), change the body of `read_saved_calendar` only.

## Rules

1. Held when the saved calendar is unusable (not an object, `days` not an object, a non-object row on the event's day).
2. The meeting is found by `same_meeting`: IDs equal; else (no ID match) day, start and end equal and normalised title equal. Never a title
   alone, never times alone, never an overlap alone. Empty titles and empty times never match.
3. A matched row is open only if it says exactly `normal` (case and spaces ignored) with no private or confidential flag. Missing or odd
   sensitivity holds. A private or personal word is `private`; anything else non-empty is `confidential`.
4. No matching row holds. More than one distinct matching row (different ID, times or title) holds; identical duplicates count once.
5. A row whose ID differs only by case, percent-encoding, padding, width or spaces inside is a look-alike: held as ambiguous.
6. Closed-meeting overlap (hold-only): with no ID match, a closed row on the day that overlaps the event's times holds. With a `created`
   time (either path), a closed row whose window `[start - 15 min, end)` contains it holds; an unreadable `created` or a closed timed row
   with unreadable times holds. An all-day closed row holds nothing (see decision 1).
7. The live event can only add a hold: not exactly `normal`, or not an object, holds. It never opens anything.

## Reasons (fixed words; never a title, ID or time; the module logs and prints nothing)

`normal` (not held), `confidential`, `private`, `unknown sensitivity`, `no event`, `calendar unreadable`, `not in saved calendar`,
`ambiguous`, `live event not normal`, `overlaps closed meeting`, `times unreadable`. Priority for several closed matches:
confidential, private, unknown sensitivity. Slice D's "short reason" line maps these to words for Alan; the constant `REASONS` is the list.

## How the other slices call it

- **Slice A, `SweepFetch(hold=...)`:** `hold` is a callable `(event_dict, live_or_None, created_or_None) -> (held, reason)`; the default is
  `transcript_hold.hold_for`. In `settle` (end of an answered run) for each queued transcript: build the event dict from the event read or
  from the saved row it was tied to, pass the live event read in this run (None if not read: order c), and the transcript's created time;
  held means drop the text, count it, and keep the reason for the closure line (counts and reasons only). A raise from the hook is a hold.
  Read the calendar once per settle by calling `calendar_hold(..., read_saved_calendar())` yourself if many transcripts are queued.
- **Guarded G3 (`live_server.py`):** no new logic. The observer passes the event reads to `SweepFetch.observe`, and `_fetch_finish` runs
  `finish(answered)`, which calls the hold. G3 never reads the calendar itself. The live event's sensitivity reaches the hold only through
  `live=`, so G3 cannot lower a hold. A stopped, timed-out or failed run does not settle (plan 4.3).
- `meeting_key` over-merging (Cap L2) is slice A's; `same_meeting` here is the calendar match only.

## Decisions needed

1. All-day closed rows (a private "Out of office") hold nothing, otherwise one private all-day entry stops every fetch that day. Accept?
2. The plan's sweep stub for an ignored confidential event is NOT built: `invite_clean.clean_calendar` keeps only `fetched`, `to`, `days`,
   so a stub needs a change to that allow-list and its idempotence tests. Until then an event dropped by an ignore rule (private events are
   dropped by the built-in rule) is "not in saved calendar" and held, which is safe; the residual gap is a confidential event dropped by a
   rule whose twin at the same times/title is saved as normal. Build the stub in this release, or accept?
3. DST: a transcript stamp in the repeated hour when clocks go back cannot be turned into one wall time, so it fails to match and is held.
4. Where `meeting_key` ties several events to one URL, slice A should call the hold for each tied event and hold if any is held.
