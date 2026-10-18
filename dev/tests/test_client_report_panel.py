"""H3 of the Reporting hub (#221): the Client report settings panel and the same setting in Settings > Projects, in a real browser against
the live server.

Run: python3 dev/tests/test_client_report_panel.py   (needs Google Chrome; skipped otherwise)

Brief: dev/sprints/reporting-hub-brief.md section 6, Rounds 4, 8, 9 and "For Alan answered". The hub's cog (H1) calls
`openClientReport(code)`; the panel here is what it opens. Every control saves at once into the project's CLAUDE.md.
"""
import base64
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_dashboard  # noqa: E402
from live_browser import TEST_PALETTES, LiveBrowserCase  # noqa: E402
from test_tracker import ABC  # noqa: E402

PANEL = "#crPanel"
MAKE_PNG = """(async () => {
  const c = document.createElement('canvas'); c.width = 200; c.height = 100; const g = c.getContext('2d');
  g.fillStyle = '#c00'; g.fillRect(80, 30, 40, 40);                       /* artwork 40 x 40 in a transparent 200 x 100 picture */
  const blob = await new Promise(r => c.toBlob(r, 'image/png'));
  window.LOGO = new File([blob], 'client.png', {type: 'image/png'}); return blob.size; })()"""


class ClientReportPanel(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 1000

    @classmethod
    def load(cls, v):
        test_dashboard.populate(v)
        v.run(script="build_dashboard.py")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.original = (cls.v.root / ABC / "CLAUDE.md").read_text()

    @property
    def memory(self):
        return self.v.root / ABC / "CLAUDE.md"

    def text(self):
        return self.memory.read_text()

    def setUp(self):
        super().setUp()
        self.memory.write_text(self.original)                                                          # an existing project: no setting lines
        logos = self.v.root / "system/branding/logos"
        logos.mkdir(parents=True, exist_ok=True)
        for f in logos.glob("*"):
            f.unlink()
        self.b.reload("typeof go==='function' && LIVE")

    def open_panel(self):
        self.b.eval("openClientReport('ABC')")
        self.b.wait(f"!!document.querySelector('{PANEL}')")

    def line(self, label):
        m = re.search(r"\*\*" + re.escape(label) + r":\*\*[ \t]*([^\n]*)", self.text())
        return m.group(1).strip() if m else None

    def wait_line(self, label, want):
        import time
        end = time.time() + 8
        while time.time() < end and (self.line(label) or "").split()[:1] != want.split()[:1]:
            time.sleep(0.1)
        self.assertEqual((self.line(label) or "").split("_")[0].strip().split("   ")[0], want)

    # ----- the panel as the mockup draws it

    def test_the_panel_has_the_switch_the_settings_and_the_three_tiles(self):
        b = self.b
        self.open_panel()
        self.assertEqual(b.eval(f"document.querySelector('{PANEL}').getAttribute('aria-label')"), "Client report settings")
        self.assertEqual(b.eval("document.querySelector('#cfgOn').checked"), True)                    # existing project: on
        self.assertIn("This project needs a separate client report", b.eval("document.querySelector('.cfgsw').textContent"))
        self.assertEqual(b.eval("[...document.querySelectorAll('#cfgRh option')].map(o=>o.value)"), ["Weekly", "Fortnightly", "Monthly"])
        self.assertEqual(b.eval("document.querySelector('#cfgRh').value"), "Fortnightly")
        self.assertEqual(b.eval("document.querySelector('#cfgNm').value"), "Example Client Ltd")
        tiles = b.eval("[...document.querySelectorAll('.cfglogo')].map(t=>[t.dataset.kind,t.querySelector('.cfgname').textContent,"
                       "t.querySelector('.mark').textContent.trim(),t.querySelector('[data-logo-tick]').checked,t.querySelector('[data-logo-tick]').disabled])")
        self.assertEqual([(t[0], t[3], t[4]) for t in tiles], [("firm", True, True), ("client", True, False), ("partner", True, False)])
        self.assertEqual([t[2] for t in tiles], ["F", "C", "P"])
        self.assertIn("Always shown", tiles[0][1])
        keep = b.eval("document.querySelector('#cfgKeep').textContent")
        self.assertIn("every future report", keep)
        self.assertIn("turning it off deletes nothing", keep)

    def test_the_panels_selects_and_inputs_use_the_field_colours_with_4_5_to_1_contrast(self):
        """Gate fix (Team Cap's walk): in the dark theme the How often select was pale on white. Every select and text input in the
        panel takes the app's field ground and ink (tokens), so text meets 4.5:1 in light and dark, in both palettes."""
        b = self.b
        self.open_panel()
        js = """(()=>{ const P=s=>{ const m=s.match(/rgba?\\(([^)]+)\\)/); if(m){ const p=m[1].split(/[ ,\\/]+/).filter(Boolean).map(Number); return [p[0],p[1],p[2],p.length>3?p[3]:1]; }
            const c=s.match(/color\\(srgb ([^)]+)\\)/); if(c){ const p=c[1].split(/[ \\/]+/).filter(Boolean).map(Number); return [p[0]*255,p[1]*255,p[2]*255,p.length>3?p[3]:1]; } return [0,0,0,0]; };
          const lum=c=>{ const f=v=>{ v/=255; return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4); }; return 0.2126*f(c[0])+0.7152*f(c[1])+0.0722*f(c[2]); };
          const out=[]; for(const el of document.querySelectorAll('#crPanel select, #crPanel input[type=text], #crPanel input.pkdt')){
            const cs=getComputedStyle(el), fg=P(cs.color); let bg=[0,0,0,0];
            for(let e=el;e;e=e.parentElement){ const c=P(getComputedStyle(e).backgroundColor); if(c[3]>0){ bg=c; break; } }
            const a=lum(fg), l=lum(bg); out.push([el.id||el.tagName, (Math.max(a,l)+0.05)/(Math.min(a,l)+0.05), bg[3]]); }
          return out; })()"""
        seen = 0
        for palette in TEST_PALETTES:
            for mode in ("light", "dark"):
                b.eval(f"document.documentElement.dataset.palette='{palette}'; document.documentElement.dataset.theme='{mode}'")
                b.pump(0.2)
                rows = b.eval(js)
                self.assertTrue(any(r[0] == "cfgRh" for r in rows), "the How often select is checked")
                for name, ratio, alpha in rows:
                    seen += 1
                    self.assertEqual(alpha, 1, f"{name} has no opaque field ground ({palette} {mode})")
                    self.assertGreaterEqual(ratio, 4.5, f"{name} text is {ratio:.2f}:1 ({palette} {mode})")
        self.assertGreaterEqual(seen, 8)

    def test_every_control_is_named(self):
        names = self.b
        self.open_panel()
        bad = names.eval("[...document.querySelectorAll('#crPanel input:not([hidden]),#crPanel select,#crPanel button')]"
                         ".filter(e=>!(e.getAttribute('aria-label')||(e.labels&&e.labels.length)||e.textContent.trim())).length")
        self.assertEqual(bad, 0)

    # ----- storage and persistence

    def test_off_is_stored_on_the_project_and_deletes_nothing(self):
        b = self.b
        report = self.v.root / ABC / "reports/2026-10-09 Client report - Example Programme.docx"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_bytes(b"r")
        before = self.text()
        self.open_panel()
        b.click("#cfgOn")
        b.wait("!document.querySelector('#cfgBody') && !!document.querySelector('#cfgOff')")
        self.wait_line("Client report", "off")
        self.assertEqual(b.eval("clientReportOn('ABC')"), False)
        self.assertIn("**Client report rhythm:** fortnightly", self.text())                          # beside the rhythm, which is untouched
        self.assertEqual(self.text().replace(re.search(r"- \*\*Client report:\*\* off\n", self.text()).group(0), ""), before)
        self.assertTrue(report.exists())
        log = (self.v.root / "system/config/settings-log.jsonl").read_text()
        self.assertIn('"key":"client_report.ABC"', log)
        self.assertTrue(list((self.v.root / "system/backups/files").glob("ABC-CLAUDE-*.md")))        # a copy first
        b.click("#cfgOn")                                                                             # turning it on restores the client side
        b.wait("!!document.querySelector('#cfgBody')")
        self.wait_line("Client report", "on")
        self.assertEqual(b.eval("clientReportOn('ABC')"), True)
        self.assertTrue(report.exists())

    def test_it_is_still_off_after_a_reload(self):
        self.open_panel()
        self.b.click("#cfgOn")
        self.wait_line("Client report", "off")
        self.b.reload("typeof go==='function' && LIVE")
        self.assertEqual(self.b.eval("clientReportOn('ABC')"), False)                                  # persistent, no per-week question

    def test_cog_label_names_the_state(self):
        b = self.b
        self.assertEqual(b.eval("clientReportCogLabel('ABC')"), "Client report settings: on")
        self.open_panel()
        b.click("#cfgOn")
        self.wait_line("Client report", "off")
        self.assertEqual(b.eval("clientReportCogLabel('ABC')"), "Client report settings: off")

    def test_how_often_name_reminder_and_logo_ticks_are_saved(self):
        b = self.b
        self.open_panel()
        b.eval("(()=>{const s=document.querySelector('#cfgRh'); s.value='Weekly'; s.dispatchEvent(new Event('change',{bubbles:true}))})()")
        self.wait_line("Client report rhythm", "weekly")
        b.eval("(()=>{const i=document.querySelector('#cfgNm'); i.value='  Northwind   Traders '; i.dispatchEvent(new Event('change',{bubbles:true}))})()")
        self.wait_line("Client / partner", "Northwind Traders")
        b.click("#cfgRem")
        self.wait_line("Client report reminder", "off")
        b.click("[data-logo-tick=partner]")
        self.wait_line("Client report logos", "firm, client")
        self.assertEqual(b.eval("clientLogosOn('ABC')"), ["firm", "client"])
        b.click("[data-logo-tick=client]")
        self.wait_line("Client report logos", "firm")
        self.assertEqual(b.eval("document.querySelector('[data-logo-tick=firm]').checked"), True)       # the firm's stays

    # ----- the same setting in Settings > Projects

    def test_settings_projects_and_the_panel_are_one_setting(self):
        b = self.b
        b.eval("go('settings','people')")
        b.wait("!!document.querySelector('[data-crsw=ABC]')")
        self.assertEqual(b.eval("document.querySelector('[data-crsw=ABC]').checked"), True)
        self.assertIn("this project needs a separate client report", (b.eval("(e=>e.getAttribute('aria-label')||[...(e.getAttribute('aria-labelledby')||'').split(' ')].map(i=>document.getElementById(i)?.textContent).join(' '))(document.querySelector('[data-crsw=ABC]'))") or "").lower())
        b.click("[data-crsw=ABC]")
        self.wait_line("Client report", "off")
        self.open_panel()                                                                              # the panel shows what Settings set
        self.assertEqual(b.eval("document.querySelector('#cfgOn').checked"), False)
        b.click("#cfgOn")
        self.wait_line("Client report", "on")
        b.eval("go('settings','people')")
        b.wait("!!document.querySelector('[data-crsw=ABC]')")
        self.assertEqual(b.eval("document.querySelector('[data-crsw=ABC]').checked"), True)

    # ----- when it is off

    def test_off_the_reports_page_lists_only_the_internal_report(self):
        b = self.b
        b.eval("go('reports')")
        b.wait("!!document.querySelector('#v-reports tbody tr')")
        self.assertEqual(b.eval("document.querySelector('[data-rpproj=ABC] .rp-cl')!==null"), True)
        self.open_panel()
        b.click("#cfgOn")
        self.wait_line("Client report", "off")
        b.eval("go('reports')")
        b.wait("!!document.querySelector('#v-reports tbody tr')")
        self.assertEqual(b.eval("document.querySelector('[data-rpproj=ABC] .rp-cl')"), None)
        self.assertIn("No client report", b.eval("document.querySelector('[data-rpproj=ABC]').textContent"))
        self.assertEqual(b.eval("weekView('ABC').clients.length"), 0)
        self.assertEqual(b.eval("REMINDERS.filter(r=>String(r.id).startsWith('client:ABC')).length"), 0)

    def test_off_the_reporting_space_and_card_do_not_break(self):
        b = self.b
        self.open_panel()
        b.click("#cfgOn")
        self.wait_line("Client report", "off")
        b.eval("location.hash='#reporting=ABC'")
        # H1 retired the Reporting space's card: the hub shows only the internal report, with no switch
        b.wait("!!document.querySelector('#v-reporting .sheet-bar')")
        self.assertEqual(b.eval("!!document.querySelector('#hubSeg')"), False)
        self.assertEqual(b.eval("document.querySelectorAll('#v-reporting .page').length"), 1)
        self.assertEqual(b.eval("!!document.querySelector('#v-reporting [data-editboth]')"), False)

    # ----- logos from the screen (Round 8 and 9)

    def test_a_logo_chosen_on_the_screen_is_trimmed_for_drawing_and_the_original_is_kept(self):
        b = self.b
        self.open_panel()
        b.eval("(" + MAKE_PNG + ").then(n => { window.LOGOSIZE = n; })")
        b.wait("window.LOGOSIZE>0")
        b.eval("uploadClientLogo('ABC','client',window.LOGO).then(r => { window.UP = r; })")
        b.wait("window.UP===true")
        logos = self.v.root / "system/branding/logos"
        drawn, original = logos / "ABC-client.png", logos / "ABC-client-original.png"
        self.assertTrue(drawn.is_file() and original.is_file())
        self.assertLess(drawn.stat().st_size, original.stat().st_size + 1)
        dims = b.eval("""(async () => { const get = async u => { const i = new Image(); i.src = u; await i.decode(); return [i.width, i.height]; };
          return [await get(Object.values(crLogoData.value)[0]), window.LOGOSIZE]; })()""")
        self.assertEqual(dims[0], [40, 40])                                                              # margins gone from the drawn copy
        orig_w = int.from_bytes(original.read_bytes()[16:20], "big")
        self.assertEqual(orig_w, 200)                                                                     # the file chosen, untouched
        b.wait("!!document.querySelector('.cfglogo[data-kind=client] .mark img')")
        self.assertEqual(b.eval("document.querySelector('.cfglogo[data-kind=client] [data-logo-add]').textContent"), "Change")

    def test_the_file_chooser_adds_a_logo_and_remove_takes_it_away(self):
        b = self.b
        self.open_panel()
        self.assertEqual(b.eval("document.querySelector('[data-logo-file=partner]').accept.includes('svg')"), True)
        svg = Path(self.v.root) / "partner.svg"
        svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="20" height="10"><rect width="20" height="10" fill="#06c"/></svg>')
        b.set_files("[data-logo-file=partner]", [svg])
        b.wait("!!document.querySelector('.cfglogo[data-kind=partner] .mark img')")
        self.assertTrue((self.v.root / "system/branding/logos/ABC-partner.svg").is_file())
        b.click("[data-logo-remove=partner]")
        b.click("[data-logo-remove-yes=partner]")
        b.wait("!document.querySelector('.cfglogo[data-kind=partner] .mark img')")
        self.assertEqual(list((self.v.root / "system/branding/logos").glob("ABC-partner*")), [])

    def test_remove_asks_first_and_the_firms_logo_says_it_is_for_all_projects(self):
        b = self.b
        self.open_panel()
        self.assertIn("all projects", b.eval("document.querySelector('.cfglogo[data-kind=firm]').innerText"))
        svg = Path(self.v.root) / "firm.svg"
        svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="20" height="10"><rect width="20" height="10" fill="#06c"/></svg>')
        b.set_files("[data-logo-file=firm]", [svg])
        b.wait("!!document.querySelector('.cfglogo[data-kind=firm] .mark img')")
        logo = next((self.v.root / "system/branding/logos").glob("firm.*"))
        b.click("[data-logo-remove=firm]")
        self.assertIn("for all projects", b.eval("document.querySelector('.cfglogo[data-kind=firm] .cfgask').innerText"))
        self.assertTrue(logo.is_file(), "nothing is removed by the first click")
        b.click("[data-logo-remove-no=firm]")
        self.assertEqual(b.eval("!!document.querySelector('.cfglogo[data-kind=firm] .cfgask')"), False)
        self.assertTrue(logo.is_file())
        b.click("[data-logo-remove=firm]")
        b.click("[data-logo-remove-yes=firm]")
        b.wait("!document.querySelector('.cfglogo[data-kind=firm] .mark img')")
        self.assertFalse(logo.exists())

    def test_the_rest_of_a_setting_line_is_kept_when_the_value_is_rewritten(self):
        b = self.b
        self.memory.write_text(self.original.replace("- **Client report rhythm:**", "- **Client report:** on, pending client OK\n- **Client report rhythm:**", 1))
        b.reload("typeof go==='function' && LIVE")
        self.open_panel()
        b.click("#cfgOn")
        b.wait("!!document.querySelector('#cfgOff')")
        import time
        end = time.time() + 8
        while time.time() < end and "**Client report:** off" not in self.text():
            time.sleep(0.1)
        self.assertIn("- **Client report:** off, pending client OK\n", self.text())

    def test_the_client_name_is_one_line_of_at_most_80_characters(self):
        b = self.b
        self.open_panel()
        self.assertEqual(b.eval("document.querySelector('#cfgNm').maxLength"), 80)
        before = self.text()
        self.assertEqual(b.eval("setClientName('ABC', 'Northwind\\nTraders')"), False)
        self.assertEqual(b.eval("setClientName('ABC', 'x'.repeat(81))"), False)
        self.assertEqual(self.text(), before, "nothing was written")
        self.assertEqual(b.eval("setClientName('ABC', 'x'.repeat(80))"), True)

    def test_a_jpeg_is_told_a_transparent_png_or_svg_sits_better(self):
        b = self.b
        self.open_panel()
        jpg = Path(self.v.root) / "client.jpg"
        jpg.write_bytes(base64.b64decode(
            "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA=") + b"\xff\xd9")      # p240-leakfix: a JPEG now has to end with its EOI marker
        b.set_files("[data-logo-file=client]", [jpg])
        b.wait("!!document.querySelector('#cfgLogoNote')")
        self.assertIn("A transparent PNG or SVG sits better", b.eval("document.querySelector('#cfgLogoNote').textContent"))

    def test_a_file_that_is_not_a_picture_is_refused_and_nothing_is_saved(self):
        b = self.b
        self.open_panel()
        bad = Path(self.v.root) / "client.png"
        bad.write_text("not a picture")
        b.set_files("[data-logo-file=client]", [bad])
        b.wait("!!document.querySelector('#cfgLogoNote')")
        self.assertEqual(list((self.v.root / "system/branding/logos").glob("*")), [])


if __name__ == "__main__":
    unittest.main()
