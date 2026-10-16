"""Tests for the chat bubbles and the dashboard after the sweep (BL-108, BL-109, BL-110).

Run: python3 dev/tests/test_chat_and_sweep.py
Item 1 (BL-110 part 1): the sweep and a minutes run rebuild dashboard.html themselves. Each test builds a throwaway
vault (as test_tracker.py does) and runs the real scripts there with the clock fixed by CREAITE_NOW.
"""
import json
import os
import re
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import Vault  # noqa: E402

EMAIL = ("Email · From: Jane Doe <jane@client.example> · Subject: [ABC] SOW · Sent: 2026-10-05 09:12 · "
         "Link: https://outlook.office365.com/owa/?ItemID=abc1")
NOTE = "projects/ABC Example Programme/minutes/2026-10-09 Quick note - catch-up.md"


class VaultCase(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.root = self.v.root
        self.v.run("init")
        self.v.run(script="build_dashboard.py")                  # a first build, as the vault has in use
        self.page = self.root / "dashboard.html"

    def tearDown(self):
        self.v.cleanup()

    def script(self, name, *args, when="2026-10-09 07:10", env=None):
        return subprocess.run([sys.executable, str(self.root / "system" / "scripts" / name), *args], capture_output=True,
                              text=True, cwd="/tmp", env={**os.environ, "CREAITE_NOW": when, **(env or {})})

    def sweep_spec(self, description):
        spec = self.root / "system" / "staging" / "sweep.json"
        spec.write_text(json.dumps({"window": {"start": "2026-10-08 08:00", "end": "2026-10-09 07:00"}, "items": [
            {"table": "actions", "match": "strong", "values": {"project": "ABC", "description": description,
                                                               "owner": "Alan Carter", "source": EMAIL}}]}))
        return spec


class SweepRebuild(VaultCase):
    def test_stage_leaves_a_dashboard_that_shows_the_new_items(self):
        self.assertNotIn("Chase the signed approval", self.page.read_text(encoding="utf-8"))
        r = self.script("sweep.py", "stage", str(self.sweep_spec("Chase the signed approval")))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Sweep: 1 item (0 possible)", r.stdout)
        self.assertRegex(r.stdout, r"Built dashboard\.html: .* \d+ to review")
        self.assertIn("Chase the signed approval", self.page.read_text(encoding="utf-8"))

    def test_done_records_the_sweep_and_the_dashboard_shows_it(self):
        self.assertNotIn('"last_sweep":"2026-10-09 07:00"', self.page.read_text(encoding="utf-8"))
        r = self.script("sweep.py", "done", "--started", "2026-10-09 07:00", "--normal", "--summary", "test")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Recorded.", r.stdout)
        self.assertIn('"last_sweep":"2026-10-09 07:00"', self.page.read_text(encoding="utf-8"))

    def test_fail_and_calendar_rebuild_too(self):
        before = self.page.stat().st_mtime_ns
        r = self.script("sweep.py", "fail", "--message", "Microsoft 365 didn't answer")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Built dashboard.html", r.stdout)
        self.assertGreater(self.page.stat().st_mtime_ns, before)
        spec = self.root / "system" / "staging" / "drafts" / "calendar.json"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text(json.dumps({"days": {"2026-10-09": [{"start": "13:00", "end": "14:00", "title": "ABC steering",
                                                              "where": "Teams", "organiser": True}]}}))
        r = self.script("sweep.py", "calendar", str(spec))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Calendar saved", r.stdout)
        self.assertIn("Built dashboard.html", r.stdout)
        self.assertIn("ABC steering", self.page.read_text(encoding="utf-8"))

    def test_commands_that_change_nothing_do_not_rebuild(self):
        before = self.page.stat().st_mtime_ns
        for args in (("due",), ("window",), ("lock",), ("unlock",)):
            r = self.script("sweep.py", *args)
            self.assertNotIn("Built dashboard.html", r.stdout, args)
        self.assertEqual(self.page.stat().st_mtime_ns, before)

    def test_a_command_that_fails_does_not_rebuild(self):
        before = self.page.stat().st_mtime_ns
        r = self.script("sweep.py", "stage", str(self.root / "no-such-file.json"))
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("Built dashboard.html", r.stdout)
        self.assertEqual(self.page.stat().st_mtime_ns, before)

    def test_a_rebuild_that_fails_never_changes_the_sweeps_result(self):
        (self.root / "system" / "templates" / "dashboard.html").unlink()      # the build can't run without its template
        r = self.script("sweep.py", "done", "--started", "2026-10-09 07:00", "--normal", "--summary", "test")
        self.assertEqual(r.returncode, 0, r.stderr)                           # the sweep's result stands
        self.assertIn("Recorded.", r.stdout)
        notes = [ln for ln in r.stdout.splitlines() if ln.startswith("Note: the dashboard wasn't rebuilt")]
        self.assertEqual(len(notes), 1, r.stdout)                             # one line, naming what to run
        self.assertIn("build_dashboard.py", notes[0])
        self.assertEqual((self.root / "system" / "staging" / "last-sweep.txt").read_text().strip(), "2026-10-09 07:00")

    def test_a_minutes_run_rebuilds_too(self):
        note = self.root / NOTE
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text("# Quick note\n\n- Date: 2026-10-09\n- Project: ABC\n\nSara will send the revised statement of work.\n")
        spec = self.root / "system" / "staging" / "note.json"
        spec.write_text(json.dumps({"title": "Quick note - catch-up", "date": "2026-10-09", "event_id": None, "projects": ["ABC"],
                                    "note": NOTE, "status_signals": [], "items": [
                                        {"table": "actions", "section": "Actions", "flags": [],
                                         "values": {"project": "ABC", "description": "Send the revised statement of work",
                                                    "owner": "Sara Example", "due_date": "2026-10-16", "raised": "2026-10-09"}}]}))
        r = self.script("minutes.py", "stage", str(spec))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Built dashboard.html", r.stdout)
        self.assertIn("Send the revised statement of work", self.page.read_text(encoding="utf-8"))


class BuildsTakeTurns(VaultCase):
    def test_a_reader_never_sees_half_a_page_while_builds_overlap(self):
        # Rounds of six overlapping builds, until the reader has read the page at least 20 times while builds were running
        # (counted only then). A count, not a time window: on a busy machine the reader thread gets few turns per round.
        stop, building, bad, reads = threading.Event(), threading.Event(), [], [0]

        def reader():
            while not stop.is_set():
                during = building.is_set()
                try:
                    text = self.page.read_text(encoding="utf-8")
                except OSError:
                    continue
                if during and building.is_set():
                    reads[0] += 1
                if not text.rstrip().endswith("</html>"):
                    bad.append(len(text))
        t = threading.Thread(target=reader)
        t.start()
        rounds = 0
        try:
            while reads[0] <= 20 and rounds < 25:
                rounds += 1
                building.set()
                procs = [subprocess.Popen([sys.executable, str(self.root / "system" / "scripts" / "build_dashboard.py")],
                                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd="/tmp") for _ in range(6)]
                self.assertEqual([p.wait(timeout=120) for p in procs], [0] * 6)
                building.clear()
        finally:
            building.clear()
            stop.set()
            t.join()
        self.assertGreater(reads[0], 20, f"the reader read the page only {reads[0]} times during {rounds} rounds of builds")
        self.assertEqual(bad, [], f"a half-written page was seen: {bad[:3]}")
        left = [p.name for p in (self.root / "system" / "staging").glob(".dashboard-build.lock")] + \
               [p.name for p in self.root.glob("dashboard.html.*.tmp")]
        self.assertEqual(left, [])                                            # no lock and no temporary file left behind

    def test_a_dead_builds_lock_is_broken(self):
        lock = self.root / "system" / "staging" / ".dashboard-build.lock"
        lock.write_text("99999")
        old = time.time() - 600
        os.utime(lock, (old, old))
        started = time.time()
        r = self.script("build_dashboard.py")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertLess(time.time() - started, 20)
        self.assertFalse(lock.exists())

    def test_a_build_waits_its_turn_and_then_goes_ahead(self):
        lock = self.root / "system" / "staging" / ".dashboard-build.lock"
        lock.write_text("99999")                                              # another build, still running
        started = time.time()
        r = self.script("build_dashboard.py", env={"CREAITE_BUILD_WAIT": "1.5"})
        took = time.time() - started
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertGreaterEqual(took, 1.4)                                    # it waited for the other build
        self.assertIn("Built dashboard.html", r.stdout)                       # and then built anyway
        self.assertTrue(lock.exists())                                        # the other build's lock is not ours to remove



# ---------------------------------------------------------------- item 2: the pulse and the self-refreshing page
import urllib.error  # noqa: E402
import urllib.request  # noqa: E402

from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402


def stage_sweep(root, *descriptions, when="2026-10-09 07:10"):
    """Stage a sweep from outside the page, as a Terminal session or the scheduler would."""
    spec = root / "system" / "staging" / "sweep.json"
    spec.write_text(json.dumps({"window": {"start": "2026-10-08 08:00", "end": "2026-10-09 07:00"}, "items": [
        {"table": "actions", "match": "strong", "values": {"project": "ABC", "description": d, "owner": "Alan Carter",
                                                           "source": EMAIL.replace("abc1", f"abc{i}")}}
        for i, d in enumerate(descriptions)]}))
    r = subprocess.run([sys.executable, str(root / "system" / "scripts" / "sweep.py"), "stage", str(spec)],
                       capture_output=True, text=True, cwd="/tmp", env={**os.environ, "CREAITE_NOW": when})
    assert r.returncode == 0, r.stdout + r.stderr
    spec.unlink()


def short_health_check(v, seconds=1):
    p = v.root / "system" / "config" / "settings.json"
    cfg = json.loads(p.read_text())
    cfg.setdefault("live_mode", {})["health_check_seconds"] = seconds
    p.write_text(json.dumps(cfg, indent=2))


class PulseRoute(unittest.TestCase):
    """/api/pulse: a fingerprint of file stamps, the number waiting in Review and the last sweep time."""

    @classmethod
    def setUpClass(cls):
        from live_browser import free_port
        cls.v = Vault()
        populate(cls.v)
        cls.v.run(script="build_dashboard.py")
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.proc = subprocess.Popen([sys.executable, str(cls.v.root / "system/scripts/live_server.py")],
                                    env={**os.environ, "CREAITE_PORT": str(cls.port)},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        html = urllib.request.urlopen(cls.base + "/").read().decode()
        cls.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    def pulse(self, token=None):
        req = urllib.request.Request(self.base + "/api/pulse", data=b"{}", method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": token or self.token})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            with e:
                return e.code, json.loads(e.read().decode())

    def test_it_needs_the_token(self):
        self.assertEqual(self.pulse(token="wrong")[0], 403)
        status, body = self.pulse()
        self.assertEqual(status, 200)
        self.assertEqual(sorted(body), ["ok", "pending", "swept", "v"])

    def test_it_changes_when_something_does_and_not_otherwise(self):
        root = self.v.root
        a = self.pulse()[1]
        self.assertEqual(self.pulse()[1]["v"], a["v"])                        # nothing happened: the same fingerprint
        stage_sweep(root, "Chase the pulse approval", "Book the pulse workshop")
        b = self.pulse()[1]
        self.assertNotEqual(b["v"], a["v"])                                   # a proposal was staged
        self.assertEqual(b["pending"], a["pending"] + 2)                      # and the count is the Review count
        self.assertEqual(self.pulse()[1]["v"], b["v"])
        (root / "system/staging/last-sweep.txt").write_text("2026-10-09 07:10\n")
        c = self.pulse()[1]
        self.assertNotEqual(c["v"], b["v"])                                   # a sweep was recorded
        self.assertEqual(c["swept"], "2026-10-09 07:10")
        (root / "system/staging/calendar.json").write_text("{}")
        d = self.pulse()[1]
        self.assertNotEqual(d["v"], c["v"])                                   # the calendar was refreshed
        self.v.run("approve", "5", script="review.py")                        # the first of the two swept items
        e = self.pulse()[1]
        self.assertNotEqual(e["v"], d["v"])                                   # a decision was recorded
        self.assertEqual(e["pending"], d["pending"] - 1)
        self.v.run("apply")
        f = self.pulse()[1]
        self.assertNotEqual(f["v"], e["v"])                                   # an apply wrote the database

    def test_the_pending_count_matches_the_review_page(self):
        stage_sweep(self.v.root, "Count me in")
        self.v.run(script="build_dashboard.py")
        html = (self.v.root / "dashboard.html").read_text(encoding="utf-8")
        data = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))
        self.assertEqual(self.pulse()[1]["pending"], len(data["review"]))


# ===== BL-284 (fix-pulse): the pulse answers 200 through a race with a save, and a page that leaves isn't a 500 =====
PULSE_RIG = """
import json, sys
sys.path.insert(0, {scripts!r})
import live_server as L
from pathlib import Path

class W:
    def __init__(self, fail): self.fail, self.out = fail, b""
    def write(self, d):
        if self.fail: raise {left}()
        self.out += d

class H(L.Handler):
    def __init__(self, fail=False):
        self.path, self.command, self.wfile = "/api/pulse", "POST", W(fail)
        self.headers = {{"X-Creaite-Token": L.TOKEN, "Content-Length": "0"}}
        self.request_version, self.requestline, self._headers_buffer = "HTTP/1.1", "POST /api/pulse HTTP/1.1", []
        self.sent = []
    def host_ok(self): return True
    def log_message(self, *a): pass
    def send(self, code, body, *a, **k):
        self.sent.append(code)
        return L.Handler.send(self, code, body, *a, **k)
"""


class PulseRace(unittest.TestCase):
    """BL-284: POST /api/pulse while staging files come and go, and when the page leaves before the reply."""

    def setUp(self):
        self.v = Vault()
        self.root = self.v.root
        self.staging = self.root / "system" / "staging"

    def tearDown(self):
        self.v.cleanup()

    def py(self, code, left="BrokenPipeError"):
        rig = PULSE_RIG.format(scripts=str(self.root / "system" / "scripts"), left=left)
        r = subprocess.run([sys.executable, "-c", rig + code], capture_output=True, text=True, cwd="/tmp",
                           env={**os.environ, "CREAITE_NOW": "2026-10-12 10:00"})
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_a_proposal_that_vanishes_or_is_half_written_mid_scan_is_skipped(self):
        item = {"n": 1, "op": "new", "table": "actions", "decision": "pending", "values": {"title": "Count me"}}
        for name in ("a-good", "b-gone", "e-good"):
            (self.staging / f"proposed-{name}.json").write_text(json.dumps({"items": [item]}))
        (self.staging / "proposed-c-half.json").write_text('{"items": [{"n": 1, "deci')   # caught mid-write
        (self.staging / "proposed-d-odd.json").write_text('{"items": 7, "meeting": "x"}')  # a shape it can't count
        (self.staging / "drafts").mkdir(exist_ok=True)
        out = self.py("""
import errno, os
real_read, real_stat, real_iterdir = Path.read_text, Path.stat, Path.iterdir
def gone(path):                        # as the system raises it: with ENOENT, which Python 3.9's is_file() relies on
    return FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), str(path))
def read_text(self, *a, **k):          # listed by the scan, then gone before it is read
    if self.name == "proposed-b-gone.json": raise gone(self)
    return real_read(self, *a, **k)
def stat(self, *a, **k):               # gone between the listing and its stamp
    if self.name == "proposed-b-gone.json": raise gone(self)
    return real_stat(self, *a, **k)
def iterdir(self):                     # the drafts folder goes while it is listed
    if self.name == "drafts": raise gone(self)
    return real_iterdir(self)
Path.read_text, Path.stat, Path.iterdir = read_text, stat, iterdir
h = H()
L.Handler.do_POST(h)
body = json.loads(h.wfile.out.split(b"\\r\\n\\r\\n", 1)[1])
print(json.dumps({"sent": h.sent, "body": body}))
""")
        got = json.loads(out.strip().splitlines()[-1])
        self.assertEqual(got["sent"], [200])
        self.assertTrue(got["body"]["ok"])
        self.assertEqual(got["body"]["pending"], 2)                 # the two readable proposals, nothing more, nothing less
        self.assertRegex(got["body"]["v"], r"^[0-9a-f]{12}$")

    def test_a_page_that_leaves_mid_reply_is_logged_at_info_never_as_a_500(self):
        for left in ("BrokenPipeError", "ConnectionResetError"):
            out = self.py("""
h = H(fail=True)
L.Handler.do_POST(h)
print(h.sent)
""", left=left)
            self.assertEqual(out.strip().splitlines()[-1], "[200]")       # no 500 attempted after the page went
        log = (self.root / "system" / "logs" / "debug-2026-10-12.log").read_text(encoding="utf-8")
        self.assertIn("POST /api/pulse client left: BrokenPipeError", log)
        self.assertIn("POST /api/pulse client left: ConnectionResetError", log)
        self.assertNotIn("ERROR", log)
        self.assertNotIn(" 500 ", log)
# ===== end BL-284 =====


class SelfRefresh(LiveBrowserCase):
    """The open page notices new items by itself, and never disturbs an edit."""

    @classmethod
    def load(cls, v):
        populate(v)
        short_health_check(v)

    def snacks(self):
        self.b.eval("window.SNACKS=[]; const o=snack; snack=function(m,u,l){ SNACKS.push(m); return o.apply(this,arguments); }; 1")

    def review_has(self, text):
        return f"REV.some(r=>(r.rec&&r.rec.t||'').includes({text!r}))"

    def test_a_sweep_staged_from_outside_shows_up_with_a_quiet_message(self):
        self.b.wait("PULSE.v!=null")
        self.snacks()
        before = self.b.eval("REV.length")
        stage_sweep(self.v.root, "Chase the signed approval", "Book the workshop room", "Send the revised plan")
        self.b.wait(self.review_has("Chase the signed approval"), timeout=15)
        self.assertEqual(self.b.eval("REV.length"), before + 3)
        self.assertEqual(self.b.eval("document.getElementById('revBadge').textContent"), str(before + 3))
        self.b.wait("SNACKS.includes('3 new items in Review')", timeout=5)
        self.assertFalse(self.b.eval("document.getElementById('newChip').classList.contains('on')"))

    def test_an_open_form_is_not_disturbed_and_a_chip_waits(self):
        self.b.wait("PULSE.v!=null")
        before = self.b.eval("REV.length")
        self.b.eval("go('cockpit','ABC'); openProject('ABC','health'); 1")    # a form (work items are the peek; BL-186: milestones their editor)
        self.b.eval("const f=document.querySelector('#pFields textarea')||document.querySelector('#pFields .rted'); "
                    "if(f.value!==undefined) f.value='my unsaved words'; else f.textContent='my unsaved words'; "
                    "window.FIELD_ID=f.id||f.name; 1")
        stage_sweep(self.v.root, "Arrived while editing")
        self.b.wait("document.getElementById('newChip').classList.contains('on')", timeout=15)
        self.assertEqual(self.b.eval("REV.length"), before)                    # nothing was reloaded
        self.assertEqual(self.b.eval("EDITING"), True)
        self.assertIn("my unsaved words", self.b.eval(
            "(document.querySelector('#pFields textarea')||document.querySelector('#pFields .rted')).value||"
            "document.querySelector('#pFields .rted').textContent"))
        self.b.eval("document.getElementById('pCancel').click(); 1")           # the edit ends
        self.b.wait(self.review_has("Arrived while editing"), timeout=15)
        self.assertFalse(self.b.eval("document.getElementById('newChip').classList.contains('on')"))

    def test_the_chip_refreshes_when_clicked_and_nothing_is_open(self):
        self.b.wait("PULSE.v!=null")
        self.b.eval("const i=document.createElement('input'); i.id='probeField'; document.body.appendChild(i); i.focus(); 1")
        stage_sweep(self.v.root, "Arrived while typing")
        self.b.wait("document.getElementById('newChip').classList.contains('on')", timeout=15)     # a focused text field holds it back
        self.assertFalse(self.b.eval(self.review_has("Arrived while typing")))
        self.b.eval("document.getElementById('probeField').remove(); 1")
        self.b.click("#newChip")
        self.b.wait(self.review_has("Arrived while typing"), timeout=10)
        self.assertFalse(self.b.eval("document.getElementById('newChip').classList.contains('on')"))

    def test_the_pages_own_reload_takes_a_fresh_fingerprint(self):
        self.b.wait("PULSE.v!=null")
        stage_sweep(self.v.root, "Seen once")
        self.b.wait(self.review_has("Seen once"), timeout=15)
        self.snacks()
        self.b.eval("reloadData(); 1")
        time.sleep(3)                                                          # three more health checks
        self.assertEqual(self.b.eval("SNACKS.length"), 0)                      # no second reload, no second message


class StaticDashboard(unittest.TestCase):
    @unittest.skipUnless(Path("/Applications/Google Chrome.app").exists(), "Google Chrome not installed")
    def test_a_dashboard_opened_as_a_file_never_polls(self):
        from cdp import Browser
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
        v = Vault()
        try:
            populate(v)
            v.run(script="build_dashboard.py")
            b = Browser(1200, 800)
            try:
                b.goto((v.root / "dashboard.html").as_uri())
                b.wait("typeof go==='function'")
                time.sleep(2)
                self.assertEqual(b.eval("SERVED"), False)
                self.assertIsNone(b.eval("PULSE.v"))
                self.assertIsNone(b.eval("PULSE.timer"))
            finally:
                b.close()
        finally:
            v.cleanup()



# ---------------------------------------------------------------- item 3: markdown in the chat (BL-109)
FAKE_CLAUDE = r"""#!/usr/bin/env python3
import json, sys, time
args = sys.argv[1:]
message = args[args.index("--") + 1]
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-md-1"})
text = message[5:] if message.startswith("ECHO:") else "plain reply"
out({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}})
if "SLOW" in message:
    time.sleep(3)                      # the reply has started but not finished
out({"type": "result", "session_id": "sess-md-1", "result": text})
"""


class FakeClaudeCase(LiveBrowserCase):
    """The live server with a stand-in `claude` that answers "ECHO:<text>" with that text (slowly if it says SLOW)."""
    shared_server = True

    @classmethod
    def load(cls, v):
        populate(v)
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE_CLAUDE)
        fake.chmod(0o755)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.v.root / "fake_claude.py")}


class MarkdownChat(FakeClaudeCase):
    def md(self, text):
        return self.b.eval(f"mdChat({json.dumps(text)})")

    def test_every_block_and_inline_form(self):
        cases = {
            "Hello **bold** and *it* and ~~gone~~ and `code` and __strong__ and _em_":
                "<p>Hello <strong>bold</strong> and <em>it</em> and <del>gone</del> and <code>code</code> and <strong>strong</strong> and <em>em</em></p>",
            "first\nsecond": "<p>first<br>second</p>",
            "one\n\ntwo": "<p>one</p><p>two</p>",
            "# One\n## Two\n### Three\n###### Six":
                '<div class="mdh mdh1" role="heading" aria-level="1">One</div><div class="mdh mdh2" role="heading" aria-level="2">Two</div>'
                '<div class="mdh mdh3" role="heading" aria-level="3">Three</div><div class="mdh mdh3" role="heading" aria-level="6">Six</div>',
            "- a\n  - b\n    - c\n- d": "<ul><li>a<ul><li>b<ul><li>c</li></ul></li></ul></li><li>d</li></ul>",
            "1. x\n2. y": "<ol><li>x</li><li>y</li></ol>",
            "3. x\n4. y": '<ol start="3"><li>x</li><li>y</li></ol>',
            "Some text:\n- a\n- b": "<p>Some text:</p><ul><li>a</li><li>b</li></ul>",
            "> quoted *text*\n> more": "<blockquote><p>quoted <em>text</em><br>more</p></blockquote>",
            "above\n\n---\n\nbelow": "<p>above</p><hr><p>below</p>",
            "[site](https://example.com/a?b=1&c=2)": '<p><a href="https://example.com/a?b=1&amp;c=2" target="_blank" rel="noopener">site</a></p>',
            "[mail](mailto:a@b.example)": '<p><a href="mailto:a@b.example" target="_blank" rel="noopener">mail</a></p>',
            "![chart](https://example.com/x.png)": "<p>chart</p>",
            "[![chart](https://example.com/x.png)](https://example.com/page)":
                '<p><a href="https://example.com/page" target="_blank" rel="noopener">chart</a></p>',
            "snake_case_name and 2 * 3 * 4": "<p>snake_case_name and 2 * 3 * 4</p>",
        }
        for text, html in cases.items():
            with self.subTest(text=text):
                self.assertEqual(self.md(text), html)

    def test_code_tables_and_a_wide_list_item(self):
        code = self.md("```python\nx = 1 < 2\n```")
        self.assertIn("<pre><code>x = 1 &lt; 2</code></pre>", code)
        self.assertIn('data-mdcopy', code)
        table = self.md("| A | B |\n|:--|--:|\n| 1 | 2 |\n| 3 | 4 |")
        self.assertIn('<div class="mdtable"><table><thead><tr><th>A</th><th class="ta-r">B</th></tr></thead>', table)
        self.assertIn('<tbody><tr><td>1</td><td class="ta-r">2</td></tr><tr><td>3</td><td class="ta-r">4</td></tr></tbody>', table)
        inside = self.md("1. Run this:\n   ```\n   - not a list\n   ```\n2. Done")
        self.assertIn("<pre><code>- not a list</code></pre>", inside)
        self.assertEqual(inside.count("<li>"), 2)

    def test_half_finished_replies_are_closed_for_display(self):
        fence = self.md("Here is code:\n```js\nlet a = 1;")
        self.assertIn("<pre><code>let a = 1;</code></pre>", fence)
        self.assertEqual(fence.count("<pre>"), 1)
        half = self.md("| A | B |\n|---|---|")
        self.assertIn("<table>", half)
        self.assertNotIn("<tbody><tr>", half)
        self.assertNotIn("<table", self.md("a | b\n1 | 2"))                    # no separator row: plain text
        self.assertEqual(self.md("a | b\n1 | 2"), "<p>a | b<br>1 | 2</p>")

    def test_hostile_replies_stay_inert(self):
        hostile = [
            "<script>window.PWNED=1</script>", "<img src=x onerror=\"window.PWNED=2\">", "[x](javascript:window.PWNED=3)",
            "[x](JaVaScRiPt:window.PWNED=4)", "[x](data:text/html,<script>window.PWNED=5</script>)", "[x](file:///etc/passwd)",
            "[x](https://a.example\" onmouseover=\"window.PWNED=6)", "[x](https://a.example/ onclick=window.PWNED=7)",
            "![x](javascript:window.PWNED=8)", "**<b onmouseover=window.PWNED=9>hi</b>**", "`<script>window.PWNED=10</script>`",
            "```\n</code></pre><script>window.PWNED=11</script>\n```", "| <img src=x onerror=window.PWNED=12> |\n|---|\n| <i>a</i> |",
            "> <iframe src=javascript:window.PWNED=13>", "# <svg onload=window.PWNED=14>", "- <a href=javascript:window.PWNED=15>x</a>",
        ]
        r = self.b.eval("""(()=>{ const out=[]; for(const t of %s){ const d=addEl("msg a md",mdChat(t));
            out.push({t, scripts:d.querySelectorAll("script,img,iframe,svg,object,embed,style,form,input").length,
              on:[...d.querySelectorAll("*")].flatMap(e=>[...e.attributes].map(a=>a.name)).filter(n=>n.startsWith("on")),
              hrefs:[...d.querySelectorAll("a")].map(a=>a.getAttribute("href")),
              others:[...d.querySelectorAll("*")].flatMap(e=>[...e.attributes].map(a=>a.name)).filter(n=>!["href","target","rel","class","role","aria-level","type","data-mdcopy","aria-label","data-mdfile","data-mditem","start"].includes(n))}); }
            return out; })()""" % json.dumps(hostile))
        for x in r:
            with self.subTest(x["t"]):
                self.assertEqual(x["scripts"], 0)
                self.assertEqual(x["on"], [])
                self.assertEqual(x["others"], [])
                self.assertTrue(all(h.startswith(("https://", "http://", "mailto:")) for h in x["hrefs"]), x["hrefs"])
        time.sleep(0.3)
        self.assertIsNone(self.b.eval("window.PWNED"))
        self.assertIn("&lt;script&gt;", self.md("<script>x</script>"))
        self.assertIn("[x](javascript:", self.b.eval("addEl('msg a md', mdChat('[x](javascript:alert(1))')).textContent"))   # the text stays visible

    def test_a_very_long_unbroken_word_stays_inside_the_bubble(self):
        r = self.b.eval("""(()=>{ const t0=performance.now(); const d=addEl("msg a md",mdChat("A"+"x".repeat(10000)+"\\n\\n**"+"y".repeat(5000)));
            const ms=performance.now()-t0, log=document.getElementById("chLog").getBoundingClientRect(), b=d.getBoundingClientRect();
            return {ms, inside:b.right<=log.right+1&&b.left>=log.left-1}; })()""")
        self.assertLess(r["ms"], 2000)
        self.assertTrue(r["inside"])

    def test_item_ids_and_files_link_and_nothing_else_does(self):
        known = self.b.eval("A[0].id")
        files = self.b.eval("FILES.filter(f=>f.path).map(f=>f.path)")
        text = f"See {known} and ABC-A-999 and `{known}`."
        html = self.md(text)
        self.assertIn(f'<a href="#" class="mdref" data-mditem="{known}">{known}</a>', html)
        self.assertIn(f'<a href="#" class="mdref" data-mditem="{known}"><code>{known}</code></a>', html)
        self.assertNotIn('data-mditem="ABC-A-999"', html)                    # an ID that isn't in the tracker stays text
        if files:
            path = files[0]
            self.assertIn(f'data-mdfile="{path}"', self.md(f"Open {path} now"))
        self.assertNotIn("data-mdfile", self.md("Open projects/Nowhere/Unknown file.docx now"))
        self.assertNotIn("data-mdfile", self.md("Open /etc/passwd or inbox/../../secret.txt"))

    def test_a_reply_loaded_from_history_looks_like_the_live_one(self):
        known = self.b.eval("A[0].id")
        reply = (f"# Summary\n\nTwo things on **{known}**:\n\n- first, with `code`\n- second, see [docs](https://example.com)\n\n"
                 "| Who | What |\n|---|---|\n| Omar | SOW |\n\n```\nplain code\n```\n\n> a quote\n")
        self.b.eval(f"openChat(); send({json.dumps('ECHO:' + reply)}); 1")
        # BL-148: each reply's Copy button is added a frame after it is drawn (a MutationObserver, then requestAnimationFrame),
        # live and from history alike; read each reply once it has its button, or a slower runner reads it a frame early
        last = "[...document.querySelectorAll('#chLog .msg.a.md')].pop()"
        self.b.wait(f"!BUSY && document.querySelectorAll('#chLog .msg.a.md').length>=1 && !!{last}.querySelector(':scope>.msgcopy')", timeout=30)
        live = self.b.eval("[...document.querySelectorAll('#chLog .msg.a.md')].pop().innerHTML")
        mine = self.b.eval("[...document.querySelectorAll('#chLog .msg.u')].pop().textContent")
        self.assertTrue(mine.startswith("ECHO:"))
        self.assertIn("<strong>", live)
        self.assertIn("<table>", live)
        self.b.eval("loadChat(ASKCHAT).then(()=>1)")                     # waits for the history to be drawn, so the live reply is gone
        self.b.wait(f"document.querySelectorAll('#chLog .msg.a.md').length>=1 && !!{last}.querySelector(':scope>.msgcopy')", timeout=15)
        history = self.b.eval("[...document.querySelectorAll('#chLog .msg.a.md')].pop().innerHTML")
        self.assertEqual(history, live)
        # Alan's own bubble is plain text: escaped, no markdown, line breaks kept by pre-wrap
        self.assertEqual(self.b.eval("getComputedStyle([...document.querySelectorAll('#chLog .msg.u')].pop()).whiteSpace"), "pre-wrap")
        self.assertEqual(self.b.eval("[...document.querySelectorAll('#chLog .msg.u')].pop().querySelectorAll('strong,table,ul,h1').length"), 0)

    def test_the_greeting_and_notices_stay_plain(self):
        self.b.eval("newChat(); 1")
        self.b.wait("document.querySelector('#chLog .msg.a')")
        self.assertEqual(self.b.eval("document.querySelector('#chLog .msg.a').classList.contains('md')"), False)
        self.assertEqual(self.b.eval("getComputedStyle(document.querySelector('#chLog .msg.a')).whiteSpace"), "pre-wrap")
        self.assertEqual(self.b.eval("getComputedStyle(addEl('msg a md','<p>x</p>')).whiteSpace"), "normal")

    def test_the_copy_button_copies_the_code(self):
        self.b.eval("""window.COPIED=null; Object.defineProperty(navigator,'clipboard',{value:{writeText:t=>{ window.COPIED=t; return Promise.resolve(); }},configurable:true});
          openChat(); addEl('msg a md', mdChat('```\\nline 1 <b>\\nline 2\\n```')); 1""")
        self.b.click("#chLog .mdcopy")
        self.b.wait("window.COPIED!==null")
        self.assertEqual(self.b.eval("window.COPIED"), "line 1 <b>\nline 2")

    def test_every_theme_keeps_the_text_readable(self):
        self.b.eval("openChat(); addEl('msg a md', mdChat('Text with [a link](https://example.com) and `code`\\n\\n> quote\\n\\n| A |\\n|---|\\n| 1 |')); 1")
        def lum(rgb):
            c = [x / 255 for x in rgb]
            c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
            return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
        for theme in ("light", "dark"):
            self.b.eval(f"document.documentElement.dataset.theme={theme!r}; 1")
            r = self.b.eval("""(()=>{ const m=[...document.querySelectorAll('#chLog .msg.a.md')].pop(), rgb=s=>(s.match(/[\\d.]+/g)||[]).slice(0,3).map(Number), bg=rgb(getComputedStyle(m).backgroundColor);
              return {bg, link:rgb(getComputedStyle(m.querySelector('a')).color), quote:rgb(getComputedStyle(m.querySelector('blockquote')).color), ink:rgb(getComputedStyle(m).color)}; })()""")
            for part in ("link", "quote", "ink"):
                hi, lo = sorted((lum(r[part]), lum(r["bg"])), reverse=True)
                self.assertGreaterEqual((hi + 0.05) / (lo + 0.05), 3.0, f"{theme} {part}: {r}")



# ---------------------------------------------------------------- item 4: times on the bubbles (BL-108)
from datetime import datetime, timedelta  # noqa: E402


class ChatTimes(FakeClaudeCase):
    def chat_files(self):
        return sorted((self.v.root / "system/staging/ask").glob("*.json"))

    def write_chat(self, name, messages, started):
        d = self.v.root / "system/staging/ask"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{name}.json").write_text(json.dumps({"chat": name, "title": "Old chat", "started": started, "updated": started,
                                                    "session": name, "messages": messages}))

    def test_a_live_exchange_is_stamped_and_stored_with_its_times(self):
        before = datetime.now().replace(microsecond=0)
        self.b.eval("openChat(); send('ECHO:SLOW times please'); 1")
        self.b.wait("document.querySelector('#chLog .msg.a.md')", timeout=30)
        # the reply has started and is still being written: Alan's bubble has its time, the reply has none yet
        self.assertEqual(self.b.eval("[...document.querySelectorAll('#chLog .msg.u')].pop().nextElementSibling.tagName"), "TIME")
        self.assertEqual(self.b.eval("!!document.querySelector('#chLog .msg.a.md').nextElementSibling?.matches('time')"), False)
        self.b.wait("!BUSY && document.querySelector('#chLog .msg.a.md').nextElementSibling?.matches('time.mtime.a')", timeout=30)
        after = datetime.now().replace(microsecond=0)
        times = self.b.eval("[...document.querySelectorAll('#chLog time.mtime')].map(t=>({cls:t.className,dt:t.dateTime,title:t.title,text:t.textContent}))")
        self.assertEqual([t["cls"] for t in times], ["mtime u", "mtime a"])
        sent, done = (datetime.fromisoformat(t["dt"]) for t in times)
        self.assertTrue(before - timedelta(seconds=1) <= sent <= done <= after + timedelta(seconds=1))
        self.assertGreaterEqual((done - sent).total_seconds(), 2)                   # the reply's time is when it finished
        for t, when in zip(times, (sent, done)):
            self.assertEqual(t["text"], when.strftime("%H:%M"))                      # today: just the time
            self.assertEqual(t["title"], when.strftime("%d-%m-%Y %H:%M:%S"))          # hover: the whole date and time
        # a chat with one day has no divider
        self.assertEqual(self.b.eval("document.querySelectorAll('#chLog .mday').length"), 0)
        # stored: at on both, done_at on the reply, and the reply's at is when it started (kept on the later update)
        rec = json.loads(self.chat_files()[-1].read_text())
        you, reply = rec["messages"][-2:]
        self.assertEqual((you["who"], reply["who"]), ("you", "creaite"))
        self.assertNotIn("done_at", you)
        s, a, d = (datetime.fromisoformat(x) for x in (you["at"], reply["at"], reply["done_at"]))
        self.assertTrue(s <= a < d)
        self.assertGreaterEqual((d - a).total_seconds(), 2)
        shown = self.b.eval("[...document.querySelectorAll('#chLog time.mtime')].map(t=>t.dateTime)")
        self.assertEqual(shown[1], reply["done_at"])
        # Alan's bubble is stamped by the page when he sends; the server stamps the same message when it arrives, which on a loaded
        # machine can be a second or more later. Never earlier, and never far.
        gap = (datetime.fromisoformat(you["at"]) - datetime.fromisoformat(shown[0])).total_seconds()
        self.assertTrue(0 <= gap <= 5, f"the page stamped {shown[0]}, the server {you['at']}")

    def test_a_reloaded_chat_over_two_days_shows_earlier_times_and_dividers(self):
        today, yesterday = datetime.now().date(), datetime.now().date() - timedelta(days=1)
        y, t = yesterday.isoformat(), today.isoformat()
        self.write_chat("chat-two-days", [
            {"who": "you", "text": "Yesterday question", "at": f"{y}T14:32:05"},
            {"who": "creaite", "text": "Yesterday answer", "steps": [], "at": f"{y}T14:32:09", "done_at": f"{y}T14:32:41"},
            {"who": "you", "text": "Today question", "at": f"{t}T08:05:00"},
            {"who": "creaite", "text": "Today answer", "steps": ["Looked at the tracker"], "at": f"{t}T08:05:02", "done_at": f"{t}T08:05:30"},
        ], f"{y}T14:32:05")
        self.b.eval("openChat(); loadChat('chat-two-days'); 1")
        self.b.wait("document.querySelectorAll('#chLog time.mtime').length===4", timeout=15)
        r = self.b.eval("""[...document.getElementById('chLog').children].map(e=>e.matches('.mday')?'D:'+e.textContent:e.matches('time')?'T:'+e.textContent+'|'+e.title+'|'+e.dateTime:e.matches('.msg')?'M:'+e.className.split(' ')[1]:'S')""")
        dd = lambda d: d.strftime("%d-%m")
        self.assertEqual(r, [
            "D:Yesterday", "M:u", f"T:{dd(yesterday)} 14:32|{yesterday:%d-%m-%Y} 14:32:05|{y}T14:32:05",
            "M:a", f"T:{dd(yesterday)} 14:32|{yesterday:%d-%m-%Y} 14:32:41|{y}T14:32:41",
            "D:Today", "M:u", f"T:08:05|{today:%d-%m-%Y} 08:05:00|{t}T08:05:00",
            "S", "M:a", f"T:08:05|{today:%d-%m-%Y} 08:05:30|{t}T08:05:30"])

    def test_a_day_before_yesterday_is_named_by_its_date(self):
        old = datetime.now().date() - timedelta(days=5)
        self.write_chat("chat-older", [
            {"who": "you", "text": "Q", "at": f"{old}T09:00:00"}, {"who": "creaite", "text": "A", "steps": [], "at": f"{old}T09:00:01", "done_at": f"{old}T09:00:09"},
            {"who": "you", "text": "Q2", "at": f"{datetime.now().date()}T09:00:00"}], f"{old}T09:00:00")
        self.b.eval("openChat(); loadChat('chat-older'); 1")
        self.b.wait("document.querySelectorAll('#chLog time.mtime').length===3", timeout=15)
        self.assertEqual(self.b.eval("[...document.querySelectorAll('#chLog .mday')].map(e=>e.textContent)"), [f"{old:%d-%m-%Y}", "Today"])

    def test_a_chat_saved_before_the_times_existed_shows_none_per_bubble(self):
        started = (datetime.now() - timedelta(days=3)).replace(microsecond=0).isoformat()
        self.write_chat("chat-before", [{"who": "you", "text": "Old question"}, {"who": "creaite", "text": "Old answer", "steps": []}], started)
        self.b.eval("openChat(); loadChat('chat-before'); 1")
        self.b.wait("document.querySelectorAll('#chLog .msg').length===2", timeout=15)
        self.assertEqual(self.b.eval("document.querySelectorAll('#chLog time').length"), 0)                    # nothing invented
        self.assertEqual(self.b.eval("[...document.querySelectorAll('#chLog .mday')].map(e=>e.textContent)"), [f"{started[8:10]}-{started[5:7]}-{started[:4]}"])
        # carrying on today adds a time to the new bubbles and a Today divider
        self.b.eval("send('ECHO:carry on'); 1")
        self.b.wait("!BUSY && document.querySelectorAll('#chLog time.mtime').length===2", timeout=30)
        self.assertEqual(self.b.eval("[...document.querySelectorAll('#chLog .mday')].map(e=>e.textContent)")[1], "Today")

    def test_steps_confirm_cards_and_the_greeting_carry_no_time(self):
        self.b.eval("newChat(); 1")
        self.b.wait("document.querySelector('#chLog .msg.a')")
        self.b.eval("addEl('step','✓ Looked'); confirmCard('Do it','Really?','Go ahead'); 1")
        self.assertEqual(self.b.eval("document.querySelectorAll('#chLog time').length"), 0)


if __name__ == "__main__":
    unittest.main()
