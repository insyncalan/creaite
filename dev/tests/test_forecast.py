"""BL-184 (sprint-milestones): the slip range, proved on fixtures (the live vault has no slip history yet). forecast.py replays
change_log: slips are forecast moves later, a rebaseline isn't one, undone applies are skipped, the class needs at least 8 closed
milestones, the 50th and 80th percentiles of the remaining slip give the range, and it never reaches client output.

Run: python3 dev/tests/test_forecast.py
"""
import json
import sys
import unittest
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import Vault  # noqa: E402

TODAY = date.today()


def d(n):
    return (TODAY + timedelta(days=n)).isoformat()


def ok(items):
    for n, i in enumerate(items, 1):
        i.update({"n": n, "match": "strong", "flags": [], "decision": "approved"})
    return items


def new(name, fc, **v):
    return {"op": "new", "table": "milestones", "values": {"project": "ABC", "name": name, "baseline_date": fc, "forecast_date": fc,
                                                             "source": "fixture", **v}}


def upd(id_, **ch):
    return {"op": "update", "table": "milestones", "id": id_, "changes": ch}


class Forecast(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.n = 0

    def tearDown(self):
        self.v.cleanup()

    def apply(self, items):
        self.n += 1
        self.v.propose(f"f{self.n:03d}", ok(items))
        self.v.run("apply")

    def closed(self, j, slips=1, remaining=0):
        """A closed milestone: first forecast, `slips` moves later by 10 days each, then achieved `remaining` days after the last."""
        self.apply([new(f"Closed {j}", d(-90))])
        mid = max(m["id"] for m in self.v.rows("milestones"))
        fc = -90
        for _ in range(slips):
            fc += 10
            self.apply([upd(mid, forecast_date=d(fc))])
        self.apply([upd(mid, status="Done", actual_date=d(fc + remaining))])
        return mid

    def open_ms(self, slips=1):
        self.apply([new("Open one", d(30))])
        mid = max(m["id"] for m in self.v.rows("milestones"))
        for i in range(slips):
            self.apply([upd(mid, forecast_date=d(40 + 10 * i))])
        return mid

    def ranges(self):
        sys.path.insert(0, str(self.v.root / "system/scripts"))
        import tracker
        import importlib
        import forecast
        importlib.reload(forecast)
        with closing(tracker.connect(self.v.root / "system/tracker.db")) as con:
            return forecast.ranges(con)

    def test_the_range_needs_eight_closed_milestones_and_uses_the_50th_and_80th_percentiles(self):
        for j in range(7):
            self.closed(j, slips=1, remaining=2 * j)
        o = self.open_ms(slips=1)
        r = self.ranges()[o]
        self.assertEqual((r["ok"], r["n"], r["k"]), (False, 7, 1))
        self.assertEqual(r["text"], "No range yet: 7 of 8 closed milestones with history")
        self.closed(7, slips=1, remaining=14)                     # remaining slips 0, 2, … 14: P50 7, P80 11.2
        r = self.ranges()[o]
        self.assertTrue(r["ok"])
        self.assertEqual((r["lo"], r["hi"]), (d(40 + 7), d(40 + 11)))
        self.assertTrue(r["thin"])                                 # one project, fewer than five
        self.assertIn("thin evidence", r["text"])
        out = self.v.run("range", "ABC", script="forecast.py").stdout
        self.assertIn(f"Likely {d(47)[8:10]}-{d(47)[5:7]}-{d(47)[:4]}", out)

    def test_only_closed_milestones_with_at_least_as_many_slips_count(self):
        for j in range(8):
            self.closed(j, slips=1, remaining=3)
        for j in range(3):
            self.closed(10 + j, slips=2, remaining=1)
        o = self.open_ms(slips=2)
        r = self.ranges()[o]
        self.assertEqual((r["k"], r["n"], r["ok"]), (2, 3, False))   # only the three with two slips
        o0 = self.open_ms(slips=0)
        self.assertEqual(self.ranges()[o0]["n"], 11)                 # with no slips yet, every closed one counts

    def test_a_rebaseline_is_not_a_slip_and_an_undone_apply_is_skipped(self):
        o = self.open_ms(slips=0)
        self.apply([dict(upd(o, baseline_date=d(60)), rebaseline={"agreed_with": "Sara Example", "reason": "Steering", "source": "minutes"})])
        self.assertEqual(self.ranges()[o]["k"], 0)
        self.apply([upd(o, forecast_date=d(70))])
        self.assertEqual(self.ranges()[o]["k"], 1)
        self.v.run("undo")
        self.assertEqual(self.ranges()[o]["k"], 0)

    def test_it_is_internal_only(self):
        for j in range(8):
            self.closed(j, slips=1, remaining=2 * j)
        o = self.open_ms(slips=1)
        self.apply([upd(o, client_visible=1, client_message="Testing a little later than agreed.")])
        weekly = json.loads(self.v.run("weekly-data", "ABC", script="report.py").stdout)
        self.assertTrue(any((m.get("likely") or "").startswith("Likely") for m in weekly["milestones"]))   # the internal weekly facts
        client = self.v.run("client-data", "ABC", "--since", d(-120), script="report.py").stdout
        steer = self.v.run("steerco-data", "ABC", "--version", "client", script="report.py").stdout
        facts = self.v.run("facts", "ABC", "--audience", "client", "--from", d(-120), "--to", d(0), script="status_facts.py").stdout
        for text in (client, steer, facts):
            self.assertNotIn("Likely", text)
            self.assertNotIn("likely", text)
        self.v.run(script="build_dashboard.py")
        html = (self.v.root / "dashboard.html").read_text(encoding="utf-8")
        self.assertIn('"range": {', html.replace('"range":{', '"range": {'))      # the page has it, for Movement


if __name__ == "__main__":
    unittest.main()
