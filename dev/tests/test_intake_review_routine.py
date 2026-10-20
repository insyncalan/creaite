"""#232-B (v2.5.0): Intake's proposal rows and Approve routine, in a real browser against the live server.
The page's rule is the server's (rvBulkOK reads the row's `hold`, `invalid` included); a meeting's proposals come in two groups,
Needs your decision first, then Routine, with the approved wording; Approve routine (n) is one apply and one Undo, never covers the
first group and keeps the meeting open.

Run: python3 dev/tests/test_intake_review_routine.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import intake_review_support as S  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402

WORDING = "Each has a project and no conflict, and none is a change you approve one by one."


class Routine(LiveBrowserCase):
    width, height = 1400, 1000

    @classmethod
    def load(cls, v):
        S.load(v)

    def test_rvBulkOK_equals_hold(self):
        b = self.b
        b.eval("go('today')")
        rows = b.eval("""(()=>{ const base={kind:'actions',p:'ABC',flags:[],indiv:false,rec:{t:'x'}};
          const syn=[{...base,hold:''},{...base,hold:'invalid',flags:['invalid']},{...base,hold:'conflict',flags:['conflict']},{...base,hold:'new risk',indiv:true},
            {...base,hold:'need a project',p:null},{...base,hold:'minutes',kind:'draft'},{...base,hold:'',done:'approved'}];
          return [...REV.map(r=>[rvBulkOK(r),!r.done&&r.hold===''&&'hold' in r]), ...syn.map(r=>[rvBulkOK(r),!r.done&&r.hold===''])]; })()""")
        self.assertGreater(len(rows), 8)
        for got, want in rows:
            self.assertEqual(got, want)

    def test_groups_needs_first_and_the_approved_wording(self):
        b = self.b
        S.open_meeting(b)
        heads = b.eval("[...document.querySelectorAll('#v-intake-review tr.icsubhead')].slice(0,2).map(t=>[t.dataset.irg,t.textContent])")
        self.assertEqual([h[0] for h in heads], ["needs", "routine"])
        self.assertIn("Needs your decision · 4", heads[0][1])
        self.assertIn("Routine · 4", heads[1][1])
        self.assertIn(WORDING, heads[1][1])
        self.assertIn("Approve routine (4)", b.eval("document.querySelector('[data-irg=routine] [data-ira=routine]').textContent"))
        self.assertFalse(b.eval("document.querySelector('[data-irg=routine] [data-ira=routine]').disabled"))

    def test_approve_routine_is_one_apply_one_undo_and_leaves_the_first_group(self):
        b = self.b
        mid = S.open_meeting(b)
        b.eval("window.__calls=[]; const f=window.fetch; window.fetch=function(u,o){ window.__calls.push(String(u)); return f.apply(this,arguments); }")
        b.eval("document.querySelector('[data-irg=routine] [data-ira=routine]').click()")
        b.wait("document.querySelector('#snackT') && /Approved 4/.test(document.getElementById('snackT').textContent)", 25)
        b.wait("document.querySelectorAll('#v-intake-review tr.irprop.mchild').length===4", 25)
        made = [r["description"] for r in self.v.rows("actions") if r["description"].startswith("Steering action")]
        self.assertEqual(len(made), 4)
        self.assertEqual(b.eval("window.__calls.filter(u=>/\\/api\\/apply/.test(u)).length"), 1)
        self.assertEqual(b.eval("irOpen.value"), mid)                                     # an apply keeps the meeting open
        self.assertFalse(any(r["description"].startswith("Scope creep") for r in self.v.rows("raid")))   # the first group is untouched
        b.click("#snackU")
        b.wait("document.querySelectorAll('#v-intake-review tr.irprop.mchild').length===8", 25)
        self.assertEqual(len([r for r in self.v.rows("actions") if r["description"].startswith("Steering action")]), 0)
        self.assertEqual(b.eval("window.__calls.filter(u=>/\\/api\\/undo/.test(u)).length"), 1)


if __name__ == "__main__":
    unittest.main()
