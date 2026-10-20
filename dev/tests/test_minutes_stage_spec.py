"""#269: `minutes.py stage` takes a meeting spec only from system/staging/drafts/, and only the files cx-minutes works from: a
transcript in inbox/ or in a project's minutes or transcripts folder, a quick note in a minutes folder, a Word draft directly in
system/staging/drafts/ that isn't another meeting's. Checked by the command itself (minutes_spec.py), so it holds in every mode.

Run: python3 dev/tests/test_minutes_stage_spec.py      (quick tier: no Chrome)
Each test builds a throwaway vault (test_tracker.Vault) with fictional files and runs the real script there. A refused spec stages
nothing, removes nothing and keeps the spec; the files it named are untouched.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import ABC, Vault, make_draft  # noqa: E402

DAY, TITLE = "2026-10-14", "Steering committee"
TRANSCRIPT = f"inbox/{DAY} Steering committee.vtt"
DRAFT = f"system/staging/drafts/{DAY} Steering committee.docx"
VTT = "WEBVTT\n\n00:00:01.000 --> 00:00:05.000\n<v Alan Carter>Morning all, first the SOW.</v>\n"
ACTION = {"table": "actions", "section": "Actions", "values": {"project": "ABC", "description": "Send the revised SOW",
                                                                "owner": "Alan Carter", "due_date": "2030-06-10"}}


class StageSpec(unittest.TestCase):
    def setUp(self):
        self.now = os.environ.get("CREAITE_NOW")
        os.environ["CREAITE_NOW"] = "2026-10-14 12:00"           # creaite's clock: the draft is made on the meeting's day
        self.v = Vault()
        self.v.run("init")
        self.root = self.v.root
        self.outside = Path(tempfile.mkdtemp(prefix="creaite-outside-"))       # a folder outside the vault (home, /tmp)
        self.write(TRANSCRIPT, VTT)
        make_draft(self.root / DRAFT)

    def tearDown(self):
        self.v.cleanup()
        if self.now is None:
            os.environ.pop("CREAITE_NOW", None)
        else:
            os.environ["CREAITE_NOW"] = self.now
        shutil.rmtree(self.outside, ignore_errors=True)

    def write(self, rel, text="x\n", root=None):
        p = (root or self.root) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def proposals(self):
        return sorted((self.root / "system/staging").glob("proposed-*.json"))

    def stage(self, where="system/staging/drafts/meeting.json", **spec):
        f = self.root / where
        f.parent.mkdir(parents=True, exist_ok=True)
        whole = spec.pop("whole", None)
        body = whole if whole is not None else {"title": TITLE, "date": DAY, "projects": ["ABC"], "transcript": TRANSCRIPT,
                                                "draft": DRAFT, "items": [ACTION], **spec}
        if not f.is_symlink():
            f.write_text(json.dumps(body), encoding="utf-8")
        return f, self.v.run("stage", str(f), script="minutes.py", ok=False, cwd=self.root)

    def refused(self, *named, **spec):
        """Stage `spec`: refused in plain words, nothing staged, the spec kept, and each file it named still there."""
        before = self.proposals()
        f, r = self.stage(**spec)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("Not staged:", r.stdout)
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(self.proposals(), before, "nothing is staged")
        self.assertTrue(f.exists() or f.is_symlink(), "a refused spec is kept, to fix and stage again")
        for p in named:
            self.assertTrue(Path(p).exists(), f"{p} is untouched")
        return r.stdout

    # ── Refused: a transcript from anywhere else ────────────────────────────────
    def test_a_transcript_by_a_full_path_outside_the_vault_is_refused(self):
        home = self.write("Private interview.vtt", VTT, root=self.outside)
        out = self.refused(home, transcript=str(home))
        self.assertIn("never a full or home path", out)

    def test_a_transcript_in_the_home_folder_by_tilde_is_refused(self):
        self.assertIn("never a full or home path", self.refused(transcript="~/Documents/interview.vtt"))

    def test_a_transcript_that_steps_out_with_dot_dot_is_refused(self):
        self.write("x.vtt", VTT, root=self.outside)
        out = self.refused(transcript=f"inbox/../../{self.outside.name}/x.vtt")
        self.assertIn("can't step out", out)

    def test_a_transcript_link_in_inbox_to_a_file_outside_is_refused(self):
        secret = self.write("secret.vtt", VTT, root=self.outside)
        (self.root / "inbox/link.vtt").symlink_to(secret)
        self.refused(secret, transcript="inbox/link.vtt")

    def test_a_transcript_link_to_another_inbox_file_is_refused_as_a_link(self):
        (self.root / "inbox/again.vtt").symlink_to(self.root / TRANSCRIPT)
        self.assertIn("is a link", self.refused(self.root / TRANSCRIPT, transcript="inbox/again.vtt"))

    def test_a_transcript_hard_linked_from_elsewhere_is_refused(self):
        secret = self.write("secret.vtt", VTT, root=self.outside)
        try:
            os.link(secret, self.root / "inbox/hard.vtt")
        except OSError:
            self.skipTest("no hard links across these folders")
        self.assertIn("second hard link", self.refused(secret, transcript="inbox/hard.vtt"))

    def test_a_transcript_from_a_project_documents_folder_is_refused(self):
        doc = self.write(f"{ABC}/documents/Statement of work.docx", "not a transcript")
        out = self.refused(doc, transcript=f"{ABC}/documents/Statement of work.docx")
        self.assertIn("inbox/ or in a project's minutes or transcripts folder", out)

    def test_a_transcript_from_a_notes_folder_is_refused(self):
        note = self.write(f"{ABC}/notes/{DAY} Thoughts.md", "# Thoughts\n")
        self.refused(note, transcript=f"{ABC}/notes/{DAY} Thoughts.md")

    def test_a_transcript_in_an_inbox_subfolder_or_the_system_folder_is_refused(self):
        sub = self.write("inbox/old/2026-10-01 Kick-off.vtt", VTT)
        self.refused(sub, transcript="inbox/old/2026-10-01 Kick-off.vtt")
        self.refused(self.root / "system/config/settings.json", transcript="system/config/settings.json")

    def test_a_transcript_in_an_archive_below_the_transcripts_folder_is_refused(self):
        old = self.write(f"{ABC}/transcripts/_Archive/{DAY} Old.vtt", VTT)
        self.refused(old, transcript=f"{ABC}/transcripts/_Archive/{DAY} Old.vtt")

    def test_a_file_in_another_projects_meeting_folder_is_refused(self):
        other = "projects/DEF Digital Enablement"
        t = self.write(f"{other}/transcripts/{DAY} Design review.vtt", VTT)
        out = self.refused(t, transcript=f"{other}/transcripts/{DAY} Design review.vtt")      # on approval it would leave DEF
        self.assertIn("another project's folder (DEF)", out)
        note = self.write(f"{other}/minutes/{DAY} Quick note - corridor.md", "# Quick note\n")
        self.refused(note, whole={"title": "Quick note - corridor", "date": DAY, "projects": ["ABC"],
                                  "note": f"{other}/minutes/{DAY} Quick note - corridor.md", "items": []})

    def test_a_transcript_that_isnt_a_meeting_file_is_refused(self):
        tool = self.write(f"{ABC}/transcripts/run me.sh", "echo hi\n")
        self.assertIn("must be a meeting file", self.refused(tool, transcript=f"{ABC}/transcripts/run me.sh"))

    def test_a_transcript_given_as_a_list_or_a_number_is_refused(self):
        self.assertIn("must be one path, as text", self.refused(transcript=[TRANSCRIPT]))
        self.assertIn("must be one path, as text", self.refused(transcript=7))

    def test_a_missing_transcript_is_refused_in_plain_words(self):
        self.assertIn("not found", self.refused(transcript="inbox/2026-10-14 Nobody.vtt"))

    def test_a_quick_note_given_as_a_transcript_is_refused(self):
        self.write(f"{ABC}/minutes/{DAY} Quick note - corridor.md", "# Quick note\n")
        self.assertIn("as \"note\"", self.refused(transcript=f"{ABC}/minutes/{DAY} Quick note - corridor.md"))

    # ── Refused: a Word draft from anywhere but drafts ──────────────────────────
    def test_a_word_draft_outside_drafts_is_refused(self):
        plan = self.write(f"{ABC}/documents/Plan.docx")
        out = self.refused(plan, draft=f"{ABC}/documents/Plan.docx")
        self.assertIn("never filed as minutes", out)
        inbox = self.write("inbox/Board pack.docx")
        self.refused(inbox, draft="inbox/Board pack.docx")
        home = self.write("Board pack.docx", root=self.outside)
        self.refused(home, draft=str(home))

    def test_a_draft_in_a_drafts_subfolder_or_not_word_is_refused(self):
        self.refused(draft="system/staging/drafts/notes/x.docx")
        self.write("system/staging/drafts/x.html", "<html></html>")
        self.refused(draft="system/staging/drafts/x.html")

    def test_a_draft_link_in_drafts_to_a_file_outside_is_refused(self):
        secret = self.write("Board pack.docx", root=self.outside)
        (self.root / "system/staging/drafts/linked.docx").symlink_to(secret)
        self.refused(secret, draft="system/staging/drafts/linked.docx")

    def test_a_draft_given_as_a_list_is_refused(self):
        self.assertIn("must be one path, as text", self.refused(draft=[DRAFT]))

    def test_another_meetings_draft_waiting_in_review_is_refused(self):
        other = "system/staging/drafts/2026-10-13 Design review.docx"
        make_draft(self.root / other)
        self.v.propose("other", [], meeting={"key": "k", "title": "Design review", "date": "2026-10-13", "projects": ["ABC"],
                                             "draft": other, "minutes_decision": "pending", "file_ops": []})
        self.assertIn("already waiting in Review", self.refused(self.root / other, draft=other))

    def test_a_report_draft_waiting_in_review_is_refused(self):
        rep = "system/staging/drafts/2026-10-16 Example Programme weekly report.docx"
        make_draft(self.root / rep)
        self.v.propose("weekly", [], report={"project": "ABC", "draft": rep, "report_decision": "pending", "file_ops": []})
        self.assertIn("already waiting in Review", self.refused(self.root / rep, draft=rep))

    # ── Refused: the spec itself, the note, the fields that make file names ─────
    def test_a_spec_outside_drafts_is_refused(self):
        self.assertIn("directly in system/staging/drafts/", self.refused(where="system/staging/meeting.json"))
        self.refused(where="inbox/meeting.json")

    def test_a_spec_that_is_a_link_is_refused(self):
        real = self.write("meeting.json", json.dumps({"title": TITLE, "date": DAY, "projects": ["ABC"],
                                                      "transcript": TRANSCRIPT, "draft": DRAFT}), root=self.outside)
        (self.root / "system/staging/drafts/linked.json").symlink_to(real)
        self.refused(real, where="system/staging/drafts/linked.json")

    def test_a_spec_that_is_not_an_object_is_refused(self):
        self.assertIn("JSON object", self.refused(whole=[TRANSCRIPT]))

    def test_a_note_outside_a_minutes_folder_is_refused(self):
        note = self.write(f"{ABC}/notes/{DAY} Working session.md", "# Working session\n")
        out = self.refused(note, whole={"title": "Working session", "date": DAY, "projects": ["ABC"],
                                        "note": f"{ABC}/notes/{DAY} Working session.md", "items": []})
        self.assertIn("Find updates", out)
        home = self.write("Note.md", "# x\n", root=self.outside)
        self.refused(home, whole={"title": "x", "date": DAY, "projects": ["ABC"], "note": str(home), "items": []})

    def test_a_date_or_project_that_would_make_a_path_is_refused(self):
        self.assertIn("YYYY-MM-DD", self.refused(date="../../../outside"))
        self.assertIn("project codes", self.refused(projects=["../../outside"]))
        self.assertIn("project codes", self.refused(projects="ABC"))

    # ── Review M1, L2, L4, L6 ───────────────────────────────────────────────────
    def test_a_spec_swapped_after_its_check_is_never_staged(self):
        """The spec is read once: the object checked is the object staged. A writer that swaps the file just after the check (here
        the check itself is wrapped to do it) can't get an unchecked spec staged."""
        doc = self.write(f"{ABC}/documents/Board pack.vtt", VTT)
        spec = self.root / "system/staging/drafts/race.json"
        good = {"title": TITLE, "date": DAY, "projects": ["ABC"], "transcript": TRANSCRIPT, "draft": DRAFT, "items": [ACTION]}
        bad = {**good, "title": "Board", "transcript": f"{ABC}/documents/Board pack.vtt"}
        spec.write_text(json.dumps(good), encoding="utf-8")
        code = ("import json, sys; sys.path.insert(0, 'system/scripts'); import minutes, minutes_spec\n"
                "orig = minutes_spec.spec_problem\n"
                "def swapped(s):\n"
                "    why = orig(s)\n"
                f"    open({str(spec)!r}, 'w').write({json.dumps(bad)!r})\n"
                "    return why\n"
                "minutes_spec.spec_problem = swapped\n"
                f"sys.exit(minutes.main(['stage', {str(spec)!r}]))")
        r = subprocess.run([sys.executable, "-c", code], cwd=self.root, capture_output=True, text=True,
                           env={**os.environ, "CREAITE_NOW": "2026-10-14 12:00"})
        staged = [json.loads(p.read_text())["meeting"]["transcript"] for p in self.proposals()]
        self.assertNotIn(f"{ABC}/documents/Board pack.vtt", staged, r.stdout + r.stderr)
        self.assertEqual(staged, [TRANSCRIPT], r.stdout + r.stderr)
        self.assertTrue(doc.exists())

    @unittest.skipUnless(hasattr(os, "mkfifo"), "needs named pipes")
    def test_a_spec_swapped_for_a_named_pipe_after_its_check_is_refused_without_hanging(self):
        """#269 round 2 (L-A): the spec is opened without waiting, so a named pipe put in its place between the check and the read
        (with nobody writing to it) is refused as not a plain file, never left hanging the command."""
        spec = self.root / "system/staging/drafts/pipe.json"
        spec.write_text(json.dumps({"title": TITLE, "date": DAY, "projects": ["ABC"], "transcript": TRANSCRIPT}), encoding="utf-8")
        code = ("import os, sys; sys.path.insert(0, 'system/scripts'); import minutes_spec\n"
                "orig = minutes_spec.spec_file_problem\n"
                "def swapped(*a, **k):\n"
                "    why = orig(*a, **k)\n"
                f"    os.unlink({str(spec)!r}); os.mkfifo({str(spec)!r})\n"
                "    return why\n"
                "minutes_spec.spec_file_problem = swapped\n"
                f"print(minutes_spec.load_spec({str(spec)!r}, {str(self.root)!r}))")
        try:
            r = subprocess.run([sys.executable, "-c", code], cwd=self.root, capture_output=True, text=True, timeout=20)
        except subprocess.TimeoutExpired:
            self.fail("reading a named pipe as the spec hung the command")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("(None, ", r.stdout)
        self.assertEqual(self.proposals(), [])

    def test_an_unknown_project_code_is_refused(self):
        self.assertIn("isn't a project", self.refused(projects=["ZZZ"]))
        self.assertIn("isn't a project", self.refused(projects=["ABC", "QQQ9"]))

    def test_a_hidden_or_temporary_file_is_refused_even_before_it_exists(self):
        self.write("inbox/.2026-10-14 Steering.vtt", VTT)
        self.assertIn("hidden or temporary", self.refused(transcript="inbox/.2026-10-14 Steering.vtt"))
        self.assertIn("hidden or temporary", self.refused(draft="system/staging/drafts/~$26-10-14 Steering committee.docx"))
        self.assertIn("hidden or temporary", self.refused(whole={"title": "x", "date": DAY, "projects": ["ABC"],
                                                                 "note": f"{ABC}/minutes/.{DAY} Quick note - x.md", "items": []}))

    def test_a_folder_named_like_a_transcript_is_refused(self):
        (self.root / "inbox/2026-10-14 Folder.vtt").mkdir()
        self.assertIn("isn't a file", self.refused(transcript="inbox/2026-10-14 Folder.vtt"))

    # ── Still staged: the flows that use stage ──────────────────────────────────
    def staged(self, **spec):
        before = self.proposals()
        f, r = self.stage(**spec)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        made = sorted(set(self.proposals()) - set(before))
        self.assertEqual(len(made), 1, r.stdout)
        self.assertFalse(f.exists(), "a staged spec is deleted (BL-118)")
        return json.loads(made[0].read_text(encoding="utf-8"))

    def test_an_inbox_transcript_with_its_word_draft_is_staged(self):
        data = self.staged()
        self.assertEqual((data["meeting"]["transcript"], data["meeting"]["draft"]), (TRANSCRIPT, DRAFT))

    def test_the_same_meeting_staged_again_is_not_refused_for_its_own_draft(self):
        self.staged()
        self.staged()      # e.g. after fixing a spec whose check failed: the waiting proposal is this meeting's own

    def test_a_transcript_already_in_the_transcripts_folder_is_staged_in_place(self):
        own = f"{ABC}/transcripts/{DAY} Steering committee.vtt"
        self.write(own, VTT)
        data = self.staged(transcript=own)
        self.assertNotIn({"op": "remove", "path": own}, data["meeting"]["file_ops"])

    def test_a_minutes_file_in_the_minutes_folder_is_staged(self):
        own = f"{ABC}/minutes/{DAY} Steering committee minutes.docx"
        self.write(own, "Minutes by Lena Park")
        self.staged(transcript=own)

    def test_a_quick_note_is_staged(self):
        note = f"{ABC}/minutes/{DAY} Quick note - corridor.md"
        self.write(note, "# Quick note\n\nSara will send the plan.\n")
        data = self.staged(whole={"title": "Quick note - corridor", "date": DAY, "projects": ["ABC"], "note": note,
                                  "items": [ACTION]})
        self.assertEqual(data["meeting"]["note"], note)

    def test_a_minutes_record_with_an_inbox_transcript_is_staged(self):
        data = self.staged(whole={"title": TITLE, "date": DAY, "projects": ["ABC"], "transcript": TRANSCRIPT,
                                  "minutes": {"start": "10:00", "end": "11:00", "attendees": "Alan Carter",
                                              "summary": ["The committee reviewed the SOW."]}, "items": [ACTION]})
        self.assertTrue(data["meeting"]["draft"].startswith("system/staging/drafts/"))

    def test_a_relative_spec_path_from_the_vault_is_staged(self):
        f = self.root / "system/staging/drafts/meeting.json"
        f.write_text(json.dumps({"title": TITLE, "date": DAY, "projects": ["ABC"], "transcript": TRANSCRIPT, "draft": DRAFT,
                                 "items": [ACTION]}), encoding="utf-8")
        r = subprocess.run([sys.executable, "system/scripts/minutes.py", "stage", "system/staging/drafts/meeting.json"],
                           cwd=self.root, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
