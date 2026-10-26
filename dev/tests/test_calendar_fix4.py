"""#375 E1, fix4 (Banner's review of the reader migration): H1 organiser address in Prep, H2 stamped rows re-filtered when the stamp does
not match the filter, M1 bare confidential on a stamped row, M2 the rescrub's stamped test, timing.

Run: python3 dev/tests/test_calendar_fix4.py      (quick tier: plain code, a throwaway folder). Fictional data only.
"""
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "system" / "scripts"))
import calendar_gateway as G  # noqa: E402
import paths  # noqa: E402
import sweep  # noqa: E402

DIRTY = {"title": "Join https://zoom.us/j/1234567890 pwd=abc", "where": "Meeting ID 845 344 731 674",
         "attendees": [{"name": "PIN 4417", "email": "x@y.example"}],
         "body": "Passcode: 4417\nJoin https://teams.microsoft.com/l/meetup-join/abc"}


def stand_in(text):
    return "\n".join(ln for ln in text.split("\n") if "http" not in ln and "Passcode" not in ln)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.saved = (G.LOCK, paths.CALENDAR, sweep.CAL_LOCK, G.FILTER)
        G.LOCK = sweep.CAL_LOCK = d / "calendar.lock"
        paths.CALENDAR = d / "calendar.json"
        G.clear_cache()

    def tearDown(self):
        G.LOCK, paths.CALENDAR, sweep.CAL_LOCK, G.FILTER = self.saved
        G.clear_cache()
        self.tmp.cleanup()

    def put(self, rows):
        paths.CALENDAR.write_text(json.dumps({"fetched": "x", "to": "y", "days": {"2026-10-27": rows}}), encoding="utf-8")

    def get(self, purpose="agenda"):
        G.clear_cache()
        return G.read(purpose, paths.CALENDAR)["days"]["2026-10-27"]


class H2(Base):
    def test_a_bare_stamp_does_not_skip_the_filter(self):
        for stamp in (1, 10 ** 30):
            self.put([{"id": "a", "start": "09:00", "sensitivity": "normal", "clean": stamp, **DIRTY}])
            r = self.get()[0]
            blob = json.dumps(r)
            for leak in ("zoom.us", "845 344", "4417", "teams.microsoft"):
                self.assertNotIn(leak, blob, stamp)

    def test_an_old_filter_version_is_filtered_again(self):
        self.put([{"id": "a", "start": "09:00", "sensitivity": "normal", "clean": G.CLEAN, "clean_v": "f0", **DIRTY}])
        self.assertNotIn("4417", json.dumps(self.get()))

    def test_a_row_stamped_by_clean_row_is_served_as_stored(self):
        G.FILTER = stand_in
        row = G.clean_row({"id": "a", "start": "09:00", "sensitivity": "normal", "title": "Plan", "body": "Agenda\nBudget"})
        self.assertEqual(row["clean_v"], G.fingerprint())
        self.put([row])
        self.assertEqual(self.get()[0]["body"], "Agenda\nBudget")
        self.assertEqual(G.clean_row(row), row)                                # idempotent

    def test_mutant_ignoring_clean_v_is_caught(self):
        was = G.is_stamped
        try:
            G.is_stamped = lambda r: isinstance(r.get("clean"), int)           # the old rule
            self.put([{"id": "a", "start": "09:00", "sensitivity": "normal", "clean": 1, **DIRTY}])
            self.assertIn("4417", json.dumps(self.get()), "the mutant must leak, or the tests above prove nothing")
        finally:
            G.is_stamped = was

    def test_timing_3000_stamped_rows_read_fast(self):
        G.FILTER = stand_in
        rows = [G.clean_row({"id": f"i{i}", "start": "09:00", "sensitivity": "normal", "title": f"Sync {i}", "body": "Agenda\n" * 20,
                             "attendees": [{"name": f"P{j}", "email": f"p{j}@x.example"} for j in range(8)]}) for i in range(3000)]
        self.put(rows)
        t = time.process_time()
        G.clear_cache()
        out = G.read("agenda", paths.CALENDAR)["days"]["2026-10-27"]
        took = time.process_time() - t
        self.assertEqual(len(out), 3000)
        self.assertLess(took, 3.0, f"cache fill took {took:.2f}s cpu")


class M1M2(Base):
    def test_m1_bare_confidential_on_a_stamped_row_is_kept(self):
        G.FILTER = stand_in
        base = G.clean_row({"id": "a", "start": "09:00", "sensitivity": "normal", "title": "Plan"})
        row = {**base, "confidential": True, "body": "Secret plan", "attendees": [{"name": "Sam", "email": "s@x.example"}]}
        self.put([row])
        for purpose in ("agenda", "prep_panel", "intake", "shape"):
            r = self.get(purpose)[0]
            self.assertEqual(r["sensitivity"], "confidential", purpose)
            self.assertNotIn("body", r)
            self.assertNotIn("attendees", r)
        self.assertEqual(G.stamp_row(row)["sensitivity"], "confidential")       # what the rescrub writes back

    def test_m2_the_rescrub_does_not_keep_a_malformed_stamped_row(self):
        G.FILTER = stand_in
        base = G.clean_row({"id": "a", "start": "09:00", "sensitivity": "normal", "title": "Plan"})
        bad = {**base, "title": "Join https://zoom.us/j/1234567890", "private": "yes", "body": "Passcode: 4417", "attendees": "x"}
        self.put([bad])
        sweep.rescrub_calendar()
        at_rest = json.dumps(json.loads(paths.CALENDAR.read_text(encoding="utf-8")))
        self.assertNotIn("zoom.us", at_rest)
        self.assertNotIn("4417", at_rest)


if __name__ == "__main__":
    unittest.main()
