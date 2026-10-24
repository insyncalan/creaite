"""#232 E1 PROPOSAL tests: someone else's minutes are filed only with an approved item. They run against a patched scratch copy.

Run: python3 dev/tests/test_minutes_by_others_filing.py                       (quick tier: no Chrome)
Fail-first: E1_TRACKER_UNPATCHED=1 python3 dev/tests/test_minutes_by_others_filing.py
            (the scratch copy is left without the proposal's patch: the "fixed" tests go red, the "defect" tests stay green)

`system/scripts/tracker.py` is a guarded file: the fix is the proposal dev/proposals/intake-232/E1-tracker.rebased-on-280.diff
(on the #280 stack and guard-small), for Jarvis to approve and apply (see E1-tracker-README.md). This file proves it without
touching tracker.py: a throwaway vault gets a copy of
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
import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_tracker import ABC, Vault, action  # noqa: E402

REPO = HERE.parents[1]
DIFF = REPO / "dev" / "proposals" / "intake-232" / "E1-tracker.rebased-on-280.diff"   # on top of the #280 stack + guard-small (v2.6)
BASE_DIFF = REPO / "dev" / "proposals" / "guard-small" / "tracker-copy-source.diff"           # its base: applied first
BASE_MARKER = "class CopySource:"
UNPATCHED = os.environ.get("E1_TRACKER_UNPATCHED") == "1"
MARKER = "def by_others_waiting"
INODE_DIFF = REPO / "dev" / "proposals" / "261-inode-gap" / "tracker-inode.py.diff"     # #261, built on E1: reversed before it
INODE_MARKER = "hold=held"
MUTATE = os.environ.get("E1_TRACKER_MUTATE", "")
# One text change per mutation, made on the patched scratch copy (E1_TRACKER_MUTATE=<name>): a test must turn red
MUTATIONS = {
    "no-regular-check": ('if not stat.S_ISREG(st.st_mode):\n        return f"{rel} is not a regular file (a link', 'if False:\n        return f"{rel} is not a regular file (a link'),
    "no-hardlink-check": ("if st.st_nlink > 1:", "if False:"),
    "no-checksum": ("if got != sha:", "if False:"),
    "no-area-check": ("if os.path.islink(paths.INBOX) or not any(", "if False and not any("),
    "no-unwritten": ("or by_others_unwritten(data, blk):", "or False:"),
    "unwritten-this-apply-only": ("or by_others_unwritten(data, blk):", 'or not any(i.get("applied") == apply_id and i.get("decision") == "approved" for i in data.get("items", [])):'),
    "no-nonblock": ("os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr", "os.open(path, os.O_RDONLY | getattr"),
    "no-nofollow": ('| getattr(os, "O_NOFOLLOW", 0), dir_fd=dir_fd)', ", dir_fd=dir_fd)"),
    "no-regular-fstat": ('        if not stat.S_ISREG(st.st_mode):\n            raise NotRegular(0, "not a regular file")', '        if False:\n            raise NotRegular(0, "not a regular file")'),
    "path-unlink": ("        os.unlink(private, dir_fd=dfd)\n        return", "        os.unlink(paths.resolve(rel))\n        return"),
    "no-inode-check": ("if (now.st_dev, now.st_ino) == (st.st_dev, st.st_ino) and stat.S_ISREG(now.st_mode):", "if True:"),
    "put-back-replaces": ("os.link(private, name, src_dir_fd=dfd, dst_dir_fd=dfd, follow_symlinks=False)", "os.rename(private, name, src_dir_fd=dfd, dst_dir_fd=dfd)"),
    "long-private-name": ('private = f".creaite-removing-{os.getpid()}-{time.monotonic_ns()}"', 'private = f".{name}.removing-{os.getpid()}-{time.monotonic_ns()}"'),
    "hash-via-file-hash": ("got = hashlib.sha256(_read_regular(p)[1]).hexdigest()", "got = file_hash(p)"),
    "finished-without-waiting": ('return all(b.get("applied") or by_others_waiting(data, b) for b, _ in blocks(data))', 'return all(b.get("applied") for b, _ in blocks(data))'),
    "no-decided-exclusion": ("            and not by_others_waiting(data, b)]", "]"),
    "no-hash-copy": ("if sha is not None and h.hexdigest() != sha:", "if False:"),
    "no-hash-remove": (' or hashlib.sha256(data).hexdigest() != fop.get("src_sha256"):', ":"),
    "unlink-by-name": ("    os.unlink(private, dir_fd=dfd)\n    raise Invalid", "    os.unlink(name, dir_fd=dfd)\n    raise Invalid"),
    "no-skip": ("        work = _skip_by_others_problems(work)\n", ""),
    "no-claimed": ('                    claimed[same] = fop.get("src_sha256")\n', ""),
    "no-fold-claimed": ("same = _folded(to)", "same = to"),
    "no-dest-check": ("        if dst.exists() and not _dst_is_same(dst, src, fop, blk):", "        if False:"),
    "undo-pending": ('blk[field] = "approved" if blk.get("kind") == BY_OTHERS else "pending"', 'blk[field] = "pending"'),
    "remove-by-path": ("    if by_others_op(fop, blk):\n        return _remove_checked(apply_id, fop, blk, done)\n", ""),
    "chain-follows-links": ("            nxt = os.open(part, flags, dir_fd=fd)", "            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY, dir_fd=fd)"),
    "no-dest-confine": ("why = by_others and by_others_dest_problem(dst, blk)", "why = False"),
    "kind-only": ('return blk.get("kind") == BY_OTHERS or bool(fop.get("src_sha256"))', 'return blk.get("kind") == BY_OTHERS'),
    "bare-oserror": ('            raise Invalid(f"copy: {self._why(e)} ({self.stored})") from None', "            raise"),
    "no-dir-check": ('        if dst.is_dir():\n            raise Invalid(f"copy: {paths.rel(dst)} is a folder")\n        if dst.exists() and not _dst_is_same',
                     "        if dst.exists() and not _dst_is_same"),
    "source-sha-skipped": ("    return None if _source_sha(src) == fop.get(\"src_sha256\") else", "    return None if True else"),
    # minutes.py (in the repo, not guarded): the review's two MEDIUMs
    "no-fold-staged": ("minutes.py", 'out[_fold(op["to"])] = ', 'out[op["to"]] = '),
    "no-where-check": ("minutes.py", "    why = _where_problem(file, p, real, in_inbox, projects)\n", "    why = None\n"),
    "no-odd-text": ("minutes.py", " or _odd_text(file)):", "):"),
    "no-fifo-check": ("minutes.py", "    if _special_file(p):", "    if False:"),
    "no-pending-check": ("minutes.py", "    return why or _pending_problem(file)", "    return why"),
    "no-holding-check": ("minutes.py", "    taken = None if by_others(spec) else _by_others_holding(spec.get(\"transcript\"))", "    taken = None"),
}

DAY, TITLE = "2026-10-12", "[ABC] Vendor call"
FILE = "inbox/Vendor call minutes.txt"
FILED = f"{ABC}/minutes/2026-10-12 Vendor call.txt"
MINUTES = "Vendor call\nDecisions\n- Pilot starts on 2 November.\nAction items\n- Omar Ali to send the SOW.\n"
ITEMS = [{"table": "actions", "section": "Action Items",
          "values": {"project": "ABC", "description": "Send the SOW to the client", "owner": "Omar Ali", "due_date": "2026-10-16"}},
         {"table": "actions", "section": "Action Items",
          "values": {"project": "ABC", "description": "Book the pilot room", "owner": "Sara Khan", "due_date": "2026-10-23"}}]


def _patch(root, *flags, diff=DIFF, strip="-p0"):
    r = subprocess.run(["patch", strip, "-s", *flags, "-i", str(diff)], cwd=root, capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError(f"patch {' '.join(flags)} failed in the scratch copy:\n{r.stdout}\n{r.stderr}")


def scratch(patched):
    """A throwaway vault with tracker.py patched (or not) by the proposal's diff. If the repo's tracker.py already has the fix,
    `patched` leaves it and `not patched` reverses the diff."""
    v = Vault()
    v.run("init")
    tracker = v.root / "system" / "scripts" / "tracker.py"
    shutil.copy(REPO / "system" / "scripts" / "tracker.py", tracker)
    if BASE_MARKER not in tracker.read_text(encoding="utf-8"):        # guard-small first: E1 is built on it (both copies have it)
        _patch(v.root, diff=BASE_DIFF)
    already = MARKER in tracker.read_text(encoding="utf-8")
    if patched and not already:
        _patch(v.root)
    if not patched and already and INODE_MARKER in tracker.read_text(encoding="utf-8"):
        _patch(v.root, "-R", diff=INODE_DIFF, strip="-p1")           # #261 touches E1's remove: off first, or E1's -R fails
    if not patched and already:
        _patch(v.root, "-R")
    if MUTATE and patched:                       # the mutation breaks the patch: the unpatched copy has nothing to break
        m = MUTATIONS[MUTATE]
        target = v.root / "system" / "scripts" / m[0] if len(m) == 3 else tracker       # (file, old, new): minutes.py
        old, new = m[-2:]
        text = target.read_text(encoding="utf-8")
        assert text.count(old) == 1, f"mutation {MUTATE}: {old!r} found {text.count(old)} times"
        target.write_text(text.replace(old, new), encoding="utf-8")
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
            if d != "applied-keep":                                  # an item already applied keeps its decision
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

    def test_a_staged_proposal_with_no_decided_item_is_not_an_apply_at_all(self):
        """Its block is approved from staging, but with no approved item it is not decided: an apply says there is nothing to apply."""
        r = self.v.run("apply")
        self.assertIn("Nothing to save", r.stdout)
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM applies").fetchone()[0], 0)
        self.assertTrue(self.inbox())
        self.assertTrue((self.v.root / "system/staging" / self.name).exists())

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
        self.check_left_alone(target, "The contract: not minutes\n", "the source is a link")        # guard-small's words

    def test_a_symlink_to_a_file_outside_the_vault_is_refused(self):
        self.swap(lambda f: f.symlink_to("/etc/hosts"))
        self.check_left_alone(Path("/etc/hosts"), Path("/etc/hosts").read_text(), "the source is a link")

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


DRIVER = r"""
import sys, os
sys.path.insert(0, 'system/scripts')
from pathlib import Path
import tracker
orig = tracker.FILE_OPS[%(op)r]
def swap(apply_id, fop, blk, done):
    %(swap)s
    return orig(apply_id, fop, blk, done)
tracker.FILE_OPS[%(op)r] = swap
print('RC', tracker.main(['apply']))
"""


DRIVER_HOOK = r"""
import sys, os
sys.path.insert(0, 'system/scripts')
from pathlib import Path
import tracker
orig = tracker.%(target)s
def swap(*a, **k):
    %(swap)s
    r = orig(*a, **k)
    %(after)s
    return r
tracker.%(target)s = swap
print('RC', tracker.main(['apply']))
"""


DRIVER_RENAME = r"""
import sys, os
sys.path.insert(0, 'system/scripts')
from pathlib import Path
import tracker
NAME = %(name)r
orig = os.rename
state = {'n': 0}
def hook(*a, **k):
    first = False
    if 'src_dir_fd' in k:
        state['n'] += 1
        first = state['n'] == 1
        if first:
            %(before)s
    r = orig(*a, **k)
    if first:
        %(after)s
    return r
os.rename = hook
print('RC', tracker.main(['apply']))
"""

DRIVER_FIFO = r"""
import sys, os
sys.path.insert(0, 'system/scripts')
from pathlib import Path
import tracker
NAME = %(name)r
state = {'done': False}
def wrap(fn):
    orig = getattr(tracker, fn)
    def w(*a, **k):
        if not state['done'] and str(a[0]).endswith(NAME):      # the moment the staged file is about to be hashed or read
            state['done'] = True
            p = Path('inbox') / NAME
            p.unlink()
            os.mkfifo(p)
        return orig(*a, **k)
    setattr(tracker, fn, w)
wrap('file_hash')
wrap('_read_regular')
print('RC', tracker.main(['apply']))
"""


# A swap that unlinks the staged file and writes another at its name first keeps the staged file open (a descriptor left open
# for the rest of the driver), so the other file is given a NEW inode. Linux (ext4, tmpfs) hands a freed inode number straight to
# the next file, so without this the "different file" has the staged file's (st_dev, st_ino) and is, by the very check under
# test, the same file: the apply removes it and succeeds (CI: RC 0). APFS never reuses a number so soon, so macOS passed anyway.
HOLD = "os.open(p, os.O_RDONLY); "


class Races(Base):
    """What a local process could do between the check and the operation (the operation is wrapped, as a reviewer would)."""

    def run_driver(self, op, swap):
        r = subprocess.run([sys.executable, "-c", DRIVER % {"op": op, "swap": swap}], cwd=self.v.root, capture_output=True, text=True)
        log = "".join(f.read_text(errors="ignore") for f in (self.v.root / "system/logs").glob("*.log")) if (self.v.root / "system/logs").exists() else ""
        return r.stdout + r.stderr, log

    def hook(self, target, swap, timeout=120, after="pass"):
        """Like run_driver, for any tracker function (`FILE_OPS['remove']`, `stash`); a hang is a failure, not a stuck suite."""
        code = DRIVER_HOOK % {"target": target, "swap": swap, "after": after}
        try:
            r = subprocess.run([sys.executable, "-c", code], cwd=self.v.root, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            self.fail(f"the apply hung ({target}): a pipe put in place of the file blocked it")
        return r.stdout + r.stderr

    def drive(self, template, timeout=120, **kw):
        try:
            r = subprocess.run([sys.executable, "-c", template % kw], cwd=self.v.root, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            self.fail("the apply hung: a pipe put in place of the file blocked a read")
        return r.stdout + r.stderr

    def test_a_pipe_swapped_in_as_the_file_is_hashed_does_not_hang_the_check(self):
        self.decide("approved", "approved")
        out = self.drive(DRIVER_FIFO, name=Path(FILE).name)
        self.assertIn("is not a regular file", out)
        self.assertNotIn("Traceback", out)
        self.assertFalse(self.filed())
        self.assertEqual(self.v.rows("actions"), [])

    def test_a_file_put_at_the_name_after_the_move_is_not_overwritten_by_the_put_back(self):
        """X is swapped in before the move, Y is written at the name after it: the put-back must not replace Y."""
        self.decide("approved", "approved")
        name = Path(FILE).name
        out = self.drive(DRIVER_RENAME, name=name, before="p = Path('inbox') / NAME; " + HOLD + "p.unlink(); p.write_text('INTRUDER X')",
                         after="(Path('inbox') / NAME).write_text('NEW FILE Y')")
        self.assertIn("RC 1", out)
        self.assertIn("the name is taken again", out)
        self.assertEqual((self.v.root / FILE).read_text(), "NEW FILE Y")                # Y survives
        kept = list((self.v.root / "inbox").glob(".creaite-removing-*"))
        self.assertEqual([k.read_text() for k in kept], ["INTRUDER X"])              # X is not lost either
        self.assertIn(kept[0].name, out)                                              # and the message says where it is

    def test_a_put_back_that_cannot_happen_says_where_the_file_is(self):
        self.decide("approved", "approved")
        name = Path(FILE).name
        out = self.drive(DRIVER_RENAME, name=name, before="p = Path('inbox') / NAME; " + HOLD + "p.unlink(); p.write_text('INTRUDER X')",
                         after="os.mkdir(Path('inbox') / NAME)")
        self.assertIn("RC 1", out)
        self.assertIn("is left in inbox/ as .creaite-removing-", out)
        self.assertNotIn("IsADirectoryError: ", out)
        self.assertEqual([k.read_text() for k in (self.v.root / "inbox").glob(".creaite-removing-*")], ["INTRUDER X"])

    def entry(self, how):
        return "p = Path('inbox') / %r; %s" % (Path(FILE).name, how)

    def test_a_pipe_put_in_place_of_the_file_does_not_hang_the_copy(self):
        self.decide("approved", "approved")
        out = self.hook("FILE_OPS['copy']", self.entry("p.unlink(); os.mkfifo(p)"))
        self.assertIn("RC 1", out)
        self.assertIn("is not a regular file", out)
        self.assertFalse(self.filed())

    def test_a_pipe_put_in_place_of_the_file_does_not_hang_the_remove(self):
        self.decide("approved", "approved")
        out = self.hook("FILE_OPS['remove']", self.entry("p.unlink(); os.mkfifo(p)"))
        self.assertIn("RC 1", out)
        self.assertIn("is not a regular file", out)
        self.assertFalse(self.filed())                              # rolled back: the copy made before is undone
        self.assertEqual(self.v.rows("actions"), [])

    def test_same_size_different_content_before_the_copy_is_refused_by_the_checksum(self):
        self.decide("approved", "approved")
        other = "X" * len(MINUTES)
        # the original content is put back after the copy, so the remove's own checksum can't be what stops the apply
        out = self.hook("FILE_OPS['copy']", self.entry("p.write_text(%r)" % other), after="p.write_text(%r)" % MINUTES)
        self.assertIn("RC 1", out)
        self.assertIn("changed since it was staged", out)
        self.assertFalse(self.filed())

    def test_same_size_different_content_before_the_remove_is_refused_and_left_alone(self):
        self.decide("approved", "approved")
        other = "X" * len(MINUTES)
        out = self.hook("FILE_OPS['remove']", self.entry("p.write_text(%r)" % other))
        self.assertIn("RC 1", out)
        self.assertEqual((self.v.root / FILE).read_text(), other)       # not deleted
        self.assertFalse(self.filed())

    def test_a_link_with_the_same_bytes_in_place_of_the_file_is_refused_at_the_remove(self):
        same = self.v.root / f"{ABC}/documents/same-bytes.txt"
        same.parent.mkdir(parents=True, exist_ok=True)
        same.write_text(MINUTES, encoding="utf-8")                  # the checksum matches: only not following the link stops it
        self.decide("approved", "approved")
        out = self.hook("FILE_OPS['remove']", self.entry("p.unlink(); p.symlink_to(%r)" % str(same)))
        self.assertIn("RC 1", out)
        self.assertIn("is not a regular file", out)
        self.assertTrue(same.exists())

    def test_a_different_file_of_the_same_name_swapped_in_after_the_read_is_put_back_not_lost(self):
        """A hook on the backup (after the file was read and checked, before the unlink) puts a different file in its place."""
        self.decide("approved", "approved")
        out = self.hook("stash", ("p = Path('inbox') / %r; " + HOLD + "p.unlink(); p.write_text('Somebody else\\'s file\\n')") % Path(FILE).name)
        self.assertIn("RC 1", out)
        self.assertIn("a different file was put there; it is left alone", out)
        self.assertEqual((self.v.root / FILE).read_text(), "Somebody else's file\n")
        self.assertFalse(self.filed())

    def test_the_folder_swapped_for_a_link_after_the_open_does_not_redirect_the_unlink(self):
        docs = self.v.root / f"{ABC}/documents"
        docs.mkdir(parents=True, exist_ok=True)
        victim = docs / Path(FILE).name
        victim.write_text("A contract with the same file name\n")
        self.decide("approved", "approved")
        out = self.hook("stash", "os.rename('inbox', 'inbox.real'); os.symlink(%r, 'inbox')" % str(docs))
        self.assertIn("RC 0", out)
        self.assertTrue(victim.exists())                              # a path unlink would have deleted it
        self.assertEqual(victim.read_text(), "A contract with the same file name\n")
        self.assertFalse((self.v.root / "inbox.real" / Path(FILE).name).exists())    # the staged file was removed from the open folder

    def test_inbox_swapped_for_a_link_before_the_remove_deletes_nothing_of_the_target(self):
        docs = self.v.root / f"{ABC}/documents"
        docs.mkdir(parents=True, exist_ok=True)
        victim = docs / Path(FILE).name
        victim.write_text("A contract with the same file name\n")
        self.decide("approved", "approved")
        out, _ = self.run_driver("remove", "os.rename('inbox', 'inbox.real'); os.symlink(%r, 'inbox')" % str(docs))
        self.assertTrue(victim.exists())
        self.assertEqual(victim.read_text(), "A contract with the same file name\n")
        self.assertIn("RC 1", out)                                   # the apply stopped and rolled back
        self.assertEqual(self.v.rows("actions"), [])
        self.assertEqual(self.processed(), "")

    def test_a_folder_in_inbox_swapped_before_the_remove_deletes_nothing_of_the_target(self):
        (self.v.root / "inbox/sub").mkdir()
        name = self.stage_more("inbox/sub/n.txt", "Nested minutes\n", title="[ABC] Nested call")
        self.approve(name)
        other = self.v.root / f"{ABC}/documents/other-inbox"
        (other / "sub").mkdir(parents=True)
        victim = other / "sub/n.txt"
        victim.write_text("Nested minutes\n")                         # the very same bytes
        out, _ = self.run_driver("remove", "os.rename('inbox', 'inbox.real'); os.symlink(%r, 'inbox')" % str(other))
        self.assertTrue(victim.exists())
        self.assertIn("RC 1", out)

    def test_the_file_swapped_for_a_link_before_the_remove_is_not_removed(self):
        target = self.contract()
        self.decide("approved", "approved")
        out, _ = self.run_driver("remove", "p = Path('inbox') / %r; p.unlink(); p.symlink_to(%r)" % (Path(FILE).name, str(target)))
        self.assertTrue(target.exists())
        self.assertIn("RC 1", out)
        self.assertEqual(self.v.rows("actions"), [])

    def test_the_copy_of_a_link_swapped_in_after_the_check_is_a_clean_refusal_with_no_absolute_path(self):
        target = self.v.root / f"{ABC}/documents/same-bytes.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(MINUTES, encoding="utf-8")                 # same bytes: only refusing the link stops the copy
        self.decide("approved", "approved")
        out, log = self.run_driver("copy", "p = Path('inbox') / %r; p.unlink(); p.symlink_to(%r)" % (Path(FILE).name, str(target)))
        self.assertIn("RC 1", out)
        self.assertIn("the source is a link", out + log)                    # guard-small's open_copy_source, the stored path only
        for root in {str(self.v.root), os.path.realpath(self.v.root)}:      # the data's path (script file names in a traceback are code)
            self.assertNotIn(root + "/inbox", out + log)
            self.assertNotIn(root + "/projects", out + log)
        self.assertFalse(self.filed())
        self.assertTrue(target.exists())


class Undo(Base):
    def test_undo_then_approve_both_files_the_minutes_again(self):
        self.decide("approved", "pending")
        self.v.run("apply")
        self.assertTrue(self.filed())
        self.v.run("undo")
        self.assertTrue(self.inbox())                               # the inbox copy is back
        self.assertFalse(self.filed())
        self.assertEqual(self.processed().strip(), "")
        self.assertEqual(self.proposal()["meeting"]["minutes_decision"], "approved")
        self.decide("approved", "approved")
        r = self.v.run("apply")
        self.assertIn("filed 1", r.stdout)
        self.assertTrue(self.filed())
        self.assertFalse(self.inbox())
        self.assertIn(f"{FILED} | 2", self.processed())
        self.assertEqual(len(self.v.rows("actions")), 2)
        self.assertTrue((self.v.root / "system/staging/applied" / self.name).exists())


class LongNames(Base):
    """The private name carries no part of the file's name: a name near the 255-byte limit still files."""

    def check(self, name, title):
        text = "Minutes with a long file name\n"
        proposal = self.stage_more(f"inbox/{name}", text, title=f"[ABC] {title}")
        self.approve(proposal)
        r = self.v.run("apply", proposal)
        self.assertIn("filed 1", r.stdout)
        self.assertFalse((self.v.root / "inbox" / name).exists())
        self.assertEqual((self.v.root / f"{ABC}/minutes/2026-10-12 {title}.txt").read_text(), text)

    def test_a_240_byte_name_files(self):
        name = "a" * 236 + ".txt"
        self.assertEqual(len(name.encode()), 240)
        self.check(name, "Long ascii")

    def test_a_78_character_cjk_name_files(self):
        name = "会" * 78 + ".txt"
        self.assertEqual(len(name.encode()), 238)
        self.check(name, "Long cjk")


class UndoSkipped(Base):
    def test_an_item_skipped_by_undo_does_not_leave_the_minutes_unfiled(self):
        self.decide("approved", "pending")
        self.v.run("apply")
        con = sqlite3.connect(self.v.root / "system/tracker.db")      # test setup only: a stray outside edit
        con.execute("UPDATE actions SET owner = 'Sara Khan' WHERE id = 'ABC-A-001'")
        con.commit()
        con.close()
        out = self.v.run("undo").stdout
        self.assertIn("skipped ABC-A-001: changed since that apply", out)
        self.assertTrue(self.inbox())                                  # the file is back in inbox/, the item stays applied
        self.assertFalse(self.filed())
        self.decide("applied-keep", "rejected")
        r = self.v.run("apply")
        self.assertIn("filed 1", r.stdout)
        self.assertTrue(self.filed())
        self.assertFalse(self.inbox())
        self.assertIn(FILED, self.processed())
        self.assertTrue((self.v.root / "system/staging/applied" / self.name).exists())


class HandWritten(Base):
    """A proposal edited to drop `kind` keeps the checks while its ops carry the checksum; `to` stays in the minutes folder."""

    def edit(self, fn):
        p = self.v.root / "system/staging" / self.name
        data = json.loads(p.read_text())
        fn(data["meeting"])
        p.write_text(json.dumps(data, indent=2))

    def test_without_kind_a_link_swap_still_deletes_nothing(self):
        target = self.contract()
        self.edit(lambda m: m.pop("kind"))
        self.swap(lambda f: f.symlink_to(target))
        self.decide("approved", "approved")
        r = self.v.run("apply", self.name, ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertTrue(target.exists())
        self.assertFalse(self.filed())

    def move_out(self, m, drop_kind):
        for op in m["file_ops"]:
            if op["op"] == "copy":
                op["to"] = f"{ABC}/documents/2026-10-12 Vendor call.txt"
        if drop_kind:
            m.pop("kind", None)

    def test_a_copy_to_outside_the_minutes_folder_is_refused_with_or_without_kind(self):
        for drop_kind in (False, True):
            self.edit(lambda m, d=drop_kind: self.move_out(m, d))
            r = self.v.run("validate", str(self.v.root / "system/staging" / self.name), ok=False)
            self.assertEqual(r.returncode, 1, drop_kind)
            self.assertIn("is not in the matched project's minutes folder", r.stdout)
        self.assertFalse((self.v.root / f"{ABC}/documents/2026-10-12 Vendor call.txt").exists())


class FolderDestination(Base):
    def test_a_folder_at_the_destination_is_a_clean_refusal(self):
        (self.v.root / FILED).mkdir(parents=True)
        r = self.v.run("validate", str(self.v.root / "system/staging" / self.name), ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("is a folder", r.stdout)
        self.assertNotIn("Traceback", r.stdout + r.stderr)
        self.assertNotIn(str(self.v.root), r.stdout + r.stderr)
        self.decide("approved", "approved")
        r = self.v.run("apply", self.name, ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("is a folder", r.stdout)
        self.assertNotIn("Traceback", r.stdout + r.stderr)
        self.assertNotIn(str(self.v.root), r.stdout + r.stderr)
        self.assertTrue(self.inbox())


# ===== the E1 re-review's open probes (rebased on guard-small) =====
FLIP = r"""
import hashlib, json, os, sys, threading
from pathlib import Path
a = json.loads(sys.stdin.read())
root = Path.cwd()
sys.path.insert(0, "system/scripts")
import paths, tracker
code, n_iter = a["code"], a["n"]
mdir = paths.folder(code, "minutes")
mdir.mkdir(parents=True, exist_ok=True)
contract = paths.project_dir(code) / "documents/contract.txt"
contract.parent.mkdir(parents=True, exist_ok=True)
contract.write_text("CONTRACT\n")
outside = Path(a["outside"])
STAGED = b"staged minutes\n"
sha = hashlib.sha256(STAGED).hexdigest()
blk = {"kind": tracker.BY_OTHERS, "projects": [code]}
rel = "inbox/m.txt"
f = root / rel
stats = {"copied": 0, "removed": 0, "bad": []}
def flipper(stop, k):
    i = 0
    alt = root / f"inbox/.alt{k}"
    while not stop.is_set():
        try:
            if alt.exists() or alt.is_symlink():
                alt.unlink()
            m = i % 6
            if m == 0:
                os.symlink(contract, alt)
            elif m == 1:
                alt.write_bytes(STAGED)
            elif m == 2:
                alt.write_bytes(b"DIFFERENT\n")
            elif m == 3:
                os.mkfifo(alt)
            elif m == 4:
                os.link(contract, alt)
            else:
                os.link(outside, alt)
            os.replace(alt, f)
        except OSError:
            pass
        i += 1
for it in range(n_iter):
    for p in mdir.iterdir():
        p.unlink()
    for p in (root / "inbox").iterdir():
        if p.name.startswith((".creaite-removing-", ".alt")):
            p.unlink()
    if f.exists() or f.is_symlink():
        f.unlink()
    f.write_bytes(STAGED)
    stop = threading.Event()
    th = threading.Thread(target=flipper, args=(stop, it))
    if it % 3:                               # two rounds in three flip during the copy too; every third, only during the remove
        th.start()
    dst = f"{paths.rel(mdir)}/m{it}.txt"
    done = []
    try:
        fop = {"op": "copy", "from": rel, "to": dst, "src_sha256": sha}
        tracker.check_file_op(fop, blk)
        tracker._op_copy(it + 1, fop, blk, done)
        stats["copied"] += 1
    except (tracker.Invalid, OSError):
        pass
    if not it % 3:
        th.start()
    try:
        tracker._op_remove(it + 1, {"op": "remove", "path": rel, "src_sha256": sha}, blk, done)   # an apply each
        stats["removed"] += 1
    except (tracker.Invalid, OSError) as e:
        if str(root) in str(e) or os.path.realpath(root) in str(e):
            stats["bad"].append("absolute path in a message: " + type(e).__name__ + " " + str(e)[:200])
    stop.set()
    th.join()
    if contract.read_text() != "CONTRACT\n" or outside.read_text() != "OUTSIDE\n":
        stats["bad"].append(f"{it}: a link's target changed")
    for p in mdir.iterdir():
        if p.is_symlink() or p.read_bytes() != STAGED:
            stats["bad"].append(f"{it}: filed something else ({p.name})")
print(json.dumps(stats))
"""


class Probes(Base):
    """The re-review's open probes: case variants, archive and hidden folders, odd names, links and pipes at stage, one file
    staged twice (as a transcript and as someone else's minutes), and the copy/remove flip."""

    def spec_file(self, **spec):
        f = self.v.root / "system/staging/drafts/probe.json"
        base = {"title": TITLE, "date": DAY, "projects": ["ABC"], "as": "minutes", "items": ITEMS}
        base.update(spec)
        f.write_text(json.dumps({k: v for k, v in base.items() if v is not None}))
        return f

    def stage_probe(self, timeout=60, **spec):
        f = self.spec_file(**spec)
        try:
            return subprocess.run([sys.executable, str(self.v.root / "system/scripts/minutes.py"), "stage", str(f)],
                                  cwd=self.v.root, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            self.fail("stage hung on the file (a pipe)")

    def test_two_titles_differing_only_in_case_get_two_files_and_both_file(self):
        """'Vendor call' and 'Vendor Call' (two people's minutes of one meeting): one file on macOS; the second is numbered at
        stage, so both are filed and the apply never fails part way."""
        second = self.stage_more("inbox/theirs.txt", "Their minutes of the same call\n", title="[ABC] Vendor Call")
        tos = [next(o["to"] for o in json.loads((self.v.root / "system/staging" / n).read_text())["meeting"]["file_ops"]
                    if o["op"] == "copy") for n in (self.name, second)]
        self.assertNotEqual(tos[0].casefold(), tos[1].casefold(), tos)
        self.approve(self.name)
        self.approve(second)
        r = self.v.run("apply", ok=False)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(sorted((self.v.root / t).read_text() for t in tos), sorted([MINUTES, "Their minutes of the same call\n"]))

    def test_a_case_variant_destination_in_one_apply_is_left_cleanly_in_staging(self):
        """Hand-written (or staged before the numbering): the second copy names the first's file in other capitals. It is left
        in staging with a line saying why; the apply itself succeeds."""
        second = self.stage_more("inbox/theirs.txt", "Their minutes of the same call\n", title="[ABC] Vendor Call")
        p2 = self.v.root / "system/staging" / second
        data = json.loads(p2.read_text())
        for op in data["meeting"]["file_ops"]:
            if op["op"] == "copy":
                op["to"] = FILED.replace("Vendor call", "VENDOR CALL")
        p2.write_text(json.dumps(data, indent=2))
        self.approve(self.name)
        self.approve(second)
        r = self.v.run("apply", ok=False)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("is taken by a different file in this apply", r.stdout)
        # The first applied. On a case-insensitive disk (APFS) both names are one file; on a case-sensitive one (Linux CI) they are
        # two, and whichever proposal the apply took first is the one filed, under its own capitals: exactly one of the two exists.
        mins = (self.v.root / FILED).parent
        there = [p for p in mins.iterdir() if p.name.casefold() == Path(FILED).name.casefold()]
        self.assertEqual(len(there), 1, [p.name for p in there])
        self.assertIn(there[0].read_text(), (MINUTES, "Their minutes of the same call\n"))
        left = [n for n in (self.name, second) if (self.v.root / "system/staging" / n).exists()]
        self.assertEqual(len(left), 1, left)                                        # the other waits, cleanly

    def test_archive_template_and_hidden_folders_and_names_are_refused_at_stage(self):
        mins = self.v.root / f"{ABC}/minutes"
        places = {f"{ABC}/minutes/_Archive/a.txt": "x", f"{ABC}/minutes/99 Archive/a.txt": "x",
                  f"{ABC}/minutes/.hidden/a.txt": "x", f"{ABC}/minutes/_Templates/a.txt": "x",
                  "inbox/.hidden.txt": "x", "inbox/~$draft.docx": "x", "inbox/.sub/a.txt": "x"}
        for rel, text in places.items():
            (self.v.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.v.root / rel).write_text(text)
        self.assertTrue(mins.is_dir())
        for rel in places:
            with self.subTest(rel):
                r = self.stage_probe(file=rel)
                self.assertNotEqual(r.returncode, 0, rel)
                self.assertIn("Nothing staged", r.stdout + r.stderr)

    def test_odd_names_are_refused_at_stage(self):
        for name in ("a\nb.txt", "a‮txt.exe.txt", "a​b.txt", "a\tb.txt", "a⁦b⁩.txt"):
            with self.subTest(repr(name)):
                (self.v.root / "inbox" / name).write_text("x")
                r = self.stage_probe(file=f"inbox/{name}")
                self.assertNotEqual(r.returncode, 0)
                self.assertIn("not a plain path", r.stdout)

    def test_links_hard_links_and_pipes_are_refused_at_stage(self):
        c = self.contract()
        (self.v.root / "inbox/link.txt").symlink_to(c)
        os.link(c, self.v.root / "inbox/hard.txt")
        os.mkfifo(self.v.root / "inbox/pipe.txt")
        for rel, words in (("inbox/link.txt", "link"), ("inbox/hard.txt", "hard link"), ("inbox/pipe.txt", "not a regular file")):
            with self.subTest(rel):
                r = self.stage_probe(file=rel)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn(words, r.stdout)

    def test_one_file_staged_as_minutes_is_not_staged_again_as_a_transcript(self):
        """The first staged keeps the file; the second is refused with the way forward, either way round."""
        spec = {"as": None, "file": None, "transcript": FILE,
                "minutes": {"start": "10:00", "end": "10:30", "attendees": "Omar Ali", "summary": ["x"], "updates": [],
                            "open_questions": []}}
        r = self.stage_probe(**spec)
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertIn("as someone else's minutes: approve or reject that one first", r.stdout)
        (self.v.root / "system/staging" / self.name).unlink()                 # now the other way round
        (self.v.root / "inbox/t.txt").write_text(MINUTES)
        r = self.stage_probe(**dict(spec, transcript="inbox/t.txt"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = self.stage_probe(file="inbox/t.txt")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Approve or reject that one first", r.stdout)

    def test_the_copy_and_remove_flip_never_files_or_deletes_anything_else(self):
        """3,000 rounds: a thread cycles the inbox name between the staged file, other bytes, a link to a vault file, a FIFO and
        hard links to a vault file and to a file outside the vault while the copy and the remove run."""
        import tempfile
        out = Path(tempfile.mkdtemp(prefix="creaite-outside-", dir=self.v.root.parent))
        try:
            (out / "secret.txt").write_text("OUTSIDE\n")
            r = subprocess.run([sys.executable, "-c", FLIP], cwd=self.v.root, capture_output=True, text=True, timeout=1500,
                               input=json.dumps({"code": "ABC", "n": int(os.environ.get("E1_FLIP", "3000")),
                                                 "outside": str(out / "secret.txt")}))
            self.assertEqual(r.returncode, 0, r.stderr[-2000:])
            got = json.loads(r.stdout.strip().splitlines()[-1])
            print(f"\nflip: copied {got['copied']}, removed {got['removed']}, bad {len(got['bad'])}", file=sys.stderr)
            self.assertEqual(got["bad"], [], got["bad"][:5])
            self.assertGreater(got["copied"], 0)
        finally:
            shutil.rmtree(out, ignore_errors=True)


CHECK_OPS = r"""
import json, sys
sys.path.insert(0, "system/scripts")
import tracker
data = json.loads(open(sys.argv[1]).read())
blk = data["meeting"]
out = {}
for fop in blk["file_ops"]:
    try:
        tracker.check_file_op(fop, blk)
        out[fop["op"]] = "ok"
    except tracker.Invalid as e:
        out[fop["op"]] = "refused: " + str(e)
print(json.dumps(out))
"""


class EachOpChecked(Base):
    """Validation checks the copy and the remove each on its own (a full apply's check of one would otherwise hide the other's)."""

    def check_ops(self):
        r = subprocess.run([sys.executable, "-c", CHECK_OPS, str(self.v.root / "system/staging" / self.name)], cwd=self.v.root,
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_the_staged_file_passes_both(self):
        self.assertEqual(self.check_ops(), {"copy": "ok", "remove": "ok"})

    def test_a_changed_file_is_refused_by_the_copy_and_the_remove_each(self):
        (self.v.root / FILE).write_text(MINUTES.replace("SOW", "XYZ"), encoding="utf-8")
        got = self.check_ops()
        for op in ("copy", "remove"):
            self.assertIn("changed since it was staged", got[op], op)

    def test_a_hard_link_is_refused_by_the_remove_too(self):
        other = self.v.root / f"{ABC}/documents/other-name.txt"
        other.parent.mkdir(parents=True, exist_ok=True)
        os.link(self.v.root / FILE, other)
        got = self.check_ops()
        self.assertIn("has another name", got["remove"])
        self.assertTrue(got["copy"].startswith("refused"), got)


if __name__ == "__main__":
    unittest.main()
