"""#275: approving minutes FROM REVIEW applies the Track column exactly as the Minutes view v2's Approve minutes does.

In the fictional steering committee of test_minutes_editor (three actions, a decision and a risk) the first action is ticked
(its default), the second crossed and the third cleared to neither, in the minutes view; then the minutes are approved from
Review, by the minutes' own Approve and by Approve n routine ("Approve all from these minutes"). Either way the ticked action is
registered, the crossed one is gone from the minutes (rejected) and the one left with neither stays in the minutes untracked;
the decision and the risk (neither, their default) stay in the minutes only. Undo of the single Approve puts the apply back and
the minutes exactly as they were before (as the view's Undo does). Both paths call stores/minutes.trackApprove, the view's code.
A promise has no row in the minutes, so no Track control: approved from Review it is never registered and waits in Review (Cap's
#268 review H1, track.approveArgs).

Cap's #275 review: the bulk paths (Approve routine, the bar's Approve, the group tick) never register a crossed or neither row
(Review's rows carry `trk`); `review.py approve` on the minutes and on an item, and `review.py bulk`, honour the Track column on the
server (ServerTrack, quick); under one project of minutes covering several, Approve registers only that project's ticked items; Undo
of Approve n routine puts the crosses back too.

Run: python3 dev/tests/test_minutes_track_review.py      (Chrome tier; skipped without Chrome)
"""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
import test_minutes_view_v2 as mv  # noqa: E402
import test_minutes_approve as ma  # noqa: E402

ROW = mv.ROW
DIFF_APPLIED = "def track_problems" in (Path(__file__).resolve().parents[2] / "system/scripts/tracker.py").read_text(encoding="utf-8")
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


    def test_04_the_bulk_paths_never_register_a_crossed_or_neither_row(self):
        b = self.b
        trk = self.ev("Object.fromEntries(REV.filter(r=>r.trk!=null).map(r=>[r.ref,r.trk]))")
        self.assertEqual(trk, {"2": "n", "3": ""}, "Review's rows carry the Track choices")
        self.assertEqual(self.ev("REV.filter(r=>r.trk!=null).map(rvBulkOK)"), [False, False], "never approved in bulk")
        self.ev("[...document.querySelectorAll('#reviewBody tr[data-n]')].forEach(tr=>{ const r=REV.find(x=>x.n===+tr.dataset.n); if(r&&!isMin(r)) RHL.add(r.n); }); rvSyncChk(); renderReview();")
        self.ev("rvApproveSelected(true)")                      # the bar's Approve on every row, the crossed and neither ones included
        for _ in range(120):
            if SOW in self.descs():
                break
            b.pump(0.25)
        self.assertIn(SOW, self.descs())
        self.assertNotIn(UAT, self.descs(), "crossed: never registered by the bar's Approve")
        self.assertNotIn(CUT, self.descs(), "neither: never registered by the bar's Approve")
        self.assertEqual((self.staged(2)["decision"], self.staged(3)["decision"]), ("pending", "pending"))
        self.ev("rvRoutine()")                                   # Approve routine: nothing of theirs is offered
        b.pump(0.4)
        self.assertNotIn(UAT, self.ev("document.getElementById('rvDlg').open ? document.getElementById('rvDlgBody').textContent : ''"))
        self.assertNotIn(UAT, self.descs())

    def test_05_undo_of_approve_n_routine_puts_the_crosses_back_too(self):
        b = self.b
        b.eval(MIN + ".querySelector('[data-act=ga]').click()")
        b.wait("document.getElementById('snack').classList.contains('on') && /from these minutes/.test(document.getElementById('snack').textContent)", 30)
        self.assertIn("4 lines taken out of the minutes or kept as lines only", self.snack())   # the cross, the neither, and the decision and risk at their default
        for _ in range(60):
            if SOW in self.descs():
                break
            b.pump(0.25)
        self.assertEqual(self.staged(2)["decision"], "rejected")
        b.click("#snackU")
        for _ in range(120):
            if SOW not in self.descs() and self.staged(2)["decision"] == "pending" and \
                    self.rows_text(self.record()) == self.rows_text(self.before):
                break
            b.pump(0.25)
        self.assertNotIn(SOW, self.descs())
        self.assertEqual([self.staged(n)["decision"] for n in (1, 2, 3, 4, 5)], ["pending"] * 5, "the approval and the crosses undone")
        self.assertEqual(self.rows_text(self.record()), self.rows_text(self.before), "the minutes' rows exactly as before")

    def test_06_a_bulk_approval_straight_after_leaving_the_minutes_waits_for_the_track_choices(self):
        """Cap's re-review (2): leaving the Minutes view reloads the data without waiting, so Review first draws the old rows; the
        bar's Approve made at once (on a row crossed a moment ago, still shown as routine) waits for the reload and leaves it out."""
        b = self.b
        self.open()
        b.click(ROW % 1 + " .mntrk button.n")                   # SOW crossed now
        for _ in range(60):
            if (self.record().get("layout") or {}).get("track", {}).get("1") == "n":
                break
            b.pump(0.25)
        self.assertEqual(self.record()["layout"]["track"].get("1"), "n")
        stale = self.ev("(()=>{ go('review'); const r=REV.find(x=>x.rec&&x.rec.t===" + json.dumps(SOW) + "); window.__t6=null;"
                        " RHL.clear(); RHL.add(r.n); rvSyncChk(); const t=r.trk; rvApproveSelected(true).then(()=>{ window.__t6='done'; });"
                        " return t===undefined?null:t; })()")
        self.assertIsNone(stale, "the row as Review first drew it: not yet marked crossed (the race)")
        for _ in range(120):
            if self.ev("window.__t6") == "done":
                break
            b.pump(0.25)
        self.assertEqual(self.ev("window.__t6"), "done")
        b.pump(1.5)
        self.assertNotIn(SOW, self.descs(), "crossed a moment ago: never registered")
        self.assertEqual(self.staged(1)["decision"], "pending")


class TwoProjects(LiveBrowserCase):
    """Cap's #275 M-b: minutes covering ABC and DEF; Approve under ABC registers ABC's ticked items only, DEF's wait in Review."""
    @classmethod
    def load(cls, v):
        mv.MinutesViewV2.load.__func__(cls, v)
        p = v.root / "system/staging" / cls.proposal
        data = json.loads(p.read_text(encoding="utf-8"))
        data["meeting"]["projects"] = ["ABC", "DEF"]
        data["items"][1]["values"]["project"] = "DEF"              # "Book the UAT test environment" is DEF's
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    open, ev, staged, snack, rows_of, record = (mv.MinutesViewV2.open, mv.MinutesViewV2.ev, mv.MinutesViewV2.staged,
                                                mv.MinutesViewV2.snack, mv.MinutesViewV2.rows_of, mv.MinutesViewV2.record)

    def test_approve_under_one_project_registers_only_its_ticked_items(self):
        b = self.b
        self.open()
        b.click(ROW % 3 + " .mntrk button.y")                   # Pat Unknown's action: neither, so nothing is worth a look
        for _ in range(60):
            if (self.record().get("layout") or {}).get("track") == {"3": ""}:
                break
            b.pump(0.25)
        b.eval("go('review')")
        b.wait("document.querySelector('#reviewBody tr.mparent[data-g=\"ABC\"] [data-act=a]')", 15)
        b.pump(0.3)
        tip = self.ev("document.querySelector('#reviewBody tr.mparent[data-g=\"ABC\"] [data-act=a]').dataset.tip")
        self.assertIn("registers the items ticked in their Track column (this project's)", tip)
        b.eval("document.querySelector('#reviewBody tr.mparent[data-g=\"ABC\"] [data-act=a]').click()")
        b.wait("document.getElementById('snack').classList.contains('on') && /Minutes approved/.test(document.getElementById('snack').textContent)", 30)
        descs = [a["description"] for a in self.rows_of("actions")]
        self.assertIn(SOW, descs, "ABC's ticked action")
        self.assertNotIn(UAT, descs, "DEF's ticked action waits in Review")
        self.assertEqual(self.staged(2)["decision"], "pending")


class ServerTrack(ma.Base):
    """Cap's #275 M-a and H1 on the server: review.py and approve_minutes honour the Track column whatever the caller sends."""
    def track(self, choices):
        self.js("import minutes_record, creaite_doc\n"
                f"d = creaite_doc.read({ma.DRAFT!r})\nd['layout'] = {{**(d.get('layout') or {{}}), 'track': {choices!r}}}\n"
                f"r = minutes_record.save_page({ma.DRAFT!r}, d)\nprint(json.dumps({{'ok': bool(r.get('ok'))}}))")

    def number(self, ref):
        rows = json.loads(self.v.run("list", "--json", script="review.py").stdout)
        return next(r["n"] for r in rows if r["file"] == self.name and r["ref"] == ref)

    def item(self, n):
        return next(i for i in self.data()["items"] if i["n"] == n)

    def test_review_py_approve_on_the_minutes_honours_the_crosses(self):
        self.track({"2": "n", "3": ""})
        out = self.v.run("approve", str(self.number("meeting")), script="review.py").stdout
        self.assertIn("Minutes approved", out)
        self.v.run("apply")
        self.assertIn("Book the UAT environment", [a["description"] for a in self.v.rows("actions")], "ticked: registered")
        self.assertNotIn("Test data isn't anonymised", [r["description"] for r in self.v.rows("raid")], "crossed: never registered")
        self.assertEqual(self.by_id("actions")["ABC-A-001"]["due_date"], "2026-10-20", "neither: the update isn't applied")
        text = (self.v.root / ma.FILED).read_text(encoding="utf-8")
        self.assertNotIn("Test data isn't anonymised", text, "the crossed line left the minutes")
        self.assertEqual(self.item(4)["decision"], "pending", "a decision at its default waits in Review, as before")

    def test_review_py_approve_and_bulk_refuse_an_item_crossed_or_left_with_neither(self):
        self.track({"1": "n", "2": ""})
        out = self.v.run("approve", str(self.number(1)), script="review.py").stdout
        self.assertIn("crossed in the minutes' Track column", out)
        out = self.v.run("approve", str(self.number(2)), script="review.py").stdout
        self.assertIn("kept in the minutes only", out)
        out = self.v.run("bulk", script="review.py").stdout
        self.assertIn("not ticked in the minutes", out)
        self.assertEqual((self.item(1)["decision"], self.item(2)["decision"], self.item(3)["decision"]), ("pending", "pending", "approved"))

    def test_approve_minutes_never_registers_a_crossed_item_whatever_it_is_sent(self):
        self.track({"1": "n", "4": ""})                       # no changes made on the page: the server makes them
        r = self.approve(group=True, own=[1, 4])
        self.assertTrue(r["ok"], r)
        self.assertNotIn("Book the UAT environment", [a["description"] for a in self.v.rows("actions")])
        self.assertNotIn("Go-live stays on 20 November", [d["decision"] for d in self.v.rows("decisions")])
        self.assertIn("Test data isn't anonymised", [x["description"] for x in self.v.rows("raid")], "the ticked issue is registered")
        text = (self.v.root / ma.FILED).read_text(encoding="utf-8")
        self.assertNotIn("Book the UAT environment", text, "crossed: the line goes")
        self.assertIn("Go-live stays on 20 November", text, "neither: the line stays")

    def test_review_py_approve_on_the_minutes_says_what_it_did_to_the_lines(self):
        self.track({"2": "n", "3": ""})
        out = self.v.run("approve", str(self.number("meeting")), script="review.py").stdout
        self.assertIn("1 crossed line taken out of the minutes, 1 line kept in the minutes untracked", out)

    def test_review_py_approve_with_no_track_choices_says_the_default_rows_are_registered(self):
        out = self.v.run("approve", str(self.number("meeting")), script="review.py").stdout
        self.assertIn("no Track choices made in the minutes, so the rows ticked by default are registered", out)

    def check(self):
        """minutes_record.track_apply_problems on the staged proposal: (problems, the items' decisions after)."""
        return self.js("import minutes_record\n"
                       f"p = 'system/staging/{self.name}'\ndata = json.load(open(p, encoding='utf-8'))\n"
                       f"out = minutes_record.track_apply_problems({self.name!r}, data)\n"
                       "print(json.dumps([out, {str(i['n']): i['decision'] for i in data['items']}]))")

    def set_decision(self, n, decision):
        p = self.v.root / "system/staging" / self.name
        data = json.loads(p.read_text(encoding="utf-8"))
        next(i for i in data["items"] if i["n"] == n)["decision"] = decision
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def test_the_apply_check_stops_only_an_approved_crossed_item_and_puts_it_back_in_review(self):
        self.track({"1": "n", "2": ""})
        self.set_decision(3, "approved")
        out, dec = self.check()
        self.assertEqual(out, [], "a pending crossed or neither item never stops the apply")
        self.set_decision(1, "approved")
        out, dec = self.check()
        self.assertEqual(len(out), 1, out)
        self.assertIn("item 1: crossed in the minutes' Track column", out[0])
        self.assertIn("approve the minutes in the Minutes view (it clears crossed lines)", out[0])
        self.assertEqual((dec["1"], dec["3"]), ("pending", "approved"), "back in Review's queue; the other item untouched")

    def test_the_apply_check_fails_closed_when_the_record_cant_be_read(self):
        f = self.v.root / ma.DRAFT
        f.write_text(re.sub(r'(<script type="application/json" id="creaite-data">).*?(</script>)', r"\1{broken\2",
                            f.read_text(encoding="utf-8"), flags=re.S), encoding="utf-8")
        self.assertEqual(self.check()[0], [], "nothing approved: nothing to stop")
        self.set_decision(3, "approved")
        out = self.check()[0]
        self.assertEqual(len(out), 1, out)
        self.assertIn("the minutes record can't be read", out[0])

    @unittest.skipUnless(DIFF_APPLIED, "dev/proposals/track-from-review/tracker-track-problems.diff not applied yet")
    def test_apply_refuses_a_crossed_item_approved_by_hand(self):
        self.track({"1": "n"})
        self.set_decision(1, "approved")
        r = self.v.run("apply", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("crossed in the minutes' Track column", r.stdout + r.stderr)
        self.assertIn("approve the minutes in the Minutes view (it clears crossed lines)", r.stdout + r.stderr)
        self.assertNotIn("Book the UAT environment", [a["description"] for a in self.v.rows("actions")])
        self.assertEqual(self.item(1)["decision"], "pending", "not stuck: back in Review's queue")
        out = self.v.run("reject", str(self.number(1)), script="review.py").stdout
        self.assertIn("rejected", out.lower())
        self.assertEqual(self.item(1)["decision"], "rejected", "and Review can reject it")

    @unittest.skipUnless(DIFF_APPLIED, "dev/proposals/track-from-review/tracker-track-problems.diff not applied yet")
    def test_a_pending_crossed_item_never_stops_the_apply_of_another(self):
        self.track({"1": "n"})                                 # crossed, still pending: the normal state before Approve minutes
        self.set_decision(3, "approved")                       # the update of ABC-A-001's due date
        r = self.v.run("apply", ok=False)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("Apply stopped", r.stdout)
        self.assertEqual(self.by_id("actions")["ABC-A-001"]["due_date"], "2026-10-30", "the approved item is written")
        self.assertEqual(self.item(1)["decision"], "pending")
        self.assertNotIn("Book the UAT environment", [a["description"] for a in self.v.rows("actions")])


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
