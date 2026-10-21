"""#280: a decision staged by cx-minutes with `raised` (decisions have `date`) must not block Apply.

Run: python3 dev/tests/test_minutes_decision_raised.py      (quick tier: no Chrome)
Builds a throwaway vault (test_tracker.Vault), stages minutes whose spec puts `raised` on a decision and on an action, and runs
the real scripts: stage, `tracker.py validate`, review approve and apply.
"""
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import Vault, make_draft  # noqa: E402

DAY, TITLE = "2026-10-14", "Steering committee"
TRANSCRIPT = f"inbox/{DAY} Steering committee.vtt"
DRAFT = f"system/staging/drafts/{DAY} Steering committee.docx"
VTT = "WEBVTT\n\n00:00:01.000 --> 00:00:05.000\n<v Alan Carter>Morning all, first the SOW.</v>\n"
ACTION = {"table": "actions", "section": "Actions", "values": {"project": "ABC", "description": "Send the revised SOW",
                                                                "owner": "Alan Carter", "due_date": "2030-06-10"}}
DECISION = {"table": "decisions", "section": "Decisions",
            "values": {"project": "ABC", "decision": "Use the phased rollout", "made_by": "Alan Carter", "raised": DAY}}


class DecisionRaised(unittest.TestCase):
    def setUp(self):
        self.now = os.environ.get("CREAITE_NOW")
        os.environ["CREAITE_NOW"] = f"{DAY} 12:00"
        self.v = Vault()
        self.v.run("init")
        self.root = self.v.root
        (self.root / TRANSCRIPT).write_text(VTT, encoding="utf-8")
        make_draft(self.root / DRAFT)

    def tearDown(self):
        self.v.cleanup()
        if self.now is None:
            os.environ.pop("CREAITE_NOW", None)
        else:
            os.environ["CREAITE_NOW"] = self.now

    def stage(self):
        f = self.root / "system/staging/drafts/meeting.json"
        f.write_text(json.dumps({"title": TITLE, "date": DAY, "projects": ["ABC"], "transcript": TRANSCRIPT, "draft": DRAFT,
                                 "items": [ACTION, DECISION]}), encoding="utf-8")
        r = self.v.run("stage", str(f), script="minutes.py", ok=False, cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        prop = sorted((self.root / "system/staging").glob("proposed-*.json"))[-1]
        return prop, json.loads(prop.read_text(encoding="utf-8"))

    def test_a_decision_staged_with_raised_has_a_date_and_no_raised(self):
        prop, data = self.stage()
        d = next(i for i in data["items"] if i["table"] == "decisions")
        self.assertNotIn("raised", d["values"])
        self.assertEqual(d["values"].get("date"), DAY)
        self.assertNotIn("invalid", d.get("flags", []))

    def test_validate_passes_on_minutes_with_a_decision(self):
        prop, _ = self.stage()
        r = self.v.run("validate", str(prop), script="tracker.py", ok=False, cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("0 problem(s)", r.stdout)

    # ── An invalid item (here an action with a field that doesn't exist) ─────────────────────────────
    def stage_bad(self):
        f = self.root / "system/staging/drafts/meeting.json"
        bad = {"table": "actions", "section": "Actions", "values": {"project": "ABC", "description": "Chase the vendor",
                                                                   "owner": "Alan Carter", "colour": "red"}}
        f.write_text(json.dumps({"title": TITLE, "date": DAY, "projects": ["ABC"], "transcript": TRANSCRIPT, "draft": DRAFT,
                                 "items": [ACTION, bad]}), encoding="utf-8")
        self.v.run("stage", str(f), script="minutes.py", ok=False, cwd=self.root)
        prop = sorted((self.root / "system/staging").glob("proposed-*.json"))[-1]
        return prop, json.loads(prop.read_text(encoding="utf-8"))

    def test_an_invalid_item_cannot_be_approved_and_review_says_why(self):
        prop, data = self.stage_bad()
        bad = next(i for i in data["items"] if "invalid" in i.get("flags", []))
        self.assertIn("colour", bad.get("invalid_reason", ""))
        rows = self.v.run("list", script="review.py", ok=False, cwd=self.root).stdout
        self.assertIn("colour", rows, "Review shows the reason")
        n = next(l.replace("↳", "").split()[0] for l in rows.splitlines() if "Chase the vendor" in l)
        r = self.v.run("approve", n, script="review.py", ok=False, cwd=self.root)
        out = r.stdout + r.stderr
        self.assertIn("invalid", out)
        after = json.loads(prop.read_text(encoding="utf-8"))
        self.assertEqual(next(i for i in after["items"] if i["n"] == bad["n"])["decision"], "pending")

    def test_the_dashboard_review_row_says_why_an_invalid_item_is_held(self):
        """The Review page's row names the reason, as review.py list does (the 2.5.4 hand check reads it)."""
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system/scripts"))
        import build_dashboard
        _, data = self.stage_bad()
        bad = next(i for i in data["items"] if "invalid" in i.get("flags", []))
        why = build_dashboard.item_why(bad, "ABC", bad["flags"])
        self.assertIn("colour", why)
        self.assertTrue(why.startswith("Can't be approved"), why)

    def test_one_invalid_item_does_not_block_the_rest_and_apply_names_it(self):
        if "#280" not in (Path(__file__).resolve().parents[2] / "system/scripts/tracker.py").read_text(encoding="utf-8"):
            self.skipTest("tracker.py has not taken dev/proposals/280 yet")
        prop, data = self.stage_bad()
        for i in data["items"]:
            i["decision"] = "approved"                     # a stale approval, as the board saw: both approved
        prop.write_text(json.dumps(data), encoding="utf-8")
        r = self.v.run("apply", prop.name, script="tracker.py", ok=False, cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("item 2", r.stdout)
        self.assertIn("colour", r.stdout)
        after = json.loads(prop.read_text(encoding="utf-8")) if prop.exists() else json.loads(
            (self.root / "system/staging/applied" / prop.name).read_text(encoding="utf-8"))
        by = {i["n"]: i for i in after["items"]}
        self.assertTrue(by[1].get("applied"), "the valid item was written")
        self.assertFalse(by[2].get("applied"))
        self.assertEqual(by[2]["decision"], "pending")


if __name__ == "__main__":
    unittest.main()
