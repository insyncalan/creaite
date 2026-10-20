"""#232 E1 PROPOSAL tests: someone else's minutes are filed only with an approved item. They run against a patched scratch copy.

Run: python3 dev/tests/test_minutes_by_others_filing.py                       (quick tier: no Chrome)
Fail-first: E1_TRACKER_UNPATCHED=1 python3 dev/tests/test_minutes_by_others_filing.py
            (the scratch copy is left without the proposal's patch: the "fixed" tests go red, the "defect" tests stay green)

`system/scripts/tracker.py` is a guarded file: the fix is the proposal dev/proposals/intake-232/E1-tracker.diff, for Jarvis to
approve and apply (see E1-tracker-README.md). This file proves it without touching tracker.py: a throwaway vault gets a copy of
`system/scripts/` and the diff is applied there with `patch -p0`. After the diff is applied to the repo, the copy is already
patched (the marker `def by_others_waiting` is found), the same tests keep guarding it, and the unpatched copy used by the
"defect" tests is made with `patch -R`.

What it proves:
- the defect is real today (always run on the unpatched copy): minutes_decision is "approved" from staging, so a full apply for an
  unrelated proposal copies the file, removes the inbox copy and writes a processed.txt line with 0 items; and rejecting every
  item still files the copy;
- with the patch: an unrelated apply leaves the proposal and the inbox file alone; with every item rejected nothing is filed, the
  rejections are recorded and the proposal finishes; one approved item files the copy, removes the inbox copy and writes the line
  (1 item); the other items stay pending and the proposal stays in staging; a different file already at the destination stops the
  apply before anything is backed up or changed.
"""
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_tracker import ABC, Vault, action  # noqa: E402

REPO = HERE.parents[1]
DIFF = REPO / "dev" / "proposals" / "intake-232" / "E1-tracker.diff"
UNPATCHED = os.environ.get("E1_TRACKER_UNPATCHED") == "1"
MARKER = "def by_others_waiting"

DAY, TITLE = "2026-10-12", "[ABC] Vendor call"
FILE = "inbox/Vendor call minutes.txt"
FILED = f"{ABC}/minutes/2026-10-12 Vendor call.txt"
MINUTES = "Vendor call\nDecisions\n- Pilot starts on 2 November.\nAction items\n- Omar Ali to send the SOW.\n"
ITEMS = [{"table": "actions", "section": "Action Items",
          "values": {"project": "ABC", "description": "Send the SOW to the client", "owner": "Omar Ali", "due_date": "2026-10-16"}},
         {"table": "actions", "section": "Action Items",
          "values": {"project": "ABC", "description": "Book the pilot room", "owner": "Sara Khan", "due_date": "2026-10-23"}}]


def _patch(root, *flags):
    r = subprocess.run(["patch", "-p0", "-s", *flags, "-i", str(DIFF)], cwd=root, capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError(f"patch {' '.join(flags)} failed in the scratch copy:\n{r.stdout}\n{r.stderr}")


def scratch(patched):
    """A throwaway vault with tracker.py patched (or not) by the proposal's diff. If the repo's tracker.py already has the fix,
    `patched` leaves it and `not patched` reverses the diff."""
    v = Vault()
    v.run("init")
    tracker = v.root / "system" / "scripts" / "tracker.py"
    shutil.copy(REPO / "system" / "scripts" / "tracker.py", tracker)
    already = MARKER in tracker.read_text(encoding="utf-8")
    if patched and not already:
        _patch(v.root)
    if not patched and already:
        _patch(v.root, "-R")
    return v


class Base(unittest.TestCase):
    PATCHED = not UNPATCHED

    def setUp(self):
        self.v = scratch(self.PATCHED)
        (self.v.root / FILE).write_text(MINUTES, encoding="utf-8")
        spec = {"title": TITLE, "date": DAY, "projects": ["ABC"], "as": "minutes", "file": FILE, "items": ITEMS}
        f = self.v.root / "system/staging/drafts/meeting.json"
        f.write_text(json.dumps(spec))
        self.v.run("stage", str(f), script="minutes.py")
        self.name = next((self.v.root / "system/staging").glob("proposed-*.json")).name

    def tearDown(self):
        self.v.cleanup()

    def proposal(self):
        p = self.v.root / "system/staging" / self.name
        p = p if p.exists() else self.v.root / "system/staging/applied" / self.name
        return json.loads(p.read_text(encoding="utf-8"))

    def decide(self, *decisions):
        p = self.v.root / "system/staging" / self.name
        data = json.loads(p.read_text())
        for item, d in zip(data["items"], decisions):
            item["decision"] = d
        p.write_text(json.dumps(data, indent=2))

    def unrelated(self):
        """Another proposal, approved, in staging: a full apply reaches both."""
        self.v.propose("2026-10-13-0900", [action(1, description="Order the test licences")])

    def processed(self):
        p = self.v.root / "system/processed.txt"
        return p.read_text() if p.exists() else ""

    def filed(self):
        return (self.v.root / FILED).exists()

    def inbox(self):
        return (self.v.root / FILE).exists()


class DefectToday(Base):
    """Always on the unpatched copy: the behaviour the proposal changes (documented, not wanted)."""
    PATCHED = False

    def test_an_unrelated_full_apply_files_the_copy_with_no_item_approved(self):
        self.unrelated()
        self.v.run("apply")
        self.assertTrue(self.filed())
        self.assertFalse(self.inbox())
        self.assertIn(f"{FILED} | 0", self.processed())            # a line with 0 items, while its items are still pending
        self.assertEqual([i.get("decision") for i in self.proposal()["items"]], ["pending", "pending"])

    def test_rejecting_every_item_still_files_the_copy(self):
        self.decide("rejected", "rejected")
        self.v.run("apply")
        self.assertTrue(self.filed())
        self.assertFalse(self.inbox())


class Fixed(Base):
    """On the patched copy (red with E1_TRACKER_UNPATCHED=1)."""

    def test_an_unrelated_full_apply_leaves_the_proposal_and_the_inbox_file_alone(self):
        self.unrelated()
        self.v.run("apply")
        self.assertFalse(self.filed())
        self.assertTrue(self.inbox())
        self.assertEqual(self.processed(), "")
        self.assertEqual([a["description"] for a in self.v.rows("actions")], ["Order the test licences"])
        self.assertTrue((self.v.root / "system/staging" / self.name).exists())
        self.assertNotIn("applied", self.proposal()["meeting"])

    def test_rejecting_every_item_files_nothing_and_the_proposal_finishes(self):
        self.decide("rejected", "rejected")
        self.v.run("apply")
        self.assertFalse(self.filed())
        self.assertTrue(self.inbox())
        self.assertEqual(self.processed(), "")
        self.assertEqual(self.v.rows("actions"), [])
        self.assertEqual(len(self.v.rows("rejected")), 2)
        self.assertTrue((self.v.root / "system/staging/applied" / self.name).exists())

    def test_one_approved_item_files_the_copy_and_the_other_stays_pending(self):
        self.decide("approved", "pending")
        self.v.run("apply")
        self.assertEqual((self.v.root / FILED).read_text(encoding="utf-8"), MINUTES)
        self.assertFalse(self.inbox())
        self.assertIn(f"{FILED} | 1", self.processed())
        self.assertEqual([a["description"] for a in self.v.rows("actions")], ["Send the SOW to the client"])
        self.assertTrue((self.v.root / "system/staging" / self.name).exists())              # one item still waits
        self.assertTrue(self.proposal()["meeting"]["applied"])                   # filed once, with the first approved item

    def test_a_later_approval_after_the_first_apply_does_not_file_twice(self):
        self.decide("approved", "pending")
        self.v.run("apply")
        p = self.v.root / "system/staging" / self.name
        data = json.loads(p.read_text())
        data["items"][1]["decision"] = "approved"
        p.write_text(json.dumps(data, indent=2))
        self.v.run("apply")
        self.assertEqual(self.processed().count(FILED), 1)
        self.assertEqual(len(self.v.rows("actions")), 2)

    def test_undo_puts_the_inbox_copy_back(self):
        self.decide("approved", "approved")
        self.v.run("apply")
        self.v.run("undo")
        self.assertTrue(self.inbox())
        self.assertFalse(self.filed())
        self.assertEqual(self.processed().strip(), "")

    def test_a_different_file_at_the_destination_stops_the_apply_before_anything_changes(self):
        self.decide("approved", "approved")
        (self.v.root / FILED).parent.mkdir(parents=True, exist_ok=True)
        (self.v.root / FILED).write_text("Another file with this name\n")
        r = self.v.run("apply", ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("already exists; it is never overwritten", r.stdout)
        self.assertEqual((self.v.root / FILED).read_text(), "Another file with this name\n")
        self.assertTrue(self.inbox())
        self.assertEqual(self.v.rows("actions"), [])
        self.assertEqual(self.processed(), "")

    def test_validation_names_a_different_file_at_the_destination_before_any_apply(self):
        (self.v.root / FILED).parent.mkdir(parents=True, exist_ok=True)
        (self.v.root / FILED).write_text("Another file with this name\n")
        r = self.v.run("validate", str(self.v.root / "system/staging" / self.name), ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("already exists; it is never overwritten", r.stdout)

    def test_the_same_file_already_at_the_destination_is_not_an_error(self):
        self.decide("approved", "approved")
        (self.v.root / FILED).parent.mkdir(parents=True, exist_ok=True)
        (self.v.root / FILED).write_text(MINUTES, encoding="utf-8")
        self.v.run("apply")
        self.assertFalse(self.inbox())
        self.assertEqual(len(self.v.rows("actions")), 2)


if __name__ == "__main__":
    unittest.main()
