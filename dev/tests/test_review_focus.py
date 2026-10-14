"""BL-208: Review one proposal at a time.

Run: python3 dev/tests/test_review_focus.py   (the browser half needs Google Chrome; skipped otherwise)
The queue puts guessed fields first; the spot-check picks routine items at the set rate (stable for a batch, never zero in the first
month); approving in the mode is the list's own decide(); the bulk rules are unchanged (a new risk is never in the routine set).
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402


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


class FocusBrowser(LiveBrowserCase):
    shared_server = False

    @classmethod
    def load(cls, v):
        populate(v)
        v.propose("guess", [{"n": 1, "op": "new", "table": "actions", "values": {"project": "ABC", "description": "Send the revised plan",
                                                                               "owner": "Sara Example", "due_date": "2026-12-04", "raised": "2026-10-10",
                                                                               "source": "projects/ABC Example Programme/minutes/2026-10-10 Steering.docx — Actions"},
                             "match": "strong", "flags": [], "decision": "pending",
                             "inferred": [{"field": "owner", "why": "Sara was named once, near the end"}, {"field": "due_date", "why": "read from “early December”"}]}])
        v.run(script="build_dashboard.py")

    def open_focus(self):
        b = self.b
        b.eval("go('review')")
        b.wait("document.getElementById('rvFocusBtn')")
        b.click("#rvFocusBtn")
        b.wait("document.querySelector('#rvFocus .rftitle')")

    def test_the_card_starts_with_guessed_fields_and_shows_the_source(self):
        b = self.b
        self.open_focus()
        self.assertEqual(b.eval("document.querySelector('#rvFocus .rftitle').textContent"), "Send the revised plan")
        self.assertEqual(b.eval("document.querySelectorAll('#rvFocus .rfrow.guess').length"), 2)
        self.assertIn("dashed", b.eval("getComputedStyle(document.querySelector('#rvFocus .rfrow.guess .rfv')).textDecorationStyle"))
        self.assertIn("Sara was named once", b.eval("document.getElementById('rvFocus').innerText"))
        self.assertIn("2026-10-10 Steering", b.eval("document.querySelector('#rvFocus .rfsrc').innerText"))
        self.assertIn("1 of", b.eval("document.querySelector('#rvFocus .rfhead').innerText"))
        self.assertTrue(b.eval("!!document.querySelector('#rvFocus [data-rf=proj]')"))
        b.key("j")
        self.assertIn("2 of", b.eval("document.querySelector('#rvFocus .rfhead').innerText"))
        b.key("k")
        self.assertIn("1 of", b.eval("document.querySelector('#rvFocus .rfhead').innerText"))
        b.key("Escape")
        b.wait("!document.getElementById('rvFocus')")
        self.assertEqual(b.errors, [])

    def test_approving_here_is_approving_in_the_list(self):
        b = self.b
        self.open_focus()
        n = b.eval("RF.q[RF.i]")
        b.key("a")
        b.wait(f"REV.find(x=>x.n==={n}).done==='approved' || document.querySelector('#rvFocus .rftitle')?.textContent!=='Send the revised plan'", 15)
        p = self.v.root / "system/staging/proposed-guess.json"
        item = json.loads(p.read_text())["items"][0]
        self.assertEqual(item["decision"], "approved")
        self.assertEqual([a["description"] for a in self.v.rows("actions") if a["description"] == "Send the revised plan"], [])   # not applied
        self.assertEqual(item["inferred"][0]["field"], "owner")              # the guesses stay with the item

    def test_reject_asks_for_the_reason_and_the_routine_rest_keeps_the_bulk_rule(self):
        b = self.b
        self.open_focus()
        b.key("r")
        b.wait("document.getElementById('rvReason')")
        b.key("Escape")
        routine = b.eval("rfRoutine().map(r=>r.kind)")
        self.assertNotIn("draft", routine)
        self.assertFalse(b.eval("rfRoutine().some(r=>r.kind==='raid'&&r.rec&&r.rec.type==='Risk')"))


if __name__ == "__main__":
    unittest.main()
