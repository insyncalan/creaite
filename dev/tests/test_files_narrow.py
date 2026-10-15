"""Files at phone width, and readable names in Files (v1.9.5 hand checks, insyncalan/creaite-plan#81).

Run: python3 dev/tests/test_files_narrow.py     (needs Google Chrome; skipped otherwise)

- At 320 px with the Archived chip selected and the page scrolled, the folder list never draws over the files table: the
  two boxes don't overlap, the table's rows are what is under the pointer, and nothing scrolls sideways. At 1400 px the
  folder list stays a column beside the table (the wide layout is unchanged).
- BL-101: people see names, never folder names: nothing visible in Files (the folder list, the chips, the Location column,
  the Archived rows) says `_portfolio`; the portfolio is "Portfolio".
Everything is fictional and temporary.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_archive_move_back import ENV, archive_old_files  # noqa: E402
from test_onedrive_projects import touch  # noqa: E402

ROWS_ON_TOP = """(()=>{ const rows=[...document.querySelectorAll('#filesTbl tr[data-fp]')], out=[];
  rows.forEach(tr=>{ const r=tr.getBoundingClientRect(); if(r.bottom<=0||r.top>=innerHeight) return;
    const x=Math.min(r.left+20,innerWidth-2), y=r.top+r.height/2, el=document.elementFromPoint(x,y);
    out.push([tr.dataset.fp, !!el&&tr.contains(el)]); });
  return out; })()"""
OVERLAP = """(()=>{ const a=document.getElementById('tree').getBoundingClientRect(), b=document.getElementById('filesTbl').getBoundingClientRect();
  return Math.max(0,Math.min(a.right,b.right)-Math.max(a.left,b.left))*Math.max(0,Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)); })()"""


class FilesNarrow(LiveBrowserCase):
    shared_server = True

    @classmethod
    def load(cls, v):
        from test_dashboard import populate
        populate(v)
        archive_old_files(v.root)
        touch(v.root / "projects/_portfolio/minutes/2026-10-12 Portfolio review.md", "the bilby review\n")   # a current portfolio file

    @classmethod
    def server_env(cls):
        return dict(ENV)

    def archived(self, width):
        b = self.b
        b.resize(width, 700)
        b.wait(f"innerWidth==={width}")
        b.eval("go('files')")
        b.wait("document.querySelector('#fquick [data-q=\"archived\"]')")
        b.eval("document.querySelector('#fquick [data-q=\"archived\"]').click()")
        b.wait("document.querySelector('#filesTbl [data-moveback]')")

    def test_at_320_the_folder_list_never_draws_over_the_archived_table(self):
        b = self.b
        self.archived(320)
        b.wait("document.documentElement.classList.contains('railicons')")
        for row in range(4):     # scroll each archived row to the top of the window in turn, as a person scrolling down would
            b.eval(f"document.querySelectorAll('#filesTbl tr[data-fp]')[{row}]?.scrollIntoView({{block:'start'}})")
            b.pump(0.1)
            self.assertEqual(b.eval(OVERLAP), 0, row)
            hits = b.eval(ROWS_ON_TOP)
            self.assertTrue(hits, row)
            self.assertTrue(all(h[1] for h in hits), hits)
        self.assertLessEqual(b.eval("document.documentElement.scrollWidth"), b.eval("innerWidth"))
        self.assertLessEqual(b.eval("document.getElementById('v-files').scrollWidth"),
                             b.eval("document.getElementById('v-files').clientWidth"))

    def test_at_1400_the_folder_list_stays_beside_the_table(self):
        b = self.b
        self.archived(1400)
        tree = b.eval("(()=>{ const r=document.getElementById('tree').getBoundingClientRect(); return [r.left,r.right,r.width]; })()")
        tbl = b.eval("document.getElementById('filesTbl').getBoundingClientRect().left")
        self.assertAlmostEqual(tree[2], 250, delta=1)
        self.assertGreater(tbl, tree[1])
        self.assertEqual(b.eval("getComputedStyle(document.getElementById('tree')).position"), "sticky")

    def test_nothing_in_files_says_underscore_portfolio(self):
        b = self.b
        self.archived(1400)
        rows = b.eval("[...document.querySelectorAll('#filesTbl tr[data-fp]')].map(tr=>tr.dataset.fp)")
        self.assertTrue(any("/_portfolio/" in r for r in rows), rows)      # the portfolio's archived minutes are listed
        self.assertNotIn("_portfolio", b.eval("document.getElementById('v-files').innerText"))
        locs = b.eval("[...document.querySelectorAll('#filesTbl tr[data-fp] td.x:first-of-type, #filesTbl tr[data-fp] td:nth-child(2)')].map(t=>t.textContent)")
        self.assertIn("Portfolio › minutes", locs)
        for chip in ("all", "week"):
            b.eval(f"document.querySelector('#fquick [data-q=\"{chip}\"]').click()")
            self.assertNotIn("_portfolio", b.eval("document.getElementById('v-files').innerText"), chip)
        b.eval("document.querySelector('#tree [data-p=\"_portfolio\"]').click()")
        self.assertEqual(b.eval("document.querySelector('#tree [data-p=\"_portfolio\"]').firstChild.textContent"), "Portfolio")
        self.assertNotIn("_portfolio", b.eval("document.getElementById('v-files').innerText"))

    def test_the_command_palette_names_the_portfolio_and_the_projects(self):
        b = self.b
        b.eval("go('files')")
        b.wait("FILES.some(f=>f.p==='_portfolio')")
        files = b.eval("ckItems('review').filter(x=>x.g==='Files').map(x=>[x.l,x.h])")
        self.assertIn(["2026-10-12 Portfolio review.md", "Portfolio › minutes"], files)
        every = b.eval("['minutes','reports','transcripts'].flatMap(q=>ckItems(q).filter(x=>x.g==='Files').map(x=>x.h))")
        self.assertTrue(every)
        self.assertFalse([h for h in every if "_portfolio" in h], every)
        self.assertTrue(any(h.startswith("Example Programme › ") for h in every), every)    # projects by name too (BL-101)
        self.assertTrue(b.eval("ckItems('ABC').some(x=>x.g==='Files')"))                    # the code still finds them
        b.eval("openCk(); const i=document.getElementById('cmdkIn'); i.value='review'; i.dispatchEvent(new Event('input',{bubbles:true}))")
        b.wait("document.querySelector('#cmdkList button')")
        self.assertNotIn("_portfolio", b.eval("document.getElementById('cmdkList').innerText"))
        self.assertIn("Portfolio › minutes", b.eval("document.getElementById('cmdkList').innerText"))
        b.eval("document.getElementById('cmdk').close()")


if __name__ == "__main__":
    unittest.main()
