"""#334: the live server asks the weekly AI budget before a typed ask creaite request (and a queued message) starts a run. Needs
dev/proposals/334/live_server.diff applied (the guarded chain, third in 2.6.4) and system/scripts/ai_budget.py; without them the tests skip. A stand-in for Run and
the usage status; no Claude, no network.

Run: python3 dev/tests/test_ai_budget_gate_334.py
"""
import sys
import threading
import types
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


def mutated(old, new):
    """live_server.py with one change, run as a second module (the mutant)."""
    path = ROOT / "system/scripts/live_server.py"
    src = path.read_text(encoding="utf-8")
    assert src.count(old) == 1, old
    mod = types.ModuleType("live_server_mutant")
    mod.__file__ = str(path)
    exec(compile(src.replace(old, new), str(path), "exec"), mod.__dict__)
    return mod


def ask(req, st, ls=None):
    ls = ls or live_server
    h = FakeHandler()
    with mock.patch.object(ai_budget, "status", return_value=st), \
            mock.patch.object(ls, "Run", side_effect=Reached), \
            mock.patch.object(ls, "current_run", return_value=None):
        try:
            ls.Handler.ask(h, dict({"message": "hello"}, **req))
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


SWEEPS = ("sweep", "sweep mail for ABC", "refresh calendar", "sweep the last 7 days")
SKIP_ASK = '        if panel_sweep(req.get("message"), req.get("images") or (), req.get("confirmed")):\n            return None\n'


@unittest.skipUnless(HAVE, "needs dev/proposals/334/live_server.diff")
class SweepsAreNeverHeld(unittest.TestCase):
    """A typed sweep (the words panel_sweep recognises) is never held at 100%, in confirm or stop mode, typed or queued."""

    def test_the_ask_path(self):
        for at_limit in ("confirm", "stop"):
            for words in SWEEPS:
                self.assertTrue(ask({"message": words}, status(500, at_limit=at_limit))[1], (at_limit, words))
        sent, reached = ask({"message": "tell me about the pilot"}, status(500))
        self.assertFalse(reached)                                    # anything else is still held
        self.assertEqual(sent[0], 429)
        self.assertFalse(ask({"message": "sweep", "images": ["i-1"]}, status(500))[1])        # an image makes it a chat, not a sweep

    def test_mutant_without_the_sweep_check_the_ask_path_holds_a_sweep(self):
        ls = mutated(SKIP_ASK, "")
        sent, reached = ask({"message": "sweep"}, status(500, at_limit="stop"), ls)
        self.assertFalse(reached)
        self.assertEqual(sent[0], 429)

    def queued(self, text, st, ls=None):
        ls = ls or live_server
        q = {"chat": "c-1", "items": [{"id": "1", "text": text, "images": []}], "held": False}
        with mock.patch.object(ai_budget, "status", return_value=st), mock.patch.object(ls, "queue_save"), \
                mock.patch.object(ls, "Run", side_effect=Reached), mock.patch.object(ls, "ask_image_files", return_value=None):
            try:
                ls.queue_start(q, mock.Mock(done=True, kind="ask", chat="c-1", session="s"))
                return q, False
            except Reached:
                return q, True

    def test_the_queue_path(self):
        for at_limit in ("confirm", "stop"):
            for words in SWEEPS:
                self.assertTrue(self.queued(words, status(500, at_limit=at_limit))[1], (at_limit, words))
        q, reached = self.queued("tell me about the pilot", status(500))
        self.assertFalse(reached)
        self.assertTrue(q["held"])

    def queued_with_images(self, st, files, ls=None):
        ls = ls or live_server
        q = {"chat": "c-1", "items": [{"id": "1", "text": "sweep", "images": ["i-gone"]}], "held": False}
        with mock.patch.object(ai_budget, "status", return_value=st), mock.patch.object(ls, "queue_save"), \
                mock.patch.object(ls, "Run", side_effect=Reached), mock.patch.object(ls, "ask_image_files", return_value=files):
            try:
                ls.queue_start(q, mock.Mock(done=True, kind="ask", chat="c-1", session="s"))
                return False
            except Reached:
                return True

    def test_a_queued_sweep_whose_picture_is_gone_is_still_a_sweep(self):
        self.assertTrue(self.queued_with_images(status(500, at_limit="stop"), []))          # the file has gone: filtered out first
        self.assertFalse(self.queued_with_images(status(500, at_limit="stop"), ["x.png"]))  # a picture still there makes it a chat

    def test_mutant_unfiltered_pictures_hold_a_queued_sweep(self):
        ls = mutated('[i for i in first.get("images") or [] if ask_image_files(i)]', 'first.get("images")')
        self.assertFalse(self.queued_with_images(status(500, at_limit="stop"), [], ls))

    def test_mutant_without_the_message_the_queue_path_holds_a_sweep(self):
        ls = mutated('"message": first.get("text"), "images": first.get("images")}', "}")
        self.assertFalse(self.queued("sweep", status(500, at_limit="stop"), ls)[1])


@unittest.skipUnless(HAVE, "needs dev/proposals/334/live_server.diff")
class RunNowSaysWhy(unittest.TestCase):
    """A queue held by the budget is held with a reason: Run now in stop mode answers with it (why, and until when)."""

    def resume(self, st, ls=None):
        ls = ls or live_server
        q = {"chat": "c-1", "items": [{"id": "1", "text": "next", "images": []}], "held": True}

        class H:
            def send(self, code, body):
                self.got = (code, body)

        h = H()
        with mock.patch.object(ai_budget, "status", return_value=st), mock.patch.object(ls, "queue_save"), mock.patch.object(ls, "queue_load", return_value=q), \
                mock.patch.object(ls, "current_run", return_value=None), mock.patch.object(ls, "Run", side_effect=Reached), \
                mock.patch.object(ls, "ask_image_files", return_value=None):
            try:
                ls.queue_route(h, {"op": "resume"})
            except Reached:
                return None, q
        return h.got[1], q

    def test_stop_mode_says_why_and_until_when(self):
        body, q = self.resume(status(60, at_limit="stop"))
        self.assertIs(body["ok"], True)
        self.assertIsNone(body.get("run"))
        self.assertIn("AI budget is used up", body["message"])
        self.assertIn("starts again on Monday 26-10-2026", body["message"])
        self.assertTrue(body["held"])
        self.assertEqual(len(body["items"]), 1)

    def test_confirm_mode_run_now_starts_and_under_budget_has_no_reason(self):
        self.assertIsNone(self.resume(status(60))[0])               # Run now is the click: it starts
        body, _ = self.resume(status(5))
        self.assertIsNone(body)

    def test_a_reason_from_an_earlier_hold_does_not_stick(self):
        q = {"chat": "c-1", "items": [{"id": "1", "text": "next", "images": []}], "held": True, "why": "old reason"}
        with mock.patch.object(ai_budget, "status", return_value=status(5)), mock.patch.object(live_server, "queue_save"), \
                mock.patch.object(live_server, "Run", side_effect=Reached), mock.patch.object(live_server, "ask_image_files", return_value=None):
            with self.assertRaises(Reached):
                live_server.queue_start(q, None)
        self.assertNotIn("why", q)


@unittest.skipUnless(HAVE, "needs dev/proposals/334/live_server.diff")
class UsageIsReadOutsideTheLock(unittest.TestCase):
    """The usage file (up to 8 MB) is read before the start lock is taken, not while it is held."""
    GATE_INSIDE = 'if held:                                            # #334'

    def locked_during_read(self, ls):
        seen, me, st = [], threading.get_ident(), status(5)

        def status_(*a, **k):
            if threading.get_ident() == me:                          # not the page's own polling threads
                seen.append(ls.START_LOCK.locked())
            return st

        q = {"chat": "c-1", "items": [{"id": "1", "text": "next", "images": []}], "held": False}
        with mock.patch.object(ai_budget, "status", status_), mock.patch.object(ls, "queue_save"), \
                mock.patch.object(ls, "Run", side_effect=Reached), mock.patch.object(ls, "ask_image_files", return_value=None):
            with self.assertRaises(Reached):
                ls.queue_start(q, mock.Mock(done=True, kind="ask", chat="c-1", session="s"))
        return seen

    def test_the_read_happens_with_the_lock_free(self):
        self.assertEqual(self.locked_during_read(live_server), [False])

    def test_mutant_reading_inside_the_lock_is_seen(self):
        ls = mutated(self.GATE_INSIDE, 'if budget_gate({"over_budget": prev is None}) or held:                   # #334')
        self.assertIn(True, self.locked_during_read(ls))


@unittest.skipUnless(HAVE, "needs dev/proposals/334/live_server.diff")
class NotRuns(unittest.TestCase):
    def test_only_the_ask_path_calls_the_gate(self):
        src = (ROOT / "system/scripts/live_server.py").read_text(encoding="utf-8")
        self.assertEqual(src.count("budget_gate("), 3)               # its definition, ask() and queue_start(); nothing else (Run now reads the reason queue_start kept)


if __name__ == "__main__":
    unittest.main()
