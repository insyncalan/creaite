"""#139 the rail's hover flyouts on Projects, Work and More (one shared hover behaviour), in a real browser.

Run: python3 dev/tests/test_rail_flyouts.py   (needs Google Chrome; skipped otherwise)

Done when:
- pointing at Projects opens a list of the ACTIVE projects by full name (never a code; an archived or a closed project is
  absent, and one added or closed while the page is open shows the change); pointing at Work lists Actions, RAID, Decisions
  and All items; pointing at More opens its menu with no click. Leaving folds about 220 ms later, and moving onto the flyout
  keeps it open; one flyout is open at a time;
- clicking the icon alone still goes to the page (Projects, Work) and clicking More still toggles its menu; a pick opens that
  project's page or Work at that list;
- keyboard: the buttons stay in their Tab order; ArrowRight or ArrowDown opens with focus in the list, arrows move, Enter
  picks, Esc (or ArrowLeft) closes with focus back on the rail button; aria-haspopup="menu" and aria-expanded on the button;
- the rail collapsed and expanded, at 1400 and 900 px: the flyout sits to the right of the rail, inside the window, and the
  collapsed Projects and Work buttons' tooltip gives way to it; More's badge and tooltip behave as before.
"""
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("CREAITE_NO_LAUNCH", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

ARCH, CLOSED = "Archived Demo Programme", "Closed Demo Programme"


class Flyouts(LiveBrowserCase):
    width, height = 1400, 900

    def seed(self):
        """An archived and a closed project in the page's data (not drawn anywhere but the flyout, so no page is visited after)."""
        self.b.eval(f"""(()=>{{ P.push({{code:'ZZA',name:{ARCH!r},active:true,archived:true,health:'On track'}},
          {{code:'ZZC',name:{CLOSED!r},active:false,health:'At risk'}}); }})()""")

    # ── helpers ──
    def point(self, x, y):
        self.b.call("Input.dispatchMouseEvent", type="mouseMoved", x=x, y=y, button="none")

    def hover(self, sel):
        p = self.b.box(sel)
        self.point(p["x"], p["y"])

    def away(self):
        self.point(700, 500)

    def btn(self, v):
        return f".rail #railMain [data-v={v}]" if v != "more" else "#railMore"

    def fly(self, v):
        return "#railMoreMenu" if v == "more" else f"#railFly-{v}"

    def expanded(self, v):
        return self.b.eval(f"document.querySelector('{self.btn(v)}').getAttribute('aria-expanded')")

    def open_by_hover(self, v):
        self.hover(self.btn(v))
        self.b.wait(f"document.querySelector('{self.btn(v)}').getAttribute('aria-expanded')==='true'", 5)
        self.b.wait(f"(e=>e&&!e.hidden&&e.getClientRects().length>0)(document.querySelector('{self.fly(v)}'))", 5)

    def names(self, v):
        return self.b.eval(f"[...document.querySelectorAll('{self.fly(v)} [role=menuitem]')].map(x=>x.firstChild.textContent.trim())")

    def collapse(self):
        if not self.b.eval("document.querySelector('.rail').classList.contains('collapsed')"):
            self.b.click("#railTog")
            self.b.wait("document.querySelector('.rail').classList.contains('collapsed')", 5)

    # ── what is in them ──
    def test_projects_lists_active_projects_by_name_only(self):
        b = self.b
        self.seed()
        self.open_by_hover("projects")
        got = self.names("projects")
        want = b.eval("P.filter(p=>p.active!==false&&!p.archived).map(p=>p.name)")
        self.assertTrue(want)
        self.assertEqual(got, want)
        self.assertNotIn(ARCH, got)
        self.assertNotIn(CLOSED, got)
        codes = b.eval("P.map(p=>p.code)")
        self.assertFalse([n for n in got if n in codes])                       # names, never codes
        self.assertEqual(b.eval(f"document.querySelectorAll('{self.fly('projects')} .health').length"), len(want))   # each with its health
        self.assertEqual(b.eval(f"document.querySelector('{self.fly('projects')}').getAttribute('role')"), "menu")
        self.assertEqual(b.eval(f"document.querySelector('{self.fly('projects')}').getAttribute('aria-label')"), "Projects")
        self.assertEqual(b.eval(f"document.querySelector('{self.fly('projects')} button').offsetHeight"), 24)

    def test_a_project_closed_or_added_while_open_shows_the_change(self):
        b = self.b
        self.seed()
        b.eval("P.push({code:'ZZN',name:'New Demo Programme',active:true,health:'On track'})")
        self.open_by_hover("projects")
        self.assertIn("New Demo Programme", self.names("projects"))
        self.away()
        b.wait("document.querySelector('#railMain [data-v=projects]').getAttribute('aria-expanded')==='false'", 3)
        b.eval("P.find(p=>p.code==='ZZN').active=false")
        self.open_by_hover("projects")
        self.assertNotIn("New Demo Programme", self.names("projects"))

    def test_work_lists_its_four_views_and_a_pick_opens_that_list(self):
        b = self.b
        self.open_by_hover("work")
        self.assertEqual(self.names("work"), ["Actions", "RAID", "Decisions", "All items"])
        b.click(f"{self.fly('work')} [role=menuitem]:nth-child(2)")
        b.wait("shared.VIEW==='work' && shared.WT==='raid'", 5)
        b.wait(f"!document.querySelector('{self.fly('work')}')", 5)                    # the pick closed it
        self.open_by_hover("work")                                                   # from Work itself: another list
        b.click(f"{self.fly('work')} [role=menuitem]:nth-child(4)")
        b.wait("shared.WT==='all'", 5)

    def test_a_project_pick_opens_its_page_and_the_icon_alone_still_goes_to_the_page(self):
        b = self.b
        self.open_by_hover("projects")
        code = b.eval("P.filter(p=>p.active!==false&&!p.archived)[0].code")
        b.click(f"{self.fly('projects')} [role=menuitem]:nth-child(1)")
        b.wait(f"shared.VIEW==='cockpit' && shared.COCK==={code!r}", 5)
        b.eval("go('today')")
        b.click(self.btn("projects"))                                                # the icon alone: as before
        b.wait("shared.VIEW==='projects'", 5)
        self.assertEqual(b.eval(f"!!document.querySelector('{self.fly('projects')}')"), False)   # and it shut the flyout
        b.click(self.btn("work"))
        b.wait("shared.VIEW==='work'", 5)

    # ── hover ──
    def test_hover_opens_leaving_folds_after_a_grace_and_one_is_open_at_a_time(self):
        b = self.b
        self.assertEqual(self.expanded("projects"), "false")
        self.assertEqual(b.eval(f"document.querySelector('{self.btn('projects')}').getAttribute('aria-haspopup')"), "menu")
        self.open_by_hover("projects")
        self.assertEqual(b.eval("document.activeElement===document.body || !document.activeElement.closest('[role=menu]')"), True)   # focus stays put
        self.hover(f"{self.fly('projects')} [role=menuitem]")                        # onto the flyout: stays open
        b.pump(0.5)
        self.assertEqual(self.expanded("projects"), "true")
        self.hover(self.btn("work"))                                                 # another: this one folds, that one opens
        b.wait(f"document.querySelector('{self.btn('work')}').getAttribute('aria-expanded')==='true'", 5)
        self.assertEqual(self.expanded("projects"), "false")
        self.hover("#railMore")                                                      # More joins in
        b.wait("document.querySelector('#railMore').getAttribute('aria-expanded')==='true'", 5)
        self.assertEqual(self.expanded("work"), "false")
        self.assertEqual(b.eval("document.querySelectorAll('#railMain [aria-expanded=true], .railmore [aria-expanded=true]').length"), 1)
        self.away()
        b.pump(0.05)
        self.assertEqual(self.expanded("more"), "true")                              # not at once
        b.wait("document.querySelector('#railMore').getAttribute('aria-expanded')==='false'", 3)
        self.assertTrue(b.eval("document.getElementById('railMoreMenu').hidden"))

    def test_more_opens_on_hover_and_still_toggles_on_a_click(self):
        b = self.b
        self.open_by_hover("more")
        self.assertEqual(b.eval("[...document.querySelectorAll('#railMoreMenu [data-v]')].map(x=>x.dataset.v)"),
                         ["inbox", "files", "activity", "settings"])
        self.away()
        b.wait("document.querySelector('#railMore').getAttribute('aria-expanded')==='false'", 3)
        b.pump(0.5)                                                                  # a plain click (the pointer arrives with it)
        b.click("#railMore")
        b.wait("!document.getElementById('railMoreMenu').hidden", 5)
        b.pump(0.6)
        b.click("#railMore")                                                         # a later click shuts it
        b.wait("document.getElementById('railMoreMenu').hidden", 5)
        b.eval("document.querySelector('#railMore').focus()")                        # the keyboard: Enter toggles
        b.key("Enter")
        b.wait("!document.getElementById('railMoreMenu').hidden", 5)
        b.wait("document.activeElement.closest('#railMoreMenu')", 5)
        b.key("Escape")
        b.wait("document.getElementById('railMoreMenu').hidden && document.activeElement===document.querySelector('#railMore')", 5)
        b.key("ArrowRight")                                                          # ArrowRight opens, arrows move, Esc closes
        b.wait("!document.getElementById('railMoreMenu').hidden && document.activeElement.closest('#railMoreMenu')", 5)
        b.key("ArrowDown")
        b.key("Escape")
        b.wait("document.getElementById('railMoreMenu').hidden && document.activeElement===document.querySelector('#railMore')", 5)
        b.eval("document.querySelector('#railMore').focus()")                        # an item still goes to its page
        b.key("ArrowRight")
        b.wait("document.activeElement.closest('#railMoreMenu')", 5)
        b.key("Enter")
        b.wait("shared.VIEW==='inbox' && document.getElementById('railMoreMenu').hidden", 5)

    # ── keyboard ──
    def test_keyboard_opens_with_arrows_picks_with_enter_and_esc_returns_focus(self):
        b = self.b
        order = b.eval("[...document.querySelectorAll('#railMain button[data-v]')].map(x=>x.dataset.v)")
        self.assertEqual(order, ["today", "work", "review", "projects", "people"])    # the Tab order is unchanged
        self.assertEqual(b.eval("[...document.querySelectorAll('#railMain button[data-v]')].every(x=>x.tabIndex===0)"), True)
        for key in ("ArrowRight", "ArrowDown"):
            b.eval(f"document.querySelector('{self.btn('work')}').focus()")
            b.key(key)
            b.wait(f"document.querySelector('{self.btn('work')}').getAttribute('aria-expanded')==='true'", 5)
            b.wait(f"document.activeElement.closest('{self.fly('work')}')", 5)
            self.assertEqual(b.eval("document.activeElement.textContent.trim()"), "Actions")
            b.key("ArrowDown")
            b.wait("document.activeElement.textContent.trim()==='RAID'", 5)
            b.key("End")
            b.wait("document.activeElement.textContent.trim()==='All items'", 5)
            b.key("Escape")
            b.wait(f"document.activeElement===document.querySelector('{self.btn('work')}')", 5)
            self.assertEqual(self.expanded("work"), "false")
        b.key("Enter")                                                                # Enter on the button itself still goes to the page
        b.wait("shared.VIEW==='work'", 5)
        b.eval(f"document.querySelector('{self.btn('projects')}').focus()")
        b.key("ArrowRight")
        b.wait(f"document.activeElement.closest('{self.fly('projects')}')", 5)
        b.key("ArrowLeft")                                                            # ArrowLeft goes back to the button too
        b.wait(f"document.activeElement===document.querySelector('{self.btn('projects')}')", 5)
        b.key("ArrowRight")
        b.wait(f"document.activeElement.closest('{self.fly('projects')}')", 5)
        first = b.eval("document.activeElement.textContent.trim()")
        b.key("Enter")
        b.wait("shared.VIEW==='cockpit'", 5)
        self.assertTrue(first)
        self.assertEqual(b.eval("pName(shared.COCK)"), first.split("On track")[0].split("At risk")[0].split("Off track")[0].split("Not set")[0].strip())

    def test_a_hover_opened_flyout_takes_the_keyboard_on_arrow_right(self):
        b = self.b
        b.eval(f"document.querySelector('{self.btn('work')}').focus()")
        self.open_by_hover("work")
        b.key("ArrowRight")
        b.wait(f"document.activeElement.closest('{self.fly('work')}')", 5)

    # ── placement: collapsed and expanded, 1400 and 900 ──
    def check_placement(self, v, collapsed):
        b = self.b
        self.open_by_hover(v)
        r = b.eval(f"(f=>{{ const q=f.getBoundingClientRect(), rl=document.querySelector('.rail').getBoundingClientRect(); return {{l:q.left,t:q.top,r:q.right,b:q.bottom,rr:rl.right,w:innerWidth,h:innerHeight,col:rl.width}}; }})(document.querySelector('{self.fly(v)}'))")
        if collapsed or v != "more":                                                 # (the expanded More menu opens above its button, as before)
            self.assertGreaterEqual(r["l"], r["rr"] - 1, (v, collapsed, r))          # to the right of the rail
        self.assertLessEqual(r["r"], r["w"] + 1, (v, r))                             # inside the window
        self.assertGreaterEqual(r["t"], 0)
        self.assertLessEqual(r["b"], r["h"] + 1, (v, r))
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('.rail')).width") == "56px" or r["col"] > 100, True)
        self.assertEqual(b.eval(f"getComputedStyle(document.querySelector('{self.fly(v)}')).position"), "fixed")
        z = b.eval(f"+getComputedStyle(document.querySelector('{self.fly(v)}')).zIndex")
        self.assertGreater(z, 0)
        if collapsed and v != "more":
            self.assertIsNone(b.eval(f"document.querySelector('{self.btn(v)}').getAttribute('data-tip')"))   # the tooltip gave way
        self.away()
        b.wait(f"document.querySelector('{self.btn(v)}').getAttribute('aria-expanded')==='false'", 3)
        if collapsed and v != "more":
            self.assertEqual(b.eval(f"document.querySelector('{self.btn(v)}').getAttribute('data-tip')"), b.eval(f"document.querySelector('{self.btn(v)}').getAttribute('aria-label')"))

    def test_placement_expanded_and_collapsed_at_1400(self):
        for v in ("projects", "work", "more"):
            self.check_placement(v, False)
        self.collapse()
        for v in ("projects", "work", "more"):
            self.check_placement(v, True)

    def test_placement_at_900(self):
        self.b.resize(900, 700)
        self.b.wait("document.querySelector('.rail').classList.contains('collapsed')", 5)
        for v in ("projects", "work", "more"):
            self.check_placement(v, True)
        self.b.resize(1400, 900)

    def test_more_keeps_its_badge_and_tooltip(self):
        b = self.b
        self.collapse()
        self.assertTrue(b.eval("document.querySelector('#railMore').getAttribute('data-tip').startsWith('More')"))
        self.assertTrue(b.eval("!!document.querySelector('#railMoreBadge')"))
        self.open_by_hover("more")
        self.assertTrue(b.eval("document.querySelector('#railMore').getAttribute('data-tip').startsWith('More')"))   # as today
        self.away()
        b.wait("document.querySelector('#railMore').getAttribute('aria-expanded')==='false'", 3)


if __name__ == "__main__":
    unittest.main()
