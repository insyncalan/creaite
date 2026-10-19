"""#232 E1 (Find work items): someone else's minutes are read for proposed items only.

Run: python3 dev/tests/test_minutes_by_others.py      (quick tier: no Chrome)
A file added in Intake that is someone else's minutes (not a transcript) is staged with `"as": "minutes"`: no draft minutes, no
minutes record, `minutes_decision` approved like a quick note. The key is the file's content, so a re-run says already processed.
On apply the inbox copy is filed in the project's minutes folder as `YYYY-MM-DD Title.ext` and the inbox copy removed. BL-260
(a transcript is never staged without its draft) must still hold, also when a transcript is passed off as minutes.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import ABC, Vault  # noqa: E402

DAY, TITLE = "2026-10-12", "[ABC] Vendor call"
FILE = "inbox/Vendor call minutes.txt"
MINUTES = ("Vendor call, 12-10-2026\nAttendees: Omar Ali, Sara Khan\nDecisions\n- Pilot starts on 2 November.\n"
           "Action items\n- Omar Ali to send the SOW by Friday.\n")
TRANSCRIPT = "WEBVTT\n\n00:00:01.000 --> 00:00:04.000\n<v Omar Ali>I'll send the SOW.</v>\n"
ITEMS = [{"table": "actions", "section": "Action Items",
          "values": {"project": "ABC", "description": "Send the SOW to the client", "owner": "Omar Ali", "due_date": "2026-10-16"}},
         {"table": "decisions", "section": "Decisions",
          "values": {"project": "ABC", "decision": "The pilot starts on 2 November", "made_by": "Sara Khan"}}]
FILED = f"{ABC}/minutes/2026-10-12 Vendor call.txt"


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        (self.v.root / FILE).write_text(MINUTES, encoding="utf-8")

    def tearDown(self):
        self.v.cleanup()

    def stage(self, ok=True, **spec):
        f = self.v.root / "system/staging/drafts/meeting.json"
        body = {"title": TITLE, "date": DAY, "projects": ["ABC"], "items": ITEMS, "as": "minutes", "file": FILE, **spec}
        f.write_text(json.dumps({k: v for k, v in body.items() if v is not None}))
        return f, self.v.run("stage", str(f), script="minutes.py", ok=ok)

    def proposals(self):
        return sorted((self.v.root / "system/staging").glob("proposed-*.json"))

    def staged(self):
        return json.loads(self.proposals()[0].read_text())

    def processed(self):
        p = self.v.root / "system/processed.txt"
        return p.read_text() if p.exists() else ""


class StageTests(Base):
    def test_it_stages_with_no_draft_and_no_minutes_record(self):
        f, r = self.stage()
        meeting = self.staged()["meeting"]
        self.assertEqual((meeting["draft"], meeting["transcript"]), (None, None))
        self.assertEqual((meeting["kind"], meeting["minutes_decision"]), ("minutes by others", "approved"))
        self.assertEqual(meeting["source_file"], FILE)
        self.assertNotIn("Draft minutes:", r.stdout)
        self.assertIn("No minutes drafted", r.stdout)
        self.assertEqual(list((self.v.root / "system/staging/drafts").glob("*.html")), [])      # no minutes record
        self.assertEqual(list((self.v.root / "system/staging/drafts").glob("*.docx")), [])      # no Word draft
        self.assertFalse(f.exists())                                                           # the spec is consumed, as always

    def test_the_items_are_sourced_to_the_filed_copy(self):
        self.stage()
        items = self.staged()["items"]
        self.assertEqual([i["values"]["source"] for i in items],
                         [f"{FILED} — Action Items", f"{FILED} — Decisions"])
        self.assertTrue(all(i["decision"] == "pending" for i in items))             # nothing is approved by staging

    def test_the_file_ops_copy_the_file_and_remove_the_inbox_copy(self):
        self.stage()
        ops = self.staged()["meeting"]["file_ops"]
        self.assertEqual(ops, [{"op": "copy", "from": FILE, "to": FILED}, {"op": "remove", "path": FILE}])

    def test_the_proposal_validates(self):
        self.stage()
        self.v.run("validate", str(self.proposals()[0]))

    def test_a_promise_is_not_read_from_someone_elses_minutes(self):
        promise = {"table": "promises", "section": "x", "values": {"project": "ABC", "promised_by": "Omar Ali",
                                                                    "promised_to": "Alan Carter", "description": "Send the deck"}}
        _, r = self.stage(items=[*ITEMS, promise])
        self.assertEqual([i["table"] for i in self.staged()["items"]], ["actions", "decisions"])
        self.assertIn("a promise is not read from someone else's minutes", r.stdout)

    def test_a_file_dated_by_its_own_date_is_flagged(self):
        self.stage()
        self.assertTrue(self.staged()["meeting"].get("date_from_file"))
        self.assertIn("date-from-file", self.staged()["items"][0]["flags"])

    def test_a_different_file_of_the_same_name_in_the_minutes_folder_is_numbered(self):
        other = self.v.root / FILED
        other.parent.mkdir(parents=True, exist_ok=True)
        other.write_text("Something else entirely\n")
        self.stage()
        copy = next(o for o in self.staged()["meeting"]["file_ops"] if o["op"] == "copy")
        self.assertEqual(copy["to"], f"{ABC}/minutes/2026-10-12 Vendor call (2).txt")

    def test_a_file_already_in_the_minutes_folder_is_left_where_it_is(self):
        own = self.v.root / f"{ABC}/minutes/2026-10-12 Vendor call.txt"
        own.parent.mkdir(parents=True, exist_ok=True)
        own.write_text(MINUTES, encoding="utf-8")
        self.stage(file=f"{ABC}/minutes/2026-10-12 Vendor call.txt")
        meeting = self.staged()["meeting"]
        self.assertEqual(meeting["file_ops"], [])
        self.assertEqual(self.staged()["items"][0]["values"]["source"].split(" — ")[0], f"{ABC}/minutes/2026-10-12 Vendor call.txt")


class Refusals(Base):
    """BL-260 still holds: a transcript is never staged without its draft, also under the minutes switch."""

    def test_a_transcript_without_a_draft_is_still_refused(self):
        (self.v.root / "inbox/catch-up.vtt").write_text(TRANSCRIPT)
        f, r = self.stage(ok=False, **{"as": None, "file": None}, transcript="inbox/catch-up.vtt")
        self.assertEqual(r.returncode, 1)
        self.assertIn("No draft minutes: run step 3", r.stdout)
        self.assertEqual(self.proposals(), [])

    def test_a_transcript_passed_off_as_minutes_is_refused(self):
        (self.v.root / "inbox/catch-up.vtt").write_text(TRANSCRIPT)
        _, r = self.stage(ok=False, transcript="inbox/catch-up.vtt")
        self.assertEqual(r.returncode, 1)
        self.assertIn("a transcript needs draft minutes", r.stdout)
        self.assertEqual(self.proposals(), [])

    def test_minutes_with_a_draft_or_a_note_are_refused(self):
        for extra in ({"draft": "system/staging/drafts/x.docx"}, {"minutes": {"summary": ["x"]}}, {"note": FILE}):
            _, r = self.stage(ok=False, **extra)
            self.assertEqual(r.returncode, 1, extra)
            self.assertIn("staged on their own", r.stdout)
        self.assertEqual(self.proposals(), [])

    def test_a_missing_file_or_an_unknown_kind_is_refused(self):
        _, r = self.stage(ok=False, file="inbox/gone.txt")
        self.assertIn("Minutes file not found: inbox/gone.txt", r.stdout)
        _, r = self.stage(ok=False, **{"as": "transcript"})
        self.assertIn("The only value is", r.stdout)
        self.assertEqual(self.proposals(), [])

    def test_no_project_stages_nothing_and_leaves_the_file(self):
        _, r = self.stage(ok=False, projects=[])
        self.assertIn("No project matched", r.stdout)
        self.assertEqual(self.proposals(), [])
        self.assertTrue((self.v.root / FILE).exists())


class ApplyTests(Base):
    """The apply files the copy (tracker.py apply, unchanged) and records the file's key, so a re-run says already processed."""

    def approve_all(self):
        p = self.proposals()[0]
        data = json.loads(p.read_text())
        for i in data["items"]:
            i["decision"] = "approved"
        p.write_text(json.dumps(data, indent=2))

    def test_nothing_is_filed_or_written_before_approval(self):
        self.stage()
        self.assertTrue((self.v.root / FILE).exists())
        self.assertFalse((self.v.root / FILED).exists())
        self.assertEqual(self.processed(), "")
        self.assertEqual(self.v.rows("actions"), [])

    def test_apply_files_the_copy_removes_the_inbox_copy_and_writes_the_items(self):
        self.stage()
        self.approve_all()
        self.v.run("apply")
        self.assertEqual((self.v.root / FILED).read_text(encoding="utf-8"), MINUTES)
        self.assertFalse((self.v.root / FILE).exists())
        self.assertEqual([a["description"] for a in self.v.rows("actions")], ["Send the SOW to the client"])
        self.assertEqual([d["decision"] for d in self.v.rows("decisions")], ["The pilot starts on 2 November"])
        self.assertEqual(self.v.rows("actions")[0]["source"], f"{FILED} — Action Items")
        self.assertIn(FILED, self.processed())

    def test_a_rerun_says_already_processed(self):
        self.stage()
        self.approve_all()
        self.v.run("apply")
        (self.v.root / FILE).write_text(MINUTES, encoding="utf-8")                   # the same file added again
        _, r = self.stage(ok=False)
        self.assertEqual(r.returncode, 3)
        self.assertIn("Already processed", r.stdout)
        self.assertEqual(self.proposals(), [])
        key = json.loads(self.v.run("key", "--date", DAY, "--title", TITLE, "--minutes", FILE, script="minutes.py").stdout)
        self.assertTrue(key["key"].startswith("fp:2026-10-12|vendor call|"))
        self.assertTrue(key["processed_on"])

    def test_the_approved_copy_is_not_offered_again_by_process_new_minutes(self):
        self.stage()
        self.approve_all()
        self.v.run("apply")
        out = self.v.run("new", "ABC", script="minutes.py").stdout
        self.assertNotIn("Vendor call", out)

    def test_undo_puts_the_inbox_copy_back_and_removes_the_filed_one(self):
        self.stage()
        self.approve_all()
        self.v.run("apply")
        self.v.run("undo")
        self.assertTrue((self.v.root / FILE).exists())
        self.assertFalse((self.v.root / FILED).exists())
        self.assertEqual(self.processed().strip(), "")

    def test_rejecting_every_item_files_nothing_until_it_is_applied(self):
        self.stage()
        self.assertTrue((self.v.root / FILE).exists())               # staging alone moves nothing


class ReadTests(Base):
    def test_the_file_reads_as_plain_text(self):
        out = self.v.run("transcript", FILE, "--minutes", script="minutes.py", cwd=self.v.root).stdout
        self.assertIn("Action items", out)
        self.assertIn("Omar Ali to send the SOW by Friday.", out)


if __name__ == "__main__":
    unittest.main()
