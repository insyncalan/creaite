"""#221 + #217 (H2 of the Reporting hub): ONE sheet for the internal and the client report, with the weekly-report-tidy defects.

Real Chrome on the real live server (desktop only; no Claude runs). One shared class of checks, `SheetChecks`, is run for both
audiences (WeeklySheet = the internal report, ClientSheet = the client report), so a change to the sheet component shows in both and
both pass the same tests:
- one component: both views mount ReportSheet (source), and both pages carry the same structure marker and the same parts;
- one header: no repeated title block in the page; the title block reads 'Weekly report · Internal' / 'Client report · Client';
- logos at the right of the header (firm always), drawn straight on the page (no box, <= 36 x 180), on a light plate on dark;
- the health indicator is 96 px wide with the strip, its dates and Change inside it, flag text 12 px on one line;
- the section menu is a popup above the page: 13 px, an icon each, fully visible at 80/100/120% and 900 px, keyboard use;
- eye icons replace the dots; 'Add from the tracker' picks existing open items (client: client-visible only) and marks them New,
  and changes nothing in the tracker or the filed report; 16 px under the milestone timeline picture.

Run: python3 dev/tests/test_report_sheet.py      (Chrome tier; skipped without Chrome)
"""
import base64
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_dashboard as TD  # noqa: E402
import test_reports as R  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402

SRC = Path(__file__).resolve().parents[2] / "system/templates/dashboard/src/components/report"
PX = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")
PALETTES = ("creaite", "Brightwater")
MODES = ("light", "dark")
ZOOMS = (0.8, 1.0, 1.2)


def put_logos(v):
    logos = v.root / "system/branding/logos"
    logos.mkdir(parents=True, exist_ok=True)
    for name in ("firm.png", "ABC-client.png"):
        (logos / name).write_bytes(PX)


class OneComponent(unittest.TestCase):
    """brief 3: both views are the same sheet component (source level; the browser checks are below)."""

    def test_both_views_mount_the_one_report_sheet(self):
        for view in ("weekly/WeeklyView.jsx", "ClientView.jsx"):
            text = (SRC / view).read_text(encoding="utf-8")
            self.assertRegex(text, r"<ReportSheet\b", view)
            self.assertNotRegex(text, r"<Sheet\b", f"{view} must not mount Sheet directly")

    def test_the_client_has_no_renderer_of_its_own_for_the_shared_parts(self):
        text = (SRC / "ClientParts.jsx").read_text(encoding="utf-8")
        for gone in ("export function HeaderSection", "export function HealthSection", "export function TableSection"):
            self.assertNotIn(gone, text, "the client draws these with the shared parts")

    def test_no_dot_characters_in_the_sheet_sources(self):
        for f in SRC.rglob("*.jsx"):
            self.assertNotIn("◉", f.read_text(encoding="utf-8"), str(f))


class SheetChecks:
    """The checks, for either audience. A subclass says how its view opens (VIEW, AUDIENCE, open_view, ...)."""
    VIEW = AUDIENCE = TITLE = ""
    shared_server = True

    # ---- helpers -----------------------------------------------------------------------------------------------------------
    def start(self, w=1400, h=1000):
        self.b.resize(w, h)
        self.b.reload("typeof go==='function' && LIVE")
        self.open_view()
        self.b.pump(0.4)

    def q(self, js):
        return self.b.eval(js)

    def theme(self, palette, mode):
        self.q(f"document.documentElement.dataset.palette='{palette}'; document.documentElement.dataset.theme='{mode}'")
        self.b.pump(0.2)

    def press(self, selector):
        r = self.q(f"(()=>{{const r=document.querySelector({selector!r}).getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}})()")
        for kind in ("mouseMoved", "mousePressed", "mouseReleased"):
            self.b.call("Input.dispatchMouseEvent", type=kind, x=r[0], y=r[1], button="left", clickCount=1)
        self.b.pump(0.15)

    # ---- one component -----------------------------------------------------------------------------------------------------
    def test_one_sheet_same_structure(self):
        self.start()
        root = f"{self.VIEW} .sheet-root"
        self.assertEqual(self.q(f"document.querySelector('{root}').dataset.reportSheet"), self.AUDIENCE)
        parts = self.q(f"""(()=>{{const p=document.querySelector('{self.VIEW} .page');
          return ['header.wr-hd .wr-title .wr-eb','header.wr-hd .wr-logos','.wr-health .wr-hcol .wr-flag','.wr-health .wr-why',
            '.sheet-handle .sheet-hbtn','.rs-eye','.rs-pick-open'].filter(s=>!p.querySelector(s))}})()""")
        self.assertEqual(parts, [], "parts missing from the shared sheet")

    # ---- the header --------------------------------------------------------------------------------------------------------
    def test_one_title_block(self):
        self.start()
        page = f"{self.VIEW} .page"
        self.assertFalse(self.q(f"!!document.querySelector('{page} header.doc')"), "the page's repeated title block is gone")
        self.assertEqual(self.q(f"document.querySelectorAll('{page} h1').length"), 0)
        self.assertEqual(self.q(f"document.querySelectorAll('{page} .wr-eb').length"), 1)
        self.assertEqual(self.q(f"document.querySelector('{page} .wr-eb').textContent.trim()"), self.TITLE)
        self.assertIn("Example Programme", self.q(f"document.querySelector('{page} .wr-pn').textContent"))
        self.assertRegex(self.q(f"document.querySelector('{page} .wr-wk').textContent"), r"2026")

    def test_logos_at_the_right_drawn_straight_on_the_page(self):
        self.start()
        self.b.wait(f"document.querySelectorAll('{self.VIEW} .wr-logo img').length>=1", 10)
        r = self.q(f"""(()=>{{const h=document.querySelector('{self.VIEW} .wr-hd'), t=h.querySelector('.wr-title').getBoundingClientRect(),
          imgs=[...h.querySelectorAll('.wr-logo img')], i=imgs[0], c=getComputedStyle(i), b=i.getBoundingClientRect(), s=h.closest('.sheet-a4')
          .style.transform; const k=Number((/scale\\(([\\d.]+)\\)/.exec(s)||[0,1])[1]);
          return {{n:imgs.length, right:b.left>=t.right-1, w:i.offsetWidth, h:i.offsetHeight, bg:c.backgroundColor, bd:c.borderTopWidth,
            sh:c.boxShadow, alt:i.alt}}}})()""")
        self.assertGreaterEqual(r["n"], 1)
        self.assertTrue(r["right"], "logos sit at the right of the title block")
        self.assertLessEqual(r["h"], 36)
        self.assertLessEqual(r["w"], 180)
        self.assertIn(r["bg"], ("rgba(0, 0, 0, 0)", "transparent"), "no box behind a logo on light")
        self.assertEqual(r["bd"], "0px")
        self.assertEqual(r["sh"], "none")
        self.assertRegex(r["alt"], r"logo$")

    def test_logos_sit_on_a_light_plate_on_dark(self):
        self.start()
        self.b.wait(f"document.querySelectorAll('{self.VIEW} .wr-logo img').length>=1", 10)
        self.theme("creaite", "dark")
        bg = self.q(f"getComputedStyle(document.querySelector('{self.VIEW} .wr-logo img')).backgroundColor")
        nums = [float(x) for x in re.findall(r"[\d.]+", bg)[:3]]
        self.assertGreater(min(nums), 200, f"a light plate on dark, got {bg}")

    # ---- the health indicator ----------------------------------------------------------------------------------------------
    def test_health_indicator_is_96_wide_in_both_palettes_light_and_dark(self):
        self.start()
        for palette in PALETTES:
            for mode in MODES:
                with self.subTest(palette=palette, mode=mode):
                    self.theme(palette, mode)
                    m = self.q(f"""(()=>{{const q=s=>document.querySelector('{self.VIEW} .wr-health '+s), w=e=>e?e.offsetWidth:0,
                      f=q('.wr-flag'), c=getComputedStyle(f), chg=q('.wr-chg'), tr=q('.wr-trend'), lb=q('.wr-tlbl');
                      return {{col:w(q('.wr-hcol')), flag:w(f), trend:w(tr), lbl:w(lb), chg:w(chg), chgCls:chg?chg.className:'',
                        fs:c.fontSize, oneLine:f.scrollWidth<=f.clientWidth && f.offsetHeight<=2.4*parseFloat(c.fontSize)+20,
                        fg:c.color, bg:c.backgroundColor, ws:c.whiteSpace}}}})()""")
                    self.assertEqual(m["col"], 96)
                    for k in ("flag", "trend", "lbl", "chg"):
                        self.assertLessEqual(m[k], 96, f"{k} stays inside the indicator")
                    self.assertGreater(m["chg"], 0, "the Change button is there")
                    self.assertIn("btn", m["chgCls"].split())
                    self.assertIn("sm", m["chgCls"].split())
                    self.assertEqual(m["fs"], "12px")
                    self.assertTrue(m["oneLine"], "the flag text never wraps")
                    self.assertNotEqual(m["fg"], m["bg"])

    # ---- the section menu --------------------------------------------------------------------------------------------------
    def open_menu(self, sid="risks"):
        self.q(f"document.querySelector('{self.VIEW} section[data-id={sid}] .sheet-hbtn').click()")
        self.b.wait("!!document.querySelector('.pophost [role=menu]')", 5)
        self.b.pump(0.15)

    def menu_report(self):
        return self.q("""(()=>{const m=document.querySelector('.pophost [role=menu]'), r=m.getBoundingClientRect(), rail=document.querySelector('.rail'),
          rr=rail?rail.getBoundingClientRect():{right:0}, items=[...m.querySelectorAll('[role^=menuitem]')];
          return {l:r.left,t:r.top,r:r.right,b:r.bottom,iw:innerWidth,ih:innerHeight,rail:rr.right,w:r.width,
            inScaled:!!m.closest('.sheet-a4'), names:items.map(i=>i.textContent.trim()),
            fs:items.map(i=>getComputedStyle(i).fontSize), icons:items.map(i=>!!i.querySelector('svg')),
            hit:items.map(i=>{const b=i.getBoundingClientRect(), e=document.elementFromPoint(b.left+b.width/2,b.top+b.height/2);
              return !!e && m.contains(e)}), disabled:items.map(i=>i.getAttribute('aria-disabled')),
            tips:items.map(i=>i.getAttribute('data-tip')||i.title||'')}})()""")

    def test_section_menu_is_a_discreet_popup_fully_visible_at_every_zoom_and_900(self):
        for w, h in ((1400, 1000), (900, 900)):
            for z in ZOOMS:
                with self.subTest(width=w, zoom=z):
                    self.start(int(w / z), int(h / z))
                    self.open_menu()
                    m = self.menu_report()
                    self.assertFalse(m["inScaled"], "the menu is a popup above the page, not inside the scaled page")
                    self.assertGreaterEqual(m["l"], m["rail"] - 0.5, "never under the side bar")
                    self.assertGreaterEqual(m["l"], 0)
                    self.assertGreaterEqual(m["t"], 0)
                    self.assertLessEqual(m["r"], m["iw"])
                    self.assertLessEqual(m["b"], m["ih"])
                    self.assertTrue(all(m["hit"]), "every item is visible and not covered")
                    self.assertTrue(all(f == "13px" for f in m["fs"]), m["fs"])
                    self.assertTrue(all(m["icons"]), "a small icon before each word")
                    self.assertLess(m["w"], 300, "never wider than needed")
                    for want in ("Leave out of the export", "Move up", "Move down", "Add a text section below"):
                        self.assertIn(want, [n.split("\n")[0].strip() for n in m["names"]])
                    self.b.key("Escape")

    def test_section_menu_at_every_sheet_zoom(self):
        self.start()
        for sel in ("Zoom out", "Zoom in"):
            for _ in range(8):
                self.q(f"document.querySelector('{self.VIEW} [aria-label=\"{sel}\"]').click()")
            self.b.pump(0.3)
            self.open_menu()
            m = self.menu_report()
            self.assertTrue(all(m["hit"]))
            self.assertEqual(set(m["fs"]), {"13px"}, "13px whatever the page's zoom")
            self.b.key("Escape")

    def test_section_menu_keyboard(self):
        self.start()
        btn = f"{self.VIEW} section[data-id=risks] .sheet-hbtn"
        self.q(f"document.querySelector('{btn}').focus()")
        self.b.key("Enter")
        self.b.wait("!!document.querySelector('.pophost [role=menu]')", 5)
        first = self.q("document.activeElement.textContent.trim()")
        self.assertIn("Leave out", first)
        self.b.key("ArrowDown")
        self.assertNotEqual(self.q("document.activeElement.textContent.trim()"), first, "arrows move")
        self.b.key("Escape")
        self.b.wait("!document.querySelector('.pophost [role=menu]')", 5)
        self.assertTrue(self.q(f"document.activeElement===document.querySelector('{btn}')"), "focus returns to the chevron")

    def test_add_text_section_is_disabled_with_a_tip_until_it_lands(self):
        self.start()
        self.open_menu()
        m = self.menu_report()
        i = [n.split("\n")[0].strip() for n in m["names"]].index("Add a text section below")
        self.assertEqual(m["disabled"][i], "true")
        self.assertTrue(m["tips"][i], "a tooltip says why")

    def test_leave_out_of_the_export_from_the_menu(self):
        self.start()
        self.open_menu("this_week")
        self.q("[...document.querySelectorAll('.pophost [role=menuitem]')].find(i=>/Leave out of the export/.test(i.textContent)).click()")
        self.b.wait(f"!!document.querySelector('{self.VIEW} [data-hidden=this_week]')", 5)

    # ---- the eyes ----------------------------------------------------------------------------------------------------------
    def test_eyes_replace_the_dots(self):
        self.start()
        r = self.q(f"""(()=>{{const e=[...document.querySelectorAll('{self.VIEW} .page .rs-eye')];
          return {{n:e.length, dots:/[◉○]/.test(document.querySelector('{self.VIEW} .page').textContent),
            icons:e.every(b=>b.querySelector('svg[data-icn=eye],svg[data-icn=eyeoff]')), names:e.every(b=>(b.getAttribute('aria-label')||'').length>3),
            pressed:e.every(b=>b.hasAttribute('aria-pressed')), size:e.map(b=>b.querySelector('svg').getBoundingClientRect().width)}}}})()""")
        self.assertGreaterEqual(r["n"], 3)
        self.assertFalse(r["dots"], "no dot character left in the sheet")
        self.assertTrue(r["icons"])
        self.assertTrue(r["names"], "accessible names")
        self.assertTrue(r["pressed"])

    def test_eye_toggles_and_slashes_in_both_palettes(self):
        self.start()
        sel = f"{self.VIEW} section[data-id=risks] tbody tr .rs-eye"
        for palette in PALETTES:
            self.theme(palette, "light")
            col = self.q(f"getComputedStyle(document.querySelector('{sel}')).color")
            self.assertNotEqual(col, "rgba(0, 0, 0, 0)")
        self.assertEqual(self.q(f"document.querySelector('{sel}').getAttribute('aria-pressed')"), "true")
        self.assertTrue(self.q(f"!!document.querySelector('{sel} svg[data-icn=eye]')"))
        self.q(f"document.querySelector('{sel}').click()")
        self.b.wait(f"document.querySelector('{sel}').getAttribute('aria-pressed')==='false'", 5)
        self.assertTrue(self.q(f"!!document.querySelector('{sel} svg[data-icn=eyeoff]')"), "left out shows the eye with a slash")
        self.assertTrue(self.q(f"document.querySelector('{sel}').closest('tr').matches('.hidrow,.crhid,.sheet-rowoff')"), "the row is dimmed")
        self.q(f"document.querySelector('{sel}').focus()")
        self.b.key(" ")
        self.b.wait(f"document.querySelector('{sel}').getAttribute('aria-pressed')==='true'", 5)

    # ---- Add from the tracker ----------------------------------------------------------------------------------------------
    PICK_SECTIONS = ("risks", "overdue")

    def open_picker(self, sid):
        self.q(f"document.querySelector('{self.VIEW} section[data-id={sid}] .rs-pick-open').click()")
        self.b.wait(f"!!document.querySelector('{self.VIEW} section[data-id={sid}] .rs-picker')", 10)
        self.b.wait(f"document.querySelectorAll('{self.VIEW} section[data-id={sid}] .rs-pick-row').length>0 || "
                    f"!!document.querySelector('{self.VIEW} section[data-id={sid}] .rs-pick-none')", 10)

    def pick_rows(self, sid):
        return self.q(f"[...document.querySelectorAll('{self.VIEW} section[data-id={sid}] .rs-pick-row')].map(r=>r.textContent)")

    def test_picker_lists_existing_open_items_not_already_in_the_report(self):
        self.start()
        for sid in self.PICK_SECTIONS:
            self.open_picker(sid)
            refs = self.pick_refs(sid)
            inside = self.q(f"[...document.querySelectorAll('{self.VIEW} section[data-id={sid}] tbody tr')].map(r=>r.dataset.ref)")
            self.assertTrue(refs, f"{sid}: something to pick")
            for r in refs:
                self.assertNotIn(r, inside, f"{sid}: {r} is already in the report")

    def pick_refs(self, sid):
        return self.q(f"[...document.querySelectorAll('{self.VIEW} section[data-id={sid}] .rs-pick-row')].map(r=>r.dataset.ref)")

    def test_picker_adds_an_existing_item_marked_new_and_saves_nothing_until_approve(self):
        self.start()
        sid = self.PICK_SECTIONS[0]
        before = self.q(f"document.querySelectorAll('{self.VIEW} section[data-id={sid}] tbody tr').length")
        tracker_before = self.v.rows("raid"), self.v.rows("actions")
        self.open_picker(sid)
        want = self.pick_refs(sid)[0]
        self.q(f"document.querySelector('{self.VIEW} section[data-id={sid}] .rs-pick-row input[type=checkbox]').click()")
        self.q(f"document.querySelector('{self.VIEW} section[data-id={sid}] .rs-pick-add').click()")
        self.b.wait(f"document.querySelectorAll('{self.VIEW} section[data-id={sid}] tbody tr').length=={before + 1}", 5)
        self.assertFalse(self.q(f"!!document.querySelector('{self.VIEW} section[data-id={sid}] .rs-picker')"), "the picker closes")
        row = f"{self.VIEW} section[data-id={sid}] tbody tr[data-ref='{want}']"
        self.b.wait(f"!!document.querySelector(\"{row} .rs-new\")", 5)
        self.assertTrue(self.q(f"!!document.querySelector(\"{row} .rs-new\")"), "marked New")
        self.assertEqual(self.q(f"document.querySelector(\"{row} .rs-new\").textContent.trim()"), "New")
        self.assertTrue(self.q(f"!!document.querySelector(\"{row} .rs-eye\")"), "with its eye")
        self.assertIn("Showing", self.q(f"document.querySelector('{self.VIEW} section[data-id={sid}] .wr-count, {self.VIEW} section[data-id={sid}] .crcount').textContent"))
        self.assertEqual((self.v.rows("raid"), self.v.rows("actions")), tracker_before, "the tracker is untouched")
        self.assertFalse(list(self.filed_reports()), "nothing is filed until Approve")
        # the exported view carries no editing marks
        self.q(f"[...document.querySelectorAll('{self.VIEW} .sheet-bar button')].find(b=>b.textContent==='Show as exported').click()")
        self.b.pump(0.3)
        self.assertFalse(self.q(f"!!document.querySelector('{self.VIEW} .rs-new')"), "New is an editing mark, not exported")
        self.assertFalse(self.q(f"!!document.querySelector('{self.VIEW} .rs-pick-open')"))

    def test_picker_cancel_changes_nothing(self):
        self.start()
        sid = self.PICK_SECTIONS[0]
        before = self.q(f"document.querySelector('{self.VIEW} section[data-id={sid}]').innerHTML")
        self.open_picker(sid)
        self.q(f"document.querySelector('{self.VIEW} section[data-id={sid}] .rs-pick-row input[type=checkbox]').click()")
        self.q(f"document.querySelector('{self.VIEW} section[data-id={sid}] .rs-pick-cancel').click()")
        self.b.wait(f"!document.querySelector('{self.VIEW} section[data-id={sid}] .rs-picker')", 5)
        self.assertEqual(self.q(f"document.querySelector('{self.VIEW} section[data-id={sid}]').innerHTML"), before)
        self.assertNotIn("Unsaved", self.q(f"document.querySelector('{self.VIEW} .sheet-status').textContent"))

    def test_picker_search_narrows_the_list(self):
        self.start()
        sid = self.PICK_SECTIONS[0]
        self.open_picker(sid)
        n = len(self.pick_rows(sid))
        self.q(f"(()=>{{const i=document.querySelector('{self.VIEW} section[data-id={sid}] .rs-picker input[type=search]'); i.value='zzzz-no-such'; "
               "i.dispatchEvent(new Event('input',{bubbles:true}))})()")
        self.b.wait(f"document.querySelectorAll('{self.VIEW} section[data-id={sid}] .rs-pick-row').length==0", 5)
        self.assertGreater(n, 0)



class WeeklySheet(SheetChecks, LiveBrowserCase):
    VIEW, AUDIENCE, TITLE = "#v-weekly", "internal", "Weekly report · Internal"

    @classmethod
    def load(cls, v):
        TD.populate(v)
        put_logos(v)
        v.propose("spare", [
            TD.new("raid", 30, project="ABC", type="Assumption", description="Spare assumption for the picker", impact="Low", likelihood="Low",
                   raised=TD.d(-2), source="s")])
        TD.stamped_apply(v)

    def open_view(self):
        self.b.eval("go('weekly',{code:'ABC'})")
        self.b.wait("document.querySelector('#v-weekly section[data-id=current_state]')", 20)

    def filed_reports(self):
        return [f for f in (self.v.root / "projects").rglob("*Weekly report*.html")]

    def test_16px_between_the_timeline_picture_and_the_milestone_list(self):
        self.start()
        self.q("[...document.querySelectorAll('#v-weekly .sheet-bar button')].find(b=>b.textContent==='Show as exported').click()")
        self.b.wait("document.querySelector('#v-weekly [data-id=milestones] .wr-tbl')", 5)
        gap = self.q("""(()=>{const s=document.querySelector('#v-weekly [data-id=milestones]'), a=s.querySelector('.wr-tlwrap'),
          b=s.querySelector('.wr-tbl'); const k=a.getBoundingClientRect().height/a.offsetHeight;
          return (b.getBoundingClientRect().top-a.getBoundingClientRect().bottom)/k})()""")
        self.assertAlmostEqual(gap, 16, delta=1, msg="the list starts 16px below the picture in Show as exported")


class ClientSheet(SheetChecks, LiveBrowserCase):
    VIEW, AUDIENCE, TITLE = "#v-clientreport", "client", "Client report · Client"
    PICK_SECTIONS = ("overdue",)       # the client report holds every client-visible risk already; client-visible actions that are not late are free to pick

    @classmethod
    def load(cls, v):
        R.populate(v)
        put_logos(v)
    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": R.NOW, "CREAITE_NO_LAUNCH": "1"}

    def open_view(self):
        self.b.eval("go('clientreport',{code:'ABC',week:'2026-10-09'})")
        self.b.wait("document.querySelector('#v-clientreport .wr-health')", 20)

    def filed_reports(self):
        return [f for f in (self.v.root / "projects").rglob("*Client report*.html")]

    def test_picker_offers_client_visible_items_only(self):
        self.start()
        self.open_picker("overdue")
        text = " ".join(self.pick_rows("overdue"))
        self.assertIn("The signed statement of work", text, "the client's own wording, not the internal title")
        self.assertNotIn("Sign the statement of work", text)
        for private in ("Escalate data access to the client CIO", "Confirm tester names"):
            self.assertNotIn(private, text, "an internal-only action is never offered")
        self.q("document.querySelector('#v-clientreport section[data-id=overdue] .rs-pick-cancel').click()")
        self.open_picker("risks")
        text = " ".join(self.pick_rows("risks"))
        self.assertNotIn("Vendor exits the market", text, "the internal-only risk is never offered")

    def test_match_internal_is_kept_per_section(self):
        self.start()
        self.assertTrue(self.q("!!document.querySelector('#v-clientreport [data-match=summary] .crmstate')"))
        self.assertTrue(self.q("!!document.querySelector('#v-clientreport [data-matchone=summary]')"))
        self.assertIn(self.q("document.querySelector('#v-clientreport [data-match=summary] .crmstate').textContent"),
                      ("Matching internal", "Edited for the client"))


if __name__ == "__main__":
    unittest.main()
