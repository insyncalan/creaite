"""#280 follow-up (Cap's 2.5.4 review): `review.py reject <not a number> --discard` answers plainly, never with a traceback.

Run: python3 dev/tests/test_review_discard_args.py      (a throwaway vault)

Skips until review.py has #280's `reject N --discard` (cmd_discard, from the 2.5.4 line) and its follow-up
(dev/proposals/280-followup/review-discard.py.diff): a word, two numbers or no number at all is refused with one line and
exit code 2, as review.py's other bad arguments are, and nothing in staging changes.
"""
import ast
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import Vault  # noqa: E402

REVIEW = Path(__file__).resolve().parents[2] / "system/scripts/review.py"
HAS_DISCARD = any(isinstance(n, ast.FunctionDef) and n.name == "cmd_discard"
                  for n in ast.parse(REVIEW.read_text(encoding="utf-8")).body)


@unittest.skipUnless(HAS_DISCARD, "review.py has no `reject N --discard` yet (#280, the 2.5.4 line)")
class DiscardArguments(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        cls.v.run("init")

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def staged(self):
        return sorted((p.name, p.read_bytes()) for p in (self.v.root / "system/staging").rglob("*.json"))

    def test_a_bad_number_is_refused_plainly(self):
        self.v.propose("2026-10-21-0900-x", [{"n": 1, "op": "new", "table": "actions", "decision": "pending",
                                               "values": {"project": "ABC", "title": "A thing", "owner": "Alan Carter"}}])
        before = self.staged()
        for args in (["abc"], ["1", "2"], [], ["1-3"], ["-1"]):
            r = self.v.run("reject", *args, "--discard", script="review.py", ok=False)
            out = r.stdout + r.stderr
            self.assertEqual(r.returncode, 2, (args, out))
            self.assertNotIn("Traceback", out, args)
            self.assertNotIn("ValueError", out, args)
            self.assertIn("not discarded", out, args)
            self.assertIn("reject 4 --discard", out, args)
            self.assertEqual(self.staged(), before, args)


if __name__ == "__main__":
    unittest.main()
