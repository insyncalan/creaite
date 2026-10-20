"""#261: approving draft minutes after rejecting some or all of their items is allowed.

A rejection is a decision about the staged item, not a difference from the draft: the draft is compared with every staged
item, rejected ones included, and a rejected match needs no owner or due check. A genuine difference still stops the approval.

Run: python3 dev/tests/test_minutes_reject_then_approve.py
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import ABC, Vault  # noqa: E402
from test_minutes_review import TRANSCRIPT, fill_values, meeting_spec  # noqa: E402

FILED = f"{ABC}/minutes/2026-10-01 Steering committee.docx"


class RejectThenApproveTests(unittest.TestCase):
    def stage(self, change=None):
        self.v = Vault()
        self.v.run("init")
        self.transcript = "inbox/Recording 2026-10-01.vtt"
        (self.v.root / self.transcript).write_text(TRANSCRIPT)
        self.draft = "system/staging/drafts/2026-10-01 Steering committee.docx"
        values = self.v.root / "system/staging/values.json"
        values.write_text(json.dumps(fill_values()))
        self.v.run("fill", "system/templates/minutes-template.docx", str(values), str(self.v.root / self.draft),
                   script="docx_tools.py", cwd=self.v.root)
        spec = meeting_spec(self.draft, self.transcript)
        if change:
            change(spec)
        path = self.v.root / "system/staging/meeting.json"
        path.write_text(json.dumps(spec))
        self.v.run("stage", str(path), script="minutes.py")
        self.review("list")

    def tearDown(self):
        self.v.cleanup()

    def review(self, *args, ok=True):
        return self.v.run(*args, script="review.py", ok=ok)

    def proposal(self):
        return json.loads(next((self.v.root / "system/staging").glob("proposed-*.json")).read_text())

    def test_a_every_item_rejected_approves_and_files_only_the_draft(self):
        self.stage()
        self.review("reject", "2-6", "because", "not mine to track")
        out = self.review("approve", "1").stdout
        self.assertNotIn("differs", out)
        self.assertIn("Minutes approved", out)
        self.assertIn("no items were taken into your work", out)
        self.assertEqual(self.proposal()["meeting"]["minutes_decision"], "approved")
        self.v.run("apply")
        self.assertTrue((self.v.root / FILED).exists())
        for table in ("actions", "decisions", "raid"):
            self.assertEqual(self.v.rows(table), [], table)
        self.assertEqual(len(self.v.rows("rejected")), 5)                 # (f) the rejections are still kept

    def test_b_some_rejected_some_approved_writes_only_the_approved(self):
        self.stage()
        self.review("reject", "2-3")                                       # the decision and the risk
        self.review("approve", "4-6")
        out = self.review("approve", "1").stdout
        self.assertIn("Minutes approved", out)
        self.assertNotIn("no items were taken", out)
        self.v.run("apply")
        self.assertTrue((self.v.root / FILED).exists())
        self.assertEqual(len(self.v.rows("actions")), 2)
        self.assertEqual(self.v.rows("decisions"), [])

    def test_c_a_draft_line_with_no_staged_item_still_stops(self):
        self.stage(lambda s: s["items"].pop(1))                           # "Book UAT environment" is in the draft only
        self.review("reject", "2-5")
        out = self.review("approve", "1").stdout
        self.assertIn("not approved — the draft differs from the staged items", out)
        self.assertIn("Action 2 is in the draft but not staged: Book UAT environment", out)
        # "Rebuild the items from the draft" adds the new line and keeps every rejection: it never undoes one silently
        prop = next((self.v.root / "system/staging").glob("proposed-*.json"))
        self.v.run("refresh", str(prop), script="minutes.py")
        items = self.proposal()["items"]
        self.assertEqual(sum(i["decision"] == "rejected" for i in items), 4)
        self.assertEqual([i["values"]["description"] for i in items if i["decision"] == "pending"], ["Book UAT environment"])
        self.review("list")
        self.review("reject", "2")
        self.assertIn("no items were taken into your work", self.review("approve", "1").stdout)

    def test_d_an_owner_changed_for_an_approved_item_still_asks(self):
        self.stage(lambda s: s["items"][0]["values"].update(owner="Sara Example"))
        self.review("reject", "2-3")
        out = self.review("approve", "1").stdout
        self.assertIn("Action 1 owner: draft says Omar Ali; staged Sara Example", out)
        self.assertIn("--sync", out)

    def test_d2_an_owner_changed_for_a_rejected_item_does_not_stop(self):
        self.stage(lambda s: s["items"][0]["values"].update(owner="Sara Example"))
        self.review("reject", "2-6")
        self.assertIn("Minutes approved", self.review("approve", "1").stdout)

    def test_g_a_rejected_item_worded_slightly_differently_still_matches(self):
        def reword(s):
            s["items"][0]["values"]["description"] = "Send the revised SOW to the client"
            s["items"][2]["values"]["decision"] = "Go-live stays on 20 Nov"
        self.stage(reword)
        self.review("reject", "2-6")
        out = self.review("approve", "1").stdout
        self.assertNotIn("differs", out)
        self.assertIn("Minutes approved", out)


if __name__ == "__main__":
    unittest.main()
