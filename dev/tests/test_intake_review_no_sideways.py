"""#232 (v2.6): the Intake page never scrolls sideways, at 900 and at 1440, in List, Board and Two panes. The old Upload files
table (#inboxTbl, eight columns) needed 809px in a 731px frame at 900, so the wide-table cue ("more columns →", BL-165) showed;
#271 fixed the same on the old Review page. Here every row gets a long, unbroken title, a long project-free source and a long note,
a drafted meeting is opened, and then: the page and every table fit their frame, no cue shows, nothing inside the page reaches past
the content's right edge, and each row's main button is visible and clickable where it is drawn.

Run: python3 dev/tests/test_intake_review_no_sideways.py   (needs Google Chrome; skipped otherwise). Desktop widths only.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ir_intake_support import DAY, IntakeBase  # noqa: E402
from pages_support import resize  # noqa: E402

LONG = "Northwind Harbour Data and Analytics Modernisation Engagement Steering Committee Weekly Working Session and Decision Review"
LONG_FILE = "2026-10-05_Northwind-Harbour-Data-and-Analytics-Modernisation-Engagement-Steering-Committee-Weekly-Working-Session.vtt"
LONG_SRC = ("projects/Northwind Harbour Data and Analytics Modernisation Engagement/minutes/2026-10-14 Northwind Harbour "
            "Steering Committee Weekly Working Session and Decision Review.html — Actions")
LONG_WHY = "Raised by Priya Example in the closing round as an action for the delivery leads with a firm date agreed"

# a long title on every meeting and file, a long note on each, a long source and reason on every pending proposal; redraw
MAKE_LONG = """(()=>{ const L=%s, N=%s;
  D.intake_review={...D.intake_review, meetings:D.intake_review.meetings.map(m=>({...m,title:m.src==='upload'?m.title:L+' '+m.title}))};
  D.intake_review.meetings.forEach(m=>irNote(m.id,N));
  REV.filter(r=>!r.done).forEach(r=>{ r.src=%s; r.why=%s; if(r.rec) r.rec.t=L; });
  const d=D.intake_review.meetings.find(m=>m.stage==='drafted'); if(d) irOpen.value=d.id; irSel.value=d?d.id:null;
  irTick.value++; return {drafted:!!d, rows:D.intake_review.meetings.length}; })()""" % (
    json.dumps(LONG), json.dumps("Couldn't: " + LONG), json.dumps(LONG_SRC), json.dumps(LONG_WHY))

STATE = """(()=>{ const page=document.scrollingElement, v=document.querySelector('#v-intake-review'), box=v.getBoundingClientRect();
  const fr=[...v.querySelectorAll('.tbl')];
  const vis=e=>{ const r=e.getBoundingClientRect(); return getComputedStyle(e).visibility!=='hidden'&&r.width>0&&r.height>0; };
  const past=[...v.querySelectorAll('*')].filter(e=>!e.closest('.icdrop')&&vis(e)&&e.getBoundingClientRect().right>box.right+1)
    .slice(0,5).map(e=>e.tagName+'.'+String(e.className||'').slice(0,40)+' '+Math.round(e.getBoundingClientRect().right)+'>'+Math.round(box.right));
  const hit=s=>[...v.querySelectorAll(s)].filter(vis).filter(e=>{ e.scrollIntoView({block:'center',inline:'nearest'}); const r=e.getBoundingClientRect(), at=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);
    return !(at&&(at===e||e.contains(at))); }).slice(0,3).map(e=>(e.dataset.ira||e.dataset.act)+' in '+String((e.closest('[data-irm],[data-irn]')||{}).className||'').slice(0,30)+' at '+(at=>at?at.tagName+'.'+String(at.className).slice(0,30):'nothing')(document.elementFromPoint(e.getBoundingClientRect().left+e.getBoundingClientRect().width/2,e.getBoundingClientRect().top+e.getBoundingClientRect().height/2)));
  const covered=hit('[data-ira=process],[data-ira=later],[data-ira=notneeded],[data-act=a],[data-act=r]'); document.scrollingElement.scrollTop=0;
  return {pageOver:page.scrollWidth>page.clientWidth+1, viewOver:v.scrollWidth>v.clientWidth+1,
    over:fr.filter(f=>f.scrollWidth>f.clientWidth+1||(f.querySelector('table')&&f.querySelector('table').scrollWidth>f.clientWidth+1)).length,
    cue:v.querySelectorAll('.xcue').length, past, frames:fr.length,
    covered,
    procs:[...v.querySelectorAll('[data-ira=process]')].filter(vis).length}; })()"""


class IntakeNoSideways(IntakeBase):
    """The rebuilt Intake page fits its frame at 900 and 1440 in every view."""

    def setUp(self):
        (self.v.root / "inbox" / LONG_FILE).write_text("WEBVTT\n\n00:00:01.000 --> 00:00:05.000\nHello\n")
        super().setUp()

    def tearDown(self):
        (self.v.root / "inbox" / LONG_FILE).unlink(missing_ok=True)
        resize(self.b, self.width, self.height)
        super().tearDown()

    def check(self, width, view):
        b = self.b
        resize(b, width, 900)
        b.eval(f"irSetView({json.dumps(view)})")
        b.wait(f"!!document.querySelector('#v-intake-review [data-irm]') && irView.value==={json.dumps(view)}")
        made = b.eval(MAKE_LONG)
        self.assertGreater(made["rows"], 2)
        b.pump(0.6)                       # xcueAll runs after the render
        if b.eval("typeof xcueAll==='function'"):
            b.eval("xcueAll()")
            b.pump(0.2)
        s = b.eval(STATE)
        where = (width, view)
        self.assertFalse(s["pageOver"], (where, "the page scrolls sideways", s))
        self.assertFalse(s["viewOver"], (where, "the Intake page is wider than its frame", s))
        self.assertEqual(s["over"], 0, (where, "a table on Intake is wider than its frame", s))
        self.assertEqual(s["cue"], 0, (where, "the 'more columns' cue shows on Intake", s))
        self.assertEqual(s["past"], [], (where, "something reaches past the page's right edge", s))
        self.assertEqual(s["covered"], [], (where, "a row's button is covered or off screen", s))
        if view != "two":
            self.assertGreater(s["procs"], 0, (where, "no Process button drawn", s))

    def test_list_900(self):
        self.check(900, "list")

    def test_board_900(self):
        self.check(900, "board")

    def test_panes_900(self):
        self.check(900, "two")

    def test_list_1440(self):
        self.check(1440, "list")

    def test_board_1440(self):
        self.check(1440, "board")

    def test_panes_1440(self):
        self.check(1440, "two")

    def test_the_long_file_has_its_row(self):
        """The fixture really draws the long file (else the checks above prove nothing about it)."""
        resize(self.b, 900, 900)
        self.assertTrue(self.b.eval("D.intake_review.meetings.some(m=>m.src==='upload'&&m.title.includes('Northwind-Harbour'))"))
        self.assertEqual(DAY, "2026-10-05")


if __name__ == "__main__":
    unittest.main()
