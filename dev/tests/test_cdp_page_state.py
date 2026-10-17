"""A failing wait, and a failing test in a LiveBrowserCase, say where the page was (no Chrome: the page is a fake)."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from cdp import Browser  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402

STATE = {"url": "http://127.0.0.1:1/#notes=ABC", "active": "DIV#x", "dialogs": ["noteLeaveDlg"], "saveLine": "Changed outside creaite",
         "snack": "Not saved", "scroll": [0, 40]}


def fake():
    b = Browser.__new__(Browser)
    b.errors = [f"e{i}" for i in range(8)]
    b.pump = lambda seconds=0.05: None
    b.eval = lambda js, wait=True: STATE if "dialogs" in js else False
    return b


class PageState(unittest.TestCase):
    def test_a_failing_wait_carries_the_page_state(self):
        with self.assertRaises(TimeoutError) as cm:
            fake().wait("false", timeout=0.1)
        m = str(cm.exception)
        self.assertIn("page errors: ['e5', 'e6', 'e7']", m)
        self.assertIn("last page errors: ['e3', 'e4', 'e5', 'e6', 'e7']", m)
        self.assertIn("page state: ", m)
        for k in ("noteLeaveDlg", "Changed outside creaite", "Not saved", "#notes=ABC", "DIV#x", "[0, 40]"):
            self.assertIn(k, m)

    def test_a_slow_answer_does_not_use_up_the_wait(self):
        """The one evaluation made before the deadline came back after it (a starved page): the condition holds by now, so it passes."""
        import time
        b = fake()
        answers = iter([False, True])

        def slow(js, wait=True):
            time.sleep(0.25)
            return next(answers)
        b.eval = slow
        self.assertTrue(b.wait("x", timeout=0.1))
        b.eval = lambda js, wait=True: False
        with self.assertRaises(TimeoutError) as cm:
            b.wait("x", timeout=0.1)
        self.assertIn("polls: ", str(cm.exception))

    def test_a_failing_test_carries_it_too_and_a_passing_one_is_untouched(self):
        class T(LiveBrowserCase):
            def setUp(self):
                self.b = fake()
            tearDown = setUp
            def test_bad(self):
                self.fail("boom")
            def test_good(self):
                pass
        r = unittest.TestResult()
        unittest.TestSuite([T("test_bad"), T("test_good")]).run(r)
        self.assertEqual(r.testsRun, 2)
        self.assertEqual(len(r.failures), 1)
        text = r.failures[0][1]
        self.assertIn("boom", text)
        self.assertIn("page state: ", text)
        self.assertIn("Changed outside creaite", text)


if __name__ == "__main__":
    unittest.main()
