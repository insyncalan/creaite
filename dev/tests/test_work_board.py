"""BL-103: the Work board (Sprint 4a), in a real browser against the real live server.

Run: python3 dev/tests/test_work_board.py   (needs Google Chrome; skipped otherwise)

Cards are dragged with real mouse events (press, move, release through the DevTools protocol). Every column is checked against an
oracle written in Python (no code shared with the page), and every move is read back from the database the server wrote.
"""
import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import work_data as W  # noqa: E402
from live_browser import TEST_PALETTES  # noqa: E402
from work_board_case import BoardCase, TODAY, W_initials, due_column, iso, wd, week_sunday  # noqa: E402

class BoardLayout(BoardCase):
    shared_server = True

    def test_toggle_hash_and_reload(self):
        b = self.open_board()
        self.assertEqual(b.eval("[...document.querySelectorAll('#wlay button')].map(x=>[x.dataset.lay,x.getAttribute('aria-pressed')])"),
                         [["list", "false"], ["board", "true"]])
        self.assertIn("lay=board&g=due", b.eval("location.hash"))                                # in the address
        b.reload("typeof go==='function' && LIVE")                                                # refresh keeps it
        b.wait("!document.getElementById('workBoard').hidden && document.querySelector('#workBoard .bcol')")
        b.click('#wlay [data-lay="list"]')
        b.wait("document.getElementById('workBoard').hidden")
        self.assertNotIn("lay=board", b.eval("location.hash"))
        b.click('#wlay [data-lay="board"]')
        b.wait("!document.getElementById('workBoard').hidden")
        b.eval("go('today')")
        b.wait("VIEW==='today'")
        b.eval("history.back()")                                                                  # Back returns to Work, on the board
        b.wait("VIEW==='work' && !document.getElementById('workBoard').hidden")

    def test_decisions_have_a_board_too(self):          # the Decisions board (sprint-debug-log-2b): see test_decisions_board.py
        b = self.b
        b.eval("go('work')")
        b.click('#wtabs button[data-t="decisions"]')
        b.wait("WT==='decisions'")
        self.assertFalse(b.eval("document.getElementById('wlay').hidden"))

    def test_defaults_per_tab(self):
        self.open_board("actions")
        self.assertEqual(self.b.eval("document.getElementById('wgrp').value"), "due")
        self.open_board("raid")
        self.assertEqual(self.b.eval("document.getElementById('wgrp').value"), "owner")

    def test_due_grouping_against_the_oracle(self):
        b = self.open_board("actions", "due", view="open")
        want = {}
        for r in self.v.rows("actions"):
            if r["status"] == "Open":                                                             # All open is Open only (Alan, 11-10-2026)
                want.setdefault(due_column(r, True), []).append(r["id"])
        got = self.columns()
        self.assertEqual(list(got), ["Overdue", "This week", "Next week", "Later", "No date"])
        for label in got:
            self.assertEqual(sorted(got[label]), sorted(want.get(label, [])), label)
        self.assertEqual(b.eval("document.querySelector('#workBoard .bcol h3').textContent"), f"Overdue · {len(want['Overdue'])}")
        self.assertRegex(self.b.eval("document.getElementById('wcount').textContent"), r"^Showing \d+ of \d+$")

    def test_status_grouping_and_cancelled_only_when_present(self):
        self.open_board("actions", "status", view="closed")
        got = self.columns()
        self.assertEqual(list(got), ["Open", "Delayed", "Closed", "Cancelled"])                 # the Closed view holds both
        self.assertEqual((got["Open"], got["Delayed"]), ([], []))
        self.open_board("actions", "status", view="open")
        self.assertEqual(list(self.columns()), ["Open", "Delayed", "Closed"])                   # nothing cancelled in view: no Cancelled column
        want = Counter(r["status"] for r in self.v.rows("actions") if r["status"] == "Open")        # All open: Delayed has its own view
        self.assertEqual({k: len(v) for k, v in self.columns().items()}, {**dict(want), "Delayed": 0, "Closed": 0})

    def test_owner_grouping_me_first_then_by_count_then_tbc(self):
        self.open_board("actions", "owner", view="open")
        heads = self.headers()
        self.assertEqual(heads[0].split(" · ")[0], "Me")
        self.assertEqual(heads[-1].split(" · ")[0], "TBC")
        mid = [int(h.rsplit(" · ", 1)[1]) for h in heads[1:-1]]
        self.assertEqual(mid, sorted(mid, reverse=True))                                         # by number of items
        mine = [r["id"] for r in self.v.rows("actions") if r["status"] == "Open" and W.is_me(r["owner"])]
        self.assertEqual(sorted(self.columns()["Me"]), sorted(mine))
        tbc = [r["id"] for r in self.v.rows("actions") if r["status"] == "Open" and r["owner"] in ("TBC", None, "")]
        self.assertEqual(sorted(self.columns()["TBC"]), sorted(tbc))

    def test_milestone_grouping_asks_for_one_project(self):
        b = self.open_board("actions", "milestone", view="open")
        self.assertTrue(b.eval("!!document.querySelector('#workBoard .bpick')"))                  # none chosen
        b.eval("(()=>{ const s=document.getElementById('bpickP'); s.value='ABC'; s.dispatchEvent(new Event('change',{bubbles:true})); })()")
        b.wait("document.querySelector('#workBoard .bcol')")
        heads = [h.split(" · ")[0] for h in self.headers()]
        self.assertEqual(heads, ["Build complete", "UAT start", "No milestone"])                 # the project's own, in its order
        self.assertEqual(sorted(self.columns()["UAT start"]), sorted(r["id"] for r in self.v.rows("actions")
                         if r["milestone"] == "ABC-M-001" and r["status"] == "Open"))

    def test_filters_search_and_sort_are_shared_with_the_list(self):
        b = self.open_board("actions", "due", view="mine")
        mine = sorted(i for ids in self.columns().values() for i in ids)
        b.click('#wlay [data-lay="list"]')
        b.wait("document.getElementById('workBoard').hidden")
        self.assertEqual(b.eval("[...document.querySelectorAll('#workTbl tbody tr[data-row]')].map(r=>r.dataset.row).sort()"), mine)
        b.eval("(()=>{ const q=document.getElementById('workQ'); q.value='alpha'; q.dispatchEvent(new Event('input',{bubbles:true})); })()")
        b.wait("document.getElementById('workQ').value==='alpha'")
        listed = b.eval("[...document.querySelectorAll('#workTbl tbody tr[data-row]')].map(r=>r.dataset.row).sort()")
        b.click('#wlay [data-lay="board"]')
        b.wait("!document.getElementById('workBoard').hidden")
        self.assertEqual(sorted(i for ids in self.columns().values() for i in ids), listed)
        self.assertEqual(b.eval("document.getElementById('workQ').value"), "alpha")
        b.eval("(()=>{ const s=document.getElementById('wbsort'); s.value='pr'; s.dispatchEvent(new Event('change',{bubbles:true})); })()")
        b.wait("SORT.actions && SORT.actions.col==='pr'")
        self.assertIn("s=pr.asc", b.eval("location.hash"))
        pri = {"Urgent": 0, "High": 1, "Medium": 2, "Low": 3}
        for ids in self.columns().values():
            ranks = [pri[next(a["priority"] for a in self.v.rows("actions") if a["id"] == i)] for i in ids]
            self.assertEqual(ranks, sorted(ranks))

    def test_saved_view_keeps_layout_and_grouping(self):
        b = self.open_board("actions", "owner", view="open")
        b.eval("OWN.add('Sara Example'); workChanged()")                                          # a custom filter, so Save view is offered
        b.click("#saveView")
        b.wait("document.getElementById('viewName')")
        b.eval("document.getElementById('viewName').value='Beta by owner'")
        b.click("#viewSave")
        b.wait("(S.savedViews||SAVED).actions.some(v=>v.name==='Beta by owner') || SAVED.actions.some(v=>v.name==='Beta by owner')")
        saved = b.eval("SAVED.actions.find(v=>v.name==='Beta by owner')")
        self.assertEqual((saved["lay"], saved["g"]), ("board", "owner"))
        b.click('#wlay [data-lay="list"]')
        b.wait("document.getElementById('workBoard').hidden")
        b.click('#wviews [data-wv="open"]')
        b.eval("applyView('saved:Beta by owner'); renderWork()")
        b.wait("!document.getElementById('workBoard').hidden")
        self.assertEqual(b.eval("groupOf('actions')"), "owner")

    def test_collapse_and_hide_empty_columns(self):
        b = self.open_board("actions", "due", view="open")
        b.click('#workBoard .bcol[data-col="later"] .bcoll')
        b.wait("document.querySelector('#workBoard .bcol[data-col=\"later\"].collapsed')")
        self.assertEqual(b.eval("document.querySelectorAll('#workBoard .bcol[data-col=\"later\"] .bcard').length"), 0)
        b.reload("typeof go==='function' && LIVE")                                                 # remembered
        b.wait("document.querySelector('#workBoard .bcol')")
        self.assertTrue(b.eval("!!document.querySelector('#workBoard .bcol[data-col=\"later\"].collapsed')"))
        b.click('#workBoard .bcol[data-col="later"].collapsed')
        b.wait("!document.querySelector('#workBoard .bcol[data-col=\"later\"].collapsed')")
        b.click('#wlay [data-lay="board"]')
        b.eval("(()=>{ const q=document.getElementById('workQ'); q.value='zzqqxx'; q.dispatchEvent(new Event('input',{bubbles:true})); })()")
        b.wait("document.querySelector('#workBoard .empty')")                                      # no match: one message, no empty columns
        self.assertIn("Nothing matches", b.eval("document.querySelector('#workBoard .empty').textContent"))      # BL-132: names the filters
        self.assertIn("zzqqxx", b.eval("document.querySelector('#workBoard .empty').textContent"))
        b.eval("(()=>{ const q=document.getElementById('workQ'); q.value=''; q.dispatchEvent(new Event('input',{bubbles:true})); const h=document.getElementById('wshowempty'); h.checked=false; h.dispatchEvent(new Event('change',{bubbles:true})); })()")
        b.wait("document.querySelector('#workBoard .bcol')")
        self.assertTrue(all(not c["empty"] for c in b.eval("[...document.querySelectorAll('#workBoard .bcol')].map(c=>({empty:!c.querySelector('.bcard')}))")))

    def test_card_content(self):
        b = self.open_board("actions", "due", view="open")
        late = self.card_in("Overdue")
        html = b.eval(f"document.querySelector('{self.card_sel(late)}').innerText")
        row = self.action(late)
        self.assertIn(late, html)
        self.assertIn({"ABC": "Example Programme", "DEF": "Digital Enablement"}[row["project"]], html)       # the project's name (BL-101)
        self.assertIn(row["description"][:20], html)
        self.assertRegex(html, r"\d+ days? late|Yesterday")
        self.assertTrue(b.eval(f"document.querySelector('{self.card_sel(late)} .bdue').classList.contains('late')"))
        self.assertEqual(b.eval(f"document.querySelector('{self.card_sel(late)} .bown').textContent"), W_initials(row["owner"]))

    def test_click_opens_the_side_panel_and_jk_step(self):
        b = self.open_board("actions", "due", view="open")
        first = b.eval("document.querySelector('#workBoard .bcard').dataset.row")
        b.click(self.card_sel(first))                                  # BL-122: a click highlights the card and opens nothing
        self.assertFalse(b.eval("document.getElementById('panel').classList.contains('on')"))
        self.assertEqual(b.eval("[...document.querySelectorAll('#workBoard .bcard.hl')].map(c=>c.dataset.row)"), [first])
        b.click(self.card_sel(first) + " .bid")                        # the ID opens it
        b.wait("document.getElementById('panel').classList.contains('on')")
        self.assertEqual(b.eval("document.querySelector('#workBoard .bcard.sel').dataset.row"), first)
        order = b.eval("[...document.querySelectorAll('#workBoard .bcard')].map(c=>c.dataset.row)")
        b.key("j")
        b.wait(f"document.querySelector('#workBoard .bcard.sel') && document.querySelector('#workBoard .bcard.sel').dataset.row==={order[1]!r}")
        b.key("k")
        b.wait(f"document.querySelector('#workBoard .bcard.sel').dataset.row==={order[0]!r}")

    def test_works_in_every_palette_and_mode(self):
        b = self.open_board("actions", "due", view="open")
        for palette in TEST_PALETTES:
            for mode in ("Light", "Dark"):
                b.eval(f"S.palette={palette!r}; S.theme={mode!r}; applyTheme()")
                colours = b.eval("""(()=>{ const c=getComputedStyle(document.querySelector('#workBoard .bcard')), col=getComputedStyle(document.querySelector('#workBoard .bcol')),
                  bg=getComputedStyle(document.body); return [c.backgroundColor,col.backgroundColor,bg.backgroundColor,c.color]; })()""")
                self.assertNotEqual(colours[0], colours[1], (palette, mode))                       # a card stands out from its column
                self.assertNotEqual(colours[0], colours[3], (palette, mode))
        self.assertEqual(b.errors, [] if hasattr(b, "errors") else [])

    def test_narrow_window_defaults_to_the_list(self):
        b = self.b
        b.eval("localStorage.setItem('creaite-worklay', JSON.stringify({actions:'board'}))")
        b.resize(600, 900)
        b.reload("typeof go==='function' && LIVE")
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tbody tr')")
        self.assertTrue(b.eval("document.getElementById('workBoard').hidden"))                      # List by default under 640px
        b.click('#wlay [data-lay="board"]')                                                         # the toggle stays available
        b.wait("!document.getElementById('workBoard').hidden")
        self.assertGreater(b.eval("document.getElementById('workBoard').scrollWidth"), b.eval("document.getElementById('workBoard').clientWidth"))   # scrolls sideways


if __name__ == "__main__":
    unittest.main()
