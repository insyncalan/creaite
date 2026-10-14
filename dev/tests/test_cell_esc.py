"""BL-178 (sprint-milestones): one Esc leaves Work's cell editor in every browser. The cell's list is shown in the page (a listbox,
never the platform's native list from showPicker), so the page gets every key on Windows, Linux and macOS alike.

Unlike test_cell_edit, nothing here switches showPicker off: these are the real keys on the real list, so the test means the same
on GitHub's Linux runner (where a native list would take the first Esc) as on a Mac.

Run: python3 dev/tests/test_cell_esc.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402


class OneEsc(LiveBrowserCase):
    width, height = 1500, 1000

    def setUp(self):
        super().setUp()
        b = self.b
        b.eval("window.PICKED=0; const sp=HTMLSelectElement.prototype.showPicker; HTMLSelectElement.prototype.showPicker=function(){ PICKED++; return sp&&sp.call(this); }")
        b.eval("S.autoApply=true; WT='actions'; go('work')")
        b.wait("document.querySelector('#workTbl tr[data-row]')")
        b.click('#wlay [data-lay="list"]')
        b.eval("document.activeElement&&document.activeElement.blur()")
        b.pump(0.3)

    def cell(self, id_, f):
        return f'#workTbl tr[data-row="{id_}"] td[data-f="{f}"]'

    def open_cell(self, id_, f):
        b = self.b
        b.click(self.cell(id_, f))
        b.wait(f"document.activeElement===document.querySelector('{self.cell(id_, f)} select')")
        return f"document.querySelector('{self.cell(id_, f)} select')"

    def editing(self):
        return self.b.eval("document.querySelectorAll('#workTbl td.editing').length")

    def row(self, id_):
        return next(r for r in self.v.rows("actions") if r["id"] == id_)

    def test_the_list_is_in_the_page_and_one_escape_closes_it(self):
        b = self.b
        sel = self.open_cell("ABC-A-002", "pr")
        self.assertGreater(b.eval(f"{sel}.size"), 1)                       # a listbox in the page, not a native popup
        self.assertEqual(b.eval("PICKED"), 0)                               # showPicker is never called
        box = b.eval(f"(()=>{{ const r={sel}.getBoundingClientRect(); return [r.top>=0, r.bottom<=innerHeight, r.height>40]; }})()")
        self.assertEqual(box, [True, True, True])
        b.key("Escape")                                                      # one Esc
        b.wait("document.querySelectorAll('#workTbl td.editing').length===0", 5)
        self.assertEqual(b.eval("document.activeElement.className"), "cebtn")
        self.assertEqual(self.row("ABC-A-002")["priority"], b.eval("REC('actions','ABC-A-002').pr"))

    def test_arrows_move_without_saving_and_enter_saves(self):
        b = self.b
        before = self.row("ABC-A-002")["priority"]
        sel = self.open_cell("ABC-A-002", "pr")
        b.key("ArrowDown")
        b.pump(0.4)
        self.assertEqual(self.editing(), 1)                                 # still open: nothing saved by the arrow
        chosen = b.eval(f"{sel}.value")
        self.assertNotEqual(chosen, before)
        self.assertEqual(self.row("ABC-A-002")["priority"], before)
        b.eval("document.getElementById('snackT').textContent=''")
        b.key("Enter")
        b.wait("document.getElementById('snackT').textContent!==''", 30)
        b.wait("document.querySelectorAll('#workTbl td.editing').length===0", 5)
        self.assertEqual(self.row("ABC-A-002")["priority"], chosen)

    def test_tab_goes_on_to_the_next_cell_with_one_press(self):
        b = self.b
        self.open_cell("ABC-A-002", "pr")
        b.key("Tab")
        b.wait("document.querySelectorAll('#workTbl td.editing').length===0", 5)
        self.assertEqual(b.eval("document.activeElement.className"), "cebtn")

    def test_a_click_on_an_option_saves_and_on_the_chosen_one_closes(self):
        b = self.b
        sel = self.open_cell("ABC-A-002", "pr")
        cur = b.eval(f"{sel}.value")
        b.click(f"{self.cell('ABC-A-002', 'pr')} select option[value=\"{cur}\"]")
        b.wait("document.querySelectorAll('#workTbl td.editing').length===0", 5)
        self.assertEqual(self.row("ABC-A-002")["priority"], cur)
        sel = self.open_cell("ABC-A-002", "pr")
        other = b.eval(f"[...{sel}.options].map(o=>o.value).find(v=>v!=={cur!r})")
        b.eval("document.getElementById('snackT').textContent=''")
        b.click(f"{self.cell('ABC-A-002', 'pr')} select option[value=\"{other}\"]")
        b.wait("document.getElementById('snackT').textContent!==''", 30)
        self.assertEqual(self.row("ABC-A-002")["priority"], other)
        self.assertEqual(b.errors, [])


if __name__ == "__main__":
    unittest.main()
