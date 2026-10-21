"""#280 (widened): saving a work item never fails because of an unrelated older staged proposal.

Run: python3 dev/tests/test_save_not_blocked.py
- Server (no Chrome): a save sends /api/apply {hold_peek, only: <its own proposal>}; only that proposal is applied, and an older
  staged proposal with an invalid approved item (a decision carrying `raised`, as Alan's Supplier checkpoint and Budget review)
  is left exactly as it was. Skips until live_server.py takes dev/proposals/280/live_server.py.diff.
- Page (needs Google Chrome): when an older server applies everything and stops on those files, the message says it is not his
  edit, names each blocking proposal by its meeting and date with every file, and offers Open in Review.
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
        self.assertIn("in Review", words)
        (self.v.root / "system/staging/proposed-2026-10-19-0900-sweep.json").write_text(
            json.dumps({"created": "2026-10-19T09:00:00", "items": []}), encoding="utf-8")
        self.assertEqual(b.eval("(async()=>await proposalLabel('proposed-2026-10-19-0900-sweep.json'))()"),
                         "a proposal staged 19-10-2026")
        b.eval("reloadData()")
        b.wait("REV.some(x=>x.file==='proposed-2026-10-20-1757-3.json')", timeout=15)
        b.eval(f"openBlockersInReview({json.dumps(list(STALE))})")
        b.wait("shared.VIEW==='review'", timeout=10)
        self.assertEqual(b.errors, [])


if __name__ == "__main__":
    unittest.main()
