"""#313 (2.6.1): no work item is shown twice on Today. The one-row rule, and a guard that fails when any two sections of
Today list the same ID (a later section, such as #310's milestone "open items" count, must count, never add a row).

Run: python3 dev/tests/test_today_once.py   (Chrome tier; skipped without Chrome)
The demo vault (test_dashboard.populate) plus one fixture where the same work qualifies for several sections.
"""
import json
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


def d(n):
    return (_today() + timedelta(days=n)).isoformat()


# every section of Today that lists work, by its host element; the order is the claim order of the one-row rule
SECTIONS = ["dnList", "attnList", "mineList", "oweList", "waitList", "tdBody", "weekList"]

# what each section lists: the item IDs it names, from the row's own link, its data-attributes and the words of a row that
# names items (a milestone row's open items, a decisions line's links); the "If it stays open" context line is not a row
AUDIT_JS = """(()=>{ const ID=/[A-Z][A-Z0-9]{1,6}-(?:[A-Z]-)?\\d{3}\\b/g, out={};
  for(const s of %s){ const host=document.getElementById(s); const ids=[]; if(!host){ out[s]=ids; continue; }
    host.querySelectorAll('li, .wkrow, .tdrow, [data-td]').forEach(row=>{
      if(row.parentElement.closest('li, .wkrow, [data-td]')) return;                       /* the outer row only */
      const own=[]; row.querySelectorAll('[data-open],[data-promise],[data-ms],[data-msattn]').forEach(a=>{
        if(a.closest('.dnslip')||a.closest('.tacts')) return;
        const v=a.dataset.open?a.dataset.open.split(':')[1]:(a.dataset.promise||a.dataset.ms||a.dataset.msattn); if(v) own.push(v); });
      const t=row.querySelector('.tb')?row.querySelector('.tb').cloneNode(true):row.cloneNode(true); t.querySelectorAll('.dnslip').forEach(x=>x.remove());
      (t.textContent.match(ID)||[]).forEach(x=>own.push(x));
      if(row.dataset.wk){ const m=row.dataset.wk.match(/[A-Z][A-Z0-9]{1,6}-(?:[A-Z]-)?\\d{3}$/); if(m) own.push(m[0]); }
      [...new Set(own)].forEach(x=>ids.push(x)); });
    out[s]=ids; } return out; })()""" % json.dumps(SECTIONS)


def duplicates(rows):
    """Every ID listed more than once across the sections, as {id: [sections]}."""
    seen = {}
    for sec in SECTIONS:
        for i in rows.get(sec, []):
            seen.setdefault(i, []).append(sec)
    return {i: s for i, s in seen.items() if len(s) > 1}


class Seeded(LiveBrowserCase):
    shared_server = True

    @classmethod
    def load(cls, v):
        populate(v)
        v.propose("ms313", [
            new("milestones", 1, project="DEF", name="Pilot go-live", baseline_date=d(3), forecast_date=d(3), source=SRC),
            new("milestones", 2, project="ABC", name="Data ready", baseline_date=d(5), forecast_date=d(5), source=SRC)])
        v.run("apply")
        ms = {m["name"]: m["id"] for m in v.rows("milestones")}
        cls.MS = ms
        a = lambda n, desc, **kw: action(n, description=desc, source=SRC, **kw)  # noqa: E731
        v.propose("items313", [
            # Alan's own, overdue and due soon, on a milestone that is due soon: Your commitments AND the milestone row
            a(1, "Confirm the licence count", project="DEF", milestone=ms["Pilot go-live"], due_date=d(-1)),
            a(2, "Schedule training sessions", project="DEF", milestone=ms["Pilot go-live"], due_date=d(2)),
            # someone else's, due soon, on the same milestone: the milestone row AND the Week ahead
            a(3, "Order pilot laptops", project="DEF", owner="Omar Ali", milestone=ms["Pilot go-live"], due_date=d(1)),
            new("raid", 4, project="DEF", type="Issue", description="Training room not booked", impact="Medium",
                likelihood="High", raised=d(-2), milestone=ms["Pilot go-live"], source=SRC),
            # a decision asked of Alan, and one of someone else, both needed soon; one with no decision maker
            new("decisions", 5, project="DEF", decision="Choose the pilot venue", made_by="Alan Carter", status="Pending",
                needed_by=d(1), source=SRC),
            new("decisions", 6, project="DEF", decision="Approve the extra tester", made_by="Sara Example", status="Pending",
                needed_by=d(-2), source=SRC),
            new("decisions", 7, project="DEF", decision="Pick the training supplier", status="Pending", source=SRC),
            # a promise of Alan's, and one made to him that is overdue
            new("promises", 8, project="DEF", promised_by="Alan Carter", promised_to="Sara Example",
                description="Send the pilot plan", due_date=d(2), raised=d(-5), source=SRC),
            new("promises", 9, project="DEF", promised_by="Omar Ali", promised_to="Alan Carter",
                description="Share the vendor quote", due_date=d(-4), raised=d(-9), source=SRC),
            # urgent work with no date (Week ahead's first group) and a plain action of someone else's
            a(10, "Escalate the supplier contract", project="DEF", owner="Omar Ali", priority="Urgent", due_date=None),
        ])
        v.run("apply")
        v.run(script="build_dashboard.py")

    def today(self):
        self.b.eval("go('today'); renderToday()")
        self.b.wait("document.getElementById('attnList')")

    def audit(self):
        self.today()
        return self.b.eval(AUDIT_JS)


def ids_of(b, desc):
    """The IDs of the work whose title is `desc`, from the page's own data."""
    return b.eval("[...A,...R,...DEC,...(D.promises||[])].filter(x=>x.t===%s).map(x=>x.id)" % json.dumps(desc))


class OnceOnToday(Seeded):
    def home(self, rows, desc):
        ids = ids_of(self.b, desc)
        self.assertEqual(len(ids), 1, desc)
        return ids[0], [s for s in SECTIONS if ids[0] in rows[s]]

    def test_guard_no_id_is_listed_in_two_sections(self):
        rows = self.audit()
        self.assertTrue(rows["mineList"] and rows["dnList"] and rows["attnList"], "the fixture fills the sections")
        self.assertEqual(duplicates(rows), {}, "an ID listed in two sections: count it or link it, do not add a row")

    def test_the_guard_does_catch_a_repeat(self):
        rows = self.audit()
        rows["weekList"] = rows["weekList"] + [rows["mineList"][0]]
        self.assertEqual(duplicates(rows), {rows["mineList"][0]: ["mineList", "weekList"]})

    def test_each_item_has_one_home_in_claim_order(self):
        rows = self.audit()
        for desc, home in (("Choose the pilot venue", ["dnList"]), ("Approve the extra tester", ["dnList"]),
                           ("Confirm the licence count", ["mineList"]), ("Schedule training sessions", ["mineList"]),
                           ("Order pilot laptops", ["attnList"]), ("Pick the training supplier", ["attnList"]),
                           ("Send the pilot plan", ["oweList"]), ("Share the vendor quote", ["waitList"])):
            _id, where = self.home(rows, desc)
            self.assertEqual(where, home, desc)
        ms = self.MS["Pilot go-live"]
        self.assertEqual([s for s in SECTIONS if ms in rows[s]], ["attnList"], "a milestone with a row above is not in Week ahead")

    def test_a_decision_is_named_once_and_the_line_counts_the_rest(self):
        self.audit()
        line = self.b.eval("document.querySelector('#attnList [data-decpending]').closest('li').textContent")
        self.assertIn("Pick the training supplier", line, "a decision with no decision maker is named here")
        self.assertNotIn("Choose the pilot venue", line)
        self.assertIn("2 are listed under Decisions needed.", line)

    def test_the_milestone_row_counts_your_own_and_names_the_others(self):
        self.audit()
        row = self.b.eval("document.querySelector('#attnList li[data-msattn]').textContent")
        self.assertIn("Order pilot laptops", row)
        self.assertNotIn("Schedule training sessions", row)
        self.assertRegex(row, r"\d+ (is|are) under Your commitments")

    def test_the_milestone_count_adds_no_second_row(self):
        """#310 with #313: the open-items count button is on the milestone's one row, never a row of its own."""
        rows = self.audit()
        ms = self.MS["Pilot go-live"]
        self.assertEqual(sum(r.count(ms) for r in rows.values()), 1, "the milestone is listed once across Today")
        self.assertEqual(self.b.eval("document.querySelectorAll('#attnList li[data-msattn] .wkcnt').length"),
                         self.b.eval("document.querySelectorAll('#attnList li[data-msattn]').length"),
                         "one count button per Needs attention milestone row")
        self.assertEqual(duplicates(rows), {})

    def test_the_week_ahead_counts_how_many_are_listed_above(self):
        self.audit()
        note = self.b.eval("document.getElementById('weekTo').textContent")
        self.assertRegex(note, r"^\d+ items? to .+ · \d+ more listed above$")

    def test_sections_are_in_claim_order_on_the_page(self):
        self.today()
        order = self.b.eval("""[...document.querySelectorAll('#tBrief > .tsec')].map(x=>x.id)""")
        pos = [order.index(i) for i in ("dnSec", "attnSec", "mineSec", "weekSec")]
        self.assertEqual(pos, sorted(pos))


class OnceOnToday900(OnceOnToday):
    width, height = 900, 1000


if __name__ == "__main__":
    unittest.main()
