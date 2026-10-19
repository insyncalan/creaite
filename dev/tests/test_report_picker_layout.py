"""#235: the weekly report's "Add from the tracker" picker lays its rows out by their content.

An action whose title wraps to two or three lines used to overlap the rows above and below it, and the last row was clipped at the foot
of the list. Real Chrome on the real live server (fictional project, no Claude runs). With 10 open actions, some with long titles, the
picker is opened in the Overdue actions section and, at the default width and at 700 px, in light and dark:
- no two rows' boxes overlap;
- each row is at least as tall as its text;
- the list scrolls inside its own box, and its last row can be scrolled fully into view.

Run: python3 dev/tests/test_report_picker_layout.py      (Chrome tier; skipped without Chrome)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_dashboard as TD  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402

LONG = ("Agree the cut-over plan, the rollback steps and the named owners for every environment with the Example Client team, then "
        "confirm the dates in writing so the steering committee can sign them off before the freeze")
MID = "Chase the licence order with the vendor and record the purchase order number in the register"
SHORT = "Book the room"
TITLES = [LONG, SHORT, LONG + " (second pass)", MID, LONG + " (third pass)", SHORT + " twice", MID + " again",
          LONG + " (fourth pass)", SHORT + " once more", LONG + " (last)"]
SECTION = "#v-reporting section[data-id=overdue]"


class PickerLayout(LiveBrowserCase):
    shared_server = True

    @classmethod
    def load(cls, v):
        TD.populate(v)
        src = "projects/ABC Example Programme/minutes/steering.docx"
        v.propose("long", [TD.new("actions", 40 + i, project="ABC", description=t, owner="Sara Example", due_date=TD.d(20 + i),
                                  raised=TD.d(-2), source=src) for i, t in enumerate(TITLES)])
        TD.stamped_apply(v)

    def open_picker(self, w, mode):
        self.b.resize(w, 1000)
        self.b.reload("typeof go==='function' && LIVE")
        self.b.eval("go('reporting','ABC')")
        self.b.wait("document.querySelector('#v-reporting section[data-id=current_state]')", 20)
        self.b.eval(f"document.documentElement.dataset.theme='{mode}'")
        self.b.eval(f"document.querySelector('{SECTION} .rs-pick-open').click()")
        self.b.wait(f"document.querySelectorAll('{SECTION} .rs-pick-row').length>=10", 10)
        self.b.pump(0.3)

    def check(self, w, mode):
        self.open_picker(w, mode)
        q = self.b.eval
        where = f"{w}px {mode}"
        rows = q(f"""[...document.querySelectorAll('{SECTION} .rs-pick-row')].map(r=>{{const b=r.getBoundingClientRect(), t=r.querySelector('.rs-pick-t');
          return {{ref:r.dataset.ref, top:b.top, bottom:b.bottom, h:r.offsetHeight, text:t.scrollHeight}}}})""")
        self.assertGreaterEqual(len(rows), 10)
        self.assertGreater(max(r["text"] for r in rows), 3 * 12, f"{where}: some title wraps to several lines")
        for a, b in zip(rows, rows[1:]):
            self.assertLessEqual(a["bottom"], b["top"] + 0.5, f"{where}: {a['ref']} overlaps {b['ref']}")
        for r in rows:
            self.assertGreaterEqual(r["h"] + 0.5, r["text"], f"{where}: {r['ref']} is shorter than its text")
        box = q(f"""(()=>{{const l=document.querySelector('{SECTION} .rs-pick-list'); return {{sh:l.scrollHeight, ch:l.clientHeight, oy:getComputedStyle(l).overflowY}}}})()""")
        self.assertGreater(box["sh"], box["ch"], f"{where}: the list scrolls inside its box")
        self.assertIn(box["oy"], ("auto", "scroll"))
        last = q(f"""(()=>{{const l=document.querySelector('{SECTION} .rs-pick-list'); l.scrollTop=l.scrollHeight;
          const rs=l.querySelectorAll('.rs-pick-row'), r=rs[rs.length-1].getBoundingClientRect(), b=l.getBoundingClientRect();
          return {{rb:r.bottom, lb:b.bottom, rt:r.top, lt:b.top}}}})()""")
        self.assertLessEqual(last["rb"], last["lb"] + 1, f"{where}: the last row is fully inside the list at the bottom")
        self.assertGreaterEqual(last["rt"], last["lt"] - 1, f"{where}: the last row starts inside the list")

    def test_default_width_light(self):
        self.check(1400, "light")

    def test_default_width_dark(self):
        self.check(1400, "dark")

    def test_narrow_light(self):
        self.check(700, "light")

    def test_narrow_dark(self):
        self.check(700, "dark")


if __name__ == "__main__":
    unittest.main()
