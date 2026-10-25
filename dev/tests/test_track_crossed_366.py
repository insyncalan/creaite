"""#366 step 3: the review kit's k26-d `apply` and `promise` probes as tests (Track from Review, #275; the minutes view v2, #268).

The kit (team-cap-reviewkit-26d, src/k26/d275.py) checked two server paths that test_minutes_track_review and test_minutes_track_ops
cover only in part:
- tracker.py apply's own stop (track_problems, the guarded tracker-track-problems.diff, now in tracker.py): an item Alan crossed or
  left with neither in the minutes' Track column, then approved by hand (a proposal edited by hand, a stale page's save), is never
  registered; the apply stops as a whole and the item goes back to Review. The existing test of it skips when the check is missing;
  these never skip, and a mutant (the check taken out of the vault's own copy of tracker.py) shows they would see the leak.
- a promise has no row in the minutes, so Approve minutes never registers it, whatever the caller sends: with the group ticked and
  with the promise's own number in `own`. The existing tests send only what track.js would (group false), and need Node.

Fictional data (test_minutes_approve's steering committee: 1 = "Book the UAT environment" action, 2 = "Test data isn't anonymised"
issue, 3 = the update of ABC-A-001's due date to 2026-10-30, 4 = a decision).

Run: python3 dev/tests/test_track_crossed_366.py      (quick tier: no Chrome, no Node)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_minutes_approve as ma  # noqa: E402

UAT, DATA = "Book the UAT environment", "Test data isn't anonymised"
CHECK = "        blocked += track_problems(p, data)"
ROWED = "    allowed = minutes_record.track_rowed(minutes_record.creaite_doc.read(draft), data)"


class ApplyStop(ma.Base):
    """tracker.py apply stops an approved item the Track column crossed or left with neither, by any path."""
    def track(self, choices):
        self.js("import minutes_record, creaite_doc\n"
                f"d = creaite_doc.read({ma.DRAFT!r})\nd['layout'] = {{**(d.get('layout') or {{}}), 'track': {choices!r}}}\n"
                f"r = minutes_record.save_page({ma.DRAFT!r}, d)\nprint(json.dumps({{'ok': bool(r.get('ok'))}}))")

    def item(self, n):
        return next(i for i in self.data()["items"] if i["n"] == n)

    def set_decision(self, n, decision):
        p = self.v.root / "system/staging" / self.name
        data = json.loads(p.read_text(encoding="utf-8"))
        next(i for i in data["items"] if i["n"] == n)["decision"] = decision
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def registered(self):
        return [a["description"] for a in self.v.rows("actions")] + [r["description"] for r in self.v.rows("raid")]

    def test_apply_stops_an_item_left_with_neither_and_approved_by_hand(self):
        self.track({"2": ""})
        self.set_decision(2, "approved")
        r = self.v.run("apply", ok=False)
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertIn("item 2:", r.stdout + r.stderr)
        self.assertNotIn(DATA, self.registered(), "an item kept in the minutes only is never a work item")
        self.assertEqual(self.item(2)["decision"], "pending", "back in Review's queue")

    def test_apply_stops_the_whole_batch_when_a_crossed_item_is_approved_by_hand(self):
        self.track({"1": "n"})
        self.set_decision(1, "approved")
        self.set_decision(3, "approved")                       # an ordinary approved item in the same proposal
        r = self.v.run("apply", ok=False)
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertIn("crossed in the minutes' Track column", r.stdout + r.stderr)
        self.assertNotIn(UAT, self.registered())
        self.assertEqual(self.by_id("actions")["ABC-A-001"]["due_date"], "2026-10-20", "nothing of the stopped apply is written")
        self.assertEqual((self.item(1)["decision"], self.item(3)["decision"]), ("pending", "approved"))

    def test_apply_stops_both_a_crossed_and_a_neither_item_and_names_each(self):
        self.track({"1": "n", "2": ""})
        self.set_decision(1, "approved")
        self.set_decision(2, "approved")
        r = self.v.run("apply", ok=False)
        out = r.stdout + r.stderr
        self.assertNotEqual(r.returncode, 0, out)
        self.assertIn("item 1:", out)
        self.assertIn("item 2:", out)
        self.assertFalse({UAT, DATA} & set(self.registered()))

    def test_mutant_without_the_check_the_crossed_item_is_registered(self):
        """Proof the tests above see the leak: take the check out of this vault's own tracker.py (never the repo's)."""
        script = self.v.root / "system/scripts/tracker.py"
        text = script.read_text(encoding="utf-8")
        self.assertEqual(text.count(CHECK), 1, "the apply check's call moved: update CHECK")
        script.write_text(text.replace(CHECK, "        pass", 1), encoding="utf-8")
        self.track({"1": "n"})
        self.set_decision(1, "approved")
        self.v.run("apply")
        self.assertIn(UAT, self.registered(), "without track_problems the crossed item is registered, so the stop is what holds it")


class RowlessPromise(ma.Base):
    """A promise has no row in the minutes, so Approve minutes never registers it, whatever approve_minutes is sent."""
    def setUp(self):
        super().setUp()
        f = self.v.root / "system/staging/drafts/promise.json"
        f.write_text(json.dumps({
            "title": "[ABC] Promise check-in", "date": "2026-10-14", "projects": ["ABC"],
            "minutes": {"start": "12:00", "end": "12:30", "summary": ["A short check-in."], "chat": False},
            "items": [{"table": "actions", "values": {"project": "ABC", "description": "Draft the cutover runbook", "owner": "Jane Doe"}},
                      {"table": "promises", "section": "Jane Doe, 12:05", "values": {
                          "project": "ABC", "promised_by": "Jane Doe", "promised_to": "Alan Carter",
                          "description": "Send the vendor's rate card", "due_date": "2026-10-20"}}]}), encoding="utf-8")
        before = {p.name for p in (self.v.root / "system/staging").glob("proposed-*.json")}
        self.v.run("stage", str(f), script="minutes.py")
        self.name = next(p.name for p in (self.v.root / "system/staging").glob("proposed-*.json") if p.name not in before)

    def promises(self):
        return [p["description"] for p in self.v.rows("promises")]

    def promise_decision(self):
        return next(i["decision"] for i in self.data()["items"] if i.get("table") == "promises")

    def test_the_group_ticked_registers_the_action_never_the_promise(self):
        r = self.approve(group=True, own=[])
        self.assertTrue(r["ok"], r)
        self.assertIn("Draft the cutover runbook", [a["description"] for a in self.v.rows("actions")], "control: the ticked row")
        self.assertNotIn("Send the vendor's rate card", self.promises(), "a promise nobody saw is never registered")
        self.assertEqual(self.promise_decision(), "pending", "the promise waits in Review")

    def test_the_promise_sent_by_number_is_still_never_registered(self):
        r = self.approve(group=True, own=[2])
        self.assertTrue(r["ok"], r)
        self.assertNotIn("Send the vendor's rate card", self.promises())
        self.assertEqual(self.promise_decision(), "pending")
        self.assertEqual(r["waiting"], [2], r)

    def test_review_py_approve_on_the_minutes_never_registers_the_promise(self):
        rows = json.loads(self.v.run("list", "--json", script="review.py").stdout)
        n = next(r["n"] for r in rows if r["file"] == self.name and r["ref"] == "meeting")
        self.v.run("approve", str(n), script="review.py")
        self.v.run("apply", ok=False)
        self.assertIn("Draft the cutover runbook", [a["description"] for a in self.v.rows("actions")], "control: the ticked row")
        self.assertNotIn("Send the vendor's rate card", self.promises())
        self.assertEqual(self.promise_decision(), "pending")

    def test_mutant_without_the_row_check_the_promise_is_registered(self):
        """Proof the tests above see the leak: take track_rowed out of this vault's own review.py (never the repo's)."""
        script = self.v.root / "system/scripts/review.py"
        text = script.read_text(encoding="utf-8")
        self.assertEqual(text.count(ROWED), 1, "approve_minutes' row check moved: update ROWED")
        script.write_text(text.replace(ROWED, "    allowed = None", 1), encoding="utf-8")
        self.assertTrue(self.approve(group=True, own=[])["ok"])
        self.assertIn("Send the vendor's rate card", self.promises(), "without track_rowed the group tick takes the promise too")


if __name__ == "__main__":
    unittest.main()
