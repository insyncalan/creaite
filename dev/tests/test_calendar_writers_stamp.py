"""#375 E1, slice S4: the sweep's writers of calendar.json stamp every row they write (through calendar_gateway).

Run: python3 dev/tests/test_calendar_writers_stamp.py      (quick tier: plain code, a throwaway folder)

Covers sweep.calendar (the save), sweep.keep_held_past_days, sweep.rescrub_calendar. Stand-ins are injected through calendar_gateway.FILTER
and SHORT (drops a line with a link or a long number). DECISION on held rows: a stamped held row keeps its own stamp and is kept as
stored; an unstamped held row (saved by an earlier version) is cleaned and its body filtered and ONLY THEN stamped: a row is never
stamped without being filtered. Fictional data only.
"""
import json
import os
import re
import sys
import tempfile
import threading
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parents[1] / "system" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import calendar_gateway as G  # noqa: E402
import paths  # noqa: E402
import sweep  # noqa: E402

LINK = "Join: https://meet.example.test/j/123456789?pwd=Zx81"


def stand_in(text):
    return "\n".join(ln for ln in text.split("\n") if not re.search(r"https?://|\d{7,}", ln))


def short_stand_in(row):
    return {k: row[k] for k in G.ROW_KEYS if k in row and k != "body"}


def ev(i="e1", **kw):
    row = {"id": i, "start": "10:00", "end": "11:00", "all_day": False, "title": "Budget review", "where": "Room 204", "teams": True,
           "private": False, "organiser": "Mia Hale", "sensitivity": "normal", "body": f"Agenda: budget\n{LINK}\nRisks and plan"}
    row.update(kw)
    return row


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.saved = (G.FILTER, G.SHORT, G.LOCK, paths.CALENDAR, sweep.CAL_LOCK)
        G.FILTER, G.SHORT, G.LOCK = stand_in, short_stand_in, d / "calendar.lock"
        paths.CALENDAR, sweep.CAL_LOCK = d / "calendar.json", G.LOCK
        G.clear_cache()

    def tearDown(self):
        G.FILTER, G.SHORT, G.LOCK, paths.CALENDAR, sweep.CAL_LOCK = self.saved
        G.clear_cache()
        self.tmp.cleanup()

    def put(self, days, **top):
        paths.CALENDAR.write_text(json.dumps({"fetched": "2026-10-20 08:00", "to": "2026-11-01", "days": days, **top}), encoding="utf-8")

    def load(self):
        return json.loads(paths.CALENDAR.read_text(encoding="utf-8"))

    def rows(self):
        return [r for rows in self.load()["days"].values() for r in rows]


class Rescrub(Base):
    def test_stamps_old_rows_and_filters_their_body(self):
        self.put({"2026-10-26": [ev("a"), ev("b")]})
        self.assertGreater(sweep.rescrub_calendar(), 0)
        for r in self.rows():
            self.assertEqual(r["clean"], G.CLEAN)
            self.assertNotIn("https", r["body"])
            self.assertIn("Risks and plan", r["body"])
        self.assertEqual(self.load()["clean"], G.CLEAN)

    def test_non_body_fields_of_unstamped_rows_unchanged(self):
        self.put({"2026-10-26": [ev("a")]})
        sweep.rescrub_calendar()
        r = self.rows()[0]
        for k, v in ev("a").items():
            if k != "body":
                self.assertEqual(r[k], v, k)

    def test_second_run_changes_nothing_bytes_identical(self):
        self.put({"2026-10-26": [ev("a")]})
        sweep.rescrub_calendar()
        first = paths.CALENDAR.read_bytes()
        self.assertEqual(sweep.rescrub_calendar(), 0)
        self.assertEqual(paths.CALENDAR.read_bytes(), first)

    def test_stamped_row_kept_as_stored(self):
        stamped = G.clean_row(ev("s"))
        self.put({"2026-10-26": [stamped, ev("u")]})
        sweep.rescrub_calendar()
        rows = {r["id"]: r for r in self.rows()}
        self.assertEqual(rows["s"], stamped)
        self.assertEqual(rows["u"]["clean"], G.CLEAN)

    def test_file_shape_unchanged(self):
        self.put({"2026-10-26": [ev("a", description="x", joinUrl="https://x.test")]}, note="stray")
        sweep.rescrub_calendar()
        cal = self.load()
        self.assertEqual(set(cal), {"fetched", "to", "days", "clean", "clean_v"})
        for r in self.rows():
            self.assertLessEqual(set(r), set(G.ROW_KEYS) | {"clean", "clean_v"})

    def test_served_as_stored_after_rescrub(self):
        self.put({"2026-10-26": [ev("a")]})
        sweep.rescrub_calendar()
        calls = []
        G.FILTER = lambda t: calls.append(t) or t           # a read must not filter a stamped row again
        G.clear_cache()
        out = G.read("agenda", paths.CALENDAR)["days"]["2026-10-26"][0]
        self.assertEqual(calls, [])
        self.assertIn("Risks and plan", out["body"])

    def test_no_temp_file_left_when_the_write_fails(self):
        self.put({"2026-10-26": [ev("a")]})
        before = paths.CALENDAR.read_bytes()
        orig = os.replace
        os.replace = lambda *a, **k: (_ for _ in ()).throw(OSError("disk"))
        try:
            with self.assertRaises(OSError):
                sweep.rescrub_calendar()
        finally:
            os.replace = orig
        self.assertEqual(paths.CALENDAR.read_bytes(), before)
        self.assertEqual([p.name for p in paths.CALENDAR.parent.glob("*.tmp")], [])

    def test_lock_contention_falls_back_without_the_lock(self):
        import fcntl
        self.put({"2026-10-26": [ev("a")]})
        fd = os.open(str(G.LOCK), os.O_RDWR | os.O_CREAT, 0o644)
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            self.assertGreater(sweep.rescrub_calendar(wait=0.1), 0)       # never skips
        finally:
            os.close(fd)
        self.assertTrue(all(r.get("clean") == G.CLEAN for r in self.rows()))

    def test_one_lock_file(self):
        self.assertEqual(sweep.CAL_LOCK, G.LOCK)
        got = []

        def other():
            with G.lock(0.1) as g:
                got.append(g)
        with sweep.calendar_lock(1) as a:
            t = threading.Thread(target=other)
            t.start()
            t.join()
        self.assertTrue(a)
        self.assertEqual(got, [False])


class Held(Base):
    def test_stamped_held_row_keeps_its_stamp(self):
        stamped = G.clean_row(ev("h"))
        self.put({"2026-10-20": [stamped]})
        days = sweep.keep_held_past_days({}, "2026-10-19", "2026-10-26")
        self.assertEqual(days["2026-10-20"], [stamped])

    def test_unstamped_held_row_is_filtered_before_it_is_stamped(self):
        self.put({"2026-10-20": [ev("h")]})
        row = sweep.keep_held_past_days({}, "2026-10-19", "2026-10-26")["2026-10-20"][0]
        self.assertEqual(row["clean"], G.CLEAN)
        self.assertNotIn("https", row["body"])

    def test_unfilterable_body_is_dropped_never_stamped_raw(self):
        def boom(t):
            raise RuntimeError("x")
        G.FILTER = boom
        self.put({"2026-10-20": [ev("h")]})
        row = sweep.keep_held_past_days({}, "2026-10-19", "2026-10-26")["2026-10-20"][0]
        self.assertNotIn("body", row)

    def test_future_and_outside_days_not_held(self):
        self.put({"2026-10-27": [ev("f")], "2026-10-01": [ev("o")]})
        self.assertEqual(sweep.keep_held_past_days({}, "2026-10-19", "2026-10-26"), {})


class Save(Base):
    def test_sweep_save_stamps_every_row_and_serves_as_stored(self):
        self.put({"2026-10-26": [ev("h")]})              # an old unstamped held day (a Monday; the clock below is the Wednesday)
        os.environ["CREAITE_NOW"] = "2026-10-28 09:00"
        try:
            spec = Path(self.tmp.name) / "spec.json"
            spec.write_text(json.dumps({"days": {"2026-10-28": [
                {"id": "n1", "start": "2026-10-28T10:00", "end": "2026-10-28T11:00", "title": "Plan", "body": f"Hello\n{LINK}"},
                {"id": "n2", "start": "2026-10-28T12:00", "end": "2026-10-28T13:00", "title": "Sync", "sensitivity": "confidential",
                 "body": "secret"}]}}), encoding="utf-8")
            self.assertEqual(sweep.calendar(str(spec)), 0)
        finally:
            os.environ.pop("CREAITE_NOW", None)
        cal = self.load()
        self.assertEqual(cal["clean"], G.CLEAN)
        rows = self.rows()
        self.assertGreaterEqual(len(rows), 3)
        for r in rows:
            self.assertEqual(r["clean"], G.CLEAN)
            self.assertLessEqual(set(r), set(G.ROW_KEYS) | {"clean", "clean_v"})
            self.assertNotIn("https", r.get("body", ""))
        conf = [r for r in rows if r["id"] == "n2"][0]
        self.assertNotIn("body", conf)
        calls = []
        G.FILTER = lambda t: calls.append(t) or t
        G.clear_cache()
        out = G.read("agenda", paths.CALENDAR)["days"]["2026-10-28"]
        self.assertEqual(calls, [])
        self.assertEqual([r["id"] for r in out], [r["id"] for r in cal["days"]["2026-10-28"]])


if __name__ == "__main__":
    unittest.main()
