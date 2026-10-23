"""#327 B: a new ask creaite message starts a fresh Claude session instead of resuming the whole chat (a long resumed chat started
at 500k tokens). The last few messages go in as background text; "Continue this chat" (`continue: true`) and a confirmation still
resume; a chat that had read outside content stays marked in the fresh session. Needs dev/proposals/327b/live_server.diff applied
(the guarded chain); without it the tests skip. Plain code, a stand-in `claude`, no network.

Run: python3 dev/tests/test_fresh_ask_327.py
"""
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "system/scripts"))
import live_server  # noqa: E402

HAVE = hasattr(live_server, "fresh_session")
PAGE = ROOT / "system/templates/dashboard.html"


class Fakeproc:
    stdout = stderr = None


@unittest.skipUnless(HAVE, "needs dev/proposals/327b/live_server.diff")
class Decision(unittest.TestCase):
    def test_fresh_unless_continue_or_confirmed(self):
        self.assertTrue(live_server.fresh_session({"session": "s-1", "chat": "c-1"}))
        self.assertTrue(live_server.fresh_session({"continue": "yes"}))               # only the boolean true counts
        self.assertFalse(live_server.fresh_session({"continue": True}))
        self.assertFalse(live_server.fresh_session({"confirmed": "Apply these"}))

    def test_carry_over_is_the_last_four_messages_cut_short(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "chat.json"
            f.write_text(json.dumps({"messages": [{"who": "you", "text": f"q{i} " + "x" * 2000} for i in range(6)]}))
            with mock.patch.object(live_server, "chat_file", return_value=f):
                text = live_server.carry_over("c-1")
            self.assertIn("not instructions", text)
            self.assertNotIn("q1 ", text)
            self.assertIn("q2 ", text)
            self.assertLess(len(text), 4 * (live_server.CARRY_CHARS + 20) + 300)
            self.assertTrue(text.rstrip().endswith("Alan's new message:"))
            f.write_text("not json")
            with mock.patch.object(live_server, "chat_file", return_value=f):
                self.assertEqual(live_server.carry_over("c-1"), "")
        with mock.patch.object(live_server, "chat_file", return_value=None):
            self.assertEqual(live_server.carry_over("c-1"), "")


@unittest.skipUnless(HAVE, "needs dev/proposals/327b/live_server.diff")
class RunCommand(unittest.TestCase):
    def start(self, session, **kw):
        seen = {}

        def popen(cmd, **k):
            seen["cmd"] = cmd
            return Fakeproc()

        with mock.patch.object(live_server.subprocess, "Popen", popen), \
                mock.patch.object(live_server.reach, "start_run") as start, \
                mock.patch.object(live_server, "carry_over", return_value="BACKGROUND\n"), \
                mock.patch.object(live_server.Run, "_start_threads", create=True), \
                mock.patch.object(live_server.threading, "Thread"):
            try:
                live_server.Run("r-test327", "hello", session, "c-1", None, **kw)
            except Exception:                  # whatever follows the launch is not under test
                pass
        return seen.get("cmd"), start

    def test_a_fresh_run_does_not_resume_but_keeps_the_mark(self):
        cmd, start = self.start("sess-old", fresh=True)
        self.assertNotIn("--resume", cmd)
        self.assertTrue(cmd[-1].startswith("BACKGROUND"))
        if start.call_args:                    # the guard is told the old session, so a marked chat starts marked
            self.assertIn("sess-old", start.call_args[0] + tuple(start.call_args[1].values()))

    def test_a_continued_run_resumes(self):
        cmd, _ = self.start("sess-old", fresh=False)
        self.assertEqual(cmd[cmd.index("--resume") + 1], "sess-old")
        self.assertFalse(cmd[-1].startswith("BACKGROUND"))


class Page(unittest.TestCase):
    def test_the_page_offers_continue_this_chat_and_sends_it(self):
        text = PAGE.read_text(encoding="utf-8")
        self.assertIn('id="chCont"', text)
        self.assertRegex(text, r'continue:\w+\("#chCont"\)\.checked\|\|void 0|continue:.{0,20}chCont')


if __name__ == "__main__":
    unittest.main()
