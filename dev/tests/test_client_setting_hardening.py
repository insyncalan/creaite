"""#233 part b, Team Cap's low findings on the client report setting writes (review of p240-h3, #135, 20:25).

Run: python3 dev/tests/test_client_setting_hardening.py   (the page tests need Google Chrome; skipped otherwise)

L4 a fenced or quoted "Client report:" line is not the setting (page and Python reader); L5 a file changed since it was read is
never written over; L6 no absolute path in a failed-save toast; L10 the server refuses a client draft, save, export and approve
while the project's setting is off, and still opens a client report that exists.
"""
import re
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
import build_dashboard as bd  # noqa: E402
import test_dashboard  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402
from test_reports import ABC, ReportRoutes  # noqa: E402
from test_tracker import ABC as ABC_DIR  # noqa: E402


class Reader(unittest.TestCase):
    def memory(self, text):
        d = Path(tempfile.mkdtemp())
        (d / "CLAUDE.md").write_text("# ABC - X\n\n- **Client / partner:** Example Client Ltd\n" + text + "\n")
        return bd.memory(d)

    def test_l4_a_fenced_or_quoted_line_is_not_the_setting(self):
        self.assertTrue(self.memory("```\n- **Client report:** off\n```")["client_report"])
        self.assertTrue(self.memory("> - **Client report:** off")["client_report"])
        self.assertFalse(self.memory("```\n- **Client report:** on\n```\n- **Client report:** off")["client_report"])


class ClientOff(unittest.TestCase):
    """L10: the setting is enforced by the server, not only hidden in the page."""
    setUpClass = classmethod(ReportRoutes.setUpClass.__func__)
    tearDownClass = classmethod(ReportRoutes.tearDownClass.__func__)
    post = ReportRoutes.post
    WEEK = "2026-10-09"

    def setting(self, state):
        mem = self.v.root / ABC / "CLAUDE.md"
        text = re.sub(r"- \*\*Client report:\*\*[^\n]*\n", "", mem.read_text())
        mem.write_text(text.replace("- **Client report rhythm:**", f"- **Client report:** {state}\n- **Client report rhythm:**", 1))

    def tearDown(self):
        self.setting("on")

    def test_l10_off_refuses_a_new_client_draft_but_not_a_weekly_one(self):
        self.setting("off")
        r = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": "2026-10-23"})
        self.assertFalse(r["ok"], r)
        self.assertIn("client report", r["message"])
        self.assertTrue(self.post("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": "2026-10-23"})["ok"])

    def test_l10_off_refuses_client_save_export_and_approve_but_still_reads_an_existing_one(self):
        self.setting("on")
        made = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": self.WEEK})
        self.assertTrue(made["ok"], made)
        doc = made["doc"]
        self.assertTrue(self.post("/api/report/save", {"doc": doc})["ok"])
        self.setting("off")
        for path, body in (("/api/report/save", {"doc": doc}),
                           ("/api/report/export", {"kind": "client", "code": "ABC", "week_ending": self.WEEK, "fmt": "html"}),
                           ("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": self.WEEK})):
            r = self.post(path, body)
            self.assertFalse(r["ok"], (path, r))
            self.assertIn("client report", r["message"], path)
        again = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": self.WEEK})
        self.assertTrue(again["ok"], again)                                   # reading what exists stays allowed
        self.assertEqual(again["where"], "draft")

    def test_l10_on_and_a_missing_line_still_work(self):
        self.setting("on")
        self.assertTrue(self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": "2026-10-16"})["ok"])
        mem = self.v.root / ABC / "CLAUDE.md"
        mem.write_text(re.sub(r"- \*\*Client report:\*\*[^\n]*\n", "", mem.read_text()))
        self.assertTrue(self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": "2026-10-30"})["ok"])


class Page(LiveBrowserCase):
    """L4, L5, L6 in the real page (the Client report panel's switch)."""
    shared_server = True
    width, height = 1400, 1000

    @classmethod
    def load(cls, v):
        test_dashboard.populate(v)
        v.run(script="build_dashboard.py")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.original = (cls.v.root / ABC_DIR / "CLAUDE.md").read_text()

    @property
    def memory(self):
        return self.v.root / ABC_DIR / "CLAUDE.md"

    def setUp(self):
        super().setUp()
        self.memory.write_text(self.original)
        self.b.reload("typeof go==='function' && LIVE")

    def toggle(self):
        self.b.eval("openClientReport('ABC')")
        self.b.wait("!!document.querySelector('#crPanel')")
        self.b.eval("document.querySelector('#cfgOn').click()")

    def snack(self):
        return self.b.eval("document.getElementById('snackT').textContent")

    def wait_snack(self):
        self.b.wait("/Not saved/.test(document.getElementById('snackT').textContent)", 10)
        return self.snack()

    def fetch_hook(self, js):
        """Replace the page's fetch: `js` is the body of (url, body, real) returning a replacement Response or null."""
        self.b.eval("(()=>{ const real = window.fetch; window.fetch = async (u, o) => { const body = o && o.body ? String(o.body) : ''; "
                    + js + " return real(u, o); }; })()")

    def test_l4_a_fenced_and_a_quoted_line_are_left_alone_and_the_real_line_is_added(self):
        text = self.original.replace("- **Client report rhythm:**", "```\n- **Client report:** on\n```\n> - **Client report:** on\n- **Client report rhythm:**", 1)
        self.memory.write_text(text)
        self.b.reload("typeof go==='function' && LIVE")
        self.toggle()
        end = time.time() + 8
        while time.time() < end and self.memory.read_text() == text:
            time.sleep(0.1)
        now = self.memory.read_text()
        self.assertIn("```\n- **Client report:** on\n```\n> - **Client report:** on\n", now)
        self.assertEqual(len(re.findall(r"^- \*\*Client report:\*\* off", now, re.M)), 1, now)

    def test_l5_a_file_changed_since_it_was_read_is_not_written_over(self):
        before = self.memory.read_text()
        # the page's second read of the memory file (the check just before the write) finds another tab's edit
        self.fetch_hook("if (/api\\/fs/.test(u) && /\"op\":\"read\"/.test(body) && /CLAUDE\\.md/.test(body) && !/backups/.test(body)) { "
                        "window.__n = (window.__n || 0) + 1; if (window.__n === 2) { const r = await real(u, o); const j = await r.json(); "
                        "j.text += '\\nanother tab\\n'; return new Response(JSON.stringify(j), {status: 200}); } }")
        self.toggle()
        msg = self.wait_snack()
        self.assertIn("changed in another window", msg)
        self.assertEqual(self.memory.read_text(), before)                        # nothing written

    def test_l6_a_failed_save_names_no_absolute_path(self):
        self.fetch_hook("if (/api\\/fs/.test(u) && /\"op\":\"write\"/.test(body) && /\"path\":\"projects\\/[^\"]*CLAUDE\\.md\"/.test(body)) "
                        "return new Response(JSON.stringify({ok: false, message: \"Permission denied: '/Users/someone/dev.env/creaite/projects/Example/CLAUDE.md'\"}), {status: 200});")
        self.toggle()
        msg = self.wait_snack()
        self.assertNotIn("/Users/", msg)
        self.assertIn("projects/Example/CLAUDE.md", msg)


if __name__ == "__main__":
    unittest.main()
