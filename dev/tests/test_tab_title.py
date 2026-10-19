"""BL-152: the browser tab title says where you are and what is waiting ("creaite · Review (4)", "creaite · Work",
"creaite · <Project name>"); the finished-run mark (BL-139) still goes first. A real browser against the real live server.

Run: python3 dev/tests/test_tab_title.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402


class TabTitle(LiveBrowserCase):
    shared_server = True

    def title(self):
        return self.b.eval("document.title")

    def test_the_title_follows_the_page_the_project_and_the_count(self):
        b = self.b
        base = b.eval("BASETITLE")
        self.assertTrue(base.endswith("creaite"))
        self.assertEqual(self.title(), f"{base} · Today")
        b.eval("go('work')")
        self.assertEqual(self.title(), f"{base} · Work")
        n = b.eval("irLiveCounts().badge")                                  # #232-C: ready to process plus proposals to approve
        self.assertGreater(n, 0)
        for old in ("review", "inbox"):                                     # the old names open the one page
            b.eval(f"go({old!r})")
            self.assertEqual(self.title(), f"{base} · Intake and Review ({n})")
        b.eval("go('cockpit','ABC')")
        self.assertEqual(self.title(), f"{base} · Example Programme")       # a project by its name
        k = b.eval("irModel().mail.routine.concat(irModel().mail.needs, irModel().other.needs, irModel().other.routine, irModel().meetings.flatMap(m=>[...m.groups.needs,...m.groups.routine]))[0]")
        b.eval(f"go('review'); REV.find(r=>r.n=={k}).done=true; renderBadge()")
        self.assertEqual(self.title(), f"{base} · Intake and Review ({n - 1})")   # the count follows
        b.eval(f"REV.find(r=>r.n=={k}).done=false; renderBadge()")
        b.eval("RBMARKED=true; tabTitle()")
        self.assertTrue(self.title().startswith(b.eval("RBMARK")))         # the finished-run mark still goes first
        b.eval("rbUnmark()")
        self.assertEqual(self.title(), f"{base} · Intake and Review ({n})")


if __name__ == "__main__":
    unittest.main()
