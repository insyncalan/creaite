"""BL-122: click selects, the ID or a double-click opens, Cmd/Ctrl and Shift select several. A real browser against the real live
server, with real mouse and key events (Work table and board, a person's page; Review's rows went with the old Review page, #232 C2: the Intake page opens a row
in the peek with one click, test_peek_follow, and has no multi-select).

Run: python3 dev/tests/test_row_selection.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

CTRL, META, SHIFT = 2, 4, 8


class Selecting(LiveBrowserCase):
    width, height = 1500, 1000

    def open_work(self, tab="actions", layout="list"):
        b = self.b
        b.eval(f"WT={tab!r}; go('work')")
        b.wait("document.querySelector('#workTbl tr[data-row], #workBoard .bcard')")
        b.click(f'#wlay [data-lay="{layout}"]')
        b.eval("COLVIS[WT]=[...new Set([...COLVIS[WT],'src'])]; renderWork()")        # the Source column is not editable (BL-123), so a click there only highlights
        b.eval("document.activeElement&&document.activeElement.blur()")      # a focused button would take Space and Enter for itself
        b.pump(0.3)
        return b

    def ids(self):
        return self.b.eval("[...document.querySelectorAll('#workTbl tr[data-row]')].map(r=>r.dataset.row)")

    def cell(self, id_, f="src"):
        if f == "src":
            return f'#workTbl tr[data-row="{id_}"] td:last-child'
        return f'#workTbl tr[data-row="{id_}"] td[data-f="{f}"]'

    def hl(self):
        return self.b.eval("[...document.querySelectorAll('#workTbl tr.hl')].map(r=>r.dataset.row)")

    def panel_on(self):
        return self.b.eval("document.getElementById('panel').classList.contains('on')")

    def opened(self):
        """The sidebar is open and has finished sliding in (the table reflows while it does)."""
        self.b.wait("document.getElementById('panel').classList.contains('on')")
        self.b.pump(0.6)

    def open_id(self):
        return self.b.eval("CUR&&CUR.mode==='record'?CUR.id:null")

    # ── the rules ──

    def test_a_click_highlights_only_that_row_and_opens_nothing(self):
        b = self.open_work()
        a, c, _ = self.ids()
        b.click(self.cell(a))
        self.assertEqual(self.hl(), [a])
        self.assertFalse(self.panel_on())
        b.click(self.cell(c))
        self.assertEqual(self.hl(), [c])                                  # replaces the highlight
        self.assertFalse(self.panel_on())

    def test_the_id_opens_the_sidebar_and_a_double_click_anywhere_on_the_row_does_too(self):
        b = self.open_work()
        a, c, _ = self.ids()
        b.click(f'#workTbl tr[data-row="{a}"] a.rowid')
        self.opened()
        self.assertEqual(self.open_id(), a)
        self.assertEqual(self.hl(), [a])
        b.key("Escape")                                                   # #108: one Esc clears the highlight and closes the sidebar
        self.assertEqual(self.hl(), [])
        b.wait("!document.getElementById('panel').classList.contains('on')")
        b.click(self.cell(c))
        b.click(self.cell(c), count=2)                                    # a double-click on the source cell
        self.opened()
        self.assertEqual(self.open_id(), c)

    def test_the_highlight_is_not_the_open_record(self):
        b = self.open_work()
        a, c, _ = self.ids()
        b.click(f'#workTbl tr[data-row="{a}"] a.rowid')
        self.opened()
        b.click(f'#workTbl tr[data-row="{c}"] td.title')   # BL-176: the peek covers the list's right; the title is clear of it
        # BL-198 (sprint-review-work): with the peek open, a single click shows the clicked row in it
        b.wait(f"CUR&&CUR.id==={c!r}")
        self.assertEqual(self.hl(), [c])
        b.eval(f"hlOnly(WT,{a!r})")                                       # the highlight moved by the keys is still not the open record
        self.assertEqual(self.open_id(), c)
        self.assertEqual(b.eval("[...document.querySelectorAll('#workTbl tr.sel')].map(r=>r.dataset.row)"), [c])    # both marked, differently
        self.assertEqual(self.hl(), [a])

    def test_cmd_and_ctrl_toggle_and_shift_selects_a_range(self):
        b = self.open_work()
        a, c, d = self.ids()
        b.click(self.cell(a))
        b.click(self.cell(d), modifiers=META)                             # Cmd adds
        self.assertEqual(sorted(self.hl()), sorted([a, d]))
        b.eval(f"document.querySelector({self.cell(a)!r}).dispatchEvent(new MouseEvent('click',{{bubbles:true,ctrlKey:true}}))")   # Ctrl takes it off
        self.assertEqual(self.hl(), [d])                                  # (a real Ctrl-click is a context click on a Mac, so it is sent as an event)
        b.click(self.cell(a))
        b.click(self.cell(d), modifiers=SHIFT)                            # Shift: the range from the last row clicked
        self.assertEqual(sorted(self.hl()), sorted([a, c, d]))
        self.assertEqual(b.eval("window.getSelection().toString()"), "")  # and no text was selected by the drag
        b.click(self.cell(c))                                             # a plain click replaces it
        self.assertEqual(self.hl(), [c])
        b.click(self.cell(a))
        b.click(self.cell(d), modifiers=SHIFT | META)                     # Cmd with Shift adds the range
        b.click(self.cell(c), modifiers=META)
        self.assertEqual(sorted(self.hl()), sorted([a, d]))

    def test_two_or_more_highlighted_close_the_sidebar(self):
        b = self.open_work()
        a, c, _ = self.ids()
        b.click(f'#workTbl tr[data-row="{a}"] a.rowid')
        self.opened()
        b.click(f'#workTbl tr[data-row="{c}"] td.title', modifiers=META)   # BL-176: the title, clear of the peek
        self.assertEqual(sorted(self.hl()), sorted([a, c]))
        self.assertFalse(self.panel_on())

    def test_a_highlighted_row_has_more_than_colour_and_the_table_is_a_multi_select_grid(self):
        b = self.open_work()
        a, c, _ = self.ids()
        b.click(self.cell(a))
        b.click(self.cell(c), modifiers=META)
        self.assertEqual(b.eval(f"document.querySelector('#workTbl tr[data-row=\"{a}\"]').getAttribute('aria-selected')"), "true")
        self.assertEqual(b.eval("document.querySelector('#workTbl tr:not(.hl)[data-row]')?.getAttribute('aria-selected')||'false'"), "false")
        self.assertEqual(b.eval("[document.getElementById('workTbl').getAttribute('role'), document.getElementById('workTbl').getAttribute('aria-multiselectable')]"), ["grid", "true"])
        tick = b.eval(f"getComputedStyle(document.querySelector('#workTbl tr[data-row=\"{a}\"] td.title'),'::before').content")
        self.assertIn("✓", tick)                                          # a tick as well as a tint
        edge = b.eval(f"getComputedStyle(document.querySelector('#workTbl tr[data-row=\"{a}\"] td:first-child')).boxShadow")
        self.assertIn("inset", edge)                                      # and an edge bar

    def test_links_and_controls_in_a_row_do_their_own_job(self):
        b = self.open_work()
        # #241: the project name sits beside the title and is clipped away when the title fills the line, so use a row where it shows
        a = b.eval("[...document.querySelectorAll('#workTbl tr[data-row]')].find(tr=>{const r=tr.querySelector('.pcode.plink').getBoundingClientRect();"
                   "return !!document.elementFromPoint(r.left+r.width/2,r.top+r.height/2).closest('.plink')}).dataset.row")
        b.click(f'#workTbl tr[data-row="{a}"] .pcode.plink')              # the project link goes to the project, and highlights nothing
        b.wait("VIEW==='cockpit'")
        b.eval("go('work')")
        b.wait("document.querySelector('#workTbl tr[data-row]')")
        self.assertEqual(self.hl(), [])
        self.assertFalse(self.panel_on())

    def test_the_highlight_goes_on_a_tab_switch_and_stays_through_a_filter_for_rows_that_remain(self):
        b = self.open_work()
        a, c, _ = self.ids()
        b.click(self.cell(a))
        b.click(self.cell(c), modifiers=META)
        b.eval("WQ=''; renderWork()")                                     # a redraw with the same rows keeps it
        self.assertEqual(sorted(self.hl()), sorted([a, c]))
        b.eval("document.getElementById('workQ').value=" + repr(f"{a}") + "; WQ=document.getElementById('workQ').value; renderWork()")
        self.assertLessEqual(len(self.hl()), 1)                           # a row that left the view leaves the highlight
        b.click('#wtabs [data-t="raid"]')
        b.pump(0.3)
        self.assertEqual(b.eval("HL.size"), 0)

    # ── the keyboard ──

    def test_j_and_k_move_the_cursor_space_toggles_shift_extends_and_enter_opens(self):
        b = self.open_work()
        a, c, d = self.ids()
        b.key("j")
        self.assertEqual(self.hl(), [a])
        self.assertFalse(self.panel_on())                                 # J does not open the sidebar when it is closed
        b.key("j")
        self.assertEqual(self.hl(), [c])
        b.key(" ")                                                        # Space toggles the cursor row off...
        self.assertEqual(self.hl(), [])
        b.key(" ")                                                        # ...and on
        self.assertEqual(self.hl(), [c])
        b.key("J", modifiers=SHIFT)                                       # Shift with J extends
        self.assertEqual(sorted(self.hl()), sorted([c, d]))
        b.key("Escape")
        self.assertEqual(self.hl(), [])
        b.key("j")                                                        # Esc cleared the cursor too: J starts again from the top
        self.assertEqual(self.hl(), [a])
        b.key("Enter")                                                    # Enter opens it
        self.opened()
        self.assertEqual(self.open_id(), a)
        b.key("j")                                                        # with the sidebar open, it follows
        b.wait(f"CUR&&CUR.id=={c!r}")
        self.assertEqual(self.hl(), [c])                                  # and the highlight moves with it

    # ── the board ──

    def test_board_cards_follow_the_same_rules(self):
        b = self.open_work(layout="board")
        cards = b.eval("[...document.querySelectorAll('#workBoard .bcard')].map(c=>c.dataset.row)")
        a, c = cards[0], cards[1]
        sel = lambda id_: f'#workBoard .bcard[data-row="{id_}"]'  # noqa: E731
        b.click(sel(a) + " .bct")
        self.assertEqual(b.eval("[...document.querySelectorAll('#workBoard .bcard.hl')].map(c=>c.dataset.row)"), [a])
        self.assertFalse(self.panel_on())
        b.click(sel(c) + " .bct", modifiers=META)
        self.assertEqual(sorted(b.eval("[...document.querySelectorAll('#workBoard .bcard.hl')].map(c=>c.dataset.row)")), sorted([a, c]))
        b.click(sel(c) + " .bid")                                         # the ID opens
        self.opened()
        self.assertEqual(self.open_id(), c)
        self.assertIn("✓", b.eval(f"getComputedStyle(document.querySelector('{sel(c)} .bct'),'::before').content"))
        b.key("Escape")
        b.key("Escape")
        b.click(sel(a) + " .bct", count=2)                                # a double-click opens
        b.wait(f"CUR&&CUR.id==={a!r}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
