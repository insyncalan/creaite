"""Files navigation (#192, v2.3.0): one model. Pills choose the view, the tree the folder, the Filter narrows within.

Run: python3 dev/tests/test_files_navigation.py     (needs Google Chrome; skipped otherwise)

At 1400 and 900 px, with the clock pinned (CREAITE_NOW) and fictional vault files:
- four pills (All files, Latest reports, This week's meetings, Archived), exclusive; Archived is a view (the archive's rows);
- the tree shows Intake once (no Intake pill, no Weekly/Adhoc/Steerco chips);
- one search bar (the vault's, with the ask creaite button) and no second name box;
- the Filter is Work's funnel icon button (.ib.bd.fbtn, .fcount) on the pills' line; its menu has Type and From/To with the
  popup calendar (typed DD-MM-YYYY accepted, Clear, Today); applied filters are chips on the row below; Esc closes and returns focus;
- combined: a pill clears the folder, a folder clears the pill, the filter narrows inside both.
Everything is fictional and temporary.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_archive_move_back import ENV, archive_old_files  # noqa: E402


class FilesNavigation(LiveBrowserCase):
    shared_server = True

    @classmethod
    def load(cls, v):
        from test_dashboard import populate
        populate(v)
        archive_old_files(v.root)

    @classmethod
    def server_env(cls):
        return dict(ENV)

    def open(self, width=1400):
        b = self.b
        b.resize(width, 800)
        b.wait(f"innerWidth==={width}")
        b.eval("go('files')")
        b.wait("document.querySelector('#fmBtn') && document.querySelector('#filesTbl tr[data-fp]')")
        return b

    def rows(self):
        return self.b.eval("[...document.querySelectorAll('#filesTbl tr[data-fp]')].map(t=>t.dataset.fp)")

    def view(self, q):
        """#341 item 13: the view is chosen in Filter (View radios), not by pills."""
        self.b.eval("(()=>{ if(!document.querySelector('#fmenu.on')) document.querySelector('#fmBtn').click(); document.querySelector('#fmenu input[name=fsView][value=" + q + "]').click(); })()")

    def pressed(self):
        return self.b.eval("(q=>q==='all'?(shared.FSEL.p==='All'&&shared.FSEL.f==='All'&&!shared.FSEL.sub?['all']:[]):[q])(shared.FSEL.quick)")

    def test_four_pills_exclusive_and_archived_is_a_view(self):
        for width in (1400, 900):
            b = self.open(width)
            self.assertEqual(b.eval("document.querySelectorAll('#fquick').length"), 0)       # the pills are gone
            b.click("#fmBtn")
            self.assertEqual(b.eval("[...document.querySelectorAll('#fmenu input[name=fsView]')].map(x=>x.parentElement.textContent.trim())"),
                             ["All files", "Latest reports", "This week's meetings", "Archived"], width)
            self.assertEqual(b.eval("document.querySelectorAll('#fmenu [data-rep], #fmenu input[value=inbox]').length"), 0)
            b.key("Escape")
            for q in ("latest", "week", "archived", "all"):
                self.view(q)
                self.assertEqual(self.pressed(), [q], (width, q))
            self.view("archived")
            self.assertTrue(b.eval("!!document.querySelector('#filesTbl [data-moveback]')"))
            rows = b.eval("[...document.querySelectorAll('#filesTbl tr[data-fp]')].map(t=>!!t.querySelector('[data-moveback]'))")
            self.assertEqual(len(rows), b.eval("D.files_archived.length"), width)       # exactly the archive's files
            self.assertTrue(rows and all(rows), width)                                   # every row is an archived one (Move back)
            self.view("all")
            self.assertFalse(b.eval("!!document.querySelector('#filesTbl [data-moveback]')"), width)   # no archived row in All files

    def test_tree_shows_intake_once_and_a_folder_clears_the_pill(self):
        b = self.open()
        self.assertEqual(b.eval("[...document.querySelectorAll('#v-files button, #v-files a')].filter(x=>x.textContent.trim().startsWith('Intake')).length"), 1)
        self.view("latest")
        b.click('#tree [data-p="inbox"]')
        self.assertEqual(self.pressed(), [])        # a folder clears the pill
        self.view("week")
        self.assertEqual(b.eval("[...document.querySelectorAll('#tree [aria-pressed=true]')].map(x=>x.dataset.p)"), ["All"])   # a pill clears the folder

    def test_one_search_bar_with_the_ask_button(self):
        b = self.open()
        self.assertEqual(b.eval("document.querySelectorAll('#v-files input[type=search]').length"), 1)
        self.assertEqual(b.eval("document.querySelector('#vsInput').placeholder"), "Search everything")
        self.assertTrue(b.eval("!!document.querySelector('#vsAskBtn')"))
        self.assertFalse(b.eval("!!document.getElementById('fsName')"))

    def test_filter_button_on_the_pills_line_with_count(self):
        for width in (1400, 900):
            b = self.open(width)
            self.assertTrue(b.eval("document.getElementById('fmBtn').matches('.ib.bd.fbtn')"))
            self.assertEqual(b.eval("!!document.querySelector('#fmBtn svg')"), True)
            rf = b.box("#filesRefresh"); btn = b.box("#fmBtn")
            self.assertLess(abs(rf["y"] - btn["y"]), 6, width)
            self.assertFalse(b.eval("!!document.querySelector('#fmBtn .fcount')"))
            self.assertEqual(b.eval("document.getElementById('fchips').hidden"), True)

    def test_menu_type_and_dates_chips_clear_and_refresh(self):
        b = self.open()
        all_n = len(self.rows())
        b.click("#fmBtn")
        self.assertEqual(b.eval("document.getElementById('fmBtn').getAttribute('aria-expanded')"), "true")
        self.assertTrue(b.eval("!!document.querySelector('#fmenu input[name=fsType]')"))
        b.click("#fmenu input[name=fsType][value=docx]")
        self.assertEqual(b.eval("document.querySelector('#fmBtn .fcount').textContent"), "1")
        self.assertTrue(all(r.endswith(".docx") for r in self.rows()), self.rows())
        # a typed date is accepted, shown DD-MM-YYYY in the chip
        b.eval("(()=>{ const i=document.getElementById('fsFrom'); i.value='01-10-2026'; i.dispatchEvent(new Event('input',{bubbles:true})); })()")
        self.assertEqual(b.eval("document.querySelector('#fmBtn .fcount').textContent"), "2")
        self.assertEqual(b.eval("[...document.querySelectorAll('#fchips .fchip')].map(c=>c.textContent.replace('✕',''))"),
                         ["Type: Word", "From 01-10-2026"])
        # the popup calendar: Today fills To; Clear empties it
        b.click('#fmenu [data-cal="fsTo"]')
        b.wait("document.querySelector('.cal')")
        b.eval("[...document.querySelectorAll('.cal .cf button')].find(x=>x.textContent==='Today').click()")
        self.assertTrue(b.eval("/^\\d\\d-\\d\\d-\\d{4}$/.test(document.getElementById('fsTo').value)"))
        self.assertEqual(b.eval("document.querySelector('#fmBtn .fcount').textContent"), "3")
        b.click('#fmenu [data-cal="fsTo"]')
        b.wait("document.querySelector('.cal')")
        b.eval("[...document.querySelectorAll('.cal .cf button')].find(x=>x.textContent==='Clear').click()")
        self.assertEqual(b.eval("document.getElementById('fsTo').value"), "")
        self.assertEqual(b.eval("document.querySelector('#fmBtn .fcount').textContent"), "2")
        # Esc closes the menu and returns focus to the Filter button
        b.key("Escape")
        self.assertEqual(b.eval("document.getElementById('fmenu').classList.contains('on')"), False)
        self.assertEqual(b.eval("document.activeElement.id"), "fmBtn")
        # chips row: remove one; Clear in the menu removes the rest; count and Refresh share the pills' line
        b.click('#fchips [data-fclr="type"]')
        self.assertEqual(b.eval("document.querySelector('#fmBtn .fcount').textContent"), "1")
        self.assertTrue(b.eval("!!document.getElementById('filesRefresh') && /files/.test(document.getElementById('filesCount').textContent)"))
        pill = b.box("#fmBtn"); rf = b.box("#filesRefresh")
        self.assertLess(abs(pill["y"] - rf["y"]), 6)
        b.click("#fmBtn")
        b.click("#fmClear")
        self.assertEqual(b.eval("document.getElementById('fchips').hidden"), True)
        self.assertEqual(len(self.rows()), all_n)

    def test_bad_dates_say_why_and_keep_the_previous_filter(self):
        b = self.open()
        b.click("#fmBtn")
        setv = lambda i, v: b.eval(f"(()=>{{ const e=document.getElementById('{i}'); e.value='{v}'; e.dispatchEvent(new Event('input',{{bubbles:true}})); e.dispatchEvent(new Event('change',{{bubbles:true}})); }})()")
        setv("fsFrom", "01-10-2026")
        n = len(self.rows())
        for bad in ("32-13-2026", "zzz", "99-99"):      # (the app reads "01-1" as 1 January, like every date box; it shows in the box and the chip)
            setv("fsFrom", bad)
            self.assertEqual(b.eval("document.getElementById('fsFromErr').textContent"), "Type a date as DD-MM-YYYY")
            self.assertEqual(b.eval("document.getElementById('fsFrom').getAttribute('aria-invalid')"), "true")
            self.assertEqual(b.eval("FF.from"), "2026-10-01")          # the previous filter stays
            self.assertEqual(len(self.rows()), n)
        setv("fsFrom", "01-10-2026")
        self.assertEqual(b.eval("document.getElementById('fsFromErr').textContent"), "")
        setv("fsTo", "01-09-2026")
        self.assertEqual(b.eval("document.getElementById('fsToErr').textContent"), "From is after To")
        self.assertEqual(b.eval("FF.to"), "")
        self.assertEqual(len(self.rows()), n)

    def test_empty_states_per_pill(self):
        b = self.open()
        b.pump(1)     # the page's own refresh on opening has landed
        b.eval("D.files_archived=[]; renderFiles()")
        self.view("archived")
        self.assertIn("Nothing has been archived.", b.eval("document.getElementById('filesTbl').innerText"))
        b.eval("FILES.splice(0,FILES.length); renderFiles()")
        self.view("latest")
        self.assertIn("No reports yet.", b.eval("document.getElementById('filesTbl').innerText"))
        self.view("week")
        self.assertIn("No meetings this week.", b.eval("document.getElementById('filesTbl').innerText"))
        self.view("all")
        self.assertIn("No files match.", b.eval("document.getElementById('filesTbl').innerText"))

    def test_combined_pill_folder_and_filter(self):
        b = self.open()
        self.view("week")
        week = self.rows()
        if not b.eval("!!document.querySelector('#fmenu.on')"):      # choosing a view leaves the menu open
            b.click("#fmBtn")
        b.click("#fmenu input[name=fsType][value=vtt]")
        narrowed = self.rows()
        self.assertTrue(set(narrowed) <= set(week))
        self.assertTrue(all(r.endswith(".vtt") for r in narrowed))
        b.key("Escape")
        b.click('#tree [data-p="All"]')               # the folder replaces the view; the filter stays
        self.assertEqual(self.pressed(), ["all"])
        self.assertEqual(b.eval("document.querySelector('#fmBtn .fcount').textContent"), "1")
        self.assertTrue(all(r.endswith(".vtt") for r in self.rows()))


if __name__ == "__main__":
    unittest.main()
