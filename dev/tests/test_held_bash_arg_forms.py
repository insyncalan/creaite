"""Held runs read only (security fix, 15-10-2026): the never list holds for every form of a script argument in a held run.

A run creaite starts itself (guard hook mode "held", and the older "prep") may run one creaite read command on its own. Before the
fix the hook didn't apply the never list to that command's arguments, so `python3 system/scripts/minutes.py transcript
~/.ssh/key-backup.txt` printed a key to the model (dev/tests/test_held_run_bash_writes.py, test_6). This test feeds the real hook,
as Claude Code runs it, every form that could name the secret: `~`, `$HOME` and `${HOME}` (bare, double- and single-quoted),
`~user`, a relative path, quoted and escaped forms, `--opt=PATH`, a path inside a longer argument, a symlink to the file and to its
folder, wildcards, the full vault path and the wrapper, `env`, `cd`, chains, `$(…)`, back-quotes, a new line, a redirect and other
programs. Each one is refused in both modes, and the table says by what: the never list (reach.held_never_reason), the shell form
(reach.bash_problem) or the command's kind (reach.held_kind_reason). A plain read of an ordinary file is still let through.

No model is called. A throwaway vault and a fake home folder with ~/.ssh/id_rsa holding a fake key.

Run: python3 dev/tests/test_held_bash_arg_forms.py     (quick tier: no Chrome)
"""
import getpass
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_tracker import ABC, Vault  # noqa: E402

NEVER, SHELL, KIND, FORM = "never list", "shell form", "not a read command", "held form"
T = "system/scripts/run minutes.py transcript"
P = "python3 system/scripts/minutes.py transcript"


def forms(root, home):
    """(name, command, what refuses it)."""
    rel = os.path.relpath(home / ".ssh/id_rsa", root)
    return [
        ("plain ~ (python3 form)", f"{P} ~/.ssh/id_rsa", NEVER),
        ("plain ~ (wrapper form)", f"{T} ~/.ssh/id_rsa", NEVER),
        ("the folder itself", f"{T} ~/.ssh", NEVER),
        ("~ then ..", f"{T} ~/.ssh/../.ssh/id_rsa", NEVER),
        ("absolute path", f"{T} {home}/.ssh/id_rsa", NEVER),
        ("full vault path to the script", f"python3 {root}/system/scripts/minutes.py transcript ~/.ssh/id_rsa", NEVER),
        ("full vault path to the wrapper", f"{root}/system/scripts/run minutes.py transcript ~/.ssh/id_rsa", NEVER),
        ("~user", f"{T} ~{getpass.getuser()}/.ssh/id_rsa", NEVER),
        ("relative ../..", f"{T} {rel}", NEVER),
        ("./ then relative", f"{T} ./{rel}", NEVER),
        ("double-quoted ~", f'{T} "~/.ssh/id_rsa"', NEVER),
        ("single-quoted ~", f"{T} '~/.ssh/id_rsa'", NEVER),
        ("single-quoted $HOME", f"{T} '$HOME/.ssh/id_rsa'", NEVER),
        ("single-quoted ${HOME}", f"{T} '${{HOME}}/.ssh/id_rsa'", NEVER),
        ("--opt=PATH", f"{T} --from=~/.ssh/id_rsa", NEVER),
        ("--opt PATH", f"{T} --from ~/.ssh/id_rsa", NEVER),
        ("-o=PATH", f"{T} -f=~/.ssh/id_rsa", NEVER),
        ("inside a longer argument (=)", f"{T} file=~/.ssh/id_rsa", NEVER),
        ("inside a longer argument (:)", f"{T} a:~/.ssh/id_rsa", NEVER),
        ("inside a longer argument (,)", f"{T} a.vtt,~/.ssh/id_rsa", NEVER),
        ("symlink to the file", f"{T} system/staging/drafts/key.vtt", NEVER),
        ("symlink to the folder", f"{T} system/staging/drafts/keys/id_rsa", NEVER),
        ("wildcard ?", f"{T} ~/.ss?/id_rsa", NEVER),
        ("wildcard *", f"{T} ~/.s*/id_r*", NEVER),
        ("wildcard [ ]", f"{T} ~/.ssh/id_[r]sa", NEVER),
        ("wildcard, absolute", f"{T} {home}/.*/id_rsa", NEVER),
        ("reach.py wrap", "system/scripts/run reach.py wrap minutes.py transcript ~/.ssh/id_rsa", NEVER),
        ("reach.py wrap, no path", "system/scripts/run reach.py wrap report.py adhoc x.json", KIND),
        ("bare $HOME", f"{T} $HOME/.ssh/id_rsa", SHELL),
        ("double-quoted $HOME", f'{T} "$HOME/.ssh/id_rsa"', SHELL),
        ("${HOME}", f"{T} ${{HOME}}/.ssh/id_rsa", SHELL),
        ("$'…' quoting", f"{T} $'\\x7e/.ssh/id_rsa'", SHELL),
        ("escaped ~", f"{T} \\~/.ssh/id_rsa", SHELL),
        ("env VAR=… cmd", f"env HOME={home} {T} ~/.ssh/id_rsa", SHELL),
        ("VAR=… cmd", f"HOME={home} {T} x.vtt", SHELL),
        ("cd X && cmd", f"cd ~/.ssh && {T} id_rsa", SHELL),
        ("; chain", f"{T} x.vtt; cat ~/.ssh/id_rsa", SHELL),
        ("&& chain", f"{T} x.vtt && cat ~/.ssh/id_rsa", SHELL),
        ("| pipe", f"cat ~/.ssh/id_rsa | {T} -", SHELL),
        ("$(…)", f"{T} $(echo ~/.ssh/id_rsa)", SHELL),
        ("back-quotes", f"{T} `echo ~/.ssh/id_rsa`", SHELL),
        ("$(…) in double quotes", f'{T} "$(cat ~/.ssh/id_rsa)"', SHELL),
        ("new line", f"{T} x.vtt\ncat ~/.ssh/id_rsa", SHELL),
        ("redirect <", f"{T} - < ~/.ssh/id_rsa", SHELL),
        ("another program", "cat ~/.ssh/id_rsa", SHELL),
        ("python3 -c", "python3 -c 'print(open(\"/x\").read())'", SHELL),
        ("a program by its path", "/bin/cat ~/.ssh/id_rsa", SHELL),
        ("a stage command, no path", "system/scripts/run report.py adhoc system/staging/drafts/a.json", KIND),
        # review N1: a shell comment hides the read flag command_kind looks for (reach.held_form_reason)
        ("# --dry-run after review.py assign", "system/scripts/run review.py assign ABC-A-001 Sara # --dry-run", FORM),
        ("# --dry-run after propose.py recode", "system/scripts/run propose.py recode ABC XYZ # --dry-run", FORM),
        ("# --check after propose.py learn", "system/scripts/run propose.py learn x.json # --check", FORM),
        ("# --dry-run after minutes.py baseline", "python3 system/scripts/minutes.py baseline # --dry-run", FORM),
        ("# at the start of the arguments", f"{T} #x ~/.ssh/id_rsa", FORM),
        ("a#b inside a word", f"{T} a#b.vtt", FORM),
        ("quoted '#'", f"{T} '#' x.vtt", FORM),
        # review N2: the shell's own folders, which the hook can't resolve (reach.held_form_reason)
        ("~-", f"{T} ~-/.ssh/id_rsa", FORM),
        ("~+", f"{T} ~+/../.ssh/id_rsa", FORM),
        ("~ and a number", f"{T} ~1/.ssh/id_rsa", FORM),
        ("--opt=~-", f"{T} --from=~-/.ssh/id_rsa", FORM),
        ("~+ after :", f"{T} a:~+/x", FORM),
        ("~- after ,", f"{T} a.vtt,~-/x", FORM),
        ("single-quoted $OLDPWD", f"{T} '$OLDPWD/.ssh/id_rsa'", FORM),
        ("single-quoted ${PWD}", f"{T} '${{PWD}}/../.ssh/id_rsa'", FORM),
        ("$PWD after =", f"{T} --from='$PWD'/x", FORM),
        ("$OLDPWD after ,", f"{T} a,'$OLDPWD'/x", FORM),
        # review N4: // then a path is the root on macOS; only a web address's host is skipped (reach.held_arg_paths)
        ("// path", f"{T} /{home}/.ssh/id_rsa", NEVER),
        ("// path after :", f"{T} a:/{home}/.ssh/id_rsa", NEVER),
        ("// path after =", f"{T} file=/{home}/.ssh/id_rsa", NEVER),
        ("// path after ,", f"{T} a.vtt,/{home}/.ssh/id_rsa", NEVER),
        ("file:// URL", f"{T} file://{home}/.ssh/id_rsa", NEVER),
    ]


class HeldArgForms(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        cls.v.run("init")
        cls.root = cls.v.root
        cls.home = Path(tempfile.mkdtemp(prefix="held-forms-home-")).resolve()
        (cls.home / ".ssh").mkdir()
        (cls.home / ".ssh/id_rsa").write_text("FAKE-PRIVATE-KEY-FOR-THE-TEST\n")
        drafts = cls.root / "system/staging/drafts"
        drafts.mkdir(parents=True, exist_ok=True)
        os.symlink(cls.home / ".ssh/id_rsa", drafts / "key.vtt")
        os.symlink(cls.home / ".ssh", drafts / "keys")
        (cls.root / ABC / "transcripts").mkdir(parents=True, exist_ok=True)
        (cls.root / ABC / "transcripts/2026-10-02 Weekly.vtt").write_text("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n<v Sara>Hello\n")
        cls.env = {**os.environ, "HOME": str(cls.home)}
        cls.rows = []

    @classmethod
    def tearDownClass(cls):
        print("\n" + "\n".join(cls.rows))
        cls.v.cleanup()
        shutil.rmtree(cls.home, ignore_errors=True)

    def hook(self, mode, command):
        r = subprocess.run(["/bin/sh", "system/scripts/run", "reach.py", "hook", "--run", "r-forms", "--mode", mode], cwd=self.root,
                           input=json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": command}}),
                           capture_output=True, text=True, timeout=60, env=self.env)
        return r.returncode, r.stderr.strip()

    @staticmethod
    def by(why):
        if "holds secrets" in why or "outside the vault, the projects folder and your home folder" in why:
            return NEVER
        if "isn't a read command" in why:
            return KIND
        if "which the shell reads as a comment" in why or "$PWD or $OLDPWD" in why or "~-, ~+" in why:
            return FORM
        if "ask creaite runs only creaite's own scripts" in why or "shell characters" in why or "$ or a back-quote" in why:
            return SHELL
        return "other: " + why

    def test_every_form_is_refused(self):
        for name, cmd, expected in forms(self.root, self.home):
            for mode in ("held", "prep"):
                with self.subTest(form=name, mode=mode):
                    code, why = self.hook(mode, cmd)
                    self.assertEqual(code, 2, f"{cmd!r}: {why}")
                    self.assertNotIn("FAKE-PRIVATE-KEY", why)
                    self.assertEqual(self.by(why), expected, f"{cmd!r}: {why}")
            self.rows.append(f"{name:32} | refused in held and prep | by the {expected}")

    def test_the_plain_secret_read(self):
        """The proof's own call (test_held_run_bash_writes, test_6), refused, and the key never printed."""
        (self.home / ".ssh/key-backup.txt").write_text("FAKE-PRIVATE-KEY-FOR-THE-TEST\n")
        for mode in ("held", "prep"):
            code, why = self.hook(mode, f"{P} ~/.ssh/key-backup.txt")
            self.assertEqual(code, 2, why)
            self.assertIn("~/.ssh/key-backup.txt: it holds secrets (keys, passwords, sign-ins)", why)

    def test_a_comment_hid_the_read_flag(self):
        """Review N1, as pure functions: without the # rule each of these record commands is classed read, because the split
        keeps the comment's flag; held_form_reason refuses them first."""
        sys.path.insert(0, str(self.root / "system/scripts"))
        import reach
        for script, cmd in (("review.py", "review.py assign ABC-A-001 Sara # --dry-run"), ("propose.py", "propose.py recode ABC X # --dry-run"),
                            ("propose.py", "propose.py learn x.json # --check"), ("minutes.py", "minutes.py baseline # --dry-run")):
            command = "system/scripts/run " + cmd
            self.assertEqual(reach.command_kind(script, reach.bash_args(command))[0], reach.READ, cmd)
            self.assertIn("comment", reach.held_form_reason(command) or "", cmd)

    def test_double_slash_pieces(self):
        """Review N4, as a pure function: `//` then a path is checked; a web address's host after http: or https: isn't."""
        sys.path.insert(0, str(self.root / "system/scripts"))
        import reach
        self.assertIn("//Users/x/.ssh/id_rsa", reach.held_arg_paths(f"{T} a://Users/x/.ssh/id_rsa"))
        self.assertIn("///Users/x/.ssh/id_rsa", reach.held_arg_paths(f"{T} file:///Users/x/.ssh/id_rsa"))
        self.assertIn("//Users/x", reach.held_arg_paths(f"{T} https=//Users/x"))   # not a web address: = isn't a scheme's :
        for url in ("https://example.com/a", "see http://example.com/a", "HTTPS://example.com/a"):
            self.assertNotIn("//example.com/a", reach.held_arg_paths(f"{T} '{url}'"), url)

    def test_an_ordinary_read_still_passes(self):
        for mode in ("held", "prep"):
            for cmd in (f"{T} '{ABC}/transcripts/2026-10-02 Weekly.vtt'", f"{T} '{ABC}/transcripts/2026-10-0? Weekly.vtt'",
                        "system/scripts/run tracker.py read actions", "system/scripts/run search.py query 'see https://x.example/a'"):
                with self.subTest(cmd=cmd, mode=mode):
                    code, why = self.hook(mode, cmd)
                    self.assertEqual(code, 0, why)


if __name__ == "__main__":
    unittest.main(verbosity=2)
