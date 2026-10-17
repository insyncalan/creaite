"""BL-286 parts A, B and E, and BL-287: the Prep popup and the Open icon beside a meeting's Prep.

A: 960 px, the header in the peek's pattern (the day line, the title, the project, series and invited chips), one toolbar (Open
prep page, then Draft agenda on the right), the facts line, the invite on one line of names, the lists in two columns (one at
320 px, with nothing scrolling sideways). B: Draft agenda is a menu (its own test is test_block_menu.py; the drafting itself is
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

    def test_at_320_px_one_column_and_nothing_scrolls_sideways(self):
        b = self.b
        b.resize(320, 800)
        self.open_popup()
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('#prepBody .prepgrid')).gridTemplateColumns.split(' ').length"), 1)
        self.assertTrue(b.eval(f"(()=>{{ const s=document.getElementById('prepScroll'); return s.scrollWidth<=s.clientWidth+1 && {DLG}.scrollWidth<={DLG}.clientWidth+1; }})()"))
        self.assertTrue(b.eval(f"{DLG}.getBoundingClientRect().right<=320"))

    def test_open_prep_page_goes_to_the_page_inside_creaite(self):
        b = self.open_popup()
        b.click("#prepDlg [data-prepview]")
        b.wait(f"!{DLG}.open")
        self.assertEqual(b.eval("decodeURIComponent(location.hash)"), f"#prep={b.eval('TODAY')}|09:00|ABC weekly")

    def test_140_the_band_has_no_prepare_pill_and_no_note_link(self):
        """#140: neither the Prepare / Prep pill, BL-287's icon nor the Note link is on the band any more."""
        b = self.b
        b.eval("go('today'); renderToday()")
        b.wait("document.querySelector('#dayMeets .dmti')")
        self.assertEqual(b.eval("document.querySelectorAll('#dayMeets .preplink, #dayMeets .prepgo, #dayMeets .prepmade, #dayMeets .mnote').length"), 0)

    def test_140_the_title_opens_a_popup_on_focus_with_prepare_then_the_agenda_actions(self):
        """#140: tabbing to a meeting's title opens the popup (Prepare); with a saved page it offers Open agenda, Prepare again and
        Open the file; Open agenda goes to the page inside creaite; Esc closes it and keeps focus on the title."""
        b = self.b
        b.call("Emulation.setFocusEmulationEnabled", enabled=True)
        b.eval("go('today'); renderToday()")
        b.wait("document.querySelector('#dayMeets .dmti')")
        self.assertEqual(b.eval("document.querySelector('#dayMeets .dmpop')"), None)               # closed until pointed at or focused
        b.eval("document.querySelector('#dayMeets .dmti').focus()")
        b.wait("document.querySelector('#dayMeets .dmpop')")
        o = b.eval("""(()=>{ const t=document.querySelector('#dayMeets .dmti'), p=document.querySelector('#dayMeets .dmpop');
          return {role:p.getAttribute('role'), exp:t.getAttribute('aria-expanded'), haspopup:t.getAttribute('aria-haspopup'), head:p.querySelector('h4').textContent,
            meta:p.querySelector('.pm').textContent, btns:[...p.querySelectorAll('button')].map(x=>x.textContent), primary:p.querySelector('.btn.primary').textContent,
            w:Math.round(p.getBoundingClientRect().width), internal:/Internal/.test(p.textContent)}; })()""")
        self.assertEqual((o["role"], o["exp"], o["haspopup"], o["head"]), ("dialog", "true", "dialog", "ABC weekly"))
        self.assertEqual(o["btns"], ["Prepare"])
        self.assertEqual(o["primary"], "Prepare")
        self.assertTrue(o["internal"])
        self.assertLessEqual(o["w"], 330)
        b.key("Escape")
        b.wait("!document.querySelector('#dayMeets .dmpop')")
        self.assertTrue(b.eval("document.activeElement.classList.contains('dmti')"))                # no trap, focus stays on the title
        b.eval("SA().prep_pages={'09:00|ABC weekly':`projects/ABC Example Programme/agendas/${TODAY} Prep - ABC weekly.html`}; renderToday(); document.activeElement.blur(); document.querySelector('#dayMeets .dmti').focus()")
        b.wait("document.querySelector('#dayMeets .dmpop .agsaved')")
        got = b.eval("[...document.querySelectorAll('#dayMeets .dmpop button')].map(x=>x.textContent)")
        self.assertEqual(got, ["Open agenda", "Prepare again", "Open the file"])
        self.assertIn("Agenda saved", b.eval("document.querySelector('#dayMeets .dmpop .agsaved').textContent"))
        b.click("#dayMeets .dmpop [data-prepgo]")
        b.wait("location.hash.startsWith('#prep=')")
        self.assertFalse(b.eval(f"!!{DLG} && {DLG}.open"))                                           # the old popup never opened

    def test_140_the_popup_opens_on_hover_after_a_rest_not_at_once(self):
        b = self.b
        b.eval("go('today'); renderToday()")
        b.wait("document.querySelector('#dayMeets .dmti')")
        r = b.eval("(()=>{ const e=document.querySelector('#dayMeets .dmti').getBoundingClientRect(); return [e.left+e.width/2, e.top+e.height/2]; })()")
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=r[0], y=r[1])
        b.pump(0.2)
        self.assertFalse(b.eval("!!document.querySelector('#dayMeets .dmpop')"))                   # no hover popup is instant
        b.wait("document.querySelector('#dayMeets .dmpop')")
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=5, y=5)
        b.wait("!document.querySelector('#dayMeets .dmpop')")


if __name__ == "__main__":
    unittest.main()
