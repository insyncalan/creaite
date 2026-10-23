"""#302 piece C, the Minutes editor's keyboard, in a real browser on the real live server (no Claude runs; fictional demo data).

- J and K move from row to row (the rows shown); nothing is taken until one has chosen a row, so E and S stay page keys.
- Y, M and N set Tracked, Minutes only and Dropped on that row; the bar's counts and the Approve label follow; Z undoes the last key choice.
- E puts the cursor in the row's words; S lights the row's turn in the transcript.
- Never while typing in a field, and never with a modifier held.
- Nothing on screen advertises the keys (no bar, no hint).

Run: python3 dev/tests/test_minutes_keys_302c.py      (Chrome tier; skipped without Chrome)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_minutes_view_v2 as v2  # noqa: E402

ROW = v2.ROW


class MinutesKeys302C(v2.MinutesViewV2):
    def setUp(self):
        super().setUp()
        self.ev("document.activeElement && document.activeElement.blur()")   # a field left focused would be 'typing'

    def press(self, key, **mods):
        flags = ",".join(f"{k}:true" for k in mods)
        self.ev("(document.activeElement||document.body).dispatchEvent(new KeyboardEvent('keydown',{key:%r,bubbles:true,cancelable:true,%s}))" % (key, flags))
        self.b.pump(0.25)

    def cursor(self):
        return self.ev("(document.querySelector('#v-minutes tr.mi.kc')||{dataset:{}}).dataset.n||null")

    def shown(self):
        return self.ev("[...document.querySelectorAll('#v-minutes tr.mi:not([hidden])')].map(r=>r.dataset.n)")

    def test_c01_j_and_k_move_and_nothing_is_taken_before_a_row_is_chosen(self):
        self.assertIsNone(self.cursor())
        before = self.trk()
        self.press("y")
        self.press("m")
        self.assertEqual(self.trk(), before, "no row chosen: Y and M do nothing (N stays the note key)")
        rows = self.shown()
        self.press("j")
        self.assertEqual(self.cursor(), rows[0])
        self.press("j")
        self.assertEqual(self.cursor(), rows[1])
        self.press("k")
        self.assertEqual(self.cursor(), rows[0])
        self.press("k")
        self.assertEqual(self.cursor(), rows[0], "stops at the first row")

    def test_c02_y_m_n_set_the_track_and_z_undoes(self):
        self.press("j")
        n = self.cursor()
        self.press("n")
        self.assertEqual(self.trk()[n], "n")
        self.assertEqual(self.ev(f"document.querySelector(\"{ROW % int(n)} .mntrw\").textContent"), "Dropped")
        self.press("m")
        self.assertEqual(self.trk()[n], "")
        self.press("y")
        self.assertEqual(self.trk()[n], "y")
        self.press("z")                                                           # back to Minutes only
        self.assertEqual(self.trk()[n], "")
        self.press("z")                                                           # back to Dropped
        self.assertEqual(self.trk()[n], "n")
        self.press("z")                                                           # back to what it was before any key
        self.assertNotEqual(self.trk().get(n), "n")

    def test_c03_s_lights_the_turn_and_e_edits(self):
        self.press("j")
        for _ in range(8):
            if self.ev(f"!!document.querySelector(\"{ROW % int(self.cursor())} button.mnsrc\")"):
                break
            self.press("j")
        n = int(self.cursor())
        turn = self.ev(f"document.querySelector(\"{ROW % n} button.mnsrc\").dataset.turn")
        self.press("s")
        self.b.pump(0.3)
        self.assertEqual(self.ev("[...document.querySelectorAll('.mnturns li.on')].map(l=>l.dataset.turn)"), [turn])
        has_box = self.ev(f"!!document.querySelector(\"{ROW % n} .mnit [contenteditable='true']\")")
        self.press("e")
        if has_box:
            self.assertTrue(self.ev(f"!!document.activeElement.closest(\"{ROW % n} .mnit\")"), "the cursor is in the row's words")

    def test_c04_never_while_typing_or_with_a_modifier(self):
        self.press("j")
        n = self.cursor()
        was = self.trk()
        self.ev("document.querySelector('.mnpane-q input').focus()")
        self.press("n")
        self.press("j")
        self.assertEqual(self.trk(), was, "typing in a field: Y M N are not taken")
        self.assertEqual(self.cursor(), n)
        self.ev("document.activeElement.blur()")
        self.press("n", metaKey=True)
        self.press("n", ctrlKey=True)
        self.press("N", shiftKey=True)
        self.assertEqual(self.trk(), was, "with a modifier held")

    def test_c05_nothing_advertises_the_keys(self):
        self.assertEqual(self.ev("document.querySelectorAll('#v-minutes [data-key], #v-minutes .kbd, #v-minutes kbd').length"), 0)
        self.assertNotRegex(self.ev("document.getElementById('v-minutes').innerText"), r"(?i)press j|keyboard shortcut|review mode")


for _n in [n for n in dir(v2.MinutesViewV2) if n.startswith('test_')]:    # only this file's tests, not the ones it builds on
    setattr(MinutesKeys302C, _n, None)


if __name__ == "__main__":
    unittest.main()
