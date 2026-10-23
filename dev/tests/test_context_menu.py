"""BL-197 (sprint-review-work): right-click a work item for a menu of its common actions.

Run: python3 dev/tests/test_context_menu.py   (needs Google Chrome; skipped otherwise)

Real right-clicks (dev/tools/cdp.py) on Work's table and Board, a person's page and an item link; the browser's own menu
outside items; each change through the existing save path with Undo; several highlighted rows act together and unfit actions
are withheld; Shift+F10 and the context-menu key, arrows, Enter and Esc. No hover is relied on.

#232 C2: the proposals' own right-click menu belonged to the old Review page and went with it (the Intake page's rows have none; their
buttons and the peek do the same jobs). Its test, test_review_menu_edits_the_proposal_and_keeps_the_bulk_rule, is removed with it.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_review_project import seed_joint  # noqa: E402

CMD = 4
MENU = ".cxmenu"


class ContextMenuTests(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        cls.prop = seed_joint(v)[0]
        v.run(script="build_dashboard.py")

    def setUp(self):
        super().setUp()
        self.b.eval("""window.CXT={prevented:[]}; document.addEventListener("contextmenu",e=>CXT.prevented.push(e.defaultPrevented));
          S.autoApply=false;""")

    def labels(self, level=0):
        return self.b.eval(f"""[...document.querySelectorAll("{MENU}")][{level}] ? [...document.querySelectorAll("{MENU}")[{level}].querySelectorAll("[role=menuitem],.cxhead")]
          .map(b=>b.classList.contains("cxhead")?"#"+b.textContent:(b.getAttribute("aria-disabled")==="true"?"-":"")+b.querySelector("span").firstChild.textContent) : null""")

    def pick(self, label, level=0):
        self.b.eval(f"""[...document.querySelectorAll("{MENU}")[{level}].querySelectorAll("[role=menuitem]")].find(b=>b.querySelector("span").firstChild.textContent==={json.dumps(label)}).click()""")

    def work(self):
        self.b.eval('go("work"); setLayout(WT,"list")')
        self.b.wait('document.querySelectorAll("#workTbl tr[data-row]").length>=3')
        return [self.b.eval(f'document.querySelectorAll("#workTbl tr[data-row]")[{i}].dataset.row') for i in range(3)]

    def test_work_row_menu_saves_through_the_existing_path(self):
        b = self.b
        ids = self.work()
        b.click(f'#workTbl tr[data-row="{ids[0]}"] td.title', inset=110, button="right")
        b.wait(f'!!document.querySelector("{MENU}")')
        self.assertEqual(b.eval(f'document.querySelector("{MENU} [role=menu]").getAttribute("role")'), "menu")
        L = self.labels()
        for want in ("Open", "Close", "Status", "Owner", "Due", "Priority", "Workstream", "Milestone", "Copy ID", "Copy link"):
            self.assertIn(want, L)
        self.assertFalse(any("Delete" in x for x in L))
        self.assertEqual(b.eval("CXT.prevented"), [True])
        self.pick("Owner")
        b.wait(f'document.querySelectorAll("{MENU}").length===2')
        self.assertTrue(b.eval(f'document.activeElement.matches("{MENU} .pkq")'))          # the people list searches
        b.type("sara")
        self.assertEqual(self.labels(1), ["Sara Example"])
        b.key("Enter")
        b.wait(f'REC("actions",{ids[0]!r}).o==="Sara Example"')
        self.assertFalse(b.eval(f'!!document.querySelector("{MENU}")'))
        b.wait('/updated/.test(document.getElementById("snackT").textContent)&&document.getElementById("snackU").style.display!=="none"')

    def test_outside_items_the_browser_menu_stays(self):
        b = self.b
        self.work()
        b.click("#workQ", button="right")
        b.click("#v-work h1", button="right")
        self.assertFalse(b.eval(f'!!document.querySelector("{MENU}")'))
        self.assertEqual(b.eval("CXT.prevented"), [False, False])

    def test_several_rows_act_together(self):
        b = self.b
        ids = self.work()
        b.click(f'#workTbl tr[data-row="{ids[0]}"] td.title', inset=110)
        b.click(f'#workTbl tr[data-row="{ids[2]}"] td.title', inset=110, modifiers=CMD)
        b.click(f'#workTbl tr[data-row="{ids[2]}"] td.title', inset=110, button="right")
        b.wait(f'!!document.querySelector("{MENU}")')
        L = self.labels()
        self.assertEqual(L[0], "#2 items")
        projects = b.eval(f'[REC("actions",{ids[0]!r}).p,REC("actions",{ids[2]!r}).p]')
        if projects[0] != projects[1]:
            self.assertIn("-Workstream", L)                                                    # withheld: one project only
        self.assertNotIn("Copy link", L)
        self.pick("Due")
        b.wait(f'document.querySelectorAll("{MENU}").length===2')
        self.pick("Tomorrow", 1)
        b.wait(f'REC("actions",{ids[0]!r}).due===pkAdd(TODAY,1)&&REC("actions",{ids[2]!r}).due===pkAdd(TODAY,1)')
        b.wait('/on 2 items/.test(document.getElementById("snackT").textContent)')

    def test_board_person_and_item_links(self):
        b = self.b
        b.eval('go("work"); setLayout(WT,"board")')
        b.wait('!!document.querySelector("#workBoard .bcard[data-row]")')
        b.click("#workBoard .bcard[data-row]", button="right")
        b.wait(f'!!document.querySelector("{MENU}")')
        self.assertIn("Owner", self.labels())
        b.key("Escape")
        b.wait(f'!document.querySelector("{MENU}")')
        b.eval('setLayout(WT,"list"); go("person","Alan Carter")')
        b.wait('!!document.querySelector("#v-person table.ptbl tr[data-row]")')
        b.click("#v-person table.ptbl tr[data-row] td.title", button="right")
        b.wait(f'!!document.querySelector("{MENU}")')
        self.assertIn("Draft email", self.labels())
        b.key("Escape")
        b.eval('go("activity")')
        b.wait('!!document.querySelector(\'#v-activity [data-open^="actions:"]\')')
        b.click('#v-activity [data-open^="actions:"]', button="right")
        b.wait(f'!!document.querySelector("{MENU}")')
        self.assertEqual(self.labels()[0], "Open")
        for page, sel in (('go("cockpit","ABC")', '#v-cockpit [data-open^="raid:"]'), ('go("today")', '#v-today [data-open^="actions:"]')):
            b.key("Escape")
            b.eval(page)
            b.wait(f"!!document.querySelector('{sel}')")
            b.click(sel, button="right")
            b.wait(f'!!document.querySelector("{MENU}")')
            self.assertIn("Copy ID", self.labels())

    def test_keyboard_opens_and_drives_it(self):
        b = self.b
        ids = self.work()
        b.click(f'#workTbl tr[data-row="{ids[1]}"] td.title')
        b.eval('document.activeElement.blur(); document.body.dispatchEvent(new KeyboardEvent("keydown",{key:"F10",shiftKey:true,bubbles:true}))')
        b.wait(f'!!document.querySelector("{MENU}")')
        self.assertTrue(b.eval(f'document.activeElement.closest("{MENU}")!==null'))
        self.assertEqual(b.eval('document.activeElement.textContent.trim()'), "Open")
        b.key("ArrowDown")
        self.assertEqual(b.eval('document.activeElement.textContent.trim()'), "Close")
        b.key("End")
        self.assertTrue(b.eval('document.activeElement.textContent.trim().startsWith("Draft email")||document.activeElement.textContent.trim()==="Copy link"'))
        b.key("Escape")
        b.wait(f'!document.querySelector("{MENU}")')
        b.eval('document.body.dispatchEvent(new KeyboardEvent("keydown",{key:"ContextMenu",bubbles:true}))')
        b.wait(f'!!document.querySelector("{MENU}")')
        for _ in range(3):
            b.key("ArrowDown")                                                                 # Open, Close, Status
        self.assertEqual(b.eval('document.activeElement.textContent.trim()'), "Owner")
        b.key("ArrowRight")
        b.wait(f'document.querySelectorAll("{MENU}").length===2')
        b.key("Escape")                                                                        # Esc closes the submenu first
        b.wait(f'document.querySelectorAll("{MENU}").length===1')
        self.assertEqual(b.eval('document.activeElement.textContent.trim()'), "Owner")
        b.key("Escape")
        b.wait(f'!document.querySelector("{MENU}")')

    def test_submenus_open_to_the_side_that_fits(self):
        b = self.b
        self.work()
        b.eval('openContextMenu([{label:"Owner",icon:"user",sub:()=>cxPeople(null,()=>{})}],innerWidth-60,120,{label:"Test"})')
        b.eval(f'document.querySelector("{MENU} [role=menuitem]").click()')
        b.wait(f'document.querySelectorAll("{MENU}").length===2')
        r = b.eval(f'(()=>{{ const m=[...document.querySelectorAll("{MENU}")].map(x=>x.getBoundingClientRect()); return [m[0].left,m[1].right,innerWidth,m[1].left]; }})()')
        self.assertLessEqual(r[1], r[0] + 4)                                                   # to the left of the menu
        self.assertGreaterEqual(r[3], 0)


if __name__ == "__main__":
    unittest.main()
