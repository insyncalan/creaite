"""BL-130: the Work filters' field picker, "is not" on every field, and the new fields (Stale, Last updated, Raised, Milestone).
A real browser against the real live server; the new fields are checked against Python.

Run: python3 dev/tests/test_work_filter_picker.py   (needs Google Chrome; skipped otherwise)
"""
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
STALE = 7


def ago(n):
    return (TODAY - timedelta(days=n)).isoformat()


class Picker(LiveBrowserCase):
    shared_server = True                    # read-only: the data is changed once, before the server starts
    width, height = 1500, 1000

    @classmethod
    def load(cls, v):
        populate(v)
        W.load(v)
        with closing(sqlite3.connect(v.root / "system/tracker.db")) as con:     # some items quiet for a while, some raised lately, some on a milestone
            for t in ("actions", "raid", "decisions"):
                ids = [r[0] for r in con.execute(f"SELECT id FROM {t} ORDER BY id")]
                for i, id_ in enumerate(ids):
                    con.execute(f"UPDATE {t} SET updated_at=? WHERE id=?", (ago([2, 10, 20, 40][i % 4]) + " 09:00:00", id_))
                    if t != "decisions":
                        con.execute(f"UPDATE {t} SET raised=? WHERE id=?", (ago([3, 12, 25, 60][i % 4]), id_))
            for i, (id_, p) in enumerate(con.execute("SELECT id, project FROM actions ORDER BY id").fetchall()):
                if p == "ABC" and i % 3 == 0:
                    con.execute("UPDATE actions SET milestone=? WHERE id=?", ("ABC-M-002" if i % 2 else "ABC-M-001", id_))
            con.commit()

    def setUp(self):
        super().setUp()
        self.b.eval("localStorage.clear()")
        W.closed_open(self.b)            # #241 b: these tests count closed rows too; Closed is folded only where nothing is saved

    def open_work(self, tab="actions", none=True):
        b = self.b
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tbody tr')")
        if b.eval("WT") != tab:
            b.click(f'#wtabs button[data-t="{tab}"]')
            b.wait(f"WT==='{tab}'")
        if none:
            b.eval("clearAllFilters(); WQ=''; workChanged()")
        return b

    def ids(self):
        return sorted(self.b.eval("[...document.querySelectorAll('#workTbl tbody tr[data-row]')].map(r=>r.dataset.row)"))

    def pick(self, k):
        b = self.b
        if not b.eval("document.getElementById('moreMenu').classList.contains('on')"):
            b.click("#moreBtn")
        b.click(f'#moreMenu [data-fpk="{k}"]')
        b.wait(f"FPK==={k!r}")

    def test_is_and_is_not_on_every_field_of_every_tab(self):
        for tab in ("actions", "raid", "decisions"):
            b = self.open_work(tab)
            everything = self.ids()
            fields = b.eval("defs().map(d=>d[0])")
            for k in fields:
                self.pick(k)
                vals = b.eval(f"[...document.querySelectorAll('#moreMenu input[data-fk=\"{k}\"]')].filter(i=>+i.closest('label').querySelector('small').textContent>0).map(i=>i.value)")
                if not vals:
                    continue
                v = vals[0]
                b.click(f'#moreMenu input[data-fk="{k}"][value="{v}"]')
                inc = self.ids()
                self.assertTrue(inc, (tab, k, v))
                b.click('#moreMenu [data-neg="1"]')
                b.wait(f"NEG.has({k!r})")
                exc = self.ids()
                self.assertFalse(set(inc) & set(exc), (tab, k, v))                     # none of the ticked values
                self.assertEqual(sorted(inc + exc), everything, (tab, k, v))           # together, everything
                chip = b.eval("document.querySelector('#wapplied .fchip.neg').textContent")
                self.assertIn("not", chip)                                             # words, not only a tint
                self.assertEqual(b.eval("document.getElementById('fpResult').textContent"), f"Result: {len(exc)} of {len(everything)} shown")
                b.click('#moreMenu [data-neg="0"]')
                b.wait(f"!NEG.has({k!r})")
                self.assertEqual(self.ids(), inc)
                b.eval("clearAllFilters(); workChanged()")
            b.click("#v-work h1")

    def test_the_toolbar_menus_have_is_not_too(self):
        b = self.open_work()
        b.click("#ownBtn")
        b.click('#ownMenu [data-neg="1"]')
        b.click('#ownMenu [data-ma="me"]')
        b.pump(0.2)
        self.assertEqual(b.eval("document.getElementById('ownBtn').textContent"), "Not Me")
        mine = {r["id"] for r in self.v.rows("actions") if W.is_me(r["owner"])}
        self.assertFalse(set(self.ids()) & mine)
        self.assertEqual(len(self.ids()), len(self.v.rows("actions")) - len(mine))

    def test_an_exclusion_saves_and_restores_in_a_view_and_the_address(self):
        b = self.open_work()
        b.eval("applyFilters({st:['Open','Delayed'],'!o':['@me']}); workChanged()")
        want = self.ids()
        self.assertIn("&!o=%40me", b.eval("location.hash"))
        b.eval("(async()=>{ await saveView('Others'); })()")
        b.wait("SAVED.actions.some(v=>v.name==='Others')")
        self.assertEqual(b.eval("SAVED.actions.find(v=>v.name==='Others').f"), {"st": ["Delayed", "Open"], "!o": ["@me"]})
        b.reload("typeof go==='function' && LIVE")
        b.wait("document.querySelector('#workTbl tbody tr[data-row]')")
        self.assertEqual(self.ids(), want)
        self.assertTrue(b.eval("NEG.has('o')"))
        b.click('#wviews [data-wv="open"]')
        b.click('#wviews [data-wv="saved:Others"]')
        b.pump(0.2)
        self.assertEqual(self.ids(), want)

    def test_older_views_and_addresses_load_unchanged(self):
        b = self.b
        b.goto(self.base + "/#work=actions&st=Open&o=Sara%20Example")
        b.wait("typeof go==='function' && LIVE && document.querySelector('#workTbl tbody tr')")
        want = sorted(r["id"] for r in self.v.rows("actions") if r["status"] == "Open" and r["owner"] == "Sara Example")
        self.assertEqual(self.ids(), want)
        self.assertFalse(b.eval("NEG.size"))
        self.assertFalse(b.eval("!!document.querySelector('#wapplied .fchip.neg')"))
        b.eval("SAVED.actions=[{name:'Old',f:{st:['Open'],o:['Sara Example']},lay:'list',g:'due'}]; applyView('saved:Old'); renderWork()")
        self.assertEqual(self.ids(), want)

    def test_the_new_fields_filter_correctly(self):
        rows = {t: self.v.rows(t) for t in ("actions", "raid", "decisions")}
        def opened(t, r):
            return r["status"] in (("Open", "Delayed") if t == "actions" else ("Open",) if t == "raid" else ("Pending",))
        def age(s):
            return (TODAY - date.fromisoformat(s[:10])).days
        for t in ("actions", "raid", "decisions"):
            b = self.open_work(t)
            b.eval("applyFilters({sl:['yes']}); workChanged()")
            self.assertEqual(self.ids(), sorted(r["id"] for r in rows[t] if opened(t, r) and age(r["updated_at"]) >= STALE), t)
            if t == "decisions":
                self.assertFalse(b.eval("defs().some(d=>d[0]==='lu'||d[0]==='rd')"))      # a decision has its Date
                continue
            for n in (7, 14, 30):
                b.eval(f"applyFilters({{lu:['{n}']}}); workChanged()")
                self.assertEqual(self.ids(), sorted(r["id"] for r in rows[t] if age(r["updated_at"]) <= n), (t, "lu", n))
                b.eval(f"applyFilters({{rd:['{n}']}}); workChanged()")
                self.assertEqual(self.ids(), sorted(r["id"] for r in rows[t] if r["raised"] and age(r["raised"]) <= n), (t, "rd", n))
            b.eval(f"applyFilters({{rr:['{ago(13)}','{ago(2)}']}}); workChanged()")
            self.assertEqual(self.ids(), sorted(r["id"] for r in rows[t] if r["raised"] and ago(13) <= r["raised"] <= ago(2)), (t, "rr"))
            self.assertIn("Raised:", b.eval("document.getElementById('wapplied').textContent"))
        b = self.open_work("actions")
        b.eval("applyFilters({ms:['ABC-M-001']}); workChanged()")
        self.assertEqual(self.ids(), sorted(r["id"] for r in rows["actions"] if r["milestone"] == "ABC-M-001"))
        b.eval("applyFilters({ms:['none']}); workChanged()")
        self.assertEqual(self.ids(), sorted(r["id"] for r in rows["actions"] if not r["milestone"]))
        b.eval("PROJF.add('ABC'); renderWork()")                                       # one project: only its milestones are offered
        self.pick("ms")
        self.assertEqual(sorted(b.eval("[...document.querySelectorAll('#moreMenu input[data-fk=ms]')].map(i=>i.value)")), ["ABC-M-001", "ABC-M-002", "none"])

    def test_the_picker_search_the_f_key_and_keyboard(self):
        b = self.open_work()
        b.click("#v-work h1")
        b.key("f")
        b.wait("document.getElementById('moreMenu').classList.contains('on') && document.activeElement.id==='fpq'")
        self.assertEqual(b.eval("document.getElementById('moreMenu').getAttribute('role')"), "dialog")
        self.assertEqual(b.eval("document.querySelector('#moreMenu .fplist').getAttribute('role')"), "listbox")
        b.type("sta")
        b.wait("document.querySelectorAll('#moreMenu [data-fpk]').length===2")
        self.assertEqual(b.eval("[...document.querySelectorAll('#moreMenu [data-fpk]')].map(x=>x.dataset.fpk)"), ["st", "sl"])
        self.assertEqual(b.eval("document.activeElement.id"), "fpq")
        b.key("Enter")
        b.wait("document.activeElement && document.activeElement.closest('#moreMenu .fpr')")
        self.assertEqual(b.eval("document.querySelector('#moreMenu [aria-selected=true]').dataset.fpk"), "st")
        self.assertEqual(b.eval("[...document.querySelectorAll('#moreMenu [data-neg]')].map(x=>x.getAttribute('aria-pressed'))"), ["true", "false"])
        b.type("x")
        b.key("Escape")
        b.wait("!document.getElementById('moreMenu').classList.contains('on')")
        self.assertEqual(b.eval("document.activeElement.id"), "moreBtn")
        b.eval("FPQ=''")
        self.assertEqual(b.errors, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
