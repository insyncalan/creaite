"""#240: the Work filter panel (the funnel's picker) is never clipped.
On a short list (one row shown) the whole panel, from its top to the Done button and the "Result: … shown" line,
must be inside the viewport and inside every ancestor that clips (overflow other than visible), at 1400 and 900 px wide;
also on a long list, a scrolled page and after a resize.

Run: python3 dev/tests/test_filter_panel_room.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import work_data as W  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402

# Returns the problems: each part of the panel that is outside the viewport or an ancestor that clips it.
MEASURE = r"""(()=>{
  const m=document.getElementById('moreMenu'); if(!m||!m.classList.contains('on')) return ['panel not open'];
  const parts=[['panel',m],['Done',document.getElementById(m.querySelector('.fpfoot .btn.primary')?.id||'x')],
               ['result',m.querySelector('.fpfoot .sub')]];
  const out=[], vw=document.documentElement.clientWidth, vh=document.documentElement.clientHeight, px=v=>Math.round(v);
  for(const [name,el] of parts){
    if(!el){ out.push(name+' missing'); continue; }
    const r=el.getBoundingClientRect();
    if(r.height<1) out.push(name+' has no height');
    if(r.top<-0.5||r.left<-0.5||r.bottom>vh+0.5||r.right>vw+0.5) out.push(`${name} outside the viewport ${px(r.top)}..${px(r.bottom)} / ${vh}`);
    if(name==='panel' && el.scrollHeight>el.clientHeight+1 && getComputedStyle(el).overflowY==='visible') out.push('panel overflows');
    for(let a=el.parentElement;a&&a!==document.documentElement;a=a.parentElement){
      const cs=getComputedStyle(a); if(cs.overflowX==='visible'&&cs.overflowY==='visible'&&cs.clipPath==='none'&&cs.contain.indexOf('paint')<0) continue;
      if(name==='panel' && getComputedStyle(m).position==='fixed' && cs.transform==='none' && cs.filter==='none' && cs.contain.indexOf('paint')<0 && cs.clipPath==='none') continue;  // a fixed box escapes overflow clipping
      const q=a.getBoundingClientRect();
      if(r.top<q.top-0.5||r.bottom>q.bottom+0.5||r.left<q.left-0.5||r.right>q.right+0.5)
        out.push(`${name} clipped by ${a.tagName.toLowerCase()}${a.id?'#'+a.id:''}.${[...a.classList].join('.')} (${cs.overflowX}/${cs.overflowY}) ${px(r.top)}..${px(r.bottom)} vs ${px(q.top)}..${px(q.bottom)}`);
      if(a===m) break;                                         // the panel's own box clips its parts; what clips the panel is checked for 'panel'
    }
  }
  const f=document.getElementById('moreBtn').getBoundingClientRect(), r=m.getBoundingClientRect();
  if(r.top<f.bottom-0.5||r.top>f.bottom+16) out.push(`panel not under the funnel: ${px(r.top)} vs ${px(f.bottom)}`);
  return out; })()"""


class Room(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 1000

    @classmethod
    def load(cls, v):
        populate(v)
        W.load(v)

    def setUp(self):
        super().setUp()
        self.b.eval("localStorage.clear()")

    def open_work(self, one_row):
        b = self.b
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tbody tr')")
        b.eval("clearAllFilters(); WQ=''; workChanged()")
        if one_row:
            first = b.eval("document.querySelector('#workTbl tbody tr[data-row]').dataset.row")
            b.eval(f"WQ={first!r}; workChanged()")
            b.wait("document.querySelectorAll('#workTbl tbody tr[data-row]').length===1")
        b.click("#moreBtn")
        b.wait("document.getElementById('moreMenu').classList.contains('on')")
        if b.eval("!!document.querySelector('#moreMenu [data-fpk=\"due\"]')"):
            b.click('#moreMenu [data-fpk="due"]')
        b.eval("new Promise(r=>setTimeout(r,400))")
        return b

    def check(self, label):
        problems = self.b.eval(MEASURE)
        self.assertEqual(problems, [], f"{label}: {problems}")

    def test_short_list_1400(self):
        self.open_work(True)
        self.check("1400, one row")

    def test_short_list_900(self):
        self.resize(900, 1000)
        self.open_work(True)
        self.check("900, one row")

    def test_long_list_scrolled_and_resized(self):
        b = self.open_work(False)
        self.check("1400, long list")
        b.eval("document.getElementById('moreBtn').click()")
        b.eval("window.scrollTo(0, 300); (document.scrollingElement||document.body).scrollTop=300; document.querySelector('main')?.scrollTo?.(0,300)")
        b.click("#moreBtn")
        b.wait("document.getElementById('moreMenu').classList.contains('on')")
        b.eval("new Promise(r=>setTimeout(r,400))")
        self.check("1400, long list, scrolled")
        self.resize(900, 700)
        self.check("900x700 after a resize")

    def resize(self, w, h):
        self.b.resize(w, h)
        self.b.eval("new Promise(r=>setTimeout(r,400))")


if __name__ == "__main__":
    unittest.main()
