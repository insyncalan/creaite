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
        n = b.eval("REV.filter(r=>!r.done).length")
        self.assertGreater(n, 0)
        b.eval("go('review')")
        self.assertEqual(self.title(), f"{base} · Review ({n})")            # what waits in Review
        b.eval("go('inbox')")
        self.assertEqual(self.title(), f"{base} · Intake")                  # Intake's own count is not in the title
        b.eval("go('cockpit','ABC')")
        self.assertEqual(self.title(), f"{base} · Example Programme")       # a project by its name
        b.eval("go('review'); REV[0].done=true; renderBadge()")
        self.assertEqual(self.title(), f"{base} · Review ({n - 1})")        # the count follows
        b.eval("REV[0].done=false; renderBadge()")
        b.eval("RBMARKED=true; tabTitle()")
        self.assertTrue(self.title().startswith(b.eval("RBMARK")))         # the finished-run mark still goes first
        b.eval("rbUnmark()")
        self.assertEqual(self.title(), f"{base} · Review ({n})")


if __name__ == "__main__":
    unittest.main()
