"""#137: the shared sample vault (test_dashboard.populate) does not change with the real date.

Its dates come from CREAITE_NOW's day when that is set, and its applies are stamped with a fixed day (CREAITE_STAMP_DAY), so a
test that asserts a fixed day does not fail just because the real date is that day. Proved by building the vault twice in a
child process whose clock is faked to two different real days (a Friday and the 1st of a month), with the same CREAITE_NOW,
and comparing everything in the database and the project files, with only the time of day (which stays real) masked.

Run: python3 dev/tests/test_populate_clock.py
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

NOW = "2026-10-12 09:30"                      # the clock the scripts and the sample data use
REAL_A, REAL_B = "2026-10-16", "2026-11-01"      # the "real" days: a Friday, and the 1st of a month (a Sunday)

# A child process with the date part of datetime's clock faked (the time of day stays real). Test machinery only.
FAKE_CLOCK = '''
import os, datetime as _dt
_day = os.environ.get("FAKE_REAL_DAY")
if _day:
    _fd = _dt.date.fromisoformat(_day)
    _rd, _rdt = _dt.date, _dt.datetime
    class date(_rd):
        @classmethod
        def today(cls):
            return cls(_fd.year, _fd.month, _fd.day)
    class datetime(_rdt):
        @classmethod
        def now(cls, tz=None):
            n = _rdt.now(tz)
            return cls(_fd.year, _fd.month, _fd.day, n.hour, n.minute, n.second, n.microsecond, n.tzinfo)
        @classmethod
        def today(cls):
            return cls.now()
    _dt.date, _dt.datetime = date, datetime
'''


def dump():
    """Child process: build the sample vault and print its database as JSON, the time of day masked."""
    from test_dashboard import populate
    from test_tracker import Vault
    v = Vault()
    try:
        populate(v)
        mask = lambda x: re.sub(r"(\d{4}-\d{2}-\d{2}[ T])\d{2}:\d{2}:\d{2}(\.\d+)?", r"\1HH:MM:SS", json.dumps(x, default=str))  # noqa: E731
        tables = {}
        with closing(sqlite3.connect(v.root / "system" / "tracker.db")) as con:
            for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
                                    "AND name NOT LIKE 'vault_search%' ORDER BY 1").fetchall():
                tables[t] = sorted(mask(list(r)) for r in con.execute(f'SELECT * FROM "{t}"'))   # sorted after masking: the time of day is real
        files = sorted(p.relative_to(v.root).as_posix() for p in (v.root / "projects").rglob("*") if p.is_file())
        print(json.dumps({"tables": tables, "files": files}, sort_keys=True))
    finally:
        v.cleanup()


def build(real_day):
    """The sample vault built while the real date is `real_day`, as a dict."""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "sitecustomize.py").write_text(FAKE_CLOCK)
        env = {**os.environ, "FAKE_REAL_DAY": real_day, "CREAITE_NOW": NOW, "PYTHONPATH": tmp}
        env.pop("CREAITE_STAMP_DAY", None)
        r = subprocess.run([sys.executable, str(Path(__file__).resolve()), "dump"], env=env, capture_output=True, text=True)
        if r.returncode:
            raise AssertionError(f"dump failed:\n{r.stdout}\n{r.stderr}")
        return json.loads(r.stdout.strip().splitlines()[-1])


class PopulateClockTests(unittest.TestCase):
    def test_the_sample_vault_is_the_same_whatever_the_real_date(self):
        a, b = build(REAL_A), build(REAL_B)
        self.assertEqual(a["files"], b["files"])
        for t in a["tables"]:
            self.assertEqual(a["tables"][t], b["tables"][t], f"{t} changes with the real date")

    def test_its_dates_follow_creaite_now_and_its_stamps_are_fixed(self):
        a = build(REAL_A)
        names = " ".join(a["files"])
        self.assertIn("2026-10-07 Steering.docx", names)         # d(-5) from CREAITE_NOW's 12 October, not the real day
        text = " ".join(a["tables"]["change_log"])
        self.assertIn("2026-10-10 HH:MM:SS", text)               # populate's STAMP_DAY
        self.assertNotIn(REAL_A + " HH:MM:SS", text)             # never the real day


if __name__ == "__main__":
    if sys.argv[1:] == ["dump"]:
        dump()
    else:
        unittest.main()
