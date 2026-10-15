"""BL-301 (Alan, 15-10-2026): reading one of Alan's notes doesn't mark an ask creaite run as having read outside content.

A note is a .md file directly inside a project's or the portfolio's notes folder, exactly as notes.note_of accepts it. Everything
else still marks: a note's pictures (_images/), a file in a subfolder of the notes folder, another file kind there, a link named
like a note that points at a transcript, a transcript and a document in the same project. The run is started with the live
server's own table (live_server.OUTSIDE_CONTENT) and the guard hook is run exactly as Claude Code runs it (the call as JSON on its
standard input), so the server's table and the hook are tested together.

Run: python3 dev/tests/test_notes_guard.py
A fake OneDrive Engagements folder under a temporary home folder (HOME) and a temporary vault only.
"""
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_onedrive_projects import OneDriveCase, touch  # noqa: E402


class NotesAreNotOutsideContent(OneDriveCase):
    def setUp(self):
        super().setUp()
        self.vault = self.v.root.resolve()
        self.eng = self.root / "Example Programme"
        self.note = touch(self.eng / "08 Notes/Kickoff thoughts.md", "---\ntitle: Kickoff thoughts\n---\n\nSara is keen.\n")
        self.portfolio_note = touch(self.root / "_Portfolio/08 Notes/Portfolio themes.md", "Themes.\n")
        self.image = touch(self.eng / "08 Notes/_images/board.png", b"\x89PNG")
        self.image_md = touch(self.eng / "08 Notes/_images/caption.md", "A caption.\n")
        self.sub = touch(self.eng / "08 Notes/Old/older note.md", "Older.\n")
        self.other = touch(self.eng / "08 Notes/scratch.txt", "Scratch.\n")
        self.transcript = touch(self.eng / "02 Meetings/Transcripts/2026-10-01 Steering.vtt", "WEBVTT\n")
        self.document = touch(self.eng / "03 Delivery/Design/plan.md", "The plan.\n")
        self.link = self.eng / "08 Notes/Looks like a note.md"
        os.symlink(self.transcript, self.link)

    def start_run(self, run):
        """Start a run with the live server's own table, as live_server does (reach.start_run with OUTSIDE_CONTENT)."""
        self.py(f"import reach, live_server; reach.start_run({run!r}, 'ask', live_server.OUTSIDE_CONTENT); print(1)")

    def marked_by(self, path, tool="Read"):
        """What reading `path` in a fresh run marks: the run's reasons after the guard hook has seen the call."""
        run = f"r-{abs(hash(str(path))) % 10**8}"
        self.start_run(run)
        inp = {"file_path": str(path)} if tool == "Read" else {"pattern": "x", "path": str(path)}
        r = subprocess.run([sys.executable, str(self.vault / "system/scripts/reach.py"), "hook", "--run", run, "--mode", "ask"],
                           input=json.dumps({"tool_name": tool, "tool_input": inp}), capture_output=True, text=True,
                           cwd=str(self.vault))
        self.assertEqual(r.returncode, 0, r.stderr)                                       # reading is open either way
        return json.loads((self.vault / "system/guard/run.json").read_text())["marked"]

    def test_the_server_table_exempts_notes(self):
        table = self.py("import live_server; print(json.dumps(live_server.OUTSIDE_CONTENT))")
        self.assertIs(table["notes_exempt"], True)
        self.assertEqual(table["folders"], ["inbox", "transcripts", "documents"])

    def test_a_note_doesnt_mark_and_a_transcript_in_the_same_project_still_does(self):
        self.assertEqual(self.marked_by(self.note), [])
        self.assertEqual(self.marked_by(f"projects/Example Programme/08 Notes/{self.note.name}"), [])   # a stored path
        self.assertEqual(self.marked_by(self.portfolio_note), [])
        self.assertEqual(self.marked_by(self.transcript), ["read a transcript"])

    def test_everything_else_still_marks(self):
        for p in (self.image, self.image_md, self.sub, self.other, self.document):
            self.assertEqual(self.marked_by(p), ["read a project document"], p)
        self.assertEqual(self.marked_by(self.link), ["read a transcript"])               # judged by what it points at
        self.assertEqual(self.marked_by(self.eng / "08 Notes", tool="Grep"), ["read a project document"])  # the folder, searched

    def test_the_server_marks_the_same_way(self):
        """The server's own reader (Run.observe's call) agrees with the hook."""
        got = self.py("import reach, live_server\n"
                      f"ps = {[str(self.note), str(self.image), str(self.transcript)]!r}\n"
                      "print(json.dumps([reach.outside_reason('Read', {'file_path': p}, live_server.OUTSIDE_CONTENT) for p in ps]))")
        self.assertEqual(got, [None, "read a project document", "read a transcript"])

    def test_without_the_exemption_a_note_marks_as_before(self):
        got = self.py("import reach, live_server\n"
                      "t = {k: v for k, v in live_server.OUTSIDE_CONTENT.items() if k != 'notes_exempt'}\n"
                      f"print(json.dumps(reach.outside_reason('Read', {{'file_path': {str(self.note)!r}}}, t)))")
        self.assertEqual(got, "read a project document")


if __name__ == "__main__":
    unittest.main()
