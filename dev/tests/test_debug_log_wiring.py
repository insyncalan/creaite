"""Tests for wiring the debug log into creaite (BL-102 part 2, stage A): script runs, the live server, Diagnostics.

Run: python3 dev/tests/test_debug_log_wiring.py
Each test builds a throwaway vault (as test_tracker.py does) and runs the real scripts in it.
"""
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dashboard import populate  # noqa: E402
from test_tracker import REPO, Vault  # noqa: E402

SCRIPTS = REPO / "system" / "scripts"
ENTRY_POINTS = ("update.py", "prep_page.py", "filechange.py", "permissions.py", "launch.py", "locations.py", "search.py",
                "build_dashboard.py", "session.py", "doctor.py")


class Wired(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.root = self.v.root
        for f in ("launch.py", "filechange.py", "prep_page.py"):          # not in every test vault's script list
            if not (self.root / "system" / "scripts" / f).exists():
                shutil.copy2(SCRIPTS / f, self.root / "system" / "scripts" / f)
        self.logs = self.root / "system" / "logs"

    def tearDown(self):
        self.v.cleanup()

    def lines(self):
        out = []
        for p in sorted(self.logs.glob("debug-*.log")):
            out += p.read_text(encoding="utf-8").splitlines()
        return out

    def run_script(self, script, *args, env=None):
        return subprocess.run([sys.executable, str(self.root / "system" / "scripts" / script), *args],
                              capture_output=True, text=True, cwd="/tmp", env={**os.environ, **(env or {})})


class ScriptRuns(Wired):
    def test_every_entry_point_logs_a_start_and_an_exit(self):
        self.v.run("init")
        for script in ENTRY_POINTS:
            if script in ("launch.py", "build_dashboard.py", "session.py", "doctor.py"):
                continue                                               # these do real work: checked in their own tests below
            before = len(self.lines())
            r = self.run_script(script)                                # no arguments: each prints its usage and returns 2
            new = self.lines()[before:]
            area = script[:-3]
            self.assertTrue(any(re.search(rf"INFO  {area}\s+start", ln) for ln in new), (script, new))
            self.assertTrue(any(re.search(rf"WARN  {area}\s+exit {r.returncode} after", ln) for ln in new), (script, r.returncode, new))

    def test_a_script_that_works_logs_an_exit_zero(self):
        self.v.run("init")
        self.assertEqual(self.run_script("doctor.py").returncode, 0)
        self.assertTrue(any(re.search(r"INFO  doctor\s+exit 0 after", ln) for ln in self.lines()))
        self.assertEqual(self.run_script("build_dashboard.py").returncode, 0)
        self.assertTrue(any(re.search(r"INFO  build_dashboard\s+exit 0 after", ln) for ln in self.lines()))

    def test_the_exit_code_and_the_output_are_unchanged(self):
        self.v.run("init")
        with_log = self.run_script("session.py")
        self.assertEqual(with_log.returncode, 2)
        shutil.rmtree(self.logs, ignore_errors=True)
        (self.root / "system" / "scripts" / "log.py").unlink()          # a vault without the helper still runs
        without = self.run_script("session.py")
        self.assertEqual((without.returncode, without.stdout), (with_log.returncode, with_log.stdout))
        self.assertFalse(self.logs.exists())

    def test_an_error_in_a_script_leaves_a_traceback_and_still_fails(self):
        self.v.run("init")
        self.root.joinpath("system", "scripts", "boom.py").write_text(
            "import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).resolve().parent))\n"
            "import paths\n\ndef main():\n    raise ValueError('it broke')\n\n"
            "if __name__ == '__main__':\n    try:\n        import log as debuglog\n    except ImportError:\n        debuglog = None\n"
            "    sys.exit(debuglog.main('boom.py', main) if debuglog else main())\n")
        r = self.run_script("boom.py")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("ValueError: it broke", r.stderr)               # the traceback still reaches the console
        text = "\n".join(self.lines())
        self.assertRegex(text, r"ERROR boom\s+failed after .*ValueError: it broke")
        self.assertIn("    Traceback (most recent call last):", text)

    def test_a_script_with_its_own_log_function_is_not_shadowed(self):
        self.v.run("init")
        self.root.joinpath("system", "scripts", "ownlog.py").write_text(
            "import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).resolve().parent))\n"
            "import paths\n\ndef log(entry):\n    print('its own log:', entry)\n\ndef main():\n    log('hello')\n    return 0\n\n"
            "if __name__ == '__main__':\n    try:\n        import log as debuglog\n    except ImportError:\n        debuglog = None\n"
            "    sys.exit(debuglog.main('ownlog.py', main) if debuglog else main())\n")
        r = self.run_script("ownlog.py")
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "its own log: hello"), r.stderr)
        self.assertRegex("\n".join(self.lines()), r"INFO  ownlog\s+exit 0 after")
        for script in ("permissions.py", "filechange.py"):             # real scripts that already have a function called log
            self.assertIn("def log(", (SCRIPTS / script).read_text(encoding="utf-8"))
            self.assertNotRegex((SCRIPTS / script).read_text(encoding="utf-8"), r"(?m)^\s+import log\s*(#.*)?$")

    def test_the_command_has_names_never_values(self):
        self.v.run("init")
        self.run_script("search.py", "query", "CANARY secret words", "--file=/Users/x/CANARY-note.json", "--limit", "5")
        text = "\n".join(self.lines())
        self.assertNotIn("CANARY", text)
        self.assertRegex(text, r"start query --file --limit")


FAKE_CLAUDE = r'''#!/usr/bin/env python3
import json, sys
args = sys.argv[1:]
message = args[args.index("--") + 1]
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-1"})
out({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": "Read", "input": {"file_path": "CANARY-TOOL-INPUT"}}]}})
out({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "content": "CANARY-TOOL-RESULT"}]}})
if "perm" in message:
    text = "I need one more rule.\nPERMISSION: Read(projects/**) | CANARY-WHY"
    out({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}})
    out({"type": "result", "result": text, "session_id": "sess-1",
         "permission_denials": [{"tool_name": "Bash", "tool_input": {"command": "cat CANARY-DENIED-INPUT"}}]})
else:
    out({"type": "assistant", "message": {"content": [{"type": "text", "text": "Here is CANARY-REPLY."}]}})
    out({"type": "result", "result": "Here is CANARY-REPLY.", "session_id": "sess-1"})
'''


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Server:
    """A live server in a throwaway vault, with a stand-in `claude`."""

    def __init__(self, level="debug", seed=None, with_log=True):
        self.v = v = Vault()
        populate(v)
        cfg = v.root / "system" / "config" / "settings.json"
        data = json.loads(cfg.read_text())
        data.setdefault("logging", {})["level"] = level
        for dotted, value in (seed or {}).items():
            o = data
            *head, last = dotted.split(".")
            for k in head:
                o = o.setdefault(k, {})
            o[last] = value
        cfg.write_text(json.dumps(data, indent=2))
        if not with_log:
            (v.root / "system" / "scripts" / "log.py").unlink()
            shutil.rmtree(v.root / "system" / "logs", ignore_errors=True)       # what the set-up scripts wrote before
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE_CLAUDE)
        fake.chmod(0o755)
        self.port = free_port()
        self.base = f"http://127.0.0.1:{self.port}"
        self.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True,
                                     env={**os.environ, "CREAITE_PORT": str(self.port), "CREAITE_CLAUDE": str(fake)})
        deadline = time.time() + 30                     # dev-test-steadiness: a loaded runner can take more than 6 s to start it
        while True:
            try:
                urllib.request.urlopen(self.base + "/health", timeout=1)
                break
            except OSError:
                if time.time() > deadline or self.proc.poll() is not None:
                    raise
                time.sleep(0.1)
        html = urllib.request.urlopen(self.base + "/").read().decode()
        self.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]
        self.logs = v.root / "system" / "logs"

    def stop(self):
        self.proc.terminate()
        self.proc.wait(timeout=10)
        self.v.cleanup()

    def post(self, path, body, token=True):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json",
                                              **({"X-Creaite-Token": self.token} if token else {})})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read().decode()
                return r.status, (json.loads(raw) if r.headers.get_content_type() == "application/json" else raw)
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def ask(self, message):
        req = urllib.request.Request(self.base + "/api/ask", data=json.dumps({"message": message}).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        with urllib.request.urlopen(req, timeout=60) as r:
            return [json.loads(ln[6:]) for ln in r.read().decode().splitlines() if ln.startswith("data: ")]

    def text(self):
        out = ""
        for p in sorted(self.logs.glob("debug-*.log")):
            out += p.read_text(encoding="utf-8") + "\n"
        return out

    def wait_for(self, pattern, count=1, timeout=15):
        """The log once `pattern` is in it `count` times. dev-test-steadiness: the server writes a request's line after it
        has sent the reply (so the time includes sending it), so a test that reads the log the moment the reply arrives can
        be first; under load it was. Returns the log as it is then, matched or not, for the test's own assertions."""
        deadline = time.time() + timeout
        while True:
            text = self.text()
            if len(re.findall(pattern, text)) >= count or time.time() > deadline:
                return text
            time.sleep(0.05)


class LiveServerLog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = Server(seed={"identity.name": "Alan Canary", "identity.short_forms": ["AC-CANARY"],
                             "identity.own_domains": ["canary.example"], "people.added": ["Pat CANARY-PERSON"],
                             "locations.projects_root": "~/Library/CloudStorage/OneDrive-CANARY/Engagements",
                             "sweep.ignore": [{"name": "CANARY-RULE", "builtin": "none"}]})

    @classmethod
    def tearDownClass(cls):
        cls.s.stop()

    def test_the_server_logs_its_start(self):
        self.assertRegex(self.s.text(), r"INFO  server\s+starting: creaite")
        self.assertRegex(self.s.text(), r"INFO  live_server\s+start")

    def test_a_request_is_logged_by_route_status_and_time_only(self):
        data_lines = len(re.findall(r"GET /api/data \d{3} \d+ms", self.s.text()))
        self.s.post("/api/fs", {"op": "read", "path": "projects/CANARY-FILE-NAME/x.md"})
        urllib.request.urlopen(self.s.base + "/health").read()
        for url in ("/api/data", "/api/data?token-ish=CANARY-QUERY-2"):         # the second isn't a route: still no value in the log
            try:
                urllib.request.urlopen(urllib.request.Request(self.s.base + url, headers={"X-Creaite-Token": self.s.token})).read()
            except urllib.error.HTTPError:
                pass
        self.s.wait_for(r"POST /api/fs \d{3} \d+ms")
        self.s.wait_for(r"GET /health \d{3} \d+ms")
        text = self.s.wait_for(r"GET /api/data \d{3} \d+ms", data_lines + 2)   # both of this test's requests are in the log
        self.assertRegex(text, r"POST /api/fs \d{3} \d+ms")
        self.assertRegex(text, r"DEBUG server\s+GET /health 200 \d+ms")          # polled routes: debug level only
        self.assertRegex(text, r"GET /api/data 200 \d+ms")
        for canary in ("CANARY-FILE-NAME", "CANARY-QUERY-2", "token-ish"):
            self.assertNotIn(canary, text)                                       # no body, no query value, no file name

    def test_a_remembered_chat_that_is_gone_is_logged_at_info_not_warn(self):
        """BL-330: a chat removed from the history (or another vault's) is normal: one INFO line, never a WARN."""
        code, rec = self.s.post("/api/chat", {"chat": "ask-CANARY-GONE"})
        self.assertEqual((code, rec.get("ok")), (404, False))
        self.assertIs(rec.get("gone"), True)                                     # the page forgets it on this
        text = self.s.wait_for(r"POST /api/chat 404 \d+ms")
        self.assertRegex(text, r"INFO  server\s+POST /api/chat 404 \d+ms chat not in the history")
        self.assertNotRegex(text, r"WARN\s+server\s+POST /api/chat")
        self.assertNotIn("CANARY-GONE", text)                                    # the chat's ID is the page's, not logged

    def test_a_failed_apply_logs_its_reason_without_item_text(self):
        prop = self.s.v.root / "system" / "staging" / "proposed-canary.json"
        prop.write_text(json.dumps({"created": "2026-10-05T10:00:00", "source_run": "dashboard", "files": [], "items": [
            {"n": 1, "op": "update", "table": "actions", "id": "ABC-A-999", "changes": {"description": "CANARY-ITEM-TEXT"},
             "based_on": "x", "decision": "approved"}]}))
        code, body = self.s.post("/api/apply", {})
        text = self.s.wait_for(r"POST /api/apply \d{3} \d+ms")
        self.assertRegex(text, r"POST /api/apply \d{3} \d+ms")
        self.assertNotIn("CANARY-ITEM-TEXT", text)

    def test_runs_are_logged_without_a_word_of_the_conversation(self):
        events = self.s.ask("tell me CANARY-CHAT")
        self.assertTrue(any(e["type"] == "done" for e in events))
        deadline = time.time() + 5
        while "ended after" not in self.s.text() and time.time() < deadline:
            time.sleep(0.1)
        text = self.s.text()
        self.assertRegex(text, r"INFO  run\s+r-\w+ started: ask")
        self.assertRegex(text, r"INFO  run\s+r-\w+ ended after \d+s: ask, \d+ steps")
        self.assertRegex(text, r"DEBUG run\s+tool Read")                         # the tool's name, never what it was given
        for canary in ("CANARY-CHAT", "CANARY-REPLY", "CANARY-TOOL-INPUT", "CANARY-TOOL-RESULT"):
            self.assertNotIn(canary, text)

    def test_a_permission_request_and_a_refused_tool_are_logged_by_rule_and_name(self):
        self.s.ask("perm please")
        deadline = time.time() + 5
        while "tool refused" not in self.s.text() and time.time() < deadline:
            time.sleep(0.1)
        text = self.s.text()
        self.assertRegex(text, r"WARN  run\s+r-\w+ card c-\w+: 1 changes for approval, 0 refused: Allow Read\(projects/\*\*\)")   # BL-141: on the one card
        self.assertRegex(text, r"WARN  run\s+r-\w+ tool refused: Bash")
        for canary in ("CANARY-WHY", "CANARY-DENIED-INPUT"):
            self.assertNotIn(canary, text)                                       # not the reason, not the tool's input

    def test_quick_capture_intake_generate_and_search_keep_their_content_out_of_the_log(self):
        import base64
        canaries = ("CANARY-NOTE", "CANARY-ACTION", "CANARY-TITLE", "CANARY-WHO", "CANARY-UPLOAD", "CANARY-TRANSCRIPT",
                    "CANARY-QUESTION", "CANARY-GEN-NOTE")
        self.s.post("/api/notes/capture/done", {"body": "CANARY-NOTE: Sara agreed to CANARY-ACTION by Friday", "code": "ABC",   # BL-301 C
                                                "title": "CANARY-TITLE catch-up", "with": ["CANARY-WHO"], "template": "working-session",
                                                "date": "2026-10-09"})
        self.s.post("/api/inbox/upload", {"name": "CANARY-UPLOAD.vtt",
                                          "data": base64.b64encode(b"WEBVTT\n\n00:00.000 --> 00:02.000\nCANARY-TRANSCRIPT words").decode()})
        self.s.post("/api/search/ask", {"q": "what did CANARY-QUESTION say?"})
        self.s.post("/api/generate", {"code": "ABC", "note": "CANARY-GEN-NOTE"})
        for route in ("notes/capture/done", "inbox/upload", "search/ask"):          # every request's line is written before the checks
            self.s.wait_for(rf"POST /api/{route} \S+ \d+ms")            # a streamed reply has no status: "-"
        text = self.s.wait_for(r"POST /api/generate \S+ \d+ms")
        self.assertRegex(text, r"POST /api/notes/capture/done \d{3}")
        self.assertRegex(text, r"POST /api/inbox/upload \d{3}")
        for canary in canaries:
            self.assertNotIn(canary, text)
        report = self.s.post("/api/diagnostics", {"report": True})[1]["report"]
        for canary in canaries:
            self.assertNotIn(canary, report)

    def test_the_browser_error_route(self):
        self.assertEqual(self.s.post("/api/log/error", {"message": "x"}, token=False)[0], 403)
        code, body = self.s.post("/api/log/error", {"message": "Cannot read properties of null", "view": "work",
                                                    "source": "http://127.0.0.1/app.js?v=CANARY-SRC", "line": 412})
        self.assertEqual((code, body["logged"]), (200, True))
        self.s.post("/api/log/error", {"message": "m" * 900, "view": "v" * 900})
        self.s.post("/api/log/error", {"message": "Unexpected token 'C', \"CANARY-JSON-SNIPPET is not\" is not valid JSON",
                                       "view": "files"})
        text = self.s.text()
        self.assertRegex(text, r"files: Unexpected token 'C', \"…\" is not valid JSON")
        self.assertNotIn("CANARY-JSON-SNIPPET", text)                            # quoted text in a page error is taken out
        self.assertRegex(text, r"ERROR dashboard\s+work: Cannot read properties of null \(http://127.0.0.1/app.js:412\)")
        self.assertNotIn("CANARY-SRC", text)                                    # a query is never kept
        long_line = next(ln for ln in text.splitlines() if "mmmm" in ln)
        self.assertLess(len(long_line), 800)                                     # each field cut at 300

    def test_the_resize_observer_notice_is_not_an_error(self):
        # BL-283: Chrome's "ResizeObserver loop …" is a browser notice; it was logged as ERROR dashboard
        for msg in ("ResizeObserver loop completed with undelivered notifications.", "ResizeObserver loop limit exceeded",
                    "Uncaught ResizeObserver loop completed with undelivered notifications."):
            code, body = self.s.post("/api/log/error", {"message": msg, "view": "cockpit"})
            self.assertEqual((code, body["logged"]), (200, False), msg)
        self.assertFalse([ln for ln in self.s.text().splitlines() if "ERROR" in ln and "ResizeObserver" in ln])
        code, body = self.s.post("/api/log/error", {"message": "A real fault after the notice", "view": "cockpit"})
        self.assertEqual((code, body["logged"]), (200, True))
        self.assertIn("A real fault after the notice", self.s.text())

    def test_diagnostics_lists_the_latest_errors(self):
        self.s.post("/api/log/error", {"message": "A page error to list", "view": "today", "source": "x", "line": 1})
        code, body = self.s.post("/api/diagnostics", {})
        self.assertEqual(code, 200)
        self.assertEqual(body["level"], "debug")
        self.assertTrue(any(e["message"].startswith("today: A page error to list") for e in body["errors"]))
        self.assertLessEqual(len(body["errors"]), 10)
        self.assertEqual(self.s.post("/api/diagnostics", {}, token=False)[0], 403)
        # BL-180: the last day's errors grouped (numbers ignored), with each group's times and the newest time
        for n in (1, 2, 3):
            self.s.post("/api/log/error", {"message": f"Grouped fault {n}", "view": "work", "source": "x", "line": 1})
        body = self.s.post("/api/diagnostics", {})[1]
        g = next(g for g in body["groups"] if "Grouped fault" in g["message"])
        self.assertEqual((g["area"], g["count"], len(g["times"])), ("dashboard", 3, 3))
        self.assertEqual(body["newest"], max(x["last"] for x in body["groups"]))
        self.assertNotIn("detail", g)

    # ===== BL-252 (fix-small-17): Settings › Diagnostics counts refused commands by shape, never their text =====
    def test_diagnostics_counts_refused_commands_by_shape_without_their_text(self):
        from datetime import datetime
        day = self.s.logs / f"debug-{datetime.now():%Y-%m-%d}.log"
        stamp = f"{datetime.now():%Y-%m-%d %H:%M:%S}"
        with day.open("a", encoding="utf-8") as f:
            for msg in ("t1 refused: tracker.py with a pipe", "t2 refused: tracker.py with a pipe",
                        "t3 refused: CANARY-REFUSED-TEXT | grep x"):
                f.write(f"{stamp} WARN  run          {msg}\n")
        body = self.s.post("/api/diagnostics", {})[1]
        got = {r["shape"]: r["count"] for r in body["refusals"]}
        self.assertGreaterEqual(got.get("a pipe", 0), 2)
        self.assertGreaterEqual(got.get("other", 0), 1)
        self.assertNotIn("CANARY-REFUSED-TEXT", json.dumps(body["refusals"]))
        self.assertTrue(all(set(r) == {"shape", "count"} for r in body["refusals"]))
    # ===== end BL-252 =====

    def test_copy_diagnostics_holds_the_safe_things_and_none_of_the_private_ones(self):
        self.s.post("/api/log/error", {"message": "mail pat@canary.example about /Users/alan/Secret/CANARY-PATH", "view": "x"})
        code, body = self.s.post("/api/diagnostics", {"report": True})
        report = body["report"]
        self.assertIn("creaite diagnostics", report)
        self.assertIn("doctor:", report)
        self.assertIn("settings (safe ones only):", report)
        self.assertIn("dashboard.palette:", report)
        self.assertIn("logging.level: debug", report)
        self.assertIn("locations.projects_root: set", report)                    # whether it is set, never where
        self.assertIn("last log lines", report)
        for private in ("Alan Canary", "AC-CANARY", "canary.example", "CANARY-PERSON", "OneDrive-CANARY", "CANARY-RULE",
                        "CANARY-PATH", "pat@"):
            self.assertNotIn(private, report, private)
        self.assertIn("[address]", report)                                       # an address or a path in a log line is removed
        self.assertIn("[path]", report)

    def test_the_log_folder_can_be_opened_and_nothing_wider(self):
        r = subprocess.run([sys.executable, "-c",
                            f"import sys; sys.path.insert(0, {str(self.s.v.root / 'system' / 'scripts')!r}); import re, live_server as L;"
                            "print(bool(re.fullmatch(L.OPEN_OK, 'system/logs')), bool(re.fullmatch(L.OPEN_OK, 'system/tracker.db')), "
                            "bool(re.fullmatch(L.OPEN_OK, 'projects/ABC Example Programme/CLAUDE.md')))"],
                           capture_output=True, text=True, cwd="/tmp")
        self.assertEqual(r.stdout.split(), ["True", "False", "True"], r.stderr)


class BrowserRateLimit(unittest.TestCase):
    def test_twenty_a_minute_then_one_summary_line(self):
        v = Vault()
        try:
            code = f"""
import sys, json, time
sys.path.insert(0, {str(v.root / 'system' / 'scripts')!r})
import live_server as L
class H:
    sent = []
    def authorised(self): return True
    def body(self): return {{"message": "boom", "view": "work"}}
    def send(self, code, body, *a, **k): self.sent.append(body)
h = H()
for i in range(25): L.browser_error(h)
print([b["logged"] for b in h.sent].count(True), [b["logged"] for b in h.sent].count(False))
real = time.time
time.time = lambda: real() + 61                        # the next minute
L.browser_error(h)
print([b["logged"] for b in h.sent][-1])
"""
            r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd="/tmp",
                               env={**os.environ, "CREAITE_NOW": ""})
            self.assertEqual(r.stdout.split(), ["20", "5", "True"], r.stderr)
            text = "\n".join(p.read_text(encoding="utf-8") for p in (v.root / "system" / "logs").glob("debug-*.log"))
            self.assertEqual(text.count("ERROR dashboard"), 21)
            self.assertIn("5 more page errors in the last minute were not logged", text)
        finally:
            v.cleanup()


class WithoutTheHelper(unittest.TestCase):
    def test_the_server_still_starts_without_log_py(self):
        s = Server(with_log=False)
        try:
            self.assertEqual(s.post("/api/diagnostics", {})[0] in (200, 404, 403), True)
            self.assertFalse(s.logs.exists())
        finally:
            s.stop()


from live_browser import LiveBrowserCase  # noqa: E402


class DashboardDiagnostics(LiveBrowserCase):
    """The page's error hook, the errors banner (BL-180; it replaced the quiet link in the top bar), and Settings › Diagnostics, in a real browser."""

    def log_text(self):
        out = ""
        for p in sorted((self.v.root / "system" / "logs").glob("debug-*.log")):
            out += p.read_text(encoding="utf-8")
        return out

    def log_has(self, needle, timeout=8):
        end = time.time() + timeout
        while time.time() < end:
            if needle in self.log_text():
                return True
            time.sleep(0.1)
        return False

    def raise_in_page(self, message):
        self.b.eval(f"setTimeout(()=>{{ throw new Error({json.dumps(message)}) }}, 0)")

    def test_a_script_error_in_the_page_reaches_the_log_with_quoted_text_taken_out(self):
        self.raise_in_page("page broke here")
        self.assertTrue(self.log_has("page broke here"))
        self.raise_in_page('bad "CANARY-QUOTED" thing')
        self.assertTrue(self.log_has('bad "…" thing'))
        self.assertNotIn("CANARY-QUOTED", self.log_text())
        self.assertRegex(self.log_text(), r"ERROR dashboard\s+today: .*page broke here")

    def test_the_page_does_not_report_the_resize_observer_notice(self):
        # BL-283: diagHook leaves the browser's notice out; a real script error is still reported
        sent = self.b.eval("DIAGSENT")
        self.b.eval("diagHook('ResizeObserver loop completed with undelivered notifications.','',0); "
                    "diagHook('ResizeObserver loop limit exceeded','',0)")
        self.assertEqual(self.b.eval("DIAGSENT"), sent)
        self.raise_in_page("a real fault after the notice")
        self.assertTrue(self.log_has("a real fault after the notice"))
        self.assertNotIn("ResizeObserver", self.log_text())

    # ===== BL-252 (fix-small-17) =====
    def test_diagnostics_shows_the_refused_command_counts(self):
        # The page loads its Diagnostics from the server when it starts; that load used to land after a stubbed DIAG and wipe it
        # (seen on slower Linux runners). So the counts come from the server, end to end, after that first load has finished.
        from datetime import datetime
        b = self.b
        b.wait("DIAG.loaded")
        b.eval("STAB='system'; go('settings')")
        b.wait("!!document.getElementById('diagRefused')")
        self.assertEqual(b.eval("document.getElementById('diagRefused').textContent"), "None in the last 7 days")
        logs = self.v.root / "system" / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        now = datetime.now()                                  # the server's clock: same machine, same time zone, not pinned
        with (logs / f"debug-{now:%Y-%m-%d}.log").open("a", encoding="utf-8") as f:
            for msg in ["p1 refused: tracker.py with a pipe", "p2 refused: tracker.py with a pipe",
                        "p3 refused: tracker.py with a pipe, a redirect", "p4 refused: CANARY-SHOWN-TEXT here"]:
                f.write(f"{now:%Y-%m-%d %H:%M:%S} WARN  run          {msg}\n")
        b.click("#diagRefresh")
        b.wait("document.getElementById('diagRefused').textContent!=='None in the last 7 days'")
        self.assertEqual(b.eval("document.getElementById('diagRefused').textContent"), "3 × a pipe, 1 × a redirect, 1 × other")
        self.assertNotIn("CANARY-SHOWN-TEXT", b.eval("document.getElementById('diagCard').textContent"))
    # ===== end BL-252 =====

    # ===== BL-180 (sprint-peek-new): the errors banner replaces the header link =====
    def banner(self):
        return self.b.eval("(b=>b&&!b.hidden?b.textContent:'')(document.getElementById('errBanner'))")

    def test_no_header_link_and_no_banner_without_errors(self):
        self.b.wait("DIAG.loaded")
        self.assertFalse(self.b.eval("!!document.querySelector('#status .diaglink')"))
        self.assertEqual(self.banner(), "")

    def test_the_banner_appears_with_errors_and_investigate_opens_diagnostics(self):
        self.raise_in_page("something failed")
        self.b.wait("!document.getElementById('errBanner').hidden")
        self.assertRegex(self.banner(), r"^\d+ errors? (\(\d+ times\) )?in the last day")
        self.assertIn("in the page", self.banner())                                  # what kind
        self.assertFalse(self.b.eval("!!document.querySelector('#status .diaglink')"))   # never in the header
        self.assertEqual(self.b.eval("document.querySelector('#errBanner svg').getAttribute('aria-hidden')"), "true")
        self.assertEqual(self.b.eval("document.getElementById('errBanner').getAttribute('role')"), "status")
        self.assertTrue(self.b.eval("!!document.getElementById('ebAsk')"))           # the live server is running
        self.b.click("#ebInv")
        self.b.wait("VIEW==='settings' && !!document.getElementById('diagCard')")
        self.assertEqual(self.banner(), "")                                           # investigated: seen

    def test_repeats_are_grouped_and_dismiss_holds_until_a_new_error(self):
        b = self.b
        for _ in range(3):
            self.raise_in_page("the same fault 7")
            b.pump(0.3)
        b.wait("/\\(\\d+ times\\)/.test(document.getElementById('errBanner').textContent)")
        self.assertRegex(self.banner(), r"^1 error \(3 times\) in the last day")
        b.click("#ebX")
        b.wait("document.getElementById('errBanner').hidden")
        b.reload()
        b.wait("typeof go==='function' && LIVE && DIAG.loaded")
        b.pump(0.3)
        self.assertEqual(self.banner(), "")                                           # stays dismissed after a reload
        self.raise_in_page("a different fault")
        b.wait("!document.getElementById('errBanner').hidden")
        self.assertRegex(self.banner(), r"^1 new error")                              # only the new one

    def test_it_stacks_under_the_live_server_alert_and_ask_needs_the_server(self):
        b = self.b
        self.raise_in_page("stack check")
        b.wait("!document.getElementById('errBanner').hidden")
        b.eval("document.getElementById('liveAlert').classList.add('on')")
        top = b.eval("document.getElementById('errBanner').getBoundingClientRect().top")
        alert_bottom = b.eval("document.getElementById('liveAlert').getBoundingClientRect().bottom")
        self.assertGreaterEqual(top, alert_bottom - 1)                                # errors last
        b.eval("LIVE=false; errBanner()")
        self.assertFalse(b.eval("!!document.getElementById('ebAsk')"))
        b.eval("LIVE=true; errBanner()")
        self.assertTrue(b.eval("!!document.getElementById('ebAsk')"))
    # ===== end BL-180 =====

    def test_the_card_lists_the_latest_errors_and_opens_a_traceback(self):
        self.raise_in_page("listed error")
        self.assertTrue(self.log_has("listed error"))
        self.b.eval("go('settings','system')")
        self.b.wait("!!document.getElementById('diagCard') && DIAG.loaded")   # #96: the errors banner has come in, so the button stays where it is
        time.sleep(0.3)
        self.b.click("#diagRefresh")
        self.b.wait("document.getElementById('diagList').textContent.includes('listed error')")
        self.assertIn("dashboard", self.b.eval("document.getElementById('diagList').textContent"))
        self.assertEqual(self.b.eval("document.getElementById('diagLevel').value"), "info")
        self.assertTrue(self.b.eval("!!document.getElementById('diagCard').querySelector('details.diagerr summary')"))

    def test_the_level_switch_writes_the_setting(self):
        self.b.eval("go('settings','system')")
        self.b.wait("!!document.getElementById('diagCard')")
        self.b.eval("const s=document.getElementById('diagLevel'); s.value='debug'; s.dispatchEvent(new Event('change',{bubbles:true}))")
        cfg = self.v.root / "system" / "config" / "settings.json"
        end = time.time() + 8
        while time.time() < end and json.loads(cfg.read_text()).get("logging", {}).get("level") != "debug":
            time.sleep(0.1)
        self.assertEqual(json.loads(cfg.read_text())["logging"]["level"], "debug")
        log = self.v.root / "system" / "config" / "settings-log.jsonl"          # written just after settings.json: wait for it too
        end = time.time() + 8
        while time.time() < end and not (log.exists() and "logging.level" in log.read_text()):
            time.sleep(0.1)
        self.assertTrue(any("logging.level" in ln for ln in log.read_text().splitlines()))

    def test_copy_diagnostics_puts_the_report_on_the_clipboard(self):
        self.b.eval("go('settings','system')")
        self.b.wait("!!document.getElementById('diagCard')")
        self.b.eval("window.__copied=null; navigator.clipboard.writeText=t=>{ window.__copied=t; return Promise.resolve(); }")
        self.b.click("#diagCopy")
        self.b.wait("!!window.__copied", timeout=30)
        report = self.b.eval("window.__copied")
        self.assertIn("creaite diagnostics", report)
        self.assertIn("settings (safe ones only):", report)
        self.assertNotIn(str(self.v.root), report)


if __name__ == "__main__":
    unittest.main()
