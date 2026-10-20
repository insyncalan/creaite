"""#248: People page v2 (spec dev/sprints/settings-cleanup-and-project-settings-v2.md, "People page v2" and the Correction; mockup
dev/mockups/people-page-v2-mockup.html), in a real browser against the live server, at 1400 and 900.

The People page is the home of the whole register: tabs Everyone, With work, Nothing assigned, Needs attention; columns Name,
Email, Organisation, Role, Projects, Actions, RAID, Decisions, Overdue; search and the same two-pane filter as the project page's
People view; Add a person; edit and Remove from the register (asks first, Undo restores); right-click drafts an email; no star
for a followed person, no merge, no "Press ? for help" line. Deleting from the register never happens from a project page.

Run: python3 dev/tests/test_people_page_v2.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_project_settings_v2 import Base

TABS = ["Everyone", "With work", "Nothing assigned", "Needs attention"]
COLS = ["Name", "Email", "Organisation", "Role", "Projects", "Actions", "RAID", "Decisions", "Overdue"]


class PeoplePage(Base):
    def open(self, tab=""):
        self.b.eval(f"go('people'{', ' + repr(tab) if tab else ''})")
        self.b.wait("VIEW==='people' && !!document.querySelector('#plRows')")

    def names(self):
        return self.b.eval("[...document.querySelectorAll('#plRows tr[data-pn]')].map(r=>r.dataset.pn)")

    def tab(self, label):
        self.b.eval(f"[...document.querySelectorAll('#ptabs [role=tab]')].find(t=>t.textContent.startsWith({label!r})).click()")
        self.b.wait(f"document.querySelector('#ptabs [aria-selected=true]').textContent.startsWith({label!r})")

    def test_the_tabs_the_columns_and_the_register(self):
        b = self.b
        self.open()
        self.assertEqual(b.eval("[...document.querySelectorAll('#ptabs [role=tab]')].map(t=>t.firstChild.textContent.trim())"), TABS)
        self.assertEqual(b.eval("document.querySelector('#ptabs [aria-selected=true]').textContent").split()[0], "Everyone")
        heads = b.eval("[...document.querySelectorAll('#peopleTbl thead th')].map(t=>t.textContent.replace(/[▲▼]/g,'').trim())")
        self.assertEqual(heads[:9], COLS)
        names = self.names()
        for n in ("Sara Example", "Omar Ali", "Mia Hale", "Jane Doe"):
            self.assertIn(n, names)
        sara = b.eval("[...document.querySelector('#plRows tr[data-pn=\"Sara Example\"]').children].map(c=>c.textContent.trim())")
        self.assertEqual(sara[1:4], ["sara@example.com", "Example Client Ltd", "Delivery lead"])
        self.assertEqual(b.eval("[...document.querySelectorAll('#plRows tr[data-pn=\"Sara Example\"] .pcode.plink')].map(x=>x.textContent)"), ["Example Programme", "Digital Enablement"])
        self.assertTrue(b.eval("!!document.querySelector('#plRows tr[data-pn=\"Sara Example\"] .cntl[data-nav^=\"actions:open:\"]')"))
        self.assertTrue(b.eval("!!document.querySelector('#plAdd')"))

    def test_with_work_nothing_assigned_and_needs_attention(self):
        b = self.b
        self.open()
        self.tab("With work")
        self.assertIn("Sara Example", self.names())
        self.assertNotIn("Mia Hale", self.names())
        self.assertEqual(b.eval("location.hash"), "#people/work")
        self.tab("Nothing assigned")
        self.assertIn("Mia Hale", self.names())
        self.assertNotIn("Sara Example", self.names())
        self.tab("Needs attention")
        self.assertIn("Jane Doe", self.names())
        self.assertIn("Omar Ali", self.names(), "no email")
        self.assertNotIn("Sara Example", self.names())
        self.assertEqual(b.eval("document.querySelector('#plRows tr[data-pn=\"Omar Ali\"] [data-needs]').title"), "Missing: email")
        self.assertNotIn("not in register", b.eval("document.querySelector('#v-people').innerText").lower())
        self.assertNotIn("Add to register", b.eval("document.querySelector('#v-people').innerText"))

    def test_search_and_the_same_two_pane_filter(self):
        b = self.b
        self.open()
        b.eval("(()=>{ const e=document.querySelector('#plQ'); e.value='Omar'; e.dispatchEvent(new Event('input',{bubbles:true})); })()")
        b.wait("document.querySelectorAll('#plRows tr[data-pn]').length===1")
        self.assertEqual(self.names(), ["Omar Ali"])
        b.eval("(()=>{ const e=document.querySelector('#plQ'); e.value=''; e.dispatchEvent(new Event('input',{bubbles:true})); })()")
        self.tap("#plFBtn")
        b.wait("!!document.querySelector('#plFMenu .fpf')")
        text = b.eval("document.querySelector('#plFMenu').textContent")
        for w in ("Project", "How they're involved", "Organisation", "Needs attention"):
            self.assertIn(w, text)
        self.assertNotIn("Followed", text, "no followed field on the People page (BL-288)")
        self.assertNotIn("In the register", text)
        b.eval("[...document.querySelectorAll('#plFMenu .fpf')].find(f=>/Needs attention/.test(f.textContent)).click()")
        b.wait("/No email/.test(document.querySelector('#plFMenu .fpr').textContent)")
        b.eval("[...document.querySelectorAll('#plFMenu .fpr [role=option], #plFMenu .fpr label')].find(o=>/No email/.test(o.textContent)).click()")
        b.wait("!document.querySelector('#plRows tr[data-pn=\"Sara Example\"]')")
        self.assertIn("Showing", b.eval("document.querySelector('#plFMenu').textContent"))
        self.tap("#plFpClear")
        b.wait("!!document.querySelector('#plRows tr[data-pn=\"Sara Example\"]')")
        self.tap("#plFpDone")

    def test_add_a_person_and_edit_without_an_email_and_no_follow_tick(self):
        b = self.b
        self.open()
        self.tap("#plAdd")
        b.wait("!!document.querySelector('#personEdit[open] #peName')")
        self.assertFalse(b.eval("!!document.querySelector('#peFollow')"), "the Follow tick is on the project settings page only")
        self.assertFalse(b.eval("!!document.querySelector('#peRemove')"))
        b.eval("document.querySelector('#peName').value='Rhea Stone'; document.querySelector('#peOrg').value='Example Client Ltd'")
        self.tap("#peSave")
        self.applied()
        b.wait("!!document.querySelector('#plRows tr[data-pn=\"Rhea Stone\"]')")
        self.assertIn("| Rhea Stone |", self.register)
        self.tap("#plAdd")
        b.wait("!!document.querySelector('#personEdit[open] #peName')")
        b.eval("document.querySelector('#peName').value='Sara Example'")
        self.tap("#peSave")
        b.wait("/already in the register/.test(document.querySelector('#peErr').textContent)")
        self.tap("#peCancel")

    def test_remove_from_the_register_asks_first_and_undo_restores(self):
        b = self.b
        self.open()
        self.tap("[data-pl-remove='Mia Hale']")
        b.wait("!!document.querySelector('[data-pl-remove-yes=\"Mia Hale\"]')")
        self.tap("[data-pl-remove-no='Mia Hale']")
        self.assertIn("| Mia Hale |", self.register)
        self.tap("[data-pl-remove='Mia Hale']")
        self.tap("[data-pl-remove-yes='Mia Hale']")
        self.applied()
        b.wait("!document.querySelector('#plRows tr[data-pn=\"Mia Hale\"]')")
        self.assertNotIn("Mia Hale", self.register)
        self.tap("#snackU")
        self.wait_for(lambda: "| Mia Hale | mia@example.com |" in self.register, "Undo puts her record back", timeout=15)
        b.wait("!!document.querySelector('#plRows tr[data-pn=\"Mia Hale\"]')", timeout=15)

    def test_a_project_page_never_deletes_from_the_register(self):
        b = self.b
        Base.open(self, "people")          # the project settings page
        self.assertEqual(b.eval("document.querySelectorAll('#v-psettings [data-pl-remove],#v-psettings [aria-label*=\"from the register\"]').length"), 0)
        self.tap("[data-pm-remove='Sara Example']")
        self.applied()
        self.assertIn("| Sara Example | sara@example.com |", self.register)

    def test_right_click_drafts_an_email_and_a_name_opens_their_page(self):
        b = self.b
        self.open()
        self.tap("#plRows tr[data-pn='Omar Ali'] a.plink2", button="right")
        b.wait("!!document.querySelector('.cxmenu')")
        b.eval("[...document.querySelectorAll('.cxmenu [role=menuitem]')].find(x=>x.textContent.startsWith('Draft email')).click()")
        b.wait("!!document.querySelector('#deDlg[open]')")
        b.eval("document.getElementById('deDlg').close()")
        self.tap("#plRows tr[data-pn='Sara Example'] a.plink2")
        b.wait("VIEW==='person' && PERSON==='Sara Example'")

    def test_no_star_no_merge_no_help_line_and_it_fits_at_900_and_1400(self):
        b = self.b
        self.open()
        page = b.eval("document.querySelector('#v-people').innerText")
        self.assertEqual(b.eval("document.querySelectorAll('#v-people .pstar,#v-people [aria-label=Followed]').length"), 0)
        self.assertNotIn("Merge", page)
        self.assertNotIn("Press ? for help", page)
        for width in (900, 1400):
            b.resize(width, 900)
            for mode in ("light", "dark"):
                b.eval(f"document.documentElement.dataset.theme='{mode}'")
                self.open()
                self.assertLessEqual(b.eval("document.documentElement.scrollWidth-document.documentElement.clientWidth"), 0, f"{width} {mode}")
        b.resize(1400, 1000)
        dup = b.eval("(()=>{ const c={}; document.querySelectorAll('[id]').forEach(e=>c[e.id]=(c[e.id]||0)+1); return Object.keys(c).filter(k=>c[k]>1); })()")
        self.assertEqual(dup, [])
        self.assertEqual(b.eval("__errs"), [])

    def test_the_address_keeps_the_tab(self):
        b = self.b
        b.goto(self.base + "/#people/att")
        b.wait("typeof go==='function' && LIVE && VIEW==='people' && !!document.querySelector('#ptabs [aria-selected=true]')")
        self.assertTrue(b.eval("document.querySelector('#ptabs [aria-selected=true]').textContent.startsWith('Needs attention')"))
        time.sleep(0.2)


if __name__ == "__main__":
    unittest.main()
