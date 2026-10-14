"""BL-315 (v1.9.2), server side: Rejects, in real life. The seven reasons and no reason, creaite's guess per row, rejecting one or many
with a reason or with each row's guess, and every reject undone, its reason changed or approved instead, before and after apply (the
`rejected` row follows the latest choice and undo puts it back), Activity's list and Quality's counts, and the live server's routes.

Run: python3 dev/tests/test_rejects_real_life.py
"""
import json
import os
import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import Vault, action  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system" / "scripts"))
NOW = "2026-10-14 09:00"
SEVEN = ["Not an action", "Duplicate", "Chatter", "Already done", "Wrong project", "Doesn't need tracking", "For another team"]


def pending(item, **kw):
    return {**item, "decision": "pending", **kw}


class Case(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.cleanup)
        self.v.run("init")
        self.v.run("migrate")
        self.v.propose("seed", [action(1, description="Send the revised statement of work to the client", due_date="2026-10-20"),
                                action(2, description="Order the test licences for the UAT team", status="Closed",
                                       closed="2026-10-10", due_date="2026-10-09")])
        self.v.run("apply")
        ids = {r["description"]: r["id"] for r in self.v.rows("actions")}
        self.open_id = ids["Send the revised statement of work to the client"]
        self.closed_id = ids["Order the test licences for the UAT team"]

    def run_(self, script, *args, ok=True):
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts" / script), *args], cwd=self.v.root,
                           env={**os.environ, "CREAITE_NOW": NOW}, capture_output=True, text=True)
        if ok and r.returncode != 0:
            raise AssertionError(f"{script} {args}: {r.stdout}{r.stderr}")
        return r

    def review(self, *args, ok=True):
        return self.run_("review.py", *args, ok=ok)

    def numbers(self, name):
        rows = json.loads(self.review("list", "--json").stdout)
        return {r["ref"]: r["n"] for r in rows if r["file"] == f"proposed-{name}.json"}

    def item(self, name, n):
        for d in ("system/staging", "system/staging/applied"):
            p = self.v.root / d / f"proposed-{name}.json"
            if p.exists():
                return next(i for i in json.loads(p.read_text())["items"] if i["n"] == n), d
        raise AssertionError(f"proposed-{name}.json is nowhere")

    def rejected_rows(self):
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            return con.execute("SELECT reason, duplicate_of FROM rejected ORDER BY rowid").fetchall()

    def five(self):
        """Five pending proposals, one for each guess and one with none."""
        self.v.propose("five", [
            pending(action(1, description="Thanks all for joining, great session")),                         # Chatter (thanks)
            pending(action(2, description="Send the revised statement of work to the client please")),       # Duplicate
            pending(action(3, description="Book a room for the offsite", owner="")),                           # no owner
            pending(action(4, description="Check calendars for a workshop next week", owner="")),             # Chatter (scheduling)
            pending(action(5, description="Prepare the migration cut-over runbook", owner="Sara Example")),   # no guess
            pending({"n": 6, "op": "update", "table": "actions", "id": self.closed_id, "match": "strong", "flags": [],
                     "changes": {"status": "Closed", "closed": "2026-10-12"}, "source": "Email · test"}),           # Already done
        ], source_run="cx-minutes")                                                     # counted by Quality
        return self.numbers("five")


class Reasons(Case):
    def test_the_seven_reasons(self):
        self.assertEqual(json.loads(self.review("reasons", "--json").stdout), SEVEN)
        import tracker
        self.assertEqual(list(tracker.REJECT_REASONS), SEVEN)

    def test_guesses(self):
        n = self.five()
        got = {g["ref"]: g for g in json.loads(self.review("guesses", "--json").stdout) if g["file"] == "proposed-five.json"}
        self.assertEqual(got[1]["reason"], "Chatter")
        self.assertEqual((got[2]["reason"], got[2]["of"]), ("Duplicate", self.open_id))
        self.assertEqual(got[3]["reason"], "Doesn't need tracking")
        self.assertEqual(got[4]["reason"], "Chatter")
        self.assertNotIn(5, got)
        self.assertEqual((got[6]["reason"], got[6]["of"]), ("Already done", self.closed_id))
        self.assertEqual(got[1]["n"], n[1])
        # with Spot repeats off, no repeat is guessed
        cfg = self.v.root / "system/config/settings.json"
        s = json.loads(cfg.read_text())
        s["drafting"] = {**(s.get("drafting") or {}), "repeat": False}
        cfg.write_text(json.dumps(s))
        got = {g["ref"]: g for g in json.loads(self.review("guesses", "--json").stdout) if g["file"] == "proposed-five.json"}
        self.assertNotIn(2, got)

    def test_use_each_guess_then_apply(self):
        n = self.five()
        out = self.review("reject", ",".join(str(n[k]) for k in (1, 2, 3, 5)), "--guess").stdout
        self.assertIn("Rejected 4", out)
        self.assertEqual(self.item("five", 1)[0]["reject_reason"], "Chatter")
        self.assertEqual((self.item("five", 2)[0]["reject_reason"], self.item("five", 2)[0]["duplicate_of"]), ("Duplicate", self.open_id))
        self.assertEqual(self.item("five", 3)[0]["reject_reason"], "Doesn't need tracking")
        self.assertNotIn("reject_reason", self.item("five", 5)[0])                      # no guess: no reason
        self.assertTrue(self.item("five", 5)[0]["rejected_at"])
        self.run_("tracker.py", "apply")
        self.assertEqual(sorted(self.rejected_rows(), key=str),
                         sorted([("Chatter", None), ("Duplicate", self.open_id), ("Doesn't need tracking", None), (None, None)], key=str))

    def test_many_with_one_reason_any_case(self):
        n = self.five()
        self.review("reject", f"{n[3]},{n[4]}", "--reason=for another team")
        self.assertEqual({self.item("five", k)[0]["reject_reason"] for k in (3, 4)}, {"For another team"})
        self.review("reject", str(n[5]), "because", "wrong", "project")
        self.assertEqual(self.item("five", 5)[0]["reject_reason"], "Wrong project")


class Redecide(Case):
    def setUp(self):
        super().setUp()
        self.n = self.five()
        self.key = lambda k: f"proposed-five.json#{k}"

    def test_before_apply_undo_and_change_the_reason(self):
        self.review("reject", str(self.n[1]), "--reason=Chatter")
        self.review("rereason", self.key(1), "--reason=Not an action")
        self.assertEqual(self.item("five", 1)[0]["reject_reason"], "Not an action")
        out = json.loads(self.review("unreject", self.key(1), "--json").stdout.splitlines()[-1])
        self.assertEqual(out["done"][0]["was"]["reason"], "Not an action")
        it = self.item("five", 1)[0]
        self.assertEqual(it["decision"], "pending")
        self.assertNotIn("reject_reason", it)
        self.assertNotIn("redecide", it)
        self.assertIn(1, self.numbers("five"))                                          # back in Review
        r = self.review("unreject", self.key(1), ok=False)                               # no longer rejected
        self.assertIn("isn't rejected", r.stderr + r.stdout)

    def test_after_apply_the_reason_changes_and_undo_restores_it(self):
        self.review("reject", str(self.n[1]), "--reason=Chatter")
        self.run_("tracker.py", "apply")
        before = self.v.rows("change_log")
        self.review("rereason", self.key(2), ok=False)                                   # pending, not rejected
        self.review("rereason", self.key(1), "--reason=Doesn't need tracking")
        it, where = self.item("five", 1)
        self.assertEqual(where, "system/staging")                                         # back out of applied/ if it was there
        self.assertTrue(it["redecide"]["fingerprint"])
        self.assertNotIn(1, self.numbers("five"))                                        # still rejected: not pending in Review
        self.run_("tracker.py", "apply")
        self.assertIn(("Doesn't need tracking", None), self.rejected_rows())
        self.assertEqual(len(self.rejected_rows()), 1)
        new = [c for c in self.v.rows("change_log") if c not in before and c["tbl"] == "rejected"]
        self.assertEqual([(c["field"], c["old_value"], c["new_value"], c["op"]) for c in new],
                         [("reason", "Chatter", "Doesn't need tracking", "update")])
        # a duplicate needs a real item
        r = self.review("rereason", self.key(1), "--duplicate-of=ABC-A-999", ok=False)
        self.assertIn("no ABC-A-999", r.stdout)
        self.run_("tracker.py", "undo")
        self.assertEqual(self.rejected_rows(), [("Chatter", None)])                       # undo restores the reason

    def test_after_apply_undo_the_reject_and_reject_again(self):
        self.review("reject", str(self.n[1]), "--reason=Chatter")
        self.run_("tracker.py", "apply")
        self.review("unreject", self.key(1))
        it = self.item("five", 1)[0]
        self.assertEqual(it["decision"], "pending")
        self.assertIn(1, self.numbers("five"))
        # rejected again with another reason: the same row is updated, not a second one
        self.review("reject", str(self.numbers("five")[1]), "--reason=Not an action")
        self.run_("tracker.py", "apply")
        self.assertEqual(self.rejected_rows(), [("Not an action", None)])

    def test_after_apply_approve_instead_writes_it_and_undo_puts_the_reject_back(self):
        self.review("reject", f"{self.n[5]}", "--reason=Wrong project")
        self.run_("tracker.py", "apply")
        self.assertEqual(self.rejected_rows(), [("Wrong project", None)])
        out = json.loads(self.review("approve-instead", self.key(5), "--json").stdout.splitlines()[-1])
        self.assertEqual((len(out["done"]), out["open"]), (1, []))
        self.assertEqual(self.item("five", 5)[0]["decision"], "approved")
        self.run_("tracker.py", "apply")
        self.assertEqual(self.rejected_rows(), [])                                        # the reject is gone
        self.assertIn("Prepare the migration cut-over runbook", [r["description"] for r in self.v.rows("actions")])
        self.run_("tracker.py", "undo")
        self.assertEqual(self.rejected_rows(), [("Wrong project", None)])                 # back as it was
        self.assertNotIn("Prepare the migration cut-over runbook", [r["description"] for r in self.v.rows("actions")])
        self.assertEqual(self.item("five", 5)[0]["decision"], "pending")                  # and in Review, as any undo leaves it

    def test_approve_instead_opens_an_item_approved_only_on_its_own(self):
        self.v.propose("risk", [pending({"n": 1, "op": "new", "table": "raid", "match": "strong", "flags": [],
                                         "values": {"project": "ABC", "type": "Risk", "description": "Vendor exits the market",
                                                    "impact": "High", "likelihood": "Low", "raised": "2026-10-01",
                                                    "source": "Email · test"}})])
        self.review("reject", str(self.numbers("risk")[1]), "--reason=Not an action")
        self.run_("tracker.py", "apply")
        out = json.loads(self.review("approve-instead", "proposed-risk.json#1", "--json").stdout.splitlines()[-1])
        self.assertEqual((out["done"], out["open"]), ([], ["proposed-risk.json#1"]))
        it = self.item("risk", 1)[0]
        self.assertEqual(it["decision"], "pending")
        self.assertNotIn("reject_reason", it)
        self.assertIn(1, self.numbers("risk"))                                            # in Review, for its own approval

    def test_rejects_activity_and_quality_follow_the_latest_choice(self):
        self.review("reject", f"{self.n[1]},{self.n[3]}", "--reason=Chatter")
        self.run_("tracker.py", "apply")
        rows = json.loads(self.review("rejects", "--json").stdout)
        self.assertEqual({r["key"] for r in rows}, {self.key(1), self.key(3)})
        self.assertTrue(all(r["applied"] and r["reason"] == "Chatter" for r in rows))
        q = json.loads(self.run_("quality.py", "--json").stdout)
        self.assertEqual({r["reason"]: r["n"] for r in q["reasons"]}, {"Chatter": 2})
        self.review("rereason", self.key(3), "--reason=Doesn't need tracking")
        self.review("approve-instead", self.key(1))
        self.run_("tracker.py", "apply")
        q = json.loads(self.run_("quality.py", "--json").stdout)
        self.assertEqual({r["reason"]: r["n"] for r in q["reasons"]}, {"Doesn't need tracking": 1})
        self.assertEqual({r["key"]: r["reason"] for r in json.loads(self.review("rejects", "--json").stdout)},
                         {self.key(3): "Doesn't need tracking"})
        # Activity: one line for the changed reject, with its new reason; none for the one approved instead
        sys.path.insert(0, str(self.v.root / "system/scripts"))
        r = subprocess.run([sys.executable, "-c", "import json,sys; sys.path.insert(0,'system/scripts'); import build_dashboard as b, "
                            "tracker; print(json.dumps(b.rejected_activity(tracker.connect())))"],
                           cwd=self.v.root, capture_output=True, text=True)
        acts = json.loads(r.stdout.splitlines()[-1])
        self.assertEqual([a["change"] for a in acts], ["rejected: Doesn't need tracking"])

    def test_minutes_rejected_but_not_applied_can_be_approved_instead(self):
        self.v.propose("mins", [], meeting={"key": "k", "title": "ABC Steering", "projects": ["ABC"], "draft": "x.docx",
                                            "minutes_decision": "rejected", "file_ops": []})
        out = json.loads(self.review("approve-instead", "proposed-mins.json#meeting", "--json").stdout.splitlines()[-1])
        self.assertEqual(out["open"], ["proposed-mins.json#meeting"])
        data = json.loads((self.v.root / "system/staging/proposed-mins.json").read_text())
        self.assertEqual(data["meeting"]["minutes_decision"], "pending")
        r = self.review("rereason", "proposed-mins.json#meeting", "--reason=Chatter", ok=False)
        self.assertIn("isn't rejected", r.stdout + r.stderr)


class Server(unittest.TestCase):
    def test_the_routes_run_review_py(self):
        import live_server
        calls = []

        def fake(script, *args):
            calls.append((script, *args))
            if args[:1] == ("list",):
                return 0, json.dumps([{"n": 4, "file": "proposed-p.json", "ref": 2}, {"n": 5, "file": "proposed-p.json", "ref": 3}])
            if args[:1] == ("reasons",):
                return 0, json.dumps(SEVEN)
            if args[:1] == ("guesses",):
                return 0, json.dumps([{"n": 4, "file": "proposed-p.json", "ref": 2, "reason": "Chatter", "why": "a thank-you", "of": None}])
            if args[:1] == ("reject",):
                return 0, "Rejected 2."
            if args[:1] == ("rejects",):
                return 0, "[]"
            return 0, json.dumps({"ok": True, "done": [{"key": "proposed-p.json#2", "was": {}}], "open": []})

        class H:
            def send(self, code, body):
                self.got = (code, body)

        old, live_server.run = live_server.run, fake
        R = live_server.REVIEW_WORK_ROUTES
        try:
            h = H()
            R["/api/review/guesses"](h, {})
            self.assertEqual((h.got[1]["reasons"], h.got[1]["guesses"][0]["reason"]), (SEVEN, "Chatter"))
            R["/api/review/reject"](h, {"rows": [{"file": "proposed-p.json", "ref": 2}, {"file": "proposed-p.json", "ref": 3},
                                                 {"file": "gone.json", "ref": 1}], "reason": "Chatter"})
            self.assertTrue(h.got[1]["ok"])
            self.assertEqual([r["key"] for r in h.got[1]["rejected"]], ["proposed-p.json#2", "proposed-p.json#3"])
            self.assertEqual(h.got[1]["gone"], [{"file": "gone.json", "ref": 1}])
            R["/api/review/reject"](h, {"rows": [{"file": "proposed-p.json", "ref": 2}], "guess": True})
            R["/api/review/reject"](h, {"rows": [{"file": "proposed-p.json", "ref": 2}], "reason": "x\ny", "duplicate_of": "not an id"})
            R["/api/review/rejected"](h, {"rows": [{"file": "proposed-p.json", "ref": 2}], "how": "reason", "reason": "Duplicate",
                                          "duplicate_of": "ABC-A-001"})
            self.assertTrue(h.got[1]["ok"])
            R["/api/review/rejected"](h, {"rows": [{"file": "../proposed-p.json", "ref": 2}], "how": "undo"})
            R["/api/review/rejected"](h, {"rows": [{"file": "proposed-p.json", "ref": 2}], "how": "approve"})
            R["/api/review/rejected"](h, {"rows": [{"file": "proposed-p.json", "ref": "2; rm"}], "how": "undo"})
            self.assertEqual(h.got[0], 400)
            R["/api/review/rejected"](h, {"rows": [{"file": "proposed-p.json", "ref": 2}], "how": "delete"})
            self.assertEqual(h.got[0], 400)
            R["/api/review/rejects"](h, {"limit": 10})
            self.assertTrue(h.got[1]["ok"])
        finally:
            live_server.run = old
        self.assertIn(("review.py", "reject", "4,5", "--reason=Chatter"), calls)
        self.assertIn(("review.py", "reject", "4", "--guess"), calls)
        self.assertIn(("review.py", "reject", "4"), calls)                                 # a bad reason or ID is left out
        self.assertIn(("review.py", "rereason", "proposed-p.json#2", "--json", "--reason=Duplicate", "--duplicate-of=ABC-A-001"), calls)
        self.assertIn(("review.py", "unreject", "proposed-p.json#2", "--json"), calls)     # only the file's name is used
        self.assertIn(("review.py", "approve-instead", "proposed-p.json#2", "--json"), calls)
        self.assertIn(("review.py", "rejects", "--json", "--limit=10"), calls)

    def test_the_new_commands_are_classified_for_ask_creaite(self):
        import reach
        table = reach.SCRIPT_COMMANDS["review.py"]
        self.assertEqual({c: table[c] for c in ("reasons", "guesses", "rejects")}, dict.fromkeys(("reasons", "guesses", "rejects"), reach.READ))
        self.assertEqual({table[c] for c in ("unreject", "rereason", "approve-instead")}, {reach.RECORD})


if __name__ == "__main__":
    unittest.main(verbosity=2)
