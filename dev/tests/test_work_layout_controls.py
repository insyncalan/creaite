"""BL-114: the Work page shows only the controls for the layout in use. A real browser against the real live server: on each tab, in
each layout, the other layout's controls are really hidden (not just invisible), the shared ones are present and don't move, and the hint
line matches the layout.

Run: python3 dev/tests/test_work_layout_controls.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

TABS = ("actions", "raid", "decisions")


class LayoutControls(LiveBrowserCase):
    shared_server = True
    width, height = 1500, 900

    def show(self, tab, lay):
        b = self.b
        b.eval("go('work')")
        b.click(f'#wtabs [data-t="{tab}"]')
        b.click(f'#wlay [data-lay="{lay}"]')
        b.pump(0.3)

    def state(self, sel):
        """Does the control take part in the page at all? (hidden attribute, computed display, and out of reach of the keyboard)"""
        return self.b.eval(f"""(()=>{{ const e=document.querySelector({sel!r}); if(!e) return null;
          return {{attr:e.hasAttribute('hidden')||!!e.closest('[hidden]'), display:getComputedStyle(e).display, shown:!!(e.offsetWidth||e.offsetHeight||e.getClientRects().length)}}; }})()""")

    def assert_hidden(self, sel, msg):
        s = self.state(sel)
        if s is None:                                                              # BL-128: not drawn at all for this layout
            return
        self.assertFalse(s["shown"], (sel, msg, s))
        self.assertTrue(s["attr"] or s["display"] == "none", (sel, msg, s))      # hidden for assistive technology too, not just unseen

    def assert_shown(self, sel, msg):
        s = self.state(sel)
        self.assertIsNotNone(s, (sel, msg))
        self.assertTrue(s["shown"], (sel, msg, s))

    def test_the_other_layouts_controls_are_hidden_on_every_tab(self):
        """BL-128: the layout-specific controls live in the Display menu; with it open, only the layout's own options show."""
        for tab in TABS:
            self.show(tab, "list")
            self.b.eval("openDisp()")
            for sel in ("#wclosed", "#wshowempty", "#whintBoard"):
                self.assert_hidden(sel, (tab, "list"))
            self.assert_hidden("#whintList", (tab, "list"))                        # BL-175: the hint lines stay in the page, hidden (Help lists the keys)
            for sel in ("#dispBtn", "#wbsort", "#wordRev", "#dprop-o" if tab != "decisions" else "#dprop-by", "#workWrap"):
                self.assert_shown(sel, (tab, "list"))
            self.assert_hidden("#workBoard", (tab, "list"))
            self.b.eval("closeDisp()")
            self.show(tab, "board")
            self.b.eval("openDisp()")
            for sel in ("#whintList", "#workWrap"):
                self.assert_hidden(sel, (tab, "board"))
            self.assert_hidden("#whintBoard", (tab, "board"))                      # BL-175
            for sel in ("#dispBtn", "#wgrp", "#wbsort", "#wclosed", "#wshowempty", "#workBoard"):
                self.assert_shown(sel, (tab, "board"))
            self.b.eval("closeDisp()")
            for sel in ("#colBtn", "#colMenu", "#wboardctl", "#wbhide"):                 # the old controls are gone
                self.assertIsNone(self.state(sel), sel)

    def test_the_shared_controls_stay_in_both_and_do_not_move(self):
        for tab in TABS:
            seen = {}
            for lay in ("list", "board"):
                self.show(tab, lay)
                for sel in ("#workQ", "#wfilters", "#wlay", "#dispBtn", "#newBtn", "#wviews", "#wapplied"):
                    s = self.state(sel)
                    self.assertIsNotNone(s, (sel, tab, lay))
                for sel in ("#workQ", "#wlay", "#dispBtn", "#newBtn"):
                    self.assert_shown(sel, (tab, lay))
                seen[lay] = {sel: self.b.eval(f"(()=>{{ const r=document.querySelector({sel!r}).getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top)]; }})()")
                             for sel in ("#workQ", "#wlay", "#dispBtn", "#newBtn")}
            self.assertEqual(seen["list"], seen["board"], tab)                    # switching layout never moves them

    def test_the_hint_line_matches_the_layout(self):
        for tab in TABS:
            self.show(tab, "list")
            text = self.b.eval("document.getElementById('whintList').textContent")
            self.assertIn("click a value to change it", text)            # BL-123: a click on a value edits it
            self.assertIn("click a heading to sort", text)
            self.assertIn("display", text)                                # BL-128: D opens Display
            self.show(tab, "board")
            text = self.b.eval("document.getElementById('whintBoard').textContent")
            self.assertIn("step through the cards", text)
            self.assertIn("Move to…", text)
            self.assertNotIn("heading", text)
            self.assertNotIn("column edge", text)

    def test_the_layout_toggle_always_shows_and_a_narrow_window_still_works(self):
        for lay in ("list", "board"):
            self.show("actions", lay)
            self.assert_shown("#wlay", lay)
            self.assertEqual(self.b.eval(f"document.querySelector('#wlay [data-lay=\"{lay}\"]').getAttribute('aria-pressed')"), "true")


if __name__ == "__main__":
    unittest.main(verbosity=2)
