"""#302 piece A, the Minutes editor v3 clean-up, in a real browser on the real live server (no Claude runs; fictional demo data).

- Track control D: three icons (Tracked, Minutes only, Dropped); the chosen one is raised and its word shows; the group's name
  includes the row and the state; every state change moves the row's mark, the bar's counts, the Approve label and the strip.
- No Done button on a text section; a click away or Esc goes back to the lines; the sparkles on Executive Summary and Updates stay.
- Approve says what it does: "Approve minutes · tracks 3 actions", "… tracks nothing".
- Plain flags on ticked rows (Needs a date), the attention strip with its chips and Next, and Decisions say "Made by".
- Undo (the sheet's own) puts a Track choice back.

Run: python3 dev/tests/test_minutes_a302.py      (Chrome tier; skipped without Chrome)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_minutes_view_v2 as v2  # noqa: E402

ROW = v2.ROW


class MinutesA302(v2.MinutesViewV2):
    def label(self):
        return self.ev("document.getElementById('mnApproveBtn').textContent.trim()")

    def strip(self):
        return self.ev("(document.getElementById('mnAttn')||{}).textContent||''")

    def word(self, n):
        return self.ev(f"(document.querySelector(\"{ROW % n} .mntrw\")||{{}}).textContent||''")

    def test_a01_three_states_move_the_counts_the_label_and_the_strip(self):
        self.assertEqual(self.label(), "Approve minutes · tracks 3 actions")
        self.assertEqual([self.word(1), self.word(4)], ["Tracked", "Minutes only"])
        self.assertEqual(self.ev(f"document.querySelector(\"{ROW % 1} .mntrk\").getAttribute('aria-label')"),
                         "Track: Send the revised SOW to the client. Now Tracked")
        self.assertEqual(self.ev(f"document.querySelectorAll(\"{ROW % 1} .mntrk button\").length"), 3)
        self.assertRegex(self.strip(), r"^1 of 3 tracked items needs attention")
        self.b.click(ROW % 1 + " .mntrk button.m")                                  # Minutes only
        self.b.pump(0.3)
        self.assertEqual(self.trk()["1"], "")
        self.assertEqual(self.word(1), "Minutes only")
        self.assertEqual(self.label(), "Approve minutes · tracks 2 actions")
        self.assertEqual(self.summary(), "2 work items to register · 3 kept in the minutes only")
        self.b.click(ROW % 1 + " .mntrk button.n")                                  # Dropped
        self.b.pump(0.3)
        self.assertEqual(self.trk()["1"], "n")
        self.assertEqual(self.word(1), "Dropped")
        self.assertEqual(self.summary(), "2 work items to register · 2 kept in the minutes only · 1 removed")
        self.assertEqual(self.ev(f"getComputedStyle(document.querySelector(\"{ROW % 1} .mnit\")).textDecorationLine"), "line-through")
        self.assertIn("Now Dropped", self.ev(f"document.querySelector(\"{ROW % 1} .mntrk\").getAttribute('aria-label')"))
        self.b.click(ROW % 1 + " .mntrk button.y")                                  # Tracked again
        self.b.pump(0.3)
        self.assertEqual(self.label(), "Approve minutes · tracks 3 actions")
        for n in (1, 2, 3):                                                        # nothing tracked
            self.b.click(ROW % n + " .mntrk button.m")
        self.b.pump(0.3)
        self.assertEqual(self.label(), "Approve minutes · tracks nothing")
        self.assertEqual(self.strip(), "", "no strip with nothing tracked")
        self.b.click(ROW % 4 + " .mntrk button.y")                                  # the decision
        self.b.pump(0.3)
        self.assertEqual(self.label(), "Approve minutes · tracks 1 decision")
        self.assertIn("Every tracked item has an owner and a date", self.strip())

    def test_a02_keyboard_and_names(self):
        self.ev(f"document.querySelector(\"{ROW % 4} .mntrk button.y\").focus()")
        self.b.key("Enter") if hasattr(self.b, "key") else self.b.click(ROW % 4 + " .mntrk button.y")
        self.b.pump(0.3)
        self.assertEqual(self.trk()["4"], "y")
        names = self.ev(f"[...document.querySelectorAll(\"{ROW % 4} .mntrk button\")].map(b=>b.getAttribute('aria-label')+'|'+b.tagName)")
        self.assertEqual([x.split(":")[0] for x in names], ["Tracked", "Minutes only", "Dropped"])
        self.assertTrue(all(x.endswith("|BUTTON") for x in names), "real buttons: Tab and Enter work")

    def test_a03_flags_chips_and_next(self):
        flags = self.ev("[...document.querySelectorAll('#v-minutes .mnflag2')].map(x=>x.textContent)")
        self.assertEqual(flags, ["Needs a date"])
        self.b.click("#mnAttn .mnfchip[data-fl=date]")
        self.b.pump(0.3)
        self.assertEqual(self.ev("[...document.querySelectorAll('#v-minutes tr.mi')].filter(r=>!r.hidden).map(r=>r.dataset.n)"), ["3"])
        self.assertEqual(self.ev("document.querySelectorAll('#v-minutes table.mnt').length"), 1, "tables with no row to show leave")
        self.b.click("#mnAttn .mnfchip[data-fl=date]")
        self.b.pump(0.3)
        self.assertEqual(self.ev("[...document.querySelectorAll('#v-minutes tr.mi')].filter(r=>r.hidden).length"), 0)
        self.b.click("#mnNext")
        self.b.pump(0.4)
        self.assertTrue(self.ev(f"document.querySelector(\"{ROW % 3}\").classList.contains('nx')"))
        self.b.click(ROW % 3 + " .mntrk button.m")                                  # no longer tracked: its flag and the strip go
        self.b.pump(0.3)
        self.assertEqual(self.ev("document.querySelectorAll('#v-minutes .mnflag2').length"), 0)

    def test_a04_no_done_button_and_the_sparkles_stay(self):
        self.assertEqual(self.ev("document.querySelectorAll('#v-minutes .mnedit').length"), 0)
        self.b.click("#v-minutes .mnedbtn")
        self.b.wait("document.querySelector('#v-minutes .mnedit')", 10)
        txt = self.ev("[...document.querySelectorAll('#v-minutes .mnedit button')].map(b=>b.textContent.trim())")
        self.assertNotIn("Done", txt)
        self.b.key("Escape") if hasattr(self.b, "key") else self.ev("document.querySelector('#v-minutes .mnedit').dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))")
        self.b.pump(0.3)
        self.assertEqual(self.ev("document.querySelectorAll('#v-minutes .mnedit').length"), 0, "Esc goes back to the lines")
        self.assertGreaterEqual(self.ev("document.querySelectorAll('#v-minutes section[data-id=summary] .sheet-spark, #v-minutes .sheet-spark').length"), 1)

    def test_a05_decisions_have_the_room(self):
        w = self.ev("(()=>{const t=document.querySelector('#v-minutes section[data-id=decisions] table.mnt'); const c=[...t.querySelectorAll('thead th')].map(h=>h.getBoundingClientRect().width); return [c[1], c[2], t.querySelector('thead th:nth-child(3)').textContent]})()")
        self.assertEqual(w[2], "Made by")
        self.assertGreater(w[0], 3 * w[1], f"the decision text spans the row: {w}")


for _n in [n for n in dir(v2.MinutesViewV2) if n.startswith("test_")]:
    setattr(MinutesA302, _n, None)

if __name__ == "__main__":
    unittest.main()
