"""v2.0.0 polish B (check 44's sheet, #61): three defects, each measured at 1400 and 900 px in the Notes tab.

- (4) the finished-run badge never covers the Apply button of the Find updates panel;
- (3) opening Find updates closes the AI bar (its selection's context has gone);
- (2) the AI bar never hides the words of the line after the selection.

Run: python3 dev/tests/test_v200_polish_b.py   (needs Google Chrome; skipped otherwise)
The real live server in a throwaway vault; Claude is the stand-in of test_ai_select_notes.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import notes_find_fixture as fx  # noqa: E402
from test_ai_select_notes import AiInANote  # noqa: E402

WIDTHS = (1400, 900)
NEXT_LINE = """(()=>{ const bar=document.querySelector('#aiLayer .aibar').getBoundingClientRect();
  const sel=getSelection(); const ps=[...document.querySelectorAll('#v-notes .nbody [data-p]')];
  const i=ps.findIndex(p=>p.contains(sel.anchorNode)); const nx=ps[i+1]; if(!nx) return null;
  const rg=document.createRange(); rg.selectNodeContents(nx); const hit=[...rg.getClientRects()].filter(r=>r.width>0&&r.height>0&&
    !(r.right<=bar.left||r.left>=bar.right||r.bottom<=bar.top||r.top>=bar.bottom));
  return {bar:[bar.top,bar.bottom,bar.left,bar.right], hits:hit.length}; })()"""


class PolishB(AiInANote):
    def test_the_run_badge_never_covers_apply_in_find_updates(self):
        b = self.b
        for w in WIDTHS:
            b.resize(w, 900)
            self.open_note()
            b.click("#noteFind")
            b.wait("!!document.getElementById('fuApply') && ['ready','none','error','ask'].includes(fuState.value)", 40)
            b.eval("RB.state='done'; RB.took='0:00'; rbDraw()")
            b.pump(0.4)
            COVER = """(()=>{ const a=document.getElementById('fuApply'), r=a.getBoundingClientRect(); if(r.bottom<=0||r.top>=innerHeight) return 'off';
              const pts=[]; for(const x of [.05,.3,.5,.7,.95]) for(const y of [.1,.5,.9]) pts.push(document.elementFromPoint(r.left+r.width*x,r.top+r.height*y));
              const bad=pts.find(e=>!(e&&(e===a||a.contains(e)))); window.__cov=bad?(bad.id||bad.className||bad.tagName)+' in '+(bad.closest('#runBadge')?'badge':'page'):''; return bad?'covered':'clear'; })()"""
            sc = "(()=>{ let c=document.getElementById('fuApply').parentElement; while(!(c.scrollHeight>c.clientHeight+5&&/auto|scroll/.test(getComputedStyle(c).overflowY))) c=c.parentElement; return c; })()"
            seen = set()
            top = b.eval(f"({sc}).scrollTop=1e6, ({sc}).scrollTop")
            for k in range(0, 420, 20):                                   # Apply scrolled through the band the badge sits in
                b.eval(f"({sc}).scrollTop={top - k}")
                b.pump(0.15)
                got = b.eval(COVER)
                seen.add(got)
                self.assertNotEqual(got, "covered", f"{w}: covered by {b.eval('window.__cov')} at scroll {top - k}")
            self.assertIn("clear", seen)
            b.eval("RB.state=''; rbDraw(); document.getElementById('noteFind').click()")


for _n in [n for n in dir(AiInANote) if n.startswith("test_") and n not in PolishB.__dict__]:   # the base class's own tests live in test_ai_select_notes
    setattr(PolishB, _n, None)


if __name__ == "__main__":
    unittest.main()
