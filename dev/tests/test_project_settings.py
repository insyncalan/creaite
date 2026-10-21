"""#228 part A: the full-page project settings (#project-settings=<CODE>), in a real browser against the live server.

Run: python3 dev/tests/test_project_settings.py   (needs Google Chrome; skipped otherwise)

Brief: dev/sprints/project-settings-brief.md and the locked mockup dev/mockups/project-settings-mockup.html (pm-intake-briefs).
Part A is the shell and four categories (General, People and partners, Milestones, Archive) with Logos and Reporting as marked
placeholders that open what exists today. No Workstreams category: they stayed in Settings > People and projects
(until #247 moved them in and the Settings line retired that section).

#247 (Project settings v2, Alan, 19-10-2026) deliberately changed the page: one scrolling page whose side list is anchors (the tabs went),
the sections Project, People and partners, Workstreams (moved in), Milestones, Client report and logos (one section), Archive and close.
These tests follow it: a category is now a section the list marks (aria-current) instead of a selected tab; the new behaviour is
dev/tests/test_project_settings_v2.py.
"""
import base64
import re
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_dashboard
from live_browser import TEST_PALETTES, LiveBrowserCase
from test_tracker import ABC

def scroll_clicks(b):
    """#247: the page is one long scroll, so a control can be below the fold; the browser helper clicks where a thing is now,
    so each click on the project settings page first scrolls its target into view (the tabs used to keep it on screen)."""
    click = b.click

    def scrolled(sel, *a, **kw):
        b.eval(f"(()=>{{ const e=document.querySelector({sel!r}); if(e&&e.closest('#v-psettings')) e.scrollIntoView({{block:'center'}}); }})()")
        return click(sel, *a, **kw)
    b.click = scrolled


CATS = ["general", "people", "ws", "miles", "rep", "arch"]     # #247: sections (Workstreams in; Logos with the client report)


class ProjectSettings(LiveBrowserCase):
    shared_server = True

    @classmethod
    def load(cls, v):
        test_dashboard.populate(v)
        v.run(script="build_dashboard.py")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.original = (cls.v.root / ABC / "CLAUDE.md").read_text()

    @property
    def memory(self):
        return self.v.root / ABC / "CLAUDE.md"

    def text(self):
        return self.memory.read_text()

    def setUp(self):
        super().setUp()
        self.memory.write_text(self.original)
        scroll_clicks(self.b)
        self.b.reload("typeof go==='function' && LIVE")
        # the server is shared, so a test that changed the record puts it back (through the page's own functions)
        self.b.eval("(async()=>{ if(P.find(p=>p.code==='ABC').name!=='Example Programme') await renameProject('ABC','Example Programme'); if(projectState('ABC')!=='active') await setProjectActive('ABC',true); return 1; })()")
        self.b.eval("window.__errs=[]; addEventListener('error',e=>__errs.push(e.message)); addEventListener('unhandledrejection',e=>__errs.push(String(e.reason)))")

    def open(self, cat="general", code="ABC"):
        cat = {"logos": "rep"}.get(cat, cat)        # #247: the logos are in the Client report and logos section
        self.b.eval(f"go('psettings', {code!r}); psCat.value={cat!r}; navWrite(false)")
        self.b.wait(f"VIEW==='psettings' && !!document.querySelector('#psBody [data-pscard]') && document.querySelector('#pscats [aria-current=true]')?.dataset.pscat==={cat!r}")
        time.sleep(0.3)          # #247: the page jumps to the address's section a moment after it opens; click after that

    def line(self, label):
        m = re.search(r"\*\*" + re.escape(label) + r":\*\*[ \t]*([^\n]*)", self.text())
        return m.group(1).strip() if m else None

    def wait_for(self, fn, what, timeout=8):
        end = time.time() + timeout
        while time.time() < end:
            if fn():
                return
            time.sleep(0.1)
        self.fail(what)

    def change(self, sel, value):
        self.b.eval(f"(()=>{{ const e=document.querySelector({sel!r}); e.value={value!r}; e.dispatchEvent(new Event('change',{{bubbles:true}})); }})()")

    CLEARED = "document.querySelector('#psPartnerIn').value===''"

    def set_partner(self, name):
        self.b.eval(f"(()=>{{ const e=document.querySelector('#psPartnerIn'); e.value={name!r}; e.dispatchEvent(new Event('input',{{bubbles:true}})); }})()")
        self.b.click("#psAddPartner")

    # ----- the doors (the project page cog, Settings; the Projects list rows have none)

    def test_the_page_opens_from_the_cog_at_the_foot_of_the_project_page(self):
        b = self.b
        b.eval("go('cockpit','ABC')")
        b.wait("VIEW==='cockpit' && !!document.querySelector('.cockfoot [data-psettings=ABC]')")
        self.assertEqual(b.eval("document.querySelector('.cockfoot [data-psettings]').getAttribute('aria-label')"), "Project settings")
        order = b.eval("[...document.querySelectorAll('.cockfoot [aria-label]')].map(x=>x.getAttribute('aria-label'))")
        self.assertEqual(order, ["Reports", "Browse files", "Project settings"])
        b.click(".cockfoot [data-psettings=ABC]")
        b.wait("VIEW==='psettings'")
        self.assertEqual(b.eval("location.hash"), "#project-settings=ABC")
        self.assertEqual(b.eval("document.querySelector('#psTitle').textContent"), "Project settings")
        self.assertIn("Each change saves on its own, with Undo.", b.eval("document.querySelector('#psSub').textContent"))
        self.assertEqual(b.eval("document.querySelector('#v-psettings .crumb').textContent"), "Projects›Example Programme›Settings")

    def test_the_projects_list_has_no_cog_in_its_rows(self):
        """Alan, 19-10-2026: the cog is on the project page (the cockpit) and in Settings; the Projects list rows carry none."""
        b = self.b
        b.eval("go('projects')")
        b.wait("VIEW==='projects' && !!document.querySelector('#projTbl tbody tr')")
        self.assertEqual(b.eval("document.querySelectorAll('#projTbl [data-psettings], #pfTbl [data-psettings]').length"), 0)

    def test_the_old_settings_addresses_open_the_projects_page_or_the_projects_settings(self):
        """The Settings line (v2.6) deliberately retired Settings › People and projects' list: its old addresses open the
        Projects page, and Workstreams from a project opens that project's settings at Workstreams. What the list held is
        here: each project's client report switch and its Archive."""
        b = self.b
        b.eval("go('today'); go('settings','projects')")
        b.wait("VIEW==='projects' && location.hash==='#projects'")
        b.eval("go('cockpit','DEF'); go('settings','workstreams')")
        b.wait("VIEW==='psettings' && psCode.value==='DEF' && psCat.value==='ws' && !!document.querySelector('#psWs')")
        self.assertEqual(b.eval("document.querySelector('#psName').value"), "Digital Enablement")
        self.assertTrue(b.eval("!!document.querySelector('#psRepOn')"), "the client report switch is here")
        self.assertTrue(b.eval("!!document.querySelector('#psArchive,#psRestore')"), "Archive (or Restore) is here")

    def test_the_address_restores_the_project_and_the_category_and_back_works(self):
        b = self.b
        self.open("people")
        self.assertEqual(b.eval("location.hash"), "#project-settings=ABC&c=people")
        b.goto(self.base + "/#project-settings=ABC&c=miles")
        b.wait("typeof go==='function' && LIVE && VIEW==='psettings'")
        b.wait("document.querySelector('#pscats [aria-current=true]').dataset.pscat==='miles'")
        b.eval("history.back()")
        self.assertEqual(b.eval("(parseHash('#project-settings=NOPE')===null)"), True)

    # ----- the categories

    def test_the_sections_are_these_six_with_workstreams(self):          # #247: was test_the_categories_are_these_six_and_there_is_no_workstreams (tabs)
        b = self.b
        self.open()
        self.assertEqual(b.eval("[...document.querySelectorAll('#pscats [data-pscat]')].map(t=>t.dataset.pscat)"), CATS)
        labels = b.eval("[...document.querySelectorAll('#pscats [data-pscat]')].map(t=>t.textContent.trim())")
        self.assertEqual(labels, ["Project", "People and partners", "Workstreams", "Milestones", "Client report and logos", "Archive and close"])
        self.assertEqual(b.eval("document.querySelectorAll('#pscats [role=tab]').length"), 0)

    def test_each_category_shows_its_content(self):
        b = self.b
        self.open("general")
        self.assertEqual(b.eval("document.querySelector('#psName').value"), "Example Programme")
        self.assertEqual(b.eval("document.querySelector('#psClient').value"), "Example Client Ltd")
        self.assertEqual(b.eval("document.querySelector('#psCode').textContent"), "ABC")
        self.assertEqual(b.eval("document.querySelector('#psStatus').value"), "active")
        self.assertIn("projects/ABC", b.eval("document.querySelector('#psFolder').textContent"))
        self.open("people")
        self.assertTrue(b.eval("[...document.querySelectorAll('#psPeople tbody tr')].length>0"))
        self.assertEqual(b.eval("[...document.querySelectorAll('#psPeople thead th')].slice(0,3).map(x=>x.textContent)"), ["Name", "Email", "Organisation · role"])   # #247: the register's own columns
        self.assertTrue(b.eval("!!document.querySelector('#psPartners') && !!document.querySelector('#psAddPartner') && !!document.querySelector('#psAddPerson')"))
        self.open("miles")
        ids = b.eval("[...document.querySelectorAll('#psMiles tbody tr td:first-child')].map(x=>x.textContent)")
        self.assertEqual(ids, ["ABC-M-001", "ABC-M-002"])
        self.assertTrue(b.eval("!!document.querySelector('#psAddMs') && !!document.querySelector('#psMsPage')"))
        self.assertRegex(b.eval("document.querySelector('#psMiles tbody tr').textContent"), r"\d\d-\d\d-\d{4}")      # DD-MM-YYYY
        self.open("arch")
        self.assertTrue(b.eval("!!document.querySelector('#psArchive') && !!document.querySelector('#psClose')"))
        self.open("logos")        # #228 C: the placeholders are real rows now (was: a button that opened the cog panel)
        self.assertEqual(b.eval("[...document.querySelectorAll('#psBody .pslogo')].map(x=>x.dataset.kind)"), ["firm", "client", "partner"])
        self.open("rep")
        self.assertTrue(b.eval("!!document.querySelector('#psRepOn') && !!document.querySelector('#psRepHub')"))

    def test_the_placeholders_are_gone_and_open_reporting_still_opens_the_hub(self):       # #228 C: was test_the_logos_and_reporting_placeholders_open_the_existing_cog_panel
        b = self.b
        self.open("rep")
        self.assertFalse(b.eval("!!document.querySelector('#psRepOpen') || !!document.querySelector('#psLogosOpen')"))
        b.click("#psRepHub")
        b.wait("VIEW==='reporting'")

    def test_milestones_use_the_existing_add_and_edit_flows(self):
        b = self.b
        self.open("miles")
        b.click("[data-psms-edit='ABC-M-001']")
        b.wait("VIEW==='milestones' && !!document.querySelector('#mvPeek')")
        self.open("miles")
        b.click("#psAddMs")
        b.wait("VIEW==='milestones' && !!shared.MV.add")
        self.open("miles")
        b.click("#psMsPage")
        b.wait("VIEW==='milestones' && MSCODE==='ABC'")

    # ----- General saves through the existing path

    def test_editing_the_name_saves_through_the_project_update_with_undo(self):
        b = self.b
        self.open("general")
        self.change("#psName", "Example Programme Two")
        self.wait_for(lambda: b.eval("P.find(p=>p.code==='ABC').name") == "Example Programme Two", "the page has the new name")
        self.wait_for(lambda: b.eval("document.querySelector('#snackU').style.display") != "none"
                      and "saved and applied" in b.eval("document.querySelector('#snackT').textContent"), "saved, with Undo offered")
        b.reload("typeof go==='function' && LIVE")                                          # the record, not just the page
        self.assertEqual(b.eval("P.find(p=>p.code==='ABC').name"), "Example Programme Two")
        self.open("general")
        self.change("#psName", "Example Programme Three")
        self.wait_for(lambda: b.eval("P.find(p=>p.code==='ABC').name") == "Example Programme Three", "renamed again")
        self.wait_for(lambda: "saved and applied" in b.eval("document.querySelector('#snackT').textContent"), "applied")
        b.click("#snackU")
        self.wait_for(lambda: b.eval("P.find(p=>p.code==='ABC').name") == "Example Programme Two", "Undo puts the name back")

    def test_an_empty_name_is_refused_in_plain_words_and_nothing_is_saved(self):
        b = self.b
        self.open("general")
        self.change("#psName", "   ")
        b.wait("!!document.querySelector('#psNameErr')")
        self.assertEqual(b.eval("document.querySelector('#psNameErr').textContent"), "Type the project's name.")
        self.assertEqual(b.eval("P.find(p=>p.code==='ABC').name"), "Example Programme")

    def test_editing_the_client_writes_the_existing_client_line(self):
        self.open("general")
        self.change("#psClient", "Harbour Foods Ltd")
        self.wait_for(lambda: self.line("Client / partner") == "Harbour Foods Ltd", "the client line is written")

    def test_the_status_closes_and_reopens_with_a_confirm_for_close_in_archive(self):
        b = self.b
        self.open("arch")
        b.click("#psClose")
        b.wait("!!document.querySelector('#psCloseYes')")
        self.assertIn("Close Example Programme?", b.eval("document.querySelector('#psCloseYes').parentElement.textContent"))
        b.click("#psCloseNo")
        b.wait("!!document.querySelector('#psClose')")
        self.assertEqual(b.eval("projectState('ABC')"), "active")
        b.click("#psClose")
        b.wait("!!document.querySelector('#psCloseYes')")
        b.click("#psCloseYes")
        self.wait_for(lambda: b.eval("projectState('ABC')") == "closed", "the project is closed")
        self.wait_for(lambda: b.eval("!!document.querySelector('#psReopen')"), "Reopen replaces Close")
        b.click("#psReopen")
        self.wait_for(lambda: b.eval("projectState('ABC')") == "active", "the project is active again (restore)")

    def test_archive_asks_first_then_goes_on_the_approval_card(self):
        b = self.b
        self.open("arch")
        b.click("#psArchive")
        b.wait("!!document.querySelector('#psArchiveYes')")
        b.click("#psArchiveNo")
        self.assertTrue(b.eval("!!document.querySelector('#psArchive')"))
        b.click("#psArchive")
        b.click("#psArchiveYes")
        # ABC has open items: creaite asks to cancel them all first (the existing dialog), or goes on the card
        b.wait("!!document.querySelector('#parchDlg[open]') || /approval card/.test(document.querySelector('#snackT').textContent)", timeout=15)

    # ----- People and partners

    def test_the_project_people_show_their_organisation_from_the_register(self):
        b = self.b
        self.open("people")
        rows = b.eval("[...document.querySelectorAll('#psPeople tbody tr')].map(r=>[...r.children].slice(0,3).map(c=>c.textContent.trim()))")
        names = [r[0] for r in rows]
        self.assertTrue(any(n.startswith("Sara Example") for n in names), names)     # #247: the cell also carries "needs details" and project codes

    def test_the_partners_line_round_trip(self):
        b = self.b
        self.open("people")
        self.set_partner("Northgate Analytics")
        self.wait_for(lambda: self.line("Partners") == "Northgate Analytics", "the Partners line is written in the project's memory file")
        self.assertIn("- **Partners:** Northgate Analytics", self.text())
        self.assertTrue(list((self.v.root / "system/backups/files").glob("ABC-CLAUDE-*.md")), "a backup of the file was kept first")
        b.wait(self.CLEARED)   # the add has finished (it clears the box after the save), so the next name isn't wiped
        self.set_partner("Harbour Labs")
        self.wait_for(lambda: self.line("Partners") == "Northgate Analytics; Harbour Labs", "a second partner")
        # reload: the list is read back from the file
        b.reload("typeof go==='function' && LIVE")
        self.open("people")
        b.wait("document.querySelectorAll('#psPartners [data-pspartner]').length===2")
        self.assertEqual(b.eval("[...document.querySelectorAll('#psPartners [data-pspartner]')].map(x=>x.textContent)"), ["Northgate Analytics", "Harbour Labs"])
        # the rest of the file is as it was
        self.assertIn("- **Client / partner:** Example Client Ltd", self.text())
        # remove one, with Undo
        b.click("[data-pspartner-remove][aria-label='Remove Northgate Analytics']")
        self.wait_for(lambda: self.line("Partners") == "Harbour Labs", "a partner is removed")
        b.wait("/removed from the partners/.test(document.querySelector('#snackT').textContent)")
        b.eval("shared.UNDO && shared.UNDO()")
        self.wait_for(lambda: self.line("Partners") == "Northgate Analytics; Harbour Labs", "Undo puts the partner back")
        # remove all: an empty line, the page says none
        b.click("[data-pspartner-remove][aria-label='Remove Harbour Labs']")
        b.click("[data-pspartner-remove][aria-label='Remove Northgate Analytics']")
        self.wait_for(lambda: self.line("Partners") == "", "no partners")
        b.wait("!document.querySelector('[data-pspartner]')")
        self.assertEqual(self.text().count("**Partners:**"), 1, "one line, never a second")

    def test_a_duplicate_partner_is_refused_whatever_the_capitals(self):
        b = self.b
        self.open("people")
        self.set_partner("Northgate Analytics")
        self.wait_for(lambda: self.line("Partners") == "Northgate Analytics", "first saved")
        b.wait(self.CLEARED)
        self.set_partner("  northgate   ANALYTICS ")
        b.wait("!!document.querySelector('#psPartnerErr')")
        self.assertEqual(b.eval("document.querySelector('#psPartnerErr').textContent"), "Northgate Analytics is already listed.")
        self.assertEqual(self.line("Partners"), "Northgate Analytics")

    def test_a_partner_is_one_line_not_empty_not_long_and_has_no_semicolon(self):
        b = self.b
        self.open("people")
        for name, said in (("   ", "Type the partner organisation's name."),
                           ("A;B", "A partner's name can't contain a semicolon; add each partner on its own."),
                           ("x" * 61, "A partner's name is over 60 characters.")):
            self.set_partner(name)
            if said:
                b.wait("!!document.querySelector('#psPartnerErr')")
                self.assertEqual(b.eval("document.querySelector('#psPartnerErr').textContent"), said)
        self.assertEqual(b.eval("partnerProblem([],'a\\nb')"), "A partner's name is one line.")
        self.assertEqual(b.eval("partnerProblem([],'x'.repeat(61))"), "A partner's name is over 60 characters.")      # #228 C: 60, was 80
        self.assertIsNone(self.line("Partners"), "nothing was written")

    def test_a_newline_never_reaches_the_file(self):
        b = self.b
        self.open("people")
        b.eval("addPartner('ABC','Evil\\n- **Client report:** off')")
        time.sleep(0.5)
        self.assertEqual(self.text(), self.original)

    def test_a_partner_can_be_renamed(self):
        b = self.b
        self.open("people")
        self.set_partner("Northgate Analytics")
        self.wait_for(lambda: self.line("Partners") == "Northgate Analytics", "saved")
        b.click("[data-pspartner-rename]")
        self.change("[data-pspartner-edit]", "Northgate Data")
        b.click("[data-pspartner-save]")
        self.wait_for(lambda: self.line("Partners") == "Northgate Data", "renamed")

    def test_a_changed_memory_file_is_never_written_over(self):
        """setMemLine's refusal: the file changed in another window since it was read (the way the client report settings behave)."""
        b = self.b
        self.open("people")
        b.eval("window.__real=shared.VW.read; shared.VW.read=async p=>{ const t=await window.__real.call(shared.VW,p); window.__n=(window.__n||0)+1; return window.__n%2===1?t:t+'\\nsomeone else typed this\\n'; }")
        self.set_partner("Northgate Analytics")
        time.sleep(1.0)
        self.assertNotIn("Partners", self.text())
        b.eval("shared.VW.read=window.__real")

    def test_a_save_updates_the_partners_the_logo_tiles_read_without_a_reload(self):
        b = self.b
        self.open("people")
        self.set_partner("Northgate Analytics")
        self.wait_for(lambda: b.eval("(P.find(p=>p.code==='ABC').partners||[]).map(x=>x.name).join('|')") == "Northgate Analytics",
                      "P[].partners follows the line, with the slug the server made")
        self.assertEqual(b.eval("P.find(p=>p.code==='ABC').partners[0].slug"), "northgate-analytics")
        self.assertEqual(b.eval("logoKindsOf('ABC')"), ["firm", "client", "partner:northgate-analytics"])

    def test_at_most_twelve_partners(self):
        b = self.b
        self.open("people")
        self.memory.write_text(self.text().replace("- **Client report rhythm:** fortnightly",
                               "- **Client report rhythm:** fortnightly\n- **Partners:** " + "; ".join(f"Org {i}" for i in range(12))))
        b.eval("loadPartners('ABC')")
        b.wait("document.querySelectorAll('#psPartners [data-pspartner]').length===12")
        self.set_partner("One too many")
        b.wait("!!document.querySelector('#psPartnerErr')")
        self.assertEqual(b.eval("document.querySelector('#psPartnerErr').textContent"), "A project lists at most 12 partner organisations.")

    def test_a_partner_with_a_logo_offers_removing_it_before_a_rename_or_removal_leaves_it_behind(self):
        b = self.b
        logos = self.v.root / "system/branding/logos"
        logos.mkdir(parents=True, exist_ok=True)
        for f in logos.glob("*"):
            f.unlink()
        self.open("people")
        self.set_partner("Northgate Analytics")
        self.wait_for(lambda: b.eval("(P.find(p=>p.code==='ABC').partners||[]).length") == 1, "saved")
        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg==")
        (logos / "ABC-partner-northgate-analytics.png").write_bytes(png)
        b.eval("readClientLogos('ABC')")
        b.wait("!!document.querySelector('[data-pspartner-logo=\"partner:northgate-analytics\"]')")
        b.click("[data-pspartner-logo]")
        self.wait_for(lambda: not list(logos.glob("ABC-partner-northgate-analytics.*")), "the logo file is removed")
        b.wait("!document.querySelector('[data-pspartner-logo]')")

    # ----- the page as a whole

    def test_search_finds_a_category_and_its_rows(self):
        b = self.b
        self.open("general")
        self.b.eval("(()=>{ const e=document.querySelector('#psq'); e.value='milestone'; e.dispatchEvent(new Event('input',{bubbles:true})); })()")
        b.wait("!!document.querySelector('#psMiles') && !document.querySelector('#psMiles').closest('[data-pscard]').hidden && document.querySelector('#psName').closest('[data-pscard]').hidden")
        self.assertEqual(b.eval("document.querySelector('#pscats [aria-current=true]')"), None)      # nothing marked while searching
        self.b.eval("(()=>{ const e=document.querySelector('#psq'); e.value='folder'; e.dispatchEvent(new Event('input',{bubbles:true})); })()")
        b.wait("!document.querySelector('#psFolder').closest('[data-psrow]').hidden && document.querySelector('#psMiles').closest('[data-pscard]').hidden")
        self.assertEqual(b.eval("[...document.querySelectorAll('#psBody .srow:not([hidden])')].map(r=>r.firstElementChild.firstElementChild.textContent)"), ["Folder", "Archive this project"])
        self.b.eval("(()=>{ const e=document.querySelector('#psq'); e.value='zzzz nothing'; e.dispatchEvent(new Event('input',{bubbles:true})); })()")
        b.wait("!document.querySelector('#psNone').hidden")
        self.assertIn("No settings match", b.eval("document.querySelector('#psNone').textContent"))
        self.b.eval("(()=>{ const e=document.querySelector('#psq'); e.value='Archive'; e.dispatchEvent(new Event('input',{bubbles:true})); })()")
        b.wait("!document.querySelector('#psArchive').closest('[data-pscard]').hidden")

    def test_the_sections_list_is_keyboard_operable(self):        # #247: links, so Tab and Enter (was ArrowDown and End on tabs)
        b = self.b
        self.open("general")
        b.eval("document.querySelector('#pscats [data-pscat=people]').focus()")
        b.key("Enter")
        b.wait("document.querySelector('#pscats [aria-current=true]').dataset.pscat==='people'")
        b.eval("document.querySelector('#pscats [data-pscat=arch]').focus()")
        b.key("Enter")
        b.wait("document.querySelector('#pscats [aria-current=true]').dataset.pscat==='arch'")
        self.assertEqual(b.eval("document.activeElement.dataset.pscat"), "arch")

    def test_no_duplicate_ids_on_any_category_and_no_script_errors(self):
        b = self.b
        for cat in CATS:
            self.open(cat)
            dup = b.eval("(()=>{ const c={}; document.querySelectorAll('[id]').forEach(e=>c[e.id]=(c[e.id]||0)+1); return Object.keys(c).filter(k=>c[k]>1); })()")
            self.assertEqual(dup, [], f"duplicate ids on {cat}")
        self.assertEqual(b.eval("__errs"), [])

    def test_every_control_has_a_name(self):
        b = self.b
        for cat in CATS:
            self.open(cat)
            bad = b.eval("""[...document.querySelectorAll('#psBody input,#psBody select,#psBody button')].filter(e=>{
                if(e.hidden||e.type==='hidden') return false;
                const n=(e.getAttribute('aria-label')||e.getAttribute('aria-labelledby')||e.textContent||'').trim()||(e.id&&document.querySelector('label[for='+e.id+']')?'x':'');
                return !n; }).map(e=>e.outerHTML.slice(0,80))""")
            self.assertEqual(bad, [], f"unnamed controls on {cat}")

    def test_no_horizontal_scroll_at_900_and_1400_in_both_palettes_light_and_dark(self):
        b = self.b
        for width in (900, 1400):
            b.resize(width, 900)
            for palette in TEST_PALETTES:
                for mode in ("light", "dark"):
                    b.eval(f"document.documentElement.dataset.palette='{palette}'; document.documentElement.dataset.theme='{mode}'")
                    for cat in ("general", "people", "logos", "miles", "rep"):
                        self.open(cat)
                        over = b.eval("document.documentElement.scrollWidth-document.documentElement.clientWidth")
                        self.assertLessEqual(over, 0, f"{cat} overflows at {width} ({palette} {mode})")
        b.resize(1400, 1000)

    def test_the_page_uses_tokens_for_font_size_and_radius(self):
        css = (Path(__file__).resolve().parents[2] / "system/templates/dashboard/style.css").read_text()
        start = css.index("#228: the full-page project settings")
        end = next((m.start() for m in re.finditer(r"\n/\* ", css[start:]) if not css[start + m.start() + 4:].startswith("#228")), len(css) - start)
        mine = css[start:start + end]                       # this page's block only: the next feature's comment ends it
        self.assertNotRegex(mine, r"font-size:\s*\d+px")
        self.assertNotRegex(mine, r"border-radius:\s*\d+px")

    def test_a_project_that_is_not_open_says_so(self):
        b = self.b
        b.eval("go('psettings','ABC')")
        b.wait("VIEW==='psettings'")
        self.assertEqual(b.eval("go('psettings','NOPE')"), False)


if __name__ == "__main__":
    unittest.main()
