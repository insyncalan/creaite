"""#174 F5 (guard hardening): `_settings_refused` is defeated by quoting. PROPOSAL tests: they run against a patched scratch copy.

Run: python3 dev/tests/test_guard_174.py                      (quick tier: no Chrome)
Older diff:  GUARD_174_DIFF=<file> python3 dev/tests/test_guard_174.py   (the first version of the diff, 5b20e38c, fails the glob and
            space tests: they were added after the independent review found those holes)
Fail-first: GUARD_174_UNPATCHED=1 python3 dev/tests/test_guard_174.py   (the scratch copy is left without the proposal's patch:
            the F5 tests go red, the "normal commands" tests stay green)

`system/scripts/reach.py` is a guarded file: the fix is the proposal dev/proposals/guard-174/reach.diff, for Alan to approve and
apply. This file proves it without touching reach.py: a throwaway vault gets a copy of the whole of `system/scripts/` and the diff is
applied there with `patch -p0`; the guard's decisions are read from that copy in a subprocess (`reach.bash_problem`, and
`reach.decide`, as the hook calls it, in every mode: ask, confirmed, sweep, prep, held). After Alan applies the diff to the repo,
the copy is already patched (the marker `def _unquoted_words` is found) and the same tests keep guarding it; the unpatched
copy used by the "defect" tests is then made with `patch -R`.

What it proves:
- every quoted, concatenated, escaped, `$'..'`, `$(..)`, back-quote, env-prefixed, `./`, absolute-path, `python`, `python3 …/propose.py`
  and `system/scripts/run propose.py` form of `propose.py setting …` and of `propose.py workstreams retire-settings` is refused in
  every mode; the quoted ones with the settings reason, from the check every mode shares (`bash_problem`);
- the glob bypass (review of 5b20e38c): `propose.py setti?g`, `[s]etting`, `s*ting`, `workstreams retire-*` … would be expanded by the
  shell to a file named `setting` (made first with `filechange.py create`, an ordinary change) in the vault, where the run starts, and
  the guard, which doesn't expand a pattern, never saw the word: refused now in every mode (a pre-existing hole, not from the patch);
  and the forms `propose.py\xa0setting` / `setting\xa0k` the old `str.split` cut apart but `shlex` doesn't stay refused;
- the defect is real: in a confirmed run the unpatched file lets the quoted forms through (F5);
- the normal creaite script runs the skills and the server make are decided exactly as before, in every mode, and the commands a
  confirmed run needs still pass; every command span in the skills, rules and draft prompts has the same decision with and without
  the patch;
- mutations (revert one hunk of the patch, or break one line of it) turn a test red.
Nothing here runs a command in a shell: every check is the guard's decision only.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_tracker import Vault  # noqa: E402

REPO = HERE.parents[1]
DIFF = Path(os.environ.get("GUARD_174_DIFF") or REPO / "dev" / "proposals" / "guard-174" / "reach.diff")   # GUARD_174_DIFF: try an older diff
UNPATCHED = os.environ.get("GUARD_174_UNPATCHED") == "1"
MUTATE = os.environ.get("GUARD_174_MUTATE", "")
MARKER = "def _unquoted_words"
MODES = ("ask", "confirmed", "sweep", "prep", "held")
SETTINGS_WHY = "settings are changed on the approval card"

# One text change per mutation, made on the patched copy: (what it reverts, old text, new text)
MUTATIONS = {
    "no-unquoted": ("hunk 1: the unquoted words are not read (only str.split is)", "_settings_refused(m.group(1), _unquoted_words(cmd))",
                    "None"),
    "no-split": ("hunk 1: the old str.split reading is dropped", "\n            or _settings_refused(m.group(1), cmd.split()))", ")"),
    "no-glob-first": ("hunk 2: a wildcard in the first argument is let through", "(args and _has_glob(args[0]))", "False"),
    "no-glob-workstreams": ("hunk 2: a wildcard after workstreams is let through", "any(_has_glob(a) for a in args[1:])", "False"),
    "no-shlex": ("hunk 2: the words are split without reading the quotes", "return shlex.split(cmd)", "return cmd.split()"),
    "no-setting": ("hunk 2: `setting` is no longer refused", 'args[:1] == ["setting"]', "False"),
    "no-retire": ("hunk 2: `retire-settings` is no longer refused", '"retire-settings" in args', "False"),
    "fail-open": ("hunk 2: a command that can't be split is let through", "words is None or ", ""),
}

HARNESS = r'''
import json, sys
sys.path.insert(0, "system/scripts")
import reach
cmds, modes = json.loads(sys.stdin.read())
out = {"problem": {c: reach.bash_problem(c) for c in cmds},
       "decide": {m: {c: list(reach.decide("Bash", {"command": c}, m, "r-1")) for c in cmds} for m in modes}}
out["direct"] = {"none_words": reach._settings_refused("propose.py", None) if hasattr(reach, "_unquoted_words") else None,
                 "unclosed": reach._unquoted_words('x "y') if hasattr(reach, "_unquoted_words") else "n/a"}
print(json.dumps(out))
'''


def _patch(root, *flags):
    r = subprocess.run(["patch", "-p0", "-s", *flags, "-i", str(DIFF)], cwd=root, capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError(f"patch {' '.join(flags)} failed in the scratch copy:\n{r.stdout}\n{r.stderr}")


def scratch(patched, mutation=""):
    """A throwaway vault holding a copy of the whole of system/scripts/, with reach.py patched (or not) by the proposal's diff.
    If the repo's reach.py already has the fix, `patched` leaves it and `not patched` reverses the diff."""
    v = Vault()
    v.run("init")
    shutil.copytree(REPO / "system" / "scripts", v.root / "system" / "scripts", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__"))
    reach = v.root / "system" / "scripts" / "reach.py"
    already = MARKER in reach.read_text(encoding="utf-8")
    if patched and not already:
        _patch(v.root)
    if not patched and already:
        _patch(v.root, "-R")
    if mutation:
        _what, old, new = MUTATIONS[mutation]
        text = reach.read_text(encoding="utf-8")
        assert text.count(old) == 1, f"mutation {mutation}: {old!r} found {text.count(old)} times"
        reach.write_text(text.replace(old, new), encoding="utf-8")
    return v


def decisions(v, commands):
    """{'problem': {cmd: reason or None}, 'decide': {mode: {cmd: [allowed, reason]}}, 'direct': …} read from the scratch copy."""
    r = subprocess.run([sys.executable, "-c", HARNESS], input=json.dumps([commands, list(MODES)]), cwd=v.root,
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


# ---- the commands -------------------------------------------------------------------------------------------------------------
# Each launcher is the shape the guard accepts for a creaite script: `python3 system/scripts/x.py`, `python …` (the regex allows
# it), `system/scripts/run x.py`, and this vault's own full path in either shape (vault_relative reads it as the relative form).
LAUNCHERS = {
    "python3": "python3 system/scripts/propose.py",
    "python": "python system/scripts/propose.py",
    "run": "system/scripts/run propose.py",
    "abs-python3": "python3 {ROOT}/system/scripts/propose.py",
    "abs-run": "{ROOT}/system/scripts/run propose.py",
}
# the word `setting` as the shell hands it over, written six ways it can be spelled with quotes
SETTING_WORDS = {
    "plain": "setting", "single quotes": "'setting'", "double quotes": '"setting"', "empty double quotes inside": 'se""tting',
    "empty single quotes inside": "se''tting", "quoted pieces": "s'et'ting", "quote then rest": '"se"tting',
    "mixed quotes": "'se'\"tt\"ing", "empty quotes first": '""setting', "empty quotes last": 'setting""', "two quoted halves": '"set""ting"',
    "single then rest": "'sett'ing",
}
RETIRE_ARGS = {
    "plain": "workstreams retire-settings", "double quotes": 'workstreams "retire-settings"',
    "single quotes": "workstreams 'retire-settings'", "quoted half": 'workstreams retire-"settings"',
    "empty quotes inside": 'workstreams retire""-settings', "pieces": "workstreams re'tire-sett'ings",
    "without workstreams": "retire-settings", "after a bare --": "workstreams -- 'retire-settings'",
    "after an option": 'workstreams -h "retire-settings"',
}
# F5 review: the shell turns these into `setting` / `retire-settings` when a file of that name is in the run's folder (the vault root)
GLOB_SETTING_WORDS = {
    "? for t": "setti?g", "[s]": "[s]etting", "star after": "setting*", "star inside": "s*ting", "star first": "*etting",
    "quoted piece and ?": "'sett'?ng", "? for e": "s?tting", "bracket in the middle": "s[e]tting", "question mark last": "setting?",
    "range": "[a-z]etting", "negated bracket": "[^x]etting", "all": "*", "a quoted pattern (the shell leaves it)": "'setti?g'",
}
GLOB_RETIRE_ARGS = {
    "? last": "workstreams retire-setting?", "star": "workstreams retire-*", "[r]": "workstreams [r]etire-settings",
    "star in the middle": "workstreams re*", "? first": "workstreams ?etire-settings", "star on workstreams": "workst*ms retire-settings",
    "after an option": "workstreams -h retire-*", "after a bare --": "workstreams -- retire-*",
    "a name with a bracket": "workstreams add ABC 'Data [Migration]'",
}
# the characters str.split cuts at and the shell doesn't (a non-breaking space, a vertical tab, a form feed, …): the old rule saw
# `setting` in these; the unquoted words alone would not
SPACE_FORMS = {
    "nbsp before setting": "python3 system/scripts/propose.py\xa0setting sweep.due_from 06:30",
    "vertical tab before setting": "python3 system/scripts/propose.py\vsetting sweep.due_from 06:30",
    "form feed before setting": "python3 system/scripts/propose.py\fsetting sweep.due_from 06:30",
    "nbsp after setting": "python3 system/scripts/propose.py setting\xa0sweep.due_from 06:30",
    "em space after setting": "python3 system/scripts/propose.py setting\u2003sweep.due_from 06:30",
    "ideographic space": "python3 system/scripts/propose.py\u3000setting sweep.due_from 06:30",
    "next line": "python3 system/scripts/propose.py setting\x85sweep.due_from 06:30",
    "file separator": "python3 system/scripts/propose.py\x1csetting sweep.due_from 06:30",
    "nbsp after retire-settings": "python3 system/scripts/propose.py workstreams retire-settings\xa0x",
    "run launcher, nbsp": "system/scripts/run propose.py\xa0setting sweep.due_from 06:30",
}

# forms the shell-character check or the script check refuses before the settings rule is reached
OTHER_FORMS = {
    "$'..'": "python3 system/scripts/propose.py $'setting' a b",
    "$'..' hex": "python3 system/scripts/propose.py $'\\x73etting' a b",
    '$"..."': 'python3 system/scripts/propose.py $"setting" a b',
    "$(..)": "python3 system/scripts/propose.py $(echo setting) a b",
    "back-quote": "python3 system/scripts/propose.py `echo setting` a b",
    "${..}": "python3 system/scripts/propose.py ${S} a b",
    "escaped letter": "python3 system/scripts/propose.py se\\tting a b",
    "escaped first letter": "python3 system/scripts/propose.py \\setting a b",
    "backslash in double quotes": 'python3 system/scripts/propose.py "se\\tting" a b',
    "env prefix": "X=1 python3 system/scripts/propose.py setting a b",
    "env command": "env python3 system/scripts/propose.py setting a b",
    "./ prefix": "./system/scripts/propose.py setting a b",
    "./ after python3": "python3 ./system/scripts/propose.py setting a b",
    "another folder's path": "python3 /opt/other/system/scripts/propose.py setting a b",
    "another folder's run": "/opt/other/system/scripts/run propose.py setting a b",
    "two spaces": "python3  system/scripts/propose.py setting a b",
    "quoted script name": "python3 system/scripts/'propose.py' setting a b",
    "quoted script path": "python3 'system/scripts/propose.py' setting a b",
    "after cd": "cd . && python3 system/scripts/propose.py setting a b",
    "after another script": "python3 system/scripts/doctor.py ; python3 system/scripts/propose.py setting a b",
    "chained with &&": "python3 system/scripts/doctor.py && python3 system/scripts/propose.py 'setting' a b",
    "through sh -c": "sh -c 'python3 system/scripts/propose.py setting a b'",
    "through bash -c": 'bash -c "python3 system/scripts/propose.py setting a b"',
    "python -c": "python3 -c \"import propose; propose.cmd_setting('a','b')\"",
    "python -m": "python3 -m propose setting a b",
    "piped": "python3 system/scripts/propose.py 'setting' a b | cat",
    "redirected": "python3 system/scripts/propose.py 'setting' a b > x",
    "new line": "python3 system/scripts/doctor.py\npython3 system/scripts/propose.py setting a b",
    "carriage return": "python3 system/scripts/propose.py setting a b\rx",
    "tab": "python3 system/scripts/propose.py\tsetting\ta b",          # a tab is a word break to the shell and shlex alike
    "the wrapper's own word": "system/scripts/run reach.py wrap propose.py setting a b",
    "permissions.py": "python3 system/scripts/permissions.py edit x",
    "unclosed quote": "python3 system/scripts/propose.py 'setting a b",
}

# normal creaite runs: the skills' and the server's commands (the guard decides them as before, in every mode)
NORMAL = {
    "tracker apply": "system/scripts/run tracker.py apply",
    "tracker apply, python3": "python3 system/scripts/tracker.py apply",
    "tracker read": "system/scripts/run tracker.py read ABC-A-001",
    "tracker undo": "system/scripts/run tracker.py undo",
    "propose stage": "system/scripts/run propose.py stage system/staging/drafts/x.json",
    "propose preview": "system/scripts/run propose.py preview system/staging/drafts/x.json",
    "propose fields": "system/scripts/run propose.py fields actions",
    "propose new-project": "system/scripts/run propose.py new-project --code DEF --name 'Example Programme Two' --out def.json",
    "propose close-project": "system/scripts/run propose.py close-project ABC --out close.json",
    "propose recode dry run": "system/scripts/run propose.py recode ABC XYZ --dry-run",
    "propose learn": "system/scripts/run propose.py learn ABC alias 'Example Prog'",
    "propose people list": "system/scripts/run propose.py people list",
    "propose people add": "system/scripts/run propose.py people add 'Sara Khan' --email s.khan@example.com",
    "propose people map": "system/scripts/run propose.py people map system/staging/drafts/x.json",
    "propose workstreams list": "system/scripts/run propose.py workstreams list --project ABC",
    "propose workstreams add": "system/scripts/run propose.py workstreams add ABC 'Data Migration' --lead 'Omar Reyes'",
    "workstream named setting": "system/scripts/run propose.py workstreams add ABC setting",
    "learn with setting as a value": "system/scripts/run propose.py learn ABC alias setting",
    "sweep stage": "system/scripts/run sweep.py stage system/staging/drafts/s.json",
    "sweep due": "system/scripts/run sweep.py due",
    "minutes transcript": "system/scripts/run minutes.py transcript 'projects/ABC Example Programme/transcripts/x.vtt'",
    "review approve": "system/scripts/run review.py approve 1 2",
    "search query": 'system/scripts/run search.py query "data access risks"',
    "doctor": "system/scripts/run doctor.py",
    "filechange edit of the settings": "system/scripts/run filechange.py edit system/config/settings.json "
                                       "--from system/staging/drafts/settings.json --why 'change the sweep time'",
    "filechange create": "system/scripts/run filechange.py create 'projects/ABC Example Programme/notes.md' "
                         "--from system/staging/drafts/n.md --why 'note'",
    "build dashboard": "system/scripts/run build_dashboard.py",
    "stage a quoted file name with a bracket": "system/scripts/run propose.py stage 'system/staging/drafts/x [1].json'",
    "preview a quoted file name": "system/scripts/run propose.py preview 'system/staging/drafts/x y.json'",
    "a name with a non-breaking space": "system/scripts/run propose.py people add 'Sara\xa0Khan' --email s.khan@example.com",
    "a name with a question mark outside workstreams": "system/scripts/run propose.py learn ABC alias 'Why? Programme'",
}
# of those, the ones a confirmed run may run (nothing in them is refused by any rule: the filechange paths are Alan's own files)
CONFIRMED_OK = ("tracker apply", "tracker apply, python3", "tracker read", "tracker undo", "propose stage", "propose preview",
                "propose fields", "propose new-project", "propose close-project", "propose recode dry run", "propose learn",
                "propose people list", "propose people add", "propose workstreams list", "propose workstreams add",
                "workstream named setting", "learn with setting as a value", "stage a quoted file name with a bracket",
                "preview a quoted file name", "a name with a non-breaking space", "a name with a question mark outside workstreams", "sweep stage", "sweep due", "minutes transcript",
                "review approve", "search query", "doctor", "filechange edit of the settings", "filechange create", "build dashboard")


def setting_commands(root):
    out = {}
    for lname, launcher in LAUNCHERS.items():
        for wname, word in SETTING_WORDS.items():
            out[f"{lname} | {wname}"] = launcher.format(ROOT=root) + f" {word} sweep.due_from 06:30"
        out[f"{lname} | setting with no value"] = launcher.format(ROOT=root) + " 'setting'"
    return out


def glob_commands(root):
    out = {f"{lname} | {wname}": launcher.format(ROOT=root) + f" {word} sweep.due_from 05:55"
           for lname, launcher in LAUNCHERS.items() for wname, word in GLOB_SETTING_WORDS.items()}
    out.update({f"{lname} | {aname}": launcher.format(ROOT=root) + f" {args}"
                for lname, launcher in LAUNCHERS.items() for aname, args in GLOB_RETIRE_ARGS.items()})
    return out


def retire_commands(root):
    return {f"{lname} | {aname}": launcher.format(ROOT=root) + f" {args}"
            for lname, launcher in LAUNCHERS.items() for aname, args in RETIRE_ARGS.items()}


class Scratch(unittest.TestCase):
    """Base: the scratch copy under test (patched, unless GUARD_174_UNPATCHED=1) and the unpatched one."""

    @classmethod
    def setUpClass(cls):
        cls.patched = scratch(patched=not UNPATCHED, mutation=MUTATE)
        cls.base = scratch(patched=False)
        cls.root = str(cls.patched.root)
        cls.base_root = str(cls.base.root)

    @classmethod
    def tearDownClass(cls):
        cls.patched.cleanup()
        cls.base.cleanup()


class Attacks(Scratch):
    """F5: every spelling of the settings commands is refused, in every mode."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.setting = setting_commands(cls.root)
        cls.retire = retire_commands(cls.root)
        cls.other = {k: v for k, v in OTHER_FORMS.items()}
        cls.glob = glob_commands(cls.root)
        cls.space = dict(SPACE_FORMS)
        cls.got = decisions(cls.patched, list(cls.setting.values()) + list(cls.retire.values()) + list(cls.other.values())
                            + list(cls.glob.values()) + list(cls.space.values()))

    def refused_everywhere(self, cmd, shared=True):
        """Refused by every mode's decision and, with `shared`, by bash_problem, the check all modes make first."""
        if shared:
            self.assertIsNotNone(self.got["problem"][cmd], f"bash_problem lets it through: {cmd!r}")
        for mode in MODES:
            self.assertFalse(self.got["decide"][mode][cmd][0], f"{mode} lets it through: {cmd!r}")

    def test_the_diff_is_in_the_repo_and_applies(self):
        self.assertTrue(DIFF.is_file(), DIFF)
        text = DIFF.read_text(encoding="utf-8")
        files = re.findall(r"^\+\+\+ (\S+)", text, re.M)
        self.assertEqual(files, ["system/scripts/reach.py"], "the proposal changes reach.py only")
        self.assertEqual(len(re.findall(r"^@@ ", text, re.M)), 2)

    def test_every_spelling_of_setting_is_refused_with_the_settings_reason(self):
        for name, cmd in self.setting.items():
            with self.subTest(name):
                self.refused_everywhere(cmd)
                if not name.startswith("abs-"):        # bash_refusal reads this vault's full path as the relative form first
                    self.assertIn(SETTINGS_WHY, self.got["problem"][cmd], cmd)      # the check every mode shares
                self.assertIn(SETTINGS_WHY, self.got["decide"]["confirmed"][cmd][1], cmd)   # and the confirmed run, which has no record gate

    def test_every_spelling_of_retire_settings_is_refused_with_the_settings_reason(self):
        for name, cmd in self.retire.items():
            with self.subTest(name):
                self.refused_everywhere(cmd)
                if not name.startswith("abs-"):
                    self.assertIn(SETTINGS_WHY, self.got["problem"][cmd], cmd)
                self.assertIn(SETTINGS_WHY, self.got["decide"]["confirmed"][cmd][1], cmd)

    def test_a_wildcard_in_the_command_word_is_refused_in_every_mode(self):
        """The shell expands `setti?g` to a file named `setting` in the vault (made first by `filechange.py create`, an ordinary
        change): the guard never expands it, so it refuses any * ? [ in propose.py's first argument and after `workstreams`."""
        for name, cmd in self.glob.items():
            with self.subTest(name):
                self.refused_everywhere(cmd)
                if not name.startswith("abs-"):
                    self.assertIn(SETTINGS_WHY, self.got["problem"][cmd], cmd)
                self.assertIn(SETTINGS_WHY, self.got["decide"]["confirmed"][cmd][1], cmd)

    def test_a_space_the_shell_does_not_cut_at_never_hides_the_word(self):
        """str.split cuts at a non-breaking space or a vertical tab, shlex and the shell don't: the old rule refused these
        forms (it saw `setting`), so the new one must too (the settings rule reads the command both ways)."""
        for name, cmd in self.space.items():
            with self.subTest(name):
                self.refused_everywhere(cmd)
                self.assertIn(SETTINGS_WHY, self.got["decide"]["confirmed"][cmd][1], cmd)

    def test_the_shell_really_expands_the_pattern(self):
        """The premise, checked with the shell itself (zsh, if installed; the Bash tool's shell): a file named `setting` in the
        run's folder is what `setti?g` and `retire-*` become."""
        zsh = shutil.which("zsh")
        if not zsh:
            self.skipTest("zsh is not installed")
        d = Path(self.root)
        (d / "setting").write_text("x", encoding="utf-8")
        (d / "retire-settings").write_text("x", encoding="utf-8")
        for pattern, word in (("setti?g", "setting"), ("[s]etting", "setting"), ("s*ting", "setting"), ("retire-*", "retire-settings")):
            r = subprocess.run([zsh, "-c", f"printf '%s' {pattern}"], cwd=d, capture_output=True, text=True)
            self.assertEqual(r.stdout, word, pattern)

    def test_the_other_forms_are_refused_in_every_mode(self):
        for name, cmd in self.other.items():
            with self.subTest(name):
                self.refused_everywhere(cmd, shared=False)      # some are refused by a later check (the hand-over rule), not bash_problem

    def test_the_settings_rule_fails_closed(self):
        self.assertIn(SETTINGS_WHY, self.got["direct"]["none_words"] or "")     # a command that can't be split is refused
        self.assertIsNone(self.got["direct"]["unclosed"])

    def test_the_hook_refuses_the_quoted_forms_in_confirmed_and_every_mode(self):
        for mode in MODES:
            for cmd in ("python3 system/scripts/propose.py 'setting' sweep.due_from 06:30",
                        'system/scripts/run propose.py se""tting sweep.due_from 06:30',
                        'system/scripts/run propose.py workstreams "retire-settings"'):
                with self.subTest(mode=mode, cmd=cmd):
                    r = subprocess.run(["/bin/sh", "system/scripts/run", "reach.py", "hook", "--run", "r-test", "--mode", mode],
                                       cwd=self.patched.root, input=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}}),
                                       capture_output=True, text=True, timeout=60, env={**os.environ})
                    self.assertEqual(r.returncode, 2, r.stderr)
                    if mode == "confirmed":
                        self.assertIn(SETTINGS_WHY, r.stderr)


class Defect(Scratch):
    """The defect is real, whatever state the repo is in: the unpatched copy lets F5's forms through a confirmed run."""

    def test_unpatched_lets_the_quoted_forms_through_a_confirmed_run(self):
        cmds = ["python3 system/scripts/propose.py 'setting' sweep.due_from 06:30",
                'python3 system/scripts/propose.py se""tting sweep.due_from 06:30',
                'python3 system/scripts/propose.py workstreams "retire-settings"',
                f"python3 {self.base_root}/system/scripts/propose.py 'setting' sweep.due_from 06:30"]
        got = decisions(self.base, cmds)
        for cmd in cmds:
            with self.subTest(cmd):
                if cmd.startswith("python3 system"):                                 # (the full-path form is made relative first)
                    self.assertIsNone(got["problem"][cmd])                           # bash_problem: no refusal
                self.assertEqual(got["decide"]["confirmed"][cmd], [True, ""])        # F5: a confirmed run goes through
        plain = decisions(self.base, ["python3 system/scripts/propose.py setting sweep.due_from 06:30"])
        self.assertIn(SETTINGS_WHY, plain["problem"]["python3 system/scripts/propose.py setting sweep.due_from 06:30"])

    def test_unpatched_lets_the_glob_forms_through_a_confirmed_run(self):
        """Pre-existing (the review of 5b20e38c): neither the old rule nor the first diff saw a pattern."""
        cmds = ["python3 system/scripts/propose.py setti?g sweep.due_from 05:55", "python3 system/scripts/propose.py workstreams retire-*",
                "python3 system/scripts/propose.py [s]etting sweep.due_from 05:55"]
        got = decisions(self.base, cmds)
        for cmd in cmds:
            with self.subTest(cmd):
                self.assertIsNone(got["problem"][cmd])
                self.assertEqual(got["decide"]["confirmed"][cmd], [True, ""])

    def test_the_other_modes_were_only_held_by_the_record_gate(self):
        """In ask, sweep, prep and held the unpatched file still refuses `'setting'`, by the record gate (a different rule, not the
        settings one): the proposal restores the settings rule itself, and the confirmed run, which has no record gate, needs it."""
        cmd = "python3 system/scripts/propose.py 'setting' sweep.due_from 06:30"
        got = decisions(self.base, [cmd])
        for mode in ("ask", "sweep", "prep", "held"):
            self.assertFalse(got["decide"][mode][cmd][0], mode)
            self.assertNotIn(SETTINGS_WHY, got["decide"][mode][cmd][1], mode)


class Normal(Scratch):
    """Nothing legitimate changes: the patch decides every normal creaite run as the unpatched file does."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cmds = dict(NORMAL)
        cls.p = decisions(cls.patched, list(cls.cmds.values()))
        cls.b = decisions(cls.base, list(cls.cmds.values()))

    def test_same_decision_as_without_the_patch_in_every_mode(self):
        for name, cmd in self.cmds.items():
            with self.subTest(name):
                self.assertEqual(self.p["problem"][cmd], self.b["problem"][cmd])
                for mode in MODES:
                    self.assertEqual(self.p["decide"][mode][cmd], self.b["decide"][mode][cmd], mode)

    def test_the_commands_a_confirmed_run_needs_still_pass(self):
        for name in CONFIRMED_OK:
            cmd = self.cmds[name]
            with self.subTest(name):
                self.assertIsNone(self.p["problem"][cmd], cmd)
                self.assertEqual(self.p["decide"]["confirmed"][cmd], [True, ""], cmd)

    def test_read_commands_still_pass_in_every_mode(self):
        for name in ("tracker read", "propose fields", "propose people list", "propose workstreams list", "doctor", "search query"):
            cmd = self.cmds[name]
            for mode in MODES:
                with self.subTest(name, mode=mode):
                    self.assertEqual(self.p["decide"][mode][cmd], [True, ""], cmd)

    def test_the_record_gate_is_unchanged_in_a_plain_chat(self):
        for name in ("tracker apply", "propose stage", "review approve"):
            self.assertFalse(self.p["decide"]["ask"][self.cmds[name]][0], name)

    def test_a_name_that_is_the_word_setting_is_still_allowed(self):
        """`workstreams add ABC setting` and `learn ABC alias setting` name something `setting`; only the first argument counts."""
        for name in ("workstream named setting", "learn with setting as a value"):
            self.assertEqual(self.p["decide"]["confirmed"][self.cmds[name]], [True, ""], name)

    def test_the_settings_edit_the_refusal_names_still_passes(self):
        cmd = self.cmds["filechange edit of the settings"]
        self.assertEqual(self.p["decide"]["ask"][cmd], [True, ""])               # the refusal text sends the model here

    def test_every_command_in_the_skills_rules_and_prompts_is_decided_as_before(self):
        docs = (sorted((REPO / ".claude/skills").glob("*/SKILL.md")) + sorted((REPO / ".claude/skills").glob("*/references/*.md"))
                + [REPO / "system/creaite-rules.md"] + sorted((REPO / "system/templates/drafts").glob("*.md")))
        span = re.compile(r"`((?:python3? system/scripts/|system/scripts/run )[^`\n]+)`")
        spans = sorted({m.group(1) for f in docs for m in span.finditer(f.read_text(encoding="utf-8"))})
        self.assertGreater(len(spans), 50, "the docs show many commands")
        import shlex
        for c in spans:           # no command the docs show has a wildcard in propose.py's first argument, or after workstreams
            if re.match(r"(?:python3? system/scripts/|system/scripts/run )propose\.py\b", c):
                words = shlex.split(c.replace("<", "x").replace(">", "x"))[2:]
                self.assertFalse(words and any(ch in words[0] for ch in "*?["), c)
                if words[:1] == ["workstreams"]:
                    self.assertFalse(any(ch in w for w in words[1:] for ch in "*?["), c)
        p, b = decisions(self.patched, spans), decisions(self.base, spans)
        self.assertEqual(p["problem"], b["problem"])
        for mode in MODES:
            self.assertEqual(p["decide"][mode], b["decide"][mode], mode)


class Mutations(unittest.TestCase):
    """Revert or break one line of the patch on the scratch copy: the attack tests go red (run in a child process)."""

    @unittest.skipIf(UNPATCHED or MUTATE, "the mutation runs are the parent's job")
    def test_each_mutation_turns_a_test_red(self):
        for name, (what, _old, _new) in MUTATIONS.items():
            with self.subTest(name):
                r = subprocess.run([sys.executable, str(Path(__file__).resolve()), "Attacks"], cwd=REPO, capture_output=True, text=True,
                                   env={**os.environ, "GUARD_174_MUTATE": name}, timeout=900)
                self.assertNotEqual(r.returncode, 0, f"mutation {name} ({what}) left every attack test green")
                self.assertIn("FAILED", r.stderr)


if __name__ == "__main__":
    unittest.main()
