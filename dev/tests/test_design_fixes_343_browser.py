"""#343 / #342 (the safe design batch, 2.6.4b), measured in the live app against the page's own boxes (no pixel numbers
that depend on a font): contrast and targets, then the other groups as they land. Each check has a mutant that must fail.

Run: python3 dev/tests/test_design_fixes_343_browser.py   (needs Google Chrome; skipped otherwise). Desktop and 900 px only.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

# Interactive things on the shown screen that are smaller than 24 px either way (a link inside running text is not counted)
SMALL_TARGETS = r"""(sel=>{ const v=e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(e).visibility!=='hidden'&&!e.closest('[hidden],[inert]')};
  return [...document.querySelectorAll(sel)].filter(v).map(e=>{const r=e.getBoundingClientRect();return [e.className||e.tagName, Math.round(r.width), Math.round(r.height)]}).filter(x=>x[1]<24||x[2]<24); })"""
SMALL_TEXT = r"""(scope=>{ const root=document.querySelector(scope)||document.body, v=e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(e).visibility!=='hidden'&&!e.closest('[hidden],[inert]')};
  return [...root.querySelectorAll('*')].filter(e=>v(e)&&[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())&&parseFloat(getComputedStyle(e).fontSize)<12).map(e=>[e.className&&e.className.baseVal===undefined?e.className:e.tagName, e.textContent.trim().slice(0,24)]); })"""


class ContrastAndTargets(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 900

    def small(self, sel):
        return self.b.eval("(%s)(%r)" % (SMALL_TARGETS, sel))

    def at(self, w):
        self.b.resize(w, 900)
        self.b.pump(0.3)

    def test_today_help_button_evidence_links_and_week_ahead_are_24px(self):
        b = self.b
        for w in (1400, 900):
            self.at(w)
            b.eval("go('today')")
            b.wait("document.querySelector('.legbtn')")
            self.assertEqual(self.small(".legbtn,.ev a.cntl,.tres>details>summary"), [], w)

    def test_mutant_a_small_help_button_is_caught(self):
        b = self.b
        b.eval("go('today')")
        b.wait("document.querySelector('.legbtn')")
        b.eval("document.head.insertAdjacentHTML('beforeend','<style id=mut>.legbtn{width:18px;height:18px}</style>')")
        self.assertTrue(self.small(".legbtn"))

    def test_work_row_ids_and_review_source_links_are_24px(self):
        b = self.b
        for w in (1400, 900):
            self.at(w)
            b.eval("go('work')")
            b.wait("document.querySelector('a.rowid')")
            self.assertEqual(self.small("a.rowid"), [], w)
        b.eval("document.body.insertAdjacentHTML('beforeend','<p id=mutsrc>Text <a class=srclink href=#>Open source</a> more</p>')")
        self.assertEqual(self.small("#mutsrc .srclink"), [])
        b.eval("document.head.insertAdjacentHTML('beforeend','<style>.srclink,a.rowid{padding:0;margin:0;display:inline}</style>')")
        self.assertTrue(self.small("a.rowid,#mutsrc .srclink"))        # mutant: the rule gone, both are caught

    def test_nothing_under_12px_on_the_changed_screens(self):
        b = self.b
        for w in (1400, 900):
            self.at(w)
            for js, scope in (("go('today')", "#v-today"), ("go('work')", "#v-work"), ("go('help')", "#v-help"), ("go('cockpit','ABC')", "#v-cockpit")):
                b.eval(js)
                b.pump(0.8)
                self.assertEqual(b.eval("(%s)('%s')" % (SMALL_TEXT, scope)), [], (w, js))

    def test_mutant_small_text_is_caught(self):
        b = self.b
        b.eval("go('work')")
        b.wait("document.querySelector('a.rowid')")
        b.eval("document.querySelector('#v-work').insertAdjacentHTML('beforeend','<span id=mut style=\"font-size:10px\">tiny</span>')")
        self.assertTrue(b.eval("(%s)('#v-work')" % SMALL_TEXT))


# A text of known words, in a box that is stepped from narrow to wide: on how many widths the last line is a single word. It reads the
# page's own wrapping (Range rects of the last two words), so it holds for any font.
LAST_LINE = r"""(el=>{ const tw=document.createTreeWalker(el,NodeFilter.SHOW_TEXT), words=[];
  for(let n=tw.nextNode();n;n=tw.nextNode()){ const re=/\S+/g; let m; while((m=re.exec(n.textContent))){ const r=document.createRange(); r.setStart(n,m.index); r.setEnd(n,m.index+m[0].length); words.push(r.getBoundingClientRect().top); } }
  return words.length<2||Math.abs(words[words.length-1]-words[words.length-2])<2; })"""
BAD_DOTS = r"""(()=>[...document.querySelectorAll('.icchg')].map(e=>e.textContent.replace(/\s+/g,' ').trim()).filter(t=>/^·|·$|·\s*·/.test(t)))()"""


class WordingAndRepetition(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 900

    def one_word_last_lines(self, wrap):
        b = self.b
        b.eval("""(()=>{ const d=document.createElement('p'); d.id='lastline'; d.style.cssText='margin:0;position:absolute;left:0;top:0;width:300px;text-wrap:%s';
          d.textContent='alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike'; document.body.appendChild(d); })()""" % wrap)
        n = b.eval("""(()=>{ const d=document.getElementById('lastline'); let bad=0; for(let w=140;w<=420;w+=3){ d.style.width=w+'px'; if(!(%s)(d)) bad++; } d.remove(); return bad; })()""" % LAST_LINE)
        return n

    def test_paragraphs_do_not_leave_a_one_word_last_line(self):
        self.assertEqual(self.one_word_last_lines("inherit"), 0)
        self.assertGreater(self.one_word_last_lines("wrap"), 0)         # mutant: plain wrapping does leave some

    def test_review_meta_line_has_no_stray_or_doubled_dots(self):
        b = self.b
        for w in (1400, 900):
            b.resize(w, 900)
            b.eval("go('review')")
            b.pump(1)
            self.assertEqual(b.eval(BAD_DOTS), [], w)
        b.eval("document.body.insertAdjacentHTML('beforeend','<div class=icchg>Action · · Routine</div>')")
        self.assertTrue(b.eval(BAD_DOTS))        # mutant: a doubled dot is caught

    def test_cockpit_health_numbers_share_one_row_at_900(self):
        b = self.b
        for w in (1400, 900):
            b.resize(w, 900)
            b.eval("go('cockpit','ABC')")
            b.wait("document.querySelectorAll('#v-cockpit .evbox').length>=5")
            tops = b.eval("[...document.querySelectorAll('#v-cockpit .evrow .evbox')].map(e=>Math.round(e.getBoundingClientRect().top))")
            self.assertEqual(len(set(tops)), 1, (w, tops))

    def test_top_risks_are_apart_and_say_whose(self):
        b = self.b
        b.eval("go('cockpit','ABC')")
        b.wait("document.querySelector('.rkrow')")
        rows = b.eval("[...document.querySelectorAll('.rkrow')].map(r=>[!!r.querySelector('.rk-t'), (r.querySelector('.rk-o')||{}).textContent||'', getComputedStyle(r.querySelector('.rk-m'),'::after').content])")
        self.assertTrue(rows)
        for has_title, owner, dot in rows:
            self.assertTrue(has_title and owner.strip())
            self.assertIn("\u00b7", dot)

    def test_work_list_hides_empty_groups_and_says_overdue_once(self):
        b = self.b
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tr.wgh')")
        EMPTY = "[...document.querySelectorAll('#workTbl tr.wgh')].filter(h=>{const n=h.nextElementSibling;return !n||n.classList.contains('wgh')}).map(h=>h.textContent.trim())"
        self.assertEqual(b.eval(EMPTY), [])
        b.eval("document.querySelector('#workTbl tbody').insertAdjacentHTML('beforeend','<tr class=wgh data-gk=x><td>Empty group 0 actions</td></tr>')")
        self.assertTrue(b.eval(EMPTY))             # mutant: a header with no rows under it is caught
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tr.wgh')")
        heads = b.eval("[...document.querySelectorAll('#workTbl tr.wgh')].map(h=>h.textContent.replace(/\\s+/g,' ').trim())")
        for h in heads:
            self.assertLessEqual(h.lower().count("overdue"), 1, h)

    def test_display_menu_headings_do_not_skip_a_level(self):
        b = self.b
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl')")
        b.click("#dispBtn")
        b.wait("document.querySelector('#dispMenu h2')")
        self.assertEqual(b.eval("document.querySelectorAll('#dispMenu h3').length"), 0)
        self.assertGreaterEqual(b.eval("document.querySelectorAll('#dispMenu h2').length"), 3)


if __name__ == "__main__":
    unittest.main()
