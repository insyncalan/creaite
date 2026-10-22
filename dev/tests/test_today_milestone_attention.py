"""#251 (2.6): Today's Needs attention gets one row per open milestone due within the Due soon window (or past due) that has
open actions or issues attached: "Milestone <u>Pilot go-live</u> is due Thursday 22nd October: 3 open items must close for it
to hold". Brief: dev/sprints/milestone-attention-brief.md (pm-intake-briefs); approved by Alan 20-10-2026 with the row
reading "Milestone <name>". Risks are left out; no dismiss.

Run: python3 dev/tests/test_today_milestone_attention.py   (Chrome tier; skipped without Chrome)
The demo vault (test_dashboard.populate) plus eight milestones of every kind the brief names and items attached to them.
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


def d(n):
    return (_today() + timedelta(days=n)).isoformat()


def ordinal(n):
    return f"{n}{'th' if 11 <= n % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def long_day(n):
    """Today's way of writing a date: "Thursday 22nd October" (the year only when it isn't this year)."""
    x = _today() + timedelta(days=n)
    return f"{x:%A} {ordinal(x.day)} {x:%B}" + (f" {x.year}" if x.year != _today().year else "")


def weekday(n):
    return f"{_today() + timedelta(days=n):%A}"


MILESTONES = [  # name, project, baseline, forecast, status: what the row should do
    ("Pilot go-live", "DEF", d(3), d(3), "Planned"),         # a row: 4 open items, one late
    ("Build review", "ABC", d(12), d(1), "Planned"),         # a row by its forecast (the baseline is outside the window)
    ("Design sign-off", "ABC", d(9), d(9), "Planned"),       # outside the 7-day window: no row
    ("Vendor chosen", "ABC", d(2), d(2), "Done"),            # achieved: no row
    ("Kick-off pack", "DEF", d(4), d(4), "Planned"),         # nothing attached: no row
    ("Data ready", "ABC", d(-2), None, "Planned"),           # past due and still open: a row, first
    ("Training plan", "DEF", None, None, "Planned"),         # no date: no row
    ("Contract signed", "ABC", d(2), d(15), "Planned"),      # the forecast moved it out of the window: no row
]


class Seeded(LiveBrowserCase):
    shared_server = True

    @classmethod
    def load(cls, v):
        populate(v)
        v.propose("ms251", [new("milestones", i + 1, project=p, name=n, baseline_date=b, forecast_date=f, status=s, source=SRC)
                            for i, (n, p, b, f, s) in enumerate(MILESTONES)])
        v.run("apply")
        ms = {m["name"]: m["id"] for m in v.rows("milestones")}
        cls.MS = ms
        a = lambda n, ms_name, desc, **kw: action(n, milestone=ms[ms_name], description=desc, source=SRC, **kw)  # noqa: E731
        v.propose("items251", [
            a(1, "Pilot go-live", "Confirm licence count with procurement", project="DEF", owner="Omar Ali", due_date=d(-1)),
            a(2, "Pilot go-live", "Schedule training sessions", project="DEF", owner="Omar Ali", due_date=d(3)),
            a(3, "Pilot go-live", "Order pilot laptops", project="DEF", owner="Omar Ali", due_date=d(2), status="Delayed"),
            a(4, "Pilot go-live", "Print pilot guides", project="DEF", due_date=d(1), status="Closed", closed=d(-1)),
            new("raid", 5, project="DEF", type="Issue", description="Training room not booked", impact="Medium",
                likelihood="High", raised=d(-2), milestone=ms["Pilot go-live"], source=SRC),
            new("raid", 6, project="DEF", type="Risk", description="Pilot users unavailable", impact="High",
                likelihood="Medium", raised=d(-2), milestone=ms["Pilot go-live"], source=SRC),
            a(7, "Build review", "Review vendor security answers", owner="Omar Ali", due_date=d(0)),
            new("raid", 8, project="ABC", type="Risk", description="Reviewer on leave", impact="Low", likelihood="Low",
                raised=d(-1), milestone=ms["Build review"], source=SRC),
            a(9, "Design sign-off", "Circulate the design pack", due_date=d(5)),
            a(10, "Vendor chosen", "File the vendor scoring", due_date=d(1)),
            a(11, "Data ready", "Load the masked data set", due_date=d(-3)),
            a(12, "Training plan", "Draft the training plan", project="DEF", due_date=d(4)),
            a(13, "Contract signed", "Send the contract to legal", due_date=d(1)),
        ])
        v.run("apply")
        v.run(script="build_dashboard.py")

    def today(self):
        self.b.eval("go('today'); renderToday()")
        self.b.wait("document.getElementById('attnList')")

    def rows(self):
        return self.b.eval("""[...document.querySelectorAll('#attnList > li[data-msattn]')].map(li=>({id:li.dataset.msattn,
          pos:[...li.parentNode.children].indexOf(li), title:li.querySelector('a.t').textContent, u:(li.querySelector('a.t u')||{}).textContent,
          ms:li.querySelector('a.t').dataset.ms, body:li.querySelector('.tb p').textContent,
          late:[...li.querySelectorAll('.tb p .late')].map(s=>s.textContent), hidden:li.hidden}))""")


class MilestoneRows(Seeded):
    def test_one_row_per_milestone_due_soon_soonest_first_with_the_words(self):
        self.today()
        r = self.rows()
        ms = self.MS
        self.assertEqual([x["id"] for x in r], [ms["Data ready"], ms["Build review"], ms["Pilot go-live"]])
        self.assertEqual([x["pos"] for x in r], [0, 1, 2], "milestone rows sit first in Needs attention")
        self.assertEqual(r[0]["title"], f"Milestone Data ready is overdue by 2 days (due {long_day(-2)}): "
                                        "its open work must close before it can be achieved")
        self.assertEqual(r[1]["title"], "Milestone Build review is due tomorrow: its open work must close for it to hold")
        self.assertEqual(r[2]["title"], f"Milestone Pilot go-live is due {long_day(3)}: its open work must close for it to hold")
        self.assertEqual([x["u"] for x in r], ["Data ready", "Build review", "Pilot go-live"], "the name is the underlined link")
        self.assertEqual([x["ms"] for x in r], [x["id"] for x in r], "the title opens the milestone")

    def test_the_sub_line_late_first_in_red_then_due_days_and_more(self):
        self.today()
        pilot = self.rows()[2]
        self.assertEqual(len(pilot["late"]), 1, pilot["late"])
        self.assertRegex(pilot["late"][0], r"^DEF-A-\d{3} ")
        self.assertTrue(pilot["late"][0].endswith("Confirm licence count with procurement, 1 day late"), pilot["late"])
        parts = pilot["body"].split(" · ")
        self.assertTrue(parts[0].endswith("Confirm licence count with procurement, 1 day late"), parts)
        self.assertTrue(parts[1].endswith(f"Order pilot laptops, due {weekday(2)}"), parts)
        self.assertTrue(parts[2].endswith(f"Schedule training sessions, due {weekday(3)}"), parts)
        self.assertEqual(parts[3:], ["and 1 more", "Digital Enablement", "5 open, 1 overdue"])  # the count is #310's: open actions and RAID items, risks included
        build = self.rows()[1]
        self.assertEqual(build["body"].split(" · ")[1:], ["Example Programme", "2 open items"])
        self.assertTrue(build["body"].split(" · ")[0].endswith("Review vendor security answers, due today"))
        self.assertNotIn("Reviewer on leave", build["body"], "risks are left out")
        late_colour = self.b.eval("""(()=>{ const s=document.querySelector('#attnList li[data-msattn] .tb p .late');
          const p=document.createElement('span'); p.style.color='var(--bad)'; document.body.appendChild(p);
          const r=[getComputedStyle(s).color, getComputedStyle(p).color]; p.remove(); return r; })()""")
        self.assertEqual(late_colour[0], late_colour[1], "late items are red")

    def test_no_owner_or_no_date_says_so(self):
        self.today()
        self.b.eval("EXPAND.add('ms:'+%r); renderToday()" % self.MS["Pilot go-live"])
        self.assertTrue(self.b.eval("typeof msAttention==='function'"))
        words = self.b.eval("msAttention().find(m=>m.ms===%r).its.map(x=>msItemWords(x).replace(/<[^>]+>/g,''))"
                            % self.MS["Pilot go-live"])
        self.assertEqual(words[-1].split(" ", 1)[1], "Training room not booked, no due date, no owner")

    def test_the_count_and_the_page_agree(self):
        self.today()
        o = self.b.eval("""({n:document.getElementById('nAttn').textContent, items:attentionItems().length,
          li:document.querySelectorAll('#attnList > li').length, more:(document.querySelector('#attnMore button')||{}).textContent||''})""")
        self.assertEqual(int(o["n"]), o["items"])
        self.assertEqual(o["li"], o["items"], "every row is drawn (the ones after five hidden behind +n more)")
        self.assertGreaterEqual(o["items"], 3)

    def test_the_title_opens_the_milestone(self):
        self.today()
        ms = self.MS["Pilot go-live"]
        self.b.click(f'#attnList li[data-msattn="{ms}"] a.t')
        self.b.wait("VIEW==='milestones' && MSCODE==='DEF'")

    def test_the_count_opens_work_listing_exactly_the_counted_items(self):
        self.today()
        ms = self.MS["Pilot go-live"]
        self.b.eval(f"""document.querySelector('#attnList li[data-msattn="{ms}"] .tb p button.wkcnt').click()""")
        self.b.wait("VIEW==='work' && WT==='all'")
        got = self.b.eval("items().filter(x=>passes(x)).map(x=>x.t).sort()")
        self.assertEqual(self.b.eval("[[...FX.mi],WQ]"), [[ms], ""], "the Milestone filter, not a search")
        self.assertEqual(got, sorted(["Confirm licence count with procurement", "Schedule training sessions",
                                      "Order pilot laptops", "Training room not booked", "Pilot users unavailable"]))

    def test_the_menu_has_no_dismiss(self):
        self.today()
        ms = self.MS["Pilot go-live"]
        self.b.click(f'#attnList li[data-msattn="{ms}"] .dots')
        self.b.wait("document.querySelector('#msAttnMenu')")
        names = self.b.eval("[...document.querySelectorAll('#msAttnMenu [role=menuitem]')].map(x=>x.textContent.trim())")
        self.assertEqual(names, ["Open the milestone", "Open all 4 in Work", "Open Digital Enablement"])
        self.assertFalse(any("Dismiss" in n for n in names))
        self.b.eval("[...document.querySelectorAll('#msAttnMenu [role=menuitem]')].find(x=>/^Open Digital/.test(x.textContent)).click()")
        self.b.wait("VIEW==='cockpit' && COCK==='DEF'")


class ItGoesAwayByItself(Seeded):
    shared_server = False    # the page's data is changed here

    def test_closing_the_items_removes_the_row_and_a_later_item_brings_it_back(self):
        self.today()
        ms = self.MS["Build review"]
        self.assertIn(ms, [x["id"] for x in self.rows()])
        self.b.eval(f"A.filter(x=>x.ms==={ms!r}).forEach(x=>{{ x.st='Closed'; }}); renderToday()")
        self.assertNotIn(ms, [x["id"] for x in self.rows()])
        self.b.eval(f"R.find(x=>x.ms==={ms!r}).type='Issue'; renderToday()")          # an open issue attached later
        self.assertIn(ms, [x["id"] for x in self.rows()])

    def test_achieved_or_due_today_or_out_of_the_window(self):
        self.today()
        ms = self.MS["Pilot go-live"]
        self.b.eval(f"(()=>{{ const m=msFind({ms!r}).m; m[8]=TODAY; renderToday(); }})()")
        row = next(x for x in self.rows() if x["id"] == ms)
        self.assertTrue(row["title"].startswith("Milestone Pilot go-live is due today: "), row["title"])
        self.b.eval(f"(()=>{{ const m=msFind({ms!r}).m; m[8]=pkAdd(TODAY,S.dueSoon+1); renderToday(); }})()")
        self.assertNotIn(ms, [x["id"] for x in self.rows()], "a forecast past the window: no row")
        self.b.eval(f"(()=>{{ const m=msFind({ms!r}).m; m[8]=pkAdd(TODAY,S.dueSoon); renderToday(); }})()")
        self.assertIn(ms, [x["id"] for x in self.rows()], "the last day of the window counts")
        self.b.eval(f"(()=>{{ const m=msFind({ms!r}).m; m[6]='Done'; renderToday(); }})()")
        self.assertNotIn(ms, [x["id"] for x in self.rows()], "an achieved milestone: no row")


class At900(Seeded):
    width = 900

    def test_the_rows_fit_at_900(self):
        self.today()
        self.assertEqual(len(self.rows()), 3)
        o = self.b.eval("""(()=>{ const s=document.getElementById('attnSec'), li=document.querySelector('#attnList li[data-msattn]');
          return {page:document.documentElement.scrollWidth<=innerWidth, sec:s.scrollWidth<=s.clientWidth+1,
                  inside:li.getBoundingClientRect().right<=s.getBoundingClientRect().right+1}; })()""")
        self.assertEqual(o, {"page": True, "sec": True, "inside": True})


if __name__ == "__main__":
    unittest.main()
