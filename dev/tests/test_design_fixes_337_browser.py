"""#337 (design fixes from the design trial): Client view with no client-visible milestone says so instead of "0 achieved, 0 to
come." (the page and the cockpit's card); the cockpit's edit pencils are readable (opacity .8); Settings tick groups keep a
readable label at 900 px; People fits its box at 900 px (Overdue on screen); Activity's By column does not wrap.

Run: python3 dev/tests/test_design_fixes_337_browser.py   (needs Google Chrome; skipped otherwise). Desktop and 900 px only.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

NONE = "None of the "
TAIL = " shown to the client yet. Switch to Internal view to see "


class DesignFixes(LiveBrowserCase):
    shared_server = True
    width, height = 900, 900

    def test_client_view_with_no_client_milestone_says_so(self):
        b = self.b
        b.eval("MVAUD='cli'; try{ localStorage.setItem('creaite.cockpit.milestones.view','cli'); }catch(e){}")
        b.eval("mvOpenPage('ABC','plan')")
        b.wait("VIEW==='milestones'&&document.querySelector('#v-milestones .mv-card')")
        txt = b.eval("(document.querySelector('#v-milestones .mv-none')||{}).textContent||''")
        self.assertTrue(txt.startswith(NONE) and TAIL in txt, txt)
        self.assertFalse(b.eval("!!document.querySelector('#v-milestones .mv-answer')"))
        self.assertNotIn("0 achieved", b.eval("document.querySelector('#v-milestones').textContent"))
        b.eval("go('cockpit','ABC')")
        b.wait("document.getElementById('mvCard')")
        card = b.eval("(document.querySelector('#mvCard .mv-none')||{}).textContent||''")
        self.assertTrue(card.startswith(txt), card)      # the card also offers Add milestone
        self.assertTrue(b.eval("!!document.querySelector('#mvCard .mv-none [data-mvadd]')"))
        # Internal view still draws the plan
        b.eval("MVAUD='int'; go('cockpit','ABC')")
        b.wait("document.getElementById('mvCard')")
        self.assertFalse(b.eval("!!document.querySelector('#mvCard .mv-none')"))

    def test_the_message_says_not_shown_for_one_milestone_and_for_many(self):        # PM: the singular dropped its "not"
        b = self.b
        self.assertEqual(b.eval("mvNoneText(1)"), "The milestone is not shown to the client yet. Switch to Internal view to see it.")
        self.assertEqual(b.eval("mvNoneText(2)"), "None of the 2 milestones are shown to the client yet. Switch to Internal view to see them.")
        self.assertEqual(b.eval("mvNoneText(7)"), "None of the 7 milestones are shown to the client yet. Switch to Internal view to see them.")

    def test_pencil_contrast(self):
        b = self.b
        b.eval("go('cockpit','ABC')")
        b.wait("document.querySelector('.card.edt .pencil')")
        self.assertGreaterEqual(float(b.eval("getComputedStyle(document.querySelector('.card.edt .pencil')).opacity")), 0.8)

    def test_targets_and_chart_text(self):
        b = self.b
        b.eval("go('cockpit','ABC')")
        b.wait("document.querySelector('.card.edt .pencil')")
        small = b.eval("[...document.querySelectorAll('.card.edt .pencil')].filter(e=>e.getBoundingClientRect().width).map(e=>e.getBoundingClientRect()).filter(r=>r.width<24||r.height<24).length")
        self.assertEqual(small, 0)
        sizes = b.eval("[...document.querySelectorAll('svg text')].filter(e=>e.getBoundingClientRect().width).map(e=>parseFloat(getComputedStyle(e).fontSize))")
        self.assertTrue(sizes and min(sizes) >= 12, sizes)
        b.eval("go('people')")
        b.wait("document.querySelector('#peopleTbl a.cntl')")
        self.assertEqual(b.eval("[...document.querySelectorAll('#peopleTbl a.cntl')].filter(e=>e.getBoundingClientRect().width<24||e.getBoundingClientRect().height<24).length"), 0)

    def test_settings_tick_labels_keep_room(self):
        b = self.b
        b.eval("go('settings')")
        b.wait("document.querySelector('.setticks')")
        w = b.eval("[...document.querySelectorAll('.setticks')].map(t=>t.closest('.srow').firstElementChild.getBoundingClientRect().width)")
        self.assertTrue(w and min(w) >= 200, w)

    def test_people_fits_and_overdue_is_on_screen(self):
        b = self.b
        b.eval("go('people')")
        b.wait("document.querySelector('#peopleTbl table')")
        tw, cw, over = b.eval("(()=>{const c=document.querySelector('#peopleTbl'),t=c.querySelector('table'),h=[...t.querySelectorAll('th')].find(x=>x.textContent.includes('Overdue'));return [t.scrollWidth,c.clientWidth,h.getBoundingClientRect().right-c.getBoundingClientRect().left]})()")
        # Intent, measured against the page's own box (the 2.6.4 gate: a wider font, as on Linux, makes the cells wrap more or the
        # table a few per cent wider than here): the sort column is on screen and the table is not meaningfully wider than its box
        # (the wide-table cue covers a small remainder). Before #337 the table was ~1.4x its box with Overdue off screen.
        self.assertLessEqual(over, cw)
        self.assertLessEqual(tw, cw * 1.08, (tw, cw))

    def test_activity_by_column_does_not_wrap(self):
        b = self.b
        b.eval("go('activity')")
        b.wait("document.querySelector('#actTbl tr[data-row]')")
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('#actTbl tbody tr td:nth-child(4)')).whiteSpace"), "nowrap")
        # the By cell's own text is on one line (other columns may wrap with a wider font and make the row taller)
        lines = b.eval("""[...document.querySelectorAll('#actTbl tbody tr')].slice(0,6).map(r=>{const td=r.children[3],rg=document.createRange();
          rg.selectNodeContents(td); const cs=getComputedStyle(td), lh=parseFloat(cs.lineHeight)||parseFloat(cs.fontSize)*1.4;
          return rg.getBoundingClientRect().height/lh;})""")
        self.assertTrue(lines and max(lines) < 1.5, lines)


class DesignFixesWide(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 900

    def test_people_and_settings_do_not_overflow(self):
        b = self.b
        b.eval("go('people')")
        b.wait("document.querySelector('#peopleTbl table')")
        self.assertTrue(b.eval("(()=>{const c=document.querySelector('#peopleTbl');return c.querySelector('table').scrollWidth<=c.clientWidth+1})()"))
        b.eval("go('settings')")
        b.wait("document.querySelector('.setticks')")
        self.assertGreaterEqual(b.eval("Math.min(...[...document.querySelectorAll('.setticks')].map(t=>t.closest('.srow').firstElementChild.getBoundingClientRect().width))"), 200)


if __name__ == "__main__":
    unittest.main()
