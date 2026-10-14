"""Sprint 5 item 2 (BL-53): decisions needed, outside the browser: extraction (cx-minutes, cx-sweep), review, early warnings,
reminders and the weekly and client reports.

Run: python3 dev/tests/test_decisions_sprint5.py
Each test builds a throwaway vault (test_tracker.Vault) with fictional data and runs the real scripts there.
"""
import json
import os
import shutil
import subprocess
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import ABC, Vault, action  # noqa: E402

DAY, TITLE = "2026-10-07", "[ABC] Steering committee"
TODAY = date(2026, 10, 9)                       # CREAITE_NOW fixes the clock where a script reads it
SRC = f"{ABC}/minutes/2026-10-01 Steering.docx — Decisions"


def d(n):
    return (TODAY + timedelta(days=n)).isoformat()


def dec(n, **v):
    return {"n": n, "op": "new", "table": "decisions", "match": "strong", "flags": [], "decision": "approved",
            "values": {"project": "ABC", "source": SRC, **v}}


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.v.propose("seed", [
            dec(1, decision="Extend the pilot by two weeks", status="Pending", made_by="Sara Example", needed_by=d(-3)),
            dec(2, decision="Choose the UAT venue", status="Pending", made_by="Alan Carter", needed_by=d(5)),
            dec(3, decision="Go-live moves two weeks", date="2026-09-15", made_by="Jane Doe",
                revisit=d(-1), reasoning="Data access is late"),
            dec(4, decision="Pilot ends on 09-10", date="2026-09-01", made_by="Jane Doe", revisit="revisit if adoption falls below 60%"),
            action(5, description="Send the SOW", owner="Sara Example", due_date=d(2)),                            # ABC-A-005: after D-001…004
        ])
        self.v.run("apply")
        (self.v.root / "inbox/steering.vtt").write_text("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n<v Omar Ali>Hello</v>")

    def tearDown(self):
        self.v.cleanup()

    def run_script(self, script, *args, ok=True):
        env = {**os.environ, "CREAITE_NOW": f"{TODAY} 09:00"}
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts" / script), *args], cwd=self.v.root, env=env,
                           capture_output=True, text=True)
        if ok and r.returncode != 0:
            raise AssertionError(f"{script} {args} failed:\n{r.stdout}\n{r.stderr}")
        return r

    def row(self, id_):
        return next(r for r in self.v.rows("decisions") if r["id"] == id_)

    def approve_all(self):
        """Alan's approval of every staged item, written into the proposal as Review does."""
        for p in (self.v.root / "system/staging").glob("proposed-2*.json"):
            data = json.loads(p.read_text())
            for i in data["items"]:
                i["decision"] = "approved"
            p.write_text(json.dumps(data))


# ── cx-minutes ────────────────────────────────────────────────────────────────

class MinutesTests(Base):
    def stage(self, items, **extra):
        f = self.v.root / "system/staging/drafts/meeting.json"
        draft = self.v.root / "system/staging/drafts/steering.docx"   # BL-260: a transcript is staged with its draft
        if not draft.exists():
            shutil.copy(self.v.root / "system/templates/minutes-template.docx", draft)
        f.write_text(json.dumps({"title": TITLE, "date": DAY, "projects": ["ABC"], "transcript": "inbox/steering.vtt",
                                 "draft": "system/staging/drafts/steering.docx", "items": items, **extra}))
        return self.v.run("stage", str(f), script="minutes.py")

    def staged(self):
        files = sorted((self.v.root / "system/staging").glob("proposed-2*.json"))
        return json.loads(files[-1].read_text())

    def test_a_decision_needed_is_staged_pending_with_no_date(self):
        out = self.stage([{"table": "decisions", "section": "Open Questions", "values": {
            "project": "ABC", "decision": "Confirm the go-live weekend", "status": "Pending", "made_by": "Omar Ali",
            "needed_by": "2026-10-20", "reasoning": "The client freeze starts the week after"}}]).stdout
        item = self.staged()["items"][0]
        self.assertEqual((item["op"], item["table"]), ("new", "decisions"))
        self.assertEqual({k: item["values"].get(k) for k in ("status", "date", "made_by", "needed_by", "reasoning")},
                         {"status": "Pending", "date": None, "made_by": "Omar Ali", "needed_by": "2026-10-20",
                          "reasoning": "The client freeze starts the week after"})
        self.assertNotIn("invalid", item["flags"])                                      # it validates
        self.assertIn("Confirm the go-live weekend", out)

    def test_a_decision_made_is_dated_the_meeting_date_with_the_fuller_record(self):
        self.stage([{"table": "decisions", "values": {
            "project": "ABC", "decision": "Use masked data for UAT", "made_by": "Jane Doe", "reasoning": "No production data",
            "options": "Masked; synthetic", "revisit": "revisit if the data access is granted", "replaces": "ABC-D-004"}}])
        v = self.staged()["items"][0]["values"]
        self.assertEqual((v["status"], v["date"], v["replaces"], v["options"]), ("Made", DAY, "ABC-D-004", "Masked; synthetic"))
        self.assertNotIn("invalid", self.staged()["items"][0]["flags"])

    def test_expected_lists_the_decisions_needed(self):
        out = json.loads(self.run_script("minutes.py", "expected", "ABC", "--title", TITLE).stdout)
        needed = out["decisions_needed"]
        self.assertEqual([(x["id"], x["made_by"], x["needed_by"]) for x in needed],
                         [("ABC-D-001", "Sara Example", d(-3)), ("ABC-D-002", "Alan Carter", d(5))])        # soonest needed first
        self.assertNotIn("ABC-D-003", [x["id"] for x in needed])                                           # made ones aren't listed

    def test_a_meeting_makes_a_pending_decision_on_the_same_record(self):
        self.stage([{"op": "update", "table": "decisions", "id": "ABC-D-001", "section": "Decisions",
                     "set": {"status": "Made", "reasoning": "Sara confirmed the extra time is funded"},
                     "why": "Sara agreed the extension"}])
        item = self.staged()["items"][0]
        self.assertEqual((item["op"], item["table"], item["id"]), ("update", "decisions", "ABC-D-001"))
        self.assertEqual(item["changes"], {"status": "Made", "reasoning": "Sara confirmed the extra time is funded", "date": DAY})
        self.assertEqual(item["based_on"], self.row("ABC-D-001")["updated_at"])
        self.assertNotIn("invalid", item["flags"])
        self.approve_all()
        self.v.run("apply")
        r = self.row("ABC-D-001")
        self.assertEqual((r["id"], r["status"], r["date"], r["reasoning"]), ("ABC-D-001", "Made", DAY, "Sara confirmed the extra time is funded"))
        self.assertEqual(len(self.v.rows("decisions")), 4)                                                # no new record

    def test_a_meeting_can_withdraw_one(self):
        self.stage([{"op": "update", "table": "decisions", "id": "ABC-D-002", "set": {"status": "Withdrawn"},
                     "why": "Alan: the venue is fixed after all"}])
        self.assertEqual(self.staged()["items"][0]["changes"], {"status": "Withdrawn"})

    def test_updates_never_touch_a_made_decision_or_its_wording(self):
        r = self.stage([{"op": "update", "table": "decisions", "id": "ABC-D-003", "set": {"status": "Withdrawn"}, "why": "x"}]).stdout
        self.assertIn("ABC-D-003 is Made; only open items are updated", r)
        r = self.stage([{"op": "update", "table": "decisions", "id": "ABC-D-001", "set": {"decision": "Something else"}, "why": "x"}]).stdout
        self.assertIn("decision can't be changed from minutes", r)

    def test_a_new_decision_that_repeats_a_pending_one_becomes_the_update(self):
        out = self.stage([{"table": "decisions", "values": {"project": "ABC", "decision": "Extend the pilot by two weeks",
                                                             "made_by": "Sara Example", "reasoning": "Agreed on the call"}}]).stdout
        data = self.staged()
        self.assertEqual([(i["op"], i["id"]) for i in data["items"]], [("update", "ABC-D-001")])
        self.assertEqual(data["items"][0]["changes"], {"status": "Made", "date": DAY, "reasoning": "Agreed on the call"})
        self.assertIn("already in the tracker as ABC-D-001, so staged as an update", out)

    def test_a_pending_decision_repeated_as_pending_is_only_a_mention(self):
        out = self.stage([{"table": "decisions", "values": {"project": "ABC", "decision": "Extend the pilot by two weeks",
                                                             "status": "Pending", "made_by": "Sara Example"}}]).stdout
        self.assertIn("skipped (already in the tracker as ABC-D-001)", out)

    def test_the_review_line_says_who_is_asked_and_by_when(self):
        self.stage([{"table": "decisions", "values": {"project": "ABC", "decision": "Confirm the go-live weekend",
                                                       "status": "Pending", "made_by": "Omar Ali", "needed_by": "2026-10-20"}}])
        out = self.v.run("list", script="review.py").stdout
        self.assertIn("Needed from Omar Ali", out)
        self.assertIn("by 20-10-2026", out)

    def test_recording_or_withdrawing_is_never_approved_in_bulk(self):
        self.stage([{"op": "update", "table": "decisions", "id": "ABC-D-001", "set": {"status": "Made"}, "why": "agreed"},
                    {"op": "update", "table": "actions", "id": "ABC-A-005", "set": {"latest_update": "07-10-2026: chased"}, "why": "x"}])
        out = self.v.run("bulk", script="review.py").stdout
        data = self.staged()
        decisions = {i["table"]: i["decision"] for i in data["items"]}
        self.assertEqual(decisions["decisions"], "pending")                                                # left for Alan
        self.assertEqual(decisions["actions"], "approved")
        self.assertIn("decision", out.lower())

    def test_refreshing_items_from_the_draft_leaves_a_pending_decision_alone(self):
        import re
        sys.path.insert(0, str(self.v.root / "system/scripts"))
        src = (self.v.root / "system/scripts/minutes.py").read_text()
        self.assertTrue(re.search(r'not \(i\.get\("table"\) == "decisions" and \(i\.get\("values"\) or \{\}\)\.get\("status"\) == "Pending"\)', src))


# ── cx-sweep ──────────────────────────────────────────────────────────────────

class SweepTests(Base):
    MAIL = ("Email · From: Sara Example <sara.example@client.com> · Subject: [ABC] Pilot · Sent: 2026-10-08 09:00 · "
            "Link: https://outlook.office365.com/owa/?ItemID=abc")

    def stage(self, items):
        f = self.v.root / "system/staging/drafts/sweep.json"
        f.write_text(json.dumps({"window": "test", "items": items, "status_signals": []}))
        return self.v.run("stage", str(f), script="sweep.py")

    def staged(self):
        files = sorted((self.v.root / "system/staging").glob("proposed-2*-sweep*.json"))
        return json.loads(files[-1].read_text())

    def test_a_pending_decision_from_a_message_stages_with_no_date(self):
        out = self.stage([{"table": "decisions", "match": "strong", "values": {
            "project": "ABC", "decision": "Confirm the go-live weekend", "status": "Pending", "date": "", "made_by": "Sara Example",
            "needed_by": "2026-10-16", "source": self.MAIL}}]).stdout
        self.assertIn("Sweep: 1 item", out)
        item = self.staged()["items"][0]
        self.assertNotIn("invalid", item["flags"])                                      # the empty date is "not set", not a bad date
        self.approve_all()
        self.v.run("apply")
        r = next(x for x in self.v.rows("decisions") if x["decision"] == "Confirm the go-live weekend")
        self.assertEqual((r["status"], r["date"], r["made_by"], r["needed_by"]), ("Pending", None, "Sara Example", "2026-10-16"))

    def test_the_skill_has_its_own_decisions_needed_subsection_and_the_steps_are_untouched(self):
        text = (self.v.root / ".claude/skills/cx-sweep/SKILL.md").read_text()
        self.assertIn("## Decisions needed (BL-53)", text)
        self.assertIn('"status": "Pending", "date": ""', text)
        self.assertIn("9. **Finish:** `sweep.py done", text)                            # the numbered flow still ends as before


# ── Early warnings, reminders ─────────────────────────────────────────────────

class SignalTests(Base):
    def warnings(self, settings=None):
        sys.path.insert(0, str(self.v.root / "system/scripts"))
        script = ("import sys, json; sys.path.insert(0, 'system/scripts'); import build_dashboard as bd; from datetime import date; "
                  f"print(json.dumps(bd.early_warnings({settings or {}!r}, date(2026, 10, 9))))")
        r = subprocess.run([sys.executable, "-c", script], cwd=self.v.root, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_an_overdue_pending_decision_is_an_early_warning(self):
        got = [w for w in self.warnings() if w["k"] == "decisions"]
        self.assertEqual([(w["id"], w["sig"], w["p"]) for w in got], [("ABC-D-001", "decision_overdue", "ABC")])
        self.assertEqual(got[0]["text"], "Decision needed from Sara Example by 06-10-2026: 3 days late")

    def test_it_can_be_switched_off_or_given_a_grace_period(self):
        self.assertEqual([w for w in self.warnings({"warnings": {"decision_overdue": {"on": False}}}) if w["k"] == "decisions"], [])
        self.assertEqual([w for w in self.warnings({"warnings": {"decision_overdue": {"days": 5}}}) if w["k"] == "decisions"], [])
        self.assertEqual(len([w for w in self.warnings({"warnings": {"decision_overdue": {"days": 3}}}) if w["k"] == "decisions"]), 1)

    def test_a_made_or_withdrawn_decision_is_never_late(self):
        self.v.propose("made", [{"n": 1, "op": "update", "table": "decisions", "id": "ABC-D-001", "match": "strong", "flags": [],
                                 "decision": "approved", "changes": {"status": "Withdrawn"}}])
        self.v.run("apply")
        self.assertEqual([w for w in self.warnings() if w["k"] == "decisions"], [])

    def reminders(self):
        script = ("import sys, json; sys.path.insert(0, 'system/scripts'); import build_dashboard as bd; from datetime import date; "
                  "print(json.dumps(bd.decision_revisit_reminders(date(2026, 10, 9))))")
        r = subprocess.run([sys.executable, "-c", script], cwd=self.v.root, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_a_revisit_date_that_has_come_is_a_reminder_but_words_are_not(self):
        got = self.reminders()
        self.assertEqual([x["id"] for x in got], [f"revisit:ABC-D-003:{d(-1)}"])                 # D-004's revisit is words, with no date to watch
        self.assertIn("ABC-D-003 is due to be revisited (08-10-2026): Go-live moves two weeks", got[0]["text"])

    def test_a_future_revisit_is_not_yet_a_reminder(self):
        self.v.propose("later", [{"n": 1, "op": "update", "table": "decisions", "id": "ABC-D-003", "match": "strong", "flags": [],
                                  "decision": "approved", "changes": {"revisit": d(20)}}])
        self.v.run("apply")
        self.assertEqual(self.reminders(), [])

    def test_the_reminders_the_dashboard_and_session_start_share_include_the_revisit(self):
        script = ("import sys, json; sys.path.insert(0, 'system/scripts'); import build_dashboard as bd, paths; from datetime import date, datetime; "
                  "print(json.dumps([r['id'] for r in bd.reminders(paths.load_settings(), [], [], date(2026, 10, 9), datetime(2026, 10, 9, 9, 0))]))")
        r = subprocess.run([sys.executable, "-c", script], cwd=self.v.root, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual([x for x in json.loads(r.stdout) if x.startswith("revisit:")], [f"revisit:ABC-D-003:{d(-1)}"])


# ── Reports ───────────────────────────────────────────────────────────────────

class ReportTests(Base):
    def weekly(self):
        r = self.run_script("report.py", "weekly-data", "ABC", "--week-ending", "2026-10-09")
        return json.loads(r.stdout)

    def test_the_weekly_data_lists_the_decisions_needed_and_those_to_revisit(self):
        got = self.weekly()
        self.assertEqual([(x["id"], x["by"], x["needed_by"], x["overdue_days"]) for x in got["decisions_needed"]],
                         [("ABC-D-001", "Sara Example", d(-3), 3), ("ABC-D-002", "Alan Carter", d(5), 0)])
        self.assertEqual([x["id"] for x in got["decisions_to_revisit"]], ["ABC-D-003"])
        self.assertEqual(got["decisions"], [])                                                   # nothing was *made* that week

    def test_the_weekly_word_report_lists_them_under_decisions(self):
        spec = {"code": "ABC", "week_ending": "2026-10-09", "health": "At risk", "health_reason": "Data access is late",
                "summary": ["Data access is late."], "key_changes": "", "current_state": "Build is behind.", "progress": [], "next_week": [],
                "help_needed": []}
        f = self.v.root / "system/staging/drafts/weekly.json"
        f.write_text(json.dumps(spec))
        self.run_script("report.py", "weekly-stage", str(f))
        draft = next((self.v.root / "system/staging/drafts").glob("*Weekly report*.docx"))
        import re
        import zipfile
        with zipfile.ZipFile(draft) as z:
            text = re.sub(r"<[^>]+>", " ", z.read("word/document.xml").decode("utf-8"))
        self.assertIn("Needed: Extend the pilot by two weeks", text)
        self.assertIn("from Sara Example, by 06-10-2026 (3 days overdue)", text)
        self.assertIn("Needed: Choose the UAT venue", text)

    def test_a_client_report_shows_a_pending_decision_only_if_client_visible(self):
        data = json.loads(self.run_script("report.py", "client-data", "ABC").stdout)
        self.assertEqual(data["decisions"], [])                                                  # none is flagged
        self.v.propose("vis", [{"n": 1, "op": "update", "table": "decisions", "id": "ABC-D-001", "match": "strong", "flags": [],
                                "decision": "approved",
                                "changes": {"client_visible": 1, "client_message": "We would like to confirm the pilot extension."}}])
        self.v.run("apply")
        data = json.loads(self.run_script("report.py", "client-data", "ABC").stdout)
        self.assertEqual([(x["id"], x["status"], x["text"]) for x in data["decisions"]],
                         [("ABC-D-001", "Pending", "We would like to confirm the pilot extension.")])
        self.assertNotIn("Choose the UAT venue", json.dumps(data))                               # not flagged: never shown


if __name__ == "__main__":
    unittest.main()
