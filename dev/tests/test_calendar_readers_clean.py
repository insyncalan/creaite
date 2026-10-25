"""2.6.8 (Full review MEDIUM 3 to 5): a calendar saved by an earlier version is clean when it is READ, and the clean-up that rewrites it
is safe.

Run: python3 dev/tests/test_calendar_readers_clean.py      (quick tier: throwaway vaults, no Chrome, no Claude)

- Every reader of calendar.json (the dashboard's day view and prep, the inbox meetings, Close the day, the draft contexts, the prep page,
  the transcript matching) returns nothing of an old entry's leaked value: `invite_clean.clean_calendar` at each read.
- `sweep.rescrub_calendar` re-reads the file before it writes: a sweep that saves in between is not lost, and its new file is cleaned.
- `session.rescrub_calendar_safely` never lets a failure stop session start; it logs one line with the kind of error and no text.
- Mutants: clean_calendar doing nothing fails every reader test; the re-read removed loses a concurrent save.
All values are made up.
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parents[1] / "system" / "scripts"
sys.path.insert(0, str(HERE))
from test_tracker import Vault  # noqa: E402

OLD = {"id": "o1", "start": "09:00", "end": "10:00", "title": "Budget Password swordfish review", "where": "Room PIN rtyu",
       "organiser": "Pat Doe", "sensitivity": "normal", "teams": True, "body": "Agenda: budget\nPassword swordfish",
       "attendees": [{"name": "Sam Lee Password swordfish", "email": "sam@brightwater.example"}]}
DAY = "2026-10-26"
READERS = {
    "dashboard saved days": "import build_dashboard as b\nprint(json.dumps(b.saved_calendar_days()))",
    "dashboard day view": "import build_dashboard as b\nprint(json.dumps(b.calendar([])))",
    "transcript rows": "import transcripts as t\nprint(json.dumps(t.calendar_rows()))",
    "draft attendees": f"import drafts as d\nprint(json.dumps(d._meeting_attendees('{DAY}', 'Meeting')))",
    "draft event": f"import drafts as d\nprint(json.dumps(d.calendar_event({{'eid': 'o1'}})))",
    "prep event": f"import prep_page as p\nprint(json.dumps(p._event('{DAY}|09:00|Meeting', '{DAY}')))",
}


def vault(test):
    v = Vault()
    test.addCleanup(v.cleanup)
    cal = v.root / "system/staging/calendar.json"
    cal.parent.mkdir(parents=True, exist_ok=True)
    cal.write_text(json.dumps({"fetched": "2026-10-25 08:00", "to": "2026-10-30", "days": {DAY: [OLD]}}), encoding="utf-8")
    return v, cal


def run(v, code, root=None):
    return subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts')\n" + code], cwd=v.root,
                          capture_output=True, text=True, env={**os.environ, "CREAITE_NO_LAUNCH": "1", "CREAITE_NOW": "2026-10-25T09:00:00"})


class Readers(unittest.TestCase):
    def check(self, v, name, code):
        r = run(v, code)
        self.assertEqual(r.returncode, 0, f"{name}: {r.stderr[-300:]}")
        self.assertNotIn("swordfish", r.stdout.lower(), name)
        self.assertNotIn("rtyu", r.stdout.lower(), name)
        return r.stdout

    def test_every_reader_is_clean(self):
        v, _cal = vault(self)
        for name, code in READERS.items():
            self.check(v, name, code)

    def test_the_file_itself_is_untouched_by_reading(self):
        v, cal = vault(self)
        before = cal.read_text(encoding="utf-8")
        run(v, READERS["dashboard saved days"])
        self.assertEqual(cal.read_text(encoding="utf-8"), before)           # readers clean in memory; rescrub rewrites the file

    def test_readers_see_the_meeting_at_all(self):
        """The clean-up must not hide the meeting itself (the day view still shows a title)."""
        v, _cal = vault(self)
        out = self.check(v, "saved days", READERS["dashboard saved days"])
        self.assertIn("agenda: budget", out.lower())
        for name in ("draft attendees", "draft event", "prep event"):          # found by the cleaned title / the ID, and not empty
            self.assertIn("o1" if name != "draft attendees" else "sam@brightwater.example", self.check(v, name, READERS[name]), name)


class Mutants(unittest.TestCase):
    def test_clean_calendar_off_leaks_in_every_reader(self):
        v, _cal = vault(self)
        f = v.root / "system/scripts/invite_clean.py"
        src = f.read_text(encoding="utf-8")
        self.assertIn("def clean_calendar(cal):", src)
        f.write_text(src.replace("def clean_calendar(cal):", "def clean_calendar(cal):\n    return cal", 1), encoding="utf-8")
        leaked = [n for n, code in READERS.items() if "swordfish" in run(v, code).stdout.lower() or "rtyu" in run(v, code).stdout.lower()]
        self.assertTrue(leaked, "no reader noticed clean_calendar being switched off")


class Rescrub(unittest.TestCase):
    # a sweep's save and the clean-up share the calendar lock: the saver holds it, writes a newer file, lets go; the clean-up waits
    CONCURRENT = 'import threading, time, json\ngot_lock = threading.Event()\ndef saver():\n    with sweep.calendar_lock() as ok:\n        got_lock.set()\n        time.sleep(0.4)\n        sweep.paths.CALENDAR.write_text(json.dumps({"days": {"2026-10-27": [{"id": "n1", "start": "08:00", "end": "09:00",\n            "title": "NEWER Password swordfish", "sensitivity": "normal"}]}}))\nt = threading.Thread(target=saver); t.start(); got_lock.wait(5)\nprint(sweep.rescrub_calendar(wait=10)); t.join()'

    def test_a_save_made_meanwhile_is_kept_and_cleaned(self):
        v, cal = vault(self)
        run(v, "import sweep\n" + self.CONCURRENT)
        flat = cal.read_text(encoding="utf-8")
        self.assertIn("2026-10-27", flat)                               # the sweep's save was not lost
        self.assertNotIn("swordfish", flat.lower())                     # and it was cleaned once the lock was free

    def test_mutant_without_the_lock_loses_the_save(self):
        v, cal = vault(self)
        f = v.root / "system/scripts/sweep.py"
        src = f.read_text(encoding="utf-8")
        old = "                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)\n"
        self.assertIn(old, src)
        f.write_text(src.replace(old, "                pass\n", 1), encoding="utf-8")
        run(v, "import sweep\n" + self.CONCURRENT)
        # without the lock the clean-up runs before the sweep's save finishes: the newer file lands afterwards, uncleaned
        self.assertIn("swordfish", cal.read_text(encoding="utf-8").lower())

    def test_session_start_survives_a_failing_rescrub(self):
        v, _cal = vault(self)
        r = run(v, "import session, sweep\ndef boom(*a, **k):\n    raise OSError('disk')\n"
                   "sweep.paths.write_text_atomic = boom\nsession.rescrub_calendar_safely()\nprint('went on')")
        self.assertEqual(r.returncode, 0, r.stderr[-300:])
        self.assertIn("went on", r.stdout)
        logs = "".join(f.read_text(encoding="utf-8", errors="ignore") for f in (v.root / "system/logs").glob("debug-*.log"))
        self.assertIn("calendar clean-up failed: OSError", logs)
        self.assertNotIn("swordfish", logs.lower())

    def test_mutant_session_without_the_guard_stops(self):
        v, _cal = vault(self)
        f = v.root / "system/scripts/session.py"
        src = f.read_text(encoding="utf-8")
        self.assertIn("    except Exception as e:  # noqa: BLE001\n        sweep.debuglog", src)
        f.write_text(src.replace("    except Exception as e:  # noqa: BLE001\n        sweep.debuglog", "    except KeyError as e:  # noqa: BLE001\n        sweep.debuglog", 1),
                     encoding="utf-8")
        r = run(v, "import session, sweep\ndef boom(*a, **k):\n    raise OSError('disk')\n"
                   "sweep.paths.write_text_atomic = boom\nsession.rescrub_calendar_safely()\nprint('went on')")
        self.assertNotEqual(r.returncode, 0)

    def test_session_start_calls_it(self):
        self.assertIn("    rescrub_calendar_safely()\n", (SCRIPTS / "session.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
