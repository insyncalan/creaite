"""#269, the guarded half: the ask creaite hook (reach.bash_refusal) makes `minutes.py stage`'s spec check before the command runs,
in every mode that lets the command through (a plain chat, a confirmed run, the catch-up sweep). Defence in depth: the command
checks its spec itself (test_minutes_stage_spec.py).

Run: python3 dev/tests/test_minutes_stage_spec_hook.py      (quick tier)
Skipped until dev/proposals/minutes-stage-spec/reach.diff is applied (reach.py is a guarded file: Alan approves the diff).
"""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import ABC, REPO, Vault, make_draft  # noqa: E402

APPLIED = "def stage_spec_gate(" in (REPO / "system/scripts/reach.py").read_text(encoding="utf-8")
SEARCH_NEVER = '("vault", "system/search", "write", RECORD)' in (REPO / "system/scripts/reach.py").read_text(encoding="utf-8")
DAY = "2026-10-14"
TRANSCRIPT = f"inbox/{DAY} Steering committee.vtt"
DRAFT = f"system/staging/drafts/{DAY} Steering committee.docx"
MODES = ("ask", "confirmed", "sweep")


@unittest.skipUnless(APPLIED, "needs dev/proposals/minutes-stage-spec/reach.diff (a guarded change)")
class HookChecksTheSpec(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        cls.root = cls.v.root
        cls.v.run("init")
        (cls.root / TRANSCRIPT).write_text("WEBVTT\n\n00:00:01.000 --> 00:00:05.000\n<v Alan Carter>Morning.</v>\n")
        make_draft(cls.root / DRAFT)
        (cls.root / ABC / "documents").mkdir(parents=True, exist_ok=True)
        (cls.root / ABC / "documents/Statement of work.docx").write_text("not a transcript")
        cls.outside = Path(tempfile.mkdtemp(prefix="creaite-outside-"))
        (cls.outside / "Board pack.docx").write_text("x")
        good = {"title": "Steering committee", "date": DAY, "projects": ["ABC"], "transcript": TRANSCRIPT, "draft": DRAFT}
        cls.specs = {"good": good,
                     "documents-transcript": {**good, "transcript": f"{ABC}/documents/Statement of work.docx"},
                     "home-draft": {**good, "draft": str(cls.outside / "Board pack.docx")},
                     "list-transcript": {**good, "transcript": [TRANSCRIPT]},
                     "dotdot-draft": {**good, "draft": "system/staging/drafts/../../../inbox/x.docx"}}
        for name, body in cls.specs.items():
            (cls.root / f"system/staging/drafts/{name}.json").write_text(json.dumps(body))
        (cls.root / "system/staging/outside.json").write_text(json.dumps(good))

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def refusals(self, commands):
        """reach.bash_refusal for each (command, mode), run in the vault: {"<mode> <command>": reason or None}."""
        code = ("import sys, json; sys.path.insert(0, 'system/scripts'); import reach\n"
                f"print(json.dumps({{f'{{m}} {{c}}': reach.bash_refusal(c, m) for c, m in {commands!r}}}))")
        r = subprocess.run([sys.executable, "-c", code], cwd=self.root, capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_a_spec_naming_a_file_from_anywhere_is_refused_in_every_mode(self):
        bad = [n for n in self.specs if n != "good"]
        cmds = [(f"system/scripts/run minutes.py stage system/staging/drafts/{n}.json", m) for n in bad for m in MODES]
        cmds += [("system/scripts/run minutes.py stage system/staging/outside.json", m) for m in MODES]
        for k, why in self.refusals(cmds).items():
            with self.subTest(k):
                self.assertTrue(why and why.startswith("minutes.py stage: "), why)

    def test_a_good_spec_and_other_commands_go_through(self):
        cmds = [("system/scripts/run minutes.py stage system/staging/drafts/good.json", m) for m in MODES]
        cmds += [("system/scripts/run minutes.py new ABC", m) for m in MODES]
        cmds += [("python3 system/scripts/minutes.py stage system/staging/drafts/good.json", "confirmed")]
        cmds += [("system/scripts/run minutes.py stage system/staging/drafts/not-there.json", m) for m in MODES]   # the command refuses it
        for k, why in self.refusals(cmds).items():
            with self.subTest(k):
                self.assertIsNone(why)

    def test_stage_with_extra_words_is_refused(self):
        why = self.refusals([("system/scripts/run minutes.py stage system/staging/drafts/good.json --x", "confirmed")])
        self.assertTrue(list(why.values())[0])


@unittest.skipUnless(SEARCH_NEVER, "needs dev/proposals/minutes-stage-spec/reach.diff (a guarded change)")
class SearchSummariesAreOnTheNeverList(unittest.TestCase):
    """#269 round 2 (M-B): a summary is written once, in every mode. system/search/ is on the never list for writes, so ask creaite
    can't replace a sidecar with `filechange.py edit` (once ordinary, at once, no card); search.py, which writes there itself,
    still does, and reading the folder is unchanged."""
    MEETING = f"{ABC}/minutes/2026-10-05 Sync.docx"

    def setUp(self):
        self.v = Vault()
        self.root = self.v.root
        self.v.run("init")
        (self.root / self.MEETING).parent.mkdir(parents=True, exist_ok=True)
        (self.root / self.MEETING).write_text("x")
        self.rel = "system/search/" + hashlib.sha256(self.MEETING.encode()).hexdigest() + ".json"
        (self.root / self.rel).parent.mkdir(parents=True, exist_ok=True)
        (self.root / self.rel).write_text(json.dumps({"path": self.MEETING, "summary": "The old summary.", "tags": ["a", "b", "c"]}))
        (self.root / "system/staging/drafts").mkdir(parents=True, exist_ok=True)
        (self.root / "system/staging/drafts/x.json").write_text(json.dumps({"path": self.MEETING, "summary": "Replaced.",
                                                                               "tags": ["a", "b", "c"]}))

    def tearDown(self):
        self.v.cleanup()

    def py(self, code):
        r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); import reach\n" + code],
                           cwd=self.root, capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_writing_a_summary_is_never_and_reading_one_is_not(self):
        got = self.py(f"print(json.dumps({{op: reach.classify({self.rel!r}, op)[0] for op in ('change', 'create', 'delete', 'read')}}))")
        self.assertEqual(got["change"], "never")
        self.assertEqual(got["create"], "never")
        self.assertEqual(got["delete"], "never")
        self.assertNotEqual(got["read"], "never")

    def test_filechange_edit_of_a_summary_is_refused(self):
        r = subprocess.run([sys.executable, str(self.root / "system/scripts/filechange.py"), "edit", self.rel,
                            "--from", "system/staging/drafts/x.json", "--why", "test"],
                           cwd=self.root, capture_output=True, text=True, timeout=120)
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("The old summary.", (self.root / self.rel).read_text())

    def test_search_py_still_writes_summaries(self):
        (self.root / self.rel).unlink()
        cmd = (f'system/scripts/run search.py enrich set --path "{self.MEETING}" --summary \'A new summary.\' '
               '--tags "pilot, escalation, supplier"')
        self.assertIsNone(self.py(f"print(json.dumps(reach.bash_refusal({cmd!r}, 'confirmed')))"))
        r = subprocess.run([sys.executable, str(self.root / "system/scripts/search.py"), "enrich", "set", "--path", self.MEETING,
                            "--summary", "A new summary.", "--tags", "pilot, escalation, supplier"],
                           cwd=self.root, capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(json.loads((self.root / self.rel).read_text())["summary"], "A new summary.")


if __name__ == "__main__":
    unittest.main()
