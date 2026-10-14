"""BL-318: a reload on Work puts back the view and every filter exactly as they were. Before the fix, an address with a view and
a project filter (#work=actions&v=open&p=ABC) came back as …&p=ABC&f=none with the view "Custom": parseHash read the project
filter as a filter set, so restoreNav took the filter branch instead of the view. A real browser against the real live server.

Run: python3 dev/tests/test_work_reload_address.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

READY = "typeof go==='function' && LIVE"


class ReloadKeepsViewAndFilters(LiveBrowserCase):
    shared_server = True

    def reload_at(self, addr):
        b = self.b
        b.goto(self.base + "/" + addr)
        b.wait(READY + " && VIEW==='work'")
        b.reload(READY)
        b.wait("VIEW==='work'")
        b.pump(0.2)

    def check(self, addr, wt, view, projects):
        self.reload_at(addr)
        b = self.b
        self.assertEqual(b.eval("WT"), wt)
        self.assertEqual(b.eval("WVIEW"), view)
        self.assertEqual(sorted(b.eval("[...PROJF]")), projects)
        h = b.eval("location.hash")
        self.assertIn(f"v={view}", h)
        self.assertNotIn("f=none", h)

    def test_actions_open_with_a_project(self):
        self.check("#work=actions&v=open&p=ABC", "actions", "open", ["ABC"])
        self.assertIn("Status: Open", self.b.eval("$('#wapplied').textContent"))

    def test_raid_open_with_two_projects(self):
        self.check("#work=raid&v=open&p=ABC,DEF", "raid", "open", ["ABC", "DEF"])

    def test_a_view_alone_still_survives(self):
        self.check("#work=actions&v=open", "actions", "open", [])

    def test_filters_without_a_view_still_survive(self):
        self.reload_at("#work=actions&p=ABC&st=Closed")
        b = self.b
        self.assertEqual(sorted(b.eval("[...PROJF]")), ["ABC"])
        self.assertEqual(b.eval("snapshot()"), {"st": ["Closed"]})
        self.assertIn("p=ABC", b.eval("location.hash"))
        self.assertIn("st=Closed", b.eval("location.hash"))

    def test_an_open_item_still_survives(self):
        b = self.b
        iid = b.eval("A.find(x=>x.p==='ABC'&&x.st==='Open').id")
        self.reload_at(f"#work=actions&v=open&p=ABC&item={iid}")
        self.assertEqual(b.eval("WVIEW"), "open")
        self.assertEqual(b.eval("[...PROJF]"), ["ABC"])
        self.assertIn(f"item={iid}", b.eval("location.hash"))


if __name__ == "__main__":
    unittest.main()
