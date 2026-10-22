"""creaite 2.5.4's hand checks (the defects patch: #276, #277, #279 to #282, #284 to #287), automated against a vault made from the
release zip (the fictional demo portfolio: Falcon Data Platform and the rest).

Run them all, fill the Results table and make the screenshot sheet:  python3 dev/tools/handcheck.py v2.5.4
Run this file on its own (it makes the vaults itself):               python3 dev/tests/handchecks/test_v254.py

One check per item, `test_cNN_...`, its docstring quoting the item's own check (gh issue view N -R insyncalan/creaite-plan). There is
no Product Manager's sheet for 2.5.4 yet; the numbers are the items in order, so the PM can number them in:

   1 #276 a Replied (and nothing for you) line has Seen          6 #282 minutes exports say Actions
   2 #277 match-check refuses a non-string project code          7 #284 no ? button in Today's day band; the ? key opens Help
   3 #279 Prep with no project opens; the Project picker          8 #285 no project dropdown or arrows (project page, Milestones)
   4 #280 no `raised` on a decision; one bad item is held         9 #286 type icons name their type (and milestones, Week ahead)
   5 #281 the Draft email preview is resizable                   10 #287 the health Change menu is compact and inside the window

How a check is wired:
  Shared254     2, 5, 7 to 10   the shared hand-check vault; nothing is changed (the Draft email and the health menu are only opened)
  Messages254   1               a vault of its own: two conversations recorded with the check's own command (sweep.py vip record)
  Prep254       3               a vault of its own: a meeting no project matches added to the saved calendar (sweep.py calendar)
  Minutes254    4, 6            a vault of its own: minutes staged with minutes.py stage and applied with tracker.py apply

Check 4 (#280) needs two things that are not in the non-guarded 2.5.4 merge: the extractor fix (branch v254-280-4: minutes.py) and
the guarded tracker.py diff (dev/proposals/280/tracker.py.diff, applied by Jarvis). Until both are in the vault it skips and says
which is missing; with both it runs. (Checked: with v254-280-4 merged and no diff, it skips naming only tracker.py.diff.)

Check 5 also repeats Cap's HIGH on v254-281 (the grip dragged and let go below the Draft email dialog closes it): on 4b45fbe9 the
resize itself passes and that last step fails; on v254-release 9d90cefa (the fix in) the whole check passes.

Judgement only (for the PM's sheet; the checks take the screenshots where noted):
  1 the Seen eye's look on a quiet line, and whether "a later message reopens it" matches Alan's wish (a new ask reopens; chatter doesn't)
  3 the Project picker's look in the Prep page header
  5 whether the grip is easy to find and the preview tall enough to read the table (screenshots); the PDF/Outlook paste of the result
  6 the PDF export's heading (a PDF's text can't be read back here) and the Word export as Word draws it
  7 Today's day band without the ? (screenshots)
  9 the tooltip read by eye on each surface, and a screen reader's reading
 10 the menu against Alan's "second image" (it never reached the PM): compact and plain (screenshots, Claude and Retro Arcade)
Desktop (1400 px) and 900 px only. Never Microsoft 365, never a real model: Claude is the hand-check vault's stand-in.
"""
import json
import sys
import time
import unittest
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))      # dev/tests, for the helpers this borrows
import hcbase  # noqa: E402
from hcbase import NOTES, SCREENS  # noqa: E402,F401  (NOTES: read by handcheck.py)
from test_v230 import V230Case  # noqa: E402

NOTES.clear()                  # test_v230's own notes (its checks 5 and 11) are not 2.5.4's

KIND = {n: "scriptable" for n in range(1, 11)}
LIVE_ONLY = {}
JUDGEMENT = {1: "the Seen eye's look; reopen-on-a-new-ask as Alan wants it", 3: "the Project picker's look",
             5: "the grip found easily, tall enough to read the table", 6: "the PDF heading; Word as Word draws it",
             7: "the day band without the ?", 9: "tooltips by eye; a screen reader", 10: "the menu against Alan's second image"}

FAL = "FAL Falcon Data Platform"
RASHID = "Rashid Al Suwaidi <rashid@northgate.example>"
LENA = "Lena Fischer <lena.fischer@example.com>"
WORDS = ["Action", "Decision", "Risk", "Issue", "Assumption", "Dependency", "Milestone"]
ICONS = """(sel=>[...document.querySelectorAll(sel)].filter(e=>e.getClientRects().length).map(e=>[e.dataset.tip||null,e.getAttribute('aria-label'),
  e.getAttribute('role'),e.getAttribute('title'),(e.querySelector('svg')||{getAttribute:()=>null}).getAttribute('aria-hidden')]))"""
HEALTH_MENU = '.pophost [role=menu][aria-label="Health for this week"]'

SCREENS.update({
    "reporting": ("go('reporting','FAL')", "!!document.querySelector('#v-reporting .wr-chg')"),
})


class Case254(V230Case):
    """V230Case, plus a POST that gives back the HTTP status and a CDP drag."""

    def post(self, path, body):
        """POST as the page does (its token): (HTTP status, JSON answer). A fault gives its status, never an exception."""
        token = self.b.eval("D.token")
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": token})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            raw = e.read().decode(errors="replace")
            try:
                return e.code, json.loads(raw)
            except ValueError:
                return e.code, {"raw": raw[:300]}

    def drag(self, x, y0, y1):
        """A left-button drag from (x, y0) to (x, y1) through CDP, as a hand on the mouse."""
        b = self.b
        for kind, y in (("mouseMoved", y0), ("mousePressed", y0), ("mouseMoved", (y0 + y1) / 2), ("mouseMoved", y1),
                        ("mouseReleased", y1)):
            b.call("Input.dispatchMouseEvent", type=kind, x=x, y=y, button="left", clickCount=1)
        b.pump(0.3)

    def day(self):
        return (self.now or "")[:10]

    def until(self, fn, what, timeout=15):
        end = time.time() + timeout
        while time.time() < end:
            if fn():
                return
            self.b.pump(0.2)
        self.fail(what)


# ── the shared vault: nothing changes ────────────────────────────────────────

class Shared254(Case254):
    """Checks 2, 5, 7, 8, 9 and 10, in the shared hand-check vault. Nothing is written: the Draft email is opened and closed, the
    health menu opened and shut with Esc, and #277's documents are only checked."""

    # ── #277 ──
    def test_c02_match_check_refuses_a_project_code_that_is_not_a_string(self):
        """2. (#277) Match internal's check route (POST /api/report/match-check) sent a client document whose project code is a list (P22's
        seed 2), a number or an object answers a refusal Alan can read, never a fault (HTTP 500); a document with a string code is
        checked as before."""
        self.screen("today")
        doc = self.py(f"import creaite_doc\nprint(json.dumps(creaite_doc.new('client', 'FAL', 'Client report', {self.day()!r})))")
        seen = []
        for bad in (["FAL"], ["FAL", "ORX"], 7, {"code": "FAL"}, True):
            status, r = self.post("/api/report/match-check", {"docs": [{**doc, "project": bad}]})
            self.assertEqual(status, 200, f"project {bad!r}: HTTP {status} {r}")
            self.assertFalse(r.get("ok"), f"project {bad!r}: refused ({r})")
            self.assertTrue(r.get("message"), f"project {bad!r}: says why ({r})")
            self.assertNotIn("findings", r, bad)
            self.assertNotIn("Traceback", json.dumps(r), bad)
            seen.append(r["message"])
        status, r = self.post("/api/report/match-check", {"docs": [doc]})
        self.assertEqual(status, 200, r)
        self.assertTrue(r.get("ok"), f"a string code is still checked: {r}")
        self.assertIn("findings", r)
        self.note(2, f"5 malformed codes: HTTP 200 refused (\"{seen[0]}\"); a string code checked ({len(r['findings'])} finding(s))")

    # ── #281 ──
    def resize_case(self, sel, label):
        """Drag `sel`'s grip taller and shorter at 1400 and 900 px; the text keeps inside the box (no sideways scroll). Returns
        the heights seen."""
        b, out = self.b, []
        for w in (1400, 900):
            hcbase.measure.width(b, w, 1000)
            b.eval(f"document.querySelector({sel!r}).style.height=''")
            b.pump(0.3)
            self.assertEqual(b.eval(f"getComputedStyle(document.querySelector({sel!r})).resize"), "vertical", f"{label} at {w}")
            b.eval(f"document.querySelector({sel!r}).scrollIntoView({{block:'center'}})")
            b.pump(0.2)
            h0 = b.eval(f"document.querySelector({sel!r}).getBoundingClientRect().height")
            self.assertGreaterEqual(h0, 127.5, f"{label} at {w}: tall enough to start with")
            r = b.eval(f"(()=>{{const r=document.querySelector({sel!r}).getBoundingClientRect(); return {{x:r.right-6,y:r.bottom-6}}}})()")
            self.drag(r["x"], r["y"], r["y"] + 120)
            h1 = b.eval(f"document.querySelector({sel!r}).getBoundingClientRect().height")
            self.assertGreater(h1, h0 + 60, f"{label} at {w}: dragging the grip down makes it taller ({h0:.0f} → {h1:.0f})")
            b.eval(f"document.querySelector({sel!r}).scrollIntoView({{block:'center'}})")
            b.pump(0.2)
            r = b.eval(f"(()=>{{const r=document.querySelector({sel!r}).getBoundingClientRect(); return {{x:r.right-6,y:r.bottom-6,ih:innerHeight}}}})()")
            self.assertLess(r["y"], r["ih"], f"{label} at {w}: the grip is in the window")
            self.drag(r["x"], r["y"], r["y"] - 200)
            h2 = b.eval(f"document.querySelector({sel!r}).getBoundingClientRect().height")
            self.assertLess(h2, h1 - 100, f"{label} at {w}: dragging it up makes it shorter ({h1:.0f} → {h2:.0f})")
            self.assertGreaterEqual(h2, 127.5, f"{label} at {w}: never shorter than its minimum")
            wide = b.eval(f"(()=>{{const e=document.querySelector({sel!r}); const t=e.querySelector('table');"
                          f" return {{over:e.scrollWidth-e.clientWidth, table:t?t.getBoundingClientRect().width-e.clientWidth:null}}}})()")
            self.assertLessEqual(wide["over"], 1, f"{label} at {w}: the text reflows, no sideways scroll")
            if wide["table"] is not None:
                self.assertLessEqual(wide["table"], 1, f"{label} at {w}: the table fits the box")
            self.assertLessEqual(b.eval("document.scrollingElement.scrollWidth-innerWidth"), 0, f"{label} at {w}: no sideways page")
            out.append(f"{w}: {h0:.0f}→{h1:.0f}→{h2:.0f}")
            b.eval(f"document.querySelector({sel!r}).style.height=''")
        hcbase.measure.width(b, self.width, self.height)
        return out

    def test_c05_the_draft_email_preview_is_resizable(self):
        """5. (#281) The Draft email preview is user-resizable, built once for every entry point: the Draft email dialog (#dePrev: decision
        chase, action chase, update request, person page, Review) and the peek's chase pane (#chMail). Drag the grip taller and shorter;
        the text and table reflow. A drag that ends below the dialog does not close it."""
        b = self.b
        self.screen("today")
        b.eval("go('person','Rashid Al Suwaidi'); openDraftEmail('Rashid Al Suwaidi','chase')")
        b.wait("document.getElementById('deDlg').open&&document.querySelector('#dePrev')&&document.querySelector('#dePrev').textContent.length>40", 20)
        dialog = self.resize_case("#dePrev", "the Draft email dialog")
        self.note(5, "dialog " + "; ".join(dialog))
        # the peek's chase pane: an open action someone else owns
        b.eval("document.getElementById('deDlg').close()")
        hcbase.measure.width(b, self.width, self.height)
        item = b.eval("""(()=>{ const a=(D.actions||[]).find(x=>x.o&&!isMe(x.o)&&!['Closed','Cancelled'].includes(x.st)); return a&&a.id; })()""")
        self.assertTrue(item, "an open action someone else owns, for the peek's Draft email")
        b.eval(f"WT='actions'; go('work'); openRecord('actions',{item!r})")
        b.wait(f"CUR&&CUR.id==={item!r}&&document.getElementById('panel').classList.contains('peek')", 15)
        b.pump(0.3)
        b.click("#pkChaseBtn")
        b.wait("document.querySelector('#chMail')&&document.querySelector('#chMail').textContent.length>20", 20)
        pane = self.resize_case("#chMail", "the peek's chase pane")
        self.note(5, f"peek ({item}) " + "; ".join(pane))
        b.eval("closePanel()")
        # Cap's HIGH on v254-281: the grip dragged and let go below the dialog box (the most likely way to make it taller)
        b.eval("go('person','Rashid Al Suwaidi'); openDraftEmail('Rashid Al Suwaidi','chase')")
        b.wait("document.getElementById('deDlg').open&&document.querySelector('#dePrev').textContent.length>40", 20)
        b.eval("document.querySelector('#dePrev').scrollIntoView({block:'end'})")
        b.pump(0.3)
        g = b.eval("""(()=>{const r=document.querySelector('#dePrev').getBoundingClientRect(), d=document.getElementById('deDlg').getBoundingClientRect();
          return {x:r.right-6,y:r.bottom-6,dlg:d.bottom,ih:innerHeight}})()""")
        if g["dlg"] + 30 < g["ih"] and g["y"] < g["ih"]:
            self.drag(g["x"], g["y"], g["dlg"] + 30)
            still = b.eval("document.getElementById('deDlg').open")
            b.eval("document.getElementById('deDlg').open&&document.getElementById('deDlg').close()")
            self.assertTrue(still, "a grip drag let go below the dialog closes the Draft email (Cap's HIGH on v254-281, not fixed)")
            self.note(5, "a drag let go below the dialog leaves it open")
        else:
            b.eval("document.getElementById('deDlg').close()")
            self.note(5, "the dialog fills the window: a drag ending below it can't be made at 1400x1000")
        self.sheet(5, "today", palettes=["creaite"], modes=("light",), widths=(1400, 900),
                   prepare=lambda b: (b.eval("openDraftEmail('Rashid Al Suwaidi','chase')"),
                                      b.wait("document.getElementById('deDlg').open&&document.querySelector('#dePrev').textContent.length>40", 20)))
        b.eval("document.getElementById('deDlg').open&&document.getElementById('deDlg').close()")

    # ── #284 ──
    def test_c07_no_help_button_in_todays_day_band_and_the_key_still_opens_help(self):
        """7. (#284) The "?" button (Help for Today, left of the Close the day door in Today's day band) is gone, the Close the day door is
        unchanged, and the ? key still opens "Help · Today". Supersedes 2.5.1 checks 16 and 17."""
        b = self.b
        self.screen("today")
        b.wait("!!document.querySelector('#v-today .dayband')", 15)
        o = b.eval("""(()=>{ const band=document.querySelector('#v-today .dayband');
          const q=[...band.querySelectorAll('button,a,[role=button]')].filter(e=>e.textContent.trim()==='?'
            ||/^help/i.test(e.getAttribute('aria-label')||'')||/^help/i.test(e.dataset.tip||''));
          return {q:q.length, thelp:document.querySelectorAll('[data-thelp], .dhelp').length}; })()""")
        self.assertEqual(o, {"q": 0, "thelp": 0}, "no help ? in Today's day band")
        door = b.eval("""(()=>{ const b=document.getElementById('dayClose'); if(!b) return null; const cs=getComputedStyle(b), r=b.getBoundingClientRect();
          return {inBand:!!b.closest('.dayband'), dclose:b.dataset.dclose, popup:b.getAttribute('aria-haspopup'), door:!!b.querySelector('svg'),
            name:b.getAttribute('aria-label')||'', tip:b.dataset.tip||'', w:cs.width, h:cs.height, shown:r.width>0}; })()""")
        self.assertIsNotNone(door, "the Close the day door is there")
        self.assertEqual({k: door[k] for k in ("inBand", "dclose", "popup", "door", "w", "h", "shown")},
                         {"inBand": True, "dclose": "1", "popup": "dialog", "door": True, "w": "32px", "h": "32px", "shown": True})
        self.assertRegex(door["name"] + " " + door["tip"], r"(?i)close the day")
        b.eval("document.activeElement&&document.activeElement.blur&&document.activeElement.blur()")
        b.call("Input.dispatchKeyEvent", type="keyDown", key="?", code="Slash", text="?", windowsVirtualKeyCode=191, modifiers=8)
        b.call("Input.dispatchKeyEvent", type="keyUp", key="?", code="Slash", windowsVirtualKeyCode=191, modifiers=8)
        b.wait("document.getElementById('helpPanel').classList.contains('on')", 10)
        self.assertEqual(b.eval("document.getElementById('hpnT').textContent"), "Help · Today")
        b.key("Escape")
        b.pump(0.3)
        self.note(7, f"no ? in the band; the door \"{door['name'] or door['tip']}\" 32x32 unchanged; ? opens Help · Today")
        self.sheet(7, "today", palettes=["creaite", "Claude"], widths=(1400, 900))

    # ── #285 ──
    def test_c08_no_project_switcher_on_the_project_page_or_milestones(self):
        """8. (#285, with Alan's three follow-ups) The project page (cockpit) has no project dropdown, no ‹ › arrows and no [ ] keys; the
        Milestones page has no dropdown and no arrows. Every project stays reachable: the Projects list, search (⌘K), Today's project
        links, and a project's Milestones from its project page's Milestones card and the address #milestones=CODE."""
        b = self.b
        self.screen("cockpit")
        b.wait("VIEW==='cockpit'&&COCK==='FAL'&&!!document.querySelector('#v-cockpit .hhead h1')", 15)
        self.assertFalse(b.eval("!!document.getElementById('projSw')"), "no project dropdown")
        self.assertEqual(b.eval("document.querySelectorAll('#v-cockpit .hhead select').length"), 0, "no select in the header")
        self.assertEqual(b.eval("document.querySelectorAll('#v-cockpit .pswitch,#v-cockpit [data-psw]').length"), 0, "no ‹ › arrows")
        for k in ("]", "["):
            b.eval(f"document.body.focus(); document.dispatchEvent(new KeyboardEvent('keydown',{{key:{k!r},bubbles:true}}))")
            b.pump(0.3)
            self.assertEqual(b.eval("[VIEW,COCK]"), ["cockpit", "FAL"], f"the {k} key leaves the project page alone")
        codes = b.eval("P.map(p=>p.code)")
        self.assertGreaterEqual(len(codes), 2)
        reached = {"list": [], "search": [], "milestones": [], "address": []}
        for code in codes:
            b.eval("go('projects')")
            b.wait("VIEW==='projects'&&!!document.querySelector('#projTbl [data-cock]')", 15)
            b.eval(f"document.querySelector('#projTbl [data-cock=\"{code}\"]').click()")
            b.wait(f"VIEW==='cockpit'&&COCK==={code!r}&&!!document.querySelector('#v-cockpit [data-mvpage]')", 15)
            reached["list"].append(code)
            b.eval(f"document.querySelector('#v-cockpit [data-mvpage=\"{code}\"]').click()")
            b.wait(f"VIEW==='milestones'&&MSCODE==={code!r}&&!!document.querySelector('#v-milestones .mv-pageh h1')", 15)
            self.assertFalse(b.eval("!!document.getElementById('mvProjSw')"), f"{code}: no Milestones dropdown")
            self.assertEqual(b.eval("document.querySelectorAll('#v-milestones .mv-pageh select,#v-milestones .pswitch,#v-milestones [data-mvpsw]').length"),
                             0, f"{code}: no Milestones arrows")
            reached["milestones"].append(code)
        for p in b.eval("P.map(p=>({code:p.code,name:p.name}))"):
            b.eval("go('today')")
            b.wait("VIEW==='today'", 10)
            b.eval("openCk()")
            b.wait("document.getElementById('cmdk').open", 10)
            b.eval(f"(()=>{{ const i=document.getElementById('cmdkIn'); i.value={p['name']!r}; i.dispatchEvent(new Event('input',{{bubbles:true}})); }})()")
            b.pump(0.4)
            hit = b.eval(f"(()=>{{ const x=[...document.querySelectorAll('#cmdkList button')].find(e=>e.textContent.includes({p['name']!r})); if(x) x.click(); return !!x; }})()")
            self.assertTrue(hit, f"search finds {p['name']}")
            b.wait(f"VIEW==='cockpit'&&COCK==={p['code']!r}", 10)
            reached["search"].append(p["code"])
        b.eval("go('today')")
        b.wait("VIEW==='today'&&!!document.querySelector('#v-today [data-cock]')", 15)
        code = b.eval("document.querySelector('#v-today [data-cock]').dataset.cock")
        b.eval("document.querySelector('#v-today [data-cock]').click()")
        b.wait(f"VIEW==='cockpit'&&COCK==={code!r}", 10)
        for c in codes[:2]:
            b.eval(f"history.replaceState(null,'',location.pathname+'#milestones={c}&v=plan')")
            b.reload("typeof go==='function' && LIVE")
            b.wait(f"VIEW==='milestones'&&MSCODE==={c!r}&&!!document.querySelector('#v-milestones .mv-pageh h1')", 20)
            reached["address"].append(c)
        b.eval("history.replaceState(null,'',location.pathname); go('today')")
        self.note(8, f"no dropdown, arrows or [ ] keys; reached {len(codes)} projects by the list, search and the Milestones card; "
                     f"Today's link opened {code}; #milestones= for {', '.join(reached['address'])}")

    # ── #286 ──
    def named(self, sel):
        got = self.b.eval(f"{ICONS}({sel!r})")
        self.assertTrue(got, f"no type icon drawn at {sel}")
        for tip, name, role, title, hid in got:
            self.assertIn(tip, WORDS, sel)
            self.assertEqual((name, role, title, hid), (tip, "img", None, "true"), f"{sel}: the name in step, no native title")
        return {g[0] for g in got}

    def test_c09_type_icons_name_their_type_everywhere(self):
        """9. (#286) Hover the type icon of each kind (Action, Decision, Risk, Issue, Assumption, Dependency, and Milestone) on Today, Work,
        Review, search and the Milestones page: the app's one tooltip (data-tip) names the type, the accessible name says the same, no
        native title beside it. The Week ahead's Urgent-with-no-date and Further-ahead rows keep a RAID item's own type (never "Risk"
        for an Issue)."""
        b = self.b
        for k, w in (("action", "Action"), ("decision", "Decision"), ("Risk", "Risk"), ("Issue", "Issue"),
                     ("Assumption", "Assumption"), ("Dependency", "Dependency"), ("milestone", "Milestone")):
            h = b.eval(f"ico({k!r})")
            for want in (f'data-tip="{w}"', f'aria-label="{w}"', 'role="img"'):
                self.assertIn(want, h, k)
            self.assertNotIn("title=", h, k)
        for k, w in (("risk", "Risk"), ("issue", "Issue"), ("assumption", "Assumption"), ("dependency", "Dependency"),
                     ("action", "Action"), ("decision", "Decision"), ("milestone", "Milestone")):
            self.assertIn(f'data-tip="{w}"', b.eval(f"searchIco({k!r})"), f"search: {k}")
        # Work, each tab, and Review
        seen = set()
        self.screen("work")
        for tab in ("actions", "raid", "decisions"):
            b.click(f'#wtabs [data-t="{tab}"]')
            b.wait(f"WT==={tab!r}", 10)
            b.pump(0.3)
            seen |= self.named("#workTbl .ki")
        self.assertTrue({"Action", "Decision", "Risk"} <= seen, seen)
        self.screen("review")      # 2.6: Review is the Intake page (#232); its proposal rows' type icons, if any, are named too
        rev = self.named("#v-intake-review tr.irprop .ki") if b.eval("document.querySelectorAll('#v-intake-review tr.irprop .ki').length") else set()
        # hover shows the tooltip with the type's word
        self.screen("work")
        b.click('#wtabs [data-t="actions"]')
        b.wait("WT==='actions'", 10)
        b.pump(0.3)
        b.eval("document.querySelector('#workTbl .ki').scrollIntoView({block:'center'})")
        p = b.box("#workTbl .ki")
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=p["x"], y=p["y"], button="none")
        b.wait("(()=>{ const t=document.getElementById('tip'); return !!(t&&t.classList.contains('on')); })()", 5)
        hover = b.eval("document.getElementById('tip').textContent")
        self.assertEqual(hover, "Action")
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=5, y=990, button="none")
        # the Week ahead: the real data carries a RAID item's type in every group, and the rows name it
        data = b.eval("(()=>{ const W=D.week||{}; const all=[...(W.undated||[]),...(W.further||[]),...(W.days||[]).flatMap(d=>d.items||[])];"
                      " return all.filter(i=>i.kind==='raid').map(i=>[i.id,i.type||null]); })()")
        self.assertTrue(all(t for _, t in data), f"a RAID item in the Week ahead has no type: {data}")
        b.eval("""(()=>{ window.__wk=JSON.stringify(D.week); D.week=JSON.parse(window.__wk); D.week.days=[];
            D.week.undated=[{kind:"raid",id:"FAL-R-920",p:"FAL",t:"Undated issue",o:"Lena Fischer",pr:"Urgent",type:"Issue"}];
            D.week.further=[{date:pkAdd(TODAY,10),kind:"raid",id:"FAL-R-921",p:"FAL",t:"Later dependency",o:"Lena Fischer",pr:"High",type:"Dependency"},
                            {date:pkAdd(TODAY,11),kind:"milestone",id:"FAL-M-921",p:"FAL",t:"A milestone",slip:false}];
            D.week.further_to=pkAdd(TODAY,20); go('today'); renderToday(); return true; })()""")
        b.wait("document.querySelectorAll('#weekList .wkic').length>=3", 10)
        wk = b.eval(f"{ICONS}('#weekList .wkic').map(x=>x[0])")
        b.eval("D.week=JSON.parse(window.__wk); renderToday()")
        self.assertEqual(wk, ["Issue", "Dependency", "Milestone"], "Urgent with no date, then Further ahead")
        # the Milestones page's own markers, and the project page's card
        b.eval("MVAUD='int'; go('cockpit','FAL')")
        b.wait("VIEW==='cockpit'&&document.querySelector('#mvCard .mv-mk')", 15)
        marks = []
        for sel, how in (("#mvCard .mv-mk", None), ("#v-milestones .mv-mk", "plan"), ("#v-milestones .mv-track .fc", "move")):
            if how:
                b.eval(f"mvOpenPage('FAL',{how!r})")
                b.wait(f"VIEW==='milestones'&&!!document.querySelector({sel!r})", 15)
            got = b.eval(f"[...document.querySelectorAll({sel!r})].map(e=>[e.dataset.tip||'',e.getAttribute('aria-label')||'',e.getAttribute('title')])")
            self.assertTrue(got, sel)
            for tip, name, title in got:
                self.assertTrue(tip.startswith("Milestone: ") and len(tip) > 11, (sel, tip))
                self.assertEqual((name, title), (tip, None), sel)
            marks.append(f"{sel.split()[-1]} {len(got)}")
        b.eval("go('today')")
        self.note(9, f"ico and search name 7 types; Work {sorted(seen)}; Review {sorted(rev) or 'no rows'}; hover \"{hover}\"; "
                     f"Week ahead {len(data)} real RAID rows typed, undated/further {wk}; milestone marks {', '.join(marks)}")

    # ── #287 ──
    def open_health(self):
        b = self.b
        b.eval("document.querySelector('#v-reporting .wr-chg').scrollIntoView({block:'center'})")
        b.pump(0.2)
        b.eval("document.querySelector('#v-reporting .wr-chg').click()")
        b.wait(f"!!document.querySelector({HEALTH_MENU!r})", 5)
        b.pump(0.3)
        return b.eval(f"""((sel)=>{{const m=document.querySelector(sel); const r=m.getBoundingClientRect(), c=getComputedStyle(m),
          rail=document.querySelector('.rail'), rr=rail?rail.getBoundingClientRect():{{right:0}}, items=[...m.querySelectorAll('[role^=menuitem]')];
          return {{l:r.left,t:r.top,r:r.right,b:r.bottom,w:r.width,iw:innerWidth,ih:innerHeight,rail:rr.right,cls:m.className,
            scaled:!!m.closest('.sheet-a4'), outline:c.outlineStyle, names:items.map(i=>i.textContent.split('·')[0].trim()),
            h:items.map(i=>i.getBoundingClientRect().height), fs:items.map(i=>getComputedStyle(i).fontSize),
            roles:items.map(i=>i.getAttribute('role')), checked:items.filter(i=>i.getAttribute('aria-checked')==='true').length,
            hit:items.map(i=>{{const b=i.getBoundingClientRect(), e=document.elementFromPoint(b.left+b.width/2,b.top+b.height/2); return !!e&&m.contains(e)}})}}}})({HEALTH_MENU!r})""")

    def test_c10_the_health_change_menu_is_compact_and_inside_the_window(self):
        """10. (#287) The health Change menu (under the health block: On track / At risk / Off track) is a compact menu like the app's
        other small menus: plain, normal row height and text size, no heavy outline, fully inside the window and never clipped at
        either edge or under the side bar; in the Claude and Retro Arcade palettes too. All three options read; Esc closes it."""
        b = self.b
        was = b.eval("[S.palette, S.theme]")
        got = []
        try:
            for w in (1400, 900):
                for pal in ("Claude", "Retro Arcade", "creaite"):
                    hcbase.measure.width(b, w, 900)
                    hcbase.measure.theme(b, pal, "light")
                    self.screen("reporting", settle=0.5)
                    m = self.open_health()
                    where = f"{pal} at {w}"
                    self.assertFalse(m["scaled"], f"{where}: a popup above the page, not inside the scaled sheet")
                    self.assertGreaterEqual(m["l"], m["rail"] - 0.5, f"{where}: not under the side bar (clipped at the left)")
                    self.assertGreaterEqual(m["t"], 0, where)
                    self.assertLessEqual(m["r"], m["iw"], f"{where}: inside the right edge")
                    self.assertLessEqual(m["b"], m["ih"], f"{where}: inside the bottom")
                    self.assertLess(m["w"], 220, f"{where}: compact ({m['w']:.0f} px)")
                    self.assertEqual(m["names"], ["On track", "At risk", "Off track"], where)
                    self.assertTrue(all(m["hit"]), f"{where}: every option visible, nothing over it")
                    self.assertTrue(all(26 <= h <= 36 for h in m["h"]), f"{where}: normal row height {m['h']}")
                    self.assertEqual(set(m["fs"]), {"13px"}, f"{where}: normal text size")
                    self.assertEqual(m["outline"], "none", f"{where}: no heavy outline")
                    self.assertEqual(set(m["roles"]), {"menuitemradio"}, where)
                    self.assertEqual(m["checked"], 1, f"{where}: the current health is checked")
                    b.key("Escape")
                    b.wait(f"!document.querySelector({HEALTH_MENU!r})", 5)
                    got.append(f"{pal}@{w} {m['w']:.0f}px")
        finally:
            hcbase.measure.width(b, self.width, self.height)
            b.eval("(()=>{ S.palette=%s; S.theme=%s; applyTheme(); return true; })()" % tuple(json.dumps(x) for x in was))
        self.note(10, "inside the window, compact, 13px rows: " + ", ".join(got))
        self.sheet(10, "reporting", palettes=["Claude", "Retro Arcade"], widths=(1400, 900),
                   prepare=lambda b: (b.eval("document.querySelector('#v-reporting .wr-chg').scrollIntoView({block:'center'})"),
                                      b.eval("document.querySelector('#v-reporting .wr-chg').click()")))
        b.eval("document.querySelector('.pophost [role=menu]')&&document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))")


# ── #276: a vault of its own ─────────────────────────────────────────────────

class Messages254(Case254):
    """Check 1: two conversations recorded with the check's own command, then Seen, Undo, a reload and a later message."""
    own_vault = True
    REPLIED = "19:hc254-replied@thread.v2"
    HELLO = "19:hc254-hello@thread.v2"

    def replied(self, later=False):
        conv = {"kind": "teams", "conversation": self.REPLIED, "title": "Falcon test plan", "from": RASHID, "people": [RASHID, LENA],
                "last": f"{self.day()} 08:40", "link": "https://teams.microsoft.com/l/chat/hc254-replied", "sensitivity": "normal",
                "summary": "Rashid asked for the test plan.", "type": "action", "ask": "Send the test plan",
                "replied": f"{self.day()} 08:45", "items": []}
        if later:          # a later message from someone else, asking something new
            conv.update({"from": LENA, "last": f"{self.day()} 09:20", "summary": "Lena asks for the cut-over checklist.",
                         "ask": "Send the cut-over checklist", "replied": None})
            conv.pop("replied")
        return conv

    def hello(self):
        return {"kind": "teams", "conversation": self.HELLO, "title": "Group chat", "from": RASHID, "people": [RASHID, LENA],
                "last": f"{self.day()} 08:44", "link": "https://teams.microsoft.com/l/chat/hc254-hello", "sensitivity": "normal",
                "summary": "Greetings only.", "items": []}

    def record(self, convs, at):
        code, out = hcbase.vip_found(self.vault, convs, f"{self.day()} {at}")
        self.assertEqual(code, 0, out[-500:])

    def alert(self, conv):
        st = json.loads((self.vault / "system/staging/vip.json").read_text(encoding="utf-8"))
        return next(a for a in st["alerts"] if a.get("conv") == conv)

    def show(self):
        b = self.b
        b.eval("window.__p=false; vipPoll().then(()=>{ window.__p=true; })")
        b.wait("window.__p", 15)
        self.screen("today")
        b.eval("EXPAND.add('td'); renderToday()")
        b.pump(0.3)

    def quiet(self):
        return self.b.eval("""[...document.querySelectorAll('#tdList>li.td-quiet')].map(l=>({id:l.dataset.td.slice(2), t:l.querySelector('.t').textContent,
            btn:[...l.querySelectorAll('button')].map(b=>[b.dataset.alertdo||'',b.getAttribute('aria-label')||'',b.dataset.tip||''])}))""")

    def row(self, aid):
        return self.b.eval(f"!!document.querySelector('#tdList li[data-td=\"al{aid}\"]')")

    def test_c01_a_replied_line_and_a_nothing_for_you_line_each_have_seen(self):
        """1. (#276) On Today › Messages, a "Replied" line ("<person> with <person>: you replied HH:MM") and a "nothing for you" line each
        have a quiet Seen (the eye), named on hover and to screen readers. Seen clears the line at once; Undo brings it back; it stays
        gone after a reload and the next check; a later message from someone else that asks something reopens the conversation."""
        b = self.b
        self.record([self.replied(), self.hello()], "08:55")
        self.show()
        rows = self.quiet()
        rep = next((r for r in rows if "you replied" in r["t"]), None)
        hel = next((r for r in rows if "nothing for you" in r["t"]), None)
        self.assertIsNotNone(rep, f"a Replied line on Today: {rows}")
        self.assertIsNotNone(hel, f"a nothing for you line on Today: {rows}")
        for r in (rep, hel):
            self.assertEqual(len(r["btn"]), 1, f"one button, Seen: {r}")
            act, name, tip = r["btn"][0]
            self.assertEqual((act, tip), ("seen", "Seen"), r)
            self.assertTrue(name.startswith("Seen: Rashid Al Suwaidi"), f"named for a screen reader: {name}")
        self.assertNotIn("VIP", b.eval("document.getElementById('tdList').textContent"))
        aid = rep["id"]
        # Seen clears it at once, and it is kept
        b.click(f'#tdList [data-alertdo="seen"][data-id="{aid}"]')
        b.wait(f"!document.querySelector('#tdList li[data-td=\"al{aid}\"]')", 5)
        self.assertEqual(b.eval("document.getElementById('snackT').textContent"), "Marked seen")
        self.assertTrue(self.alert(self.REPLIED).get("seen"), "kept in vip.json")
        # Undo brings it back, still a quiet Replied line
        b.click("#snackU")
        b.wait(f"!!document.querySelector('#tdList li[data-td=\"al{aid}\"]')", 5)
        self.assertFalse(self.alert(self.REPLIED).get("seen"))
        self.assertEqual(self.alert(self.REPLIED).get("state"), "replied")
        # Seen again; a reload and the next check (the same conversation recorded again) keep it gone
        b.click(f'#tdList [data-alertdo="seen"][data-id="{aid}"]')
        b.wait(f"!document.querySelector('#tdList li[data-td=\"al{aid}\"]')", 5)
        b.click(f'#tdList [data-alertdo="seen"][data-id="{hel["id"]}"]')
        b.wait(f"!document.querySelector('#tdList li[data-td=\"al{hel['id']}\"]')", 5)
        b.reload("typeof go==='function' && LIVE")
        self.show()
        self.assertFalse(self.row(aid), "gone after a reload")
        self.record([self.replied(), self.hello()], "09:10")
        self.show()
        self.assertFalse(self.row(aid), "gone after the next check")
        self.assertFalse(self.row(hel["id"]), "the nothing for you line too")
        # a later message from someone else asking something new reopens it
        self.record([self.replied(later=True)], "09:25")
        self.show()
        a = self.alert(self.REPLIED)
        self.assertFalse(a.get("seen"), f"a later ask reopens the conversation: {a.get('state')}")
        self.assertTrue(self.row(a["id"]), "back on Today")
        self.note(1, f"both quiet lines: one Seen button (\"{rep['btn'][0][1]}\"); Seen, Undo, Seen; gone after a reload and a re-record; "
                     f"a later ask from Lena reopens it ({a.get('state')})")


# ── #279: a vault of its own ─────────────────────────────────────────────────

class Prep254(Case254):
    """Check 3: a meeting no project matches, added to the saved calendar; the Prep page opens and its Project chip is a picker."""
    own_vault = True
    TITLE = "Quarterly catch-up"

    def add_meeting(self):
        day = self.day()
        tomorrow = (date.fromisoformat(day) + timedelta(days=1)).isoformat()
        fal = {"id": "hc-1", "start": "10:00", "end": "11:00", "title": "FAL Steering committee", "where": "Microsoft Teams Meeting",
               "teams": True, "private": False, "organiser": True}
        other = {"id": "hc254-q", "start": "14:00", "end": "14:30", "title": self.TITLE, "where": "Room 4", "teams": False,
                 "private": False, "organiser": True}
        cal = self.vault / "system/staging/hc254-cal.json"
        cal.write_text(json.dumps({"days": {day: [fal, other], tomorrow: [dict(fal, id="hc-2")]}}), encoding="utf-8")
        code, out = self.run_in_vault("sweep.py", "calendar", str(cal))
        cal.unlink()
        self.assertEqual(code, 0, out[-400:])
        code, out = self.run_in_vault("build_dashboard.py")
        self.assertEqual(code, 0, out[-400:])

    def open_prep(self, key):
        b = self.b
        b.eval(f"go('prep', {json.dumps(key)})")
        b.wait("document.querySelector('#v-prep #ppTitle, #v-prep .card') && !document.querySelector('#v-prep .pploading')", 25)
        b.pump(0.4)

    def picker(self):
        sel = "#v-prep .ppmeta select[data-ppproject]"
        return self.b.eval(f"""(()=>{{ const s=document.querySelector({json.dumps(sel)}); if(!s) return null;
          return {{value:s.value, options:[...s.options].map(o=>[o.value,o.text]), name:s.getAttribute('aria-label')}}; }})()""")

    def choose(self, code):
        b = self.b
        sel = "#v-prep .ppmeta select[data-ppproject]"
        b.eval(f"(() => {{ const s = document.querySelector({json.dumps(sel)}); s.value = {json.dumps(code)}; "
               f"s.dispatchEvent(new Event('change', {{bubbles: true}})); }})()")
        self.until(lambda: code in json.dumps(json.loads((self.vault / "system/config/settings.json").read_text(encoding="utf-8"))
                                              .get("prep", {}).get("series", {})), f"{code} saved in prep.series", 20)
        b.wait(f"document.querySelector({json.dumps(sel)}) && document.querySelector({json.dumps(sel)}).value==={json.dumps(code)}"
               " && !document.querySelector('#v-prep .pploading')", 25)

    def series(self):
        return json.loads((self.vault / "system/config/settings.json").read_text(encoding="utf-8")).get("prep", {}).get("series", {})

    def test_c03_prep_with_no_project_opens_and_the_project_is_a_remembered_picker(self):
        """3. (#279) Prep on a meeting with no project opens the Prep page (never "Choose the meeting's project in the Prep brief first."
        with only Back to Today). Its Project chip is a picker: the projects and "No project (general meeting)". Choose a project; repeat
        with No project; reopen and the choice is remembered for the series (settings prep.series)."""
        b = self.b
        self.add_meeting()
        b.reload("typeof go==='function' && LIVE")
        key = f"{self.day()}|14:00|{self.TITLE}"
        self.open_prep(key)
        page = b.eval("document.getElementById('v-prep').innerText")
        self.assertNotIn("Choose the meeting's project", page, "no dead end")
        self.assertTrue(b.eval("!!document.querySelector('#v-prep #ppTitle')"), f"the Prep page opens: {page[:200]}")
        p = self.picker()
        self.assertIsNotNone(p, "the Project chip is a picker")
        self.assertEqual(p["value"], "", "nothing chosen yet")
        texts = [t for _, t in p["options"]]
        self.assertEqual(texts[0], "Choose a project…")
        for name in ("Falcon Data Platform", "Orbit Customer App", "No project (general meeting)"):
            self.assertIn(name, texts)
        self.assertNotIn("_portfolio", json.dumps(self.series()), "No project is not the same as nothing chosen")
        # choose a project: saved for the series and remembered on reopening
        self.choose("FAL")
        sk = next(k for k, v in self.series().items() if v == "FAL")
        b.reload("typeof go==='function' && LIVE")
        self.open_prep(key)
        self.assertEqual(self.picker()["value"], "FAL", "remembered after a reload")
        # then No project (general meeting): the all-projects view, remembered too
        self.choose("_portfolio")
        self.assertEqual(self.series().get(sk), "_portfolio")
        b.reload("typeof go==='function' && LIVE")
        self.open_prep(key)
        p = self.picker()
        self.assertEqual(p["value"], "_portfolio", "No project remembered after a reload")
        self.assertNotIn("Choose a project…", [t for _, t in p["options"]], "chosen: no 'Choose a project…' any more")
        self.assertNotIn("Choose the meeting's project", b.eval("document.getElementById('v-prep').innerText"))
        self.note(3, f"opened with no project; picker of {len(texts) - 1} choices; FAL then No project saved for series \"{sk}\" and "
                     f"remembered after reloads")


# ── #280 and #282: a vault of its own ────────────────────────────────────────

VTT = ("WEBVTT\n\n00:00:01.000 --> 00:00:05.000\n<v Alan Carter>Morning all, first the test plan.</v>\n\n"
       "00:00:05.000 --> 00:00:09.000\n<v Lena Fischer>We agreed the phased rollout.</v>\n\n"
       "00:00:09.000 --> 00:00:15.000\n<v Sara Khan>I'll send the revised plan next week.</v>\n")


class Minutes254(Case254):
    """Checks 4 and 6: minutes staged with minutes.py stage (as cx-minutes does) in the demo vault, for Falcon Data Platform."""
    own_vault = True

    def stage(self, title, items, minutes=None, code_wanted=0):
        """A transcript in the inbox and its spec staged; (the new proposal's path, its JSON, the stage output).
        `minutes.py stage` exits 1 when its checks flag an item (an invalid one included): the proposal is still written."""
        day = self.day()
        (self.vault / f"inbox/{day} {title}.vtt").write_text(VTT, encoding="utf-8")
        spec = {"title": title, "date": day, "projects": ["FAL"], "transcript": f"inbox/{day} {title}.vtt", "items": items}
        if minutes:
            spec["minutes"] = minutes
        else:
            from test_tracker import make_draft
            draft = f"system/staging/drafts/{day} {title}.docx"
            make_draft(self.vault / draft)
            spec["draft"] = draft
        f = self.vault / "system/staging/drafts/hc254-meeting.json"
        f.write_text(json.dumps(spec), encoding="utf-8")
        before = set(hcbase.pending_proposals(self.vault))
        code, out = self.run_in_vault("minutes.py", "stage", "system/staging/drafts/hc254-meeting.json")
        self.assertEqual(code, code_wanted, out[-600:])
        new = sorted(set(hcbase.pending_proposals(self.vault)) - before)
        self.assertEqual(len(new), 1, out[-400:])
        p = self.vault / "system/staging" / new[0]
        return p, json.loads(p.read_text(encoding="utf-8")), out

    def need_280(self):
        mins = "#280" in (self.vault / "system/scripts/minutes.py").read_text(encoding="utf-8")
        trk = "#280" in (self.vault / "system/scripts/tracker.py").read_text(encoding="utf-8")
        missing = [w for ok, w in ((mins, "the extractor fix in minutes.py (branch v254-280-4)"),
                                   (trk, "dev/proposals/280/tracker.py.diff in tracker.py (guarded: Jarvis applies it)")) if not ok]
        if missing:
            self.skipTest("#280 is not in this vault: needs " + " and ".join(missing) + "; the check runs once both are in")

    def test_c04_a_decision_is_never_staged_with_raised_and_one_bad_item_never_blocks_apply(self):
        """4. (#280) cx-minutes stages a decision with `date`, never `raised` (decisions have no `raised`), and `tracker.py validate` passes
        the minutes. An invalid item cannot be approved and Review shows the reason; one bad item does not block the rest: Apply writes
        the good one and names the bad one, which is held in Review."""
        self.need_280()
        day = self.day()
        act = {"table": "actions", "section": "Actions", "values": {"project": "FAL", "description": "Send the revised test plan",
                                                                     "owner": "Sara Khan", "due_date": day}}
        dec = {"table": "decisions", "section": "Decisions", "values": {"project": "FAL", "decision": "Use the phased rollout",
                                                                         "made_by": "Lena Fischer", "raised": day}}
        p, data, _ = self.stage("Pilot readiness review", [act, dec])
        d = next(i for i in data["items"] if i["table"] == "decisions")
        self.assertNotIn("raised", d["values"], "a decision is never staged with raised")
        self.assertEqual(d["values"].get("date"), day, "it is dated by date")
        self.assertNotIn("invalid", d.get("flags", []))
        code, out = self.run_in_vault("tracker.py", "validate", f"system/staging/{p.name}")
        self.assertEqual(code, 0, out[-400:])
        self.assertIn("0 problem(s)", out)
        # an invalid item beside a good one (an action with a field that doesn't exist)
        good = {"table": "actions", "section": "Actions", "values": {"project": "FAL", "description": "Book the cut-over room",
                                                                      "owner": "Sara Khan", "due_date": day}}
        bad = {"table": "actions", "section": "Actions", "values": {"project": "FAL", "description": "Chase the vendor",
                                                                     "owner": "Sara Khan", "colour": "red"}}
        q, data, _ = self.stage("Supplier checkpoint", [good, bad], code_wanted=1)   # flagged invalid: exit 1, still staged
        badn = next(i["n"] for i in data["items"] if "invalid" in i.get("flags", []))
        code, rows = self.run_in_vault("review.py", "list")
        self.assertIn("colour", rows, "Review shows the reason")
        n = next(ln.replace("↳", "").split()[0] for ln in rows.splitlines() if "Chase the vendor" in ln)
        code, out = self.run_in_vault("review.py", "approve", n)
        self.assertIn("invalid", out, "an invalid item can't be approved")
        for i in data["items"]:
            i["decision"] = "approved"                     # a stale approval, as Alan's board had: both approved
        q.write_text(json.dumps(data), encoding="utf-8")
        code, out = self.run_in_vault("tracker.py", "apply", q.name)
        self.assertEqual(code, 0, f"one bad item doesn't stop the apply: {out[-500:]}")
        self.assertIn("Held in Review, not applied", out)
        self.assertIn(f"item {badn}", out, "Apply names it")
        self.assertIn("colour", out)
        self.assertTrue(hcbase.db_rows(self.vault, "SELECT id FROM actions WHERE description=?", "Book the cut-over room"), "the good item is written")
        self.assertFalse(hcbase.db_rows(self.vault, "SELECT id FROM actions WHERE description=?", "Chase the vendor"))
        after = json.loads(q.read_text(encoding="utf-8")) if q.exists() else json.loads((self.vault / "system/staging/applied" / q.name).read_text())
        held = next(i for i in after["items"] if i["n"] == badn)
        self.assertEqual(held["decision"], "pending", "held in Review")
        self.screen("review")
        self.b.pump(0.5)
        self.assertIn("colour", self.b.eval("document.getElementById('v-review').innerText"), "Review shows why")
        self.note(4, f"decision staged with date {day}, no raised; validate 0 problems; item {badn} held and named, the good one written")

    def test_c06_minutes_exports_say_actions(self):
        """6. (#282) Export each format from a minutes view: the actions heading reads "Actions", never "Action Items" (HTML, Word, the
        follow-up email; an older record that stored "Action Items" exports as "Actions" too). Wording only: the Action column and the
        items are unchanged."""
        minutes = {"start": "10:00", "end": "11:00", "attendees": "Lena Fischer, Sara Khan (Example Consulting)",
                   "summary": [{"text": "The team reviewed the cut-over plan.", "turn": 1}],
                   "updates": [{"heading": "Cut-over", "items": [{"text": "The plan is in review.", "turn": 2}]}],
                   "open_questions": ["Who signs off the rehearsal? Raised by Alan Carter; unresolved"]}
        items = [{"table": "actions", "turn": 3, "due_words": "next week",
                  "values": {"project": "FAL", "description": "Send the revised cut-over plan", "owner": "Sara Khan"}},
                 {"table": "decisions", "turn": 2, "values": {"project": "FAL", "decision": "Rehearse the cut-over twice",
                                                               "made_by": "Lena Fischer"}}]
        _, _, out = self.stage("Cut-over planning", items, minutes=minutes)
        rel = next(ln.split("Draft minutes:", 1)[1].strip() for ln in out.splitlines() if "Draft minutes:" in ln)
        # the minutes view, before the older-record step below changes the stored heading
        b = self.b
        b.eval(f"go('minutes',{{path:{json.dumps(rel)}}})")
        b.wait("VIEW==='minutes'&&!!document.querySelector('#v-minutes #mnTitle')", 25)
        b.pump(1.5)
        view = b.eval("document.getElementById('v-minutes').innerText")
        heads = b.eval("""(s=>s?[...s.querySelectorAll('input,h2,h3')].map(e=>(e.value||e.textContent||'').trim()).filter(Boolean).slice(0,2)
          :null)(document.querySelector('#v-minutes [data-id=actions]'))""")
        self.assertNotIn("Action Items", view, "the minutes view never says Action Items")
        self.assertTrue(heads and heads[0] == "Actions", f"the view's Actions section heading: {heads}")
        got = self.py("import creaite_doc, minutes_record, paths, zipfile\n"
                      f"rel = {rel!r}\n"
                      "d = creaite_doc.read(rel)\n"
                      "h = minutes_record.export(rel, 'html', file_beside=False)\n"
                      "html = paths.resolve(h['path']).read_text(encoding='utf-8')\n"
                      "w = minutes_record.export(rel, 'docx', file_beside=False)\n"
                      "z = zipfile.ZipFile(str(paths.resolve(w['path'])))\n"
                      "xml = ''.join(z.read(n).decode('utf-8', 'ignore') for n in z.namelist() if n.startswith('word/') and n.endswith('.xml'))\n"
                      "f = json.dumps(minutes_record.followup_facts(rel), default=str)\n"
                      "for s in d['sections']:\n"
                      "    if s['id'] == 'actions': s['heading'] = s['default_heading'] = 'Action Items'\n"
                      "creaite_doc.write(rel, d) if hasattr(creaite_doc, 'write') else open(str(creaite_doc.real(rel)), 'w').write(creaite_doc.dumps(d))\n"
                      "o = minutes_record.export(rel, 'html', file_beside=False)\n"
                      "old = paths.resolve(o['path']).read_text(encoding='utf-8')\n"
                      "print(json.dumps({'heading': next(s['heading'] for s in creaite_doc.read(rel)['sections'] if s['id'] == 'actions'),"
                      " 'html': ['<h2>Actions</h2>' in html, 'Action Items' in html, 'Send the revised cut-over plan' in html],"
                      " 'word': ['Actions' in xml, 'Action Items' in xml], 'follow': ['Action Items' in f],"
                      " 'old': ['<h2>Actions</h2>' in old, 'Action Items' in old]}))")
        self.assertEqual(got["html"], [True, False, True], "HTML: Actions, never Action Items, the action kept")
        self.assertEqual(got["word"], [True, False], "Word: Actions, never Action Items")
        self.assertEqual(got["follow"], [False], "the follow-up email never says Action Items")
        self.assertEqual(got["old"], [True, False], "an older record that stored Action Items exports as Actions")
        self.assertEqual(got["heading"], "Action Items", "the stored record is left as it was (wording at export only)")
        self.note(6, "HTML and Word exports, the follow-up email and an older record's export say Actions; the view's heading "
                     f"\"{heads[0]}\"; PDF on the sheet")


if __name__ == "__main__":
    unittest.main()
