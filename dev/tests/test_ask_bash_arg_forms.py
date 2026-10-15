"""ask-hook-fix (15-10-2026): ask creaite's guard holds the never list for every form of a script argument.

A5 (dev/tests/test_held_bash_arg_forms.py) closed the argument forms for the runs creaite starts itself (modes "held" and "prep").
ask creaite's own modes ("ask", a plain chat; "confirmed", a request Alan confirmed; "sweep", a typed sweep) were decided by
hook_decision, whose Bash check saw only tool_paths: each whole argument that looked like a path and didn't start with "-". So
`minutes.py transcript ~/.ss?/id_rsa` (the shell expands the wildcard after the hook has looked) and `… --file=~/.ssh/id_rsa`
passed. hook_decision now also checks reach.ask_arg_paths, ask creaite's own copy of the held check. This test feeds the real
hook, as Claude Code runs it, every form A5's table covers, in all three modes, says by what each is refused, and lets through
the lookalikes ask creaite legitimately sends (search text with / : , and =, URLs, a ~/Documents path, an option's value in the
vault). The one narrow over-refusal is written down: a separator directly followed by a path outside reach, inside free text.

No model is called. A throwaway vault and a fake home folder with ~/.ssh/id_rsa holding a fake key; HOME is the fake home.

Run: python3 dev/tests/test_ask_bash_arg_forms.py     (quick tier: no Chrome)
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

NEVER, SHELL = "never list", "shell form"
MODES = ("ask", "confirmed", "sweep")
T = "system/scripts/run minutes.py transcript"
P = "python3 system/scripts/minutes.py transcript"


def forms(root, home):
    """(name, command, what refuses it) in every ask mode. A shell-form row may be refused earlier by the never list on its whole
    arguments (hook_decision has always checked those first, for every tool)."""
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
        ("--opt=PATH (python3 form)", f"{P} --file=~/.ssh/id_rsa", NEVER),
        ("--opt PATH", f"{T} --from ~/.ssh/id_rsa", NEVER),
        ("-o=PATH", f"{T} -f=~/.ssh/id_rsa", NEVER),
        ("inside a longer argument (=)", f"{T} file=~/.ssh/id_rsa", NEVER),
        ("inside a longer argument (:)", f"{T} a:~/.ssh/id_rsa", NEVER),
        ("inside a longer argument (,)", f"{T} a.vtt,~/.ssh/id_rsa", NEVER),
        ("a second separator", f"{T} a=b:~/.ssh/id_rsa", NEVER),
        ("// after a separator (not a URL)", f"{T} a=/{home}/.ssh/id_rsa", NEVER),
        ("symlink to the file", f"{T} system/staging/drafts/key.vtt", NEVER),
        ("symlink to the folder", f"{T} system/staging/drafts/keys/id_rsa", NEVER),
        ("wildcard ? (python3 form)", f"{P} ~/.ss?/id_rsa", NEVER),
        ("wildcard ?", f"{T} ~/.ss?/id_rsa", NEVER),
        ("wildcard *", f"{T} ~/.s*/id_r*", NEVER),
        ("wildcard [ ]", f"{T} ~/.ssh/id_[r]sa", NEVER),
        ("wildcard, absolute", f"{T} {home}/.*/id_rsa", NEVER),
        ("wildcard after =", f"{T} --from=~/.ss?/id_rsa", NEVER),
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
    ]


def lookalikes(root):
    """Commands ask creaite legitimately sends that look like the refused forms: each is let through in every ask mode."""
    return [
        f"{T} '{ABC}/transcripts/2026-10-02 Weekly.vtt'",
        f"{T} '{ABC}/transcripts/2026-10-0? Weekly.vtt'",
        f"{T} ~/Documents/notes.vtt",
        "system/scripts/run tracker.py read ABC-A-001",
        "python3 system/scripts/tracker.py read actions",
        "system/scripts/run search.py query 'a/b: c, d'",
        "system/scripts/run search.py query \"time 10:30, owner=Sara/Mia; budget 1/2\"",
        "system/scripts/run search.py query 'see https://x.example/a?b=1&c=d/e'",
        "system/scripts/run search.py query 'https://x.example:8080/a/b, http://y.example/c'",
        "system/scripts/run search.py query 'link=https://x.example/a,ftp://y.example/b'",
        "system/scripts/run search.py query 'from: /tmp/x, to ~/.ssh keys'",       # a space after the separator: text
        "system/scripts/run search.py query '$5,000 budget/forecast: ~3 weeks'",
        "system/scripts/run search.py query 'ABC/*?'",
        f"system/scripts/run filechange.py check '{ABC}/notes.md' --edit",
        f"system/scripts/run filechange.py edit '{ABC}/notes.md' --from=system/staging/drafts/n.md --why 'ratio 1/2, see: notes'",
        "system/scripts/run propose.py new-project --code DEF --name 'Data/AI: Phase 2, pilot' --out new-project.json",
        "system/scripts/run reach.py classify ~/Documents/notes.txt read",
        "system/scripts/run reach.py never",
        f"python3 {root}/system/scripts/tracker.py read ABC",
    ]


# The one narrow over-refusal, kept (fail closed): a separator directly followed by a path outside the vault, the projects folder
# and the home folder, inside free text. The reason names the piece, so ask creaite can rephrase (a space after the separator).
OVER_REFUSED = ["system/scripts/run search.py query 'copy from:/tmp/x'"]


def by(why):
    if "holds secrets" in why or "outside the vault, the projects folder and your home folder" in why:
        return NEVER
    if "ask creaite runs only creaite's own scripts" in why or "shell characters" in why or "$ or a back-quote" in why:
        return SHELL
    return "other: " + why


class HookCase(unittest.TestCase):
    """A throwaway vault and fake home; hook() runs the real guard hook through the wrapper, as Claude Code does."""

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        cls.v.run("init")
        cls.root = cls.v.root
        cls.home = Path(tempfile.mkdtemp(prefix="ask-forms-home-")).resolve()
        (cls.home / ".ssh").mkdir()
        (cls.home / ".ssh/id_rsa").write_text("FAKE-PRIVATE-KEY-FOR-THE-TEST\n")
        (cls.home / "Documents").mkdir()
        (cls.home / "Documents/notes.vtt").write_text("WEBVTT\n")
        drafts = cls.root / "system/staging/drafts"
        drafts.mkdir(parents=True, exist_ok=True)
        os.symlink(cls.home / ".ssh/id_rsa", drafts / "key.vtt")
        os.symlink(cls.home / ".ssh", drafts / "keys")
        (cls.root / ABC / "transcripts").mkdir(parents=True, exist_ok=True)
        (cls.root / ABC / "transcripts/2026-10-02 Weekly.vtt").write_text("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n<v Sara>Hello\n")
        (cls.root / ABC / "notes.md").write_text("# Notes\n")
        cls.env = {**os.environ, "HOME": str(cls.home)}
        cls.rows = []

    @classmethod
    def tearDownClass(cls):
        if cls.rows:
            print("\n" + "\n".join(cls.rows))
        cls.v.cleanup()
        shutil.rmtree(cls.home, ignore_errors=True)

    def hook(self, mode, command):
        r = subprocess.run(["/bin/sh", "system/scripts/run", "reach.py", "hook", "--run", "r-ask-forms", "--mode", mode],
                           cwd=self.root, capture_output=True, text=True, timeout=60, env=self.env,
                           input=json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": command}}))
        return r.returncode, r.stderr.strip()

    def refused_by(self, table, classify=by):
        for name, cmd, expected in table:
            seen = set()
            for mode in MODES:
                with self.subTest(form=name, mode=mode):
                    code, why = self.hook(mode, cmd)
                    self.assertEqual(code, 2, f"{cmd!r}: {why}")
                    self.assertNotIn("FAKE-PRIVATE-KEY", why)
                    self.assertIn(classify(why), {expected, NEVER} if expected == SHELL else {expected}, f"{cmd!r}: {why}")
                    seen.add(classify(why))
            self.rows.append(f"{name:34} | refused in ask, confirmed and sweep | by the {' / '.join(sorted(seen))}")


class AskArgForms(HookCase):
    def test_every_form_is_refused(self):
        self.refused_by(forms(self.root, self.home))

    def test_the_two_reported_forms(self):
        """The two forms reported against ask mode, with the secret named in the reason."""
        for cmd in (f"{P} ~/.ss?/id_rsa", f"{P} --file=~/.ssh/id_rsa"):
            for mode in MODES:
                with self.subTest(cmd=cmd, mode=mode):
                    code, why = self.hook(mode, cmd)
                    self.assertEqual(code, 2, why)
                    self.assertIn("/.ssh", why)
                    self.assertIn("it holds secrets (keys, passwords, sign-ins)", why)

    def test_legitimate_lookalikes_pass(self):
        for cmd in lookalikes(self.root):
            for mode in MODES:
                with self.subTest(cmd=cmd, mode=mode):
                    code, why = self.hook(mode, cmd)
                    self.assertEqual(code, 0, f"{cmd!r} in {mode}: {why}")

    def test_the_narrow_over_refusal_is_known(self):
        for cmd in OVER_REFUSED:
            code, why = self.hook("ask", cmd)
            self.assertEqual((code, by(why)), (2, NEVER), why)
            self.assertIn("/tmp/x", why)


if __name__ == "__main__":
    unittest.main(verbosity=2)
