"""#247: Project settings v2 (spec dev/sprints/settings-cleanup-and-project-settings-v2.md, Part 2, People on the project page,
Followed people; locked mockup dev/mockups/project-settings-v2-mockup.html), in a real browser against the live server.

One scrolling page with a sticky list of anchors (the tabs go; no summary header), the sections in order (Project, People and
partners, Workstreams, Milestones, Client report and logos, Archive and close set apart), People on this project as the register's
own table (search, the two-pane filter, needs details, Not on any project yet, edit form, Remove from this project only), the
Workstreams moved in, the Projects page's Show archived, and the followed star on this page only (BL-288).

Run: python3 dev/tests/test_project_settings_v2.py   (needs Google Chrome; skipped otherwise)
"""
import re
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_dashboard
from live_browser import LiveBrowserCase
from test_dashboard import new
from test_tracker import action

# a section is near the top of the page (in its top third, where the list marks the section you are in), or the page is scrolled as far as it goes
AT_TOP = ("(()=>{ const v=document.querySelector('#v-psettings'), s=document.querySelector('#s-%s'), d=s.getBoundingClientRect().top-v.getBoundingClientRect().top; "
          "return (d>=-4 && d<v.clientHeight/3) || (v.scrollTop>0 && v.scrollTop+v.clientHeight>=v.scrollHeight-2); })()")
SECTIONS = ["general", "people", "ws", "miles", "rep", "arch"]
LABELS = ["Project", "People and partners", "Workstreams", "Milestones", "Client report and logos", "Archive and close"]
REGISTER = ("# People register\n\n## People\n\n| Full name | Email | Aliases | Organisation | Role | Hidden | VIP |\n"
            "|---|---|---|---|---|---|---|\n"
            "| Sara Example | sara@example.com | Sara, SE | Example Client Ltd | Delivery lead | | yes |\n"
            "| Omar Ali | | Omar | Digital Enablement Team | Test lead | | |\n"
            "| Mia Hale | mia@example.com | | Example Client Ltd | Analyst | | |\n")


def seed(v):
    test_dashboard.populate(v)
    v.propose("v2", [action(40, project="DEF", description="Share the pilot plan", owner="Sara Example", due_date="2026-12-01"),
                     new("workstreams", 41, project="ABC", name="Testing", lead="Omar Ali", keywords="UAT, test plan", created="2026-10-01", source="Alan (cx-edit)"),
                     new("workstreams", 42, project="ABC", name="Integration", lead="Sara Example", keywords="data, interface", created="2026-10-01", source="Alan (cx-edit)"),
                     action(43, description="Write the UAT test plan", owner="Sara Example", workstream="Testing", due_date="2026-12-02")])
    v.run("apply")
    (v.root / "projects/_portfolio/people-register.md").write_text(REGISTER, encoding="utf-8")
    v.run(script="build_dashboard.py")


class Base(LiveBrowserCase):
    shared_server = False

    @classmethod
    def load(cls, v):
        seed(v)

    @property
    def register(self):
        return (self.v.root / "projects/_portfolio/people-register.md").read_text()

    def setUp(self):
        super().setUp()
        self.b.eval("window.__errs=[]; addEventListener('error',e=>__errs.push(e.message))")

    def open(self, cat="general", code="ABC"):
        self.b.eval(f"go('psettings', {code!r}); psCat.value={cat!r}; navWrite(false)")
        self.b.wait("VIEW==='psettings' && !!document.querySelector('#psBody [data-pssec=arch]') && !!document.querySelector('#psPeopleRows')")
        time.sleep(0.3)          # the page's own first jump to its section (60 ms after it opens) is done before anything is clicked

    def rows(self):
        return self.b.eval("[...document.querySelectorAll('#psPeopleRows tr[data-pn]')].map(r=>r.dataset.pn)")

    def wait_for(self, fn, what, timeout=10):
        end = time.time() + timeout
        while time.time() < end:
            if fn():
                return
            time.sleep(0.1)
        self.fail(what)

    def tap(self, sel, **kw):
        """Click, after scrolling it into view (the page scrolls inside its view; the browser helper clicks where it is now)."""
        self.b.eval(f"document.querySelector({sel!r}).scrollIntoView({{block:'center'}})")
        self.b.click(sel, **kw)

    def applied(self):
        self.b.wait("(()=>{ const s=document.querySelector('#snackT'); return /saved and applied/.test(s.textContent) && s.textContent!==s.dataset.seen; })()", timeout=15)
        self.b.eval("document.querySelector('#snackT').dataset.seen=document.querySelector('#snackT').textContent")
        time.sleep(0.3)


class Page(Base):
    shared_server = True        # reads only
    def test_one_scrolling_page_with_the_sections_in_order_and_no_tabs(self):
        b = self.b
        self.open()
        self.assertEqual(b.eval("[...document.querySelectorAll('#psBody [data-pssec]')].map(s=>s.dataset.pssec)"), SECTIONS)
        self.assertEqual(b.eval("[...document.querySelectorAll('#pscats [data-pscat]')].map(a=>a.textContent.trim())"), LABELS)
        self.assertEqual(b.eval("document.querySelectorAll('#v-psettings [role=tab],#v-psettings [role=tablist],#v-psettings [role=tabpanel]').length"), 0)
        self.assertEqual(b.eval("document.querySelector('#pscats').tagName"), "NAV")
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('#v-psettings .setside')).position"), "sticky")
        self.assertEqual(b.eval("document.querySelectorAll('#v-psettings .pshead,#v-psettings .pshstats').length"), 0, "no summary header (dropped by Alan)")
        self.assertEqual(b.eval("document.querySelector('#pscats [aria-current=true]').dataset.pscat"), "general")

    def settled(self):
        """Wait until the page stops growing (the partners and logos arrive a moment after it opens)."""
        last, same = -1, 0
        while same < 4:
            h = self.b.eval("document.querySelector('#v-psettings').scrollHeight")
            same, last = (same + 1, h) if h == last else (0, h)
            time.sleep(0.15)

    def test_an_anchor_scrolls_to_its_section_marks_it_and_writes_the_address(self):
        b = self.b
        self.open()
        self.settled()
        self.tap("#pscats [data-pscat=ws]")
        b.wait(AT_TOP % "ws", timeout=5)
        self.assertEqual(b.eval("location.hash"), "#project-settings=ABC&c=ws")
        self.assertEqual(b.eval("[...document.querySelectorAll('#pscats [aria-current=true]')].map(a=>a.dataset.pscat)"), ["ws"])
        self.assertTrue(b.eval("document.querySelector('#pscats').getBoundingClientRect().top>=0"), "the list stays in view (sticky)")

    def test_scrolling_marks_where_you_are(self):
        b = self.b
        self.open()
        self.settled()
        b.eval("(()=>{ const v=document.querySelector('#v-psettings'), s=document.querySelector('#s-ws'); v.scrollTop+=s.getBoundingClientRect().top-v.getBoundingClientRect().top; v.dispatchEvent(new Event('scroll')); })()")
        time.sleep(1.0)
        b.eval("document.querySelector('#v-psettings').dispatchEvent(new Event('scroll'))")
        b.wait("document.querySelector('#pscats [aria-current=true]').dataset.pscat==='ws'")
        b.eval("(()=>{ const v=document.querySelector('#v-psettings'); v.scrollTop=v.scrollHeight; v.dispatchEvent(new Event('scroll')); })()")
        b.wait("document.querySelector('#pscats [aria-current=true]').dataset.pscat==='arch'")

    def test_the_address_opens_at_its_section_and_the_old_names_still_work(self):
        b = self.b
        b.goto(self.base + "/#project-settings=ABC&c=ws")
        b.wait("typeof go==='function' && LIVE && VIEW==='psettings' && !!document.querySelector('#s-ws')")
        b.wait(AT_TOP % "ws")
        for old, now in (("logos", "rep"), ("rep", "rep"), ("nope", "general")):
            self.assertEqual(b.eval(f"parseHash('#project-settings=ABC&c={old}').cat"), now)

    def test_archive_and_close_is_last_and_set_apart_in_red(self):
        b = self.b
        self.open("arch")
        self.assertTrue(b.eval("!!document.querySelector('#s-arch .psdanger #psArchive') && !!document.querySelector('#s-arch .psdanger #psClose')"))
        red, plain = b.eval("[getComputedStyle(document.querySelector('#s-arch .card')).borderTopColor, getComputedStyle(document.querySelector('#s-miles .card')).borderTopColor]")
        self.assertNotEqual(red, plain)
        self.assertEqual(b.eval("document.querySelector('#s-arch h2').textContent"), "Archive and close")

    def test_the_client_report_and_the_logos_are_one_section(self):
        b = self.b
        self.open("rep")
        self.assertTrue(b.eval("!!document.querySelector('#s-rep #psRepOn') && document.querySelectorAll('#s-rep .pslogo').length===3"))

    def test_search_hides_the_sections_with_nothing_left(self):
        b = self.b
        self.open()
        b.eval("(()=>{ const e=document.querySelector('#psq'); e.value='keywords'; e.dispatchEvent(new Event('input',{bubbles:true})); })()")
        b.wait("!document.querySelector('#s-ws').hidden && document.querySelector('#s-miles').hidden && document.querySelector('#s-general').hidden")
        self.assertEqual(b.eval("document.querySelector('#pscats [aria-current=true]')"), None)
        b.eval("(()=>{ const e=document.querySelector('#psq'); e.value='Mia'; e.dispatchEvent(new Event('input',{bubbles:true})); })()")
        b.wait("!document.querySelector('#s-people').hidden && document.querySelector('#s-ws').hidden")

    def test_no_horizontal_scroll_at_900_and_1400_and_no_errors_or_duplicate_ids(self):
        b = self.b
        for width in (900, 1400):
            b.resize(width, 900)
            for mode in ("light", "dark"):
                b.eval(f"document.documentElement.dataset.theme='{mode}'")
                self.open()
                self.assertLessEqual(b.eval("document.querySelector('#v-psettings').scrollWidth-document.querySelector('#v-psettings').clientWidth"), 0, f"{width} {mode}")
                self.assertLessEqual(b.eval("document.documentElement.scrollWidth-document.documentElement.clientWidth"), 0)
        b.resize(1400, 1000)
        dup = b.eval("(()=>{ const c={}; document.querySelectorAll('[id]').forEach(e=>c[e.id]=(c[e.id]||0)+1); return Object.keys(c).filter(k=>c[k]>1); })()")
        self.assertEqual(dup, [])
        self.assertEqual(b.eval("__errs"), [])


class People(Base):
    def test_the_register_view_columns_and_one_entry_per_person(self):
        b = self.b
        self.open("people")
        heads = b.eval("[...document.querySelectorAll('#psPeople thead th')].map(t=>t.textContent.trim())")
        self.assertEqual(heads[:6], ["Name", "Email", "Organisation · role", "Aliases", "Actions", "RAID"])
        self.assertIn("Sara Example", self.rows())
        self.assertNotIn("Mia Hale", self.rows(), "on no project: in the quiet group, not the table")
        sara = b.eval("[...document.querySelector('#psPeopleRows tr[data-pn=\"Sara Example\"]').children].map(c=>c.textContent.trim())")
        self.assertEqual(sara[1], "sara@example.com")
        self.assertEqual(sara[2], "Example Client Ltd · Delivery lead")
        self.assertEqual(sara[3], "Sara, SE")
        self.assertEqual(sara[4], "2", "this project's actions only (her DEF action is not counted)")
        self.assertTrue(b.eval("!!document.querySelector('#psPeopleRows tr[data-pn=\"Sara Example\"] .tag.pcodetag[title=\"Also on Digital Enablement\"]')"))
        self.assertEqual(b.eval("document.querySelector('#psPeopleRows tr[data-pn=\"Sara Example\"] .cntl').dataset.nav"), "actions:open:ABC:st=&o=Sara%20Example")

    def test_needs_details_with_what_is_missing_and_no_not_in_register(self):
        b = self.b
        self.open("people")
        self.assertIn("Jane Doe", self.rows(), "the decision maker is on the project")
        tag = b.eval("document.querySelector('#psPeopleRows tr[data-pn=\"Jane Doe\"] [data-needs]').title")
        self.assertEqual(tag, "Missing: email, organisation, role")

        page = b.eval("document.querySelector('#s-people').textContent")
        self.assertNotIn("not in register", page.lower())
        self.assertNotIn("Add to register", page)
        self.tap("[data-pm-details='Jane Doe']")
        b.wait("!!document.querySelector('#personEdit[open] #peSave')")
        self.assertEqual(b.eval("document.querySelector('#peTitle').textContent"), "Edit Jane Doe")

    def test_a_followed_person_has_a_star_named_followed_and_the_form_has_the_tick(self):
        b = self.b
        self.open("people")
        star = b.eval("document.querySelector('#psPeopleRows tr[data-pn=\"Sara Example\"] .pstar').getAttribute('aria-label')")
        self.assertEqual(star, "Followed")
        self.assertEqual(b.eval("document.querySelectorAll('#psPeopleRows .pstar').length"), 1)
        self.assertNotIn("VIP", b.eval("document.querySelector('#s-people').textContent"))
        self.tap("[data-pm-edit='Sara Example']")
        b.wait("!!document.querySelector('#personEdit[open] #peFollow')")
        self.assertTrue(b.eval("document.querySelector('#peFollow').checked"))
        labels = b.eval("[...document.querySelectorAll('#personEdit .pdgrid > label:not(.settick), #personEdit .pdgrid > .pdlab')].map(l=>l.textContent.trim())")
        self.assertEqual(labels, ["Full name", "Email", "Aliases", "Organisation", "Role", "On projects", "Follow"])
        self.assertEqual(b.eval("[...document.querySelectorAll('#personEdit .deacts button')].map(x=>x.textContent)"), ["Remove from this project", "Cancel", "Save"])

    def test_edit_saves_one_entry_without_an_email_and_the_follow_tick_with_undo(self):
        b = self.b
        self.open("people")
        self.tap("[data-pm-edit='Sara Example']")
        b.wait("!!document.querySelector('#personEdit[open] #peEmail')")
        b.eval("document.querySelector('#peEmail').value=''; document.querySelector('#peRole').value='Programme lead'; document.querySelector('#peFollow').checked=false")
        self.tap("#peSave")
        self.applied()
        self.wait_for(lambda: "| Sara Example |  | Sara, SE | Example Client Ltd | Programme lead |" in self.register, "saved, with no email")
        self.assertNotIn("| yes |", self.register.split("Sara Example")[1].split("\n")[0], "unfollowed")
        b.wait("!document.querySelector('#psPeopleRows tr[data-pn=\"Sara Example\"] .pstar')")
        self.tap("#snackU")
        self.wait_for(lambda: "sara@example.com" in self.register, "Undo puts her record back")

    def test_add_a_person_with_the_follow_tick_is_saved_followed(self):
        """M1: Add a person ignored the Follow tick (the add function dropped it), so the new row had an empty followed column."""
        b = self.b
        self.open("people")
        self.tap("#psAddPerson")
        b.wait("!!document.querySelector('#personEdit[open] #peFollow')")
        self.assertFalse(b.eval("document.querySelector('#peFollow').checked"), "new people start unfollowed")
        b.eval("document.querySelector('#peName').value='Nora Probe'; document.querySelector('#peOrg').value='Example Client Ltd'; "
               "document.querySelector('#peFollow').checked=true")
        self.tap("#peSave")
        self.applied()
        row = lambda: [ln for ln in self.register.splitlines() if ln.startswith("| Nora Probe")]
        self.wait_for(lambda: bool(row()), "the new person is in the register")
        self.assertEqual([c.strip() for c in row()[0].strip().strip("|").split("|")][5:7], ["", "yes"], "Hidden empty, VIP (followed) yes")
        b.wait("!!document.querySelector('#psPeopleRows tr[data-pn=\"Nora Probe\"] .pstar')")
        # added without the tick: unfollowed
        self.tap("#psAddPerson")
        b.wait("!!document.querySelector('#personEdit[open] #peFollow')")
        b.eval("document.querySelector('#peName').value='Otto Probe'")
        self.tap("#peSave")
        self.applied()
        self.wait_for(lambda: "| Otto Probe" in self.register, "the second person is in the register")
        line = [ln for ln in self.register.splitlines() if ln.startswith("| Otto Probe")][0]
        self.assertNotIn("yes", line)

    def test_person_page_edit_details_has_no_followed_field_and_keeps_the_flag(self):
        """Alan, 19-10-2026: following is this page's alone. The person page's Edit details has no VIP select, and saving it
        leaves a followed person followed."""
        b = self.b
        b.eval("go('person','Sara Example')")
        b.wait("VIEW==='person' && !!document.querySelector('#ppEdit')")
        self.tap("#ppEdit")
        b.wait("document.getElementById('personDlg').open && document.getElementById('pd_name').value==='Sara Example'")
        self.assertEqual(b.eval("document.querySelectorAll('#personDlg #pd_vip, #personDlg .pdvip, #personDlg select').length"), 0)
        self.assertNotRegex(b.eval("document.getElementById('personDlg').innerText"), re.compile(r"\bVIP\b|Follow"))
        b.eval("document.getElementById('pd_role').value='Programme lead'")
        self.tap("#pdSave")
        self.applied()
        self.wait_for(lambda: "| Programme lead |" in self.register, "saved")
        line = [ln for ln in self.register.splitlines() if ln.startswith("| Sara Example")][0]
        self.assertEqual([c.strip() for c in line.strip().strip("|").split("|")][5:7], ["", "yes"], "still followed")
        self.open("people")
        self.assertEqual(b.eval("document.querySelectorAll('#psPeopleRows tr[data-pn=\"Sara Example\"] .pstar').length"), 1)

    def test_the_bin_removes_from_this_project_only_and_undo_puts_her_back(self):
        b = self.b
        self.open("people")
        self.tap("[data-pm-remove='Sara Example']")
        self.applied()
        b.wait("!document.querySelector('#psPeopleRows tr[data-pn=\"Sara Example\"]')")
        line = [ln for ln in self.register.splitlines() if ln.startswith("| Sara Example")][0]
        self.assertIn("ABC", line, "kept in Left projects")
        self.assertIn("sara@example.com", line, "her record is never deleted from a project page")
        self.assertIn("Left projects", self.register)
        self.tap("#snackU")
        b.wait("!!document.querySelector('#psPeopleRows tr[data-pn=\"Sara Example\"]')", timeout=15)

    def test_not_on_any_project_yet_and_add_to_this_project(self):
        b = self.b
        self.open("people")
        self.assertEqual(b.eval("[...document.querySelectorAll('#psUnas tr[data-pn]')].map(r=>r.dataset.pn)"), ["Mia Hale"])
        self.assertIn("Not on any project yet", b.eval("document.querySelector('#psUnas h3').textContent"))
        self.open("people", "DEF")
        self.assertEqual(b.eval("[...document.querySelectorAll('#psUnas tr[data-pn]')].map(r=>r.dataset.pn)"), ["Mia Hale"], "on every project's page")
        self.open("people")
        self.tap("[data-pm-addto='Mia Hale']")
        self.applied()
        b.wait("!!document.querySelector('#psPeopleRows tr[data-pn=\"Mia Hale\"]') && !document.querySelector('#psUnas')")
        self.assertRegex(self.register, r"\| Projects \|")
        self.assertRegex([ln for ln in self.register.splitlines() if ln.startswith("| Mia Hale")][0], r"\| ABC \|")

    def test_on_projects_ticks_add_and_remove_projects(self):
        b = self.b
        self.open("people")
        self.tap("[data-pm-edit='Jane Doe']")
        b.wait("!!document.querySelector('#personEdit[open] [data-pe-proj=DEF]')")
        self.assertTrue(b.eval("document.querySelector('[data-pe-proj=ABC]').checked"))
        b.eval("document.querySelector('[data-pe-proj=DEF]').checked=true")
        self.tap("#peSave")
        self.applied()
        b.wait("!!document.querySelector('#psPeopleRows tr[data-pn=\"Jane Doe\"] .pcodetag')")
        self.open("people", "DEF")
        self.assertIn("Jane Doe", self.rows())

    def test_the_two_pane_filter_with_counts_showing_clear_all_and_done(self):
        b = self.b
        self.open("people")
        self.tap("#psPmFBtn")
        b.wait("!!document.querySelector('#psPmFMenu .fpf')")
        fields = b.eval("[...document.querySelectorAll('#psPmFMenu .fpf')].map(f=>f.dataset.fpk||f.textContent.trim())")
        text = b.eval("document.querySelector('#psPmFMenu').textContent")
        for w in ("Who", "Tidy up", "Other projects", "How they're involved", "Organisation", "Followed", "Needs attention"):
            self.assertIn(w.lower(), text.lower(), w)
        self.assertNotIn("In the register", text)
        self.assertTrue(fields)
        b.eval("[...document.querySelectorAll('#psPmFMenu .fpf')].find(f=>/Needs attention/.test(f.textContent)).click()")
        b.wait("/No email/.test(document.querySelector('#psPmFMenu .fpr').textContent)")
        opts = b.eval("document.querySelector('#psPmFMenu .fpr').textContent")
        self.assertIn("No organisation", opts)
        self.assertIn("No role", opts)
        self.tap("#psPmFMenu input[data-fk=att][value=email]")
        b.wait("!document.querySelector('#psPeopleRows tr[data-pn=\"Sara Example\"]')")
        shown = self.rows()
        self.assertIn("Jane Doe", shown)
        self.assertTrue(all(b.eval(f"/email/.test(document.querySelector('#psPeopleRows tr[data-pn=\"{n}\"] [data-needs]')?.title||'')") for n in shown), shown)
        self.assertIn(f"Showing {len(shown)} of", b.eval("document.querySelector('#psPmCount').textContent"))
        self.assertIn(f"Showing {len(shown)} of", b.eval("document.querySelector('#psPmFMenu').textContent"))
        self.tap("#psPmFpClear")
        b.wait("document.querySelectorAll('#psPeopleRows tr[data-pn]').length>1")
        self.tap("#psPmFpDone")
        b.wait("!document.querySelector('#psPmFMenu') || document.querySelector('#psPmFMenu').hidden || getComputedStyle(document.querySelector('#psPmFMenu')).display==='none'")

    def test_the_search_narrows_by_name_alias_email_or_role(self):
        b = self.b
        self.open("people")
        b.eval("(()=>{ const e=document.querySelector('#psPmQ'); e.value='SE'; e.dispatchEvent(new Event('input',{bubbles:true})); })()")
        b.wait("document.querySelectorAll('#psPeopleRows tr[data-pn]').length===1")
        self.assertEqual(self.rows(), ["Sara Example"])

    def test_a_name_opens_their_work_and_a_right_click_drafts_an_email_even_with_no_email(self):
        b = self.b
        self.open("people")
        self.tap("#psPeopleRows tr[data-pn='Jane Doe'] a.plink2", button="right")
        b.wait("!!document.querySelector('.cxmenu')")
        items = b.eval("[...document.querySelectorAll('.cxmenu [role=menuitem]')].map(x=>[x.textContent.trim(), x.getAttribute('aria-disabled')||x.disabled||''])")
        draft = [i for i in items if i[0].startswith("Draft email")][0]
        self.assertIn(draft[1], ("", False, "false"), "a person with no email still gets a draft")
        b.key("Escape")
        self.open("people")
        self.tap("#psPeopleRows tr[data-pn='Sara Example'] a.plink2")
        b.wait("VIEW==='person' && PERSON==='Sara Example'")


class Workstreams(Base):
    def test_the_section_lists_the_projects_workstreams_and_no_old_footers(self):
        b = self.b
        self.open("ws")
        self.assertEqual(b.eval("[...document.querySelectorAll('#psWs tbody tr[data-ws]')].map(r=>r.dataset.ws)"), ["Integration", "Testing"])
        self.assertEqual(b.eval("[...document.querySelectorAll('#psWs thead th')].map(t=>t.textContent.trim())")[:4], ["Workstream", "Lead", "Keywords", "Open items"])
        txt = b.eval("document.querySelector('#s-ws').textContent")
        self.assertNotIn("Fix spellings", txt)
        self.assertNotIn("Show retired", txt)

    def test_add_edit_rename_merge_and_retire_with_undo(self):
        b = self.b
        self.open("ws")
        self.tap("#psAddWs")
        b.wait("!!document.querySelector('#psWs .wsedit [data-wsf=name]')")
        b.eval("document.querySelector('#psWs .wsedit [data-wsf=name]').value='Training'; document.querySelector('#psWs .wsedit [data-wsf=keywords]').value='course, guide'")
        self.tap("#psWs [data-ws-save]")
        self.applied()
        b.wait("!!document.querySelector('#psWs tr[data-ws=Training]')")
        self.tap("[data-ws-edit=Testing]")
        b.eval("document.querySelector('#psWs .wsedit [data-wsf=name]').value='Test'")
        self.tap("#psWs [data-ws-save]")
        self.applied()
        b.wait("!!document.querySelector('#psWs tr[data-ws=Test]')")
        self.assertEqual(b.eval("A.find(a=>a.t==='Write the UAT test plan').ws"), "Test", "its items follow a rename")
        self.tap("[data-ws-edit=Test]")
        b.eval("(()=>{ const s=document.querySelector('#psWs [data-ws-merge]'); s.value=WSD().find(w=>w.name==='Integration').id; s.dispatchEvent(new Event('change',{bubbles:true})); })()")
        self.applied()
        b.wait("!document.querySelector('#psWs tr[data-ws=Test]')")
        self.assertEqual(b.eval("A.find(a=>a.t==='Write the UAT test plan').ws"), "Integration")
        self.tap("#snackU")
        b.wait("!!document.querySelector('#psWs tr[data-ws=Test]')", timeout=15)
        self.tap("[data-ws-edit=Training]")
        self.tap("#psWs [data-ws-retire]")
        self.applied()
        b.wait("!document.querySelector('#psWs tr[data-ws=Training]')")


class ProjectsArchived(Base):
    shared_server = True        # reads only
    def test_the_projects_page_has_show_archived_and_restore_on_archived_rows(self):
        b = self.b
        b.eval("D.project_states.push({code:'ZZZ',name:'Old Programme',state:'archived'}); go('projects')")
        b.wait("VIEW==='projects' && !!document.querySelector('#projShowArch')")
        self.assertFalse(b.eval("!!document.querySelector('#projArchived [data-parch=restore]')"))
        b.eval("S.showArchived=true; renderProjects()")
        b.wait("!!document.querySelector('#projArchived [data-parch=restore][data-pcode=ZZZ]')")
        self.assertIn("Old Programme", b.eval("document.querySelector('#projArchived').textContent"))


class FollowedIsPrivate(Base):
    """BL-288: the followed marker shows only on the project settings page's People view (and its form)."""
    shared_server = True        # reads only

    def marks(self):
        return self.b.eval("""[...document.querySelectorAll('.pstar,[aria-label=Followed],#peFollow')].filter(e=>!e.closest('#v-psettings,#personEditHost')&&e.getClientRects().length).length
            + ([...document.querySelectorAll('.view:not([hidden])')].filter(v=>v.id!=='v-psettings').some(v=>/\\bFollowed\\b/.test(v.innerText))?100:0)""")

    def test_no_followed_marker_on_any_other_surface(self):
        b = self.b
        self.open("people")
        self.assertEqual(b.eval("document.querySelectorAll('#v-psettings .pstar').length"), 1)
        for js, ready in (("go('today')", "VIEW==='today'"), ("go('work')", "VIEW==='work'"), ("go('people')", "VIEW==='people'"),
                          ("go('person','Sara Example')", "VIEW==='person'"), ("go('review')", "VIEW==='review'"), ("go('inbox')", "VIEW==='inbox'"),
                          ("go('cockpit','ABC')", "VIEW==='cockpit'"), ("go('projects')", "VIEW==='projects'"),
                          ("go('work'); openRecord('actions', A.find(a=>a.o==='Sara Example').id)", "!!document.querySelector('#panel.on, .peek')")):
            b.eval(js)
            b.wait(ready)
            time.sleep(0.3)
            self.assertEqual(self.marks(), 0, js)
        b.eval("go('person','Sara Example')")
        b.wait("VIEW==='person' && !!document.querySelector('#ppEmail')")
        self.tap("#ppEmail")
        b.wait("!!document.querySelector('#deDlg[open]')")
        self.assertNotRegex(b.eval("document.querySelector('#deDlg').innerText"), re.compile(r"\bFollowed\b|\bVIP\b"))
        self.assertEqual(b.eval("document.querySelectorAll('#deDlg .pstar,#deDlg [aria-label=Followed]').length"), 0)


if __name__ == "__main__":
    unittest.main()
