"""BL-341 (#212): creaite 2.3.0's hand checks (dev/handchecks/v2.3.0.md, the Product Manager's sheet), automated against a vault
made from the release zip.
Run them all, fill the Results table and make the screenshot sheet:  python3 dev/tools/handcheck.py v2.3.0
Run this file on its own (it makes the vault itself):                 python3 dev/tests/handchecks/test_v230.py

One method per check, `test_cNN_…`, its docstring quoting the check. The groups are separate classes; those that change data
(checks 2, 4, 5, 6, 9, 10 and 11) are mixins combined into one `Changing` class with a vault of its own, because building
a vault is the slow step:
  TopBar        1                   the top bar hides on scroll and comes back at the top (shared vault)
  FilesToday    3, 7, 8, 13         Files, Choose a project, People, the design scale (shared vault, nothing changed)
  SideBar       2                   Customise sidebar: Small, Medium, Large
  TodayLine     4, 5                Intake and Review as one line; the late-sweep banner
  NotesMenu     6                   right-click a note
  ActivityHand  9                   "You, by hand"
  DraftEmail    10, 12              the two Review items and the person menu
  SentIt        11                  "I sent it"
The 2.3.1 patch checks (14 to 17 in the sheet) are in test_v231.py.
Kinds (the Product Manager's map, confirmed as built): 1, 2, 8 and 13 measurable; the rest scriptable; none is judgement or live only
as a whole. The judgement parts (how the top bar feels, whether icons are sharp, Files against its mockup, the calm of Today, the
Choose a project page) are on the screenshot sheet (checks 2, 3, 4, 7); a real sweep (5) is live only and is noted on its row.
Desktop (1400 px) and 900 px only. Never Microsoft 365, never a real model: Claude is the hand-check vault's stand-in.
Helpers: hcbase.HandcheckCase (screens, notes, the sheet, own vaults), measure.py (CDP measures), sheet.py.

Numbering follows dev/handchecks/v2.3.0.md.
"""
import json
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import measure
import test_rail_icon_size as tris
import test_topbar_hide as tbh
from hcbase import NOTES, SCREENS, HandcheckCase, db_rows

KIND = {**{n: "scriptable" for n in (3, 4, 5, 6, 7, 9, 10, 11, 12)},
        **{n: "measurable" for n in (1, 2, 8, 13)}}

# No check is live only as a whole. Parts that are: a real sweep (5), a real recipient's mailbox (11, 14), a real model's wording.
LIVE_ONLY = {}
NOTES.update({
    5: "the stand-in Claude answers the sweep; a real sweep (mail, Teams, the calendar) is live only",
    11: "nothing is sent: what Outlook or Word draws from the copied email is live only",
})

SCREENS.update({
    "weekly": ("go('weekly',{code:'FAL'})", "document.querySelector('#v-weekly section[data-id=current_state]')"),
    "cockpit-choose": ("go('cockpit')", "!!document.querySelector('#v-cockpit a[data-choose]')"),
    "milestones-choose": ("go('milestones')", "!!document.querySelector('#v-milestones a[data-choose]')"),
})


class V230Case(HandcheckCase):
    """Helpers the groups share: the page's own API token, seeding through propose.py and tracker.py, a Python probe in the vault."""
    width, height = 1400, 1000

    def api(self, path, body=None):
        """POST to the live server as the page does (its token); the JSON answer."""
        token = self.b.eval("D.token")
        req = urllib.request.Request(self.base + path, data=json.dumps(body or {}).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": token})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            try:
                return json.loads(e.read().decode())
            except ValueError:
                return {"ok": False, "message": f"HTTP {e.code}"}

    def seed(self, items, source="cx-edit"):
        """Items as cx-edit makes them: propose.py stage, then tracker.py apply (the one writer). Raises if either refuses."""
        f = self.vault / "system/staging/drafts/hc-seed.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"source_run": source, "items": items}), encoding="utf-8")
        code, out = self.run_in_vault("propose.py", "stage", "system/staging/drafts/hc-seed.json")
        self.assertEqual(code, 0, out)
        code, out = self.run_in_vault("tracker.py", "apply")
        self.assertEqual(code, 0, out)

    def py(self, code):
        """Python in the vault (its system/scripts on the path, the clock pinned); the JSON the code prints."""
        r = subprocess.run([sys.executable, "-I", "-c", "import sys, json, sqlite3\nsys.path.insert(0, 'system/scripts')\n" + code],
                           cwd=self.vault, capture_output=True, text=True, check=False,
                           env={**__import__("os").environ, "CREAITE_NOW": self.now or ""})
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        return json.loads(r.stdout)

    def staged_updates(self, item_id):
        """Every staged dashboard proposal's update for an item: [changes]."""
        out = []
        for f in sorted((self.vault / "system/staging").glob("proposed-*-dashboard*.json")):
            for it in json.loads(f.read_text()).get("items", []):
                if it.get("id") == item_id and it.get("op") == "update":
                    out.append(it["changes"])
        return out

    def today_words(self):
        """The page's own today as Alan reads it (DD-MM-YYYY)."""
        return self.b.eval("fd(TODAY)")


# ── Top bar and side bar ─────────────────────────────────────────────────────

class TopBar(V230Case):
    """Check 1: the shared vault; nothing changes."""
    # #207's own test is the model: the same wheel ticks and the same measures
    open, centre, st = tbh.Pages.open, tbh.Pages.centre, tbh.Pages.st
    bar_h, off, press_wheel = tbh.Common.bar_h, tbh.Common.off, tbh.Common.press_wheel

    PAGES = (("Today", "go('today')"), ("Work", "go('work')"), ("Files", "go('files')"), ("Review", "go('review')"))

    def test_c01_top_bar_hides_on_scroll(self):
        """1. Scroll down any page (Today, Work, Files, Review, a report) → the top bar (search or jump, ask creaite, theme switch)
        goes; scroll back to the very top → it returns. On the Weekly report the slim bar's buttons never bring the header back."""
        b = self.b
        for name, call in self.PAGES:
            self.open(call, 1400, 1000)
            self.assertAlmostEqual(self.bar_h(), tbh.BAR, delta=1.5, msg=f"{name}: the bar is {tbh.BAR} px at the top")
            x, y = self.centre()
            self.press_wheel(x, y, 2)
            b.pump(0.1)
            self.assertTrue(self.off(), f"{name}: the first 2 px tick down hides the bar")
            b.eval("document.querySelector('[data-tbs]').scrollTop=900")
            b.pump(0.2)
            self.assertTrue(self.off(), f"{name}: it stays away while scrolled")
            b.eval("document.querySelector('[data-tbs]').scrollTop=0")
            b.pump(0.3)
            self.assertFalse(self.off(), f"{name}: scrolled back to the very top, the bar returns")
            self.assertAlmostEqual(self.bar_h(), tbh.BAR, delta=1.5, msg=name)
        # a report: the Weekly report, and its slim bar
        self.screen("weekly")
        b.pump(0.4)

        def tick(dy):
            r = b.eval("(()=>{const r=document.querySelector('#v-weekly .sheet-scroll').getBoundingClientRect();"
                       "const t=Math.max(r.top,60), bt=Math.min(r.bottom,innerHeight); return [r.left+r.width/2, t+(bt-t)/2]})()")
            b.call("Input.dispatchMouseEvent", type="mouseWheel", x=r[0], y=r[1], deltaX=0, deltaY=dy)
        self.assertAlmostEqual(self.bar_h(), tbh.BAR, delta=1.5, msg="Weekly report: bar at the top")
        tick(2)
        b.wait("!!document.querySelector('#v-weekly .sheet-root.rpt-slim')", 5)
        b.pump(0.3)
        self.assertTrue(self.off(), "Weekly report: the top bar goes")
        self.assertAlmostEqual(b.eval("document.querySelector('#v-weekly .sheet-bar').getBoundingClientRect().top"), 0, delta=1.5,
                               msg="the slim bar sits at the very top of the window")
        labels = b.eval("[...document.querySelectorAll('#v-weekly .sheet-bar button')].map(x=>x.getAttribute('aria-label')||x.textContent.trim())")
        self.assertGreaterEqual(len(labels), 4, labels)
        for lab in ("Zoom out", "Zoom in", "Show as exported"):         # the harmless ones are pressed; Export and Approve are only hovered
            b.eval(f"[...document.querySelectorAll('#v-weekly .sheet-bar button')].find(x=>(x.getAttribute('aria-label')||x.textContent.trim())==={json.dumps(lab)}).click()")
            b.pump(0.3)
            self.assertTrue(self.off(), f"pressing '{lab}' does not bring the header back")
        for lab in ("Zoom in", "Show as exported"):                     # put the zoom and the view back
            b.eval(f"[...document.querySelectorAll('#v-weekly .sheet-bar button')].find(x=>(x.getAttribute('aria-label')||x.textContent.trim())==={json.dumps(lab)}).click()")
        for sel in ("#v-weekly .sheet-bar .sheet-exp", "#wrApprove"):
            bx = b.box(sel)
            b.call("Input.dispatchMouseEvent", type="mouseMoved", x=bx["x"], y=bx["y"])
            b.pump(0.25)
            self.assertTrue(self.off(), f"hovering {sel} does not bring the header back")
        self.note(1, "Today, Work, Files, Review and the Weekly report; how the hiding feels is judgement")


class SideBarChecks:
    """Check 2: Customise sidebar's icon size. Own vault: it saves dashboard.rail_icon_size."""
    icon, rail_w, open_customise, choose = (tris.IconSizeBase.icon, tris.IconSizeBase.rail_w, tris.IconSizeBase.open_customise,
                                            tris.IconSizeBase.choose)

    def saved(self):
        return json.loads((self.vault / "system/config/settings.json").read_text())["dashboard"].get("rail_icon_size")

    def test_c02_sidebar_icon_size(self):
        """2. Customise sidebar offers Small, Medium, Large; Small equals today's look; the choice is remembered after a reload;
        the existing Customise features (order, hide) still work."""
        b = self.b
        self.assertEqual(self.icon(), [20, 20], "Small is today's look: 20 px icons")
        self.assertEqual(self.rail_w(), 188)
        self.open_customise()
        self.assertEqual(b.eval("[...document.querySelectorAll('#railCust .rcsz')].map(x=>[x.textContent.trim(),x.getAttribute('aria-pressed')])"),
                         [["Small", "true"], ["Medium", "false"], ["Large", "false"]])
        b.click("#railCustCancel")
        b.wait("!document.getElementById('railCust').open")
        got = {}
        for size, n in (("medium", 24), ("large", 28), ("small", 20)):
            self.choose(size)
            self.assertEqual(self.icon(), [n, n], size)
            self.assertEqual(self.rail_w(), 188, f"{size}: the rail's width is unchanged")
            self.assertEqual(b.eval(tris.CLIPPED), [], f"{size}: no name or count clipped")
            b.reload(wait_for="typeof go==='function' && LIVE")
            self.assertEqual(self.icon(), [n, n], f"{size}: remembered after a reload")
            self.assertEqual(self.saved(), size)
            got[size] = (self.icon(), self.rail_w())
        # the existing Customise features: move a page by its button, and back; Today is always first
        self.open_customise()
        b.click('#railCust li[data-rid="settings"] [data-mv="swap"]')
        self.assertEqual(b.eval("document.querySelector('#railCust ul[data-zone=top]').lastElementChild.dataset.rid"), "settings")
        self.assertEqual(b.eval("document.querySelectorAll('#railCust li[data-rid=today] button').length"), 0, "Today has no controls")
        b.click("#railCustDone")
        b.wait("!document.getElementById('railCust').open")
        self.assertTrue(b.eval("!!document.querySelector('#railMain button[data-v=settings]')"), "Settings moved into the sidebar")
        self.assertEqual(self.icon(), [20, 20], "the size survives a reorder")
        self.note(2, "icon box 20/24/28 px for Small/Medium/Large, expanded rail 188 px for all three (Team Stark, 18-10-2026: the sheet's "
                     "188/204/220 was the mockup's earlier idea and was dropped); sharpness is judgement, on the sheet (Large)")
        self.choose("large")        # the size most likely to show a stretched icon, for the sheet
        self.sheet(2, "today", palettes=measure.themes(b)[:2], widths=(1400, 900))


# ── Files, Choose a project, People, the design scale ────────────────────────

class FilesToday(V230Case):
    """Checks 3, 7, 8 and 13: the shared vault; nothing here changes data."""

    def test_c03_files_pills_and_filter(self):
        """3. Files shows four view pills and a Filter button beside them on the same line; the Filter opens the filter bar; the
        date filter opens a popup calendar."""
        b = self.b
        for width in (1400, 900):
            measure.width(b, width, 900)
            self.screen("files")
            b.wait("document.querySelector('#fquick [data-q]') && document.querySelector('#filesTbl tr[data-fp]')", 15)
            self.assertEqual(b.eval("[...document.querySelectorAll('#fquick .vchip')].map(x=>x.textContent)"),
                             ["All files", "Latest reports", "This week's meetings", "Archived"], width)
            mid = ("(s=>{const r=document.querySelector(s).getBoundingClientRect(); return r.top+r.height/2;})")
            pill, btn = b.eval(f"[{mid}('#fquick [data-q=\"all\"]'),{mid}('#fmBtn')]")
            self.assertLess(abs(pill - btn), 6, f"{width}: the Filter button is on the pills' line")
            self.assertTrue(b.eval("document.getElementById('fmBtn').textContent.trim()==='Filter' || !!document.querySelector('#fmBtn svg')"))
        measure.width(b, self.width, self.height)
        self.screen("files")
        b.click("#fmBtn")
        b.wait("document.getElementById('fmBtn').getAttribute('aria-expanded')==='true'", 5)
        self.assertTrue(b.eval("!!document.querySelector('#fmenu input[name=fsType]') && !!document.querySelector('#fmenu [data-cal=fsTo]')"),
                        "the filter bar has Type and the dates")
        b.click('#fmenu [data-cal="fsTo"]')
        b.wait("!!document.querySelector('.cal')", 5)
        self.assertTrue(b.eval("document.querySelectorAll('.cal button').length>20"), "a popup calendar with its days")
        b.key("Escape")
        self.note(3, "layout against files-navigation-v2-mockup.html is judgement, on the sheet")
        self.sheet(3, "files", palettes=measure.themes(b)[:2], widths=(1400, 900))

    def test_c07_choose_a_project(self):
        """7. With no project chosen, Cockpit and Milestones show "Choose a project" (not a blank page); choosing one fills the page."""
        b = self.b
        for page, view, sel in (("cockpit", "cockpit", "#v-cockpit"), ("milestones", "milestones", "#v-milestones")):
            b.eval(f"go({page!r})")
            b.wait(f"!!document.querySelector('{sel} a[data-choose]')", 15)
            c = b.eval(f"(()=>{{ const v=document.querySelector('{sel}'); return {{h1:(v.querySelector('h1')||{{}}).textContent, "
                       f"codes:[...v.querySelectorAll('a[data-choose]')].map(a=>a.dataset.code)}}; }})()")
            self.assertEqual(c["h1"], "Choose a project", page)
            self.assertEqual(sorted(c["codes"]), ["FAL", "MER", "ORX", "TID"], page)
            b.click(f"{sel} a[data-choose][data-code=FAL]")
            b.wait(f"VIEW==={view!r} && !document.querySelector('{sel} a[data-choose]') && document.querySelector('{sel}').textContent.length>200", 15)
            self.assertIn("Falcon Data Platform", b.eval(f"document.querySelector('{sel}').textContent"), page)
        self.sheet(7, "cockpit-choose", palettes=measure.themes(b)[:2], widths=(1400, 900))
        self.sheet(7, "milestones-choose", palettes=measure.themes(b)[:2], widths=(1400, 900))

    def test_c08_people_zeros_and_alignment(self):
        """8. People: every zero looks the same (one kind of zero); the counts are right-aligned."""
        b = self.b
        self.screen("people")
        zeros = n = 0
        sigs = set()
        for tab in ("work", "none"):
            b.click(f'#ptabs [data-ptab="{tab}"]')
            b.wait(f"PTAB==={tab!r}", 5)
            b.pump(0.2)
            heads = b.eval("[...document.querySelectorAll('#peopleTbl thead th.num')].map(h=>getComputedStyle(h).textAlign)")
            self.assertTrue(heads and all(h == "right" for h in heads), (tab, heads))
            cells = b.eval("[...document.querySelectorAll('#peopleTbl tbody td.num')].map(c=>{ const s=getComputedStyle(c); "
                           "return [c.textContent.trim(), s.textAlign, s.color, s.fontWeight, s.opacity, !!c.querySelector('a')]; })")
            for text, align, color, weight, opacity, link in cells:
                n += 1
                self.assertEqual(align, "right", (tab, text))
                self.assertNotIn(text, ("", "-", "—", "–"), "a zero is written 0, never a dash or blank")
                if text == "0":
                    zeros += 1
                    sigs.add((color, weight, opacity, link))
        self.assertGreater(zeros, 3, "the demo has zeros to compare")
        self.assertEqual(len(sigs), 1, f"every zero looks the same: {sigs}")
        self.note(8, f"{n} count cells right-aligned; {zeros} zeros, all one style")

    def test_c13_design_scale(self):
        """13. On every screen: fields are 32 px high, chips are 26 px pills, headings are 22 px and 16 px. Spot-check Work, Files,
        Settings, People, Review, Activity."""
        b = self.b
        measure_js = """(()=>{ const v=document.querySelector('.view:not([hidden])'); const vis=e=>e.offsetParent&&e.getBoundingClientRect().height>0;
          const r=e=>Math.round(e.getBoundingClientRect().height*10)/10;
          return {fields:[...v.querySelectorAll('input:not([type=checkbox]):not([type=radio]):not([type=hidden]):not([type=file]):not([type=range]):not([type=color]),select')].filter(vis).map(e=>[e.id||e.name||e.type,r(e)]),
            chips:[...v.querySelectorAll('.chip,.vchip')].filter(vis).map(e=>[r(e),getComputedStyle(e).borderRadius]),
            h1:[...v.querySelectorAll('h1')].filter(vis).map(e=>getComputedStyle(e).fontSize),
            h2:[...v.querySelectorAll('h2')].filter(vis).map(e=>getComputedStyle(e).fontSize)}; })()"""
        # the two deliberate exceptions the design system names: Files' centred vault search (--ctl-h-lg, 40 px) and Today's and Help's display title
        big_search = {"vsInput"}
        seen = {"fields": 0, "chips": 0, "h1": 0, "h2": 0}
        for name in ("work", "files", "settings-essentials", "people", "review", "activity"):
            self.screen(name, settle=0.5)
            m = b.eval(measure_js)
            for fid, h in m["fields"]:
                self.assertEqual(h, 40 if fid in big_search else 32, f"{name}: field {fid} is {h} px")
            for h, radius in m["chips"]:
                self.assertEqual(h, 26, f"{name}: a chip is {h} px")
                self.assertEqual(radius, "999px", f"{name}: a chip is a pill")
            for fs in m["h1"]:
                self.assertEqual(fs, "22px", f"{name}: the page title is {fs}")
            for fs in m["h2"]:
                self.assertEqual(fs, "16px", f"{name}: a section heading is {fs}")
            for k in seen:
                seen[k] += len(m[k])
        self.assertTrue(all(seen.values()), f"each kind was found on the six screens: {seen}")
        self.note(13, f"measured {seen['fields']} fields (32 px; Files' vault search 40 px by design), {seen['chips']} chips (26 px pills), "
                      f"{seen['h1']} page titles (22 px), {seen['h2']} section headings (16 px); Today and Help keep their 34 px display title by design")


# ── Today ────────────────────────────────────────────────────────────────────

class TodayLineChecks:
    """Checks 4 and 5: own vault (4 rejects what waits in Review; 5 writes last-sweep.txt)."""

    def test_c04_intake_and_review_one_line(self):
        """4. Today's Intake and Review is one quiet line, not a list, and opens Review/Intake when clicked; with nothing waiting
        the line is absent."""
        b = self.b
        self.screen("today")
        b.wait("document.getElementById('tdLine')", 15)
        o = b.eval("""(()=>{ const l=document.getElementById('tdLine'); return {rows:document.querySelectorAll('#tdList>li.td-review,#tdList>li.td-transcript').length,
          text:l.textContent.trim(), links:[...l.querySelectorAll('a')].map(a=>[a.dataset.tdline,a.getAttribute('href')]),
          pending:REV.filter(r=>!r.done).length, h:Math.round(l.getBoundingClientRect().height), next:document.getElementById('tdSec').nextElementSibling.id}; })()""")
        self.assertEqual(o["rows"], 0, "no per-item rows")
        self.assertGreater(o["pending"], 0, "the demo has proposals waiting")
        self.assertIn(f"{o['pending']} proposal", o["text"])
        self.assertLess(o["h"], 60, f"one line, not a list ({o['h']} px)")
        self.assertEqual(o["next"], "weekSec", "just above the Week ahead")
        href = dict(o["links"])["review"]
        self.assertEqual(href, "#review")
        b.click("#tdLine [data-tdline=review]")
        b.wait("VIEW==='review'", 10)
        self.sheet(4, "today", palettes=measure.themes(b)[:2], widths=(1400, 900))
        # nothing waiting: reject every proposal in Review, and the line is absent
        code, out = self.run_in_vault("review.py", "reject", "all")
        if code:
            ns = ",".join(str(r["n"]) for r in b.eval("REV.filter(r=>!r.done).map(r=>({n:r.n}))"))
            code, out = self.run_in_vault("review.py", "reject", ns)
        self.assertEqual(code, 0, out[-300:])
        for f in (self.vault / "inbox").iterdir():      # and the demo's one new file in Intake is put aside
            f.rename(self.vault / "system/staging/drafts" / ("hc-aside-" + f.name))
        b.reload("typeof go==='function' && LIVE")
        self.screen("today")
        b.pump(0.6)
        self.assertEqual(b.eval("REV.filter(r=>!r.done).length"), 0, "Review is empty")
        left = b.eval("({line:tdLine().map(x=>x.key+':'+x.n), text:(document.getElementById('tdLine')||{}).textContent, hidden:document.getElementById('tdSec').hidden})")
        self.assertEqual(left["line"], [], f"nothing waits in Review or Intake: {left}")
        self.assertTrue(b.eval("!document.getElementById('tdLine') || document.getElementById('tdSec').hidden || !document.getElementById('tdLine').textContent.trim()"),
                        f"with nothing waiting the line is absent: {left}")

    def test_c05_sweep_due_banner(self):
        """5. When the last sweep is before 07:00 today and it is later than 07:00, Today shows "Sweep due since 07:00" with a Run
        sweep button; the button runs the sweep; the banner goes when the sweep finishes."""
        b = self.b
        day = (datetime.strptime(self.now, "%Y-%m-%d %H:%M") - timedelta(days=1)).strftime("%Y-%m-%d")
        last = self.vault / "system/staging/last-sweep.txt"
        last.write_text(f"{day} 07:30\n", encoding="utf-8")
        code, out = self.run_in_vault("build_dashboard.py")
        self.assertEqual(code, 0, out[-300:])
        b.reload("typeof go==='function' && LIVE")
        self.screen("today")
        visible = ("(()=>{const e=document.getElementById('sweepDue'); return !!e && !e.hidden && e.offsetParent!==null "
                   "&& getComputedStyle(e).display!=='none';})()")
        b.wait(visible, 15)
        self.assertIn("Sweep due since 07:00", b.eval("document.getElementById('sweepDue').textContent"))
        self.assertEqual(b.eval("document.getElementById('sweepRun').textContent"), "Run sweep")
        b.click("#sweepRun")                       # the stand-in Claude runs the sweep
        b.wait("document.getElementById('chat').classList.contains('on')", 10)
        b.wait("/sweep/i.test(document.getElementById('chat').innerText)", 10)
        b.wait("/stand-in|Raise data access|HTML from the model/.test(document.getElementById('chat').innerText)", 60)    # the stand-in's reply
        b.pump(1.5)
        b.eval("closeChat()")                       # the chat's box has the focus, and the page waits while Alan is typing
        b.eval("document.activeElement && document.activeElement.blur()")
        # the sweep finishes: cx-sweep's last step records it (sweep.py done --normal), and the banner goes by itself
        code, out = self.run_in_vault("sweep.py", "done", "--started", self.now, "--normal", "--summary", "hand check")
        self.assertEqual(code, 0, out[-300:])
        b.wait(f"!({visible})", 30)
        self.assertIn(self.now[:10], (last.read_text() or ""), "last-sweep.txt holds today")


# ── Notes, Activity ──────────────────────────────────────────────────────────

class NotesMenuChecks:
    """Check 6: own vault (makes two notes)."""

    def make(self, title):
        b = self.b
        b.eval("go('notes','FAL')")
        b.wait("!!document.getElementById('notesNew')", 15)
        b.click("#notesNew")
        b.wait("document.getElementById('newNoteDlg').open", 10)
        b.eval(f"(()=>{{ const i=document.getElementById('nnTitle'); i.value={json.dumps(title)}; i.dispatchEvent(new Event('input',{{bubbles:true}})); }})()")
        b.eval("document.querySelector('#newNoteDlg input[value=\"blank\"]').click()")
        b.click("#nnMake")
        b.wait("!document.getElementById('newNoteDlg').open", 10)
        b.wait(f"noteCur.value&&noteCur.value.note.title==={json.dumps(title)}&&!!document.querySelector('.nbody.ProseMirror')", 15)
        b.eval("noteFlush()")
        b.wait("noteSave.value.state==='saved'", 15)

    def test_c06_right_click_a_note(self):
        """6. Right-click a note in the Notes list → that note's menu (unpin, mark confidential and so on) opens without opening
        the note."""
        b = self.b
        self.make("Alpha")
        self.make("Beta")
        b.eval("document.querySelectorAll('.nlist .ni').forEach(x=>x.dataset.notetitle=x.querySelector('b').textContent.replace('\\u25c6 ',''))")
        self.assertEqual(b.eval("noteCur.value.note.title"), "Beta")
        b.click('[data-notetitle="Alpha"]', button="right")
        b.wait("!!document.querySelector('.pophost [role=menu]')", 10)
        items = b.eval("[...document.querySelectorAll('.pophost [role=menuitem]')].map(x=>x.textContent)")
        self.assertTrue(any(i.startswith(("Pin", "Unpin")) for i in items), items)
        self.assertTrue(any("onfidential" in i for i in items), items)
        self.assertTrue(items[-1].startswith("Delete note"), items)
        self.assertEqual(b.eval("noteCur.value.note.title"), "Beta", "Alpha was not opened")
        self.assertEqual(b.eval("document.getElementById('noteTitle').value"), "Beta")
        b.eval("[...document.querySelectorAll('.pophost [role=menuitem]')].find(x=>x.textContent.startsWith('Mark confidential')).click()")
        b.wait("notesList.value.find(n=>n.title==='Alpha').confidential===true", 15)
        notes = next((self.vault / "projects").glob("FAL */")) / "notes"
        self.assertIn("confidential: true", (notes / "Alpha.md").read_text())
        self.assertNotIn("confidential: true", (notes / "Beta.md").read_text())
        self.assertEqual(b.eval("noteCur.value.note.title"), "Beta", "the menu acted on Alpha and left the open note alone")
        self.note(6, "the menu items: " + ", ".join(items[:4]))


class ActivityHandChecks:
    """Check 9: own vault (a hand edit is applied)."""

    def test_c09_activity_you_by_hand(self):
        """9. Activity: an entry made by hand says "You, by hand"; rows are evenly spaced; every row has a tick box."""
        b = self.b
        self.seed([{"op": "update", "table": "actions", "id": "FAL-A-002", "changes": {"priority": "High"}}], source="cx-edit")
        b.reload("typeof go==='function' && LIVE")
        self.screen("activity")
        b.wait("!!document.querySelector('#actTbl tbody tr')", 15)
        text = b.eval("document.getElementById('actTbl').innerText")
        self.assertIn("You, by hand", text)
        self.assertNotIn("cx-edit", text, "the command's name is not shown as the actor")
        k, f = b.eval("[...['#actTypeBtn','#actFunnel'].map(s=>{const r=document.querySelector(s).getBoundingClientRect(); return [r.top,r.height];})]")
        self.assertAlmostEqual(k[1], f[1], delta=0.5, msg=f"Kind {k[1]} px, funnel {f[1]} px")
        self.assertAlmostEqual(k[0], f[0], delta=0.5, msg="the Kind button and the funnel share a top")
        rows, boxes = b.eval("[document.querySelectorAll('#actTbl tbody tr').length, document.querySelectorAll('#actTbl tbody tr td.actck input[type=checkbox]').length]")
        self.assertGreater(rows, 1)
        self.assertEqual(rows, boxes, "every row has a tick box")
        # evenly spaced: rows that are one line tall share one height
        hs = b.eval("[...document.querySelectorAll('#actTbl tbody tr')].map(tr=>Math.round(tr.getBoundingClientRect().height))")
        common = max(set(hs), key=hs.count)
        self.assertGreaterEqual(hs.count(common), len(hs) // 2, f"row heights {sorted(set(hs))}")
        self.note(9, f"{rows} rows, {boxes} tick boxes, row heights {sorted(set(hs))} px")


# ── Draft email ──────────────────────────────────────────────────────────────

class DraftEmailChecks:
    """Checks 10 and 12. Own vault: check 10 adds an overdue action owned by a registered person (the demo's overdue ones are owned
    by an alias, "Rashid Al Suwaidi (Northgate)", which the menu does not offer Draft email for: see the report)."""

    def work_list(self):
        b = self.b
        b.eval('go("work"); setLayout(WT,"list")')
        b.wait('document.querySelectorAll("#workTbl tr[data-row]").length>=3', 15)

    def test_c10_both_review_items_read_draft_email(self):
        """10. Both Review items read "Draft email" (not "Chase")."""
        b = self.b
        self.seed([{"op": "new", "table": "actions", "values": {
            "project": "FAL", "description": "Send the ingestion test results", "owner": "Lena Fischer", "due_date": "2026-10-09",
            "raised": "2026-10-01", "source": "Alan (cx-edit), 2026-10-01"}}])
        b.reload("typeof go==='function' && LIVE")
        iid = db_rows(self.vault, "SELECT id FROM actions WHERE description = 'Send the ingestion test results'")[0]["id"]
        # an overdue action of someone else's: an update request and a chase are both offered
        labels = b.eval(f"cxWork('actions',{iid!r}).map(x=>x.label||'')")
        self.assertFalse([x for x in labels if x.startswith("Chase")], labels)
        self.assertEqual(labels.count("Draft email"), 2, labels)
        for index, mode in ((0, "update"), (1, "chase")):
            b.eval(f"cxWork('actions',{iid!r}).filter(x=>x.label==='Draft email')[{index}].run()")
            b.wait("document.getElementById('deDlg').open", 10)
            self.assertEqual(b.eval("DE.mode"), mode)
            b.eval("document.getElementById('deDlg').close()")
        # and as Alan meets it: a right-click on the row in Work
        self.work_list()
        b.click(f'#workTbl tr[data-row="{iid}"] td.title', button="right")
        b.wait('!!document.querySelector(".cxmenu")', 10)
        shown = b.eval('[...document.querySelectorAll(".cxmenu [role=menuitem]")].map(x=>x.textContent.trim())')
        self.assertEqual(sum(1 for x in shown if x.startswith("Draft email")), 2, shown)
        self.assertFalse([x for x in shown if x.startswith("Chase")], shown)
        b.key("Escape")
        self.note(10, "menu: " + ", ".join(x[:18] for x in shown if "mail" in x))

    def test_c12_right_click_a_name_draft_email(self):
        """12. Right-click a person's name → Draft email for that person."""
        b = self.b
        self.work_list()
        b.click('#workTbl a[data-person="Rashid Al Suwaidi"]', button="right")
        b.wait('!!document.querySelector(".cxmenu")', 10)
        labels = b.eval('[...document.querySelectorAll(".cxmenu [role=menuitem]")].map(x=>x.querySelector("span").firstChild.textContent)')
        self.assertEqual(labels, ["Draft email", "Open Rashid's page", "Copy email address"])
        b.eval('[...document.querySelectorAll(".cxmenu [role=menuitem]")].find(x=>x.textContent.startsWith("Draft email")).click()')
        b.wait("document.getElementById('deDlg').open", 10)
        self.assertEqual(b.eval("document.getElementById('deTitle').textContent"), "Draft email: Rashid Al Suwaidi")
        self.assertGreaterEqual(b.eval("document.querySelectorAll('#deInc [data-deit]').length"), 1)
        b.eval("document.getElementById('deDlg').close()")


class SentItChecks:
    """Check 11: own vault ("I sent it" stages updates; the check applies them and looks at the record)."""

    def test_c11_i_sent_it(self):
        """11. "I sent it" updates every sent item and the email stays internal."""
        b = self.b
        b.eval("S.ownDomains=['northgate.example','example.com']")          # every item starts ticked, as for a colleague
        b.eval("go('person','Rashid Al Suwaidi'); openDraftEmail('Rashid Al Suwaidi','update')")
        b.wait("document.getElementById('deDlg').open&&document.querySelector('#deInc [data-deit]')", 15)
        b.eval("document.querySelectorAll('#deInc [data-deit]').forEach(i=>{ if(!i.checked) i.click(); })")
        picked = b.eval("[...document.querySelectorAll('#deInc [data-deit]')].filter(c=>c.checked).map(c=>c.dataset.deit.split(':')[1])")
        self.assertGreaterEqual(len(picked), 2, picked)
        b.click("#deSent")
        b.wait("!document.getElementById('deDlg').open", 15)
        self.assertEqual(b.eval("document.getElementById('snackT').textContent"), f"Logged on {len(picked)} items.")
        day = self.today_words()
        line = re.compile(rf"^{re.escape(day)}: Emailed Rashid Al Suwaidi by email asking for an update\.$")
        for i in picked:
            ch = self.staged_updates(i)
            self.assertEqual(len(ch), 1, f"{i}: one update staged")
            first = [str(v).split("\n")[0] for v in ch[0].values() if isinstance(v, str)]
            self.assertTrue(any(line.match(x) for x in first), (i, ch[0]))
        code, out = self.run_in_vault("tracker.py", "apply")
        self.assertEqual(code, 0, out[-300:])
        rec = db_rows(self.vault, "SELECT id, latest_update FROM actions WHERE id = ?", picked[0])[0] if picked[0].count("-A-") else None
        if rec:
            self.assertIn("Emailed Rashid Al Suwaidi", rec["latest_update"], "the tracker keeps the line")
        # internal: no client path carries it (the client wording context and the client text check)
        ctx = self.py("""import report
con = sqlite3.connect('system/tracker.db'); con.row_factory = sqlite3.Row
out = {}
for table, col in (('actions', 'description'), ('raid', 'description'), ('decisions', 'decision')):
    for r in con.execute(f"SELECT id FROM {table} WHERE project = 'FAL'"):
        out[r[0]] = json.dumps(report.client_item_context(con, r[0]), default=str)
print(json.dumps(out))""")
        for iid in picked:
            self.assertIn(iid, ctx)
            self.assertNotIn("Emailed Rashid", ctx[iid], f"{iid}: the client wording context never carries the line")
        facts = self.py("import report_doc\nprint(json.dumps(report_doc.client_facts('FAL'), default=str))")
        self.assertNotIn("Emailed", json.dumps(facts))
        found = self.py(f"""import client_leak
con = sqlite3.connect('system/tracker.db'); con.row_factory = sqlite3.Row
print(json.dumps(client_leak.text_findings(con, 'FAL', {day + ': Emailed Rashid Al Suwaidi by email asking for an update.'!r})))""")
        self.assertTrue([x for x in found if "chase" in x.lower() or "sent" in x.lower()], found)
        self.note(11, f"{len(picked)} items logged once each, kept in the tracker, absent from the client wording, facts and check")


# ── the checks that change data share one vault of their own ────────────────

class Changing(SideBarChecks, TodayLineChecks, NotesMenuChecks, ActivityHandChecks, DraftEmailChecks, SentItChecks, V230Case):
    """Checks 2, 4, 5, 6, 9, 10 and 11 in one vault of their own (building a vault is the slow step). Each check starts
    from what it needs and none relies on another; they run in check order."""
    own_vault = True


if __name__ == "__main__":
    import unittest
    unittest.main()
