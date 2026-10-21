"""#204: Cockpit and Milestones opened with no project chosen show "Choose a project" and the projects as links (UX review
findings 11 and 19), and a vault with no projects says so. A real browser against the real live server, at 1400 and 900 wide,
with the clock fixed.

Run: python3 dev/tests/test_choose_project.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402

NOW = "2026-10-14 09:00"


class Base(LiveBrowserCase):
    shared_server = True

    @classmethod
    def load(cls, v):
        populate(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": NOW}

    def chooser(self):
        return self.b.eval("(()=>{ const v=document.querySelector('.view:not([hidden])'), h=v&&v.querySelector('h1');"
                           " return {view:VIEW, h1:h&&h.textContent, links:[...v.querySelectorAll('a[data-choose]')].map(a=>[a.dataset.code,a.querySelector('.chname').textContent,!!a.querySelector('.health')])}; })()")


class WithProjects(Base):
    width = 1400

    def test_cockpit_with_no_project(self):
        b = self.b
        b.eval("go('cockpit')")
        b.wait("document.querySelector('#v-cockpit a[data-choose]')")
        c = self.chooser()
        self.assertEqual((c["view"], c["h1"]), ("cockpit", "Choose a project"))
        self.assertEqual([x[:2] for x in c["links"]], [["ABC", "Example Programme"], ["DEF", "Digital Enablement"]])
        self.assertTrue(all(x[2] for x in c["links"]))                     # health shown as elsewhere
        self.assertEqual(b.eval("location.hash"), "#cockpit")
        self.assertEqual(b.errors, [])

    def test_milestones_with_no_project(self):
        b = self.b
        b.eval("go('milestones')")
        b.wait("document.querySelector('#v-milestones a[data-choose]')")
        c = self.chooser()
        self.assertEqual((c["view"], c["h1"]), ("milestones", "Choose a project"))
        self.assertEqual(len(c["links"]), 2)
        self.assertEqual(b.eval("location.hash"), "#milestones&v=plan")
        self.assertEqual(b.errors, [])

    def test_a_click_opens_the_project_on_the_same_page(self):
        b = self.b
        b.eval("go('milestones')")
        b.wait("document.querySelector('#v-milestones a[data-choose]')")
        b.click('#v-milestones a[data-code="DEF"]')
        b.wait("VIEW==='milestones'&&MSCODE==='DEF'&&document.querySelector('#v-milestones .mv-pageh')")
        self.assertEqual(b.eval("location.hash"), "#milestones=DEF&v=plan")
        b.eval("go('cockpit')")
        b.wait("document.querySelector('#v-cockpit a[data-choose]')")
        b.click('#v-cockpit a[data-code="ABC"]')
        b.wait("VIEW==='cockpit'&&COCK==='ABC'&&!document.querySelector('#v-cockpit a[data-choose]')")

    def test_enter_on_a_focused_project_opens_it_and_the_address_works(self):
        b = self.b
        b.eval("go('cockpit')")
        b.wait("document.querySelector('#v-cockpit a[data-choose]')")
        b.eval("document.querySelector('#v-cockpit a[data-code=\"DEF\"]').focus()")
        b.key("Enter")
        b.wait("VIEW==='cockpit'&&COCK==='DEF'")
        b.eval("restoreNav(parseHash('#cockpit'))")
        b.wait("document.querySelector('#v-cockpit a[data-choose]')")


class Narrow(WithProjects):
    width = 900


class NoProjects(Base):
    width = 1400

    def test_no_projects_says_so(self):
        b = self.b
        b.eval("P.splice(0)")                                              # an empty vault's page: no projects in the data
        for page in ("cockpit", "milestones"):
            b.eval(f"go('{page}')")
            b.wait(f"document.querySelector('#v-{page} .choose .empty')")
            self.assertEqual(b.eval(f"document.querySelector('#v-{page} h1').textContent"), "Choose a project")
            self.assertEqual(b.eval(f"document.querySelector('#v-{page} .empty').textContent"),
                             "No projects yet. Add one on the Projects page.")     # the Settings line: projects are added there
            b.click(f"#v-{page} .empty a")
            b.wait("VIEW==='projects'")
        self.assertEqual(b.errors, [])

    def test_enter_on_the_link_opens_the_projects_page(self):
        b = self.b
        b.eval("P.splice(0)")
        b.eval("go('cockpit')")
        b.wait("document.querySelector('#v-cockpit .empty a')")
        b.eval("document.querySelector('#v-cockpit .empty a').focus()")
        b.key("Enter")
        b.wait("VIEW==='projects'")
        b.wait("location.hash==='#projects'", 10)                           # the link and its words agree: the Projects page
        # the Settings line: People and projects left Settings; a project is added from the Projects page (in ask creaite)
        b.wait("!!document.querySelector('#projTbl .empty [data-setup=proj]')")
        b.click("#projTbl .empty [data-setup=proj]")                         # there, Add a project starts it in ask creaite, unsent
        b.wait("document.getElementById('chat').classList.contains('on') && document.getElementById('chIn').value==='add project '")
        self.assertEqual(b.errors, [])

if __name__ == "__main__":
    unittest.main()
