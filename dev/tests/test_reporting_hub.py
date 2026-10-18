"""#221 H1 (Reporting hub, release 2.4): the hub page shell, in real Chrome on the real live server (no Claude runs). Desktop only:
1400 and 900 px. The hub is `#reporting=<CODE>` (`go('reporting', code)`), one page for a project's weekly reporting, replacing the
separate weekly and client pages. Brief: dev/sprints/reporting-hub-brief.md (Round 10 = final choices); mockup (locked):
dev/mockups/reporting-hub-mockup.html.

Brief item -> test (the PM fills the hand-check sheet from this list):
  (a) Internal | Client | Side by side ........ ViewSwitch.test_the_switch_shows_internal_client_and_side_by_side
      switch not shown when no client report ... ViewSwitch.test_no_client_report_no_switch_and_no_client_status
      side by side: both sheets, scroll together  SideBySide.test_both_sheets_at_a_readable_size_in_one_scroller
  (b) week Menu, list of weeks, no arrows ...... WeekMenu.test_the_date_opens_a_list_of_weeks_and_jumps
      jump-to-a-date box ........................ WeekMenu.test_a_date_in_the_box_jumps_to_that_weeks_friday
  (c) toolbar on one line, 32 px, cog last ..... Toolbar.test_one_line_32px_controls_cog_last
      icons always, words as tooltips ........... Toolbar.test_icons_always_names_as_tooltips_and_accessible_names
      zoom - Fit +, click % = Fit, pinch ........ Toolbar.test_zoom_is_one_joined_control_and_the_pinch_still_zooms
      Show as exported .......................... Toolbar.test_show_as_exported_toggles_the_exported_view
      Export asks only with the client report on  Actions.test_export_asks_which_report_only_when_the_client_report_is_on
      Approve menu rules ........................ Actions.test_approve_menu_internal_first_then_client
  (d) quiet status label on each report ........ Labels.test_each_report_has_a_quiet_status_label
  (e) scrolling header as #202/#207 ............ Scroll.test_*  (hide on the first tick, back only at the top)
  (f) old entry points open the hub ............ EntryPoints.test_*  (one test per entry point)
  (g) no Check this report button .............. Toolbar.test_no_check_this_report_button_yet
  cog + ClientReportPanel mount point (H3) ..... Panel.test_the_cog_opens_the_panel_slot_and_clientReportOn_reads_one_function

Run: python3 dev/tests/test_reporting_hub.py      (Chrome tier; skipped without Chrome)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_reports as R  # noqa: E402  (its fixture and fixed clock: Friday 09-10-2026)
from live_browser import LiveBrowserCase, pin_page_clock  # noqa: E402

WIDTHS = ((1400, 1000), (900, 900))
SLIM = "document.querySelector('#v-reporting .sheet-root.rpt-slim')"
BAR = "#v-reporting .sheet-bar"


class Hub(LiveBrowserCase):
    shared_server = True

    @classmethod
    def load(cls, v):
        R.populate(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": R.NOW, "CREAITE_NO_LAUNCH": "1"}

    def setUp(self):
        super().setUp()
        pin_page_clock(self.b, R.NOW)                # the page's clock agrees with the server's: this week is the one ending 09-10-2026

    def open_hub(self, w=1400, h=1000, hash_="go('reporting','ABC')", client_on=True):
        self.b.resize(w, h)
        self.b.reload("typeof go==='function' && LIVE")
        self.b.eval(f"(()=>{{ P.find(p=>p.code==='ABC').cr={json.dumps(client_on)}; crTick.value++; }})()")
        self.b.eval(hash_)
        self.b.wait("document.querySelector('#v-reporting .page')", 25)
        self.b.pump(0.3)

    def start_at(self, js, ready):
        """Open the page at another screen (not the hub): reload, run `js`, wait for `ready`."""
        self.b.reload("typeof go==='function' && LIVE")
        self.b.eval(js)
        self.b.wait(ready, 20)

    def api(self, path, body):
        return self.b.eval(f"""fetch({json.dumps(path)},{{method:'POST',headers:{{'Content-Type':'application/json','X-Creaite-Token':D.token}},
          body:JSON.stringify({json.dumps(body)})}}).then(r=>r.json())""")

    def q(self, js):
        return self.b.eval(js)

    def press(self, selector):
        """A real mouse click at the element's centre, without scrolling it into view."""
        r = self.b.eval(f"(()=>{{const r=document.querySelector({json.dumps(selector)}).getBoundingClientRect();return [r.left+r.width/2, r.top+r.height/2]}})()")
        for kind in ("mouseMoved", "mousePressed", "mouseReleased"):
            self.b.call("Input.dispatchMouseEvent", type=kind, x=r[0], y=r[1], button="left", clickCount=1)
        self.b.pump(0.2)


class ViewSwitch(Hub):
    def test_the_switch_shows_internal_client_and_side_by_side(self):
        self.open_hub()
        self.assertEqual(self.q("[...document.querySelectorAll('#hubSeg button')].map(b=>b.textContent.trim())"),
                         ["Internal", "Client", "Side by side"])
        self.assertEqual(self.q("document.querySelectorAll('#v-reporting .page').length"), 1)
        for v, n, aud in (("client", 1, "client"), ("side", 2, None), ("internal", 1, "internal")):
            self.b.click(f"#hubSeg [data-hv='{v}']")
            self.b.wait(f"document.querySelectorAll('#v-reporting .page').length=={n}", 20)
            self.assertEqual(self.q(f"document.querySelector('#hubSeg [data-hv={v}]').getAttribute('aria-pressed')"), "true")
            if aud:
                self.assertEqual(self.q("document.querySelector('#v-reporting .page').dataset.audience"), aud)
            self.assertEqual("v=" + v in self.q("location.hash"), v != "internal", "the address keeps the view")

    def test_no_client_report_no_switch_and_no_client_status(self):
        self.open_hub(client_on=False)
        self.assertEqual(self.q("!!document.querySelector('#hubSeg')"), False, "not rendered at all (not just disabled)")
        self.assertEqual(self.q("document.querySelectorAll('#v-reporting .hubstat[data-k=client]').length"), 0)
        self.assertEqual(self.q("document.querySelectorAll('#v-reporting .page').length"), 1)
        self.assertNotIn("Client", self.q("document.querySelector('#v-reporting .sheet-bar').innerText"))
        self.b.click("#hubWeek")
        self.b.wait("document.querySelector('.wkpop')")
        self.assertNotIn("Client", self.q("document.querySelector('.wkpop').innerText"), "no client status in the week list")
        self.b.key("Escape")
        # an address naming the client view falls back to the internal report
        self.open_hub(hash_="location.hash='#reporting=ABC&v=client'; window.dispatchEvent(new HashChangeEvent('hashchange')); go('reporting','ABC')", client_on=False)
        self.assertEqual(self.q("document.querySelector('#v-reporting .page').dataset.audience"), "internal")


class SideBySide(Hub):
    def test_both_sheets_at_a_readable_size_in_one_scroller(self):
        for w, h in WIDTHS:
            with self.subTest(width=w):
                self.open_hub(w, h)
                self.b.click("#hubSeg [data-hv='side']")
                self.b.wait("document.querySelectorAll('#v-reporting .page').length==2", 20)
                self.b.pump(0.4)
                r = self.q("""(()=>{const s=[...document.querySelectorAll('#v-reporting .sheet-scroll')], p=[...document.querySelectorAll('#v-reporting .page')];
                  return {scrollers:s.length, w:p.map(x=>x.getBoundingClientRect().width), h:p.map(x=>x.getBoundingClientRect().height),
                    aud:p.map(x=>x.dataset.audience), same:p.every(x=>s[0].contains(x))}})()""")
                self.assertEqual(r["scrollers"], 1, "one scroller, so both sheets scroll together")
                self.assertTrue(r["same"])
                self.assertEqual(r["aud"], ["internal", "client"])
                self.assertTrue(all(x >= (400 if w == 1400 else 300) for x in r["w"]), f"readable: {r['w']}")
                self.q("document.querySelector('#v-reporting .sheet-scroll').scrollTop=400")
                self.b.pump(0.2)
                tops = self.q("[...document.querySelectorAll('#v-reporting .page')].map(x=>Math.round(x.getBoundingClientRect().top))")
                self.assertEqual(tops[0], tops[1], "scrolled together")


    def test_the_label_row_does_not_overflow_at_900_with_a_client_draft(self):
        self.open_hub(900, 900)
        self.b.click("#hubSeg [data-hv='side']")
        self.b.wait("document.querySelectorAll('#v-reporting .page').length==2 && document.querySelector('[data-crmatchall]')", 20)
        self.b.pump(0.4)
        r = self.q("""(()=>{const row=document.querySelector('#v-reporting .hubrow'), W=document.documentElement.clientWidth;
          const els=[...row.querySelectorAll('.hubpl *')].filter(e=>e.getClientRects().length), sub=row.querySelector('.hubpl[data-k=client] .sub');
          return {sw:row.scrollWidth, cw:row.clientWidth, out:els.filter(e=>e.getBoundingClientRect().right>W+0.5).map(e=>e.className||e.tagName),
            subw: sub?sub.getBoundingClientRect().width:-1}})()""")
        self.assertLessEqual(r["sw"], r["cw"], r)
        self.assertEqual(r["out"], [], r)
        self.assertGreater(r["subw"], 0, "the client name keeps some width")


class WeekMenu(Hub):
    def test_the_date_opens_a_list_of_weeks_and_jumps(self):
        self.open_hub()
        self.assertEqual(self.q("document.querySelectorAll('#v-reporting .hubwk .ib, #v-reporting [aria-label=\"Earlier week\"], #v-reporting [aria-label=\"Later week\"]').length"), 0, "no arrows")
        self.assertIn("09-10-2026", self.q("document.querySelector('#hubWeek').innerText"))
        self.b.click("#hubWeek")
        self.b.wait("document.querySelector('.wkpop')")
        rows = self.q("[...document.querySelectorAll('.wkpop .wkrow')].map(r=>({w:r.dataset.w, dot:!!r.querySelector('i'), t:r.innerText}))")
        self.assertGreaterEqual(len(rows), 4)
        self.assertEqual(rows[0]["w"], "2026-10-09")
        self.assertTrue(all(r["dot"] for r in rows), "a health dot on each week")
        self.assertIn("Internal", rows[0]["t"])
        self.assertIn("Client", rows[0]["t"])
        self.assertEqual(self.q("document.querySelector('.wkpop .wkrow[aria-current=true]').dataset.w"), "2026-10-09")
        self.b.click(".wkpop .wkrow:nth-of-type(3)")
        self.b.wait("!document.querySelector('.wkpop')")
        self.b.wait("location.hash.includes('w=2026-09-25')", 10)
        self.b.wait("/25-09-2026/.test(document.querySelector('#hubWeek').innerText)", 20)

    def test_a_date_in_the_box_jumps_to_that_weeks_friday(self):
        self.open_hub()
        self.b.click("#hubWeek")
        self.b.wait("document.querySelector('.wkpop #wkJump')")
        self.q("""(()=>{const i=document.querySelector('#wkJump'); i.value='2026-09-30'; i.dispatchEvent(new Event('input',{bubbles:true})); i.dispatchEvent(new Event('change',{bubbles:true}));
          i.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));})()""")
        self.b.wait("location.hash.includes('w=2026-10-02')", 10)       # the Friday ending the week that holds 30-09


class Toolbar(Hub):
    CONTROLS = "#v-reporting .sheet-bar :is(button, .hubzoom)"

    def test_one_line_32px_controls_cog_last(self):
        for w, h in WIDTHS:
            for view in ("internal", "client", "side"):
                with self.subTest(width=w, view=view):
                    self.open_hub(w, h)
                    self.b.click(f"#hubSeg [data-hv='{view}']")
                    self.b.wait(f"document.querySelectorAll('#v-reporting .page').length=={2 if view == 'side' else 1}", 20)
                    r = self.q("""(()=>{const bar=document.querySelector('#v-reporting .sheet-bar'),
                      els=[...bar.querySelectorAll(':scope > .seg, :scope > .hubzoom, :scope button, :scope .hubcfgwrap > button')]
                        .filter(e=>!e.closest('.hubzoom')||e.classList.contains('hubzoom')).filter(e=>!e.closest('.seg')||e.classList.contains('seg'))
                        .filter(e=>e.getBoundingClientRect().width>0 && !e.closest('#crHost'));
                      const b=bar.getBoundingClientRect(); const rs=els.map(e=>e.getBoundingClientRect());
                      return {barH:b.height, tops:[...new Set(rs.map(r=>Math.round(r.top)))], hs:[...new Set(rs.map(r=>Math.round(r.height)))],
                        ids:els.map(e=>e.id||e.className), last:els[els.length-1].id, over:rs.some(r=>r.right>b.right+1||r.left<b.left-1)}})()""")
                    self.assertEqual(len(r["tops"]), 1, f"one line: {r}")
                    self.assertEqual(r["hs"], [32], f"every control 32 px: {r}")
                    self.assertEqual(r["last"], "hubCfg", f"the cog is last: {r['ids']}")
                    self.assertFalse(r["over"], "nothing runs out of the bar")

    def test_icons_always_names_as_tooltips_and_accessible_names(self):
        self.open_hub()
        for sel, name in (("#hubExp", "Show as exported"), ("#hubExport", "Export"), ("#hubApprove", "Approve"), ("#hubCfg", "Client report settings")):
            with self.subTest(sel=sel):
                self.assertEqual(self.q(f"document.querySelector('{sel}').innerText.trim()"), "", "no visible words")
                self.assertTrue(self.q(f"!!document.querySelector('{sel} svg')"))
                self.assertIn(name, self.q(f"(document.querySelector('{sel}').getAttribute('aria-label')||'')"))
                self.assertIn(name, self.q(f"(document.querySelector('{sel}').getAttribute('data-tip')||document.querySelector('{sel}').title||'')"))

    def test_the_menus_open_inside_the_window(self):
        for w, h in WIDTHS:
            for opener, box in (("#hubExport", ".ddmenu.on"), ("#hubApprove", ".ddmenu.on"), ("#hubWeek", ".wkpop")):
                with self.subTest(width=w, menu=opener):
                    self.open_hub(w, h)
                    self.press(opener)
                    self.b.wait(f"document.querySelector('{box}')", 5)
                    r = self.q(f"(()=>{{const r=document.querySelector('{box}').getBoundingClientRect(); return [r.left, r.right, innerWidth]}})()")
                    self.assertGreaterEqual(r[0], 0)
                    self.assertLessEqual(r[1], r[2], f"{opener} menu runs off the window: {r}")

    def test_no_check_this_report_button_yet(self):
        self.open_hub()
        self.assertEqual(self.q("/Check this report|Check and export/.test(document.querySelector('#v-reporting .sheet-bar').innerHTML)"), False)

    def test_zoom_is_one_joined_control_and_the_pinch_still_zooms(self):
        self.open_hub()
        z = "document.querySelector('#zVal')"
        self.assertEqual(self.q(f"{z}.textContent.trim()"), "Fit")
        self.assertEqual(self.q("[...document.querySelectorAll('#v-reporting .hubzoom > *')].map(e=>e.id)"), ["zOut", "zVal", "zIn"])
        self.b.click("#zOut")
        self.b.pump(0.2)
        self.assertRegex(self.q(f"{z}.textContent.trim()"), r"^\d+%$")
        small = self.q("document.querySelector('#v-reporting .sheet-fit').getBoundingClientRect().width")
        self.b.click("#zOut")
        self.assertLess(self.q("document.querySelector('#v-reporting .sheet-fit').getBoundingClientRect().width"), small)
        self.b.click("#zVal")                                        # the percentage returns to Fit
        self.b.pump(0.2)
        self.assertEqual(self.q(f"{z}.textContent.trim()"), "Fit")
        before = self.q("document.querySelector('#v-reporting .sheet-fit').getBoundingClientRect().width")
        r = self.q("(()=>{const r=document.querySelector('#v-reporting .sheet-scroll').getBoundingClientRect();return [r.left+r.width/2,r.top+200]})()")
        self.b.call("Input.dispatchMouseEvent", type="mouseWheel", x=r[0], y=r[1], deltaX=0, deltaY=60, modifiers=2)     # Ctrl + wheel
        self.b.pump(0.3)
        self.assertLess(self.q("document.querySelector('#v-reporting .sheet-fit').getBoundingClientRect().width"), before, "the pinch zooms out")
        self.assertRegex(self.q(f"{z}.textContent.trim()"), r"^\d+%$")

    def test_show_as_exported_toggles_the_exported_view(self):
        self.open_hub()
        self.assertEqual(self.q("document.querySelector('#hubExp').getAttribute('aria-pressed')"), "false")
        self.assertGreater(self.q("document.querySelectorAll('#v-reporting .sheet-handle, #v-reporting .wr-eye').length"), 0)
        self.b.click("#hubExp")
        self.b.pump(0.3)
        self.assertEqual(self.q("document.querySelector('#hubExp').getAttribute('aria-pressed')"), "true")
        self.assertTrue(self.q("!!document.querySelector('#v-reporting .sheet-exported')"))


class Labels(Hub):
    def test_each_report_has_a_quiet_status_label(self):
        self.open_hub()
        self.assertEqual(self.q("document.querySelector('.hubstat[data-k=internal]').innerText.trim()"), "Draft")
        self.assertEqual(self.q("document.querySelectorAll('.hubstat[data-k=client]').length"), 0, "internal view: the client label is not drawn")
        self.b.click("#hubSeg [data-hv='client']")
        self.b.wait("document.querySelector('.hubstat[data-k=client]')", 20)
        self.assertEqual(self.q("document.querySelector('.hubstat[data-k=client]').innerText.trim()"), "Waits for the internal report")
        self.b.click("#hubSeg [data-hv='side']")
        self.b.wait("document.querySelectorAll('#v-reporting .page').length==2", 20)
        self.assertEqual(self.q("document.querySelectorAll('.hubstat').length"), 2)


class Actions(Hub):
    def intercept(self):
        self.q("""window.__calls=[]; (()=>{const real=window.fetch.bind(window);
          window.fetch=(u,o)=>{ if(String(u).endsWith('/api/report/check')) return Promise.resolve(new Response(JSON.stringify({ok:true,left_out:{items:[],sections:[],logos:[],tags:0,
            health:null,findings:[],ready:true,not_ready:'',facts_week:'2026-10-09'}}),{headers:{'Content-Type':'application/json'}}));
            if(String(u).includes('/api/report/export')||String(u).includes('/api/report/approve')) { window.__calls.push([String(u),String(o&&o.body)]);
            return Promise.resolve(new Response(JSON.stringify({ok:true,saved:true,name:'x.html',folder:'',folder_label:'Example Programme › Reports',path:''}),{headers:{'Content-Type':'application/json'}})); }
            return real(u,o); };})()""")

    def pick_item(self, text):
        self.b.wait(f"[...document.querySelectorAll('.ddmenu.on [role^=menuitem]')].some(e=>e.textContent.includes({json.dumps(text)}))")
        self.q(f"[...document.querySelectorAll('.ddmenu.on [role^=menuitem]')].find(e=>e.textContent.includes({json.dumps(text)})).setAttribute('data-pick','1')")
        self.press("[data-pick='1']")

    def test_export_asks_which_report_only_when_the_client_report_is_on(self):
        self.open_hub(client_on=False)
        self.intercept()
        self.press("#hubExport")
        names = self.q("[...document.querySelectorAll('.ddmenu.on [role^=menuitem]')].map(e=>({n:e.querySelector('b')&&e.querySelector('b').textContent, l:!!e.querySelector('small'), i:!!e.querySelector('svg')}))")
        self.assertEqual([n["n"] for n in names][:3], ["HTML", "Word (.docx)", "PDF"])
        self.assertTrue(all(n["l"] and n["i"] for n in names), "an icon, a name and one line each")
        self.pick_item("HTML")
        self.b.pump(0.5)
        self.assertEqual(self.q("!!document.querySelector('[data-hubpick]')"), False, "off: no question")
        calls = self.q("window.__calls")
        self.assertEqual(len(calls), 1)
        self.assertEqual(json.loads(calls[0][1])["kind"], "weekly")
        # on: the question comes after the format
        self.open_hub(client_on=True)
        self.intercept()
        self.press("#hubExport")
        self.pick_item("Word")
        self.b.wait("document.querySelector('[data-hubpick]')", 10)
        self.assertEqual(self.q("window.__calls.length"), 0, "nothing exported before the answer")
        self.assertEqual(self.q("[...document.querySelectorAll('[data-hubpick]')].map(e=>e.dataset.hubpick)"), ["internal", "client", "both"])
        self.press("[data-hubpick='both']")
        self.b.wait("window.__calls.length==2", 10)
        kinds = sorted(json.loads(c[1])["kind"] for c in self.q("window.__calls"))
        self.assertEqual(kinds, ["client", "weekly"])

    def test_a_client_export_before_the_internal_week_is_approved_opens_the_left_out_dialog_and_exports_nothing(self):
        self.open_hub()
        self.q("""window.__calls=[]; (()=>{const f=window.fetch.bind(window); window.fetch=(u,o)=>{ if(String(u).includes('/api/report/export')) window.__calls.push(String(u)); return f(u,o); };})()""")
        self.press("#hubExport")
        self.pick_item("HTML")
        self.b.wait("document.querySelector('[data-hubpick=client]')", 10)
        self.press("[data-hubpick='client']")
        self.b.wait("document.querySelector('#crLeftDlg[open] [data-crleft-list]')", 20)
        self.assertIn("Approve the internal weekly report", self.q("document.querySelector('#crLeftDlg').innerText"))
        self.assertEqual(self.q("window.__calls"), [], "nothing was exported")

    def test_approve_menu_internal_first_then_client(self):
        self.open_hub()
        self.press("#hubApprove")
        items = self.q("[...document.querySelectorAll('.ddmenu.on [role^=menuitem]')].map(e=>({t:e.textContent, d:e.getAttribute('aria-disabled')}))")
        self.assertEqual(len(items), 2)
        self.assertIn("Approve the internal report", items[0]["t"])
        self.assertIn("Approve the client report", items[1]["t"])
        self.assertEqual(items[0]["d"], None)
        self.assertEqual(items[1]["d"], "true", "the client report waits for the internal one")
        self.assertIn("internal report is approved", items[1]["t"])
        self.b.key("Escape")
        # approve the internal report on the server: the client item opens
        doc = self.api("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": "2026-10-09"})["doc"]
        next(x for x in doc["sections"] if x["id"] == "health")["text"] = "UAT start slipped two weeks."     # a health that is not On track needs its reason
        self.assertTrue(self.api("/api/report/save", {"doc": doc, "base_version": 0})["ok"])
        a = self.api("/api/report/approve", {"kind": "weekly", "code": "ABC", "week_ending": "2026-10-09", "force": True})
        self.assertTrue(a["ok"], a)
        self.open_hub()
        self.press("#hubApprove")
        items = self.q("[...document.querySelectorAll('.ddmenu.on [role^=menuitem]')].map(e=>({t:e.textContent, d:e.getAttribute('aria-disabled')}))")
        self.assertEqual(items[0]["d"], "true", "the internal report is already approved")
        self.assertEqual(items[1]["d"], None, "the client report can now be approved")
        self.b.key("Escape")
        self.assertEqual(self.q("document.querySelector('.hubstat[data-k=internal]').innerText.trim()"), "Approved")


    def test_approve_menu_lists_only_the_internal_item_with_the_client_report_off(self):
        self.open_hub(client_on=False)
        self.press("#hubApprove")
        items = self.q("[...document.querySelectorAll('.ddmenu.on [role^=menuitem]')].map(e=>e.textContent)")
        self.assertEqual(len(items), 1, items)
        self.assertIn("Approve the internal report", items[0])
        self.assertNotIn("Approve the client report", items[0])


class Scroll(Hub):
    def tick(self, dy=2):
        r = self.q("(()=>{const r=document.querySelector('#v-reporting .sheet-scroll').getBoundingClientRect();"
                   "const t=Math.max(r.top,60), b=Math.min(r.bottom,window.innerHeight);return [r.left+r.width/2, t+(b-t)/2]})()")
        self.b.call("Input.dispatchMouseEvent", type="mouseWheel", x=r[0], y=r[1], deltaX=0, deltaY=dy)

    def header_bottom(self):
        return self.q(f"document.querySelector('{BAR}').getBoundingClientRect().bottom")

    def test_the_first_tick_hides_search_and_title_and_leaves_one_line_with_a_short_title(self):
        for w, h in WIDTHS:
            with self.subTest(width=w):
                self.open_hub(w, h)
                self.assertGreater(self.header_bottom(), 150)
                self.tick(2)
                self.b.wait(SLIM, 5)
                self.b.pump(0.1)
                st = self.q("""(()=>{const q=s=>document.querySelector(s); return {bar:q('.main>.bar').getBoundingClientRect().height,
                  head:q('#v-reporting .wrhead').getBoundingClientRect().height, mini:q('#v-reporting .sheet-mini').innerText,
                  mh:q('#v-reporting .sheet-mini').getBoundingClientRect().height}})()""")
                self.assertEqual((st["bar"], st["head"]), (0, 0))
                self.assertIn("Weekly reporting", st["mini"])
                self.assertAlmostEqual(self.header_bottom(), 48, delta=1.5)
                tops = self.q("[...document.querySelectorAll('#v-reporting .sheet-bar > .seg, #v-reporting .sheet-bar > .hubzoom, #v-reporting .sheet-bar > button, #v-reporting .sheet-bar .dd > button, #v-reporting .sheet-bar .hubcfgwrap > button')].filter(e=>e.getBoundingClientRect().width>0).map(e=>Math.round(e.getBoundingClientRect().top))")
                self.assertLessEqual(max(tops) - min(tops), 8, "still one line")
                self.assertEqual(self.q(f"getComputedStyle(document.querySelector('{BAR}')).transitionDuration"), "0s")

    def test_scrolling_up_never_brings_it_back_only_the_top_does(self):
        for w, h in WIDTHS:
            with self.subTest(width=w):
                self.open_hub(w, h)
                self.tick(2)
                self.b.wait(SLIM, 5)
                self.q("document.querySelector('#v-reporting .sheet-scroll').scrollTop=900")
                self.b.pump(0.2)
                for up in (8, 50, 500):
                    self.tick(-up)
                    self.b.pump(0.2)
                    self.assertTrue(self.q("!!" + SLIM), f"still slim after {up} px up")
                self.press(f"{BAR} #zVal")
                self.assertTrue(self.q("!!" + SLIM), "a click in the bar keeps it slim")
                self.q("document.querySelector('#v-reporting .sheet-scroll').scrollTop=0")
                self.b.pump(0.3)
                self.assertFalse(self.q("!!" + SLIM), "the top brings the header back")
                self.assertGreater(self.header_bottom(), 150)


class Panel(Hub):
    def test_the_cog_opens_the_panel_slot_and_clientReportOn_reads_one_function(self):
        self.open_hub()
        self.assertEqual(self.q("typeof clientReportOn"), "function")
        self.assertEqual(self.q("clientReportOn('ABC')"), True, "existing projects default to on")
        self.assertEqual(self.q("document.querySelector('#hubCfg').getAttribute('aria-expanded')"), "false")
        self.b.click("#hubCfg")
        self.b.wait("document.querySelector('[data-slot=ClientReportPanel]')", 5)
        self.assertEqual(self.q("document.querySelector('#hubCfg').getAttribute('aria-expanded')"), "true")
        self.assertEqual(self.q("document.querySelector('#hubCfg').getAttribute('aria-label')"), "Client report settings: on")
        self.b.key("Escape")
        self.b.wait("!document.querySelector('[data-slot=ClientReportPanel]')", 5)


class CogPanel(Hub):
    """Cap's acceptance walk (21:18, 18-10-2026): the cog opened an empty 30 px strip, clipped by an outer wrapper. The tests
    above only looked for the slot's node; this one clicks the real cog and measures what a person sees."""

    BOX = ("(()=>{const e=document.querySelector('#crPanel'); if(!e) return null; const r=e.getBoundingClientRect(); "
           "return {t:r.top,l:r.left,b:r.bottom,r:r.right,h:r.height,sh:e.scrollHeight,ch:e.clientHeight,w:innerWidth,ih:innerHeight}})()")

    def inside(self, sel):
        return self.q(f"""(()=>{{const p=document.querySelector('#crPanel').getBoundingClientRect(); const out=[];
          for (const e of document.querySelectorAll({json.dumps(sel)})) {{ e.scrollIntoView({{block:'nearest'}}); const r=e.getBoundingClientRect();
            if (r.width<=0 || r.height<=0) {{ out.push('hidden '+(e.id||e.className)); continue; }}
            if (r.left<p.left-1 || r.right>p.right+1 || r.left<0 || r.right>innerWidth) out.push('across '+(e.id||e.className)); }}
          return out}})()""")

    def check(self, w, h):
        self.open_hub(w, h)
        self.b.click("#hubCfg")
        self.b.wait("document.querySelector('#crPanel')", 5)
        self.b.pump(0.3)
        box = self.q(self.BOX)
        self.assertGreaterEqual(box["h"], 300, f"the panel is a full panel, not a strip: {box}")
        self.assertGreaterEqual(box["t"], 0); self.assertLessEqual(box["b"], box["ih"], f"inside the window: {box}")
        self.assertLessEqual(box["r"], box["w"])
        for sel in ("#cfgOn", "#cfgRh", "#cfgNm", "#cfgRem", ".cfglogo", ".cfglogo input", ".cfglogo button, .cfglogo label.btn", "#cfgDone"):
            self.assertTrue(self.q(f"document.querySelectorAll({json.dumps('#crPanel ' + sel)}).length>0"), sel)
        self.assertEqual(self.q("document.querySelectorAll('#crPanel .cfglogo').length"), 3)
        self.assertEqual(self.inside("#crPanel #cfgOn,#crPanel #cfgRh,#crPanel #cfgNm,#crPanel #cfgRem,#crPanel .cfglogo,#crPanel .cfglogo button"),
                         [], "every control can be scrolled to and lies fully inside the panel and the window")
        self.q("document.querySelector('#crPanel').scrollTop=0")
        ctl = "#crPanel #cfgOn,#crPanel #cfgRh,#crPanel #cfgDone"
        self.assertEqual(self.q("[...document.querySelectorAll(" + json.dumps(ctl) + """)].filter(e=>{const r=e.getBoundingClientRect();
          const hit=document.elementFromPoint(r.left+r.width/2, r.top+r.height/2); return !(hit && hit.closest('#crPanel'))}).map(e=>e.id||e.className)"""), [],
                         "a person can see and click each control: nothing clips it")
        self.assertEqual(self.q("document.querySelectorAll('#hubCfg').length"), 1)
        self.assertEqual(self.q("document.querySelectorAll('#crPanel').length"), 1)
        self.assertEqual(self.q("(()=>{const ids=[...document.querySelectorAll('[id]')].map(e=>e.id); return ids.filter((x,i)=>ids.indexOf(x)!==i)})()"), [],
                         "no duplicate ids anywhere on the page")
        return box

    def test_the_cog_opens_a_full_panel_at_1400(self):
        self.check(1400, 1000)

    def test_the_cog_opens_a_full_panel_at_900(self):
        self.check(900, 700)

    def test_a_panel_taller_than_the_window_scrolls_inside_itself(self):
        box = self.check(1400, 560)
        self.assertGreater(box["sh"], box["ch"], "the content is taller than the panel")
        self.assertLessEqual(box["b"], box["ih"])

    def test_esc_closes_it_and_focus_returns_to_the_cog(self):
        self.open_hub()
        self.b.click("#hubCfg")
        self.b.wait("document.querySelector('#crPanel')", 5)
        self.b.key("Escape")
        self.b.wait("!document.querySelector('#crPanel')", 5)
        self.assertEqual(self.q("document.activeElement.id"), "hubCfg")
        self.assertEqual(self.q("document.querySelector('#hubCfg').getAttribute('aria-expanded')"), "false")

    def test_the_cog_and_done_toggle_it(self):
        self.open_hub()
        self.b.click("#hubCfg"); self.b.wait("document.querySelector('#crPanel')", 5)
        self.b.click("#hubCfg"); self.b.wait("!document.querySelector('#crPanel')", 5)
        self.b.click("#hubCfg"); self.b.wait("document.querySelector('#crPanel')", 5)
        self.b.click("#cfgDone"); self.b.wait("!document.querySelector('#crPanel')", 5)


class Triage(Hub):
    """The cheap differences from Cap's acceptance walk (21:18, 18-10-2026), each measured."""

    def test_the_firm_tile_is_not_greyed_and_the_panel_has_no_extra_note(self):
        self.open_hub()
        self.b.click("#hubCfg"); self.b.wait("document.querySelector('#crPanel .cfglogo')", 5)
        self.assertEqual(self.q("getComputedStyle(document.querySelector('#crPanel .cfglogo[data-kind=firm] .mark')).opacity"), "1")
        self.assertEqual(self.q("getComputedStyle(document.querySelector('#crPanel .cfglogo[data-kind=firm] .cfgname')).opacity"), "1")
        self.assertNotIn("Ticking a logo", self.q("document.querySelector('#crPanel').innerText"))

    def test_jump_to_takes_a_dd_mm_yyyy_date_and_a_go_button(self):
        self.open_hub()
        self.b.click("#hubWeek"); self.b.wait("document.querySelector('.wkpop #wkJump')")
        self.assertEqual(self.q("document.querySelector('#wkJump').placeholder"), "DD-MM-YYYY")
        self.assertEqual(self.q("document.querySelector('#wkJump').type"), "text")
        self.assertIn("jump to", self.q("document.querySelector('.wkpop').innerText").lower())
        self.assertEqual(self.q("document.querySelector('#wkGo').textContent"), "Go")
        self.q("document.querySelector('#wkJump').focus()")
        self.b.type("30-09-2026")
        self.b.click("#wkGo")
        self.b.wait("location.hash.includes('w=2026-10-02')", 10)

    def test_the_status_pill_sits_at_the_far_right_of_its_label_row(self):
        for view in ("internal", "side"):
            with self.subTest(view=view):
                self.open_hub()
                self.b.click(f"#hubSeg [data-hv='{view}']")
                self.b.pump(0.3)
                gaps = self.q("""[...document.querySelectorAll('.hubpl')].map(l=>{const p=l.querySelector('.hubstat').getBoundingClientRect(), r=l.getBoundingClientRect();
                  return Math.round(r.right-p.right)})""")
                self.assertTrue(gaps and all(g <= 2 for g in gaps), gaps)

    def test_show_as_exported_is_a_document_not_an_eye_and_the_menus_have_grey_icons(self):
        self.open_hub()
        self.assertIn("M15 2H6", self.q("document.querySelector('#hubExp svg').innerHTML"))
        for btn in ("#hubExport", "#hubApprove"):
            with self.subTest(menu=btn):
                self.b.click(btn); self.b.wait("document.querySelector('.hubm')", 5)
                self.assertEqual(self.q("getComputedStyle(document.querySelector('.hubm button svg')).color"),
                                 self.q("getComputedStyle(document.querySelector('.hubstat')).color"), "the icons are the muted grey")
                self.b.key("Escape"); self.b.wait("!document.querySelector('.hubm')", 5)


class EntryPoints(Hub):
    def arrives(self, code_js, week="2026-10-09", audience="internal", pages=1):
        self.open_hub(hash_=code_js)
        self.assertEqual(self.q("shared.VIEW"), "reporting")
        self.assertTrue(self.q("location.hash.startsWith('#reporting=ABC')"), self.q("location.hash"))
        self.assertIn(week.split("-")[2] + "-" + week.split("-")[1] + "-" + week.split("-")[0], self.q("document.querySelector('#hubWeek').innerText"))
        self.assertEqual(self.q("document.querySelector('#v-reporting .page').dataset.audience"), audience)
        self.assertEqual(self.q("document.querySelectorAll('#v-reporting .page').length"), pages)

    def test_go_reporting(self):
        self.arrives("go('reporting','ABC')")

    def test_the_address(self):
        self.arrives("location.hash='#reporting=ABC&w=2026-10-02'; restoreNav(parseHash(location.hash))", week="2026-10-02")

    def test_the_address_names_the_view(self):
        self.arrives("location.hash='#reporting=ABC&w=2026-10-09&v=client'; restoreNav(parseHash(location.hash))", audience="client")

    def test_the_old_weekly_address(self):
        self.arrives("location.hash='#weekly=ABC&week=2026-10-02'; restoreNav(parseHash(location.hash))", week="2026-10-02")

    def test_the_old_client_report_address(self):
        self.arrives("location.hash='#client-report=ABC/2026-10-09/Example%20Client%20Ltd'; restoreNav(parseHash(location.hash))", audience="client")

    def test_go_weekly_and_go_clientreport_still_work(self):
        self.arrives("go('weekly',{code:'ABC',week:'2026-10-02'})", week="2026-10-02")
        self.arrives("go('clientreport',{code:'ABC',week:'2026-10-09'})", audience="client")

    def test_the_old_pages_are_retired(self):
        self.open_hub(hash_="go('weekly',{code:'ABC'})")
        self.assertEqual(self.q("document.querySelector('#v-weekly .page')"), None)
        self.assertEqual(self.q("document.querySelector('#v-clientreport .page')"), None)

    def test_the_reports_page_open_button(self):
        self.start_at("go('reports')", "document.querySelector('[data-rpopen=ABC]')")
        self.b.click("[data-rpopen=ABC]")
        self.b.wait("document.querySelector('#v-reporting .page')", 25)
        self.assertEqual(self.q("shared.VIEW"), "reporting")

    def test_the_cockpit_reports_icon_opens_the_latest_week_internal(self):
        self.open_hub()
        others = self.q("P.filter(p=>p.code!=='ABC').map(p=>p.code)")
        for code in ["ABC"] + others[:1]:
            with self.subTest(code=code):
                self.open_hub(hash_="location.hash='#reporting=ABC&w=2026-10-02&v=client'; restoreNav(parseHash(location.hash))")
                self.assertEqual(self.q("document.querySelector('#v-reporting .page').dataset.audience"), "client")
                self.q(f"go('cockpit',{json.dumps(code)})")
                self.b.wait("document.querySelector('#v-cockpit [data-reports]')", 20)
                self.b.click("#v-cockpit [data-reports]")
                self.b.wait("document.querySelector('#v-reporting .page')", 25)
                self.b.pump(0.4)
                self.assertEqual(self.q("document.querySelector('#v-reporting .page').dataset.audience"), "internal")
                self.assertEqual(self.q("document.querySelector('#hubWeek').innerText.includes('02-10-2026')"), False, "the latest week, not the last visit's")

    def test_today_week_ahead_rows_do_not_take_the_week_menu_styles(self):
        self.open_hub()
        r = self.q("""(()=>{const u=document.createElement('ul'); u.innerHTML='<li class="wkrow"><i></i><span>x</span></li>'; document.body.appendChild(u);
          const c=getComputedStyle(u.firstChild), i=getComputedStyle(u.querySelector('i')); const o={cursor:c.cursor, display:c.display, dot:i.width}; u.remove(); return o})()""")
        self.assertNotEqual(r["cursor"], "pointer")
        self.assertNotEqual(r["display"], "grid")
        self.assertNotEqual(r["dot"], "8px")

    def test_the_projects_reporting_card(self):
        self.start_at("go('cockpit','ABC')", "document.querySelector('[data-rpcard=space]')")
        self.b.click("[data-rpcard=space]")
        self.b.wait("document.querySelector('#v-reporting .page')", 25)

    def test_the_command_palette_entries(self):
        self.start_at("go('today')", "typeof openSpace==='function'")
        self.assertEqual(self.q("typeof openSpace"), "function")
        self.q("openSpace('ABC')")
        self.b.wait("document.querySelector('#v-reporting .page')", 25)

    def test_the_old_weekly_href_helpers_point_at_the_hub(self):
        self.start_at("go('today')", "typeof weeklyHref==='function'")
        self.assertTrue(self.q("weeklyHref('ABC','2026-10-09')").startswith("#reporting=ABC"))
        self.assertTrue(self.q("clientReportHref('ABC','2026-10-09','Example Client Ltd')").startswith("#reporting=ABC"))
        self.assertIn("v=client", self.q("clientReportHref('ABC','2026-10-09','Example Client Ltd')"))


if __name__ == "__main__":
    unittest.main()
