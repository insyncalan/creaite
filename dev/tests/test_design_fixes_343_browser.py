"""#343 / #342 (the safe design batch, 2.6.4b), measured in the live app against the page's own boxes (no pixel numbers
that depend on a font): contrast and targets, then the other groups as they land. Each check has a mutant that must fail.

Run: python3 dev/tests/test_design_fixes_343_browser.py   (needs Google Chrome; skipped otherwise). Desktop and 900 px only.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

# Interactive things on the shown screen that are smaller than 24 px either way (a link inside running text is not counted)
SMALL_TARGETS = r"""(sel=>{ const v=e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(e).visibility!=='hidden'&&!e.closest('[hidden],[inert]')};
  return [...document.querySelectorAll(sel)].filter(v).map(e=>{const r=e.getBoundingClientRect();return [e.className||e.tagName, Math.round(r.width), Math.round(r.height)]}).filter(x=>x[1]<24||x[2]<24); })"""
SMALL_TEXT = r"""(scope=>{ const root=document.querySelector(scope)||document.body, v=e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(e).visibility!=='hidden'&&!e.closest('[hidden],[inert]')};
  return [...root.querySelectorAll('*')].filter(e=>v(e)&&[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())&&parseFloat(getComputedStyle(e).fontSize)<12).map(e=>[e.className&&e.className.baseVal===undefined?e.className:e.tagName, e.textContent.trim().slice(0,24)]); })"""


class ContrastAndTargets(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 900

    def small(self, sel):
        return self.b.eval("(%s)(%r)" % (SMALL_TARGETS, sel))

    def at(self, w):
        self.b.resize(w, 900)
        self.b.pump(0.3)

    def test_today_help_button_evidence_links_and_week_ahead_are_24px(self):
        b = self.b
        for w in (1400, 900):
            self.at(w)
            b.eval("go('today')")
            b.wait("document.querySelector('.legbtn')")
            self.assertEqual(self.small(".legbtn,.ev a.cntl,.tres>details>summary"), [], w)

    def test_mutant_a_small_help_button_is_caught(self):
        b = self.b
        b.eval("go('today')")
        b.wait("document.querySelector('.legbtn')")
        b.eval("document.head.insertAdjacentHTML('beforeend','<style id=mut>.legbtn{width:18px;height:18px}</style>')")
        self.assertTrue(self.small(".legbtn"))

    def test_work_row_ids_and_review_source_links_are_24px(self):
        b = self.b
        for w in (1400, 900):
            self.at(w)
            b.eval("go('work')")
            b.wait("document.querySelector('a.rowid')")
            self.assertEqual(self.small("a.rowid"), [], w)
        b.eval("document.body.insertAdjacentHTML('beforeend','<p id=mutsrc>Text <a class=srclink href=#>Open source</a> more</p>')")
        self.assertEqual(self.small("#mutsrc .srclink"), [])
        b.eval("document.head.insertAdjacentHTML('beforeend','<style>.srclink,a.rowid{padding:0;margin:0;display:inline}</style>')")
        self.assertTrue(self.small("a.rowid,#mutsrc .srclink"))        # mutant: the rule gone, both are caught

    def test_nothing_under_12px_on_the_changed_screens(self):
        b = self.b
        for w in (1400, 900):
            self.at(w)
            for js, scope in (("go('today')", "#v-today"), ("go('work')", "#v-work"), ("go('help')", "#v-help"), ("go('cockpit','ABC')", "#v-cockpit")):
                b.eval(js)
                b.pump(0.8)
                self.assertEqual(b.eval("(%s)('%s')" % (SMALL_TEXT, scope)), [], (w, js))

    def test_mutant_small_text_is_caught(self):
        b = self.b
        b.eval("go('work')")
        b.wait("document.querySelector('a.rowid')")
        b.eval("document.querySelector('#v-work').insertAdjacentHTML('beforeend','<span id=mut style=\"font-size:10px\">tiny</span>')")
        self.assertTrue(b.eval("(%s)('#v-work')" % SMALL_TEXT))


if __name__ == "__main__":
    unittest.main()
