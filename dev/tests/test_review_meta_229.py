"""#229 (UX review #172, finding 4): a Review row has ONE line of meta (kind, reason, source), not three.

The item's detail (owner, priority, due) goes on the row's tooltip (the one hover standard, data-tip) and stays in the peek; the
reason and the source stay on the line; "approve individually" and the conflict mark stay visible on the row, and the row is
keyboard reachable.

Run: python3 dev/tests/test_review_meta_229.py   (needs Google Chrome; skipped otherwise). Desktop width only.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

ROW = "tr.click[data-n]:not(.mparent)"


class ReviewMeta(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 1000

    def open_review(self):
        b = self.b
        b.eval("go('review',null,{legacy:true})")
        b.wait(f"!!document.querySelector('{ROW}')")

    def test_a_row_has_exactly_one_meta_line(self):
        b = self.b
        self.open_review()
        res = b.eval("""[...document.querySelectorAll('tr.click[data-n]')].map(tr=>{
          const t=tr.querySelector('td.title'), w=[...t.querySelectorAll('.why')].filter(e=>!e.closest('.conflict'));
          const lh=parseFloat(getComputedStyle(w[0]||t).lineHeight)||16;
          return [w.length, w[0]?w[0].getBoundingClientRect().height:0, lh]; })""")
        self.assertTrue(res)
        for n, h, lh in res:
            self.assertEqual(n, 1, "a row must have exactly one meta line")
            self.assertLessEqual(h, lh * 1.5 + 1, "the meta line wraps onto a second line")

    def test_detail_on_hover_and_in_the_peek_and_marks_stay(self):
        b = self.b
        self.open_review()
        r = b.eval("""(()=>{ const tr=document.querySelector('tr.click[data-n]:not(.mparent)'); const w=tr.querySelector('td.title .why');
          return {tip:w.getAttribute('data-tip')||'', n:tr.dataset.n}; })()""")
        self.assertTrue(r["tip"].strip(), "no tooltip carrying the detail")
        p = b.box(f"tr.click[data-n='{r['n']}'] td.title .why")
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=p["x"], y=p["y"], button="none")
        b.wait("!!document.getElementById('tip')&&document.getElementById('tip').classList.contains('on')&&document.getElementById('tip').textContent.trim().length>0", timeout=5)
        b.eval(f"openProposal({int(r['n'])})")
        b.wait("document.getElementById('panel').classList.contains('on')")
        self.assertTrue(b.eval("document.getElementById('panel').textContent.length>20"))
        b.key("Escape")
        # approve individually: visible, on the one meta line; the row is reachable by keyboard
        b.eval("(()=>{ const x=REV.find(y=>!y.done&&y.kind==='raid')||REV.find(y=>!y.done); x.indiv=true; renderReview(); })()")
        b.wait("!!document.querySelector('tr.click[data-n] .indiv')")
        self.assertTrue(b.eval("(e=>{const r=e.getBoundingClientRect(); return r.width>0&&r.height>0;})(document.querySelector('tr.click[data-n] .indiv'))"))
        self.assertEqual(b.eval("document.querySelector('tr.click[data-n] .indiv').closest('td.title').querySelectorAll('.why').length"), 1)
        self.assertTrue(b.eval("!!document.querySelector('tr.click[data-n] [data-act=a]')"))


if __name__ == "__main__":
    unittest.main()
