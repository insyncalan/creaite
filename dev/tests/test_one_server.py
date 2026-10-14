"""BL-329: two quick launches give one server and one window; a second server for this vault exits 0, "already running".

Run: python3 dev/tests/test_one_server.py
Real servers on free ports in throwaway vaults, made slow to start with CREAITE_START_DELAY (tests only), and a stub browser.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import free_port  # noqa: E402
from test_tracker import Vault  # noqa: E402

STUB_BROWSER = '#!/bin/bash\necho "$@" >> "{log}"\n'


def alive(port):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1)
        return True
    except OSError:
        return False


def wait_until(fn, seconds=20, every=0.2):
    end = time.time() + seconds
    while time.time() < end:
        if fn():
            return True
        time.sleep(every)
    return False


class OneServerTests(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.port = free_port()
        self.log = self.v.root / "browser.log"
        stub = self.v.root / "stub-browser.sh"
        stub.write_text(STUB_BROWSER.format(log=self.log))
        stub.chmod(0o755)
        self.env = {**os.environ, "CREAITE_PORT": str(self.port), "CREAITE_BROWSER": str(stub), "CREAITE_STOP_AFTER": "30"}
        self.staging = self.v.root / "system" / "staging"
        self.procs = []

    def tearDown(self):
        for pid in self.listeners():                       # only the servers on this test's own port
            try:
                os.kill(int(pid), 15)
            except OSError:
                pass
        for p in self.procs:
            if p.poll() is None:
                p.terminate()
                p.wait(timeout=10)
            if p.stdout:
                p.stdout.close()
        wait_until(lambda: not self.listeners(), 10)
        self.v.cleanup()

    def listeners(self):
        r = subprocess.run(["lsof", "-ti", f"tcp:{self.port}", "-sTCP:LISTEN"], capture_output=True, text=True)
        return r.stdout.split()

    def launch(self):
        return subprocess.Popen([sys.executable, str(self.v.root / "system/scripts/launch.py")], cwd=tempfile.gettempdir(),
                                env=self.env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    def server(self, **env):
        p = subprocess.Popen([sys.executable, str(self.v.root / "system/scripts/live_server.py")], cwd=tempfile.gettempdir(),
                             env={**self.env, **env}, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.procs.append(p)
        return p

    def debug_log(self):
        logs = self.v.root / "system" / "logs"
        return "".join(f.read_text(encoding="utf-8") for f in sorted(logs.glob("debug-*.log"))) if logs.is_dir() else ""

    def test_two_quick_launches_give_one_server_and_one_window(self):
        self.env["CREAITE_START_DELAY"] = "4"                  # holds the port, but doesn't answer /health for 4 s
        first = self.launch()
        mark = self.staging / "live-server-starting.json"
        self.assertTrue(wait_until(lambda: mark.exists(), 15), "the starting server writes its mark")
        rec = json.loads(mark.read_text())
        self.assertEqual(rec["port"], self.port)
        self.assertTrue(rec["launched"])
        self.assertFalse(alive(self.port))                     # still starting
        second = self.launch()
        out2, _ = second.communicate(timeout=60)
        out1, _ = first.communicate(timeout=60)
        first.stdout.close()
        second.stdout.close()
        self.assertEqual(first.returncode, 0, out1)
        self.assertEqual(second.returncode, 0, out2)
        self.assertIn("Starting the live server", out1)
        self.assertIn("is starting", out2)
        self.assertNotIn("Starting the live server", out2)
        self.assertEqual(len(self.listeners()), 1)
        self.assertTrue(wait_until(lambda: self.log.exists(), 15))   # the stub browser runs a moment after the launcher returns
        time.sleep(2)                                          # time for a second window, were one opened
        self.assertEqual(self.log.read_text().splitlines(), [f"--app=http://127.0.0.1:{self.port}/"])   # one window
        self.assertTrue(wait_until(lambda: not mark.exists(), 10), "the mark goes once /health answers")
        self.assertNotRegex(self.debug_log(), r"live_server.*exit 1")

    def test_a_second_server_for_this_vault_says_already_running_and_exits_0(self):
        first = self.server()
        self.assertTrue(wait_until(lambda: alive(self.port)))
        info = json.loads((self.staging / "live-server.json").read_text())
        self.assertEqual(info["pid"], first.pid)
        second = self.server()
        out, _ = second.communicate(timeout=60)
        self.assertEqual(second.returncode, 0, out)
        self.assertIn("already running", out)
        self.assertEqual(self.listeners(), [str(first.pid)])
        self.assertEqual(json.loads((self.staging / "live-server.json").read_text())["pid"], first.pid)   # not overwritten
        log = self.debug_log()
        self.assertRegex(log, r"INFO.*already running on port")
        self.assertNotRegex(log, r"WARN.*exit 1")

    def test_a_second_server_while_the_first_is_still_starting_exits_0(self):
        first = self.server(CREAITE_START_DELAY="4")
        mark = self.staging / "live-server-starting.json"
        self.assertTrue(wait_until(lambda: mark.exists(), 15))
        second = self.server()
        out, _ = second.communicate(timeout=60)
        self.assertEqual(second.returncode, 0, out)
        self.assertIn("already running", out)
        self.assertEqual(self.listeners(), [str(first.pid)])

    def test_a_mark_left_by_a_server_that_has_gone_is_ignored(self):
        self.staging.mkdir(parents=True, exist_ok=True)
        (self.staging / "live-server-starting.json").write_text(json.dumps({"pid": 999999, "port": self.port, "launched": True}))
        p = self.launch()
        out, _ = p.communicate(timeout=60)
        p.stdout.close()
        self.assertEqual(p.returncode, 0, out)
        self.assertIn("Starting the live server", out)
        self.assertTrue(alive(self.port))


if __name__ == "__main__":
    unittest.main()
