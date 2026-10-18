"""#212 (hand checks 29, 30 and 32 of 2.4.0): the "Always" checks of the reporting hub, in real Chrome on the real live server.

  29 Themes and widths ... Always.test_the_hub_reads_in_both_palettes_light_and_dark_at_900_and_1400
  30 Keyboard ............ Always.test_the_toolbar_week_menu_section_menu_cog_and_export_work_from_the_keyboard
  32 Reopened and refused  Always.test_left_out_stays_out_when_reopened_and_a_client_export_is_refused_before_approval

Desktop only: 1400 and 900 px (Alan, 15-10-2026). It uses the hub's own fixture and fixed clock (test_reports: Friday 09-10-2026).
Run: python3 dev/tests/test_hub_always.py      (Chrome tier; skipped without Chrome)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_reporting_hub as H  # noqa: E402
from live_browser import TEST_PALETTES  # noqa: E402

WEEK = "2026-10-09"
# Colour of the first thing that paints a background behind an element, and the contrast between it and a text colour (WCAG ratio).
CONTRAST_JS = """
window.__contrast=(sel)=>{
  const lum=c=>{const m=c.match(/[\\d.]+/g).map(Number);const [r,g,b]=m.slice(0,3).map(v=>{v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4)});return 0.2126*r+0.7152*g+0.0722*b};
  const el=document.querySelector(sel); if(!el) return null;
  let bg=null; for(let n=el;n;n=n.parentElement){const c=getComputedStyle(n).backgroundColor; const a=(c.match(/[\\d.]+/g)||[]).map(Number);
    if(a.length>=3 && (a.length<4 || a[3]>0.5)){bg=c;break}}
  bg=bg||'rgb(255,255,255)';
  const fg=getComputedStyle(el).color, l1=lum(fg), l2=lum(bg), hi=Math.max(l1,l2), lo=Math.min(l1,l2);
  return {fg, bg, ratio:(hi+0.05)/(lo+0.05)};
}"""


class Always(H.Hub):
    def theme(self, palette, mode):
        self.q(f"document.documentElement.dataset.palette={palette!r}; document.documentElement.dataset.theme={mode!r}")
        self.b.pump(0.25)

    def pick_item(self, text):
        self.b.wait(f"[...document.querySelectorAll('.ddmenu.on [role^=menuitem]')].some(e=>e.textContent.includes({json.dumps(text)}))")
        self.q(f"[...document.querySelectorAll('.ddmenu.on [role^=menuitem]')].find(e=>e.textContent.includes({json.dumps(text)})).setAttribute('data-pick','1')")
        self.press("[data-pick='1']")

    def test_the_hub_reads_in_both_palettes_light_and_dark_at_900_and_1400(self):
        """29. Light and dark, creaite and Cursor palettes, at 1400 px and 900 px: the hub, the report and the dialogs."""
        seen = 0
        for w, h in H.WIDTHS:
            self.open_hub(w, h)
            self.q(CONTRAST_JS)
            for palette in TEST_PALETTES:
                for mode in ("light", "dark"):
                    with self.subTest(width=w, palette=palette, mode=mode):
                        self.theme(palette, mode)
                        self.assertEqual(self.q("document.documentElement.dataset.theme"), mode)
                        # the hub: no sideways scroll, every toolbar control inside the window, the cog last
                        over = self.q("document.documentElement.scrollWidth - window.innerWidth")
                        self.assertLessEqual(over, 1, f"the page scrolls sideways by {over} px")
                        boxes = self.q("""[...document.querySelectorAll('#v-reporting .sheet-bar button')].filter(b=>b.offsetParent)
                          .map(b=>{const r=b.getBoundingClientRect();return [b.id||b.textContent.trim(),Math.round(r.left),Math.round(r.right)]})""")
                        self.assertTrue(boxes, "the toolbar has buttons")
                        for name, left, right in boxes:
                            self.assertGreaterEqual(left, 0, f"{name} is off the left edge")
                            self.assertLessEqual(right, w, f"{name} is off the right edge")
                        # the report: text readable on its paper
                        for sel in ("#v-reporting .page", "#v-reporting .page section[data-id] h2", "#hubExport", "#hubCfg"):
                            c = self.q(f"window.__contrast({json.dumps(sel)})")
                            self.assertIsNotNone(c, f"{sel} is on the page")
                            self.assertGreaterEqual(c["ratio"], 3.0, f"{sel}: {c['fg']} on {c['bg']}")
                        # the dialogs: the cog's panel and the export menu are painted, inside the window
                        self.press("#hubCfg")
                        self.b.wait("document.querySelector('.hubcfg')", 10)
                        panel = self.q("""(()=>{const e=document.querySelector('.hubcfg'),r=e.getBoundingClientRect(),
                          c=getComputedStyle(e).backgroundColor; return {l:r.left,r:r.right,t:r.top,b:r.bottom,w:r.width,bg:c}})()""")
                        self.assertGreater(panel["w"], 100)
                        self.assertGreaterEqual(panel["l"], 0)
                        self.assertLessEqual(panel["r"], w + 1)
                        self.assertNotIn(panel["bg"], ("rgba(0, 0, 0, 0)", "transparent"), "the panel has a background")
                        self.b.key("Escape")
                        self.b.wait("!document.querySelector('.hubcfg')", 5)
                        self.press("#hubExport")
                        self.b.wait("document.querySelector('.ddmenu.on')", 10)
                        menu = self.q("""(()=>{const r=document.querySelector('.ddmenu.on').getBoundingClientRect();
                          return {l:r.left,r:r.right,bg:getComputedStyle(document.querySelector('.ddmenu.on')).backgroundColor}})()""")
                        self.assertGreaterEqual(menu["l"], 0)
                        self.assertLessEqual(menu["r"], w + 1)
                        self.assertNotIn(menu["bg"], ("rgba(0, 0, 0, 0)", "transparent"))
                        self.b.key("Escape")
                        self.b.wait("!document.querySelector('.ddmenu.on')", 5)
                        seen += 1
        self.assertEqual(seen, len(H.WIDTHS) * len(TEST_PALETTES) * 2)

    def test_the_toolbar_week_menu_section_menu_cog_and_export_work_from_the_keyboard(self):
        """30. Keyboard: the toolbar, the week menu, the section menu, the cog panel and the export dialog work without a mouse; Esc
        closes each."""
        self.open_hub()
        # the toolbar: every control is a real, enabled button that a key can reach (in the page's tab order) and that shows focus
        ids = [e for e in self.q("""[...document.querySelectorAll('#v-reporting .sheet-bar button')].filter(b=>b.offsetParent).map(b=>b.id||b.dataset.hv||'')""")]
        for need in ("hubWeek", "zOut", "zVal", "zIn", "hubExp", "hubExport", "hubApprove", "hubCfg", "internal", "client", "side"):
            self.assertIn(need, ids, f"{need} is on the toolbar")
        for el in self.q("[...document.querySelectorAll('#v-reporting .sheet-bar button')].filter(b=>b.offsetParent&&!b.disabled).map(b=>b.id||b.dataset.hv)"):
            sel = f"#{el}" if el in ("hubWeek", "zOut", "zVal", "zIn", "hubExp", "hubExport", "hubApprove", "hubCfg") else f"[data-hv='{el}']"
            r = self.q(f"(()=>{{const b=document.querySelector({json.dumps(sel)}); b.focus(); return [b.tabIndex>=0, b.tagName, document.activeElement===b]}})()")
            self.assertEqual(r, [True, "BUTTON", True], f"{el} is a focusable button")
        # the view switch: Enter on a button changes the view
        self.q("document.querySelector('#hubSeg [data-hv=client]').focus()")
        self.b.key("Enter")
        self.b.wait("document.querySelector('#hubSeg [data-hv=client]').getAttribute('aria-pressed')==='true'", 10)
        self.q("document.querySelector('#hubSeg [data-hv=internal]').focus()")
        self.b.key("Enter")
        self.b.wait("document.querySelector('#hubSeg [data-hv=internal]').getAttribute('aria-pressed')==='true'", 10)
        # zoom: Enter on - zooms out (Fit is the largest), Enter on the percentage returns to Fit
        self.q("document.querySelector('#zOut').focus()")
        self.b.key("Enter")
        self.b.wait("document.querySelector('#zVal').textContent!=='Fit'", 10)
        self.q("document.querySelector('#zVal').focus()")
        self.b.key("Enter")
        self.b.wait("document.querySelector('#zVal').textContent==='Fit'", 10)
        # the week menu, the export menu and the approve menu: Enter opens, Esc closes and focus goes back to the button
        for opener, popup in (("#hubWeek", ".wkpop"), ("#hubExport", ".ddmenu.on"), ("#hubApprove", ".ddmenu.on")):
            with self.subTest(opener):
                self.q(f"document.querySelector({json.dumps(opener)}).focus()")
                self.b.key("Enter")
                self.b.wait(f"document.querySelector({json.dumps(popup)})", 10)
                self.b.key("Escape")
                self.b.wait(f"!document.querySelector({json.dumps(popup)})", 10)
                self.assertTrue(self.q(f"document.activeElement===document.querySelector({json.dumps(opener)})"), "focus returns")
        # the export dialog: Enter, arrow keys and Enter choose a format, then the which-report question; Esc closes it
        self.q("document.querySelector('#hubExport').focus()")
        self.b.key("Enter")
        self.b.wait("document.querySelector('.ddmenu.on [role^=menuitem]')", 10)
        self.assertTrue(self.q("document.querySelector('.ddmenu.on').contains(document.activeElement)"), "focus moves into the menu")
        self.b.key("Enter")                                   # the first format
        self.b.wait("document.querySelector('[data-hubpick]')", 10)
        self.assertTrue(self.q("document.querySelector('.ddmenu.on').contains(document.activeElement)"))
        self.b.key("ArrowDown")
        self.b.key("Escape")
        self.b.wait("!document.querySelector('[data-hubpick]')", 10)
        # the cog's panel: Enter opens it, Esc closes it and returns to the cog
        self.q("document.querySelector('#hubCfg').focus()")
        self.b.key("Enter")
        self.b.wait("document.querySelector('.hubcfg')", 10)
        self.b.key("Escape")
        self.b.wait("!document.querySelector('.hubcfg')", 10)
        self.assertTrue(self.q("document.activeElement===document.querySelector('#hubCfg')"), "focus returns to the cog")
        # the section menu: Enter on a section's chevron, arrows move, Esc closes and returns focus
        btn = "#v-reporting section[data-id=risks] .sheet-hbtn"
        self.q(f"document.querySelector({json.dumps(btn)}).focus()")
        self.b.key("Enter")
        self.b.wait("!!document.querySelector('.pophost [role=menu]')", 5)
        first = self.q("document.activeElement.textContent.trim()")
        self.b.key("ArrowDown")
        self.assertNotEqual(self.q("document.activeElement.textContent.trim()"), first, "arrows move")
        self.b.key("Escape")
        self.b.wait("!document.querySelector('.pophost [role=menu]')", 5)
        self.assertTrue(self.q(f"document.activeElement===document.querySelector({json.dumps(btn)})"), "focus returns to the chevron")

    def test_left_out_stays_out_when_reopened_and_a_client_export_is_refused_before_approval(self):
        """32. Left out items stay out when the report is reopened, and a client export is refused before the internal one is
        approved."""
        d = self.api("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": WEEK})
        doc = d["doc"]
        sec = {s["id"]: s for s in doc["sections"]}
        rows = len(sec["risks"]["rows"])
        self.assertGreater(rows, 1)
        gone = sec["risks"]["rows"][0]
        gone["shown"] = False
        sec["decisions"]["hidden"] = True
        saved = self.api("/api/report/save", {"doc": doc, "base_version": d.get("version") or None})
        self.assertTrue(saved["ok"], saved)
        # reopened from the server: still out
        again = self.api("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": WEEK})["doc"]
        s2 = {s["id"]: s for s in again["sections"]}
        self.assertEqual(s2["risks"]["rows"][0].get("shown"), False)
        self.assertTrue(s2["decisions"].get("hidden"))
        # reopened in the page (a reload and the hub again): the exported view leaves them out
        self.open_hub()
        self.b.click("#hubExp")
        self.b.wait("document.querySelector('#hubExp').getAttribute('aria-pressed')==='true'", 10)
        self.b.pump(0.4)
        self.assertEqual(self.q("document.querySelectorAll('#v-reporting [data-id=risks] tbody tr').length"), rows - 1)
        self.assertEqual(self.q("document.querySelectorAll('#v-reporting section[data-id=decisions]').length"), 0)
        self.b.click("#hubExp")
        # a client export before the internal week is approved: the check says not ready, and the page exports nothing
        chk = self.api("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": WEEK})
        c = self.api("/api/report/check", {"doc": chk["doc"]})
        self.assertTrue(c["ok"], c)
        self.assertFalse(c["left_out"]["ready"])
        self.assertIn("Approve the internal weekly report", c["left_out"]["not_ready"])
        self.q("""window.__calls=[]; (()=>{const f=window.fetch.bind(window); window.fetch=(u,o)=>{ if(String(u).includes('/api/report/export')) window.__calls.push(String(u)); return f(u,o); };})()""")
        self.press("#hubExport")
        self.pick_item("PDF")
        self.b.wait("document.querySelector('[data-hubpick=client]')", 10)
        self.press("[data-hubpick='client']")
        self.b.wait("document.querySelector('#crLeftDlg[open] [data-crleft-list]')", 20)
        self.assertIn("Approve the internal weekly report", self.q("document.querySelector('#crLeftDlg').innerText"))
        self.assertEqual(self.q("window.__calls"), [], "nothing was exported")


if __name__ == "__main__":
    unittest.main()
