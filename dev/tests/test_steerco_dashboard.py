"""Sprint 5 item 4 (BL-92): the "Draft the one-pager" link in a steering meeting's Prep, in a real browser against the live server.

Run: python3 dev/tests/test_steerco_dashboard.py   (needs Google Chrome; skipped otherwise)
"""
import json
import os
import subprocess
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402

TODAY = date.today()


class SteercoPrep(LiveBrowserCase):
    shared_server = True

    @classmethod
    def load(cls, v):
        populate(v)
        f = v.root / "system/staging/drafts/calendar.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"days": {TODAY.isoformat(): [
            {"id": "s1", "start": "09:00", "end": "10:00", "title": "ABC SteerCo"},
            {"id": "s2", "start": "10:30", "end": "11:00", "title": "ABC weekly sync"},
            {"id": "s3", "start": "13:00", "end": "14:00", "title": "Steering committee (portfolio)"},
            {"id": "s4", "start": "15:00", "end": "16:00", "title": "Steering update"}]}}))
        subprocess.run([sys.executable, str(v.root / "system/scripts/sweep.py"), "calendar", str(f)], cwd=v.root, check=True,
                       env={**os.environ, "CREAITE_NOW": f"{TODAY} 08:00"}, capture_output=True)
        subprocess.run([sys.executable, str(v.root / "system/scripts/build_dashboard.py")], cwd=v.root, check=True,
                       env={**os.environ, "CREAITE_NOW": f"{TODAY} 08:00"}, capture_output=True)

    def prep(self, title):
        b = self.b
        b.eval("go('today'); renderToday();")
        b.wait("document.querySelector('#dayMeets .dm')")
        b.eval(f"openPrep(prepTimed().find(e=>e.title===({title!r})), TODAY)")
        b.wait("document.getElementById('prepDlg').open && document.getElementById('prepBody').children.length")
        return b.eval("[...document.querySelectorAll('#prepBody .steerlink button')].map(x=>[x.getAttribute('aria-label'),x.dataset.ask])")

    def test_a_steering_meeting_for_a_project_offers_both_drafts(self):
        got = self.prep("ABC SteerCo")
        self.assertEqual(got, [["Draft the one-pager", "steerco one-pager ABC"],
                               ["Draft the client-safe one-pager", "steerco one-pager ABC client-safe"]])
        self.assertIn("nothing is sent", self.b.eval("document.querySelector('#prepBody .steerlink').textContent"))
        self.assertEqual(self.b.eval("document.querySelectorAll('#prepBody .steerlink').length"), 1)
        self.assertEqual(self.b.errors, [])

    def test_an_ordinary_meeting_has_no_link(self):
        self.assertEqual(self.prep("ABC weekly sync"), [])

    def test_a_portfolio_or_unmatched_steering_meeting_has_no_link(self):
        self.assertEqual(self.prep("Steering committee (portfolio)"), [])
        self.assertEqual(self.prep("Steering update"), [])                         # no project to draft for

    def test_pressing_it_closes_the_brief_and_asks_creaite(self):
        self.prep("ABC SteerCo")
        self.b.eval("window.SENT=[]; window.send=m=>{ SENT.push(m); }")           # what the chat would be sent, without running Claude
        self.b.click('#prepBody .steerlink button[data-ask="steerco one-pager ABC"]')
        self.b.wait("!document.getElementById('prepDlg').open")
        self.assertEqual(self.b.eval("SENT"), ["steerco one-pager ABC"])


if __name__ == "__main__":
    unittest.main()
