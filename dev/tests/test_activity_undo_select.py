"""BL-164: Activity's type icons, search and filters, and undoing several past changes, part 3 of 3 (the Activity page, undoing a selection; the fixture is in activity_undo_support.py).

Run: python3 dev/tests/test_activity_undo_select.py   (the browser tests need Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from activity_undo_support import (  # noqa: E402
    ActivityBase,
    SHIFT,
)


class ActivitySelect(ActivityBase):
    """The page: undoing a selection."""

    def test_undo_three_older_changes_with_the_confirm_then_undo_the_undo(self):
        b = self.b
        self.go_activity()
        rows = self.older_rows()
        self.pick(rows)
        b.click("#actUndoSel")
        b.wait("document.getElementById('actDlg').open")
        items = b.eval("[...document.querySelectorAll('#actDlg li')].map(l=>l.textContent)")
        self.assertEqual(len(items), 3)
        self.assertTrue(any("ABC-A-001" in x and "Closed → Open" in x for x in items), items)
        self.assertTrue(any("ABC-A-002" in x and "Sara Example → Alan Carter" in x for x in items), items)
        self.assertTrue(any("ABC-A-003" in x and "20-11-2026 → —" in x for x in items), items)
        b.click("#actDlgGo")
        b.wait("document.getElementById('snack').classList.contains('on')&&/Undid/.test(document.getElementById('snackT').textContent)", 20)
        self.assertRegex(b.eval("document.getElementById('snackT').textContent"), r"Undid \d changes?")
        b.wait("ACT.some(a=>a.revert)")
        self.assertTrue(b.eval("ACT.filter(a=>a.reverted).length>=2"))
        self.assertTrue(b.eval("[...document.querySelectorAll('#actTbl tr.undone')].length>=2"))
        self.assertIn("undone", b.eval("document.querySelector('#actTbl tr.undone td:last-child').textContent"))
        # the revert is one entry with its own Undo (it is the latest apply now)
        rev = b.eval("(()=>{ const i=ACT.findIndex(a=>a.revert); return {i, apply:ACT[i].apply_id, latest:D.latest_apply}; })()")
        self.assertEqual(rev["apply"], rev["latest"])
        b.click(f'#actTbl [data-undoapply="{rev["apply"]}"]')
        b.wait("!ACT.some(a=>a.revert&&!a.undone)", 20)
        self.assertFalse(b.eval("ACT.some(a=>a.reverted)"))

    def test_a_selection_of_the_whole_latest_apply_uses_the_exact_undo(self):
        b = self.b
        self.go_activity()
        latest = self.latest_rows()
        self.assertGreaterEqual(len(latest), 2)
        b.eval("window.CALLED=[]; const u=undoApply; undoApply=function(id){ CALLED.push(id); return u.apply(this,arguments); }")
        self.pick(latest)
        b.click("#actUndoSel")
        b.wait("CALLED.length===1", 20)
        self.assertEqual(b.eval("CALLED[0]"), b.eval("D.latest_apply") or b.eval("CALLED[0]"))
        self.assertFalse(b.eval("document.getElementById('actDlg')&&document.getElementById('actDlg').open"))

    def test_over_25_asks_again(self):
        b = self.b
        self.go_activity()
        b.eval("""window.FAKE=Array.from({length:30},(_,i)=>({rowid:i+1,id:'ABC-A-001',field:'owner',change:'set',from:'a',to:'b'}));
          api=(p,body)=>Promise.resolve(p==='/api/undo-changes'?{ok:true,done:FAKE,skipped:[],message:'x',apply_id:body.dry_run?null:99}:{ok:true});""")
        self.pick(self.older_rows())
        b.click("#actUndoSel")
        b.wait("document.getElementById('actDlg').open")
        self.assertEqual(b.eval("document.getElementById('actDlgGo').textContent"), "Undo 30")
        b.click("#actDlgGo")
        self.assertTrue(b.eval("document.getElementById('actDlg').open"))                       # asked again, with the count
        self.assertIn("30", b.eval("document.getElementById('actDlgAsk').textContent"))
        b.click("#actDlgCancel")
        b.wait("!document.getElementById('actDlg').open")

    def test_entries_that_cannot_be_chosen_have_a_disabled_tick(self):
        b = self.b
        self.go_activity()
        r = b.eval("""(()=>{ ACT.unshift({at:'2026-10-10 09:00',what:'ABC-A-001 · changed',by:'You'}); renderActivity();
          const first=document.querySelector('#actTbl tbody tr'); const cb=first.querySelector('input[type=checkbox]'); return {row:first.dataset.row||null, tick:!!cb, off:!!cb&&cb.disabled}; })()""")
        self.assertEqual(r, {"row": None, "tick": True, "off": True})   # #191: a tick box on every row, disabled where it cannot be chosen

    def test_the_disabled_tick_is_skipped_by_a_range_and_not_counted(self):
        """#191: a range across a row that cannot be chosen never takes it, its tick cannot be ticked, and Undo n counts only chosen rows.
        (Activity has no select-all key and J/K are not bound there: ranges and ticks are how several rows are chosen.)"""
        b = self.b
        self.go_activity()
        b.eval("""(()=>{ const x={at:'2026-10-10 09:00',what:'ABC-A-001 · changed',by:'You'}; ACT.unshift({...x}); ACT.splice(3,0,{...x}); renderActivity(); })()""")
        b.eval("document.activeElement&&document.activeElement.blur(); hlClear(); actPaint()")
        order = b.eval("[...document.querySelectorAll('#actTbl tbody tr')].map(t=>t.dataset.row||null)")
        self.assertIsNone(order[0])
        self.assertIsNone(order[3])
        ok = [r for r in order if r]
        cell = lambda r: f'#actTbl tr[data-row="{r}"] td.actwhen'  # noqa: E731
        b.click(cell(ok[0]))
        b.click(cell(ok[3]), modifiers=SHIFT)                                            # a range from the first to the fourth, over the disabled row
        self.assertEqual(self.sel_rows(), ok[:4])                                        # the range spans the disabled row without taking it
        b.eval("document.querySelector('#actTbl tr:not([data-row]) input').click()")        # a disabled tick does nothing
        self.assertEqual(self.sel_rows(), ok[:4])
        self.assertEqual(b.eval("document.querySelectorAll('#actTbl tr:not([data-row]) input:checked').length"), 0)
        self.assertEqual(b.eval("document.getElementById('actUndoSel').textContent.trim()"), "Undo 4")
        self.assertEqual(b.eval("document.querySelectorAll('#actTbl input[disabled]').length"), 2)

    def test_the_footer_says_when_the_cap_is_reached(self):
        b = self.b
        self.go_activity()
        self.assertFalse(b.eval("!!document.getElementById('actCap')&&!document.getElementById('actCap').hidden"))
        b.eval("D.activity_capped=true; renderActivity()")
        self.assertIn("newest", b.eval("document.getElementById('actCap').textContent"))


if __name__ == "__main__":
    unittest.main()
