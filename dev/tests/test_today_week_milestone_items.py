"""#310 + #313 (2.6.1): a milestone is ONE row on Today (Needs attention if it qualifies there, else the Week ahead) and that row says how many open work items a milestone depends on ("3 open items", "1 open item",
"3 open, 1 overdue"; nothing when none), the milestone opens when clicked, and the count opens Work on that milestone with open
items only.

Run: python3 dev/tests/test_today_week_milestone_items.py   (Chrome tier; skipped without Chrome)
"""
import sys
import unittest
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import new, populate  # noqa: E402
from test_dashboard import today as _today  # noqa: E402
from test_tracker import action  # noqa: E402

SRC = "Alan (cx-edit)"


def weekday(n):
    """The first working day from n days on, as an ISO date (a weekend has no row in the Week ahead)."""
    x = _today() + timedelta(days=n)
    while x.weekday() > 4:
        x += timedelta(days=1)
    return x.isoformat()


MILESTONES = [("Empty one", "ABC", 1), ("Single one", "ABC", 1), ("Busy one", "DEF", 2), ("Only closed", "ABC", 2),
              ("Risk only", "DEF", 2)]
# Single one and Busy one have open actions: their single row is in Needs attention. Empty one, Only closed and Risk only
# (a risk alone does not qualify for Needs attention) have their single row in the Week ahead.


class WeekMilestoneItems(LiveBrowserCase):
    shared_server = True

    @classmethod
    def load(cls, v):
        populate(v)
        v.propose("ms310", [new("milestones", i + 1, project=p, name=n, baseline_date=weekday(k), forecast_date=weekday(k),
                                status="Planned", source=SRC) for i, (n, p, k) in enumerate(MILESTONES)])
        v.run("apply")
        ms = {m["name"]: m["id"] for m in v.rows("milestones")}
        cls.MS = ms
        yesterday = (_today() - timedelta(days=1)).isoformat()
        v.propose("items310", [
            action(1, milestone=ms["Single one"], description="Only open thing", due_date=weekday(3), source=SRC),
            action(2, milestone=ms["Busy one"], description="Late thing", project="DEF", due_date=yesterday, source=SRC),
            action(3, milestone=ms["Busy one"], description="Delayed thing", project="DEF", due_date=weekday(3), status="Delayed", source=SRC),
            action(4, milestone=ms["Busy one"], description="Finished thing", project="DEF", status="Closed", closed=yesterday, source=SRC),
            action(5, milestone=ms["Busy one"], description="Dropped thing", project="DEF", status="Cancelled", source=SRC),
            new("raid", 6, project="DEF", type="Risk", description="Open risk", impact="Low", likelihood="Low",
                raised=yesterday, milestone=ms["Busy one"], source=SRC),
            new("raid", 7, project="DEF", type="Issue", description="Closed issue", impact="Low", likelihood="Low",
                raised=yesterday, status="Closed", closed=yesterday, milestone=ms["Busy one"], source=SRC),
            new("raid", 9, project="DEF", type="Risk", description="Lone risk", impact="Low", likelihood="Low",
                raised=yesterday, milestone=ms["Risk only"], source=SRC),
            action(8, milestone=ms["Only closed"], description="Done already", status="Closed", closed=yesterday, source=SRC),
        ])
        v.run("apply")
        v.run(script="build_dashboard.py")

    def today(self):
        self.b.eval("go('today'); renderToday()")
        self.b.wait("document.getElementById('weekList')")

    def entry(self, name):
        """The milestone's row(s) across Needs attention and the Week ahead: where it is, how many rows, and its count button."""
        mid = self.MS[name]
        return self.b.eval(f"""(()=>{{ const q=(sel)=>[...document.querySelectorAll(sel)];
          const attn=q('#attnList li[data-msattn="{mid}"]'), wk=q('#weekList li.wk-milestone').filter(l=>l.querySelector('a.t[data-ms="{mid}"]'));
          const li=attn[0]||wk[0]; if(!li) return {{rows:0}}; const c=li.querySelector('.wkcnt');
          return {{rows:attn.length+wk.length, where:attn.length?'attn':'week', buttons:li.querySelectorAll('.wkcnt').length,
          text:c?c.textContent:null, tip:c?c.dataset.tip:null, aria:c?c.getAttribute('aria-label'):null,
          warn:c&&c.querySelector('.warn')?c.querySelector('.warn').textContent:null}}; }})()""")

    def test_count_for_none_one_and_several(self):
        self.today()
        self.assertEqual(self.entry("Empty one"), {"rows": 1, "where": "week", "buttons": 0, "text": None, "tip": None,
                                                   "aria": None, "warn": None})
        one = self.entry("Single one")
        self.assertEqual((one["where"], one["rows"], one["buttons"]), ("attn", 1, 1), "in Needs attention: one row, one count")
        self.assertEqual((one["text"], one["tip"]), ("1 open item", "1 open work item this milestone depends on"))
        self.assertEqual(one["aria"], "Milestone Single one: 1 open work item. Open the list")
        busy = self.entry("Busy one")
        self.assertEqual((busy["where"], busy["rows"], busy["buttons"]), ("attn", 1, 1))
        lone = self.entry("Risk only")
        self.assertEqual((lone["where"], lone["rows"], lone["buttons"], lone["text"]), ("week", 1, 1, "1 open item"),
                         "only in the Week ahead: the same count on its single row")
        self.assertEqual(busy["text"], "3 open, 1 overdue", "open action, delayed action and open risk; closed and cancelled left out")
        self.assertEqual(busy["warn"], ", 1 overdue")
        self.assertEqual(busy["tip"], "3 open work items this milestone depends on")
        self.assertEqual(busy["aria"], "Milestone Busy one: 3 open work items, 1 overdue. Open the list")
        self.assertIsNone(self.entry("Only closed")["text"], "only closed work: no count, not a 0")

    def test_a_milestone_is_one_row_with_one_count(self):
        self.today()
        for name, _p, _k in MILESTONES:
            self.assertEqual(self.entry(name)["rows"], 1, name)

    def test_archived_items_are_left_out(self):
        self.today()
        self.b.eval(f"A.find(x=>x.ms==={self.MS['Single one']!r}).ar=true; renderToday()")
        self.assertIsNone(self.entry("Single one")["text"])

    def test_the_milestone_opens_and_the_count_opens_work(self):
        self.today()
        mid = self.MS["Busy one"]
        self.b.click(f"#attnList li[data-msattn=\"{mid}\"] a.t")
        self.b.wait("VIEW==='milestones' && MSCODE==='DEF'")
        self.today()
        self.b.click(f"#attnList li[data-msattn=\"{mid}\"] .wkcnt[data-wkitems=\"{mid}\"]")
        self.b.wait("VIEW==='work' && WT==='all'")
        self.assertEqual(self.b.eval("[[...FX.mi],WQ]"), [[mid], ""])
        self.assertEqual(self.b.eval("items().filter(x=>passes(x)).map(x=>x.t).sort()"),
                         ["Delayed thing", "Late thing", "Open risk"], "the same three, open only")

    def test_the_week_ahead_row_opens_and_counts_the_same_way(self):
        self.today()
        mid = self.MS["Risk only"]
        self.b.click(f"#weekList a.t[data-ms=\"{mid}\"]")
        self.b.wait("VIEW==='milestones' && MSCODE==='DEF'")
        self.today()
        self.b.click(f"#weekList .wkcnt[data-wkitems=\"{mid}\"]")
        self.b.wait("VIEW==='work' && WT==='all'")
        self.assertEqual(self.b.eval("[[...FX.mi],WQ]"), [[mid], ""])
        self.assertEqual(self.b.eval("items().filter(x=>passes(x)).map(x=>x.t).sort()"), ["Lone risk"])

    def test_the_count_is_a_keyboard_button(self):
        self.today()
        mid = self.MS["Risk only"]
        self.assertEqual(self.b.eval(f"""(()=>{{ const c=document.querySelector('#weekList .wkcnt[data-wkitems="{mid}"]');
          c.focus(); return [c.tagName, document.activeElement===c, c.tabIndex]; }})()"""), ["BUTTON", True, 0])


if __name__ == "__main__":
    unittest.main()
