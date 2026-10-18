"""BL-337 (v2.1.0 P9): the reporting space and the Reports page, as drawn in the "Reporting journey" mockup, in a real browser
against the live server.

- Reports in the left menu, between Projects and People, with a count of the projects that need Alan this week.
- The Reports page: one row per project (health, the internal report's state, each client's report), Needs me or All projects,
  the week control, Open to that project's reporting space.
- The Reporting hub (#reporting=ABC&w=…, #221 H1: it replaced the reporting space, the weekly page and the client page; its own tests are
  test_reporting_hub.py): Open on a project's row goes to it, the week Menu lists the weeks, the older addresses open it.
- The cockpit's Reporting card; Today's Friday reminder opens the project's week in the hub; ⌘K reaches Reports and each project's hub.
- The week is the reminder's (Friday from 12:00); a draft waiting in Review and the report records (D.reports, the stub for
  P3's) change a state.

Stubbed on this base (dev/sprints/v210-contract.md, P1 to P3 are Team Cap's): the report records, more than one client per project,
the report views (P6 and P8 are linked by address; they open once those merge), and Approve and Export (disabled).

Run: python3 dev/tests/test_reports_page.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_dashboard  # noqa: E402
from live_browser import LiveBrowserCase, pin_page_clock  # noqa: E402
from test_tracker import ABC  # noqa: E402

FIXED = date(2026, 10, 16)                      # a Friday
NOW = f"{FIXED} 14:00"                          # after the reminder's 12:00, so this week is the one ending today
test_dashboard.TODAY = FIXED
DEF = "projects/DEF Digital Enablement"


class ReportsPage(LiveBrowserCase):
    shared_server = True
    width, height = 1400, 1000

    @classmethod
    def load(cls, v):
        test_dashboard.populate(v)
        # ABC: last week's internal report filed, none for this week; its client report was 15 days ago (fortnightly, so due).
        # DEF: both reports filed for this week, so it does not need Alan.
        for rel in (f"{ABC}/reports/2026-10-09 Weekly report - Example Programme.docx",
                    f"{DEF}/reports/2026-10-16 Weekly report - Digital Enablement.docx",
                    f"{DEF}/reports/2026-10-16 Client report - Digital Enablement.docx"):
            (v.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (v.root / rel).write_bytes(b"r")
        v.run(script="build_dashboard.py")

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": NOW, "TZ": "UTC"}

    def setUp(self):
        super().setUp()
        pin_page_clock(self.b, NOW)
        self.b.eval("go('today')")

    def go_reports(self):
        self.b.eval("go('reports')")
        self.b.wait("!!document.querySelector('#v-reports tbody tr')")

    def cells(self, sel):
        return self.b.eval(f"[...document.querySelectorAll({sel!r})].map(e=>e.textContent.trim().replace(/\\s+/g,' '))")

    # ----- the week and the states

    def test_the_week_is_the_reminders(self):
        b = self.b
        self.assertEqual(b.eval("thisWeek('2026-10-16','12:00')"), "2026-10-16")
        self.assertEqual(b.eval("thisWeek('2026-10-16','11:59')"), "2026-10-09")
        self.assertEqual(b.eval("thisWeek('2026-10-13','09:00')"), "2026-10-09")
        self.assertEqual(b.eval("thisWeek('2026-10-17','09:00')"), "2026-10-16")

    def test_states_from_the_filed_files_and_a_draft_in_review(self):
        b = self.b
        st = b.eval("(()=>{ const a=weekView('ABC'), d=weekView('DEF'), o=weekView('ABC','2026-10-09');"
                    "return [a.internal.key,a.clients[0].state.key,a.needs,d.internal.key,d.clients[0].state.key,d.needs,o.internal.key,o.clients[0].state.key]; })()")
        self.assertEqual(st, ["due", "due", True, "filed", "filed", False, "filed", "notdue"])
        # a weekly report waiting in Review is a draft
        b.eval("REV.push({n:900,kind:'draft',ref:'report',p:'ABC',done:false,rec:{t:'Weekly report: Example Programme'}})")
        self.assertEqual(b.eval("weekView('ABC').internal.key"), "draft")
        b.eval("REV.pop()")
        # the stub for P3's records: D.reports
        b.eval("D.reports=[{project:'ABC',kind:'weekly',date:'2026-10-16',state:'approved',edited:'today 14:20'}]")
        self.assertEqual(b.eval("[weekView('ABC').internal.key, weekView('ABC').internal.label, weekView('ABC').internal.edited]"),
                         ["approved", "Approved", "today 14:20"])
        b.eval("D.reports=[]")

    # ----- the menu

    def test_reports_sits_between_projects_and_people_with_a_count(self):
        b = self.b
        titles = self.cells(".rail [data-v] .rl")
        self.assertLess(titles.index("Projects"), titles.index("Reports"))
        self.assertLess(titles.index("Reports"), titles.index("People"))
        self.assertEqual(b.eval("document.getElementById('repBadge').textContent"), "1")                      # ABC needs Alan; DEF is filed
        self.assertIn("1 project with a report to check", b.eval("document.getElementById('repBadge').getAttribute('aria-label')"))

    def test_the_menu_button_opens_reports_and_marks_it(self):
        b = self.b
        b.eval("document.querySelector('.rail [data-v=reports]').click()")
        b.wait("VIEW==='reports' && !document.getElementById('v-reports').hidden")
        self.assertEqual(b.eval("document.querySelector('.rail [aria-current=page]').dataset.v"), "reports")
        self.assertEqual(b.eval("location.hash"), "#reports")
        self.assertEqual(b.eval("document.title"), "creaite · Reports")

    # ----- the Reports page

    def test_needs_me_and_all_projects(self):
        b = self.b
        self.go_reports()
        self.assertEqual(self.cells("#v-reports tbody tr td:first-child"), ["Example Programme"])
        self.assertEqual(b.eval("document.getElementById('rpSummary').textContent"),
                         "1 internal report to check · 1 client report due")
        b.eval("document.querySelector('[data-rpf=all]').click()")
        b.wait("document.querySelectorAll('#v-reports tbody tr').length===2")
        self.assertEqual(self.cells("#v-reports tbody tr td:first-child"), ["Example Programme", "Digital Enablement"])
        row = self.cells("#v-reports tbody tr:last-child td")
        self.assertIn("Filed", row[2])
        self.assertIn("Filed", row[3])
        b.eval("document.querySelector('[data-rpf=need]').click()")
        b.wait("document.querySelectorAll('#v-reports tbody tr').length===1")

    def test_an_earlier_week_one_click_back(self):
        b = self.b
        self.go_reports()
        b.eval("document.querySelector('[data-rpweek=\"2026-10-09\"]').click()")
        b.wait("location.hash.includes('w=2026-10-09')")
        self.assertIn("Week ending 09-10-2026", b.eval("document.querySelector('#v-reports .sub').textContent"))
        b.eval("document.querySelector('[data-rpf=all]').click()")
        row = self.cells("#v-reports tbody tr:first-child td")
        self.assertIn("Filed", row[2])                                                 # ABC's report for last week
        self.assertIn("Not due (fortnightly)", row[3])
        b.reload("typeof go==='function' && LIVE")                                     # the address keeps the week
        b.eval("go('reports')")

    def test_open_goes_to_the_projects_reporting_hub(self):
        b = self.b
        self.go_reports()
        b.eval("document.querySelector('[data-rpopen=ABC]').click()")
        b.wait("VIEW==='reporting' && !!document.querySelector('#v-reporting .page')", 25)
        self.assertEqual(b.eval("location.hash"), "#reporting=ABC")
        self.assertEqual(b.eval("document.title"), "creaite · Example Programme reporting")
        self.assertEqual(b.eval("document.querySelector('.rail [aria-current=page]').dataset.v"), "projects")

    # ----- the reporting hub (the old reporting space is gone)

    def space(self, week=""):
        self.b.eval(f"openSpace('ABC'{', ' + repr(week) if week else ''})")
        self.b.wait("VIEW==='reporting' && !!document.querySelector('#v-reporting .page')", 25)

    def test_the_hub_week_menu_lists_the_weeks_with_both_reports_states(self):
        b = self.b
        self.space()
        b.click("#hubWeek")
        b.wait("document.querySelector('.wkpop')")
        rows = b.eval("[...document.querySelectorAll('.wkpop .wkrow')].map(r=>[r.dataset.w, r.innerText.replace(/\\s+/g,' ')])")
        self.assertEqual([r[0] for r in rows][:2], ["2026-10-16", "2026-10-09"])
        self.assertGreaterEqual(len(rows), 4)
        self.assertIn("Internal:", rows[0][1])
        self.assertIn("Client:", rows[0][1])
        self.assertIn("Internal: filed", rows[1][1])                                 # last week's report is filed
        self.assertIn("Client: not due (fortnightly)", rows[1][1])

    def test_the_hub_opens_an_earlier_week_from_its_address(self):
        b = self.b
        self.space("2026-10-09")
        self.assertIn("09-10-2026", b.eval("document.querySelector('#hubWeek').innerText"))
        self.assertIn("w=2026-10-09", b.eval("location.hash"))

    def test_the_old_links_are_hub_addresses(self):
        b = self.b
        self.assertEqual(b.eval("weeklyHref('ABC','2026-10-16')"), "#reporting=ABC&w=2026-10-16")
        self.assertEqual(b.eval("clientReportHref('ABC','2026-10-16','Example Client Ltd')"), "#reporting=ABC&w=2026-10-16&v=client")

    def test_the_address_reopens_the_same_place(self):
        b = self.b
        b.eval("location.hash='#reporting=ABC&w=2026-10-09&e=client'")      # an older address keeps working; the old view letter is dropped
        b.reload("typeof go==='function' && LIVE")
        b.wait("VIEW==='reporting' && !!document.querySelector('#v-reporting .page')", 25)
        self.assertEqual(b.eval("[spaceCode.value, spaceWeek.value]"), ["ABC", "2026-10-09"])
        self.assertEqual(b.eval("location.hash.includes('e=')"), False)

    # ----- the other ways in

    def test_the_cockpit_has_a_reporting_card_that_opens_the_hub(self):
        b = self.b
        b.eval("go('cockpit','ABC')")
        b.wait("!!document.querySelector('#cockRep #repCard')")
        text = b.eval("document.getElementById('repCard').textContent")
        for want in ("Reporting", "Weekly report", "Client report", "Example Client Ltd", "Fortnightly"):
            self.assertIn(want, text)
        b.eval("document.querySelector('[data-rpcard=space]').click()")
        b.wait("VIEW==='reporting' && !!document.querySelector('#v-reporting .page')", 25)
        b.eval("go('cockpit','ABC')")
        b.wait("!!document.querySelector('#cockRep #repCard')")
        self.assertEqual(b.eval("document.querySelector('[data-rpcard=internal]').getAttribute('href')"), "#reporting=ABC&w=2026-10-16")
        self.assertEqual(b.eval("document.querySelector('[data-rpcard=client]').getAttribute('href')"),
                         "#reporting=ABC&w=2026-10-16&v=client")

    def test_a_filed_report_opens_its_file_from_the_card(self):
        b = self.b
        b.eval("go('cockpit','DEF')")
        b.wait("!!document.querySelector('#cockRep #repCard')")
        self.assertEqual(b.eval("document.querySelectorAll('#repCard a[data-openfile]').length"), 2)

    def test_the_friday_reminder_opens_the_projects_week_in_the_hub(self):
        b = self.b
        b.eval("go('today')")
        b.wait("!!document.querySelector('#v-today li.rem[data-id^=\"weekly:\"]')")
        self.assertEqual(b.eval("document.querySelector('#v-today li.rem[data-id^=\"weekly:\"] a.t').dataset.rphub"), "ABC|2026-10-16")
        b.eval("document.querySelector('#v-today li.rem[data-id^=\"weekly:\"] a.t').click()")
        b.wait("VIEW==='reporting' && !!document.querySelector('#v-reporting .page')", 25)
        self.assertIn("16-10-2026", b.eval("document.querySelector('#hubWeek').innerText"))

    def test_command_k_reaches_reports_and_the_hub(self):
        b = self.b
        items = b.eval("ckItems('').filter(x=>x.g==='Go to').map(x=>[x.l,x.h])")
        self.assertIn(["Reports", "1 needs you"], items)
        found = b.eval("ckItems('weekly report ABC').filter(x=>x.g==='Reporting').map(x=>x.l)")
        self.assertEqual(found, ["Weekly report: Example Programme", "Reporting: Example Programme"])
        b.eval("ckItems('reporting').find(x=>x.g==='Reporting').fn()")
        b.wait("VIEW==='reporting'")
        self.assertEqual(b.eval("spaceCode.value"), "ABC")

    def test_command_k_client_report_opens_the_hubs_client_view(self):
        b = self.b
        self.assertEqual(b.eval("ckItems('client report ABC').filter(x=>x.g==='Reporting').map(x=>x.l)"),
                         ["Reporting: Example Programme", "Client report: Example Programme"])
        b.eval("ckItems('client report ABC').find(x=>x.l==='Client report: Example Programme').fn()")
        b.wait("VIEW==='reporting' && !!document.querySelector('#v-reporting .page')", 25)
        self.assertEqual(b.eval("document.querySelector('#v-reporting .page').dataset.audience"), "client")

    def test_nothing_scrolls_sideways_at_900(self):
        b = self.b
        b.resize(900, 900)
        for js in ("go('reports')", "openSpace('ABC')"):
            b.eval(js)
            b.pump(1.0)
            self.assertLessEqual(b.eval("document.documentElement.scrollWidth - innerWidth"), 0, js)


if __name__ == "__main__":
    unittest.main()
