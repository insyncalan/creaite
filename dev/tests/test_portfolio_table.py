"""BL-285 (v1.9.0): Today's Portfolio table. The project's description is no longer a line under its name but the name's
tooltip, on hover and on keyboard focus, and screen readers get it too (aria-describedby); an empty description has no
tooltip. The columns resize like Work's (pointer drag, the keyboard separator, 60 to 900 px), remembered in this browser
under creaite-colwidths `portfolio|<column>`; double-click resets one; a resize never opens the project; at 320 px nothing
scrolls sideways. And BL-308's source checks: the wordmark has no dashed draft copy, and BL-291's rule for it is gone.

The page tests run in a real browser on the snapshot sample vault (test_snapshots: fixed day, UTC, en-GB): ABC, Example
Programme, has a description (its client, "Example Client Ltd"); DEF, Digital Enablement, has none.

Run: python3 dev/tests/test_portfolio_table.py   (the page tests need Google Chrome; skipped otherwise)
"""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_snapshots as ts  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DASH = ROOT / "system" / "templates" / "dashboard"
PF = "#pfTbl"
ABC = f'{PF} tr[data-cock="ABC"]'
DEF = f'{PF} tr[data-cock="DEF"]'


class Source(unittest.TestCase):
    """Without a browser: the template's own files."""

    def test_wordmark_has_no_dashed_copy(self):
        shell = (DASH / "shell.html").read_text(encoding="utf-8")
        logo = re.search(r'<div class="logo">.*?</div>', shell, re.S).group(0)
        self.assertNotIn("wmd", logo)
        self.assertNotIn("stroke-dasharray", logo)
        self.assertEqual(logo.count("<use "), 1, "the word once")
        self.assertIn('aria-label="creaite"', logo)
        self.assertIn('class="wmb"', logo, "the saffron bar")

    def test_bl291_rule_is_gone(self):
        css = (DASH / "style.css").read_text(encoding="utf-8")
        self.assertNotIn(".wmd", css)
        for block in re.findall(r"@media \(prefers-contrast: more\)\{(.*?)\n?\}", css, re.S):
            self.assertNotIn(".logo", block)

    def test_description_is_not_a_line_under_the_name(self):
        src = (DASH / "src" / "today.js").read_text(encoding="utf-8")
        fn = src[src.index("export function portfolioTable("):src.index("export function pfResize(")]
        self.assertNotIn("p.client)}</div>", fn)
        self.assertIn('class="pfname"', fn)
        self.assertNotIn(" title=", fn, "never a title attribute")


class Portfolio(ts.Snapshots):
    test_every_screen_matches_its_golden = None

    def setUp(self):
        super().setUp()
        b = self.b
        b.eval("try{ localStorage.removeItem('creaite-colwidths'); }catch(e){} shared.RZ={}; go('today')")
        b.wait(f"!document.getElementById('v-today').hidden && document.querySelector({json.dumps(ABC)})", 15)
        b.pump(0.3)

    def tip(self):
        return self.b.eval("(()=>{ const t=document.getElementById('tip'); return t&&t.classList.contains('on')?t.textContent:null; })()")

    def colw(self, col):
        return self.b.eval(f"Math.round(document.querySelector('{PF} th[data-col=\"{col}\"]').getBoundingClientRect().width)")

    # 1. Description on hover and focus
    def test_one_line_per_project_and_the_description_is_the_names_tooltip(self):
        b = self.b
        r = b.eval(f"""(()=>{{ const td=document.querySelector({json.dumps(ABC)}+' td'), n=td.querySelector('button.pfname'), d=document.getElementById(n.getAttribute('aria-describedby'));
          return {{name:n.textContent, tip:n.dataset.tip, title:n.hasAttribute('title'), subs:td.querySelectorAll('.sub').length, desc:d&&d.textContent, hidden:d&&d.classList.contains('vh')}}; }})()""")
        self.assertEqual(r, {"name": "Example Programme", "tip": "Example Client Ltd", "title": False, "subs": 0,
                             "desc": "Example Client Ltd", "hidden": True})
        # the pointer resting on the name shows it
        pos = b.box(f"{ABC} button.pfname")
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=pos["x"], y=pos["y"])
        b.wait("document.getElementById('tip')&&document.getElementById('tip').classList.contains('on')", 5)
        self.assertEqual(self.tip(), "Example Client Ltd")
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=5, y=990)
        b.pump(0.4)

    def test_keyboard_focus_shows_the_description_and_enter_opens_the_project(self):
        b = self.b
        b.eval("document.body.focus()")
        b.key("Tab")             # a keyboard user: focus becomes :focus-visible
        for _ in range(80):
            if b.eval("document.activeElement&&document.activeElement.matches('#pfTbl tr[data-cock=\"ABC\"] .pfname')"):
                break
            b.key("Tab")
        self.assertTrue(b.eval("document.activeElement.matches('#pfTbl .pfname')"), "Tab reaches the project's name")
        b.wait("document.getElementById('tip')&&document.getElementById('tip').classList.contains('on')", 5)
        self.assertEqual(self.tip(), "Example Client Ltd")
        self.assertEqual(b.eval("document.activeElement.getAttribute('aria-describedby')"), "pfd-ABC", "screen readers keep the description")
        b.key("Enter")
        b.wait("VIEW==='cockpit' && COCK==='ABC'", 5)

    def test_an_empty_description_has_no_tooltip(self):
        r = self.b.eval(f"""(()=>{{ const n=document.querySelector({json.dumps(DEF)}+' button.pfname');
          return {{name:n.textContent, tip:n.hasAttribute('data-tip'), desc:n.hasAttribute('aria-describedby')}}; }})()""")
        self.assertEqual(r, {"name": "Digital Enablement", "tip": False, "desc": False})

    # 2. Resizable columns
    def test_every_column_has_a_resize_handle(self):
        r = self.b.eval(f"""[...document.querySelectorAll('{PF} thead th')].map(th=>{{ const h=th.querySelector('.colrz');
          return [th.dataset.col, !!h&&h.getAttribute('role'), !!h&&h.tabIndex, !!h&&h.getAttribute('aria-label')]; }})""")
        self.assertEqual(r, [["project", "separator", 0, "Resize Project column"], ["health", "separator", 0, "Resize Health column"],
                             ["evidence", "separator", 0, "Resize Evidence column"], ["trend", "separator", 0, "Resize 8 weeks column"],
                             ["next", "separator", 0, "Resize Next milestone column"]])

    def test_drag_resizes_is_remembered_and_double_click_resets(self):
        b = self.b
        w0 = self.colw("project")
        h = b.box(f'{PF} th[data-col="project"] .colrz')
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=h["x"], y=h["y"])
        b.call("Input.dispatchMouseEvent", type="mousePressed", x=h["x"], y=h["y"], button="left", buttons=1, clickCount=1)
        for i in range(1, 9):
            b.call("Input.dispatchMouseEvent", type="mouseMoved", x=h["x"] + 10 * i, y=h["y"], button="left", buttons=1)
        b.call("Input.dispatchMouseEvent", type="mouseReleased", x=h["x"] + 80, y=h["y"], button="left", buttons=0, clickCount=1)
        b.pump(0.2)
        self.assertEqual(b.eval("VIEW"), "today", "a resize never opens the project")
        w1 = self.colw("project")
        self.assertAlmostEqual(w1, w0 + 80, delta=3)
        saved = b.eval("JSON.parse(localStorage.getItem('creaite-colwidths'))['portfolio|project']")
        self.assertAlmostEqual(saved, w1, delta=1)
        # survives a reload
        b.reload("typeof go==='function' && LIVE")
        b.eval("go('today')")
        b.wait(f"document.querySelector({json.dumps(ABC)})", 15)
        b.pump(0.3)
        self.assertAlmostEqual(self.colw("project"), w1, delta=1)
        # a click on the handle doesn't open the project; a double-click puts the column back
        b.click(f'{PF} th[data-col="project"] .colrz')
        self.assertEqual(b.eval("VIEW"), "today")
        b.click(f'{PF} th[data-col="project"] .colrz', count=2)
        b.pump(0.2)
        self.assertIsNone(b.eval("JSON.parse(localStorage.getItem('creaite-colwidths')||'{}')['portfolio|project']??null"))
        self.assertAlmostEqual(self.colw("project"), w0, delta=3)

    def test_keyboard_resizes_within_60_to_900(self):
        b = self.b
        b.eval(f"document.querySelector('{PF} th[data-col=\"health\"] .colrz').focus()")
        w0 = self.colw("health")
        b.key("ArrowRight")
        self.assertAlmostEqual(self.colw("health"), w0 + 16, delta=2)
        self.assertEqual(b.eval("VIEW"), "today")
        for _ in range(80):
            b.key("ArrowLeft")
        small = b.eval("JSON.parse(localStorage.getItem('creaite-colwidths'))['portfolio|health']")
        self.assertGreaterEqual(small, 60)          # never under 60 (the column's own content may stop it sooner)
        self.assertLess(small, w0)
        for _ in range(70):
            b.key("ArrowRight")
        self.assertEqual(b.eval("JSON.parse(localStorage.getItem('creaite-colwidths'))['portfolio|health']"), 900)

if __name__ == "__main__":
    unittest.main()
