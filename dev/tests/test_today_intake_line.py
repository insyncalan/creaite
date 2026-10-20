"""#245 (v2.5.2): Intake as a quiet line on Today (dev/sprints/intake-line-brief.md; locked mockup dev/mockups/today-intake-line-mockup.html).

Run: python3 dev/tests/test_today_intake_line.py   (Chrome tier; skipped without Chrome)
The "Intake and Review" section (heading, count, "new" mark, fold, line) is gone from Today. In its place one muted line at the foot
of Your commitments: "Intake: 1 meeting ready to process and 4 proposals to approve.", each phrase a link, and a small x. Nothing
waiting, no line. The x hides it until something new arrives (an item not waiting when it was pressed) or the next morning, kept in this browser. Today's
rows have no quick Approve or Reject. Messages from people Alan follows (BL-334) keep their cards, now in a section of their own.
"""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

KEY = "creaite-intakeline-dismissed"
VISIBLE = "(()=>{const e=document.getElementById('tdQuiet'); return !!e && !e.hidden && e.offsetParent!==null && getComputedStyle(e).display!=='none';})()"
# exactly p proposals, m meetings with a transcript ready (the last one confidential when conf), f new files in Intake. po, mo and fo
# shift the ids of the proposals, meetings and files, so a test can say "a different one" (the x keeps ids, not counts)
SET = """window.setWaiting=(p,m,f,conf,po=0,mo=0,fo=0)=>{ REV.forEach(r=>{ if(r.n<9000) r.done='approved'; }); REV.splice(0,REV.length,...REV.filter(r=>r.n<9000));
  for(let i=0;i<p;i++) REV.push({n:9000+po+i,p:'ABC',kind:'actions',why:'Strong match',indiv:false,flags:[],file:'proposed-2026-10-13-1000.json',ref:po+i+1,rec:{t:'Late one '+i},src:''});
  D.inbox=Array.from({length:f},(_,i)=>({state:'new',name:'f'+(fo+i)+'.docx',path:'inbox/f'+(fo+i)+'.docx'}));
  D.meetings={rows:Array.from({length:m},(_,i)=>{ const c=conf&&i===m-1; return c?{key:TODAY+'|09:00|SECRETBOARD',id:null,title:'SECRETBOARD',p:'ABC',day:TODAY,start:'09:00',end:'10:00',transcript:'available',processed:false,draft:null,private:true}
    :{id:'mx'+(mo+i),key:'mx'+(mo+i),title:'Steering '+i,p:'ABC',day:TODAY,start:'09:00',end:'10:00',transcript:'available',processed:false,draft:null,private:false}; })};
  renderBadge(); renderToday(); return true; }"""


class Line(LiveBrowserCase):
    """The sample vault (populate). Each test sets exactly what waits."""
    shared_server = True

    def setUp(self):
        super().setUp()
        b = self.b
        b.eval(f"try{{localStorage.removeItem('{KEY}')}}catch(e){{}}")
        b.eval("go('today')")
        b.eval(SET)

    def waiting(self, p, m, f=0, conf=False, po=0, mo=0, fo=0):
        self.b.eval(f"setWaiting({p},{m},{f},{'true' if conf else 'false'},{po},{mo},{fo})")

    def text(self):
        return self.b.eval("(document.getElementById('tdQuiet')||{textContent:''}).textContent.replace(/\\s+/g,' ').trim()")

    def reload(self):
        self.b.reload(wait_for="typeof go==='function' && LIVE")
        self.b.eval("go('today')")
        self.b.eval(SET)


class Shows(Line):
    def test_counts_in_the_locked_wording_with_two_links_and_an_x(self):
        b = self.b
        self.waiting(4, 1)
        self.assertTrue(b.eval(VISIBLE))
        self.assertEqual(self.text(), "Intake: 1 meeting ready to process and 4 proposals to approve.")
        links = b.eval("[...document.querySelectorAll('#tdQuiet a')].map(a=>[a.dataset.tdq,a.textContent,a.getAttribute('href')])")
        self.assertEqual(links, [["meetings", "1 meeting ready to process", "#inbox"], ["proposals", "4 proposals to approve", "#review"]])
        self.assertTrue(b.eval("!!document.querySelector('#tdQuiet svg.i') && !!document.querySelector('#tdQuiet button#tdQx svg')"))

    def test_plurals_and_singulars(self):
        self.waiting(1, 3)
        self.assertEqual(self.text(), "Intake: 3 meetings ready to process and 1 proposal to approve.")

    def test_only_one_kind_waiting_has_one_phrase(self):
        self.waiting(2, 0)
        self.assertEqual(self.text(), "Intake: 2 proposals to approve.")
        self.waiting(0, 2)
        self.assertEqual(self.text(), "Intake: 2 meetings ready to process.")

    def test_new_files_in_intake_are_a_third_phrase(self):
        self.waiting(4, 1, 2)
        self.assertEqual(self.text(), "Intake: 1 meeting ready to process, 4 proposals to approve and 2 new files to process.")
        self.assertEqual(self.b.eval("document.querySelector('#tdQuiet [data-tdq=files]').getAttribute('href')"), "#inbox")

    def test_the_line_has_no_live_role_and_a_small_hidden_region_announces_the_count_politely(self):
        b = self.b
        self.waiting(4, 1, 2)
        o = b.eval("""(()=>{ const l=document.getElementById('tdQuiet'), r=document.getElementById('tdQuietLive'), rc=r.getBoundingClientRect(); return {
          lineRole:l.getAttribute('role'), lineLive:l.getAttribute('aria-live'), inLine:l.contains(r), role:r.getAttribute('role'),
          live:r.getAttribute('aria-live'), atomic:r.getAttribute('aria-atomic'), text:r.textContent, small:rc.width<=2&&rc.height<=2,
          visible:l.textContent.replace(/\\s+/g,' ').trim()}; })()""")
        self.assertEqual((o["lineRole"], o["lineLive"], o["inLine"]), (None, None, False))
        self.assertEqual((o["role"], o["live"], o["atomic"]), ("status", "polite", "true"))
        self.assertEqual(o["text"], "7 waiting in Intake")                       # the count alone, not the sentence
        self.assertTrue(o["small"])                                              # visually hidden
        self.assertEqual(o["visible"], "Intake: 1 meeting ready to process, 4 proposals to approve and 2 new files to process.")

    def test_a_redraw_with_the_same_count_leaves_the_region_alone_and_a_dismiss_silences_it(self):
        b = self.b
        self.waiting(4, 1)
        b.eval("window.__live=document.getElementById('tdQuietLive'); window.__node=__live.firstChild; true")
        b.eval("renderToday()")
        self.assertTrue(b.eval("document.getElementById('tdQuietLive')===__live && __live.firstChild===__node"))   # same node: nothing re-read
        self.waiting(5, 1)
        self.assertEqual(b.eval("document.getElementById('tdQuietLive').textContent"), "6 waiting in Intake")
        b.click("#tdQx")
        b.pump(0.2)
        self.assertEqual(b.eval("document.getElementById('tdQuietLive').textContent"), "")
        self.assertTrue(b.eval("document.getElementById('tdQuietLive')===__live"))

    def test_it_is_the_last_thing_in_your_commitments(self):
        b = self.b
        self.waiting(4, 1)
        self.assertTrue(b.eval("document.getElementById('mineSec').lastElementChild.contains(document.getElementById('tdQuiet'))"))
        self.assertTrue(b.eval("document.getElementById('tdQuiet').closest('#mineSec')!==null"))

    def test_no_line_when_nothing_waits(self):
        b = self.b
        self.waiting(0, 0, 0)
        self.assertFalse(b.eval("!!document.getElementById('tdQuiet')"))
        self.assertEqual(b.eval("document.getElementById('tdQuietHost').children.length"), 1)       # only the (silent) live region stays
        self.assertEqual(b.eval("document.getElementById('tdQuietLive').textContent"), "")
        self.assertEqual(b.eval("document.getElementById('mineSec').textContent.includes('Intake:')"), False)

    def test_the_section_and_its_fold_are_gone_and_the_page_never_says_intake_and_review(self):
        b = self.b
        self.waiting(4, 1)
        o = b.eval("""({fold:!!document.getElementById('tdFold'), tdLine:!!document.getElementById('tdLine'), tdNew:!!document.getElementById('tdNew'),
          heads:[...document.querySelectorAll('#v-today h2')].map(h=>(h.firstChild||h).textContent.trim()), text:document.getElementById('v-today').textContent.includes('Intake and Review')})""")
        self.assertFalse(o["fold"])
        self.assertFalse(o["tdLine"])
        self.assertFalse(o["tdNew"])
        self.assertNotIn("Intake and Review", o["heads"])
        self.assertFalse(o["text"])
        self.assertEqual(b.eval("localStorage.getItem('creaite-intake-review-hidden')"), None)

    def test_no_quick_approve_or_reject_on_todays_rows(self):
        b = self.b
        self.waiting(4, 1)
        n = b.eval("""[...document.querySelectorAll('#v-today button, #v-today [role=button], #v-today a')].filter(e=>{
          const w=((e.getAttribute('aria-label')||'')+' '+(e.dataset.tip||'')+' '+e.textContent).trim();
          return /^(Approve|Reject|Open in Review)\\b/i.test(w) || /\\b(Approve and save|Reject, with a reason)\\b/i.test(w); }).map(e=>e.outerHTML).join('|')""")
        self.assertEqual(n, "")
        self.assertEqual(b.eval("document.querySelectorAll('#v-today [data-tdact=approve],#v-today [data-tdact=reject],#v-today [data-rvact]').length"), 0)

    def test_confidential_meeting_counts_but_is_never_named(self):
        b = self.b
        self.waiting(2, 2, 0, conf=True)
        self.assertEqual(self.text(), "Intake: 2 meetings ready to process and 2 proposals to approve.")
        self.assertNotIn("SECRETBOARD", b.eval("document.getElementById('v-today').innerText + document.getElementById('v-today').innerHTML"))

    def test_no_vip_label_and_dates_are_not_us_style(self):
        self.waiting(4, 1)
        t = self.b.eval("document.getElementById('tdQuiet').outerHTML")
        self.assertNotRegex(t, r"(?i)\bvip\b")
        self.assertNotRegex(self.text(), r"\d{4}-\d{2}-\d{2}")          # a date is written DD-MM-YYYY, never stored-style
        self.assertNotRegex(self.text(), r"\d{1,2}/\d{1,2}/\d{2,4}")

    def test_the_phrases_say_what_the_pages_count(self):
        b = self.b
        self.waiting(3, 2, 1)
        o = b.eval("({p:REV.filter(r=>!r.done).length, m:MTG().filter(mtgHasTx).length, f:(D.inbox||[]).filter(x=>x.state==='new').length})")
        self.assertEqual(o, {"p": 3, "m": 2, "f": 1})
        self.assertIn("3 proposals to approve", self.text())
        self.assertIn("2 meetings ready to process", self.text())


class Links(Line):
    def where(self, key):
        b = self.b
        b.eval(f"document.querySelector('#tdQuiet [data-tdq={key}]').focus()")
        self.assertTrue(b.eval(f"document.activeElement===document.querySelector('#tdQuiet [data-tdq={key}]')"))   # a real link: Tab reaches it
        b.key("Enter")

    def test_proposals_open_review_and_meetings_open_intake(self):
        b = self.b
        self.waiting(4, 1, 1)
        for key, view in (("proposals", "review"), ("meetings", "inbox"), ("files", "inbox")):
            self.where(key)
            b.wait(f"VIEW==='{view}'")
            b.eval("go('today')")
            b.eval("renderToday()")
            b.wait("document.getElementById('tdQuiet')")

    def test_the_target_lives_in_one_function(self):
        b = self.b
        self.assertEqual(b.eval("[intakeTarget('proposals'),intakeTarget('meetings'),intakeTarget('files')]"), ["review", "inbox", "inbox"])

    def test_a_click_goes_to_the_page_too(self):
        b = self.b
        self.waiting(4, 1)
        b.click("#tdQuiet [data-tdq=meetings]")
        b.wait("VIEW==='inbox'")


class Dismiss(Line):
    def test_the_x_is_a_real_button_with_a_name_and_a_tooltip(self):
        b = self.b
        self.waiting(4, 1)
        o = b.eval("""(()=>{ const x=document.getElementById('tdQx'); return {tag:x.tagName, type:x.type, name:x.getAttribute('aria-label'), tip:x.dataset.tip,
          ib:x.classList.contains('ib'), right:x.getBoundingClientRect().right<=document.getElementById('tdQuiet').getBoundingClientRect().right+0.5,
          after:!!(document.querySelector('#tdQuiet .tdq').compareDocumentPosition(x)&4)}; })()""")
        self.assertEqual(o["tag"], "BUTTON")
        self.assertEqual(o["type"], "button")
        self.assertEqual(o["name"], "Dismiss until something new arrives")
        self.assertEqual(o["tip"], "Dismiss until something new arrives")
        self.assertTrue(o["ib"] and o["right"] and o["after"])

    def test_the_x_hides_it_and_it_stays_hidden_across_re_render_and_reload(self):
        b = self.b
        self.waiting(4, 1)
        b.click("#tdQx")
        b.pump(0.2)
        self.assertFalse(b.eval("!!document.getElementById('tdQuiet')"))
        b.eval("renderToday()")
        self.assertFalse(b.eval("!!document.getElementById('tdQuiet')"))
        stored = b.eval(f"JSON.parse(localStorage.getItem('{KEY}'))")
        self.assertEqual(stored["day"], b.eval("TODAY"))
        self.reload()
        self.waiting(4, 1)
        self.assertFalse(b.eval("!!document.getElementById('tdQuiet')"))

    def test_dismissing_changes_nothing_in_review_or_intake(self):
        b = self.b
        self.waiting(4, 1, 2)
        b.click("#tdQx")
        b.pump(0.2)
        self.assertEqual(b.eval("[REV.filter(r=>!r.done).length, MTG().filter(mtgHasTx).length, D.inbox.length]"), [4, 1, 2])

    def test_it_comes_back_when_a_new_proposal_arrives(self):
        b = self.b
        self.waiting(4, 1)
        b.click("#tdQx")
        b.pump(0.2)
        self.waiting(4, 1)                                              # a refresh with the same things: still hidden
        self.assertFalse(b.eval("!!document.getElementById('tdQuiet')"))
        self.waiting(5, 1)
        self.assertEqual(self.text(), "Intake: 1 meeting ready to process and 5 proposals to approve.")

    def test_it_comes_back_when_a_new_meeting_or_file_arrives(self):
        b = self.b
        self.waiting(4, 1)
        b.click("#tdQx")
        b.pump(0.2)
        self.waiting(4, 2)
        self.assertTrue(b.eval(VISIBLE))
        b.click("#tdQx")
        b.pump(0.2)
        self.waiting(4, 2, 1)
        self.assertTrue(b.eval(VISIBLE))

    def test_fewer_waiting_stays_hidden_and_a_later_rise_above_the_new_low_returns(self):
        b = self.b
        self.waiting(4, 1)
        b.click("#tdQx")
        b.pump(0.2)
        self.waiting(1, 1)                                              # Alan approved three: nothing new, still quiet
        self.assertFalse(b.eval("!!document.getElementById('tdQuiet')"))
        self.assertFalse(b.eval("!!document.getElementById('tdQuiet')"))
        b.eval("REV.push({...REV.find(r=>r.n===9000), n:9010, ref:11}); renderToday()")   # one new proposal since: back, though 2 < the 4 hidden
        self.assertTrue(b.eval(VISIBLE))

    def test_a_swap_is_new(self):
        b = self.b
        self.waiting(1, 1)
        b.click("#tdQx")
        b.pump(0.2)
        self.waiting(0, 2)                                              # the proposal went, a second meeting came
        self.assertTrue(b.eval(VISIBLE))

    def test_it_comes_back_the_next_morning(self):
        b = self.b
        self.waiting(4, 1)
        b.click("#tdQx")
        b.pump(0.2)
        b.eval(f"(()=>{{ const d=JSON.parse(localStorage.getItem('{KEY}')); d.day='2000-01-01'; localStorage.setItem('{KEY}', JSON.stringify(d)); }})()")   # dismissed yesterday
        self.reload()
        self.waiting(4, 1)
        self.assertTrue(b.eval(VISIBLE))

    def test_dismissed_today_with_the_same_ids_stays_hidden_after_reload(self):
        b = self.b
        self.waiting(4, 1)
        b.click("#tdQx")
        b.pump(0.2)
        kept = b.eval(f"localStorage.getItem('{KEY}')")
        self.reload()
        b.eval(f"localStorage.setItem('{KEY}', {kept!r})")
        self.waiting(4, 1)
        self.assertFalse(b.eval("!!document.getElementById('tdQuiet')"))

    def test_a_count_only_entry_is_not_read_as_a_dismissal(self):
        """The first #245 build kept counts (so new arrivals could stay hidden); such an entry is ignored, and the line shows."""
        b = self.b
        self.waiting(4, 1)
        b.eval(f"localStorage.setItem('{KEY}', JSON.stringify({{day:TODAY, c:{{meetings:1, proposals:4, files:0}}}}))")
        b.eval("renderToday()")
        self.assertTrue(b.eval(VISIBLE))

    def test_approve_two_and_two_new_staged_while_on_review_shows_it_on_return(self):
        """Repro (a): 4 waiting, x; in Review 2 are approved and 2 new ones are staged; back on Today the line shows (4 is not more than
        4, but 2 of the 4 are new)."""
        b = self.b
        self.waiting(4, 1)
        b.click("#tdQx")
        b.pump(0.2)
        b.eval("go('review')")
        b.eval("""REV.filter(r=>r.n===9000||r.n===9001).forEach(r=>r.done='approved');
          REV.push({...REV.find(r=>r.n===9002), n:9004, ref:5}, {...REV.find(r=>r.n===9002), n:9005, ref:6}); true""")
        b.eval("go('today')")
        b.pump(0.2)
        self.assertTrue(b.eval(VISIBLE))
        self.assertEqual(self.text(), "Intake: 1 meeting ready to process and 4 proposals to approve.")

    def test_a_fifth_shows_it_and_approving_an_older_one_keeps_it_showing(self):
        """Repro (b): 4 dismissed, a 5th arrives (shows); one of the older 4 is approved: the new one still waits, so the line stays."""
        b = self.b
        self.waiting(4, 1)
        b.click("#tdQx")
        b.pump(0.2)
        b.eval("REV.push({...REV.find(r=>r.n===9000), n:9004, ref:5}); renderToday()")
        self.assertTrue(b.eval(VISIBLE))
        b.eval("REV.find(r=>r.n===9000).done='approved'; renderToday()")
        self.assertTrue(b.eval(VISIBLE))
        self.assertEqual(self.text(), "Intake: 1 meeting ready to process and 4 proposals to approve.")

    def test_what_is_kept_is_hashed_ids_per_kind_and_never_text(self):
        b = self.b
        self.waiting(3, 2, 2, conf=True)
        b.click("#tdQx")
        b.pump(0.2)
        raw = b.eval(f"localStorage.getItem('{KEY}')")
        import json
        d = json.loads(raw)
        self.assertEqual(set(d), {"day", "ids"})
        self.assertEqual({k: len(v) for k, v in d["ids"].items()}, {"meetings": 2, "proposals": 3, "files": 2})
        for v in d["ids"].values():
            for h in v:
                self.assertRegex(h, r"^[0-9a-f]{8}$")
        for word in ("SECRETBOARD", "Steering", "proposed-", ".docx", "inbox", "Late one", "mx"):
            self.assertNotIn(word, raw)

    def test_the_kept_ids_are_capped_at_200_a_kind_and_many_waiting_still_hide(self):
        b = self.b
        self.waiting(250, 1)
        b.click("#tdQx")
        b.pump(0.2)
        n = b.eval(f"JSON.parse(localStorage.getItem('{KEY}')).ids.proposals.length")
        self.assertLessEqual(n, 200)
        self.assertLess(len(b.eval(f"localStorage.getItem('{KEY}')")), 4000)
        b.eval("renderToday()")
        self.assertFalse(b.eval("!!document.getElementById('tdQuiet')"))
        self.reload()
        self.waiting(250, 1)
        self.assertFalse(b.eval("!!document.getElementById('tdQuiet')"))
        b.eval("REV.push({...REV.find(r=>r.n===9000), n:9999, ref:999}); renderToday()")   # one more, not kept: back
        self.assertTrue(b.eval(VISIBLE))

    def test_a_swap_beyond_the_cap_is_never_hidden(self):
        """250 dismissed (50 beyond the cap): one of the 50 left out goes and a new one comes. The count of unknown ids is no more than
        the 50 left out, but the set has changed, so the line shows."""
        b = self.b
        self.waiting(250, 1)
        b.click("#tdQx")
        b.pump(0.2)
        self.assertFalse(b.eval("!!document.getElementById('tdQuiet')"))
        # approve the first proposal (the kept list is the last 200, so the first one is beyond the cap) and stage a new one
        b.eval("REV.find(r=>r.n===9000).done='approved'; REV.push({...REV.find(r=>r.n===9001), n:9998, ref:998}); renderToday()")
        self.assertTrue(b.eval(VISIBLE))
        self.assertIn("250 proposals to approve", self.text())

    def test_the_same_set_beyond_the_cap_in_another_order_stays_hidden(self):
        b = self.b
        self.waiting(250, 1)
        b.click("#tdQx")
        b.pump(0.2)
        b.eval("REV.reverse(); renderToday()")
        self.assertFalse(b.eval("!!document.getElementById('tdQuiet')"))

    def test_a_reused_proposal_file_name_with_new_items_shows_it(self):
        """minutes.py names a proposal file by the minute, so a later proposal can reuse the name and the item numbers: the item's
        created time is part of its kept id, so the new items are new."""
        b = self.b
        b.eval("REV.forEach(r=>{ if(r.n<9000) r.done='approved'; }); REV.splice(0,REV.length,...REV.filter(r=>r.n<9000)); D.inbox=[]; D.meetings={rows:[]};"
               "REV.push({n:9000,p:'ABC',kind:'actions',why:'',indiv:false,flags:[],file:'proposed-2026-10-20-1000.json',ref:1,made:'2026-10-20T10:00:05',rec:{t:'Old'},src:''});"
               "renderBadge(); renderToday(); true")
        self.assertTrue(b.eval(VISIBLE))
        b.click("#tdQx")
        b.pump(0.2)
        self.assertFalse(b.eval("!!document.getElementById('tdQuiet')"))
        b.eval("REV[REV.length-1].done='approved'; REV.push({n:9001,p:'ABC',kind:'actions',why:'',indiv:false,flags:[],file:'proposed-2026-10-20-1000.json',ref:1,"
               "made:'2026-10-20T10:00:41',rec:{t:'New'},src:''}); renderToday()")
        self.assertTrue(b.eval(VISIBLE))

    def test_a_store_that_reads_but_will_not_write_still_hides_it_for_this_page_load(self):
        b = self.b
        self.waiting(4, 1)
        b.eval("Storage.prototype.setItem=function(){ throw 1; }; true")
        b.click("#tdQx")
        b.pump(0.2)
        self.assertFalse(b.eval("!!document.getElementById('tdQuiet')"))
        b.eval("renderToday()")
        self.assertFalse(b.eval("!!document.getElementById('tdQuiet')"))
        b.eval("REV.push({...REV.find(r=>r.n===9000), n:9004, ref:5}); renderToday()")   # and something new still shows it
        self.assertTrue(b.eval(VISIBLE))

    def test_nothing_waiting_then_something_arrives_after_a_dismiss_shows_it(self):
        b = self.b
        self.waiting(2, 0)
        b.click("#tdQx")
        b.pump(0.2)
        self.waiting(0, 0)
        self.assertFalse(b.eval("!!document.getElementById('tdQuiet')"))
        self.waiting(1, 0, po=5)                                        # one new one (an id not dismissed): shows
        self.assertTrue(b.eval(VISIBLE))

    def test_dismiss_from_the_keyboard_keeps_focus_in_the_page(self):
        b = self.b
        self.waiting(4, 1)
        b.eval("document.getElementById('tdQx').focus()")
        b.key("Enter")
        b.pump(0.2)
        self.assertFalse(b.eval("!!document.getElementById('tdQuiet')"))
        self.assertFalse(b.eval("document.activeElement===document.body"))
        self.assertTrue(b.eval("!!document.activeElement.closest('#v-today')"))

    def test_storage_failing_still_hides_it_for_this_page_load(self):
        b = self.b
        self.waiting(4, 1)
        b.eval("Object.defineProperty(window,'localStorage',{get(){ throw new Error('blocked'); }}); true")
        b.eval("renderToday()")
        self.assertTrue(b.eval(VISIBLE))
        b.click("#tdQx")
        b.pump(0.2)
        self.assertFalse(b.eval("!!document.getElementById('tdQuiet')"))
        b.eval("renderToday()")
        self.assertFalse(b.eval("!!document.getElementById('tdQuiet')"))


class TwoTabs(Line):
    """Two tabs of one browser share localStorage: what one dismisses, the other must read as dismissed (the store is the truth, the page's
    own memory only a fallback). The second tab is a second page of the same Chrome profile, driven by its own connection."""

    def other_tab(self):
        import json
        import urllib.request
        from cdp import Browser, WebSocket
        t = json.load(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{self.b.port}/json/new?{self.base}/", method="PUT")))
        c = Browser.__new__(Browser)                    # the same Chrome (so the same storage); only the connection is new
        c.ws, c.n, c.events, c.errors = WebSocket(t["webSocketDebuggerUrl"]), 0, [], []
        for domain in ("Page", "Runtime"):
            c.call(f"{domain}.enable")
        self.addCleanup(c.ws.close)
        c.wait("typeof go==='function' && LIVE")
        if os.environ.get("CREAITE_NOW"):               # the same pinned clock as the first tab, so both say the same TODAY
            from live_browser import pin_page_clock
            pin_page_clock(c, os.environ["CREAITE_NOW"])
        c.settle_boot()
        c.eval("go('today')")
        c.eval(SET)
        return c

    def test_a_dismiss_in_one_tab_is_read_as_dismissed_by_the_other(self):
        a = self.b
        self.waiting(4, 1)
        c = self.other_tab()
        c.eval("setWaiting(4,1,0,false)")
        self.assertTrue(c.eval(VISIBLE))
        a.eval("document.getElementById('tdQx').click()")      # a click event: the first tab is in the background now, so no animation frames
        a.pump(0.2)
        self.assertFalse(a.eval("!!document.getElementById('tdQuiet')"))
        c.eval("renderToday()")                                                 # its next redraw reads the store, not its own memory
        self.assertFalse(c.eval("!!document.getElementById('tdQuiet')"))

    def test_the_other_tab_hides_at_once_on_the_storage_event(self):
        a = self.b
        self.waiting(4, 1)
        c = self.other_tab()
        c.eval("setWaiting(4,1,0,false)")
        self.assertTrue(c.eval(VISIBLE))
        a.eval("document.getElementById('tdQx').click()")      # a click event: the first tab is in the background now, so no animation frames
        c.wait("!document.getElementById('tdQuiet')", 10)                      # no redraw asked for: the storage event does it

    def test_clearing_the_store_in_one_tab_shows_it_again_in_the_other_even_after_it_dismissed_there(self):
        a = self.b
        self.waiting(4, 1)
        c = self.other_tab()
        c.eval("setWaiting(4,1,0,false)")
        c.eval("document.getElementById('tdQx').click()")                      # this tab's own memory now holds a dismissal too
        self.assertFalse(c.eval("!!document.getElementById('tdQuiet')"))
        a.eval(f"localStorage.removeItem('{KEY}')")                             # the store (the truth) says: not dismissed
        c.eval("renderToday()")
        self.assertTrue(c.eval(VISIBLE))


class Staged(LiveBrowserCase):
    """Repro (a) through the vault: real proposal files in staging, the page's own reload of the data, Review and back."""

    def stage(self, name, title):
        import json
        item = {"n": 1, "op": "new", "table": "actions", "decision": "pending",
                "values": {"project": "ABC", "description": title, "owner": "Jane Doe", "source": "minutes"}}
        (self.v.root / "system/staging" / f"proposed-2026-10-20-{name}.json").write_text(json.dumps({"items": [item]}))

    def decide(self, name):
        import json
        f = self.v.root / "system/staging" / f"proposed-2026-10-20-{name}.json"
        d = json.loads(f.read_text())
        d["items"][0]["decision"] = "approved"
        f.write_text(json.dumps(d))

    def pending(self):
        return self.b.eval("REV.filter(r=>!r.done).length")

    def test_a_staged_row_carries_its_proposal_s_created_time(self):
        """#245: the created time is part of a proposal's dismissed id, so the page's rows must carry it."""
        import json
        b = self.b
        f = self.v.root / "system/staging" / "proposed-2026-10-20-made.json"
        f.write_text(json.dumps({"created": "2026-10-20T10:00:41", "items": [{"n": 1, "op": "new", "table": "actions", "decision": "pending",
                     "values": {"project": "ABC", "description": "Made", "owner": "Jane Doe", "source": "minutes"}}]}))
        b.eval("window.__ok=0; reloadData().then(()=>window.__ok=1); true")
        b.wait("window.__ok===1", 30)
        self.assertEqual(b.eval("(REV.find(r=>r.file==='proposed-2026-10-20-made.json')||{}).made"), "2026-10-20T10:00:41")

    def test_approve_two_and_stage_two_while_on_review_then_today_shows_the_line(self):
        b = self.b
        b.eval(f"try{{localStorage.removeItem('{KEY}')}}catch(e){{}}")
        for i in range(4):
            self.stage(f"w{i}", f"Waiting {i}")
        b.eval("reloadData().then(()=>window.__ok=1); true")
        b.wait("window.__ok===1", 30)
        b.eval("go('today')")
        before = self.pending()
        self.assertTrue(b.eval(VISIBLE))
        b.click("#tdQx")
        b.pump(0.2)
        self.assertFalse(b.eval("!!document.getElementById('tdQuiet')"))
        b.eval("go('review')")
        self.decide("w0")
        self.decide("w1")
        self.stage("n0", "New 0")
        self.stage("n1", "New 1")
        b.eval("window.__ok=0; reloadData().then(()=>window.__ok=1); true")
        b.wait("window.__ok===1", 30)
        self.assertEqual(self.pending(), before)                       # the same count waits: only which ones has changed
        b.eval("go('today')")
        b.pump(0.2)
        self.assertTrue(b.eval(VISIBLE))


class Messages(Line):
    """BL-334 message cards survive: they were rows of the old section and have no other home on Today."""

    def test_message_cards_keep_a_section_of_their_own_called_messages(self):
        b = self.b
        b.eval("""SA().vip={people:{},alerts:[{id:'m1',who:'Tom Reid',subject:'Signed FDS',kind:'mail',sent:'2099-01-01T09:00',p:'ABC',link:'https://x/1'}]}; renderToday()""")
        o = b.eval("""({head:document.getElementById('hTd').firstChild.textContent.trim(), rows:[...document.querySelectorAll('#tdList>li')].map(l=>l.dataset.td),
          fold:!!document.getElementById('tdFold'), hidden:document.getElementById('tdSec').hidden, text:document.getElementById('tdSec').textContent,
          after:document.getElementById('tdSec').previousElementSibling.id, before:document.getElementById('tdSec').nextElementSibling.id})""")
        self.assertEqual(o["head"], "Messages")
        self.assertEqual(o["rows"], ["alm1"])
        self.assertFalse(o["fold"])
        self.assertFalse(o["hidden"])
        self.assertEqual((o["after"], o["before"]), ("mineSec", "weekSec"))
        self.assertNotRegex(o["text"], r"(?i)\bvip\b")

    def test_no_messages_no_section(self):
        b = self.b
        b.eval("SA().vip={people:{},alerts:[]}; renderToday()")
        self.assertTrue(b.eval("document.getElementById('tdSec').hidden"))


class Narrow(Line):
    width, height = 900, 900

    def test_900_px_one_line_or_two_never_a_list_and_nothing_scrolls_sideways(self):
        b = self.b
        self.waiting(4, 1, 2)
        for theme in ("light", "dark"):
            b.eval(f"document.documentElement.dataset.theme='{theme}'")
            b.pump(0.2)
            self.assertLess(b.eval("document.getElementById('tdQuiet').getBoundingClientRect().height"), 70)
            self.assertEqual(b.eval("document.scrollingElement.scrollWidth<=document.scrollingElement.clientWidth"), True)
            self.assertTrue(b.eval("document.getElementById('tdQx').getBoundingClientRect().right<=document.getElementById('tdQuiet').getBoundingClientRect().right+0.5"))


if __name__ == "__main__":
    unittest.main()
