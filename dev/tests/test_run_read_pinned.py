"""BL-229 step 4 (v1.7.0): pin live_server's Run.read before it is split. Run.read turns Claude Code's stream (one JSON
event a line) into what the panel shows: text, steps, a stop, an error, a confirm, a permission request, refused tools,
and the final "done". Each scenario feeds the real Run.read (with the debug log's wrapper, as the server runs it) a
recorded stream through a stand-in process, inside a throwaway vault, and compares every event it emits with the saved
expectation in dev/tests/pinned/run_read/.

Not covered here: a guarded run's approval card (test_admin_card, test_ask_access) and a transcript job (test_transcripts).

Run: python3 dev/tests/test_run_read_pinned.py     (quick tier: no Chrome)
Record (only before the split, or for a reviewed change): CREAITE_PIN_RECORD=1 python3 dev/tests/test_run_read_pinned.py
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import Vault  # noqa: E402

PINNED = Path(__file__).resolve().parent / "pinned" / "run_read"
RECORD = os.environ.get("CREAITE_PIN_RECORD") == "1"


def assistant(*parts):
    return {"type": "assistant", "session_id": "s-1", "message": {"content": list(parts)}}


def text(t):
    return {"type": "text", "text": t}


def tool(i, name, inp):
    return {"type": "tool_use", "id": i, "name": name, "input": inp}


def result_of(i, error=False):
    return {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": i, "is_error": error,
                                                     "content": "ok" if not error else "failed"}]}}


def final(t, denials=()):
    return {"type": "result", "session_id": "s-1", "result": t, "permission_denials": list(denials)}


READ = tool("t1", "Read", {"file_path": "projects/ABC Example Programme/CLAUDE.md"})
SCRIPT = tool("t2", "Bash", {"command": "python3 system/scripts/tracker.py read ABC"})
SCENARIOS = {
    "answer_with_a_step": {"events": [{"type": "system", "session_id": "s-1"}, assistant(text("Looking.")), assistant(READ),
                                      result_of("t1"), assistant(text("ABC is At risk.")), final("ABC is At risk.")]},
    "a_tool_that_failed": {"events": [assistant(SCRIPT), result_of("t2", error=True), final("That didn't work.")]},
    "not_json_lines_are_skipped": {"events": ["not json", assistant(text("Fine.")), "{broken", final("Fine.")]},
    "deferred_stop_ends_after_the_step": {"attrs": {"stop": True, "confirmed": True},
                                          "events": [assistant(SCRIPT), result_of("t2"), assistant(text("never read")), final("x")]},
    "failed_without_an_answer": {"events": [assistant(text("Starting."))], "returncode": 1,
                                 "stderr": "warning: something\nError: Claude Code couldn't reach the API\n"},
    "failed_with_no_stderr": {"events": [], "returncode": 2, "stderr": ""},
    "confirm": {"events": [final("I'll write three actions.\nCONFIRM: Apply 3 items | They go to ABC and need your yes")]},
    "confirm_already_confirmed": {"attrs": {"confirmed": True},
                                  "events": [final("Done.\nCONFIRM: Apply 3 items | They go to ABC")]},
    "permission_already_allowed": {"events": [final("PERMISSION: Bash(python3 system/scripts/tracker.py *) | to read the tracker")]},
    "permission_edit_refused": {"events": [final("PERMISSION: Edit | to change a file")]},
    "permission_for_a_new_rule": {"events": [final("PERMISSION: WebFetch(domain:example.com) | to read the client's site")]},
    "refused_tools": {"events": [final("I couldn't run that.", denials=[
        {"tool_name": "Bash", "tool_input": {"command": "rm -rf projects/old"}},
        {"tool_name": "Write", "tool_input": {"file_path": "/etc/hosts", "content": "x"}}])]},
    "a_check_job_has_no_chat": {"attrs": {"kind": "check"}, "events": [final("Checked.")]},
    "text_with_a_confirm_line_inside": {"events": [assistant(text("Here it is.\nCONFIRM: Apply | now")), final("Here it is.")]},
}

HARNESS = r'''
import io, json, sys, threading, time
sys.path.insert(0, "system/scripts")
import live_server as L
spec = json.loads(sys.stdin.read())

class Proc:
    def __init__(self, lines, stderr, code):
        self.stdout, self.stderr, self.returncode, self._code, self.pid = io.StringIO(lines), io.StringIO(stderr), None, code, 0
    def poll(self):
        return self.returncode
    def wait(self, timeout=None):
        self.returncode = self._code
        return self.returncode
    def terminate(self):
        self.returncode = self._code
    kill = terminate

run = L.Run.__new__(L.Run)
lines = "".join((e if isinstance(e, str) else json.dumps(e)) + "\n" for e in spec["events"])
attrs = {"id": "r-1", "message": "How is ABC?", "session": None, "chat": None, "confirmed": False, "kind": "ask", "images": [],
         "job": None, "label": "How is ABC?", "tooluse": {}, "events": [], "cond": threading.Condition(), "watchers": 0,
         "pending": {}, "said": [], "steps": [], "stop": False, "deferred": False, "done": False, "seen": False,
         "started": time.time(), "guarded": False}
attrs.update(spec.get("attrs") or {})
for k, v in attrs.items():
    setattr(run, k, v)
run.proc = Proc(lines, spec.get("stderr", ""), spec.get("returncode", 0))
L.Run.read(run)
for e in run.events:
    if "done_at" in e:
        e["done_at"] = "<TIME>"
print(json.dumps({"events": run.events, "steps": run.steps, "said": run.said, "session": run.session,
                  "denied": getattr(run, "denied", None)}, sort_keys=True, ensure_ascii=False))
'''


class Pinned(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        cls.v.run("init")

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_run_read(self):
        for name, spec in SCENARIOS.items():
            with self.subTest(name):
                r = subprocess.run([sys.executable, "-c", HARNESS], input=json.dumps(spec), cwd=self.v.root,
                                   capture_output=True, text=True, timeout=120)
                self.assertEqual(r.returncode, 0, r.stderr)
                got = json.dumps(json.loads(r.stdout.strip().splitlines()[-1]), indent=1, sort_keys=True, ensure_ascii=False)
                got = got.replace(str(self.v.root.resolve()), "<VAULT>").replace(str(self.v.root), "<VAULT>") + "\n"   # /var is /private/var on macOS
                f = PINNED / f"{name}.json"
                if RECORD:
                    PINNED.mkdir(parents=True, exist_ok=True)
                    f.write_text(got, encoding="utf-8")
                self.assertEqual(got, f.read_text(encoding="utf-8"), f"{name}: Run.read changed")


if __name__ == "__main__":
    unittest.main()
