"""BL-132: Work's empty state (the filters named, what removing each alone would show, Remove, Include closed items, Clear all
filters) and the count of what is hidden, in a real browser against the real live server, checked against Python.

Run: python3 dev/tests/test_work_empty_state.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import work_data as W  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402


class EmptyState(LiveBrowserCase):
    shared_server = True
    width, height = 1500, 1000

    @classmethod
    def load(cls, v):
        populate(v)
        W.load(v)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rows = cls.v.rows("actions")

    def setUp(self):
        super().setUp()
        b = self.b
        b.eval("localStorage.clear(); go('work')")
        b.wait("document.querySelector('#workTbl tbody tr')")

    def filt(self, f, q=""):
        self.b.eval(f"clearAllFilters(); applyFilters({f!r}); WQ={q!r}; workChanged()")
        self.b.pump(0.1)

    def relax(self):
        return self.b.eval("[...document.querySelectorAll('#workTbl .empty .relax > div')].map(d=>[d.querySelector('span').textContent, +d.querySelector('.sub').textContent.split(' ')[0]])")

    def oracle(self, **kw):
        return len(W.expected_ids(self.rows, "actions", **kw))

    def test_one_two_and_three_filters(self):
        cases = [({"st": ["Open"], "pr": ["Low"], "o": ["Jane Doe"]}, {"status": {"Open"}, "priority": {"Low"}, "owner": {"Jane Doe"}}),
                 ({"pr": ["Low"], "o": ["Jane Doe"]}, None),
                 ({"o": ["Nobody Here"]}, {"owner": {"Nobody Here"}})]
        for f, kw in cases:
            self.filt(f)
            if self.b.eval("rows().length"):
                continue                                                      # this data doesn't make that one empty
            n = len(f)
            head = self.b.eval("document.querySelector('#workTbl .empty h2').textContent")
            self.assertEqual(head, "Nothing matches this filter" if n == 1 else f"Nothing matches these {n} filters")
            got = dict(self.relax())
            if kw:
                names = {"st": ("status", "Status"), "pr": ("priority", "Priority"), "o": ("owner", "Owner")}
                for k in f:
                    arg, lab = names[k]
                    rest = {a: v for a, v in kw.items() if a != arg}
                    label = next(x for x in got if x.startswith(f"Remove {lab}"))
                    self.assertEqual(got[label], self.oracle(**rest), (f, k))
        # three filters, none of them alone enough
        self.filt({"st": ["Open"], "pr": ["Low"], "o": ["Jane Doe"]})
        self.assertEqual(len([r for r in self.relax() if r[0].startswith("Remove")]), 3)

    def test_remove_restores_items_and_clear_all(self):
        self.filt({"st": ["Open"], "o": ["Nobody Here"]})
        self.assertEqual(self.b.eval("rows().length"), 0)
        self.b.click('#workTbl .empty [data-relax="o"]')
        self.b.wait("rows().length>0")
        self.assertEqual(self.b.eval("rows().length"), self.oracle(status={"Open"}))
        self.filt({"st": ["Open"], "o": ["Nobody Here"]}, q="zzqq")
        self.b.click('#workTbl .empty [data-relax="all"]')
        self.b.wait("rows().length>0")
        self.assertEqual(self.b.eval("[rows().length, WQ, NEG.size]"), [len(self.rows), "", 0])

    def test_include_closed_items(self):
        closed = next(r for r in self.rows if r["status"] == "Closed" and r["description"].startswith("Action number"))
        q = closed["id"]
        self.filt({"st": ["Open", "Delayed"]}, q=q)
        self.assertEqual(self.b.eval("rows().length"), 0)
        got = dict(self.relax())
        self.assertEqual(got.get("Include closed items"), self.oracle(query=q))
        self.b.click('#workTbl .empty [data-relax="closed"]')
        self.b.wait("rows().length>0")
        self.assertIn(closed["id"], self.b.eval("rows().map(x=>x.id)"))
        self.filt({"st": ["Open", "Delayed"]}, q="zzqqxx")                       # nothing closed matches: no Include closed
        self.assertNotIn("Include closed items", dict(self.relax()))
        self.assertIn("zzqqxx", self.b.eval("document.querySelector('#workTbl .empty').textContent"))

    def test_the_count_line_on_both_layouts_and_the_announcement(self):
        b = self.b
        self.filt({"st": ["Open", "Delayed"]})
        n_closed = sum(1 for r in self.rows if r["status"] in ("Closed", "Cancelled"))
        self.assertEqual(b.eval("document.getElementById('whidden').textContent"), f" · {n_closed} closed hidden")
        self.assertEqual(b.eval("document.getElementById('wlive').textContent"), f"Showing {len(self.rows) - n_closed} of {len(self.rows)} · {n_closed} closed hidden")
        self.assertEqual(b.eval("document.getElementById('wlive').getAttribute('aria-live')"), "polite")
        self.filt({"o": ["Jane Doe"]})                                            # another filter's exclusions are not "hidden"
        self.assertEqual(b.eval("document.getElementById('whidden').textContent"), "")
        # the Board: what the Closed column's window leaves out
        b.click('#wlay [data-lay="board"]')
        b.eval("(()=>{ const s=document.getElementById('wgrp'); s.value='due'; s.dispatchEvent(new Event('change',{bubbles:true})); })()")
        self.filt({})
        b.eval("S.boardClosedDays=-5; renderWork()")                              # every closed item is outside the window
        self.assertEqual(b.eval("document.getElementById('whidden').textContent"), f" · {n_closed} closed hidden")
        b.eval("S.boardClosedDays=14; renderWork()")
        self.assertEqual(b.eval("document.getElementById('whidden').textContent"), "")
        self.filt({"o": ["Nobody Here"]})
        self.assertIn("Nothing matches this filter", b.eval("document.querySelector('#workBoard .empty').textContent"))
        self.assertTrue(b.eval("document.getElementById('wlive').textContent.startsWith('Nothing matches this filter')"))
        b.click('#workBoard .empty [data-relax="o"]')
        b.wait("document.querySelector('#workBoard .bcard')")


if __name__ == "__main__":
    unittest.main(verbosity=2)
