"""Dashboard pages (BL-87, BL-88, BL-89, BL-95, BL-91, BL-90 part 1).

Run: python3 dev/tests/test_pages.py   (the page tests need Google Chrome; they are skipped otherwise)

Everything is fictional and temporary. The data tests run in the default layout and in a temporary OneDrive-style projects
root (the BL-85 `locations` setting, resolved against a fake home folder); the page tests drive a real headless Chrome
against the real live server, as a person would.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
import unittest.mock
import urllib.error
import zipfile
from datetime import date, timedelta
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import CHROME, d, png, populate  # noqa: E402
from test_onedrive_projects import OneDriveCase, touch  # noqa: E402
from test_insight import chrome, log, py  # noqa: E402
from test_tracker import ABC, Vault, action  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from split_dashboard import readable_page  # noqa: E402

DEFAULT_REPORTS = f"{ABC}/reports"


# ===== BL-87: Files page, the real report folders =====


def theme_count():
    """How many named themes the dashboard has (its THEMES list), so theme checks follow new themes by themselves."""
    page = readable_page()     # BL-231: the source; the bundle reprints the code
    return len(re.findall(r'\{id:"', re.search(r"const THEMES=\[(.*?)\];", page, re.S).group(1)))

class FilesDataTests(unittest.TestCase):
    """files(): report folders by their real names, documents set aside, in the default layout."""

    @classmethod
    def setUpClass(cls):
        cls.v = v = Vault()
        populate(v)
        touch(v.root / DEFAULT_REPORTS / "2026-10-02 Weekly report.docx")
        touch(v.root / DEFAULT_REPORTS / "2026-10-09 Client report.docx")
        touch(v.root / DEFAULT_REPORTS / "Ad hoc risk register.xlsx")
        touch(v.root / DEFAULT_REPORTS / "Steerco" / "Steerco pack.pptx")
        touch(v.root / ABC / "documents" / "Plans" / "Plan.md")

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def py(self, code):
        src = f"import sys, json; sys.path.insert(0, {str(self.v.root / 'system/scripts')!r})\n{code}"
        r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, cwd=tempfile.gettempdir())
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def rows(self, show=False):
        o = self.py(f"""import build_dashboard as bd, paths
print(json.dumps([[f['p'], f['f'], f['n'], f['sub']] for f in bd.files({{'ABC': paths.project_dir('ABC')}}, {show}) if f['p'] == 'ABC']))""")
        return {tuple(r) for r in o}

    def test_reports_carry_their_folder_and_steerco_is_listed(self):
        got = self.rows()
        self.assertIn(("ABC", "reports", "2026-10-02 Weekly report.docx", "Weekly"), got)
        self.assertIn(("ABC", "reports", "2026-10-09 Client report.docx", "Weekly"), got)       # client reports are filed with the weekly ones
        self.assertIn(("ABC", "reports", "Ad hoc risk register.xlsx", "Adhoc"), got)             # ad hoc files in the shared reports folder
        self.assertIn(("ABC", "reports", "Steerco pack.pptx", "Steerco"), got)                   # reports/Steerco in the default layout
        self.assertEqual(sum(1 for r in got if r[3] == "Steerco"), 1)                            # never listed twice

    def test_documents_are_set_aside_by_default_and_come_back_with_the_setting(self):
        self.assertFalse([r for r in self.rows() if r[1] == "documents"])
        self.assertIn(("ABC", "documents", "Plan.md", "Plans"), self.rows(show=True))

    def test_the_scan_does_not_walk_documents_when_they_are_set_aside(self):
        o = self.py("""import build_dashboard as bd, paths
def boom(*a, **k): raise SystemExit('walked the documents')
paths.document_files = boom
files = bd.files({'ABC': paths.project_dir('ABC')})
print(json.dumps(len(files)))""")
        self.assertGreater(o, 0)

    def test_search_indexing_still_reads_documents(self):
        o = self.py("""import tracker
print(json.dumps(sorted(set(kind for _, kind, _ in tracker.index_files()))))""")
        self.assertIn("documents", o)
        self.assertIn("reports", o)

    def test_the_light_entry_point_scans_only_the_file_lists(self):
        o = self.py("""import build_dashboard as bd
def boom(*a, **k): raise SystemExit('built everything')
bd.collect = boom
v = bd.files_view()
print(json.dumps([sorted(v), len(v['files']), [f['f'] for f in v['files'] if f['f'] == 'documents'], bool(v['inbox'])]))""")
        self.assertEqual(o[0], ["at", "files", "inbox"])
        self.assertGreater(o[1], 0)
        self.assertEqual(o[2], [])
        self.assertTrue(o[3])

    def test_the_setting_and_the_folder_have_defaults(self):
        defaults = json.loads((Path(__file__).resolve().parents[2] / "system/templates/settings-defaults.json").read_text())
        self.assertIs(defaults["dashboard"]["files_show_documents"], False)
        self.assertEqual(defaults["locations"]["folders"]["steerco"], "04 Reporting/Steerco")


class FilesExternalLayoutTests(OneDriveCase):
    """The same, with the projects in a OneDrive-style root: the numbered template's Weekly, Adhoc and Steerco folders."""

    def setUp(self):
        super().setUp()
        touch(self.eng("ABC", "04 Reporting", "Weekly", "2026-10-02 Weekly report.docx"))
        touch(self.eng("ABC", "04 Reporting", "Weekly", "2026-10-09 Client report.docx"))
        touch(self.eng("ABC", "04 Reporting", "Adhoc", "Risk register.xlsx"))
        touch(self.eng("ABC", "04 Reporting", "Steerco", "SteerCo 8 October.pptx"))
        touch(self.eng("ABC", "04 Reporting", "Milestones", "Milestone plan.xlsx"))
        touch(self.eng("ABC", "04 Reporting", "Content", "chart.png"))
        touch(self.eng("ABC", "02 Meetings", "Agendas", "Agenda.docx"))
        touch(self.eng("ABC", "00 Admin", "Contract", "Statement of work.docx"))
        touch(self.eng("ABC", "zz Archive", "Old plan.docx"))
        touch(self.eng("ABC", "02 Meetings", "Minutes", "2026-10-01 Weekly sync.docx"))

    def files(self, show=False):
        o = self.py(f"""import build_dashboard as bd, paths
print(json.dumps([[f['p'], f['f'], f['n'], f['sub']] for f in bd.files({{'ABC': paths.project_dir('ABC')}}, {show}) if f['p'] == 'ABC']))""")
        return {tuple(r) for r in o}

    def test_real_report_folders_and_the_left_out_ones(self):
        got = self.files()
        self.assertEqual({r for r in got if r[1] == "reports"}, {
            ("ABC", "reports", "2026-10-02 Weekly report.docx", "Weekly"), ("ABC", "reports", "2026-10-09 Client report.docx", "Weekly"),
            ("ABC", "reports", "Risk register.xlsx", "Adhoc"), ("ABC", "reports", "SteerCo 8 October.pptx", "Steerco")})
        self.assertEqual({r[2] for r in got} & {"Milestone plan.xlsx", "chart.png", "Old plan.docx"}, set())   # left out
        self.assertIn(("ABC", "agendas", "Agenda.docx", ""), got)                                            # BL-135: Agendas are listed as their own kind
        self.assertIn(("ABC", "minutes", "2026-10-01 Weekly sync.docx", ""), got)

    def test_documents_are_set_aside_and_not_walked(self):
        self.assertFalse([r for r in self.files() if r[1] == "documents"])
        shown = self.files(show=True)
        self.assertIn(("ABC", "documents", "Statement of work.docx", "00 Admin › Contract"), shown)
        self.assertNotIn("SteerCo 8 October.pptx", {r[2] for r in shown if r[1] == "documents"})    # Steerco is a report folder, not a document
        o = self.py("""import build_dashboard as bd, paths
def boom(*a, **k): raise SystemExit('walked')
paths.document_files = boom
print(json.dumps(len(bd.files({'ABC': paths.project_dir('ABC')}))))""")
        self.assertGreater(o, 0)

    def test_steerco_is_listed_in_files_and_an_older_settings_file_still_works(self):
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data["locations"]["folders"].pop("steerco", None)          # settings made before BL-87 lack the key
        cfg.write_text(json.dumps(data))
        o = self.py("import paths; print(json.dumps([paths.folder_name('steerco'), str(paths.folder('ABC', 'steerco'))]))")
        self.assertEqual(o[0], "04 Reporting/Steerco")
        self.assertTrue(o[1].endswith("Example Programme/04 Reporting/Steerco"))
        self.assertIn("Steerco", {r[3] for r in self.files()})


# ===== the live page =====

def settle(b, js, timeout=10):
    b.wait(js, timeout)


class FilesLiveBase(LiveBrowserCase):
    """A live server and a headless Chrome; files are added to the vault from outside the dashboard."""

    @classmethod
    def load(cls, v):
        populate(v)
        for name in ("2026-10-02 Weekly report.docx", "2026-10-09 Client report.docx", "Ad hoc risk register.xlsx"):
            touch(v.root / DEFAULT_REPORTS / name)
        touch(v.root / DEFAULT_REPORTS / "Steerco" / "Steerco pack.pptx")
        touch(v.root / ABC / "documents" / "Plans" / "Plan.md")

    def rows(self):
        return self.b.eval("[...document.querySelectorAll('#filesTbl tbody tr[data-fp]')].map(r=>r.querySelector('a').textContent)")

    def open_files(self):
        self.b.eval("go('files')")
        self.b.wait("document.querySelector('#filesTbl tbody tr, #filesTbl .empty') && !document.getElementById('filesAt').textContent.startsWith('Checking')")
        self.b.wait("FBUSY===false")


class FilesLiveTests(FilesLiveBase):
    def test_opening_files_shows_the_real_folders_with_documents_set_aside(self):
        self.open_files()
        names = self.rows()
        self.assertIn("Steerco pack.pptx", names)
        self.assertIn("2026-10-02 Weekly report.docx", names)
        self.assertNotIn("Plan.md", names)                                   # documents are set aside
        loc = self.b.eval("[...document.querySelectorAll('#filesTbl tbody tr[data-fp]')].find(r=>r.textContent.includes('Steerco pack')).cells[1].textContent")
        self.assertEqual(loc, "Example Programme › reports › Steerco")                     # each report shows its folder

    def test_a_file_added_outside_the_dashboard_appears_on_opening_files(self):
        self.open_files()
        self.assertNotIn("2026-10-16 Weekly report.docx", self.rows())
        touch(self.v.root / DEFAULT_REPORTS / "2026-10-16 Weekly report.docx")
        self.b.eval("go('today'); go('files')")                             # looking again
        self.b.wait("[...document.querySelectorAll('#filesTbl a')].some(a=>a.textContent.startsWith('2026-10-16'))")
        self.assertIn("2026-10-16 Weekly report.docx", self.rows())
        self.assertEqual(self.b.eval("[...document.querySelectorAll('#filesTbl tr[data-fp]')].filter(r=>r.querySelector('.tag.new')).map(r=>r.querySelector('a').textContent)"),
                         ["2026-10-16 Weekly report.docx"])                 # tagged New
        self.assertIn("1 new", self.b.eval("document.getElementById('filesCount').textContent"))
        self.assertRegex(self.b.eval("document.getElementById('filesAt').textContent"), r"^Updated \d\d:\d\d\.")
        self.b.eval("go('today'); go('files')")                             # the next look clears the tags
        self.b.wait("FBUSY===false")
        self.assertEqual(self.b.eval("document.querySelectorAll('#filesTbl .tag.new').length"), 0)
        self.assertNotIn("new", self.b.eval("document.getElementById('filesCount').textContent"))

    def test_a_file_that_went_disappears(self):
        extra = touch(self.v.root / DEFAULT_REPORTS / "Gone soon.docx")
        self.open_files()
        self.assertIn("Gone soon.docx", self.rows())
        extra.unlink()
        self.b.click("#filesRefresh")
        self.b.wait("!document.querySelector('#filesTbl a[data-openfile$=\"Gone soon.docx\"]')")
        self.assertNotIn("Gone soon.docx", self.rows())

    def test_refresh_keeps_filters_selection_open_folders_and_scroll(self):
        for n in range(60):
            touch(self.v.root / DEFAULT_REPORTS / f"2026-09-{(n % 28) + 1:02d} Bulk {n:02d}.docx")
        self.open_files()
        b = self.b
        b.eval("document.getElementById('fsName').value='report'; document.getElementById('fsName').dispatchEvent(new Event('input',{bubbles:true}))")
        b.eval("FOPEN.add('ABC'); renderFiles()")
        b.click("#filesTbl tbody tr[data-fp] td:nth-child(2)")
        selected = b.eval("FSELFILE")
        self.assertTrue(selected)
        b.eval("FSEL={p:'ABC',f:'reports',sub:'Weekly',quick:'all'}; renderFiles()")
        b.eval("document.getElementById('v-files').scrollTop=120")
        scroll = b.eval("document.getElementById('v-files').scrollTop")
        touch(self.v.root / DEFAULT_REPORTS / "2026-10-20 Weekly report.docx")
        b.click("#filesRefresh")
        b.wait("[...document.querySelectorAll('#filesTbl a')].some(a=>a.textContent.startsWith('2026-10-20'))")
        self.assertEqual(b.eval("document.getElementById('fsName').value"), "report")           # the filter
        self.assertEqual(b.eval("FSELFILE"), selected)                                            # the selected file
        self.assertTrue(b.eval(f"!!document.querySelector('#filesTbl tr.sel[data-fp={json.dumps(selected)}]') || !document.querySelector('#filesTbl tr[data-fp={json.dumps(selected)}]')"))
        self.assertEqual(b.eval("[FSEL.p,FSEL.f,FSEL.sub]"), ["ABC", "reports", "Weekly"])
        self.assertTrue(b.eval("FOPEN.has('ABC')"))                                               # the open folders
        self.assertEqual(b.eval("document.getElementById('v-files').scrollTop"), scroll)          # the scroll position

    def test_the_light_route_returns_only_the_file_lists_and_needs_the_token(self):
        req = urllib.request.Request(self.base + "/api/files")
        with self.assertRaises(urllib.error.HTTPError) as err:
            urllib.request.urlopen(req, timeout=10)
        self.assertEqual(err.exception.code, 403)
        token = self.b.eval("D.token")
        req = urllib.request.Request(self.base + "/api/files", headers={"X-Creaite-Token": token})
        with urllib.request.urlopen(req, timeout=30) as r:
            body = json.loads(r.read())
        self.assertEqual(sorted(body), ["at", "files", "inbox", "ok"])                            # not the dashboard's whole data
        self.assertTrue(body["ok"])
        self.assertNotIn("documents", {f["f"] for f in body["files"]})

    def test_a_failed_scan_keeps_the_old_list_and_says_so(self):
        self.open_files()
        before = self.rows()
        self.b.eval("window.fetch=async()=>({ok:false,status:500,json:async()=>({ok:false,message:'disk unavailable'})})")
        self.b.click("#filesRefresh")
        self.b.wait("document.getElementById('filesAt').textContent.startsWith(\"Couldn't refresh\")")
        self.assertEqual(self.rows(), before)
        self.assertIn("disk unavailable", self.b.eval("document.getElementById('filesAt').textContent"))

    def test_a_slow_scan_shows_checking(self):
        self.open_files()
        self.b.eval("const f0=window.fetch; window.fetch=(...a)=>new Promise(r=>setTimeout(()=>r(f0(...a)),1700))")
        self.b.click("#filesRefresh")
        self.b.wait("document.getElementById('filesAt').textContent==='Checking…'", 5)
        self.b.wait("FBUSY===false", 10)
        self.assertRegex(self.b.eval("document.getElementById('filesAt').textContent"), r"^Updated ")

    def test_window_focus_refreshes_at_most_every_ten_seconds_and_only_on_these_pages(self):
        self.open_files()
        self.b.eval("window.__n=0; const f0=window.fetch; window.fetch=(...a)=>{ if(String(a[0]).includes('/api/files')) window.__n++; return f0(...a); }")
        self.b.eval("window.dispatchEvent(new Event('focus'))")
        self.b.eval("window.dispatchEvent(new Event('focus'))")
        self.assertEqual(self.b.eval("window.__n"), 0)                                            # a look a moment ago: too soon
        self.b.eval("FLAST=Date.now()-11000; window.dispatchEvent(new Event('focus'))")
        self.b.wait("window.__n===1")
        self.b.eval("go('work'); FLAST=Date.now()-11000; window.dispatchEvent(new Event('focus'))")
        time.sleep(0.4)
        self.assertEqual(self.b.eval("window.__n"), 1)                                            # not on Work

    def test_latest_reports_are_the_newest_in_each_folder_not_by_file_name(self):
        touch(self.v.root / DEFAULT_REPORTS / "Steerco" / "2026-10-08 SteerCo.pptx")
        touch(self.v.root / DEFAULT_REPORTS / "Steerco" / "Board pack (no date in the name).pptx")
        touch(self.v.root / DEFAULT_REPORTS / "Ad hoc milestone note.docx")
        self.open_files()
        self.b.click('#fquick [data-q="latest"]')
        names = self.rows()
        self.assertEqual(sum(1 for n in names if "Steerco" in n or "SteerCo" in n or "Board pack" in n), 1)   # one per folder
        self.assertIn("2026-10-09 Client report.docx", names)                                    # the newest weekly-folder file by date
        self.assertTrue(any("Ad hoc" in n for n in names))                                        # an ad hoc file counts without "Weekly report" in its name

    def test_the_tree_and_chips_show_the_report_folders(self):
        self.open_files()
        self.b.eval("FOPEN.add('ABC'); renderFiles()")
        tree = self.b.eval("[...document.querySelectorAll('#tree .l3')].map(b=>b.textContent.replace(/\\d+$/,''))")
        self.assertEqual(tree, ["Weekly", "Adhoc", "Steerco"])
        self.assertEqual(self.b.eval("[...document.querySelectorAll('#fquick [data-rep]')].map(b=>b.textContent)"), ["Weekly", "Adhoc", "Steerco"])
        self.assertNotIn("documents", self.b.eval("[...document.querySelectorAll('#tree .l2')].map(b=>b.textContent.replace(/\\d+$/,''))"))
        self.b.click('#fquick [data-rep="Steerco"]')
        self.assertEqual(self.rows(), ["Steerco pack.pptx"])
        self.b.click('#fquick [data-rep="Steerco"]')                                              # again: back to all files
        self.assertGreater(len(self.rows()), 1)

    def test_the_documents_switch_in_settings_brings_them_back(self):
        self.open_files()
        self.assertNotIn("Plan.md", self.rows())
        self.b.eval("go('settings','work')")
        self.b.wait("document.querySelector('[data-k=filesDocs]')")
        self.b.click("[data-k=filesDocs]")
        self.b.wait("S.filesDocs===true")
        saved = json.loads((self.v.root / "system/config/settings.json").read_text())
        self.assertIs(saved["dashboard"]["files_show_documents"], True)
        self.open_files()
        self.b.wait("FILES.some(f=>f.f==='documents')")
        self.assertIn("Plan.md", self.rows())
        self.assertIn("documents", self.b.eval("(FOPEN.add('ABC'),renderFiles(),[...document.querySelectorAll('#tree .l2')].map(b=>b.textContent.replace(/\\d+$/,'')))"))

    def test_intake_reloads_its_files_too(self):
        touch(self.v.root / "inbox" / "Late arrival.vtt", "WEBVTT")
        self.b.eval("go('inbox')")
        self.b.wait("document.body.textContent.includes('Late arrival.vtt')")
        self.assertIn("Late arrival.vtt", self.b.eval("document.getElementById('inboxTbl').textContent"))


class FilesFileVersionTests(unittest.TestCase):
    """A dashboard opened from disk (not served) keeps the old note, and Refresh says what it needs."""

    @unittest.skipUnless(CHROME.exists(), "Google Chrome not installed")
    def test_not_served(self):
        from test_insight import chrome
        v = Vault()
        try:
            populate(v)
            v.run(script="build_dashboard.py")
            out, errors = chrome(v, """VSTATE="ok"; go("files"); await new Promise(r=>setTimeout(r,100));
              const before=document.getElementById("filesAt").textContent; document.getElementById("filesRefresh").click(); await new Promise(r=>setTimeout(r,100));
              window.OUT={before, after:document.getElementById("filesAt").textContent, snack:document.getElementById("snackT").textContent, rows:document.querySelectorAll("#filesTbl tbody tr").length};""", name="files-file")
        finally:
            v.cleanup()
        self.assertEqual(errors, [])
        self.assertTrue(out["before"].startswith("File list as of the last build."))
        self.assertEqual(out["after"], out["before"])
        self.assertIn("live server", out["snack"])
        self.assertGreater(out["rows"], 0)


# ===== BL-88: Files search, a centred bar with an ask creaite button =====

THEMES = tuple(re.findall(r'\{id:"([^"]+)"', re.search(r"const THEMES=\[(.*?)\];", readable_page(), re.S).group(1)))   # every theme (BL-40)


def theme(b, palette, mode):
    b.eval(f"S.palette={json.dumps(palette)}; S.theme={json.dumps(mode)}; applyTheme()")


CONTRAST_JS = """(()=>{ const lum=c=>{ const [r,g,b]=c.match(/[\\d.]+/g).slice(0,3).map(Number).map(v=>{ v/=255; return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4); }); return 0.2126*r+0.7152*g+0.0722*b; };
  window.__ratio=(a,b)=>{ const x=lum(a), y=lum(b); return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05); };
  window.__bgOf=el=>{ for(let e=el;e;e=e.parentElement){ const c=getComputedStyle(e).backgroundColor; if(!/rgba\\(0, 0, 0, 0\\)|transparent/.test(c)) return c; } return "rgb(255,255,255)"; }; })()"""


class SearchBarTests(LiveBrowserCase):
    shared_server = True

    @classmethod
    def load(cls, v):
        populate(v)

    def setUp(self):
        super().setUp()
        self.b.eval("go('files')")
        self.b.wait("document.getElementById('vsInput')")

    def box(self, sel):
        return self.b.eval(f"(()=>{{ const r=document.querySelector({json.dumps(sel)}).getBoundingClientRect(); return [r.left,r.top,r.width,r.height,r.right,r.bottom]; }})()")

    def type_in(self, text):
        self.b.eval(f"(()=>{{ const i=document.getElementById('vsInput'); i.value={json.dumps(text)}; i.dispatchEvent(new Event('input',{{bubbles:true}})); }})()")

    def test_the_bar_is_centred_about_half_the_page_with_the_button_beside_it(self):
        for width in (1400, 1700, 1100):
            self.b.resize(width, 900)
            self.b.eval("go('files')")
            page = self.box("#vsearch")[2]
            bar, col, btn = self.box("#vsInput"), self.box(".vscol"), self.box("#vsAskBtn")
            self.assertAlmostEqual(bar[2], min(760, max(420, page * 0.5)), delta=3, msg=width)       # about 50%, 420 to 760px
            self.assertAlmostEqual(col[2], page * 0.8, delta=3, msg=width)                           # the column is 80%
            self.assertAlmostEqual(btn[3], 40, delta=1)                                                # the same height as the bar
            self.assertAlmostEqual(bar[3], 40, delta=1)
            self.assertAlmostEqual(btn[1], bar[1], delta=1)                                            # on the same line
            self.assertLessEqual(btn[0] - bar[4], 14)                                                  # immediately to its right
            self.assertGreaterEqual(btn[0] - bar[4], 0)
            self.assertAlmostEqual(bar[0] - col[0], col[4] - btn[4], delta=3, msg=width)               # bar and button centred in the column
            tree = self.box("#v-files .files")
            self.assertAlmostEqual(tree[2], page, delta=2)                                            # the tree and table stay full width

    def test_the_placeholder_and_the_hint_line(self):
        self.assertEqual(self.b.eval("document.getElementById('vsInput').placeholder"), "Search the vault")
        hint = self.b.eval("document.getElementById('vsHint').textContent")
        self.assertIn("risks ABC last month", hint)
        self.assertIn("what did Sara say about UAT?", hint)
        h, bar = self.box("#vsHint"), self.box("#vsInput")
        self.assertGreater(h[1], bar[5] - 1)                                                          # under the bar
        self.assertEqual(self.b.eval("getComputedStyle(document.getElementById('vsHint')).textAlign"), "center")
        self.type_in("data")
        self.assertFalse(self.b.eval("!!document.getElementById('vsHint').offsetParent"))             # hidden once there is text
        self.type_in("")
        self.b.wait("!!document.getElementById('vsHint').offsetParent")

    def test_no_ask_row_in_the_results(self):
        self.type_in("why did go-live move?")
        self.b.wait("!document.getElementById('vsResults').hidden")
        self.assertEqual(self.b.eval("document.querySelectorAll('#vsResults [data-vsask], .vsask').length"), 0)
        self.assertNotIn("Ask Claude", self.b.eval("document.getElementById('vsearch').textContent"))

    def test_the_buttons_states_and_enter(self):
        b = self.b
        state = lambda: b.eval("[document.getElementById('vsAskBtn').dataset.state, document.getElementById('vsAskBtn').getAttribute('aria-disabled'), getComputedStyle(document.querySelector('#vsAskBtn .askret')).display]")
        self.assertEqual(state(), ["idle", "true", "none"])                                           # no text: dimmed
        self.type_in("data access")
        self.assertEqual(state(), ["ready", "false", "none"])                                         # text, not a question: available
        self.type_in("why did go-live move?")
        self.assertEqual(state(), ["question", "false", "block"])                                  # a question: highlighted, with ↵
        self.assertEqual(b.eval("document.getElementById('vsAskBtn').title"), "ask creaite: an answer with a link to the source for every point.")
        self.assertEqual(b.eval("document.getElementById('vsAskBtn').textContent.replace(/\\s+/g,' ').trim()"), "ask creaite↵")
        self.assertEqual(b.eval("getComputedStyle(document.getElementById('vsAskBtn')).borderRadius"), "999px")   # a pill
        self.assertTrue(b.eval("document.querySelector('#vsAskBtn svg.spark path').getAttribute('d').startsWith('M366 214')"))   # the app icon's spark
        # a stand-in for the answer's stream: one that never ends until it is aborted
        b.eval("""window.__asked=0; const f0=window.fetch; window.fetch=async(u,o)=>{ if(u!=="/api/search/ask") return f0(u,o); window.__asked++;
          const stream=new ReadableStream({start(c){ const enc=new TextEncoder(); c.enqueue(enc.encode("data: "+JSON.stringify({type:"sources",question:JSON.parse(o.body).q,sources:[]})+"\\n\\n"));
            c.enqueue(enc.encode("data: "+JSON.stringify({type:"text",text:"Looking."})+"\\n\\n")); o.signal.addEventListener("abort",()=>c.error(new DOMException("aborted","AbortError"))); }});
          return new Response(stream,{status:200,headers:{"Content-Type":"text/event-stream"}}); }""")
        b.key("Enter")                                                                                 # Enter on a question asks creaite
        b.eval("document.getElementById('vsInput').focus()")
        b.key("Enter")
        b.wait("window.__asked===1")
        b.wait("document.getElementById('vsAskBtn').dataset.state==='answering'")
        self.assertEqual(b.eval("document.querySelector('#vsAskBtn .asklab').textContent"), "Answering…")
        self.assertFalse(b.eval("document.getElementById('vsAskStop').hidden"))
        b.click("#vsAskBtn")                                                                           # one answer at a time: the button does nothing now
        time.sleep(0.3)
        self.assertEqual(b.eval("window.__asked"), 1)
        b.click("#vsAskStop")
        b.wait("ASKQ.done===true")
        self.assertEqual(b.eval("document.getElementById('vsAskBtn').dataset.state"), "question")
        self.assertTrue(b.eval("document.getElementById('vsAskStop').hidden"))
        self.assertIn("Stopped.", b.eval("document.getElementById('vsAnswer').textContent"))
        b.click("#vsAskBtn")                                                                           # clicking asks too
        b.wait("window.__asked===2")
        b.click("#vsAskStop")
        b.wait("ASKQ.done===true")

    def test_enter_on_other_text_searches_at_once(self):
        b = self.b
        b.eval("document.getElementById('vsInput').focus()")
        b.eval("document.getElementById('vsInput').value='data access'; window.__runs=0; const r0=runSearch; runSearch=function(){ window.__runs++; return r0(); }")
        b.key("Enter")
        b.wait("window.__runs>=1", 1)

    def test_without_the_live_server_it_says_so(self):
        b = self.b
        self.type_in("data access")
        b.eval("LIVE=false")
        b.click("#vsAskBtn")
        b.wait("document.getElementById('vsNote').textContent.includes('Live server needed')")
        b.eval("LIVE=true")

    def test_narrow_windows_stack_the_button_under_the_bar(self):
        b = self.b
        b.resize(700, 900)
        b.eval("go('files')")
        page = self.box("#vsearch")[2]
        bar, btn, col = self.box("#vsInput"), self.box("#vsAskBtn"), self.box(".vscol")
        self.assertAlmostEqual(col[2], page, delta=2)                                                  # the column is the full width
        self.assertAlmostEqual(bar[2], page, delta=2)                                                  # the bar takes it all
        self.assertGreater(btn[1], bar[5] - 1)                                                         # the button is on its own line below
        self.assertAlmostEqual(btn[4], bar[4], delta=3)                                                # right-aligned

    def test_contrast_edge_and_motion_in_every_theme_and_mode(self):
        b = self.b
        b.eval(CONTRAST_JS)
        res = {}
        for pal in THEMES:
            for mode in ("Light", "Dark"):
                theme(b, pal, mode)
                for text in ("data", "why did go-live move?"):
                    self.type_in(text)
                    r = b.eval("""(()=>{ const btn=document.getElementById('vsAskBtn'), cs=getComputedStyle(btn), page=getComputedStyle(document.getElementById('v-files')).backgroundColor||'rgb(255,255,255)';
                      return {label:__ratio(cs.color,cs.backgroundColor), edge:__ratio(cs.borderTopColor,__bgOf(document.getElementById('vsearch'))), spark:getComputedStyle(btn.querySelector('.spark')).color, fill:cs.backgroundColor}; })()""")
                    res[f"{pal}|{mode}|{text[:4]}"] = r
                self.type_in("")                                                                          # dimmed: still a button, label readable
                r = b.eval("""(()=>{ const btn=document.getElementById('vsAskBtn'), cs=getComputedStyle(btn); return {label:__ratio(cs.color,cs.backgroundColor), edge:__ratio(cs.borderTopColor,__bgOf(document.getElementById('vsearch'))), spark:getComputedStyle(btn.querySelector('.spark')).color, fill:cs.backgroundColor}; })()""")
                res[f"{pal}|{mode}|idle"] = r
        self.assertEqual(len(res), len(THEMES) * 2 * 3)
        self.assertEqual({k: round(v["label"], 2) for k, v in res.items() if v["label"] < 4.5}, {})          # label on its fill: 4.5:1
        self.assertEqual({k: round(v["edge"], 2) for k, v in res.items() if v["edge"] < 3}, {})              # the button's edge on the page: 3:1
        # the fill is the theme's accent
        self.assertEqual(res["creaite|Light|data"]["fill"], "rgb(11, 110, 127)")
        self.assertEqual(res["Brightwater|Light|data"]["fill"], "rgb(30, 31, 30)")                          # Charcoal, with a Signal Green spark
        self.assertEqual(res["Brightwater|Light|data"]["spark"], "rgb(145, 255, 1)")
        self.assertEqual(res["Brightwater|Dark|data"]["fill"], "rgb(145, 255, 1)")                          # Signal Green with Charcoal text and spark
        self.assertEqual(res["Brightwater|Dark|data"]["spark"], "rgb(30, 31, 30)")
        self.assertTrue(b.eval("[...document.styleSheets].flatMap(s=>[...s.cssRules]).some(r=>r.selectorText&&r.selectorText.includes('.askbtn:focus-visible'))"))   # a clear focus ring
        theme(b, "creaite", "Light")

    def test_the_spark_moves_and_stops_under_reduced_motion(self):
        b = self.b
        b.call("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "no-preference"}])   # BL-136: tests start reduced
        self.type_in("why did go-live move?")
        b.eval("ASKQ={run:'x',q:'q',said:[],sources:[],steps:0,done:false}; vsAnswerDraw()")
        anim = lambda: b.eval("getComputedStyle(document.querySelector('#vsAskBtn .spark')).animationName")
        self.assertEqual(anim(), "askpulse")                                                           # pulses while answering
        b.eval("ASKQ={run:null}; vsAnswerDraw()")
        self.assertEqual(anim(), "none")
        b.call("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "reduce"}])
        b.eval("ASKQ={run:'x',q:'q',said:[],sources:[],steps:0,done:false}; vsAnswerDraw()")
        self.assertEqual(anim(), "none")                                                               # all motion stops
        self.assertEqual(b.eval("getComputedStyle(document.getElementById('vsAskBtn')).transitionDuration"), "0s")
        b.eval("ASKQ={run:null}; vsAnswerDraw()")
        b.call("Emulation.setEmulatedMedia", features=[{"name": "prefers-reduced-motion", "value": "no-preference"}])
        self.assertNotEqual(b.eval("getComputedStyle(document.querySelector('#vsAskBtn .spark')).transitionDuration"), "0s")


# ===== BL-89: Current state in two resizable panes =====

MARKER = "<!-- creaite: second pane -->"


class CurrentStateDataTests(unittest.TestCase):
    """The marker through docx_tools, report.py (the weekly Word report, approval, Generate) and the dashboard's data."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
        import docx_tools
        import report
        cls.dt, cls.rp = docx_tools, report

    def test_split_join_and_one_message(self):
        dt = self.dt
        self.assertEqual(dt.split_panes("Only left."), ("Only left.", ""))                       # no marker: just the left pane
        self.assertEqual(dt.split_panes(f"Left.\n\n{MARKER}\n\nRight."), ("Left.", "Right."))
        self.assertEqual(dt.split_panes(f"Left.\n\n{MARKER}\n\nRight.\n\n{MARKER}\n\nMore"), ("Left.", "Right.\n\nMore"))   # one marker counts
        self.assertEqual(dt.join_panes("Left.", ""), "Left.")                                    # an empty right pane leaves no marker
        self.assertEqual(dt.join_panes("Left.", "Right."), f"Left.\n\n{MARKER}\n\nRight.")
        self.assertEqual(dt.join_panes("", "Right."), f"{MARKER}\n\nRight.")
        self.assertEqual(dt.one_message(f"Left.\n\n{MARKER}\n\nRight."), "Left.\n\nRight.")        # marker removed, nothing added
        self.assertEqual(dt.md_normalise(f"Left.\n\n{MARKER}\n\nRight."), f"Left.\n\n{MARKER}\n\nRight.")
        self.assertEqual(dt.md_normalise(f"Left.\n\n{MARKER}"), "Left.")                       # nothing after it: a one-pane text
        self.assertEqual(dt.md_normalise("Left only\n\n- a\n- b"), "Left only\n\n- a\n- b")  # unchanged for existing texts
        kinds = [k for k, _ in dt.md_blocks(f"Left.\n{MARKER}\nRight.")]
        self.assertEqual(kinds, ["p", "p"])                                                     # readers see two paragraphs, no marker

    def test_replace_current_keeps_the_right_pane_unless_the_new_text_carries_the_marker(self):
        rc = self.rp.replace_current
        md = f"# X\n\n## Current state\n\n_guide_\n\nOld left.\n\n{MARKER}\n\nMy notes.\n\n## Next\n"
        out = rc(md, "New left.")
        self.assertIn(f"New left.\n\n{MARKER}\n\nMy notes.\n", out)                           # the right pane is Alan's own
        self.assertIn("_guide_", out)
        self.assertIn(f"Left two.\n\n{MARKER}\n\nChanged notes.", rc(md, f"Left two.\n\n{MARKER}\n\nChanged notes."))   # a text with the marker stands
        self.assertEqual(rc(md, f"Only left.\n\n{MARKER}\n\nMy notes.").count(MARKER), 1)
        flat = rc(md, "New left.\n\nMy notes.")                                                # came back from Word as one piece
        self.assertIn(f"New left.\n\n{MARKER}\n\nMy notes.\n", flat)                         # the marker goes back where it was
        self.assertEqual(flat.count("My notes."), 1)
        plain = "# X\n\n## Current state\n\nOld.\n\n## Next\n"
        self.assertEqual(rc(plain, "New."), "# X\n\n## Current state\n\nNew.\n\n## Next\n")      # a one-pane text is as before

    def test_the_generate_context_separates_the_panes(self):
        v = Vault()
        try:
            populate(v)
            mem = next((v.root / "projects").glob("ABC */CLAUDE.md"))
            text = mem.read_text()
            mem.write_text(text.replace("UAT preparation continues on masked data.", f"UAT preparation continues on masked data.\n\n{MARKER}\n\nMy own note about the sponsor."))
            out = v.run("current-context", "ABC", script="report.py").stdout
            prompt = (v.root / "system/templates/current-state-prompt.md").read_text()
            one = out.split("## Current state now: the left pane")[1].split("## Current state now: the right pane")
            self.assertEqual(len(one), 2)
            self.assertIn("UAT preparation continues", one[0])
            self.assertNotIn("My own note", one[0])
            self.assertIn("My own note about the sponsor.", one[1].split("\n## ")[0])
            self.assertIn("right pane", out)
            self.assertIn("never write the pane marker", prompt)                                  # Generate drafts the left pane only
            plain = v.run("current-context", "ABC", script="report.py").stdout
            mem.write_text(text)
            self.assertNotIn("the right pane", v.run("current-context", "ABC", script="report.py").stdout)   # one pane: no second section
            self.assertIn("the left pane", plain)
        finally:
            v.cleanup()


class CurrentStateReportTests(unittest.TestCase):
    """The weekly Word report reads two panes as one piece, keeping the marker and the right pane in CLAUDE.md."""

    def setUp(self):
        import test_reports as tr
        self.tr = tr
        self.v = tr.ReportVault()
        tr.populate(self.v)
        (self.v.root / ABC / "images" / "second.png").write_bytes(png(200, 100, (160, 60, 20)))
        self.mem = self.v.root / ABC / "CLAUDE.md"
        self.left = "Build is two weeks behind.\n\n![Delivery plan](images/plan.png)\n\nMore on the left."
        self.right = "Sponsor wants a call.\n\n![Second view](images/second.png)\n\nRight pane ends."
        text = self.mem.read_text()
        head = text[:text.index("## Current state")]
        self.mem.write_text(head + f"## Current state\n\n_Rewritten weekly._\n\n{self.left}\n\n{MARKER}\n\n{self.right}\n")

    def tearDown(self):
        self.v.cleanup()

    def spec(self, **extra):
        f = self.v.root / "system/staging/drafts/weekly.json"
        f.write_text(json.dumps({"code": "ABC", "health": "At risk", "health_reason": "UAT start slipped 14 days",
                                 "summary": ["UAT start has slipped two weeks."], "key_changes": "UAT start moved",
                                 "progress": ["Plan revised"], "next_week": ["Escalate data access"], "help_needed": ["Sponsor support"], **extra}))
        return str(f)

    def staged(self):
        prop = next((self.v.root / "system/staging").glob("proposed-*-weekly-ABC.json"))
        data = json.loads(prop.read_text())
        draft = self.v.root / data["report"]["draft"]
        with zipfile.ZipFile(draft) as z:
            xml = z.read("word/document.xml").decode()
        memory = next(o for o in data["report"]["file_ops"] if o["op"] == "write")["content"]
        return data, draft, xml, memory

    def test_two_panes_are_one_piece_in_word_and_unchanged_in_claude_md(self):
        # no current_state in the spec: the report uses what is there, both panes
        self.v.at("weekly-stage", self.spec(), script="report.py")
        data, draft, xml, memory = self.staged()
        paras = re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)
        at = lambda pred: next(i for i, p in enumerate(paras) if pred(p))  # noqa: E731
        order = [at(lambda p: ">Build is two weeks behind.<" in p), at(lambda p: ">Delivery plan<" in p), at(lambda p: ">More on the left.<" in p),
                 at(lambda p: ">Sponsor wants a call.<" in p), at(lambda p: ">Second view<" in p), at(lambda p: ">Right pane ends.<" in p)]
        self.assertEqual(order, sorted(order))                                                  # left, then right, as one message
        self.assertEqual(order[3] - order[2], 1)                                                # nothing added between them
        self.assertNotIn("second pane", xml)                                                    # the marker is not in the report
        self.assertEqual(xml.count('r:embed="rIdCreaiteImg'), 2)                                # an image from each pane
        self.assertIn(f"More on the left.\n\n{MARKER}\n\nSponsor wants a call.", memory)       # CLAUDE.md keeps the marker and the right pane
        self.assertEqual(memory.count(MARKER), 1)
        listed = json.loads(self.v.run("list", "--json", script="review.py").stdout)
        n = next(r["n"] for r in listed if r["ref"] == "report")
        out = self.v.run("approve", str(n), script="review.py").stdout                         # an unedited draft raises no difference
        self.assertNotIn("Current state: draft says", out)
        self.assertIn("Approved 1.", out)
        approved = self.mem.read_text()
        self.assertIn(f"More on the left.\n\n{MARKER}\n\nSponsor wants a call.", approved)

    def test_a_new_left_pane_without_the_marker_keeps_the_right_pane(self):
        self.v.at("weekly-stage", self.spec(current_state="A fresh left pane."), script="report.py")
        data, draft, xml, memory = self.staged()
        self.assertIn(f"A fresh left pane.\n\n{MARKER}\n\nSponsor wants a call.", memory)
        text = self.v.run("text", str(draft), script="docx_tools.py").stdout
        self.assertLess(text.index("A fresh left pane."), text.index("Sponsor wants a call."))
        self.assertNotIn("second pane", text)

    def test_the_dashboards_data_has_both_panes_once(self):
        self.v.run(script="build_dashboard.py")
        html = (self.v.root / "dashboard.html").read_text(encoding="utf-8")
        data = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))
        cur = next(p for p in data["projects"] if p["code"] == "ABC")["current"]
        self.assertEqual(cur.count(MARKER), 1)
        self.assertTrue(cur.index("More on the left.") < cur.index(MARKER) < cur.index("Sponsor wants a call."))


class PanesLive(LiveBrowserCase):
    """A fresh vault, live server and browser for each test; real clicks, real drags, real keys."""

    width, height = 1280, 900

    def setUp(self):
        super().setUp()
        self.mem = next((self.v.root / "projects").glob("ABC */CLAUDE.md"))

    def md(self):
        return re.search(r"## Current state\n(.*?)(?=\n## |\Z)", self.mem.read_text(), re.S).group(1)

    def two_panes(self, left="Left pane text.", right="Right pane text.\n\n![Second view](images/second.png)"):
        (self.mem.parent / "images" / "second.png").write_bytes(png(200, 100, (160, 60, 20)))
        text = self.mem.read_text()
        head = text[:text.index("## Current state")]
        self.mem.write_text(head + f"## Current state\n\n_Rewritten weekly._\n\n{left}\n\n{MARKER}\n\n{right}\n")
        self.v.run(script="build_dashboard.py")
        self.b.reload()
        self.b.wait("typeof go==='function' && LIVE")
        self.open_card()

    def open_card(self):
        self.b.eval("go('cockpit','ABC')")
        self.b.wait("document.querySelector('#v-cockpit .curcard')")

    def edit(self):
        self.b.click("#v-cockpit .curcard [data-edcur]")
        self.b.wait("document.getElementById('curEd2')")

    def save(self):
        self.b.eval("document.getElementById('snackT').textContent=''")
        self.b.click('[data-cure="save"]')
        self.b.wait("/saved and applied|Not saved/i.test(document.getElementById('snackT').textContent)", 15)
        return self.b.eval("document.getElementById('snackT').textContent")

    def widths(self):
        return self.b.eval("""(()=>{ const box=document.querySelector('.curpanes').getBoundingClientRect(), a=document.querySelector('.curpane[data-pane="1"]').getBoundingClientRect(),
          c=document.querySelector('.curpane[data-pane="2"]').getBoundingClientRect(), d=document.querySelector('.curdiv').getBoundingClientRect();
          return {box:box.width, left:a.width, right:c.width, div:d.width, leftPct:(a.width+6)/box.width*100, divX:d.left+d.width/2}; })()""")

    def drag_divider(self, dx):
        b = self.b
        pos = b.box(".curdiv")
        y = pos["y"]
        for kind, x in (("mouseMoved", pos["x"]), ("mousePressed", pos["x"]), ("mouseMoved", pos["x"] + dx / 2), ("mouseMoved", pos["x"] + dx), ("mouseReleased", pos["x"] + dx)):
            b.call("Input.dispatchMouseEvent", type=kind, x=x, y=y, button="left", clickCount=1)
        b.pump(0.1)

    def test_a_text_without_a_marker_is_the_left_pane_and_notes_can_be_added(self):
        b = self.b
        before = self.mem.read_text()
        self.open_card()
        self.assertEqual(b.eval("document.querySelectorAll('.curpanes.read.solo').length"), 1)         # BL-117: the same frame, the right column empty
        self.assertEqual(b.eval("document.querySelectorAll('[data-edcur2], .curnotes').length"), 0)    # BL-116: no Add notes link
        self.assertNotIn("Add notes", b.eval("document.getElementById('curText').textContent"))
        for sel in (".curdiv", ".curcollapse", ".curdot"):                                              # no divider, fold button or dot
            self.assertEqual(b.eval(f"document.querySelectorAll('.curtext {sel}').length"), 0, sel)
        b.click("#v-cockpit .curcard [data-edcur]")                                                     # the pencil opens both panes
        b.wait("document.getElementById('curEd2')")
        self.assertEqual(b.eval("document.querySelectorAll('.curpanes.edit .curpane').length"), 2)
        b.click("#curEd2")
        self.assertEqual(b.eval("document.getElementById('curEd2').dataset.ph"), "Write here…")        # faint placeholder, no caption
        self.assertTrue(b.eval("document.getElementById('curEd2').classList.contains('blank')"))
        self.assertEqual(b.eval("document.querySelectorAll('.curpane h2, .curpane h3, .curpane legend, .curpane label').length"), 0)   # the panes have no titles
        b.type("My own note.")
        self.assertFalse(b.eval("document.getElementById('curEd2').classList.contains('blank')"))
        self.assertIn("saved and applied", self.save())
        md = self.md()
        self.assertIn(f"\n\n{MARKER}\n\nMy own note.", md)
        self.assertEqual(md.count(MARKER), 1)
        self.assertEqual(b.eval("document.querySelectorAll('.curpanes.read').length"), 1)              # now shown in two panes
        # one apply, one Activity line, one Undo
        self.assertEqual(b.eval("ACT.filter(a=>/^Example Programme — current state updated/.test(a.what)).length"), 1)
        b.eval("document.querySelector('#v-activity') && go('activity')")
        b.wait("document.querySelector('#actTbl [data-undoapply], #actTbl [data-undoact]')")
        b.click("#actTbl [data-undoapply], #actTbl [data-undoact]")
        b.wait("!document.querySelector('.curpanes') || true")
        time.sleep(1.5)
        self.assertEqual(self.mem.read_text(), before)                                                  # one Undo puts it all back

    def left_width(self):
        return self.b.eval("document.querySelector('.curpane[data-pane=\"1\"]').getBoundingClientRect().width")

    def test_the_text_keeps_its_width_with_nothing_on_the_right(self):
        """BL-117: the read view always draws the two-column frame, so the left text sits at its saved share either way."""
        b = self.b
        self.open_card()
        solo = self.left_width()
        box = b.eval("document.querySelector('.curpanes').getBoundingClientRect().width")
        self.assertAlmostEqual((solo + 6) / box * 100, 62, delta=2)                                      # the default share, not the full card
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('.curpane[data-pane=\"2\"]')).display"), "block")
        self.two_panes()
        self.assertAlmostEqual(self.left_width(), solo, delta=1)                                         # adding text on the right changes nothing on the left
        b.eval("localStorage.setItem('creaite-cur-split','40')")                                         # a dragged split is kept by both
        b.eval("renderCockpit('ABC')")
        two = self.left_width()
        self.assertAlmostEqual(self.widths()["leftPct"], 40, delta=1.5)
        self.mem.write_text(self.mem.read_text().replace(f"\n\n{MARKER}\n\nRight pane text.\n\n![Second view](images/second.png)", ""))
        self.v.run(script="build_dashboard.py")
        b.reload()
        b.wait("typeof go==='function' && LIVE")
        self.open_card()
        self.assertEqual(b.eval("document.querySelectorAll('.curpanes.solo').length"), 1)
        self.assertAlmostEqual(self.left_width(), two, delta=1)

    def test_a_solo_read_view_is_full_width_in_a_narrow_window(self):
        b = self.b
        self.open_card()
        b.resize(700, 900)
        b.eval("renderCockpit('ABC')")
        left = b.eval("document.querySelector('.curpane[data-pane=\"1\"]').getBoundingClientRect().toJSON()")
        box = b.eval("document.querySelector('.curpanes').getBoundingClientRect().width")
        self.assertAlmostEqual(left["width"], box, delta=2)                                              # stacked: the text is the full width
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('.curpane[data-pane=\"2\"]')).display"), "none")

    def test_two_panes_show_side_by_side_at_about_62_per_cent(self):
        self.two_panes()
        w = self.widths()
        self.assertAlmostEqual(w["leftPct"], 62, delta=2)
        self.assertGreater(w["right"], 150)
        figs = self.b.eval("[document.querySelectorAll('.curpane[data-pane=\"1\"] figure').length, document.querySelectorAll('.curpane[data-pane=\"2\"] figure').length]")
        self.assertEqual(figs, [0, 1])                                                                   # an image stays in the pane it is in
        self.assertNotIn("second pane", self.b.eval("document.getElementById('curText').textContent"))   # the marker never shows
        self.assertEqual(self.b.eval("document.querySelector('.curdiv').getAttribute('role')"), "separator")
        self.assertEqual(self.b.eval("document.querySelector('.curdiv').getAttribute('aria-valuenow')"), "62")

    def test_the_divider_drags_remembers_resets_and_keeps_both_panes_in_reach(self):
        b = self.b
        self.two_panes()
        start = self.widths()
        self.drag_divider(-200)
        w = self.widths()
        self.assertLess(w["leftPct"], start["leftPct"] - 10)                                            # dragging left gives the right pane room
        self.assertEqual(b.eval("+localStorage.getItem('creaite-cur-split')") // 1, round(w["leftPct"]) if False else b.eval("Math.floor(+localStorage.getItem('creaite-cur-split'))"))
        saved = float(b.eval("localStorage.getItem('creaite-cur-split')"))
        self.assertAlmostEqual(saved, w["leftPct"], delta=1.5)                                          # remembered
        b.reload()
        b.wait("typeof go==='function' && LIVE")
        self.open_card()
        self.assertAlmostEqual(self.widths()["leftPct"], saved, delta=1.5)                              # and after a reload
        b.eval("go('projects')"); self.open_card()
        self.assertAlmostEqual(self.widths()["leftPct"], saved, delta=1.5)                              # the same for every project (a browser setting)
        self.drag_divider(-2000)
        self.assertGreaterEqual(self.widths()["leftPct"], 24.5)                                          # never less than about 25%
        self.drag_divider(4000)
        self.assertLessEqual(self.widths()["leftPct"], 75.5)
        self.assertGreaterEqual(100 - self.widths()["leftPct"], 24)
        pos = b.box(".curdiv")
        for _ in range(2):
            b.call("Input.dispatchMouseEvent", type="mousePressed", x=pos["x"], y=pos["y"] + 30, button="left", clickCount=2)
            b.call("Input.dispatchMouseEvent", type="mouseReleased", x=pos["x"], y=pos["y"] + 30, button="left", clickCount=2)
        b.eval("document.querySelector('.curdiv').dispatchEvent(new MouseEvent('dblclick',{bubbles:true}))")
        self.assertAlmostEqual(self.widths()["leftPct"], 62, delta=2)                                   # double-click resets
        b.eval("document.querySelector('.curdiv').focus()")                                              # the keyboard
        b.key("ArrowLeft")
        self.assertEqual(b.eval("document.querySelector('.curdiv').getAttribute('aria-valuenow')"), "60")
        b.key("Home")
        self.assertEqual(b.eval("document.querySelector('.curdiv').getAttribute('aria-valuenow')"), "25")
        b.key("End")
        self.assertEqual(b.eval("document.querySelector('.curdiv').getAttribute('aria-valuenow')"), "75")
        b.key("ArrowRight")
        self.assertEqual(b.eval("document.querySelector('.curdiv').getAttribute('aria-valuenow')"), "75")   # clamped
        self.assertEqual(b.errors, [])

    def test_the_right_pane_folds_into_a_strip_that_shows_it_holds_text(self):
        b = self.b
        self.two_panes()
        b.click(".curcollapse")
        self.assertTrue(b.eval("document.querySelector('.curpanes').classList.contains('collapsed')"))
        w = self.widths()
        self.assertLess(w["right"], 50)                                                                 # a thin strip
        self.assertTrue(b.eval("getComputedStyle(document.querySelector('.curdot')).display!=='none'"))   # it holds text: the strip says so
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('.curpane[data-pane=\"2\"] .curin')).display"), "none")
        self.assertEqual(b.eval("document.querySelector('.curcollapse').getAttribute('aria-expanded')"), "false")
        self.assertIn("Right pane text.", b.eval("document.querySelector('.curpane[data-pane=\"2\"]').textContent"))   # hidden, still there
        b.reload()
        b.wait("typeof go==='function' && LIVE")
        self.open_card()
        self.assertTrue(b.eval("document.querySelector('.curpanes').classList.contains('collapsed')"))   # remembered
        b.click(".curcollapse")
        self.assertFalse(b.eval("document.querySelector('.curpanes').classList.contains('collapsed')"))
        self.assertGreater(self.widths()["right"], 150)

    def test_editing_both_panes_with_one_toolbar_and_one_save(self):
        b = self.b
        self.two_panes("Left start.", "Right start.")
        self.edit()
        self.assertEqual(b.eval("document.querySelectorAll('.rtebar').length"), 1)                      # one toolbar
        self.assertEqual(b.eval("document.querySelectorAll('[data-cure=\"save\"]').length"), 1)
        self.assertEqual(b.eval("document.querySelectorAll('[data-cure=\"cancel\"]').length"), 1)
        self.assertTrue(b.eval("document.activeElement.id==='curEd'"))
        b.click("#curEd p")
        b.key("End")
        b.type(" Left added.")
        b.click("#curEd2 p")                                                                             # the toolbar acts on the pane the cursor is in
        b.key("End")
        b.eval("document.getSelection().selectAllChildren(document.querySelector('#curEd2 p'))")
        b.call("Input.dispatchMouseEvent", type="mousePressed", x=0, y=0, button="none") if False else None
        b.eval("document.querySelector('[data-rc=\"bold\"]').dispatchEvent(new MouseEvent('mousedown',{bubbles:true,cancelable:true}))")
        self.assertEqual(b.eval("document.querySelector('#curEd2 b, #curEd2 strong')?.textContent"), "Right start.")
        self.assertIsNone(b.eval("document.querySelector('#curEd b, #curEd strong')?.textContent"))
        b.click("#curEd2 p")
        b.key("End")
        b.type(" Right added.")
        img = self.mem.parent / "images" / "third.png"
        img.write_bytes(png(120, 80, (20, 120, 60)))
        b.set_files("#curImgFile", [img])                                                                # the cursor is in the right pane
        b.wait("document.querySelectorAll('#curEd2 figure.cimg').length>=1", 5)
        self.assertEqual(b.eval("document.querySelectorAll('#curEd figure').length"), 0)                 # so the picture lands there
        b.type("Third view")
        self.assertIn("saved and applied", self.save())
        md = self.md()
        left, right = md.split(MARKER)
        self.assertIn("Left start. Left added.", left)
        self.assertIn("**Right start. Right added.**", right)
        self.assertEqual(right.count("!["), 1)
        self.assertEqual(left.count("!["), 0)
        self.assertEqual(b.eval("document.querySelectorAll('.curpanes.read').length"), 1)
        self.assertEqual(b.errors, [])

    def test_an_unchanged_two_pane_text_round_trips_untouched(self):
        self.two_panes("Left **bold** text.\n\n- one\n- two", "Right note with a [link](https://example.com/x).")
        before = self.mem.read_text()
        self.edit()
        self.b.click('[data-cure="save"]')
        time.sleep(0.6)
        self.assertEqual(self.mem.read_text(), before)                                                   # nothing to save: nothing written
        self.assertEqual(self.b.eval("document.querySelectorAll('#curEd').length"), 0)                  # and the editor closed

    def test_escape_asks_before_discarding_and_command_enter_saves(self):
        b = self.b
        self.two_panes()
        self.edit()
        b.click("#curEd2 p")
        b.type(" Oops.")
        b.key("Escape")
        b.wait("document.getElementById('discardBar').classList.contains('on')")                         # the same "Discard changes?" guard
        b.click("#discardBar [data-dis=keep]")
        self.assertTrue(b.eval("!!document.getElementById('curEd2')"))
        b.eval("document.getElementById('curEd2').focus()")
        b.key("Enter", 4)                                                                                # ⌘Enter saves
        b.wait("!document.getElementById('curEd2')", 15)
        self.assertIn("Right pane text. Oops.", self.md())

    def test_narrow_windows_stack_the_panes(self):
        b = self.b
        self.two_panes()
        b.resize(700, 900)
        b.eval("renderCockpit('ABC')")
        left, right = (b.eval(f"document.querySelector('.curpane[data-pane=\"{n}\"]').getBoundingClientRect().toJSON()") for n in (1, 2))
        self.assertGreaterEqual(right["top"], left["bottom"] - 1)                                        # left on top
        self.assertAlmostEqual(left["width"], right["width"], delta=2)
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('.curdiv')).display"), "none")  # no divider

    def test_generate_drafts_the_left_pane_and_never_touches_the_right(self):
        b = self.b
        self.two_panes("Old left text.", "Alan's own notes.")
        b.eval("genDraft('ABC','A new drafted left pane. {F1}','- the minutes')")
        b.wait("document.getElementById('curEd2')")
        self.assertIn("A new drafted left pane.", b.eval("document.getElementById('curEd').textContent"))
        self.assertEqual(b.eval("document.getElementById('curEd2').textContent.trim()"), "Alan's own notes.")
        self.assertEqual(b.eval("CURED.html2.includes(\"Alan's own notes.\")"), True)
        self.assertIn("saved and applied", self.save())
        left, right = self.md().split(MARKER)
        self.assertIn("A new drafted left pane.", left)
        self.assertNotIn("Old left text.", left)
        self.assertEqual(right.strip(), "Alan's own notes.")

    def test_every_theme_and_mode_styles_the_panes(self):
        b = self.b
        self.two_panes()
        b.eval(CONTRAST_JS)
        bad = {}
        for pal in THEMES:
            for mode in ("Light", "Dark"):
                theme(b, pal, mode)
                r = b.eval("""(()=>{ const card=document.querySelector('.curcard'), bg=__bgOf(document.querySelector('.curpane')), t=getComputedStyle(document.querySelector('.curpane .curin p')).color,
                  div=getComputedStyle(document.querySelector('.curdiv'),'::before').backgroundColor, btn=document.querySelector('.curcollapse'), bs=getComputedStyle(btn);
                  return {text:__ratio(t,bg), divider:__ratio(div,bg), collapse:__ratio(bs.color,bs.backgroundColor), edge:__ratio(bs.borderTopColor,bg)}; })()""")
                if r["text"] < 4.5 or r["divider"] < 1.2 or r["collapse"] < 4.5:
                    bad[f"{pal}|{mode}"] = r
        self.assertEqual(bad, {})
        theme(b, "creaite", "Light")


# ===== BL-95: undated open work always shows on the project page =====

def ago(days):
    return d(-days)


def oracle(v, code="ABC"):
    """The rule written out in Python, sharing no code with the page: IDs of open work with no due date."""
    acts = [a["id"] for a in v.rows("actions") if a["project"] == code and a["status"] in ("Open", "Delayed") and not a["due_date"]]
    raid = [r["id"] for r in v.rows("raid") if r["project"] == code and r["status"] == "Open" and not r["due_date"]
            and (r["type"] in ("Risk", "Issue") or (r["response_action"] or "").strip())]
    return sorted(acts), sorted(raid)


class UndatedWorkTests(LiveBrowserCase):
    """A fresh vault with undated, dated, closed and other-project items, a live server and a browser per test."""

    @classmethod
    def load(cls, v):
        populate(v)
        src = "Alan (cx-edit)"
        item = lambda table, n, **vals: {"n": n, "op": "new", "table": table, "values": vals, "match": "strong", "flags": [], "decision": "approved"}  # noqa: E731
        v.propose("undated", [
            item("actions", 1, project="ABC", description="Undated and old", owner="Sara Example", raised=ago(20), source=src),
            item("actions", 2, project="ABC", description="Undated and fresh", owner="Omar Ali", raised=ago(1), priority="Urgent", source=src),
            item("actions", 3, project="ABC", description="Dated action", owner="Sara Example", raised=ago(20), due_date=d(9), source=src),
            item("actions", 4, project="ABC", description="Undated but closed", owner="Sara Example", raised=ago(20), status="Closed", closed=ago(2), source=src),
            item("actions", 5, project="ABC", description="Undated but cancelled", owner="Sara Example", raised=ago(20), status="Cancelled", source=src),
            item("actions", 6, project="DEF", description="Undated in another project", owner="Omar Ali", raised=ago(20), source=src),
            item("raid", 7, project="ABC", type="Assumption", description="Assumption with no response", impact="Low", likelihood="Low", raised=ago(20), source=src),
            item("raid", 8, project="ABC", type="Assumption", description="Assumption with a response to date", impact="Low", likelihood="Low", raised=ago(20),
                 response_action="Confirm with the client", source=src),
            item("raid", 9, project="ABC", type="Dependency", description="Dependency with no response", impact="Low", likelihood="Low", raised=ago(20), source=src),
            item("raid", 10, project="ABC", type="Issue", description="Issue with a date", impact="Medium", likelihood="High", raised=ago(20), due_date=d(5), source=src),
            item("decisions", 11, project="ABC", decision="A decision has no due date", made_by="Jane Doe", date=ago(3), source=src),
        ])
        v.run("apply")

    def setUp(self):
        super().setUp()
        self.b.eval("go('cockpit','ABC')")
        self.b.wait("document.querySelector('#v-cockpit .curcard')")

    def card_ids(self):
        return self.b.eval("[...document.querySelectorAll('#undatedCard [data-open]')].map(r=>r.dataset.open.split(':')[1]).sort()")

    def test_the_card_lists_exactly_the_open_undated_work(self):
        acts, raid = oracle(self.v)
        self.assertGreaterEqual(len(acts), 2)
        self.assertGreaterEqual(len(raid), 3)                                                              # the two seeded risks, an issue-free ABC, the assumption with a response
        self.assertEqual(self.card_ids(), sorted(acts + raid))
        texts = self.b.eval("document.getElementById('undatedCard').textContent")
        for out in ("Undated but closed", "Undated but cancelled", "Dated action", "Undated in another project", "Assumption with no response",
                    "Dependency with no response", "Issue with a date", "A decision has no due date"):
            self.assertNotIn(out, texts)
        self.assertIn("Assumption with a response to date", texts)                                         # an assumption only when it has a response to date
        self.assertEqual(self.b.eval("document.querySelector('#undatedCard').previousElementSibling.querySelector('h2').textContent.startsWith('Actions due or overdue')"), True)   # directly under it

    def test_the_count_is_in_the_heading_the_evidence_row_and_the_projects_table_and_matches_the_data(self):
        acts, raid = oracle(self.v)
        n = len(acts) + len(raid)
        b = self.b
        self.assertIn(f"· {n}", b.eval("document.querySelector('#undatedCard h2').textContent"))
        labels = b.eval("[...document.querySelectorAll('.evrow .evbox .l')].map(e=>e.textContent)")
        self.assertNotIn("No due date", labels)                                                            # BL-185: the status line drops it; the card keeps the count
        b.eval("go('projects')")
        b.wait("document.querySelector('#projTbl .ev')")
        self.assertIn(f"No date {n}", b.eval("[...document.querySelectorAll('#projTbl tr')].find(r=>r.textContent.includes('Example Programme')).querySelector('.ev').textContent"))
        self.assertEqual(b.eval("P.find(p=>p.code==='ABC').undated"), {"actions": len(acts), "raid": len(raid), "total": n})   # the data's own count agrees
        self.assertEqual(b.eval("P.find(p=>p.code==='DEF').undated.total"), 1)

    def test_the_links_open_works_no_date_filter_with_exactly_that_many(self):
        acts, raid = oracle(self.v)
        b = self.b
        self.assertEqual(b.eval("document.querySelectorAll('#undatedCard h2 a').length"), 0)              # the heading's number covers both lists, so it has no link
        link = b.eval("document.querySelector('#undatedCard a[data-nav^=\"actions:undated\"]').textContent.trim()")
        self.assertEqual(link, f"All {len(acts)} Example Programme undated action{'s' if len(acts) != 1 else ''} ›")
        b.click('#undatedCard a[data-nav^="actions:undated"]')
        b.wait("VIEW==='work'")
        self.assertEqual(b.eval("[WT,[...FX.due],[...PROJF],[...FX.st].sort()]"), ["actions", ["none"], ["ABC"], ["Delayed", "Open"]])
        self.assertEqual(b.eval("rows().map(x=>x.id).sort()"), acts)                                      # the same actions as the card
        b.eval("go('cockpit','ABC')")
        b.wait("document.querySelector('#undatedCard')")
        b.click('#undatedCard [data-nav^="raid:undated"]')
        b.wait("VIEW==='work' && WT==='raid'")
        shown = b.eval("rows().map(x=>x.id).sort()")
        self.assertEqual(sorted(set(raid) - set(shown)), [])                                              # every RAID item on the card is in Work's list
        extra = sorted(set(shown) - set(raid))
        self.assertEqual(len(extra), 2)                                                                    # Work's filter also has the two with no response to date
        b.eval("go('cockpit','ABC')")
        b.wait("document.querySelector('#undatedCard')")
        self.assertFalse(b.eval("!!document.querySelector('.evbox[data-undated]')"))                      # BL-185: no figure for it in the status line

    def test_each_row_shows_its_id_owner_priority_and_a_set_date_control_and_new_ones_are_dimmer(self):
        b = self.b
        rows = b.eval("""[...document.querySelectorAll('#undatedCard .undrow')].map(r=>({id:r.querySelector('.undid').textContent, text:r.querySelector('.undt').textContent.replace(/\\s+/g,' ').trim(),
          who:r.textContent, dim:r.classList.contains('dim'), btn:!!r.querySelector('input[data-und]')}))""")
        by = {r["id"]: r for r in rows}
        fresh = next(r for r in rows if r["text"].startswith("Undated and fresh"))
        old = next(r for r in rows if r["text"].startswith("Undated and old"))
        self.assertTrue(fresh["dim"])                                                                      # raised yesterday: new, dimmer
        self.assertIn("new", fresh["text"])
        self.assertFalse(old["dim"])
        self.assertIn("Omar Ali", fresh["who"])
        self.assertIn("Urgent", fresh["who"])                                                              # its priority
        self.assertTrue(all(r["btn"] for r in rows))
        # the grace period is a setting
        b.eval("go('settings','work')")
        b.wait("document.querySelector('[data-k=undatedGrace]')")
        b.eval("(()=>{ const i=document.querySelector('[data-k=undatedGrace]'); i.value=0; i.dispatchEvent(new Event('change',{bubbles:true})); })()")
        b.wait("S.undatedGrace===0")
        self.assertEqual(json.loads((self.v.root / "system/config/settings.json").read_text())["dashboard"]["undated_grace_days"], 0)
        b.eval("go('cockpit','ABC')")
        b.wait("document.querySelector('#undatedCard')")
        self.assertEqual(b.eval("document.querySelectorAll('#undatedCard .undrow.dim').length"), 0)       # grace 0: nothing is new

    def test_set_date_saves_inline_without_opening_the_panel_and_the_item_leaves_the_card(self):
        b = self.b
        acts, raid = oracle(self.v)
        target = next(a for a in self.v.rows("actions") if a["description"] == "Undated and old")["id"]
        b.click(f'#undatedCard input[data-und="actions:{target}"]')
        b.wait("document.querySelector('.cal')")                                                           # the calendar opens on the row
        self.assertFalse(b.eval("!!document.getElementById('f_due')"))                                     # and the side panel does not
        b.eval(f"(()=>{{ const i=document.getElementById('und-{target}'); i.value='16-11-2026'; i.dispatchEvent(new Event('input',{{bubbles:true}})); }})()")
        b.wait(f"!document.querySelector('#undatedCard [data-open=\"actions:{target}\"]')", 15)
        self.assertFalse(b.eval("!!document.getElementById('f_due')"))                                     # still no panel
        self.assertEqual(next(a for a in self.v.rows("actions") if a["id"] == target)["due_date"], "2026-11-16")   # a normal proposal, applied (BL-181: a Monday, so no weekend alert)
        b.wait(f"!document.querySelector('#undatedCard [data-open=\"actions:{target}\"]')")
        left_acts, left_raid = oracle(self.v)
        self.assertEqual(left_acts, sorted(set(acts) - {target}))
        self.assertEqual(self.card_ids(), sorted(left_acts + left_raid))
        self.assertEqual(b.eval("P.find(p=>p.code==='ABC').undated.actions"), len(left_acts))
        self.assertFalse(list((self.v.root / "system/staging").glob("proposed-*dashboard*.json")))        # nothing of ours waits: it was applied

    def test_the_card_is_absent_when_nothing_is_undated(self):
        b = self.b
        acts, raid = oracle(self.v)
        items = [{"n": i, "op": "update", "table": "actions", "id": a, "changes": {"due_date": d(12)}, "decision": "approved", "match": "strong", "flags": []}
                 for i, a in enumerate(acts, 1)] + \
                [{"n": 20 + i, "op": "update", "table": "raid", "id": r, "changes": {"due_date": d(12)}, "decision": "approved", "match": "strong", "flags": []}
                 for i, r in enumerate(raid, 1)]
        self.v.propose("dates", items)
        self.v.run("apply")
        b.eval("reloadData()")
        b.wait("P.find(p=>p.code==='ABC').undated.total===0")
        b.eval("go('cockpit','ABC')")
        self.assertEqual(b.eval("document.querySelectorAll('#undatedCard').length"), 0)                   # hidden
        self.assertFalse(b.eval("[...document.querySelectorAll('.evrow .evbox .l')].some(e=>e.textContent==='No due date')"))   # BL-185: not in the status line

    def test_readable_in_every_theme_and_mode(self):
        b = self.b
        b.eval(CONTRAST_JS)
        bad = {}
        for pal in THEMES:
            for mode in ("Light", "Dark"):
                theme(b, pal, mode)
                r = b.eval("""(()=>{ const card=document.getElementById('undatedCard'), bg=__bgOf(card), pick=s=>getComputedStyle(card.querySelector(s)).color,
                  dim=card.querySelector('.undrow.dim .undt'), over=getComputedStyle(card.querySelector('.undset input')), ph=getComputedStyle(card.querySelector('.undset input'),'::placeholder'); return {title:__ratio(pick('.undrow:not(.dim) .undt'),bg), id:__ratio(pick('.undid'),bg),
                  dim:__ratio(getComputedStyle(dim).color,bg), btn:__ratio(over.color,over.backgroundColor), ph:__ratio(ph.color,over.backgroundColor)}; })()""")
                if min(r.values()) < 4.5:
                    bad[f"{pal}|{mode}"] = r
        self.assertEqual(bad, {})
        theme(b, "creaite", "Light")


# ===== BL-91: Trends and flow =====

NOW = "2026-10-14 09:00"          # a Wednesday; the weeks are Monday to Sunday from 24-08-2026 to this one (8 of them)
WEEKS = ["2026-08-24", "2026-08-31", "2026-09-07", "2026-09-14", "2026-09-21", "2026-09-28", "2026-10-05", "2026-10-12"]


def item(table, n, **values):
    return {"n": n, "op": "new", "table": table, "values": values, "match": "strong", "flags": [], "decision": "approved"}


def flow_vault():
    """Fixed sample data with known opened, closed, overdue and ageing values (today is 14-10-2026), described in the test names."""
    v = Vault()
    v.run("init")
    src = f"{ABC}/minutes/2026-09-01 Steering.docx — Actions"
    v.propose("flow", [
        action(1, description="a1 closed in week 3", raised="2026-09-01", status="Closed", closed="2026-09-10", source=src),
        action(2, description="a2 closed in week 5", raised="2026-09-02", status="Closed", closed="2026-09-22", source=src),
        action(3, description="a3 open and overdue", raised="2026-09-08", due_date="2026-09-30", source=src),
        action(4, description="a4 open, undated", raised="2026-09-15", source=src),
        action(5, description="a5 cancelled", raised="2026-09-16", status="Cancelled", closed="2026-09-17", source=src),
        action(6, description="a6 due later", raised="2026-10-06", due_date="2026-10-20", source=src),
        action(7, description="a7 due today", raised="2026-10-13", due_date="2026-10-14", source=src),
        action(8, description="a8 re-dated", raised="2026-09-29", due_date="2026-10-30", source=src),
        action(9, description="a9 just overdue", raised="2026-10-12", due_date="2026-10-13", source=src),
        item("raid", 10, project="ABC", type="Risk", description="r1 an older risk", impact="High", likelihood="Medium", raised="2026-09-03", source=src),
        item("raid", 11, project="ABC", type="Dependency", description="r4 a dependency", impact="Low", likelihood="Low", raised="2026-09-10", source=src),
        item("raid", 12, project="ABC", type="Issue", description="r2 an issue, closed", impact="Medium", likelihood="High", raised="2026-09-20",
             status="Closed", closed="2026-10-07", source=src),
        item("raid", 13, project="ABC", type="Risk", description="r3 an Urgent risk", impact="High", likelihood="High", raised="2026-10-13", source=src),
        item("milestones", 14, project="ABC", name="UAT start", baseline_date="2026-10-01", forecast_date="2026-10-22", source="Alan (cx-edit)"),
        item("milestones", 15, project="ABC", name="Build complete", baseline_date="2026-10-10", forecast_date="2026-10-07", source="Alan (cx-edit)"),
    ])
    v.run("apply")
    log(v, [("2026-10-08 10:00:00", "actions", "ABC-A-008", "due_date", "2026-10-02", "2026-10-30"),      # a8 was overdue at the end of week 6
            ("2026-09-12 10:00:00", "milestones", "ABC-M-001", "forecast_date", "2026-10-01", "2026-10-15"),
            ("2026-10-02 10:00:00", "milestones", "ABC-M-001", "forecast_date", "2026-10-15", "2026-10-22"),
            ("2026-10-05 10:00:00", "milestones", "ABC-M-002", "forecast_date", "2026-10-10", "2026-10-07")])
    for f in (v.root / "system/history").glob("flow-*.json"):     # the apply's build ran on the real clock, not NOW: its snapshot
        f.unlink()                                                  # (one for a Sunday in the period is read back) isn't sample data
    return v


def flow(v, now=NOW, extra=""):
    return json.loads(py(v, f"import json, build_dashboard as b\n{extra}print(json.dumps(b.collect()['flow']['ABC']))", now))


class FlowDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = flow_vault()
        cls.f = flow(cls.v)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def col(self, key):
        return [w[key] for w in self.f["weeks"]]

    def test_the_weeks_run_monday_to_sunday_and_the_last_is_this_week_so_far(self):
        self.assertEqual([w["start"] for w in self.f["weeks"]], WEEKS)
        self.assertEqual(self.f["weeks"][0]["end"], "2026-08-30")
        self.assertEqual(self.f["weeks"][-1]["end"], "2026-10-14")                                      # today
        self.assertEqual(self.f["period"], 8)

    def test_opened_and_closed_per_week(self):
        self.assertEqual(self.col("a_opened"), [0, 2, 1, 2, 0, 1, 1, 2])                                # actions raised
        self.assertEqual(self.col("a_closed"), [0, 0, 1, 0, 1, 0, 0, 0])
        self.assertEqual(self.col("a_cancelled"), [0, 0, 0, 1, 0, 0, 0, 0])                             # cancelled is not closed
        self.assertEqual(self.col("r_opened"), [0, 1, 0, 1, 0, 0, 0, 1])                                # risks and issues only
        self.assertEqual(self.col("r_closed"), [0, 0, 0, 0, 0, 0, 1, 0])
        self.assertEqual(self.col("opened"), [0, 3, 2, 3, 0, 1, 1, 3])                                  # everything, the dependency too
        self.assertEqual(self.col("closed"), [0, 0, 1, 0, 1, 0, 1, 0])
        self.assertEqual(self.col("cancelled"), [0, 0, 0, 1, 0, 0, 0, 0])

    def test_overdue_by_week_is_rebuilt_from_the_change_log(self):
        self.assertEqual(self.col("overdue"), [0, 0, 0, 0, 0, 2, 1, 2])                                 # a8 was overdue until it was re-dated on 08-10
        self.assertEqual(self.f["overdue"], {"now": 2, "last_week": 1})
        self.assertFalse(any(w["from_snapshot"] for w in self.f["weeks"]))

    def test_how_long_open_items_have_been_open(self):
        a = self.f["ageing"]
        self.assertEqual(a["labels"], ["0 to 7 days", "8 to 14 days", "15 to 30 days", "Over 30 days"])
        self.assertEqual(a["buckets"], [3, 1, 2, 3])                                                    # of 9 open items
        self.assertEqual(a["open"], 9)
        self.assertEqual([(o["id"], o["days"]) for o in a["oldest"]], [("ABC-010", 41), ("ABC-A-003", 36), ("ABC-011", 34)])
        self.assertEqual([o["k"] for o in a["oldest"]], ["raid", "actions", "raid"])                    # linked to their tables

    def test_risks_and_milestone_movement(self):
        r = self.f["risks"]
        self.assertEqual((r["opened"], r["closed"], r["cancelled"]), (3, 1, 0))
        self.assertEqual(r["mix"], {"Urgent": 1, "High": 1, "Medium": 0, "Low": 0})                     # the open ones now
        m = self.f["milestones"]
        self.assertEqual((m["moves"], m["days"]), (3, 18))                                              # +14, +7 and -3
        self.assertEqual([(x["id"], x["moves"], x["days"], x["name"]) for x in m["by"]],
                         [("ABC-M-001", 2, 21, "UAT start"), ("ABC-M-002", 1, -3, "Build complete")])

    def test_the_summary_line(self):
        self.assertEqual(self.f["summary"], "3 opened, 0 closed; 2 overdue, up from 1; the oldest open action is 36 days old")

    def test_the_daily_snapshot_is_written_by_a_build_and_read_back_for_past_weeks_only(self):
        v = self.v
        py(v, "import build_dashboard as b\nb.build()", NOW)
        snap = json.loads((v.root / "system/history/flow-2026-10-14.json").read_text())
        self.assertEqual(snap["projects"]["ABC"], {"overdue": 2, "open": 9})
        (v.root / "system/history/flow-2026-10-11.json").write_text(json.dumps({"date": "2026-10-11", "projects": {"ABC": {"overdue": 7, "open": 9}}}))
        (v.root / "system/history/flow-2026-10-14.json").write_text(json.dumps({"date": "2026-10-14", "projects": {"ABC": {"overdue": 99, "open": 9}}}))
        f = flow(v)
        self.assertEqual(f["weeks"][-2]["overdue"], 7)                                                 # last week's end: the snapshot wins
        self.assertTrue(f["weeks"][-2]["from_snapshot"])
        self.assertEqual(f["overdue"]["now"], 2)                                                       # today is always worked out afresh
        self.assertEqual(f["weeks"][-3]["overdue"], 2)                                                 # no snapshot for that day: rebuilt
        for p in (v.root / "system/history").glob("flow-*.json"):
            p.unlink()
        self.assertEqual([r for r in v.rows("projects") if r["code"] == "ABC"][0]["code"], "ABC")      # (a snapshot is a file, not a table)
        import sqlite3
        with sqlite3.connect(v.root / "system/tracker.db") as con:
            self.assertFalse([t for (t,) in con.execute("select name from sqlite_master where type='table'") if "flow" in t])

    def test_the_period_is_a_setting(self):
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        try:
            for value, weeks in ((12, 12), (3, 4), (40, 26), ("x", 8)):
                data.setdefault("dashboard", {})["flow_weeks"] = value
                cfg.write_text(json.dumps(data))
                self.assertEqual(len(flow(self.v)["weeks"]), weeks, value)                              # 4 to 26, 8 if unreadable
        finally:
            data["dashboard"]["flow_weeks"] = 8
            cfg.write_text(json.dumps(data))

    def test_an_undone_date_change_never_happened(self):
        import sqlite3
        v = self.v
        with sqlite3.connect(v.root / "system/tracker.db") as con:
            con.execute("INSERT INTO applies (apply_id, at, proposals, undone_at) VALUES (901, '2026-10-03', '[]', '2026-10-04')")
        log(v, [("2026-10-03 10:00:00", "actions", "ABC-A-003", "due_date", "2026-09-30", "2026-10-30", 901)])
        try:
            self.assertEqual(flow(v)["weeks"][-1]["overdue"], 2)                                         # a3 is still overdue
        finally:
            with sqlite3.connect(v.root / "system/tracker.db") as con:
                con.execute("DELETE FROM change_log WHERE apply_id = 901")
                con.execute("DELETE FROM applies WHERE apply_id = 901")


class FlowWeeklyReportTests(unittest.TestCase):
    """The weekly report gets a line about flow, first in Progress This Week."""

    def test_the_line_and_the_word_report(self):
        v = flow_vault()
        try:
            now = "2026-10-16 13:00"
            line = json.loads(py(v, "import json, report\nprint(json.dumps(report.weekly_data('ABC')['flow']))", now))
            self.assertEqual(line, "3 opened, 0 closed; 3 overdue, up from 1; the oldest open action is 38 days old")
            spec = v.root / "system/staging/drafts/weekly.json"
            spec.parent.mkdir(parents=True, exist_ok=True)
            spec.write_text(json.dumps({"code": "ABC", "health": "At risk", "health_reason": "Overdue items rising", "summary": ["Quiet but late."],
                                        "key_changes": "None", "current_state": "Steady.", "progress": ["Plan revised"], "next_week": ["Chase"]}))
            import os
            subprocess.run([sys.executable, str(v.root / "system/scripts/report.py"), "weekly-stage", str(spec)], cwd=v.root, check=True,
                           env={**os.environ, "CREAITE_NOW": now}, capture_output=True)
            draft = next((v.root / "system/staging/drafts").glob("* Weekly report - Example Programme.docx"))
            text = v.run("text", str(draft), script="docx_tools.py").stdout
            self.assertIn("Flow: 3 opened, 0 closed; 3 overdue, up from 1; the oldest open action is 38 days old.", text)
            self.assertLess(text.index("Flow: 3 opened"), text.index("Plan revised"))                      # first in Progress This Week
            self.assertEqual(text.count("Flow: "), 1)
        finally:
            v.cleanup()


class FlowCardTests(unittest.TestCase):
    """The Flow card in the browser: inline SVG drawn to scale, in each theme's colours."""

    @classmethod
    def setUpClass(cls):
        if not CHROME.exists():
            raise unittest.SkipTest("Google Chrome not installed")
        cls.v = flow_vault()
        py(cls.v, "import build_dashboard as b\nb.build()", NOW)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def probe(self, script):
        out, errors = chrome(self.v, "VSTATE='ok'; " + CONTRAST_JS + ";" + script, name="flow")
        self.assertEqual(errors, [])
        self.assertIsNotNone(out)
        self.assertNotIn("error", out, out)
        return out

    def test_the_card_is_drawn_to_scale_with_every_number_on_it(self):
        o = self.probe("""
          go("cockpit","ABC"); const c=document.getElementById("flowCard"), out={}, figs=[...c.querySelectorAll("figure.flc")];
          out.captions=figs.map(f=>f.querySelector("figcaption").textContent);
          const bars=f=>[...f.querySelectorAll("rect[data-wk]")].map(r=>({v:+r.dataset.v,h:+r.getAttribute("height"),wk:r.dataset.wk,cls:r.getAttribute("class")}));
          out.actions=bars(figs[0]); out.risks=bars(figs[1]); out.overdue=bars(figs[2]);
          out.labels=[...figs[0].querySelectorAll("text.fl-m")].map(t=>t.textContent);
          out.valueLabels=[...figs[0].querySelectorAll("text.fl-t")].map(t=>t.textContent);
          out.hbars=[...figs[3].querySelectorAll("rect[data-v]")].map(r=>({v:+r.dataset.v,w:+r.getAttribute("width")}));
          out.mix=[...figs[4].querySelectorAll("rect[data-v]")].map(r=>({v:+r.dataset.v,w:+r.getAttribute("width")}));
          out.summary=document.getElementById("flowSummary").textContent; out.legend=[...figs[0].querySelectorAll("text.fl-t")].map(t=>t.textContent).filter(t=>/opened|closed/.test(t));
          out.oldest=[...c.querySelectorAll("[data-open]")].map(e=>e.dataset.open); out.svgs=c.querySelectorAll("figure.flc svg").length; out.aria=figs.map(f=>f.querySelector("svg").getAttribute("aria-label"));
          window.OUT=out;""")
        self.assertEqual(o["svgs"], 5)
        self.assertEqual(o["captions"][0], "Actions opened and closed, by week")
        self.assertIn("2 now, up from 1 last week", o["captions"][2])
        # one scale per chart: a bar is its count times the same factor, so 2 is twice 1 and the tallest fills the plot
        a = o["actions"]
        opened = [b for b in a if "fl-op" in b["cls"]]
        self.assertEqual([b["v"] for b in opened], [0, 2, 1, 2, 0, 1, 1, 2])
        unit = 98 / 2                                                                                  # plot height (150 - 22 - 30) over the largest count
        for b in a:
            self.assertAlmostEqual(b["h"], b["v"] * unit, delta=0.02, msg=b)
        self.assertEqual([b["wk"] for b in opened][-1], "2026-10-14")
        for b in o["risks"]:
            self.assertAlmostEqual(b["h"], b["v"] * 98, delta=0.02)                                    # largest 1: the full height
        self.assertEqual([b["v"] for b in o["overdue"]], [0, 0, 0, 0, 0, 2, 1, 2])
        self.assertEqual(o["labels"][0:2], ["2", "0"])                                                 # the scale: the largest count, and zero
        self.assertEqual(o["labels"][2:], ["28-08", "04-09", "11-09", "18-09", "25-09", "02-10", "09-10", "16-10"])   # each week's Friday, DD-MM
        self.assertEqual(len(o["labels"]), 8 + 2)                                                      # eight weeks, the largest count and zero
        self.assertTrue({"opened", "closed"} <= set(o["legend"]))                                      # a legend in words
        self.assertEqual([x["v"] for x in o["hbars"]], [3, 1, 2, 3])
        self.assertAlmostEqual(o["hbars"][0]["w"] / o["hbars"][1]["w"], 3, delta=0.02)                 # to scale
        self.assertAlmostEqual(o["hbars"][3]["w"], o["hbars"][0]["w"], delta=0.02)
        self.assertEqual([x["v"] for x in o["mix"]], [1, 1])                                           # Urgent and High
        self.assertAlmostEqual(o["mix"][0]["w"], o["mix"][1]["w"], delta=0.02)
        self.assertEqual(o["summary"], "This week: 3 opened, 0 closed; 2 overdue, up from 1; the oldest open action is 36 days old.")
        self.assertEqual(o["oldest"], ["raid:ABC-010", "actions:ABC-A-003", "raid:ABC-011"])
        self.assertTrue(all(a.startswith(("Actions", "Risks", "Overdue", "Open")) for a in o["aria"]))

    def test_the_oldest_open_items_open_their_panel_and_the_card_shows_milestone_movement(self):
        o = self.probe("""
          go("cockpit","ABC"); const c=document.getElementById("flowCard"), out={}; out.text=c.textContent.replace(/\\s+/g," ");
          c.querySelector('[data-open="actions:ABC-A-003"]').click(); out.opened=[!!CUR,CUR&&CUR.id]; window.OUT=out;""")
        self.assertEqual(o["opened"], [True, "ABC-A-003"])
        self.assertIn("3 forecast moves in 8 weeks, 18 days later in all", o["text"])
        self.assertIn("UAT start: 2 moves, 21 days later", o["text"])
        self.assertIn("Build complete: 1 move, 3 days earlier", o["text"])
        self.assertIn("3 opened, 1 closed in 8 weeks", o["text"])                                      # risks and issues
        self.assertIn("counts only", o["text"])

    def test_colours_are_the_themes_and_readable_in_every_mode_with_a_colour_blind_safe_pair(self):
        o = self.probe("""
          go("cockpit","ABC"); const out={}, hue=c=>{ const [r,g,b]=c.match(/[\\d.]+/g).slice(0,3).map(Number).map(v=>v/255), mx=Math.max(r,g,b), mn=Math.min(r,g,b), d=mx-mn; if(!d) return null;
            const h=mx===r?((g-b)/d)%6:mx===g?(b-r)/d+2:(r-g)/d+4; return ((h*60)+360)%360; };
          for(const pal of THEMES.map(t=>t.id)) for(const mode of ["Light","Dark"]){ S.palette=pal; S.theme=mode; applyTheme(); renderCockpit("ABC"); const c=document.getElementById("flowCard"), bg=__bgOf(c);
            const fill=s=>getComputedStyle(c.querySelector(s)).fill, root=getComputedStyle(document.documentElement), tok=n=>{ const e=document.createElement("i"); e.style.color=`var(${n})`; c.appendChild(e); const v=getComputedStyle(e).color; e.remove(); return v; };
            const op=fill("rect.fl-op[data-v]"), cl=fill("rect.fl-cl[data-v]"), od=fill("rect.fl-od[data-v]");
            const dh=(a,b)=>{ const x=hue(a), y=hue(b); if(x===null||y===null) return null; const d=Math.abs(x-y); return Math.min(d,360-d); };
            out[pal+"|"+mode]={op:__ratio(op,bg), cl:__ratio(cl,bg), od:__ratio(od,bg), muted:__ratio(fill("rect.fl-pL")||tok("--muted"),bg), pair:__ratio(op,cl), hue:dh(op,cl),
              text:__ratio(getComputedStyle(c.querySelector("text.fl-t")).fill,bg), small:__ratio(getComputedStyle(c.querySelector("text.fl-m")).fill,bg), hatched:c.querySelectorAll("rect.fl-cl[data-v] ~ rect.fl-hatch, rect.fl-hatch").length>0&&getComputedStyle(c.querySelector("pattern .fl-hp")).fill!=="none", isAccent:op===tok("--accent"), isWarn:cl===tok("--warn"), isBad:od===tok("--bad")}; }
          window.OUT=out;""")
        self.assertEqual(len(o), theme_count() * 2)                                                     # every theme, light and dark
        for key, r in o.items():
            for k in ("op", "cl", "od"):
                self.assertGreaterEqual(r[k], 3.0, (key, k))                                            # bars against the card: 3:1
            self.assertGreaterEqual(r["text"], 4.5, key)
            self.assertGreaterEqual(r["small"], 4.5, key)
            self.assertTrue(r["isAccent"] and r["isWarn"] and r["isBad"], key)                         # the theme's own tokens
            self.assertTrue(r["hatched"], key)                                                           # closed bars are hatched, not only coloured
            self.assertTrue((r["hue"] is not None and r["hue"] >= 40) or r["pair"] >= 1.5, (key, r))   # and the pair is still two colours


# ===== BL-90 part 1: dependencies, with no schema change =====

DEPNOW = d(0) + " 09:00"                      # the page works out "today" from the browser's clock, so these dates are relative to the real today


def dmy(n):
    return d(n)[8:] + "-" + d(n)[5:7] + "-" + d(n)[:4]


def subst(js):
    """The page scripts name dates relative to today: __D6__ is DD-MM-YYYY, six days on."""
    return js.replace("__D6__", dmy(6)).replace("__D40__", dmy(40))


def dep_vault():
    """Dependencies attached to milestones (a milestone link on a Dependency), with and without date trouble. Dates are relative to today."""
    v = Vault()
    v.run("init")
    reg = v.root / "projects/_portfolio/project-register.md"
    reg.write_text(reg.read_text().replace("|  |  |  |  |  |  |  |  |", "| DEF | Digital Enablement | DEF Digital Enablement | Enable | Sam (sponsor) | def.example | DEF core | portal |"))
    v.run("init")
    src = "Alan (cx-edit)"
    dep = lambda n, text, **kw: item("raid", n, project=kw.pop("project", "ABC"), type="Dependency", description=text, impact="Medium", likelihood="Medium",   # noqa: E731
                                     raised=d(-13), source=src, **kw)
    v.propose("deps", [
        item("milestones", 1, project="ABC", name="UAT start", baseline_date=d(6), forecast_date=d(10), source=src),          # ABC-M-001
        item("milestones", 2, project="ABC", name="Go-live", baseline_date=d(37), forecast_date=d(37), source=src),            # ABC-M-002
        item("milestones", 3, project="ABC", name="Hypercare", baseline_date=d(62), forecast_date=d(62), source=src),         # ABC-M-003
        item("milestones", 4, project="ABC", name="Closure", baseline_date=d(98), forecast_date=d(98), source=src),           # ABC-M-004
        item("milestones", 5, project="ABC", name="Build complete", baseline_date=d(-13), forecast_date=d(-13), status="Done", source=src),   # ABC-M-005
        dep(10, "Data extract from the client", due_date=d(16), milestone="ABC-M-001", owner="Client IT"),         # due after UAT start: warning
        dep(11, "Test environment ready", due_date=d(6), milestone="ABC-M-001", owner="Sara Example"),            # before it: fine
        dep(12, "Security approval", due_date=d(-4), milestone="ABC-M-001", owner="Client security"),              # overdue, UAT start is 10 days off: warning
        dep(13, "Licences purchased", due_date=d(-13), milestone="ABC-M-002", owner="Omar Ali"),                    # overdue, but go-live is 37 days off
        dep(14, "Legal sign-off", due_date=d(14), owner="Jane Doe"),                                                # not attached
        dep(15, "Closed dependency", due_date=d(47), milestone="ABC-M-001", owner="Sara Example", status="Closed", closed=d(-2)),
        dep(16, "On a finished milestone", due_date=d(16), milestone="ABC-M-005", owner="Sara Example"),           # its milestone is Done
        item("raid", 17, project="ABC", type="Risk", description="A risk with a milestone", impact="High", likelihood="High", raised=d(-13),
             due_date=d(16), milestone="ABC-M-001", source=src),                                                  # not a dependency
        dep(18, "Another project's dependency", project="DEF", due_date=d(16), owner="Sam"),
    ])
    v.run("apply")
    return v


def dep_ids(v):
    return {r["description"]: r["id"] for r in v.rows("raid")}


class DependencyWarningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = dep_vault()
        cls.ids = dep_ids(cls.v)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def warnings(self, now=DEPNOW):
        return json.loads(py(self.v, "import json, paths, build_dashboard as b\nfrom datetime import date\n"
                             f"print(json.dumps([w for w in b.early_warnings(paths.load_settings(), date.fromisoformat('{now[:10]}')) if w['sig'] == 'dependency']))", now))

    def test_a_dependency_due_after_what_it_blocks_and_an_overdue_one_near_it(self):
        i = self.ids
        got = {w["id"]: w for w in self.warnings()}
        self.assertEqual(set(got), {i["Data extract from the client"], i["Security approval"]})
        w = got[i["Data extract from the client"]]
        self.assertEqual((w["k"], w["p"], w["ms"]), ("raid", "ABC", "ABC-M-001"))
        self.assertEqual(w["text"], f"ABC-M-001 forecast {dmy(10)}, but dependency {i['Data extract from the client']} isn't due until {dmy(16)}")
        self.assertEqual(got[i["Security approval"]]["text"],
                         f"Dependency {i['Security approval']} is overdue (due {dmy(-4)}) and ABC-M-001 is forecast for {dmy(10)}")
        quiet = {i[t] for t in ("Test environment ready", "Licences purchased", "Legal sign-off", "Closed dependency", "On a finished milestone",
                                "A risk with a milestone", "Another project's dependency")}
        self.assertFalse(quiet & set(got))                                                              # nothing for the rest

    def test_the_setting_switches_it_off_and_moves_the_near_days(self):
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        try:
            data["warnings"]["dependency"] = {"on": True, "near_days": 40}
            cfg.write_text(json.dumps(data))
            self.assertIn(self.ids["Licences purchased"], {w["id"] for w in self.warnings()})           # now go-live counts as near
            data["warnings"]["dependency"] = {"on": False, "near_days": 14}
            cfg.write_text(json.dumps(data))
            self.assertEqual(self.warnings(), [])
        finally:
            data["warnings"]["dependency"] = {"on": True, "near_days": 14}
            cfg.write_text(json.dumps(data))

    def test_it_follows_the_dates(self):
        later = (date.today() + timedelta(days=12)).isoformat() + " 09:00"                              # UAT start has passed its forecast by then
        self.assertIn(self.ids["Data extract from the client"], {w["id"] for w in self.warnings(later)})
        self.assertEqual(len(self.warnings()), 2)

    def test_nothing_is_stored(self):
        import sqlite3
        with sqlite3.connect(self.v.root / "system/tracker.db") as con:
            self.assertFalse([t for (t,) in con.execute("select name from sqlite_master where type='table'")
                              if ("link" in t or "depend" in t) and t != "links"])
            self.assertEqual(con.execute("select count(*) from links").fetchone()[0], 0)    # the warning isn't stored as a link (the table is BL-90 part 2, Sprint 5)


class DependencyPageTests(unittest.TestCase):
    """The card, the marks, the suggestion chips and Work's filter, in the browser (file mode, today fixed)."""

    @classmethod
    def setUpClass(cls):
        if not CHROME.exists():
            raise unittest.SkipTest("Google Chrome not installed")
        cls.v = dep_vault()
        cls.ids = dep_ids(cls.v)
        py(cls.v, "import build_dashboard as b\nb.build()", DEPNOW)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def probe(self, script):
        out, errors = chrome(self.v, "VSTATE='ok'; " + CONTRAST_JS + ";const wait=ms=>new Promise(r=>setTimeout(r,ms)); " + script, name="deps")
        self.assertEqual(errors, [])
        self.assertIsNotNone(out)
        self.assertNotIn("error", out, out)
        return out

    def test_the_dependencies_card_groups_by_what_they_block(self):
        i = self.ids
        o = self.probe("""
          go("cockpit","ABC"); const c=document.getElementById("depCard"), out={};
          out.head=c.querySelector("h2").textContent.replace(/\\s+/g," ").trim();
          out.groups=[...c.querySelectorAll(".depg")].map(g=>({g:g.dataset.g,head:g.querySelector(".depgh").textContent.replace(/\\s+/g," ").trim(),rows:[...g.querySelectorAll(".deprow")].map(r=>({id:r.dataset.open,text:r.querySelector(".dept").textContent,warn:(r.querySelector(".depwarn")||{}).textContent||"",late:!!r.querySelector(".late"),who:r.textContent}))}));
          out.below=document.getElementById("depCard").previousElementSibling.querySelector("h2").textContent;
          window.OUT=out;""")
        self.assertEqual(o["head"], "Dependencies · 6 · 2 at risk")                                    # open ones only (one is on a finished milestone); two have a date warning
        groups = o["groups"]
        self.assertEqual([g["g"] for g in groups], ["ABC-M-005", "ABC-M-001", "ABC-M-002", ""])         # by milestone date (the finished one is earliest); unattached last
        g1 = next(g for g in groups if g["g"] == "ABC-M-001")
        self.assertIn("UAT start", g1["head"])
        self.assertIn(f"forecast {dmy(10)}", g1["head"])
        self.assertEqual([r["id"] for r in g1["rows"]], [f"raid:{i['Data extract from the client']}", f"raid:{i['Test environment ready']}", f"raid:{i['Security approval']}"])
        self.assertIn(f"isn't due until {dmy(16)}", g1["rows"][0]["warn"])
        self.assertEqual(g1["rows"][1]["warn"], "")
        self.assertTrue(g1["rows"][2]["late"])                                                          # the overdue one's date in the late style
        self.assertIn("Client IT", g1["rows"][0]["who"])                                                # an outside party is its owner
        self.assertIn("Not attached", groups[3]["head"])
        self.assertEqual([r["text"] for r in groups[3]["rows"]], ["Legal sign-off"])
        flat = " ".join(r["text"] for g in groups for r in g["rows"])
        for out_ in ("Closed dependency", "A risk with a milestone", "Another project"):
            self.assertNotIn(out_, flat)
        self.assertEqual(o["below"], "Recent decisions")

    def test_the_card_is_absent_when_there_are_no_open_dependencies(self):
        o = self.probe("""go("cockpit","DEF"); R.filter(r=>r.p==="DEF").forEach(r=>r.st="Closed"); renderCockpit("DEF"); window.OUT={n:document.querySelectorAll("#depCard").length};""")
        self.assertEqual(o["n"], 0)

    def test_a_blocked_milestone_shows_waiting_on_and_an_at_risk_mark(self):
        i = self.ids
        o = self.probe("""
          MVAUD="int";   /* BL-244: Client is the first-visit view; "waiting on" is internal only (BL-90) */
          go("cockpit","ABC"); const rows=[...document.querySelectorAll("#mvCard .mv-prow[data-mvedit]")], out={};   /* BL-186: the card's Plan rows */
          out.rows=rows.map(r=>({id:r.dataset.mvedit,risk:r.classList.contains("atrisk"),tag:(r.querySelector(".waiting")||{}).textContent||"",title:(r.querySelector(".waiting")||{}).title||""}));
          document.querySelector("#depCard [data-ms=ABC-M-001]").click(); await wait(50); out.panel=[VIEW,MSCODE,MV.peek]; window.OUT=out;""")
        by = {r["id"]: r for r in o["rows"]}
        uat = by["ABC-M-001"]
        self.assertTrue(uat["risk"])
        self.assertEqual(uat["tag"], f"waiting on {i['Data extract from the client']}, {i['Security approval']}")
        self.assertIn(f"isn't due until {dmy(16)}", uat["title"])
        for quiet in ("ABC-M-002", "ABC-M-003", "ABC-M-004"):
            self.assertFalse(by[quiet]["risk"], quiet)                                                  # a late dependency far off doesn't mark go-live
        self.assertEqual(o["panel"], ["milestones", "ABC", "ABC-M-001"])                                 # BL-186: the Milestones page, its editor open

    def test_the_warning_flags_the_dependency_in_work_and_the_panel(self):
        i = self.ids
        o = self.probe(f"""
          WT="raid"; applyView("open"); go("work"); const flagged=[...document.querySelectorAll("#workTbl tr[data-row]")].filter(r=>r.querySelector(".wflag")&&warnsOf("raid",r.dataset.row).some(w=>w.sig==="dependency")).map(r=>r.dataset.row);   /* BL-181: a weekend due date flags too */
          openRecord("raid","{i['Data extract from the client']}"); window.OUT={{flagged, note:(document.getElementById("pkWarn")||{{}}).textContent||""}};   /* BL-176: the peek's warning line */""")
        self.assertEqual(sorted(o["flagged"]), sorted([i["Data extract from the client"], i["Security approval"]]))
        self.assertIn(f"isn't due until {dmy(16)}", o["note"])

    def test_suggested_milestones_appear_as_chips_in_the_panel_and_are_never_attached_by_themselves(self):
        i = self.ids
        o = self.probe(subst("""
          go("work"); WT="raid"; openNew("raid"); const out={}, set=(n,v)=>{ CUR.draft[n]=n==="due"&&DDATE.test(v)?toIso(v):v; pkDraw(); };   /* BL-179: the new item is the peek; its draft as the chips leave it */
          const chips=()=>[...document.querySelectorAll("#depSug button")].map(b=>b.textContent);
          set("p","ABC"); out.risk=chips();                                                            // a Risk: no chips
          set("type","Dependency"); out.noDue=chips();                                                  // no due date: nothing to compare with
          set("t","Vendor access"); set("due","__D6__"); out.chips=chips();
          out.msStill=CUR.draft.ms;                                                                     // nothing attached by itself
          set("due","__D40__"); out.later=chips(); set("due","__D6__");
          document.querySelector("[data-pkdep=ABC-M-002]").click(); await pkQuiet(); out.attached=[CUR.draft.ms,chips()];
          set("ms",""); out.again=chips().length; document.querySelector("[data-pkdepnone]").click(); out.none=chips();
          set("t","Vendor access, revised"); out.textChanged=chips().length; window.OUT=out;"""))
        self.assertEqual(o["risk"], [])
        self.assertEqual(o["noDue"], [])
        self.assertEqual(o["chips"], [f"Attach to ABC-M-001 (forecast {dmy(10)})?", f"Attach to ABC-M-002 (forecast {dmy(37)})?",
                                      f"Attach to ABC-M-003 (forecast {dmy(62)})?", "None needed"])    # up to three, nearest first; Done ones never; then None needed
        self.assertEqual(o["msStill"], "")
        self.assertEqual(o["later"], [f"Attach to ABC-M-003 (forecast {dmy(62)})?", f"Attach to ABC-M-004 (forecast {dmy(98)})?", "None needed"])   # only those it could threaten
        self.assertEqual(o["attached"], ["ABC-M-002", []])                                              # a click attaches it; the chips go
        self.assertEqual(o["again"], 4)
        self.assertEqual(o["none"], [])                                                                 # "None needed" is remembered
        self.assertEqual(o["textChanged"], 4)                                                           # until its text changes

    def test_work_has_an_unattached_dependencies_view_and_filter(self):
        i = self.ids
        o = self.probe("""
          WT="raid"; go("work"); const out={};
          out.views=allViews("raid").map(v=>v.label); applyView("unatt"); renderWork(); out.rows=rows().map(x=>x.id).sort(); out.chips=[...document.querySelectorAll("#wapplied .fchip")].map(c=>c.firstChild.textContent.trim());
          out.sub=[...document.querySelectorAll("#workTbl tr[data-row]")].map(r=>r.querySelector("td.title .x").textContent.trim());
          out.hash=hashOf(navState()); out.parsed=parseHash("#work=raid&st=Open&ty=Dependency&ms=no").fx;
          WT="raid"; applyView("open"); renderWork(); out.attachedSub=[...document.querySelectorAll("#workTbl tr[data-row]")].filter(r=>r.dataset.row==="%s").map(r=>r.querySelector("td.title .x").textContent.trim());
          out.more=(defs().find(d=>d[0]==="ms")||[])[1]; window.OUT=out;""" % i["Data extract from the client"])
        self.assertIn("Unattached dependencies", o["views"])
        self.assertEqual(o["rows"], sorted([self.ids["Legal sign-off"], self.ids["Another project's dependency"]]))   # open dependencies with no milestone, in any project
        self.assertTrue(all("not attached" in s for s in o["sub"]), o["sub"])                           # a quiet tag on each
        self.assertIn("Milestone: Not attached", " ".join(o["chips"]))
        self.assertIn("v=unatt", o["hash"])
        self.assertEqual(o["parsed"], {"st": ["Open"], "ty": ["Dependency"], "ms": ["no"]})
        self.assertNotIn("not attached", " ".join(o["attachedSub"]))
        self.assertEqual(o["more"], "Milestone")

    def test_readable_in_every_theme_and_mode(self):
        o = self.probe(subst("""
          MVAUD="int";   /* BL-244: the internal "waiting on" mark is checked too */
          const out={}; for(const pal of THEMES.map(t=>t.id)) for(const mode of ["Light","Dark"]){ S.palette=pal; S.theme=mode; applyTheme(); go("cockpit","ABC"); const c=document.getElementById("depCard"), bg=__bgOf(c), css=s=>getComputedStyle(c.querySelector(s));
            const m=document.querySelector("#mvCard .mv-prow.atrisk .waiting"); out[pal+"|"+mode]={warn:__ratio(css(".depwarn").color,bg), text:__ratio(css(".dept").color,bg), id:__ratio(css(".depid").color,bg), tag:__ratio(getComputedStyle(m).color,__bgOf(m))};
            go("work"); WT="raid"; openNew("raid"); Object.assign(CUR.draft,{p:"ABC",type:"Dependency",due:toIso("__D6__")}); pkDraw();   /* BL-179: the peek's suggestions */
            const b=document.querySelector("#depSug .chipbtn"), cs=getComputedStyle(b); out[pal+"|"+mode].chip=__ratio(cs.color,cs.backgroundColor); out[pal+"|"+mode].chipEdge=__ratio(cs.borderTopColor,__bgOf(b.parentElement)); closePanel(); }
          window.OUT=out;"""))
        self.assertEqual(len(o), theme_count() * 2)
        bad = {k: {n: round(x, 2) for n, x in v.items() if x < (3.0 if n == "chipEdge" else 4.5)} for k, v in o.items()}
        self.assertEqual({k: v for k, v in bad.items() if v}, {})


class DependencyNearDaysSetting(LiveBrowserCase):
    """Settings › Early warnings: the dependency signal's switch and its "near" days, saved to settings.json and applied to the flags."""

    @classmethod
    def load(cls, v):
        d = dep_vault()                                   # (builds its own vault; copy its data into this one)
        try:
            import shutil as sh
            sh.copy2(d.root / "system/tracker.db", v.root / "system/tracker.db")
        finally:
            d.cleanup()

    def test_the_near_days_are_set_in_settings_and_change_the_warnings(self):
        b = self.b
        licences = next(r["id"] for r in self.v.rows("raid") if r["description"] == "Licences purchased")   # overdue; its milestone is 37 days off
        b.eval("go('settings','warnings')")
        b.wait("document.querySelector('[data-wk=\"dependency.near_days\"]')")          # BL-320: Early warnings are in Advanced
        label = b.eval("document.querySelector('[data-wk=\"dependency.near_days\"]').closest('.srow').textContent.replace(/\\s+/g,' ').trim()")
        self.assertIn("Overdue counts when the milestone is within (days)", label)
        self.assertEqual(b.eval("document.querySelector('[data-wk=\"dependency.near_days\"]').value"), "14")
        self.assertIn("Dependency due after what it blocks", b.eval("document.getElementById('warnSettings').textContent"))
        self.assertFalse(b.eval("WARNS().some(w=>w.id===%s && w.sig==='dependency')" % json.dumps(licences)))
        b.eval("(()=>{ const i=document.querySelector('[data-wk=\"dependency.near_days\"]'); i.value=40; i.dispatchEvent(new Event('change',{bubbles:true})); })()")
        b.wait("WARNS().some(w=>w.id===%s && w.sig==='dependency')" % json.dumps(licences), 15)               # the flags updated at once
        saved = json.loads((self.v.root / "system/config/settings.json").read_text())["warnings"]["dependency"]
        self.assertEqual(saved, {"on": True, "near_days": 40})
        b.eval("(()=>{ const i=document.querySelector('[data-wk=\"dependency.on\"]'); i.checked=false; i.dispatchEvent(new Event('change',{bubbles:true})); })()")
        b.wait("!WARNS().some(w=>w.sig==='dependency')", 15)                                                  # switched off: none
        self.assertIs(json.loads((self.v.root / "system/config/settings.json").read_text())["warnings"]["dependency"]["on"], False)


if __name__ == "__main__":
    unittest.main()
