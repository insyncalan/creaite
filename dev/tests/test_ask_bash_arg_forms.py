"""ask-hook-fix (15-10-2026): ask creaite's guard holds the never list for every form of a script argument, and never runs
reach.py wrap or hook.

A5 (dev/tests/test_held_bash_arg_forms.py) closed the argument forms for the runs creaite starts itself (modes "held" and "prep").
ask creaite's own modes ("ask", a plain chat; "confirmed", a request Alan confirmed; "sweep", a typed sweep) were decided by
hook_decision, whose Bash check saw only tool_paths: each whole argument that looked like a path and didn't start with "-". So
`minutes.py transcript ~/.ss?/id_rsa` (the shell expands the wildcard after the hook has looked) and `… --file=~/.ssh/id_rsa`
passed. hook_decision now also checks reach.ask_arg_paths, ask creaite's own copy of the held check. This test feeds the real
hook, as Claude Code runs it, every form A5's table covers, in all three modes, says by what each is refused, and lets through
the lookalikes ask creaite legitimately sends (search text with / : , and =, URLs, a ~/Documents path, an option's value in the
vault). The one narrow over-refusal is written down: a separator directly followed by a path outside reach, inside free text.

The read commands that write a file: propose.py new-project, close-project, archive, restore and old-archives (--out) write
only a bare file name directly in system/staging/drafts/; tracker.py validate, which writes its findings back into the file it is
given, runs only on a proposal in system/staging/ in every ask mode.

What the shell does to a word that the guard's own reading doesn't, refused unquoted in every ask mode (reach.ask_shell_refusal):
a `#` comment (the guard read the words after it, so `review.py assign … # --dry-run` was classed read and ran for real),
`~+` `~-` `~N` ($PWD, $OLDPWD, the directory stack) and `**` (recursive in zsh). Quoted, each is text and runs. Only benign
commands are sent here: no secret path is needed to show the gap.

`reach.py wrap` and `reach.py hook` are refused in every ask mode: wrap ran the command it wrapped after the record gate had
judged the wrapper (`reach.py wrap tracker.py apply` passed a plain chat). `reach.py classify` and `never` still run.

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
    if "hands over to another command" in why:
        return HANDOVER
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



def handovers(root):
    return [
        ("reach.py wrap tracker.py apply", "system/scripts/run reach.py wrap tracker.py apply", HANDOVER),
        ("reach.py wrap (python3 form)", "python3 system/scripts/reach.py wrap tracker.py apply", HANDOVER),
        ("reach.py wrap (full vault path)", f"python3 {root}/system/scripts/reach.py wrap tracker.py apply", HANDOVER),
        ("reach.py wrap permissions.py", "system/scripts/run reach.py wrap permissions.py edit x", HANDOVER),
        ("reach.py wrap, a stage command", "system/scripts/run reach.py wrap report.py adhoc x.json", HANDOVER),
        ("reach.py wrap, an option first", "system/scripts/run reach.py --x wrap doctor.py", HANDOVER),
        ("reach.py wrap with a secret", "system/scripts/run reach.py wrap minutes.py transcript ~/.ssh/id_rsa", NEVER),
        ("reach.py hook", "system/scripts/run reach.py hook --run r --mode confirmed", HANDOVER),
    ]


class Handover(HookCase):
    def test_wrap_and_hook_are_refused(self):
        self.refused_by(handovers(self.root))

    def test_the_wrapped_command_is_judged_on_its_own(self):
        """What wrap would have run: refused in a plain chat (BL-267), run in a confirmed one; unchanged."""
        code, why = self.hook("ask", "system/scripts/run tracker.py apply")
        self.assertEqual(code, 2)
        self.assertIn("changes the record", why)
        self.assertEqual(self.hook("confirmed", "system/scripts/run tracker.py apply")[0], 0)


class ValidateOnlyInStaging(unittest.TestCase):
    """The one READ command that writes into a file it is given: tracker.py validate rewrites its proposal with its findings. It
    runs only on a proposal in system/staging/, in every ask mode; elsewhere it is refused."""

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        cls.v.run("init")
        cls.root = cls.v.root
        cls.prop = cls.v.propose("x", [])
        (cls.root / "system/staging/drafts").mkdir(parents=True, exist_ok=True)
        cls.home = Path(tempfile.mkdtemp(prefix="ask-validate-home-")).resolve()
        cls.outside = cls.home / "Documents"                 # in reach (the home folder), so only the validate rule refuses it
        cls.outside.mkdir()
        cls.env = {**os.environ, "HOME": str(cls.home)}
        (cls.outside / "spec.json").write_text('{"items": [], "note": "kept as it is"}')
        os.symlink(cls.outside / "spec.json", cls.root / "system/staging/proposed-link.json")
        os.symlink(cls.root / ".claude/settings.json", cls.root / "system/staging/link.json")

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()
        shutil.rmtree(cls.home, ignore_errors=True)

    def hook(self, mode, command):
        r = subprocess.run(["/bin/sh", "system/scripts/run", "reach.py", "hook", "--run", "r-validate", "--mode", mode],
                           cwd=self.root, capture_output=True, text=True, timeout=60, env=self.env,
                           input=json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": command}}))
        return r.returncode, r.stderr.strip()

    def test_validate_rewrites_the_file_it_is_given(self):
        """Why the guard restricts it: run directly, validate rewrites a JSON file outside staging."""
        f = self.outside / "plain.json"
        f.write_text('{"items": []}')
        self.v.run("validate", str(f), ok=False, cwd=self.root)
        self.assertNotEqual(f.read_text(), '{"items": []}')

    def test_outside_staging_is_refused(self):
        """A5's rule (reach.held_validate_reason), in ask creaite's own function: the first file found in
        tracker.resolve_proposal's order must be in system/staging/; nothing found, or more than one file, is refused."""
        targets = (
            (".claude/settings.json", "a permission file"),
            ("system/config/settings.json", "settings.json"),
            (str(self.root / ".claude/settings.json"), "absolute"),
            ("~/.claude/settings.json", "~ the shell expands (not found by the hook)"),
            (str(self.outside / "spec.json"), "absolute, in the home folder"),
            ("system/staging/proposed-link.json", "a symlink in staging, by path"),
            ("proposed-link.json", "a symlink in staging, by name"),
            ("system/staging/link.json", "a symlink to a permission file, by path"),
            ("link.json", "a symlink to a permission file, by name"),
            ("proposed-missing.json", "a missing file"),
            (f"{self.prop.name} .claude/settings.json", "two files"),
        )
        for target, name in targets:
            for mode in MODES:
                with self.subTest(target=name, mode=mode):
                    code, why = self.hook(mode, f"system/scripts/run tracker.py validate {target}")
                    self.assertEqual(code, 2, why)
                    self.assertIn("runs only on a proposal in system/staging/", why)

    def test_a_proposal_in_staging_runs(self):
        for target in (str(self.prop.relative_to(self.root)), self.prop.name):
            for mode in MODES:
                with self.subTest(target=target, mode=mode):
                    self.assertEqual(self.hook(mode, f"system/scripts/run tracker.py validate {target}"), (0, ""))


class ReadCommandsWriteOnlyDrafts(unittest.TestCase):
    """The READ commands whose --out saves a spec (propose.emit_spec): a bare name lands directly in system/staging/drafts/, and a
    path, a hidden name or a folder is refused with nothing written."""

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        cls.v.run("init")
        cls.root = cls.v.root
        cls.drafts = cls.root / "system/staging/drafts"
        cls.outside = Path(tempfile.mkdtemp(prefix="ask-out-")).resolve()

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()
        shutil.rmtree(cls.outside, ignore_errors=True)

    def files(self):
        every = {p for p in self.root.rglob("*") if p.is_file() and "__pycache__" not in p.parts and "logs" not in p.parts}
        return every | {p for p in self.outside.rglob("*")}

    def propose(self, *args):
        return self.v.run(*args, script="propose.py", ok=False, cwd=self.root)

    COMMANDS = (("new-project", "--code", "DEF", "--name", "Digital Enablement", "--out"), ("close-project", "ABC", "--out"),
                ("archive", "ABC", "--cancel-open", "--out"), ("restore", "ABC", "--out"))

    def test_a_bare_name_lands_in_drafts(self):
        r = self.propose("new-project", "--code", "DEF", "--name", "Digital Enablement", "--out", "np.json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.drafts / "np.json").is_file())
        self.assertIn("Spec saved: system/staging/drafts/np.json", r.stdout)

    def test_a_path_is_refused_and_nothing_is_written(self):
        for base in self.COMMANDS:
            for out in (str(self.outside / "x.json"), "../x.json", "../../x.json", "~/x.json", "sub/x.json", ".x.json", "..",
                        "system/staging/proposed-x.json", f"{self.outside}/../x.json"):
                with self.subTest(cmd=base[0], out=out):
                    before = self.files()
                    r = self.propose(*base, out)
                    self.assertNotEqual(r.returncode, 0, f"{base} {out}: {r.stdout}")
                    self.assertEqual(self.files() - before, set(), f"{base} {out} wrote a file")

    def test_every_saving_read_command_goes_through_emit_spec(self):
        """Every READ command of propose.py that takes --out saves through emit_spec (its one confined writer)."""
        src = (self.root / "system/scripts/propose.py").read_text(encoding="utf-8")
        writer = src[src.index("def emit_spec"):src.index("def cmd_new_project")]
        self.assertIn("name != out or name.startswith(\".\")", writer)
        self.assertIn("paths.DRAFTS / f\"{stem}.json\"", writer)
        for fn in ("def cmd_new_project", "def cmd_close_project", "def archive_cli", "def cmd_old_archives"):
            body = src[src.index(fn):]
            body = body[:body.index("\ndef ", 1)]
            self.assertIn("emit_spec(", body, fn)
            self.assertNotIn("write_text(", body, fn)
        arch = (self.root / "system/scripts/archive.py").read_text(encoding="utf-8")       # archive.py reports --out
        at = arch.index('argv.index("--out") + 1]')
        self.assertIn("return propose.emit_spec(spec, out)", arch[at:at + 300], "archive.py reports --out saves through emit_spec")



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
]
SHELL_WORDS_ALLOWED = [
    f"{SR} search.py query '#12 owner: Sara, ~-5 days, **bold**'",
    f'{SR} search.py query "issue #4 ~+ ~1"',
    f"{SR} tracker.py read ABC#1",
    f"{SR} search.py query 'a ~ b'",
    f"{SR} minutes.py transcript '{ABC}/transcripts/2026-10-0*.vtt'",
]


class ShellWords(HookCase):
    def test_unquoted_shell_words_are_refused(self):
        self.refused_by(SHELL_WORDS)

    def test_quoted_they_are_text(self):
        for cmd in SHELL_WORDS_ALLOWED:
            for mode in MODES:
                with self.subTest(cmd=cmd, mode=mode):
                    self.assertEqual(self.hook(mode, cmd), (0, ""))

    def test_the_comment_gap_in_the_pure_functions(self):
        """Why the comment is refused: the guard's words go on after the #, so a (kind, flag) entry reads as read."""
        sys.path.insert(0, str(self.root / "system/scripts"))
        import reach
        cmd = SHELL_WORDS[0][1]
        self.assertEqual(reach.command_kind("review.py", reach.bash_args(cmd)), ("read", "review.py assign"))
        self.assertIsNone(reach.record_problem(cmd))                       # the record gate alone let it through
        self.assertIn("# comment", reach.ask_shell_refusal(cmd))
        self.assertIsNone(reach.ask_shell_refusal(f"{SR} review.py assign ABC-A-001 'Sara Khan' --dry-run"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
