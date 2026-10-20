"""BL-208: Review one proposal at a time.

Run: python3 dev/tests/test_review_focus.py
The queue puts guessed fields first; the spot-check picks routine items at the set rate (stable for a batch, never zero in the first
month). #232 C2: the focus view (the browser half, FocusBrowser) went with the old Review page; the queue's data (review.focus_queue,
D.review_focus) is still built, and this is its test.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))


class Queue(unittest.TestCase):
    def setUp(self):
        import review
        self.review = review

    def rows(self, n_routine):
        rows = [{"n": i, "p": "ABC", "file": "proposed-a.json", "kind": "actions"} for i in range(1, n_routine + 1)]
        rows += [{"n": 100, "p": "ABC", "file": "proposed-a.json", "kind": "raid", "indiv": True},
                 {"n": 101, "p": "ABC", "file": "proposed-a.json", "kind": "actions", "inferred": [{"field": "owner", "why": "named once"}]},
                 {"n": 102, "p": None, "file": "proposed-b.json", "kind": "actions"}]
        return rows

    def test_guessed_fields_first_then_what_needs_you_then_the_spot_checks(self):
        q = self.review.focus_queue(self.rows(20), 0.1)
        self.assertEqual(q["queue"][0], 101)
        self.assertEqual(set(q["queue"][1:3]), {100, 102})
        self.assertEqual(len(q["spot"]), 2)                                  # one in ten of 20
        self.assertEqual(q["queue"][3:], q["spot"])
        self.assertTrue(set(q["spot"]) <= set(range(1, 21)))
        self.assertNotIn(100, q["routine"])                                  # a new risk is never routine
        self.assertEqual(q, self.review.focus_queue(self.rows(20), 0.1))    # stable for the batch

    def test_the_rate_never_zero_in_the_first_month(self):
        r = self.review.spot_rate
        self.assertEqual(r({"review": {}}), 0.1)
        self.assertEqual(r({"review": {"spot_check_every": 5}}), 0.2)
        self.assertEqual(r({"review": {"spot_check_every": 0}}, "2026-10-01 09:00", "2026-10-15"), 0.1)
        self.assertEqual(r({"review": {"spot_check_every": 0}}, "2026-08-01 09:00", "2026-10-15"), 0.0)
        self.assertEqual(self.review.focus_queue(self.rows(3), 0.1)["spot"].__len__(), 1)   # at least one when there are any

    def test_only_well_formed_guesses_are_kept(self):
        c = self.review.clean_inferred([{"field": "owner", "why": "  Sara was  named once "}, {"field": "colour", "why": "x"}, "bad", {"field": "due_date"}])
        self.assertEqual(c, [{"field": "owner", "why": "Sara was named once"}])


if __name__ == "__main__":
    unittest.main()
