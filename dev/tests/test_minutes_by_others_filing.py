"""#232 E1 PROPOSAL tests: someone else's minutes are filed only with an approved item. They run against a patched scratch copy.

Run: python3 dev/tests/test_minutes_by_others_filing.py                       (quick tier: no Chrome)
Fail-first: E1_TRACKER_UNPATCHED=1 python3 dev/tests/test_minutes_by_others_filing.py
            (the scratch copy is left without the proposal's patch: the "fixed" tests go red, the "defect" tests stay green)

`system/scripts/tracker.py` is a guarded file: the fix is the proposal dev/proposals/intake-232/E1-tracker.diff, for Jarvis to
approve and apply (see E1-tracker-README.md). This file proves it without touching tracker.py: a throwaway vault gets a copy of
`system/scripts/` and the diff is applied there with `patch -p0`. After the diff is applied to the repo, the copy is already
patched (the marker `def by_others_waiting` is found), the same tests keep guarding it, and the unpatched copy used by the
"defect" tests is made with `patch -R`.

What it proves (round 3 adds the swap, held-item and queue tests):
- a link or another file put in inbox/ after staging is never filed as the minutes and nothing it points at is deleted: a symlink
  to a vault file, a symlink to /etc/hosts, a hard link, and a regular file replaced by a different one (checksum mismatch); the
  proposal is left in staging with a line saying why, and the rest of the queue still applies;
- an approved item that is held (needs a project) does not file the copy;
- a destination collision (with a file, or with another proposal in the same apply) leaves only that proposal in staging;
- the defect is real today (always run on the unpatched copy): minutes_decision is "approved" from staging, so a full apply for an
  unrelated proposal copies the file, removes the inbox copy and writes a processed.txt line with 0 items; and rejecting every
  item still files the copy;
- with the patch: an unrelated apply leaves the proposal and the inbox file alone; with every item rejected nothing is filed, the
  rejections are recorded and the proposal finishes; one approved item files the copy, removes the inbox copy and writes the line
  (1 item); the other items stay pending and the proposal stays in staging; a different file already at the destination stops the
  apply before anything is backed up or changed.
"""
import hashlib
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
MUTATE = os.environ.get("E1_TRACKER_MUTATE", "")
# One text change per mutation, made on the patched scratch copy (E1_TRACKER_MUTATE=<name>): a test must turn red
MUTATIONS = {
    "no-regular-check": ("if not stat.S_ISREG(st.st_mode):", "if False:"),
    "no-hardlink-check": ("if st.st_nlink > 1:", "if False:"),
    "no-checksum": ("if file_hash(p) != sha:", "if False:"),
    "no-area-check": ("if os.path.islink(paths.INBOX) or not any(", "if False and not any("),
    "copy-follows-links": ('os.open(src, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))', "os.open(src, os.O_RDONLY)"),
    "no-unwritten": ("or by_others_unwritten(data, blk, apply_id):", "or False:"),
    "no-skip": ("        work = _skip_by_others_problems(work)\n", ""),
    "no-claimed": ('                    claimed[to] = fop.get("src_sha256")\n', ""),
    "no-waiting-in-apply": ('not in ("approved", "rejected") or by_others_waiting(data, blk) \\', 'not in ("approved", "rejected") \\'),
    "no-dest-check": ("if dst.exists() and file_hash(dst) != file_hash(paths.resolve(src)):", "if False:"),
    "remove-follows-links": ("        if p.is_symlink():\n            raise Invalid(f\"remove:", "        if False:\n            raise Invalid(f\"remove:"),
}

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
    if MUTATE:
        old, new = MUTATIONS[MUTATE]
        text = tracker.read_text(encoding="utf-8")
        assert text.count(old) == 1, f"mutation {MUTATE}: {old!r} found {text.count(old)} times"
        tracker.write_text(text.replace(old, new), encoding="utf-8")
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

    def stage_more(self, file, text, title="[ABC] Vendor call"):
        """Another proposal for another file; returns its proposal name."""
        (self.v.root / file).write_text(text, encoding="utf-8")
        before = {p.name for p in (self.v.root / "system/staging").glob("proposed-*.json")}
        f = self.v.root / "system/staging/drafts/meeting2.json"
        f.write_text(json.dumps({"title": title, "date": DAY, "projects": ["ABC"], "as": "minutes", "file": file, "items": ITEMS}))
        self.v.run("stage", str(f), script="minutes.py")
        return next(p.name for p in (self.v.root / "system/staging").glob("proposed-*.json") if p.name not in before)

    def approve(self, name):
        p = self.v.root / "system/staging" / name
        data = json.loads(p.read_text())
        for i in data["items"]:
            i["decision"] = "approved"
        p.write_text(json.dumps(data, indent=2))

    def contract(self):
        c = self.v.root / f"{ABC}/documents/contract.txt"
        c.parent.mkdir(parents=True, exist_ok=True)
        c.write_text("The contract: not minutes\n", encoding="utf-8")
        return c

    def swap(self, make):
        """Replace the staged inbox file with whatever `make(path)` builds, as someone could between staging and approving."""
        f = self.v.root / FILE
        f.unlink()
        make(f)

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

    def test_a_different_file_at_the_destination_leaves_only_that_proposal_in_staging(self):
        self.decide("approved", "approved")
        (self.v.root / FILED).parent.mkdir(parents=True, exist_ok=True)
        (self.v.root / FILED).write_text("Another file with this name\n")
        self.unrelated()
        r = self.v.run("apply")                                     # a full apply: the rest of the queue goes through
        self.assertIn("Left in staging, not applied", r.stdout)
        self.assertIn("already exists; it is never overwritten", r.stdout)
        self.assertEqual((self.v.root / FILED).read_text(), "Another file with this name\n")
        self.assertTrue(self.inbox())
        self.assertEqual([a["description"] for a in self.v.rows("actions")], ["Order the test licences"])
        self.assertEqual(self.processed(), "")
        self.assertTrue((self.v.root / "system/staging" / self.name).exists())

    def test_named_apply_of_that_proposal_stops_with_the_message(self):
        self.decide("approved", "approved")
        (self.v.root / FILED).parent.mkdir(parents=True, exist_ok=True)
        (self.v.root / FILED).write_text("Another file with this name\n")
        r = self.v.run("apply", self.name, ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("already exists; it is never overwritten", r.stdout)
        self.assertEqual(self.v.rows("actions"), [])
        self.assertTrue(self.inbox())

    def test_two_proposals_for_one_destination_in_one_apply_file_the_first_only(self):
        second = self.stage_more("inbox/second.txt", "A different set of minutes\n")
        p2 = self.v.root / "system/staging" / second
        data = json.loads(p2.read_text())
        for op in data["meeting"]["file_ops"]:
            if op["op"] == "copy":
                op["to"] = FILED                                    # as if both had been staged before either was numbered
        p2.write_text(json.dumps(data, indent=2))
        self.approve(self.name)
        self.approve(second)
        self.unrelated()
        r = self.v.run("apply")
        self.assertIn("is taken by a different file in this apply", r.stdout)
        filed = (self.v.root / FILED).read_text(encoding="utf-8")
        self.assertIn(filed, (MINUTES, "A different set of minutes\n"))
        left_in_inbox = [f for f in ("inbox/second.txt", FILE) if (self.v.root / f).exists()]
        self.assertEqual(len(left_in_inbox), 1)                      # exactly one was filed (and its inbox copy removed)
        self.assertEqual(len(list((self.v.root / "system/staging").glob("proposed-*.json"))), 1)       # the other waits
        self.assertEqual(self.processed().count(FILED), 1)

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


class Swapped(Base):
    """A link or another file put in inbox/ after staging is never filed, and nothing it points at is deleted (pre-existing for an
    inbox transcript too: safe_path resolves a link, so the remove deleted its target)."""

    def check_left_alone(self, victim, text=None, why=None):
        self.decide("approved", "approved")
        self.unrelated()
        r = self.v.run("apply")                                     # a full apply: the rest of the queue goes through
        if why:
            self.assertIn(why, r.stdout)
        self.assertFalse(self.filed())
        self.assertEqual(self.processed(), "")
        if victim is not None:
            self.assertTrue(victim.exists())
            self.assertEqual(victim.read_text(), text)
        self.assertTrue((self.v.root / "system/staging" / self.name).exists())
        self.assertEqual([a["description"] for a in self.v.rows("actions")], ["Order the test licences"])

    def test_a_symlink_to_a_vault_file_is_not_filed_and_its_target_survives(self):
        target = self.contract()
        self.swap(lambda f: f.symlink_to(target))
        self.check_left_alone(target, "The contract: not minutes\n", "not a regular file")

    def test_a_symlink_to_a_file_outside_the_vault_is_refused(self):
        self.swap(lambda f: f.symlink_to("/etc/hosts"))
        self.check_left_alone(Path("/etc/hosts"), Path("/etc/hosts").read_text(), "not a regular file")

    def test_a_hard_link_is_refused_and_the_other_name_survives(self):
        target = self.contract()
        self.swap(lambda f: os.link(target, f))
        self.check_left_alone(target, "The contract: not minutes\n", "hard link")

    def test_a_different_regular_file_put_there_after_staging_is_a_checksum_mismatch(self):
        self.swap(lambda f: f.write_text("Quite different minutes\n"))
        self.check_left_alone(self.v.root / FILE, "Quite different minutes\n", "changed since it was staged")

    def test_the_file_edited_in_place_after_staging_is_refused_too(self):
        (self.v.root / FILE).write_text(MINUTES + "One more line\n")
        self.check_left_alone(self.v.root / FILE, MINUTES + "One more line\n", "changed since it was staged")

    def test_a_folder_swapped_for_a_link_after_staging_is_caught_by_the_area_check(self):
        """inbox/sub/m.txt staged; sub is then replaced by a link to a vault folder holding the very same bytes."""
        (self.v.root / "inbox/sub").mkdir()
        (self.v.root / "inbox/sub/m.txt").write_text(MINUTES, encoding="utf-8")
        name = self.stage_more("inbox/sub/m.txt", MINUTES, title="[ABC] Sub call")
        folder = self.v.root / f"{ABC}/documents/sub"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "m.txt").write_text(MINUTES, encoding="utf-8")
        shutil.rmtree(self.v.root / "inbox/sub")
        (self.v.root / "inbox/sub").symlink_to(folder)
        self.approve(name)
        r = self.v.run("apply", name, ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("not in inbox/ or the project's minutes folder", r.stdout)
        self.assertTrue((folder / "m.txt").exists())

    def test_a_named_apply_stops_with_the_reason_and_changes_nothing(self):
        target = self.contract()
        self.swap(lambda f: f.symlink_to(target))
        self.decide("approved", "approved")
        r = self.v.run("apply", self.name, ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("not a regular file", r.stdout)
        self.assertTrue(target.exists())
        self.assertEqual(self.v.rows("actions"), [])

    def test_a_link_swapped_in_between_validation_and_the_copy_is_still_caught(self):
        """The copy reads the bytes once, never through a link, and checks them against the staged checksum."""
        target = self.v.root / f"{ABC}/documents/same-bytes.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(MINUTES, encoding="utf-8")                 # the same bytes: only refusing a link stops it
        code = ("import sys, os; sys.path.insert(0, 'system/scripts')\nimport tracker, paths\nfrom pathlib import Path\n"
                f"f = Path({str(self.v.root / FILE)!r}); f.unlink(); f.symlink_to({str(target)!r})\n"
                f"fop = {{'op': 'copy', 'from': {FILE!r}, 'to': {FILED!r}, 'src_sha256': {hashlib.sha256(MINUTES.encode()).hexdigest()!r}}}\n"
                "blk = {'kind': 'minutes by others'}\n"
                "try:\n    tracker._op_copy(1, fop, blk, [])\nexcept (tracker.Invalid, OSError) as e:\n    print('REFUSED', type(e).__name__)\n")
        r = subprocess.run([sys.executable, "-c", code], cwd=self.v.root, capture_output=True, text=True)
        self.assertIn("REFUSED", r.stdout, r.stderr)
        self.assertFalse(self.filed())
        self.assertTrue(target.exists())


class HeldItems(Base):
    def test_an_approved_item_that_is_held_does_not_file_the_copy(self):
        p = self.v.root / "system/staging" / self.name
        data = json.loads(p.read_text())
        data["items"][0].update(decision="approved", match="possible")              # needs a project: held, not written
        p.write_text(json.dumps(data, indent=2))
        r = self.v.run("apply")
        self.assertEqual(self.v.rows("actions"), [])
        self.assertFalse(self.filed())
        self.assertTrue(self.inbox())
        self.assertEqual(self.processed(), "")
        self.assertTrue(p.exists())
        self.assertNotIn("applied", json.loads(p.read_text())["meeting"])
        self.assertIn("filed 0", r.stdout)

    def test_once_an_item_is_written_the_copy_is_filed_with_its_count(self):
        p = self.v.root / "system/staging" / self.name
        data = json.loads(p.read_text())
        data["items"][0].update(decision="approved", match="possible")
        p.write_text(json.dumps(data, indent=2))
        self.v.run("apply")
        data = json.loads(p.read_text())
        data["items"][0]["match"] = "strong"
        p.write_text(json.dumps(data, indent=2))
        self.v.run("apply")
        self.assertTrue(self.filed())
        self.assertFalse(self.inbox())
        self.assertIn(f"{FILED} | 1", self.processed())


if __name__ == "__main__":
    unittest.main()
