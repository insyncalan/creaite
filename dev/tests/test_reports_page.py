"""BL-337 (v2.1.0 P9): the reporting space and the Reports page, as drawn in the "Reporting journey" mockup, in a real browser
against the live server.

- Reports in the left menu, between Projects and People, with a count of the projects that need Alan this week.
- The Reports page: one row per project (health, the internal report's state, each client's report), Needs me or All projects,
  the week control, Open to that project's reporting space.
- The reporting space (#reporting=ABC&w=…&e=…): weeks down the left, the internal and client reports as cards, Edit both side
  by side, the week's files; the three views switch without leaving the page and the address keeps them.
- The cockpit's Reporting card; Today's Friday reminder points at Reports; ⌘K reaches Reports and each project's space.
- The week is the reminder's (Friday from 12:00); a draft waiting in Review and the report records (D.reports, the stub for
  P3's) change a state.

Stubbed on this base (dev/sprints/v210-contract.md, P1 to P3 are Team Cap's): the report records, more than one client per project,
the report editor itself (the outline page), and Approve and Export (disabled).

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

    def test_open_goes_to_the_projects_reporting_space(self):
        b = self.b
        self.go_reports()
        b.eval("document.querySelector('[data-rpopen=ABC]').click()")
        b.wait("VIEW==='reporting' && !!document.querySelector('#v-reporting .rp-card')")
        self.assertEqual(b.eval("location.hash"), "#reporting=ABC")
        self.assertEqual(b.eval("document.title"), "creaite · Example Programme reporting")
        self.assertEqual(b.eval("document.querySelector('.rail [aria-current=page]').dataset.v"), "projects")

    # ----- the reporting space

    def space(self, hash_=""):
        self.b.eval(f"openSpace('ABC'{hash_})")
        self.b.wait("VIEW==='reporting' && !!document.querySelector('#v-reporting .rp-card')")

    def test_the_space_lists_weeks_and_both_reports_as_cards(self):
        b = self.b
        self.space()
        weeks = self.cells("#v-reporting .rp-wk .l")
        self.assertEqual(weeks[:2], ["Week ending 16-10-2026", "Week ending 09-10-2026"])
        self.assertEqual(len(weeks), 4)
        cards = self.cells("#v-reporting .rp-card .top")
        self.assertEqual(cards, ["Weekly reportInternalNot drafted", "Client reportExample Client LtdDue"])
        self.assertTrue(b.eval("[...document.querySelectorAll('#v-reporting .rp-card .btn')].some(x=>x.textContent==='Approve' && x.disabled)"))
        self.assertIn("Approve the internal report first", b.eval("document.querySelector('#v-reporting .rp-card:nth-child(2)').textContent"))
        self.assertIn("Nothing filed yet", b.eval("document.querySelector('#v-reporting .rp-files').textContent"))

    def test_an_earlier_week_shows_its_files_and_a_client_not_due(self):
        b = self.b
        self.space()
        b.eval("document.querySelector('[data-week=\"2026-10-09\"]').click()")
        b.wait("document.querySelector('#v-reporting .rp-files a[data-openfile]')")
        self.assertIn("Weekly report - Example Programme.docx", b.eval("document.querySelector('#v-reporting .rp-files').textContent"))
        self.assertIn("is fortnightly; no client report was due this week",
                      b.eval("document.querySelector('#v-reporting .rp-card:nth-child(2)').textContent"))
        self.assertIn("w=2026-10-09", b.eval("location.hash"))

    def test_edit_both_switches_views_without_leaving_the_page(self):
        b = self.b
        self.space()
        b.eval("[...document.querySelectorAll('#v-reporting .rp-both .btn')].find(x=>x.textContent==='Edit both').click()")
        b.wait("!!document.querySelector('#v-reporting .rp-ed')")
        self.assertIn("e=side", b.eval("location.hash"))
        self.assertEqual(b.eval("document.querySelectorAll('#v-reporting .rp-sheet').length"), 2)
        self.assertTrue(b.eval("!!document.querySelector('#v-reporting .rp-diff')"))                    # ≠ Client on the internal page
        for mode, n in (("internal", 1), ("client", 1), ("side", 2)):
            b.eval(f"document.querySelector('[data-rpmode={mode}]').click()")
            b.wait(f"document.querySelectorAll('#v-reporting .rp-sheet').length=={n}")
            self.assertIn(f"e={mode}", b.eval("location.hash"))
            self.assertEqual(b.eval("VIEW"), "reporting")
        self.assertTrue(b.eval("[...document.querySelectorAll('#v-reporting .rp-ebar .btn')].every(x=>x.disabled)"))
        b.eval("history.back()")
        b.wait("!!document.querySelector('#v-reporting .rp-ed') && location.hash.includes('e=client')")

    def test_the_address_reopens_the_same_place(self):
        b = self.b
        b.eval("location.hash='#reporting=ABC&w=2026-10-09&e=client'")
        b.reload("typeof go==='function' && LIVE")
        b.wait("VIEW==='reporting' && !!document.querySelector('#v-reporting .rp-ed')")
        self.assertEqual(b.eval("[spaceCode.value, spaceWeek.value, spaceEdit.value]"), ["ABC", "2026-10-09", "client"])
        self.assertEqual(b.eval("document.querySelector('[data-rpmode=client]').getAttribute('aria-pressed')"), "true")
        self.assertIn("Week ending 09-10-2026", b.eval("document.querySelector('#v-reporting .crumb').textContent"))

    # ----- the other ways in

    def test_the_cockpit_has_a_reporting_card_that_opens_the_space(self):
        b = self.b
        b.eval("go('cockpit','ABC')")
        b.wait("!!document.querySelector('#cockRep #repCard')")
        text = b.eval("document.getElementById('repCard').textContent")
        for want in ("Reporting", "Weekly report", "Client report", "Example Client Ltd", "Fortnightly"):
            self.assertIn(want, text)
        b.eval("document.querySelector('[data-rpcard=space]').click()")
        b.wait("VIEW==='reporting' && !!document.querySelector('#v-reporting .rp-card')")
        b.eval("go('cockpit','ABC')")
        b.wait("!!document.querySelector('#cockRep #repCard')")
        b.eval("document.querySelector('[data-rpcard=internal]').click()")                 # Open goes straight to that report
        b.wait("VIEW==='reporting' && !!document.querySelector('#v-reporting .rp-ed')")
        self.assertIn("e=internal", b.eval("location.hash"))

    def test_a_filed_report_opens_its_file_from_the_card(self):
        b = self.b
        b.eval("go('cockpit','DEF')")
        b.wait("!!document.querySelector('#cockRep #repCard')")
        self.assertEqual(b.eval("document.querySelectorAll('#repCard a[data-openfile]').length"), 2)

    def test_the_friday_reminder_points_to_reports(self):
        b = self.b
        b.eval("go('today')")
        b.wait("!!document.querySelector('#v-today li.rem[data-id^=\"weekly:\"]')")
        self.assertEqual(b.eval("document.querySelector('#v-today li.rem[data-id^=\"weekly:\"] a.t').dataset.go"), "reports")

    def test_command_k_reaches_reports_and_the_space(self):
        b = self.b
        items = b.eval("ckItems('').filter(x=>x.g==='Go to').map(x=>[x.l,x.h])")
        self.assertIn(["Reports", "1 needs you"], items)
        found = b.eval("ckItems('weekly report ABC').filter(x=>x.g==='Reporting').map(x=>x.l)")
        self.assertEqual(found, ["Reporting: Example Programme"])
        b.eval("ckItems('reporting').find(x=>x.g==='Reporting').fn()")
        b.wait("VIEW==='reporting'")
        self.assertEqual(b.eval("spaceCode.value"), "ABC")

    def test_the_client_view_is_linked_by_p8s_address(self):
        # P8's #client-report=CODE/week/client is not on this base: only the links are checked here
        b = self.b
        self.space()
        self.assertEqual(b.eval("document.querySelector('[data-clientreport]').getAttribute('href')"),
                         "#client-report=ABC/2026-10-16/Example%20Client%20Ltd")
        self.assertEqual(b.eval("ckItems('client report ABC').filter(x=>x.g==='Reporting').map(x=>x.l)"),
                         ["Reporting: Example Programme", "Client report: Example Programme"])

    def test_nothing_scrolls_sideways_at_900(self):
        b = self.b
        b.resize(900, 900)
        for js in ("go('reports')", "openSpace('ABC')", "openSpace('ABC','','side')"):
            b.eval(js)
            b.pump(0.4)
            self.assertLessEqual(b.eval("document.documentElement.scrollWidth - innerWidth"), 0, js)


if __name__ == "__main__":
    unittest.main()
