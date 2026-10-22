"""#306: Approve without the transcript on held minutes must say what happened.

Backend (runs now): approved, held by Apply, approved without the transcript, applied: the minutes are filed and the row leaves
Review. A refusal (the draft differs from the staged items) is one plain line the page shows on the row, not only in the chat.
Page source: heldApprove shows 'Approved without the transcript: n items saved' with Undo, or 'Not saved because <reason>' on the
row and in a message.
"""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(__file__))
import test_held_missing_source as base

REPO = base.REPO


class Held306(base.HeldMissingSource):
    def test_held_then_approved_without_then_applied_leaves_review(self):
        held = self.stage_gone()
        r = self.v.run("apply", ok=False, cwd=self.root)
        self.assertIn("Held in Review, not applied", r.stdout)
        r = self.v.run("approve", str(self.number()), "--without-transcript", "--as-staged", script="review.py", ok=False, cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Approved 1.", r.stdout)
        r = self.v.run("apply", ok=False, cwd=self.root)
        self.assertIn("written 1", r.stdout)
        self.assertFalse(held.exists())
        self.assertIn("Nothing is waiting for review", self.v.run("list", script="review.py", cwd=self.root).stdout)

    def test_a_refusal_is_one_readable_reason(self):
        held = self.stage_gone()
        self.v.run("apply", ok=False, cwd=self.root)
        r = self.v.run("approve", str(self.number()), "--without-transcript", script="review.py", ok=False, cwd=self.root)
        self.assertIn("not approved", r.stdout)
        self.assertEqual(self.read(held)["meeting"]["minutes_decision"], "pending")

    def test_the_page_says_what_happened(self):
        js = (REPO / "system/templates/dashboard/src/review.js").read_text(encoding="utf-8")
        i = js.index("export async function heldApprove")
        body = js[i:i + 1800]
        self.assertIn("Approved without the transcript: ${n} item", body)
        self.assertIn("Not saved because ${why}", body)
        self.assertIn("undoApply(a.apply_id)", body)
        jsx = (REPO / "system/templates/dashboard/src/components/intakeReview/proposals.jsx").read_text(encoding="utf-8")
        self.assertIn("Not saved because {HELD_ERR.get(r.file)}", jsx)


for _n in [n for n in dir(base.HeldMissingSource) if n.startswith("test_")]:
    if _n not in Held306.__dict__:
        setattr(Held306, _n, None)           # inherit nothing: run only this file's tests
del base.HeldMissingSource
if __name__ == "__main__":
    unittest.main()
