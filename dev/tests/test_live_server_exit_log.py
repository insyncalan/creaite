"""#93: a live server start that stops says why in the debug log (ids, ports and counts only), and stale pages are counted
in one info line an hour (beside BL-269's log_stale).

Run: python3 dev/tests/test_live_server_exit_log.py
Real servers on free ports in throwaway vaults; the hourly count is driven with a faked clock in a subprocess.
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import free_port  # noqa: E402
from test_tracker import Vault  # noqa: E402

CANT_USE = "Can't use port {port} (Address already in use). Is the live server already running? " \
           "Change live_mode.port in settings.json if another app uses it."


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


class StartStopReasons(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.port = free_port()
        self.env = {**os.environ, "CREAITE_PORT": str(self.port), "CREAITE_STOP_AFTER": "30"}
        self.staging = self.v.root / "system" / "staging"
        self.procs = []

    def tearDown(self):
        for p in self.procs:                                  # only the servers this test started, by their own pids
            if p.poll() is None:
                p.terminate()
                p.wait(timeout=10)
            for s in (p.stdout, p.stderr):
                if s:
                    s.close()
        self.v.cleanup()

    def server(self, **env):
        p = subprocess.Popen([sys.executable, str(self.v.root / "system/scripts/live_server.py")], cwd=tempfile.gettempdir(),
                             env={**self.env, **env}, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.procs.append(p)
        return p

    def debug_log(self):
        logs = self.v.root / "system" / "logs"
        return "".join(f.read_text(encoding="utf-8") for f in sorted(logs.glob("debug-*.log"))) if logs.is_dir() else ""

    def running_line(self, pid):
        return (rf"INFO.*already running on port {self.port} \(this vault's server, pid {pid}, is running or starting\): "
                r"this start exits")

    def stopped_line(self):
        return [ln for ln in self.debug_log().splitlines() if "start stopped:" in ln]

    def test_port_taken_by_another_program(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", self.port))
            s.listen(1)
            p = self.server()
            out, err = p.communicate(timeout=60)
        self.assertEqual(p.returncode, 1)
        self.assertEqual(err.strip(), CANT_USE.format(port=self.port))          # the message is unchanged
        lines = self.stopped_line()
        self.assertEqual(len(lines), 1, self.debug_log())
        self.assertRegex(lines[0], rf"WARN.*start stopped: can't use port {self.port} \(EADDRINUSE\): held by another program")
        self.assertRegex(self.debug_log(), r"WARN.*exit 1 after")

    def test_already_running_names_the_running_pid(self):
        first = self.server()
        self.assertTrue(wait_until(lambda: alive(self.port)))
        second = self.server()
        out, _ = second.communicate(timeout=60)
        self.assertEqual(second.returncode, 0, out)
        self.assertIn(f"The live server is already running on port {self.port}: this one stops.", out)
        self.assertRegex(self.debug_log(), self.running_line(first.pid))
        self.assertEqual(first.poll(), None)

    def test_already_running_while_the_first_holds_the_starting_mark(self):
        first = self.server(CREAITE_START_DELAY="4")
        mark = self.staging / "live-server-starting.json"
        self.assertTrue(wait_until(lambda: mark.exists(), 15))
        second = self.server()
        out, _ = second.communicate(timeout=60)
        self.assertEqual(second.returncode, 0, out)
        self.assertRegex(self.debug_log(), self.running_line(first.pid))

    def test_a_port_that_isnt_a_number(self):
        p = self.server(CREAITE_PORT="eighty")
        _, err = p.communicate(timeout=60)
        self.assertEqual(p.returncode, 1)
        self.assertIn("ValueError", err)                                         # raised as before
        self.assertRegex("\n".join(self.stopped_line()), r"ERROR.*start stopped: the port isn't a whole number \(ValueError\)")
        self.assertNotIn("eighty", "\n".join(self.stopped_line()))                # never the value given

    def test_a_port_out_of_range(self):
        p = self.server(CREAITE_PORT="70000")
        _, err = p.communicate(timeout=60)
        self.assertEqual(p.returncode, 1)
        self.assertIn("OverflowError", err)
        self.assertRegex("\n".join(self.stopped_line()), r"ERROR.*start stopped: port 70000 is out of range")

    def test_settings_that_cant_be_read(self):
        env = {k: v for k, v in self.env.items() if k != "CREAITE_PORT"}
        settings = self.v.root / "system" / "config" / "settings.json"
        good = settings.read_text(encoding="utf-8")
        p = subprocess.Popen([sys.executable, "-c", textwrap.dedent(f"""
            import sys
            from pathlib import Path
            sys.argv = [{str(self.v.root / 'system/scripts/live_server.py')!r}]
            sys.path.insert(0, {str(self.v.root / 'system/scripts')!r})
            import live_server as L                     # loaded with good settings, then they break before main reads them
            Path({str(settings)!r}).write_text("{{ not json", encoding="utf-8")
            sys.exit(L.debuglog.main("live_server.py", L.main))
            """)], cwd=tempfile.gettempdir(), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.procs.append(p)
        _, err = p.communicate(timeout=60)
        settings.write_text(good, encoding="utf-8")
        self.assertEqual(p.returncode, 1, err)
        self.assertIn("JSONDecodeError", err)
        self.assertRegex("\n".join(self.stopped_line()), r"ERROR.*start stopped: settings.json can't be read \(JSONDecodeError\)")


class HourlyStaleCount(unittest.TestCase):
    """The hourly line: distinct stale pages and repeat requests, from the first stale request after the hour (a faked clock)."""

    def test_counts_with_a_faked_clock(self):
        v = Vault()
        try:
            code = f"""
import sys, json
sys.path.insert(0, {str(v.root / 'system' / 'scripts')!r})
import live_server as L
out = []
t0 = 1_800_000_000.0
out.append(L.count_stale("aaa", t0))              # opens the window
out.append(L.count_stale("aaa", t0 + 10))         # a repeat
out.append(L.count_stale("bbb", t0 + 20))         # a second page
out.append(L.count_stale("aaa", t0 + 3599))       # still this hour
out.append(L.count_stale("ccc", t0 + 3600))       # an hour on: the line for the hour, and a new window
out.append(dict(pages=sorted(L.STALE_HOUR["pages"]), repeats=L.STALE_HOUR["repeats"]))
out.append(L.count_stale("ccc", t0 + 9000))       # the next window closes too
class H:
    headers = {{"X-Creaite-Token": "an-old-pages-token"}}
lines = []
L.debuglog.info = lambda area, msg: lines.append(("info", area, msg))
L.debuglog.debug = lambda area, msg: lines.append(("debug", area, msg))
L.STALE_HOUR.update(start=None, pages=set(), over=0, repeats=0)
L.log_stale(H(), "POST /api/pulse 403")
L.STALE_HOUR["start"] -= 3600
L.log_stale(H(), "POST /api/pulse 403")
out.append(lines)
print(json.dumps(out))
"""
            r = subprocess.run([sys.executable, "-c", code], cwd=tempfile.gettempdir(), capture_output=True, text=True,
                               timeout=120)
            self.assertEqual(r.returncode, 0, r.stderr)
            out = json.loads(r.stdout.strip().splitlines()[-1])
        finally:
            v.cleanup()
        self.assertEqual(out[:4], [None, None, None, None])                     # no line within the hour
        self.assertRegex(out[4], r"^stale pages in the hour from \d\d:\d\d: 2 pages, 2 repeat requests$")
        self.assertEqual(out[5], {"pages": ["ccc"], "repeats": 0})
        self.assertRegex(out[6], r": 1 pages, 0 repeat requests$")
        lines = out[7]
        self.assertEqual(len(lines), 3, lines)                                  # page line, hourly line, repeat at debug
        self.assertEqual(lines[0][0], "info")
        self.assertIn("told to reload", lines[0][2])
        self.assertEqual(lines[1][:2], ["info", "server"])
        self.assertRegex(lines[1][2], r"^stale pages in the hour from \d\d:\d\d: 1 pages, 0 repeat requests$")
        self.assertEqual(lines[2][0], "debug")
        self.assertNotIn("an-old-pages-token", json.dumps(lines))              # never the token

    def test_no_line_when_nothing_stale(self):
        v = Vault()
        try:
            code = f"""
import sys
sys.path.insert(0, {str(v.root / 'system' / 'scripts')!r})
import live_server as L
print(L.STALE_HOUR["start"], len(L.STALE_HOUR["pages"]), L.STALE_HOUR["repeats"])
"""
            r = subprocess.run([sys.executable, "-c", code], cwd=tempfile.gettempdir(), capture_output=True, text=True,
                               timeout=120)
        finally:
            v.cleanup()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.split()[-3:], ["None", "0", "0"])


if __name__ == "__main__":
    unittest.main()
