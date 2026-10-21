"""#285: the project page (cockpit) has no project dropdown between its ‹ › arrows. The arrows stay and still move between
projects, and the Projects list still reaches every project. The Milestones page keeps its own switcher. A real browser
against the real live server.

Run: python3 dev/tests/test_cockpit_no_dropdown_285.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402


class CockpitNoDropdown(LiveBrowserCase):
    shared_server = True

    def open(self, code):
        b = self.b
        b.eval(f"go('cockpit',{code!r})")
        b.wait(f"VIEW==='cockpit'&&COCK==={code!r}&&!!document.querySelector('#v-cockpit .pswitch')")

    def test_no_select_between_the_arrows(self):
        self.open("ABC")
        b = self.b
        self.assertFalse(b.eval("!!document.getElementById('projSw')"))
        self.assertEqual(b.eval("document.querySelectorAll('#v-cockpit .hhead select').length"), 0)
        self.assertEqual(b.eval("[...document.querySelectorAll('#v-cockpit .pswitch [data-psw]')].map(e=>e.dataset.psw)"), ["-1", "1"])

    def test_arrows_still_move_between_projects(self):
        self.open("ABC")
        b = self.b
        codes = b.eval("P.map(p=>p.code)")
        self.assertGreaterEqual(len(codes), 2)
        b.eval("document.querySelector('#v-cockpit [data-psw=\"1\"]').click()")
        nxt = codes[(codes.index("ABC") + 1) % len(codes)]
        b.wait(f"COCK==={nxt!r}")
        b.eval("document.querySelector('#v-cockpit [data-psw=\"-1\"]').click()")
        b.wait("COCK==='ABC'")

    def test_projects_list_reaches_every_project(self):
        b = self.b
        b.eval("go('projects')")
        b.wait("VIEW==='projects'&&!!document.querySelector('#v-projects [data-cock]')")
        listed = set(b.eval("[...document.querySelectorAll('#projTbl [data-cock]')].map(e=>e.dataset.cock)"))
        self.assertTrue(set(b.eval("P.map(p=>p.code)")) <= listed)

    def test_milestones_keeps_its_switcher(self):
        b = self.b
        b.eval("go('milestones','ABC')")
        b.wait("VIEW==='milestones'&&!!document.getElementById('mvProjSw')")


if __name__ == "__main__":
    unittest.main()
