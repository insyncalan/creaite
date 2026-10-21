"""#232 E1 on Process's route: Intake's Find work items (someone else's minutes) runs Process's own run kind with
`"as": "minutes"`, never a confirmed ask creaite chat.

Run: python3 dev/tests/test_intake_process_minutes.py      (quick tier: no Chrome)

- intake_process.py (plain code, on this branch): a file may carry "as": "minutes" (nothing else, never a .vtt); the prompt marks
  that file and says how it is staged; the label says Find work items; a staged proposal for someone else's minutes (meeting.kind
  "minutes by others", source_file) counts as staged and as waiting in Review.
- The guard hook's mode "process" (reach.py and live_server.py: a guarded diff in dev/proposals/intake-232-minutes/): the run
  record names the files Alan pressed Find work items on; a spec with "as": "minutes" is staged only for one of those, with no
  draft, minutes, transcript or note; such a file is never staged as a transcript; a transcript file is never staged as minutes.
  Those tests are expected failures until the diff is applied (APPLIED below).
"""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "system" / "scripts"))
from test_tracker import Vault  # noqa: E402
from test_intake_process import DAY, in_vault, put_samples  # noqa: E402

APPLIED = "def process_minutes_files" in (REPO / "system/scripts/reach.py").read_text(encoding="utf-8") and \
    "as_minutes=" in (REPO / "system/scripts/live_server.py").read_text(encoding="utf-8")
needs_diff = (lambda f: f) if APPLIED else unittest.expectedFailure


class Helpers(unittest.TestCase):
    """intake_process.py with "as": "minutes", in a throwaway vault."""

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        cls.v.run("init")
        cls.files = put_samples(cls.v)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def validate(self, req):
        return in_vault(self.v, "import intake_process as ip; r = json.loads(sys.stdin.read()); "
                        "print(json.dumps(ip.validate_request(r, codes={'ABC'})))", req)

    def test_a_minutes_file_may_be_sent_as_minutes(self):
        ok, why = self.validate({"files": [{"path": self.files[2], "as": "minutes"}, {"path": self.files[0]}]})
        self.assertIsNone(why)
        self.assertEqual(ok, [{"path": self.files[2], "project": None, "as": "minutes"}, {"path": self.files[0], "project": None}])

    def test_as_is_only_minutes_and_never_for_a_vtt(self):
        for req, said in (({"files": [{"path": self.files[2], "as": "transcript"}]}, "only \"minutes\""),
                          ({"files": [{"path": self.files[2], "as": "Minutes"}]}, "only \"minutes\""),
                          ({"files": [{"path": self.files[0], "as": "minutes"}]}, "a .vtt is a transcript"),
                          ({"files": [{"path": self.files[2], "as": "minutes", "draft": "x"}]}, "Each file is")):
            with self.subTest(req):
                ok, why = self.validate(req)
                self.assertIsNone(ok)
                self.assertIn(said, why)

    def test_the_prompt_marks_the_minutes_file_and_says_how_it_is_staged(self):
        import intake_process as ip
        plain = ip.build_prompt([{"path": "inbox/a.vtt", "project": None}])
        self.assertNotIn("someone else's minutes", plain)                  # a transcript-only prompt is as before
        p = ip.build_prompt([{"path": "inbox/a.vtt", "project": None}, {"path": "inbox/b.docx", "project": "ABC", "as": "minutes"}])
        self.assertIn('1. path: "inbox/a.vtt"\n', p)
        self.assertIn('2. path: "inbox/b.docx" (project ABC, as set in Intake) (someone else\'s minutes: find work items)\n', p)
        self.assertIn("minutes.py transcript <file> --minutes", p)
        self.assertIn('"as": "minutes" and "file"', p)
        self.assertIn("draft no minutes", p)
        self.assertEqual(ip.label([{"path": "inbox/b.docx", "as": "minutes"}]), "Find work items in 1 Intake file")
        self.assertEqual(ip.label([{"path": "inbox/b.docx", "as": "minutes"}, {"path": "inbox/a.vtt"}]), "Process 2 Intake files")

    def test_staged_minutes_by_others_count_as_staged_and_waiting(self):
        st = self.v.root / "system/staging"
        (st / "proposed-e1.json").write_text(json.dumps({"items": [], "meeting": {
            "kind": "minutes by others", "transcript": None, "draft": None, "source_file": self.files[2], "note": "x"}}))
        try:
            got = in_vault(self.v, "import intake_process as ip, time; "
                           "print(json.dumps([sorted(ip.staged_paths(time.time() - 60)), sorted(ip._waiting())]))")
            self.assertEqual(got, [[self.files[2]], [self.files[2]]])
            ok, why = self.validate({"files": [{"path": self.files[2], "as": "minutes"}]})
            self.assertIsNone(ok)
            self.assertIn("already waiting in Review", why)
        finally:
            (st / "proposed-e1.json").unlink()


class Fence(unittest.TestCase):
    """The guard hook's mode "process" with a Find work items file (reach.decide), in a throwaway vault."""

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        cls.v.run("init")
        cls.files = put_samples(cls.v)
        cls.vtt, cls.mins = cls.files[0], cls.files[2]
        d = cls.v.root / "system/staging/drafts"
        d.mkdir(parents=True, exist_ok=True)
        base = {"title": "Budget review", "date": DAY, "projects": ["ABC"]}
        specs = {
            "byothers.json": {**base, "as": "minutes", "file": cls.mins},
            "byothers_vtt.json": {**base, "as": "minutes", "file": cls.vtt},           # a transcript pressed with Make minutes
            "byothers_draft.json": {**base, "as": "minutes", "file": cls.mins, "draft": "system/staging/drafts/x.docx"},
            "byothers_transcript.json": {**base, "as": "minutes", "file": cls.mins, "transcript": cls.mins},
            "byothers_note.json": {**base, "as": "minutes", "file": cls.mins, "note": cls.mins},
            "byothers_as.json": {**base, "as": "Minutes", "file": cls.mins},
            "byothers_list.json": {**base, "as": "minutes", "file": [cls.mins]},
            "mins_as_transcript.json": {**base, "transcript": cls.mins, "minutes": {"summary": ["x"]}},
            "vtt.json": {**base, "transcript": cls.vtt, "minutes": {"summary": ["x"]}},
        }
        for n, s in specs.items():
            (d / n).write_text(json.dumps(s))
        cls.own = list(specs)
        st = cls.v.root / "system/staging"
        (st / "proposed-e1.json").write_text(json.dumps({"items": [], "meeting": {
            "kind": "minutes by others", "transcript": None, "draft": None, "source_file": cls.mins, "note": "x"}}))

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def decide(self, calls, as_minutes=None, mode="process"):
        code = ("import os, reach; a = json.loads(sys.stdin.read()); "
                "kw = {'files': a['files']} if a['mode'] == 'process' else {}; "
                "kw.update({'as_minutes': a['as_minutes']} if a['mode'] == 'process' and "
                "'as_minutes' in reach.start_run.__code__.co_varnames else {}); "
                "reach.start_run('i-1', a['mode'], {}, None, **kw); "
                "d = json.loads(reach.RUN_FILE.read_text()); d['started'] -= 600; "
                "d.update({'made': [os.path.realpath('system/staging/drafts/' + n) for n in a['own']]} if 'made' in d else {}); "
                "d.update({'before': [n for n in d['before'] if n != 'proposed-e1.json']} if 'before' in d else {}); "
                "reach.RUN_FILE.write_text(json.dumps(d)); "
                "print(json.dumps({k: reach.decide(t, i, a['mode'], 'i-1', True) for k, (t, i) in a['calls'].items()}))")
        return in_vault(self.v, code, {"mode": mode, "files": self.files, "own": self.own, "calls": calls,
                                       "as_minutes": [self.mins] if as_minutes is None else as_minutes})

    @staticmethod
    def stage(name):
        return ("Bash", {"command": f"system/scripts/run minutes.py stage system/staging/drafts/{name}"})

    @needs_diff
    def test_find_work_items_stages_only_as_minutes_for_its_own_file(self):
        got = self.decide({"ok": self.stage("byothers.json"),
                           "read": ("Bash", {"command": f"system/scripts/run minutes.py transcript '{self.mins}' --minutes"}),
                           "transcript_ok": self.stage("vtt.json")})
        for k, (ok, why) in got.items():
            with self.subTest(k):
                self.assertTrue(ok, why)

    @needs_diff
    def test_a_minutes_spec_is_refused_for_anything_else(self):
        got = self.decide({n: self.stage(n) for n in ("byothers_vtt.json", "byothers_draft.json", "byothers_transcript.json",
                                                     "byothers_note.json", "byothers_as.json", "byothers_list.json",
                                                     "mins_as_transcript.json")})
        for k, (ok, why) in got.items():
            with self.subTest(k):
                self.assertFalse(ok, k)
                self.assertNotIn("Error", why)                                    # a plain refusal, never a crash

    @needs_diff
    def test_without_find_work_items_a_minutes_spec_is_refused(self):
        ok, why = self.decide({"s": self.stage("byothers.json")}, as_minutes=[])["s"]
        self.assertFalse(ok)
        self.assertIn("Find work items", why)

    @needs_diff
    def test_the_run_record_names_the_find_work_items_files(self):
        got = in_vault(self.v, "import reach; a = json.loads(sys.stdin.read()); "
                       "reach.start_run('i-2', 'process', {}, None, files=a[0], as_minutes=a[1]); reach._HOOK['run'] = 'i-2'; "
                       "d = json.loads(reach.RUN_FILE.read_text()); "
                       "print(json.dumps([d['files_as_minutes'], sorted(reach.process_minutes_files())]))",
                       [self.files, [self.mins, "inbox/not one of the files.docx"]])
        self.assertEqual(got[0], [self.mins, "inbox/not one of the files.docx"])
        self.assertEqual(got[1], [self.mins])                                     # only one of the run's own files
        # a record for another mode names none
        got = in_vault(self.v, "import reach; reach.start_run('i-3', 'ask', {}, None); reach._HOOK['run'] = 'i-3'; "
                       "print(json.dumps(sorted(reach.process_minutes_files())))")
        self.assertEqual(got, [])

    @needs_diff
    def test_its_proposal_is_the_runs_by_its_source_file(self):
        got = in_vault(self.v, "import reach, os; a = json.loads(sys.stdin.read()); "
                       "reach.start_run('i-4', 'process', {}, None, files=a[0], as_minutes=a[1]); reach._HOOK['run'] = 'i-4'; "
                       "d = json.loads(reach.RUN_FILE.read_text()); d['before'] = []; reach.RUN_FILE.write_text(json.dumps(d)); "
                       "print(json.dumps([os.path.basename(str(p)) for p, _ in reach._runs_proposals()]))",
                       [self.files, [self.mins]])
        self.assertIn("proposed-e1.json", got)
        got = in_vault(self.v, "import reach, os; a = json.loads(sys.stdin.read()); "
                       "reach.start_run('i-5', 'process', {}, None, files=a[0], as_minutes=[]); reach._HOOK['run'] = 'i-5'; "
                       "d = json.loads(reach.RUN_FILE.read_text()); d['before'] = []; reach.RUN_FILE.write_text(json.dumps(d)); "
                       "print(json.dumps([os.path.basename(str(p)) for p, _ in reach._runs_proposals()]))", [self.files])
        self.assertNotIn("proposed-e1.json", got)                                 # not pressed Find work items on: not the run's


if __name__ == "__main__":
    unittest.main(verbosity=1)
