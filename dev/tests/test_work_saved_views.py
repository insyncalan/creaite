"""BL-131: Work's saved views: the unsaved marker, Update view and Save as new view, rename, reorder and delete in a view's menu,
More views, a default view per tab, and the built-in Chase view. A real browser against the real live server.

Run: python3 dev/tests/test_work_saved_views.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sqlite3
import sys
import unittest
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import work_data as W  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402

TODAY = date.today()


def ago(n):
    return (TODAY - timedelta(days=n)).isoformat()


class Views(LiveBrowserCase):
    width, height = 1500, 1000

    @classmethod
    def load(cls, v):
        populate(v)
        W.load(v)
        with closing(sqlite3.connect(v.root / "system/tracker.db")) as con:     # half the items have gone quiet
            for t in ("actions", "raid", "decisions"):
                for i, (id_,) in enumerate(con.execute(f"SELECT id FROM {t} ORDER BY id").fetchall()):
                    con.execute(f"UPDATE {t} SET updated_at=? WHERE id=?", (ago(20 if i % 2 else 1) + " 09:00:00", id_))
            con.commit()

    def setUp(self):
        super().setUp()
        self.b.eval("localStorage.clear()")

    def open_work(self, tab="actions"):
        b = self.b
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tbody tr, #workTbl .empty')")
        if b.eval("WT") != tab:
            b.click(f'#wtabs button[data-t="{tab}"]')
            b.wait(f"WT==='{tab}'")
        return b

    def ids(self):
        return sorted(self.b.eval("[...document.querySelectorAll('#workTbl tbody tr[data-row]')].map(r=>r.dataset.row)"))

    def saved(self, tab="actions"):
        return json.loads((self.v.root / "system/config/settings.json").read_text())["work"]["saved_views"].get(tab, [])

    def save_as(self, name):
        b = self.b
        b.click("#saveView")
        b.click("#viewName")
        b.type(name)
        b.click("#viewSave")
        b.wait(f"WVIEW==='saved:{name}'", 5)

    def test_the_marker_update_view_and_save_as_new(self):
        b = self.open_work()
        b.eval("applyFilters({st:['Open','Delayed'],pr:['Urgent']}); workChanged()")
        self.save_as("Urgent")
        self.assertFalse(b.eval("!!document.querySelector('#wviews .vdot')"))
        b.eval("setOf('pr').add('High'); workChanged()")                                   # a change: the dot, and both buttons
        self.assertTrue(b.eval("!!document.querySelector('#wviews [data-wv=\"saved:Urgent\"] .vdot')"))
        self.assertIn("not saved", b.eval("document.querySelector('#wviews [data-wv=\"saved:Urgent\"]').textContent"))   # words too
        self.assertEqual(b.eval("[!!document.getElementById('updView'), document.getElementById('saveView').textContent]"), [True, "Save as new view"])
        self.assertIn("vb=saved%3AUrgent", b.eval("location.hash"))
        b.reload("typeof go==='function' && LIVE")                                    # the marker survives a reload
        b.wait("document.querySelector('#workTbl tbody tr')")
        self.assertTrue(b.eval("!!document.querySelector('#wviews [data-wv=\"saved:Urgent\"] .vdot')"))
        b.click("#updView")
        b.wait("WVIEW==='saved:Urgent'", 5)
        self.assertEqual(self.saved()[0]["f"]["pr"], ["High", "Urgent"])
        self.assertFalse(b.eval("!!document.querySelector('#wviews .vdot')"))
        # the display is part of a saved view: a new order marks it changed too
        b.eval("SORT.actions={col:'t',dir:'asc'}; renderWork()")
        self.assertTrue(b.eval("!!document.querySelector('#wviews [data-wv=\"saved:Urgent\"] .vdot')"))
        self.save_as("Urgent by title")
        self.assertEqual([v["name"] for v in self.saved()], ["Urgent", "Urgent by title"])
        self.assertEqual(self.saved()[1]["o"], {"col": "t", "dir": "asc"})
        self.assertEqual(self.saved()[0]["f"]["pr"], ["High", "Urgent"])            # the first is untouched

    def test_a_built_in_view_cannot_be_overwritten(self):
        b = self.open_work()
        b.eval("setOf('pr').add('Low'); workChanged()")
        self.assertTrue(b.eval("!!document.querySelector('#wviews [data-wv=\"open\"] .vdot')"))
        self.assertFalse(b.eval("!!document.getElementById('updView')"))
        self.assertEqual(b.eval("document.getElementById('saveView').textContent"), "Save as new view")
        self.assertFalse(b.eval("!!document.querySelector('#wviews [data-vmenu=\"All open\"]')"))   # no menu on a built-in view
        b.eval("SORT.actions={col:'t',dir:'asc'}; setOf('pr').clear(); workChanged()")       # a built-in view is filters only
        self.assertEqual(b.eval("WVIEW"), "open")

    def test_rename_reorder_delete_and_the_default_survive_a_reload(self):
        b = self.open_work()
        for name, pr in (("First", "Urgent"), ("Second", "High"), ("Third", "Low")):
            b.eval(f"applyFilters({{st:['Open'],pr:['{pr}']}}); workChanged()")
            self.save_as(name)
        b.click('#wviews [data-vmenu="Second"]')
        b.wait("document.getElementById('vmenuPop')")
        self.assertEqual(b.eval("document.activeElement.dataset.vm"), "rename")
        b.click('#vmenuPop [data-vm="rename"]')
        b.wait("document.getElementById('vrename')")
        b.eval("document.getElementById('vrename').select()")
        b.type("Highs")
        b.key("Enter")
        b.wait("SAVED.actions.some(v=>v.name==='Highs')", 5)
        b.click('#wviews [data-vmenu="Third"]')
        b.click('#vmenuPop [data-vm="up"]')
        b.wait("SAVED.actions[1].name==='Third'", 5)
        self.assertEqual([v["name"] for v in self.saved()], ["First", "Third", "Highs"])
        # the default view for Actions, set on the Settings page
        b.eval("go('settings','views')")
        b.wait("document.querySelector('select[data-k=\"defActionView\"]')")
        self.assertIn("saved:Highs", b.eval("[...document.querySelectorAll('select[data-k=\"defActionView\"] option')].map(o=>o.value)"))
        self.assertTrue(b.eval("!!document.querySelector('select[data-k=\"defDecisionView\"]')"))
        b.eval("(()=>{ const s=document.querySelector('select[data-k=\"defActionView\"]'); s.value='saved:Highs'; s.dispatchEvent(new Event('change',{bubbles:true})); })()")
        b.wait("JSON.stringify(S.defActionView)==='\"saved:Highs\"'", 5)
        b.pump(0.5)
        self.assertEqual(json.loads((self.v.root / "system/config/settings.json").read_text())["defaults"]["actions_status_filter"], "saved:Highs")
        b.goto(self.base + "/")
        b.wait("typeof go==='function' && LIVE")
        self.open_work()
        self.assertEqual(b.eval("WVIEW"), "saved:Highs")                              # opens with the default
        self.assertEqual(b.eval("[...document.querySelectorAll('#wviews .vwrap [data-wv^=\"saved:\"]')].map(x=>x.dataset.wv)"), ["saved:First", "saved:Third", "saved:Highs"])
        # renaming the default keeps it the default
        b.click('#wviews [data-vmenu="Highs"]')
        b.click('#vmenuPop [data-vm="rename"]')
        b.eval("document.getElementById('vrename').select()")
        b.type("High ones")
        b.key("Enter")
        b.wait("SAVED.actions.some(v=>v.name==='High ones')", 5)
        b.pump(0.3)
        self.assertEqual(json.loads((self.v.root / "system/config/settings.json").read_text())["defaults"]["actions_status_filter"], "saved:High ones")
        b.click('#wviews [data-vmenu="First"]')
        b.click('#vmenuPop [data-vm="delete"]')
        b.wait("!SAVED.actions.some(v=>v.name==='First')", 5)
        self.assertEqual([v["name"] for v in self.saved()], ["Third", "High ones"])
        # the Decisions tab's default
        b.eval("go('settings','views')")
        b.wait("document.querySelector('select[data-k=\"defDecisionView\"]')")
        b.eval("(()=>{ const s=document.querySelector('select[data-k=\"defDecisionView\"]'); s.value='pending'; s.dispatchEvent(new Event('change',{bubbles:true})); })()")
        b.wait("S.defDecisionView==='pending'", 5)
        b.pump(0.5)
        self.assertEqual(json.loads((self.v.root / "system/config/settings.json").read_text())["defaults"]["decisions_view"], "pending")
        b.goto(self.base + "/")
        b.wait("typeof go==='function' && LIVE")
        self.open_work("decisions")
        self.assertEqual(b.eval("WVIEW"), "pending")

    def test_overflow_keeps_the_view_in_use_in_sight(self):
        b = self.open_work()
        b.click("#vmore")                                                                            # BL-316: the menu is drawn when it opens
        self.assertTrue(b.eval("!!document.querySelector('#vmoreMenu [data-wv=\"overdue\"]')"))     # Overdue sits under More views
        b.key("Escape")
        for n in range(6):
            b.eval(f"applyFilters({{st:['Open'],pr:['Urgent'],due:['{['overdue','soon','none','later'][n % 4]}'],cv:['{['yes','no'][n // 4]}']}}); workChanged()")
            self.save_as(f"A longer saved view name {n}")
        b.resize(900)
        b.pump(0.3)
        b.eval("renderWork()")
        self.assertLessEqual(b.eval("document.getElementById('wviews').scrollWidth"), b.eval("document.getElementById('wviews').clientWidth") + 1)   # never wraps or spills
        b.click("#vmore")
        hidden = b.eval("[...document.querySelectorAll('#vmoreMenu [data-wv]')].map(x=>x.dataset.wv)")
        self.assertIn("saved:A longer saved view name 0", hidden)
        self.assertIn(f"More views ({len(hidden)})", b.eval("document.getElementById('vmore').textContent"))
        b.click('#vmoreMenu [data-wv="saved:A longer saved view name 0"]')
        b.wait("WVIEW==='saved:A longer saved view name 0'")
        self.assertTrue(b.eval("(()=>{ const c=document.querySelector('#wviews .vwrap [data-wv=\"saved:A longer saved view name 0\"]'); const r=c.getBoundingClientRect(), w=document.getElementById('wviews').getBoundingClientRect(); return c.getAttribute('aria-pressed')==='true'&&r.right<=w.right+1&&r.width>0; })()"))

    def test_chase_on_each_tab(self):
        quiet = lambda r: (TODAY - date.fromisoformat(r["updated_at"][:10])).days >= 7  # noqa: E731
        for tab, opened, who in (("actions", ("Open", "Delayed"), "owner"), ("raid", ("Open",), "owner"), ("decisions", ("Pending",), "made_by")):
            b = self.open_work(tab)
            b.click('#wviews .vwrap [data-wv="chase"]')
            b.wait("WVIEW==='chase'")
            rows = self.v.rows(tab)
            want = sorted(r["id"] for r in rows if (r.get("status") or "Pending") in opened and not W.is_me(r[who]) and quiet(r))
            self.assertEqual(self.ids(), want, tab)
            self.assertEqual(b.eval("document.querySelector('#wviews .vwrap [data-wv=\"chase\"]').textContent"), "Chase")
        b = self.open_work("raid")
        self.assertTrue(b.eval("!!document.querySelector('#wviews [data-wv=\"nomit\"]')"))              # RAID keeps No response yet


if __name__ == "__main__":
    unittest.main(verbosity=2)
