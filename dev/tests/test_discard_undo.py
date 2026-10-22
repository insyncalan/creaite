"""#307 path 12: Intake's Discard has an Undo. `review.py restore-discarded <file>` puts a discarded proposal back in staging.

Run: python3 dev/tests/test_discard_undo.py      (quick tier: no Chrome)
- Restore: the proposal returns byte for byte as it was just before Discard (the marker Discard added is the only thing removed), the
  tracker is untouched, and it is in Review again.
- Refusals, in words, exit 2, nothing moved: the name is already taken in staging; a path or traversal; a file that isn't there;
  a file in discarded/ that Discard didn't write; not a proposal name.
- Guard: reach.SCRIPT_COMMANDS classes the command, so a run Alan hasn't confirmed refuses it.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_held_missing_source as hm  # noqa: E402  (the module, so its tests aren't collected here)

REPO = Path(__file__).resolve().parents[2]
PROPOSALS = REPO / "dev/proposals/discard-undo"
COMMAND_IN_TREE = "restore-discarded" in (REPO / "system/scripts/review.py").read_text(encoding="utf-8")
CLASSED_IN_TREE = "restore-discarded" in (REPO / "system/scripts/reach.py").read_text(encoding="utf-8")


def apply_proposals(root, *names):
    """Until the guarded/shared engine takes dev/proposals/discard-undo/*.diff, each test applies them to its throwaway vault."""
    for name in names:
        subprocess.run(["git", "apply", str(PROPOSALS / name)], cwd=root, check=True)


class RestoreDiscarded(unittest.TestCase):
    tearDown = hm.HeldMissingSource.tearDown
    stage_gone, read, number = hm.HeldMissingSource.stage_gone, hm.HeldMissingSource.read, hm.HeldMissingSource.number

    def setUp(self):
        hm.HeldMissingSource.setUp(self)
        if not COMMAND_IN_TREE:
            apply_proposals(self.root, "review.py.diff")

    def discard(self):
        held = self.stage_gone(approve=False)
        before = held.read_bytes()
        r = self.v.run("reject", str(self.number()), "--discard", script="review.py", ok=False, cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return held, before, self.root / "system/staging/discarded" / held.name

    def restore(self, name):
        return self.v.run("restore-discarded", name, script="review.py", ok=False, cwd=self.root)

    def test_restore_puts_it_back_byte_for_byte_and_in_review(self):
        held, before, aside = self.discard()
        tracker_before = self.v.snapshot()[0]
        r = self.restore(held.name)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(f"Put back: {hm.TITLE} is waiting in Intake again.", r.stdout)
        self.assertEqual(held.read_bytes(), before)
        self.assertFalse(aside.exists())
        self.assertEqual(self.v.snapshot()[0], tracker_before)
        self.assertIn(hm.TITLE, self.v.run("list", script="review.py", cwd=self.root).stdout)

    def test_discard_again_after_a_restore_works(self):
        held, before, aside = self.discard()
        self.restore(held.name)
        r = self.v.run("reject", str(self.number()), "--discard", script="review.py", ok=False, cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertTrue(aside.is_file())

    def test_a_second_discard_of_the_same_name_is_put_back_under_its_own_name(self):
        held, before, aside = self.discard()
        held.write_bytes(before)                                # the same name staged again, then discarded again
        r = self.v.run("reject", str(self.number()), "--discard", script="review.py", ok=False, cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stdout)
        second = self.root / "system/staging/discarded" / f"{held.stem}-2{held.suffix}"
        self.assertTrue(second.is_file())
        r = self.restore(second.name)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertTrue(held.is_file(), "back under the name it had in staging")
        self.assertFalse(second.exists())
        self.assertTrue(aside.is_file(), "the first one is still set aside")

    def test_refuses_when_the_name_is_taken_and_moves_nothing(self):
        held, before, aside = self.discard()
        held.write_text("{}", encoding="utf-8")
        r = self.restore(held.name)
        self.assertEqual(r.returncode, 2)
        self.assertIn("already waiting in Intake", r.stdout)
        self.assertEqual(held.read_text(encoding="utf-8"), "{}")
        self.assertTrue(aside.is_file())

    def test_refuses_traversal_paths_and_other_names(self):
        held, before, aside = self.discard()
        outside = self.root / "system/staging/proposed-outside.json"
        outside.write_bytes(before)
        (self.root / "system/staging/discarded/note.txt").write_text("x", encoding="utf-8")
        for bad in ("../proposed-outside.json", "discarded/" + held.name, str(aside), "..", "", "note.txt",
                    "proposed-missing.json", "proposed-../x.json", "/etc/passwd"):
            r = self.restore(bad)
            self.assertEqual(r.returncode, 2, bad)
            self.assertIn("not put back", r.stdout, bad)
        self.assertTrue(aside.is_file())
        self.assertEqual(outside.read_bytes(), before)

    def test_refuses_a_file_discard_did_not_write(self):
        held, before, aside = self.discard()
        stray = self.root / "system/staging/discarded/proposed-stray.json"
        stray.write_text(json.dumps({"meeting": {"title": "x"}}), encoding="utf-8")
        r = self.restore(stray.name)
        self.assertEqual(r.returncode, 2)
        self.assertIn("wasn't set aside by Discard", r.stdout)
        self.assertTrue(stray.is_file())
        stray.write_text("not json", encoding="utf-8")
        self.assertEqual(self.restore(stray.name).returncode, 2)

    def test_the_command_is_classed_so_an_unconfirmed_run_refuses_it(self):
        if not CLASSED_IN_TREE:
            apply_proposals(self.root, "reach.py.diff")
        out = subprocess.run([sys.executable, "-c", "import reach; print(reach.SCRIPT_COMMANDS['review.py'].get('restore-discarded'), reach.RECORD)"],
                             cwd=self.root / "system/scripts", capture_output=True, text=True, check=True).stdout.split()
        self.assertEqual(out[0], out[1], "restore-discarded must be classed record")


if __name__ == "__main__":
    unittest.main()
