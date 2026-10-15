"""BL-286 parts A, B and E, and BL-287: the Prep popup and the Open icon beside a meeting's Prep.

A: 960 px, the header in the peek's pattern (the day line, the title, the project, series and invited chips), one toolbar (Open
prep page, then Draft agenda on the right), the facts line, the invite on one line of names, the lists in two columns. B: Draft agenda is a menu (its own test is test_block_menu.py; the drafting itself is
test_drafts_agenda.py). E: every item opens the full Work peek over the popup, ↑ ↓ step through the popup's items, Esc brings
the popup back with focus on the item, and the popup shows a changed item. BL-287: the Open icon and "Prep page made" when a
prep page exists, opening #prep=<key>; none without a page.

Run: python3 dev/tests/test_prep_popup.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_decisions_prep import prep_world  # noqa: E402

DLG = "document.getElementById('prepDlg')"


class PrepPopup(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        prep_world(v)

    def open_popup(self):
        b = self.b
        b.eval("go('today'); renderToday(); openPrep(prepTimed()[0],TODAY)")
        b.wait(f"{DLG}.open && document.querySelector('#prepBody .prepsec')")
        return b

    def test_the_header_toolbar_facts_and_two_columns(self):
        b = self.open_popup()
        self.assertEqual(b.eval(f"Math.round({DLG}.getBoundingClientRect().width)"), 960)
        self.assertTrue(b.eval("document.getElementById('prepWhen').textContent").startswith("Today · "))
        self.assertIn("09:00 – 10:00 · Teams", b.eval("document.getElementById('prepWhen').textContent"))
        self.assertEqual(b.eval("document.getElementById('prepTitle').textContent"), "ABC weekly")
        chip = b.eval("(()=>{ const c=document.getElementById('prepProjBtn'); return [c.dataset.code, c.textContent, c.getAttribute('aria-haspopup')]; })()")
        self.assertEqual(chip[0], "ABC")
        self.assertNotIn("ABC", chip[1])                                           # by name (BL-101)
        self.assertEqual(chip[2], "listbox")
        b.wait("document.getElementById('prepInvited')")
        self.assertIn("Sara Example", b.eval("document.getElementById('prepInvited').getAttribute('aria-label')"))
        tools = b.eval("[...document.querySelectorAll('.preptb button')].map(x=>x.textContent.trim())")
        self.assertEqual(tools[:3], ["Shape this meeting", "Open prep page", "Draft agenda"])   # BL-286 C registers Shape
        self.assertEqual(b.eval("document.querySelectorAll('.preptb').length"), 1)
        self.assertEqual(b.eval("document.querySelectorAll('#prepDlg [data-agstyle]').length"), 0)   # no POAD / Lighter chips
        facts = b.eval("document.getElementById('prepFacts').textContent")
        self.assertRegex(facts, r"^(Since the last meeting \(\d\d-\d\d-\d{4}\)|No earlier meeting on record; since \d\d-\d\d-\d{4}): ")
        inv = b.eval("document.querySelector('#prepDlg details.prepinv summary').textContent")
        self.assertIn("Invite: organised by", inv)
        self.assertIn("Sara Example", inv)
        self.assertFalse(b.eval("document.querySelector('#prepDlg details.prepinv').open"))   # collapsed
        cols = b.eval("getComputedStyle(document.querySelector('#prepBody .prepgrid')).gridTemplateColumns.split(' ').length")
        self.assertEqual(cols, 2)
        self.assertTrue(b.eval("!!document.querySelector('#prepBody .idc')"))      # each line shows its ID
        self.assertEqual(b.errors, [])

    def test_the_project_chip_opens_the_picker_inside_the_popup(self):
        b = self.open_popup()
        b.click("#prepProjBtn")
        b.wait("document.querySelector('#prepDlg .pkpop')")
        opts = b.eval("[...document.querySelectorAll('#prepDlg .pkpop .pkopt')].map(o=>o.textContent)")
        self.assertIn("Portfolio (all projects)", opts)
        b.key("Escape")
        b.wait("!document.querySelector('.pkpop')")
        self.assertTrue(b.eval(f"{DLG}.open"))                                      # Esc closed the picker, not the popup

    def test_an_item_opens_the_full_peek_over_the_popup_and_esc_brings_it_back(self):
        b = self.open_popup()
        first = b.eval("document.querySelector('#prepBody [data-open^=\"actions:\"]').dataset.open")
        b.click(f"#prepBody [data-open='{first}']")
        b.wait("document.getElementById('panel').classList.contains('on') && document.getElementById('panel').classList.contains('peek')")
        self.assertEqual(b.eval("CUR.id"), first.split(":")[1])
        self.assertTrue(b.eval(f"{DLG}.open && !{DLG}.matches(':modal')"))          # still shown, under the peek
        self.assertTrue(b.eval("(()=>{ const r=document.getElementById('pkTitle').getBoundingClientRect(); const e=document.elementFromPoint(r.left+5,r.top+5); return !!e.closest('#panel'); })()"))
        n = b.eval("prepPeekList().length")
        if n > 1:
            b.click("#pkNext")
            b.wait(f"CUR && CUR.id!=={first.split(':')[1]!r}")
            self.assertEqual(b.eval("document.querySelector('#prepBody .sel').dataset.open.split(':')[1]"), b.eval("CUR.id"))
        cur = b.eval("CUR.id")
        b.eval("document.body.focus()")
        b.key("Escape")
        b.wait(f"!document.getElementById('panel').classList.contains('on') && {DLG}.matches(':modal')")
        self.assertEqual(b.eval("document.activeElement.dataset.open.split(':')[1]"), cur)
        self.assertFalse(b.eval("!!document.getElementById('prepScrim')"))
        b.key("Escape")
        b.wait(f"!{DLG}.open")

    def test_a_changed_item_shows_in_the_popup(self):
        b = self.open_popup()
        first = b.eval("document.querySelector('#prepBody [data-open^=\"actions:\"]').dataset.open")
        b.eval(f"A.find(x=>x.id==={first.split(':')[1]!r}).t='Retitled in the peek'; refreshAll()")
        b.wait("document.getElementById('prepBody').textContent.includes('Retitled in the peek')")

    def test_open_prep_page_goes_to_the_page_inside_creaite(self):
        b = self.open_popup()
        b.click("#prepDlg [data-prepview]")
        b.wait(f"!{DLG}.open")
        self.assertEqual(b.eval("decodeURIComponent(location.hash)"), f"#prep={b.eval('TODAY')}|09:00|ABC weekly")

    def test_bl287_the_open_icon_only_with_a_page(self):
        b = self.b
        b.eval("go('today'); renderToday()")
        b.wait("document.querySelector('#dayMeets .preplink')")
        self.assertEqual(b.eval("document.querySelectorAll('#dayMeets .prepgo').length"), 0)       # no page, no icon
        b.eval("SA().prep_pages={'09:00|ABC weekly':`projects/ABC Example Programme/agendas/${TODAY} Prep - ABC weekly.html`}; renderToday()")
        b.wait("document.querySelector('#dayMeets .prepgo')")
        got = b.eval("(()=>{ const g=document.querySelector('#dayMeets .prepgo'); return [g.tagName, g.getAttribute('aria-label'), g.dataset.tip, "
                     "g.closest('.prepline').querySelector('.prepmade').textContent, !!g.closest('.preplink'), Math.round(g.getBoundingClientRect().width)]; })()")
        self.assertEqual(got[0], "BUTTON")
        self.assertEqual(got[1], "Open the prep page for ABC weekly")
        self.assertTrue(got[2].startswith("Prep page saved "), got[2])
        self.assertEqual(got[3], "Prep page made")
        self.assertFalse(got[4])                                                     # its own control, not inside Prep
        self.assertGreaterEqual(got[5], 24)                                          # BL-216
        b.click("#dayMeets .prepgo")
        b.wait("location.hash.startsWith('#prep=')")
        self.assertFalse(b.eval(f"!!{DLG} && {DLG}.open"))                           # the popup never opened


if __name__ == "__main__":
    unittest.main()
