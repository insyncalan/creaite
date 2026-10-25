"""2.6.8 review: a saved calendar of any shape is cleaned, and readers never fail on it.

Run: python3 dev/tests/test_calendar_shapes.py      (quick tier: throwaway vaults, no Chrome, no Claude)

A legacy or foreign calendar.json may hold keys the sweep never writes (description, joinUrl, location, extra), a note at the top, a string
for a row or a day. clean_row now keeps ONLY invite_clean.ROW_KEYS (what sweep.calendar_row writes); clean_calendar keeps only
"fetched", "to" and a dict of YYYY-MM-DD days to lists of dict rows; rescrub_calendar rewrites the file to that; and every reader reads
through invite_clean.read_calendar (cleaned, cached while the file is unchanged), so none can raise on an odd shape.
- SHAPES: the reviewer's examples. READERS: build_dashboard, transcripts, drafts, prep_page on the odd file. CACHE: the second read of an
  unchanged file is fast, a changed file always misses, the caller gets its own copy.
- MUTANTS: the allow-list off, non-dict rows kept, the readers' guard off, the cache key without the size or time.
All values are made up.
"""
import copy
import importlib.util
import json
import os
import subprocess
import sys

import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parents[1] / "system" / "scripts"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SCRIPTS))
import invite_clean as I  # noqa: E402
from test_tracker import Vault  # noqa: E402

SECRET = "Passcode: 4321"
ODD = {"fetched": "2026-10-25 08:00", "to": "2026-10-30", "note": SECRET, "extra": [SECRET],
       "days": {"2026-10-26": [{"id": "a1", "start": "09:00", "end": "10:00", "title": "Sync", "description": SECRET,
                                "joinUrl": "https://zoom.example.invalid/j/5550001111?pwd=abc", "location": SECRET, "extra": SECRET,
                                "sensitivity": "normal"}, SECRET, 7, None, ["x"]],
                "2026-10-27": SECRET, "2026-10-28": None, "not-a-day": [{"id": "z", "title": SECRET}]}}


def vault(test, data=None):
    v = Vault()
    test.addCleanup(v.cleanup)
    cal = v.root / "system/staging/calendar.json"
    cal.parent.mkdir(parents=True, exist_ok=True)
    cal.write_text(json.dumps(ODD if data is None else data), encoding="utf-8")
    return v, cal


def run(v, code):
    return subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts')\n" + code], cwd=v.root,
                          capture_output=True, text=True, env={**os.environ, "CREAITE_NO_LAUNCH": "1", "CREAITE_NOW": "2026-10-25T09:00:00"})


READERS = {
    "dashboard saved days": "import build_dashboard as b\nprint(json.dumps(b.saved_calendar_days()))",
    "dashboard day view": "import build_dashboard as b\nprint(json.dumps(b.calendar([])))",
    "transcript rows": "import transcripts as t\nprint(json.dumps(t.calendar_rows()))",
    "draft attendees": "import drafts as d\nprint(json.dumps(d._meeting_attendees('2026-10-26', 'Sync')))",
    "draft event": "import drafts as d\nprint(json.dumps(d.calendar_event({'eid': 'a1'})))",
    "prep event": "import prep_page as p\nprint(json.dumps(p._event('2026-10-26|09:00|Sync', '2026-10-26')))",
}


class Shapes(unittest.TestCase):
    def test_clean_calendar_keeps_only_a_calendar(self):
        out = I.clean_calendar(copy.deepcopy(ODD))
        self.assertEqual(set(out), {"fetched", "to", "days"})
        self.assertEqual(list(out["days"]), ["2026-10-26"])
        self.assertEqual(len(out["days"]["2026-10-26"]), 1)
        self.assertEqual(set(out["days"]["2026-10-26"][0]) - set(I.ROW_KEYS), set())
        self.assertNotIn("4321", json.dumps(out))
        self.assertNotIn("zoom", json.dumps(out))
        self.assertEqual(I.clean_calendar(out), out)                          # a cleaned calendar cleans to itself

    def test_not_a_calendar_at_all(self):
        for odd in ([], "x", None, 5, [ODD], {"days": [1, 2]}, {"days": "x"}):
            self.assertEqual(I.clean_calendar(odd)["days"], {})

    def test_each_example_on_its_own(self):
        base = {"id": "a", "start": "09:00", "end": "10:00", "title": "Sync", "sensitivity": "normal"}
        for key in ("description", "joinUrl", "location", "extra", "notes", "body2", "teams_url"):
            row = I.clean_row({**base, key: SECRET})
            self.assertNotIn(key, row)
            self.assertNotIn("4321", json.dumps(row))

    def test_rescrub_rewrites_the_file(self):
        v, cal = vault(self)
        r = run(v, "import sweep\nprint(sweep.rescrub_calendar())")
        self.assertEqual(r.returncode, 0, r.stderr[-300:])
        self.assertNotIn("4321", cal.read_text(encoding="utf-8"))
        self.assertNotIn("note", json.loads(cal.read_text(encoding="utf-8")))
        self.assertEqual(run(v, "import sweep\nprint(sweep.rescrub_calendar())").stdout.strip(), "0")        # then nothing to do


class Recurrence(unittest.TestCase):
    """The recurrence is free text (Cap, 18:57): calendar_row scrubbed nothing, and a passcode in it was written to calendar.json."""

    def row(self, text, mod=None):
        import sweep
        return (mod or sweep).calendar_row({"id": "r1", "title": "Weekly sync", "recurrence": text}, "09:00", "10:00", False)

    def test_a_secret_in_the_recurrence_is_gone_on_the_first_save(self):
        for text in ("RRULE Passcode 9999", "weekly Meeting ID: 987 654 321", "every week, PIN 4417", "https://zoom.example.invalid/j/5550001111?pwd=ab"):
            row = self.row(text)
            self.assertNotIn("recurrence", row, text)
            self.assertNotRegex(json.dumps(row), r"9999|987 654|4417|5550001111")

    def test_an_ordinary_recurrence_is_kept(self):
        for text in ("weekly", "RRULE:FREQ=WEEKLY;BYDAY=MO", "Every 2 weeks on Monday"):
            self.assertEqual(self.row(text)["recurrence"], text)

    def test_rescrub_removes_it_from_a_saved_file(self):
        row = {"id": "a", "start": "09:00", "end": "10:00", "title": "Sync", "sensitivity": "normal", "recurrence": "RRULE Passcode 9999"}
        v, cal = vault(self, {"fetched": "x", "to": "y", "days": {"2026-10-26": [row]}})
        run(v, "import sweep\nprint(sweep.rescrub_calendar())")
        self.assertNotIn("9999", cal.read_text(encoding="utf-8"))

    def test_mutant_without_the_scrub_in_calendar_row(self):
        import sweep
        src = (SCRIPTS / "sweep.py").read_text(encoding="utf-8")
        old = 'rec = invite_clean.scrub(ev.get("recurrence"), 40) if ev.get("recurrence") else ""'
        self.assertIn(old, src)
        spec = importlib.util.spec_from_loader("sweep_rec_mutant", loader=None)
        mod = importlib.util.module_from_spec(spec)
        mod.__file__ = str(SCRIPTS / "sweep.py")
        exec(compile(src.replace(old, 'rec = str(ev.get("recurrence") or "")[:40]', 1), "sweep_rec_mutant", "exec"), mod.__dict__)
        self.assertIn("9999", json.dumps(self.row("RRULE Passcode 9999", mod)))
        self.assertTrue(sweep)


class Readers(unittest.TestCase):
    def test_no_reader_fails_on_an_odd_file(self):
        v, _cal = vault(self)
        for name, code in READERS.items():
            r = run(v, code)
            self.assertEqual(r.returncode, 0, f"{name}: {r.stderr[-300:]}")
            self.assertNotIn("4321", r.stdout, name)

    def test_no_reader_fails_on_other_shapes(self):
        for data in ([], "text", {"days": "x"}, {"days": {"2026-10-26": "x"}}, {"days": {"2026-10-26": ["x", 1]}}):
            v, _cal = vault(self, data)
            for name, code in READERS.items():
                r = run(v, code)
                self.assertEqual(r.returncode, 0, f"{name} on {data!r}: {r.stderr[-300:]}")


class Cache(unittest.TestCase):
    def big(self, n=60):
        row = {"id": "a", "start": "09:00", "end": "10:00", "title": "Sync", "sensitivity": "normal",
               "body": "Agenda: budget\n" + "Review the plan with the team\n" * 600}
        return {"fetched": "x", "to": "y", "days": {"2026-10-26": [dict(row, id=str(i)) for i in range(n)]}}

    def test_second_read_is_fast_and_a_changed_file_misses(self):
        v, cal = vault(self, self.big())
        code = ("import time, json, invite_clean as I, paths\nt0 = time.time(); a = I.read_calendar(paths.CALENDAR); t1 = time.time()\n"
                "b = I.read_calendar(paths.CALENDAR); t2 = time.time()\na['days'].clear()\nc = I.read_calendar(paths.CALENDAR)\n"
                "print(json.dumps([round(t1 - t0, 3), round(t2 - t1, 3), len(c['days']['2026-10-26'])]))")
        first, second, n = json.loads(run(v, code).stdout.strip().splitlines()[-1])
        self.assertGreater(first, second * 3)                                # the first read cleans 60 rows of 18 KB
        self.assertLess(second, 0.1)                                         # the second read of the unchanged file does not
        self.assertEqual(n, 60)                                              # and the caller's copy was its own
        code2 = ("import json, invite_clean as I, paths\nI.read_calendar(paths.CALENDAR)\n"
                 "d = json.loads(paths.CALENDAR.read_text()); d['days']['2026-10-26'][0]['title'] = 'Passcode: 4321'\n"
                 "paths.CALENDAR.write_text(json.dumps(d))\nprint(json.dumps(I.read_calendar(paths.CALENDAR)['days']['2026-10-26'][0]['title']))")
        self.assertEqual(json.loads(run(v, code2).stdout.strip().splitlines()[-1]), "Meeting")        # changed file: cleaned afresh

    def test_cached_value_is_cleaned(self):
        v, _cal = vault(self)
        code = ("import json, invite_clean as I, paths\nI.read_calendar(paths.CALENDAR)\nprint(json.dumps(I.read_calendar(paths.CALENDAR)))")
        self.assertNotIn("4321", run(v, code).stdout)


class Unlocked(unittest.TestCase):
    """The clean-up never skips: when the calendar lock cannot be had it cleans without it (writing only if the file is unchanged since
    it was read) and logs that it did."""

    def check(self, v, cal, prelude, wait="0.3"):
        r = run(v, "import sweep\n" + prelude + "\nprint(sweep.rescrub_calendar(wait=" + wait + "))")
        self.assertEqual(r.returncode, 0, r.stderr[-300:])
        self.assertGreaterEqual(int(r.stdout.strip().splitlines()[-1]), 1)
        self.assertNotIn("4321", cal.read_text(encoding="utf-8"))                         # cleaned, not skipped
        logs = "".join(f.read_text(encoding="utf-8", errors="ignore") for f in (v.root / "system/logs").glob("debug-*.log"))
        self.assertIn("clean-up ran without the lock", logs)
        self.assertNotIn("4321", logs)

    def test_lock_held_by_another_process(self):
        v, cal = vault(self)
        holder = subprocess.Popen([sys.executable, "-c", "import sys, fcntl, time\nsys.path.insert(0, 'system/scripts')\nimport sweep\n"
                                   "sweep.CAL_LOCK.parent.mkdir(parents=True, exist_ok=True)\nf = open(sweep.CAL_LOCK, 'w')\n"
                                   "fcntl.flock(f, fcntl.LOCK_EX)\nprint('held', flush=True)\ntime.sleep(6)"],
                                  cwd=v.root, stdout=subprocess.PIPE, text=True)
        self.addCleanup(holder.kill)
        self.assertEqual(holder.stdout.readline().strip(), "held")
        self.check(v, cal, "")

    def test_unwritable_lock_path(self):
        v, cal = vault(self)
        self.check(v, cal, "from pathlib import Path\nsweep.CAL_LOCK = Path('/dev/null/nowhere/calendar.lock')")

    def test_no_fcntl(self):
        v, cal = vault(self)
        self.check(v, cal, "import sys\nsys.modules['fcntl'] = None")

    def test_a_save_made_meanwhile_is_not_overwritten_without_the_lock(self):
        v, cal = vault(self)
        prelude = ("import sys, json\nsys.modules['fcntl'] = None\nreal = sweep.invite_clean.clean_calendar\nstate = {'n': 0}\n"
                   "def late(c):\n    if state['n'] == 0:\n        state['n'] = 1\n"
                   "        sweep.paths.CALENDAR.write_text(json.dumps({'days': {'2026-10-27': [{'id': 'n1', 'start': '08:00', 'end': '09:00',"
                   " 'title': 'NEWER Passcode: 4321 swordfish', 'sensitivity': 'normal'}]}}))\n    return real(c)\n"
                   "sweep.invite_clean.clean_calendar = late")
        run(v, "import sweep\n" + prelude + "\nprint(sweep.rescrub_calendar(wait=0.1))")
        flat = cal.read_text(encoding="utf-8")
        self.assertIn("2026-10-27", flat)                                                # the newer save was kept...
        self.assertNotIn("4321", flat)                                                   # ...and cleaned on the retry

    def test_mutant_fallback_removed_leaves_the_file_raw(self):
        v, cal = vault(self)
        f = v.root / "system/scripts/sweep.py"
        src = f.read_text(encoding="utf-8")
        old = "        if not got:\n            for _ in range(5):"
        self.assertIn(old, src)
        f.write_text(src.replace(old, "        if False:\n            for _ in range(5):", 1), encoding="utf-8")
        run(v, "import sweep, sys\nsys.modules['fcntl'] = None\nprint(sweep.rescrub_calendar(wait=0.1))")
        self.assertIn("4321", cal.read_text(encoding="utf-8"))                           # raw: what the fallback prevents


class Mutants(unittest.TestCase):
    def mutated(self, old, new):
        src = (SCRIPTS / "invite_clean.py").read_text(encoding="utf-8")
        self.assertIn(old, src)
        spec = importlib.util.spec_from_loader("invite_clean_shape_mutant", loader=None)
        mod = importlib.util.module_from_spec(spec)
        mod.__file__ = str(SCRIPTS / "invite_clean.py")
        exec(compile(src.replace(old, new, 1), "invite_clean_shape_mutant", "exec"), mod.__dict__)
        return mod

    def test_allow_list_off(self):
        m = self.mutated("    out = _row_head(row, sens, private)\n",
                         "    out = {**{k: v for k, v in row.items() if k not in ('title', 'where', 'body')}, **_row_head(row, sens, private)}\n")
        self.assertIn("4321", json.dumps(m.clean_row({"id": "a", "title": "Sync", "description": SECRET, "sensitivity": "normal"})))

    def test_non_dict_rows_kept(self):
        m = self.mutated("[clean_row(r) for r in rows if isinstance(r, dict)]", "[clean_row(r) if isinstance(r, dict) else r for r in rows]")
        self.assertIn(SECRET, json.dumps(m.clean_calendar(copy.deepcopy(ODD))))

    def test_reader_without_the_guard_raises(self):
        v, _cal = vault(self, [])                                            # a top-level list
        f = v.root / "system/scripts/invite_clean.py"
        src = f.read_text(encoding="utf-8")
        old = '    if not isinstance(cal, dict):\n        return {"days": {}}\n'
        self.assertIn(old, src)
        f.write_text(src.replace(old, "", 1), encoding="utf-8")
        self.assertNotEqual(run(v, READERS["dashboard day view"]).returncode, 0)

    def test_cache_key_without_size_or_time(self):
        v, cal = vault(self)
        f = v.root / "system/scripts/invite_clean.py"
        src = f.read_text(encoding="utf-8")
        old = "sig = (st.st_mtime_ns, st.st_size, st.st_ino)"
        self.assertIn(old, src)
        f.write_text(src.replace(old, "sig = (0,)", 1).replace("(st2.st_mtime_ns, st2.st_size, st2.st_ino) == sig", "True", 1), encoding="utf-8")
        code = ("import json, invite_clean as I, paths\nI.read_calendar(paths.CALENDAR)\npaths.CALENDAR.write_text(json.dumps({'days': "
                "{'2026-10-26': [{'id': 'n', 'title': 'NEWER'}]}}))\nprint(json.dumps(I.read_calendar(paths.CALENDAR)))")
        self.assertNotIn("NEWER", run(v, code).stdout)                       # stale: the cache would serve the old file


if __name__ == "__main__":
    unittest.main()
