# #341 item 17: amber applied (25-10-2026)

Amber now means "at risk" and nothing else. In plain words for the release notes:

- Amber stays only where something is at risk: a project's health "At risk" and its trend, a milestone at risk (and a dependency that puts one at risk), a usage budget close to its limit, and the amber flag in reports and the health menu.
- Things that need you or need approval are teal. A Health problem, a save conflict and error banners are red. A sensitive change is a neutral chip with a lock. Age, stale and caution notes are neutral, with an icon or words.
- Test: `dev/tests/test_amber_uses.py` reads `dev/tests/amber-allowed.txt`; a new amber use fails until Alan adds it to that list.
- Goldens were not re-recorded; the screens that changed are listed in the report.
