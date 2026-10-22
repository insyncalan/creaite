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
from test_dashboard import new
from test_project_settings_v2 import Base, seed

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

    def test_a_missing_detail_is_a_quiet_flag_that_opens_the_same_form_as_the_pencil(self):
        """#304: no second "Add details" button; one pencil, and a flag naming what is missing when something is."""
        b = self.b
        self.open()
        row = "#plRows tr[data-pn=%r]"
        self.assertEqual(b.eval(f"document.querySelector({row % 'Omar Ali'!r} + ' [data-pl-details]').textContent.trim()"), "No email")
        self.assertEqual(b.eval(f"document.querySelector({row % 'Jane Doe'!r} + ' [data-pl-details]').textContent.trim()"), "No email, no organisation, no role")
        self.assertEqual(b.eval("[...document.querySelectorAll('#plRows button')].filter(x=>x.textContent.trim()==='Add details').length"), 0)
        self.assertEqual(b.eval(f"document.querySelectorAll({row % 'Omar Ali'!r} + ' [data-pl-edit]').length"), 1)
        self.assertEqual(b.eval(f"document.querySelectorAll({row % 'Sara Example'!r} + ' [data-pl-details]').length"), 0, "complete: only the pencil")
        self.assertEqual(b.eval(f"document.querySelectorAll({row % 'Mia Hale'!r} + ' [data-pl-details]').length"), 0)
        self.assertIn("No email", b.eval(f"document.querySelector({row % 'Omar Ali'!r} + ' [data-pl-details]').getAttribute('aria-label')"))
        titles = []
        for sel in ("[data-pl-details='Omar Ali']", "[data-pl-edit='Omar Ali']"):
            self.tap(sel)
            b.wait("!!document.querySelector('#personEdit[open] #peSave')")
            titles.append(b.eval("document.querySelector('#peTitle').textContent"))
            self.tap("#peCancel")
            b.wait("!document.querySelector('#personEdit[open]')")
        self.assertEqual(titles[0], titles[1])
        self.assertEqual(titles[0], "Edit Omar Ali")

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

    def test_remove_is_refused_while_they_own_items(self):
        """#248 M3 (Alan, 20-10-2026): no Remove for someone who still owns items; the message gives the count and says to
        reassign them first; nothing is written, so their aliases and details stay and no "needs details" row appears."""
        b = self.b
        self.open()
        owned = b.eval("(()=>{ const me=['Sara Example','Sara','SE']; return [...A,...R].filter(i=>me.includes(i.o)).length"
                       " + DEC.filter(d=>me.includes(d.by)).length; })()")
        self.assertGreater(owned, 0, "the fixture gives Sara Example items")
        before = self.register
        self.tap("[data-pl-remove='Sara Example']")
        b.wait("!!document.querySelector('[data-pl-remove-refused=\"Sara Example\"]')")
        msg = b.eval("document.querySelector('[data-pl-remove-refused=\"Sara Example\"]').textContent")
        self.assertIn(f"{owned} item", msg)
        self.assertIn("reassign or remove them first", msg.lower())
        self.assertFalse(b.eval("!!document.querySelector('[data-pl-remove-yes=\"Sara Example\"]')"), "no Remove button")
        self.tap("[data-pl-remove-no='Sara Example']")
        b.wait("!document.querySelector('[data-pl-remove-refused=\"Sara Example\"]')")
        time.sleep(0.5)
        self.assertEqual(self.register, before, "nothing written")
        self.assertIn("| Sara Example | sara@example.com | Sara, SE |", self.register)
        self.assertFalse(b.eval("!!document.querySelector('#plRows tr[data-pn=\"Sara Example\"] [data-needs]')"))

    def test_edit_details_on_a_person_page_has_no_followed_field(self):
        """#248 M2 (Alan, 20-10-2026): the person page's Edit details has no VIP select or Follow tick (people you follow are
        set on the project settings page); saving it keeps the register's value as it was."""
        b = self.b
        b.eval("go('person','Sara Example')")
        b.wait("VIEW==='person' && !!document.querySelector('#ppEdit')")
        self.tap("#ppEdit")
        b.wait("document.getElementById('personDlg').open")
        self.assertFalse(b.eval("!!document.querySelector('#personDlg select, #personDlg #pd_vip, #personDlg .pdvip, #personDlg input[type=checkbox]:not(#pdRemember)')"))
        self.assertNotRegex(b.eval("document.getElementById('personDlg').innerText"), r"\bVIP\b|Follow")
        b.eval("document.getElementById('pd_role').value='Delivery director'")
        self.tap("#pdSave")
        self.applied()
        line = [ln for ln in self.register.splitlines() if ln.startswith("| Sara Example")][0]
        self.assertIn("Delivery director", line)
        self.assertRegex(line, r"\| yes \|", "still followed")

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

    def marks(self, scope=""):
        """Visible followed markers (the star, anything named Followed, the Follow tick) outside the project settings page, plus
        100 when a shown view or the given dialog says "Followed" in words."""
        return self.b.eval(f"""[...document.querySelectorAll('.pstar,[aria-label=Followed],#peFollow')].filter(e=>!e.closest('#v-psettings')&&e.getClientRects().length).length
            + ([...document.querySelectorAll('.view:not([hidden]){', ' + scope if scope else ''}')].filter(v=>v.id!=='v-psettings').some(v=>/\\bFollowed\\b/.test(v.innerText))?100:0)""")

    def test_no_followed_marker_on_the_people_page_or_any_surface(self):
        """BL-288 (spec, Followed people): Sara Example is followed; the star shows on the project settings page and nowhere else."""
        b = self.b
        Base.open(self, "people")
        self.assertEqual(b.eval("document.querySelectorAll('#v-psettings .pstar').length"), 1, "the one place it shows")
        for tab in ("all", "work", "none", "att"):                     # every tab of the People page
            self.open(tab)
            self.assertEqual(self.marks(), 0, tab)
        self.open("all")
        self.tap("#plFBtn")                                            # the People page's filter has no Followed field
        b.wait("!!document.querySelector('#plFMenu .fpf')")
        self.assertNotIn("Followed", b.eval("document.querySelector('#plFMenu').textContent"))
        self.tap("#plFpDone")
        self.tap("[data-pl-edit='Sara Example']")                       # the People page's edit form has no Follow tick
        b.wait("!!document.querySelector('#personEdit[open] #peEmail')")
        self.assertEqual(self.marks("#personEdit"), 0)
        self.assertFalse(b.eval("!!document.querySelector('#peFollow')"))
        self.tap("#peCancel")
        b.wait("!document.querySelector('#personEdit[open]')")
        for js, ready in (("go('work')", "VIEW==='work'"), ("go('today')", "VIEW==='today'"), ("go('review')", "VIEW==='intake-review'"),   # #232 C2: Review and Inbox are Intake's page
                          ("go('inbox')", "VIEW==='intake-review'"), ("go('person','Sara Example')", "VIEW==='person'"),
                          ("go('work'); openRecord('actions', A.find(a=>a.o==='Sara Example').id)", "!!document.querySelector('#panel.on, .peek')")):
            b.eval(js)
            b.wait(ready)
            time.sleep(0.3)
            self.assertEqual(self.marks(), 0, js)
        b.eval("go('today'); openCk(); const q=document.getElementById('cmdkIn'); q.value='Sara'; q.dispatchEvent(new Event('input',{bubbles:true}))")
        b.wait("document.getElementById('cmdk').open && document.querySelectorAll('#cmdkList button').length>0")
        self.assertTrue(b.eval("/Sara Example/.test(document.getElementById('cmdkList').textContent)"), "search finds her")
        self.assertEqual(self.marks("#cmdk"), 0, "the command palette's search")
        self.assertEqual(b.eval("document.querySelectorAll('#cmdk .pstar,#cmdk [aria-label=Followed]').length"), 0)
        b.eval("document.getElementById('cmdk').close()")
        b.eval("openSearch('Sara Example')")                           # the vault search (Files)
        b.wait("VIEW==='files'")
        time.sleep(0.5)
        self.assertEqual(self.marks(), 0, "the vault search")

    def test_the_add_people_links_open_the_people_page(self):
        """The register's home moved: Today's setup checklist's Add people opens the People page, not Settings."""
        b = self.b
        b.eval("go('today'); const x=document.createElement('button'); x.dataset.setup='people'; x.id='tSetupPeople'; document.body.append(x); x.click(); x.remove()")
        b.wait("VIEW==='people' && !!document.querySelector('#plRows')")
        self.assertEqual(b.eval("location.hash"), "#people")

    def test_the_address_keeps_the_tab(self):
        b = self.b
        b.goto(self.base + "/#people/att")
        b.wait("typeof go==='function' && LIVE && VIEW==='people' && !!document.querySelector('#ptabs [aria-selected=true]')")
        self.assertTrue(b.eval("document.querySelector('#ptabs [aria-selected=true]').textContent.startsWith('Needs attention')"))
        time.sleep(0.2)


class RemoveWhileNamed(Base):
    """#248 (Cap's finding on B): Remove from the register is refused while anything still names the person, not only their
    actions, RAID and decisions: a project's Key stakeholders, a milestone's owner and a workstream's lead count too, so their
    aliases and the followed column are never lost to a "needs details" row. Someone named nowhere can still be removed."""

    @classmethod
    def load(cls, v):
        seed(v)
        v.propose("named", [new("milestones", 50, project="DEF", name="Pilot live", baseline_date="2026-12-15", owner="Noah Reed",
                                source="Alan (cx-edit)"),
                            new("workstreams", 51, project="DEF", name="Training", lead="Lena Park", created="2026-10-01",
                                source="Alan (cx-edit)")])
        v.run("apply")
        reg = v.root / "projects/_portfolio/project-register.md"
        reg.write_text(reg.read_text().replace("| Sam (sponsor) |", "| Sam (sponsor), Mia Hale (analyst) |"))
        people = v.root / "projects/_portfolio/people-register.md"
        people.write_text(people.read_text()
                          .replace("| Mia Hale | mia@example.com | |", "| Mia Hale | mia@example.com | MH |")
                          .replace("| Analyst | | |", "| Analyst | | yes |")
                          + "| Noah Reed | noah@example.com | Noah | Example Client Ltd | Test manager | | |\n"
                          + "| Lena Park | lena@example.com | Lena | Example Client Ltd | Trainer | | |\n"
                          + "| Ivy Moss | ivy@example.com | Ivy | Example Client Ltd | Adviser | | yes |\n")
        v.run(script="build_dashboard.py")

    def open(self):
        self.b.eval("go('people')")
        self.b.wait("VIEW==='people' && !!document.querySelector('#plRows')")

    def refused(self, name):
        b = self.b
        before = self.register
        self.tap(f"[data-pl-remove='{name}']")
        sel = f'[data-pl-remove-refused="{name}"]'
        b.wait(f"!!document.querySelector({sel!r})")
        msg = b.eval(f"document.querySelector({sel!r}).textContent")
        self.assertIn("reassign or remove them first", msg.lower())
        self.assertFalse(b.eval(f"!!document.querySelector('[data-pl-remove-yes=\"{name}\"]')"), "no Remove button")
        self.tap(f"[data-pl-remove-no='{name}']")
        time.sleep(0.5)
        self.assertEqual(self.register, before, "nothing written")
        return msg

    def test_a_key_stakeholder_with_an_alias_and_followed_is_refused(self):
        self.open()
        msg = self.refused("Mia Hale")
        self.assertIn("a key stakeholder on 1 project", msg)
        self.assertIn("| Mia Hale | mia@example.com | MH | Example Client Ltd | Analyst | | yes |", self.register)

    def test_a_milestone_owner_is_refused(self):
        self.open()
        self.assertIn("owns 1 milestone", self.refused("Noah Reed"))

    def test_a_workstream_lead_is_refused(self):
        self.open()
        self.assertIn("leads 1 workstream", self.refused("Lena Park"))

    def test_someone_named_nowhere_can_still_be_removed_with_undo(self):
        b = self.b
        self.open()
        self.tap("[data-pl-remove='Ivy Moss']")
        b.wait("!!document.querySelector('[data-pl-remove-yes=\"Ivy Moss\"]')")
        self.tap("[data-pl-remove-yes='Ivy Moss']")
        self.applied()
        self.assertNotIn("Ivy Moss", self.register)
        self.tap("#snackU")
        self.wait_for(lambda: "| Ivy Moss | ivy@example.com | Ivy | Example Client Ltd | Adviser | | yes |" in self.register,
                      "Undo puts her record back, alias and followed column included", timeout=15)


if __name__ == "__main__":
    unittest.main()
