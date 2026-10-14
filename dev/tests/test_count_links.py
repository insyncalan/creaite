"""BL-190 (sprint-links): every figure that counts work items opens Work, filtered to exactly those items.

For each kind of link the number shown equals the rows Work then lists; a zero is plain text; a link names what it opens,
is reached with the keyboard and works with Enter; a click on a figure doesn't also open the row or card it sits in; Back
returns. A real browser against the real live server, on a throwaway vault with a richer portfolio than the usual one.

Run: python3 dev/tests/test_count_links.py   (needs Google Chrome; skipped otherwise)
"""
import json
import os
import subprocess
import sys
from datetime import date
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import d, new, populate  # noqa: E402
from test_tracker import ABC, action  # noqa: E402

TODAY = date.today()
SRC = f"{ABC}/minutes/{d(-5)} Steering.docx — Actions"


def seed(v):
    """populate()'s ABC and DEF, plus open, delayed, closed and cancelled items raised over several weeks, more risks of each
    priority, an assumption and a dependency, pending decisions and work for a second owner."""
    populate(v)
    a = lambda n, **k: action(n, source=SRC, **k)    # noqa: E731
    r = lambda n, **k: new("raid", n, project=k.pop("project", "ABC"), source=SRC, **k)    # noqa: E731
    v.propose("links", [
        a(1, description="Draft the cut-over plan", owner="Sara Example", due_date=d(-2), raised=d(-3)),
        a(2, description="Confirm the data owner", owner="Sara Example", due_date=d(-6), raised=d(-16), status="Delayed"),
        a(3, description="Order test licences", owner="Sara Example", raised=d(-12), status="Closed", closed=d(-2)),
        a(4, description="Book the old venue", raised=d(-9), status="Cancelled", closed=d(-1)),
        a(5, description="Write the training plan", owner="Omar Ali", raised=d(-40)),
        a(6, description="Agree the UAT exit criteria", owner="Omar Ali", due_date=d(2), raised=d(-1), priority="High"),
        a(7, project="DEF", description="Sign the pilot charter", owner="Sara Example", due_date=d(-1), raised=d(-20)),
        r(8, type="Risk", description="Key tester leaves", impact="High", likelihood="High", owner="Sara Example",
          raised=d(-20), due_date=d(-4)),
        r(9, type="Issue", description="Masked data incomplete", impact="Low", likelihood="Low", raised=d(-2)),
        r(10, type="Assumption", description="Client provides testers", impact="Medium", likelihood="Medium", raised=d(-35)),
        r(11, type="Dependency", description="Network change approved", impact="Medium", likelihood="High", raised=d(-6),
          owner="Omar Ali"),
        r(12, type="Risk", description="Vendor fixes slip", impact="High", likelihood="Medium", raised=d(-15),
          status="Closed", closed=d(-3)),
        new("decisions", 13, project="ABC", decision="Choose the UAT tool", made_by="Sara Example", status="Pending",
            needed_by=d(4), source=SRC),
        new("decisions", 14, project="ABC", decision="Approve the extra tester", made_by="Omar Ali", status="Pending",
            source=SRC),
    ])
    v.run("apply")
    f = v.root / "system/staging/drafts/calendar.json"         # a meeting today, for the prep brief
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"days": {TODAY.isoformat(): [{"id": "s1", "start": "09:00", "end": "10:00", "title": "ABC SteerCo"}]}}))
    env = {**os.environ, "CREAITE_NOW": f"{TODAY} 08:00"}
    subprocess.run([sys.executable, str(v.root / "system/scripts/sweep.py"), "calendar", str(f)], cwd=v.root, check=True, env=env, capture_output=True)
    subprocess.run([sys.executable, str(v.root / "system/scripts/build_dashboard.py")], cwd=v.root, check=True, env=env, capture_output=True)


SHOWN = "(()=>{ const m=/Showing (\\d+) of/.exec(($('#wcount')||{}).textContent||''); return m?+m[1]:-1; })()"


class Links(LiveBrowserCase):
    shared_server = True

    @classmethod
    def load(cls, v):
        seed(v)

    # ---- helpers ----
    def links(self, scope):
        """[{nav, n, label}] for every count link inside scope; n is the figure the link carries (data-n), checked against its text."""
        return self.b.eval(f"[...document.querySelectorAll({scope!r}+' a.cntl[data-nav], '+{scope!r}+' .flk[data-nav]')].map(a=>({{nav:a.dataset.nav, "
                           "n:+(a.dataset.n||-1), label:a.getAttribute('aria-label')||''}))")

    def follow(self, nav, n, back_to=None):
        """Click the link with this data-nav; Work must list exactly n rows; Back returns to back_to (a VIEW)."""
        b = self.b
        sel = json.dumps(f'[data-nav="{nav}"]')
        b.eval(f"document.querySelector({sel}).dispatchEvent(new MouseEvent('click',{{bubbles:true,cancelable:true}}))")
        b.wait("VIEW==='work'")
        b.pump(0.1)
        shown = b.eval(SHOWN)
        self.assertEqual(shown, n, f"{nav}: shown {n}, Work lists {shown}")
        self.assertEqual(b.eval("rows().length"), n, nav)
        if back_to:
            b.eval("history.back()")
            b.wait(f"VIEW==={back_to!r}")

    def check_all(self, scope, open_page, back_to, minimum=1):
        open_page()
        L = self.links(scope)
        self.assertGreaterEqual(len(L), minimum, f"no count links in {scope}")
        for x in L:
            self.assertGreater(x["n"], 0, x)                      # a zero is never a link
            self.assertIn("open in Work", x["label"], x)          # the link says what it opens
            open_page()
            self.follow(x["nav"], x["n"])
        return L

    # ---- 1. the Projects table's Evidence column ----
    def test_projects_evidence_figures_open_work_with_that_many(self):
        b = self.b
        L = self.check_all("#projTbl", lambda: (self.b.eval("go('projects')"), self.b.wait("document.querySelector('#projTbl tr')")), "projects")
        navs = [x["nav"] for x in L]
        self.assertIn("actions:overdue:ABC", navs)
        self.assertIn("raid:urgentonly:ABC", navs)
        b.eval("go('projects')")
        b.wait("document.querySelector('#projTbl tr')")
        self.assertIn("in Example Programme", b.eval("document.querySelector('#projTbl [data-nav=\"actions:overdue:ABC\"]').getAttribute('aria-label')"))

    def test_evidence_click_does_not_open_the_row_and_back_returns(self):
        b = self.b
        b.eval("go('projects')")
        b.wait("document.querySelector('#projTbl tr')")
        b.click("#projTbl [data-nav='actions:overdue:ABC'] b")
        b.wait("VIEW==='work'")
        self.assertEqual(b.eval("WT"), "actions")
        self.assertEqual(b.eval("[...PROJF]"), ["ABC"])
        b.eval("history.back()")
        b.wait("VIEW==='projects'")
        b.click("#projTbl tr[data-cock='ABC'] td")                 # elsewhere on the row still opens the project page
        b.wait("VIEW==='cockpit' && COCK==='ABC'")

    def test_evidence_zero_is_plain_and_no_date_and_slip_show_their_cards(self):
        b = self.b
        b.eval("go('projects')")
        b.wait("document.querySelector('#projTbl tr')")
        def_ev = b.eval("document.querySelector('#projTbl tr[data-cock=\"DEF\"] .ev').innerHTML")
        self.assertNotIn("raid:urgentonly:DEF", def_ev)              # DEF has no urgent risk: plain text
        self.assertIn("Urgent risks <b", def_ev)
        b.click("#projTbl [data-cockjump='ABC|undated']")
        b.wait("VIEW==='cockpit' && COCK==='ABC' && !!document.getElementById('undatedCard')")
        b.eval("go('projects')")
        b.wait("document.querySelector('#projTbl tr')")
        if b.eval("!!document.querySelector(\"#projTbl [data-cockjump='ABC|ms']\")"):
            b.click("#projTbl [data-cockjump='ABC|ms']")
            b.wait("VIEW==='cockpit' && COCK==='ABC'")

    def test_keyboard_reaches_a_figure_and_enter_opens_it(self):
        b = self.b
        b.eval("go('projects')")
        b.wait("document.querySelector('#projTbl tr')")
        b.eval("document.querySelector('#projTbl [data-nav=\"raid:urgentonly:ABC\"]').focus()")
        self.assertEqual(b.eval("document.activeElement.dataset.nav"), "raid:urgentonly:ABC")
        b.key("Enter")
        b.wait("VIEW==='work' && WT==='raid'")
        self.assertEqual(b.eval(SHOWN), b.eval("R.filter(r=>r.p==='ABC'&&r.st==='Open'&&r.pr==='Urgent').length"))

    def test_extra_filters_round_trip_through_the_address(self):
        b = self.b
        self.assertEqual(b.eval("navParse('actions:open:ABC:o=Sara%20Example,Omar&rr=,2026-10-01&st=')"),
                         {"wt": "actions", "view": "open", "code": "ABC",
                          "extra": {"o": ["Sara Example", "Omar"], "rr": ["", "2026-10-01"], "st": []}})
        self.assertEqual(b.eval("navParse('raid:open:ABC')['extra']"), None)

    # ---- 2. the project page's Flow card ----
    def cockpit(self, code="ABC"):
        self.b.eval(f"go('cockpit',{code!r})")
        self.b.wait("document.querySelector('#flowCard')")

    def test_flow_figures_open_work_with_that_many(self):
        L = self.check_all("#flowCard", self.cockpit, "cockpit", minimum=4)
        navs = " ".join(x["nav"] for x in L)
        for part in ("actions:open:ABC:st=&rr=", "actions:closed:ABC:st=Closed&cr=", "raid:open:ABC:st=&ty=Risk,Issue&rr=",
                     "all:open:ABC:st=Open&ty=", "raid:open:ABC:st=Open&ty=Risk,Issue&pr="):
            self.assertIn(part, navs)

    def test_flow_overdue_bars_stay_plain_and_charts_with_links_are_groups(self):
        b = self.b
        self.cockpit()
        figs = b.eval("[...document.querySelectorAll('#flowCard figure')].map(f=>({cap:f.querySelector('figcaption').textContent, links:f.querySelectorAll('.flk').length, role:f.querySelector('svg').getAttribute('role')}))")
        for f in figs:
            self.assertEqual(f["role"], "group" if f["links"] else "img", f)
            if f["cap"].startswith("Overdue at the end"):
                self.assertEqual(f["links"], 0)
        self.assertEqual(b.eval("[...document.querySelectorAll('#flowCard .flk')].filter(g=>!(+g.dataset.n>0)).length"), 0)

    def test_flow_link_works_from_the_keyboard_and_shows_its_filters(self):
        b = self.b
        self.cockpit()
        nav = b.eval("document.querySelector('#flowCard .flk[data-nav^=\"all:open\"]').dataset.nav")
        b.eval(f"document.querySelector('#flowCard .flk[data-nav={json.dumps(nav)}]').focus()")
        b.key("Enter")
        b.wait("VIEW==='work' && WT==='all'")
        chips = b.eval("$('#wapplied').textContent")
        self.assertIn("Raised:", chips)
        self.assertIn("Type:", chips)

    def test_closed_between_is_a_work_filter(self):
        b = self.b
        b.eval("go('work'); WT='actions'; clearAllFilters(); applyFilters({st:['Closed','Cancelled'],cr:[TODAY.slice(0,8)+'01',TODAY]}); renderWork()")
        self.assertIn("Closed:", b.eval("$('#wapplied').textContent"))
        self.assertEqual(b.eval("rows().length"), b.eval("A.filter(x=>['Closed','Cancelled'].includes(x.st)&&x.closed&&x.closed>=TODAY.slice(0,8)+'01'&&x.closed<=TODAY).length"))
        self.assertIn("cr=", b.eval("navWrite(false), location.hash"))
        b.eval("document.querySelector('#wapplied [data-clr=\"cr\"]').click()")
        self.assertEqual(b.eval("CR"), {"from": "", "to": ""})

    # ---- 3. the People list ----
    def people(self):
        self.b.eval("setPTab('work'); go('people','work')")
        self.b.wait("document.querySelector('#peopleTbl tr[data-pp]')")

    def test_people_figures_open_work_for_that_person_and_kind(self):
        L = self.check_all("#peopleTbl", self.people, "people", minimum=6)
        tabs = {x["nav"].split(":")[0] for x in L}
        self.assertEqual(tabs, {"actions", "raid", "decisions", "all"})
        sara = [x for x in L if "Sara%20Example" in x["nav"]]
        self.assertTrue(any(x["nav"].startswith("decisions:pending::") for x in sara))
        self.assertTrue(all("Sara Example" in x["label"] for x in sara))

    def test_people_zero_is_plain_and_a_figure_does_not_open_the_person(self):
        b = self.b
        self.people()
        cells = b.eval("[...document.querySelectorAll('#peopleTbl tbody tr')].flatMap(tr=>[...tr.querySelectorAll('td.num')].map(td=>({t:td.textContent.trim(), a:!!td.querySelector('a')})))")
        for c in cells:
            self.assertEqual(c["a"], c["t"] not in ("0", "—"), c)
        b.click("#peopleTbl tr[data-pp='Sara Example'] td.num a")
        b.wait("VIEW==='work'")
        self.assertNotEqual(b.eval("VIEW"), "person")
        self.assertEqual(b.eval("[...PROJF]"), [])                   # every project
        self.assertIn("Owner:", b.eval("$('#wapplied').textContent"))
        b.eval("history.back()")
        b.wait("VIEW==='people'")

    # ---- 4. the audit: Today, a person's page, Nothing assigned, the project page's cards, the prep brief, Settings ----
    def today(self):
        self.b.eval("go('today'); renderToday()")
        self.b.wait("document.querySelector('#briefText')")

    def test_today_figures_open_work_with_that_many(self):
        b = self.b
        L = self.check_all("#briefText", self.today, "today")
        self.assertEqual(L[0]["nav"], "actions:overdue::o=%40me")
        L = self.check_all("#hMine", self.today, "today")
        self.assertEqual(L[0]["n"], b.eval("A.filter(x=>isMe(x.o)&&(overdue(x)||soon(x))).length"))

    def test_today_missing_owner_or_date_counts_already_open_exactly_that_many(self):
        b = self.b
        self.today()
        gaps = b.eval("[...document.querySelectorAll('#tBrief a[data-gap]')].filter(a=>a.dataset.gap.split('|')[0]).map(a=>({g:a.dataset.gap, n:+a.textContent.match(/\\d+/)[0]}))")
        self.assertTrue(gaps)
        for g in gaps:
            self.today()
            b.eval(f"document.querySelector('#tBrief a[data-gap={json.dumps(g['g'])}]').click()")
            b.wait("VIEW==='work'")
            self.assertEqual(b.eval(SHOWN), g["n"], g)

    def test_today_decisions_waiting_line_lists_every_pending_decision(self):
        b = self.b
        b.eval("go('work'); WT='decisions'; PROJF.clear(); PROJF.add('DEF'); renderWork()")   # an earlier filter isn't kept
        self.today()
        b.click("#tBrief [data-decpending]")
        b.wait("VIEW==='work' && WT==='decisions'")
        self.assertEqual(b.eval(SHOWN), b.eval("decPending().length"))

    def test_person_page_figures(self):
        b = self.b
        page = lambda: (b.eval("go('person','Sara Example')"), b.wait("document.querySelector('#v-person .ppcounts')"))    # noqa: E731
        self.check_all("#v-person .ppcounts", page, "person", minimum=3)
        self.check_all("#decWaiting", page, "person")

    def test_nothing_assigned_closed_items(self):
        b = self.b
        page = lambda: (b.eval("setPTab('none'); go('people','none')"), b.wait("document.querySelector('#peopleTbl tr[data-pp]')"))    # noqa: E731
        L = self.check_all("#peopleTbl", page, "people")
        self.assertTrue(all(x["nav"].startswith("all:closed::st=Closed,Cancelled&o=") for x in L))
        b.eval("setPTab('work')")

    def test_project_page_cards(self):
        b = self.b
        page = lambda: (b.eval("go('cockpit','ABC')"), b.wait("document.querySelector('#depCard') && document.querySelector('#decCard')"))    # noqa: E731
        L = self.check_all("#depCard h2", page, "cockpit") + self.check_all("#decCard h2", page, "cockpit")
        self.assertEqual(len(L), 2)

    def prep(self, portfolio=False):
        b = self.b
        b.eval("go('today'); renderToday()")
        pf = "prepOf(e,TODAY).p='_portfolio';" if portfolio else ""
        b.eval("(()=>{ const e=prepTimed()[0]; " + pf + " openPrep(e,TODAY); })()")
        b.wait("document.getElementById('prepDlg').open && document.querySelector('#prepBody .prepsec')")

    def test_prep_brief_figures_for_a_project_and_the_portfolio(self):
        b = self.b
        for portfolio in (False, True):
            L = self.check_all("#prepBody", lambda: self.prep(portfolio), None, minimum=3)
            if portfolio:
                self.assertTrue(all(x["nav"].split(":")[2] == "" for x in L), L)
            self.assertFalse(b.eval("document.getElementById('prepDlg').open"))
        self.prep()
        plain = b.eval("[...document.querySelectorAll('#prepBody .prepsec h3')].filter(h=>/^Decisions since|^Recent reports|^Early warnings/.test(h.textContent)).map(h=>!!h.querySelector('a'))")
        self.assertTrue(plain and not any(plain))                    # what Work can't list stays plain

    def test_settings_people_and_workstream_counts(self):
        b = self.b
        page = lambda: (b.eval("go('settings','people')"), b.wait("document.querySelector('#peopleMgr td.num')"))    # noqa: E731
        L = self.check_all("#peopleMgr", page, "settings", minimum=2)
        self.assertTrue(all(":st=&o=" in x["nav"] for x in L))


if __name__ == "__main__":
    unittest.main()
