"""#268 Minutes view v2: the Track column's states map onto the record's existing changes, with no server change.

Run: python3 dev/tests/test_minutes_track_ops.py      (quick tier: no Chrome)
What the view does on Approve minutes (components/minutes/track.js reconcileOps), done here through the real
minutes_record.change and review.approve_minutes on test_minutes_approve's staged meeting:
- neither = `remove` with keep_line (the line stays in the filed minutes, no item); cross = `remove` (the line goes); a tick
  on a kept line = `restore`; a cross on a kept line = `restore` then `remove`;
- nothing ticked (#261, "take no items"): every item rejected, and the minutes are still filed with no work items;
- a mix: only the ticked items are written, in one apply;
- track.js itself (TrackJs, with Node): its defaults (the plan's "own" group, updates among them, start with neither; new
  actions and issues ticked), what its reconcileOps sends through the real minutes_record.change, and that neither on an
  update approved one by one leaves it in Review instead of rejecting it (review H2);
- Approve, Undo, Approve again (#268's bug): Undo leaves the minutes exactly as they were before Approve (the rows the approve
  took out or kept as lines come back as item rows, with their items pending and no "Removed in the minutes"), so the second
  Approve gives the same result as the first: nothing leaks to Review.
"""
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_minutes_approve import ABC, FILED, Base  # noqa: E402


class TrackOps(Base):
    def test_nothing_ticked_files_the_minutes_with_no_items(self):
        for n in range(1, 8):
            self.assertTrue(self.change({"op": "remove", "n": n, "keep_line": n % 2 == 0})["ok"])
        r = self.approve(group=True, own=[])
        self.assertTrue(r["ok"], r)
        self.assertEqual((r["approved"], r["waiting"]), (0, []))
        self.assertIn("filed 1", r["message"])
        self.assertIn("rejected 7", r["message"])
        self.assertTrue((self.v.root / FILED).exists())
        filed = self.doc(FILED)
        self.assertEqual(filed["state"], "approved")
        kept = [x for s in filed["sections"] for x in s.get("rows") or [] if x.get("kept_line")]
        self.assertEqual(len(kept), 3, "neither: three lines stay in the minutes, with no item")
        self.assertNotIn("Book the UAT environment", [a["description"] for a in self.v.rows("actions")])

    def test_a_mix_writes_only_the_ticked_items_and_kept_lines_come_back_by_restore(self):
        self.assertTrue(self.change({"op": "remove", "n": 2, "keep_line": True})["ok"])     # neither
        self.assertTrue(self.change({"op": "remove", "n": 5, "keep_line": True})["ok"])     # neither, then ticked again
        self.assertTrue(self.change({"op": "restore", "n": 5})["ok"])                       # tick on a kept line
        self.assertTrue(self.change({"op": "remove", "n": 4, "keep_line": True})["ok"])     # neither, then crossed
        self.assertTrue(self.change({"op": "restore", "n": 4})["ok"])
        self.assertTrue(self.change({"op": "remove", "n": 4})["ok"])                        # cross on a kept line
        r = self.approve(group=True, own=[5, 6, 7])
        self.assertTrue(r["ok"], r)
        raid = [x["description"] for x in self.v.rows("raid")]
        self.assertIn("Vendor capacity is short → the cutover slips", raid, "the restored risk is written")
        self.assertNotIn("Test data isn't anonymised", raid, "neither: no item")
        self.assertNotIn("Go-live stays on 20 November", [d["decision"] for d in self.v.rows("decisions")], "crossed: no item")
        text = (self.v.root / FILED).read_text(encoding="utf-8")
        self.assertIn("Test data isn't anonymised", text, "neither: the line stays")
        self.assertNotIn("Go-live stays on 20 November", text, "crossed: the line goes")
        self.assertTrue(str(FILED).startswith(ABC))


    def view(self):
        return self.js("import minutes_record\n"
                       f"r = minutes_record.view(file={self.name!r})\nprint(json.dumps({{'settle': r.get('settle'), 'doc': r['doc']}}))")

    def approve_as_the_view_does(self):
        """Neither on the decision (4) and the risk (5), a cross on the issue (2), the rest ticked; the own ticks 6 and 7."""
        for op in ({"op": "remove", "n": 2}, {"op": "remove", "n": 4, "keep_line": True}, {"op": "remove", "n": 5, "keep_line": True}):
            self.assertTrue(self.change(op)["ok"], op)
        return self.approve(group=True, own=[6, 7])

    def test_approve_undo_approve_again_gives_the_same_result(self):
        before = self.doc()
        first = self.approve_as_the_view_does()
        self.assertTrue(first["ok"], first)
        self.assertIn("Undid apply", self.v.run("undo").stdout)
        seen = self.view()
        self.assertEqual(seen["settle"], [5, 4, 2], "the view says which rows to put back, newest first")
        r = self.change({"op": "settle"})
        self.assertTrue(r["ok"], r)
        self.assertIn("Put back 3 lines", r["message"])
        after = self.doc()
        for sid in ("decisions", "raid", "actions"):
            self.assertEqual(self.rows(after, sid), self.rows(before, sid), f"{sid}: every row as it was before Approve")
        self.assertFalse(after["meta"].get("removed"), "nothing left taken out")
        for i in self.data()["items"]:
            self.assertEqual(i["decision"], "pending", i["n"])
            self.assertNotIn("reject_reason", i, i["n"])
        self.assertEqual(self.view()["settle"], [], "settled")
        again = self.change({"op": "settle"})
        self.assertEqual((again["ok"], again["message"]), (False, "Nothing to put back."), "nothing to settle: no new version")
        second = self.approve_as_the_view_does()
        self.assertTrue(second["ok"], second)
        self.assertEqual((second["approved"], second["waiting"]), (first["approved"], first["waiting"]), "the same result both times")
        self.assertEqual(second["waiting"], [], "nothing waits in Review")
        text = (self.v.root / FILED).read_text(encoding="utf-8")
        self.assertIn("Go-live stays on 20 November", text, "neither: the line stays")
        self.assertNotIn("Test data isn't anonymised", text, "crossed: the line goes")
        self.assertNotIn("Test data isn't anonymised", [x["description"] for x in self.v.rows("raid")], "crossed: never registered (review H1)")
        self.assertNotIn("Go-live stays on 20 November", [d["decision"] for d in self.v.rows("decisions")], "neither: no item")

    def test_any_change_after_an_undo_settles_the_record_first(self):
        self.assertTrue(self.approve_as_the_view_does()["ok"])
        self.v.run("undo")
        self.assertTrue(self.change({"op": "edit", "n": 1, "values": {"owner": "Jane Doe"}})["ok"])
        self.assertEqual(self.view()["settle"], [])
        self.assertTrue(any(x.get("ref") == "@4" for x in self.rows(self.doc(), "decisions")), "the decision is an item row again")



TRACK_JS = (Path(__file__).resolve().parents[2] / "system/templates/dashboard/src/components/minutes/track.js").as_uri()


class RunsTrackJs:
    """components/minutes/track.js run for real (Node) on the record and plan the view gets."""
    def view(self):
        return self.js("import minutes_record\n"
                       f"r = minutes_record.view(file={self.name!r})\nprint(json.dumps({{'doc': r['doc'], 'plan': r['plan']['items']}}))")

    def track(self, expr, choices=None):
        v = self.view()
        script = (f"import * as T from {json.dumps(TRACK_JS)};\n"
                  f"let doc = {json.dumps(v['doc'])}; const plan = {json.dumps(v['plan'])};\n"
                  f"for (const [n, t] of Object.entries({json.dumps(choices or {})})) doc = T.setTrack(doc, Number(n), t);\n"
                  f"console.log(JSON.stringify({expr}));")
        r = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def states(self, choices=None):
        return {str(k): t for k, t in self.track("Object.fromEntries(T.trackRows(doc).map(r => [r.n, T.trackOf(doc, r, plan)]))", choices).items()}


@unittest.skipUnless(shutil.which("node"), "needs Node")
class TrackJs(RunsTrackJs, Base):
    """track.js on test_minutes_approve's meeting, its ops sent to the server."""
    def test_the_defaults_follow_the_plan(self):
        self.assertEqual(self.states(), {"1": "y", "2": "y", "3": "y", "4": "", "5": "", "6": "", "7": ""},
                         "a new action, a new issue and an update in the group ticked; a new decision, a new risk, a closure and a "
                         "decision recorded (each approved one by one) neither")
        self.assertEqual(self.track("T.defaultTrack('raid', {op: 'new', values: {type: 'Issue'}})"), "y", "a new issue starts ticked")
        self.assertEqual(self.track("T.defaultTrack('raid', {op: 'new', values: {type: 'Risk'}})"), "")
        self.assertEqual(self.track("T.defaultTrack('actions', {op: 'update'}, 'own')"), "", "anything approved one by one starts neither")
        self.assertEqual(self.track("T.defaultTrack('actions', {op: 'new'}, 'group')"), "y")

    def test_neither_on_an_update_decided_one_by_one_leaves_it_in_review(self):
        self.assertEqual(self.track("T.reconcileOps(doc, plan)"),
                         [{"op": "remove", "n": 4, "keep_line": True}, {"op": "remove", "n": 5, "keep_line": True}],
                         "nothing for the closure (6) and the decision recorded (7)")
        self.assertEqual(self.track("T.trackSummary(T.trackCounts(doc, plan))"),
                         "3 work items to register · 2 kept in the minutes only · 2 left in Review", "counts only what will register")
        for op in self.track("T.reconcileOps(doc, plan)"):
            self.assertTrue(self.change(op)["ok"], op)
        r = self.approve(**self.track("T.approveArgs(doc, plan)"))
        self.assertTrue(r["ok"], r)
        self.assertEqual((r["approved"], sorted(r["waiting"])), (3, [6, 7]))
        items = {i["n"]: i for i in self.data()["items"]}
        self.assertEqual((items[6]["decision"], items[7]["decision"]), ("pending", "pending"), "not rejected: still in Review")

    def test_a_ticked_closure_is_approved_with_the_minutes(self):
        self.assertEqual(sorted(self.track("T.approveArgs(doc, plan)", {"6": "y"})["own"]), [1, 2, 3, 6])
        self.assertEqual(self.track("T.trackCounts(doc, plan)", {"6": "y"})["y"], 4)

    def test_a_kept_line_ticked_is_restored_and_crossed_is_restored_then_removed(self):
        self.assertTrue(self.change({"op": "remove", "n": 4, "keep_line": True})["ok"])
        self.assertTrue(self.change({"op": "remove", "n": 2, "keep_line": True})["ok"])
        ops = self.track("T.reconcileOps(doc, plan)", {"4": "y", "2": "n", "5": "y"})
        self.assertEqual(ops, [{"op": "restore", "n": 4}, {"op": "restore", "n": 2}, {"op": "remove", "n": 2, "keep_line": False}])
        self.assertEqual(self.track("T.reconcileOps(doc, plan)", {"4": "", "2": "", "5": "y"}), [], "kept lines left as they are")
        for op in ops:
            self.assertTrue(self.change(op)["ok"], op)
        self.assertEqual(self.track("T.reconcileOps(doc, plan)", {"4": "y", "2": "n", "5": "y"}), [], "in line now")


@unittest.skipUnless(shutil.which("node"), "needs Node")
class RowlessPromise(RunsTrackJs, Base):
    """Cap's #268 review H1: a promise has no row in the minutes, so no Track control; Approve minutes must never register it.
    The view sends group false with exactly the ticked rows' numbers (track.js approveArgs)."""
    def setUp(self):
        super().setUp()
        f = self.v.root / "system/staging/drafts/promise.json"
        s = {"title": "[ABC] Promise check-in", "date": "2026-10-14", "projects": ["ABC"],
             "minutes": {"start": "12:00", "end": "12:30", "summary": ["A short check-in."], "chat": False},
             "items": [{"table": "actions", "values": {"project": "ABC", "description": "Draft the cutover runbook", "owner": "Jane Doe"}},
                       {"table": "promises", "section": "Jane Doe, 12:05", "values": {
                           "project": "ABC", "promised_by": "Jane Doe", "promised_to": "Alan Carter",
                           "description": "Send the vendor's rate card", "due_date": "2026-10-20"}}]}
        f.write_text(json.dumps(s), encoding="utf-8")
        before = {p.name for p in (self.v.root / "system/staging").glob("proposed-*.json")}
        self.v.run("stage", str(f), script="minutes.py")
        self.name = next(p.name for p in (self.v.root / "system/staging").glob("proposed-*.json") if p.name not in before)
        self.draft = json.loads((self.v.root / "system/staging" / self.name).read_text())["meeting"]["draft"]

    def change(self, op):
        return self.js("import minutes_record\n"
                       f"r = minutes_record.change({self.draft!r}, {op!r})\nr.pop('doc', None)\nprint(json.dumps(r))")

    def promises(self):
        return [p["description"] for p in self.v.rows("promises")]

    def test_every_row_crossed_registers_nothing_not_even_the_promise(self):
        choices = {"1": "n"}
        self.assertEqual(self.states(choices), {"1": "n"}, "only the action has a Track control")
        for op in self.track("T.reconcileOps(doc, plan)", choices):
            self.assertTrue(self.change(op)["ok"], op)
        args = self.track("T.approveArgs(doc, plan)", choices)
        self.assertEqual(args, {"group": False, "own": []})
        r = self.approve(**args)
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["approved"], 0, r)
        self.assertNotIn("Send the vendor's rate card", self.promises(), "a promise nobody saw is never registered")
        self.assertNotIn("Draft the cutover runbook", [a["description"] for a in self.v.rows("actions")])
        self.assertEqual(r["waiting"], [2], "the promise waits in Review")

    def test_a_ticked_row_registers_and_the_rowless_promise_is_counted_as_left_in_review(self):
        self.assertEqual(self.track("T.trackSummary(T.trackCounts(doc, plan))"),
                         "1 work item to register · 0 kept in the minutes only · 1 left in Review")
        r = self.approve(**self.track("T.approveArgs(doc, plan)"))
        self.assertTrue(r["ok"], r)
        self.assertEqual((r["approved"], r["waiting"]), (1, [2]))
        self.assertIn("Draft the cutover runbook", [a["description"] for a in self.v.rows("actions")])
        self.assertNotIn("Send the vendor's rate card", self.promises())


class RaidWorkstream(Base):
    """dev/proposals/minutes-view-v2/raid-workstream.diff, applied: a risk's or issue's workstream is set from the minutes, and
    every workstream from the minutes (an action's too) must be one of the project's Active workstreams, or empty."""
    def setUp(self):
        super().setUp()
        self.v.propose("2026-10-14-0800", [{"n": 1, "op": "new", "table": "workstreams", "decision": "approved",
                                            "values": {"project": "ABC", "name": "Testing", "lead": "Jane Doe", "status": "Active",
                                                       "source": "t"}}])
        self.v.run("apply")

    def item(self, n):
        return next(i for i in self.data()["items"] if i["n"] == n)

    def test_a_risk_takes_one_of_the_projects_workstreams_in_its_own_spelling(self):
        r = self.change({"op": "edit", "n": 5, "values": {"workstream": "testing"}})
        self.assertTrue(r["ok"], r)
        self.assertEqual(self.item(5)["values"]["workstream"], "Testing")
        self.assertTrue(self.change({"op": "edit", "n": 2, "values": {"workstream": "Testing"}})["ok"], "an issue too")
        self.assertTrue(self.change({"op": "edit", "n": 5, "values": {"workstream": ""}})["ok"])
        self.assertNotIn("workstream", self.item(5)["values"], "empty clears it")

    def test_anything_else_is_refused_and_nothing_changes(self):
        for bad in ("Unknown", "<img src=x onerror=alert(1)>", "Testing\n", "Test\x00ing", "   ", 7, ["Testing"], {"a": 1}, "x" * 200):
            for n in (5, 1):
                r = self.change({"op": "edit", "n": n, "values": {"workstream": bad}})
                self.assertFalse(r["ok"], (n, bad))
                self.assertNotIn("workstream", self.item(n)["values"], (n, bad))


if __name__ == "__main__":
    unittest.main()
