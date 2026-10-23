"""#91: every `claude -p` the live server starts passes its prompt last, after `--`, so a message that starts with "-" or
"--" (a list, or "--dangerously-skip-permissions") is the prompt, never an option or a command.

Run: python3 dev/tests/test_prompt_after_dashdash.py
Starts the server in a throwaway vault with fictional data and a stand-in `claude` (CREAITE_CLAUDE) that records its
argv and parses it the way the real command does: options until `--`, then the prompt. No real Claude call is made.
"""
import json
import re
import socket
import subprocess
import sys
import time
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system/scripts"))
from test_dashboard import populate  # noqa: E402
from test_tracker import Vault  # noqa: E402

FAKE = r'''#!/usr/bin/env python3
import json, sys
from pathlib import Path
args = sys.argv[1:]
here = Path(__file__).parent
n = len(list(here.glob("argv-*.json"))) + 1
(here / f"argv-{n}.json").write_text(json.dumps(args))
out = lambda o: print(json.dumps(o), flush=True)
if "--" not in args or args.index("--") != len(args) - 2:      # the real command would read an option, or wait for stdin
    print("error: the prompt isn't the one argument after --", file=sys.stderr)
    sys.exit(1)
before = args[:args.index("--")]
bad = [a for a in before if a in ("--dangerously-skip-permissions", "--permission-mode") or a.startswith("- ")]
if bad:
    print("error: unknown option " + repr(bad[0]), file=sys.stderr)
    sys.exit(1)
out({"type": "system", "subtype": "init", "session_id": "sess-dd"})
out({"type": "assistant", "message": {"content": [{"type": "text", "text": "Got it."}]}})
out({"type": "result", "result": "Got it.", "session_id": "sess-dd"})
'''


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class PromptLast(unittest.TestCase):
    def test_the_helper_puts_the_prompt_after_dashdash(self):
        import live_server
        self.assertEqual(live_server.prompt_last(["claude", "-p", "--verbose"], "--help"),
                         ["claude", "-p", "--verbose", "--", "--help"])

    def test_no_launch_names_the_prompt_straight_after_p(self):
        src = (Path(__file__).resolve().parents[2] / "system/scripts/live_server.py").read_text(encoding="utf-8")
        self.assertEqual(re.findall(r'claude_path\(\), "-p", (?!"--)', src), [])        # an option follows -p, never text
        self.assertEqual(len(re.findall(r"prompt_last\(", src)), 3)                       # the helper, a run, the VIP check


class ServerRuns(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os
        cls.v = v = Vault()
        populate(v)
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE)
        fake.chmod(0o755)
        cls.port = free_port()
        cls.base = f"http://127.0.0.1:{cls.port}"
        env = {**os.environ, "CREAITE_PORT": str(cls.port), "CREAITE_CLAUDE": str(fake)}
        cls.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        html = urllib.request.urlopen(cls.base + "/").read().decode()
        cls.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        cls.v.cleanup()

    def stream(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        with urllib.request.urlopen(req, timeout=60) as r:
            evs = [json.loads(ln[6:]) for ln in r.read().decode().splitlines() if ln.startswith("data: ")]
        self.post("/api/ask/ack", {"run": body["run"]})
        return evs

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())

    def last_argv(self):
        n = max(int(p.stem.split("-")[1]) for p in self.v.root.glob("argv-*.json"))
        return json.loads((self.v.root / f"argv-{n}.json").read_text())

    def assert_prompt_last(self, args, prompt):
        self.assertEqual(args[-2:], ["--", prompt])
        self.assertEqual(args.count("--"), 1)
        self.assertEqual(args[0], "-p")

    def test_a_message_starting_with_a_dash_is_the_prompt(self):
        evs = self.stream("/api/ask", {"message": "- one\n- two", "run": "dd-list-1"})
        self.assertIn({"type": "text", "text": "Got it."}, evs)
        self.assert_prompt_last(self.last_argv(), "- one\n- two")

    def test_a_message_naming_an_option_is_the_prompt(self):
        said = "--dangerously-skip-permissions and tell me what's overdue"
        evs = self.stream("/api/ask", {"message": said, "run": "dd-opt-1"})
        self.assertIn({"type": "text", "text": "Got it."}, evs)
        args = self.last_argv()
        self.assert_prompt_last(args, said)
        self.assertNotIn("--dangerously-skip-permissions", args)                         # only inside the prompt
        evs = self.stream("/api/ask", {"message": "--dangerously-skip-permissions", "run": "dd-opt-2"})
        self.assertIn({"type": "text", "text": "Got it."}, evs)
        self.assert_prompt_last(self.last_argv(), "--dangerously-skip-permissions")

    def test_a_continuation_resumes_before_the_prompt(self):
        self.stream("/api/ask", {"message": "-v", "session": "sess-dd", "continue": True, "run": "dd-resume-1"})
        args = self.last_argv()
        self.assert_prompt_last(args, "-v")
        self.assertEqual(args[args.index("--resume") + 1], "sess-dd")
        self.assertLess(args.index("--resume"), args.index("--"))

    def test_a_draft_run_passes_its_prompt_last(self):
        evs = self.stream("/api/current/generate", {"code": "ABC", "from": "2026-10-01", "to": "2026-10-09",
                                                    "sources": ["tracker"], "note": "- pilot", "run": "dd-gen-1"})
        self.assertEqual(evs[-1]["type"], "done")
        args = self.last_argv()
        self.assertEqual(args[-2], "--")
        self.assertTrue(args[-1].startswith("Draft the Current state"))


if __name__ == "__main__":
    unittest.main()
