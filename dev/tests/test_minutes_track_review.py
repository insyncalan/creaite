"""#275: approving minutes FROM REVIEW applies the Track column exactly as the Minutes view v2's Approve minutes does.

In the fictional steering committee of test_minutes_editor (three actions, a decision and a risk) the first action is ticked
(its default), the second crossed and the third cleared to neither, in the minutes view; then the minutes are approved from
Review, by the minutes' own Approve and by Approve n routine ("Approve all from these minutes"). Either way the ticked action is
registered, the crossed one is gone from the minutes (rejected) and the one left with neither stays in the minutes untracked;
the decision and the risk (neither, their default) stay in the minutes only. Undo of the single Approve puts the apply back and
the minutes exactly as they were before (as the view's Undo does). Both paths call stores/minutes.trackApprove, the view's code.
A promise has no row in the minutes, so no Track control: approved from Review it is never registered and waits in Review (Cap's
#268 review H1, track.approveArgs).

Run: python3 dev/tests/test_minutes_track_review.py      (Chrome tier; skipped without Chrome)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
import test_minutes_view_v2 as mv  # noqa: E402

ROW = mv.ROW
SOW, UAT, CUT = "Send the revised SOW to the client", "Book the UAT test environment", "Share the cut-over plan with the client"
MIN = "document.querySelector('#reviewBody tr.mparent')"


class TrackFromReview(LiveBrowserCase):
    load = classmethod(mv.MinutesViewV2.load.__func__)
    open, ev, staged, record, trk, snack, filed, rows_of = (mv.MinutesViewV2.open, mv.MinutesViewV2.ev, mv.MinutesViewV2.staged,
                                                             mv.MinutesViewV2.record, mv.MinutesViewV2.trk, mv.MinutesViewV2.snack,
                                                             mv.MinutesViewV2.filed, mv.MinutesViewV2.rows_of)

    def setUp(self):
        super().setUp()
        self.open()
        b = self.b
        b.click(ROW % 2 + " .mntrk button.n")                   # cross: out of the minutes
        b.pump(0.2)
        b.click(ROW % 3 + " .mntrk button.y")                   # the pressed tick again: neither, kept untracked
        b.pump(0.2)
        self.assertEqual(self.trk(), {"1": "y", "2": "n", "3": "", "4": "", "5": ""})
        for _ in range(60):                                     # the choices are saved with the page (layout.track)
            if (self.record().get("layout") or {}).get("track") == {"2": "n", "3": ""}:
                break
            b.pump(0.25)
        self.assertEqual(self.record()["layout"]["track"], {"2": "n", "3": ""}, "the Track choices saved with the minutes")
        self.before = self.record()
        b.eval("go('review')")
        b.wait(MIN + " && " + MIN + ".querySelector('[data-act=a]')", 15)
        b.pump(0.3)

    def descs(self):
        return [a["description"] for a in self.rows_of("actions")]

    def assert_track_applied(self):
        descs = self.descs()
        self.assertIn(SOW, descs, "ticked: a work item registered")
        self.assertNotIn(UAT, descs, "crossed: no work item")
        self.assertNotIn(CUT, descs, "neither: no work item")
        self.assertEqual(self.staged(2)["decision"], "rejected")
        self.assertEqual(self.staged(3)["reject_reason"], "Removed in the minutes")
        self.assertNotIn("The pilot stays on the lighthouse site", [x["decision"] for x in self.rows_of("decisions")])
        self.assertNotIn("Data access late → the MVP slips", [x["description"] for x in self.rows_of("raid")])

    def rows_text(self, doc):
        return json.dumps([s.get("rows") for s in doc["sections"] if s.get("id") in ("actions", "decisions", "raid")])

    def test_01_approve_from_review_applies_the_track_column_and_undo_puts_the_minutes_back(self):
        b = self.b
        b.eval(MIN + ".querySelector('[data-act=a]').click()")
        b.wait("document.getElementById('snack').classList.contains('on') && /Minutes approved/.test(document.getElementById('snack').textContent)", 30)
        self.assertIn("Minutes approved · 1 work item registered", self.snack())
        self.assertNotIn("wait in Review", self.snack())
        self.assert_track_applied()
        filed = self.filed()
        self.assertIsNotNone(filed, "the minutes are filed")
        text = filed.read_text(encoding="utf-8")
        self.assertNotIn(UAT, text, "the crossed line left the minutes")
        self.assertIn(CUT, text, "neither: the line stays in the minutes")
        self.assertIn("lighthouse site", text, "the decision stays in the minutes")
        self.assertTrue(self.ev("getComputedStyle(document.getElementById('snackU')).display!=='none'"), "with Undo")
        b.click("#snackU")                                      # Undo: the apply back, and the minutes exactly as they were
        for _ in range(120):
            if SOW not in self.descs() and self.staged(2)["decision"] == "pending" and \
                    self.rows_text(self.record()) == self.rows_text(self.before):
                break
            b.pump(0.25)
        self.assertNotIn(SOW, self.descs())
        self.assertEqual([self.staged(n)["decision"] for n in (1, 2, 3, 4, 5)], ["pending"] * 5, "every item pending again")
        after = self.record()
        self.assertEqual(self.rows_text(after), self.rows_text(self.before), "the minutes' rows exactly as before Approve")
        self.assertEqual((after.get("meta") or {}).get("removed") or {}, (self.before.get("meta") or {}).get("removed") or {})
        self.assertEqual(after["layout"]["track"], {"2": "n", "3": ""}, "the Track choices kept")

    def test_02_approve_all_from_these_minutes_applies_the_track_column_too(self):
        b = self.b
        b.eval(MIN + ".querySelector('[data-act=ga]').click()")
        for _ in range(120):
            if SOW in self.descs():
                break
            b.pump(0.25)
        self.assert_track_applied()
        doc = self.record()
        self.assertEqual(doc["state"], "draft", "the bulk rule: the minutes still wait for their own Approve")
        rows = self.rows_text(doc)
        self.assertNotIn(UAT, rows, "the crossed line left the minutes")
        self.assertIn(CUT, rows, "neither: the line stays in the minutes")
        self.assertIn("lighthouse site", rows)

    def test_03_a_ticked_item_worth_a_look_opens_the_minutes_with_the_before_approving_box(self):
        b = self.b
        self.open()
        b.click(ROW % 3 + " .mntrk button.y")                   # Pat Unknown's action ticked again: he needs details
        b.pump(0.2)
        for _ in range(60):
            if (self.record().get("layout") or {}).get("track", {}).get("3") == "y":
                break
            b.pump(0.25)
        b.eval("go('review')")
        b.wait(MIN + " && " + MIN + ".querySelector('[data-act=a]')", 15)
        b.eval(MIN + ".querySelector('[data-act=a]').click()")
        b.wait("location.hash.startsWith('#minutes') && document.getElementById('mnApprove') && document.getElementById('mnApprove').open", 20)
        lis = self.ev("[...document.querySelectorAll('#mnApprove li')].map(l=>l.textContent)")
        self.assertIn("Pat Unknown needs details" + CUT, lis, "the view's box, with the ticked item worth a look")
        self.assertFalse([x for x in lis if "Possible duplicate" in x], "the crossed item isn't listed")
        self.assertEqual(self.staged(1)["decision"], "pending", "nothing approved yet")
        b.click("#mnApproveGo")
        b.wait("document.getElementById('snack').classList.contains('on') && /Minutes approved/.test(document.getElementById('snack').textContent)", 30)
        self.assertIn("Minutes approved · 2 work items registered", self.snack())
        self.assertIn(CUT, self.descs())
        self.assertNotIn(UAT, self.descs())


class RowlessPromiseFromReview(LiveBrowserCase):
    """Cap's #268 review H1 from Review: the minutes' Approve registers the ticked action, never the promise with no row."""
    @classmethod
    def load(cls, v):
        populate(v)
        f = v.root / "system/staging/drafts/promise.json"
        f.write_text(json.dumps({"title": "[ABC] Promise check-in", "date": "2026-10-14", "projects": ["ABC"],
                                 "minutes": {"start": "12:00", "end": "12:30", "summary": ["A short check-in."], "chat": False},
                                 "items": [{"table": "actions", "values": {"project": "ABC", "description": "Draft the cutover runbook",
                                                                           "owner": "Jane Doe"}},
                                           {"table": "promises", "section": "Jane Doe, 12:05", "values": {
                                               "project": "ABC", "promised_by": "Jane Doe", "promised_to": "Alan Carter",
                                               "description": "Send the vendor's rate card", "due_date": "2026-10-20"}}]}),
                     encoding="utf-8")
        before = {p.name for p in (v.root / "system/staging").glob("proposed-*.json")}
        v.run("stage", str(f), script="minutes.py")
        cls.proposal = next(p.name for p in (v.root / "system/staging").glob("proposed-*.json") if p.name not in before)

    ev, staged, snack, rows_of = mv.MinutesViewV2.ev, mv.MinutesViewV2.staged, mv.MinutesViewV2.snack, mv.MinutesViewV2.rows_of

    def test_the_ticked_row_registers_and_the_promise_waits_in_review(self):
        b = self.b
        b.eval("go('review')")
        b.wait(MIN + " && " + MIN + ".querySelector('[data-act=a]')", 15)
        b.pump(0.3)
        b.eval(MIN + ".querySelector('[data-act=a]').click()")
        b.wait("document.getElementById('snack').classList.contains('on') && /Minutes approved/.test(document.getElementById('snack').textContent)", 30)
        self.assertIn("Minutes approved · 1 work item registered · 1 wait in Review", self.snack())
        self.assertIn("Draft the cutover runbook", [a["description"] for a in self.rows_of("actions")])
        self.assertNotIn("Send the vendor's rate card", [x["description"] for x in self.rows_of("promises")],
                         "a promise nobody saw is never registered")
        self.assertEqual(self.staged(2)["decision"], "pending", "the promise waits in Review")


if __name__ == "__main__":
    unittest.main()
