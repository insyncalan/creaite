"""Dashboard pages (BL-87, BL-88, BL-89, BL-95, BL-91, BL-90 part 1), part 3 of 3 (undated work, Trends and flow, and dependencies; the fixture is in pages_support.py).

Run: python3 dev/tests/test_pages_flow.py   (the page tests need Google Chrome; they are skipped otherwise)

Everything is fictional and temporary. The data tests run in the default layout and in a temporary OneDrive-style projects
root (the BL-85 `locations` setting, resolved against a fake home folder); the page tests drive a real headless Chrome
against the real live server, as a person would.
"""
import json
import subprocess
import sys
import unittest
import unittest.mock
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from live_browser import TEST_PALETTES_JS, LiveBrowserCase  # noqa: E402
from test_dashboard import CHROME, d, populate  # noqa: E402
from test_dashboard import today as _cx_today  # noqa: E402
from test_insight import chrome, log, py  # noqa: E402
from test_tracker import ABC, Vault, action  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from pages_support import (  # noqa: E402
    CONTRAST_JS,
    THEMES,
    theme,
    theme_count,
)


# ===== BL-95: undated open work always shows on the project page =====

def ago(days):
    return d(-days)


def oracle(v, code="ABC"):
    """The rule written out in Python, sharing no code with the page: IDs of open work with no due date."""
    acts = [a["id"] for a in v.rows("actions") if a["project"] == code and a["status"] in ("Open", "Delayed") and not a["due_date"]]
    raid = [r["id"] for r in v.rows("raid") if r["project"] == code and r["status"] == "Open" and not r["due_date"]
            and (r["type"] in ("Risk", "Issue") or (r["response_action"] or "").strip())]
    return sorted(acts), sorted(raid)


class UndatedWorkTests(LiveBrowserCase):
    """A fresh vault with undated, dated, closed and other-project items, a live server and a browser per test."""

    @classmethod
    def load(cls, v):
        populate(v)
        src = "Alan (cx-edit)"
        item = lambda table, n, **vals: {"n": n, "op": "new", "table": table, "values": vals, "match": "strong", "flags": [], "decision": "approved"}  # noqa: E731
        v.propose("undated", [
            item("actions", 1, project="ABC", description="Undated and old", owner="Sara Example", raised=ago(20), source=src),
            item("actions", 2, project="ABC", description="Undated and fresh", owner="Omar Ali", raised=ago(1), priority="Urgent", source=src),
            item("actions", 3, project="ABC", description="Dated action", owner="Sara Example", raised=ago(20), due_date=d(9), source=src),
            item("actions", 4, project="ABC", description="Undated but closed", owner="Sara Example", raised=ago(20), status="Closed", closed=ago(2), source=src),
            item("actions", 5, project="ABC", description="Undated but cancelled", owner="Sara Example", raised=ago(20), status="Cancelled", source=src),
            item("actions", 6, project="DEF", description="Undated in another project", owner="Omar Ali", raised=ago(20), source=src),
            item("raid", 7, project="ABC", type="Assumption", description="Assumption with no response", impact="Low", likelihood="Low", raised=ago(20), source=src),
            item("raid", 8, project="ABC", type="Assumption", description="Assumption with a response to date", impact="Low", likelihood="Low", raised=ago(20),
                 response_action="Confirm with the client", source=src),
            item("raid", 9, project="ABC", type="Dependency", description="Dependency with no response", impact="Low", likelihood="Low", raised=ago(20), source=src),
            item("raid", 10, project="ABC", type="Issue", description="Issue with a date", impact="Medium", likelihood="High", raised=ago(20), due_date=d(5), source=src),
            item("decisions", 11, project="ABC", decision="A decision has no due date", made_by="Jane Doe", date=ago(3), source=src),
        ])
        v.run("apply")

    def setUp(self):
        super().setUp()
        self.b.eval("go('cockpit','ABC')")
        self.b.wait("document.querySelector('#v-cockpit .curcard')")

    def card_ids(self):
        return self.b.eval("[...document.querySelectorAll('#undatedCard [data-open]')].map(r=>r.dataset.open.split(':')[1]).sort()")

    def test_the_card_lists_exactly_the_open_undated_work(self):
        acts, raid = oracle(self.v)
        self.assertGreaterEqual(len(acts), 2)
        self.assertGreaterEqual(len(raid), 3)                                                              # the two seeded risks, an issue-free ABC, the assumption with a response
        self.assertEqual(self.card_ids(), sorted(acts + raid))
        texts = self.b.eval("document.getElementById('undatedCard').textContent")
        for out in ("Undated but closed", "Undated but cancelled", "Dated action", "Undated in another project", "Assumption with no response",
                    "Dependency with no response", "Issue with a date", "A decision has no due date"):
            self.assertNotIn(out, texts)
        self.assertIn("Assumption with a response to date", texts)                                         # an assumption only when it has a response to date
        self.assertEqual(self.b.eval("document.querySelector('#undatedCard').previousElementSibling.querySelector('h2').textContent.startsWith('Actions due or overdue')"), True)   # directly under it

    def test_the_count_is_in_the_heading_the_evidence_row_and_the_projects_table_and_matches_the_data(self):
        acts, raid = oracle(self.v)
        n = len(acts) + len(raid)
        b = self.b
        self.assertIn(f"· {n}", b.eval("document.querySelector('#undatedCard h2').textContent"))
        labels = b.eval("[...document.querySelectorAll('.evrow .evbox .l')].map(e=>e.textContent)")
        self.assertNotIn("No due date", labels)                                                            # BL-185: the status line drops it; the card keeps the count
        b.eval("go('projects')")
        b.wait("document.querySelector('#projTbl .ev')")
        self.assertIn(f"No date {n}", b.eval("[...document.querySelectorAll('#projTbl tr')].find(r=>r.textContent.includes('Example Programme')).querySelector('.ev').textContent"))
        self.assertEqual(b.eval("P.find(p=>p.code==='ABC').undated"), {"actions": len(acts), "raid": len(raid), "total": n})   # the data's own count agrees
        self.assertEqual(b.eval("P.find(p=>p.code==='DEF').undated.total"), 1)

    def test_the_links_open_works_no_date_filter_with_exactly_that_many(self):
        acts, raid = oracle(self.v)
        b = self.b
        self.assertEqual(b.eval("document.querySelectorAll('#undatedCard h2 a').length"), 0)              # the heading's number covers both lists, so it has no link
        link = b.eval("document.querySelector('#undatedCard a[data-nav^=\"actions:undated\"]').textContent.trim()")
        self.assertEqual(link, f"All {len(acts)} Example Programme undated action{'s' if len(acts) != 1 else ''} ›")
        b.click('#undatedCard a[data-nav^="actions:undated"]')
        b.wait("VIEW==='work'")
        self.assertEqual(b.eval("[WT,[...FX.due],[...PROJF],[...FX.st].sort()]"), ["actions", ["none"], ["ABC"], ["Delayed", "Open"]])
        self.assertEqual(b.eval("rows().map(x=>x.id).sort()"), acts)                                      # the same actions as the card
        b.eval("go('cockpit','ABC')")
        b.wait("document.querySelector('#undatedCard')")
        b.click('#undatedCard [data-nav^="raid:undated"]')
        b.wait("VIEW==='work' && WT==='raid'")
        shown = b.eval("rows().map(x=>x.id).sort()")
        self.assertEqual(sorted(set(raid) - set(shown)), [])                                              # every RAID item on the card is in Work's list
        extra = sorted(set(shown) - set(raid))
        self.assertEqual(len(extra), 2)                                                                    # Work's filter also has the two with no response to date
        b.eval("go('cockpit','ABC')")
        b.wait("document.querySelector('#undatedCard')")
        self.assertFalse(b.eval("!!document.querySelector('.evbox[data-undated]')"))                      # BL-185: no figure for it in the status line

    def test_each_row_shows_its_id_owner_priority_and_a_set_date_control_and_new_ones_are_dimmer(self):
        b = self.b
        rows = b.eval("""[...document.querySelectorAll('#undatedCard .undrow')].map(r=>({id:r.querySelector('.undid').textContent, text:r.querySelector('.undt').textContent.replace(/\\s+/g,' ').trim(),
          who:r.textContent, dim:r.classList.contains('dim'), btn:!!r.querySelector('input[data-und]')}))""")
        by = {r["id"]: r for r in rows}
        fresh = next(r for r in rows if r["text"].startswith("Undated and fresh"))
        old = next(r for r in rows if r["text"].startswith("Undated and old"))
        self.assertTrue(fresh["dim"])                                                                      # raised yesterday: new, dimmer
        self.assertIn("new", fresh["text"])
        self.assertFalse(old["dim"])
        self.assertIn("Omar Ali", fresh["who"])
        self.assertIn("Urgent", fresh["who"])                                                              # its priority
        self.assertTrue(all(r["btn"] for r in rows))
        # the grace period is a setting
        b.eval("go('settings','work')")
        b.wait("document.querySelector('[data-k=undatedGrace]')")
        b.eval("(()=>{ const i=document.querySelector('[data-k=undatedGrace]'); i.value=0; i.dispatchEvent(new Event('change',{bubbles:true})); })()")
        b.wait("S.undatedGrace===0")
        self.assertEqual(json.loads((self.v.root / "system/config/settings.json").read_text())["dashboard"]["undated_grace_days"], 0)
        b.eval("go('cockpit','ABC')")
        b.wait("document.querySelector('#undatedCard')")
        self.assertEqual(b.eval("document.querySelectorAll('#undatedCard .undrow.dim').length"), 0)       # grace 0: nothing is new

    def test_set_date_saves_inline_without_opening_the_panel_and_the_item_leaves_the_card(self):
        b = self.b
        acts, raid = oracle(self.v)
        target = next(a for a in self.v.rows("actions") if a["description"] == "Undated and old")["id"]
        b.click(f'#undatedCard input[data-und="actions:{target}"]')
        b.wait("document.querySelector('.cal')")                                                           # the calendar opens on the row
        self.assertFalse(b.eval("!!document.getElementById('f_due')"))                                     # and the side panel does not
        b.eval(f"(()=>{{ const i=document.getElementById('und-{target}'); i.value='16-11-2026'; i.dispatchEvent(new Event('input',{{bubbles:true}})); }})()")
        b.wait(f"!document.querySelector('#undatedCard [data-open=\"actions:{target}\"]')", 15)
        self.assertFalse(b.eval("!!document.getElementById('f_due')"))                                     # still no panel
        b.eval("(async()=>{ await savesSettled(); return true; })()")                                     # BL-304: it leaves the card at once; applied in the background
        self.assertEqual(next(a for a in self.v.rows("actions") if a["id"] == target)["due_date"], "2026-11-16")   # a normal proposal, applied (BL-181: a Monday, so no weekend alert)
        b.wait(f"!document.querySelector('#undatedCard [data-open=\"actions:{target}\"]')")
        left_acts, left_raid = oracle(self.v)
        self.assertEqual(left_acts, sorted(set(acts) - {target}))
        self.assertEqual(self.card_ids(), sorted(left_acts + left_raid))
        self.assertEqual(b.eval("P.find(p=>p.code==='ABC').undated.actions"), len(left_acts))
        self.assertFalse(list((self.v.root / "system/staging").glob("proposed-*dashboard*.json")))        # nothing of ours waits: it was applied

    def test_the_card_is_absent_when_nothing_is_undated(self):
        b = self.b
        acts, raid = oracle(self.v)
        items = [{"n": i, "op": "update", "table": "actions", "id": a, "changes": {"due_date": d(12)}, "decision": "approved", "match": "strong", "flags": []}
                 for i, a in enumerate(acts, 1)] + \
                [{"n": 20 + i, "op": "update", "table": "raid", "id": r, "changes": {"due_date": d(12)}, "decision": "approved", "match": "strong", "flags": []}
                 for i, r in enumerate(raid, 1)]
        self.v.propose("dates", items)
        self.v.run("apply")
        b.eval("reloadData()")
        b.wait("P.find(p=>p.code==='ABC').undated.total===0")
        b.eval("go('cockpit','ABC')")
        self.assertEqual(b.eval("document.querySelectorAll('#undatedCard').length"), 0)                   # hidden
        self.assertFalse(b.eval("[...document.querySelectorAll('.evrow .evbox .l')].some(e=>e.textContent==='No due date')"))   # BL-185: not in the status line

    def test_readable_in_every_theme_and_mode(self):
        b = self.b
        b.eval(CONTRAST_JS)
        bad = {}
        for pal in THEMES:
            for mode in ("Light", "Dark"):
                theme(b, pal, mode)
                r = b.eval("""(()=>{ const card=document.getElementById('undatedCard'), bg=__bgOf(card), pick=s=>getComputedStyle(card.querySelector(s)).color,
                  dim=card.querySelector('.undrow.dim .undt'), over=getComputedStyle(card.querySelector('.undset input')), ph=getComputedStyle(card.querySelector('.undset input'),'::placeholder'); return {title:__ratio(pick('.undrow:not(.dim) .undt'),bg), id:__ratio(pick('.undid'),bg),
                  dim:__ratio(getComputedStyle(dim).color,bg), btn:__ratio(over.color,over.backgroundColor), ph:__ratio(ph.color,over.backgroundColor)}; })()""")
                if min(r.values()) < 4.5:
                    bad[f"{pal}|{mode}"] = r
        self.assertEqual(bad, {})
        theme(b, "creaite", "Light")


# ===== BL-91: Trends and flow =====

NOW = "2026-10-14 09:00"          # a Wednesday; the weeks are Monday to Sunday from 24-08-2026 to this one (8 of them)
WEEKS = ["2026-08-24", "2026-08-31", "2026-09-07", "2026-09-14", "2026-09-21", "2026-09-28", "2026-10-05", "2026-10-12"]


def item(table, n, **values):
    return {"n": n, "op": "new", "table": table, "values": values, "match": "strong", "flags": [], "decision": "approved"}


def flow_vault():
    """Fixed sample data with known opened, closed, overdue and ageing values (today is 14-10-2026), described in the test names."""
    v = Vault()
    v.run("init")
    src = f"{ABC}/minutes/2026-09-01 Steering.docx — Actions"
    v.propose("flow", [
        action(1, description="a1 closed in week 3", raised="2026-09-01", status="Closed", closed="2026-09-10", source=src),
        action(2, description="a2 closed in week 5", raised="2026-09-02", status="Closed", closed="2026-09-22", source=src),
        action(3, description="a3 open and overdue", raised="2026-09-08", due_date="2026-09-30", source=src),
        action(4, description="a4 open, undated", raised="2026-09-15", source=src),
        action(5, description="a5 cancelled", raised="2026-09-16", status="Cancelled", closed="2026-09-17", source=src),
        action(6, description="a6 due later", raised="2026-10-06", due_date="2026-10-20", source=src),
        action(7, description="a7 due today", raised="2026-10-13", due_date="2026-10-14", source=src),
        action(8, description="a8 re-dated", raised="2026-09-29", due_date="2026-10-30", source=src),
        action(9, description="a9 just overdue", raised="2026-10-12", due_date="2026-10-13", source=src),
        item("raid", 10, project="ABC", type="Risk", description="r1 an older risk", impact="High", likelihood="Medium", raised="2026-09-03", source=src),
        item("raid", 11, project="ABC", type="Dependency", description="r4 a dependency", impact="Low", likelihood="Low", raised="2026-09-10", source=src),
        item("raid", 12, project="ABC", type="Issue", description="r2 an issue, closed", impact="Medium", likelihood="High", raised="2026-09-20",
             status="Closed", closed="2026-10-07", source=src),
        item("raid", 13, project="ABC", type="Risk", description="r3 an Urgent risk", impact="High", likelihood="High", raised="2026-10-13", source=src),
        item("milestones", 14, project="ABC", name="UAT start", baseline_date="2026-10-01", forecast_date="2026-10-22", source="Alan (cx-edit)"),
        item("milestones", 15, project="ABC", name="Build complete", baseline_date="2026-10-10", forecast_date="2026-10-07", source="Alan (cx-edit)"),
    ])
    v.run("apply")
    log(v, [("2026-10-08 10:00:00", "actions", "ABC-A-008", "due_date", "2026-10-02", "2026-10-30"),      # a8 was overdue at the end of week 6
            ("2026-09-12 10:00:00", "milestones", "ABC-M-001", "forecast_date", "2026-10-01", "2026-10-15"),
            ("2026-10-02 10:00:00", "milestones", "ABC-M-001", "forecast_date", "2026-10-15", "2026-10-22"),
            ("2026-10-05 10:00:00", "milestones", "ABC-M-002", "forecast_date", "2026-10-10", "2026-10-07")])
    for f in (v.root / "system/history").glob("flow-*.json"):     # the apply's build ran on the real clock, not NOW: its snapshot
        f.unlink()                                                  # (one for a Sunday in the period is read back) isn't sample data
    return v


def flow(v, now=NOW, extra=""):
    return json.loads(py(v, f"import json, build_dashboard as b\n{extra}print(json.dumps(b.collect()['flow']['ABC']))", now))


class FlowDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = flow_vault()
        cls.f = flow(cls.v)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def col(self, key):
        return [w[key] for w in self.f["weeks"]]

    def test_the_weeks_run_monday_to_sunday_and_the_last_is_this_week_so_far(self):
        self.assertEqual([w["start"] for w in self.f["weeks"]], WEEKS)
        self.assertEqual(self.f["weeks"][0]["end"], "2026-08-30")
        self.assertEqual(self.f["weeks"][-1]["end"], "2026-10-14")                                      # today
        self.assertEqual(self.f["period"], 8)

    def test_opened_and_closed_per_week(self):
        self.assertEqual(self.col("a_opened"), [0, 2, 1, 2, 0, 1, 1, 2])                                # actions raised
        self.assertEqual(self.col("a_closed"), [0, 0, 1, 0, 1, 0, 0, 0])
        self.assertEqual(self.col("a_cancelled"), [0, 0, 0, 1, 0, 0, 0, 0])                             # cancelled is not closed
        self.assertEqual(self.col("r_opened"), [0, 1, 0, 1, 0, 0, 0, 1])                                # risks and issues only
        self.assertEqual(self.col("r_closed"), [0, 0, 0, 0, 0, 0, 1, 0])
        self.assertEqual(self.col("opened"), [0, 3, 2, 3, 0, 1, 1, 3])                                  # everything, the dependency too
        self.assertEqual(self.col("closed"), [0, 0, 1, 0, 1, 0, 1, 0])
        self.assertEqual(self.col("cancelled"), [0, 0, 0, 1, 0, 0, 0, 0])

    def test_overdue_by_week_is_rebuilt_from_the_change_log(self):
        self.assertEqual(self.col("overdue"), [0, 0, 0, 0, 0, 2, 1, 2])                                 # a8 was overdue until it was re-dated on 08-10
        self.assertEqual(self.f["overdue"], {"now": 2, "last_week": 1})
        self.assertFalse(any(w["from_snapshot"] for w in self.f["weeks"]))

    def test_how_long_open_items_have_been_open(self):
        a = self.f["ageing"]
        self.assertEqual(a["labels"], ["0 to 7 days", "8 to 14 days", "15 to 30 days", "Over 30 days"])
        self.assertEqual(a["buckets"], [3, 1, 2, 3])                                                    # of 9 open items
        self.assertEqual(a["open"], 9)
        self.assertEqual([(o["id"], o["days"]) for o in a["oldest"]], [("ABC-010", 41), ("ABC-A-003", 36), ("ABC-011", 34)])
        self.assertEqual([o["k"] for o in a["oldest"]], ["raid", "actions", "raid"])                    # linked to their tables

    def test_risks_and_milestone_movement(self):
        r = self.f["risks"]
        self.assertEqual((r["opened"], r["closed"], r["cancelled"]), (3, 1, 0))
        self.assertEqual(r["mix"], {"Urgent": 1, "High": 1, "Medium": 0, "Low": 0})                     # the open ones now
        m = self.f["milestones"]
        self.assertEqual((m["moves"], m["days"]), (3, 18))                                              # +14, +7 and -3
        self.assertEqual([(x["id"], x["moves"], x["days"], x["name"]) for x in m["by"]],
                         [("ABC-M-001", 2, 21, "UAT start"), ("ABC-M-002", 1, -3, "Build complete")])

    def test_the_summary_line(self):
        self.assertEqual(self.f["summary"], "3 opened, 0 closed; 2 overdue, up from 1; the oldest open action is 36 days old")

    def test_the_daily_snapshot_is_written_by_a_build_and_read_back_for_past_weeks_only(self):
        v = self.v
        py(v, "import build_dashboard as b\nb.build()", NOW)
        snap = json.loads((v.root / "system/history/flow-2026-10-14.json").read_text())
        self.assertEqual(snap["projects"]["ABC"], {"overdue": 2, "open": 9})
        (v.root / "system/history/flow-2026-10-11.json").write_text(json.dumps({"date": "2026-10-11", "projects": {"ABC": {"overdue": 7, "open": 9}}}))
        (v.root / "system/history/flow-2026-10-14.json").write_text(json.dumps({"date": "2026-10-14", "projects": {"ABC": {"overdue": 99, "open": 9}}}))
        f = flow(v)
        self.assertEqual(f["weeks"][-2]["overdue"], 7)                                                 # last week's end: the snapshot wins
        self.assertTrue(f["weeks"][-2]["from_snapshot"])
        self.assertEqual(f["overdue"]["now"], 2)                                                       # today is always worked out afresh
        self.assertEqual(f["weeks"][-3]["overdue"], 2)                                                 # no snapshot for that day: rebuilt
        for p in (v.root / "system/history").glob("flow-*.json"):
            p.unlink()
        self.assertEqual([r for r in v.rows("projects") if r["code"] == "ABC"][0]["code"], "ABC")      # (a snapshot is a file, not a table)
        import sqlite3
        with sqlite3.connect(v.root / "system/tracker.db") as con:
            self.assertFalse([t for (t,) in con.execute("select name from sqlite_master where type='table'") if "flow" in t])

    def test_the_period_is_a_setting(self):
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        try:
            for value, weeks in ((12, 12), (3, 4), (40, 26), ("x", 8)):
                data.setdefault("dashboard", {})["flow_weeks"] = value
                cfg.write_text(json.dumps(data))
                self.assertEqual(len(flow(self.v)["weeks"]), weeks, value)                              # 4 to 26, 8 if unreadable
        finally:
            data["dashboard"]["flow_weeks"] = 8
            cfg.write_text(json.dumps(data))

    def test_an_undone_date_change_never_happened(self):
        import sqlite3
        v = self.v
        with sqlite3.connect(v.root / "system/tracker.db") as con:
            con.execute("INSERT INTO applies (apply_id, at, proposals, undone_at) VALUES (901, '2026-10-03', '[]', '2026-10-04')")
        log(v, [("2026-10-03 10:00:00", "actions", "ABC-A-003", "due_date", "2026-09-30", "2026-10-30", 901)])
        try:
            self.assertEqual(flow(v)["weeks"][-1]["overdue"], 2)                                         # a3 is still overdue
        finally:
            with sqlite3.connect(v.root / "system/tracker.db") as con:
                con.execute("DELETE FROM change_log WHERE apply_id = 901")
                con.execute("DELETE FROM applies WHERE apply_id = 901")


class FlowWeeklyReportTests(unittest.TestCase):
    """The weekly report gets a line about flow, first in Progress This Week."""

    def test_the_line_and_the_word_report(self):
        v = flow_vault()
        try:
            now = "2026-10-16 13:00"
            line = json.loads(py(v, "import json, report\nprint(json.dumps(report.weekly_data('ABC')['flow']))", now))
            self.assertEqual(line, "3 opened, 0 closed; 3 overdue, up from 1; the oldest open action is 38 days old")
            spec = v.root / "system/staging/drafts/weekly.json"
            spec.parent.mkdir(parents=True, exist_ok=True)
            spec.write_text(json.dumps({"code": "ABC", "health": "At risk", "health_reason": "Overdue items rising", "summary": ["Quiet but late."],
                                        "key_changes": "None", "current_state": "Steady.", "progress": ["Plan revised"], "next_week": ["Chase"]}))
            import os
            subprocess.run([sys.executable, str(v.root / "system/scripts/report.py"), "weekly-stage", str(spec)], cwd=v.root, check=True,
                           env={**os.environ, "CREAITE_NOW": now}, capture_output=True)
            draft = next((v.root / "system/staging/drafts").glob("* Weekly report - Example Programme.docx"))
            text = v.run("text", str(draft), script="docx_tools.py").stdout
            self.assertIn("Flow: 3 opened, 0 closed; 3 overdue, up from 1; the oldest open action is 38 days old.", text)
            self.assertLess(text.index("Flow: 3 opened"), text.index("Plan revised"))                      # first in Progress This Week
            self.assertEqual(text.count("Flow: "), 1)
        finally:
            v.cleanup()


class FlowCardTests(unittest.TestCase):
    """The Flow card in the browser: inline SVG drawn to scale, in each theme's colours."""

    @classmethod
    def setUpClass(cls):
        if not CHROME.exists():
            raise unittest.SkipTest("Google Chrome not installed")
        cls.v = flow_vault()
        py(cls.v, "import build_dashboard as b\nb.build()", NOW)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def probe(self, script):
        out, errors = chrome(self.v, "VSTATE='ok'; " + CONTRAST_JS + ";" + script, name="flow")
        self.assertEqual(errors, [])
        self.assertIsNotNone(out)
        self.assertNotIn("error", out, out)
        return out

    def test_the_card_is_drawn_to_scale_with_every_number_on_it(self):
        o = self.probe("""
          go("cockpit","ABC"); const c=document.getElementById("flowCard"), out={}, figs=[...c.querySelectorAll("figure.flc")];
          out.captions=figs.map(f=>f.querySelector("figcaption").textContent);
          const bars=f=>[...f.querySelectorAll("rect[data-wk]")].map(r=>({v:+r.dataset.v,h:+r.getAttribute("height"),wk:r.dataset.wk,cls:r.getAttribute("class")}));
          out.actions=bars(figs[0]); out.risks=bars(figs[1]); out.overdue=bars(figs[2]);
          out.labels=[...figs[0].querySelectorAll("text.fl-m")].map(t=>t.textContent);
          out.valueLabels=[...figs[0].querySelectorAll("text.fl-t")].map(t=>t.textContent);
          out.hbars=[...figs[3].querySelectorAll("rect[data-v]")].map(r=>({v:+r.dataset.v,w:+r.getAttribute("width")}));
          out.mix=[...figs[4].querySelectorAll("rect[data-v]")].map(r=>({v:+r.dataset.v,w:+r.getAttribute("width")}));
          out.summary=document.getElementById("flowSummary").textContent; out.legend=[...figs[0].querySelectorAll("text.fl-t")].map(t=>t.textContent).filter(t=>/opened|closed/.test(t));
          out.oldest=[...c.querySelectorAll("[data-open]")].map(e=>e.dataset.open); out.svgs=c.querySelectorAll("figure.flc svg").length; out.aria=figs.map(f=>f.querySelector("svg").getAttribute("aria-label"));
          window.OUT=out;""")
        self.assertEqual(o["svgs"], 5)
        self.assertEqual(o["captions"][0], "Actions opened and closed, by week")
        self.assertIn("2 now, up from 1 last week", o["captions"][2])
        # one scale per chart: a bar is its count times the same factor, so 2 is twice 1 and the tallest fills the plot
        a = o["actions"]
        opened = [b for b in a if "fl-op" in b["cls"]]
        self.assertEqual([b["v"] for b in opened], [0, 2, 1, 2, 0, 1, 1, 2])
        unit = 98 / 2                                                                                  # plot height (150 - 22 - 30) over the largest count
        for b in a:
            self.assertAlmostEqual(b["h"], b["v"] * unit, delta=0.02, msg=b)
        self.assertEqual([b["wk"] for b in opened][-1], "2026-10-14")
        for b in o["risks"]:
            self.assertAlmostEqual(b["h"], b["v"] * 98, delta=0.02)                                    # largest 1: the full height
        self.assertEqual([b["v"] for b in o["overdue"]], [0, 0, 0, 0, 0, 2, 1, 2])
        self.assertEqual(o["labels"][0:2], ["2", "0"])                                                 # the scale: the largest count, and zero
        self.assertEqual(o["labels"][2:], ["28-08", "04-09", "11-09", "18-09", "25-09", "02-10", "09-10", "16-10"])   # each week's Friday, DD-MM
        self.assertEqual(len(o["labels"]), 8 + 2)                                                      # eight weeks, the largest count and zero
        self.assertTrue({"opened", "closed"} <= set(o["legend"]))                                      # a legend in words
        self.assertEqual([x["v"] for x in o["hbars"]], [3, 1, 2, 3])
        self.assertAlmostEqual(o["hbars"][0]["w"] / o["hbars"][1]["w"], 3, delta=0.02)                 # to scale
        self.assertAlmostEqual(o["hbars"][3]["w"], o["hbars"][0]["w"], delta=0.02)
        self.assertEqual([x["v"] for x in o["mix"]], [1, 1])                                           # Urgent and High
        self.assertAlmostEqual(o["mix"][0]["w"], o["mix"][1]["w"], delta=0.02)
        self.assertEqual(o["summary"], "This week: 3 opened, 0 closed; 2 overdue, up from 1; the oldest open action is 36 days old.")
        self.assertEqual(o["oldest"], ["raid:ABC-010", "actions:ABC-A-003", "raid:ABC-011"])
        self.assertTrue(all(a.startswith(("Actions", "Risks", "Overdue", "Open")) for a in o["aria"]))

    def test_the_oldest_open_items_open_their_panel_and_the_card_shows_milestone_movement(self):
        o = self.probe("""
          go("cockpit","ABC"); const c=document.getElementById("flowCard"), out={}; out.text=c.textContent.replace(/\\s+/g," ");
          c.querySelector('[data-open="actions:ABC-A-003"]').click(); out.opened=[!!CUR,CUR&&CUR.id]; window.OUT=out;""")
        self.assertEqual(o["opened"], [True, "ABC-A-003"])
        self.assertIn("3 forecast moves in 8 weeks, 18 days later in all", o["text"])
        self.assertIn("UAT start: 2 moves, 21 days later", o["text"])
        self.assertIn("Build complete: 1 move, 3 days earlier", o["text"])
        self.assertIn("3 opened, 1 closed in 8 weeks", o["text"])                                      # risks and issues
        self.assertIn("counts only", o["text"])

    def test_colours_are_the_themes_and_readable_in_every_mode_with_a_colour_blind_safe_pair(self):
        o = self.probe("""
          go("cockpit","ABC"); const out={}, hue=c=>{ const [r,g,b]=c.match(/[\\d.]+/g).slice(0,3).map(Number).map(v=>v/255), mx=Math.max(r,g,b), mn=Math.min(r,g,b), d=mx-mn; if(!d) return null;
            const h=mx===r?((g-b)/d)%6:mx===g?(b-r)/d+2:(r-g)/d+4; return ((h*60)+360)%360; };
          for(const pal of TEST_PALETTES) for(const mode of ["Light","Dark"]){ S.palette=pal; S.theme=mode; applyTheme(); renderCockpit("ABC"); const c=document.getElementById("flowCard"), bg=__bgOf(c);
            const fill=s=>getComputedStyle(c.querySelector(s)).fill, root=getComputedStyle(document.documentElement), tok=n=>{ const e=document.createElement("i"); e.style.color=`var(${n})`; c.appendChild(e); const v=getComputedStyle(e).color; e.remove(); return v; };
            const op=fill("rect.fl-op[data-v]"), cl=fill("rect.fl-cl[data-v]"), od=fill("rect.fl-od[data-v]");
            const dh=(a,b)=>{ const x=hue(a), y=hue(b); if(x===null||y===null) return null; const d=Math.abs(x-y); return Math.min(d,360-d); };
            out[pal+"|"+mode]={op:__ratio(op,bg), cl:__ratio(cl,bg), od:__ratio(od,bg), muted:__ratio(fill("rect.fl-pL")||tok("--muted"),bg), pair:__ratio(op,cl), hue:dh(op,cl),
              text:__ratio(getComputedStyle(c.querySelector("text.fl-t")).fill,bg), small:__ratio(getComputedStyle(c.querySelector("text.fl-m")).fill,bg), hatched:c.querySelectorAll("rect.fl-cl[data-v] ~ rect.fl-hatch, rect.fl-hatch").length>0&&getComputedStyle(c.querySelector("pattern .fl-hp")).fill!=="none", isAccent:op===tok("--accent"), isWarn:cl===tok("--ink")   /* #341 item 17: closed bars are the neutral ink, amber is for At risk */, isBad:od===tok("--bad")}; }
          window.OUT=out;""".replace("TEST_PALETTES", TEST_PALETTES_JS))
        self.assertEqual(len(o), theme_count() * 2)                                                     # every theme, light and dark
        for key, r in o.items():
            for k in ("op", "cl", "od"):
                self.assertGreaterEqual(r[k], 3.0, (key, k))                                            # bars against the card: 3:1
            self.assertGreaterEqual(r["text"], 4.5, key)
            self.assertGreaterEqual(r["small"], 4.5, key)
            self.assertTrue(r["isAccent"] and r["isWarn"] and r["isBad"], key)                         # the theme's own tokens
            self.assertTrue(r["hatched"], key)                                                           # closed bars are hatched, not only coloured
            self.assertTrue((r["hue"] is not None and r["hue"] >= 40) or r["pair"] >= 1.5, (key, r))   # and the pair is still two colours


# ===== BL-90 part 1: dependencies, with no schema change =====

DEPNOW = d(0) + " 09:00"                      # the page works out "today" from the browser's clock, so these dates are relative to the real today


def dmy(n):
    return d(n)[8:] + "-" + d(n)[5:7] + "-" + d(n)[:4]


def subst(js):
    """The page scripts name dates relative to today: __D6__ is DD-MM-YYYY, six days on."""
    return js.replace("__D6__", dmy(6)).replace("__D40__", dmy(40))


def dep_vault():
    """Dependencies attached to milestones (a milestone link on a Dependency), with and without date trouble. Dates are relative to today."""
    v = Vault()
    v.run("init")
    reg = v.root / "projects/_portfolio/project-register.md"
    reg.write_text(reg.read_text().replace("|  |  |  |  |  |  |  |  |", "| DEF | Digital Enablement | DEF Digital Enablement | Enable | Sam (sponsor) | def.example | DEF core | portal |"))
    v.run("init")
    src = "Alan (cx-edit)"
    dep = lambda n, text, **kw: item("raid", n, project=kw.pop("project", "ABC"), type="Dependency", description=text, impact="Medium", likelihood="Medium",   # noqa: E731
                                     raised=d(-13), source=src, **kw)
    v.propose("deps", [
        item("milestones", 1, project="ABC", name="UAT start", baseline_date=d(6), forecast_date=d(10), source=src),          # ABC-M-001
        item("milestones", 2, project="ABC", name="Go-live", baseline_date=d(37), forecast_date=d(37), source=src),            # ABC-M-002
        item("milestones", 3, project="ABC", name="Hypercare", baseline_date=d(62), forecast_date=d(62), source=src),         # ABC-M-003
        item("milestones", 4, project="ABC", name="Closure", baseline_date=d(98), forecast_date=d(98), source=src),           # ABC-M-004
        item("milestones", 5, project="ABC", name="Build complete", baseline_date=d(-13), forecast_date=d(-13), status="Done", source=src),   # ABC-M-005
        dep(10, "Data extract from the client", due_date=d(16), milestone="ABC-M-001", owner="Client IT"),         # due after UAT start: warning
        dep(11, "Test environment ready", due_date=d(6), milestone="ABC-M-001", owner="Sara Example"),            # before it: fine
        dep(12, "Security approval", due_date=d(-4), milestone="ABC-M-001", owner="Client security"),              # overdue, UAT start is 10 days off: warning
        dep(13, "Licences purchased", due_date=d(-13), milestone="ABC-M-002", owner="Omar Ali"),                    # overdue, but go-live is 37 days off
        dep(14, "Legal sign-off", due_date=d(14), owner="Jane Doe"),                                                # not attached
        dep(15, "Closed dependency", due_date=d(47), milestone="ABC-M-001", owner="Sara Example", status="Closed", closed=d(-2)),
        dep(16, "On a finished milestone", due_date=d(16), milestone="ABC-M-005", owner="Sara Example"),           # its milestone is Done
        item("raid", 17, project="ABC", type="Risk", description="A risk with a milestone", impact="High", likelihood="High", raised=d(-13),
             due_date=d(16), milestone="ABC-M-001", source=src),                                                  # not a dependency
        dep(18, "Another project's dependency", project="DEF", due_date=d(16), owner="Sam"),
    ])
    v.run("apply")
    return v


def dep_ids(v):
    return {r["description"]: r["id"] for r in v.rows("raid")}


class DependencyWarningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = dep_vault()
        cls.ids = dep_ids(cls.v)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def warnings(self, now=DEPNOW):
        return json.loads(py(self.v, "import json, paths, build_dashboard as b\nfrom datetime import date\n"
                             f"print(json.dumps([w for w in b.early_warnings(paths.load_settings(), date.fromisoformat('{now[:10]}')) if w['sig'] == 'dependency']))", now))

    def test_a_dependency_due_after_what_it_blocks_and_an_overdue_one_near_it(self):
        i = self.ids
        got = {w["id"]: w for w in self.warnings()}
        self.assertEqual(set(got), {i["Data extract from the client"], i["Security approval"]})
        w = got[i["Data extract from the client"]]
        self.assertEqual((w["k"], w["p"], w["ms"]), ("raid", "ABC", "ABC-M-001"))
        self.assertEqual(w["text"], f"ABC-M-001 forecast {dmy(10)}, but dependency {i['Data extract from the client']} isn't due until {dmy(16)}")
        self.assertEqual(got[i["Security approval"]]["text"],
                         f"Dependency {i['Security approval']} is overdue (due {dmy(-4)}) and ABC-M-001 is forecast for {dmy(10)}")
        quiet = {i[t] for t in ("Test environment ready", "Licences purchased", "Legal sign-off", "Closed dependency", "On a finished milestone",
                                "A risk with a milestone", "Another project's dependency")}
        self.assertFalse(quiet & set(got))                                                              # nothing for the rest

    def test_the_setting_switches_it_off_and_moves_the_near_days(self):
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        try:
            data["warnings"]["dependency"] = {"on": True, "near_days": 40}
            cfg.write_text(json.dumps(data))
            self.assertIn(self.ids["Licences purchased"], {w["id"] for w in self.warnings()})           # now go-live counts as near
            data["warnings"]["dependency"] = {"on": False, "near_days": 14}
            cfg.write_text(json.dumps(data))
            self.assertEqual(self.warnings(), [])
        finally:
            data["warnings"]["dependency"] = {"on": True, "near_days": 14}
            cfg.write_text(json.dumps(data))

    def test_it_follows_the_dates(self):
        later = (_cx_today() + timedelta(days=12)).isoformat() + " 09:00"                              # UAT start has passed its forecast by then
        self.assertIn(self.ids["Data extract from the client"], {w["id"] for w in self.warnings(later)})
        self.assertEqual(len(self.warnings()), 2)

    def test_nothing_is_stored(self):
        import sqlite3
        with sqlite3.connect(self.v.root / "system/tracker.db") as con:
            self.assertFalse([t for (t,) in con.execute("select name from sqlite_master where type='table'")
                              if ("link" in t or "depend" in t) and t != "links"])
            self.assertEqual(con.execute("select count(*) from links").fetchone()[0], 0)    # the warning isn't stored as a link (the table is BL-90 part 2, Sprint 5)


class DependencyPageTests(unittest.TestCase):
    """The card, the marks, the suggestion chips and Work's filter, in the browser (file mode, today fixed)."""

    @classmethod
    def setUpClass(cls):
        if not CHROME.exists():
            raise unittest.SkipTest("Google Chrome not installed")
        cls.v = dep_vault()
        cls.ids = dep_ids(cls.v)
        py(cls.v, "import build_dashboard as b\nb.build()", DEPNOW)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def probe(self, script):
        out, errors = chrome(self.v, "VSTATE='ok'; " + CONTRAST_JS + ";const wait=ms=>new Promise(r=>setTimeout(r,ms)); " + script, name="deps")
        self.assertEqual(errors, [])
        self.assertIsNotNone(out)
        self.assertNotIn("error", out, out)
        return out

    def test_the_dependencies_card_groups_by_what_they_block(self):
        i = self.ids
        o = self.probe("""
          go("cockpit","ABC"); const c=document.getElementById("depCard"), out={};
          out.head=c.querySelector("h2").textContent.replace(/\\s+/g," ").trim();
          out.groups=[...c.querySelectorAll(".depg")].map(g=>({g:g.dataset.g,head:g.querySelector(".depgh").textContent.replace(/\\s+/g," ").trim(),rows:[...g.querySelectorAll(".deprow")].map(r=>({id:r.dataset.open,text:r.querySelector(".dept").textContent,warn:(r.querySelector(".depwarn")||{}).textContent||"",late:!!r.querySelector(".late"),who:r.textContent}))}));
          out.below=document.getElementById("depCard").previousElementSibling.querySelector("h2").textContent;
          window.OUT=out;""")
        self.assertEqual(o["head"], "Dependencies · 6 · 2 at risk")                                    # open ones only (one is on a finished milestone); two have a date warning
        groups = o["groups"]
        self.assertEqual([g["g"] for g in groups], ["ABC-M-005", "ABC-M-001", "ABC-M-002", ""])         # by milestone date (the finished one is earliest); unattached last
        g1 = next(g for g in groups if g["g"] == "ABC-M-001")
        self.assertIn("UAT start", g1["head"])
        self.assertIn(f"forecast {dmy(10)}", g1["head"])
        self.assertEqual([r["id"] for r in g1["rows"]], [f"raid:{i['Data extract from the client']}", f"raid:{i['Test environment ready']}", f"raid:{i['Security approval']}"])
        self.assertIn(f"isn't due until {dmy(16)}", g1["rows"][0]["warn"])
        self.assertEqual(g1["rows"][1]["warn"], "")
        self.assertTrue(g1["rows"][2]["late"])                                                          # the overdue one's date in the late style
        self.assertIn("Client IT", g1["rows"][0]["who"])                                                # an outside party is its owner
        self.assertIn("Not attached", groups[3]["head"])
        self.assertEqual([r["text"] for r in groups[3]["rows"]], ["Legal sign-off"])
        flat = " ".join(r["text"] for g in groups for r in g["rows"])
        for out_ in ("Closed dependency", "A risk with a milestone", "Another project"):
            self.assertNotIn(out_, flat)
        self.assertEqual(o["below"], "Recent decisions")

    def test_the_card_is_absent_when_there_are_no_open_dependencies(self):
        o = self.probe("""go("cockpit","DEF"); R.filter(r=>r.p==="DEF").forEach(r=>r.st="Closed"); renderCockpit("DEF"); window.OUT={n:document.querySelectorAll("#depCard").length};""")
        self.assertEqual(o["n"], 0)

    def test_a_blocked_milestone_shows_waiting_on_and_an_at_risk_mark(self):
        i = self.ids
        o = self.probe("""
          MVAUD="int";   /* BL-244: Client is the first-visit view; "waiting on" is internal only (BL-90) */
          go("cockpit","ABC"); const rows=[...document.querySelectorAll("#mvCard .mv-prow[data-mvedit]")], out={};   /* BL-186: the card's Plan rows */
          out.rows=rows.map(r=>({id:r.dataset.mvedit,risk:r.classList.contains("atrisk"),tag:(r.querySelector(".waiting")||{}).textContent||"",title:(r.querySelector(".waiting")||{}).title||""}));
          document.querySelector("#depCard [data-ms=ABC-M-001]").click(); await wait(50); out.panel=[VIEW,MSCODE,MV.peek]; window.OUT=out;""")
        by = {r["id"]: r for r in o["rows"]}
        uat = by["ABC-M-001"]
        self.assertTrue(uat["risk"])
        self.assertEqual(uat["tag"], f"waiting on {i['Data extract from the client']}, {i['Security approval']}")
        self.assertIn(f"isn't due until {dmy(16)}", uat["title"])
        for quiet in ("ABC-M-002", "ABC-M-003", "ABC-M-004"):
            self.assertFalse(by[quiet]["risk"], quiet)                                                  # a late dependency far off doesn't mark go-live
        self.assertEqual(o["panel"], ["milestones", "ABC", "ABC-M-001"])                                 # BL-186: the Milestones page, its editor open

    def test_the_warning_flags_the_dependency_in_work_and_the_panel(self):
        i = self.ids
        o = self.probe(f"""
          WT="raid"; applyView("open"); go("work"); const flagged=[...document.querySelectorAll("#workTbl tr[data-row]")].filter(r=>r.querySelector(".wflag")&&warnsOf("raid",r.dataset.row).some(w=>w.sig==="dependency")).map(r=>r.dataset.row);   /* BL-181: a weekend due date flags too */
          openRecord("raid","{i['Data extract from the client']}"); window.OUT={{flagged, note:(document.getElementById("pkWarn")||{{}}).textContent||""}};   /* BL-176: the peek's warning line */""")
        self.assertEqual(sorted(o["flagged"]), sorted([i["Data extract from the client"], i["Security approval"]]))
        self.assertIn(f"isn't due until {dmy(16)}", o["note"])

    def test_suggested_milestones_appear_as_chips_in_the_panel_and_are_never_attached_by_themselves(self):
        i = self.ids
        o = self.probe(subst("""
          go("work"); WT="raid"; openNew("raid"); const out={}, set=(n,v)=>{ CUR.draft[n]=n==="due"&&DDATE.test(v)?toIso(v):v; pkDraw(); };   /* BL-179: the new item is the peek; its draft as the chips leave it */
          const chips=()=>[...document.querySelectorAll("#depSug button")].map(b=>b.textContent);
          set("p","ABC"); out.risk=chips();                                                            // a Risk: no chips
          set("type","Dependency"); out.noDue=chips();                                                  // no due date: nothing to compare with
          set("t","Vendor access"); set("due","__D6__"); out.chips=chips();
          out.msStill=CUR.draft.ms;                                                                     // nothing attached by itself
          set("due","__D40__"); out.later=chips(); set("due","__D6__");
          document.querySelector("[data-pkdep=ABC-M-002]").click(); await pkQuiet(); out.attached=[CUR.draft.ms,chips()];
          set("ms",""); out.again=chips().length; document.querySelector("[data-pkdepnone]").click(); out.none=chips();
          set("t","Vendor access, revised"); out.textChanged=chips().length; window.OUT=out;"""))
        self.assertEqual(o["risk"], [])
        self.assertEqual(o["noDue"], [])
        self.assertEqual(o["chips"], [f"Attach to ABC-M-001 (forecast {dmy(10)})?", f"Attach to ABC-M-002 (forecast {dmy(37)})?",
                                      f"Attach to ABC-M-003 (forecast {dmy(62)})?", "None needed"])    # up to three, nearest first; Done ones never; then None needed
        self.assertEqual(o["msStill"], "")
        self.assertEqual(o["later"], [f"Attach to ABC-M-003 (forecast {dmy(62)})?", f"Attach to ABC-M-004 (forecast {dmy(98)})?", "None needed"])   # only those it could threaten
        self.assertEqual(o["attached"], ["ABC-M-002", []])                                              # a click attaches it; the chips go
        self.assertEqual(o["again"], 4)
        self.assertEqual(o["none"], [])                                                                 # "None needed" is remembered
        self.assertEqual(o["textChanged"], 4)                                                           # until its text changes

    def test_work_has_an_unattached_dependencies_view_and_filter(self):
        i = self.ids
        o = self.probe("""
          WT="raid"; go("work"); const out={};
          out.views=allViews("raid").map(v=>v.label); applyView("unatt"); renderWork(); out.rows=rows().map(x=>x.id).sort(); out.chips=[...document.querySelectorAll("#wapplied .fchip")].map(c=>c.firstChild.textContent.trim());
          out.sub=[...document.querySelectorAll("#workTbl tr[data-row]")].map(r=>r.querySelector("td.title .x").textContent.trim());
          out.hash=hashOf(navState()); out.parsed=parseHash("#work=raid&st=Open&ty=Dependency&ms=no").fx;
          WT="raid"; applyView("open"); renderWork(); out.attachedSub=[...document.querySelectorAll("#workTbl tr[data-row]")].filter(r=>r.dataset.row==="%s").map(r=>r.querySelector("td.title .x").textContent.trim());
          out.more=(defs().find(d=>d[0]==="ms")||[])[1]; window.OUT=out;""" % i["Data extract from the client"])
        self.assertIn("Unattached dependencies", o["views"])
        self.assertEqual(o["rows"], sorted([self.ids["Legal sign-off"], self.ids["Another project's dependency"]]))   # open dependencies with no milestone, in any project
        self.assertTrue(all("not attached" in s for s in o["sub"]), o["sub"])                           # a quiet tag on each
        self.assertIn("Milestone: Not attached", " ".join(o["chips"]))
        self.assertIn("v=unatt", o["hash"])
        self.assertEqual(o["parsed"], {"st": ["Open"], "ty": ["Dependency"], "ms": ["no"]})
        self.assertNotIn("not attached", " ".join(o["attachedSub"]))
        self.assertEqual(o["more"], "Milestone")

    def test_readable_in_every_theme_and_mode(self):
        o = self.probe(subst("""
          MVAUD="int";   /* BL-244: the internal "waiting on" mark is checked too */
          const out={}; for(const pal of TEST_PALETTES) for(const mode of ["Light","Dark"]){ S.palette=pal; S.theme=mode; applyTheme(); go("cockpit","ABC"); const c=document.getElementById("depCard"), bg=__bgOf(c), css=s=>getComputedStyle(c.querySelector(s));
            const m=document.querySelector("#mvCard .mv-prow.atrisk .waiting"); out[pal+"|"+mode]={warn:__ratio(css(".depwarn").color,bg), text:__ratio(css(".dept").color,bg), id:__ratio(css(".depid").color,bg), tag:__ratio(getComputedStyle(m).color,__bgOf(m))};
            go("work"); WT="raid"; openNew("raid"); Object.assign(CUR.draft,{p:"ABC",type:"Dependency",due:toIso("__D6__")}); pkDraw();   /* BL-179: the peek's suggestions */
            const b=document.querySelector("#depSug .chipbtn"), cs=getComputedStyle(b); out[pal+"|"+mode].chip=__ratio(cs.color,cs.backgroundColor); out[pal+"|"+mode].chipEdge=__ratio(cs.borderTopColor,__bgOf(b.parentElement)); closePanel(); }
          window.OUT=out;""".replace("TEST_PALETTES", TEST_PALETTES_JS)))
        self.assertEqual(len(o), theme_count() * 2)
        bad = {k: {n: round(x, 2) for n, x in v.items() if x < (3.0 if n == "chipEdge" else 4.5)} for k, v in o.items()}
        self.assertEqual({k: v for k, v in bad.items() if v}, {})


class DependencyNearDaysSetting(LiveBrowserCase):
    """Settings › Early warnings: the dependency signal's switch and its "near" days, saved to settings.json and applied to the flags."""

    @classmethod
    def load(cls, v):
        d = dep_vault()                                   # (builds its own vault; copy its data into this one)
        try:
            import shutil as sh
            sh.copy2(d.root / "system/tracker.db", v.root / "system/tracker.db")
        finally:
            d.cleanup()

    def test_the_near_days_are_set_in_settings_and_change_the_warnings(self):
        b = self.b
        licences = next(r["id"] for r in self.v.rows("raid") if r["description"] == "Licences purchased")   # overdue; its milestone is 37 days off
        b.eval("go('settings','warnings')")
        b.wait("document.querySelector('[data-wk=\"dependency.near_days\"]')")          # BL-320: Early warnings are in Advanced
        label = b.eval("document.querySelector('[data-wk=\"dependency.near_days\"]').closest('.srow').textContent.replace(/\\s+/g,' ').trim()")
        self.assertIn("Overdue counts when the milestone is within (days)", label)
        self.assertEqual(b.eval("document.querySelector('[data-wk=\"dependency.near_days\"]').value"), "14")
        self.assertIn("Dependency due after what it blocks", b.eval("document.getElementById('warnSettings').textContent"))
        self.assertFalse(b.eval("WARNS().some(w=>w.id===%s && w.sig==='dependency')" % json.dumps(licences)))
        b.eval("(()=>{ const i=document.querySelector('[data-wk=\"dependency.near_days\"]'); i.value=40; i.dispatchEvent(new Event('change',{bubbles:true})); })()")
        b.wait("WARNS().some(w=>w.id===%s && w.sig==='dependency')" % json.dumps(licences), 15)               # the flags updated at once
        saved = json.loads((self.v.root / "system/config/settings.json").read_text())["warnings"]["dependency"]
        self.assertEqual(saved, {"on": True, "near_days": 40})
        b.eval("(()=>{ const i=document.querySelector('[data-wk=\"dependency.on\"]'); i.checked=false; i.dispatchEvent(new Event('change',{bubbles:true})); })()")
        b.wait("!WARNS().some(w=>w.sig==='dependency')", 15)                                                  # switched off: none
        self.assertIs(json.loads((self.v.root / "system/config/settings.json").read_text())["warnings"]["dependency"]["on"], False)


if __name__ == "__main__":
    unittest.main()
