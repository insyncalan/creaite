"""#241 D / Team Cap's M1: a proposal whose top-level `note` is the wrong shape must not roll the whole apply back.

Before the history diff an unexpected extra field in a proposal was ignored: the apply succeeded. With the item-history diff
(dev/proposals/work-item-history/tracker.diff) `emit_event` and item_history.source_of read the proposal's `note` as {"path": ...};
a string or a list made the whole apply roll back (rc 1, no rows). Now the history never stops an apply: emit_event catches any
fault (logging its type only) and item_history reads a field of the wrong shape as absent.

Run: python3 dev/tests/test_malformed_note.py     The apply tests skip until the guarded history diff is applied (emit_event in tracker.py).
"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "system" / "scripts"))
from test_tracker import Vault, action  # noqa: E402

CHAIN = "def emit_event" in (REPO / "system/scripts/tracker.py").read_text(encoding="utf-8")
BAD = {"string": "a note", "list": ["x"], "number": 7, "bool": True, "nested list": [{"path": "a"}], "nested dict": {"path": {"x": 1}},
       "path is a list": {"path": ["x"]}, "path is a number": {"path": 5}}


class MalformedNote(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")

    def tearDown(self):
        self.v.cleanup()

    @unittest.skipUnless(CHAIN, "needs the guarded history diff (emit_event in tracker.py)")
    def test_an_apply_succeeds_whatever_shape_the_note_has(self):
        for name, note in BAD.items():
            with self.subTest(note=name):
                before = len(self.v.rows("actions"))
                self.v.propose("n-" + name.replace(" ", "-"), [action(1, description=f"Item for {name}")], note=note)
                r = self.v.run("apply", ok=False)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertEqual(len(self.v.rows("actions")), before + 1, "the change stands")

    @unittest.skipUnless(CHAIN, "needs the guarded history diff (emit_event in tracker.py)")
    def test_the_item_still_has_its_history_and_an_undo_works(self):
        self.v.propose("n-ok", [action(1, description="Plain item")], note={"path": "projects/ABC Example/notes/x.md"})
        self.v.propose("n-bad", [action(2, description="Odd item")], note="oops")
        self.assertEqual(self.v.run("apply", ok=False).returncode, 0)
        self.assertEqual(len(self.v.rows("actions")), 2)
        self.assertEqual(self.v.run("undo", ok=False).returncode, 0)
        self.assertEqual(len(self.v.rows("actions")), 0)

    def test_history_reads_a_note_of_the_wrong_shape_as_absent(self):
        """item_history (plain code, no guarded file): source_of and derive never raise on a malformed note, item or values."""
        import item_history as ih
        for note in BAD.values():
            data = {"source_run": "cx-edit", "note": note}
            for item in ({"values": note}, {"values": {"source": None}, "decided_in": ["x"]}, note, None):
                self.assertEqual(ih.source_of(item, data, "proposed-x.json"), ih.source_of({}, {}, "proposed-x.json"))
                ih.derive("proposed-x.json", data, item)
            ih.derive("proposed-x.json", note, note)
        self.assertEqual(ih.source_of({}, {"note": {"path": "a/b.md"}}, "proposed-x.json"), "a/b.md")


if __name__ == "__main__":
    unittest.main()
