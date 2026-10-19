"""#238 Usage and context monitor: usage_report.py --json (the Usage tab's figures), context_size.py (what every run loads,
measured once a day, counts only), usage_reviews.py (Alan's own dated notes) and D.usage. Fixed dates only.

Run: python3 dev/tests/test_usage_monitor.py
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
NOW = "2026-10-19 09:00"
os.environ.setdefault("CREAITE_NOW", NOW)      # the live server and the page share the fixed day
sys.path.insert(0, str(REPO / "system" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import context_size  # noqa: E402
import usage_report  # noqa: E402
import usage_reviews  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402

TODAY = date(2026, 10, 19)


def run(day, kind, cost, start, skills=(), label="Chat"):
    """One run-usage line as usage_log.py writes it."""
    return {"at": f"{day}T10:00:00", "kind": kind, "label": label, "model": "claude-sonnet-5-5", "seconds": 4.0, "turns": 2,
            "input": 1000, "output": 100, "cache_read": 20000, "cache_create": 0, "cost_usd": cost, "start_tokens": start,
            "stopped": False, "skills": list(skills)}


FIXTURE = [run("2026-10-19", "ask", 0.10, 21000, ["cx-minutes"]), run("2026-10-19", "ask", 0.20, 22000),
           run("2026-10-19", "ask", 0.30, 23000), run("2026-10-15", "sweep", 0.40, 20000, ["cx-sweep"]),
           run("2026-10-08", "ask", 0.25, 20000), run("2026-10-08", "ask", 0.25, 20000),
           run("2026-09-01", "prep", 5.00, 19000, ["cx-steerco"])]


def write_usage(root, rows=FIXTURE):
    f = Path(root) / "system" / "staging" / "run-usage.jsonl"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def write_context(root, rules_bytes):
    """A record with the rules 2 KB smaller on 15-09 and at today's size since 12-10; the rest unchanged."""
    f = Path(root) / "system" / "staging" / "context-size.jsonl"
    f.parent.mkdir(parents=True, exist_ok=True)
    lines = [{"date": "2026-09-15", "file": "rules", "bytes": rules_bytes - 2048, "tokens": 1, "files": 1},
             {"date": "2026-10-12", "file": "rules", "bytes": rules_bytes, "tokens": 1, "files": 1}]
    f.write_text("".join(json.dumps(x) + "\n" for x in lines), encoding="utf-8")


class Page(unittest.TestCase):
    def setUp(self):
        self.p = usage_report.page(FIXTURE, TODAY, skills_dir=REPO / ".claude" / "skills")

    def test_cards_compare_with_the_previous_week(self):
        c = self.p["cards"]
        self.assertEqual((c["week"]["cost_usd"], c["previous"]["cost_usd"], c["change"]["cost_pct"]), (1.0, 0.5, 100))
        self.assertEqual((c["week"]["runs"], c["previous"]["runs"], c["change"]["runs_pct"]), (4, 2, 100))
        self.assertEqual((c["week"]["start_median"], c["previous"]["start_median"], c["change"]["start_tokens"]), (21500, 20000, 1500))
        self.assertEqual((c["week"]["avg_cost_usd"], c["change"]["avg_cost_pct"]), (0.25, 0))

    def test_daily_has_fourteen_days_oldest_first(self):
        d = self.p["daily"]
        self.assertEqual((len(d), d[0]["day"], d[-1]["day"]), (14, "2026-10-06", "2026-10-19"))
        self.assertEqual((d[-1]["runs"], d[-1]["cost_usd"], d[-1]["start_median"]), (3, 0.6, 22000))
        self.assertIsNone(d[1]["start_median"])            # 07-10: no runs

    def test_by_kind_rows_and_share(self):
        self.assertEqual([(k["kind"], k["runs"], k["cost_usd"], k["share"], k["start_median"], k["avg_tokens"]) for k in self.p["kinds"]],
                         [("ask", 5, 1.1, 0.7333, 21000, 21100), ("sweep", 1, 0.4, 0.2667, 20000, 21100)])

    def test_skills_flag_never_in_this_period(self):
        s = {x["skill"]: x for x in self.p["skills"]}
        self.assertEqual((s["cx-minutes"]["runs"], s["cx-minutes"]["cost_usd"], s["cx-minutes"]["last"]), (1, 0.1, "2026-10-19"))
        self.assertEqual((s["cx-sweep"]["runs"], s["cx-sweep"]["last"], s["cx-sweep"]["never_in_period"]), (1, "2026-10-15", False))
        self.assertEqual((s["cx-steerco"]["runs"], s["cx-steerco"]["never_in_period"], s["cx-steerco"]["days_since"]), (0, True, 48))
        self.assertEqual((s["cx-setup"]["last"], s["cx-setup"]["days_since"], s["cx-setup"]["never_in_period"]), (None, None, True))

    def test_no_text_field_reaches_the_page(self):
        text = json.dumps(self.p)
        for leak in ("Chat", "claude-sonnet", "label", "model"):
            self.assertNotIn(leak, text)

    def test_empty_record(self):
        p = usage_report.page([], TODAY)
        self.assertTrue(p["empty"])
        self.assertEqual((p["runs"], p["kinds"], p["cards"]["change"]["cost_pct"]), (0, [], None))

    def test_json_flag_prints_the_page(self):
        with tempfile.TemporaryDirectory() as t:
            f = Path(t) / "u.jsonl"
            f.write_text("".join(json.dumps(r) + "\n" for r in FIXTURE))
            out = subprocess.run([sys.executable, str(REPO / "system/scripts/usage_report.py"), "--json", "--file", str(f)],
                                 env={**os.environ, "CREAITE_NOW": NOW}, capture_output=True, text=True, check=True).stdout
        self.assertEqual(json.loads(out)["cards"]["week"]["runs"], 4)


class ContextSize(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.root = Path(self.t.name)
        (self.root / "system").mkdir()
        (self.root / "system" / "creaite-rules.md").write_text("r" * 52000)
        (self.root / "CLAUDE.md").write_text("c" * 700)
        for folder, files in (("ABC Example Client Programme", ["CLAUDE.md"]), ("_portfolio", ["PORTFOLIO.md", "project-register.md"])):
            (self.root / "projects" / folder).mkdir(parents=True)
            for n in files:
                (self.root / "projects" / folder / n).write_text("m" * 1000)
        sk = self.root / ".claude" / "skills" / "cx-demo"
        sk.mkdir(parents=True)
        (sk / "SKILL.md").write_text("---\nname: cx-demo\ndescription: a demo\n---\n" + "BODY TEXT " * 500)

    def tearDown(self):
        self.t.cleanup()

    def lines(self):
        return [json.loads(x) for x in (self.root / "system/staging/context-size.jsonl").read_text().splitlines()]

    def test_measures_each_group(self):
        m = {x["file"]: x for x in context_size.measure(self.root)}
        self.assertEqual((m["rules"]["bytes"], m["rules"]["tokens"]), (52000, 13000))
        self.assertEqual((m["memory"]["bytes"], m["memory"]["files"]), (3000, 3))
        self.assertEqual(m["skills"]["bytes"], len("---\nname: cx-demo\ndescription: a demo\n---"))

    def test_daily_lines_are_counts_only_and_once_a_day(self):
        context_size.record_daily(self.root, TODAY)
        self.assertIsNone(context_size.record_daily(self.root, TODAY))
        got = self.lines()
        self.assertEqual([x["file"] for x in got], list(context_size.GROUPS))
        for x in got:
            self.assertEqual(sorted(x), ["bytes", "date", "file", "files", "tokens"])
            self.assertTrue(all(isinstance(x[k], int) for k in ("bytes", "tokens", "files")))
        text = json.dumps(got)
        for leak in ("Example Client", "ABC", "BODY", "demo", "/"):
            self.assertNotIn(leak, text)

    def test_never_in_the_development_repository(self):
        (self.root / ".creaite-dev").write_text("")
        self.assertIsNone(context_size.record_daily(self.root, TODAY))
        self.assertFalse((self.root / "system/staging/context-size.jsonl").exists())

    def test_change_in_thirty_days_from_the_record(self):
        write_context(self.root, 52000)
        rows = {r["file"]: r for r in context_size.table(self.root, TODAY)}
        self.assertEqual((rows["rules"]["change_bytes"], rows["rules"]["changed_on"]), (2048, "2026-10-12"))
        self.assertEqual((rows["claude_md"]["change_bytes"], rows["claude_md"]["changed_on"]), (None, None))

    def test_daily_line_for_the_server(self):
        self.assertIn("tokens", context_size.daily_line(self.root))
        self.assertIsNone(context_size.daily_line(self.root))


class Reviews(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.root = Path(self.t.name)

    def tearDown(self):
        self.t.cleanup()

    def test_only_the_three_fields_are_kept(self):
        notes, why = usage_reviews.add({"date": "2026-10-12", "saw": "Start load  about\n21,000", "decided": "Trim the rules",
                                        "who": "Jane Doe", "path": "/Users/x"}, self.root)
        self.assertIsNone(why)
        self.assertEqual(notes, [{"date": "2026-10-12", "saw": "Start load about 21,000", "decided": "Trim the rules"}])
        line = (self.root / "system/staging/usage-reviews.jsonl").read_text()
        self.assertNotIn("Jane", line)
        self.assertNotIn("/Users", line)

    def test_refused_without_a_day_or_a_note(self):
        self.assertIsNotNone(usage_reviews.add({"date": "12-10-2026", "saw": "x"}, self.root)[1])
        self.assertIsNotNone(usage_reviews.add({"date": "2026-10-12"}, self.root)[1])
        self.assertEqual(len(usage_reviews.add({"date": "2026-10-12", "saw": "x" * 500}, self.root)[0][0]["saw"]), 200)

    def test_route_table_for_the_live_server(self):
        import threading
        self.assertEqual(list(usage_reviews.routes(threading.Lock())), ["/api/usage/review"])


class NoReportReadsIt(unittest.TestCase):
    def test_no_report_or_export_reads_the_usage_figures(self):
        for name in ("report.py", "excel_sync.py", "prep_page.py", "status_facts.py", "docx_tools.py", "client_leak.py"):
            text = (REPO / "system/scripts" / name).read_text(encoding="utf-8")
            for mod in ("import usage_report", "import context_size", "import usage_reviews", '"usage"'):
                self.assertNotIn(mod, text, name)


class DashboardData(unittest.TestCase):
    def test_collect_carries_d_usage(self):
        from test_tracker import Vault
        v = Vault()
        self.addCleanup(v.cleanup)
        v.run("init")
        write_usage(v.root)
        write_context(v.root, (v.root / "system/creaite-rules.md").stat().st_size)
        out = subprocess.run([sys.executable, "-c", "import json,build_dashboard;print(json.dumps(build_dashboard.collect()['usage']))"],
                             cwd=v.root / "system/scripts", env={**os.environ, "CREAITE_NOW": NOW}, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        u = json.loads(out.stdout)
        self.assertEqual(u["cards"]["week"]["runs"], 4)
        self.assertEqual({r["file"]: r["change_bytes"] for r in u["context"]}["rules"], 2048)
        self.assertEqual(u["reviews"], [])


LIVE = (REPO / "system/scripts/live_server.py").read_text(encoding="utf-8")
ROUTE_APPLIED = "usage_reviews.routes(LOCK)" in LIVE          # dev/proposals/usage-monitor, applied by Jarvis


class LiveServerHook(unittest.TestCase):
    @unittest.skipUnless("context_size.daily_line()" in LIVE, "dev/proposals/usage-monitor not applied yet")
    def test_daily_job_records_the_context_size_once_a_day(self):
        import ast
        tree = ast.parse(LIVE)
        job = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "backup_daily_job")
        src = ast.get_source_segment(LIVE, job)
        self.assertLess(src.index(".creaite-dev"), src.index("context_size.daily_line()"))     # never in the development repository
        self.assertLess(src.index("backup.ask_run()"), src.index("context_size.daily_line()"))  # never from an ask creaite run

    @unittest.skipUnless("context_size.daily_line()" in LIVE, "dev/proposals/usage-monitor not applied yet")
    def test_daily_job_appends_counts_only_lines(self):
        from test_tracker import Vault
        v = Vault()
        self.addCleanup(v.cleanup)
        v.run("init")
        code = ("import sys, json; sys.path.insert(0, 'system/scripts'); import live_server as L; "
                "print(json.dumps([L.backup_daily_job(), L.backup_daily_job()]))")
        r = subprocess.run([sys.executable, "-c", code], cwd=v.root, capture_output=True, text=True, env={**os.environ, "CREAITE_NOW": NOW})
        first, second = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertTrue(any(x.startswith("context size recorded") for x in first), first)
        self.assertFalse(any(x.startswith("context size") for x in second), second)
        lines = [json.loads(x) for x in (v.root / "system/staging/context-size.jsonl").read_text().splitlines()]
        self.assertEqual({x["date"] for x in lines}, {"2026-10-19"})
        self.assertTrue(all(sorted(x) == ["bytes", "date", "file", "files", "tokens"] for x in lines))


class UsageTab(LiveBrowserCase):
    shared_server = True

    @classmethod
    def load(cls, v):
        populate(v)
        write_usage(v.root)
        write_context(v.root, (v.root / "system/creaite-rules.md").stat().st_size)

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": NOW}

    def open_usage(self):
        b = self.b
        b.eval("go('activity')")
        b.click("#actTabU")
        b.wait("document.querySelectorAll('#uKind tr').length>=2")
        return b

    def test_cards_rows_and_thirty_day_change(self):
        b = self.open_usage()
        cards = b.eval("[...document.querySelectorAll('#uSum .ucard')].map(c=>c.innerText.replace(/\\s+/g,' '))")
        self.assertEqual(cards, ["$1.00 Cost this week +100% on last week", "4 Runs this week +100% on last week",
                                 "21,500 Tokens a run loads before it starts (about) +1,500 on last week",
                                 "$0.25 Cost of an average run 0% on last week"])
        rows = b.eval("[...document.querySelectorAll('#uKind tr')].map(r=>[...r.cells].map(c=>c.textContent))")
        self.assertEqual(rows, [["ask creaite", "5", "21,100", "21,000", "$1.10", "73%"], ["Sweep", "1", "21,100", "20,000", "$0.40", "27%"]])
        ctx = b.eval("[...document.querySelectorAll('#uCtx tr')].map(r=>r.cells[0].textContent+' | '+r.cells[3].textContent)")
        self.assertIn("Rules (creaite-rules.md) | +2.0 KB since 12-10-2026", ctx)
        self.assertIn("Your CLAUDE.md | no earlier measure yet", ctx)
        steer = b.eval("[...document.querySelectorAll('#uSkill tr')].find(r=>r.cells[0].textContent==='cx-steerco').innerText")
        self.assertIn("never in this period (last 48 days ago)", steer)
        self.assertIn("estimates", b.eval("document.getElementById('actUsage').innerText"))
        self.assertEqual(b.eval("document.querySelectorAll('#uChart .ubar').length"), 14)
        self.assertEqual(b.eval("document.querySelectorAll('#uChart .udot').length"), 3)      # three days with runs
        self.assertTrue(b.eval("document.getElementById('actTbl').offsetParent===null"))     # the change list is behind its tab
        b.click("#actTabCh")
        self.assertTrue(b.eval("document.getElementById('actUsage').hidden"))
        self.assertEqual(b.errors, [])

    def test_review_note_form_and_csv(self):
        b = self.open_usage()
        self.assertIn("No review notes yet", b.eval("document.getElementById('uRev').innerText"))
        self.assertTrue(b.eval("document.getElementById('uRevForm').offsetParent===null"))      # the form shows only when asked for
        csv = b.eval("uCsv([{date:'2026-10-12',saw:'Start load \"21k\"',decided:'Trim, first'}])")
        self.assertEqual(csv, 'Date,What you saw,What you decided\r\n"12-10-2026","Start load ""21k""","Trim, first"\r\n')
        b.click("#uRevAdd")
        self.assertEqual(b.eval("document.getElementById('uRevDate').value"), "2026-10-19")
        b.eval("document.getElementById('uRevSaw').value='Start load up'")
        b.click("#uRevSave")
        b.wait("document.getElementById('uRevMsg').textContent!=='' || document.querySelectorAll('#uRev td.empty').length===0")
        saved = b.eval("document.querySelectorAll('#uRev td.empty').length===0")
        if not ROUTE_APPLIED:               # without the live server's route (dev/proposals/usage-monitor) it says so
            self.assertFalse(saved)
            self.assertIn("live server", b.eval("document.getElementById('uRevMsg').textContent"))
        else:
            self.assertTrue(saved)
            self.assertIn("Start load up", b.eval("document.getElementById('uRev').innerText"))
            self.assertTrue(b.eval("document.getElementById('uRevForm').offsetParent===null"))
            line = json.loads((self.v.root / "system/staging/usage-reviews.jsonl").read_text().splitlines()[-1])
            self.assertEqual(line, {"date": "2026-10-19", "saw": "Start load up", "decided": ""})

    def test_fits_at_900(self):
        b = self.open_usage()
        b.resize(900, 900)
        b.frames()
        self.assertLessEqual(b.eval("document.documentElement.scrollWidth-document.documentElement.clientWidth"), 0)
        self.assertLessEqual(b.eval("(()=>{const p=document.getElementById('actUsage');return p.scrollWidth-p.clientWidth})()"), 1)
        self.assertEqual(b.eval("getComputedStyle(document.getElementById('uSum')).gridTemplateColumns.split(' ').length"), 2)


class UsageTabEmpty(LiveBrowserCase):
    shared_server = True

    def test_no_runs_yet(self):
        b = self.b
        b.eval("go('activity')")
        b.click("#actTabU")
        b.wait("!document.getElementById('uEmpty').hidden")
        self.assertIn("No runs yet", b.eval("document.getElementById('uEmpty').textContent"))
        self.assertTrue(b.eval("document.getElementById('uRuns').offsetParent===null && document.getElementById('uRuns2').offsetParent===null"))
        self.assertTrue(b.eval("document.getElementById('uEmpty').offsetParent!==null"))
        self.assertEqual(b.errors, [])


if __name__ == "__main__":
    unittest.main()
