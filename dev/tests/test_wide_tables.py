"""BL-165 (sprint-polish-2): wide tables show that they scroll. A real browser against the real live server.

Run: python3 dev/tests/test_wide_tables.py   (needs Google Chrome; skipped otherwise)

A table wider than its frame (Projects at 700px, Settings › People at 900px) shows the edge fade and "more columns →";
BL-176: the peek and ask creaite are over the page, so with them open at 1100px nothing narrows and a table that fits shows no cue; the cue goes once scrolled to the
end; the button scrolls; the first column (the ID or name) stays put while the rest scrolls, unless it is over half the frame.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

PAGES = {"projects": "go('projects')", "work": "go('work')", "people": "go('settings','people')"}
FRAME = {"projects": "#projTbl", "work": "#workWrap", "people": "#v-settings .tbl"}
CUE = """(()=>{ const f=document.querySelector(%r), c=f&&f.querySelector(':scope>.xcue'), m=c&&c.querySelector('.xmore');
  const vis=e=>!!e&&getComputedStyle(e).display!=='none'&&e.getBoundingClientRect().width>0;
  const fr=f.getBoundingClientRect(), mr=m?m.getBoundingClientRect():null;
  return {over:f.querySelector('table').scrollWidth>f.clientWidth+1, cue:vis(m), fade:vis(c&&c.querySelector('.xfade.r')),
    inside:!!mr&&mr.right<=fr.right+1&&mr.left>=fr.left-1, text:m?m.textContent:'', left:f.scrollLeft, stick:f.classList.contains('xstick')}; })()"""


class WideTables(LiveBrowserCase):
    shared_server = True

    def state(self, page):
        return self.b.eval(CUE % FRAME[page])

    def setup_page(self, page, width, chat=False, panel=False):
        b = self.b
        b.resize(width, 900)
        b.eval("closeChat(); if(CUR){ EDITING=false; closePanel(true); }")
        b.pump(0.2)
        b.eval(PAGES[page])
        if chat:
            b.eval("openChat()")
        if panel:
            b.eval("openRecord('actions',A[0].id)")
        b.pump(0.8)

    def test_the_peek_and_the_chat_narrow_nothing_at_1100(self):
        """BL-176 (sprint-peek): the item panel is the peek, over the page, so with it and ask creaite open the tables keep their
        frames: what fits still fits and shows no cue."""
        for page in ("projects", "work"):
            self.setup_page(page, 1100)
            alone = self.state(page)
            self.setup_page(page, 1100, chat=True, panel=True)
            self.assertEqual(self.state(page), alone, page)

    def test_each_table_shows_the_cue_when_wider_than_its_frame(self):
        for page, width in (("projects", 700), ("people", 900)):
            self.setup_page(page, width, panel=page == "projects")
            s = self.state(page)
            self.assertTrue(s["over"], page)
            self.assertTrue(s["cue"] and s["fade"] and s["inside"], (page, s))
            self.assertEqual(s["text"], "more columns →")

    def test_a_table_that_fits_has_no_cue(self):
        self.setup_page("projects", 1400)
        s = self.state("projects")
        self.assertFalse(s["over"])
        self.assertFalse(s["cue"])
        self.assertFalse(self.b.eval("!!document.querySelector('#projTbl>.xcue')"))     # nothing added to a table that fits

    def test_the_cue_goes_at_the_end_and_the_button_scrolls(self):
        b = self.b
        self.setup_page("people", 900)
        b.click("#v-settings .tbl .xmore")
        b.wait("document.querySelector('#v-settings .tbl').scrollLeft>0", 5)
        b.eval("(()=>{ const f=document.querySelector('#v-settings .tbl'); f.scrollLeft=f.scrollWidth; })()")
        b.pump(0.3)
        s = self.state("people")
        self.assertFalse(s["cue"])
        self.assertFalse(s["fade"])
        b.eval("document.querySelector('#v-settings .tbl').scrollLeft=0")
        b.pump(0.3)
        self.assertTrue(self.state("people")["cue"])                                      # back at the start: it shows again

    def test_the_first_column_stays_fixed(self):
        b = self.b
        self.setup_page("people", 900)
        self.assertTrue(self.state("people")["stick"])
        first = "document.querySelector('#v-settings .tbl tbody tr td:first-child').getBoundingClientRect().left"
        second = "document.querySelector('#v-settings .tbl tbody tr td:nth-child(2)').getBoundingClientRect().left"
        x1, x2 = b.eval(first), b.eval(second)
        b.eval("document.querySelector('#v-settings .tbl').scrollLeft=120")
        b.pump(0.3)
        self.assertAlmostEqual(b.eval(first), x1, delta=1)                                # the name stays
        self.assertLess(b.eval(second), x2 - 60)                                          # the rest moves
        hit = b.eval("""(()=>{ const td=document.querySelector('#v-settings .tbl tbody tr td:first-child'), r=td.getBoundingClientRect();
          return td.contains(document.elementFromPoint(r.left+8, r.top+r.height/2)); })()""")
        self.assertTrue(hit)                                                              # drawn over the scrolled columns

    def test_the_projects_name_stays_fixed_too(self):
        b = self.b
        self.setup_page("projects", 700, panel=True)
        s = self.state("projects")
        if not s["stick"]:
            self.skipTest("the first column is over half the frame here")
        x1 = b.eval("document.querySelector('#projTbl tbody tr td:first-child').getBoundingClientRect().left")
        b.eval("document.querySelector('#projTbl').scrollLeft=80")
        b.pump(0.3)
        self.assertAlmostEqual(b.eval("document.querySelector('#projTbl tbody tr td:first-child').getBoundingClientRect().left"), x1, delta=1)


if __name__ == "__main__":
    unittest.main()
