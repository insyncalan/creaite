"""Tests for BL-118: a staging command deletes the draft input it has finished with.

Run: python3 dev/tests/test_draft_inputs.py
Each test builds a throwaway vault (as test_tracker.py does) and runs the real scripts there.
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
GONE = "Removed draft input: "


class DraftInputs(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.root = self.v.root
        self.v.run("init")
        self.drafts = self.root / "system/staging/drafts"
        self.drafts.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.v.cleanup()

    def script(self, name, *args, cwd=None):
        return subprocess.run([sys.executable, str(self.root / "system/scripts" / name), *args], capture_output=True, text=True,
                              cwd=cwd or self.root, env={**os.environ, "CREAITE_NOW": "2026-10-09 07:10"})

    def write(self, name, data, folder=None):
        f = (folder or self.drafts) / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(data))
        return f

    def sweep_spec(self, name="sweep.json", description="Chase the signed approval", **extra):
        return self.write(name, {"window": {"start": "2026-10-08 08:00", "end": "2026-10-09 07:00"}, "items": [
            {"table": "actions", "match": "strong", "values": {"project": "ABC", "description": description,
                                                               "owner": "Alan Carter", "source": EMAIL}}], **extra})

    def edit_spec(self, name="spec.json", status="Closed"):
        return self.write(name, {"items": [{"op": "update", "table": "actions", "id": "ABC-A-001", "changes": {"status": status}}]})

    def seed(self):
        self.v.propose("seed", [action(1)])
        self.v.run("apply")

    # ── the commands ──

    def test_sweep_stage_removes_its_input_and_says_so(self):
        spec = self.sweep_spec()
        r = self.script("sweep.py", "stage", str(spec))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Sweep: 1 item", r.stdout)
        self.assertIn(GONE + "sweep.json", r.stdout.splitlines())
        self.assertFalse(spec.exists())
        self.assertEqual(len(list((self.root / "system/staging").glob("proposed-*-sweep.json"))), 1)

    def test_sweep_stage_with_nothing_to_propose_still_clears_its_input(self):
        spec = self.write("sweep.json", {"window": {}, "items": []})
        r = self.script("sweep.py", "stage", str(spec))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(spec.exists())

    def test_a_sweep_stage_that_cannot_read_its_input_keeps_it(self):
        bad = self.drafts / "sweep.json"
        bad.write_text("{not json")
        r = self.script("sweep.py", "stage", str(bad))
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue(bad.exists())
        self.assertNotIn(GONE, r.stdout)

    def test_sweep_calendar_removes_its_input(self):
        spec = self.write("calendar.json", {"days": {"2026-10-09": [{"start": "13:00", "end": "14:00", "title": "ABC steering",
                                                                      "where": "Teams", "organiser": True}]}})
        r = self.script("sweep.py", "calendar", str(spec))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Calendar saved", r.stdout)
        self.assertIn(GONE + "calendar.json", r.stdout)
        self.assertFalse(spec.exists())
        self.assertTrue((self.root / "system/staging/calendar.json").exists())          # the real calendar is a different file, kept

    def test_a_calendar_that_cannot_be_read_keeps_its_input(self):
        bad = self.drafts / "calendar.json"
        bad.write_text("nope")
        r = self.script("sweep.py", "calendar", str(bad))
        self.assertNotIn(GONE, r.stdout)
        self.assertTrue(bad.exists())

    def test_sweep_ignore_removes_its_input_and_stdout_stays_the_json_alone(self):
        f = self.write("messages.json", {"messages": [{"kind": "mail", "subject": "ToDo list"}, {"kind": "mail", "subject": "SOW"}]})
        r = self.script("sweep.py", "ignore", str(f))
        self.assertEqual(json.loads(r.stdout)["keep"], [1])                       # still parseable as it is
        self.assertIn(GONE + "messages.json", r.stderr)
        self.assertFalse(f.exists())

    def test_vip_record_removes_its_input(self):
        f = self.write("vip-found.json", [])
        r = self.script("sweep.py", "vip", "record", str(f), "--found", "sweep")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(GONE + "vip-found.json", r.stdout)
        self.assertFalse(f.exists())

    def test_propose_stage_removes_its_spec_but_preview_keeps_it(self):
        self.seed()
        spec = self.edit_spec()
        r = self.script("propose.py", "preview", str(spec))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(spec.exists())                                             # preview writes and deletes nothing
        self.assertNotIn(GONE, r.stdout)
        r = self.script("propose.py", "stage", str(spec))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Staged and approved", r.stdout)
        self.assertIn(GONE + "spec.json", r.stdout.splitlines())
        self.assertFalse(spec.exists())
        self.assertEqual(len(list((self.root / "system/staging").glob("proposed-*-edit.json"))), 1)

    def test_a_spec_that_fails_validation_is_kept_and_nothing_is_staged(self):
        self.seed()
        spec = self.edit_spec(status="Done")                                       # not a status
        r = self.script("propose.py", "stage", str(spec))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Not staged.", r.stdout)
        self.assertNotIn(GONE, r.stdout)
        self.assertTrue(spec.exists())                                             # kept, so it can be fixed and retried
        self.assertEqual(list((self.root / "system/staging").glob("proposed-*-edit.json")), [])

    def test_a_repeat_run_on_the_same_path_fails_cleanly(self):
        self.seed()
        spec = self.edit_spec()
        self.assertEqual(self.script("propose.py", "stage", str(spec)).returncode, 0)
        again = self.script("propose.py", "stage", str(spec))                      # the file is gone: the usual error, no second delete
        self.assertNotEqual(again.returncode, 0)
        self.assertNotIn(GONE, again.stdout)

    def test_minutes_stage_removes_its_spec_only_when_it_is_staged_and_checked(self):
        note = self.root / ABC / "minutes/2026-10-09 Quick note - catch-up.md"
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text("# Quick note\n\nSara will send the revised statement of work.\n")
        values = {"project": "ABC", "description": "Send the revised statement of work", "owner": "Sara Example",
                  "due_date": "2026-10-16", "raised": "2026-10-09"}
        spec = {"title": "Quick note - catch-up", "date": "2026-10-09", "event_id": None, "projects": ["ABC"],
                "note": note.relative_to(self.root).as_posix(), "status_signals": [],
                "items": [{"table": "actions", "section": "Actions", "flags": [], "values": values}]}
        f = self.write("note.json", spec)
        r = self.script("minutes.py", "stage", str(f))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(GONE + "note.json", r.stdout)
        self.assertFalse(f.exists())

    def test_report_adhoc_removes_its_spec(self):
        self.seed()
        f = self.write("adhoc-spec.json", {"title": "ABC open actions", "sections": [
            {"heading": "Summary", "paragraphs": ["One open action."]}]})
        r = self.script("report.py", "adhoc", str(f))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(GONE + "adhoc-spec.json", r.stdout)
        self.assertFalse(f.exists())
        bad = self.write("adhoc-spec.json", {"sections": []})                      # no title: the spec is refused and kept
        r = self.script("report.py", "adhoc", str(bad))
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue(bad.exists())

    # ── what is never deleted ──

    def test_a_file_outside_drafts_is_staged_and_left_alone(self):
        outside = self.root / "system/staging"
        spec = self.write("sweep.json", {"window": {}, "items": []}, folder=outside)
        r = self.script("sweep.py", "stage", str(spec))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn(GONE, r.stdout)
        self.assertTrue(spec.exists())
        elsewhere = self.write("sweep.json", {"window": {}, "items": []}, folder=self.root / "inbox")
        self.assertEqual(self.script("sweep.py", "stage", str(elsewhere)).returncode, 0)
        self.assertTrue(elsewhere.exists())

    def test_a_path_that_climbs_out_of_drafts_is_not_deleted(self):
        victim = self.write("sweep.json", {"window": {}, "items": []}, folder=self.root / "system/staging")
        sneaky = self.drafts / "sub" / ".." / ".." / "sweep.json"                  # resolves to system/staging/sweep.json
        (self.drafts / "sub").mkdir(exist_ok=True)
        r = self.script("sweep.py", "stage", str(sneaky))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn(GONE, r.stdout)
        self.assertTrue(victim.exists())
        # and a relative path that resolves inside drafts is fine, with the vault as the working folder
        inside = self.write("sweep.json", {"window": {}, "items": []})
        r = self.script("sweep.py", "stage", "system/staging/drafts/sweep.json")
        self.assertIn(GONE + "sweep.json", r.stdout)
        self.assertFalse(inside.exists())

    def test_a_symlink_in_drafts_pointing_elsewhere_is_not_followed(self):
        target = self.write("real.json", {"window": {}, "items": []}, folder=self.root / "inbox")
        link = self.drafts / "sweep.json"
        link.symlink_to(target)
        r = self.script("sweep.py", "stage", str(link))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn(GONE, r.stdout)
        self.assertTrue(target.exists())
        self.assertTrue(link.is_symlink())

    def test_only_the_named_file_goes_and_never_draft_minutes(self):
        keep_json = self.write("other.json", {"x": 1})
        draft = self.drafts / "2026-10-09 ABC steering.docx"
        draft.write_bytes(b"draft minutes")
        folder = self.drafts / "keepme.json"
        folder.mkdir()
        spec = self.sweep_spec()
        self.assertEqual(self.script("sweep.py", "stage", str(spec)).returncode, 0)
        self.assertFalse(spec.exists())
        self.assertTrue(keep_json.exists() and draft.exists() and folder.is_dir())
        # a folder (or a non-JSON file) passed as the input is never removed by the helper
        code = ("import sys; sys.path.insert(0, %r); import paths; print(repr(paths.consume_draft(%r)), repr(paths.consume_draft(%r)))"
                % (str(self.root / "system/scripts"), str(folder), str(draft)))
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=self.root)
        self.assertEqual(out.stdout.strip(), "'' ''", out.stderr)
        self.assertTrue(draft.exists() and folder.is_dir())


if __name__ == "__main__":
    unittest.main(verbosity=2)
