"""#116 H1 (16-10-2026): the guard's shell-character check refuses a backslash inside double quotes.

Run: python3 dev/tests/test_guard_backslash.py     (quick tier: no Chrome)

`_shell_refused` read `\\"` inside double quotes as an escaped quote. Inside double quotes the shell reads `\\\\` as one backslash,
so in `"a\\\\"` the last quote closes the word: the check thought the quote was still open and missed a following `;`, `&&`, `|` or
`$(…)`, and the shell would have run a second command. A backslash inside double quotes is now refused (fail closed): a quote
then closes at the next double quote and nothing else, as the shell reads it. Inside single quotes a backslash is literal to the
shell and stays allowed; outside quotes it was already refused. Covers:
- Team Cap's reproduction and a table of forms, through `_shell_refused`, `bash_refusal` in every mode and the guard's decision
  (`reach.decide`, as the hook calls it) in a throwaway vault, plus the hook itself (`reach.py hook`, exit 2) for the reproduction;
- the legitimate forms that still pass: double quotes without a backslash, single quotes with backslashes, plain reads, searches;
- no skill or rules file shows a creaite command with a backslash inside double quotes (ask creaite copies what the docs show).
Nothing here runs a command in a shell: every check is the guard's decision only.
"""
import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_tracker import Vault  # noqa: E402

REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "system/scripts"))
import reach  # noqa: E402

MODES = ("ask", "confirmed", "sweep", "prep", "held")
P = "python3 system/scripts/"
W = "system/scripts/run "
BS = "\\"                                                   # one backslash
REPRO = P + 'doctor.py "a' + BS * 2 + '" ; rm -rf ~/Documents ' + BS * 2 + '""'     # Team Cap's reproduction, as typed
REPRO_TILDE = P + 'minutes.py transcript "a' + BS * 2 + '" ~HOME/.ssh/id_rsa ' + BS * 2 + '""'

REFUSED = {
    "Cap's reproduction": REPRO,
    "Cap's tilde reproduction": REPRO_TILDE,
    "escaped backslash then ;": P + 'doctor.py "a' + BS * 2 + '" ; rm x',
    "escaped backslash then ; (no space)": P + 'doctor.py "a' + BS * 2 + '"; rm x',
    "escaped quote, unclosed": P + 'doctor.py "a' + BS + '"',
    "only an escaped backslash": P + 'doctor.py "' + BS * 2 + '"',
    "after a word, then &&": P + 'doctor.py x "a' + BS * 2 + '" && rm x',
    "then $(…)": P + 'doctor.py "a' + BS * 2 + '" $(id)',
    "then a pipe": P + 'doctor.py "a' + BS * 2 + '" | sh',
    "then a back-quote": P + 'doctor.py "a' + BS * 2 + '" `id`',
    "then a redirect": P + 'doctor.py "a' + BS * 2 + '" > /tmp/x',
    "then a new line": P + 'doctor.py "a' + BS * 2 + '"\nrm x',
    "then a carriage return": P + 'doctor.py "a' + BS * 2 + '"\rrm x',
    "backslash-new line inside": P + 'doctor.py "a' + BS + '\nrm x"',
    "backslash-n inside": P + 'search.py query "a' + BS + 'nb"',
    "backslash-dollar inside": P + 'search.py query "a' + BS + '$HOME"',
    "single quote inside, escaped backslash": P + 'doctor.py "a\'' + BS * 2 + '" ; rm x',
    "backslash last inside": P + 'doctor.py "a' + BS + '"',
    "backslash at the very end, unclosed": P + 'doctor.py "a' + BS,
    "through the wrapper": W + 'doctor.py "a' + BS * 2 + '" ; rm x',
    "a record command hidden": P + 'tracker.py read "x' + BS * 2 + '" ; ' + P + "tracker.py apply",
}
# The same forms with a balancing tail (`\\""`), which the old check read as still inside the quote and so let through
TAIL = " " + BS * 2 + '""'
for _name, _rest in (("&&", " && rm x"), ("$(…)", " $(id)"), ("a pipe", " | sh"), ("a back-quote", " `id`"),
                     ("a redirect", " > /tmp/x"), ("a new line", "\nrm x"), ("a background &", " & rm x"),
                     ("a record command", " ; " + P + "tracker.py apply"), ("a never path", " ; cat ~/.ssh/id_rsa")):
    REFUSED[f"balanced, then {_name}"] = P + 'doctor.py "a' + BS * 2 + '"' + _rest + TAIL
    REFUSED[f"balanced through the wrapper, then {_name}"] = W + 'doctor.py "a' + BS * 2 + '"' + _rest + TAIL

ALLOWED = {
    "double quotes, no backslash": P + 'search.py query "data access risks"',
    "double quotes with a slash, colon and commas": P + 'search.py query "a/b: c, d"',
    "single quotes with backslashes": P + "search.py query 'a" + BS + "nb " + BS * 2 + " c'",
    "single quotes, backslash last": P + "search.py query 'a" + BS + "'",
    "single quote inside double quotes": P + 'search.py query "Alan\'s plan"',
    "double quote inside single quotes": P + "search.py query 'say \"hi\"'",
    "a plain read": P + "tracker.py read ABC-A-001",
    "a plain read through the wrapper": W + "tracker.py read ABC-A-001",
    "a summary in single quotes": W + "search.py enrich set --path 'projects/ABC Example/minutes/x.docx' --summary 'Line one"
                                  + BS + "nLine two' --tags \"uat, data\"",
    "unicode backslash look-alikes": P + 'search.py query "a＼b ∖ c ⧵ d"',
}

# A run creaite starts itself may come to run read commands only (#116 A5): the summary write is checked in ask creaite's modes
NOT_HELD = {"a summary in single quotes"}

# Shell semantics, for the record: the shell's reading of the reproduction. It ends the quoted word after `a\\`, so the `;` is a
# command separator; the old check didn't see it. Checked with shlex (POSIX mode reads double quotes as the shell does).
import shlex  # noqa: E402


class PureFunctions(unittest.TestCase):
    def test_the_shell_ends_the_quote_where_the_guard_now_does(self):
        words = shlex.split(REPRO, posix=True)
        self.assertEqual(words[2], "a" + BS)                  # one word, a and one backslash: the quote closed
        self.assertIn(";", words)                             # the separator is outside any quote

    def test_refused_forms(self):
        for name, cmd in REFUSED.items():
            with self.subTest(name):
                self.assertIsNotNone(reach._shell_refused(cmd), cmd)
                for mode in MODES:
                    self.assertIsNotNone(reach.bash_refusal(cmd, mode), (mode, cmd))

    def test_the_reproduction_is_refused_for_the_backslash(self):
        why = reach.bash_refusal(REPRO, "ask")
        self.assertIn("backslash inside double quotes", why)
        self.assertIn("single quotes", why)                   # it says what to do instead

    def test_legitimate_forms_still_pass(self):
        for name, cmd in ALLOWED.items():
            with self.subTest(name):
                self.assertIsNone(reach._shell_refused(cmd), cmd)
                self.assertIsNone(reach.bash_problem(cmd), cmd)
                for mode in ("ask", "confirmed", "sweep"):
                    self.assertIsNone(reach.bash_refusal(cmd, mode), (mode, cmd))

    def test_unchanged_rules(self):
        self.assertIsNotNone(reach._shell_refused(P + "doctor.py a" + BS + " b"))          # unquoted backslash: refused, as before
        self.assertIn("$", reach._shell_refused(P + 'tracker.py read "ABC $HOME"'))        # $ in double quotes: as before
        self.assertIsNone(reach._shell_refused(P + "tracker.py read 'ABC $HOME'"))         # $ in single quotes: as before
        self.assertEqual(reach._shell_refused(P + "tracker.py read 'unclosed"), "the command has an unclosed quote")
        self.assertIsNotNone(reach._shell_refused(P + 'doctor.py "a" ; rm x'))             # the plain chain: as before


class Decisions(unittest.TestCase):
    """The guard's decision as the hook makes it (reach.decide), in a throwaway vault, in every mode."""

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        cls.v.run("init")

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def decide(self, commands):
        code = ("import json, sys; sys.path.insert(0, 'system/scripts'); import reach; cs = json.loads(sys.stdin.read()); "
                "print(json.dumps({m: {c: reach.decide('Bash', {'command': c}, m, 'r-1') for c in cs} for m in sys.argv[1:]}))")
        r = subprocess.run([sys.executable, "-c", code, *MODES], input=json.dumps(commands), cwd=self.v.root,
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_refused_in_every_mode(self):
        got = self.decide(list(REFUSED.values()))
        for mode in MODES:
            for name, cmd in REFUSED.items():
                with self.subTest(mode=mode, form=name):
                    self.assertFalse(got[mode][cmd][0], (mode, cmd))

    def test_legitimate_forms_allowed_in_every_mode(self):
        got = self.decide(list(ALLOWED.values()))
        for mode in MODES:
            for name, cmd in ALLOWED.items():
                if mode in ("prep", "held") and name in NOT_HELD:
                    continue
                with self.subTest(mode=mode, form=name):
                    self.assertEqual(got[mode][cmd], [True, ""], (mode, cmd))

    def test_the_hook_itself_refuses_the_reproduction(self):
        for mode in ("ask", "confirmed", "sweep", "held"):
            with self.subTest(mode):
                r = subprocess.run(["/bin/sh", "system/scripts/run", "reach.py", "hook", "--run", "r-test", "--mode", mode],
                                   cwd=self.v.root, input=json.dumps({"tool_name": "Bash", "tool_input": {"command": REPRO}}),
                                   capture_output=True, text=True, timeout=60, env={**os.environ})
                self.assertEqual(r.returncode, 2, r.stderr)
                self.assertIn("backslash inside double quotes", r.stderr)


class Docs(unittest.TestCase):
    DOCS = sorted((REPO / ".claude/skills").glob("*/SKILL.md")) + sorted((REPO / ".claude/skills").glob("*/references/*.md")) + [
        REPO / "system/creaite-rules.md"] + sorted((REPO / "system/templates/drafts").glob("*.md"))
    SPAN = re.compile(r"`((?:python3? system/scripts/|system/scripts/run )[^`]+)`")

    def test_no_doc_shows_a_backslash_inside_double_quotes(self):
        bad = []
        for f in self.DOCS:
            for m in self.SPAN.finditer(f.read_text(encoding="utf-8")):
                if "backslash inside double quotes" in (reach._shell_refused(m.group(1)) or ""):
                    bad.append(f"{f.relative_to(REPO)}: {m.group(1)[:90]}")
        self.assertEqual(bad, [], "a doc shows a command the guard refuses (a backslash inside double quotes)")


if __name__ == "__main__":
    unittest.main()
