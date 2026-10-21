"""#285: the project page (cockpit) has no project switcher: no dropdown, no ‹ › arrows and no [ ] keys. Every project
stays reachable: the Projects list, search (Cmd/Ctrl + K) and the project links on Today. The Milestones page keeps its
own ‹ › arrows but loses its dropdown. A real browser against the real live server.

Run: python3 dev/tests/test_cockpit_no_dropdown_285.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402


class CockpitNoSwitcher(LiveBrowserCase):
    shared_server = True

    def open(self, code):
        b = self.b
        b.eval(f"go('cockpit',{code!r})")
        b.wait(f"VIEW==='cockpit'&&COCK==={code!r}&&!!document.querySelector('#v-cockpit .hhead h1')")

    def test_no_switcher_on_the_project_page(self):
        self.open("ABC")
        b = self.b
        self.assertFalse(b.eval("!!document.getElementById('projSw')"))
        self.assertEqual(b.eval("document.querySelectorAll('#v-cockpit .hhead select').length"), 0)
        self.assertEqual(b.eval("document.querySelectorAll('#v-cockpit .pswitch,#v-cockpit [data-psw]').length"), 0)

    def test_square_bracket_keys_leave_the_project_page_alone(self):
        self.open("ABC")
        b = self.b
        for k in ("]", "["):                                               # each on its own: ] then [ would round-trip
            b.eval(f"document.body.focus(); document.dispatchEvent(new KeyboardEvent('keydown',{{key:{k!r},bubbles:true}}))")
            b.eval("new Promise(r=>setTimeout(r,300))")
            self.assertEqual(b.eval("[VIEW,COCK]"), ["cockpit", "ABC"], k)

    def test_projects_list_reaches_every_project(self):
        b = self.b
        b.eval("go('projects')")
        b.wait("VIEW==='projects'&&!!document.querySelector('#projTbl [data-cock]')")
        codes = b.eval("P.map(p=>p.code)")
        self.assertGreaterEqual(len(codes), 2)
        self.assertTrue(set(codes) <= set(b.eval("[...document.querySelectorAll('#projTbl [data-cock]')].map(e=>e.dataset.cock)")))
        last = codes[-1]
        b.eval(f"document.querySelector('#projTbl [data-cock=\"{last}\"]').click()")
        b.wait(f"VIEW==='cockpit'&&COCK==={last!r}")

    def test_search_reaches_every_project(self):
        b = self.b
        for p in b.eval("P.map(p=>({code:p.code,name:p.name}))"):
            b.eval("go('today')")
            b.wait("VIEW==='today'")
            b.eval("openCk()")
            b.wait("document.getElementById('cmdk').open")
            b.eval(f"(()=>{{ const i=document.getElementById('cmdkIn'); i.value={p['name']!r}; i.dispatchEvent(new Event('input',{{bubbles:true}})); }})()")
            hit = b.eval(f"(()=>{{ const x=[...document.querySelectorAll('#cmdkList button')].find(e=>e.textContent.includes({p['name']!r})); if(x) x.click(); return !!x; }})()")
            self.assertTrue(hit, p)
            b.wait(f"VIEW==='cockpit'&&COCK==={p['code']!r}")

    def test_today_links_open_a_project(self):
        b = self.b
        b.eval("go('today')")
        b.wait("VIEW==='today'&&!!document.querySelector('#v-today [data-cock]')")
        code = b.eval("document.querySelector('#v-today [data-cock]').dataset.cock")
        b.eval("document.querySelector('#v-today [data-cock]').click()")
        b.wait(f"VIEW==='cockpit'&&COCK==={code!r}")

    # Milestones page (#285 follow-up): its dropdown goes; its ‹ › arrows stay (it never had [ ] keys). A project's
    # milestones stay reachable from the project page's Milestones card, the Projects list (via the project page), the
    # address #milestones=CODE and the arrows.
    def mv_wait(self, code):
        self.b.wait(f"VIEW==='milestones'&&MSCODE==={code!r}&&!!document.querySelector('#v-milestones .mv-pageh h1')")

    def test_milestones_has_no_dropdown_but_keeps_its_arrows(self):
        b = self.b
        b.eval("go('milestones','ABC')")
        self.mv_wait("ABC")
        self.assertFalse(b.eval("!!document.getElementById('mvProjSw')"))
        self.assertEqual(b.eval("document.querySelectorAll('#v-milestones .mv-pageh select').length"), 0)
        self.assertEqual(b.eval("[...document.querySelectorAll('#v-milestones [data-mvpsw]')].map(e=>e.dataset.mvpsw)"), ["-1", "1"])
        codes = b.eval("P.map(p=>p.code)")
        nxt = codes[(codes.index("ABC") + 1) % len(codes)]
        b.eval("document.querySelector('#v-milestones [data-mvpsw=\"1\"]').click()")
        self.mv_wait(nxt)
        b.eval("document.querySelector('#v-milestones [data-mvpsw=\"-1\"]').click()")
        self.mv_wait("ABC")

    def test_milestones_reached_from_the_project_page(self):
        b = self.b
        b.eval("go('projects')")
        b.wait("VIEW==='projects'&&!!document.querySelector('#projTbl [data-cock]')")
        for code in b.eval("P.map(p=>p.code)"):
            b.eval("go('projects')")
            b.wait("VIEW==='projects'&&!!document.querySelector('#projTbl [data-cock]')")
            b.eval(f"document.querySelector('#projTbl [data-cock=\"{code}\"]').click()")
            b.wait(f"VIEW==='cockpit'&&COCK==={code!r}&&!!document.querySelector('#v-cockpit [data-mvpage]')")
            b.eval(f"document.querySelector('#v-cockpit [data-mvpage=\"{code}\"]').click()")
            self.mv_wait(code)
            b.eval(f"document.querySelector('#v-milestones .crumb [data-proj=\"{code}\"]').click()")   # and back by the breadcrumb
            b.wait(f"VIEW==='cockpit'&&COCK==={code!r}")

    def test_milestones_reached_by_address(self):
        b = self.b
        for code in b.eval("P.map(p=>p.code)"):
            b.eval(f"history.replaceState(null,'',location.pathname+'#milestones={code}&v=plan')")
            b.reload("typeof go==='function' && LIVE")
            self.mv_wait(code)
            self.assertIn(f"#milestones={code}", b.eval("location.hash"))

if __name__ == "__main__":
    unittest.main()
