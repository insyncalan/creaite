"""#352: Today's My Commitments no longer carries the "N open actions have had no update for 7 days" line or its Draft updates button.
The draft itself stays (Work's bulk bar). Measured at 1400 and 900 px: the card renders, nothing spills sideways.

Run: python3 dev/tests/test_today_no_stale_line_352.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402


class NoStaleLine(LiveBrowserCase):
    shared_server = True

    def test_my_commitments_has_no_stale_block_and_does_not_overflow(self):
        b = self.b
        for width in (1400, 900):
            b.resize(width, 1000)
            b.eval("A.forEach(x=>x.upd_at='2026-01-01'); go('today'); renderToday()")      # every open action is stale
            b.wait("!!document.querySelector('#v-today')", 20)
            b.pump(0.8)
            self.assertFalse(b.eval("!!document.querySelector('#drStale, #v-today [data-drstale]')"), width)
            self.assertNotRegex(b.eval("document.getElementById('v-today').textContent"), r"had no update for", width)
            self.assertEqual(b.eval("document.documentElement.scrollWidth<=document.documentElement.clientWidth+1"), True, f"no sideways scroll at {width}")
        self.assertEqual(b.errors, [])


if __name__ == "__main__":
    unittest.main()
