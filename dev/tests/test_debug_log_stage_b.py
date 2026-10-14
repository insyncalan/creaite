"""Debug log, part 2, stage B (BL-102): the six scripts that do the work (tracker, excel_sync, sweep, minutes, review, report) write
what they did, with item IDs, counts and paths, and nothing from mail, minutes, notes or chats in it.

Run: python3 dev/tests/test_debug_log_stage_b.py
Each test builds a throwaway vault (as test_tracker.py does) and runs the real scripts in it. The canary strings (CANARY-...) are put
in every kind of input; none may reach system/logs/.
"""
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import ABC, REPO, Vault, action  # noqa: E402

sys.path.insert(0, str(REPO / "system" / "scripts"))

SCRIPTS = ("tracker.py", "excel_sync.py", "sweep.py", "minutes.py", "review.py", "report.py")
SRC = f"{ABC}/minutes/2026-10-01 Steering.docx — Actions"
def email(subject="[ABC] SOW", sender="Jane Doe <jane@client.example>", link="abc1"):
    return (f"Email · From: {sender} · Subject: {subject} · Sent: 2026-10-07 09:12 · "
            f"Link: https://outlook.office365.com/owa/?ItemID={link}")


class Staged(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.root = self.v.root
        self.logs = self.root / "system" / "logs"

    def tearDown(self):
        self.v.cleanup()

    def text(self):
        return "\n".join(p.read_text(encoding="utf-8") for p in sorted(self.logs.glob("debug-*.log"))) if self.logs.exists() else ""

    def run_script(self, script, *args, ok=True):
        return self.v.run(*args, script=script, ok=ok)

    def assertLogged(self, pattern):
        self.assertRegex(self.text(), pattern)

    def assertNoCanary(self):
        self.assertNotIn("CANARY", self.text())


class EntryPoints(Staged):
    def test_every_script_logs_a_start_and_an_exit(self):
        for script in SCRIPTS:
            r = self.run_script(script, ok=False)                      # no arguments: usage, exit 2 (tracker too)
            area = script[:-3]
            self.assertLogged(rf"INFO  {area}\s+start")
            self.assertLogged(rf"WARN  {area}\s+exit {r.returncode} after")

    def test_a_script_runs_the_same_without_the_helper(self):
        with_log = {s: self.run_script(s, ok=False) for s in SCRIPTS}
        (self.root / "system" / "scripts" / "log.py").unlink()
        shutil.rmtree(self.logs, ignore_errors=True)
        for s in SCRIPTS:
            r = self.run_script(s, ok=False)
            self.assertEqual((r.returncode, r.stdout), (with_log[s].returncode, with_log[s].stdout), s)
        self.assertFalse(self.logs.exists())
        self.run_script("tracker.py", "read", "projects")              # real work without the helper
        self.assertFalse(self.logs.exists())


class ApplyAndUndo(Staged):
    def test_apply_and_undo_log_ids_and_counts_never_text(self):
        self.v.propose("a", [action(1, description="CANARY-ACTION text", owner="Alan Carter"),
                             action(2, description="CANARY-SECOND text")])
        self.run_script("tracker.py", "apply")
        self.assertLogged(r"INFO  tracker\s+apply: backup system/backups/tracker-.*-apply\.db; proposals proposed-a\.json")
        self.assertLogged(r"INFO  tracker\s+apply 1: written 2 \(actions 2\), filed 0, rejected 0, held 0, 0 still pending")
        self.run_script("tracker.py", "undo")
        self.assertLogged(r"INFO  tracker\s+undo 1: backup system/backups/tracker-.*-undo\.db, 2 item\(s\) to reverse, 0 changed since")
        self.assertLogged(r"INFO  tracker\s+undid apply 1: 2 item\(s\) reversed")
        self.assertNoCanary()

    def test_an_invalid_item_logs_the_rule_without_the_value(self):
        self.v.propose("bad", [action(1, description="CANARY-BAD", status="CANARY-STATUS")])
        r = self.run_script("tracker.py", "apply", ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertLogged(r"WARN  tracker\s+invalid proposed-bad\.json item 1 \(actions new\): ")
        self.assertLogged(r"WARN  tracker\s+apply stopped, nothing written: 1 problem\(s\) in 1 proposal\(s\)")
        self.assertNoCanary()                                           # the printed reason may quote it; the log does not

    def test_a_held_conflict_and_a_rejected_item_are_counted(self):
        self.v.propose("a", [action(1)])
        self.run_script("tracker.py", "apply")
        self.v.propose("b", [{"n": 1, "op": "update", "table": "actions", "id": "ABC-A-001", "changes": {"status": "Closed"},
                              "based_on": "2000-01-01 00:00:00", "match": "strong", "flags": [], "decision": "approved"},
                             {**action(2, description="CANARY-REJECTED"), "decision": "rejected"}])
        self.run_script("tracker.py", "apply")
        self.assertLogged(r"INFO  tracker\s+held proposed-b\.json item 1 \(conflict\)")
        self.assertLogged(r"INFO  tracker\s+apply 2: written 0 \(none\), filed 0, rejected 1, held 1")
        self.assertNoCanary()

    def test_a_recode_logs_the_codes_and_the_row_counts(self):
        self.v.propose("a", [action(1, description="CANARY-RECODE")])
        self.run_script("tracker.py", "apply")
        shutil.move(str(self.root / ABC), str(self.root / "projects" / "XPL Example Plus"))
        self.run_script("propose.py", "recode", "ABC", "XPL", "--name", "Example Plus", "--folder", "XPL Example Plus")
        self.run_script("tracker.py", "apply")
        self.assertLogged(r"INFO  tracker\s+recode ABC to XPL: projects 1, actions 1")
        self.assertNoCanary()


class Excel(Staged):
    def test_export_and_import_log_counts(self):
        self.v.propose("a", [action(1, description="CANARY-EXCEL")])
        self.run_script("tracker.py", "apply")
        self.run_script("excel_sync.py", "export")
        self.assertLogged(r"INFO  excel\s+exported .*actions 1")
        self.run_script("excel_sync.py", "import")
        self.assertLogged(r"INFO  excel\s+import: ")
        self.assertNoCanary()


class Sweep(Staged):
    def stage(self, items, **spec):
        f = self.root / "system" / "staging" / "drafts" / "sweep.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"window": {"start": "2026-10-07 08:00", "end": "2026-10-09 08:00"}, "items": items, **spec}))
        return self.run_script("sweep.py", "stage", str(f))

    def item(self, text, source):
        return {"table": "actions", "match": "strong", "values": {"project": "ABC", "description": text, "owner": "Alan Carter",
                                                                 "source": source}}

    def test_stage_logs_counts_and_why_never_the_message(self):
        mail = email(sender="CANARY-SENDER <a@canary.example>", subject="[ABC] CANARY-SUBJECT", link="m1")
        self.stage([self.item("CANARY-ONE keep", mail),
                    self.item("CANARY-TWO no source", "somewhere CANARY-SOURCE"),
                    self.item("CANARY-THREE todo", email(sender="Bo <bo@x.example>", subject="[ABC] ToDo CANARY-TODO", link="m3"))])
        self.assertLogged(r"INFO  sweep\s+stage: 3 proposed by the search, 1 staged \(0 possible\) in proposed-.*-sweep\.json, 2 skipped "
                          r"\(ignore rule ToDo invites 1, no structured source 1\)")
        self.assertNoCanary()
        self.stage([self.item("CANARY-ONE keep", mail)])                # the same message again
        self.assertLogged(r"1 skipped \(already proposed 1\)")
        self.assertNoCanary()

    def test_window_lock_calendar_done_and_fail(self):
        today = "2026-10-09"
        with mock.patch.dict(os.environ, {"CREAITE_NOW": f"{today} 12:00"}):     # the day below stays inside the calendar window
            self.window_lock_calendar_done_and_fail(today)

    def window_lock_calendar_done_and_fail(self, today):
        self.run_script("sweep.py", "window")
        self.assertLogged(r"INFO  sweep\s+window \d{4}-\d\d-\d\d \d\d:\d\d to \d{4}-\d\d-\d\d \d\d:\d\d \(")
        self.run_script("sweep.py", "lock")
        self.run_script("sweep.py", "lock", ok=False)
        self.assertLogged(r"INFO  sweep\s+lock refused: another sweep started \d+ minutes ago")
        self.run_script("sweep.py", "unlock")
        cal = self.root / "system" / "staging" / "drafts" / "cal.json"
        cal.parent.mkdir(parents=True, exist_ok=True)
        cal.write_text(json.dumps({"days": {today: [{"title": "CANARY-MEETING", "start": "09:00", "end": "10:00", "where": "CANARY-ROOM",
                                                      "organiser": "CANARY-ORGANISER", "body": "CANARY-BODY"},
                                                     {"title": "CANARY-BAD", "start": "11:00", "end": "10:00"}]}}))
        self.run_script("sweep.py", "calendar", str(cal))
        self.assertLogged(r"INFO  sweep\s+calendar saved: \d+ meeting\(s\) over \d+ day\(s\) in \S+ \([+-]\d{4}\), 1 with times that could not")
        self.run_script("sweep.py", "done", "--started", "2026-10-09 08:00", "--normal",
                        "--summary", "searched 41, proposed 3, skipped 'CANARY-QUOTED' from boss@canary.example")
        self.assertLogged(r"INFO  sweep\s+done \(normal\): searched 41, proposed 3, skipped '…' from …")
        self.run_script("sweep.py", "fail", "--message", "Outlook search for \"CANARY-QUERY\" timed out")
        self.assertLogged(r"ERROR sweep\s+sweep failed: Outlook search for \"…\" timed out")
        self.assertNoCanary()


class Minutes(Staged):
    def test_stage_logs_the_key_kind_counts_and_skips(self):
        spec = self.root / "system" / "staging" / "meeting.json"
        values = {"project": "ABC", "description": "CANARY-MINUTES action", "owner": "Alan Carter", "due_date": "2026-10-20"}
        spec.write_text(json.dumps({"date": "2026-10-01", "title": "CANARY-TITLE steering", "projects": ["ABC"], "items": [
            {"table": "actions", "values": values, "match": "strong"},
            {"table": "actions", "values": {**values, "project": "ZZZ"}, "match": "strong"}]}))
        self.run_script("minutes.py", "stage", str(spec))
        self.assertLogged(r"INFO  minutes\s+staged proposed-.*\.json: fp key, 2026-10-01, projects ABC, 1 item\(s\) \(actions 1\), "
                          r"notes: other project 1")
        self.assertNoCanary()
        self.v.run("apply")
        self.run_script("minutes.py", "stage", str(spec), ok=False)
        self.assertNoCanary()

    def test_a_meeting_with_no_project_is_logged_without_its_title(self):
        spec = self.root / "system" / "staging" / "meeting.json"
        spec.write_text(json.dumps({"date": "2026-10-01", "title": "CANARY-NOPROJECT", "projects": [], "items": []}))
        self.run_script("minutes.py", "stage", str(spec), ok=False)
        self.assertLogged(r"INFO  minutes\s+stage skipped: no project matched \(fp key, 2026-10-01\)")
        self.assertNoCanary()


class Review(Staged):
    def test_decisions_log_ids_and_field_names(self):
        self.v.propose("r", [{**action(1, description="CANARY-REVIEW one"), "decision": "pending"},
                             {**action(2, description="CANARY-REVIEW two"), "decision": "pending"},
                             {**action(3, description="CANARY-REVIEW three"), "decision": "pending"},
                             {**action(4, description="CANARY-REVIEW four"), "decision": "pending"}])
        self.run_script("review.py", "list")
        self.run_script("review.py", "approve", "1")
        self.assertLogged(r"INFO  review\s+approved proposed-r\.json item 1 \(actions new\)")
        self.assertLogged(r"INFO  review\s+approved: 1 of 1 decided")
        self.run_script("review.py", "edit", "2", "owner=CANARY-OWNER")
        self.assertLogged(r"INFO  review\s+proposed-r\.json item 2 edited \(owner\)")
        self.run_script("review.py", "reject", "3")
        self.assertLogged(r"INFO  review\s+rejected proposed-r\.json item 3 \(actions new\)")
        self.run_script("review.py", "bulk")
        self.assertLogged(r"INFO  review\s+bulk approved 1")
        self.assertNoCanary()


class Reports(Staged):
    def test_an_ad_hoc_document_logs_its_path_and_size(self):
        spec = self.root / "system" / "staging" / "adhoc.json"
        spec.write_text(json.dumps({"title": "Open actions", "sections": [{"heading": "Actions", "tracker": {"table": "actions", "project": "ABC"}}]}))
        self.v.propose("a", [action(1, description="CANARY-ADHOC")])
        self.run_script("tracker.py", "apply")
        self.run_script("report.py", "adhoc", str(spec))
        self.assertLogged(r"INFO  report\s+ad hoc document written: system/staging/drafts/\d{4}-\d\d-\d\d Open actions\.docx \(1 table\(s\), 1 row\(s\)\)")
        self.assertNoCanary()


class RuleHelper(unittest.TestCase):
    def test_rule_takes_out_quoted_values_and_addresses(self):
        import log
        self.assertEqual(log.rule("owner 'Sara Khan' isn't in the register"), "owner '…' isn't in the register")
        self.assertEqual(log.rule('status "CANARY" not in (Open, Closed)'), 'status "…" not in (Open, Closed)')
        self.assertEqual(log.rule("sent to boss@canary.example today"), "sent to … today")
        self.assertEqual(log.rule("x" * 400, 50), "x" * 49 + "…")
        self.assertEqual(log.rule(None), "None")


class PanelAccess(unittest.TestCase):
    """A4: ask creaite can read system/logs/ and is refused a write there (the tool lists the live server gives a run)."""

    def setUp(self):
        import live_server
        self.ls = live_server

    def covers(self, tools, kind, path):
        for t in tools:
            m = re.fullmatch(rf"{kind}\((.*)\)", t)
            if m and fnmatch.fnmatch(path, m.group(1)):
                return True
        return False

    def test_reading_the_log_is_open(self):
        self.assertIn("Read", self.ls.READ_TOOLS)                       # a bare Read: every vault file, the log folder included
        self.assertIn("Grep", self.ls.READ_TOOLS)

    def test_writing_the_log_is_not_allowed_even_when_confirmed(self):
        log = "system/logs/debug-2026-10-09.log"
        allowed = self.ls.READ_TOOLS + self.ls.WRITE_TOOLS
        for kind in ("Write", "Edit"):
            self.assertFalse(self.covers(allowed, kind, log), kind)
        self.assertIn("Edit(system/scripts/**)", self.ls.DENY_TOOLS)    # and the script that writes it can't be edited either
        self.assertIn("Write(system/logs/**)", self.ls.DENY_TOOLS)
        self.assertIn("Edit(system/logs/**)", self.ls.DENY_TOOLS)

    def test_the_file_tool_refuses_the_log_folder(self):
        r = subprocess.run([sys.executable, str(REPO / "system" / "scripts" / "filechange.py"), "check", "system/logs/debug-2026-10-09.log"],
                           capture_output=True, text=True, cwd=REPO)
        self.assertFalse(json.loads(r.stdout)["ok"], r.stdout)


if __name__ == "__main__":
    unittest.main()
