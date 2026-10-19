"""#232-B (v2.5.0): the standing rules on Intake and Review's proposal rows, in a real browser: full project names (the short code only
inside an item's ID), no VIP label anywhere on a row (a followed person's proposal looks like any other), dates as DD-MM-YYYY, and
the source line names where it came from without a time. (The meeting rows' rules are in the Intake side's tests.)

Run: python3 dev/tests/test_intake_review_rules.py   (needs Google Chrome; skipped otherwise)
"""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import intake_review_support as S  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402


class Rules(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 1000

    @classmethod
    def load(cls, v):
        S.load(v)

    def rows(self):
        S.open_meeting(self.b)
        self.b.wait("!!document.querySelector('#v-intake-review [data-irsec=mail]')")
        return self.b.eval("[...document.querySelectorAll('#v-intake-review tr.irprop')].map(t=>t.textContent)")

    def test_no_vip_label_on_any_row(self):
        rows = self.rows()
        self.assertTrue(any("Share the pilot plan" in r for r in rows))
        self.assertFalse(any(re.search(r"\bvip\b", r, re.I) for r in rows))

    def test_project_names_not_codes(self):
        rows = self.rows()
        for r in rows:
            self.assertNotRegex(re.sub(r"\b[A-Z]{2,7}-[A-Z]-\d+\b", "", r), r"\bABC\b", r)       # a code only as the prefix of an item ID
        self.assertTrue(any("Example Programme" in r for r in rows))

    def test_dates_are_written_day_month_year(self):
        rows = self.rows()
        self.assertTrue(any("due 04-11-2026" in r for r in rows))
        for r in rows:
            self.assertNotRegex(r, r"\d{4}-\d{2}-\d{2}", r)

    def test_source_line_has_no_times(self):
        self.rows()
        for src in self.b.eval("[...document.querySelectorAll('#v-intake-review tr.irprop .icsrc')].map(x=>x.textContent)"):
            self.assertNotRegex(src, r"\d{1,2}:\d{2}", src)


if __name__ == "__main__":
    unittest.main()
