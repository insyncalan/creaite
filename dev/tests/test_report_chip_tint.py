"""#193: neutral report chips and the label chips keep their tinted (--sunk) ground; the unified .chip must not repaint them white.

Run: python3 dev/tests/test_report_chip_tint.py   (needs Google Chrome; skipped otherwise)
Probes the cascade with throwaway elements in the real page, so it does not depend on which report is open.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import TEST_PALETTES, LiveBrowserCase  # noqa: E402
import milestone_data  # noqa: E402

PROBE = r"""(()=>{
  const out={}; const host=document.createElement('div'); host.id='chipProbe'; document.body.appendChild(host);
  const make=(wrap,cls)=>{ host.insertAdjacentHTML('beforeend','<div class="'+wrap+'"><span class="'+cls+'">Chip</span></div>'); const e=host.lastElementChild.firstElementChild; const c=getComputedStyle(e); return {bg:c.backgroundColor,color:c.color,h:e.getBoundingClientRect().height}; };
  const tok=(prop,v)=>{ const e=document.createElement('span'); e.style[prop]=v; host.appendChild(e); return getComputedStyle(e)[prop]; };
  out.sunk=tok('backgroundColor','var(--sunk)'); out.muted=tok('color','var(--muted)');
  out.rp=make('rp','chip'); out.labels=make('nlabels','chip');
  host.remove(); return out; })()"""


class ReportChipTint(LiveBrowserCase):
    shared_server = True

    @classmethod
    def load(cls, v):
        milestone_data.load(v)

    def test_neutral_chips_keep_the_grey_tint(self):
        for palette in TEST_PALETTES:
            for mode in ("light", "dark"):
                self.b.eval(f"document.documentElement.dataset.palette='{palette}'; document.documentElement.dataset.theme='{mode}'")
                o = self.b.eval(PROBE)
                for k in ("rp",):   # #254: the cockpit's Reporting card (rp-cockcard) is gone
                    self.assertEqual(o[k]["bg"], o["sunk"], f"{palette} {mode} {k}: fill is not --sunk")
                    self.assertEqual(o[k]["color"], o["muted"], f"{palette} {mode} {k}: text is not --muted")
                    self.assertAlmostEqual(o[k]["h"], 26, delta=1, msg=f"{palette} {mode} {k}: not 26px")
                self.assertEqual(o["labels"]["bg"], o["sunk"], f"{palette} {mode}: label chip fill is not --sunk")
                self.assertAlmostEqual(o["labels"]["h"], 24, delta=1, msg="label chip is not 24px")


if __name__ == "__main__":
    unittest.main()
