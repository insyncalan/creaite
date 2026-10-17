"""#177 (Review age, option A): age as quiet text, one banner when the queue is old, the outlier marked, Oldest first.

Run: python3 dev/tests/test_review_age.py   (needs Google Chrome; skipped otherwise)

The clock is pinned (CREAITE_NOW, a Wednesday) and every fixture day is counted back from it. The stale setting is its default, 7 days,
so an outlier is older than 14.
"""
import json
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_tracker import action  # noqa: E402

NOW = "2026-10-14 09:30"
SRC = "Teams · Chat: Omar"


def created(days_ago):
    return (datetime.strptime(NOW, "%Y-%m-%d %H:%M") - timedelta(days=days_ago)).strftime("%Y-%m-%dT09:00:00")


def stage(v, ages):
    for i, d in enumerate(ages):
        p = v.propose(f"2026-10-0{i + 1}-0900-age{i}", [{**action(1, project="ABC", description=f"Age fixture {i}", owner="Sara Example", due_date="2026-12-01", source=SRC),
                                                           "decision": "pending"}])
        data = json.loads(p.read_text())
        data["created"] = created(d)
        p.write_text(json.dumps(data, indent=2))


class AgeBase(LiveBrowserCase):
    ages = ()
    width, height = 1500, 1100

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": NOW}

    @classmethod
    def load(cls, v):
        populate(v)
        stage(v, cls.ages)

    def open_review(self):
        b = self.b
        b.eval("go('review')")
        b.wait("document.querySelector('#reviewBody tr[data-n]')")
        return b

    def texts(self, b):
        return b.eval("[...document.querySelectorAll('#reviewBody tr[data-n]')].filter(t=>/Age fixture/.test(t.textContent)).map(t=>t.querySelector('td.title').textContent.match(/Age fixture \\d/)[0]+'|'+t.querySelector('.rvage').textContent)")


class AllOld(AgeBase):
    ages = (12, 12, 9, 30)

    def test_banner_age_text_and_oldest_first(self):
        b = self.open_review()
        und = b.eval("REV.filter(r=>!r.done).length")
        self.assertEqual(b.eval("document.querySelectorAll('#reviewBody .tag.stale').length"), 0)
        self.assertNotIn("stale", b.eval("document.getElementById('rvSub').textContent"))
        self.assertIn("waiting", b.eval("document.getElementById('rvSub').textContent"))
        self.assertEqual(b.eval("document.querySelectorAll('#reviewBody .rvage.old').length"), 0)          # all old: no row is singled out
        self.assertEqual(b.eval("document.getElementById('rvAgeBanner').textContent.trim().replace(/\\s+/g,' ').replace(/([.?])(?=\\S)/g,'$1 ')"),
                         f"All {und} have waited more than 7 days. Oldest first? Oldest first")
        self.assertEqual(self.texts(b)[:4], ["Age fixture 0|12 days", "Age fixture 1|12 days", "Age fixture 2|9 days", "Age fixture 3|30 days"])
        b.click("#rvOldest")
        b.pump(0.2)
        self.assertIn("Oldest first: on", b.eval("document.getElementById('rvOldest').textContent"))
        self.assertEqual(self.texts(b)[0], "Age fixture 3|30 days")
        b.click("#rvOldest")
        b.pump(0.2)
        self.assertEqual(self.texts(b)[0], "Age fixture 0|12 days")


class Mixed(AgeBase):
    ages = (24, 3, 1, 0)

    def test_one_outlier(self):
        b = self.open_review()
        und = b.eval("REV.filter(r=>!r.done).length")
        self.assertGreaterEqual(und, 4)
        self.assertEqual(b.eval("document.getElementById('rvAgeBanner').textContent.trim().replace(/\\s+/g,' ').replace(/([.?])(?=\\S)/g,'$1 ')"), "1 has waited 24 days. Oldest first")
        self.assertEqual(b.eval("[...document.querySelectorAll('#reviewBody .rvold')].map(e=>e.textContent)"), ["Oldest · 24 days"])
        self.assertEqual(b.eval("[...document.querySelectorAll('#reviewBody .rvage.old')].map(e=>e.textContent)"), ["24 days"])
        self.assertEqual(self.texts(b)[1:], ["Age fixture 1|3 days", "Age fixture 2|1 day", "Age fixture 3|today"])
        b.click("#rvOldest")
        b.pump(0.2)
        self.assertEqual(self.texts(b)[0], "Age fixture 0|24 days")

    def test_needs_stale_filter_still_works(self):
        b = self.open_review()
        b.click('#rvfilters [data-rvf="nd"]')
        b.click('#rvf-nd input[data-fk="nd"][value="stale"]')
        b.pump(0.2)
        self.assertEqual(b.eval("rvShown().filter(r=>/Age fixture/.test(r.rec.t||'')).map(r=>r.rec.t)"), ["Age fixture 0"])


class NoneOld(AgeBase):
    ages = (5, 3, 1, 0)

    def test_no_banner(self):
        b = self.open_review()
        self.assertTrue(b.eval("!document.getElementById('rvAgeBanner')"))
        self.assertEqual(b.eval("document.querySelectorAll('#reviewBody .rvold').length"), 0)
        self.assertEqual(self.texts(b), ["Age fixture 0|5 days", "Age fixture 1|3 days", "Age fixture 2|1 day", "Age fixture 3|today"])


class Themes(AgeBase):
    ages = (24, 3)

    def test_both_palettes_light_and_dark(self):
        from live_browser import TEST_PALETTES_JS
        b = self.open_review()
        for pal in b.eval(TEST_PALETTES_JS):
            for th in ("light", "dark"):
                b.eval(f"document.documentElement.dataset.theme={th!r}; document.documentElement.dataset.palette={pal!r}")
                b.pump(0.1)
                fg = b.eval("getComputedStyle(document.querySelector('#rvAgeBanner')).color")
                bg = b.eval("getComputedStyle(document.querySelector('#rvAgeBanner')).backgroundColor")
                self.assertNotEqual(fg, bg)


if __name__ == "__main__":
    unittest.main()
