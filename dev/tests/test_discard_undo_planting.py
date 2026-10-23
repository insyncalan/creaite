"""#307 path 12, Cap's H1: Discard's Undo restores only what Discard itself set aside.

Run: python3 dev/tests/test_discard_undo_planting.py      (quick tier: no Chrome)
- reach.py (dev/proposals/discard-undo/reach.py.diff): system/staging/discarded/ is on the never list for create, change, delete and move,
  so ask creaite, a sweep, a confirmed run and filechange.py can't plant, edit or remove a set-aside proposal; the ledger Discard writes
  (system/staging/discarded-ledger.jsonl) is already on it (system/staging/*.jsonl).
- review.py (review.py.diff): Discard appends {name, sha256 of the file as set aside} to the ledger; restore-discarded needs the newest
  ledger line for the name to carry the file's own sha256. Refused in words, nothing moved: a file planted with no ledger line, a forged
  line without a checksum, a wrong checksum, a file edited after Discard, a second Undo (replay), a symlink, a second hard link.
- Mutants: no checksum check goes red; no never rule goes red.
Until this tree has the diffs each test applies them to its throwaway vault (never to this tree).
"""
import hashlib
import io
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_held_missing_source as hm  # noqa: E402
from test_discard_undo import PROPOSALS, COMMAND_IN_TREE  # noqa: E402

REPO = hm.REPO
NEVER_IN_TREE = "system/staging/discarded" in (REPO / "system/scripts/reach.py").read_text(encoding="utf-8")
LEDGER_IN_TREE = "discarded-ledger" in (REPO / "system/scripts/review.py").read_text(encoding="utf-8")


def apply(root, name):
    subprocess.run(["git", "apply", str(PROPOSALS / name)], cwd=root, check=True)


class Base(unittest.TestCase):
    tearDown = hm.HeldMissingSource.tearDown
    stage_gone, read, number = hm.HeldMissingSource.stage_gone, hm.HeldMissingSource.read, hm.HeldMissingSource.number

    def setUp(self, mutation=None):
        hm.HeldMissingSource.setUp(self)
        if not (COMMAND_IN_TREE and LEDGER_IN_TREE):
            apply(self.root, "review.py.diff")
        if not NEVER_IN_TREE:
            apply(self.root, "reach.py.diff")
        if mutation:
            f = self.root / mutation[0]
            text = f.read_text(encoding="utf-8")
            assert mutation[1] in text, mutation[1]
            f.write_text(text.replace(mutation[1], mutation[2], 1), encoding="utf-8")
        self.stage = self.root / "system/staging"
        self.ledger = self.stage / "discarded-ledger.jsonl"

    def discard(self):
        held = self.stage_gone(approve=False)
        before = held.read_bytes()
        r = self.v.run("reject", str(self.number()), "--discard", script="review.py", ok=False, cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return held, before, self.stage / "discarded" / held.name

    def restore(self, name):
        return self.v.run("restore-discarded", name, script="review.py", ok=False, cwd=self.root)

    def py(self, code, *args):
        return subprocess.run([sys.executable, "-c", code, *args], cwd=self.root / "system/scripts", capture_output=True, text=True,
                              env={**os.environ, "CREAITE_ROOT": str(self.root)})

    def refused(self, name, words):
        """The restore is refused in words and nothing moves: the file stays, staging gets nothing."""
        waiting = sorted(p.name for p in self.stage.glob("proposed-*.json"))
        aside = self.stage / "discarded" / name
        was = aside.read_bytes() if aside.exists() else None
        r = self.restore(name)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("not put back", r.stdout)
        self.assertIn(words, r.stdout)
        self.assertEqual(sorted(p.name for p in self.stage.glob("proposed-*.json")), waiting)
        if was is not None:
            self.assertEqual(aside.read_bytes(), was)


class Planting(Base):
    def test_discard_records_the_checksum_and_a_genuine_undo_still_works(self):
        held, before, aside = self.discard()
        last = json.loads(self.ledger.read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(last["name"], aside.name)
        self.assertEqual(last["sha256"], hashlib.sha256(aside.read_bytes()).hexdigest())
        r = self.restore(held.name)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(held.read_bytes(), before)
        self.assertFalse(aside.exists())

    def test_a_file_planted_with_no_ledger_line_is_refused(self):
        held, before, aside = self.discard()
        planted = self.stage / "discarded/proposed-planted.json"
        data = json.loads(aside.read_text(encoding="utf-8"))
        data["discarded"]["name"] = "proposed-planted.json"
        planted.write_text(json.dumps(data), encoding="utf-8")
        self.refused(planted.name, "no record of setting that proposal aside")

    def test_a_forged_ledger_line_without_a_checksum_is_refused(self):
        held, before, aside = self.discard()
        planted = self.stage / "discarded/proposed-planted.json"
        data = json.loads(aside.read_text(encoding="utf-8"))
        planted.write_text(json.dumps(data), encoding="utf-8")
        with open(self.ledger, "a", encoding="utf-8") as f:
            f.write(json.dumps({"name": planted.name}) + "\n")
        self.refused(planted.name, "no record of setting that proposal aside")

    def test_a_wrong_checksum_is_refused(self):
        held, before, aside = self.discard()
        planted = self.stage / "discarded/proposed-planted.json"
        planted.write_bytes(aside.read_bytes())
        with open(self.ledger, "a", encoding="utf-8") as f:
            f.write(json.dumps({"name": planted.name, "sha256": "0" * 64}) + "\n")
        self.refused(planted.name, "changed since Discard set it aside")

    def test_a_file_edited_after_discard_is_refused(self):
        held, before, aside = self.discard()
        data = json.loads(aside.read_text(encoding="utf-8"))
        data["items"] = [{"id": "XYZ-A-999", "type": "action", "title": "PLANTED", "decision": "approved"}]
        data["discarded"]["name"] = "proposed-planted.json"
        aside.write_text(json.dumps(data), encoding="utf-8")
        self.refused(aside.name, "changed since Discard set it aside")
        self.assertFalse((self.stage / "proposed-planted.json").exists())

    def test_a_second_undo_is_refused(self):
        held, before, aside = self.discard()
        self.assertEqual(self.restore(held.name).returncode, 0)
        aside.write_bytes(before)                           # the same bytes put back without Discard: the last ledger line is the restore
        held.unlink()
        self.refused(aside.name, "no record of setting that proposal aside")

    def test_a_symlink_and_a_second_hard_link_are_refused(self):
        held, before, aside = self.discard()
        target = self.root / "outside.json"
        os.replace(aside, target)
        os.symlink(target, aside)
        self.refused(aside.name, "isn't one Discard set aside")
        aside.unlink()
        os.link(target, aside)                              # two names for one file
        self.refused(aside.name, "isn't one Discard set aside")

    def test_the_second_discard_of_a_name_is_a_new_line_and_undoes_under_its_own_name(self):
        held, before, aside = self.discard()
        held.write_bytes(before)
        r = self.v.run("reject", str(self.number()), "--discard", script="review.py", ok=False, cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stdout)
        second = self.stage / "discarded" / f"{held.stem}-2{held.suffix}"
        self.assertEqual(self.restore(second.name).returncode, 0)
        self.assertTrue(held.is_file() and aside.is_file())


class NeverList(Base):
    PROBE = ("import sys, reach\n"
             "from pathlib import Path\n"
             "root = Path(sys.argv[1])\n"
             "for rel in ('system/staging/discarded', 'system/staging/discarded/proposed-x.json', 'system/staging/discarded-ledger.jsonl'):\n"
             "    for op in ('create', 'change', 'delete', 'move'):\n"
             "        for marked in (False, True):\n"
             "            kind, why = reach.classify(root / rel, op, marked=marked)\n"
             "            print(rel, op, marked, kind)\n")

    def classes(self):
        r = self.py(self.PROBE, str(self.root))
        self.assertEqual(r.returncode, 0, r.stderr)
        return [line.rsplit(" ", 1) for line in r.stdout.splitlines()]

    def check_never(self):
        got = self.classes()
        self.assertEqual(len(got), 24)
        for line, kind in got:
            self.assertEqual(kind, "never", line)

    def test_nothing_but_discard_can_create_change_delete_or_move_there(self):
        self.check_never()

    def test_reading_a_set_aside_proposal_is_still_open(self):
        r = self.py("import sys, reach\nfrom pathlib import Path\nprint(reach.classify(Path(sys.argv[1]) / 'system/staging/discarded/proposed-x.json', 'read')[0])",
                    str(self.root))
        self.assertEqual(r.stdout.strip(), "ordinary", r.stderr)

    def test_filechange_cannot_plant_edit_delete_or_move(self):
        held, before, aside = self.discard()
        was = aside.read_bytes()
        new = self.stage / "discarded/proposed-planted.json"
        src = self.root / "system/staging/drafts/planted.json"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_bytes(was.replace(b"Discarded", b"Planted"))
        fc = str(self.root / "system/scripts/filechange.py")
        for args in (["create", str(new), "--from", str(src)], ["edit", str(aside), "--from", str(src)], ["delete", str(aside)],
                     ["move", str(aside), str(self.stage / "proposed-moved.json")], ["create", str(self.stage / "discarded-ledger.jsonl"), "--from", str(src)]):
            r = subprocess.run([sys.executable, fc, *args, "--why", "planting test", "--via", "ask"], cwd=self.root, capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0, (args, r.stdout))
            self.assertIn("written only by creaite", r.stdout + r.stderr, args)
        self.assertFalse(new.exists())
        self.assertFalse((self.stage / "proposed-moved.json").exists())
        self.assertEqual(aside.read_bytes(), was)

    def test_a_direct_write_by_an_ask_run_is_refused_by_the_hook(self):
        code = ("import sys, reach\n"
                "ok, why = reach.hook_decision('Write', {'file_path': sys.argv[1], 'content': '{}'}, 'ask', 'r1')\n"
                "print(ok)\n")
        r = self.py(code, str(self.stage / "discarded/proposed-planted.json"))
        self.assertEqual(r.stdout.strip(), "False", r.stderr)

    def test_discard_itself_still_writes_there(self):
        held, before, aside = self.discard()                # review.py, run by the live server through the record route, not filechange
        self.assertTrue(aside.is_file() and self.ledger.is_file())


MUTANTS = [
    ("no checksum check", "system/scripts/review.py", '    if rec.get("sha256") != _sha(src):', "    if False:"),
]


class Mutants(unittest.TestCase):
    def test_removing_the_checksum_check_turns_the_edited_file_test_red(self):
        class M(Planting):
            def setUp(self):
                Base.setUp(self, MUTANTS[0][1:])
        r = unittest.TextTestRunner(stream=io.StringIO()).run(unittest.defaultTestLoader.loadTestsFromName(
            "test_a_file_edited_after_discard_is_refused", M))
        self.assertFalse(r.wasSuccessful(), "mutant survived: no checksum check")

    def test_removing_the_never_rule_turns_the_reach_test_red(self):
        class M(NeverList):
            def setUp(self):
                Base.setUp(self)
                f = self.root / "system/scripts/reach.py"
                lines = [x for x in f.read_text(encoding="utf-8").splitlines(True) if '"system/staging/discarded"' not in x]
                f.write_text("".join(lines), encoding="utf-8")
        r = unittest.TextTestRunner(stream=io.StringIO()).run(unittest.defaultTestLoader.loadTestsFromName(
            "test_nothing_but_discard_can_create_change_delete_or_move_there", M))
        self.assertFalse(r.wasSuccessful(), "mutant survived: no never rule")


if __name__ == "__main__":
    unittest.main()
