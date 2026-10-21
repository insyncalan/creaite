"""#264 round 2: Team Cap's review of Process's R1 (READY WITH NOTES, 20-10-2026), the guarded round.

Run: python3 dev/tests/test_intake_process_round2.py      (quick tier: no Chrome, no server)

- M2: the hook claims a file for the run only once every check of the call has passed (a refused fill, write or enrich claims
  nothing), and keeps what the file was when it first saw it, so a file another flow writes over or puts in its place isn't
  the run's any more.
- L1: hooks deciding at the same moment never lose each other's claims (system/guard/run.json under a lock).
- L2: a queued ask creaite message starts under START_LOCK and never beside a run that began meanwhile (the queue holds).
- L3: a Process run reads only the vault and the projects folder (Read, Grep, Glob, LS, a script's path arguments).
- L4: the run record counts only when it is the hook's own run (its --run).
- N10 at the hook: when the record can't be written, a new file can't be claimed, so the write is refused.

They need the guarded diffs in dev/proposals/intake-process-round2/ and are expected failures until those are applied (N10
holds either way, so it always runs).
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
from test_intake_process import in_vault, put_samples  # noqa: E402
from test_tracker import Vault  # noqa: E402

REACH = (REPO / "system/scripts/reach.py").read_text(encoding="utf-8")
LIVE = (REPO / "system/scripts/live_server.py").read_text(encoding="utf-8")
R2 = "def _commit_claims" in REACH and "def process_reach_problem" in REACH
L2 = "#264 round 2 (review L2)" in LIVE
needs_r2 = (lambda f: f) if R2 else unittest.expectedFailure
needs_l2 = (lambda f: f) if L2 else unittest.expectedFailure

TPL = "system/templates/minutes-template.docx"
D = "system/staging/drafts/"

# A Process run "i-1" (or another ID), its own files named in "made", then each call decided by the hook, in order; between calls
# a {"write": name, "data": text} step stands for another flow writing into drafts; "made" and "prints" are returned at the end.
SCRIPT = r'''
import os, reach
a = json.loads(sys.stdin.read())
reach.start_run(a["record_run"], "process", {}, None, files=a["files"])
d = json.loads(reach.RUN_FILE.read_text())
d["made"] = [os.path.realpath("system/staging/drafts/" + n) for n in a["own"]]
d["before"] = [n for n in d["before"] if n not in a["staged"]]
reach.RUN_FILE.write_text(json.dumps(d))
out = []
for step in a["steps"]:
    if "write" in step:
        p = "system/staging/drafts/" + step["write"]
        tmp = p + ".tmp"
        open(tmp, "w").write(step["data"])
        os.replace(tmp, p)                                  # another flow: a new file in its place
        out.append(None)
    elif "make" in step:
        open("system/staging/drafts/" + step["make"], "w").write(step["data"])   # the run's own tool, after the hook allowed it
        out.append(None)
    else:
        out.append(reach.decide(step["tool"], step["inp"], "process", a["hook_run"], True)[0])
d = json.loads(reach.RUN_FILE.read_text())
print(json.dumps({"ok": out, "made": sorted(os.path.basename(m) for m in d.get("made", []))}))
'''


def bash(words):
    return {"tool": "Bash", "inp": {"command": "system/scripts/run " + words}}


class Round2(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        cls.v.run("init")
        cls.files = put_samples(cls.v)
        dr = cls.v.root / D
        dr.mkdir(parents=True, exist_ok=True)
        (dr / "pics.json").write_text(json.dumps({"BODY": [{"image": "~/Pictures/a.png"}]}))
        (dr / "values.json").write_text("{}")
        (dr / "board.json").write_text(json.dumps({"title": "Board", "transcript": cls.files[0],
                                                   "draft": D + "2026-10-20 Board minutes.docx"}))
        (dr / "own.json").write_text(json.dumps({"title": "Pilot", "date": "2026-10-20", "projects": ["ABC"], "transcript": cls.files[0],
                                                 "draft": D + "own minutes.docx"}))
        (dr / "pilot.json").write_text(json.dumps({"title": "Pilot", "date": "2026-10-20", "projects": ["ABC"], "transcript": cls.files[0]}))
        st = cls.v.root / "system/staging"
        cls.mine = "projects/ABC Example/minutes/2026-10-20 Pilot readiness review.docx"
        cls.theirs = "projects/ABC Example/reports/2026-10-01 ABC client report.docx"
        (st / "proposed-own.json").write_text(json.dumps({"items": [], "meeting": {"transcript": cls.files[0], "file_ops": [
            {"op": "copy", "from": "draft", "to": cls.mine}]}}))
        cls.home = Path(tempfile.mkdtemp(prefix="r2home-"))
        (cls.home / "Documents").mkdir()
        (cls.home / "Documents/private.txt").write_text("Alan's own file, not the vault's")

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def run_steps(self, steps, own=("pics.json", "values.json", "board.json", "own.json", "pilot.json"), record_run="i-1",
                  hook_run="i-1"):
        return in_vault(self.v, SCRIPT, {"files": self.files, "own": list(own), "staged": ["proposed-own.json"],
                                         "steps": steps, "record_run": record_run, "hook_run": hook_run})

    @needs_r2
    def test_m2_a_refused_call_claims_nothing(self):
        """Cap's repro: a fill refused for its pictures, a write refused as report-named and an enrich refused on its second
        --path leave no claim; another flow then writing the name makes it no Word draft of this run's."""
        board = "2026-10-20 Board minutes.docx"
        side = hashlib.sha256(self.mine.encode()).hexdigest() + ".json"
        got = self.run_steps([
            bash(f"docx_tools.py fill {TPL} {D}pics.json '{D}{board}'"),
            {"tool": "Write", "inp": {"file_path": str(self.v.root / D / "x client report.json")}},
            bash(f"search.py enrich set --path '{self.mine}' --path '{self.theirs}' --summary 'x' --tags 'a, b, c'"),
            {"write": board, "data": "PK another flow's export"},
            bash(f"minutes.py stage {D}board.json")])
        self.assertEqual(got["ok"], [False, False, False, None, False])
        for name in (board, "x client report.json", side):
            self.assertNotIn(name, got["made"])

    @needs_r2
    def test_m2_a_file_put_in_place_of_the_runs_own_is_not_its_own(self):
        """The run fills its own Word draft (claimed once allowed), the spec stages; another flow then replaces the file: the
        same spec is refused. The run's own writes are its own again (a Write of its new .json, twice)."""
        new = str(self.v.root / D / "fresh spec.json")
        got = self.run_steps([
            bash(f"docx_tools.py fill {TPL} {D}values.json '{D}own minutes.docx'"),
            {"make": "own minutes.docx", "data": "PK the run's own draft"},
            bash(f"minutes.py stage {D}own.json"),
            {"write": "own minutes.docx", "data": "PK another flow, written over it"},
            bash(f"minutes.py stage {D}own.json"),
            {"tool": "Write", "inp": {"file_path": new}},
            {"make": "fresh spec.json", "data": "{}"},
            {"tool": "Write", "inp": {"file_path": new}}])
        self.assertEqual(got["ok"], [True, None, True, None, False, True, None, True])
        self.assertIn("own minutes.docx", got["made"])

    @needs_r2
    def test_l4_the_record_counts_only_for_the_hooks_own_run(self):
        """A Process record for another run ID names no files and makes nothing this hook's run's own."""
        got = self.run_steps([bash(f"minutes.py stage {D}pilot.json"),
                              bash(f"propose.py people map {D}pilot.json"),
                              {"tool": "Write", "inp": {"file_path": str(self.v.root / D / "l4.json")}}],
                             record_run="i-other", hook_run="i-mine")
        self.assertEqual(got["ok"], [False, False, False])
        same = self.run_steps([bash(f"minutes.py stage {D}pilot.json")])
        self.assertEqual(same["ok"], [True])

    @needs_r2
    def test_l1_hooks_at_the_same_moment_keep_every_claim(self):
        """Twelve hooks at once, five new files each: all sixty are the run's afterwards."""
        in_vault(self.v, "import reach; reach.start_run('i-c', 'process', {}, None, files=[]); print(1)")
        code = ("import json, sys; sys.path.insert(0, 'system/scripts'); import os, reach\n"
                "for i in range(5):\n"
                "    p = os.path.realpath('system/staging/drafts/c-%s-%d.json' % (sys.argv[1], i))\n"
                "    assert reach.decide('Write', {'file_path': p}, 'process', 'i-c', True)[0]\n")
        procs = [subprocess.Popen([sys.executable, "-c", code, str(n)], cwd=self.v.root) for n in range(12)]
        self.assertEqual([p.wait(timeout=120) for p in procs], [0] * 12)
        made = in_vault(self.v, "import reach; print(json.dumps(len([m for m in json.loads(reach.RUN_FILE.read_text())"
                                "['made'] if '/c-' in m])))")
        self.assertEqual(made, 60)

    @needs_r2
    def test_l3_a_process_run_reads_only_the_vault_and_the_projects(self):
        """With a home folder outside the vault: Read, Grep, Glob and a script's path there are refused in a Process run (a
        plain chat is unchanged); the run's own reading in the vault still goes."""
        priv = str(self.home / "Documents/private.txt")
        calls = {"read_home": ("Read", {"file_path": priv}), "grep_home": ("Grep", {"pattern": "x", "path": str(self.home)}),
                 "glob_home": ("Glob", {"pattern": "~/Documents/*"}),
                 "script_home": ("Bash", {"command": "system/scripts/run minutes.py transcript ~/Documents/private.txt"}),
                 "read_inbox": ("Read", {"file_path": str(self.v.root / self.files[0])}),
                 "grep_vault": ("Grep", {"pattern": "Pilot"})}
        code = ("import reach; a = json.loads(sys.stdin.read()); reach.start_run('i-h', a['mode'], {}, None, files=[]); "
                "print(json.dumps({k: reach.decide(t, i, a['mode'], 'i-h', True)[0] for k, (t, i) in a['calls'].items()}))")
        env = {**os.environ, "HOME": str(self.home)}

        def run(mode):
            r = subprocess.run([sys.executable, "-c", "import json, sys; sys.path.insert(0, 'system/scripts')\n" + code],
                               input=json.dumps({"mode": mode, "calls": calls}), cwd=self.v.root, capture_output=True,
                               text=True, timeout=120, env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            return json.loads(r.stdout)
        got = run("process")
        self.assertEqual(got, {"read_home": False, "grep_home": False, "glob_home": False, "script_home": False,
                               "read_inbox": True, "grep_vault": True})
        self.assertTrue(run("ask")["read_home"])                      # a plain chat still reads the home folder

    def test_n10_when_the_record_cant_be_written_a_new_file_is_refused(self):
        """A regression guard (it holds before and after round 2): the claim now waits for the end of the call, and must still
        fail closed."""
        code =("import reach, os; reach.start_run('i-4', 'process', {}, None, files=[]); os.chmod('system/guard', 0o500)\n"
                "try:\n  r = reach.decide('Write', {'file_path': os.path.realpath('system/staging/drafts/n10.json')}, "
                "'process', 'i-4', True)[0]\nfinally:\n  os.chmod('system/guard', 0o700)\nprint(json.dumps(r))")
        try:
            self.assertFalse(in_vault(self.v, code))
        finally:
            (self.v.root / "system/guard").chmod(0o700)


# L2: live_server.queue_start with Run stood in for (nothing is started for real).
QUEUE = r'''
import threading, time, live_server as L
made = []
class FakeRun:
    def __init__(self, run_id, *a, **k):
        self.id, self.done, self.kind = run_id, False, "ask"
        made.append(run_id)
    def summary(self):
        return {"run": self.id}
L.Run = FakeRun
q = {"chat": None, "items": [{"id": "q-1", "text": "What is due?"}], "held": False}
L.START_LOCK.acquire()
t = threading.Thread(target=lambda: L.queue_start(q)); t.start(); time.sleep(0.5)
waited = not made                                         # nothing starts while another start holds the lock
L.START_LOCK.release(); t.join(10)
class Busy: done = False; kind = "process"
L.RUNS.clear(); L.RUNS["i-x"] = Busy()
q2 = {"chat": None, "items": [{"id": "q-2", "text": "And next week?"}], "held": False}
started = L.queue_start(q2)
print(json.dumps({"waited": waited, "started_after": len(made), "beside_process": started, "held": q2["held"],
                  "kept": len(q2["items"])}))
'''


class Queue(unittest.TestCase):

    @needs_l2
    def test_l2_a_queued_message_starts_under_start_lock_and_never_beside_a_run(self):
        v = Vault()
        try:
            got = in_vault(v, QUEUE)
        finally:
            v.cleanup()
        self.assertEqual(got, {"waited": True, "started_after": 1, "beside_process": None, "held": True, "kept": 1})


class ProcessSelectedMeetings(unittest.TestCase):

    def test_m1_ask_creaite_never_opens_when_intake_processes(self):
        """2.6's one Intake page (#232; the old page's processMeetings was retired in C2): Process, Make minutes and Find work
        items go straight to /api/intake/process through processLive; ask creaite's panel opens only for "ask creaite about
        this", and nothing on the page sends an ask creaite message."""
        src = (Path(__file__).resolve().parents[2] / "system/templates/dashboard/src/components/intakeReview/actions.js").read_text(
            encoding="utf-8")
        self.assertEqual(src.count("openChat()"), 1)
        self.assertLess(src.index("export function irAskAbout"), src.index("openChat()"))
        self.assertNotIn("askLive", src)
        body = src[src.index("export async function irProcess("):src.index("export function irStop")]
        self.assertEqual(body.count("processLive("), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
