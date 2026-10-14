"""BL-189 (sprint-milestones): other applies leave the peek's staged changes alone. A cell edit, a bulk change and a Review
approval with auto-apply on apply their own proposals; what the peek staged waits for its own Apply (or ⌘↵).

Run: python3 dev/tests/test_hold_peek.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import time
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_tracker import action  # noqa: E402


class HoldPeek(LiveBrowserCase):
    def setUp(self):
        super().setUp()
        b = self.b
        b.eval("S.autoApply=true; WT='actions'; go('work')")
        b.wait("document.querySelector('#workTbl tbody tr[data-row]')")
        self.ids = b.eval("A.filter(x=>x.st==='Open').map(x=>x.id)")
        self.assertGreaterEqual(len(self.ids), 3)
        self.peek_id = self.ids[0]
        b.eval(f"openRecord('actions',{self.peek_id!r})")
        b.wait(f"CUR&&CUR.id==={self.peek_id!r}")
        b.eval(f"pkCommit('actions',{self.peek_id!r},{{t:'Staged in the peek'}},'Title',curObj().t,'Staged in the peek')")
        b.wait("PKS.length===1", timeout=15)
        b.eval("closePanel()")
        self.before = self.desc(self.peek_id)

    def desc(self, id_):
        return next(r for r in self.v.rows("actions") if r["id"] == id_)["description"]

    def field(self, id_, f):
        return next(r for r in self.v.rows("actions") if r["id"] == id_)[f]

    def peek_files(self):
        out = []
        for p in sorted((self.v.root / "system/staging").glob("proposed-*dashboard*.json")):
            if json.loads(p.read_text()).get("peek"):
                out.append(p)
        return out

    def still_staged(self):
        b = self.b
        self.assertEqual(len(self.peek_files()), 1)
        self.assertEqual(self.desc(self.peek_id), self.before)
        b.wait("PKS.length===1&&!document.getElementById('pkStage').hidden", timeout=15)
        self.assertEqual(b.eval("document.getElementById('pkStN').textContent"), "1 change staged on 1 item")

    def then_the_peek_applies(self):
        b = self.b
        b.eval("pkApply()")
        b.wait("PKS.length===0", timeout=20)
        self.assertEqual(self.desc(self.peek_id), "Staged in the peek")
        self.assertEqual(self.peek_files(), [])

    def test_a_cell_edit_applies_only_its_own_change(self):
        b = self.b
        other = self.ids[1]
        self.assertTrue(b.eval(f"ceApply('actions',[{other!r}],{{pr:'Low'}})"))   # BL-304: on screen at once, applied in the background
        self.assertTrue(b.eval("(async()=>{ await savesSettled(); return true; })()"))
        self.assertEqual(self.field(other, "priority"), "Low")
        self.still_staged()
        self.then_the_peek_applies()
        self.assertEqual(b.errors, [])

    def test_a_bulk_change_applies_only_its_own_changes(self):
        b = self.b
        two = self.ids[1:3]
        b.eval(f"batchMove('actions',{two!r},{{pr:'Low'}},'Priority set to Low')")
        deadline = time.time() + 20
        while time.time() < deadline and any(self.field(i, "priority") != "Low" for i in two):
            b.pump(0.2)
        self.assertEqual([self.field(i, "priority") for i in two], ["Low", "Low"])
        self.still_staged()
        self.then_the_peek_applies()

    def test_a_review_approval_with_auto_apply_leaves_the_peek_alone(self):
        b = self.b
        self.v.propose("review-one", [dict(action(1, description="Approved in Review"), decision="pending")])
        b.eval("reloadData()")
        b.wait("REV.some(r=>r.rec&&r.rec.t==='Approved in Review')", timeout=15)
        n = b.eval("REV.find(r=>r.rec&&r.rec.t==='Approved in Review').n")
        b.eval(f"decide({n},'approved')")
        deadline = time.time() + 20
        while time.time() < deadline and not any(r["description"] == "Approved in Review" for r in self.v.rows("actions")):
            b.pump(0.2)
        self.assertTrue(any(r["description"] == "Approved in Review" for r in self.v.rows("actions")))
        self.still_staged()
        self.then_the_peek_applies()

    def test_the_route_holds_the_peek_only_when_asked(self):
        tok = self.b.eval("D.token")
        def post(body):
            req = urllib.request.Request(self.base + "/api/apply", data=json.dumps(body).encode(), method="POST",
                                         headers={"Content-Type": "application/json", "X-Creaite-Token": tok})
            return json.loads(urllib.request.urlopen(req, timeout=60).read())
        r = post({"hold_peek": True})                       # only the peek's change is staged: nothing to apply
        self.assertTrue(r["ok"])
        self.assertIn("Nothing to apply", r["message"])
        self.assertEqual(r["held"], 1)
        self.assertEqual(len(self.peek_files()), 1)
        r = post({})                                        # the peek's own Apply: everything decided
        self.assertTrue(r["ok"])
        self.assertEqual(self.desc(self.peek_id), "Staged in the peek")


if __name__ == "__main__":
    unittest.main()
