"""BL-200 (sprint-review-work): change the project in Review — one pending item, or a whole set of minutes.

Run: python3 dev/tests/test_review_project.py

review.py assign moves any pending new item (its old project's milestone and workstream are cleared) and, on a minutes
entry, every item from those minutes with the minutes' filing (file_ops, projects, source paths). Update items stay;
an unknown or closed project is refused; nothing reaches the tracker before approval and apply.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dashboard import d, new, populate  # noqa: E402
from test_tracker import ABC, Vault, action  # noqa: E402

DEF = "projects/DEF Digital Enablement"
GHI = "projects/GHI Growth Hub"


def add_ghi(v, active=True):
    reg = v.root / "projects/_portfolio/project-register.md"
    lines = reg.read_text().splitlines()
    at = max(i for i, ln in enumerate(lines) if ln.startswith("| DEF |"))
    lines.insert(at + 1, "| GHI | Growth Hub | GHI Growth Hub | Grow | Gill (sponsor) | ghi.example | GHI core | hub |")
    reg.write_text("\n".join(lines) + "\n")
    v.run("init")
    for sub in ("minutes", "transcripts"):
        (v.root / GHI / sub).mkdir(parents=True, exist_ok=True)


def seed_joint(v):
    """ABC, DEF and GHI, and one pending set of minutes (ABC) with two new items, an update and a DEF item."""
    populate(v)
    add_ghi(v)
    a_id = next(a["id"] for a in v.rows("actions") if a["project"] == "ABC")
    (v.root / "inbox/Joint.vtt").write_bytes(b"WEBVTT joint")
    (v.root / "system/staging/drafts/Joint.docx").write_bytes((v.root / "system/templates/minutes-template.docx").read_bytes())
    name = f"{d(0)} Joint sync"
    src = f"{ABC}/minutes/{name}.docx — Actions"
    p = v.propose("joint", [
        {**action(1, description="Send the joint plan", milestone="ABC-M-001", workstream="Build", source=src),
         "decision": "pending"},
        {**new("raid", 2, project="ABC", type="Risk", description="Joint risk", raised=d(0), source=src),
         "decision": "pending"},
        {"n": 3, "op": "update", "table": "actions", "id": a_id, "changes": {"status": "Closed"},
         "why": "Done", "source": src, "match": "strong", "flags": [], "decision": "pending"},
        {**action(4, project="DEF", description="DEF follow-up", source=f"{DEF}/minutes/{name}.docx — Actions"),
         "decision": "pending"},
    ], meeting={"key": "k-joint", "title": "Joint sync", "date": d(0), "projects": ["ABC"],
                "draft": "system/staging/drafts/Joint.docx", "transcript": "inbox/Joint.vtt",
                "minutes_decision": "pending",
                "file_ops": [{"op": "copy", "from": "draft", "to": f"{ABC}/minutes/{name}.docx"},
                             {"op": "copy", "from": "transcript", "to": f"{ABC}/transcripts/{name}.vtt"},
                             {"op": "remove", "path": "inbox/Joint.vtt"},
                             {"op": "remove", "path": "system/staging/drafts/Joint.docx"}],
                "source_map": {f"{ABC}/minutes/{name}.docx": f"{ABC}/transcripts/{name}.vtt"}})
    return p, name, a_id


class ReviewProjectTests(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.p, self.name, self.a_id = seed_joint(self.v)

    def tearDown(self):
        self.v.cleanup()

    def rows(self):
        return json.loads(self.v.run("list", "--json", script="review.py").stdout)

    def num(self, file, ref):
        return next(r["n"] for r in self.rows() if r["file"] == file and r["ref"] == ref)

    def data(self):
        return json.loads(self.p.read_text())

    def test_one_item_moves_and_its_stale_milestone_is_cleared(self):
        before = self.v.snapshot()
        n = self.num(self.p.name, 1)
        out = self.v.run("assign", str(n), "def", script="review.py").stdout
        self.assertIn("project set to Digital Enablement", out)
        self.assertIn("milestone", out)
        it = next(i for i in self.data()["items"] if i["n"] == 1)
        self.assertEqual((it["values"]["project"], it["values"]["milestone"], it["values"]["workstream"]), ("DEF", None, None))
        self.assertEqual((it["match"], it["decision"], it["moved_from"], it["edited_in"]), ("strong", "pending", "ABC", "review"))
        self.assertEqual(self.v.snapshot(), before)                       # nothing reaches the tracker before apply

    def test_moving_back_puts_back_the_milestone_and_workstream_the_move_cleared(self):
        # BL-281: Review's Undo of a move ran the move backwards, but the cleared links stayed cleared
        n = self.num(self.p.name, 1)
        self.v.run("assign", str(n), "DEF", script="review.py")
        it = next(i for i in self.data()["items"] if i["n"] == 1)
        self.assertEqual(it["moved_cleared"], {"ABC": {"milestone": "ABC-M-001", "workstream": "Build"}})
        self.v.run("assign", str(n), "GHI", script="review.py")             # on through a third project: still kept
        self.v.run("assign", str(n), "ABC", script="review.py")
        it = next(i for i in self.data()["items"] if i["n"] == 1)
        self.assertEqual((it["values"]["project"], it["values"]["milestone"], it["values"]["workstream"]),
                         ("ABC", "ABC-M-001", "Build"))
        self.assertNotIn("moved_cleared", it)
        self.assertNotIn("moved_from", it)

    def test_a_strong_match_can_be_moved_too(self):
        n = self.num("proposed-pending.json", 1)                          # a strong ABC action, not only a possible match
        self.v.run("assign", str(n), "DEF", script="review.py")
        it = next(i for i in json.loads((self.v.root / "system/staging/proposed-pending.json").read_text())["items"] if i["n"] == 1)
        self.assertEqual(it["values"]["project"], "DEF")

    def test_update_item_unknown_and_closed_projects_are_refused(self):
        n = self.num(self.p.name, 3)
        r = self.v.run("assign", str(n), "DEF", script="review.py", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("is an update to", r.stderr)
        n = self.num(self.p.name, 1)
        r = self.v.run("assign", str(n), "XYZ", script="review.py", ok=False)
        self.assertIn("isn't in the tracker", r.stderr)
        self.v.propose("close", [{"n": 1, "op": "update", "table": "projects", "id": "GHI", "changes": {"active": 0},
                                  "decision": "approved"}])
        self.v.run("apply")
        n = self.num(self.p.name, 1)
        r = self.v.run("assign", str(n), "GHI", script="review.py", ok=False)
        self.assertIn("is closed", r.stderr)
        self.assertEqual(next(i for i in self.data()["items"] if i["n"] == 1)["values"]["project"], "ABC")

    def test_whole_minutes_move_with_their_files(self):
        before = self.v.snapshot()
        n = self.num(self.p.name, "meeting")
        prev = json.loads(self.v.run("assign", str(n), "GHI", "--dry-run", "--json", script="review.py").stdout)
        self.assertEqual(prev["headline"], "Move 2 items from Example Programme to Growth Hub")
        self.assertIn(self.a_id, prev["updates"])
        self.assertEqual(self.data()["meeting"]["projects"], ["ABC"])            # a dry run changes nothing
        out = self.v.run("assign", str(n), "GHI", script="review.py").stdout
        self.assertIn("moved 2 items from Example Programme to Growth Hub", out)
        self.assertIn(f"Note: {self.a_id} is an update", out)
        data = self.data()
        m = data["meeting"]
        self.assertEqual(m["projects"], ["GHI"])
        copies = [o["to"] for o in m["file_ops"] if o["op"] == "copy"]
        self.assertEqual(copies, [f"{GHI}/minutes/{self.name}.docx", f"{GHI}/transcripts/{self.name}.vtt"])
        self.assertEqual(m["source_map"], {f"{GHI}/minutes/{self.name}.docx": f"{GHI}/transcripts/{self.name}.vtt"})
        items = {i["n"]: i for i in data["items"]}
        self.assertEqual([items[k]["values"]["project"] for k in (1, 2, 4)], ["GHI", "GHI", "DEF"])
        self.assertTrue(items[1]["values"]["source"].startswith(f"{GHI}/minutes/"))
        self.assertEqual(items[3]["id"], self.a_id)                             # the update is left as it was
        self.assertEqual(self.v.snapshot(), before)                             # nothing filed, nothing written yet
        # approve everything and apply: the files land in GHI's folders and processed.txt names them
        for i in data["items"]:
            i["decision"] = "approved"
        m["minutes_decision"] = "approved"
        self.p.write_text(json.dumps(data))
        self.v.run("apply")
        self.assertTrue((self.v.root / GHI / "minutes" / f"{self.name}.docx").is_file())
        self.assertTrue((self.v.root / GHI / "transcripts" / f"{self.name}.vtt").is_file())
        self.assertFalse((self.v.root / ABC / "minutes" / f"{self.name}.docx").exists())
        self.assertIn(f"{GHI}/minutes/{self.name}.docx", (self.v.root / "system/processed.txt").read_text())
        self.assertEqual({a["project"] for a in self.v.rows("actions") if a["description"] == "Send the joint plan"}, {"GHI"})

    def test_items_moved_alone_are_offered_not_taken(self):
        n1 = self.num(self.p.name, 1)
        self.v.run("assign", str(n1), "DEF", script="review.py")
        n = self.num(self.p.name, "meeting")
        prev = json.loads(self.v.run("assign", str(n), "GHI", "--dry-run", "--json", script="review.py").stdout)
        self.assertEqual((prev["items"], prev["alone"]), (1, 1))
        self.assertEqual(json.loads(self.v.run("assign", str(n), "GHI", "--all", "--dry-run", "--json",
                                               script="review.py").stdout)["items"], 2)
        self.v.run("assign", str(n), "GHI", script="review.py")
        items = {i["n"]: i for i in self.data()["items"]}
        self.assertEqual((items[1]["values"]["project"], items[2]["values"]["project"]), ("DEF", "GHI"))

    def test_cross_project_minutes_ask_which_project(self):
        data = self.data()
        m = data["meeting"]
        m["projects"] = ["ABC", "DEF"]
        m["file_ops"][2:2] = [{"op": "copy", "from": "draft", "to": f"{DEF}/minutes/{self.name}.docx"},
                              {"op": "copy", "from": "transcript", "to": f"{DEF}/transcripts/{self.name}.vtt"}]
        self.p.write_text(json.dumps(data))
        n = self.num(self.p.name, "meeting")
        r = self.v.run("assign", str(n), "GHI", script="review.py", ok=False)
        self.assertIn("Say which project's items to move", r.stderr)
        self.v.run("assign", str(n), "GHI", "--from=DEF", script="review.py")
        data = self.data()
        self.assertEqual(data["meeting"]["projects"], ["ABC", "GHI"])
        copies = [o["to"] for o in data["meeting"]["file_ops"] if o["op"] == "copy"]
        self.assertEqual(copies, [f"{ABC}/minutes/{self.name}.docx", f"{ABC}/transcripts/{self.name}.vtt",
                                  f"{GHI}/minutes/{self.name}.docx", f"{GHI}/transcripts/{self.name}.vtt"])
        items = {i["n"]: i for i in data["items"]}
        self.assertEqual([items[k]["values"]["project"] for k in (1, 2, 4)], ["ABC", "ABC", "GHI"])
        # moving into a project the minutes already have: its own copies are kept, the moved ones dropped
        n = self.num(self.p.name, "meeting")
        self.v.run("assign", str(n), "ABC", "--from=GHI", script="review.py")
        data = self.data()
        self.assertEqual(data["meeting"]["projects"], ["ABC"])
        self.assertEqual([o["to"] for o in data["meeting"]["file_ops"] if o["op"] == "copy"],
                         [f"{ABC}/minutes/{self.name}.docx", f"{ABC}/transcripts/{self.name}.vtt"])

    def test_transcript_already_in_the_old_project_is_copied_not_moved(self):
        data = self.data()
        m = data["meeting"]
        tr = f"{ABC}/transcripts/{self.name}.vtt"
        (self.v.root / tr).write_bytes(b"WEBVTT mine")
        m["transcript"] = tr
        m["file_ops"] = [{"op": "copy", "from": "draft", "to": f"{ABC}/minutes/{self.name}.docx"},
                         {"op": "remove", "path": "system/staging/drafts/Joint.docx"}]
        self.p.write_text(json.dumps(data))
        n = self.num(self.p.name, "meeting")
        self.v.run("assign", str(n), "GHI", script="review.py")
        ops = self.data()["meeting"]["file_ops"]
        self.assertIn({"op": "copy", "from": "transcript", "to": f"{GHI}/transcripts/{self.name}.vtt"}, ops)
        self.assertFalse(any(o.get("path") == tr for o in ops))                  # Alan's own file is never removed



# ── the dashboard, against the real live server (BL-200) ─────────────────────────────────────────────────────────────
from live_browser import LiveBrowserCase  # noqa: E402


class ReviewProjectBrowserTests(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        cls.prop, cls.name, cls.a_id = seed_joint(v)
        v.run(script="build_dashboard.py")

    def data(self):
        return json.loads(self.prop.read_text())

    def open_review(self):
        self.b.eval('go("review")')
        self.b.wait('!!document.querySelector("#reviewBody tr[data-n]")')

    def row_of(self, text):
        n = self.b.eval(f'(REV.find(r=>!r.done&&r.rec&&r.rec.t.includes({json.dumps(text)}))||{{}}).n')
        self.assertIsNotNone(n, text)
        return f'#reviewBody tr[data-n="{n}"]'

    def test_an_item_row_moves_to_another_project(self):
        before = self.v.snapshot()
        self.open_review()
        row = self.row_of("Send the joint plan")
        self.b.click(row + " td.title")                                    # the row's buttons show on the cursor row
        self.b.click(row + ' [data-act="pj"]')
        self.b.wait('!!document.querySelector("#rvMoveTo[role=menu]")')                 # BL-316: the Menu block's menu
        self.assertEqual(self.b.eval('document.querySelector("#rvMoveTo [role=menuitem][aria-disabled=true]").textContent.trim()'),
                         "Example ProgrammeIts project now")
        self.b.eval('[...document.querySelectorAll("#rvMoveTo [role=menuitem]")].find(b=>b.textContent.startsWith("Growth Hub")).click()')
        self.b.wait('/Moved to Growth Hub/.test(document.getElementById("snackT").textContent)')
        it = next(i for i in self.data()["items"] if i["n"] == 1)
        self.assertEqual((it["values"]["project"], it["values"]["milestone"], it["decision"]), ("GHI", None, "pending"))
        self.assertEqual(self.v.snapshot()[0], before[0])                  # the tracker is untouched
        self.b.wait('REV.some(r=>r.rec&&r.rec.t==="Send the joint plan"&&r.p==="GHI")')
        self.b.eval('UNDO()')                                              # BL-281: Undo puts back what the move cleared
        self.b.wait('/Moved back/.test(document.getElementById("snackT").textContent)')
        it = next(i for i in self.data()["items"] if i["n"] == 1)
        self.assertEqual((it["values"]["project"], it["values"]["milestone"], it["values"]["workstream"]), ("ABC", "ABC-M-001", "Build"))
        self.b.wait('REV.some(r=>r.rec&&r.rec.t==="Send the joint plan"&&r.p==="ABC")')
        self.assertFalse(self.b.eval('!!document.querySelector(`#reviewBody tr[data-n="${REV.find(r=>r.kind==="update"&&!r.done).n}"] [data-act=pj]`)'))

    def test_the_minutes_move_after_a_preview(self):
        self.open_review()
        row = '#reviewBody tr.mparent'
        self.b.click(row + " td.title")
        self.b.click(row + ' [data-act="pj"]')
        self.b.wait('!!document.querySelector("#rvMoveTo[role=menu]")')
        self.b.eval('[...document.querySelectorAll("#rvMoveTo [role=menuitem]")].find(b=>b.textContent.startsWith("Growth Hub")).click()')
        self.b.wait('!!document.querySelector(".pkpop.rvmv")')
        self.assertEqual(self.b.eval('document.querySelector(".rvmv-h").textContent'), "Move 2 items from Example Programme to Growth Hub")
        self.assertIn(self.a_id, self.b.eval('document.querySelector(".pkpop.rvmv").textContent'))
        self.assertEqual(self.data()["meeting"]["projects"], ["ABC"])     # nothing yet: only the preview
        self.b.click('.pkpop.rvmv [data-mv="go"]')
        self.b.wait('/Moved 2 items/.test(document.getElementById("snackT").textContent)')
        m = self.data()["meeting"]
        self.assertEqual(m["projects"], ["GHI"])
        self.assertTrue(all(o["to"].startswith("projects/GHI") for o in m["file_ops"] if o["op"] == "copy"))
        self.b.wait('REV.some(r=>r.ref==="meeting"&&r.p==="GHI")')
        self.b.eval('UNDO()')                                              # Undo moves them back
        self.b.wait('/Moved back/.test(document.getElementById("snackT").textContent)')
        self.assertEqual(self.data()["meeting"]["projects"], ["ABC"])
        it = next(i for i in self.data()["items"] if i["n"] == 1)               # BL-281: and its milestone and workstream
        self.assertEqual((it["values"]["milestone"], it["values"]["workstream"]), ("ABC-M-001", "Build"))

    def test_the_peek_has_a_project_chip_for_a_proposal(self):
        self.open_review()
        n = self.b.eval('REV.find(r=>r.rec&&r.rec.t==="Joint risk").n')
        self.b.eval(f'openProposal({n})')
        self.b.wait('!!document.querySelector(\'#pkProps [data-pkp="p"]\')')
        self.assertIn("Example Programme", self.b.eval('document.querySelector(\'#pkProps [data-pkp="p"]\').textContent'))


if __name__ == "__main__":
    unittest.main()
