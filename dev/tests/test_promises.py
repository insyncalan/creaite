"""BL-125 stage A, the Python side: promises proposed by cx-minutes and cx-sweep (approved in Review like any item), the
readers (`tracker.py read promises --list owe|waiting`, `--search`), Waiting on's "quiet for N days" from the mentions log,
and the weekly report's promise lines.

Run: python3 dev/tests/test_promises.py          (quick tier: no Chrome)
Each test builds a throwaway vault (test_tracker.Vault) with fictional data and runs the real scripts there.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest
import sqlite3
import zipfile
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import ABC, REPO, Vault  # noqa: E402

TODAY = date(2026, 10, 9)                       # a Friday; CREAITE_NOW fixes the clock where a script reads it
DAY, TITLE = "2026-10-07", "[ABC] Steering committee"
MAIL = ("Email · From: Sara Example <sara.example@client.com> · Subject: [ABC] Extract · Sent: 2026-10-08 09:00 · "
        "Link: https://outlook.office365.com/owa/?ItemID=p1")


def d(n):
    return (TODAY + timedelta(days=n)).isoformat()


def promise(n, by, to, text, due=None, raised=None, **extra):
    v = {"project": "ABC", "promised_by": by, "promised_to": to, "description": text, "raised": raised or d(-10),
         "source": f"{ABC}/minutes/2026-09-29 Steering.docx — Actions", **extra}
    if due:
        v["due_date"] = due
    return {"n": n, "op": "new", "table": "promises", "match": "strong", "flags": [], "decision": "approved", "values": v}


SEED = [
    promise(1, "Alan Carter", "Sara Example", "Send the SOW to the client", d(2)),           # ABC-P-001: you owe, not yet due
    promise(2, "Alan Carter", "Jane Doe", "Share the UAT plan", d(-2)),                      # ABC-P-002: you owe, 2 days overdue
    promise(3, "Sara Example", "Alan Carter", "Send the data extract", d(-3)),               # ABC-P-003: waiting on, quiet 10 days
    promise(4, "Jane Doe", "Alan Carter", "Confirm the budget", d(4)),                       # ABC-P-004: to Alan, not yet due
    promise(5, "Sara Example", "Jane Doe", "Book the room", d(-5)),                         # ABC-P-005: neither is Alan
    promise(6, "Omar Ali", "Alan Carter", "Send the test report"),                           # ABC-P-006: no date, never overdue
    promise(7, "Jane Doe", "Alan Carter", "Approve the plan", d(-1), status="Done"),         # ABC-P-007: kept
]


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.v.propose("seed", SEED)
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

    def read(self, *args):
        return json.loads(self.run_script("tracker.py", "read", "promises", *args).stdout)

    def staged(self, pattern="proposed-2*.json"):
        return json.loads(sorted((self.v.root / "system/staging").glob(pattern))[-1].read_text())

    def mention(self, item_id, day):
        with open(self.v.root / "system/staging/mentions.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"at": day, "id": item_id, "run": "cx-sweep", "source": "x"}) + "\n")

    def approve_all(self):
        """Alan's approval of every staged item, written into the proposal as Review does."""
        for p in (self.v.root / "system/staging").glob("proposed-2*.json"):
            data = json.loads(p.read_text())
            for i in data["items"]:
                i["decision"] = "approved"
            p.write_text(json.dumps(data))


# ── Readers ───────────────────────────────────────────────────────────────────

class ReaderTests(Base):
    def test_you_owe_lists_alans_open_promises_soonest_first_with_how_late(self):
        got = [(r["id"], r["overdue_days"]) for r in self.read("--list", "owe")]
        self.assertEqual(got, [("ABC-P-002", 2), ("ABC-P-001", 0)])

    def test_waiting_on_is_the_overdue_promises_made_to_alan_with_how_long_they_have_been_quiet(self):
        got = [(r["id"], r["promised_by"], r["overdue_days"], r["quiet_days"]) for r in self.read("--list", "waiting")]
        self.assertEqual(got, [("ABC-P-003", "Sara Example", 3, 10)])     # not yet due, no date, kept or between others: left out

    def test_a_mention_resets_the_quiet_days(self):
        self.mention("ABC-P-003", d(-1))
        self.mention("ABC-P-003", d(-4))                                  # an older mention never wins
        with open(self.v.root / "system/staging/mentions.jsonl", "a", encoding="utf-8") as f:
            f.write("not json\n")                                        # a torn line is skipped
        self.assertEqual(self.read("--list", "waiting")[0]["quiet_days"], 1)

    def edit_promise(self, name, run, day, **changes):
        """An applied change to ABC-P-003 from `run` (cx-edit is Alan's own; cx-minutes is a meeting's), logged on `day`."""
        based = next(r for r in self.v.rows("promises") if r["id"] == "ABC-P-003")["updated_at"]
        self.v.propose(name, [{"n": 1, "op": "update", "table": "promises", "id": "ABC-P-003", "based_on": based,
                               "changes": changes, "decision": "approved"}], source_run=run)
        self.v.run("apply")
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con, con:
            con.execute("UPDATE change_log SET at = ? WHERE apply_id = (SELECT MAX(apply_id) FROM applies)", (f"{day} 10:00:00",))

    def test_alans_own_edit_restarts_the_quiet_clock(self):
        """Decision 5 (Alan, 13-10-2026): his own edits restart the clock, as a meeting or message raising it again does.
        A change applied from a meeting's proposal isn't his edit (the meeting is a mention), and an undone edit no longer counts."""
        self.edit_promise("meeting", "cx-minutes", d(-1), due_date=d(-2))
        self.assertEqual(self.read("--list", "waiting")[0]["quiet_days"], 10)          # a proposal file's change: not an edit
        self.edit_promise("mine", "cx-edit", d(-4), due_date=d(-1))
        got = self.read("--list", "waiting")[0]
        self.assertEqual((got["overdue_days"], got["quiet_days"]), (1, 4))
        self.mention("ABC-P-003", d(-6))                                                # the latest of the two wins
        self.assertEqual(self.read("--list", "waiting")[0]["quiet_days"], 4)
        self.v.run("undo")
        self.assertEqual(self.read("--list", "waiting")[0]["quiet_days"], 6)           # the undone edit is gone; the mention stays

    def test_lists_take_the_other_filters_and_search_reads_promises(self):
        self.assertEqual([r["id"] for r in self.read("--list", "owe", "--search", "uat")], ["ABC-P-002"])
        self.assertEqual(self.read("--list", "waiting", "--project", "DEF"), [])
        self.assertEqual([r["id"] for r in self.read("--search", "EXTRACT")], ["ABC-P-003"])
        self.assertEqual([r["id"] for r in self.read("--status", "closed")], ["ABC-P-007"])
        everything = json.loads(self.run_script("tracker.py", "read", "--search", "data extract").stdout)
        self.assertEqual([r["id"] for r in everything["promises"]], ["ABC-P-003"])

    def test_list_is_refused_off_promises_and_with_a_bad_value(self):
        r = self.run_script("tracker.py", "read", "actions", "--list", "owe", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unknown option --list", r.stderr)
        r = self.run_script("tracker.py", "read", "promises", "--list", "late", ok=False)
        self.assertIn("--list is owe or waiting", r.stderr)

    def test_the_lines_a_person_reads(self):
        sys.path.insert(0, str(REPO / "system/scripts"))
        import tracker
        self.assertEqual(tracker.promise_line({"description": "Send the SOW", "promised_to": "Sara Example",
                                               "due_date": "2026-10-16", "overdue_days": 0}),
                         "Send the SOW — to Sara Example, by 16-10-2026")
        self.assertEqual(tracker.promise_line({"description": "Call back", "promised_to": "Jane Doe", "overdue_days": 0}),
                         "Call back — to Jane Doe, no date given")
        self.assertEqual(tracker.promise_line({"promised_by": "Sara Example", "description": "Send the extract",
                                               "due_date": "2026-10-06", "overdue_days": 1, "quiet_days": 5}, waiting=True),
                         "Sara Example: Send the extract — due 06-10-2026, 1 day overdue, quiet for 5 days")


# ── cx-minutes ────────────────────────────────────────────────────────────────

class MinutesTests(Base):
    def stage(self, items):
        f = self.v.root / "system/staging/drafts/meeting.json"
        draft = self.v.root / "system/staging/drafts/steering.docx"
        if not draft.exists():
            shutil.copy(self.v.root / "system/templates/minutes-template.docx", draft)
        f.write_text(json.dumps({"title": TITLE, "date": DAY, "projects": ["ABC"], "transcript": "inbox/steering.vtt",
                                 "draft": "system/staging/drafts/steering.docx", "items": items}))
        return self.run_script("minutes.py", "stage", str(f))

    def test_a_promise_is_proposed_from_the_transcript_and_written_on_approval(self):
        out = self.stage([{"table": "promises", "section": "Omar Ali, 00:14:32", "values": {
            "project": "ABC", "promised_by": "Omar Ali", "promised_to": "Alan Carter", "description": "Send the vendor contacts"}}]).stdout
        self.assertIn("· Promise · Send the vendor contacts · Omar Ali → Alan Carter ·", out)
        item = self.staged()["items"][0]
        v = item["values"]
        self.assertEqual(v["raised"], DAY)
        self.assertTrue(v["source"].endswith("/transcripts/2026-10-07 Steering committee.vtt — Omar Ali, 00:14:32"), v["source"])
        self.assertIn("no-due-date", item["flags"])
        self.assertNotIn("invalid", item["flags"])
        self.assertEqual(item["decision"], "pending")                    # a proposal: nothing is written yet
        self.assertEqual(len(self.v.rows("promises")), len(SEED))
        self.approve_all()
        self.v.run("apply")
        row = next(r for r in self.v.rows("promises") if r["description"] == "Send the vendor contacts")
        self.assertEqual((row["id"], row["status"], row["promised_by"]), ("ABC-P-008", "Open", "Omar Ali"))

    def test_a_promise_said_again_is_a_mention_not_a_second_promise(self):
        out = self.stage([{"table": "promises", "values": {"project": "ABC", "promised_by": "Sara Example",
                                                           "promised_to": "Alan Carter", "description": "Send the data extract"}}]).stdout
        self.assertIn("already in the tracker as ABC-P-003", out)
        self.assertEqual(self.staged()["items"], [])
        mentions = (self.v.root / "system/staging/mentions.jsonl").read_text()
        self.assertIn('"id": "ABC-P-003"', mentions)
        self.assertEqual(self.read("--list", "waiting")[0]["quiet_days"], 2)        # raised again on the meeting day

    def test_a_meeting_can_mark_an_open_promise_kept_and_approve_routine_covers_it(self):
        """Decision 6 (Alan, 13-10-2026): a promise marked Done or Dropped is routine, unlike an action's closing update."""
        self.stage([{"op": "update", "table": "promises", "id": "ABC-P-003", "set": {"status": "Done"}, "why": "Sara said she sent it"},
                    {"op": "update", "table": "promises", "id": "ABC-P-007", "set": {"status": "Dropped"}, "why": "already kept"}])
        items = self.staged()["items"]
        self.assertEqual([(i["id"], i["changes"]) for i in items], [("ABC-P-003", {"status": "Done"})])   # P-007 isn't open
        self.v.run("bulk", script="review.py")
        self.assertEqual(self.staged()["items"][0]["decision"], "approved")
        self.v.run("apply")
        row = next(r for r in self.v.rows("promises") if r["id"] == "ABC-P-003")
        self.assertEqual((row["status"], bool(row["closed"])), ("Done", True))

    def test_the_bulk_rule_for_promises(self):
        """Done and Dropped are routine (decision 6); a probably-done guess (BL-218) and an action's close stay one by one."""
        sys.path.insert(0, str(REPO / "system/scripts"))
        import review
        upd = lambda table, status, **x: {"op": "update", "table": table, "id": "ABC-P-003", "changes": {"status": status}, **x}
        self.assertIsNone(review.individual_only(upd("promises", "Done")))
        self.assertIsNone(review.individual_only(upd("promises", "Dropped")))
        self.assertIsNone(review.individual_only({"op": "new", "table": "promises", "values": {}}))
        self.assertEqual(review.individual_only(upd("promises", "Done", suggested={"feature": "done"})), "closing update")
        self.assertEqual(review.individual_only(upd("actions", "Closed")), "closing update")
        self.assertEqual(review.individual_only(upd("raid", "Closed")), "closing update")

    def test_expected_lists_the_open_promises(self):
        got = json.loads(self.run_script("minutes.py", "expected", "ABC", "--title", TITLE).stdout)
        self.assertEqual([p["id"] for p in got["open_promises"]], ["ABC-P-005", "ABC-P-003", "ABC-P-002", "ABC-P-001", "ABC-P-004",
                                                                  "ABC-P-006"])     # soonest due first, no date last

    def test_refresh_from_the_draft_leaves_a_promise_alone(self):
        sys.path.insert(0, str(REPO / "system/scripts"))
        import minutes
        self.assertFalse(minutes.follows_draft({"op": "new", "table": "promises", "values": {}}))
        self.assertFalse(minutes.follows_draft({"op": "new", "table": "decisions", "values": {"status": "Pending"}}))
        self.assertTrue(minutes.follows_draft({"op": "new", "table": "actions", "values": {}}))


# ── cx-sweep ──────────────────────────────────────────────────────────────────

class SweepTests(Base):
    def setUp(self):
        super().setUp()
        self.from_sweep(True)                          # these tests are about the sweep's promises, so switch them on

    def from_sweep(self, on):
        cfg = self.v.root / "system/config/settings.json"
        s = json.loads(cfg.read_text(encoding="utf-8"))
        s.setdefault("promises", {})["from_sweep"] = on
        cfg.write_text(json.dumps(s, indent=2), encoding="utf-8")

    def stage(self, items):
        f = self.v.root / "system/staging/drafts/sweep.json"
        f.write_text(json.dumps({"window": "test", "items": items, "status_signals": []}))
        return self.run_script("sweep.py", "stage", str(f))

    def test_the_sweeps_promises_are_off_by_default(self):
        """Alan, 13-10-2026: promises.from_sweep ships off; while it is off nothing the sweep finds about a promise is staged,
        new or an update, and an action beside it still is."""
        shipped = json.loads((REPO / "system/templates/settings-defaults.json").read_text(encoding="utf-8"))
        self.assertIs(shipped["promises"]["from_sweep"], False)
        self.from_sweep(False)
        out = self.stage([
            {"table": "promises", "match": "strong", "values": {"project": "ABC", "promised_by": "Sara Example",
             "promised_to": "Alan Carter", "description": "Send the cut-over plan", "due_date": d(3), "source": MAIL}},
            {"op": "update", "table": "promises", "id": "ABC-P-003", "set": {"status": "Done"}, "why": "sent", "source": MAIL},
            {"table": "actions", "match": "strong", "values": {"project": "ABC", "owner": "Sara Example",
             "description": "Book the cut-over rehearsal", "due_date": d(3), "source": MAIL}}]).stdout
        self.assertIn("Sweep: 1 item", out)
        self.assertEqual(out.count("promises from the sweep are off"), 2)
        self.assertEqual([i["table"] for i in self.staged("proposed-2*-sweep*.json")["items"]], ["actions"])

    def test_a_promise_to_alan_from_a_message_is_raised_the_day_it_was_sent(self):
        out = self.stage([{"table": "promises", "match": "strong", "values": {
            "project": "ABC", "promised_by": "Sara Example", "promised_to": "Alan Carter", "description": "Send the cut-over plan",
            "due_date": d(3), "source": MAIL}}]).stdout
        self.assertIn("Sweep: 1 item", out)
        item = self.staged("proposed-2*-sweep*.json")["items"][0]
        self.assertEqual(item["values"]["raised"], "2026-10-08")
        self.assertEqual([f for f in item["flags"] if f != "vip"], [])
        self.approve_all()
        self.v.run("apply")
        self.assertIn("Send the cut-over plan", [r["description"] for r in self.v.rows("promises")])

    def test_an_open_promise_seen_again_is_a_mention(self):
        out = self.stage([{"table": "promises", "match": "strong", "values": {
            "project": "ABC", "promised_by": "Sara Example", "promised_to": "Alan Carter", "description": "Send the data extract",
            "source": MAIL}}]).stdout
        self.assertIn("skipped (already in the tracker)", out)
        self.assertIn('"id": "ABC-P-003"', (self.v.root / "system/staging/mentions.jsonl").read_text())

    def test_a_message_can_mark_an_open_promise_kept(self):
        self.stage([{"op": "update", "table": "promises", "id": "ABC-P-003", "set": {"status": "Done"}, "why": "Sara sent it",
                     "source": MAIL}])
        item = self.staged("proposed-2*-sweep*.json")["items"][0]
        self.assertEqual((item["op"], item["id"], item["changes"]), ("update", "ABC-P-003", {"status": "Done"}))

    def test_people_are_mapped_and_an_unknown_one_flagged(self):
        f = self.v.root / "system/staging/drafts/sweep.json"
        f.write_text(json.dumps({"items": [{"n": 1, "table": "promises", "values": {
            "project": "ABC", "promised_by": "sara.example@client.com", "promised_to": "Alan", "description": "x"}},
            {"n": 2, "table": "promises", "values": {"project": "ABC", "promised_by": "Zed Nobody", "promised_to": "Alan Carter",
                                                     "description": "y"}}]}))
        self.run_script("propose.py", "people", "map", str(f))
        items = json.loads(f.read_text())["items"]
        self.assertEqual((items[0]["values"]["promised_by"], items[0]["values"]["promised_to"]), ("Sara Example", "Alan Carter"))
        self.assertIn("unknown-owner", items[1]["flags"])


# ── Review ────────────────────────────────────────────────────────────────────

class ReviewTests(Base):
    def test_review_shows_a_promise_with_its_two_people(self):
        self.v.propose("p", [{**promise(1, "Alan Carter", "Jane Doe", "Send the risk log", d(1)), "decision": "pending"}])
        out = self.v.run("list", script="review.py").stdout
        self.assertIn("Promise", out)
        self.assertIn("Alan Carter → Jane Doe", out)

    def test_renaming_a_person_moves_their_promises(self):
        self.run_script("propose.py", "people", "rename", "Jane Doe", "Jane Doe-Smith")
        data = self.staged()
        moved = {i["id"]: i["changes"] for i in data["items"] if i.get("table") == "promises"}
        self.assertEqual(moved, {"ABC-P-002": {"promised_to": "Jane Doe-Smith"}, "ABC-P-004": {"promised_by": "Jane Doe-Smith"},
                                 "ABC-P-005": {"promised_to": "Jane Doe-Smith"}, "ABC-P-007": {"promised_by": "Jane Doe-Smith"}})


    def test_quality_counts_promises_as_their_own_type(self):
        """BL-233 measures each kind's precision; promises are the new kind whose precision is the main risk."""
        sys.path.insert(0, str(REPO / "system/scripts"))
        import quality
        self.assertEqual(quality.type_of({"op": "new", "table": "promises", "values": {}}), "promise")
        self.assertIn(("promise", "Promises"), quality.TYPES)


# ── The weekly report ─────────────────────────────────────────────────────────

class WeeklyTests(Base):
    def test_the_weekly_data_and_the_word_report_carry_the_promise_lines(self):
        data = json.loads(self.run_script("report.py", "weekly-data", "ABC", "--week-ending", d(0)).stdout)
        self.assertEqual([p["id"] for p in data["promises"]["you_owe"]], ["ABC-P-002", "ABC-P-001"])
        self.assertEqual([(p["id"], p["quiet_days"]) for p in data["promises"]["waiting_on"]], [("ABC-P-003", 10)])
        spec = {"code": "ABC", "week_ending": d(0), "health": "At risk", "health_reason": "The extract is late",
                "summary": ["The extract is late."], "key_changes": "", "current_state": "Build is behind.", "progress": [],
                "next_week": ["Run UAT."], "help_needed": []}
        f = self.v.root / "system/staging/drafts/weekly.json"
        f.write_text(json.dumps(spec))
        self.run_script("report.py", "weekly-stage", str(f))
        draft = next((self.v.root / "system/staging/drafts").glob("*Weekly report*.docx"))
        with zipfile.ZipFile(draft) as z:
            text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", z.read("word/document.xml").decode("utf-8")))
        self.assertIn("Promised: Share the UAT plan — to Jane Doe, by 07-10-2026 (2 days overdue).", text)
        self.assertIn("Promised: Send the SOW to the client — to Sara Example, by 11-10-2026.", text)
        self.assertIn("Waiting on Sara Example: Send the data extract — due 06-10-2026, 3 days overdue, quiet for 10 days.", text)
        self.assertLess(text.index("Promised: Send the SOW"), text.index("Run UAT."))


if __name__ == "__main__":
    unittest.main()
