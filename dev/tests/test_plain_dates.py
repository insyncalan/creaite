"""BL-147: dates typed in plain words. The one parser (parseWhen) against a fixed "today", every form the item lists and the
ones it must refuse; then a real date field in the browser showing what it understood ("Friday 16-10-2026") and holding
DD-MM-YYYY afterwards.

Run: python3 dev/tests/test_plain_dates.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

SAT = "2026-10-10"      # a Saturday
WED = "2026-10-14"
FRI = "2026-10-16"

ACCEPTED = [
    # (text, today, due, expected)
    ("today", SAT, False, "2026-10-10"), ("Today", SAT, True, "2026-10-10"),
    ("tomorrow", SAT, False, "2026-10-11"), ("yesterday", SAT, False, "2026-10-09"),
    ("fri", SAT, True, "2026-10-16"), ("friday", SAT, True, "2026-10-16"), ("Fri", SAT, False, "2026-10-16"),
    ("next fri", SAT, True, "2026-10-23"), ("sat", SAT, True, "2026-10-17"),               # never today
    ("mon", SAT, True, "2026-10-12"), ("tues", SAT, True, "2026-10-13"), ("thurs", SAT, True, "2026-10-15"),
    ("fri", WED, True, "2026-10-16"), ("fri", FRI, True, "2026-10-23"), ("next fri", FRI, True, "2026-10-30"),
    ("+3d", SAT, True, "2026-10-13"), ("+2w", SAT, True, "2026-10-24"), ("+1m", SAT, True, "2026-11-10"),
    ("+1m", "2026-01-31", True, "2026-02-28"), ("3 days", SAT, True, "2026-10-13"), ("in 2 weeks", SAT, True, "2026-10-24"),
    ("next week", SAT, True, "2026-10-12"), ("next week", "2026-10-12", True, "2026-10-19"),           # Monday
    ("end of week", SAT, True, "2026-10-16"), ("end of week", WED, True, "2026-10-16"), ("end of week", FRI, True, "2026-10-16"),
    ("end of month", SAT, True, "2026-10-31"), ("end of month", "2026-02-03", True, "2026-02-28"),
    ("15/10", SAT, True, "2026-10-15"), ("15-10", SAT, True, "2026-10-15"),
    ("5/10", SAT, True, "2027-10-05"),                  # a due date: next year rather than the past
    ("5/10", SAT, False, "2026-10-05"),                 # any other date: this year
    ("15 oct", SAT, True, "2026-10-15"), ("15 October", SAT, True, "2026-10-15"), ("oct 15", SAT, True, "2026-10-15"),
    ("16-10-2026", SAT, True, "2026-10-16"), ("16/10/2026", SAT, True, "2026-10-16"), ("16.10.2026", SAT, True, "2026-10-16"),
    ("16-10-26", SAT, True, "2026-10-16"), ("2026-10-16", SAT, True, "2026-10-16"), ("01-01-2025", SAT, True, "2025-01-01"),
    ("29-02-2028", SAT, True, "2028-02-29"),
]
REFUSED = ["abc", "32-10-2026", "31-02-2026", "29-02-2027", "15/13", "next", "fri fri", "1-2-3-4", "+", "march",
           "tomorrow please", "next month please", "0/10", "99"]


class PlainDates(LiveBrowserCase):
    shared_server = True

    def parse(self, text, today, due):
        return self.b.eval(f"parseWhen({json.dumps(text)},{json.dumps(today)},{json.dumps(due)})")

    def test_every_form_against_a_fixed_today(self):
        got = self.b.eval("JSON.stringify(%s.map(([t,d,u])=>parseWhen(t,d,u)))" % json.dumps([a[:3] for a in ACCEPTED]))
        for (text, today, due, want), have in zip(ACCEPTED, json.loads(got)):
            self.assertEqual(have, want, (text, today, due))

    def test_what_it_refuses(self):
        got = json.loads(self.b.eval("JSON.stringify(%s.map(t=>parseWhen(t,%s,true)))" % (json.dumps(REFUSED), json.dumps(SAT))))
        for text, have in zip(REFUSED, got):
            self.assertIsNone(have, text)
        self.assertIsNone(self.parse("", SAT, True))

    def friday(self):
        t = date.today()
        return t + timedelta(days=((4 - t.weekday()) % 7) or 7)

    def test_a_field_says_what_it_understood_and_then_holds_dd_mm_yyyy(self):
        """BL-186: milestone dates are calendar picks now, so this uses Work's due-date cell, a typed date field that remains."""
        b = self.b
        b.eval("S.autoApply=true; WT='actions'; go('work')")
        b.wait("document.querySelector('#workTbl tr[data-row]')")
        b.click('#wlay [data-lay="list"]')
        b.eval("COLVIS[WT]=[...new Set([...COLVIS[WT],'due'])]; renderWork()")
        id_ = b.eval("A.find(x=>x.p==='ABC'&&x.st==='Open').id")
        cell = f'#workTbl tr[data-row="{id_}"] td[data-f="due"]'
        b.click(cell)
        b.wait("document.activeElement&&document.activeElement.id==='ceDate'")
        b.eval("$('#ceDate').select()")
        b.type("fri")
        b.pump(0.1)
        fri = self.friday()
        hint = b.eval("$('#dateHint')&&!$('#dateHint').hidden?$('#dateHint').textContent:''")
        self.assertEqual(hint, f"Friday {fri:%d-%m-%Y}")                       # what it understood, straight away
        hb, fb = json.loads(b.eval("JSON.stringify([$('#dateHint').getBoundingClientRect(),$('#ceDate').getBoundingClientRect()])"))
        self.assertGreaterEqual(hb["top"], fb["bottom"] - 1)                  # under the field, not over it
        b.eval("$('#ceDate').select()")
        b.type("someday")
        b.pump(0.1)
        bad = b.eval("$('#dateHint').textContent")
        self.assertIn("Not a date creaite knows", bad)                        # said in words, with examples
        self.assertIn("“fri”", bad)
        self.assertTrue(b.eval("$('#dateHint').classList.contains('bad')"))
        b.eval("$('#ceDate').select()")
        b.type("fri")
        b.key("Enter")                                                        # Enter settles it to DD-MM-YYYY and saves it
        b.wait(f"REC('actions','{id_}').due==='{fri.isoformat()}'", 20)
        for _ in range(100):                                                  # the apply writes it a moment later
            if next(r for r in self.v.rows("actions") if r["id"] == id_)["due_date"] == fri.isoformat():
                break
            b.pump(0.2)
        self.assertEqual(next(r for r in self.v.rows("actions") if r["id"] == id_)["due_date"], fri.isoformat())
    # BL-301 C: Quick Capture's typed date went with its form (the capture drawer replaced it); a Working session note takes
    # its date from the meeting.


if __name__ == "__main__":
    unittest.main()
