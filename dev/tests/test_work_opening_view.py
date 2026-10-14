"""BL-153: Work opens on the view Help says it does. A fresh browser profile (each test starts its own headless Chrome) on a new
vault opens Work on All open with nothing to explain; a vault whose Settings › Opening views says Overdue opens there and the
page says why, with Show all open. A real browser against the real live server.

Run: python3 dev/tests/test_work_opening_view.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402


class FreshProfile(LiveBrowserCase):
    def test_a_fresh_browser_opens_work_on_all_open(self):
        b = self.b
        b.click('.rail button[data-v="work"]')
        b.pump(0.3)
        self.assertEqual(b.eval("WT"), "actions")
        self.assertEqual(b.eval("WVIEW"), "open")
        self.assertIn("Status: Open", b.eval("$('#wapplied').textContent"))
        self.assertFalse(b.eval("!!document.querySelector('#wapplied .openedon')"))   # nothing to explain
        self.assertNotIn("Due: Overdue", b.eval("$('#wapplied').textContent"))
        b.click('#wtabs [data-t="raid"]')
        b.pump(0.3)
        self.assertEqual(b.eval("WVIEW"), "open")


class OpeningViewSetToOverdue(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        from test_dashboard import populate
        populate(v)
        cfg = v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data.setdefault("defaults", {})["actions_status_filter"] = "overdue"
        cfg.write_text(json.dumps(data, indent=2))

    def test_it_opens_there_and_says_why(self):
        b = self.b
        b.click('.rail button[data-v="work"]')
        b.pump(0.3)
        self.assertEqual(b.eval("WVIEW"), "overdue")
        note = b.eval("(document.querySelector('#wapplied .openedon')||{}).textContent||''")
        self.assertIn("Opened on Overdue", note)
        self.assertIn("Show all open", note)
        b.click("#wapplied [data-openall]")
        b.pump(0.3)
        self.assertEqual(b.eval("WVIEW"), "open")
        self.assertFalse(b.eval("!!document.querySelector('#wapplied .openedon')"))   # gone once the view changes
        b.eval("applyView('overdue'); workChanged()")                                   # chosen by hand: never explained
        b.pump(0.2)
        self.assertFalse(b.eval("!!document.querySelector('#wapplied .openedon')"))


if __name__ == "__main__":
    unittest.main()
