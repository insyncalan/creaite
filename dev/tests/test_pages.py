"""Dashboard pages (BL-87, BL-88, BL-89, BL-95, BL-91, BL-90 part 1), part 1 of 3 (the Files page and the Files search; the fixture is in pages_support.py).

Run: python3 dev/tests/test_pages.py   (the page tests need Google Chrome; they are skipped otherwise)

Everything is fictional and temporary. The data tests run in the default layout and in a temporary OneDrive-style projects
root (the BL-85 `locations` setting, resolved against a fake home folder); the page tests drive a real headless Chrome
against the real live server, as a person would.
"""
import json
import subprocess
import sys
import tempfile
import time
import unittest
import unittest.mock
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import CHROME, d, populate  # noqa: E402
from test_onedrive_projects import OneDriveCase, touch  # noqa: E402
from test_insight import chrome  # noqa: E402
from test_tracker import ABC, Vault  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from pages_support import (  # noqa: E402
    DEFAULT_REPORTS,
    CONTRAST_JS,
    THEMES,
    resize,
    theme,
)


# ===== BL-87: Files page, the real report folders =====


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
        self.assertEqual(o[0], ["archived", "at", "files", "inbox"])        # BL-331: the files BL-03 archived, for Files' Archived
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
        touch(self.eng("ABC", "99 Archive", "Old plan.docx"))
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


class FilesLiveBase(LiveBrowserCase):
    """A live server and a headless Chrome; files are added to the vault from outside the dashboard."""

    @classmethod
    def load(cls, v):
        populate(v)
        (v.root / DEFAULT_REPORTS / f"{d(-15)} Client report.docx").unlink()     # populate's own report is dated from today: leave the fixed dates below the newest
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
        b.eval("FF.type='docx'; renderFiles()")
        b.eval("FOPEN.add('ABC'); renderFiles()")
        b.click("#filesTbl tbody tr[data-fp] td:nth-child(2)")
        selected = b.eval("FSELFILE")
        self.assertTrue(selected)
        b.eval("FSEL={p:'ABC',f:'reports',sub:'Weekly',quick:'all'}; renderFiles()")
        b.eval("document.getElementById('v-files').scrollTop=120")
        scroll = b.eval("document.getElementById('v-files').scrollTop")
        touch(self.v.root / DEFAULT_REPORTS / "2026-10-20 Weekly report.docx")
        b.eval("document.getElementById('filesRefresh').click()")     # #192: Refresh is on the pills' line, so a real click would scroll up to it
        b.wait("[...document.querySelectorAll('#filesTbl a')].some(a=>a.textContent.startsWith('2026-10-20'))")
        self.assertEqual(b.eval("FF.type"), "docx")                                               # the filter
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
        self.assertEqual(sorted(body), ["archived", "at", "files", "inbox", "ok"])                          # not the dashboard's whole data
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
        self.assertNotIn("documents", self.b.eval("[...document.querySelectorAll('#tree .l2')].map(b=>b.textContent.replace(/\\d+$/,''))"))
        self.b.click('#tree .l3[data-s="Steerco"]')                                               # #192: the folder is in the tree
        self.assertEqual(self.rows(), ["Steerco pack.pptx"])
        self.b.click('#fquick [data-q="all"]')                                                    # the All files pill: back to all files
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
            resize(self.b, width, 900)
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
        resize(b, 700, 900)
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


if __name__ == "__main__":
    unittest.main()
