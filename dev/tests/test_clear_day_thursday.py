"""BL-104 Clear day (Sprint 4a): set a day's meetings aside in Intake's Calendar import, with the clock pinned to a Thursday, part 2 of 3 (the fixture is in clear_day_support.py).

Run: python3 dev/tests/test_clear_day_thursday.py   (the page tests need Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clear_day_support import ClearData, ClearDayPage, THURSDAY  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402


class ClearDataThursday(ClearData, unittest.TestCase):
    NOW = THURSDAY


class ClearDayPageThursday(ClearDayPage, LiveBrowserCase):
    NOW = THURSDAY


if __name__ == "__main__":
    unittest.main()
