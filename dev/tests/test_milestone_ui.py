"""sprint-milestone-ui: the milestone view's two looks (BL-244), Add milestone in one step (BL-245), and the history feed on the
milestone editor and the project panel (BL-250 part A).

BL-244: the Client view is the cockpit's plain card (no pill, no note, no outline) and opens first when nothing is remembered; the
Internal view has a bright border and an INTERNAL VIEW pill, in theme tokens that meet contrast in every theme, light and dark, and
that still print. A real browser against the real live server, on milestone_data's project.

Run: python3 dev/tests/test_milestone_ui.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase, theme_names  # noqa: E402
import milestone_data  # noqa: E402
from milestone_data import d  # noqa: E402

KEY = "creaite.cockpit.milestones.view"

# the WCAG contrast ratio of two computed colours (rgb or rgba strings), in the page
RATIO = """const rgb=s=>{ const m=s.match(/[\\d.]+/g).map(Number); return m.slice(0,3); },
  lum=c=>{ const v=c.map(x=>{ x/=255; return x<=0.03928?x/12.92:Math.pow((x+0.055)/1.055,2.4); }); return 0.2126*v[0]+0.7152*v[1]+0.0722*v[2]; },
  ratio=(a,b)=>{ const x=lum(rgb(a)), y=lum(rgb(b)); return (Math.max(x,y)+0.05)/(Math.min(x,y)+0.05); };"""


class Case(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        milestone_data.load(v)

    def setUp(self):
        super().setUp()
        self.b.eval(f"try{{ localStorage.removeItem('{KEY}'); }}catch(e){{}}")
        self.b.eval("S.autoApply=true")

    def fresh(self):
        """A reload with nothing remembered: the page reads the stored view as it loads."""
        self.b.eval(f"try{{ localStorage.removeItem('{KEY}'); }}catch(e){{}}")
        self.b.reload("typeof go==='function'&&LIVE")

    def cockpit(self):
        self.b.eval("go('cockpit','ABC')")
        self.b.wait("document.getElementById('mvCard')&&document.querySelector('#mvCard .mv-head')")

    def page(self, view="plan"):
        self.b.eval(f"mvOpenPage('ABC','{view}')")
        self.b.wait("VIEW==='milestones'&&document.querySelector('#v-milestones .mv-card')")


class Looks(Case):
    def test_a_first_visit_opens_on_the_plain_client_view(self):
        b = self.b
        self.fresh()
        self.cockpit()
        c = b.eval("""(()=>{ const c=document.getElementById('mvCard'), o=[...document.querySelectorAll('#v-cockpit .card')].find(x=>x.id!=='mvCard'), s=getComputedStyle(c), t=getComputedStyle(o);
          return {cls:c.className, pill:!!c.querySelector('.mv-pill'), note:!!c.querySelector('.mv-hidenote,.mv-banner'), text:c.innerText.toUpperCase(),
            bw:s.borderTopWidth, bs:s.borderTopStyle, bc:s.borderTopColor, shadow:s.boxShadow, ow:t.borderTopWidth, oc:t.borderTopColor, ob:t.backgroundColor, bg:s.backgroundColor}; })()""")
        self.assertIn("client", c["cls"])
        self.assertIn("card", c["cls"].split())                            # the cockpit's own card look
        self.assertFalse(c["pill"])                                         # no CLIENT VIEW pill
        self.assertFalse(c["note"])                                         # no "This is what a client sees" line
        self.assertNotIn("CLIENT VIEW", c["text"])
        self.assertNotIn("INTERNAL VIEW", c["text"])
        self.assertEqual((c["bw"], c["bs"], c["bc"], c["bg"]), (c["ow"], "solid", c["oc"], c["ob"]))   # exactly another card's edge
        self.assertEqual(c["shadow"], "none")
        self.assertNotIn("Security review", c["text"].title())             # what the client view hides is unchanged
        self.assertEqual(b.eval("document.getElementById('mvSwap').getAttribute('aria-label')"), "Switch to internal view")
        self.page()
        self.assertEqual(b.eval("document.getElementById('mvACli').getAttribute('aria-pressed')"), "true")
        p = b.eval("(()=>{ const c=document.getElementById('mvPlanCard'); return {pill:!!c.querySelector('.mv-pill'), note:!!c.querySelector('.mv-hidenote,.mv-banner'), cls:c.className}; })()")
        self.assertEqual((p["pill"], p["note"]), (False, False))
        self.assertIn("client", p["cls"])
        self.assertEqual(b.errors, [])

    def test_the_internal_view_has_a_bright_border_and_its_pill_and_is_remembered(self):
        b = self.b
        self.cockpit()
        b.click("#mvSwap")
        b.wait("document.getElementById('mvCard').classList.contains('internal')")
        c = b.eval("""(()=>{ const c=document.getElementById('mvCard'), s=getComputedStyle(c), pill=c.querySelector('.mv-pill.int'), w=getComputedStyle(document.documentElement).getPropertyValue('--warn').trim();
          const probe=document.createElement('i'); probe.style.color=w; document.body.appendChild(probe); const warn=getComputedStyle(probe).color; probe.remove();
          return {bw:s.borderTopWidth, bs:s.borderTopStyle, bc:s.borderTopColor, warn, pill:pill&&pill.innerText.trim().toUpperCase(), icon:!!(pill&&pill.querySelector('svg')), pbg:pill&&getComputedStyle(pill).backgroundColor}; })()""")
        self.assertEqual((c["bw"], c["bs"]), ("2px", "solid"))
        self.assertEqual(c["bc"], c["warn"])                                # the bright border is the theme's --warn
        self.assertEqual(c["pill"], "INTERNAL VIEW")
        self.assertTrue(c["icon"])                                          # never colour alone
        self.assertEqual(c["pbg"], c["warn"])
        b.reload("typeof go==='function'&&LIVE")
        self.cockpit()
        self.assertTrue(b.eval("document.getElementById('mvCard').classList.contains('internal')"))   # remembered
        self.page()
        self.assertEqual(b.eval("document.querySelector('#mvPlanCard .mv-pill.int').innerText.trim().toUpperCase()"), "INTERNAL VIEW")
        b.click("#mvVMove")
        b.wait("document.querySelector('#v-milestones .mv-card.internal .mv-pill.int')&&/Movement/.test(document.querySelector('#v-milestones .mv-card h2').textContent)")
        b.click("#mvACli")                                                  # the page's switch: back to the plain view
        b.wait("document.getElementById('mvPlanCard')&&document.getElementById('mvPlanCard').classList.contains('client')")
        self.assertFalse(b.eval("!!document.querySelector('#v-milestones .mv-pill')"))
        self.assertEqual(b.errors, [])

    def test_border_and_pill_meet_contrast_in_every_theme(self):
        b = self.b
        b.eval(f"localStorage.setItem('{KEY}','int')")
        b.reload("typeof go==='function'&&LIVE")
        self.cockpit()
        bad = []
        for palette in theme_names():
            for mode in ("Light", "Dark"):
                b.eval(f"S.palette={palette!r}; S.theme={mode!r}; applyTheme()")
                r = b.eval("(()=>{ " + RATIO + """ const c=document.getElementById('mvCard'), s=getComputedStyle(c), p=getComputedStyle(c.querySelector('.mv-pill.int'));
                  return [ratio(s.borderTopColor,s.backgroundColor), ratio(p.color,p.backgroundColor)]; })()""")
                if r[0] < 3 or r[1] < 4.5:
                    bad.append((palette, mode, round(r[0], 2), round(r[1], 2)))
        self.assertEqual(bad, [])

    def test_the_internal_mark_reaches_a_printout(self):
        b = self.b
        b.eval(f"localStorage.setItem('{KEY}','int')")
        b.reload("typeof go==='function'&&LIVE")
        self.cockpit()
        b.call("Emulation.setEmulatedMedia", media="print")
        try:
            r = b.eval("""(()=>{ const c=document.getElementById('mvCard'), s=getComputedStyle(c), p=c.querySelector('.mv-pill.int'), ps=getComputedStyle(p);
              return {bs:s.borderTopStyle, bw:s.borderTopWidth, adj:ps.printColorAdjust||ps.webkitPrintColorAdjust, pb:ps.borderTopStyle, text:p.innerText.trim().toUpperCase(), vis:p.offsetWidth>0}; })()""")
        finally:
            b.call("Emulation.setEmulatedMedia", media="")
        self.assertEqual((r["bs"], r["bw"]), ("solid", "2px"))
        self.assertEqual(r["adj"], "exact")
        self.assertEqual(r["pb"], "solid")                                  # its words never print white on white
        self.assertEqual(r["text"], "INTERNAL VIEW")
        self.assertTrue(r["vis"])


class AddInOneStep(Case):
    """BL-245: Add milestone opens with every field ready at once; one Create saves them all, with the editor's rules and Undo."""

    FIELDS = ["mvName", "mvAgr", "mvFc", "mvRng", "mvNum", "mvDesc", "mvOwner", "mvCli", "mvCw", "mvACreate"]

    def until(self, fn, seconds=20):
        end = time.time() + seconds
        while time.time() < end:
            if fn():
                return True
            self.b.pump(0.2)
        return False

    def named(self, name):
        return [m for m in self.v.rows("milestones") if m["name"] == name]

    def open_add(self):
        b = self.b
        b.eval(f"localStorage.setItem('{KEY}','int'); MVAUD='int'")
        self.page()
        b.click("#mvAdd")
        b.wait("MV.add&&!document.getElementById('mvPeek').hidden&&document.getElementById('mvACreate')")

    def test_every_field_is_ready_at_once_and_create_saves_them_all(self):
        b = self.b
        before = len(self.v.rows("milestones"))
        self.open_add()
        r = b.eval("(()=>{ const ids=" + repr(self.FIELDS).replace("'", '"') + """; return {missing:ids.filter(i=>!document.getElementById(i)),
          states:document.querySelectorAll('#mvPeek [data-mvstate]').length, focus:document.activeElement.id, rebase:!!document.querySelector('#mvPeek [data-mvpk=rebase]'),
          chips:!!document.querySelector('#mvPeek .mv-dchips'), edit:[...document.querySelectorAll('#mvPeek button')].some(x=>/^Edit$/.test(x.textContent.trim()))}; })()""")
        self.assertEqual(r["missing"], [])                                  # every editable field, in the first view
        self.assertEqual(r["states"], 5)
        self.assertEqual(r["focus"], "mvName")
        self.assertFalse(r["rebase"])                                       # a first agreed date is a pick, not a rebaseline
        self.assertFalse(r["chips"])                                        # no summary first
        self.assertFalse(r["edit"])                                         # and no second Edit click
        b.type("Data migration signed off")
        b.click("#mvAgr")                                                   # the calendar, as in the editor
        b.wait("!document.getElementById('mvCal').hidden")
        b.eval(f"mvCalClose(false); mvDatePicked('mvAgr','{d(10)}')")
        b.eval(f"mvDatePicked('mvFc','{d(20)}')")                          # later than agreed: the dates say Slipped
        b.wait("/Slipped/.test(document.querySelector('#mvPeek .mv-explain').textContent)")
        b.click('#mvPeek [data-mvstate="ontrack"]')                         # better than the dates: a reason is needed
        b.wait("document.getElementById('mvAWhy')")
        b.eval("const n=document.getElementById('mvNum'); n.value='30'; n.dispatchEvent(new Event('input',{bubbles:true}))")
        b.eval("const t=document.getElementById('mvDesc'); t.value='Every table moved and reconciled'; t.dispatchEvent(new Event('input',{bubbles:true}))")
        b.click("#mvOwner")
        b.wait("!document.getElementById('mvPop').hidden")
        b.type("Omar")
        b.key("Enter")
        b.wait("document.getElementById('mvOwner').textContent.includes('Omar Ali')")
        b.click("#mvCli")
        b.wait("!document.getElementById('mvCw').disabled")
        self.assertEqual(b.eval("document.getElementById('mvNum').value"), "30")   # kept across the redraws
        b.click("#mvACreate")                                               # no reason yet: refused, nothing saved
        b.wait("/say why/.test(document.getElementById('mvACreateErr').textContent)")
        self.assertEqual(b.eval("document.activeElement.id"), "mvAWhy")
        b.type("Vendor confirmed the extra weekend")
        b.click("#mvACreate")                                               # no client wording yet: refused
        b.wait("/client wording/.test(document.getElementById('mvACreateErr').textContent)")
        b.pump(0.5)
        self.assertEqual(len(self.v.rows("milestones")), before)
        b.eval("const c=document.getElementById('mvCw'); c.value='Data moved to the new platform.'; c.dispatchEvent(new Event('input',{bubbles:true}))")
        b.click("#mvACreate")
        self.assertTrue(self.until(lambda: self.named("Data migration signed off")))
        m = self.named("Data migration signed off")[0]
        self.assertEqual((m["baseline_date"], m["forecast_date"], m["state"], m["state_reason"], m["percent_complete"]),
                         (d(10), d(20), "On track", "Vendor confirmed the extra weekend", 30))
        self.assertEqual((m["description"], m["owner"], m["client_visible"], m["client_message"]),
                         ("Every table moved and reconciled", "Omar Ali", 1, "Data moved to the new platform."))
        self.assertEqual(len(self.v.rows("milestones")), before + 1)       # one new milestone, from one proposal
        b.wait(f"!MV.add&&MV.peek==='{m['id']}'&&document.querySelector('#mvPeek .mv-dchips')")   # now its ordinary editor
        b.wait("document.getElementById('snack').classList.contains('on')&&getComputedStyle(document.getElementById('snackU')).display!=='none'")
        b.click("#snackU")                                                  # Undo, as for any save
        self.assertTrue(self.until(lambda: not self.named("Data migration signed off")))
        self.assertEqual(b.errors, [])

    def test_a_draft_is_never_lost_to_a_stray_click_and_esc_discards_it(self):
        b = self.b
        before = len(self.v.rows("milestones"))
        self.open_add()
        b.click("#v-milestones h1")                                         # empty: an outside click closes it, as before
        b.wait("document.getElementById('mvPeek').hidden&&!MV.add")
        b.click("#mvAdd")
        b.wait("MV.add&&document.getElementById('mvACreate')")
        b.type("Pilot go-live")
        b.click("#v-milestones h1")                                         # something entered: it shakes and stays
        b.pump(0.3)
        self.assertFalse(b.eval("document.getElementById('mvPeek').hidden"))
        self.assertEqual(b.eval("document.getElementById('mvName').value"), "Pilot go-live")
        b.click('#mvPeek [data-mvstate="achieved"]')                        # Achieved asks when, today by default
        b.wait("document.getElementById('mvAAch')")
        b.key("Escape")                                                     # Esc discards the draft
        b.wait("document.getElementById('mvPeek').hidden&&!MV.add")
        b.pump(0.5)
        self.assertEqual(len(self.v.rows("milestones")), before)
        b.click("#mvAdd")                                                   # Enter in the name still creates at once
        b.wait("MV.add&&document.activeElement.id==='mvName'")
        b.type("Achieved today")
        b.click('#mvPeek [data-mvstate="achieved"]')
        b.wait("document.getElementById('mvAAch')")
        b.eval("document.getElementById('mvName').focus()")
        b.key("Enter")
        self.assertTrue(self.until(lambda: self.named("Achieved today")))
        m = self.named("Achieved today")[0]
        self.assertEqual((m["status"], m["state"], m["percent_complete"]), ("Done", "Achieved", 100))
        self.assertEqual(b.errors, [])


FEED = """(()=>{ const s=document.querySelector('[data-fdhost="%s"]'); if(!s) return null;
  return {tabs:[...s.querySelectorAll('[data-fdtab]')].map(t=>t.textContent), sel:s.querySelector('[aria-selected=true]').dataset.fdtab, none:[...s.querySelectorAll('.sub')].some(e=>e.offsetParent!==null),
    rows:[...s.querySelectorAll('.pk-fe')].filter(e=>e.offsetParent!==null).map(e=>({text:e.innerText.replace(/\\s+/g,' '), undone:e.classList.contains('undone')}))}; })()"""


class HistoryFeed(Case):
    """BL-250 A: the milestone editor and the project panel show their own history in the peek's feed (All, Activity, Updates,
    Source), read from the same change log lines; the milestone's is internal only."""

    def until(self, fn, seconds=20):
        end = time.time() + seconds
        while time.time() < end:
            if fn():
                return True
            self.b.pump(0.2)
        return False

    def feed(self, host):
        return self.b.eval(FEED % host)

    def tab(self, host, v):
        self.b.click(f'[data-fdhost="{host}"] [data-fdtab="{v}"]')
        self.b.wait(f"document.querySelector('[data-fdhost=\"{host}\"] [aria-selected=true]').dataset.fdtab==='{v}'")
        return self.feed(host)

    def test_a_milestone_shows_its_moves_reasons_and_source_and_an_undone_change(self):
        b = self.b
        b.eval(f"localStorage.setItem('{KEY}','int'); MVAUD='int'")
        self.page()
        b.click('#v-milestones .mv-prow[data-mvedit="ABC-M-007"]')        # Go-live: three moves, one a rebaseline
        b.wait("MV.peek==='ABC-M-007'&&document.querySelector('[data-fdhost=\"ms\"]')")
        f = self.feed("ms")
        self.assertEqual(f["tabs"], ["All", "Activity", "Updates", "Source"])
        text = [r["text"] for r in f["rows"]]
        moves = [t for t in text if "forecast:" in t]
        self.assertEqual(len(moves), 3)                                    # newest first, as the Activity page lists them
        self.assertIn(milestone_data.d(69)[8:10], moves[0])
        self.assertTrue(any("baseline:" in t for t in text))               # the rebaseline
        a = self.tab("ms", "upd")                                           # the reasons given with the changes
        self.assertTrue(any("reason: Security review still open" in r["text"] for r in a["rows"]))
        self.assertTrue(all(r["text"].count("reason:") for r in a["rows"]))
        s = self.tab("ms", "src")
        self.assertTrue(any("created" in r["text"] for r in s["rows"]))
        self.assertTrue(any("steering pack" in r["text"] for r in s["rows"]))   # its source line
        self.tab("ms", "all")
        # a change saved here appears, and undoing it marks it undone
        b.eval("const n=document.getElementById('mvNum'); n.value='35'; n.dispatchEvent(new Event('change',{bubbles:true}))")
        self.assertTrue(self.until(lambda: any("percent complete: 0 → 35" in r["text"] for r in (self.feed("ms") or {"rows": []})["rows"])))
        self.assertEqual(self.feed("ms")["rows"][0]["text"].count("percent complete: 0 → 35"), 1)   # first: the newest
        b.wait("document.getElementById('snack').classList.contains('on')&&getComputedStyle(document.getElementById('snackU')).display!=='none'")
        b.click("#snackU")
        self.assertTrue(self.until(lambda: any(r["undone"] and "0 → 35" in r["text"] for r in (self.feed("ms") or {"rows": []})["rows"])))
        # internal only: the Client view shows no feed
        b.eval("MVAUD='cli'; mvEdDraw()")
        self.assertIsNone(self.feed("ms"))
        self.assertIn("internal", b.eval("document.getElementById('mvHistHid').textContent"))
        self.assertEqual(b.errors, [])

    def test_the_project_panel_shows_health_changes_and_weekly_updates(self):
        b = self.b
        b.eval("openProject('ABC','health')")
        b.wait("document.querySelector('[data-fdhost=\"proj\"]')")
        f = self.feed("proj")
        self.assertEqual(f["tabs"], ["All", "Activity", "Updates", "Source"])
        self.assertTrue(any("health: — → Off track" in r["text"] for r in f["rows"]))
        u = self.tab("proj", "upd")                                         # the weekly updates rows, by their week
        self.assertTrue(any("weekly update, week ending 02-10-2026: Data access late" in r["text"] for r in u["rows"]))
        self.assertTrue(all("health" not in r["text"] for r in u["rows"]))
        self.tab("proj", "all")
        b.eval("document.getElementById('f_health').value='At risk'; document.getElementById('f_reason').value='Data access late, recovery agreed'")
        b.click("#pSave")
        self.assertTrue(self.until(lambda: next(r for r in self.v.rows("projects") if r["code"] == "ABC")["health"] == "At risk"))
        b.wait("!document.getElementById('panel').classList.contains('on')||!CUR")
        b.wait("ACT.some(a=>a.id==='ABC'&&/Off track → At risk/.test(a.change||''))", 20)   # the apply's lines have reloaded
        b.eval("openProject('ABC','health')")                               # the panel draws the history it opens with
        b.wait("document.querySelector('[data-fdhost=\"proj\"]')")
        self.assertTrue(any("health: Off track → At risk" in r["text"] for r in self.feed("proj")["rows"]))
        rows = self.feed("proj")["rows"]
        self.assertTrue("At risk" in rows[0]["text"] or "recovery agreed" in rows[0]["text"])   # newest first
        self.assertEqual(b.errors, [])


    def test_older_history_past_the_cap_is_joined_and_dates_new_items(self):
        """With BL-250 B's older history (D.activity_older), a milestone's and a project's early lines and "created" stay, and
        mCreated finds a creation date that ACT no longer holds."""
        b = self.b
        aid = b.eval("A.find(a=>a.p==='ABC').id")
        b.eval(f"""(()=>{{ const gone=a=>(a.id==='ABC-M-007'||a.id==='{aid}'||a.id==='2026-10-02|ABC')&&/^created/.test(a.change||'');
          ACT=ACT.filter(a=>!gone(a)); D.activity_older={{by:['Approved in review'],items:{{'ABC-M-007':[['2026-01-05 09:00','created',0,7,0]],
          'ABC':[['2026-01-04 09:00','health: — → On track',0,6,0]],'2026-10-02|ABC':[['2026-01-03 09:00','created',0,5,0]],'{aid}':[['2026-01-02 09:00','created',0,4,0]]}}}};
          MCREATEDOF=null; }})()""")
        self.assertEqual(b.eval(f"mCreated('actions','{aid}')"), "2026-01-02 09:00")
        b.eval(f"localStorage.setItem('{KEY}','int'); MVAUD='int'")
        self.page()
        b.click('#v-milestones .mv-prow[data-mvedit="ABC-M-007"]')
        b.wait("MV.peek==='ABC-M-007'&&document.querySelector('[data-fdhost=\"ms\"]')")
        rows = [r["text"] for r in self.feed("ms")["rows"]]
        older = next(t for t in rows if "05-01-2026" in t)
        self.assertIn("Approved in review created", older)
        self.assertLess(rows.index(older), next(i for i, t in enumerate(rows) if "steering pack" in t))   # oldest change, then Source
        self.assertTrue(all("forecast" not in t for t in rows[rows.index(older):]))                       # after the newer lines
        b.eval("mvEdClose(true); openProject('ABC','health')")
        b.wait("document.querySelector('[data-fdhost=\"proj\"]')")
        rows = [r["text"] for r in self.feed("proj")["rows"]]
        self.assertIn("health: — → On track", rows[-2])
        self.assertIn("weekly update, week ending 02-10-2026: created", rows[-1])                        # oldest last
        self.assertEqual(b.errors, [])

if __name__ == "__main__":
    unittest.main()
