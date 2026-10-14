"""Tests for v2.1.0 P4 (BL-338): Approve minutes (review.approve_minutes) and the item rows' changes (minutes_record.change).

Run: python3 dev/tests/test_minutes_approve.py      (quick tier: no Chrome)
A fictional steering meeting is staged as a minutes record over a tracker that already holds two open actions and a pending
decision. Approving it applies the minutes and the ticked items in ONE apply (tracker.py apply, the one writer): actions and
updates are one group; a new decision, a decision recorded, a new risk and a closure each need their own tick (the bulk rule);
unticked items wait in Review; a removed item leaves the minutes (or keeps its line only); Update that one makes a new item an
update of an existing one; Undo takes the whole apply back.
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from contextlib import closing

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_tracker import ABC, Vault, action  # noqa: E402

DAY, TITLE = "2026-10-14", "[ABC] Steering committee"
DRAFT = "system/staging/drafts/2026-10-14 Steering committee.html"
FILED = f"{ABC}/minutes/2026-10-14 Steering committee.html"
VTT = ("WEBVTT\n\n00:00:01.000 --> 00:00:06.000\n<v Alan Carter>Morning all.</v>\n\n"
       "00:00:06.000 --> 00:00:12.000\n<v Jane Doe>Go-live stays on 20 November.</v>\n")
SEED = [action(1, description="Send the revised SOW to the client", due_date="2026-10-20"),
        action(2, description="Order the test licences"),
        {"n": 3, "op": "new", "table": "decisions", "match": "strong", "flags": [], "decision": "approved",
         "values": {"project": "ABC", "decision": "Choose the pilot site", "status": "Pending",
                    "source": f"{ABC}/minutes/2026-10-01 Steering.docx — Decisions"}}]


def spec():
    v = {"project": "ABC"}
    return {"title": TITLE, "date": DAY, "projects": ["ABC"], "transcript": "inbox/2026-10-14 Steering committee.vtt",
            "minutes": {"start": "10:00", "end": "11:00", "summary": ["The committee met."], "chat": False},
            "items": [
                {"table": "actions", "due_words": "Friday", "values": {**v, "description": "Book the UAT environment",
                                                                       "owner": "Alan Carter"}},
                {"table": "raid", "values": {**v, "type": "Issue", "description": "Test data isn't anonymised"}},
                {"op": "update", "table": "actions", "id": "ABC-A-001", "set": {"due_date": "2026-10-30"}, "why": "Omar said so"},
                {"table": "decisions", "values": {**v, "decision": "Go-live stays on 20 November", "made_by": "Jane Doe"}},
                {"table": "raid", "values": {**v, "type": "Risk", "description": "Vendor capacity is short → the cutover slips"}},
                {"op": "update", "table": "actions", "id": "ABC-A-002", "set": {"status": "Closed"}, "why": "Omar ordered them"},
                {"op": "update", "table": "decisions", "id": "ABC-D-003", "set": {"status": "Made", "reasoning": "Closest site"},
                 "why": "Jane decided"},
            ]}


def world(v):
    """The tracker's open items, then the meeting staged as a minutes record."""
    v.run("init")
    v.propose("2026-10-13-0900", SEED)
    v.run("apply")
    (v.root / "inbox/2026-10-14 Steering committee.vtt").write_text(VTT, encoding="utf-8")
    f = v.root / "system/staging/drafts/meeting.json"
    f.write_text(json.dumps(spec()), encoding="utf-8")
    v.run("stage", str(f), script="minutes.py")
    return next((v.root / "system/staging").glob("proposed-*.json")).name


class Base(unittest.TestCase):
    def setUp(self):
        self.now = os.environ.get("CREAITE_NOW")
        os.environ["CREAITE_NOW"] = "2026-10-14 12:00"
        self.v = Vault()
        self.name = world(self.v)

    def tearDown(self):
        self.v.cleanup()
        if self.now is None:
            os.environ.pop("CREAITE_NOW", None)
        else:
            os.environ["CREAITE_NOW"] = self.now

    def proposal_path(self):
        return next((self.v.root / "system/staging").glob("proposed-*.json"))

    def data(self):
        p = self.v.root / "system/staging" / self.name
        p = p if p.exists() else self.v.root / "system/staging/applied" / self.name
        return json.loads(p.read_text(encoding="utf-8"))

    def js(self, code):
        r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts')\n" + code],
                           cwd=self.v.root, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def approve(self, group=True, own=()):
        return self.js(f"import review\nprint(json.dumps(review.approve_minutes({self.name!r}, {group!r}, {list(own)!r})))")

    def change(self, op):
        return self.js("import minutes_record\n"
                       f"try:\n    r = minutes_record.change({DRAFT!r}, {op!r})\n"
                       "except minutes_record.RecordError as e:\n    r = {'ok': False, 'message': str(e)}\n"
                       "r.pop('doc', None)\nprint(json.dumps(r))")

    def doc(self, path=DRAFT):
        return self.js(f"import creaite_doc\nprint(json.dumps(creaite_doc.read({path!r})))")

    def rows(self, doc, sid):
        return next(s for s in doc["sections"] if s["id"] == sid)["rows"]

    def applies(self):
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            return [r[0] for r in con.execute("SELECT apply_id FROM applies WHERE undone_at IS NULL ORDER BY apply_id")]

    def by_id(self, table):
        return {r["id"]: r for r in self.v.rows(table)}


class Groups(Base):
    def test_the_popup_lists_the_group_and_each_own_tick(self):
        plan = self.js(f"import review\nprint(json.dumps(review.minutes_plan(json.load(open('system/staging/{self.name}')))))")
        groups = {r["n"]: (r["group"], r["why"]) for r in plan["items"]}
        self.assertEqual(groups, {1: ("group", None), 2: ("group", None), 3: ("group", None), 4: ("own", "new decision"),
                                  5: ("own", "new risk"), 6: ("own", "closing update"), 7: ("own", "decision made")})
        self.assertEqual(plan["group"], 3)
        self.assertEqual(plan["files"], [FILED])
        self.assertEqual(plan["transcripts"], [f"{ABC}/transcripts/2026-10-14 Steering committee.vtt"])
        self.assertEqual(plan["joins"], [])                       # the bulk rule unchanged: the one switch is off
        labels = {r["n"]: r["label"] for r in plan["items"]}
        self.assertEqual(labels[1], "New action: Book the UAT environment")
        self.assertEqual(labels[6][:20], "Closes ABC-A-002: AB")
        self.assertTrue(labels[7].startswith("Records ABC-D-003 as made"))

    def test_a_milestone_change_and_an_item_needing_a_project_never_join(self):
        out = self.js("import review\nprint(json.dumps([review.minutes_group(i) for i in ("
                      "{'op': 'update', 'table': 'milestones', 'id': 'ABC-M-001', 'changes': {'forecast_date': '2026-11-20'}},"
                      "{'op': 'new', 'table': 'actions', 'match': 'possible', 'values': {'project': 'ABC'}},"
                      "{'op': 'new', 'table': 'actions', 'values': {'project': 'ABC'}, 'decision': 'rejected'},"
                      "{'op': 'new', 'table': 'raid', 'values': {'project': 'ABC', 'type': 'Assumption'}})]))")
        self.assertEqual(out, ["milestone", "waits", "removed", "group"])


class Approve(Base):
    def test_one_apply_files_the_minutes_with_the_ticked_items_and_leaves_the_rest_in_review(self):
        before = self.applies()
        r = self.approve(group=True, own=[4, 6])
        self.assertTrue(r["ok"], r)
        self.assertEqual(self.applies(), before + [r["apply_id"]])            # one apply
        self.assertEqual((r["approved"], r["waiting"]), (5, [5, 7]))
        self.assertIn("filed 1", r["message"])
        acts, decs, raid = self.by_id("actions"), self.by_id("decisions"), self.by_id("raid")
        self.assertEqual(acts["ABC-A-001"]["due_date"], "2026-10-30")
        self.assertEqual(acts["ABC-A-002"]["status"], "Closed")
        self.assertEqual(acts["ABC-A-004"]["description"], "Book the UAT environment")
        self.assertEqual(acts["ABC-A-004"]["due_date"], "2026-10-16")
        self.assertEqual(acts["ABC-A-004"]["source"], f"{FILED} — Action Items")
        self.assertEqual(raid["ABC-005"]["type"], "Issue")
        self.assertEqual(decs["ABC-D-006"]["decision"], "Go-live stays on 20 November")
        self.assertEqual(decs["ABC-D-003"]["status"], "Pending")                # not ticked: waits
        self.assertNotIn("Vendor capacity is short → the cutover slips", [x["description"] for x in raid.values()])
        filed = self.doc(FILED)
        self.assertEqual(filed["state"], "approved")
        self.assertIn("Approved by Alan on 14 October 2026", filed["sections"][0]["text"])
        self.assertNotIn("Not yet reviewed", json.dumps(filed))
        self.assertEqual([x["ref"] for x in self.rows(filed, "actions")], ["ABC-A-004", "ABC-A-001", "ABC-A-002"])
        self.assertEqual([x["ref"] for x in self.rows(filed, "raid")], ["ABC-005", "@5"])     # the unticked risk: still a proposal
        self.assertIn("ABC-D-006", filed["items"])
        self.assertTrue((self.v.root / ABC / "transcripts/2026-10-14 Steering committee.vtt").exists())
        self.assertFalse((self.v.root / DRAFT).exists())
        self.assertIn(self.data()["meeting"]["key"], (self.v.root / "system/processed.txt").read_text())
        data = self.data()                                                       # still in staging: two items wait
        self.assertTrue((self.v.root / "system/staging" / self.name).exists())
        self.assertEqual([i["n"] for i in data["items"] if not i.get("applied")], [5, 7])
        self.assertTrue(all(i["decision"] == "pending" for i in data["items"] if not i.get("applied")))
        listed = json.loads(self.v.run("list", "--json", script="review.py").stdout)
        mine = [x for x in listed if x["file"] == self.name]
        self.assertEqual(sorted(x["ref"] for x in mine), [5, 7])                 # the minutes don't go to Review again

    def test_actions_and_updates_wait_when_their_tick_is_off(self):
        r = self.approve(group=False, own=[])
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["approved"], 0)
        self.assertEqual(sorted(r["waiting"]), [1, 2, 3, 4, 5, 6, 7])
        self.assertTrue((self.v.root / FILED).exists())
        self.assertEqual(self.by_id("actions")["ABC-A-001"]["due_date"], "2026-10-20")

    def test_undo_takes_the_whole_apply_back(self):
        self.approve(group=True, own=[4, 5, 6, 7])
        self.assertIn("Undid apply", self.v.run("undo").stdout)
        self.assertFalse((self.v.root / FILED).exists())
        self.assertEqual(self.doc()["state"], "draft")
        self.assertEqual(self.by_id("actions")["ABC-A-002"]["status"], "Open")
        self.assertNotIn("ABC-A-004", self.by_id("actions"))
        self.assertEqual(self.data()["meeting"].get("minutes_decision"), "pending")            # back in Review, as any undo

    def test_a_failed_apply_puts_every_decision_back(self):
        (self.v.root / ABC / "minutes").mkdir(parents=True, exist_ok=True)
        (self.v.root / FILED).write_text("Alan's own file", encoding="utf-8")       # a copy is never written over a file
        r = self.approve(group=True, own=[4])
        self.assertFalse(r["ok"])
        data = self.data()
        self.assertEqual(data["meeting"]["minutes_decision"], "pending")
        self.assertTrue(all(i["decision"] == "pending" for i in data["items"]))
        self.assertEqual((self.v.root / FILED).read_text(), "Alan's own file")

    def test_approved_or_word_minutes_are_refused(self):
        self.approve()
        again = self.approve()
        self.assertFalse(again["ok"])
        self.assertIn("already been approved", again["message"])


class Rows(Base):
    def test_remove_drops_the_line_and_rejects_the_item_in_the_same_apply(self):
        r = self.change({"op": "remove", "n": 2})
        self.assertEqual(r["message"], "Removed item 2 and its line.")
        doc = self.doc()
        self.assertEqual([x["ref"] for x in self.rows(doc, "raid")], ["@5"])
        self.assertNotIn("@2", doc["items"])
        self.assertIn("2", doc["meta"]["removed"])
        self.assertEqual(self.data()["items"][1]["decision"], "rejected")
        self.approve(group=True)
        self.assertNotIn("Test data isn't anonymised", [x["description"] for x in self.v.rows("raid")])
        self.assertEqual(len(self.v.rows("rejected")), 1)
        self.assertNotIn("anonymised", (self.v.root / FILED).read_text(encoding="utf-8"))

    def test_keep_the_line_keeps_its_words_without_the_item_and_undo_brings_it_back(self):
        self.change({"op": "remove", "n": 2, "keep_line": True})
        rows = self.rows(self.doc(), "raid")
        self.assertEqual(rows[0], {"ref": None, "cells": {"type": "Issue", "description": "Test data isn't anonymised", "owner": ""},
                                   "shown": True, "kept_line": True, "was": "@2"})
        self.assertTrue(self.change({"op": "restore", "n": 2})["ok"])
        rows = self.rows(self.doc(), "raid")
        self.assertEqual([x["ref"] for x in rows], ["@2", "@5"])
        self.assertEqual(self.data()["items"][1]["decision"], "pending")

    def test_update_that_one_turns_a_new_item_into_an_update(self):
        f = self.v.root / "system/staging/drafts/meeting.json"
        s = spec()
        s["title"], s["items"] = "[ABC] SOW check-in", [{"table": "actions", "values": {
            "project": "ABC", "description": "Send the SOW to the client", "owner": "Alan Carter", "due_date": "2026-10-23"}}]
        f.write_text(json.dumps(s), encoding="utf-8")
        self.v.run("stage", str(f), script="minutes.py")
        draft = "system/staging/drafts/2026-10-14 SOW check-in.html"
        r = self.js("import minutes_record\n"
                    f"r = minutes_record.change({draft!r}, {{'op': 'update', 'n': 1, 'id': 'abc-a-001'}})\nr.pop('doc')\n"
                    "print(json.dumps(r))")
        self.assertEqual(r["message"], "Item 1 now updates ABC-A-001 instead.")
        doc = self.doc(draft)
        row = self.rows(doc, "actions")[0]
        self.assertEqual(row["does"], "Updates ABC-A-001")
        self.assertEqual(row["cells"]["action"], "ABC-A-001: due 23-10-2026")
        name = json.loads(json.dumps(doc["meta"]))["proposal"]
        item = json.loads((self.v.root / "system/staging" / name).read_text())["items"][0]
        self.assertEqual((item["op"], item["id"], item["changes"]), ("update", "ABC-A-001", {"due_date": "2026-10-23"}))
        back = self.js("import minutes_record\n"
                       f"r = minutes_record.change({draft!r}, {{'op': 'keep_new', 'n': 1}})\nr.pop('doc')\nprint(json.dumps(r))")
        self.assertTrue(back["ok"])
        self.assertEqual(self.rows(self.doc(draft), "actions")[0]["does"], "New action")
        bad = self.js("import minutes_record\n"
                      f"try:\n    minutes_record.change({draft!r}, {{'op': 'update', 'n': 1, 'id': 'ABC-D-003'}})\n"
                      "    print(json.dumps('changed'))\nexcept minutes_record.RecordError as e:\n    print(json.dumps(str(e)))")
        self.assertIn("ABC-D-003 isn't an action in the tracker", bad)

    def test_editing_a_row_edits_its_staged_item(self):
        r = self.change({"op": "edit", "n": 1, "values": {"owner": "Omar Ali", "description": "Book the UAT environment now"}})
        self.assertTrue(r["ok"], r)
        item = self.data()["items"][0]
        self.assertEqual((item["values"]["owner"], item["values"]["description"]), ("Omar Ali", "Book the UAT environment now"))
        self.assertEqual(self.rows(self.doc(), "actions")[0]["cells"]["owner"], "Omar Ali")
        self.assertIn("can't be changed", self.change({"op": "edit", "n": 1, "values": {"project": "DEF"}})["message"])
        self.assertIn("is an update", self.change({"op": "edit", "n": 3, "values": {"owner": "Omar Ali"}})["message"])


class ThroughTheServer(unittest.TestCase):
    """The four routes, in order: the view, a row change, a page save (rows stay as staged), a stale save, the export, Approve,
    the filed minutes reopened and saved again (Edit again, with the server's own approval)."""

    @classmethod
    def setUpClass(cls):
        from test_live_server import free_port
        cls.now = os.environ.get("CREAITE_NOW")
        os.environ["CREAITE_NOW"] = "2026-10-14 12:00"
        cls.v = Vault()
        cls.name = world(cls.v)
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.proc = subprocess.Popen([sys.executable, str(cls.v.root / "system/scripts/live_server.py")], cwd=cls.v.root,
                                    env={**os.environ, "CREAITE_PORT": str(cls.port)}, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
        for _ in range(150):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        page = urllib.request.urlopen(cls.base + "/").read().decode()
        cls.token = json.loads(re.search(r'id="data">(.*?)</script>', page, re.S).group(1).replace("<\\/", "</"))["token"]

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()
        if cls.now is None:
            os.environ.pop("CREAITE_NOW", None)
        else:
            os.environ["CREAITE_NOW"] = cls.now

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())

    def test_the_four_routes(self):
        view = self.post("/api/minutes/draft", {"file": self.name})
        self.assertTrue(view["ok"], view)
        self.assertEqual((view["path"], view["doc"]["kind"], view["doc"]["version"]), (DRAFT, "minutes", 1))
        self.assertEqual([t["who"] for t in view["turns"]["turns"]], ["Alan Carter", "Jane Doe"])
        self.assertEqual(view["plan"]["group"], 3)
        self.assertEqual(view["versions"][0]["version"], 1)
        r = self.post("/api/minutes/save", {"path": DRAFT, "op": {"op": "remove", "n": 2}, "base_version": 1})
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["version"], 2)
        page = r["doc"]
        page["sections"][1]["text"] = "The committee met and agreed the go-live."
        raid = next(s for s in page["sections"] if s["id"] == "raid")
        raid["rows"] = []                                                      # rows change only through a row change
        r = self.post("/api/minutes/save", {"path": DRAFT, "doc": page, "base_version": 2})
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["version"], 3)
        self.assertEqual(r["doc"]["sections"][1]["text"], "The committee met and agreed the go-live.")
        self.assertEqual([x["ref"] for x in next(s for s in r["doc"]["sections"] if s["id"] == "raid")["rows"]], ["@5"])
        stale = self.post("/api/minutes/save", {"path": DRAFT, "doc": page, "base_version": 2})
        self.assertFalse(stale["ok"])
        self.assertIn("saved elsewhere", stale["message"])
        ex = self.post("/api/minutes/export", {"path": DRAFT, "format": "pdf"})
        if ex.get("stub"):                                                     # P2's creaite_doc.export isn't on this branch yet
            self.assertFalse(ex["ok"])
            self.assertIn("creaite_doc.export", ex["message"])
        else:
            self.assertTrue(ex["ok"], ex)
        self.assertFalse(self.post("/api/minutes/export", {"path": DRAFT, "format": "odt"})["ok"])
        ok = self.post("/api/minutes/approve", {"file": self.name, "group": True, "own": [4]})
        self.assertTrue(ok["ok"], ok)
        self.assertIsInstance(ok["apply_id"], int)
        self.assertEqual(ok["waiting"], [5, 6, 7])
        filed = self.post("/api/minutes/draft", {"path": FILED})
        self.assertEqual((filed["doc"]["state"], filed["plan"]), ("approved", None))
        self.assertEqual(filed["doc"]["meta"]["transcript"], f"{ABC}/transcripts/2026-10-14 Steering committee.vtt")
        self.assertEqual(len(filed["turns"]["turns"]), 2)                     # the pane reads the filed transcript
        doc = filed["doc"]
        doc["sections"][1]["text"] = "Edited again after approval."
        again = self.post("/api/minutes/save", {"path": FILED, "doc": doc, "base_version": doc["version"]})
        self.assertTrue(again["ok"], again)                                     # sensitive, approved by Alan's own Save
        self.assertEqual(again["version"], doc["version"] + 1)
        self.assertEqual(again["doc"]["state"], "approved")
        refused = self.post("/api/minutes/save", {"path": FILED, "op": {"op": "remove", "n": 5}})
        self.assertIn("approved", refused["message"])
        for bad in ("../etc/passwd.html", "system/config/settings.json", f"{ABC}/CLAUDE.md"):
            self.assertFalse(self.post("/api/minutes/draft", {"path": bad})["ok"], bad)


if __name__ == "__main__":
    unittest.main()
