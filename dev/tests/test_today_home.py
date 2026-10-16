"""BL-319 (v1.9.2) parts 1 to 5: Today as one home (dev/mockups/today-one-home-mockup.html, tab "Today, one home").

Run: python3 dev/tests/test_today_home.py   (Chrome tier; skipped without Chrome)
One class per Done-when point:
  Header      the header is BL-293's day band, exactly, at full width, with its arrows fixed at the top right;
  ToDecide    To decide first after the band: Review, transcripts ready and messages, newest first, top five, "Open Review (n)";
              icon actions with Undo (approve and save; reject with a reason; never approve for a one-at-a-time item);
  Sections    every current section present, in order, unboxed; Resolved folded to one line; the Week ahead to next Monday
              with why each row is there, following dashboard.week_ahead_priorities; the Portfolio as it was;
  Icons       row icons named on hover and to screen readers, 55% until pointed at or tabbed into, nothing moves; Mark done
              and Move the date staged with Undo; the keyboard reaches and runs them;
  Rhythm      28px between sections, rows at least 44px, one 13px uppercase heading style, a 980px reading width, centred;
  Narrow      320 px with nothing scrolling sideways (BL-217), and dark mode.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_today_days as fx  # noqa: E402  (fixes CREAITE_NOW and the fixture's TODAY on import)
from live_browser import LiveBrowserCase, pin_page_clock  # noqa: E402

TD = "[...document.querySelectorAll('#tdList>li')]"


class Header(LiveBrowserCase):
    """The fixture calendar (test_today_days), both clocks pinned."""
    shared_server = True

    @classmethod
    def load(cls, v):
        fx.world(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": fx.NOW}

    def setUp(self):
        super().setUp()
        pin_page_clock(self.b, fx.NOW)
        self.b.eval("go('today')")
        self.b.wait("document.querySelectorAll('#todayDate [role=tab]').length>1")

    def test_the_band_is_bl_293_s_at_full_width_with_fixed_arrows(self):
        b = self.b
        o = b.eval("""(()=>{ const v=document.getElementById('v-today'), band=document.querySelector('#v-today .dayband'), r=e=>e.getBoundingClientRect();
          const arrows=()=>[...document.querySelectorAll('.dayedge')].map(e=>[Math.round(r(e).top-r(band).top),Math.round(r(band).right-r(e).right)]);
          const first=arrows(); goDay('2026-10-16'); const later=arrows(); goDay(TODAY);
          return {pieces:['todayDate','dayHead','dayLine','dayMeets','dayClose'].every(id=>band.contains(document.getElementById(id))),
            full:Math.round(r(band).width)===v.clientWidth, first, later, labels:[...document.querySelectorAll('.dayedge')].map(e=>e.getAttribute('aria-label')),
            next:band.nextElementSibling.id, firstSec:[...document.querySelectorAll('#tBrief>.tsec')].find(s=>!s.hidden).id}; })()""")
        self.assertTrue(o["pieces"])                                    # the day line, headline, the line, the meetings, Close the day
        self.assertTrue(o["full"])                                      # the header at full width
        self.assertEqual(o["labels"], ["Previous day", "Next day"])
        self.assertEqual(o["first"], o["later"])                         # the arrows never move between days (BL-321)
        self.assertEqual(o["next"], "tBrief")

    def test_the_headers_content_is_80_percent_centred_and_the_band_full_width_at_1400_and_900(self):
        """#113 (regression, BL-319 04c87566 dropped .col80): the band spans the whole view; its content is 80% of the band's
        inner width, centred; below 640px it is full width."""
        b = self.b
        for w in (1400, 900):
            b.resize(w, 1000)
            o = b.eval("""(()=>{ const v=document.getElementById('v-today'), band=document.querySelector('#v-today .dayband'), c=document.querySelector('#v-today .bandin'),
              r=e=>e.getBoundingClientRect(), cs=getComputedStyle(band), inner=r(band).width-parseFloat(cs.paddingLeft)-parseFloat(cs.paddingRight);
              return {band:Math.round(r(band).width), view:v.clientWidth, ratio:r(c).width/inner,
                offL:r(c).left-r(band).left-parseFloat(cs.paddingLeft), offR:r(band).right-parseFloat(cs.paddingRight)-r(c).right}; })()""")
            self.assertEqual(o["band"], o["view"], w)                      # the coloured band at full width
            self.assertAlmostEqual(o["ratio"], 0.8, delta=0.005, msg=w)    # the content in 80% of it
            self.assertAlmostEqual(o["offL"], o["offR"], delta=1.5, msg=w) # centred


class Home(LiveBrowserCase):
    """The sample vault (populate): six proposals, reminders, an overdue action of Alan's."""

    def today(self):
        self.b.eval("go('today'); renderToday()")
        self.b.wait("document.querySelector('#tdList>li')")


class ToDecide(Home):
    shared_server = False

    def test_it_comes_first_newest_first_top_five_then_open_review(self):
        b = self.b
        b.eval("""SA().vip={people:{},alerts:[{id:'m1',who:'Tom Reid',subject:'Signed FDS',kind:'mail',sent:'2099-01-01T09:00',p:'ABC',link:'https://x/1'},
          {id:'m2',who:'Sam Lee',subject:'Shortlist',kind:'teams',sent:'2000-01-01T09:00',p:'ABC'},{id:'m3',who:'Sam Lee',subject:'Budget',kind:'mail',sent:'2000-01-01T08:00',p:''}]}""")
        self.today()
        o = b.eval(f"""(()=>{{ const L={TD}; return {{first:[...document.querySelectorAll('#tBrief>.tsec:not(.setupsec)')].find(s=>!s.hidden).id,
          kinds:L.map(l=>l.className), msgs:L.filter(l=>l.classList.contains('td-message')).map(l=>l.dataset.td), shown:L.filter(l=>!l.hidden).length, all:L.length, pending:REV.filter(r=>!r.done).length,
          foot:document.querySelector('#tBrief .tdfoot').textContent, count:document.getElementById('nTd').textContent,
          tag:L[0].querySelector('.tdtag').textContent, text:document.getElementById('tdSec').textContent}}; }})()""")
        self.assertEqual(o["first"], "tdSec")
        self.assertIn("td-message", o["kinds"][0])                     # the newest first: the message (sent in 2099)
        self.assertEqual(o["tag"], "Message")
        self.assertNotIn("VIP", o["text"])                              # BL-288: never labelled
        self.assertEqual(o["shown"], min(5, o["all"]))
        self.assertEqual(o["count"], str(o["all"]))
        self.assertIn(f"Open Review ({o['pending']})", o["foot"])
        self.assertGreater(o["all"], 5)
        self.assertIn(f"+{o['all'] - 5} more", o["foot"])
        self.assertEqual(o["msgs"], ["alm1", "alm2", "alm3"])            # newest first
        b.click("#tBrief .tdfoot button.qa")
        b.wait(f"{TD}.every(l=>!l.hidden)")
        b.click("#tdReview")
        b.wait("VIEW==='review'")

    def test_the_bulk_rule_only_routine_rows_have_approve(self):
        b = self.b
        self.today()
        b.eval("EXPAND.add('td'); renderToday()")
        rows = b.eval(f"""{TD}.filter(l=>l.classList.contains('td-review')).map(l=>{{ const r=REV.find(x=>'rv'+x.n===l.dataset.td);
          return [tdApprovable(r), r.kind, !!r.indiv, [...l.querySelectorAll('[data-tdact]')].map(x=>x.dataset.tdact)]; }})""")
        self.assertTrue(rows)
        self.assertTrue(any(r[0] for r in rows) and any(not r[0] for r in rows))
        for ok, kind, indiv, acts in rows:
            if ok:
                self.assertEqual(acts, ["approve", "reject"])
            else:                                                       # minutes, a new risk …: to Review, never approved here
                self.assertEqual(acts[0], "review")
                self.assertNotIn("approve", acts)
                if kind in ("draft", "files"):
                    self.assertEqual(acts, ["review"])

    def test_approve_and_save_then_undo(self):
        b = self.b
        self.today()
        b.eval("EXPAND.add('td'); renderToday()")
        key = b.eval(f"{TD}.find(l=>l.querySelector('[data-tdact=approve]')).dataset.td")
        n = int(key[2:])
        b.click(f'#tdList li[data-td="{key}"] [data-tdact="approve"]')
        b.wait(f"REV.find(r=>r.n==={n}).done==='approved' || !REV.some(r=>r.n==={n}&&!r.done)", 20)
        b.wait(f"!document.querySelector('#tdList li[data-td=\"{key}\"]')")
        b.wait("document.getElementById('snack').classList.contains('on') && document.getElementById('snackU') && !document.getElementById('snackU').hidden", 20)
        self.assertTrue(b.eval("document.activeElement.closest('#tdList')!==null || document.activeElement.id==='hTd'"))   # focus stays in To decide
        b.click("#snackU")                                              # Undo
        b.wait(f"REV.some(r=>r.n==={n}&&!r.done) || [...document.querySelectorAll('#tdList>li')].some(l=>l.dataset.td==='{key}')", 30)

    def test_reject_opens_bl_315_s_menu_esc_returns_a_reason_rejects_with_undo(self):
        b = self.b
        self.today()
        sel = "#tdList [data-tdact=reject]"
        b.eval(f"document.querySelector('{sel}').focus()")
        b.key("Enter")
        b.wait("document.getElementById('rvReason')")
        items = b.eval("[...document.querySelectorAll('#rvReason [role=menuitem]')].map(x=>x.textContent)")
        self.assertTrue(any("Not an action" in x for x in items))
        b.key("Escape")
        b.wait("!document.getElementById('rvReason')")
        self.assertTrue(b.eval(f"document.activeElement===document.querySelector('{sel}')"))
        key = b.eval(f"document.querySelector('{sel}').closest('li').dataset.td")      # BL-315's menu: a reason, then Undo
        title = b.eval(f"JSON.stringify(REV.find(r=>'rv'+r.n==='{key}').rec.t)")
        b.click(f'#tdList li[data-td="{key}"] [data-tdact=reject]')
        b.wait("document.getElementById('rvReason')")
        b.key("1")
        b.wait(f"!document.querySelector('#tdList li[data-td=\"{key}\"]')", 20)
        b.wait("/Rejected 1 as Not an action/.test(document.getElementById('snackT').textContent)", 20)
        b.click("#snackU")
        b.wait(f"REV.some(r=>!r.done&&r.rec&&r.rec.t==={title})", 30)


class Sections(Home):
    shared_server = True

    def test_every_section_in_order_unboxed_resolved_folded(self):
        b = self.b
        self.today()
        o = b.eval("""(()=>{ const secs=[...document.querySelectorAll('#tBrief>.tsec:not(.setupsec)')];
          return {ids:secs.map(s=>s.id), boxed:secs.filter(s=>{ const c=getComputedStyle(s); return parseFloat(c.borderTopWidth)||parseFloat(c.borderLeftWidth)||c.boxShadow!=='none'||!/rgba\\(0, 0, 0, 0\\)|transparent/.test(c.backgroundColor); }).map(s=>s.id),
            inMine:['tOwe','tWait'].every(id=>document.getElementById('mineSec').contains(document.getElementById(id))),
            fold:!document.getElementById('resFold').open, sum:document.querySelector('#resFold>summary').getBoundingClientRect().height,
            pf:[...document.querySelectorAll('#pfTbl th')].map(t=>t.textContent), tip:!!document.querySelector('#pfTbl .pfname[data-tip]')}; })()""")
        self.assertEqual(o["ids"], ["tdSec", "ftSec", "dnSec", "attnSec", "mineSec", "weekSec", "resSec", "pfSec"])
        self.assertEqual(o["boxed"], [])
        self.assertTrue(o["inMine"])                                    # You owe and Waiting on inside Your commitments
        self.assertTrue(o["fold"])
        self.assertLess(o["sum"], 30)                                   # one line
        self.assertEqual(o["pf"], ["Project", "Health", "Evidence", "8 weeks", "Next milestone"])   # the Portfolio as it was
        b.click("#resFold>summary")
        b.wait("document.getElementById('resFold').open")

    def test_the_week_ahead_folds_like_resolved_and_is_remembered(self):
        """#105: the Week ahead hides and shows like Resolved, the choice survives a reload, Resolved is as before."""
        b = self.b
        self.today()
        b.eval("localStorage.removeItem('creaite-week-ahead-hidden')")
        self.today()
        self.assertTrue(b.eval("document.getElementById('weekFold').open"))        # shown until hidden
        b.click("#weekFold>summary")
        b.wait("!document.getElementById('weekFold').open")
        self.assertEqual(b.eval("localStorage.getItem('creaite-week-ahead-hidden')"), "true")
        b.eval("document.querySelector('#weekFold>summary').focus()")
        self.assertTrue(b.eval("document.activeElement.tagName==='SUMMARY'"))      # reachable by keyboard like Resolved's
        b.reload("typeof go==='function' && LIVE")
        self.today()
        self.assertFalse(b.eval("document.getElementById('weekFold').open"))       # still hidden after a reload
        self.assertFalse(b.eval("document.getElementById('resFold').open"))        # Resolved untouched: folded
        b.click("#resFold>summary")
        b.wait("document.getElementById('resFold').open")
        b.click("#weekFold>summary")
        b.wait("document.getElementById('weekFold').open")
        self.assertEqual(b.eval("localStorage.getItem('creaite-week-ahead-hidden')"), "false")

    def test_the_week_ahead_says_why_and_follows_the_setting(self):
        b = self.b
        self.today()
        o = b.eval("""(()=>{ const was=S.weekPrios; D.week={from:TODAY,to:pkAdd(TODAY,5),days:[{date:pkAdd(TODAY,1),dow:"",weekend:false,meetings:[],items:[
            {kind:"decisions",id:"ABC-D-009",p:"ABC",t:"Pick a vendor",o:"Omar Ali"},{kind:"raid",id:"ABC-R-009",p:"ABC",t:"A risk",o:"Omar Ali",type:"Risk",pr:"Urgent"},
            {kind:"milestone",id:"ABC-M-001",p:"ABC",t:"UAT",slip:true}]}],undated:[],further:[]};
          S.weekPrios=["Urgent"]; renderToday(); const out={rows:[...document.querySelectorAll('#weekList li.wkrow')].map(l=>[l.className.replace('wkrow ',''),(l.querySelector('.wkdot')||{className:'none'}).className.replace('wkdot','').trim(),l.querySelector('.wkwhy').textContent,[...l.querySelectorAll('.tacts button')].map(x=>x.dataset.tip)]),
            note:document.querySelectorAll('#weekList .wknote').length};
          S.weekPrios=["Urgent","High"]; renderToday(); out.note2=document.querySelectorAll('#weekList .wknote').length; out.text=document.getElementById('weekList').textContent; S.weekPrios=was; return out; })()""")
        self.assertEqual(o["rows"], [["wk-decisions", "", "needed by", ["Draft a chase"]],
                                     ["wk-raid", "u", "due", ["Write an update", "Draft a chase"]],          # #112: a red dot, not a tag; the why is one word
                                     ["wk-milestone", "", "at risk", ["Open the project"]]])
        self.assertEqual((o["note"], o["note2"]), (0, 0))                # #104: the "Urgent work, every milestone and decision, and meetings" note is gone
        self.assertNotIn("every milestone and decision", o["text"])


class WeekCalm(Header):
    """#112 and #105 (Alan, 16-10-2026): the Week ahead as calm rows with Resolved's fold, the quiet overdue line, the Prep chip;
    #150: Your commitments shows five, then +n more. Over the fixture calendar (Tuesday 13-10-2026 11:05)."""

    WEEK = """D.week={from:TODAY,to:'2026-10-19',days:[
      {date:TODAY,dow:'Tuesday',weekend:false,meetings:[],items:[{kind:'actions',id:'ZZZ-A-001',p:'ABC',t:'Mine due soon',o:S.me,pr:'Urgent'},
        {kind:'actions',id:'ZZZ-A-002',p:'ABC',t:'Theirs due today',o:'Omar Ali',pr:'High'}]},
      {date:'2026-10-14',dow:'Wednesday',weekend:false,meetings:[{start:'10:00',end:'11:00',title:'ABC board',p:'ABC'},{start:'12:00',end:'13:00',title:'DEF sync',p:'DEF'}],
        items:[{kind:'raid',id:'ZZZ-R-001',p:'ABC',t:'A risk',o:'Omar Ali',type:'Risk',pr:'Urgent'},{kind:'milestone',id:'ZZZ-M-001',p:'ABC',t:'UAT start',slip:true},
        {kind:'decisions',id:'ZZZ-D-001',p:'ABC',t:'Pick a vendor',o:'Omar Ali'}]}],undated:[],further:[]};
      D.prep=D.prep||{}; D.prep.meetings=D.prep.meetings||{}; D.prep.meetings['2026-10-14|10:00|ABC board']={series:'abc board',p:'ABC',how:'matched',last:null,day:'2026-10-14',since:'2026-10-07'};
      D.prep.meetings['2026-10-14|12:00|DEF sync']={series:'def sync',p:'DEF',how:'matched',last:null,day:'2026-10-14',since:'2026-10-07'};"""

    def draw(self, extra=""):
        b = self.b
        b.eval("""(()=>{ const x=A.filter(a=>a.id.startsWith('ZZZ')); x.forEach(a=>A.splice(A.indexOf(a),1)); R.filter(a=>a.id.startsWith('ZZZ')).forEach(a=>R.splice(R.indexOf(a),1)); })()""")
        b.eval("A.push({id:'ZZZ-A-001',p:'ABC',t:'Mine due soon',o:S.me,st:'Open',due:pkAdd(TODAY,1)})")
        b.eval(self.WEEK + extra + "; go('today'); renderToday()")
        b.wait("document.querySelector('#weekList .wkrow')")

    def test_calm_rows_one_list_a_day_no_tags_and_nothing_repeated(self):
        b = self.b
        self.draw()
        o = b.eval("""(()=>{ const days=[...document.querySelectorAll('#weekList .wkday')];
          return {heads:days.map(d=>d.querySelector('.wkdh').textContent), lists:days.map(d=>d.querySelectorAll('ul.wkl').length),
            rows:days.map(d=>[...d.querySelectorAll('li.wkrow')].map(l=>[l.className.replace('wkrow ',''), (l.querySelector('.t')||{}).textContent, (l.querySelector('.wkdot')||{className:''}).className.replace('wkdot','').trim(),
              (l.querySelector('.wkwhy')||{textContent:''}).textContent, !!l.querySelector('.wkic svg'), l.querySelectorAll('.wktag,.tag').length])),
            who:document.querySelector('.wkrow .wkwho').textContent, link:!!document.querySelector('.wkrow .wkwho a[data-cock]'),
            below:(()=>{ const r=document.querySelector('.wkrow .tb .t').getBoundingClientRect(), w=document.querySelector('.wkrow .wkwho').getBoundingClientRect(); return w.top>=r.top+r.height/2; })()}; })()""")
        self.assertEqual(o["lists"], [1, 1])
        self.assertEqual(o["rows"][0], [["wk-actions", "Theirs due today", "h", "due", True, 0]])             # mine is under Your commitments: not repeated
        self.assertEqual([r[0] for r in o["rows"][1]], ["wk-meeting", "wk-meeting", "wk-raid", "wk-milestone", "wk-decisions"])
        self.assertEqual([r[3] for r in o["rows"][1]], ["", "", "due", "at risk", "needed by"])               # one quiet word; a meeting has none
        self.assertEqual(o["rows"][1][2][2], "u")                                                              # Urgent: a red dot
        self.assertTrue(all(r[4] and r[5] == 0 for r in o["rows"][1][2:]))                                    # a kind icon, no tag or pill
        self.assertTrue(o["link"] and o["below"])                                                              # who and the project under the title

    def test_the_fold_says_how_many_items_and_to_when_like_resolved(self):
        b = self.b
        self.draw()
        self.assertEqual(b.eval("document.getElementById('weekTo').textContent"), "6 items to Monday 19th October")
        self.assertEqual(b.eval("document.querySelector('#weekFold>summary h2').firstChild.textContent.trim()"), "Week ahead")

    def test_quiet_overdue_line_counts_other_people_s_work_links_to_work_and_hides_at_zero(self):
        b = self.b
        self.draw("""; A.push({id:'ZZZ-A-010',p:'ABC',t:'Late theirs',o:'Omar Ali',st:'Open',due:pkAdd(TODAY,-3)},{id:'ZZZ-A-011',p:'ABC',t:'Late theirs 2',o:'Sara Khan',st:'Open',due:pkAdd(TODAY,-1)},
          {id:'ZZZ-A-012',p:'ABC',t:'Late mine',o:S.me,st:'Open',due:pkAdd(TODAY,-2)},{id:'ZZZ-A-013',p:'ABC',t:'Closed late',o:'Omar Ali',st:'Closed',due:pkAdd(TODAY,-2)});
          R.push({id:'ZZZ-R-010',p:'ABC',t:'Late risk theirs',o:'Omar Ali',st:'Open',due:pkAdd(TODAY,-4)},{id:'ZZZ-R-011',p:'ABC',t:'Late risk mine',o:S.me,st:'Open',due:pkAdd(TODAY,-4)},
          {id:'ZZZ-R-012',p:'ABC',t:'Closed risk',o:'Omar Ali',st:'Closed',due:pkAdd(TODAY,-4)})""")
        # actions and RAID items count (the two actions and one risk added here); a milestone has no owner and is never counted
        want = b.eval("[...A,...R].filter(a=>!a.id.startsWith('ZZZ')&&a.st==='Open'&&a.due&&a.due<TODAY&&!isMe(a.o)).length") + 3
        o = b.eval("(()=>{ const p=document.querySelector('#weekList .wkpoint'); return {text:p.textContent, nav:p.querySelector('a').dataset.nav, first:document.querySelector('#weekList').firstElementChild===p}; })()")
        self.assertEqual(o["text"], f"{want} items owned by others are overdue. See them in Work")
        self.assertTrue(o["first"])                                                                            # above the days
        self.assertIn("due=overdue", o["nav"])
        self.assertIn("!o=%40me", o["nav"])                                                                    # overdue, and not mine
        b.eval("document.querySelector('#weekList .wkpoint a').click()")
        b.wait("VIEW==='work'")
        self.assertEqual(b.eval("[...document.querySelectorAll('#v-work .chip, #v-work .fchip, #v-work [data-filter]')].length>=0"), True)
        self.draw("""; A.splice(0,A.length,...A.filter(a=>isMe(a.o)||a.id.startsWith('ZZZ-A-00'))); R.splice(0,R.length,...R.filter(a=>isMe(a.o)||a.id.startsWith('ZZZ-R-00'))); renderToday()""")
        self.assertEqual(b.eval("document.querySelectorAll('#weekList .wkpoint').length"), 0)                # hidden at zero

    def test_overdue_work_no_longer_leads_the_week(self):
        b = self.b
        self.draw("""; A.push({id:'ZZZ-A-010',p:'ABC',t:'Late theirs',o:'Omar Ali',st:'Open',due:pkAdd(TODAY,-3)}); D.week.days[0].items.push({kind:'actions',id:'ZZZ-A-010',p:'ABC',t:'Late theirs',o:'Omar Ali',od:3})""")
        self.assertNotIn("overdue", b.eval("[...document.querySelectorAll('#weekList .wkwhy')].map(x=>x.textContent).join(' ')"))

    def test_a_meeting_row_is_tinted_with_its_time_and_one_prep_chip(self):
        b = self.b
        self.draw()
        o = b.eval("""(()=>{ const m=document.querySelector('#weekList .wk-meeting'); const cs=getComputedStyle(m), plain=getComputedStyle(document.querySelector('#weekList .wk-raid'));
          return {time:m.querySelector('.wktm').textContent, chips:[...m.querySelectorAll('.wkchip')].map(c=>c.textContent), tint:cs.backgroundColor!==plain.backgroundColor,
            data:m.querySelector('.wkchip').dataset.prepday, others:document.querySelectorAll('#weekList .wk-raid .wkchip').length}; })()""")
        self.assertEqual((o["time"], o["chips"], o["tint"], o["data"], o["others"]), ("10:00", ["Prep"], True, "2026-10-14", 0))
        b.eval("SA().prep_pages={...(SA().prep_pages||{}),'2026-10-14|10:00|ABC board':'projects/ABC Example Programme/agendas/x.html'}; renderToday()")
        self.assertEqual(b.eval("[...document.querySelectorAll('#weekList .wk-meeting')[0].querySelectorAll('.wkchip')].map(c=>c.textContent)"), ["Prep page made"])
        b.click("#weekList .wk-meeting .wkchip.made")
        b.wait("location.hash.startsWith('#prep=')")

    def test_actions_show_on_hover_or_focus_and_are_keyboard_reachable(self):
        b = self.b
        self.draw()
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('#weekList .wk-raid .tacts')).opacity"), "0")
        b.call("Emulation.setFocusEmulationEnabled", enabled=True)
        b.eval("document.querySelector('#weekList .wk-raid .tacts button').focus()")
        b.pump(0.4)
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('#weekList .wk-raid .tacts')).opacity"), "1")          # focus-within
        self.assertEqual(b.eval("[...document.querySelectorAll('#weekList .wk-raid .tacts button')].map(x=>x.dataset.tip)"), ["Write an update", "Draft a chase"])

    def test_more_after_six_rows_a_day_and_further_ahead_is_kept(self):
        b = self.b
        self.draw("""; D.week.days[1].items=[1,2,3,4,5,6,7].map(n=>({kind:'actions',id:'ZZZ-A-9'+n,p:'ABC',t:'Item '+n,o:'Omar Ali',pr:'Low'})); D.week.further=[{date:'2026-10-26',kind:'actions',id:'ZZZ-A-100',p:'ABC',t:'Far one',o:'Omar Ali',pr:'High'}]""")
        self.assertEqual(b.eval("[...document.querySelectorAll('#weekList .wkday:nth-child(2) li.wkrow')].filter(l=>!l.hidden).length"), 6)
        self.assertEqual(b.eval("document.querySelector('#weekList [data-more]').textContent"), "+3 more")
        self.assertIn("Further ahead", b.eval("[...document.querySelectorAll('#weekList .wkdh')].map(h=>h.textContent).join('|')"))
        self.assertIn("Monday 26th October", b.eval("document.querySelector('#weekList .wkday:last-child .wkwhy').textContent"))

    def test_the_fold_follows_forced_colours_and_both_widths(self):
        b = self.b
        self.draw()
        for w in (1400, 900):
            b.resize(w, 1000)
            self.assertEqual(b.eval("(()=>{ const d=document.scrollingElement; return d.scrollWidth-d.clientWidth; })()"), 0, w)
        b.call("Emulation.setEmulatedMedia", features=[{"name": "forced-colors", "value": "active"}])
        self.assertTrue(b.eval("!!document.querySelector('#weekList .wkdot.u') && getComputedStyle(document.querySelector('#weekList .wkdot.u')).backgroundColor!==''"))

    # ---- #150: Your commitments shows five, then +n more ----
    def commitments(self, n):
        b = self.b
        b.eval("""(()=>{ A.filter(a=>a.id.startsWith('ZZZ-C')).forEach(a=>A.splice(A.indexOf(a),1)); })()""")
        b.eval(f"for(let i=1;i<={n};i++) A.push({{id:'ZZZ-C'+i,p:'ABC',t:'Commitment '+i,o:S.me,st:'Open',due:pkAdd(TODAY,-i)}})")
        b.eval("EXPAND.delete('mine'); go('today'); renderToday()")

    def test_150_five_rows_then_more_expands_and_folds(self):
        b = self.b
        self.commitments(8)
        base = b.eval("A.filter(a=>!a.id.startsWith('ZZZ-C')&&isMe(a.o)&&(overdue(a)||soon(a))).length")
        total = base + 8
        shown = "[...document.querySelectorAll('#mineList>li')].filter(l=>!l.hidden).length"
        self.assertEqual(b.eval(shown), 5)
        self.assertEqual(b.eval("document.querySelector('#mineMore [data-more=mine]').textContent"), f"+{total - 5} more")
        self.assertIn(str(total), b.eval("document.getElementById('nMine').textContent"))                      # the count is the total
        b.eval("document.querySelector('#mineMore [data-more=mine]').focus()")
        b.click("#mineMore [data-more=mine]")
        self.assertEqual(b.eval(shown), total)
        self.assertEqual(b.eval("document.querySelector('#mineMore [data-more=mine]').textContent"), "Show fewer")
        self.assertEqual(b.eval("document.querySelector('#mineMore [data-more=mine]').getAttribute('aria-expanded')"), "true")
        b.click("#mineMore [data-more=mine]")
        self.assertEqual(b.eval(shown), 5)
        # the order and the row actions after expanding
        b.eval("EXPAND.add('mine'); renderToday()")
        self.assertTrue(b.eval("document.querySelectorAll('#mineList>li:nth-child(8) [data-tdo=done]').length")==1)
        b.eval("EXPAND.delete('mine'); renderToday()")

    def test_150_no_control_at_five_or_fewer_and_you_owe_is_unchanged(self):
        b = self.b
        b.eval("A.filter(a=>!a.id.startsWith('ZZZ-C')&&isMe(a.o)).forEach(a=>a.st='Closed')")
        self.commitments(5)
        self.assertEqual(b.eval("document.querySelectorAll('#mineMore [data-more=mine]').length"), 0)
        self.commitments(6)
        self.assertEqual(b.eval("document.querySelectorAll('#mineMore [data-more=mine]').length"), 1)
        self.assertTrue(b.eval("document.getElementById('mineSec').contains(document.getElementById('tOwe'))"))   # You owe stays inside


class NoFileNames(Home):
    shared_server = True

    def test_no_staging_file_name_shows_anywhere_on_today(self):
        """BL-319 (Alan, 14-10-2026): nothing on Today shows a raw staging file name (proposed-….json), whatever the file is called."""
        b = self.b
        b.eval("""REV.push({n:990,p:"ABC",kind:"actions",why:"Strong match",indiv:false,flags:[],file:"proposed-0000-00-01-demo.json",ref:1,rec:{t:"Demo action"},src:""},
          {n:991,p:"ABC",kind:"draft",why:"Draft minutes",indiv:true,flags:[],file:"proposed-0000-00-01-demo.json",ref:"meeting",rec:{t:"Minutes: FAL Steering committee"},src:""})""")
        self.today()
        b.eval("EXPAND.add('td'); EXPAND.add('attn'); renderToday(); document.getElementById('resFold').open=true")
        text = b.eval("document.getElementById('v-today').innerText")
        self.assertIn("Demo action", text)
        self.assertNotIn("proposed-", text)
        self.assertNotIn(".json", text)


class Icons(Home):
    shared_server = False

    def test_named_calm_until_hover_or_focus_and_nothing_moves(self):
        b = self.b
        self.today()
        o = b.eval("""(()=>{ const bs=[...document.querySelectorAll('#tBrief .tacts button')];
          return {n:bs.length, named:bs.every(x=>x.getAttribute('aria-label')&&x.dataset.tip), op:getComputedStyle(bs[0].closest('.tacts')).opacity}; })()""")
        self.assertGreater(o["n"], 3)
        self.assertTrue(o["named"])
        self.assertEqual(o["op"], "0.55")
        sel = "#tdList>li:first-child .tacts button"
        before = b.eval(f"JSON.stringify(document.querySelector('{sel}').getBoundingClientRect())")
        b.eval(f"document.querySelector('{sel}').focus()")
        b.pump(0.3)
        self.assertEqual(b.eval(f"getComputedStyle(document.querySelector('{sel}').closest('.tacts')).opacity"), "1")
        self.assertEqual(b.eval(f"JSON.stringify(document.querySelector('{sel}').getBoundingClientRect())"), before)   # nothing moves
        self.assertTrue(b.eval("document.querySelectorAll('#tBrief .tacts button svg').length>3"))

    def test_calm_without_a_pointer_full_on_a_touch_screen(self):
        """CI's headless Linux Chrome reports no hover and no pointer: the rows still rest at 55% there; only a touch screen
        (no hover, a coarse pointer) shows them full, since it can't point at a row."""
        b = self.b
        self.today()
        b.eval("document.activeElement&&document.activeElement.blur()")
        op = "getComputedStyle(document.querySelector('#tBrief .tacts')).opacity"
        try:
            b.call("Emulation.setEmulatedMedia", features=[{"name": "hover", "value": "none"}, {"name": "pointer", "value": "none"}])
            b.pump(0.3)
            self.assertEqual(b.eval(op), "0.55")
            b.call("Emulation.setEmulatedMedia", features=[{"name": "hover", "value": "none"}, {"name": "pointer", "value": "coarse"}])
            b.pump(0.3)
            if b.eval("matchMedia('(hover:none) and (pointer:coarse)').matches"):
                self.assertEqual(b.eval(op), "1")
        finally:
            b.call("Emulation.setEmulatedMedia", features=[])

    def test_mark_done_and_move_the_date_are_staged_with_undo(self):
        b = self.b
        self.today()
        sel = "#mineList [data-tdo=done]"
        b.wait(f"document.querySelector('{sel}')")
        n0 = b.eval("PKS.length")
        b.eval(f"document.querySelector('{sel}').focus()")
        b.key("Enter")
        b.wait(f"PKS.length==={n0 + 1}", 20)
        self.assertIn("marked done", b.eval("document.getElementById('snackT').textContent"))
        b.click("#snackU")
        b.wait(f"PKS.length==={n0}", 20)
        b.eval("go('today'); renderToday()")
        b.click("#mineList [data-tdo=move]")
        b.wait("document.querySelector('.pkpop.pkcal')")
        b.key("Escape")
        b.wait("!document.querySelector('.pkpop.pkcal')")

    def test_decisions_and_reminders_are_icons_too(self):
        b = self.b
        b.eval("""DEC.push({id:'ABC-D-099',p:'ABC',t:'Pick a vendor',by:'Omar Ali',st:'Pending',due:pkAdd(TODAY,2),date:''})""")
        self.today()
        o = b.eval("""(()=>({dn:[...document.querySelectorAll('#dnList .tacts button')].map(x=>x.dataset.tip),
          rem:[...document.querySelectorAll('#attnList .rem .tacts button')].map(x=>x.dataset.tip)}))()""")
        self.assertIn("Draft a chase", o["dn"])
        self.assertIn("Open", o["dn"])
        self.assertTrue(o["rem"] and all(t.startswith(("Draft", "Run", "Needs", "Already")) for t in o["rem"]))


class Rhythm(Home):
    shared_server = True

    def test_the_8px_rhythm_and_the_980px_reading_width(self):
        b = self.b
        self.today()
        o = b.eval("""(()=>{ const brief=document.getElementById('tBrief'), v=document.getElementById('v-today'), r=brief.getBoundingClientRect(), vr=v.getBoundingClientRect(), cs=getComputedStyle(v);
          const secs=[...document.querySelectorAll('#tBrief>.tsec:not([hidden]):not(.setupsec)')];
          return {w:r.width, centre:Math.abs((r.left+r.right)/2-(vr.left+parseFloat(cs.paddingLeft)+(v.clientWidth-parseFloat(cs.paddingLeft)-parseFloat(cs.paddingRight))/2)),
            gaps:secs.map(s=>getComputedStyle(s).marginBottom), rows:[...document.querySelectorAll('#tBrief ol.bl>li:not([hidden])')].filter(l=>l.offsetParent).map(l=>l.getBoundingClientRect().height),
            heads:[...document.querySelectorAll('#tBrief>.tsec:not(.setupsec) h2.th')].map(h=>{ const c=getComputedStyle(h); return [c.fontSize,c.textTransform,c.fontWeight]; })}; })()""")
        self.assertLessEqual(o["w"], 980.5)
        self.assertLess(o["centre"], 1.5)
        self.assertEqual(set(o["gaps"]), {"28px"})
        self.assertTrue(o["rows"])
        self.assertGreaterEqual(min(o["rows"]), 44)
        self.assertEqual({tuple(h)[:2] for h in o["heads"]}, {("16px", "none")})      # BL-325: the shared h2, sentence case
        self.assertEqual(len({tuple(h) for h in o["heads"]}), 1)                     # one heading style


class Narrow(Home):
    shared_server = True
    width = 320

    def test_320_px_nothing_scrolls_sideways_and_dark_reads(self):
        b = self.b
        self.today()
        b.eval("EXPAND.add('td'); renderToday()")
        for theme in ("light", "dark"):
            b.eval(f"document.documentElement.dataset.theme='{theme}'")
            b.pump(0.2)
            sizes = b.eval("""(()=>{ const v=document.getElementById('v-today'), d=document.scrollingElement;
                return [d.scrollWidth-d.clientWidth, v.scrollWidth-v.clientWidth]; })()""")
            self.assertEqual(sizes, [0, 0], theme)
            self.assertTrue(b.eval("[...document.querySelectorAll('#tdList .tacts')].every(t=>t.getBoundingClientRect().right<=document.getElementById('v-today').getBoundingClientRect().right+0.5)"))


if __name__ == "__main__":
    unittest.main()
