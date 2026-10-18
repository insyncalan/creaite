"""#226 (with #219): the weekly report's HTML and PDF export is the sheet's own "Show as exported" page (real Chrome, the real live
server; no Claude runs). One test per acceptance check of dev/sprints/export-226-html-pdf-brief.md, named test_cNN_*.

  1 header, logos, no duplicate title     5 tables: Response, chips, Late, empty sentence   9 dates DD-MM-YYYY
  2 health block, strip, last week        6 headings, text, no empty heading               10 light print theme, A4
  3 At a glance strip                     7 left out stays out (also in the source)        11 the PDF equals the HTML
  4 milestones: picture, gap, table       8 client report, server re-check                 12 fallback, told it is plain
  + test_every_section_matches_the_screen: each section's text and box against Show as exported (the #219 done-when)

Run: python3 dev/tests/test_report_export_page.py      (Chrome tier; skipped without Chrome)
"""
import json
import re
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts" / "vendor"))
from live_browser import LiveBrowserCase  # noqa: E402
import test_weekly_report_view as twrv  # noqa: E402   (the module, so its own tests are not collected here)

ISO = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
SECTIONS_JS = ("(()=>{const o={};document.querySelectorAll('.page>section[data-id]').forEach(s=>{o[s.dataset.id]="
               "{text:s.innerText.replace(/\\s+/g,' ').trim(),w:s.offsetWidth,h:s.offsetHeight}});return o})()")


class ExportPage(LiveBrowserCase):
    """The demo weekly report (ABC) with a firm and a client logo, saved as a draft and opened at #weekly=ABC."""

    @classmethod
    def load(cls, v):
        twrv.WeeklyReportView.load(v)

    def setUp(self):
        super().setUp()
        self.b.eval("go('weekly',{code:'ABC'})")
        self.b.wait("document.querySelector('#v-reporting section[data-id=current_state]')", 20)
        d = self.aeval("api('/api/report/draft',{kind:'weekly',code:'ABC'})")
        self.assertTrue(self.aeval("api('/api/report/save',{doc:%s,base_version:null})" % json.dumps(d["doc"]))["ok"])
        self.b.eval("go('weekly',{code:'ABC'})")
        self.b.wait("document.querySelector('#v-reporting section[data-id=current_state]')", 20)

    def ev(self, js):
        return self.b.eval(js)

    def aeval(self, expr, timeout=20):
        """Await a promise in the dashboard and return its value."""
        self.b.eval("window.__r=undefined;Promise.resolve(%s).then(v=>{window.__r={v:v}},e=>{window.__r={e:String(e)}})" % expr)
        self.b.wait("window.__r!==undefined", timeout)
        r = self.b.eval("window.__r")
        self.assertNotIn("e", r, r)
        return r["v"]

    def set_dark(self):
        self.b.eval("document.documentElement.dataset.theme='dark'")

    def show_exported(self):
        """Press Show as exported and wait for it."""
        self.ev("document.querySelector('#v-reporting #hubExp').click()")
        self.b.wait("document.querySelector('#v-reporting .sheet-exported') && !document.querySelector('#v-reporting .wr-eye')", 10)
        time.sleep(0.4)           # the timeline fits itself to its box after the first draw

    def screen(self):
        """{section id: text and box} of the exported view on screen."""
        return self.ev(SECTIONS_JS.replace("document.querySelectorAll('.page", "document.querySelectorAll('#v-reporting .page"))

    def drafts(self, pattern):
        return sorted((self.v.root / "system/staging/drafts").glob(pattern))

    def saved(self):
        """Every file in drafts and in the project's Reports folder (#220 files an export there, not in drafts)."""
        return set(self.drafts("*")) | set((self.v.root / "projects").glob("ABC*/reports/*"))

    def export(self, fmt):
        """Press Export > fmt as the person does; returns the file the export wrote. #220: an unfiled report's HTML meets its reserved
        filing name, so the clash dialog opens and its default (Add a number) is taken."""
        before = self.saved()
        self.ev("document.querySelector('#v-reporting #hubExport').click()")
        self.b.wait("document.querySelector('[role=menu] [role=menuitem]')", 5)
        label = {"html": "HTML", "pdf": "PDF", "docx": "Word"}[fmt]
        self.ev("[...document.querySelectorAll('[role=menu] [role=menuitem]')].find(x=>x.textContent.includes(%r)).click()" % label)
        end = time.time() + 40
        self.b.wait("document.querySelector('[data-hubpick=internal]')", 5)       # #221: the hub asks which report after the format
        self.ev("document.querySelector('[data-hubpick=internal]').click()")
        while time.time() < end:
            if self.ev("!!document.querySelector('#exportClashDlg[open]')"):
                self.ev("document.querySelector('#exportClashGo').click()")
            new = [p for p in self.saved() if p not in before and p.suffix == "." + fmt]
            if new:
                time.sleep(0.5)
                return new[0]
            time.sleep(0.2)
        self.fail(f"no {fmt} export was written")

    def open_file(self, path, width=1400):
        """The exported file opened on its own in a second Chrome."""
        from cdp import Browser
        b = Browser(width, 1000)
        self.addCleanup(b.close)
        b.goto(Path(path).resolve().as_uri())
        time.sleep(0.4)
        return b

    def exported_html(self):
        """Show as exported on screen, export HTML, open it: (the screen's sections, the file's Chrome, the file's text)."""
        self.show_exported()
        screen = self.screen()
        f = self.export("html")
        return screen, self.open_file(f), f.read_text(encoding="utf-8")

    # ── 1 ─────────────────────────────────────────────────────────────────────────────────────────────────────────
    def test_c01_header_logos_one_title(self):
        _, b, src = self.exported_html()
        self.assertEqual(b.eval("document.querySelector('.wr-eb').textContent"), "Weekly report · Internal")
        self.assertEqual(b.eval("document.querySelector('.wr-pn').textContent"), "Example Programme")
        self.assertRegex(b.eval("document.querySelector('.wr-wk').textContent"), r"^Week ending \w+day \d+ \w+ \d{4}")
        self.assertEqual(b.eval("document.querySelectorAll('.wr-logos img').length"), 2, "the firm's and the client's logo")
        self.assertTrue(b.eval("[...document.querySelectorAll('.wr-logos img')].every(i=>i.src.startsWith('data:image/')&&i.naturalWidth>0)"))
        self.assertEqual(b.eval("[...document.querySelectorAll('h1,h2,h3')].filter(h=>h.offsetParent&&/^\\s*Weekly report\\s*$/i.test(h.textContent)).length"), 0,
                         "no second 'Weekly report' title")
        self.assertEqual(b.eval("[...document.querySelectorAll('h1,h2,h3,h4')].filter(h=>h.offsetParent&&!h.textContent.trim()).length"), 0,
                         "no empty heading")
        self.assertEqual(b.eval("[...document.querySelectorAll('h2')].filter(h=>/^\\s*summary\\s*$/i.test(h.textContent)).length"), 0,
                         "no empty Summary heading (the report's summary is empty)")
        self.assertNotIn("<script", src)

    # ── 2 ─────────────────────────────────────────────────────────────────────────────────────────────────────────
    def test_c02_health_block_strip_and_last_week(self):
        self.show_exported()
        screen_flag = self.ev("document.querySelector('#v-reporting .wr-flag').textContent")
        screen_weeks = self.ev("document.querySelectorAll('#v-reporting .wr-trend i').length")
        f = self.export("html")
        b = self.open_file(f)
        self.assertEqual(b.eval("document.querySelector('.wr-flag').textContent"), screen_flag)
        self.assertNotEqual(b.eval("getComputedStyle(document.querySelector('.wr-flag')).backgroundColor"), "rgba(0, 0, 0, 0)")
        self.assertEqual(b.eval("document.querySelectorAll('.wr-trend i').length"), screen_weeks, "the strip, a bar a week")
        self.assertGreaterEqual(screen_weeks, 2)
        self.assertEqual(b.eval("document.querySelectorAll('.wr-tlbl span').length"), 2, "its two dates")
        self.assertRegex(b.eval("document.querySelector('.wr-last').textContent"), r"^Last week: \w[\w ]+ \(\d\d-\d\d\)$")
        self.assertTrue(b.eval("document.querySelector('.wr-why').textContent.trim().length>5"), "the reason")
        self.assertEqual(b.eval("getComputedStyle(document.body).printColorAdjust"), "exact", "colour is kept in print")

    # ── 3 ─────────────────────────────────────────────────────────────────────────────────────────────────────────
    def test_c03_at_a_glance_strip(self):
        self.show_exported()
        want = self.ev("[...document.querySelectorAll('#v-reporting .wr-stat')].map(s=>s.innerText.replace(/\\s+/g,' ').trim())")
        red = self.ev("getComputedStyle(document.querySelector('#v-reporting .wr-stat .n.r')).color")
        b = self.open_file(self.export("html"))
        self.assertEqual(b.eval("[...document.querySelectorAll('.wr-stat')].map(s=>s.innerText.replace(/\\s+/g,' ').trim())"), want)
        self.assertEqual(b.eval("document.querySelectorAll('.wr-stats').length"), 1, "one strip, not loose boxes")
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('.wr-stat .n.r')).color"), red, "the overdue figure is red")

    # ── 4 ─────────────────────────────────────────────────────────────────────────────────────────────────────────
    def test_c04_milestones_picture_gap_and_table(self):
        self.show_exported()
        b = self.open_file(self.export("html"))
        for cls in (".wr-tltoday", ".wr-slip", ".wr-tltx", ".wr-tlline"):
            self.assertTrue(b.eval("!!document.querySelector('svg.wr-tl %s')" % cls), cls)
        self.assertTrue(b.eval("document.querySelector('svg.wr-tl').getBoundingClientRect().height>40"), "a picture with a size")
        self.assertEqual(b.eval("[...document.querySelectorAll('[data-id=milestones] th')].map(t=>t.textContent)"),
                         ["Milestone", "Agreed", "Expected", "Progress", "State"])
        gap = b.eval("document.querySelector('[data-id=milestones] .wr-tbl').getBoundingClientRect().top"
                     "-document.querySelector('[data-id=milestones] .wr-tlwrap').getBoundingClientRect().bottom")
        self.assertAlmostEqual(gap, 16, delta=1, msg="a 16 px gap between the picture and the table")
        cells = b.eval("[...document.querySelectorAll('[data-id=milestones] tbody tr')].map(r=>[...r.cells].map(c=>c.textContent))")
        self.assertTrue(cells)
        for row in cells:
            for c in (row[1], row[2]):
                self.assertTrue(re.match(r"^(\d\d-\d\d-\d{4}( \(\+\d+\))?|achieved \d\d-\d\d-\d{4})$", c), c)
        self.assertTrue(any("(+14)" in r[2] for r in cells), "the slip is shown")
        self.assertTrue(any(r[2].startswith("achieved ") for r in cells), "a done milestone reads achieved <date>")
        self.assertTrue(b.eval("document.querySelectorAll('[data-id=milestones] .wr-st').length")>=2, "State chips")

    # ── 5 ─────────────────────────────────────────────────────────────────────────────────────────────────────────
    def test_c05_tables_columns_chips_late_and_empty(self):
        self.show_exported()
        b = self.open_file(self.export("html"))
        self.assertEqual(b.eval("[...document.querySelectorAll('[data-id=risks] th')].map(t=>t.textContent)"),
                         ["ID", "Risk or issue", "Priority", "Owner", "Response"])
        self.assertTrue(b.eval("document.querySelectorAll('[data-id=risks] .wr-st').length")>=1, "priority chips")
        self.assertIn("rgb", b.eval("getComputedStyle(document.querySelector('[data-id=risks] .wr-st')).backgroundColor"))
        self.assertEqual(b.eval("[...document.querySelectorAll('[data-id=overdue] th')].map(t=>t.textContent)"),
                         ["ID", "Action", "Owner", "Due", "Late"])
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('[data-id=overdue] .late')).color"),
                         self.ev("(()=>{const e=document.createElement('span');e.className='late';"
                                 "document.querySelector('#v-reporting .page').append(e);const c=getComputedStyle(e).color;e.remove();return c})()"))
        self.assertTrue(re.search(r"\d+ days?", b.eval("document.querySelector('[data-id=overdue] .late').textContent")))
        self.assertEqual(b.eval("document.querySelector('[data-id=decisions]').innerText.replace(/\\s+/g,' ')"),
                         self.ev("document.querySelector('#v-reporting [data-id=decisions]').innerText.replace(/\\s+/g,' ')"))
        self.assertIn("Nothing is needed from anyone this week.", b.eval("document.querySelector('[data-id=asks]').textContent"))
        self.assertEqual(b.eval("document.querySelectorAll('[data-id=asks] table').length"), 0, "an empty table is its sentence, not a header row")

    # ── 6 ─────────────────────────────────────────────────────────────────────────────────────────────────────────
    def test_c06_headings_and_text(self):
        self.show_exported()
        want = self.ev("(()=>{const h=document.querySelector('#v-reporting [data-id=this_week] h2');return getComputedStyle(h,'::before').width})()")
        b = self.open_file(self.export("html"))
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('[data-id=this_week] h2'),'::before').width"), want)
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('[data-id=this_week] h2')).textTransform"), "uppercase")
        self.assertEqual(b.eval("[...document.querySelectorAll('h1,h2,h3,h4')].filter(h=>!h.textContent.trim()).length"), 0)
        self.assertTrue(b.eval("!!document.querySelector('[data-id=this_week] ul')"), "a list is a list")
        self.assertIn("Delivery plan", b.eval("document.querySelector('[data-id=current_state]').textContent"),
                      "the Current state's picture line is kept, as on screen, never dropped silently")

    # ── 7 ─────────────────────────────────────────────────────────────────────────────────────────────────────────
    def test_c07_left_out_stays_out_of_the_file_and_its_source(self):
        d = self.aeval("api('/api/report/draft',{kind:'weekly',code:'ABC'})")
        doc = d["doc"]
        sec = {s["id"]: s for s in doc["sections"]}
        gone = sec["risks"]["rows"][0]
        gone_text = [v for k, v in gone["cells"].items() if k not in ("id", "priority") and isinstance(v, str) and len(v) > 12][0]
        gone["shown"] = False
        sec["decisions"]["hidden"] = True
        sec["glance"]["figures"][0]["shown"] = False
        keep = sec["milestones"]["data"].get("milestones") or []
        sec["milestones"]["data"]["milestones"] = keep[:1]
        saved = self.aeval("api('/api/report/save',{doc:%s,base_version:%s})" % (json.dumps(doc), d["version"] or "null"))
        self.assertTrue(saved["ok"], saved)
        self.b.eval("go('weekly',{code:'ABC'})")
        self.b.wait("document.querySelector('#v-reporting section[data-id=current_state]')", 20)
        self.show_exported()
        f = self.export("html")
        src = f.read_text(encoding="utf-8")
        self.assertNotIn(gone_text, src)
        self.assertNotIn('data-id="decisions"', src)
        self.assertNotIn("Go-live moves two weeks", src)
        self.assertNotIn("creaite-data", src)
        self.assertNotRegex(src, r"<script|onclick=|onerror=|<button|<input|contenteditable")
        b = self.open_file(f)
        self.assertEqual(b.eval("document.querySelectorAll('[data-id=risks] tbody tr').length"),
                         len(sec["risks"]["rows"]) - 1)
        self.assertEqual(b.eval("document.querySelectorAll('.wr-stat').length"), self.ev("document.querySelectorAll('#v-reporting .wr-stat').length"))
        self.assertEqual(b.eval("document.querySelectorAll('[data-id=milestones] tbody tr').length"), len(keep[:1]))

    # ── 9 ─────────────────────────────────────────────────────────────────────────────────────────────────────────
    def test_c09_dates_are_dd_mm_yyyy(self):
        self.show_exported()
        f = self.export("html")
        b = self.open_file(f)
        for sid in ("header", "health", "glance", "milestones", "asks", "risks", "overdue"):
            part = b.eval("(document.querySelector('[data-id=%s]')||{innerText:''}).innerText" % sid)
            self.assertIsNone(ISO.search(part), f"{sid}: {ISO.search(part)}")
        text = b.eval("document.body.innerText")
        self.assertIsNone(ISO.search(re.search(r"<title>(.*?)</title>", f.read_text(encoding="utf-8")).group(1)))
        self.assertRegex(text, r"\b\d\d-\d\d-\d{4}\b")
        self.assertRegex(text, r"Week ending \w+day \d+ \w+ \d{4}", "the long date stays as written")

    # ── 10 ────────────────────────────────────────────────────────────────────────────────────────────────────────
    def test_c10_fixed_light_print_theme_on_a4(self):
        self.set_dark()
        self.show_exported()
        f = self.export("html")
        b = self.open_file(f)
        src = f.read_text(encoding="utf-8")
        paper = b.eval("getComputedStyle(document.querySelector('.page')).backgroundColor")
        self.assertTrue(all(int(x) >= 240 for x in re.findall(r"\d+", paper)[:3]), f"a light paper, not the dark theme's: {paper}")
        self.assertNotIn("rgb(17, 21, 24)", b.eval("getComputedStyle(document.body).backgroundColor"), "no dark theme leak")
        self.assertIn("light", re.search(r"<html[^>]*>", src).group(0))
        self.assertRegex(src, r"@page\s*\{[^}]*size:\s*A4")
        self.assertIn(b.eval("getComputedStyle(document.querySelector('.page>section')).breakInside"), ("avoid", "avoid-page"))
        self.assertAlmostEqual(b.eval("document.querySelector('.page').offsetWidth"), 794, delta=2, msg="A4 wide")
        self.assertEqual(b.eval("document.querySelectorAll('[data-id=milestones] .wr-tlwrap, [data-id=milestones] .wr-tbl').length"), 2,
                         "picture and table in one section, kept together")

    # ── 11 ────────────────────────────────────────────────────────────────────────────────────────────────────────
    def test_c11_pdf_equals_html_apart_from_page_breaks(self):
        import difflib
        import pypdf
        self.show_exported()
        h = self.export("html")
        p = self.export("pdf")
        self.assertEqual(p.read_bytes()[:5], b"%PDF-")
        pdf = "".join(pg.extract_text() for pg in pypdf.PdfReader(str(p)).pages)
        html = self.open_file(h).eval("document.body.innerText")
        a, c = re.sub(r"\s+", "", html), re.sub(r"\s+", "", pdf)
        from collections import Counter
        self.assertEqual(Counter(a), Counter(c), "the same characters (a picture's labels may come in another order)")
        self.assertGreater(difflib.SequenceMatcher(None, a, c, autojunk=False).ratio(), 0.94)
        for word in ("Example Programme", "Off track".upper(), "Risks and issues".upper(), "Milestone"):
            self.assertIn(re.sub(r"\s+", "", word), c)
        self.assertEqual(len(pypdf.PdfReader(str(p)).pages) >= 1, True)

    # ── 12 ────────────────────────────────────────────────────────────────────────────────────────────────────────
    def test_c12_without_a_page_the_python_renderer_still_makes_a_file_and_says_so(self):
        self.show_exported()
        d = self.aeval("api('/api/report/draft',{kind:'weekly',code:'ABC'})")
        s = self.aeval("api('/api/report/save',{doc:%s,base_version:%s})" % (json.dumps(d["doc"]), d["version"] or "null"))
        self.assertTrue(s["ok"], s)
        r = self.aeval("api('/api/report/export',{kind:'weekly',code:'ABC',week_ending:%s,fmt:'html',on_clash:'number'})" % json.dumps(d["doc"]["date"]))
        self.assertTrue(r["ok"], r)
        self.assertTrue(r.get("plain"), "told it is the plain version")
        self.assertIn("plain version", r["message"])
        self.assertTrue((self.v.root / r["path"]).is_file())
        self.assertNotIn("wr-flag", (self.v.root / r["path"]).read_text(encoding="utf-8"))

    def test_c12b_a_page_that_fails_the_server_check_gives_the_plain_file_without_the_leak(self):
        """Check 7 and 8's server side: a posted page is checked against the saved report and the tracker, never trusted."""
        d = self.aeval("api('/api/report/draft',{kind:'weekly',code:'ABC'})")
        doc = d["doc"]
        sec = {s["id"]: s for s in doc["sections"]}
        sec["decisions"]["hidden"] = True
        sec["risks"]["rows"][0]["shown"] = False
        s = self.aeval("api('/api/report/save',{doc:%s,base_version:%s})" % (json.dumps(doc), d["version"] or "null"))
        self.assertTrue(s["ok"], s)
        css = ".page{color:red}"
        pages = {
            "a hidden section": '<div id="v-weekly"><div class="page"><section data-id="decisions"><h2>Decisions</h2>'
                                '<p>Go-live moves two weeks</p></section></div></div>',
            "a hidden row's words, under a shown section": '<div id="v-weekly"><div class="page"><section data-id="health"><h2>Health</h2>'
                                                          '<p>Data access delayed &rarr; UAT slips</p></section></div></div>',
            "a script": '<div id="v-weekly"><div class="page"><section data-id="health"><h2>Health</h2><script>alert(1)</script>'
                        '<p onclick="alert(2)">fine</p></section></div></div>',
        }
        for what, html in pages.items():
            r = self.aeval("api('/api/report/export',{kind:'weekly',code:'ABC',week_ending:%s,fmt:'html',on_clash:'number',page:%s})"
                           % (json.dumps(doc["date"]), json.dumps({"html": html, "css": css, "palette": "creaite", "version": s["version"]})))
            self.assertTrue(r["ok"], r)
            text = (self.v.root / r["path"]).read_text(encoding="utf-8")
            for gone in ("alert(", "Go-live moves two weeks", "Data access delayed"):
                self.assertNotIn(gone, text, what)
            if what != "a script":
                self.assertTrue(r.get("plain"), what)
                self.assertIn("plain_why", r, what)
            else:                       # a script is stripped; the rest of the page is fine and is used
                self.assertFalse(r.get("plain"), r)
                self.assertIn("fine", text)

    # ── #219 / all of 1 to 6 together ─────────────────────────────────────────────────────────────────────────────
    def test_every_section_matches_the_screen(self):
        screen, b, _ = self.exported_html()
        got = b.eval(SECTIONS_JS)
        self.assertEqual(list(got), list(screen), "the same sections in the same order")
        for sid, want in screen.items():
            self.assertEqual(got[sid]["text"], want["text"], f"{sid}: the words")
            self.assertAlmostEqual(got[sid]["w"], want["w"], delta=2, msg=f"{sid}: width")
            if sid != "milestones":          # its picture is fitted to the page in a file
                self.assertAlmostEqual(got[sid]["h"], want["h"], delta=4, msg=f"{sid}: height")


if __name__ == "__main__":
    unittest.main()
