"""BL-03: reports, minutes and Steerco one-pagers moved into the engagement's own _Archive after 12 months (v1.9.5; Alan, 14-10-2026).

Run: python3 dev/tests/test_archive_reports.py     (quick tier: no Chrome; one live server)

What is covered, with the clock pinned (CREAITE_NOW):
- which files are due: weekly and client reports, minutes and Steerco one-pagers dated 12 months ago or more (by the date in
  their name), never transcripts, agendas, documents, ad hoc reports or an undated file; the period is a setting;
- the monthly Health line ("Archive 4 reports and minutes older than 12 months") with its Fix it; once archived this month it is
  quiet until next month;
- the one-click route: refused without the token and with a body; it only puts the moves on the approval card; Approve moves them
  through tracker.py apply; undo moves them back and removes the folders it made;
- stored paths still resolve; the archived files aren't indexed and ask creaite can't read them;
- reach.archive_move_problem's "reports" shape: one file of those folders into its own engagement's _Archive, nothing else;
- the same with the projects in a OneDrive-style folder (mapped folders).
Everything is fictional and temporary.
"""
import json
import os
import re
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_onedrive_projects import OneDriveCase, touch  # noqa: E402
from test_tracker import Vault  # noqa: E402

DAY = "2026-10-14 09:00"
ENV = {"CREAITE_NOW": DAY}


def vault_files(abc):
    """(due, kept): relative to the project folder."""
    due = ["minutes/2025-09-30 Steering committee.docx", "minutes/2025-10-14 Checkpoint.md",
           "reports/2025-10-03 Weekly report - Example Programme.docx", "reports/2025-01-09 Client report - Example Programme.docx",
           "reports/Steerco/2025-02-01 Example Programme Steerco one-pager.docx"]
    kept = ["minutes/2025-10-15 Checkpoint.md", "minutes/Notes without a date.md", "reports/2025-01-01 Actions register.docx",
            "reports/2026-10-09 Weekly report - Example Programme.docx", "transcripts/2024-01-01 Steering.vtt",
            "agendas/2024-01-01 Steering prep.html", "documents/2024-01-01 SOW.docx"]
    for f in due + kept:
        touch(abc / f, f"{f}: the wombat budget line\n")
    return due, kept


class VaultReports(unittest.TestCase):
    """The projects in the vault (projects/ABC Example Programme/…)."""

    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.abc = next(d for d in (self.v.root / "projects").iterdir() if d.name.startswith("ABC "))
        self.due, self.kept = vault_files(self.abc)

    def tearDown(self):
        self.v.cleanup()

    def run_at(self, *args, script="archive.py", ok=True):
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts" / script), *args], capture_output=True, text=True,
                           cwd=self.v.root, env={**os.environ, **ENV})
        if ok:
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def py(self, code):
        src = f"import sys, json; sys.path.insert(0, 'system/scripts')\n{code}"
        r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, cwd=self.v.root, env={**os.environ, **ENV})
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def doctor(self):
        r = self.run_at("--json", "--read-only", script="doctor.py", ok=False)
        return {c["id"]: c for c in json.loads(r.stdout.strip().splitlines()[-1])["checks"]}

    def stage_and_apply(self):
        spec = self.run_at("reports").stdout
        f = self.v.root / "system/staging/drafts/r.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(spec, encoding="utf-8")
        out = self.run_at("stage", str(f), script="propose.py").stdout
        self.run_at("apply", script="tracker.py")
        return out

    def test_the_due_files_and_the_health_line(self):
        spec = json.loads(self.run_at("reports").stdout)
        moves = {(o["from"], o["to"]) for o in spec["file_changes"]["file_ops"]}
        base = f"projects/{self.abc.name}"
        self.assertEqual(moves, {(f"{base}/{f}", f"{base}/_Archive/{f}") for f in self.due})
        self.assertEqual(spec["file_changes"]["archive"], "reports")
        self.assertEqual(spec["file_changes"]["title"], "Archive 5 reports and minutes older than 12 months")
        c = self.doctor()["archive_reports"]
        self.assertEqual(c["status"], "warn")
        self.assertTrue(c["detail"].startswith("Archive 5 reports and minutes older than 12 months: "), c["detail"])
        h = self.py(f"import health; print(json.dumps(health.health({json.dumps({'checks': [c]})})['problems']))")
        self.assertEqual(h[0]["title"], "Archive 5 reports and minutes older than 12 months")
        self.assertTrue(h[0]["fix"]["built"])
        self.assertEqual((h[0]["fix"]["id"], h[0]["fix"]["button"]), ("archive_reports", "Archive them"))
        cfg = self.v.root / "system/config/settings.json"                  # the period is a setting
        data = json.loads(cfg.read_text())
        data.setdefault("archive", {})["reports_after_months"] = 24
        cfg.write_text(json.dumps(data, indent=2))
        self.assertEqual(self.run_at("reports", ok=False).returncode, 1)
        self.assertEqual(self.doctor()["archive_reports"]["status"], "pass")

    def test_the_move_through_apply_resolves_is_not_indexed_and_undoes(self):
        preview = self.stage_and_apply()
        self.assertIn(f"Move file projects/{self.abc.name}/{self.due[0]} → projects/{self.abc.name}/_Archive/{self.due[0]}", preview)
        for f in self.due:
            self.assertFalse((self.abc / f).exists(), f)
            self.assertTrue((self.abc / "_Archive" / f).is_file(), f)        # its place below _Archive kept
        for f in self.kept:
            self.assertTrue((self.abc / f).is_file(), f)
        stored = [f"projects/{self.abc.name}/{f}" for f in self.due]
        o = self.py(f"import paths, reach, tracker; s = {stored!r}; print(json.dumps([[str(paths.resolve(x)) for x in s], "
                    "[reach.classify(x, 'read')[0] for x in s], [str(f) for f, _, _ in tracker.index_files()]]))")
        self.assertEqual(o[0], [str((self.abc / "_Archive" / f).resolve()) for f in self.due])   # stored paths still open
        self.assertEqual(set(o[1]), {"never"})                               # ask creaite can't read them
        self.assertFalse(any("/_Archive/" in f for f in o[2]))                # nor are they indexed
        self.assertTrue(any(f.endswith("2025-10-15 Checkpoint.md") for f in o[2]))
        c = self.doctor()["archive_reports"]                                  # quiet for the rest of the month
        self.assertEqual(c["status"], "pass")
        self.assertIn("Archived 5 reports and minutes on 14-10-2026", c["detail"])
        touch(self.abc / "minutes/2025-10-01 Late find.md")
        self.assertEqual(self.doctor()["archive_reports"]["status"], "pass")
        (self.abc / "minutes/2025-10-01 Late find.md").unlink()
        out = self.run_at("undo", script="tracker.py").stdout
        self.assertNotIn("skipped", out)
        for f in self.due:
            self.assertTrue((self.abc / f).is_file(), f)
        self.assertFalse((self.abc / "_Archive").exists())                   # the folders the move made are gone again

    def test_only_one_report_file_into_its_own_archive(self):
        b = f"projects/{self.abc.name}"
        (self.v.root / "projects/DEF Other").mkdir()
        cases = {
            "transcript": (f"{b}/transcripts/2024-01-01 Steering.vtt", f"{b}/_Archive/transcripts/2024-01-01 Steering.vtt"),
            "document": (f"{b}/documents/2024-01-01 SOW.docx", f"{b}/_Archive/documents/2024-01-01 SOW.docx"),
            "another engagement": (f"{b}/{self.due[0]}", f"projects/DEF Other/_Archive/{self.due[0]}"),
            "a different place": (f"{b}/{self.due[0]}", f"{b}/_Archive/reports/2025-09-30 Steering committee.docx"),
            "a folder": (f"{b}/minutes", f"{b}/_Archive/minutes"),
            "the projects archive": (f"{b}/{self.due[0]}", f"projects/_Archive/{self.abc.name}/{self.due[0]}"),
        }
        o = self.py("import reach; c = " + json.dumps(cases) + "\n"
                    "print(json.dumps({k: reach.archive_move_problem(a, b, 'reports') for k, (a, b) in c.items()}))")
        for k, why in o.items():
            self.assertTrue(why, k)
        ok = self.py(f"import reach; print(json.dumps(reach.archive_move_problem({cases['another engagement'][0]!r}, "
                     f"{(b + '/_Archive/' + self.due[0])!r}, 'reports')))")
        self.assertIsNone(ok)
        touch(self.abc / "_Archive" / self.due[0])                           # never onto a file that is there
        self.assertIn("already exists", self.py(f"import reach; print(json.dumps(reach.archive_move_problem("
                                                f"{cases['another engagement'][0]!r}, {(b + '/_Archive/' + self.due[0])!r}, 'reports')))"))
        for f in (self.abc / "_Archive" / self.due[0],):
            f.unlink()
        spec = {"source_run": "cx-edit", "items": [], "file_changes": {"title": "x", "archive": "reports",
                "file_changes_decision": "approved",
                "file_ops": [{"op": "move", "from": cases["transcript"][0], "to": cases["transcript"][1]}]}}
        self.v.propose("bad", [], file_changes=spec["file_changes"])
        r = self.run_at("apply", script="tracker.py", ok=False)
        self.assertIn("isn't a report or minutes file", r.stdout)
        self.assertTrue((self.abc / "transcripts/2024-01-01 Steering.vtt").is_file())

    def test_portfolio_minutes_move_into_the_portfolios_own_archive(self):
        pf = self.v.root / "projects/_portfolio"
        touch(pf / "minutes/2025-06-01 Portfolio sync.md", "the numbat review\n")
        touch(pf / "minutes/2026-06-01 Portfolio sync.md")
        touch(pf / "transcripts/2025-06-01 Portfolio sync.vtt")
        spec = json.loads(self.run_at("reports").stdout)
        moves = {(o["from"], o["to"]) for o in spec["file_changes"]["file_ops"]}
        self.assertIn(("projects/_portfolio/minutes/2025-06-01 Portfolio sync.md",
                       "projects/_portfolio/_Archive/minutes/2025-06-01 Portfolio sync.md"), moves)
        self.assertFalse(any("transcripts" in a or "2026-06-01" in a for a, _ in moves))
        bad = self.py("import reach; print(json.dumps([reach.archive_move_problem(a, b, 'reports') for a, b in ["
                      "('projects/_portfolio/transcripts/2025-06-01 Portfolio sync.vtt', "
                      "'projects/_portfolio/_Archive/transcripts/2025-06-01 Portfolio sync.vtt'), "
                      "('projects/_portfolio/minutes/2025-06-01 Portfolio sync.md', "
                      f"'projects/{self.abc.name}/_Archive/minutes/2025-06-01 Portfolio sync.md')]]))")
        self.assertTrue(all(bad), bad)                                # the portfolio: its minutes, into its own _Archive only
        self.stage_and_apply()
        self.assertTrue((pf / "_Archive/minutes/2025-06-01 Portfolio sync.md").is_file())
        stored = "projects/_portfolio/minutes/2025-06-01 Portfolio sync.md"
        o = self.py(f"import paths, reach, tracker; print(json.dumps([str(paths.resolve({stored!r})), "
                    f"reach.classify({stored!r}, 'read')[0], [str(f) for f, _, _ in tracker.index_files()]]))")
        self.assertEqual(o[0], str((pf / "_Archive/minutes/2025-06-01 Portfolio sync.md").resolve()))
        self.assertEqual(o[1], "never")
        self.assertFalse(any("/_Archive/" in f for f in o[2]))
        self.run_at("undo", script="tracker.py")
        self.assertTrue((pf / "minutes/2025-06-01 Portfolio sync.md").is_file())
        self.assertFalse((pf / "_Archive").exists())


class ReportRoute(unittest.TestCase):
    """POST /api/health/fix/archive_reports: token-checked, takes nothing from the page, and only puts the moves on the card."""

    @classmethod
    def setUpClass(cls):
        from test_health_fixes import free_port
        cls.v = Vault()
        cls.v.run("init")
        cls.abc = next(d for d in (cls.v.root / "projects").iterdir() if d.name.startswith("ABC "))
        cls.due, _ = vault_files(cls.abc)
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls.proc = subprocess.Popen([sys.executable, str(cls.v.root / "system/scripts/live_server.py")],
                                    env={**os.environ, **ENV, "CREAITE_PORT": str(cls.port)},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        page = urllib.request.urlopen(cls.base + "/").read().decode()
        cls.token = json.loads(re.search(r'id="data">(.*?)</script>', page, re.S).group(1).replace("<\\/", "</"))["token"]

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    def post(self, path, body, token=True):
        headers = {"Content-Type": "application/json", **({"X-Creaite-Token": self.token} if token else {})}
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            with e:
                return {"status": e.code, **json.loads(e.read() or b"{}")}

    def test_refused_without_the_token_or_with_a_body_then_the_card_moves_them(self):
        route = "/api/health/fix/archive_reports"
        self.assertEqual(self.post(route, {}, token=False)["status"], 403)
        self.assertEqual(self.post(route, {"files": ["x"]})["status"], 400)
        self.assertEqual(self.post(route + "?x=1", {})["status"], 400)
        for f in self.due:
            self.assertTrue((self.abc / f).is_file())                         # nothing moved by a refused call
        got = self.post(route, {})
        self.assertTrue(got["ok"] and got["card"], got)
        for f in self.due:
            self.assertTrue((self.abc / f).is_file())                         # nothing moves before Approve
        card = self.post("/api/edit/pending", {})["card"]
        self.assertEqual(card["title"], "Archive old reports and minutes")
        self.assertTrue(any(ln.startswith("Move file ") for ln in card["lines"]), card["lines"])
        done = self.post("/api/edit/approve", {"card": card["card"]})
        self.assertTrue(done["ok"], done)
        for f in self.due:
            self.assertTrue((self.abc / "_Archive" / f).is_file(), f)
        self.assertIn(route.rsplit("/", 1)[1], [f["id"] for f in self.post("/api/health/fixes", {})["fixes"]])


class OneDriveReports(OneDriveCase):
    """The projects in a OneDrive-style folder: the mapped folders, each kept below the engagement's own _Archive."""

    def test_mapped_folders_move_into_the_engagements_own_archive(self):
        files = ["02 Meetings/Minutes/2025-06-01 Steering.docx", "04 Reporting/Weekly/2025-06-06 Weekly report - Example Programme.docx",
                 "04 Reporting/Weekly/2025-06-06 Client report - Example Programme.docx",
                 "04 Reporting/Steerco/2025-06-01 Example Programme Steerco one-pager.docx"]
        portfolio = "02 Meetings/Minutes/2025-06-01 Portfolio sync.docx"
        touch(self.root / "_Portfolio" / portfolio)
        kept = ["02 Meetings/Transcripts/2025-06-01 Steering.vtt", "04 Reporting/Adhoc/2025-06-01 Weekly report notes.docx",
                "03 Delivery/2025-01-01 Plan.docx"]
        for f in files + kept:
            touch(self.eng("ABC", f))
        os.environ["CREAITE_NOW"] = DAY
        try:
            spec = self.v.run("reports", script="archive.py").stdout
            f = self.v.root / "system/staging/drafts/r.json"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(spec, encoding="utf-8")
            self.v.run("stage", str(f), script="propose.py")
            self.v.run("apply")
        finally:
            os.environ.pop("CREAITE_NOW", None)
        for x in files:
            self.assertTrue(self.eng("ABC", "_Archive", x).is_file(), x)
            self.assertFalse(self.eng("ABC", x).exists(), x)
        for x in kept:
            self.assertTrue(self.eng("ABC", x).is_file(), x)
        stored = "projects/Example Programme/" + files[1]
        o = self.py(f"import paths, reach; print(json.dumps([str(paths.resolve({stored!r})), reach.classify({stored!r}, 'read')[0]]))")
        self.assertEqual(o, [str(self.eng("ABC", "_Archive", files[1])), "never"])
        self.assertTrue((self.root / "_Portfolio/_Archive" / portfolio).is_file())        # the portfolio's own _Archive
        stored = "projects/_portfolio/" + portfolio
        o = self.py(f"import paths, reach; print(json.dumps([str(paths.resolve({stored!r})), reach.classify({stored!r}, 'read')[0]]))")
        self.assertEqual(o, [str(self.root / "_Portfolio/_Archive" / portfolio), "never"])
        self.v.run("undo")
        self.assertTrue((self.root / "_Portfolio" / portfolio).is_file())
        for x in files:
            self.assertTrue(self.eng("ABC", x).is_file(), x)


if __name__ == "__main__":
    unittest.main()
