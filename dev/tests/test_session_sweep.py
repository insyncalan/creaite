"""Tests for session.py (session-start rule) and sweep.py (cx-sweep's deterministic parts).

Run: python3 dev/tests/test_session_sweep.py
The clock is fixed with CREAITE_NOW so due times and windows are predictable.
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import ABC, Vault, action  # noqa: E402

EMAIL = ("Email · From: Jane Doe <jane@client.example> · Subject: [ABC] SOW · Sent: 2026-10-05 09:12 · "
         "Link: https://outlook.office365.com/owa/?ItemID=abc1")


class Clock(Vault):
    def at(self, when, *args, script):
        r = subprocess.run([sys.executable, str(self.root / "system/scripts" / script), *args],
                           env={**os.environ, "CREAITE_NOW": when}, capture_output=True, text=True)
        if r.returncode not in (0, 3):
            raise AssertionError(f"{script} {args}: {r.stdout}{r.stderr}")
        return r


class SweepTests(unittest.TestCase):
    def setUp(self):
        self.v = Clock()
        self.v.run("init")

    def tearDown(self):
        self.v.cleanup()

    def sweep(self, when, *args):
        return self.v.at(when, *args, script="sweep.py")

    def test_due_rule(self):
        self.assertFalse(json.loads(self.sweep("2026-10-05 06:30", "due").stdout)["due"])   # before 07:00
        self.assertTrue(json.loads(self.sweep("2026-10-05 08:00", "due").stdout)["due"])    # never swept
        self.sweep("2026-10-05 08:00", "done", "--started", "2026-10-05 08:00", "--normal")
        self.assertFalse(json.loads(self.sweep("2026-10-05 16:00", "due").stdout)["due"])   # done today
        self.assertTrue(json.loads(self.sweep("2026-10-06 07:05", "due").stdout)["due"])    # next morning
        s = self.v.root / "system/config/settings.json"
        data = json.loads(s.read_text())
        data["sweep"]["due_from"] = "06:30"                                                  # changed in Settings
        s.write_text(json.dumps(data))
        info = json.loads(self.sweep("2026-10-06 06:45", "due").stdout)
        self.assertEqual((info["due"], info["due_from"]), (True, "06:30"))

    def test_window_and_timestamp(self):
        w = json.loads(self.sweep("2026-10-05 08:00", "window").stdout)
        self.assertEqual((w["start"], w["kind"]), ("2026-09-21 08:00", "first run"))       # 14-day look-back
        self.sweep("2026-10-05 08:00", "done", "--started", "2026-10-05 08:00", "--normal", "--summary", "3 items")
        w = json.loads(self.sweep("2026-10-06 08:00", "window").stdout)
        self.assertEqual((w["start"], w["kind"]), ("2026-10-05 08:00", "since the last sweep"))
        w = json.loads(self.sweep("2026-10-06 08:00", "window", "--days", "7").stdout)
        self.assertEqual((w["start"], w["advances_timestamp"]), ("2026-09-29 08:00", False))
        self.sweep("2026-10-06 08:30", "done", "--started", "2026-10-06 08:00")             # not a normal sweep
        self.assertEqual((self.v.root / "system/staging/last-sweep.txt").read_text().strip(), "2026-10-05 08:00")
        self.sweep("2026-10-06 09:00", "fail", "--message", "Microsoft 365 unavailable")
        log = (self.v.root / "system/staging/run-log.txt").read_text()
        self.assertIn("sweep ok (normal) | 3 items", log)
        self.assertIn("sweep FAILED | Microsoft 365 unavailable", log)

    def test_calendar_keeps_only_day_view_fields(self):
        spec = self.v.root / "system/staging/drafts/calendar.json"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text(json.dumps({"days": {"2026-10-06": [
            {"start": "13:00", "end": "14:00", "title": "ABC steering", "where": "Teams", "organiser": True,
             "body": "agenda text", "attendees": ["a@b.c"]},
            {"start": "10:00", "end": "11:00", "title": "Doctor", "where": "Clinic", "private": True},
            {"start": "15:00", "end": "14:00", "title": "Backwards"},
            {"all_day": True, "title": "Office closed"}]}}))
        out = self.sweep("2026-10-06 07:10", "calendar", str(spec)).stdout
        self.assertIn("Calendar saved: 2 meetings over 1 day.", out)
        self.assertIn("Backwards", out)                                                       # bad times skipped, named
        cal = json.loads((self.v.root / "system/staging/calendar.json").read_text())
        self.assertEqual(cal["fetched"], "2026-10-06 07:10")
        day = cal["days"]["2026-10-06"]
        self.assertEqual([e["title"] for e in day], ["Office closed", "ABC steering"])        # all-day first; private dropped (BL-97)
        self.assertEqual(set(day[1]), {"start", "end", "title", "where", "all_day", "organiser", "teams", "private",
                                       "sensitivity", "body", "attendees"})   # BL-42 adds teams, private; BL-98 the invite

    def test_lock(self):
        self.assertIn("Locked", self.sweep("2026-10-05 08:00", "lock").stdout)
        r = self.sweep("2026-10-05 08:10", "lock")
        self.assertEqual(r.returncode, 3)                                                    # another sweep running
        self.assertIn("stale", self.sweep("2026-10-05 08:45", "lock").stdout)               # over 30 minutes
        self.sweep("2026-10-05 08:50", "unlock")
        self.assertFalse((self.v.root / "system/staging/sweep.lock").exists())

    def test_stage_dedupes_and_flags(self):
        self.v.propose("seed", [action(1, description="Chase legal on the SOW")])
        self.v.run("apply")
        spec = self.v.root / "system/staging/sweep.json"
        spec.write_text(json.dumps({"window": {"start": "2026-10-04 08:00", "end": "2026-10-05 08:00"}, "items": [
            {"table": "actions", "match": "strong", "values": {"project": "ABC", "description": "Send the signed SOW",
                                                               "owner": "Alan Carter", "source": EMAIL}},
            {"table": "actions", "match": "strong", "values": {"project": "ABC", "description": "Chase legal on the SOW",
                                                               "source": EMAIL}},                       # already open
            {"table": "raid", "match": "possible", "values": {"project": "ABC", "type": "Dependency",
                                                              "description": "Vendor API by 15-10-2026", "source": EMAIL}},
            {"table": "actions", "match": "strong", "values": {"project": "ABC", "description": "No source here",
                                                               "source": "somewhere"}}],
            "status_signals": ["Client keen to sign this week"],
            "attachments": {"to_inbox": ["Recording.vtt"], "to_file": ["SOW v3.pdf"]}}))
        out = self.sweep("2026-10-05 08:05", "stage", str(spec)).stdout
        self.assertIn("Sweep: 2 items (1 possible), 1 transcript(s) to Intake (inbox/), 1 document(s) to file", out)
        self.assertIn("skipped (already in the tracker): Chase legal on the SOW", out)
        self.assertIn("skipped (no structured Email/Teams source): No source here", out)
        self.assertIn("To file in documents/: SOW v3.pdf", out)
        prop = next((self.v.root / "system/staging").glob("proposed-*-sweep.json"))
        data = json.loads(prop.read_text())
        self.assertEqual(data["source_run"], "cx-sweep")
        first = data["items"][0]
        self.assertEqual((first["values"]["raised"], first["flags"]), ("2026-10-05", ["no-due-date"]))
        self.assertEqual(data["items"][1]["match"], "possible")
        # the same message isn't proposed twice
        out = self.sweep("2026-10-05 09:00", "stage", str(spec)).stdout
        self.assertIn("skipped (proposed before from the same message): Send the signed SOW", out)


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.v = Clock()
        self.v.run("init")
        (self.v.root / ".creaite-dev").write_text("")      # behaves like the dev repo until --force

    def tearDown(self):
        self.v.cleanup()

    def start(self, when, *extra):
        return self.v.at(when, "start", *extra, script="session.py").stdout

    def test_dev_guard(self):
        self.assertIn("session-start rules skipped", self.start("2026-10-05 08:00"))

    def test_session_start(self):
        (self.v.root / "inbox/Recording.vtt").write_text("WEBVTT")
        self.v.propose("p", [{**action(1, description="Pending one"), "decision": "pending"}])
        out = self.start("2026-10-09 13:00", "--force")                                 # a Friday afternoon
        self.assertIn("Daily backup: system/backups/tracker-", out)
        self.assertIn("Sweep due since 07:00, running now…", out)
        self.assertIn("Example Programme weekly report for week ending 09-10-2026 is due — say weekly report ABC for week ending 09-10-2026", out)
        self.assertIn("Example Programme client report is due (last: none yet) — say client report ABC", out)
        self.assertIn("Status: 1 pending", out)
        self.assertIn("1 file waiting in Intake (inbox/)", out)
        again = self.start("2026-10-09 14:00", "--force")
        self.assertNotIn("Daily backup", again)                                         # once a day
        data = json.loads(self.v.at("2026-10-09 14:00", "start", "--force", "--json", script="session.py").stdout)
        self.assertEqual(data["status"]["inbox"], ["Recording.vtt"])

    def test_weekly_reminder_window_and_dismissal(self):
        out = self.start("2026-10-09 11:00", "--force")                                 # Friday morning
        self.assertIn("week ending 02-10-2026", out)                                    # last week's still due
        (self.v.root / ABC / "reports").mkdir(exist_ok=True)
        (self.v.root / ABC / "reports/2026-10-09 Weekly report.docx").write_text("x")
        out = self.start("2026-10-09 15:00", "--force")
        self.assertNotIn("weekly report for week ending", out)                          # every project's is filed
        s = self.v.root / "system/config/settings.json"
        data = json.loads(s.read_text())
        data["reminders"]["dismissed_forever"] = ["client:ABC:never"]
        s.write_text(json.dumps(data))
        self.assertNotIn("Example Programme client report", self.start("2026-10-09 15:00", "--force"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
