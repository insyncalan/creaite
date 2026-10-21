"""#204 (UX review 11 and 19): the project cockpit and Milestones, opened with no project chosen, say "Choose a project" and list the
projects by full name, instead of drawing a blank page. A real browser against the real live server, at 1400 and 900 px; the list
is reached by Tab and Enter opens the page for that project.

Run: python3 dev/tests/test_choose_project.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

PAGES = (("cockpit", "v-cockpit"), ("milestones", "v-milestones"))


class ChooseProject(LiveBrowserCase):
    shared_server = True

    def open_bare(self, view):
        b = self.b
        b.eval("S.autoApply=true")
        b.eval(f"go({view!r})")
        b.wait(f"VIEW=={view!r}")

    def test_no_project_shows_the_prompt_and_the_projects_by_name(self):
        b = self.b
        names = b.eval("P.filter(p=>p.active!==false&&!p.archived).map(p=>p.name)")
        codes = b.eval("P.map(p=>p.code)")
        self.assertGreaterEqual(len(names), 2)
        for width in (1400, 900):
            b.resize(width, 900)
            for view, el in PAGES:
                with self.subTest(width=width, view=view):
                    self.open_bare(view)
                    text = b.eval(f"document.getElementById({el!r}).innerText")
                    self.assertIn("Choose a project", text)
                    links = b.eval(f"[...document.querySelectorAll('#{el} .chooseproj a')].map(a=>a.textContent.trim())")
                    self.assertEqual(links, names)
                    for c in codes:
                        self.assertNotIn(c, links)
                    # the list sits inside the window at this width: no sideways scroll, every link on screen
                    if view == "milestones":
                        self.assertEqual(b.eval("location.hash"), "#milestones")
                    self.assertTrue(b.eval(
                        f"[...document.querySelectorAll('#{el} .chooseproj a')].every(a=>{{ const r=a.getBoundingClientRect(); return r.left>=0&&r.right<=innerWidth&&r.width>0; }})"))
                    self.assertLessEqual(b.eval("document.documentElement.scrollWidth"), width)

    def test_tab_reaches_the_list_and_enter_opens_the_project(self):
        b = self.b
        for width in (1400, 900):
            b.resize(width, 900)
            for view, el in PAGES:
                with self.subTest(width=width, view=view):
                    self.open_bare(view)
                    b.eval(f"(()=>{{ const h=document.querySelector('#{el} .chooseproj h2'); h.tabIndex=-1; h.focus(); }})()")      # Tab goes on from the heading
                    in_list = f"!!document.activeElement.closest&&!!document.activeElement.closest('#{el} .chooseproj')"
                    b.key("Tab")
                    self.assertTrue(b.eval(in_list), "Tab did not reach the project list")
                    first = b.eval("document.activeElement.textContent.trim()")
                    b.key("Enter")
                    code = b.eval(f"P.find(p=>p.name==={first!r}).code")
                    b.wait(f"VIEW==={view!r}&&{'COCK' if view == 'cockpit' else 'MSCODE'}==={code!r}")
                    self.assertIn(first, b.eval(f"document.getElementById({el!r}).innerText"))
                    self.assertNotIn("Choose a project", b.eval(f"document.getElementById({el!r}).innerText"))

    def test_a_chosen_project_still_opens_without_the_prompt(self):
        b = self.b
        b.eval("go('cockpit','ABC')")
        b.wait("VIEW==='cockpit'&&document.querySelector('#v-cockpit h1')")
        self.assertNotIn("Choose a project", b.eval("document.getElementById('v-cockpit').innerText"))


if __name__ == "__main__":
    unittest.main()
