"""2.6.8 (#369): the live server cleans the saved calendar again at start-up and in its daily job (sweep.rescrub_calendar).

Run: python3 dev/tests/test_live_rescrub_369.py      (quick tier: a throwaway vault, no Chrome, no Claude)

live_server.py is guarded, so the change is a proposal: dev/proposals/369/live_server-rescrub.diff. This test applies the diff to the
throwaway vault's COPY of live_server.py (never the checkout), unless the checkout already has calendar_rescrub_job, seeds a calendar
saved by an earlier version with a leaked value, and checks that the hook cleans it, that an exception inside the rescrub is swallowed,
and that backup_timer calls the hook before its first wait and on every pass. Mutants: the hook without its call, the call removed from
the timer, and the exception handler removed, each fails a test. All values are made up.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DIFF = REPO / "dev/proposals/369/live_server-rescrub.diff"
sys.path.insert(0, str(HERE))
from test_tracker import Vault  # noqa: E402

OLD = {"id": "o1", "start": "09:00", "end": "10:00", "title": "Budget Password swordfish review", "where": "Room PIN rtyu",
       "organiser": "Pat Doe", "sensitivity": "normal", "body": "Agenda: budget\nPassword swordfish"}
RUN = ("import sys, json; sys.path.insert(0, 'system/scripts')\nimport live_server, sweep\n{code}")


def patched_vault(test, diff_text=None):
    """A throwaway vault whose live_server.py carries the proposal (or `diff_text`, a changed copy of it)."""
    v = Vault()
    test.addCleanup(v.cleanup)
    live = v.root / "system/scripts/live_server.py"
    if "def calendar_rescrub_job" not in live.read_text(encoding="utf-8"):
        d = v.root / "369.diff"
        d.write_text(diff_text if diff_text is not None else DIFF.read_text(encoding="utf-8"), encoding="utf-8")
        r = subprocess.run(["patch", "-p1", "-s", "-d", str(v.root), "-i", str(d)], capture_output=True, text=True)
        test.assertEqual(r.returncode, 0, r.stdout + r.stderr)
    cal = v.root / "system/staging/calendar.json"
    cal.parent.mkdir(parents=True, exist_ok=True)
    cal.write_text(json.dumps({"fetched": "2026-10-20 08:00", "days": {"2026-10-26": [OLD]}}), encoding="utf-8")
    return v, cal


def run(v, code):
    import os
    return subprocess.run([sys.executable, "-c", RUN.format(code=code)], cwd=v.root, capture_output=True, text=True,
                          env={**os.environ, "CREAITE_NO_LAUNCH": "1"})


class Rescrub(unittest.TestCase):
    def test_the_hook_cleans_an_old_entry(self):
        v, cal = patched_vault(self)
        r = run(v, "print(live_server.calendar_rescrub_job()); print(live_server.calendar_rescrub_job())")
        self.assertEqual(r.returncode, 0, r.stderr[-300:])
        first, second = r.stdout.strip().splitlines()[-2:]
        self.assertIn("1 saved meeting", first)
        self.assertEqual(second, "None")                          # nothing left to clean
        flat = cal.read_text(encoding="utf-8").lower()
        self.assertNotIn("swordfish", flat)
        self.assertNotIn("rtyu", flat)
        self.assertIn("agenda: budget", flat)

    def test_the_development_repository_is_left_alone(self):
        v, cal = patched_vault(self)
        (v.root / ".creaite-dev").write_text("", encoding="utf-8")
        before = cal.read_bytes()
        r = run(v, "print(live_server.calendar_rescrub_job())")
        self.assertEqual(r.returncode, 0, r.stderr[-300:])
        self.assertEqual(r.stdout.strip().splitlines()[-1], "None")
        self.assertEqual(cal.read_bytes(), before)                        # byte for byte

    def test_an_exception_never_stops_the_server(self):
        v, cal = patched_vault(self)
        r = run(v, "def boom():\n    raise RuntimeError('x')\nsweep.rescrub_calendar = boom\nprint(live_server.calendar_rescrub_job())")
        self.assertEqual(r.returncode, 0, r.stderr[-300:])
        self.assertEqual(r.stdout.strip().splitlines()[-1], "None")

    def test_the_timer_calls_it_at_start_and_each_pass(self):
        v, _cal = patched_vault(self)
        r = run(v, "import inspect\nsrc = inspect.getsource(live_server.backup_timer)\n"
                   "print(src.index('calendar_rescrub_job()') < src.index('time.sleep(60)'), src.count('calendar_rescrub_job()'))")
        self.assertEqual(r.stdout.strip().splitlines()[-1], "True 2", r.stdout + r.stderr[-300:])

    def test_a_save_made_meanwhile_is_not_overwritten(self):
        v, cal = patched_vault(self)
        run(v, "import sweep\n" + 'import threading, time, json\ngot_lock = threading.Event()\ndef saver():\n    with sweep.calendar_lock() as ok:\n        got_lock.set()\n        time.sleep(0.4)\n        sweep.paths.CALENDAR.write_text(json.dumps({"days": {"2026-10-27": [{"id": "n1", "start": "08:00", "end": "09:00",\n            "title": "NEWER Password swordfish", "sensitivity": "normal"}]}}))\nt = threading.Thread(target=saver); t.start(); got_lock.wait(5)\nprint(sweep.rescrub_calendar(wait=10)); t.join()')
        self.assertIn("2026-10-27", cal.read_text(encoding="utf-8"))


class Mutants(unittest.TestCase):
    def mutated(self, old, new):
        text = DIFF.read_text(encoding="utf-8")
        self.assertIn(old, text, "mutant anchor not found")
        return text.replace(old, new, 1)

    def test_dev_guard_removed_rewrites_the_sample(self):
        old = "+        return None                                      # the development repository keeps its sample calendar as it is"
        v, cal = patched_vault(self, self.mutated(old, "+        pass"))
        (v.root / ".creaite-dev").write_text("", encoding="utf-8")
        run(v, "live_server.calendar_rescrub_job()")
        self.assertNotIn("swordfish", cal.read_text(encoding="utf-8").lower())      # the sample was rewritten: what the guard prevents

    def test_hook_without_its_call_fails(self):
        v, cal = patched_vault(self, self.mutated("+        n = sweep.rescrub_calendar()", "+        n = 0"))
        run(v, "live_server.calendar_rescrub_job()")
        self.assertIn("swordfish", cal.read_text(encoding="utf-8"))          # left unclean: Rescrub.test_the_hook... would fail

    def test_timer_without_the_call_fails(self):
        text = self.mutated("+            calendar_rescrub_job()\n", "+            pass\n")
        v, _cal = patched_vault(self, text)
        r = run(v, "import inspect\nprint(inspect.getsource(live_server.backup_timer).count('calendar_rescrub_job()'))")
        self.assertNotEqual(r.stdout.strip().splitlines()[-1], "2")

    def test_hook_without_its_handler_fails(self):
        text = self.mutated("+    except Exception as e:  # noqa: BLE001  fail safe: the server and the daily job go on\n+        swallowed(\"calendar-rescrub\", e)\n+        return None\n",
                            "+    except KeyError:\n+        pass\n+        return None\n")
        v, _cal = patched_vault(self, text)
        r = run(v, "def boom():\n    raise RuntimeError('x')\nsweep.rescrub_calendar = boom\nprint(live_server.calendar_rescrub_job())")
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
