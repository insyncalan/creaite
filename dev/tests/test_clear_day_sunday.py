"""BL-104 Clear day (Sprint 4a): set a day's meetings aside in Intake's Calendar import, with the clock pinned to a Sunday, part 3 of 3 (the fixture is in clear_day_support.py).

Run: python3 dev/tests/test_clear_day_sunday.py   (the page tests need Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clear_day_support import ClearData, SUNDAY  # noqa: E402


class ClearDataSunday(ClearData, unittest.TestCase):
    NOW = SUNDAY



if __name__ == "__main__":
    unittest.main()
