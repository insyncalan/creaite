"""#250 (2.6.10), G3: the live server's side of the sweep's transcript fetch. Skipped until dev/proposals/250/live_server-250.diff has
landed (marker: Run._fetch_finish). The fetch itself (SweepFetch) is tested in test_fetch_transcripts / test_fetch_settle; here the
Run engine is checked: when a run gets a fetch, what it is shown, when finish(answered) is called and with what, that a fault never
stops _done(), and what the closure line says. Fictional data only; nothing is written (the fetch is a spy).
Run: python3 dev/tests/test_live_fetch_250.py"""
import io
import json
import re
import sys
import threading
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system" / "scripts"))
import live_server as L  # noqa: E402
import transcripts as T  # noqa: E402

LANDED = hasattr(getattr(L, "Run", None), "_fetch_finish")
READ = "mcp__claude_ai_Microsoft_365__read_resource"
SEARCH = "mcp__claude_ai_Microsoft_365__outlook_calendar_search"
COUNTS = {"fetched": 2, "held": 1, "failed": 0, "left": 1, "error": 0}
LINE = "2 transcripts fetched, 1 held back: a confidential meeting at that time, 1 left: Process to load it"


class Spy:
    """Stands in for SweepFetch: records what the Run hands it and in what order relative to _done()."""

    def __init__(self, log, boom=False):
        self.log, self.boom, self.observed, self.finished = log, boom, [], []

    def observe(self, name, tool_input, text, is_error=False):
        self.observed.append((name, tool_input, text, is_error))

    def finish(self, answered):
        self.log.append("finish")
        self.finished.append(answered)
        if self.boom:
            raise RuntimeError("settle failed")
        return dict(COUNTS)


class Proc:
    def __init__(self, lines, code, stderr=""):
        self.stdout, self.stderr, self.returncode, self._code, self.pid = io.StringIO(lines), io.StringIO(stderr), None, code, 0

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        self.returncode = self._code
        return self.returncode

    def terminate(self):
        self.returncode = self._code
    kill = terminate


def use(i, name, inp):
    return {"type": "assistant", "session_id": "s-1", "message": {"content": [{"type": "tool_use", "id": i, "name": name, "input": inp}]}}


def got(i, text, error=False):
    return {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": i, "is_error": error, "content": text}]}}


EVENTS = [use("a", SEARCH, {"query": "today"}), got("a", "calendar rows"),
          use("b", READ, {"uri": "calendar:///events/ev-1"}), got("b", "event text"),
          use("c", "Bash", {"command": "system/scripts/run sweep.py status"}), got("c", "fine"),
          use("d", READ, {"uri": "meeting-transcript:///events/ev-1"}), got("d", "WEBVTT body", error=True),
          {"type": "result", "session_id": "s-1", "result": "Swept."}]


def build(fetch, events=EVENTS, code=0, plain=False, attrs=None, log=None):
    log = log if log is not None else []
    run = L.Run.__new__(L.Run)
    base = {"id": "r-1", "message": "sweep", "session": None, "chat": None, "confirmed": False, "kind": "sweep" if plain else "ask",
            "images": [], "job": None, "label": "sweep", "tooluse": {}, "events": [], "cond": threading.Condition(), "watchers": 0,
            "pending": {}, "said": [], "steps": [], "stop": False, "deferred": False, "done": False, "seen": False,
            "started": time.time(), "guarded": False, "fetch": fetch}
    base.update(attrs or {})
    for k, v in base.items():
        setattr(run, k, v)
    run.record = lambda *a, **k: None                      # nothing is written to the vault
    run._done = lambda: log.append("done")
    run.proc = Proc("".join(json.dumps(e) + "\n" for e in events), code)
    return run, log


@unittest.skipUnless(LANDED, "live_server-250.diff has not landed")
class Gets(unittest.TestCase):
    def setUp(self):
        self.old = T.fetch_on
        self.made = []
        self.old_cls = T.SweepFetch
        T.SweepFetch = lambda *a, **k: self.made.append(1) or Spy([])

    def tearDown(self):
        T.fetch_on, T.SweepFetch = self.old, self.old_cls

    def make(self, kind, sweep, on):
        T.fetch_on = lambda settings=None: on
        return L.Run.__new__(L.Run)._fetch_for(kind, sweep)

    def test_off_there_is_no_fetch_and_none_is_built(self):
        for kind, sweep in (("sweep", False), ("ask", True)):
            self.assertIsNone(self.make(kind, sweep, False))
        self.assertEqual(self.made, [])

    def test_on_a_sweep_run_gets_one(self):
        self.assertIsInstance(self.make("sweep", False, True), Spy)        # the catch-up and Close the day
        self.assertIsInstance(self.make("ask", True, True), Spy)           # a typed sweep
        self.assertEqual(len(self.made), 2)

    def test_a_run_that_is_not_a_sweep_never_gets_one(self):
        for kind in ("ask", "search", "generate", "prep", "check", "load", "process", "reextract", "edit-ai"):
            self.assertIsNone(self.make(kind, False, True), kind)
        self.assertEqual(self.made, [])

    def test_start_assigns_it_from_the_kind_and_the_sweep_flag(self):
        src = Path(L.__file__).read_text(encoding="utf-8")
        self.assertRegex(src, r"self\.fetch = self\._fetch_for\(kind, sweep\)")

    def test_a_fetch_that_cannot_be_built_leaves_the_sweep_running_without_it(self):
        T.fetch_on = lambda settings=None: True
        T.SweepFetch = lambda *a, **k: 1 / 0
        self.assertIsNone(L.Run.__new__(L.Run)._fetch_for("sweep", False))

    def test_no_new_tool_folder_or_old_path(self):
        src = Path(L.__file__).read_text(encoding="utf-8")
        block = src[src.index("# ===== #250 (v2.6.10)"):src.index("# ===== end #250 =====")]
        for word in ("--add-dir", "allowedTools", "sweep-fetched", "sweep.py done", "KIND_TOOLS", "subprocess"):
            self.assertNotIn(word, block)


@unittest.skipUnless(LANDED, "live_server-250.diff has not landed")
class Reads(unittest.TestCase):
    def test_only_read_resource_results_reach_observe(self):
        spy = Spy([])
        run, _ = build(spy)
        L.Run.read(run)
        self.assertEqual([o[0] for o in spy.observed], [READ, READ])
        self.assertEqual(spy.observed[0][1:], ({"uri": "calendar:///events/ev-1"}, "event text", False))
        self.assertEqual(spy.observed[1][3], True)                           # the error flag travels

    def test_no_fetch_no_observer_calls_and_nothing_added(self):
        run, log = build(None)
        L.Run.read(run)
        self.assertEqual(log, ["done"])
        self.assertEqual(run.said, [])
        self.assertFalse(any(e["type"] == "text" for e in run.events))

    def test_a_result_the_observer_chokes_on_is_swallowed_and_the_run_goes_on(self):
        class Bad(Spy):
            def observe(self, *a, **k):
                raise ValueError("odd")
        spy = Bad([])
        run, log = build(spy)
        spy.log = log
        L.Run.read(run)
        self.assertEqual(log, ["finish", "done"])
        self.assertEqual(len(spy.finished), 1)


@unittest.skipUnless(LANDED, "live_server-250.diff has not landed")
class Ends(unittest.TestCase):
    def ended(self, code=0, attrs=None, events=EVENTS, plain=False):
        spy = Spy([])
        run, log = build(spy, events=events, code=code, attrs=attrs, plain=plain)
        spy.log = log
        L.Run.read(run)
        return spy, run, log

    def test_an_answered_run_settles_with_true_and_finish_comes_before_done(self):
        spy, _, log = self.ended()
        self.assertEqual(spy.finished, [True])
        self.assertEqual(log, ["finish", "done"])

    def test_a_stopped_run_settles_with_false(self):
        self.assertEqual(self.ended(attrs={"stop": True})[0].finished, [False])

    def test_a_timed_out_run_settles_with_false(self):
        self.assertEqual(self.ended(attrs={"stop": True, "timed_out": True})[0].finished, [False])
        self.assertEqual(self.ended(attrs={"timed_out": True})[0].finished, [False])      # the flag alone is enough

    def test_a_failed_run_settles_with_false(self):
        no_answer = [e for e in EVENTS if e["type"] != "result"]
        self.assertEqual(self.ended(code=1, events=no_answer)[0].finished, [False])
        self.assertEqual(self.ended(code=1)[0].finished, [False])                          # an answer but a non-zero exit is not answered
        self.assertEqual(self.ended(attrs={"failed": True})[0].finished, [False])          # the run's own failed flag, even at exit 0

    def test_exit_0_with_an_error_result_settles_with_false(self):
        ev = [e for e in EVENTS if e["type"] != "result"] + [{"type": "result", "is_error": True, "result": "Swept."}]
        self.assertEqual(self.ended(events=ev)[0].finished, [False])

    def test_exit_0_with_no_result_event_settles_with_false(self):
        self.assertEqual(self.ended(events=[e for e in EVENTS if e["type"] != "result"])[0].finished, [False])

    def test_exit_0_with_a_result_but_an_empty_final_settles_with_false(self):
        for text in ("", None):
            ev = [e for e in EVENTS if e["type"] != "result"] + [{"type": "result", "result": text}]
            self.assertEqual(self.ended(events=ev)[0].finished, [False], text)

    def test_exit_0_with_a_good_result_and_a_final_settles_with_true(self):
        ev = [e for e in EVENTS if e["type"] != "result"] + [{"type": "result", "is_error": False, "result": "Swept."}]
        self.assertEqual(self.ended(events=ev)[0].finished, [True])

    def test_a_stop_after_a_good_result_settles_with_false(self):
        """The stop clause alone: a good result and exit 0, but Stop was pressed (a stop that comes after the answer)."""
        spy = Spy([])
        run, log = build(spy)
        spy.log = log
        orig = run._on_result

        def result_then_stop(ev):
            out = orig(ev)
            run.stop = True                                  # Stop arrives after the good result, before the process ends
            return out
        run._on_result = result_then_stop
        L.Run.read(run)
        self.assertEqual(spy.finished, [False])
        self.assertTrue(run.usage_result and not run.usage_result.get("is_error"))      # the result itself was good

    def test_answered_is_a_helper_that_reads_the_stream_result_not_the_exit_code_alone(self):
        run = L.Run.__new__(L.Run)
        run.stop = False
        proc = Proc("", 0)
        proc.returncode = 0
        self.assertFalse(run._answered(proc, "Swept."))                     # no usage_result yet
        run.usage_result = {"result": "Swept."}
        self.assertTrue(run._answered(proc, "Swept."))
        run.usage_result = ["not", "a", "dict"]
        self.assertFalse(run._answered(proc, "Swept."))

    def test_finish_is_called_once_for_every_ending(self):
        for kw in ({}, {"attrs": {"stop": True}}, {"code": 2}):
            self.assertEqual(len(self.ended(**kw)[0].finished), 1)

    def test_a_finish_that_raises_does_not_stop_done(self):
        spy = Spy([], boom=True)
        run, log = build(spy)
        spy.log = log
        L.Run.read(run)
        self.assertEqual(log, ["finish", "done"])
        self.assertEqual(run.said, [])                                  # nothing is shown for a settle that failed

    def test_a_typed_sweep_shows_the_counts_as_a_line_of_the_chat(self):
        _, run, _ = self.ended()
        self.assertEqual(run.said, [LINE])
        self.assertIn({"type": "text", "text": LINE}, run.events)

    def test_a_run_creaite_started_leaves_the_line_to_its_closure(self):
        _, run, _ = self.ended(plain=True)
        self.assertEqual(run.fetch_line, LINE)
        self.assertEqual(run.said, [])


@unittest.skipUnless(LANDED, "live_server-250.diff has not landed")
class Closure(unittest.TestCase):
    def test_the_line_follows_the_runs_own_words_and_adds_no_title(self):
        run = L.Run.__new__(L.Run)
        run.fetch_line = LINE
        out = run._with_fetch_line({"ok": True, "line": "The catch-up sweep has finished: anything it found is waiting in Review"})
        self.assertEqual(out["line"], f"The catch-up sweep has finished: anything it found is waiting in Review. {LINE}.")
        self.assertEqual(out["ok"], True)
        self.assertEqual(run._with_fetch_line({"ok": False, "stopped": True, "line": "Stopped."})["line"], f"Stopped. {LINE}.")
        for word in ("ABC", "Steering", "Board", "private"):
            self.assertNotIn(word, out["line"])

    def test_nothing_is_added_without_a_line(self):
        run = L.Run.__new__(L.Run)
        c = {"ok": True, "line": "Done"}
        self.assertIs(run._with_fetch_line(c), c)
        run.fetch_line = ""
        self.assertIs(run._with_fetch_line(c), c)

    def test_close_puts_the_line_in_the_closure_event(self):
        spy = Spy([])
        run, _ = build(spy, plain=True, attrs={"lines": {"done": "Swept"}, "closer": None, "outcome": None})
        old = (L.remember_chat, L.plain_chat_id)
        L.remember_chat, L.plain_chat_id = (lambda *a, **k: None), (lambda: "chat")
        try:
            run.fetch_line = LINE
            run._close(False)
        finally:
            L.remember_chat, L.plain_chat_id = old
        closure = [e for e in run.events if e["type"] == "closure"]
        self.assertEqual(len(closure), 1)
        self.assertEqual(closure[0]["line"], f"Swept. {LINE}.")

    def test_the_line_is_counts_only(self):
        line = T.fetch_text({"fetched": 1, "held": 2, "left": 0})
        self.assertFalse(re.search(r"\d{2}:\d{2}|@|\.vtt|uri", line))


if __name__ == "__main__":
    unittest.main()
