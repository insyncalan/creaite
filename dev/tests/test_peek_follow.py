"""BL-198 (sprint-review-work): with the peek open, a single click on another work item shows it in the peek.

Run: python3 dev/tests/test_peek_follow.py   (needs Google Chrome; skipped otherwise)

Work's table and Board, a person's page and Intake's proposal rows (Review's, before #232 C2): the peek follows a plain click; on Work a Shift or Cmd/Ctrl click
is still a selection and leaves it; with no peek open a click only highlights. Real clicks (dev/tools/cdp.py), no hover.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_review_project import seed_joint  # noqa: E402
from test_tracker import action  # noqa: E402

SHIFT, CMD = 8, 4


class PeekFollowTests(LiveBrowserCase):
    shared_server = True

    @classmethod
    def load(cls, v):
        seed_joint(v)
        v.propose("more", [action(1, description="Second action for Alan", due_date="2026-12-01")])   # two rows on his page
        v.run("apply")
        v.run(script="build_dashboard.py")

    def cur(self):
        return self.b.eval("CUR&&pkOn()?(CUR.mode==='proposal'?'rv'+CUR.n:CUR.id):null")

    def work(self, layout="list"):
        b = self.b
        b.eval(f'go("work"); setLayout(WT,"{layout}")')
        sel = "#workBoard .bcard[data-row]" if layout == "board" else "#workTbl tr[data-row]"
        b.wait(f'document.querySelectorAll("{sel}").length>=3')
        return [b.eval(f'document.querySelectorAll("{sel}")[{i}].dataset.row') for i in range(3)], sel

    def row(self, sel, id_, part=" td.title"):
        return f'{sel}[data-row="{id_}"]' + ("" if "bcard" in sel else part)

    def test_work_table(self):
        b = self.b
        ids, sel = self.work()     # on_text: on the title, not the cell's centre, which is on the ID and project line (cdp.click)
        b.click(self.row(sel, ids[0]), on_text=True)                      # no peek: a click only highlights
        self.assertIsNone(self.cur())
        self.assertEqual(b.eval("[...HL.keys()]"), [ids[0]])
        b.click(self.row(sel, ids[0]), count=2, on_text=True)
        b.wait(f"CUR&&CUR.id==={ids[0]!r}&&pkOn()")
        b.eval("document.activeElement.blur()")
        b.click(self.row(sel, ids[1]), on_text=True)                      # the peek follows a single click
        b.wait(f"CUR&&CUR.id==={ids[1]!r}")
        self.assertEqual(b.eval("[...HL.keys()]"), [ids[1]])
        self.assertFalse(b.eval('document.getElementById("panel").contains(document.activeElement)'))   # focus wasn't pulled in
        self.assertEqual(b.eval("pkOrder().findIndex(o=>o.id===CUR.id)>0&&!$('#pkPrev').disabled"), True)
        b.click(self.row(sel, ids[2]), modifiers=SHIFT, on_text=True)       # Shift extends the highlight and never shows ids[2];
        self.assertNotEqual(self.cur(), ids[2])                            # two highlighted hand over to the bulk bar (BL-122)
        self.assertEqual(sorted(b.eval("[...HL.keys()]")), sorted(ids[1:3]))

    def test_work_board_and_person(self):
        b = self.b
        b.resize(2400, 1000)                                                    # room for board columns beside the peek
        ids, sel = self.work("board")
        b.click(self.row(sel, ids[0]), count=2)
        b.wait(f"CUR&&CUR.id==={ids[0]!r}&&pkOn()")
        free = b.eval("""[...document.querySelectorAll("#workBoard .bcard[data-row]")].filter(c=>{ c.scrollIntoView({block:"center"});
          const r=c.getBoundingClientRect(), e=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2); return e&&c.contains(e); }).map(c=>c.dataset.row)""")
        others = [i for i in free if i != ids[0]]                              # the cards the peek doesn't cover
        self.assertTrue(others, free)
        b.click(self.row(sel, others[0]))
        b.wait(f"CUR&&CUR.id==={others[0]!r}")
        if len(others) > 1:
            b.click(self.row(sel, others[1]), modifiers=CMD)
            self.assertNotEqual(self.cur(), others[1])
        b.resize(self.width, self.height)
        b.eval('closePanel(); setLayout(WT,"list"); go("person","Alan Carter")')
        b.wait('document.querySelectorAll("#v-person table.ptbl tr[data-row]").length>=2')
        p = "#v-person table.ptbl tr[data-row]"
        pid = [b.eval(f'document.querySelectorAll("{p}")[{i}].dataset.row') for i in range(2)]
        b.click(self.row(p, pid[0]), count=2)
        b.wait(f"CUR&&CUR.id==={pid[0]!r}&&pkOn()")
        b.click(self.row(p, pid[1]))
        b.wait(f"CUR&&CUR.id==={pid[1]!r}")

    def test_review_rows(self):
        """#232 C2: Intake's proposal rows (BL-198's Review rows). A click on a row opens it in the peek, an update included (B2);
        with the peek open a click on another row shows that one; edits not yet saved keep the peek, with a note. The old page's
        highlight, Shift and Cmd/Ctrl selection went with it (the Intake page has no multi-select)."""
        b = self.b
        n1 = b.eval('REV.find(r=>r.rec&&r.rec.t==="Send the joint plan").n')
        n2 = b.eval('REV.find(r=>r.rec&&r.rec.t==="Joint risk").n')
        nu = b.eval('REV.find(r=>r.kind==="update"&&!r.done).n')
        b.eval(f'closePanel(); go("intake-review", {n1})')
        row = lambda n: f'#v-intake-review tr.irprop[data-irn="{n}"] td.title .icttl'
        b.wait(f'!!document.querySelector(\'{row(n1)}\')')
        self.assertIsNone(self.cur())
        b.click(row(n1))
        b.wait(f"CUR&&CUR.mode==='proposal'&&CUR.n==={n1}&&pkOn()")
        b.click(row(n2))
        b.wait(f"CUR&&CUR.n==={n2}")
        b.click(row(nu))                                                   # an update opens in the peek too (B2)
        b.wait(f"CUR&&CUR.n==={nu}")
        b.click(row(n2))
        b.wait(f"CUR&&CUR.n==={n2}")
        b.eval("PK.dirty=true")                                             # edits not yet saved: the peek stays, with a note
        b.click(row(n1))
        self.assertEqual(self.cur(), f"rv{n2}")
        self.assertIn("Save or cancel", b.eval('document.getElementById("pkNote").textContent'))
        b.eval("PK.dirty=false; closePanel()")


if __name__ == "__main__":
    unittest.main()
