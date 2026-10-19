"""#245 (v2.5.2): Intake as a quiet line on Today (dev/sprints/intake-line-brief.md; locked mockup dev/mockups/today-intake-line-mockup.html).

Run: python3 dev/tests/test_today_intake_line.py   (Chrome tier; skipped without Chrome)
The "Intake and Review" section (heading, count, "new" mark, fold, line) is gone from Today. In its place one muted line at the foot
of Your commitments: "Intake: 1 meeting ready to process and 4 proposals to approve.", each phrase a link, and a small x. Nothing
waiting, no line. The x hides it until something new arrives (a count rises) or the next morning, kept in this browser. Today's
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
# exactly p proposals, m meetings with a transcript ready (the last one confidential when conf), f new files in Intake
SET = """window.setWaiting=(p,m,f,conf)=>{ REV.forEach(r=>{ if(r.n<9000) r.done='approved'; }); REV.splice(0,REV.length,...REV.filter(r=>r.n<9000));
  for(let i=0;i<p;i++) REV.push({n:9000+i,p:'ABC',kind:'actions',why:'Strong match',indiv:false,flags:[],file:'proposed-2026-10-13-1000.json',ref:1,rec:{t:'Late one '+i},src:''});
  D.inbox=Array.from({length:f},(_,i)=>({state:'new',name:'f'+i+'.docx'}));
  D.meetings={rows:Array.from({length:m},(_,i)=>({id:'mx'+i,title:(conf&&i===m-1)?'SECRETBOARD':'Steering '+i,p:'ABC',day:TODAY,start:'09:00',end:'10:00',transcript:'available',processed:false,draft:null,private:!!(conf&&i===m-1)}))};
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

    def waiting(self, p, m, f=0, conf=False):
        self.b.eval(f"setWaiting({p},{m},{f},{'true' if conf else 'false'})")

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
        self.waiting(2, 1)                                              # one new proposal since: back, though 2 < the 4 hidden
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
        b.eval(f"localStorage.setItem('{KEY}', JSON.stringify({{day:'2000-01-01', c:{{meetings:1, proposals:4, files:0}}}}))")   # dismissed yesterday
        self.reload()
        self.waiting(4, 1)
        self.assertTrue(b.eval(VISIBLE))

    def test_dismissed_today_with_the_same_counts_stays_hidden_after_reload(self):
        b = self.b
        self.waiting(4, 1)
        b.eval(f"localStorage.setItem('{KEY}', JSON.stringify({{day:TODAY, c:{{meetings:1, proposals:4, files:0}}}}))")
        b.eval("renderToday()")
        self.assertFalse(b.eval("!!document.getElementById('tdQuiet')"))

    def test_nothing_waiting_then_something_arrives_after_a_dismiss_shows_it(self):
        b = self.b
        self.waiting(2, 0)
        b.click("#tdQx")
        b.pump(0.2)
        self.waiting(0, 0)
        self.assertFalse(b.eval("!!document.getElementById('tdQuiet')"))
        self.waiting(1, 0)                                              # one new one: 1 is more than the 0 it was left at
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
