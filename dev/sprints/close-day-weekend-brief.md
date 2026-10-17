# Close the day: a Friday card shows the weekend (brief for Team Stark, #187)

Product Manager, 17-10-2026. Sonnet, size S. Alan (17-10-2026): show the weekend's planned work on a Friday close card.

1. **Today:** the Close the day card shows the next working day only (`next_working_day` in `system/scripts/close_day.py`), so a planned Saturday or Sunday meeting does not appear on Friday.
2. **Change:** on a Friday, or the last working day before a weekend (a holiday Friday means Thursday), the card also lists what is planned for Saturday and Sunday, under the next working day, one line each as the day line writes them (time, title); a weekend with nothing planned adds nothing (no "nothing planned" line).
3. **Plain code only:** `close_day.py` and the card's rendering; reads the same saved calendar and day plan as today; no new setting, no guarded file.
4. **Tests** (extend `test_close_day.py`, found in #138's check on `weekend-gap-138`): `test_friday_card_shows_weekend_work`, `test_friday_card_no_weekend_line_when_empty`, `test_midweek_card_unchanged`, `test_thursday_before_a_holiday_friday` (the date helpers follow `CREAITE_NOW`, so pin the clock; do not use the real date, see #178).
5. **Done when:** the Friday card lists planned Saturday and Sunday work; every other day is unchanged; the four tests pass.
