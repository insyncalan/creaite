"""#158 Phase B part 2: Help's home lists the twelve jobs. help.md's `Jobs:` block under Start here is parsed like the other blocks;
every link must resolve to a how-to card. The page: a grid of cards after the loop and the first hour, each opening its page.

Run: python3 dev/tests/test_help_jobs.py   (the page tests need Google Chrome; skipped otherwise)
"""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import TEST_PALETTES_JS, LiveBrowserCase  # noqa: E402
from test_tracker import REPO  # noqa: E402

sys.path.insert(0, str(REPO / "system" / "scripts"))
import build_dashboard as bd  # noqa: E402

TWELVE = ["Start the day", "Review and approve proposals", "Turn a meeting into minutes", "Prepare for a meeting", "Capture a note",
          "Add or change an item", "Ask someone for an update", "Close the day", "Write the weekly report", "Write a client report",
          "Find anything", "Undo a mistake"]


class JobsBlock(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = bd.help_sections()
        cls.ids = {t["id"] for t in cls.h["tasks"]}

    def test_the_twelve_in_the_agreed_order_and_words(self):
        self.assertEqual([t for t, _ in self.h["jobs"]], TWELVE)

    def test_every_job_link_resolves_to_a_how_to_card(self):
        for title, i in self.h["jobs"]:
            self.assertIn(i, self.ids, f"{title} → {i}")
        self.assertEqual(len({i for _, i in self.h["jobs"]}), 12)

    def test_the_block_sits_after_the_loop_and_the_first_hour(self):
        html = next(t["html"] for t in self.h["tabs"] if t["id"] == "start")
        at = [html.index(x) for x in ('class="hp-loop"', 'class="hp-steps"', 'class="hp-jobs"', 'class="hp-rhythm"')]
        self.assertEqual(at, sorted(at))
        self.assertEqual(html.count('class="hp-job"'), 12)
        self.assertEqual(len(re.findall(r'<div class="hp-job"><a href="#help-howto-[a-z0-9-]+" data-help="howto-[a-z0-9-]+">', html)), 12)
        self.assertNotIn("Jobs:", re.sub(r"<[^>]+>", " ", html))                    # the label line is not shown
        self.assertEqual(self.h["start"]["jobs"], [i for _, i in self.h["jobs"]])


class JobsPage(LiveBrowserCase):
    shared_server = True

    def test_help_opens_on_start_here_and_a_job_opens_its_page(self):
        b = self.b
        b.eval("go('help')")
        r = b.eval("""(()=>({hash:location.hash, jobs:[...document.querySelectorAll('#helpPane .hp-job a')].map(a=>a.textContent)}))()""")
        self.assertEqual(r["hash"], "#help-start")
        self.assertEqual(r["jobs"], TWELVE)
        b.eval("document.querySelector('#helpPane .hp-jobs').scrollIntoView()")
        b.click("#helpPane .hp-job a[data-help='howto-close-the-day']")
        b.pump(0.3)
        self.assertEqual(b.eval("location.hash"), "#help-howto-close-the-day")
        self.assertTrue(b.eval("document.querySelector('#ht-close-the-day').classList.contains('hp-hl')"))

    def test_the_grid_at_desktop_and_900_in_both_palettes_and_modes(self):
        b = self.b
        for width, cols_min, cols_max in ((1400, 3, 6), (900, 2, 4)):
            b.resize(width, 900)
            b.eval("go('help','start')")
            r = b.eval("""(()=>{ const g=document.querySelector('#helpPane .hp-jobs'); const lum=c=>{ const [r,g,b]=c.match(/[\\d.]+/g).slice(0,3).map(Number).map(v=>{ v/=255; return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4); }); return 0.2126*r+0.7152*g+0.0722*b; };
              const ratio=(a,b)=>{ const x=lum(a), y=lum(b); return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05); };
              const bgOf=el=>{ for(let e=el;e;e=e.parentElement){ const c=getComputedStyle(e).backgroundColor; if(!/rgba\\(0, 0, 0, 0\\)|transparent/.test(c)) return c; } return 'rgb(255,255,255)'; };
              const res={}; for(const pal of %s) for(const mode of ['Light','Dark']){ S.palette=pal; S.theme=mode; applyTheme(); const a=document.querySelector('#helpPane .hp-job a'); res[pal+'|'+mode]=ratio(getComputedStyle(a).color,bgOf(a)); }
              return {cols:getComputedStyle(g).gridTemplateColumns.split(' ').length, side:document.documentElement.scrollWidth<=innerWidth+1, res}; })()""" % TEST_PALETTES_JS)
            self.assertTrue(cols_min <= r["cols"] <= cols_max, (width, r["cols"]))
            self.assertTrue(r["side"], width)
            self.assertEqual({k: v for k, v in r["res"].items() if v < 4.5}, {}, width)


if __name__ == "__main__":
    unittest.main()
