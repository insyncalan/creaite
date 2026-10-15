"""BL-10: items archived for their age (v1.9.5; Alan's decisions, 14-10-2026).

Run: python3 dev/tests/test_archive_items.py     (quick tier: no Chrome)

What is covered, with the clock pinned (CREAITE_NOW):
- closed or cancelled actions and RAID items, and done or dropped promises, are archived exactly 6 months after their closed date
  (archive.after_months), not a day before; open items, decisions and milestones never are, whatever their age;
- an item a client report could cite (client-visible) follows the same rule;
- the run goes through tracker.py apply (logged, undoable; undo leaves nothing in Review); a hand-made proposal can't archive an
  open item, a decision or a recent one;
- editing an archived item un-archives it, and the next day's run leaves it live (an edit buys a full period);
- archived items leave the default views and stay searchable, marked Archived;
- the daily slot runs once a day, never from an ask creaite run, and Health shows its last run;
- session start runs it after the daily backup, and the live server's daily backup job after Tidy up (no timer of its own).
Everything is fictional and temporary.
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import Vault  # noqa: E402

DAY = "2026-10-14 09:00"
SRC = "projects/ABC Example Programme/minutes/2026-01-05 Steering.docx"
MSG = "What it is: SOW revision\nWhat it means for you: Sign-off needed\nWhat is being done: Draft sent"


def new(n, table, **v):
    base = {"project": "ABC", "raised": "2025-01-01", "source": SRC}
    if table in ("actions", "raid"):
        base["owner"] = "Alan Carter"
    if table == "raid":
        base["type"] = "Risk"
    if table == "promises":
        base.update(promised_by="Alan Carter", promised_to="Jane Doe")
    if table == "decisions":
        base = {"project": "ABC", "source": SRC}
    if table == "milestones":
        base = {"project": "ABC", "source": SRC}
    base.update(v)
    return {"n": n, "op": "new", "table": table, "values": base, "match": "strong", "flags": [], "decision": "approved"}


SEED = [
    new(1, "actions", description="Closed on the boundary", status="Closed", closed="2026-04-14"),
    new(2, "actions", description="Cancelled a day short", status="Cancelled", closed="2026-04-15"),
    new(3, "actions", description="Open for ages"),
    new(4, "actions", description="Delayed for ages", status="Delayed"),
    new(5, "actions", description="Client-visible, long closed", status="Closed", closed="2026-01-01", client_visible=1,
        client_message=MSG),
    new(6, "raid", description="Risk closed long ago", status="Closed", closed="2026-04-01"),
    new(7, "raid", description="Risk cancelled on the boundary", status="Cancelled", closed="2026-04-14"),
    new(8, "raid", description="Risk still open"),
    new(9, "promises", description="Promise done long ago", status="Done", closed="2026-03-01"),
    new(10, "promises", description="Promise dropped recently", status="Dropped", closed="2026-04-20"),
    new(11, "promises", description="Promise still open"),
    new(12, "decisions", decision="An old decision", date="2025-01-01", status="Made"),
    new(13, "milestones", name="An old milestone", status="Done", baseline_date="2025-01-01", actual_date="2025-01-01"),
]


class ArchiveItems(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.v.propose("seed", SEED)
        self.v.run("apply")
        self.ids = {}
        for t in ("actions", "raid", "promises", "decisions", "milestones"):
            for r in self.v.rows(t):
                self.ids[r.get("description") or r.get("decision") or r.get("name")] = (t, r["id"])

    def tearDown(self):
        self.v.cleanup()

    def run_at(self, day, *args, script="archive.py", ok=True, env=None):
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts" / script), *args], capture_output=True, text=True,
                           cwd=self.v.root, env={**os.environ, "CREAITE_NOW": day, **(env or {})})
        if ok:
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def archived(self):
        """{description: archived flag} for every item."""
        out = {}
        for words, (t, i) in self.ids.items():
            out[words] = next(r["archived"] for r in self.v.rows(t) if r["id"] == i)
        return out

    def flagged(self):
        return sorted(w for w, a in self.archived().items() if a)

    def test_each_type_and_status_at_the_boundary(self):
        r = self.run_at(DAY, "daily")
        self.assertIn("Archived 5 items", r.stdout)
        self.assertEqual(self.flagged(), sorted(["Closed on the boundary", "Client-visible, long closed", "Risk closed long ago",
                                                 "Risk cancelled on the boundary", "Promise done long ago"]))
        self.run_at("2026-10-15 09:00", "daily")                    # a day later the cancelled action's six months are up
        self.assertIn("Cancelled a day short", self.flagged())
        self.assertNotIn("Promise dropped recently", self.flagged())
        self.run_at("2027-10-14 09:00", "daily")                    # a year on: still never open items, decisions, milestones
        never = {"Open for ages", "Delayed for ages", "Risk still open", "Promise still open", "An old decision", "An old milestone"}
        self.assertEqual({w for w, a in self.archived().items() if not a}, never)

    def test_a_period_is_a_setting_and_zero_turns_a_kind_off(self):
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data.setdefault("archive", {}).setdefault("after_months", {}).update(raid=0, promises=12)
        cfg.write_text(json.dumps(data, indent=2))
        self.run_at(DAY, "daily")
        self.assertEqual(self.flagged(), ["Client-visible, long closed", "Closed on the boundary"])

    def test_through_apply_logged_and_undone_leaving_nothing_in_review(self):
        before = {t: self.v.rows(t) for t in ("actions", "raid", "promises")}
        self.run_at(DAY, "daily")
        applied = list((self.v.root / "system/staging/applied").glob("proposed-*-archive.json"))
        self.assertEqual(len(applied), 1)
        data = json.loads(applied[0].read_text())
        self.assertEqual(data["source_run"], "archive")
        self.assertEqual({i["op"] for i in data["items"]}, {"archive_item"})
        log = self.v.run("read", "change_log").stdout
        self.assertEqual(sum(1 for c in json.loads(log) if c["field"] == "archived"), 5)
        out = self.v.run("undo").stdout
        self.assertIn("daily archiving: not returned to Review", out)
        self.assertEqual({t: self.v.rows(t) for t in ("actions", "raid", "promises")}, before)     # exactly as before
        self.assertEqual(list((self.v.root / "system/staging").glob("proposed-*.json")), [])

    def test_a_proposal_cannot_archive_an_open_recent_or_never_archived_item(self):
        for words in ("Open for ages", "Cancelled a day short", "An old decision", "An old milestone"):
            t, i = self.ids[words]
            p = self.v.propose("bad", [{"n": 1, "op": "archive_item", "table": t, "id": i, "decision": "approved",
                                        "match": "strong", "flags": []}])
            r = self.run_at(DAY, "apply", str(p), script="tracker.py", ok=False)
            self.assertNotEqual(r.returncode, 0, words)
            self.assertIn("Apply stopped. Nothing was written.", r.stdout)
            p.unlink()
        self.assertEqual(self.flagged(), [])
        p = self.v.propose("hand", [{"n": 1, "op": "update", "table": "actions", "id": self.ids["Closed on the boundary"][1],
                                     "changes": {"archived": 1}, "decision": "approved", "match": "strong", "flags": []}])
        self.assertIn("archived is set only by", self.run_at(DAY, "apply", str(p), script="tracker.py", ok=False).stdout)

    def test_editing_an_archived_item_unarchives_it_for_a_full_period(self):
        self.run_at(DAY, "daily")
        _, aid = self.ids["Closed on the boundary"]
        p = self.v.propose("edit", [{"n": 1, "op": "update", "table": "actions", "id": aid,
                                     "changes": {"latest_update": "Checked again"}, "decision": "approved",
                                     "match": "strong", "flags": []}])
        self.run_at(DAY, "apply", str(p), script="tracker.py")
        self.assertEqual(self.archived()["Closed on the boundary"], 0)
        self.run_at("2026-10-15 09:00", "daily")                     # the next day: edited within six months, so it stays live
        self.assertEqual(self.archived()["Closed on the boundary"], 0)
        self.run_at("2027-04-16 09:00", "daily")                     # six months after the edit it goes again
        self.assertEqual(self.archived()["Closed on the boundary"], 1)

    def stage(self, *args):
        spec = self.run_at(DAY, *args, script="propose.py").stdout
        f = self.v.root / "system/staging/drafts/a.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(spec, encoding="utf-8")
        self.run_at(DAY, "stage", str(f), script="propose.py")
        self.run_at(DAY, "apply", script="tracker.py")

    def test_restoring_the_project_leaves_items_archived_for_their_age(self):
        self.run_at(DAY, "daily")
        aged = self.flagged()
        self.assertEqual(len(aged), 5)
        self.stage("archive", "ABC", "--cancel-open")                # every item flagged by the project's archive
        self.assertEqual({w for w, a in self.archived().items() if not a}, set())
        self.stage("restore", "ABC")
        self.assertEqual(self.flagged(), aged)                       # only the archive's own flags cleared: nothing flickers back
        self.assertEqual(self.v.rows("projects")[0]["archived"], 0)
        self.run_at(DAY, "undo", script="tracker.py")                # undo of the restore archives the project again, exactly
        self.assertEqual({w for w, a in self.archived().items() if not a}, set())

    def test_archived_items_leave_the_views_and_stay_searchable(self):
        self.run_at(DAY, "daily")
        code =("import sys, json; sys.path.insert(0, 'system/scripts'); import build_dashboard; d = build_dashboard.collect(); "
                "print(json.dumps([sorted(a['id'] for a in d['actions']), sorted(a['id'] for a in d['raid'])]))")
        got = json.loads(subprocess.run([sys.executable, "-c", code], cwd=self.v.root, capture_output=True, text=True,
                                        env={**os.environ, "CREAITE_NOW": DAY}).stdout.strip().splitlines()[-1])
        gone = {self.ids[w][1] for w in ("Closed on the boundary", "Client-visible, long closed", "Risk closed long ago")}
        self.assertFalse(gone & set(got[0] + got[1]), got)
        self.assertIn(self.ids["Open for ages"][1], got[0])
        out = json.loads(self.run_at(DAY, "query", "boundary", script="search.py").stdout)
        found = {r.get("id"): r for rs in out["groups"].values() for r in rs}
        self.assertTrue(found[self.ids["Closed on the boundary"][1]]["archived"])
        self.assertIn("Archived", found[self.ids["Closed on the boundary"][1]]["meta"])

    def test_daily_runs_once_a_day_never_from_ask_creaite_and_health_shows_it(self):
        self.assertIn("Archived 5 items", self.run_at(DAY, "daily").stdout)
        self.assertEqual(self.run_at(DAY, "daily").stdout.strip(), "Archiving: already run today.")
        st = json.loads((self.v.root / "system/staging/archive-state.json").read_text())
        self.assertEqual((st["items"]["day"], st["items"]["archived"]), ("2026-10-14", 5))
        guard = self.v.root / "system/guard/run.json"                 # an ask creaite run in progress: nothing runs
        guard.parent.mkdir(parents=True, exist_ok=True)
        guard.write_text("{}")
        self.assertEqual(self.run_at("2026-10-15 09:00", "daily").stdout.strip(), "")
        self.assertEqual(self.run_at("2026-10-15 09:00", "daily", env={"CREAITE_HEADLESS_RUN": "1"}).stdout.strip(), "")
        self.assertNotIn("Cancelled a day short", self.flagged())
        guard.unlink()
        r = self.run_at(DAY, "--json", "--read-only", script="doctor.py", ok=False)
        checks = {c["id"]: c for c in json.loads(r.stdout.strip().splitlines()[-1])["checks"]}
        self.assertEqual(checks["archive_items"]["status"], "pass")
        self.assertIn("Archived 5 items on 14-10-2026", checks["archive_items"]["detail"])
        code = ("import sys, json; sys.path.insert(0, 'system/scripts'); import health; "
                f"print(json.dumps(health.health({json.dumps({'checks': list(checks.values())})})['archiving']))")
        got = json.loads(subprocess.run([sys.executable, "-c", code], cwd=self.v.root, capture_output=True,
                                        text=True).stdout.strip().splitlines()[-1])
        self.assertTrue(any(a.startswith("Archived 5 items on 14-10-2026") for a in got), got)

    def test_session_start_runs_it_after_the_backup(self):
        r = self.run_at(DAY, "start", "--force", script="session.py")
        self.assertIn("Archived 5 items", r.stdout)
        self.assertEqual(len(self.flagged()), 5)
        r = self.run_at(DAY, "start", "--force", script="session.py")
        self.assertNotIn("Archiv", r.stdout)                         # once a day: nothing said the second time

    def test_the_live_servers_daily_job_runs_it_after_tidy_up(self):
        """BL-323 follow-up: no archive timer of its own; the daily backup job archives after the backup, zip and Tidy up."""
        text = (self.v.root / "system/scripts/live_server.py").read_text(encoding="utf-8")
        self.assertNotIn("archive_timer", text)
        job = text[text.index("def backup_daily_job"):text.index("def backup_timer")]
        self.assertLess(job.index("session.backup_today("), job.index("archive_after_backup()"))
        code = ("import sys, json; sys.path.insert(0, 'system/scripts'); import live_server as L; "
                "print(json.dumps([L.backup_daily_job(), L.backup_daily_job()]))")
        r = subprocess.run([sys.executable, "-c", code], cwd=self.v.root, capture_output=True, text=True,
                           env={**os.environ, "CREAITE_NOW": DAY})
        first, second = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertTrue(any(line.startswith("Archived 5 items") for line in first), first)
        self.assertTrue(any("tracker-2026-10-14.db" in line for line in first), first)       # the backup came first
        self.assertFalse(any("Archiv" in line for line in second), second)                    # once a day, nothing said again
        self.assertEqual(len(self.flagged()), 5)

    def test_never_in_the_development_repository(self):
        (self.v.root / ".creaite-dev").write_text("")
        self.assertEqual(self.run_at(DAY, "daily").stdout.strip(), "")
        self.assertEqual(self.run_at(DAY, "items", ok=False).returncode, 1)
        self.assertIn("5 items would be archived", self.run_at(DAY, "items", "--dry-run").stdout)
        self.assertEqual(self.flagged(), [])


if __name__ == "__main__":
    unittest.main()
