"""Shared fixture for the BL-164 Activity tests (test_activity_undo.py, test_activity_undo_page.py, test_activity_undo_select.py): the seed, the Db helper and the Activity page base."""
import json
import os
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

os.environ.setdefault("CREAITE_NO_LAUNCH", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import action  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402

META, SHIFT = 4, 8


def upd(n, table, id_, **changes):
    return {"n": n, "op": "update", "table": table, "id": id_, "changes": changes, "decision": "approved"}


def seed(v):
    """Three actions and a risk, then three later applies that each change one of them."""
    v.run("init")
    v.propose("a1", [action(1, description="Send revised SOW"), action(2, description="Book the UAT room"),
                     action(3, description="Order test licences"),
                     {"n": 4, "op": "new", "table": "raid", "decision": "approved",
                      "values": {"project": "ABC", "type": "Risk", "description": "Data access late", "impact": "High",
                                 "likelihood": "Medium", "raised": "2026-10-01", "source": "Alan (cx-edit)"}}])
    v.run("apply")
    v.propose("a2", [upd(1, "actions", "ABC-A-001", status="Closed")])
    v.run("apply")
    v.propose("a3", [upd(1, "actions", "ABC-A-002", owner="Sara Example")])
    v.run("apply")
    v.propose("a4", [upd(1, "actions", "ABC-A-003", due_date="2026-11-20", priority="High")])
    v.run("apply")


class Db:
    def __init__(self, v):
        self.v = v

    def q(self, sql, *a):
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            con.row_factory = sqlite3.Row
            return [dict(r) for r in con.execute(sql, a)]

    def rowid(self, item, field, op="update"):
        return self.q("SELECT rowid FROM change_log WHERE item_id = ? AND field = ? AND op = ? ORDER BY rowid DESC LIMIT 1",
                      item, field, op)[0]["rowid"]

    def item(self, table, id_):
        r = self.q(f"SELECT * FROM {table} WHERE id = ?", id_)
        return r[0] if r else None



class ActivityBase(LiveBrowserCase):
    width, height = 1400, 900

    @classmethod
    def load(cls, v):
        seed(v)
        v.propose("a5", [upd(1, "actions", "ABC-A-001", owner="Omar Ali", priority="Urgent")])   # the latest apply
        v.run("apply")

    def go_activity(self, hash_=""):
        b = self.b
        b.eval(f"go('activity')" if not hash_ else f"location.hash={json.dumps(hash_)}")
        b.wait("document.querySelector('#actTbl tbody tr')")

    def rows(self):
        return self.b.eval("[...document.querySelectorAll('#actTbl tbody tr')].map(t=>t.textContent)")

    def count(self):
        return self.b.eval("document.getElementById('actCount').textContent")

    def sel_rows(self):
        return self.b.eval("[...document.querySelectorAll('#actTbl tbody tr[data-row].hl')].map(t=>t.dataset.row)")

    def pick(self, rowids):
        self.b.eval(f"HL.clear(); {json.dumps(rowids)}.forEach(r=>HL.set('r'+r,'act')); actPaint()")

    def latest_rows(self):
        return self.b.eval("ACT.filter(a=>a.rowid&&a.apply_id===D.latest_apply).map(a=>a.rowid)")

    def older_rows(self):
        return self.b.eval("""['ABC-A-001|status','ABC-A-002|owner','ABC-A-003|due_date'].map(k=>{ const [id,f]=k.split('|');
          return ACT.find(a=>a.rowid&&a.id===id&&a.apply_id!==D.latest_apply&&a.change.startsWith(f.replace('_',' ')+':')).rowid; })""")
