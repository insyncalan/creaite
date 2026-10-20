"""ask-hook-fix (15-10-2026): ask creaite's guard holds the never list for every form of a script argument, and never runs, part 3 of 3 (the fixture is in ask_bash_arg_forms_support.py).

Run: python3 dev/tests/test_ask_bash_arg_forms_more.py
"""
import json
import os
import shutil
import subprocess
import tempfile
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ask_bash_arg_forms_support import (  # noqa: E402
    ASK_TILDE,
    HookCase,
    MODES,
    NEVER,
    SHELL_WORDS,
    SHELL_WORDS_ALLOWED,
    SR,
    T,
    Vault,
    WORDS,
    by,
)


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
        (cls.outside / cls.prop.name).write_text('{"items": []}')      # what the shell's ~/Documents/<name> would hand over
        (cls.home / cls.prop.name).write_text('{"items": []}')
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
            # #116 A6 F1: the shell expands these after the hook has looked, so a namesake in staging must not pass
            (f"~/Documents/{self.prop.name}", "~ with a namesake in staging (the shell's file is outside)"),
            (f"~/{self.prop.name}", "~/ with a namesake in staging"),
            ("proposed-*.json", "an unquoted wildcard"),
            ("'proposed-*.json'", "a quoted wildcard"),
            ("validate", "a file named validate (the command word dropped once only)"),
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
        for fn in ("def cmd_new_project", "def cmd_close_project", "def archive_cli"):
            body = src[src.index(fn):]
            body = body[:body.index("\ndef ", 1)]
            self.assertIn("emit_spec(", body, fn)
            self.assertNotIn("write_text(", body, fn)
        arch = (self.root / "system/scripts/archive.py").read_text(encoding="utf-8")       # archive.py reports --out
        at = arch.index('argv.index("--out") + 1]')
        self.assertIn("return propose.emit_spec(spec, out)", arch[at:at + 300], "archive.py reports --out saves through emit_spec")


class Tilde(HookCase):
    def test_every_tilde_form_is_refused(self):
        self.refused_by(ASK_TILDE, classify=lambda why: WORDS if by(why) in (WORDS, NEVER) else by(why))

    def test_plain_tilde_still_passes(self):
        for cmd in (f"{T} ~/Documents/notes.vtt", f"{SR} search.py query 'a ~ b'", f"{SR} search.py query '~HOME ~root'"):
            for mode in MODES:
                with self.subTest(cmd=cmd, mode=mode):
                    self.assertEqual(self.hook(mode, cmd), (0, ""))


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
    unittest.main()
