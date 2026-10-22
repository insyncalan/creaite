"""#295: the avatar takes More's place at the foot of the sidebar, in a real browser against the real live server.

Run: python3 dev/tests/test_rail_avatar.py   (needs Google Chrome; skipped otherwise)

Done when (the brief's list):
- in the three rail states (expanded 188px: circle, name, second line; collapsed with labels 76px: circle, first name under
  it; icons only 56px: circle and badge only) and the three icon sizes, the avatar stands where More was and opens the same
  menu, which now starts with a header row (initials, name, "creaite · v<VERSION>");
- nothing wrong: the second line says "Settings and health" and there is no badge; a problem: the amber badge on the circle and
  the first problem in plain words, in --warn; the button is named "<name>, menu, 1 problem";
- with dashboard.rail.more empty the avatar still shows and opens Health, Help and Customise sidebar;
- it opens on a click only (no hover-open); the keys and focus return are More's;
- the name comes from settings (identity.name): with none set, a person icon and "You";
- no "vault", "account" or "More" in what it says; contrast passes on the circle, the badge and the warning line in the
  creaite, Cursor, Claude and Retro Arcade palettes, light and dark.
The demo vault's owner is the fictional Alan Carter.
"""
import json
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("CREAITE_NO_LAUNCH", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

LUM = """const rgb=s=>s.match(/[\\d.]+/g).map(Number).slice(0,3), L=c=>{ const f=v=>{ v/=255; return v<=0.03928?v/12.92:((v+0.055)/1.055)**2.4; };
  const [r,g,b]=c.map(f); return 0.2126*r+0.7152*g+0.0722*b; }, ratio=(a,b)=>{ const x=L(rgb(a)), y=L(rgb(b)); return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05); };"""
BANNED = ("vault", "account", "More", "sweep", "proposal", "tracker")


class RailAvatar(LiveBrowserCase):
    width, height = 1400, 900

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": "2026-10-16 09:00"}

    def rect(self, sel):
        return self.b.eval(f"(s=>{{ const e=document.querySelector(s); if(!e) return null; const r=e.getBoundingClientRect(); return {{l:r.left,t:r.top,r:r.right,b:r.bottom,w:r.width,h:r.height}}; }})({json.dumps(sel)})")

    def wait_w(self, w):
        self.b.wait(f"Math.round(document.querySelector('.rail').getBoundingClientRect().width)==={w}", 5)

    def shown(self, sel):
        return self.b.eval(f"(e=>!!e&&e.offsetParent!==null&&getComputedStyle(e).display!=='none')(document.querySelector({json.dumps(sel)}))")

    def text(self, sel):
        return self.b.eval(f"(e=>e?e.textContent.trim():null)(document.querySelector({json.dumps(sel)}))")

    def open_menu(self):
        self.b.click("#railMore")
        self.b.wait("!document.getElementById('railMoreMenu').hidden", 5)

    def close_menu(self):
        self.b.key("Escape")
        self.b.wait("document.getElementById('railMoreMenu').hidden", 5)

    def test_the_avatar_in_each_state_and_icon_size(self):
        b = self.b
        b.eval("healthCount.value=0")
        self.assertIsNone(self.rect("#railMore [data-icn=more]"))                               # no More icon any more
        self.assertFalse(b.eval("[...document.querySelectorAll('#railMore .rl')].some(x=>x.textContent.trim()==='More')"))
        for size in ("small", "medium", "large"):
            with self.subTest(size=size):
                b.eval(f"railSetIconSize({json.dumps(size)})")
                b.wait(f"railIconSize.value==={json.dumps(size)}", 5)
                # expanded: circle, name, second line, side by side
                if self.rect(".rail")["w"] < 100:
                    b.click("#railTog")
                self.wait_w(188)
                self.assertEqual(self.text("#railMore .av .avi"), "AC")
                self.assertEqual(self.text("#railMore .avn"), "Alan Carter")
                self.assertEqual(self.text("#railMore .avs"), "Settings and health")
                av, name, rail = self.rect("#railMore .av"), self.rect("#railMore .avn"), self.rect(".rail")
                self.assertAlmostEqual(av["w"], av["h"], delta=0.5)                           # a circle
                self.assertEqual(b.eval("getComputedStyle(document.querySelector('#railMore .av')).borderRadius"), "50%")
                self.assertGreater(name["l"], av["r"])                                         # the name beside the circle
                self.assertLessEqual(self.rect("#railMore")["r"], rail["r"] + 0.5)
                clipped = b.eval("[...document.querySelectorAll('#railMore .avn, #railMore .avs')].filter(e=>e.scrollWidth>e.clientWidth+1).length")
                self.assertEqual(clipped, 0)
                # the menu opens beside the rail, bottom-aligned with the button
                self.open_menu()
                m, btn = self.rect("#railMoreMenu"), self.rect("#railMore")
                self.assertGreaterEqual(m["l"], rail["r"])
                self.assertAlmostEqual(m["b"], btn["b"], delta=2)
                self.close_menu()
                # collapsed with labels: circle, first name under it, no second line
                b.click("#railTog")
                self.wait_w(76)
                self.assertEqual(self.text("#railMore .avn"), "Alan")
                self.assertFalse(self.shown("#railMore .avs"))
                self.assertGreaterEqual(self.rect("#railMore .avn")["t"], self.rect("#railMore .av")["b"] - 1)
                self.assertLessEqual(self.rect("#railMore")["r"], self.rect(".rail")["r"] + 0.5)
                # icons only: circle (and badge) only
                b.eval("railSetLabels(false)")
                self.wait_w(56)
                self.assertTrue(self.shown("#railMore .av"))
                self.assertFalse(self.shown("#railMore .avn"))
                self.assertFalse(self.shown("#railMore .avs"))
                self.assertLessEqual(self.rect("#railMore .av")["r"], self.rect(".rail")["r"])
                b.eval("railSetLabels(true)")
                self.wait_w(76)
                b.click("#railTog")
                self.wait_w(188)
        b.eval("railSetIconSize('small')")

    def test_a_problem_shows_the_badge_and_the_words_and_none_shows_neither(self):
        b = self.b
        b.eval("healthFirst.value=\"Set-up isn't finished\"; healthCount.value=1")
        b.wait("document.getElementById('railMoreBadge').textContent==='1'", 5)
        self.assertEqual(self.text("#railMore .avs"), "Set-up isn't finished")
        self.assertEqual(b.eval("document.getElementById('railMore').getAttribute('aria-label')"), "Alan Carter, menu, 1 problem")
        warn = b.eval("(()=>{ const d=document.createElement('i'); d.style.color='var(--warn)'; document.body.appendChild(d); const c=getComputedStyle(d).color; d.remove(); return c; })()")
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('#railMore .avs')).color"), warn)
        badge, av = self.rect("#railMoreBadge"), self.rect("#railMore .av")
        self.assertTrue(badge["l"] < av["r"] and badge["r"] > av["l"] and badge["t"] < av["b"] and badge["b"] > av["t"])   # on the circle
        self.assertEqual(b.eval("document.getElementById('railMoreBadge').closest('.av')!==null"), True)
        b.eval("healthCount.value=2")
        b.wait("document.getElementById('railMore').getAttribute('aria-label')==='Alan Carter, menu, 2 problems'", 5)
        b.eval("healthFirst.value=''")                                                          # a count with no words (an older browser's)
        b.wait("document.querySelector('#railMore .avs').textContent.trim()==='2 problems to fix'", 5)
        b.eval("healthCount.value=0")
        b.wait("document.getElementById('railMoreBadge').style.display==='none'", 5)
        self.assertEqual(self.text("#railMore .avs"), "Settings and health")
        self.assertEqual(b.eval("document.getElementById('railMore').getAttribute('aria-label')"), "Alan Carter, menu")
        self.assertNotEqual(b.eval("getComputedStyle(document.querySelector('#railMore .avs')).color"), warn)

    def test_the_menu_has_the_header_then_more_menu_and_click_only(self):
        b = self.b
        # click only: pointing at it opens nothing
        p = b.box("#railMore")
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=p["x"], y=p["y"], button="none")
        b.pump(0.8)
        self.assertTrue(b.eval("document.getElementById('railMoreMenu').hidden"))
        self.assertEqual(b.eval("document.getElementById('railMore').getAttribute('aria-haspopup')"), "menu")
        self.open_menu()
        head = b.eval("""(()=>{ const h=document.querySelector('#railMoreMenu .avhead'); return h && {first:h===document.querySelector('#railMoreMenu').firstElementChild,
          av:h.querySelector('.av .avi').textContent.trim(), name:h.querySelector('.avn').textContent.trim(), app:h.querySelector('.avv').textContent.trim(),
          role:h.getAttribute('role'), item:!!h.closest('[role=menuitem]')}; })()""")
        self.assertEqual(head["av"], "AC")
        self.assertEqual(head["name"], "Alan Carter")
        self.assertRegex(head["app"], r"^creaite( · v\d+\.\d+\.\d+)?$")
        self.assertTrue(head["first"])
        self.assertFalse(head["item"])
        self.assertEqual(b.eval("document.activeElement.closest('#railMoreMenu')!==null && document.activeElement.getAttribute('role')"), "menuitem")
        self.assertEqual(b.eval("[...document.querySelectorAll('#railMoreMenu [role^=menuitem]')].map(x=>x.id||x.dataset.v)"),
                         ["files", "activity", "railHealth", "settings", "railHelp", "railCustBtn"])
        words = b.eval("document.getElementById('railMoreMenu').textContent + ' ' + document.getElementById('railMore').textContent + ' ' + document.getElementById('railMore').getAttribute('aria-label') + ' ' + (document.getElementById('railMoreMenu').getAttribute('aria-label')||'')")
        for w in BANNED:
            self.assertNotIn(w.lower(), words.lower(), w)
        self.close_menu()
        self.assertEqual(b.eval("document.activeElement.id"), "railMore")                      # focus back, as More's

    def test_with_more_empty_the_avatar_still_opens_health_help_and_customise(self):
        b = self.b
        b.eval("railSave({...RAILCFG,order:['today','work','review','projects','reports','people','files','activity','settings'],more:[]})")
        b.wait("!document.querySelector('#railMoreMenu [data-v]')", 5)
        self.assertTrue(self.shown("#railMore"))
        self.open_menu()
        self.assertEqual(b.eval("[...document.querySelectorAll('#railMoreMenu [role^=menuitem]')].map(x=>x.id||x.dataset.v)"),
                         ["railHealth", "railHelp", "railCustBtn"])
        self.assertTrue(self.shown("#railMoreMenu .avhead"))
        b.click("#railCustBtn")
        b.wait("document.getElementById('railCust').open", 5)
        self.assertIn("Empty", self.text("#railCust .rcempty"))
        self.assertNotIn("hidden", self.text("#railCust .rcempty"))
        self.assertNotIn("More", b.eval("document.getElementById('railCust').textContent"))
        self.assertIn("the menu under your name", b.eval("document.getElementById('railCust').textContent"))

    def test_with_no_name_set_a_person_icon_and_you(self):
        b = self.b
        b.eval("railName.value=''")
        b.wait("document.querySelector('#railMore .avn').textContent.trim()==='You'", 5)
        self.assertEqual(b.eval("!!document.querySelector('#railMore .av svg')"), True)
        self.assertIsNone(self.text("#railMore .av .avi"))
        self.assertEqual(b.eval("document.getElementById('railMore').getAttribute('aria-label')"), "You, menu")
        b.eval("railName.value='Maya'")                                                         # one word: one initial
        b.wait("(e=>e&&e.textContent==='M')(document.querySelector('#railMore .av .avi'))", 5)
        self.assertEqual(b.eval("document.querySelectorAll('#railMore .av > *').length"), 2)       # the initials and the badge, nothing left over
        self.assertEqual(b.eval("document.getElementById('railMoreBadge').closest('.av')!==null"), True)

    def test_contrast_on_the_circle_the_badge_and_the_warning_line(self):
        b = self.b
        b.eval("healthFirst.value='The projects folder can\\'t be reached'; healthCount.value=1")
        b.wait("document.getElementById('railMoreBadge').textContent==='1'", 5)
        for p in ("creaite", "Cursor", "Claude", "Retro Arcade"):
            for t in ("light", "dark"):
                with self.subTest(palette=p, mode=t):
                    r = b.eval(f"""(()=>{{ {LUM} const R=document.documentElement; R.dataset.palette={json.dumps(p)}; R.dataset.theme={json.dumps(t)};
                      const g=s=>getComputedStyle(document.querySelector(s)), rail=g('.rail').backgroundColor;
                      const av=g('#railMore .av'), bd=g('#railMoreBadge'), line=g('#railMore .avs');
                      return {{circle:ratio(av.color,av.backgroundColor), badge:ratio(bd.color,bd.backgroundColor), line:ratio(line.color,rail),
                               ring:ratio(av.backgroundColor,rail)}}; }})()""")
                    self.assertGreaterEqual(r["circle"], 4.5, r)
                    self.assertGreaterEqual(r["badge"], 4.5, r)
                    self.assertGreaterEqual(r["line"], 4.5, r)
                    self.assertGreaterEqual(r["ring"], 3, r)                                   # the circle stands out from the rail


class AvatarSettings(unittest.TestCase):
    """The page's settings say whether a name is set (#295: "You" until it is) and the installed version, from settings only."""

    def test_me_set_follows_identity_name(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
        import build_dashboard
        self.assertTrue(build_dashboard.ui_settings({"identity": {"name": "Alan Carter"}})["meSet"])
        for none in ({}, {"identity": {}}, {"identity": {"name": ""}}, {"identity": {"name": "  "}}, {"identity": {"name": None}}):
            with self.subTest(none=none):
                self.assertFalse(build_dashboard.ui_settings(none)["meSet"])
        self.assertIsInstance(build_dashboard.ui_settings({})["version"], str)


if __name__ == "__main__":
    unittest.main()
