"""#232 E1 (Find work items): someone else's minutes are read for proposed items only.

Run: python3 dev/tests/test_minutes_by_others.py      (quick tier: no Chrome)
A file added in Intake that is someone else's minutes (not a transcript) is staged with `"as": "minutes"`: no draft minutes, no
minutes record, `minutes_decision` approved like a quick note. The key is the file's content, so a re-run says already processed.
On apply the inbox copy is filed in the project's minutes folder as `YYYY-MM-DD Title.ext` and the inbox copy removed. BL-260
(a transcript is never staged without its draft) must still hold, also when a transcript is passed off as minutes.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
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
                         [f"{FILED} — Actions", f"{FILED} — Decisions"])
        self.assertTrue(all(i["decision"] == "pending" for i in items))             # nothing is approved by staging

    def test_the_file_ops_copy_the_file_and_remove_the_inbox_copy(self):
        self.stage()
        ops = self.staged()["meeting"]["file_ops"]
        sha = hashlib.sha256(MINUTES.encode()).hexdigest()          # the checksum the apply compares before it copies or removes
        self.assertEqual(ops, [{"op": "copy", "from": FILE, "to": FILED, "src_sha256": sha},
                               {"op": "remove", "path": FILE, "src_sha256": sha}])

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
            if "note" in extra:                  # #269's spec gate reads "note" first: a quick note must be a .md in a minutes folder
                self.assertIn('"note" must be a quick note', r.stdout)
            else:
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

    def test_empty_values_do_not_slip_past_the_check(self):
        """`minutes: {}` and `draft: ""` are falsy but given: refused, never the record path."""
        for extra in ({"minutes": {}}, {"draft": ""}, {"transcript": ""}, {"note": ""}):
            _, r = self.stage(ok=False, **extra)
            self.assertEqual(r.returncode, 1, extra)
            self.assertIn("staged on their own", r.stdout)
        self.assertEqual(self.proposals(), [])

    def test_a_transcript_by_its_type_or_its_header_is_refused(self):
        (self.v.root / "inbox/call.vtt").write_text(TRANSCRIPT)
        (self.v.root / "inbox/call.srt").write_text("1\n00:00:01,000 --> 00:00:04,000\nHello\n")
        (self.v.root / "inbox/loaded.txt").write_text("Event ID: AAMkAD123\n\nOmar Ali: I'll send it.\n")
        for f in ("inbox/call.vtt", "inbox/call.srt", "inbox/loaded.txt"):
            _, r = self.stage(ok=False, file=f)
            self.assertEqual(r.returncode, 1, f)
            self.assertIn("is a transcript, not minutes", r.stdout)
        self.assertEqual(self.proposals(), [])

    def test_an_unreadable_file_is_a_clean_refusal(self):
        if os.geteuid() == 0:
            self.skipTest("root reads everything")
        (self.v.root / FILE).chmod(0)
        try:
            _, r = self.stage(ok=False)
        finally:
            (self.v.root / FILE).chmod(0o644)
        self.assertEqual(r.returncode, 1)
        self.assertIn("can't be read", r.stdout)
        self.assertNotIn("Traceback", r.stderr)


class Confinement(Base):
    """The file is a plain path in inbox/ (or the matched project's minutes folder): the inbox copy's removal can't reach any
    other file, and only relative paths are stored."""

    def refused(self, file, **extra):
        _, r = self.stage(ok=False, file=file, **extra)
        self.assertEqual(r.returncode, 1, file)
        self.assertEqual(self.proposals(), [], file)
        return r.stdout

    def test_an_absolute_path_is_refused(self):
        outside = self.v.root.parent / "outside-minutes.txt"
        outside.write_text("x")
        try:
            self.assertIn("not a plain path", self.refused(str(outside)))
            self.assertIn("not a plain path", self.refused("/etc/hosts"))
        finally:
            outside.unlink()

    def test_a_dotdot_path_that_reaches_another_project_file_is_refused_and_the_file_survives(self):
        doc = self.v.root / f"{ABC}/documents/contract.txt"
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_text("The contract\n")
        self.assertIn("not a plain path", self.refused(f"inbox/../{ABC}/documents/contract.txt"))
        self.assertTrue(doc.exists())

    def test_a_backslash_path_is_refused_not_staged_without_a_remove(self):
        (self.v.root / "inbox/m.txt").write_text(MINUTES)
        self.assertIn("not a plain path", self.refused("inbox\\m.txt"))

    def test_a_file_outside_the_inbox_and_the_minutes_folder_is_refused(self):
        doc = self.v.root / f"{ABC}/documents/plan.txt"
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_text("The plan\n")
        self.assertIn("neither in inbox/", self.refused(f"{ABC}/documents/plan.txt"))
        self.assertTrue(doc.exists())

    def test_a_symlink_leaving_the_inbox_is_refused(self):
        target = self.v.root / f"{ABC}/documents/secret.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("Secret\n")
        (self.v.root / "inbox/link.txt").symlink_to(target)
        self.assertIn("neither in inbox/", self.refused("inbox/link.txt"))
        self.assertTrue(target.exists())

    def test_a_symlink_in_the_minutes_folder_leaving_it_is_refused(self):
        target = self.v.root / f"{ABC}/documents/secret.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("Secret\n")
        link = self.v.root / f"{ABC}/minutes/2026-10-12 Vendor call.txt"
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(target)
        self.assertIn("neither in inbox/", self.refused(f"{ABC}/minutes/2026-10-12 Vendor call.txt"))
        self.assertTrue(target.exists())

    def test_the_inbox_folder_itself_and_a_missing_file_are_refused(self):
        self.assertIn("not found", self.refused("inbox/nothing.txt"))
        self.assertIn("not found", self.refused("inbox"))

    def test_a_minutes_folder_file_of_a_project_not_matched_is_refused(self):
        other = self.v.root / f"{ABC}/minutes/2026-10-12 Vendor call.txt"
        other.parent.mkdir(parents=True, exist_ok=True)
        other.write_text(MINUTES)
        self.assertIn("neither in inbox/", self.refused(f"{ABC}/minutes/2026-10-12 Vendor call.txt", projects=[]))

    def test_only_relative_paths_reach_the_proposal(self):
        self.stage()
        text = self.proposals()[0].read_text()
        self.assertNotIn(str(self.v.root), text)
        meeting = json.loads(text)["meeting"]
        self.assertFalse(Path(meeting["source_file"]).is_absolute() or Path(meeting["note"]).is_absolute())

    def ops_for(self, file):
        """by_others_ops called directly (behind the refusal): the removal is a second line of defence."""
        code = ("import sys, json; sys.path.insert(0, 'system/scripts')\nimport minutes\n"
                f"print(json.dumps(minutes.by_others_ops({{'file': {file!r}}}, ['ABC'], '2026-10-12 Vendor call')[1]))")
        r = subprocess.run([sys.executable, "-c", code], cwd=self.v.root, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_only_a_file_in_the_inbox_is_ever_removed(self):
        other = self.v.root / f"{ABC}/documents/plan.txt"
        other.parent.mkdir(parents=True, exist_ok=True)
        other.write_text("The plan\n")
        ops = self.ops_for(f"{ABC}/documents/plan.txt")
        self.assertNotIn("remove", [o["op"] for o in ops])
        own = self.v.root / f"{ABC}/minutes/2026-10-12 Vendor call.txt"
        own.parent.mkdir(parents=True, exist_ok=True)
        own.write_text(MINUTES)
        self.assertEqual(self.ops_for(f"{ABC}/minutes/2026-10-12 Vendor call.txt"), [])
        self.assertEqual([o["op"] for o in self.ops_for(FILE)], ["copy", "remove"])

    def test_a_nested_inbox_file_is_removed_after_filing(self):
        (self.v.root / "inbox/sub").mkdir()
        (self.v.root / "inbox/sub/m.txt").write_text(MINUTES)
        self.stage(file="inbox/sub/m.txt")
        ops = self.staged()["meeting"]["file_ops"]
        self.assertEqual((ops[-1]["op"], ops[-1]["path"]), ("remove", "inbox/sub/m.txt"))


class Names(Base):
    """The filed name: only Intake's upload types, no trailing dot or space, never the same destination twice in the queue."""

    def refused(self, name, text="Vendor call minutes\n"):
        (self.v.root / "inbox" / name).write_text(text)
        _, r = self.stage(ok=False, file=f"inbox/{name}")
        self.assertEqual(r.returncode, 1, name)
        self.assertEqual(self.proposals(), [], name)
        return r.stdout

    def test_a_trailing_dot_or_space_is_refused_not_filed_as_vendor_call_dot_dot(self):
        for name in ("a.txt.", "a.txt ", "a.md..", "a.docx "):
            said = self.refused(name)            # a trailing space is refused first, as a path with spaces around it (#269)
            self.assertTrue("must end in .txt, .md, .docx or .pdf" in said or "no spaces around it" in said, (name, said))

    def test_other_types_are_refused(self):
        for name in ("a.rtf", "a.xlsx", "a", "a.eml", "a.html"):
            self.assertIn("must end in", self.refused(name), name)

    def test_the_four_types_stage_and_a_capital_extension_is_filed_lower_case(self):
        for name in ("a.txt", "a.md", "a.docx", "a.pdf", "b.TXT"):
            (self.v.root / "inbox" / name).write_text("Minutes\n")
            self.stage(file=f"inbox/{name}", title="[ABC] Name check")
            copy = next(o for o in self.staged()["meeting"]["file_ops"] if o["op"] == "copy")
            self.assertEqual(copy["to"], f"{ABC}/minutes/2026-10-12 Name check{Path(name).suffix.lower()}", name)
            self.proposals()[0].unlink()

    def test_two_staged_files_with_one_date_and_title_get_two_destinations(self):
        (self.v.root / "inbox/second.txt").write_text("A different set of minutes\n")
        self.stage()
        self.stage(file="inbox/second.txt")
        tos = [o["to"] for p in self.proposals() for o in json.loads(p.read_text())["meeting"]["file_ops"] if o["op"] == "copy"]
        self.assertEqual(set(tos), {FILED, f"{ABC}/minutes/2026-10-12 Vendor call (2).txt"})
        self.assertEqual(len(tos), 2)

    def test_the_same_file_staged_twice_is_refused_the_second_time(self):
        self.stage()
        _, r = self.stage(ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("is already in proposed-", r.stdout)                 # the first keeps it; the way forward is said
        self.assertIn("Approve or reject that one first", r.stdout)
        self.assertEqual(len(self.proposals()), 1)


class LinkedFolders(Base):
    """If inbox/ or the minutes folder is a symlink, everything under its target would count as that folder: refused."""

    def test_an_inbox_that_is_a_symlink_is_refused(self):
        other = self.v.root / f"{ABC}/documents"
        other.mkdir(parents=True, exist_ok=True)
        (other / "contract.txt").write_text("The contract\n")
        inbox = self.v.root / "inbox"
        for f in inbox.iterdir():
            f.unlink()
        inbox.rmdir()
        inbox.symlink_to(other)
        _, r = self.stage(ok=False, file="inbox/contract.txt")
        self.assertEqual(r.returncode, 1)
        self.assertIn("neither in inbox/", r.stdout)
        self.assertEqual(self.proposals(), [])
        self.assertTrue((other / "contract.txt").exists())

    def test_a_minutes_folder_that_is_a_symlink_is_refused(self):
        real = self.v.root / f"{ABC}/documents"
        real.mkdir(parents=True, exist_ok=True)
        (real / "plan.txt").write_text("The plan\n")
        folder = self.v.root / f"{ABC}/minutes"
        if folder.exists():
            shutil.rmtree(folder)
        folder.symlink_to(real)
        _, r = self.stage(ok=False, file=f"{ABC}/minutes/plan.txt")
        self.assertEqual(r.returncode, 1)
        self.assertIn("neither in inbox/", r.stdout)

    def test_a_link_deeper_in_the_inbox_path_is_refused(self):
        other = self.v.root / f"{ABC}/documents"
        other.mkdir(parents=True, exist_ok=True)
        (other / "contract.txt").write_text("The contract\n")
        (self.v.root / "inbox/sub").symlink_to(other)
        _, r = self.stage(ok=False, file="inbox/sub/contract.txt")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.proposals(), [])


class KeyTests(Base):
    def test_the_key_includes_the_content_hash(self):
        """Same date and title, different content: a different key (so a corrected file is not 'already processed')."""
        (self.v.root / "inbox/a.txt").write_text("first version\n")
        (self.v.root / "inbox/b.txt").write_text("second version\n")
        keys = [json.loads(self.v.run("key", "--date", DAY, "--title", TITLE, "--minutes", f, script="minutes.py").stdout)["key"]
                for f in ("inbox/a.txt", "inbox/b.txt")]
        self.assertNotEqual(keys[0], keys[1])
        self.assertTrue(all(re.fullmatch(r"fp:2026-10-12\|vendor call\|[0-9a-f]{12}", k) for k in keys), keys)

    def test_a_missing_file_is_a_clean_error(self):
        r = self.v.run("key", "--date", DAY, "--title", TITLE, "--minutes", "inbox/gone.txt", script="minutes.py", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("can't read inbox/gone.txt", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_reading_a_missing_file_as_minutes_fails_with_a_message(self):
        r = self.v.run("transcript", "inbox/gone.txt", "--minutes", script="minutes.py", ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("can't read inbox/gone.txt", r.stdout)


class ApplyTests(Base):
    """The apply files the copy (tracker.py apply, unchanged) and records the file's key, so a re-run says already processed."""

    def approve_all(self):
        p = self.proposals()[0]
        data = json.loads(p.read_text())
        for i in data["items"]:
            i["decision"] = "approved"
        p.write_text(json.dumps(data, indent=2))

    def test_staging_alone_files_and_writes_nothing(self):
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
        self.assertEqual(self.v.rows("actions")[0]["source"], f"{FILED} — Actions")
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



class ReadTests(Base):
    def test_the_file_reads_as_plain_text(self):
        out = self.v.run("transcript", FILE, "--minutes", script="minutes.py", cwd=self.v.root).stdout
        self.assertIn("Action items", out)
        self.assertIn("Omar Ali to send the SOW by Friday.", out)


if __name__ == "__main__":
    unittest.main()
