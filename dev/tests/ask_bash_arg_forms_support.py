"""Shared fixture for test_ask_bash_arg_forms and its split parts (module-level helpers and the base class; no tests here)."""
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
from test_held_bash_arg_forms import TILDE_FORMS  # noqa: E402  the held table's ~ rows: the same forms go through ask mode
NEVER, SHELL, HANDOVER, WORDS = "never list", "shell form", "a hand-over command", "the shell's own words"
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
        ("wildcard ? (python3 form)", f"{P} ~/.ss?/id_rsa", WORDS),
        ("wildcard ?", f"{T} ~/.ss?/id_rsa", WORDS),
        ("wildcard *", f"{T} ~/.s*/id_r*", WORDS),
        ("wildcard [ ]", f"{T} ~/.ssh/id_[r]sa", NEVER),
        ("wildcard, absolute", f"{T} {home}/.*/id_rsa", WORDS),
        ("wildcard after =", f"{T} --from=~/.ss?/id_rsa", WORDS),
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

OVER_REFUSED = ["system/scripts/run search.py query 'copy from:/tmp/x'"]
def by(why):
    if "holds secrets" in why or "outside the vault, the projects folder and your home folder" in why:
        return NEVER
    if "hands over to another command" in why:
        return HANDOVER
    if "wildcard or pattern character" in why:       # #174 F5: an unquoted * ? [ ^ # or mid-word ~ is refused before the never list
        return WORDS
    if "# comment" in why or "turns into another folder" in why or "through every folder" in why:
        return WORDS
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

def handovers(root):
    return [
        ("reach.py wrap tracker.py apply", "system/scripts/run reach.py wrap tracker.py apply", HANDOVER),
        ("reach.py wrap (python3 form)", "python3 system/scripts/reach.py wrap tracker.py apply", HANDOVER),
        ("reach.py wrap (full vault path)", f"python3 {root}/system/scripts/reach.py wrap tracker.py apply", HANDOVER),
        ("reach.py wrap permissions.py", "system/scripts/run reach.py wrap permissions.py edit x", HANDOVER),
        ("reach.py wrap, a stage command", "system/scripts/run reach.py wrap minutes.py stage x.json", HANDOVER),  # #174: report.py adhoc is refused earlier, as a report draft
        ("reach.py wrap, an option first", "system/scripts/run reach.py --x wrap doctor.py", HANDOVER),
        ("reach.py wrap with a secret", "system/scripts/run reach.py wrap minutes.py transcript ~/.ssh/id_rsa", NEVER),
        ("reach.py hook", "system/scripts/run reach.py hook --run r --mode confirmed", HANDOVER),
    ]

SR = "system/scripts/run"
SHELL_WORDS = [
    ("# then a read flag (record command)", f"{SR} review.py assign ABC-A-001 'Sara Khan' # --dry-run", WORDS),
    ("# then a read flag (recode)", f"{SR} propose.py recode ABC XYZ # --dry-run", WORDS),
    ("# then --check (learn)", f"{SR} propose.py learn ABC sender a@b.example # --check", WORDS),
    ("# then --dry-run (baseline)", f"{SR} minutes.py baseline # --dry-run", WORDS),
    ("# after a quoted word", f"{SR} tracker.py read 'ABC' #x", WORDS),
    ("~- ($OLDPWD)", f"{SR} minutes.py transcript ~-/x.vtt", WORDS),
    ("~+ ($PWD)", f"{SR} minutes.py transcript ~+/x.vtt", WORDS),
    ("~1 (the directory stack)", f"{SR} minutes.py transcript ~1/x.vtt", WORDS),
    ("~- after =", f"{SR} minutes.py transcript --from=~-/x.vtt", WORDS),
    ("~+ after :", f"{SR} minutes.py transcript a:~+/x.vtt", WORDS),
    ("** (recursive in zsh)", f"{SR} minutes.py transcript projects/**/x.vtt", WORDS),
    ("# inside a word (zsh x#, #174 F5)", f"{SR} tracker.py read ABC#1", WORDS),
]
SHELL_WORDS_ALLOWED = [
    f"{SR} search.py query '#12 owner: Sara, ~-5 days, **bold**'",
    f'{SR} search.py query "issue #4 ~+ ~1"',
    f"{SR} tracker.py read 'ABC#1'",
    f"{SR} search.py query 'a ~ b'",
    f"{SR} minutes.py transcript '{ABC}/transcripts/2026-10-0*.vtt'",
]
ASK_TILDE = [(n, c, WORDS) for n, c, _ in TILDE_FORMS if "quoted" not in n]
HIDDEN = [
    ("* matching a hidden folder", f"{T} ~/*/id_rsa", WORDS),
    ("? matching a hidden folder", f"{T} ~/?ssh/id_rsa", WORDS),
    ("[ ] matching a hidden folder", f"{T} ~/[.]ssh/id_rsa", WORDS),
    ("* after =", f"{T} --from=~/*/id_rsa", WORDS),
]
def shared_forms(root, home):
    return [(n, c) for n, c, _ in ASK_TILDE] + [(n, c) for n, c, _ in HIDDEN] + [
        ("plain ~", f"{P} ~/.ssh/id_rsa"), ("absolute", f"{T} {home}/.ssh/id_rsa"),
        ("relative ../..", f"{T} {os.path.relpath(home / '.ssh/id_rsa', root)}"),
        ("--opt=PATH", f"{T} --from=~/.ssh/id_rsa"), ("after :", f"{T} a:~/.ssh/id_rsa"), ("after ,", f"{T} a.vtt,~/.ssh/id_rsa"),
        ("single-quoted $HOME", f"{T} '$HOME/.ssh/id_rsa'"), ("bare $HOME", f"{T} $HOME/.ssh/id_rsa"),
        ("symlink to the file", f"{T} system/staging/drafts/key.vtt"), ("wildcard ?", f"{T} ~/.ss?/id_rsa"),
        ("wildcard, absolute", f"{T} {home}/.*/id_rsa"), ("// path after =", f"{T} a=/{home}/.ssh/id_rsa"),
        ("** unquoted", f"{T} ~/**/id_rsa"), ("~-", f"{T} ~-/.ssh/id_rsa"), ("~+ after :", f"{T} a:~+/x"),
        ("# comment", f"{SR} review.py assign ABC-A-001 Sara # --dry-run"),
        ("reach.py wrap", f"{SR} reach.py wrap tracker.py apply"), ("reach.py hook", f"{SR} reach.py hook --run r --mode confirmed"),
        ("validate a permission file", f"{SR} tracker.py validate .claude/settings.json"),
        ("validate ~ (shell's)", f"{SR} tracker.py validate ~/.claude/settings.json"),
        ("validate a wildcard", f"{SR} tracker.py validate 'proposed-*.json'"),
        ("validate a missing file", f"{SR} tracker.py validate nothing-here.json"),
        ("; chain", f"{T} x.vtt; cat ~/.ssh/id_rsa"), ("$(…)", f"{T} $(echo ~/.ssh/id_rsa)"),
    ]

