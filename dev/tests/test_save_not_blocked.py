"""#280 (widened): saving a work item never fails because of an unrelated older staged proposal.

Run: python3 dev/tests/test_save_not_blocked.py
- Server (no Chrome): a save sends /api/apply {hold_peek, only: <its own proposal>}; only that proposal is applied, and an older
  staged proposal with an invalid approved item (a decision carrying `raised`, as Alan's Supplier checkpoint and Budget review)
  is left exactly as it was. Skips until live_server.py takes dev/proposals/280/live_server.py.diff.
- Page (needs Google Chrome): when an older server applies everything and stops on those files, the message says it is not his
  edit, names each blocking proposal by its meeting and date with every file, and offers Open in Intake (2.6: Review is the
  Intake page, #232).
"""
import json
import os
import re
import socket
import subprocess
import sys
import time
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_tracker import Vault  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
STALE = {"proposed-2026-10-20-1757-2.json": "Supplier checkpoint", "proposed-2026-10-20-1757-3.json": "Budget review"}


def stale_proposal(title):
    """An older meeting's proposal: its minutes still pending, item 1 an approved new decision carrying `raised` (invalid)."""
    return {"created": "2026-10-20T17:57:00", "source_run": "minutes", "files": [],
            "meeting": {"key": f"fp:2026-10-20|{title.lower()}", "title": title, "date": "2026-10-20", "projects": ["ABC"],
                        "minutes_decision": "pending"},
            "items": [{"n": 1, "op": "new", "table": "decisions", "match": "strong", "flags": [], "decision": "approved",
                       "values": {"project": "ABC", "decision": f"{title}: go with option B", "made_by": "Alan Carter",
                                  "raised": "2026-10-20", "source": f"minutes {title}"}}]}


def write_stale(root):
    out = {}
    for name, title in STALE.items():
        p = root / "system/staging" / name
        p.write_text(json.dumps(stale_proposal(title), indent=2) + "\n", encoding="utf-8")
        out[name] = p.read_bytes()
    return out


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@unittest.skipUnless("#280" in (REPO / "system/scripts/live_server.py").read_text(encoding="utf-8"),
                     "live_server.py has not taken dev/proposals/280/live_server.py.diff yet")
class SaveAppliesOnlyItsOwn(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = v = Vault()
        populate(v)
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        env = {**os.environ, "CREAITE_PORT": str(cls.port)}
        cls.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        html = urllib.request.urlopen(cls.base + "/").read().decode()
        cls.data = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))
        cls.token = cls.data["token"]

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())

    def owner(self, id_):
        return next(a["owner"] for a in self.v.rows("actions") if a["id"] == id_)

    def test_a_save_applies_only_its_own_proposal(self):
        before = write_stale(self.v.root)
        a1 = next(a for a in self.v.rows("actions") if a["id"] == "ABC-A-001")
        name = "proposed-2026-10-21-100000-dashboard.json"
        prop = {"created": "2026-10-21T10:00:00", "source_run": "dashboard", "files": [], "items": [
            {"n": 1, "op": "update", "table": "actions", "id": "ABC-A-001", "changes": {"owner": "Saved Alone"},
             "based_on": a1["updated_at"], "match": "strong", "flags": [], "decision": "approved"}]}
        (self.v.root / "system/staging" / name).write_text(json.dumps(prop), encoding="utf-8")
        res = self.post("/api/apply", {"hold_peek": True, "only": name})
        self.assertTrue(res["ok"], res)
        self.assertEqual(self.owner("ABC-A-001"), "Saved Alone")
        self.assertFalse((self.v.root / "system/staging" / name).exists(), "its own proposal was applied")
        for f, raw in before.items():                       # the older proposals were not touched, nor named
            self.assertEqual((self.v.root / "system/staging" / f).read_bytes(), raw, f)
            self.assertNotIn(f, res["message"])
        self.assertTrue(self.post("/api/undo", {"apply_id": res["apply_id"]})["ok"])

    def change(self, n, id_, owner):
        a = next(a for a in self.v.rows("actions") if a["id"] == id_)
        return {"n": n, "op": "update", "table": "actions", "id": id_, "changes": {"owner": owner},
                "based_on": a["updated_at"], "match": "strong", "flags": [], "decision": "approved"}

    def namesakes(self, name, owner, root_owner, id_="ABC-A-001"):
        """A staged save, and a file of the same name in the vault root holding another approved change (as an ask creaite run
        could plant: a root .json is an ordinary create)."""
        for f in STALE:
            (self.v.root / "system/staging" / f).unlink(missing_ok=True)
        staged, planted = self.v.root / "system/staging" / name, self.v.root / name
        staged.write_text(json.dumps({"created": "2026-10-21T12:00:00", "source_run": "dashboard", "files": [],
                                      "items": [self.change(1, id_, owner)]}), encoding="utf-8")
        raw = json.dumps({"created": "2026-10-21T12:00:00", "source_run": "dashboard", "files": [],
                          "items": [self.change(1, id_, root_owner)]})
        planted.write_text(raw, encoding="utf-8")
        self.addCleanup(planted.unlink, missing_ok=True)
        return staged, planted, raw

    def test_only_applies_the_staging_file_never_a_root_namesake(self):
        name = "proposed-2026-10-21-120000-dashboard.json"
        staged, planted, raw = self.namesakes(name, "From Staging", "From The Root")
        res = self.post("/api/apply", {"hold_peek": True, "only": name})
        self.assertTrue(res["ok"], res)
        self.assertEqual(self.owner("ABC-A-001"), "From Staging")
        self.assertFalse(staged.exists(), "the staged save was applied")
        self.assertEqual(planted.read_text(encoding="utf-8"), raw, "the root namesake is never read")
        self.assertTrue(self.post("/api/undo", {"apply_id": res["apply_id"]})["ok"])

    def test_hold_peek_applies_staging_files_never_root_namesakes(self):
        peek = self.v.root / "system/staging/proposed-2026-10-21-110000-dashboard.json"
        peek.write_text(json.dumps({"created": "2026-10-21T11:00:00", "source_run": "dashboard", "files": [],
                                    "peek": {"k": "actions", "id": "ABC-A-002", "ms": 1},
                                    "items": [self.change(1, "ABC-A-002", "Peek Waits")]}), encoding="utf-8")
        self.addCleanup(peek.unlink, missing_ok=True)
        name = "proposed-2026-10-21-120500-dashboard.json"
        staged, planted, raw = self.namesakes(name, "Held Peek Staging", "Held Peek Root")
        res = self.post("/api/apply", {"hold_peek": True})
        self.assertTrue(res["ok"], res)
        self.assertEqual(res.get("held"), 1, res)
        self.assertEqual(self.owner("ABC-A-001"), "Held Peek Staging")
        self.assertNotEqual(self.owner("ABC-A-002"), "Peek Waits")
        self.assertFalse(staged.exists())
        self.assertEqual(planted.read_text(encoding="utf-8"), raw, "the root namesake is never read")
        self.assertTrue(self.post("/api/undo", {"apply_id": res["apply_id"]})["ok"])

    def test_only_names_one_staged_proposal(self):
        for bad in ("../tracker.db", "proposed-none-such.json", "system/staging/proposed-x.json", 7, ""):
            res = self.post("/api/apply", {"only": bad})
            self.assertFalse(res["ok"], bad)
            self.assertIn("nothing was applied", res["message"])


class BlockedSaveWords(LiveBrowserCase):
    def test_the_message_names_each_older_proposal_and_offers_review(self):
        write_stale(self.v.root)
        b = self.b
        own = "proposed-2026-10-21-100000-dashboard.json"
        msg = ("Apply stopped. Nothing was written.\n"
               "  proposed-2026-10-20-1757-2.json item 1: unknown field(s) for decisions: raised\n"
               "  proposed-2026-10-20-1757-3.json item 1: unknown field(s) for decisions: raised\n")
        bl = b.eval(f"applyBlockers({json.dumps(msg)},{json.dumps(own)})")
        self.assertEqual([x["file"] for x in bl], list(STALE))
        self.assertEqual(b.eval(f"applyBlockers({json.dumps(msg)},'proposed-2026-10-20-1757-2.json').length"), 1)
        self.assertEqual(b.eval("applyBlockers('Saved.\\n  proposed-a.json item 1: x','b').length"), 0)
        words = b.eval(f"(async()=>await blockerWords(applyBlockers({json.dumps(msg)},{json.dumps(own)})))()")
        self.assertIn("not because of your edit", words)
        self.assertIn("2 older staged proposals", words)
        self.assertIn("Supplier checkpoint (20-10-2026)", words)
        self.assertIn("Budget review (20-10-2026)", words)
        for f in STALE:
            self.assertIn(f, words)
        self.assertIn("in Intake", words)
        (self.v.root / "system/staging/proposed-2026-10-19-0900-sweep.json").write_text(
            json.dumps({"created": "2026-10-19T09:00:00", "items": []}), encoding="utf-8")
        self.assertEqual(b.eval("(async()=>await proposalLabel('proposed-2026-10-19-0900-sweep.json'))()"),
                         "a proposal staged 19-10-2026")
        b.eval("reloadData()")
        b.wait("REV.some(x=>x.file==='proposed-2026-10-20-1757-3.json')", timeout=15)
        first = b.eval(f"REV.filter(x=>{json.dumps(list(STALE))}.includes(x.file)&&!x.done)[0].n")
        b.eval(f"openBlockersInIntake({json.dumps(list(STALE))})")
        b.wait("shared.VIEW==='intake-review'", timeout=10)
        # its meeting is open on the page, with the blocking proposal's row shown (here the minutes: their items are approved)
        b.wait(f"irOpen.value===irMeetingOf({first})&&!!document.querySelector('#v-intake-review tr.irprop[data-irn=\"{first}\"]')", timeout=10)
        self.assertEqual(b.errors, [])


@unittest.skipUnless("#280" in (REPO / "system/scripts/live_server.py").read_text(encoding="utf-8")
                     and "Held in Review, not applied: {p.name} item" in (REPO / "system/scripts/tracker.py").read_text(encoding="utf-8"),
                     "live_server.py and tracker.py have not taken dev/proposals/280/ yet")
class OwnItemHeld(LiveBrowserCase):
    """A page save whose own item the tracker refuses: tracker.py holds it in Review and exits 0, so the server says ok. The page
    says the tracker's reason (never "changed elsewhere"), puts the record back and drops its own proposal; a save is all or
    nothing, so another item of the same save that was written is undone."""

    def setUp(self):
        super().setUp()
        self.b.eval("S.autoApply=true")

    def item(self, n, id_, changes):
        a = next(a for a in self.v.rows("actions") if a["id"] == id_)
        return {"n": n, "op": "update", "table": "actions", "id": id_, "changes": changes, "based_on": a["updated_at"],
                "match": "strong", "flags": [], "decision": "approved"}

    def save(self, items):
        recs = [{"k": "actions", "id": i["id"], "f": "o"} for i in items]
        return self.b.eval(f"(async()=>await save('Owner changed',{json.dumps(items)},{{}},()=>{{}},()=>{{}},'test',"
                           f"{{recs:{json.dumps(recs)},wait:true}}))()")

    def snack(self):
        self.b.wait("document.getElementById('snackT')&&document.getElementById('snackT').textContent.length>0", 10)
        return self.b.eval("document.getElementById('snackT').textContent")

    def dashboard_proposals(self):
        return sorted(p.name for p in (self.v.root / "system/staging").glob("proposed-*dashboard*.json"))

    def owner(self, id_):
        return next(a["owner"] for a in self.v.rows("actions") if a["id"] == id_)

    def test_its_own_invalid_item_says_the_reason_and_leaves_nothing(self):
        was, applies = self.owner("ABC-A-001"), len(self.v.rows("applies"))
        ok = self.save([self.item(1, "ABC-A-001", {"owner": "Never Saved", "bogus_field": "x"})])
        self.assertFalse(ok)
        text = self.snack()
        self.assertIn("Not saved", text)
        self.assertIn("bogus_field", text)
        self.assertNotIn("changed elsewhere", text)
        self.assertEqual(self.owner("ABC-A-001"), was)
        self.assertEqual(self.dashboard_proposals(), [], "the page's own proposal is dropped, not left half-held")
        self.assertLessEqual(len(self.v.rows("applies")), applies + 1)
        self.assertEqual(self.b.errors, [])

    def test_a_save_is_all_or_nothing_when_one_of_its_items_is_held(self):
        was2, was1 = self.owner("ABC-A-002"), self.owner("ABC-A-001")
        ok = self.save([self.item(1, "ABC-A-002", {"owner": "Half Saved"}),
                        self.item(2, "ABC-A-001", {"owner": "Never Saved", "bogus_field": "x"})])
        self.assertFalse(ok)
        self.assertIn("bogus_field", self.snack())
        self.assertEqual(self.owner("ABC-A-002"), was2, "the written part of the save is undone")
        self.assertEqual(self.owner("ABC-A-001"), was1)
        self.assertEqual(self.dashboard_proposals(), [])
        self.assertEqual(self.b.errors, [])


if __name__ == "__main__":
    unittest.main()
