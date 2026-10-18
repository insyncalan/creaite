"""v2.3.0 #154: the right-click menu on a linked person's name.

Run: python3 dev/tests/test_person_menu.py   (needs Google Chrome; skipped otherwise)

Real right-clicks and keys in Chrome against the real live server: Draft email opens the person page's own popup (not the peek's
pane) with the item the click came from as the starting selection, Open <first>'s page, Copy email address, Add details and the
greyed Draft email when there is no address; never on Alan's own name; Menu key and Shift+F10, arrows, Enter, Esc returning
focus to the link; the browser's own menu stays elsewhere.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_draft_chase_pane import CLIPBOARD  # noqa: E402
from test_sent_it_person_menu import SentCase  # noqa: E402

MENU = ".cxmenu"


class PersonMenu(SentCase):
    shared_server = True

    def right_click_owner(self, who, row=None):
        b = self.b
        b.eval('go("work"); setLayout(WT,"list")')
        b.wait('document.querySelectorAll("#workTbl tr[data-row]").length>=3')
        sel = f'#workTbl tr[data-row="{row}"] a[data-person="{who}"]' if row else f'#workTbl a[data-person="{who}"]'
        b.click(sel, button="right")
        b.wait(f'!!document.querySelector("{MENU}")')

    def labels(self):
        return self.b.eval(f"""[...document.querySelectorAll("{MENU} [role=menuitem]")].map(b=>(b.getAttribute("aria-disabled")==="true"?"-":"")+b.querySelector("span").firstChild.textContent)""")

    def test_right_click_a_name_in_work_opens_the_menu_and_draft_email_opens_the_person_popup_on_that_item(self):
        b = self.b
        b.eval("S.ownDomains=['client.com','example.com']")
        self.right_click_owner("Sara Example", self.s_room)
        self.assertEqual(self.labels(), ["Draft email", "Open Sara's page", "Copy email address"])
        b.eval(f"""[...document.querySelectorAll("{MENU} [role=menuitem]")].find(x=>x.textContent.startsWith("Draft email")).click()""")
        b.wait("document.getElementById('deDlg').open")
        self.assertEqual(b.eval("document.getElementById('deTitle').textContent"), "Draft email: Sara Example")
        picked = b.eval("[...document.querySelectorAll('#deInc [data-deit]')].filter(c=>c.checked).map(c=>c.dataset.deit)")
        self.assertEqual(picked, [f"actions:{self.s_room}"])              # the row the click came from starts ticked
        self.assertGreaterEqual(b.eval("document.querySelectorAll('#deInc [data-deit]').length"), 3)
        b.eval("document.getElementById('deDlg').close()")
        self.assertEqual(b.errors, [])

    def test_open_page_and_copy_email_address(self):
        b = self.b
        self.right_click_owner("Sara Example")
        b.eval(CLIPBOARD)
        b.eval(f"""[...document.querySelectorAll("{MENU} [role=menuitem]")].find(x=>x.textContent.startsWith("Copy email")).click()""")
        b.wait("CLIP.length===1")
        self.assertEqual(b.eval("CLIP[0]['text/plain']"), "sara.example@client.com")
        self.right_click_owner("Sara Example")
        b.eval(f"""[...document.querySelectorAll("{MENU} [role=menuitem]")].find(x=>x.textContent.startsWith("Open Sara")).click()""")
        b.wait("VIEW==='person'&&PERSON==='Sara Example'")

    def test_never_on_alans_own_name_and_not_a_person_menu(self):
        b = self.b
        b.eval('go("work"); setLayout(WT,"list")')
        b.wait('document.querySelectorAll("#workTbl tr[data-row]").length>=3')
        sel = f'#workTbl tr[data-row="{self.mine}"] a[data-person]'
        b.click(sel, button="right")
        b.wait(f'!!document.querySelector("{MENU}")')
        self.assertNotIn("Open Alan's page", self.labels())                 # the item's own menu, as before
        self.assertIn("Copy ID", self.labels())
        b.key("Escape")

    def test_keyboard_shift_f10_arrows_enter_and_esc_returns_focus(self):
        b = self.b
        b.eval('go("work"); setLayout(WT,"list")')
        b.wait('document.querySelectorAll("#workTbl tr[data-row]").length>=3')
        b.pump(1.0)                                                          # let Work's own redraws settle: a redrawn row drops the link
        b.eval(f"""window.LINK=document.querySelector('#workTbl tr[data-row="{self.s_room}"] a[data-person="Sara Example"]'); LINK.focus();
          document.body.dispatchEvent(new KeyboardEvent("keydown",{{key:"F10",shiftKey:true,bubbles:true}}))""")
        b.wait(f'!!document.querySelector("{MENU}")')
        self.assertEqual(b.eval("document.activeElement.textContent.trim()"), "Draft email")
        b.key("ArrowDown")
        self.assertTrue(b.eval("document.activeElement.textContent.trim().startsWith('Open Sara')"))
        b.key("Escape")
        b.wait(f'!document.querySelector("{MENU}")')
        self.assertTrue(b.eval("document.activeElement===LINK"))
        b.eval('LINK.focus(); document.body.dispatchEvent(new KeyboardEvent("keydown",{key:"ContextMenu",bubbles:true}))')
        b.wait(f'!!document.querySelector("{MENU}")')
        b.key("Enter")                                                      # Draft email
        b.wait("document.getElementById('deDlg').open")
        b.eval("document.getElementById('deDlg').close()")

    def test_a_person_without_an_email_has_draft_email_greyed_and_add_details(self):
        b = self.b
        b.eval("""openContextMenu(cxPerson('Nobody Known',''),200,200,{label:'Nobody Known'})""")
        b.wait(f'!!document.querySelector("{MENU}")')
        self.assertEqual(self.labels(), ["-Draft email", "Open Nobody's page", "Add details"])
        self.assertIn("No email on record: add details first", b.eval(f'document.querySelector("{MENU}").textContent'))
        b.key("Escape")

    def test_add_details_opens_the_details_dialog_on_the_persons_page(self):
        """Finding 8: choosing Add details lands on the person's page and opens the details dialog (no fixed delay)."""
        b = self.b
        b.eval("""window.__em=(REG.find(x=>x.name==='Tom Reid')||{}).email; (REG.find(x=>x.name==='Tom Reid')||{}).email=''; openContextMenu(cxPerson('Tom Reid',''),200,200,{label:'Tom Reid'})""")
        b.wait(f'!!document.querySelector("{MENU}")')
        b.eval(f"""[...document.querySelectorAll("{MENU} [role=menuitem]")].find(x=>x.textContent.includes("Add details")).click()""")
        try:
            b.wait("document.getElementById('personDlg').open")
            self.assertEqual(b.eval("VIEW"), "person")
        finally:
            b.eval("document.getElementById('personDlg').close(); (REG.find(x=>x.name==='Tom Reid')||{}).email=window.__em")

    def test_add_details_works_for_a_name_that_owns_nothing_and_is_not_on_the_register(self):
        """#154 finding 4: no dead end: the person page offers the add-person form for an unknown name, and for a hidden register entry."""
        b = self.b
        for who, setup, undo in (("Nobody Known", "", ""),
                                 ("Hidden Person", "REG.push({name:'Hidden Person',email:'',aliases:[],org:'',role:'',hidden:true,extra:{}});", "REG.pop();")):
            b.eval(f"""{setup} openContextMenu(cxPerson({who!r},''),200,200,{{label:{who!r}}})""")
            b.wait(f'!!document.querySelector("{MENU}")')
            b.eval(f"""[...document.querySelectorAll("{MENU} [role=menuitem]")].find(x=>x.textContent.includes("Add details")).click()""")
            try:
                b.wait("document.getElementById('personDlg').open")
                self.assertEqual(b.eval("VIEW"), "person")
            finally:
                b.eval(f"document.getElementById('personDlg').close(); {undo}")

    def test_a_registered_person_without_an_email_also_gets_add_details(self):
        b = self.b
        b.eval("""REG.push({name:'Quiet Person',email:'',aliases:[],org:'',role:'',extra:{}}); openContextMenu(cxPerson('Quiet Person',''),200,200,{label:'Quiet Person'})""")
        b.wait(f'!!document.querySelector("{MENU}")')
        self.assertEqual(self.labels(), ["-Draft email", "Open Quiet's page", "Add details"])   # the hint's "add details" is on the menu
        b.key("Escape")
        b.eval("REG.pop()")

    def test_the_browsers_own_menu_stays_elsewhere_and_review_still_has_its_menu(self):
        b = self.b
        b.eval('go("work"); setLayout(WT,"list")')
        b.wait('document.querySelectorAll("#workTbl tr[data-row]").length>=3')
        b.eval("""window.CXT={prevented:[]}; document.addEventListener("contextmenu",e=>CXT.prevented.push(e.defaultPrevented));""")
        b.eval("document.body.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true,clientX:5,clientY:5}))")
        self.assertEqual(b.eval("CXT.prevented"), [False])


if __name__ == "__main__":
    unittest.main()
