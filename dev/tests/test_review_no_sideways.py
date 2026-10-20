"""#271: Review never scrolls sideways. Expanding a minutes row's "n items" toggle shows its items, and a child item's long source
("projects/<engagement>/minutes/<date> <title>.html — Actions"), its reject guess and its "Looks like …" tag used to widen the
table past its frame, so the generic wide-table cue ("more columns →", BL-165) appeared. The meta line truncates with an ellipsis
(its full text on the row's tooltip, data-tip, and in the element's title), the title cell's tags wrap, and Project, Approve and
Reject stay visible and clickable at 900 and 1440.

Run: python3 dev/tests/test_review_no_sideways.py   (needs Google Chrome; skipped otherwise). Desktop widths only.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

LONG_SRC = ("projects/Northwind Harbour Data and Analytics Modernisation Engagement/minutes/2026-10-14 Northwind Harbour "
            "Steering Committee Weekly Working Session and Decision Review.html — Actions")
LONG_WHY = "Raised by Priya Example in the closing round as an action for the delivery leads with a firm date agreed"

# give every pending row a long, unbroken source, a long reason, a reject guess and a "Looks like" tag, then open every minutes row
MAKE_LONG = """(()=>{ REV.filter(r=>!r.done).forEach(r=>{ r.src=%r; r.why=%r;
    if(!isMin(r)) r.dup={id:'ABC-A-001',t:'Chase legal on the statement of work for the Northwind Harbour data platform',strength:'Possible',p:'ABC'}; });
  rjGuesses.value=Object.fromEntries(REV.filter(r=>!r.done).map(r=>[r.file+'#'+r.ref,{reason:'Duplicate',why:'looks like ABC-A-001 Chase legal on the statement of work for the Northwind Harbour data platform',of:'ABC-A-001'}]));
  renderReview(); document.querySelectorAll('#reviewBody tr.mparent [data-act=t][aria-expanded=false]').forEach(t=>t.click()); return document.querySelectorAll('#reviewBody tr.mchild').length; })()""" % (LONG_SRC, LONG_WHY)

STATE = """(()=>{ const page=document.scrollingElement, fr=[...document.querySelectorAll('#reviewBody .tbl')];
  const vis=e=>{ if(!e) return false; const r=e.getBoundingClientRect(); return getComputedStyle(e).visibility!=='hidden'&&r.width>0&&r.height>0; };
  const inFrame=(e,f)=>{ const a=e.getBoundingClientRect(), b=f.getBoundingClientRect(); return a.left>=b.left-1&&a.right<=b.right+1; };
  const rows=[...document.querySelectorAll('#reviewBody tr[data-n]')].map(tr=>{ const f=tr.closest('.tbl'), m=tr.querySelector('td.title .why.rvmeta');
    const btn=s=>{ const e=tr.querySelector(s); return !!e&&vis(e)&&inFrame(e,f); };
    return {child:tr.classList.contains('mchild'), approve:btn('[data-act=a]'), reject:btn('[data-act=r]'),
      project:!tr.querySelector('.rvpj')||btn('.rvpj'),
      clipped:!!m&&m.scrollWidth>m.clientWidth+1, ellipsis:!!m&&getComputedStyle(m).textOverflow==='ellipsis',
      full:!!m&&((m.getAttribute('title')||'')+' '+(m.getAttribute('data-tip')||'')).includes('Steering Committee Weekly Working Session')}; });
  return {pageOver:page.scrollWidth>page.clientWidth+1,
    over:fr.filter(f=>f.querySelector('table').scrollWidth>f.clientWidth+1||f.scrollWidth>f.clientWidth+1).length,
    cue:document.querySelectorAll('#reviewBody .xcue').length, pj:document.querySelectorAll('#reviewBody tr.mchild .rvpj').length, frames:fr.length, rows}; })()"""


class ReviewNoSideways(LiveBrowserCase):
    shared_server = True

    def check(self, width):
        b = self.b
        b.resize(width, 900)
        b.eval("go('review')")
        b.wait("!!document.querySelector('#reviewBody tr.mparent')")
        self.assertGreater(b.eval(MAKE_LONG), 0, "no minutes row with items to expand")
        b.pump(0.6)                       # xcueAll runs after the render
        s = b.eval(STATE)
        self.assertFalse(s["pageOver"], (width, "the page scrolls sideways"))
        self.assertEqual(s["over"], 0, (width, "a Review table is wider than its frame", s))
        self.assertEqual(s["cue"], 0, (width, "the 'more columns' cue shows on Review"))
        self.assertGreater(s["pj"], 0, "no Project button on an expanded item")
        kids = [r for r in s["rows"] if r["child"]]
        self.assertTrue(kids)
        for r in s["rows"]:
            self.assertTrue(r["approve"] and r["reject"] and r["project"], (width, r))
        for r in kids:
            self.assertTrue(r["clipped"] and r["ellipsis"], (width, "the long meta line should truncate with an ellipsis", r))
            self.assertTrue(r["full"], (width, "the full source should be on the line's title or tooltip", r))
        # Approve on an expanded child is clickable where it is drawn (hit-testing, not element.click())
        hit = b.eval("""(()=>{ const e=document.querySelector('#reviewBody tr.mchild [data-act=a]'), r=e.getBoundingClientRect();
          const at=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2); return !!at&&!!at.closest('[data-act=a]')&&at.closest('tr')===e.closest('tr'); })()""")
        self.assertTrue(hit, (width, "Approve on an expanded item is covered or off screen"))

    def test_900(self):
        self.check(900)

    def test_1440(self):
        self.check(1440)


if __name__ == "__main__":
    unittest.main()
