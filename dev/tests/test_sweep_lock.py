"""BL-328: a sweep's lock never outlives the sweep.

The lock records the live server's run (CREAITE_RUN_ID); the server releases it when that run ends, however it ends (finished,
stopped, timed out), and when the server stops (only a lock its own runs hold). A lock held with no sweep running is replaced by
the next sweep at once, shows in doctor and Settings › Health, and Health's Release (sweep.py unlock --if-idle) removes it,
never a running sweep's.

Each run test starts the real Run with a stand-in `claude` (CREAITE_CLAUDE) that takes the lock exactly as cx-sweep does, inside
a throwaway vault. The shutdown test runs the real live server and stops it with SIGTERM, as launchd or kill would.

Run: python3 dev/tests/test_sweep_lock.py     (quick tier: no Chrome)
"""
import json
import os
import subprocess
import sys
import threading
import time
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_live_server import free_port  # noqa: E402
from test_tracker import Vault  # noqa: E402

# The stand-in claude: takes the sweep lock with the run's own environment, says one thing, then finishes or waits to be ended.
FAKE = r'''#!/usr/bin/env python3
import json, subprocess, sys, time
from pathlib import Path
here = Path(__file__).resolve().parent
subprocess.run([sys.executable, str(here / "system/scripts/sweep.py"), "lock"], cwd=here, capture_output=True)
print(json.dumps({"type": "system", "subtype": "init", "session_id": "s-1"}), flush=True)
print(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Sweeping."}]}}), flush=True)
if (here / "fake_mode").read_text().strip() == "hang":
    time.sleep(300)
time.sleep(1)                       # a real sweep holds the lock for a while: long enough for the harness to see it
print(json.dumps({"type": "result", "session_id": "s-1", "result": "Swept: 0 items staged for Review."}), flush=True)
'''

# One real Run in its own process: start it, wait for the lock, end it as the scenario says, and report what was left.
HARNESS = r'''
import json, sys, time
sys.path.insert(0, "system/scripts")
import live_server as L
import sweep
how = sys.argv[1]
run = L.Run("s-test0001", "sweep", None, None, None, kind="sweep", label="Catch-up sweep")
for _ in range(200):
    if sweep.LOCK.exists() or run.done:
        break
    time.sleep(0.05)
held = sweep.lock_info()
state = sweep.lock_state()
if how == "stop":
    run.request_stop()
for _ in range(400):
    if run.done:
        break
    time.sleep(0.05)
print(json.dumps({"held_run": held and held["run"], "server": held and held["server"], "state": state, "done": run.done,
                  "left": sweep.LOCK.exists(), "events": [e["type"] for e in run.events]}))
'''


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.fake = self.v.root / "fake_claude.py"
        self.fake.write_text(FAKE)
        self.fake.chmod(0o755)
        self.lock = self.v.root / "system/staging/sweep.lock"

    def tearDown(self):
        self.v.cleanup()

    def mode(self, m):
        (self.v.root / "fake_mode").write_text(m)

    def settings(self, **assistant):
        p = self.v.root / "system/config/settings.json"
        s = json.loads(p.read_text(encoding="utf-8"))
        s.setdefault("assistant", {}).update(assistant)
        p.write_text(json.dumps(s, indent=2), encoding="utf-8")

    def sweep(self, *args, env=None):
        return subprocess.run([sys.executable, str(self.v.root / "system/scripts/sweep.py"), *args], cwd=self.v.root,
                              capture_output=True, text=True, env={**os.environ, **(env or {})})

    def doctor(self):
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/doctor.py"), "--read-only", "--json"],
                           cwd=self.v.root, capture_output=True, text=True)
        out = json.loads([ln for ln in r.stdout.splitlines() if ln.startswith("{")][-1])
        return next(c for c in out["checks"] if c["id"] == "sweep_lock")

    def run_harness(self, how):
        env = {**os.environ, "CREAITE_CLAUDE": str(self.fake)}
        env.pop("CREAITE_RUN_ID", None)
        r = subprocess.run([sys.executable, "-c", HARNESS, how], cwd=self.v.root, capture_output=True, text=True, env=env,
                           timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])


class RunEnds(Base):
    """However a sweep run ends, it leaves no lock."""

    def test_a_finished_sweep_leaves_no_lock(self):
        self.mode("finish")
        got = self.run_harness("finish")
        self.assertEqual(got["held_run"], "s-test0001")              # the lock named its run, and its server
        self.assertTrue(got["server"])
        self.assertTrue(got["done"])
        self.assertFalse(got["left"])

    def test_stopping_a_sweep_leaves_no_lock(self):
        self.mode("hang")
        got = self.run_harness("stop")
        self.assertEqual(got["held_run"], "s-test0001")
        self.assertEqual(got["state"], "running")                     # while it ran, it was a running sweep
        self.assertIn("stopped", got["events"])
        self.assertFalse(got["left"])

    def test_a_sweep_that_times_out_leaves_no_lock(self):
        self.mode("hang")
        self.settings(run_timeout_minutes=0.05)                       # 3 seconds, and nobody watching
        got = self.run_harness("wait")
        self.assertEqual(got["held_run"], "s-test0001")
        self.assertIn("stopped", got["events"])
        self.assertFalse(got["left"])


class ServerStops(Base):
    """Stopping the live server releases the lock its own run holds."""

    def test_sigterm_releases_the_servers_own_lock(self):
        self.mode("hang")
        port = free_port()
        base = f"http://127.0.0.1:{port}"
        proc = subprocess.Popen([sys.executable, str(self.v.root / "system/scripts/live_server.py")], cwd=self.v.root,
                                env={**os.environ, "CREAITE_PORT": str(port), "CREAITE_CLAUDE": str(self.fake)},
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(100):
                try:
                    urllib.request.urlopen(base + "/health", timeout=1)
                    break
                except OSError:
                    time.sleep(0.1)
            html = urllib.request.urlopen(base + "/").read().decode()
            import re
            token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]
            req = urllib.request.Request(base + "/api/ask", data=json.dumps({"message": "sweep"}).encode(), method="POST",
                                         headers={"Content-Type": "application/json", "X-Creaite-Token": token})

            def follow():
                try:
                    with urllib.request.urlopen(req, timeout=60) as r:
                        r.read()
                except OSError:
                    pass
            threading.Thread(target=follow, daemon=True).start()
            for _ in range(200):
                if self.lock.exists():
                    break
                time.sleep(0.05)
            self.assertTrue(self.lock.exists(), "the sweep took its lock")
            self.assertIn(f"server {proc.pid}", self.lock.read_text())
            proc.terminate()                                          # SIGTERM
            proc.wait(timeout=30)
            self.assertFalse(self.lock.exists(), "the server released its run's lock on the way out")
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=10)

    def test_a_lock_another_run_holds_is_not_the_servers_to_release(self):
        sys.path.insert(0, str(self.v.root / "system/scripts"))
        r = subprocess.run([sys.executable, "-c", (
            "import sys; sys.path.insert(0, 'system/scripts'); import live_server as L, sweep;"
            "sweep.LOCK.write_text('2026-10-14 08:39\\nrun s-other001\\nserver 1\\n');"
            "print(L.release_sweep_lock(['s-mine0001'], 'ended'), sweep.LOCK.exists())")],
            cwd=self.v.root, capture_output=True, text=True)
        self.assertEqual(r.stdout.split(), ["False", "True"], r.stderr)


class HeldWithNoSweep(Base):
    """A lock left by an ended sweep: replaced by the next sweep, shown by doctor and Health, released by Release."""

    def leave(self, run="s-gone0001", server=None, at="2026-10-14 08:39"):
        self.lock.write_text(f"{at}\nrun {run}\n" + (f"server {server}\n" if server else ""))

    def test_the_next_sweep_replaces_it_at_once(self):
        self.leave()
        r = self.sweep("lock", env={"CREAITE_NOW": "2026-10-14 08:50"})       # 11 minutes on: before, refused
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("ended", r.stdout)

    def test_a_running_sweeps_lock_still_refuses_another(self):
        self.leave(run="s-live0001", server=os.getpid())
        guard = self.v.root / "system/guard/run.json"
        guard.parent.mkdir(parents=True, exist_ok=True)
        guard.write_text(json.dumps({"run": "s-live0001", "mode": "sweep", "marked": []}))
        r = self.sweep("lock", env={"CREAITE_NOW": "2026-10-14 08:50"})
        self.assertEqual(r.returncode, 3, r.stdout)
        r = self.sweep("unlock", "--if-idle", env={"CREAITE_NOW": "2026-10-14 08:50"})
        self.assertEqual(r.returncode, 3)                                    # Release never ends a running sweep
        self.assertTrue(self.lock.exists())
        self.assertTrue(self.doctor()["status"] == "pass")
        self.assertIn("a sweep is running", self.doctor()["detail"])

    def test_a_dead_servers_lock_is_held_with_no_sweep(self):
        dead = subprocess.Popen([sys.executable, "-c", "pass"])
        dead.wait()
        self.leave(run="s-live0001", server=dead.pid)
        guard = self.v.root / "system/guard/run.json"
        guard.parent.mkdir(parents=True, exist_ok=True)
        guard.write_text(json.dumps({"run": "s-live0001", "mode": "sweep", "marked": []}))    # left by a server that died
        self.assertEqual(self.doctor()["status"], "warn")

    def test_doctor_and_health_show_it_with_release(self):
        self.leave()
        c = self.doctor()
        self.assertEqual(c["status"], "warn")
        self.assertIn("no sweep running", c["detail"])
        self.assertIn("14-10-2026 08:39", c["detail"])                      # DD-MM-YYYY on screen
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system/scripts"))
        import health
        h = health.health({"checks": [c]})
        p = h["problems"][0]
        self.assertEqual(p["title"], "A mail and Teams check looks stuck")
        self.assertTrue(p["fix"]["built"])
        self.assertEqual(p["fix"]["button"], "Clear it")
        self.assertEqual(p["fix"]["command"], "system/scripts/run sweep.py unlock --if-idle")

    def test_release_removes_it(self):
        self.leave()
        r = self.sweep("unlock", "--if-idle")
        self.assertEqual(r.returncode, 0)
        self.assertFalse(self.lock.exists())
        self.assertEqual(self.doctor()["status"], "pass")
        self.assertEqual(self.sweep("unlock", "--if-idle").returncode, 0)     # nothing held: nothing to do

    def test_a_sweep_from_claude_code_keeps_the_thirty_minute_rule(self):
        self.lock.write_text("2026-10-14 08:39\n")                             # no run: a Terminal sweep
        self.assertEqual(self.sweep("lock", env={"CREAITE_NOW": "2026-10-14 08:50"}).returncode, 3)
        self.assertEqual(self.sweep("lock", env={"CREAITE_NOW": "2026-10-14 09:10"}).returncode, 0)

    def test_the_lock_names_its_run_only_from_the_server(self):
        r = self.sweep("lock", env={"CREAITE_RUN_ID": "s-abc12345", "CREAITE_SERVER_PID": "4242"})
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self.lock.read_text().splitlines()[1:], ["run s-abc12345", "server 4242"])
        env = {k: v for k, v in os.environ.items() if k not in ("CREAITE_RUN_ID", "CREAITE_SERVER_PID")}
        self.lock.unlink()
        subprocess.run([sys.executable, str(self.v.root / "system/scripts/sweep.py"), "lock"], cwd=self.v.root, env=env,
                       capture_output=True)
        self.assertEqual(len(self.lock.read_text().splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
