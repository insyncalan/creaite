"""#334: the live server asks the weekly AI budget before a typed ask creaite request (and a queued message) starts a run. Needs
dev/proposals/334/live_server.diff applied (the guarded chain, third in 2.6.4) and system/scripts/ai_budget.py; without them the tests skip. A stand-in for Run and
the usage status; no Claude, no network.

Run: python3 dev/tests/test_ai_budget_gate_334.py
"""
import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "system/scripts"))
import live_server  # noqa: E402

try:
    import ai_budget  # noqa: E402  (unguarded; merged separately from this diff)
except ImportError:
    ai_budget = None
HAVE = ai_budget is not None and hasattr(live_server, "budget_gate")
WED = datetime(2026, 10, 21, 12, 0)


def status(spent, **cfg):
    rows = [{"at": "2026-10-20T09:00:00", "cost_usd": spent}]
    return ai_budget.status(rows, ai_budget.settings(dict({"weekly_dollars": 50}, **cfg)), WED)


class Reached(Exception):
    """Raised by the stand-in Run: the request got past the budget."""


class FakeHandler:
    def __init__(self):
        self.sent = None

    def send(self, code, body):
        self.sent = (code, body)

    numbered = staticmethod(lambda: False)

    def follow(self, run, **kw):
        raise Reached()


def ask(req, st):
    h = FakeHandler()
    with mock.patch.object(ai_budget, "status", return_value=st), \
            mock.patch.object(live_server, "Run", side_effect=Reached), \
            mock.patch.object(live_server, "current_run", return_value=None):
        try:
            live_server.Handler.ask(h, dict({"message": "hello"}, **req))
            reached = False
        except Reached:
            reached = True
    return h.sent, reached


@unittest.skipUnless(HAVE, "needs dev/proposals/334/live_server.diff")
class AskPath(unittest.TestCase):
    def test_under_budget_runs(self):
        self.assertTrue(ask({}, status(10))[1])

    def test_over_budget_in_confirm_mode_answers_429_and_starts_nothing(self):
        sent, reached = ask({}, status(60))
        self.assertFalse(reached)
        self.assertEqual(sent[0], 429)
        self.assertIs(sent[1]["ok"], False)
        self.assertTrue(sent[1]["budget"]["can_continue"])
        self.assertNotIn("hello", str(sent))                        # the message is not echoed or kept

    def test_run_anyway_goes_through(self):
        self.assertTrue(ask({"over_budget": True}, status(60))[1])

    def test_stop_mode_refuses_even_with_run_anyway(self):
        sent, reached = ask({"over_budget": True}, status(60, at_limit="stop"))
        self.assertFalse(reached)
        self.assertEqual(sent[0], 429)
        self.assertFalse(sent[1]["budget"]["can_continue"])

    def test_a_confirmed_request_is_never_held(self):
        self.assertTrue(ask({"confirmed": "Apply these changes"}, status(500, at_limit="stop"))[1])

    def test_off_and_faults_hold_nothing(self):
        self.assertTrue(ask({}, status(500, enabled=False))[1])
        h = FakeHandler()
        with mock.patch.object(ai_budget, "status", side_effect=RuntimeError("boom")), \
                mock.patch.object(live_server, "Run", side_effect=Reached), mock.patch.object(live_server, "current_run", return_value=None):
            with self.assertRaises(Reached):
                live_server.Handler.ask(h, {"message": "hello"})


@unittest.skipUnless(HAVE, "needs dev/proposals/334/live_server.diff")
class Queue(unittest.TestCase):
    def start(self, st, prev):
        q = {"chat": "c-1", "items": [{"id": "1", "text": "next", "images": []}], "held": False}
        with mock.patch.object(ai_budget, "status", return_value=st), mock.patch.object(live_server, "queue_save"), \
                mock.patch.object(live_server, "Run", side_effect=Reached), mock.patch.object(live_server, "ask_image_files", return_value=None):
            try:
                live_server.queue_start(q, prev)
                return q, False
            except Reached:
                return q, True

    def test_a_run_ending_over_budget_holds_the_queue(self):
        prev = mock.Mock(done=True, kind="ask", chat="c-1", session="s")
        q, reached = self.start(status(60), prev)
        self.assertFalse(reached)
        self.assertTrue(q["held"])
        self.assertEqual(len(q["items"]), 1)                        # nothing lost

    def test_run_now_overrides_in_confirm_mode_but_not_in_stop_mode(self):
        self.assertTrue(self.start(status(60), None)[1])
        self.assertFalse(self.start(status(60, at_limit="stop"), None)[1])

    def test_under_budget_starts_the_next(self):
        self.assertTrue(self.start(status(5), mock.Mock(done=True, kind="ask", chat="c-1", session="s"))[1])


@unittest.skipUnless(HAVE, "needs dev/proposals/334/live_server.diff")
class NotRuns(unittest.TestCase):
    def test_only_the_ask_path_calls_the_gate(self):
        src = (ROOT / "system/scripts/live_server.py").read_text(encoding="utf-8")
        self.assertEqual(src.count("budget_gate("), 3)               # its definition, ask() and queue_start(); nothing else


if __name__ == "__main__":
    unittest.main()
