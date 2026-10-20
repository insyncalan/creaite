"""Tests for log hygiene (board #253): the sweep's done line is counts only, no `sweep` debug-log call is handed a
free-text summary, and an unhandled route error is logged by route, class and frame, never its words, once a minute
(the result routes /api/apply, /api/undo and /api/review too: "not ok", and a fault's class, never its message).

Run: python3 dev/tests/test_log_hygiene.py
Fictional names only. The live-server test (c) needs the guarded change in dev/proposals/log-hygiene/; until that diff is
applied to system/scripts/live_server.py it is an expected failure (see LIVE_FAULT_APPLIED below).
"""
import ast
import json
import os
import re
import subprocess
import sys
import time
import unittest
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import REPO, Vault  # noqa: E402

SCRIPTS = REPO / "system" / "scripts"
NOW = "2026-10-08 09:30"
FREE_TEXT_NAMES = {"summary", "text", "subject", "title"}

# The guarded half (#253 item 2) is a proposal until Jarvis applies it; the helper's name is how the test knows.
LIVE_FAULT_APPLIED = "def log_fault(" in (SCRIPTS / "live_server.py").read_text(encoding="utf-8")
NOT_APPLIED = ("#253 item 2 is guarded (live_server.py): expected to fail until dev/proposals/log-hygiene/"
               "live_server.diff is applied")


def run(v, *args, check=True):
    r = subprocess.run([sys.executable, str(v.root / "system/scripts/sweep.py"), *args], cwd=v.root,
                       capture_output=True, text=True, env={**os.environ, "CREAITE_NOW": NOW})
    if check and r.returncode:
        raise AssertionError(f"sweep.py {args}: {r.stdout}{r.stderr}")
    return r


def log_text(root):
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted((root / "system/logs").glob("debug-*.log")))


def email(subject, sender, link):
    return (f"Email · From: {sender} · Subject: {subject} · Sent: 2026-10-07 09:12 · "
            f"Link: https://outlook.office365.com/owa/?ItemID={link}")


class SweepDoneCountsOnly(unittest.TestCase):
    """(a) sweep.py done: the debug-log line carries counts and the duration, never a word of the summary."""

    SUMMARY = ('Sweep: 2 items (1 possible) - 1 Example Programme, 1 Sample Project; Jane Doe chat on Today; '
               'UAT schedule thread, marked confidential; "Quarterly Budget Sign-off" from pat.lee@client.example; '
               '1 restricted message left out')
    CANARIES = ("Example Programme", "Sample Project", "Jane Doe", "UAT schedule", "confidential", "Quarterly Budget",
                "pat.lee", "client.example", "restricted", "Today")

    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.drafts = self.v.root / "system/staging/drafts"
        self.drafts.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.v.cleanup()

    def item(self, text, link, match="strong"):
        return {"table": "actions", "match": match, "values": {
            "project": "ABC", "description": text, "owner": "Alan Carter",
            "source": email("[ABC] Quarterly Budget Sign-off", "Jane Doe <jane@client.example>", link)}}

    def done_line(self):
        lines = [ln for ln in log_text(self.v.root).splitlines() if re.search(r"INFO  sweep\s+done", ln)]
        self.assertEqual(len(lines), 1, lines)
        return lines[0]

    def test_the_done_line_has_counts_and_no_names(self):
        ignored = self.item("Book the offsite", "a3")                     # the shipped ToDo rule drops it
        ignored["values"]["source"] = email("[ABC] ToDo offsite", "Jane Doe <jane@client.example>", "a3")
        f = self.drafts / "sweep.json"
        f.write_text(json.dumps({"window": {"start": "2026-10-07 08:00", "end": NOW}, "items": [
            self.item("Send the SOW", "a1"), self.item("Book the room", "a2", "possible"), ignored]}))
        run(self.v, "stage", str(f))
        out = run(self.v, "done", "--started", "2026-10-08 09:18", "--normal", "--summary", self.SUMMARY).stdout
        line = self.done_line()
        for canary in self.CANARIES:
            self.assertNotIn(canary, line)
        self.assertIn("done (normal): 2 items (1 possible)", line)
        self.assertIn("1 ignored", line)                                  # the ToDo rule's drop, a count only
        self.assertIn("12 min", line)                                     # 09:18 to 09:30
        self.assertNotIn("ToDo invites", line)                            # not even the rule's name
        self.assertIn("Recorded.", out)
        runlog = (self.v.root / "system/staging/run-log.txt").read_text()
        self.assertIn("Jane Doe chat on Today", runlog)                   # the run log is the intended record: unchanged

    def test_a_done_with_no_stage_logs_zero_counts(self):
        run(self.v, "done", "--started", "garbled", "--summary", self.SUMMARY)
        line = self.done_line()
        self.assertRegex(line, r"done: 0 items \(0 possible\), 0 alerts, 0 skipped, 0 ignored")
        self.assertNotIn("min", line)                                     # no duration from a start it can't read
        for canary in self.CANARIES:
            self.assertNotIn(canary, line)

    def test_the_counts_are_cleared_for_the_next_run(self):
        f = self.drafts / "sweep.json"
        f.write_text(json.dumps({"window": {"start": "2026-10-07 08:00", "end": NOW}, "items": [self.item("Send it", "b1")]}))
        run(self.v, "stage", str(f))
        run(self.v, "done", "--started", NOW)
        self.assertFalse((self.v.root / "system/staging/sweep-ignored.json").exists())
        run(self.v, "done", "--started", NOW)
        lines = [ln for ln in log_text(self.v.root).splitlines() if re.search(r"INFO  sweep\s+done", ln)]
        self.assertIn("1 item ", lines[0] + " ")
        self.assertIn("0 items", lines[1])


def sweep_log_calls():
    """Every debuglog.<level>("sweep", …) call in system/scripts, as (file, line, call)."""
    out = []
    for path in sorted(SCRIPTS.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr in ("info", "warn", "error", "debug", "exception")
                    and isinstance(node.func.value, ast.Name) and node.func.value.id in ("debuglog", "log")
                    and node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == "sweep"):
                out.append((path.name, node.lineno, node))
    return out


def free_text_names(call):
    """The names in the call's message that are free text: a variable or an attribute named summary, text, subject, title."""
    found = set()
    for arg in [*call.args[1:], *(k.value for k in call.keywords)]:
        for n in ast.walk(arg):
            if isinstance(n, ast.Name) and n.id in FREE_TEXT_NAMES:
                found.add(n.id)
            elif isinstance(n, ast.Attribute) and n.attr in FREE_TEXT_NAMES:
                found.add(n.attr)
    return found


class NoFreeTextInSweepLog(unittest.TestCase):
    """(b) No `sweep` debug-log call is handed a variable named summary, text, subject or title."""

    def test_the_call_sites_are_found(self):
        self.assertGreaterEqual(len(sweep_log_calls()), 8)                # the walker sees sweep.py's calls

    def test_no_call_passes_free_text(self):
        bad = [(f, ln, sorted(free_text_names(c))) for f, ln, c in sweep_log_calls() if free_text_names(c)]
        self.assertEqual(bad, [])

    def test_the_guard_catches_a_summary(self):
        call = ast.parse('debuglog.info("sweep", f"done: {debuglog.rule(summary, 200)}")').body[0].value
        self.assertEqual(free_text_names(call), {"summary"})
        call = ast.parse('debuglog.info("sweep", a.title)').body[0].value
        self.assertEqual(free_text_names(call), {"title"})


def _maybe_expected(fn):
    return fn if LIVE_FAULT_APPLIED else unittest.expectedFailure(fn)


FAKE_CATALOGUE = '''"""A stand-in settings_catalogue for #253: its routes raise."""


class ResetRefused(Exception):
    pass


def catalogue():
    raise RuntimeError("secret words CANARY-FAULT")


def reset(keys):
    raise BrokenPipeError("CANARY-PIPE")
'''


# A stand-in tracker.py for the result routes (#253): `apply` fails with item-like words; `read applies` answers [] (mode
# "notok") or something that isn't JSON (mode "fault"), so the apply route raises and is answered as a 500.
FAKE_TRACKER = """import pathlib, sys
mode = (pathlib.Path(__file__).with_name("fake-mode")).read_text().strip()
if sys.argv[1:3] == ["read", "applies"]:
    print("[]" if mode == "notok" else "CANARY-NOT-JSON")
    sys.exit(0)
print("Validation failed: ABC-A-999 description 'CANARY-APPLY-WORDS' is too long")
sys.exit(1)
"""


class LiveServerFault(unittest.TestCase):
    """(c) A route that raises: the class and the route are logged, never the words; once a minute; a page that left is info."""

    @classmethod
    def setUpClass(cls):
        from test_debug_log_wiring import Server
        cls.s = Server()
        (cls.s.v.root / "system/scripts/settings_catalogue.py").write_text(FAKE_CATALOGUE)   # imported on the first call

    @classmethod
    def tearDownClass(cls):
        cls.s.stop()

    @_maybe_expected
    def test_a_route_error_logs_its_class_and_route_once_a_minute(self):
        for _ in range(2):
            code, _body = self.s.post("/api/settings/catalogue", {})
            self.assertEqual(code, 500)
        text = self.s.wait_for(r"POST /api/settings/catalogue 500 \d+ms", 2)
        causes = re.findall(r"ERROR server\s+POST /api/settings/catalogue raised RuntimeError at settings_catalogue\.py:\d+"
                            r" in catalogue.*", text)
        self.assertEqual(len(causes), 1, text)                            # the second, within a minute, adds no line
        self.assertNotIn("secret words", text)
        self.assertNotIn("CANARY-FAULT", text)

    def fake_tracker(self, mode):
        scripts = self.s.v.root / "system/scripts"
        real = (scripts / "tracker.py").read_bytes()
        (scripts / "fake-mode").write_text(mode)
        (scripts / "tracker.py").write_text(FAKE_TRACKER)               # run as a script by the route; the server's import is done
        self.addCleanup((scripts / "tracker.py").write_bytes, real)

    @_maybe_expected
    def test_a_failed_apply_logs_not_ok_and_never_its_message(self):
        """RESULT_ROUTES: a refused apply (200, ok false) is logged as "not ok", without tracker.py's words."""
        self.fake_tracker("notok")
        code, body = self.s.post("/api/apply", {})
        self.assertEqual((code, body.get("ok")), (200, False))
        self.assertIn("CANARY-APPLY-WORDS", body.get("message", ""))       # the page still gets the reason
        text = self.s.wait_for(r"POST /api/apply 200 \d+ms not ok")
        self.assertRegex(text, r"WARN  server\s+POST /api/apply 200 \d+ms not ok\n")
        self.assertNotIn("CANARY-APPLY-WORDS", text)
        self.assertNotIn("Validation failed", text)

    @_maybe_expected
    def test_an_apply_that_raises_logs_its_class_and_route_only(self):
        """RESULT_ROUTES: a fault on /api/apply (a 500 from fault()) names the class twice (the cause line at ERROR, the result
        line at WARN) and never str(e)."""
        self.fake_tracker("fault")
        code, body = self.s.post("/api/apply", {})
        self.assertEqual(code, 500)
        self.assertIn("Expecting value", body.get("message", ""))          # str(e) reaches the page, as before
        text = self.s.wait_for(r"POST /api/apply 500 \d+ms not ok")
        self.assertRegex(text, r"WARN  server\s+POST /api/apply 500 \d+ms not ok: JSONDecodeError\n")
        self.assertRegex(text, r"ERROR server\s+POST /api/apply raised JSONDecodeError at \S+\.py:\d+ in ")
        self.assertNotIn("Expecting value", text)
        self.assertNotIn("CANARY", text)

    @_maybe_expected
    def test_a_background_thread_error_logs_its_class_and_thread_once(self):
        """A thread's uncaught error (the VIP timer, the apply worker...) is logged by thread, class and frame, never str(e)."""
        code = ("import sys, threading; sys.path.insert(0, 'system/scripts'); import live_server\n"
                "def boom():\n    raise RuntimeError('CANARY-THREAD-WORDS')\n"
                "for _ in range(2):\n    t = threading.Thread(target=boom, name='canary-worker'); t.start(); t.join()\n")
        r = subprocess.run([sys.executable, "-c", code], cwd=self.s.v.root, capture_output=True, text=True, timeout=120,
                           env={**os.environ, "CREAITE_PORT": "1"})
        self.assertIn("CANARY-THREAD-WORDS", r.stderr)                     # Python's own hook still prints it to the console
        text = self.s.wait_for(r"thread canary-worker raised")
        lines = re.findall(r"ERROR server\s+thread canary-worker raised RuntimeError at <string>:\d+ in boom.*", text)
        self.assertEqual(len(lines), 1, text)                               # the second, within a minute, adds no line
        self.assertNotIn("CANARY-THREAD-WORDS", text)

    def test_a_page_that_left_stays_at_info(self):
        try:
            self.s.post("/api/settings/reset", {"key": "sweep.due_from"})
        except (urllib.error.URLError, ConnectionError, OSError):
            pass                                                          # nothing was sent back: the page "left"
        deadline = time.time() + 15
        while "client left" not in self.s.text() and time.time() < deadline:
            time.sleep(0.05)
        text = self.s.text()
        self.assertRegex(text, r"INFO  server\s+POST /api/settings/reset client left: BrokenPipeError")
        self.assertNotRegex(text, r"ERROR server\s+POST /api/settings/reset")
        self.assertNotIn("CANARY-PIPE", text)


if __name__ == "__main__":
    unittest.main()
