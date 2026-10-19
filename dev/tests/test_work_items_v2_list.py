"""#241 A: Work items v2, the list. Row density (Compact, one line with the ID beside the title, by default where nothing
is saved, Comfortable on request, row height only, the Board untouched), the status and priority marks beside the existing columns (words for screen readers; the Status and
Priority columns stay, in Display too), the client-visible tag, and the List's default grouping (Actions by due with Closed
last, RAID by priority, Decisions by status) only where nothing is saved, with an explicit "no grouping" kept as a choice.
A real browser against the real live server.

Run: python3 dev/tests/test_work_items_v2_list.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import work_data as W  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402

READY = "typeof go==='function' && LIVE"
DUE_GROUPS = ["Overdue", "This week", "Next week", "Later", "No date", "Closed"]


class ListV2(LiveBrowserCase):
    width, height = 1500, 1000
    shared_server = True            # nothing here changes the data

    @classmethod
    def load(cls, v):
        populate(v)
        W.load(v)

    def setUp(self):
        super().setUp()
        self.b.eval("localStorage.clear()")
        self.b.reload(READY)

    def open_work(self, tab="actions"):
        b = self.b
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tbody tr, #workTbl .empty, #workBoard .bcol')")
        if b.eval("WT") != tab:
            b.click(f'#wtabs button[data-t="{tab}"]')
            b.wait(f"WT==='{tab}'")
        return b

    def groups(self):
        return self.b.eval("[...document.querySelectorAll('#workTbl tr.wgh.lv1')].map(r=>r.querySelector('.wgn').textContent)")

    def heights(self):
        return self.b.eval("[...document.querySelectorAll('#workTbl tbody tr[data-row]')].slice(0,12).map(r=>Math.round(r.getBoundingClientRect().height))")

    def widths(self):
        return self.b.eval("[...document.querySelectorAll('#workTbl thead th[data-col]')].map(t=>[t.dataset.col,Math.round(t.getBoundingClientRect().width)])")

    def one_line(self):
        # for each of the first rows: is the ID on the title's line, after the title (its middle inside the title line, to the right)
        return self.b.eval("""[...document.querySelectorAll('#workTbl tbody tr[data-row]')].slice(0,12).map(r=>{
          const td=r.querySelector('td.title'), id=td.querySelector(':scope > .x .rowid').getBoundingClientRect(), rg=document.createRange();
          rg.setStart(td,0); rg.setEndBefore(td.querySelector(':scope > .x'));
          const q=[...rg.getClientRects()].filter(c=>c.width>0&&c.height>0), last=q.reduce((a,c)=>c.bottom>a.bottom?c:a,q[0]), mid=(id.top+id.bottom)/2;
          return mid>last.top&&mid<last.bottom&&id.left>=last.right; })""")

    def stored(self, k):
        v = self.b.eval(f"localStorage.getItem({k!r})")
        return None if v is None else json.loads(v)

    def choose(self, sel, value):
        self.b.eval(f"(()=>{{ const s=document.querySelector({sel!r}); s.value={value!r}; s.dispatchEvent(new Event('change',{{bubbles:true}})); }})()")
        self.b.pump(0.2)

    # ── density ──
    def test_compact_by_default_comfortable_on_request_row_height_only(self):
        b = self.open_work()
        self.assertEqual(b.eval("document.getElementById('wdens').nextElementSibling.id"), "wlay")        # beside the list and board icons
        self.assertEqual(b.eval("document.getElementById('workWrap').classList.contains('cmp')"), True)
        self.assertEqual(b.eval("document.querySelector('#wdens [data-dens=cmp]').getAttribute('aria-pressed')"), "true")
        self.assertIsNone(self.stored("creaite-density"))                                             # nothing written unasked
        # 40 px rows (a row whose title wraps grows), one line: the ID beside the title, as in the approved mockup (Alan's decision
        # a, 19-10-2026; it was two tighter lines). The cells keep the same content and sizing CSS, so the same widths
        self.assertTrue(all(h <= 41 for h in self.heights()), self.heights())
        b.wait("document.querySelector('#workTbl tr[data-row] td.title > .x.xup')")
        lines = self.one_line()
        self.assertTrue(lines and all(lines), lines)                                                  # beside the title, on its line
        compact = self.widths()
        b.click('#wdens [data-dens="cmf"]')
        b.wait("document.getElementById('workWrap').classList.contains('cmf')")
        self.assertTrue(all(h >= 57 for h in self.heights()), self.heights())
        b.wait("!document.querySelector('#workTbl .x.xup')")                                         # two lines again
        self.assertFalse(any(self.one_line()))
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('#workTbl tr[data-row] td.title > .x')).lineHeight"), "20px")
        self.assertEqual(self.widths(), compact)                                                     # row height only, never a width
        self.assertEqual(self.stored("creaite-density"), "cmf")
        b.reload(READY)
        self.open_work()
        self.assertTrue(b.eval("document.getElementById('workWrap').classList.contains('cmf')"))      # remembered
        self.assertEqual(b.eval("document.querySelector('#wdens [data-dens=cmf]').getAttribute('aria-pressed')"), "true")
        b.click('#wlay [data-lay="board"]')                                                           # the Board is untouched
        b.wait("!document.getElementById('workBoard').hidden")
        self.assertTrue(b.eval("document.getElementById('wdens').hidden"))
        self.assertEqual(b.eval("document.querySelectorAll('#workBoard .cmp, #workBoard .cmf, #workBoard .wkm, #workBoard .tg').length"), 0)

    # ── marks and tags ──
    def test_status_and_priority_marks_beside_the_columns_with_words(self):
        b = self.open_work()
        rows = b.eval("""[...document.querySelectorAll('#workTbl tbody tr[data-row]')].map(r=>({id:r.dataset.row,
          marks:r.querySelectorAll('td.title .wkm svg').length, words:(r.querySelector('td.title .wkm .vh')||{}).textContent,
          st:r.querySelector('td[data-f=st]').firstChild.textContent.trim(), pr:r.querySelector('td[data-f=pr]').firstChild.textContent.trim()}))""")
        self.assertTrue(rows)
        for r in rows:
            self.assertEqual(r["marks"], 2, r)
            self.assertEqual(r["words"], f"{r['st']}, {r['pr']} priority: ", r)
        self.assertEqual(b.eval("[...document.querySelectorAll('#workTbl thead th[data-col]')].map(t=>t.dataset.col)"), ["t", "o", "due", "pr", "st"])
        b.click("#dispBtn")
        self.assertTrue(b.eval("document.getElementById('dprop-st').checked && document.getElementById('dprop-pr').checked"))
        b.click("#dprop-pr")                                                                          # hiding the column keeps the mark
        b.wait("!document.querySelector('#workTbl thead th[data-col=pr]')")
        self.assertEqual(b.eval("document.querySelectorAll('#workTbl tbody tr[data-row] td.title .wkm svg').length"), 2 * len(rows))
        self.open_work("decisions")                                                                    # a decision has a status only
        self.assertTrue(b.eval("[...document.querySelectorAll('#workTbl tbody tr[data-row]')].every(r=>r.querySelectorAll('td.title .wkm svg').length===1)"))

    def test_client_visible_items_carry_a_tag(self):
        b = self.open_work()
        tagged = b.eval("[...document.querySelectorAll('#workTbl tbody tr[data-row]')].filter(r=>r.querySelector('td.title .tg[data-tg=cv]')).map(r=>r.dataset.row).sort()")
        client = b.eval("A.filter(x=>x.client&&x.st==='Open').map(x=>x.id).sort()")
        self.assertTrue(client)
        self.assertEqual(tagged, client)
        self.assertEqual(b.eval("document.querySelector('#workTbl .tg[data-tg=cv]').textContent"), "Client")

    # ── grouping ──
    def test_default_grouping_per_tab_where_nothing_is_saved(self):
        b = self.open_work()
        g = self.groups()
        self.assertTrue(g and all(x in DUE_GROUPS for x in g), g)
        self.assertEqual(g, [x for x in DUE_GROUPS if x in g])                                       # in the plan's order
        self.assertIsNone(self.stored("creaite-listgrp"))
        self.open_work("raid")
        self.assertEqual(self.groups(), [x for x in ["Urgent", "High", "Medium", "Low"] if x in self.groups()])
        self.assertTrue(self.groups())
        self.open_work("decisions")
        self.assertEqual(self.groups()[0], "Pending" if "Pending" in self.groups() else "Made")
        self.assertTrue(set(self.groups()) <= {"Pending", "Made", "Withdrawn"})
        self.open_work("actions")
        b.click('#wlay [data-lay="board"]')                                                           # the Board keeps its own grouping
        b.wait("!document.getElementById('workBoard').hidden")
        self.assertEqual(b.eval("groupOf('actions')"), "due")
        self.open_work("raid")
        self.assertEqual(b.eval("layoutOf('raid')"), "list")

    def test_closed_comes_last_and_keeps_its_rows(self):
        # the brief asks for Closed folded; folding by default hides rows the Work filter tests count (they must pass unchanged),
        # so Closed is the last group and opens drawn: a decision for Jarvis (see the report)
        b = self.open_work()
        b.eval("applyFilters({st:['Open','Closed']}); renderWork()")
        b.wait("document.querySelector('#workTbl tr.wgh[data-gk=\"actions|due|closed\"]')")
        self.assertEqual(self.groups()[-1], "Closed")
        self.assertGreater(b.eval("[...document.querySelectorAll('#workTbl tr[data-row]')].filter(r=>REC('actions',r.dataset.row).st==='Closed').length"), 0)
        self.assertIsNone(self.stored("creaite-listcoll"))

    def test_no_grouping_is_kept_as_a_choice_and_reset_returns_to_the_default(self):
        b = self.open_work()
        b.click("#dispBtn")
        self.choose("#wgrp", "none")
        self.assertEqual(self.groups(), [])
        self.assertEqual(self.stored("creaite-listgrp"), {"actions": "none"})
        b.reload(READY)
        self.open_work()
        self.assertEqual(self.groups(), [])                                                           # not mistaken for unset
        self.assertIn("&lg=none", b.eval("location.hash"))
        b.reload(READY)                                                                                # the address says it too
        self.assertEqual(self.groups(), [])
        b.click("#dispBtn")
        b.click("#dispReset")
        b.wait("document.querySelector('#workTbl tr.wgh')")
        self.assertEqual(self.groups()[0] in DUE_GROUPS, True)

    def test_a_saved_grouping_wins_and_a_chosen_order_shows_the_list_in_that_order(self):
        b = self.b
        b.eval("localStorage.setItem('creaite-listgrp', JSON.stringify({actions:'priority'}))")
        b.reload(READY)
        self.open_work()
        self.assertEqual(self.groups()[0], "Urgent")
        b.eval("localStorage.clear()")
        b.goto(self.base + "/#work=actions")                                                         # a fresh address: no lg in it
        b.wait(READY)
        self.open_work()
        self.assertEqual(self.groups()[0], "Overdue")
        b.click('#workTbl thead th[data-col="t"]')                                                  # a heading sort: the default steps aside
        b.wait("!document.querySelector('#workTbl tr.wgh')")
        titles = b.eval("[...document.querySelectorAll('#workTbl tbody tr[data-row]')].map(r=>REC('actions',r.dataset.row).t.toLowerCase())")
        self.assertEqual(titles, sorted(titles))
        self.assertIsNone(self.stored("creaite-listgrp"))


if __name__ == "__main__":
    unittest.main()
