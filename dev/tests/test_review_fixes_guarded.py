"""v2.6 review fixes in guarded files (/code-review high on origin/v253-release): the diffs in dev/proposals/review-fixes/.

Run: python3 dev/tests/test_review_fixes_guarded.py      (quick tier: no Chrome; one live server, no Claude)

- (4) POST /api/intake/process refuses another site's request (a cross-site fetch, a foreign Origin) with a 403, as
  /api/calendar/refresh does; the page's own Origin, and no Origin, still reach the request's own checks.
- (6) reach._RunLock closes its lock file when the lock itself fails: no file descriptor is left open.
- (9) a background thread's fault is counted once a minute by its thread name and its cause, so one thread's fault never keeps a
  different fault of another thread (even one with the same name) out of the log.

Each part skips until its diff is applied (the marker it adds is how the test knows); with the diffs applied (in a scratch copy:
git apply dev/proposals/review-fixes/*.diff) every test passes. Everything is fictional and temporary.
"""
import json
import os
import re
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_tracker import REPO, Vault  # noqa: E402

LIVE = (REPO / "system/scripts/live_server.py").read_text(encoding="utf-8")
REACH = (REPO / "system/scripts/reach.py").read_text(encoding="utf-8")
FIX4 = "review-fixes (4)" in LIVE
FIX6 = "review-fixes (6)" in REACH
FIX9 = "review-fixes (9)" in LIVE
DIFFS = "dev/proposals/review-fixes/"


def log_text(root):
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted((root / "system/logs").glob("debug-*.log")))


@unittest.skipUnless(FIX4, f"live_server.diff in {DIFFS} is not applied")
class IntakeProcessOrigin(unittest.TestCase):
    """(4) the route's own same-origin check, through a real live server."""

    @classmethod
    def setUpClass(cls):
        from test_dashboard import populate
        from test_live_server import free_port
        cls.v = v = Vault()
        populate(v)
        cfg = v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text(encoding="utf-8"))
        data.setdefault("backups", {})["daily"] = False
        cfg.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], cwd=v.root,
                                    env={**os.environ, "CREAITE_PORT": str(cls.port), "CREAITE_CLAUDE": "/nonexistent"},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(300):
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

    def post(self, path, body, headers=None):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token, **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            with e:
                return e.code, json.loads(e.read() or b"{}")

    def test_another_sites_request_is_refused_before_anything_else(self):
        body = {"files": ["projects/elsewhere.vtt"]}            # refused by the request's own checks (400) once past the origin
        for headers in ({"Origin": "https://evil.example"}, {"Sec-Fetch-Site": "cross-site"},
                        {"Origin": "http://evil.example"}, {"Origin": "null"}):
            with self.subTest(headers=headers):
                status, got = self.post("/api/intake/process", body, headers)
                self.assertEqual(status, 403, got)
        for headers in ({"Origin": self.base}, {}, {"Sec-Fetch-Site": "same-origin"}):
            with self.subTest(headers=headers):
                status, got = self.post("/api/intake/process", body, headers)
                self.assertEqual(status, 400, got)                   # the page's own request reaches validate_request
                self.assertIn("only files in Intake", got["message"])


@unittest.skipUnless(FIX6, f"reach.diff in {DIFFS} is not applied")
class RunLockFd(unittest.TestCase):
    """(6) a lock that fails closes its file."""

    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.cleanup)

    def test_a_failed_lock_leaves_no_file_open(self):
        code = ("import os, sys, json, fcntl; sys.path.insert(0, 'system/scripts'); import reach\n"
                "def fail(fd, op):\n    raise OSError(4, 'Interrupted system call')\n"
                "real = fcntl.flock\nfcntl.flock = fail\nbefore = len(os.listdir('/dev/fd'))\nrefused = 0\n"
                "for _ in range(40):\n    try:\n        reach._RunLock().__enter__()\n    except OSError:\n        refused += 1\n"
                "after = len(os.listdir('/dev/fd'))\nfcntl.flock = real\n"
                "with reach._RunLock() as lk:\n    held = lk.fd is not None\n"
                "print(json.dumps([refused, after - before, held, lk.fd]))\n")
        r = subprocess.run([sys.executable, "-c", code], cwd=self.v.root, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout.strip().splitlines()[-1]), [40, 0, True, None])


@unittest.skipUnless(FIX9, f"live_server.diff in {DIFFS} is not applied")
class ThreadFaultKey(unittest.TestCase):
    """(9) one thread's fault never keeps another's out of the log."""

    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.cleanup)

    def test_each_threads_own_fault_is_logged(self):
        code = ("import sys, threading; sys.path.insert(0, 'system/scripts'); import live_server\n"
                "def boom():\n    raise RuntimeError('CANARY-ONE')\n"
                "def bust():\n    raise KeyError('CANARY-TWO')\n"
                "for target in (boom, boom, bust):\n"
                "    t = threading.Thread(target=target, name='canary-worker'); t.start(); t.join()\n"
                "t = threading.Thread(target=boom, name='other-worker'); t.start(); t.join()\n")
        r = subprocess.run([sys.executable, "-c", code], cwd=self.v.root, capture_output=True, text=True, timeout=120,
                           env={**os.environ, "CREAITE_PORT": "1"})
        self.assertIn("CANARY-ONE", r.stderr)
        text = ""
        for _ in range(100):
            text = log_text(self.v.root)
            if "other-worker raised" in text:
                break
            time.sleep(0.1)
        self.assertEqual(len(re.findall(r"thread canary-worker raised RuntimeError at <string>:\d+ in boom", text)), 1, text)
        self.assertEqual(len(re.findall(r"thread canary-worker raised KeyError at <string>:\d+ in bust", text)), 1, text)
        self.assertEqual(len(re.findall(r"thread other-worker raised RuntimeError", text)), 1, text)
        self.assertNotIn("CANARY", text)

    def test_the_remembered_keys_stay_bounded(self):
        code = ("import sys, json; sys.path.insert(0, 'system/scripts'); import live_server\n"
                "for n in range(live_server.FAULT_KEEP + 50):\n"
                "    live_server.log_cause('thread t', RuntimeError(), seen=f'k{n}')\n"
                "print(json.dumps([len(live_server.FAULT_SEEN), 'k0' in live_server.FAULT_SEEN]))\n")
        r = subprocess.run([sys.executable, "-c", code], cwd=self.v.root, capture_output=True, text=True, timeout=120,
                           env={**os.environ, "CREAITE_PORT": "1"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout.strip().splitlines()[-1]), [500, False])     # the oldest go first


if __name__ == "__main__":
    unittest.main(verbosity=2)
