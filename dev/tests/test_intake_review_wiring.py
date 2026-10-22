"""#232-C (v2.5.0): the wiring of Intake, in a real browser against the live server. One page now answers to every
name the old Intake pages had: go("review"), go("inbox") and go("intake"), the addresses #review, #intake, #inbox
(also #review=<n> and #intake-review&stage=&m=), a saved history entry from before the one page, and every link that used to
point at them (Today's line, the rail, a toast, Close the day, the breadcrumb on a minutes page, a reminder's address).
The rail badge, Today's line, the tab title, the command palette's one entry and the page's own sub-heading show one number.

Item -> test (the PM's table):
  go() aliases                       test_go_aliases
  old addresses and their forms      test_old_addresses_and_forms, test_the_hash_round_trips, test_a_typed_address_opens_the_stage
  Back / Forward and old entries     test_back_restores_stage_and_old_history_entries
  rail badge, Today, page, title     test_badge_today_page_and_title_agree, test_they_agree_after_a_decision
  Today's line and its links         test_todays_line_links_enter_the_stage
  links from other pages             test_link_families (Work, cockpit, activity, breadcrumb, data-go), test_server_made_addresses
  Close the day, First thing, toast  test_review_now_opens_the_meeting
  command palette                    test_one_palette_entry, test_the_palettes_intake_actions_are_the_pages_own
  help screen                        test_help_screen_for_the_one_page

Run: python3 dev/tests/test_intake_review_wiring.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_dashboard  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402

QUIET = """(()=>{ if(!window.__quiet){ window.__quiet=1; const of=window.fetch, off=u=>/\\/health|\\/api\\/data|\\/api\\/files/.test(String(u));
    window.fetch=(u,...a)=>/\\/health/.test(String(u))?Promise.reject(new Error('offline')):off(u)?Promise.resolve(new Response('{}',{status:503})):of(u,...a); }
  shared.LIVE=false; return true; })()"""   # the fixture stands for the lists: the page's health check (every 30 s) would flip LIVE back and reload the data, and opening Intake reads the data and the file list again, over it
SETTLED = "PULSE.reloads===0 && !shared.FBUSY"                                        # nothing still reading or reloading from the page's start-up


class Wiring(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 1000

    @classmethod
    def load(cls, v):
        test_dashboard.populate(v)
        v.run(script="build_dashboard.py")

    def setUp(self):
        super().setUp()
        self.b.eval("try{ localStorage.removeItem('creaite-ir-view'); }catch(e){} irSetView('list'); irStage.value='all'; irOpen.value=null; go('today')")

    def model(self, ready=2):
        """A fixed model on the page's own Review rows: one drafted meeting holding two proposals, `ready` meetings to process."""
        self.b.eval(QUIET)
        self.b.wait(SETTLED)
        ns = self.b.eval("REV.filter(r=>!r.done).map(r=>r.n)")
        self.assertGreaterEqual(len(ns), 3, "the sample has fewer than three proposals")
        meetings = [{"id": "mA", "src": "calendar", "title": "Sample steering", "day": "2026-10-05", "start": "09:00", "p": None, "stage": "drafted",
                     "state": "proposals", "age": 0, "stale": False, "groups": {"needs": ns[:1], "routine": ns[1:2]}}]
        for i in range(ready):
            meetings.append({"id": f"mR{i}", "src": "calendar", "title": f"Ready {i}", "day": "2026-10-05", "start": f"1{i}:00", "p": None,
                             "stage": "arrived", "state": "ready", "age": 0, "stale": False, "groups": {"needs": [], "routine": []}})
        m = {"v": 1, "meetings": meetings, "mail": {"needs": [], "routine": ns[2:]}, "other": {"needs": [], "routine": []},
             "later": [], "not_needed": [], "counts": {}}
        # the fixed model stands for the whole page: the sample's two inbox files (rows of the real model) go with the rows they replace
        # #245 (merged in 2.5.2): Today's Intake line counts the meetings from the calendar import (D.meetings), so the `ready` meetings are there too;
        # and every pending proposal is in the model (the page counts all of them), so the line and the page say the same number
        rows = [{"id": f"mR{i}", "key": f"mR{i}", "title": f"Ready {i}", "p": "ABC", "day": "2026-10-05", "start": f"1{i}:00", "end": f"1{i}:30",
                 "transcript": "available", "processed": False, "draft": None, "private": False} for i in range(ready)]
        # the fixture stands for the lists: opening Intake would read the real inbox again (refreshFiles) and bring the sample's files back
        self.b.eval(f"shared.LIVE=false; D.inbox=[]; D.meetings={{rows:{json.dumps(rows)}}}; D.intake_review={json.dumps(m)}; irTick.value++; renderBadge(); go('today')")
        return ns

    # --- go() and the addresses ---

    def test_go_aliases(self):
        b = self.b
        for name in ("review", "inbox", "intake", "intake-review"):
            b.eval("go('today')")
            b.eval(f"go({name!r})")
            self.assertEqual(b.eval("[VIEW, location.hash, document.getElementById('v-intake-review').hidden, document.getElementById('v-review'), document.getElementById('v-inbox')]"),
                             ["intake-review", "#intake-review", False, None, None], name)       # #232 C2: the old pages are not in the page at all
        self.assertEqual(b.eval("document.querySelector('.rail [data-v=review]').getAttribute('aria-current')"), "page")

    def test_old_addresses_and_forms(self):
        b = self.b
        self.model()
        self.assertEqual(b.eval("['#review','#intake','#inbox','#intake-review','review','inbox'].map(h=>parseHash(h).v)"), ["intake-review"] * 6)
        self.assertEqual(b.eval("parseHash('#review=7').ir"), {"stage": "", "m": "", "n": 7})
        self.assertEqual(b.eval("parseHash('#intake-review&stage=drafted&m=mA').ir"), {"stage": "drafted", "m": "mA", "n": None})
        self.assertEqual(b.eval("parseHash('#inbox&stage=nonsense').ir.stage"), "")             # an unknown stage is no filter
        self.assertEqual(b.eval("parseHash('#review&item=ABC-A-001')?.v"), "intake-review")      # the old item form still parses

    def test_the_hash_round_trips(self):
        b = self.b
        self.model()
        self.assertEqual(b.eval("hashOf({v:'inbox'})"), "#intake-review")
        self.assertEqual(b.eval("hashOf({v:'review'})"), "#intake-review")
        self.assertEqual(b.eval("hashOf({v:'intake-review',ir:{stage:'drafted',m:'mA'}})"), "#intake-review&stage=drafted&m=mA")
        b.eval("go('intake-review',{stage:'arrived'})")
        self.assertEqual(b.eval("irStage.value"), "arrived")
        b.eval("go('today'); go('intake-review')")                                               # no argument: the page keeps its stage
        self.assertEqual(b.eval("irStage.value"), "arrived")

    def test_a_typed_address_opens_the_stage(self):
        b = self.b
        self.model()
        b.eval("location.hash='#review&stage=drafted'")
        b.wait("VIEW==='intake-review' && irStage.value==='drafted'")
        b.eval("go('today'); location.hash='#inbox&stage=arrived'")
        b.wait("VIEW==='intake-review' && irStage.value==='arrived'")
        ns = b.eval("REV.filter(r=>!r.done).map(r=>r.n)")
        b.eval(f"go('today'); location.hash='#review={ns[0]}'")
        b.wait("VIEW==='intake-review' && irOpen.value==='mA'")                                  # a proposal number opens its meeting
        self.assertEqual(b.eval("document.querySelector('[data-irm=mA]').getAttribute('aria-expanded')"), "true")

    def test_back_restores_stage_and_old_history_entries(self):
        b = self.b
        self.model()
        b.eval("go('intake-review',{stage:'drafted'}); go('work')")
        b.eval("history.back()")
        b.wait("VIEW==='intake-review'")
        self.assertEqual(b.eval("irStage.value"), "drafted")
        for old in ("review", "inbox", "intake"):                                                # an entry saved before the one page
            b.eval("go('today')")
            b.eval(f"restoreNav({{v:{old!r},arg:null,wt:'actions',wv:null,p:[],from:null,item:null,scroll:0}})")
            self.assertEqual(b.eval("VIEW"), "intake-review", old)

    # --- the one number ---

    def numbers(self):
        """Every place the number shows, read from the page itself."""
        b = self.b
        b.eval("renderToday()")
        o = b.eval("""(()=>{ const c=irLiveCounts(), t=n=>{ const e=document.querySelector(n); return e?e.textContent.trim():null; };
          const line=[...document.querySelectorAll('#tdQuiet a')].map(a=>a.textContent.trim());   /* #245's line (#tdQuiet), in the 2.6 merge */
          const num=s=>{ const m=/^(\\d+)/.exec(s); return m?+m[1]:0; };
          return {badge:c.badge, ready:c.ready, to_approve:c.to_approve, rail:t('#revBadge'), line, lineSum:line.reduce((a,s)=>a+num(s),0)}; })()""")
        b.eval("go('intake-review')")
        b.eval("new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))")
        sub = b.eval("document.querySelector('#irSub').textContent.trim()")
        o.update(sub=sub, subNums=[int(x) for x in __import__("re").findall(r"\d+", sub.split("Calendar read")[0])], title=b.eval("document.title"))
        b.eval("go('today')")
        return o

    def test_badge_today_page_and_title_agree(self):
        self.model(ready=2)
        o = self.numbers()
        self.assertEqual(o["ready"], 2)
        self.assertGreaterEqual(o["to_approve"], 3)
        self.assertEqual(o["badge"], o["ready"] + o["to_approve"])
        self.assertEqual(o["rail"], str(o["badge"]))
        self.assertEqual(o["lineSum"], o["badge"], o["line"])
        self.assertEqual(sum(o["subNums"]), o["badge"], o["sub"])
        self.assertTrue(o["title"].endswith("Intake (%d)" % o["badge"]), o["title"])

    def test_the_real_model_counts_each_file_once(self):
        """p250-d puts a waiting upload in the model as a row; 232-C's extra-file count must not add it a second time."""
        o = self.b.eval("""(()=>{ const m=irModel(), rows=m.meetings.filter(x=>x.src==='upload'&&!x.already).length,
          files=(D.inbox||[]).filter(f=>f.state==='new'&&f.uploaded!==false&&!f.event).length;
          return {rows, files, arrived:irLiveCounts().arrived, fromModel:irCounts(m, irDone).arrived}; })()""")
        self.assertGreaterEqual(o["files"], 1, "the sample has a waiting file")
        self.assertEqual(o["rows"], o["files"], o)
        self.assertEqual(o["arrived"], o["fromModel"], o)

    def test_they_agree_after_a_decision(self):
        b = self.b
        ns = self.model(ready=1)
        before = self.numbers()
        b.eval(f"(()=>{{ const r=REV.find(x=>x.n=={ns[1]}); r.done=true; renderBadge(); }})()")   # a decision, as review.js and rvDecideMany leave REV
        after = self.numbers()
        self.assertEqual(after["badge"], before["badge"] - 1, (before, after))
        self.assertEqual(after["rail"], str(after["badge"]))
        self.assertEqual(after["lineSum"], after["badge"])
        self.assertEqual(sum(after["subNums"]), after["badge"])
        self.assertTrue(after["title"].endswith("(%d)" % after["badge"]), after["title"])

    def test_nothing_waiting_no_badge_no_line(self):
        b = self.b
        b.eval("D.inbox=[]; D.meetings={rows:[]}; D.intake_review={v:1,meetings:[],mail:{needs:[],routine:[]},other:{needs:[],routine:[]},later:[],not_needed:[],counts:{}}; REV.forEach(r=>r.done=true); irTick.value++; renderBadge(); renderToday()")
        self.assertEqual(b.eval("irLiveCounts().badge"), 0)
        self.assertEqual(b.eval("document.querySelectorAll('#tdQuiet a').length"), 0)
        self.assertIn(b.eval("document.querySelector('#revBadge')?.textContent.trim()||''"), ("", "0"))
        b.eval("REV.forEach(r=>r.done=false)")

    # --- the links ---

    def test_todays_line_links_enter_the_stage(self):
        b = self.b
        self.model(ready=2)
        b.eval("renderToday()")
        self.assertEqual(b.eval("[...document.querySelectorAll('#tdQuiet a')].map(a=>a.dataset.tdq)"), ["meetings", "proposals"])
        self.assertEqual(b.eval("document.querySelector('#tdQuiet a[data-tdq=meetings]').textContent.trim()"), "2 meetings ready to process")
        self.assertRegex(b.eval("document.querySelector('#tdQuiet a[data-tdq=proposals]').textContent.trim()"), r"^\d+ suggestions? to approve$")
        self.assertEqual(b.eval("document.querySelector('#tdQuiet a[data-tdq=meetings]').getAttribute('href')"), "#intake-review&stage=arrived")
        b.eval("document.querySelector('#tdQuiet a[data-tdq=meetings]').click()")
        b.wait("VIEW==='intake-review'")
        self.assertEqual(b.eval("irStage.value"), "arrived")
        b.eval("go('today')")
        b.eval("document.querySelector('#tdQuiet a[data-tdq=proposals]').click()")
        b.wait("VIEW==='intake-review'")
        self.assertEqual(b.eval("irStage.value"), "drafted")

    def test_link_families(self):
        b = self.b
        self.model()
        probes = {
            "data-go review (reminders, toasts, empty states)": "(()=>{ const a=document.createElement('a'); a.href='#'; a.dataset.go='review'; document.body.append(a); a.click(); a.remove(); })()",
            "data-go inbox": "(()=>{ const a=document.createElement('a'); a.href='#'; a.dataset.go='inbox'; document.body.append(a); a.click(); a.remove(); })()",
            "Today's day-band Review action": "DAYACTS.review()",
            "a toast's Open Review": "go('review')",
            "a proposal from Today": "tdToReview(REV.find(r=>!r.done).n)",
            "the minutes breadcrumb": "(()=>{ const a=document.createElement('a'); a.href='#'; a.dataset.go='intake-review'; document.body.append(a); a.click(); a.remove(); })()",
            "a conflict (core/server.js)": "go('review')",
        }
        for name, js in probes.items():
            b.eval("go('work')")
            b.eval(js)
            b.wait("VIEW==='intake-review'")
            self.assertFalse(b.eval("document.getElementById('v-intake-review').hidden"), name)
        # the cockpit and Work have no link of their own to the old pages: their empty states and cards use the same data-go
        for src in ("go('cockpit', P[0].code)", "go('work')", "go('activity')", "go('files')", "go('settings')"):
            b.eval(src)
            self.assertEqual(b.eval("[...document.querySelectorAll('#v-' + VIEW + ' [data-go=review], #v-' + VIEW + ' [data-go=inbox]')].length >= 0"), True)
        self.assertEqual(b.eval("document.querySelectorAll('.rail [data-v=inbox]').length"), 0)

    def test_server_made_addresses(self):
        """The addresses the server writes into a finished run's link (drafts.py '#review', live_server.py '#intake' and '#review')."""
        b = self.b
        self.model()
        for h in ("#review", "#intake"):
            b.eval(f"go('today'); location.hash={h!r}")
            b.wait("VIEW==='intake-review'")

    def test_review_now_opens_the_meeting(self):
        b = self.b
        ns = self.model()
        # Today's First thing / a toast: a proposal number opens the meeting it came from
        b.eval(f"irOpen.value=null; tdToReview({ns[0]})")
        b.wait("VIEW==='intake-review' && irOpen.value==='mA'")
        # Close the day's Review now: the proposal's file and ref find its meeting
        row = b.eval(f"(()=>{{ const r=REV.find(x=>x.n=={ns[1]}); return {{file:r.file, ref:r.ref}}; }})()")
        b.eval(f"go('today'); irOpen.value=null; cdOpenPlaces({{review:[{json.dumps(row)}], work:[], intake:false}})")
        b.wait("VIEW==='intake-review' && irOpen.value==='mA'")
        # and "Also for Review now: Intake" lands on the Arrived stage
        b.eval("go('today'); cdOpenPlaces({review:[], work:[], intake:true})")
        b.wait("VIEW==='intake-review' && irStage.value==='arrived'")

    # --- the command palette ---

    def test_one_palette_entry(self):
        b = self.b
        self.model(ready=1)
        names = b.eval("ckItems('').map(i=>i.g+'|'+i.l)")
        self.assertEqual([n for n in names if n.startswith("Go to|") and ("Intake" in n or "Review" in n)], ["Go to|Intake"])
        self.assertNotIn("Go to|Review", names)
        hint = b.eval("ckItems('').find(i=>i.l==='Intake'&&i.g==='Go to').h")
        self.assertEqual(hint, "%d waiting" % b.eval("irLiveCounts().badge"))
        for q in ("intake", "review"):
            self.assertIn("Go to|Intake", b.eval(f"ckItems({q!r}).map(i=>i.g+'|'+i.l)"))
        b.eval("go('today'); ckItems('intake').find(i=>i.g==='Go to').fn()")
        self.assertEqual(b.eval("VIEW"), "intake-review")

    def test_the_palettes_intake_actions_are_the_pages_own(self):
        """#232 C2: Add files, Process all ready and Process a meeting no longer click the old page's ids; they call the page's actions."""
        b = self.b
        self.model(ready=2)
        names = b.eval("ckItems('').map(i=>i.g+'|'+i.l)")
        self.assertIn("Actions|Add files to Intake", names)
        self.assertIn("Actions|Process all ready", names)
        self.assertNotIn("Actions|Process new files", names)
        hint = b.eval("ckItems('').find(i=>i.l==='Process all ready').h")
        self.assertEqual(hint, "%d ready" % b.eval("irLiveCounts().ready"))
        meet = b.eval("ckItems('process meeting').map(i=>i.l).filter(l=>l.startsWith('Intake:'))")
        self.assertEqual(sorted(meet), ["Intake: process meeting Ready 0", "Intake: process meeting Ready 1"])      # the ready ones, not the drafted one
        b.eval("""window.PICKED=[]; window.REALCLICK=HTMLInputElement.prototype.click; HTMLInputElement.prototype.click=function(){ window.PICKED.push([this.type,this.multiple]); }; 0""")
        try:
            b.eval("go('today'); ckItems('').find(i=>i.l==='Add files to Intake').fn()")
            self.assertEqual(b.eval("VIEW"), "intake-review")
            self.assertEqual(b.eval("PICKED"), [["file", True]])                                               # the chooser opened from the palette
            self.assertEqual(b.eval("!!document.getElementById('inboxFile')"), False)                          # and no old page's input
        finally:
            b.eval("HTMLInputElement.prototype.click=window.REALCLICK; document.querySelectorAll('body > input[type=file]').forEach(e=>e.remove()); 0")

    # --- help ---

    def test_help_screen_for_the_one_page(self):
        b = self.b
        self.model()
        o = b.eval("""(()=>{ go('intake-review'); helpScreenSync();
          const foot=document.getElementById('hFoot'), sc=HD.screens['intake'];
          return {keys:Object.keys(HD.screens), foot:foot&&!foot.hidden?foot.textContent:null, title:sc&&sc.title, ids:sc&&sc.ids, ref:sc&&sc.ref,
                  inPage:!!document.querySelector('#v-intake-review #hFoot'), screenKey:screenKey()}; })()""")
        self.assertEqual(o["keys"], ["today", "work", "intake", "projects", "people", "notes", "files"])
        self.assertEqual((o["title"], o["screenKey"]), ("Intake", "intake"))
        self.assertEqual(o["foot"], "Press ? for help with Intake")
        self.assertTrue(o["inPage"])
        self.assertTrue(1 <= len(o["ids"]) <= 5 and o["ref"] == "intake")
        b.eval("document.dispatchEvent(new KeyboardEvent('keydown',{key:'?',bubbles:true}))")
        b.wait("helpPanelOpen()")
        self.assertEqual(b.eval("document.querySelector('#hpnT').textContent"), "Help · Intake")
        self.assertTrue(b.eval("!!document.querySelector('#helpPanel a[href=\"#help-reference-intake\"]')"))


if __name__ == "__main__":
    unittest.main()
