"""BL-213: the milestone strip's text meets WCAG 1.4.3 (4.5:1 under 24px, or 18.66px bold) in every theme, light and dark.

Run: python3 dev/tests/test_strip_contrast.py   (needs Google Chrome; skipped otherwise)
A real browser and server on milestone_data's project. The colours are the rendered ones (getComputedStyle, each background
composited up to an opaque one), and the themes come from the page's own THEMES list, so a new theme is checked by itself.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase, theme_names  # noqa: E402
import milestone_data  # noqa: E402

# Every visible element with its own words inside the parts of the card and page BL-213 names: the plan line (month labels,
# the today mark, the milestone labels), its bar, the details toggle, the State/range labels. Returns the failures.
CHECK = r"""(scope=>{
  const P=s=>{ const m=s.match(/rgba?\(([^)]+)\)/); if(m){ const p=m[1].split(/[ ,\/]+/).filter(Boolean).map(Number); return [p[0],p[1],p[2],p.length>3?p[3]:1]; }
    const c=s.match(/color\(srgb ([^)]+)\)/); if(c){ const p=c[1].split(/[ \/]+/).filter(Boolean).map(Number); return [p[0]*255,p[1]*255,p[2]*255,p.length>3?p[3]:1]; }
    return [0,0,0,0]; };
  const over=(a,b)=>{ const t=a[3]+b[3]*(1-a[3]); if(!t) return [0,0,0,0]; return [0,1,2].map(i=>(a[i]*a[3]+b[i]*b[3]*(1-a[3]))/t).concat([t]); };
  const bgOf=el=>{ const layers=[]; for(let e=el;e;e=e.parentElement){ const c=P(getComputedStyle(e).backgroundColor); if(c[3]>0) layers.push(c); if(c[3]>=1) break; }
    let out=[255,255,255,1]; for(let i=layers.length-1;i>=0;i--) out=over(layers[i],out); return out; };
  const lum=c=>{ const f=v=>{ v/=255; return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4); }; return 0.2126*f(c[0])+0.7152*f(c[1])+0.0722*f(c[2]); };
  const ratio=(a,b)=>{ const x=lum(a), y=lum(b); return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05); };
  const sel=".mv-strip *, .mv-stripbar *, .mv-detog *, .mv-lbl, .mv-range *";
  const bad=[]; let n=0;
  for(const el of scope.querySelectorAll(sel)){
    if(![...el.childNodes].some(t=>t.nodeType===3&&t.textContent.trim())) continue;
    const r=el.getBoundingClientRect(), cs=getComputedStyle(el); if(!r.width||!r.height||cs.visibility==="hidden") continue;
    let op=1; for(let e=el;e;e=e.parentElement) op*=Number(getComputedStyle(e).opacity);
    const bg=bgOf(el), fg=P(cs.color); fg[3]*=op; const shown=over(fg,bg);
    const size=parseFloat(cs.fontSize), bold=Number(cs.fontWeight)>=700, need=(size>=24||(bold&&size>=18.66))?3:4.5;
    const k=ratio(shown,bg); n++;
    if(k<need) bad.push(`${el.className||el.tagName} "${el.textContent.trim().slice(0,30)}" ${k.toFixed(2)} < ${need}`);
  }
  return {n,bad};
})"""


class StripContrast(LiveBrowserCase):
    shared_server = True

    @classmethod
    def load(cls, v):
        milestone_data.load(v)

    def setUp(self):
        super().setUp()
        self.b.eval("try{ localStorage.removeItem('creaite.cockpit.milestones.view'); localStorage.removeItem('creaite.cockpit.milestones.details'); }catch(e){}")

    def check(self, where):
        failures, counted = [], 0
        for palette in theme_names():
            for mode in ("light", "dark"):
                self.b.eval(f"document.documentElement.dataset.palette='{palette}'; document.documentElement.dataset.theme='{mode}'")
                self.b.wait(f"getComputedStyle(document.documentElement).colorScheme.includes('{mode}')||true")
                out = self.b.eval(f"{CHECK}(document.querySelector('{where}'))")
                counted += out["n"]
                failures += [f"{palette} {mode}: {x}" for x in out["bad"]]
        self.assertGreater(counted, 9 * 2 * 3, "the check found almost no text: the selectors no longer match the strip")
        self.assertEqual(failures, [])

    def test_the_projects_milestones_card(self):
        self.b.eval("go('cockpit','ABC')")
        self.b.wait("document.querySelector('#mvCard .mv-strip .mon')")
        self.check("#mvCard")

    def test_the_milestones_page(self):
        self.b.eval("mvOpenPage('ABC','plan')")
        self.b.wait("VIEW==='milestones'&&document.querySelector('#v-milestones .mv-strip .mon')")
        self.check("#v-milestones")

    def test_the_strip_words_use_muted_not_faint(self):
        """--faint stays for marks (rules, ticks); text in the strip uses --muted."""
        self.b.eval("go('cockpit','ABC')")
        self.b.wait("document.querySelector('#mvCard .mv-strip .mon')")
        got = self.b.eval("""(()=>{ const t=document.createElement('span'); t.style.color='var(--muted)'; document.body.append(t);
          const m=getComputedStyle(t).color; t.remove();
          return ['#mvCard .mv-strip .mon','#mvCard .mv-detog button'].map(s=>getComputedStyle(document.querySelector(s)).color===m); })()""")
        self.assertEqual(got, [True, True])


if __name__ == "__main__":
    unittest.main(verbosity=2)
