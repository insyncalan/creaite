"""BL-268 follow-up: a refused command's kind in the debug log, so the next refusal is diagnosable at once.

The live run that failed to save the calendar (BL-268) logged only "a command that isn't a creaite script". Now:
- reach.command_kind_words names the kind in a few words, never the command's text, paths or arguments: a common program by
  name (ls, cat, cd…), python -c or with another file, a program by its path, a creaite script by its full path (this vault or
  another folder), a creaite script refused for something else (its name), or another program;
- the guard hook's line is "refused Bash (<kind>): <why>", and it still refuses (exit 2), also when the call can't be read;
- live_server.refused_shape adds the kind to "a command that isn't a creaite script (…)" and knows the system/scripts/run
  wrapper as a creaite script; doctor's counts (log.refusals) still count it under "not a creaite script".

Run: python3 dev/tests/test_refusal_kind.py     (quick tier: no Chrome)
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import reach  # noqa: E402
import live_server  # noqa: E402
from test_tracker import Vault  # noqa: E402

ROOT = str(reach.paths.ROOT)
KINDS = [("ls system/staging/drafts", "ls"),
         ("cat system/staging/drafts/calendar.json", "cat"),
         ("cd /tmp/secret-folder && ls", "cd"),
         ("python3 -c 'import os; print(os.listdir())'", "python -c"),
         ("python3 build.js", "python with another file"),
         ("node build.js --secret-arg", "node"),
         ("/usr/bin/mv a.json b.json", "mv by its path"),
         ("/opt/tools/frobnicate --x", "a program by its path"),
         ("frobnicate --token abc123", "another program"),
         ("", "an empty command"),
         (f"{ROOT}/system/scripts/run sweep.py calendar x.json", "sweep.py by its full path (this vault)"),
         (f"python3 {ROOT}/system/scripts/sweep.py calendar x.json", "sweep.py by its full path (this vault)"),
         ("/tmp/elsewhere/system/scripts/run sweep.py calendar x.json", "sweep.py by its full path (another folder)"),
         ("system/scripts/run sweep.py calendar x.json | tail", "sweep.py"),
         ("python3 system/scripts/propose.py stage x.json > y", "propose.py")]


class Words(unittest.TestCase):
    def test_each_kind_in_a_few_words(self):
        for cmd, want in KINDS:
            with self.subTest(cmd):
                self.assertEqual(reach.command_kind_words(cmd), want)

    def test_never_the_command_text_paths_or_arguments(self):
        for cmd, _ in KINDS:
            words = reach.command_kind_words(cmd)
            for secret in ("secret", "abc123", "/tmp", "drafts", ".json", "listdir", "Users", "frobnicate"):
                with self.subTest(cmd=cmd, secret=secret):
                    self.assertNotIn(secret, words)

    def test_the_live_servers_shape_names_the_kind(self):
        shape = lambda c: live_server.refused_shape({"tool_name": "Bash", "tool_input": {"command": c}})  # noqa: E731
        self.assertEqual(shape("ls system/staging/drafts"), "a command that isn't a creaite script (ls)")
        self.assertEqual(shape("system/scripts/run sweep.py calendar x.json | tail"), "sweep.py with a pipe")   # the wrapper is a script
        self.assertEqual(shape("python3 system/scripts/propose.py stage x > y"), "propose.py with a redirect")    # as before


class HookLog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        cls.v.run("init")

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def hook(self, stdin):
        return subprocess.run([sys.executable, "system/scripts/reach.py", "hook", "--run", "r-1", "--mode", "ask"], input=stdin,
                              cwd=self.v.root, capture_output=True, text=True, timeout=60)

    def log(self):
        return "".join(p.read_text(encoding="utf-8") for p in sorted((self.v.root / "system/logs").glob("debug-*.log")))

    def test_a_refused_command_is_logged_with_its_kind_and_still_refused(self):
        r = self.hook(json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls system/staging/drafts"}}))
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("refused Bash (ls): ask creaite runs only creaite's own scripts", self.log())
        self.assertNotIn("staging/drafts", self.log())

    def test_a_call_that_cant_be_read_is_still_refused(self):
        for stdin in ("{not json", json.dumps({"tool_name": "Bash", "tool_input": "a string"})):
            with self.subTest(stdin):
                self.assertEqual(self.hook(stdin).returncode, 2)

    def test_doctors_counts_still_count_it(self):
        code = ("import sys; sys.path.insert(0, 'system/scripts'); import log; "
                "log.warn('run', \"r9 refused: a command that isn't a creaite script (ls)\"); print(log.refusals_line())")
        r = subprocess.run([sys.executable, "-c", code], cwd=self.v.root, capture_output=True, text=True, timeout=60)
        self.assertIn("× not a creaite script", r.stdout)


if __name__ == "__main__":
    unittest.main()
