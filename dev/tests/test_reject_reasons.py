"""BL-133 stage B: reject reasons and duplicate hints. The schema change (rejected.reason, rejected.duplicate_of) with its migration
from a database made before it, apply and undo, review.py's phrases, the read for extraction, the duplicate hint, Activity, and the
reason menu in a real browser.

Run: python3 dev/tests/test_reject_reasons.py   (the browser part needs Google Chrome; skipped otherwise)
"""
import json
import sqlite3
import sys
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_tracker import Vault, action  # noqa: E402

OLD_REJECTED = """CREATE TABLE IF NOT EXISTS rejected (
  fingerprint  TEXT PRIMARY KEY,  -- hash of project + type + normalised description
  rejected_at  TEXT NOT NULL DEFAULT (datetime('now')),
  via          TEXT
);"""


def pending(item, **kw):
    return {**item, "decision": "pending", **kw}


def old_schema(v):
    """schema.sql as it was before this change: the rejected table without its two new columns."""
    s = (v.root / "system/scripts/schema.sql").read_text()
    start = s.index("CREATE TABLE IF NOT EXISTS rejected (")
    end = s.index(");", start) + 2
    return s[:start] + OLD_REJECTED + s[end:]


class Engine(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        populate(self.v)

    def tearDown(self):
        self.v.cleanup()

    def cols(self):
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            return [r[1] for r in con.execute("PRAGMA table_info(rejected)")]

    def reject(self, name, n, ok=True, **kw):
        p = self.v.propose(name, [pending(action(n, description=f"Item {name} {n}"), **kw)])
        data = json.loads(p.read_text())
        data["items"][0]["decision"] = "rejected"
        p.write_text(json.dumps(data))
        return self.v.run("apply", ok=ok)

    def test_the_migration_keeps_every_row_and_adds_the_columns(self):
        db = self.v.root / "system/tracker.db"
        # a copy of a database made before the change: rebuild rejected the old way, with rows in it
        with closing(sqlite3.connect(db)) as con:
            con.execute("DROP TABLE rejected")
            con.executescript(old_schema(self.v))
            con.executemany("INSERT INTO rejected (fingerprint, rejected_at, via) VALUES (?,?,?)",
                            [(f"fp{i}", "2026-10-01 09:00:00", "proposed-old.json") for i in range(5)])
            con.commit()
            before = {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ("actions", "raid", "decisions", "projects", "rejected", "change_log")}
        self.assertNotIn("reason", self.cols())
        out = self.v.run("init").stdout
        self.assertIn("run tracker.py migrate", out)
        self.assertIn("rejected", self.v.run(script="doctor.py", ok=False).stdout)        # doctor names it
        out = self.v.run("migrate").stdout
        self.assertIn("rejected (5 rows)", out)
        self.assertEqual(self.cols(), ["fingerprint", "rejected_at", "via", "reason", "duplicate_of"])
        with closing(sqlite3.connect(db)) as con:
            after = {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in before}
            self.assertEqual(con.execute("SELECT via FROM rejected WHERE fingerprint='fp3'").fetchone()[0], "proposed-old.json")
        self.assertEqual(before, after)                                                    # every row kept
        self.assertIn("Schema is up to date", self.v.run("migrate").stdout)                # again: nothing changes
        # and an apply, an undo and a re-apply behave
        self.reject("one", 1, reject_reason="Not mine to track")
        with closing(sqlite3.connect(db)) as con:
            self.assertEqual(con.execute("SELECT count(*), max(reason) FROM rejected WHERE reason IS NOT NULL").fetchone(), (1, "Not mine to track"))
        self.v.run("undo")
        with closing(sqlite3.connect(db)) as con:
            self.assertEqual(con.execute("SELECT count(*) FROM rejected").fetchone()[0], 5)
        self.reject("two", 1, reject_reason="Not an action")
        with closing(sqlite3.connect(db)) as con:
            self.assertEqual(con.execute("SELECT count(*) FROM rejected").fetchone()[0], 6)

    def test_a_reason_and_a_duplicate_are_stored_and_undone(self):
        self.v.run("migrate")
        dup = next(r["id"] for r in self.v.rows("actions") if r["status"] == "Open")
        self.reject("dup", 1, duplicate_of=dup)
        row = [r for r in self.v.rows("rejected") if r["duplicate_of"]][0]
        self.assertEqual((row["reason"], row["duplicate_of"]), ("Duplicate", dup))
        self.v.run("undo")
        self.assertFalse([r for r in self.v.rows("rejected") if r["duplicate_of"]])
        # a duplicate of something that doesn't exist stops the apply, with its reason
        r = self.reject("bad", 2, ok=False, duplicate_of="ABC-A-999")
        self.assertIn("no such action", r.stdout)
        self.assertFalse([x for x in self.v.rows("rejected") if x["duplicate_of"]])

    def test_review_py_takes_a_reason_and_a_duplicate_phrase(self):
        dup = next(r["id"] for r in self.v.rows("actions") if r["status"] == "Open")
        self.v.propose("rv", [pending(action(1, description="Phrase one")), pending(action(2, description="Phrase two")),
                              pending(action(3, description="Phrase three"))])
        rows = json.loads(self.v.run("list", "--json", script="review.py").stdout)
        n = {r["text"]: r["n"] for r in rows if r["file"] == "proposed-rv.json"}
        out = self.v.run("reject", str(n["Phrase one"]), "as", "a", "duplicate", "of", dup.lower(), script="review.py").stdout
        self.assertIn("Rejected 1", out)
        self.v.run("reject", str(n["Phrase two"]), "because", "not", "mine", "to", "track", script="review.py")
        self.v.run("reject", str(n["Phrase three"]), "--reason=Covered in the steering pack", script="review.py")
        bad = self.v.run("reject", "1", "as", "a", "duplicate", "of", "ABC-A-999", script="review.py", ok=False).stdout
        self.assertIn("no ABC-A-999", bad)
        items = {i["values"]["description"]: i for i in json.loads((self.v.root / "system/staging/proposed-rv.json").read_text())["items"]}
        self.assertEqual((items["Phrase one"]["reject_reason"], items["Phrase one"]["duplicate_of"]), ("Duplicate", dup))
        self.assertEqual(items["Phrase two"]["reject_reason"], "Not mine to track")
        self.assertEqual(items["Phrase three"]["reject_reason"], "Covered in the steering pack")
        self.v.run("migrate")
        self.v.run("apply")
        # what extraction reads: the project's reasons with the items they were given for
        got = json.loads(self.v.run("read", "rejected", "--project", "ABC").stdout)
        self.assertEqual(sorted(g["item"] for g in got), ["Phrase one", "Phrase three", "Phrase two"])
        self.assertTrue(all(g["reason"] for g in got))
        self.assertEqual(json.loads(self.v.run("read", "rejected", "--project", "DEF").stdout), [])
        # Activity shows the reason
        self.v.run(script="build_dashboard.py")
        html = (self.v.root / "dashboard.html").read_text()
        self.assertIn("rejected: Not mine to track", html)
        # and a rejected duplicate is not proposed again: its fingerprint is in the table
        fps = {r["fingerprint"] for r in self.v.rows("rejected")}
        import importlib.util
        spec = importlib.util.spec_from_file_location("tracker_mod", self.v.root / "system/scripts/tracker.py")
        t = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(self.v.root / "system/scripts"))
        spec.loader.exec_module(t)
        self.assertIn(t.fingerprint(action(1, description="Phrase one")), fps)

    def test_the_duplicate_hint(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system/scripts"))
        import build_dashboard as bd
        self.assertGreaterEqual(bd.dup_overlap(bd.dup_tokens("Send the revised SOW to the client"), bd.dup_tokens("Send revised SOW to client")), 0.6)
        self.v.run("migrate")
        open_ = next(r for r in self.v.rows("actions") if r["status"] == "Open" and r["project"] == "ABC")
        closed = [r for r in self.v.rows("actions") if r["status"] in ("Closed", "Cancelled")]
        items = [pending(action(1, description=open_["description"] + " please")),                          # close match: found
                 pending(action(2, description=open_["description"], project="DEF")),                         # another project: no
                 pending({"n": 3, "op": "new", "table": "raid", "match": "strong", "flags": [], "values": {"project": "ABC", "type": "Issue",
                          "description": open_["description"], "source": "x"}}),                                # another type: no
                 pending(action(4, description="Something else entirely about the budget"))]
        if closed:
            items.append(pending(action(5, description=closed[0]["description"], project=closed[0]["project"])))  # closed: no
        self.v.propose("dups", items)
        self.v.run(script="build_dashboard.py")
        html = (self.v.root / "dashboard.html").read_text()
        data = json.loads(html.split('<script type="application/json" id="data">', 1)[1].split("</script>", 1)[0])
        rev = {r["ref"]: r for r in data["review"] if r["file"] == "proposed-dups.json"}
        self.assertEqual(rev[1]["dup"]["id"], open_["id"])
        self.assertIsNone(rev[2]["dup"])
        self.assertIsNone(rev[3]["dup"])
        self.assertIsNone(rev[4]["dup"])
        if closed:
            self.assertIsNone(rev[5]["dup"])
        # the threshold is a setting
        cfg = self.v.root / "system/config/settings.json"
        s = json.loads(cfg.read_text())
        s.setdefault("review", {})["duplicate_overlap"] = 1.01
        cfg.write_text(json.dumps(s))
        self.v.run(script="build_dashboard.py")
        data = json.loads((self.v.root / "dashboard.html").read_text().split('<script type="application/json" id="data">', 1)[1].split("</script>", 1)[0])
        self.assertIsNone(next(r for r in data["review"] if r["file"] == "proposed-dups.json" and r["ref"] == 1)["dup"])


class ReasonMenu(LiveBrowserCase):
    width, height = 1500, 1000

    @classmethod
    def load(cls, v):
        populate(v)
        v.run("migrate")
        open_ = next(r for r in v.rows("actions") if r["status"] == "Open" and r["project"] == "ABC")
        cls.dup = open_["id"]
        v.propose("menu", [pending(action(1, description=open_["description"])), pending(action(2, description="Plain one to reject")),
                           pending(action(3, description="Keyboard one to reject")), pending(action(4, description="Another for the bar")),
                           pending(action(5, description="Yet another for the bar"))])

    def staged(self):
        for d in ("system/staging", "system/staging/applied"):
            p = self.v.root / d / "proposed-menu.json"
            if p.exists():
                return {i["values"]["description"]: i for i in json.loads(p.read_text())["items"]}

    def n(self, text):
        return self.b.eval(f"REV.find(r=>r.rec.t.startsWith({text!r})).n")

    def test_a_spot_repeats_off_shows_no_looks_like(self):
        """BL-290: with Settings › General › AI drafts › Spot repeats off, neither the row nor the panel says Looks like."""
        b = self.b
        b.eval("go('review',null,{legacy:true})")
        b.wait("document.querySelector('#reviewBody tr[data-n]')")
        n1 = b.eval(f"(REV.find(r=>r.dup&&r.dup.id==={self.dup!r}&&!r.done)||{{}}).n")
        if not n1:
            self.skipTest("rejected by another test in this class's server")
        row = f'#reviewBody tr[data-n="{n1}"]'
        try:
            b.eval("S.drafting={...(S.drafting||{}),repeat:false}; renderReview()")
            b.wait(f"document.querySelector('{row}')")
            self.assertNotIn("Looks like", b.eval(f"document.querySelector('{row}').textContent"))
            self.assertIsNone(b.eval(f"document.querySelector('{row} .dupt')"))
            b.click(f"{row} td.title", count=2)
            b.wait("document.querySelector('#pkPropTop .pk-propline')")
            self.assertIsNone(b.eval("document.querySelector('#pkPropTop .rvdupnote')"))
            self.assertNotIn("Looks like", b.eval("document.getElementById('pkPropTop').textContent"))
            b.eval("closePanel()")
        finally:
            b.eval("S.drafting={...(S.drafting||{}),repeat:true}; renderReview()")
        b.wait(f"document.querySelector('{row} .dupt')")

    def test_the_menu_by_mouse_and_keyboard_and_r_alone(self):
        """BL-315 replaced BL-133's four-item menu with the seven reasons, Use each guess and No reason; R alone opens it too."""
        b = self.b
        b.eval("go('review',null,{legacy:true})")
        b.wait("document.querySelector('#reviewBody tr[data-n]')")
        n1 = self.n(b.eval(f"REV.find(r=>r.dup&&r.dup.id==={self.dup!r}).rec.t"))
        self.assertIn(f"Looks like {self.dup} (same project, open)", b.eval(f"document.querySelector('#reviewBody tr[data-n=\"{n1}\"]').textContent"))
        b.click(f'#reviewBody tr[data-n="{n1}"] [data-act=rr]')                         # the mouse
        b.wait("document.getElementById('rvReason')")
        self.assertEqual(b.eval("[...document.querySelectorAll('#rvReason [role=menuitem]')].map(s=>s.dataset.reason)"),
                         ["Not an action", "Duplicate", "Chatter", "Already done", "Wrong project", "Doesn't need tracking", "For another team", "guess", ""])
        self.assertIn(f"of {self.dup}", b.eval("document.querySelector('#rvReason [data-reason=Duplicate]').textContent"))
        b.click('#rvReason [data-reason="Duplicate"]')
        b.wait(f"!REV.some(r=>r.dup&&r.dup.id==={self.dup!r}&&!r.done)", 15)
        # keyboard: Shift+R on the cursor row, then 1
        n3 = self.n("Keyboard one")
        b.eval(f"RHL.clear(); RSEL=[...document.querySelectorAll('#reviewBody tr[data-n]')].findIndex(t=>+t.dataset.n==={n3}); renderReview(); document.activeElement.blur()")
        b.key("R", modifiers=8)
        b.wait("document.getElementById('rvReason') && document.getElementById('rvReason').contains(document.activeElement)")
        b.key("1")
        b.wait("!document.getElementById('rvReason')")
        # R alone opens the menu now; 0 is no reason
        b.wait("REV.some(r=>/^Plain one/.test(r.rec.t)&&!r.done)", 15)
        n2 = self.n("Plain one")
        b.eval(f"RHL.clear(); RSEL=[...document.querySelectorAll('#reviewBody tr[data-n]')].findIndex(t=>+t.dataset.n==={n2}); renderReview(); document.activeElement.blur()")
        b.key("r")
        b.wait("document.getElementById('rvReason') && document.getElementById('rvReason').contains(document.activeElement)")
        b.key("0")
        b.wait("!document.getElementById('rvReason')")
        # the bar: two at once, For another team
        b.wait("REV.filter(r=>/for the bar/.test(r.rec.t)&&!r.done).length===2", 15)
        ns = b.eval("REV.filter(r=>/for the bar/.test(r.rec.t)&&!r.done).map(r=>r.n)")
        b.eval(f"RHL.clear(); {json.dumps(ns)}.forEach(n=>RHL.add(n)); rvSyncChk(); renderReview()")
        b.wait("!document.getElementById('rvReason') && !document.getElementById('rvbar').hidden", 10)
        b.click("#bulkReject")
        b.wait("document.getElementById('rvReason')")
        b.key("7")
        b.wait("/Rejected 2 as For another team/.test(document.getElementById('rvresult').textContent)", 15)
        items = None
        for _ in range(100):
            items = self.staged()
            if all(items[k].get("applied") for k in items):
                break
            b.pump(0.1)
        self.assertEqual(next(i for i in items.values() if i.get("duplicate_of"))["duplicate_of"], self.dup)
        self.assertEqual(items["Keyboard one to reject"]["reject_reason"], "Not an action")
        self.assertNotIn("reject_reason", items["Plain one to reject"])
        self.assertEqual(items["Another for the bar"]["reject_reason"], "For another team")
        reasons = {r["reason"] for r in self.v.rows("rejected")}
        self.assertTrue({"Duplicate", "Not an action", "For another team"} <= reasons)
        b.eval("go('activity')")
        b.wait("document.querySelector('#v-activity')")
        b.wait("/rejected: Not an action/.test(document.getElementById('v-activity').textContent)", 10)

    def test_the_panel_offers_reject_as_duplicate(self):
        b = self.b
        b.eval("go('review',null,{legacy:true})")
        b.wait("document.querySelector('#reviewBody tr[data-n]')")
        n1 = b.eval(f"(REV.find(r=>r.dup&&r.dup.id==={self.dup!r}&&!r.done)||{{}}).n")
        if not n1:
            self.skipTest("rejected by the other test in this class's server")
        b.click(f'#reviewBody tr[data-n="{n1}"] td.title', count=2)
        b.wait("document.querySelector('#pkPropTop .rvdupnote')")                       # BL-177: the peek layout keeps the note
        self.assertIn(f"Reject as duplicate of {self.dup}", b.eval("document.querySelector('#pkPropTop .rvdupnote').textContent"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
