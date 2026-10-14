"""BL-126 (sprint prep-files): what the meeting prep page and popup show.

Run: python3 dev/tests/test_prep_page_content.py   (the last class needs Google Chrome; skipped otherwise)

  - only Urgent, overdue and due-soon work is listed, in the stated order, with "n other open items are not listed";
  - the reporting block shows health as a word and icon, the headline, at most five points and a closed disclosure;
  - up to three recent report links (weekly, client, steering one-pager), newest first, none for a missing file;
  - the page stays one self-contained file;
  - the popup lists the same reports; #openfile= opens an allowed path once and clears the address.
"""
import json
import re
import subprocess
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
from live_browser import LiveBrowserCase  # noqa: E402
from test_decisions_prep import prep_world  # noqa: E402
from test_tracker import ABC, Vault, action  # noqa: E402
import build_dashboard as bd  # noqa: E402
import prep_page  # noqa: E402

TODAY = date.today()


def d(n):
    return (TODAY + timedelta(days=n)).isoformat()


class Pool(unittest.TestCase):
    """select_items on its own: the rule and the order."""

    def act(self, i, due=None, pr="Medium", st="Open"):
        return ("actions", {"id": f"ABC-A-{i:03d}", "p": "ABC", "t": f"Action {i}", "due": due, "pr": pr, "st": st})

    def test_urgent_overdue_and_due_soon_in_that_order(self):
        pool = [self.act(1, d(5)), self.act(2, None, "Urgent"), self.act(3, d(-10)), self.act(4, d(2)), self.act(5, d(-2), "Urgent"),
                self.act(6, d(40), "Urgent"), self.act(7, None), self.act(8, d(30)), self.act(9, d(7))]
        chosen, universe = prep_page.select_items(pool, TODAY.isoformat(), 7)
        self.assertEqual([x["id"][-1] for _, x in chosen], ["3", "5", "4", "1", "9", "6", "2"])   # overdue (oldest first), due soonest, Urgent far, Urgent undated
        self.assertEqual(universe, 9)                                                              # 2 are not listed: undated Medium, due in 30 days

    def test_the_due_soon_setting_moves_the_edge(self):
        pool = [self.act(1, d(5)), self.act(2, d(1))]
        self.assertEqual([x["id"][-1] for _, x in prep_page.select_items(pool, TODAY.isoformat(), 2)[0]], ["2"])
        self.assertEqual([x["id"][-1] for _, x in prep_page.select_items(pool, TODAY.isoformat(), 7)[0]], ["2", "1"])

    def test_an_overdue_item_is_judged_from_the_meetings_day(self):
        pool = [self.act(1, d(0))]
        self.assertEqual(len(prep_page.select_items(pool, d(1), 7)[0]), 1)                         # due today is overdue by tomorrow's meeting

    def test_decisions_needed_when_due_soon_and_to_revisit_when_the_date_has_come(self):
        day = TODAY.isoformat()
        dec = lambda i, **v: ("decisions", {"id": f"ABC-D-{i:03d}", "p": "ABC", "t": f"Decision {i}", "st": "Pending", **v})   # noqa: E731
        pool = [dec(1, due=d(-3)), dec(2), dec(3, due=d(20)), dec(4, due=d(3)),
                dec(5, st="Made", revisit=d(-1)), dec(6, st="Made", revisit=d(30)), dec(7, st="Made", date=d(-2))]
        chosen, universe = prep_page.select_items(pool, day, 7)
        self.assertEqual([x["id"][-1] for _, x in chosen], ["1", "5", "4"])
        self.assertEqual(universe, 5)                                                              # four pending and one to revisit; made ones aren't open


class Render(unittest.TestCase):
    def ctx(self, **v):
        base = {"key": "09:00|ABC weekly", "day": TODAY.isoformat(), "project": "ABC", "project_name": "Example Programme", "port": 8765,
                "meeting": {"title": "ABC weekly", "start": "09:00", "end": "10:00", "where": "Teams", "attendees": [], "confidential": False},
                "items": [], "not_listed": 0, "due_soon_days": 7, "reporting": [], "reports": []}
        base.update(v)
        return base

    def item(self, i, **v):
        return {"table": "actions", "id": f"ABC-A-{i:03d}", "p": "ABC", "text": f"Action {i}", "type": "Action", "owner": "Jane Doe",
                "due": d(-1), "priority": "Urgent", "status": "Open", "workstream": "", "milestone": "", "why": "", **v}

    STATE = ("**At risk for go-live: UAT data is six days late.**\n\n"
             + "\n".join(f"- **Point {i}.** The {i}th thing <b>matters</b>." for i in range(1, 8)) + "\n\nAnd a closing paragraph.")

    def reporting(self, code="ABC", name="Example Programme", health="At risk", state=None):
        return {"project": code, "name": name, "health": health, "health_reason": "Data late", "current_state": self.STATE if state is None else state,
                "update": {"week_ending": "2026-10-02", "health": health, "summary": "Data access is late. " * 30},
                "weekly_report": None}

    def test_the_work_table_lists_what_it_is_given_and_says_how_many_are_left_out(self):
        html = prep_page.render(self.ctx(items=[self.item(1), self.item(2)], not_listed=14), {})
        self.assertIn("ABC-A-001", html)
        self.assertIn("14 other open items are not listed", html)
        self.assertRegex(html, r'href="http://127\.0\.0\.1:8765/#work=actions&p=ABC"')
        self.assertIn("1 other open item is not listed", prep_page.render(self.ctx(items=[self.item(1)], not_listed=1), {}))
        self.assertNotIn("not listed", prep_page.render(self.ctx(items=[self.item(1)], not_listed=0), {}))

    def test_nothing_urgent_says_so_instead_of_an_empty_table(self):
        html = prep_page.render(self.ctx(not_listed=3), {})
        self.assertIn("Nothing is Urgent, overdue or due in the next 7 days", html)
        self.assertNotIn("<table", html)
        self.assertIn("3 other open items are not listed", html)

    def test_the_portfolio_link_has_no_project(self):
        html = prep_page.render(self.ctx(project="_portfolio", items=[self.item(1)], not_listed=2), {})
        self.assertRegex(html, r'href="http://127\.0\.0\.1:8765/#work=actions"')

    def test_the_reporting_block_has_health_headline_five_points_and_a_closed_disclosure(self):
        html = prep_page.render(self.ctx(reporting=[self.reporting()]), {})
        block = html[html.index('class="rep"'):]
        self.assertRegex(block, r'class="health warnh"><span aria-hidden="true">▲</span> At risk')       # a word and an icon, not colour alone
        self.assertIn("as of 02-10-2026", block)
        self.assertIn('<p class=headline><strong>At risk for go-live: UAT data is six days late.</strong></p>', block)
        points = re.search(r'<ul class="points">(.*?)</ul>', block, re.S).group(1)
        self.assertEqual(points.count("<li>"), 5)
        self.assertIn("<strong>Point 1.</strong>", points)                                                # the bold lead-ins are kept
        self.assertNotIn("Point 6", points)
        full = re.search(r'<details class="full">(.*?)</details>', block, re.S)
        self.assertTrue(full and "Show the full current state" in full.group(1))
        self.assertNotIn("open", re.search(r'<details class="full"[^>]*>', block).group(0))               # closed by default
        self.assertIn("Point 7", full.group(1))                                                           # the rest is behind it
        self.assertIn("And a closing paragraph.", full.group(1))
        self.assertNotIn("<b>matters</b>", block)                                                         # everything is escaped
        self.assertIn("&lt;b&gt;matters&lt;/b&gt;", block)
        upd = re.search(r'<p class="upd">(.*?)</p>', block, re.S).group(1)
        self.assertLess(len(upd), 360)                                                                    # the weekly update is a line or two
        self.assertTrue(upd.endswith("…"))

    def test_each_health_word_has_its_own_icon(self):
        for health, icon in (("On track", "✔"), ("At risk", "▲"), ("Off track", "✖")):
            html = prep_page.render(self.ctx(reporting=[self.reporting(health=health)]), {})
            self.assertIn(f'<span aria-hidden="true">{icon}</span> {health}', html)

    def test_a_project_with_no_reporting_says_so(self):
        r = {"project": "ABC", "name": "Example Programme", "health": "", "health_reason": "", "current_state": "", "update": None, "weekly_report": None}
        self.assertIn("No reporting recorded yet.", prep_page.render(self.ctx(reporting=[r]), {}))

    def test_a_portfolio_meeting_gets_a_compact_block_for_each_project(self):
        html = prep_page.render(self.ctx(project="_portfolio", project_name="", reporting=[
            self.reporting("ABC", "Example Programme"), self.reporting("DEF", "Digital Enablement", "On track")]), {})
        self.assertEqual(html.count('<section class="proj">'), 2)
        for sect in re.findall(r'<section class="proj">(.*?)</section>', html, re.S):
            self.assertIn("<p class=headline>", sect)
            more = re.search(r'<details class=more>(.*?)</details>', sect, re.S).group(1)
            self.assertIn('<ul class="points">', more)                                                    # the points are behind the disclosure
            self.assertNotIn('<ul class="points">', sect.replace(more, ""))

    def reports(self):
        p = "projects/ABC Example Programme/reports/"
        return [{"p": "ABC", "kind": "Weekly report", "date": "2026-10-09", "name": "2026-10-09 Weekly report - Example Programme.docx",
                 "path": p + "2026-10-09 Weekly report - Example Programme.docx", "online": False},
                {"p": "ABC", "kind": "Client report", "date": "2026-10-02", "name": "2026-10-02 Client report - Example Programme.docx",
                 "path": p + "2026-10-02 Client report - Example Programme.docx", "online": False},
                {"p": "ABC", "kind": "Steerco one-pager", "date": "2026-09-30", "name": "2026-09-30 Example Programme Steerco one-pager.docx",
                 "path": p + "Steerco/2026-09-30 Example Programme Steerco one-pager.docx", "online": True}]

    def test_the_page_links_the_recent_reports_through_the_dashboard(self):
        html = prep_page.render(self.ctx(reporting=[self.reporting()], reports=self.reports()), {})
        self.assertIn("Recent reports", html)
        self.assertIn('href="http://127.0.0.1:8765/#openfile=projects/ABC%20Example%20Programme/reports/2026-10-09%20Weekly%20report%20-%20Example%20Programme.docx"', html)
        order = [html.index(k) for k in ("Weekly report <", "Client report <", "Steerco one-pager")]
        self.assertEqual(order, sorted(order))                                                            # newest first
        self.assertRegex(html, r'Client report <span class="tag">for the client</span>')                  # marked as such
        self.assertIn("unavailable: the file is online-only", html)                                       # an online-only file is not linked
        self.assertNotIn("Steerco%20one-pager.docx", html)
        self.assertIn("needs the live server to be running", html)

    def test_the_page_is_one_self_contained_file(self):
        html = prep_page.render(self.ctx(items=[self.item(1)], reporting=[self.reporting()], reports=self.reports()), {})
        self.assertNotRegex(html, r"<script|<link|<img|@import|src=")
        self.assertEqual(len(re.findall(r"url\(", html)), 0)
        self.assertIn("@media print", html)
        self.assertIn("Internal", html)


class Vaulted(unittest.TestCase):
    """The context and the prep data from a real (throwaway) vault."""

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        prep_world(cls.v)
        src = f"{ABC}/minutes/{d(-5)} Steering.docx — Actions"
        cls.v.propose("more", [
            action(30, description="Overdue ten days", due_date=d(-10), priority="Medium", source=src),
            action(31, description="Due in five days", due_date=d(5), priority="Medium", source=src),
            action(32, description="Due in forty days", due_date=d(40), priority="Medium", source=src),
            action(33, description="Urgent, no date", priority="Urgent", source=src),
            action(34, description="Medium, no date", priority="Medium", source=src)])
        cls.v.run("apply")
        reports = cls.v.root / ABC / "reports"
        (reports / "Steerco").mkdir(parents=True, exist_ok=True)
        for name in ("2026-10-02 Weekly report - Example Programme.docx", "2026-10-09 Weekly report - Example Programme.docx",
                     "2026-10-01 Client report - Example Programme.docx", "2026-10-08 Ad hoc actions register.docx",
                     "Steerco/2026-09-30 Example Programme Steerco one-pager.docx"):
            (reports / name).write_bytes(b"x")

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def context(self):
        r = self.v.run("context", "09:00|ABC weekly", script="prep_page.py")
        return json.loads(r.stdout[r.stdout.index("{"):])

    def test_only_urgent_overdue_and_due_soon_work_is_listed_in_order(self):
        ctx = self.context()
        texts = [i["text"] for i in ctx["items"]]
        self.assertNotIn("Due in forty days", texts)
        self.assertNotIn("Medium, no date", texts)                                                                 # undated and not Urgent
        self.assertLess(texts.index("Overdue ten days"), texts.index("Escalate data access to the client CIO"))      # oldest overdue first
        self.assertLess(texts.index("Escalate data access to the client CIO"), texts.index("Book UAT environment"))   # overdue before due soon
        self.assertLess(texts.index("Book UAT environment"), texts.index("Due in five days"))                         # due soonest first
        self.assertLess(texts.index("Due in five days"), texts.index("Urgent, no date"))                              # Urgent with no date last
        self.assertEqual(ctx["not_listed"], self.universe(ctx) - len(ctx["items"]))
        self.assertGreaterEqual(ctx["not_listed"], 2)                                                              # forty days, Medium no date, and more
        self.assertEqual(ctx["due_soon_days"], 7)

    def universe(self, ctx):
        con = __import__("sqlite3").connect(self.v.root / "system/tracker.db")
        n = lambda sql: con.execute(sql).fetchone()[0]                                                              # noqa: E731
        open_n = (n("SELECT count(*) FROM actions WHERE project='ABC' AND status IN ('Open','Delayed')")
                  + n("SELECT count(*) FROM raid WHERE project='ABC' AND status='Open'")
                  + n("SELECT count(*) FROM decisions WHERE project='ABC' AND status='Pending'")
                  + n(f"SELECT count(*) FROM decisions WHERE project='ABC' AND status='Made' AND revisit <= '{TODAY.isoformat()}'"))
        con.close()
        return open_n

    def test_the_setting_sets_what_due_soon_means(self):
        f = self.v.root / "system/config/settings.json"
        old = f.read_text(encoding="utf-8")
        try:
            cfg = json.loads(old)
            cfg.setdefault("review", {})["due_soon_days"] = 2
            f.write_text(json.dumps(cfg), encoding="utf-8")
            texts = [i["text"] for i in self.context()["items"]]
            self.assertNotIn("Due in five days", texts)
            self.assertNotIn("Book UAT environment", texts)                                                        # due in three days
            self.assertIn("Overdue ten days", texts)
        finally:
            f.write_text(old, encoding="utf-8")

    def test_the_prep_data_carries_up_to_three_reports_newest_first(self):
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/build_dashboard.py")], capture_output=True, text=True, cwd=self.v.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        html = (self.v.root / "dashboard.html").read_text(encoding="utf-8")
        data = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))
        reps = data["prep"]["reports"]["ABC"]
        self.assertEqual([(x["kind"], x["date"]) for x in reps],
                         [("Weekly report", "2026-10-09"), ("Client report", "2026-10-01"), ("Steerco one-pager", "2026-09-30")])
        self.assertEqual(len(reps), 3)                                                                              # the ad hoc register and the older weekly report are left out
        self.assertFalse(any("Ad hoc" in x["name"] for x in reps))
        self.assertEqual(data["prep"]["reports"]["DEF"], [])
        ctx = self.context()
        self.assertEqual([x["kind"] for x in ctx["reports"]], [x["kind"] for x in reps])

    def test_a_missing_file_is_not_listed_and_an_online_only_one_is_marked(self):
        listing = [{"p": "ABC", "f": "reports", "sub": "Weekly", "n": "2026-10-09 Weekly report - Gone.docx", "date": "2026-10-09", "mod": "2026-10-09",
                    "path": "projects/ABC Example Programme/reports/2026-10-09 Weekly report - Gone.docx"}]
        self.assertEqual(bd.recent_reports("ABC", listing), [])
        real = self.v.root / ABC / "reports/2026-10-09 Weekly report - Example Programme.docx"
        listing[0].update(n=real.name, path=f"projects/ABC Example Programme/reports/{real.name}")
        saved = (bd.paths.resolve, bd.paths.is_online_only)
        try:
            bd.paths.resolve = lambda rel: real
            bd.paths.is_online_only = lambda p: True
            self.assertEqual([(x["kind"], x["online"]) for x in bd.recent_reports("ABC", listing)], [("Weekly report", True)])
        finally:
            bd.paths.resolve, bd.paths.is_online_only = saved


class PrepPopup(LiveBrowserCase):
    shared_server = True

    @classmethod
    def load(cls, v):
        prep_world(v)
        reports = v.root / ABC / "reports"
        (reports / "Steerco").mkdir(parents=True, exist_ok=True)
        for name in ("2026-10-09 Weekly report - Example Programme.docx", "2026-10-01 Client report - Example Programme.docx",
                     "Steerco/2026-09-30 Example Programme Steerco one-pager.docx"):
            (reports / name).write_bytes(b"x")

    def section(self):
        self.b.eval("openPrep(prepTimed()[0])")
        self.b.wait("document.querySelector('#prepBody .prepsec')")
        return self.b.eval("(()=>{ const s=[...document.querySelectorAll('#prepBody .prepsec')].find(s=>/^Recent reports/.test(s.querySelector('h3').textContent)); "
                           "return s?[...s.querySelectorAll('.wlist > div')].map(x=>({text:x.textContent.replace(/\\s+/g,' ').trim(),open:(x.querySelector('[data-openfile]')||{dataset:{}}).dataset.openfile||''})):null; })()")

    def test_the_popup_lists_the_same_reports(self):
        rows = self.section()
        self.assertEqual(len(rows), 3)
        self.assertIn("Weekly report", rows[0]["text"])
        self.assertIn("09-10-2026", rows[0]["text"])
        self.assertIn("Client report", rows[1]["text"])
        self.assertIn("for the client", rows[1]["text"])
        self.assertIn("Steerco one-pager", rows[2]["text"])
        self.assertEqual(rows[0]["open"], "projects/ABC Example Programme/reports/2026-10-09 Weekly report - Example Programme.docx")

    def test_a_row_opens_the_file_through_the_files_pages_call(self):
        self.section()
        self.b.eval("window.CALLS=[]; window.api=async(p,b)=>{ CALLS.push([p,b]); return {ok:true}; }")
        self.b.eval("[...document.querySelectorAll('#prepBody [data-openfile]')][0].click()")
        self.b.wait("CALLS.length===1")
        self.assertEqual(self.b.eval("CALLS[0][0]"), "/api/open")
        self.assertTrue(self.b.eval("CALLS[0][1].path").endswith("2026-10-09 Weekly report - Example Programme.docx"))

    def open_address(self, path):
        self.b.eval("window.CALLS=[]; window.SNACKS=[]; window.api=async(p,b)=>{ CALLS.push([p,b]); return {ok:true}; }; "
                    "if(!window.SNACK0){ window.SNACK0=window.snack; window.snack=m=>{ SNACKS.push(m); return SNACK0(m); }; }")
        self.b.eval(f"location.hash='#openfile='+{json.dumps(path)}")
        self.b.wait("location.hash===''")

    def test_the_address_opens_an_allowed_path_once_and_clears_itself(self):
        self.open_address("projects/ABC%20Example%20Programme/reports/2026-10-09%20Weekly%20report%20-%20Example%20Programme.docx")
        opens = self.b.eval("CALLS.filter(c=>c[0]==='/api/open').map(c=>c[1].path)")       # only /api/open: the page's own polling also goes through api
        self.assertEqual(opens, ["projects/ABC Example Programme/reports/2026-10-09 Weekly report - Example Programme.docx"])
        self.assertEqual(self.b.eval("location.hash"), "")
        self.assertEqual(self.b.eval("SNACKS.length"), 0)

    def test_the_address_refuses_dotdot_and_paths_outside_the_vault(self):
        for bad in ("projects/ABC%20Example%20Programme/../../../etc/passwd", "etc/passwd", "%2Fetc%2Fpasswd", "system/scripts/tracker.py", "projects/", "%E0%A4%A"):
            self.open_address(bad)
            self.assertEqual(self.b.eval("CALLS.filter(c=>c[0]==='/api/open').length"), 0, bad)   # other calls (the page's own polling) don't count
            self.assertEqual(self.b.eval("SNACKS[SNACKS.length-1]"), "Can't open that file", bad)
            self.assertEqual(self.b.eval("location.hash"), "")

    def test_the_server_refuses_a_path_that_does_not_exist_or_climbs(self):
        for bad in ("projects/ABC Example Programme/reports/none.docx", "projects/ABC Example Programme/../../../etc/passwd"):
            r = self.b.eval("fetch('/api/open',{method:'POST',headers:{'Content-Type':'application/json','X-Creaite-Token':D.token||''},"
                            f"body:JSON.stringify({{path:{json.dumps(bad)}}})}}).then(r=>r.status)")
            self.assertEqual(r, 403)

    def test_a_page_opened_on_the_address_does_it_at_start(self):
        self.b.goto(self.base + "/#openfile=projects/ABC%20Example%20Programme/reports/none.docx")
        self.b.wait("typeof go==='function'")
        self.b.wait("location.hash===''")


if __name__ == "__main__":
    unittest.main()
