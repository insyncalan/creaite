"""#174 (a hole in v2.5.1): ask creaite must not stage a weekly or client report, however the command is spelled. PROPOSAL test.

Run: python3 dev/tests/test_guard_report_quoted.py                      (quick tier: no Chrome)
Fail-first: GUARD_REPORT_UNPATCHED=1 python3 dev/tests/test_guard_report_quoted.py   (the scratch copy is left without the diff)

v2.5.1 refuses `report.py weekly-stage` and `client-stage` in ask, confirmed and sweep with a regular expression on the raw command
text, so quotes splice the word apart: `report.py 'weekly-stage' x.json`, `weekly''-stage`, `"client-stage"` and the same through
`system/scripts/run` were allowed, and wrote a report draft. `reach.py` is a guarded file: the fix is the proposal
dev/proposals/guard-174/reach-report.diff (one hunk), which stands on its own (it needs nothing from reach.diff). This file applies it
with `patch -p0` to a copy of the whole of system/scripts/ in a throwaway vault and reads the guard's decisions from that copy
(`reach.decide`, as the hook calls it) in every mode. It proves: every quoted, spliced, `run`, `python`, absolute-path and
after-an-option form is refused (the plain forms are refused unpatched too, so they can't fail first); reading reports stays allowed
(hand check 40); the diff applies alone, before and after reach.diff (both orders); one mutation (back to raw-text matching) turns it red.
After the diff is applied to the repo the marker is found and the same tests keep guarding it (the unpatched copy is made with `patch -R`).
"""
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_tracker import Vault  # noqa: E402

REPO = HERE.parents[1]
PROPOSALS = REPO / "dev" / "proposals" / "guard-174"
REPORT_DIFF = PROPOSALS / "reach-report.diff"
GLOB_DIFF = PROPOSALS / "reach.diff"
UNPATCHED = os.environ.get("GUARD_REPORT_UNPATCHED") == "1"
MUTATE = os.environ.get("GUARD_REPORT_MUTATE", "")
MARKER = "def _stages_a_report"
MODES = ("ask", "confirmed", "sweep", "prep", "held")
WHY = "reports are the user's"

MUTATIONS = {
    "raw-text": ("the report rule is matched on the raw text again", " or _stages_a_report(cmd):", ":"),
    "fail-open": ("a report.py command that can't be split is let through", 'return "report.py" in cmd', "return False"),
    "first-word": ("only an exact `weekly-stage` word counts (no `client-stage`)", r'r"(?:weekly|client)-stage\b", first', r'r"weekly-stage\b", first'),
}

HARNESS = r'''
import json, sys
sys.path.insert(0, "system/scripts")
import reach
cmds, modes = json.loads(sys.stdin.read())
out = {"decide": {m: {c: list(reach.decide("Bash", {"command": c}, m, "r-1")) for c in cmds} for m in modes},
       "read_report": list(reach.decide("Read", {"file_path": "system/staging/drafts/2026-10-16 Example Programme Client report.json"},
                                        "ask", "r-1")),
       "unclosed": reach._stages_a_report("python3 system/scripts/report.py 'weekly-stage") if hasattr(reach, "_stages_a_report") else None}
print(json.dumps(out))
'''

STAGE_FORMS = {
    "plain weekly (refused before too)": "python3 system/scripts/report.py weekly-stage system/staging/drafts/x.json",
    "plain client (refused before too)": "python3 system/scripts/report.py client-stage system/staging/drafts/x.json",
    "run weekly (refused before too)": "system/scripts/run report.py weekly-stage system/staging/drafts/x.json",
    "run client (refused before too)": "system/scripts/run report.py client-stage system/staging/drafts/x.json",
    "single quotes": "python3 system/scripts/report.py 'weekly-stage' system/staging/drafts/x.json",
    "double quotes": 'python3 system/scripts/report.py "client-stage" system/staging/drafts/x.json',
    "empty quotes inside": "python3 system/scripts/report.py weekly''-stage system/staging/drafts/x.json",
    "empty double quotes inside": 'python3 system/scripts/report.py client""-stage system/staging/drafts/x.json',
    "quoted first half": 'python3 system/scripts/report.py "weekly"-stage system/staging/drafts/x.json',
    "quoted pieces": "python3 system/scripts/report.py we'ekly-st'age system/staging/drafts/x.json",
    "run, single quotes": "system/scripts/run report.py 'weekly-stage' system/staging/drafts/x.json",
    "run, double quotes": 'system/scripts/run report.py "client-stage" system/staging/drafts/x.json',
    "run, empty quotes": "system/scripts/run report.py client''-stage system/staging/drafts/x.json",
    "python (no 3)": "python system/scripts/report.py 'weekly-stage' system/staging/drafts/x.json",
    "after an option": "python3 system/scripts/report.py --x 'client-stage' system/staging/drafts/x.json",
    "abs path, quoted": "python3 {ROOT}/system/scripts/report.py 'weekly-stage' system/staging/drafts/x.json",
    "abs run, quoted": "{ROOT}/system/scripts/run report.py 'client-stage' system/staging/drafts/x.json",
}
# refused earlier than the report rule (the script or quote check), so only "refused" is asserted
FORM_REFUSED = {
    "the script name quoted": "python3 system/scripts/'report.py' weekly-stage system/staging/drafts/x.json",
    "unclosed quote": "python3 system/scripts/report.py 'weekly-stage system/staging/drafts/x.json",
}
READ_FORMS = {
    "weekly-data": "python3 system/scripts/report.py weekly-data ABC", "client-data": "system/scripts/run report.py client-data ABC",
    "steerco-data": "python3 system/scripts/report.py steerco-data ABC", "facts": "system/scripts/run report.py facts ABC",
    "current-context": "python3 system/scripts/report.py current-context ABC", "adhoc-data": "system/scripts/run report.py adhoc-data ABC",
    "quoted read": "python3 system/scripts/report.py 'weekly-data' ABC",
    "a file called weekly-stage-notes": "python3 system/scripts/report.py weekly-data weekly-stage-notes",
}


def _patch(root, diff, *flags):
    r = subprocess.run(["patch", "-p0", "-s", *flags, "-i", str(diff)], cwd=root, capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError(f"patch {diff.name} {' '.join(flags)} failed in the scratch copy:\n{r.stdout}\n{r.stderr}")


def scratch(patched, first_glob=False, mutation=""):
    """A throwaway vault with a copy of the whole of system/scripts/; reach.py with (or without) reach-report.diff, and with
    `first_glob` after reach.diff has been applied first (the other order is checked by Orders)."""
    v = Vault()
    v.run("init")
    shutil.copytree(REPO / "system" / "scripts", v.root / "system" / "scripts", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__"))
    reach = v.root / "system" / "scripts" / "reach.py"
    already = MARKER in reach.read_text(encoding="utf-8")
    if first_glob and "def _glob_refused" not in reach.read_text(encoding="utf-8"):
        _patch(v.root, GLOB_DIFF)
    if patched and not already:
        _patch(v.root, REPORT_DIFF)
    if not patched and already:
        _patch(v.root, REPORT_DIFF, "-R")
    if mutation:
        _what, old, new = MUTATIONS[mutation]
        text = reach.read_text(encoding="utf-8")
        assert text.count(old) == 1, f"mutation {mutation}: {old!r} found {text.count(old)} times"
        reach.write_text(text.replace(old, new), encoding="utf-8")
    return v


def decisions(v, commands):
    r = subprocess.run([sys.executable, "-c", HARNESS], input=json.dumps([commands, list(MODES)]), cwd=v.root,
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


class ReportRule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patched = scratch(patched=not UNPATCHED, mutation=MUTATE)
        cls.base = scratch(patched=False)
        cls.stage = {k: v.replace("{ROOT}", str(cls.patched.root)) for k, v in STAGE_FORMS.items()}
        cls.got = decisions(cls.patched, list(cls.stage.values()) + list(FORM_REFUSED.values()) + list(READ_FORMS.values()))

    @classmethod
    def tearDownClass(cls):
        cls.patched.cleanup()
        cls.base.cleanup()

    def test_every_form_of_a_report_stage_is_refused_in_every_mode(self):
        for name, cmd in self.stage.items():
            with self.subTest(name):
                for mode in MODES:
                    self.assertFalse(self.got["decide"][mode][cmd][0], f"{mode} lets it through: {cmd!r}")
                for mode in ("ask", "confirmed", "sweep"):          # the modes the report rule (ask_bash_refusal) is in
                    self.assertIn(WHY, self.got["decide"][mode][cmd][1], (mode, cmd))

    def test_forms_refused_earlier_stay_refused(self):
        for name, cmd in FORM_REFUSED.items():
            with self.subTest(name):
                for mode in MODES:
                    self.assertFalse(self.got["decide"][mode][cmd][0], (mode, cmd))

    def test_reading_reports_stays_allowed(self):
        for name, cmd in READ_FORMS.items():
            with self.subTest(name):
                for mode in ("ask", "confirmed", "sweep"):
                    self.assertEqual(self.got["decide"][mode][cmd], [True, ""], (mode, cmd))
        self.assertEqual(self.got["read_report"], [True, ""])      # the Read tool on a report draft (hand check 40)

    def test_a_command_that_cant_be_split_fails_closed(self):
        self.assertIs(self.got["unclosed"], True)

    def test_the_hole_is_real_unpatched(self):
        """On the unpatched file ask, confirmed and sweep run the quoted forms: a report draft is written."""
        quoted = [v.replace("{ROOT}", str(self.base.root)) for n, v in STAGE_FORMS.items() if "refused before" not in n]
        got = decisions(self.base, quoted)
        for cmd in quoted:
            with self.subTest(cmd):
                for mode in ("ask", "confirmed", "sweep"):
                    self.assertEqual(got["decide"][mode][cmd], [True, ""], (mode, cmd))

    def test_the_plain_forms_were_already_refused(self):
        plain = [v for n, v in STAGE_FORMS.items() if "refused before" in n]
        got = decisions(self.base, plain)
        for cmd in plain:
            for mode in ("ask", "confirmed", "sweep"):
                self.assertIn(WHY, got["decide"][mode][cmd][1], (mode, cmd))


class Orders(unittest.TestCase):
    """The diff applies on its own and in either order with reach.diff, and the combined copy still refuses the quoted forms."""

    @unittest.skipIf(UNPATCHED or MUTATE, "the unpatched and mutation runs look at the rule only")
    def test_both_orders_apply_and_refuse(self):
        glob_in_repo = "def _glob_refused" in (REPO / "system/scripts/reach.py").read_text(encoding="utf-8")
        for first_glob in (True, False):
            with self.subTest(glob_first=first_glob):
                v = scratch(patched=True, first_glob=first_glob)
                try:
                    if not first_glob and not glob_in_repo:       # the report diff first, then reach.diff
                        _patch(v.root, GLOB_DIFF)
                    cmd = "python3 system/scripts/report.py 'weekly-stage' system/staging/drafts/x.json"
                    got = decisions(v, [cmd])
                    for mode in MODES:
                        self.assertFalse(got["decide"][mode][cmd][0], mode)
                finally:
                    v.cleanup()


class Mutations(unittest.TestCase):
    @unittest.skipIf(UNPATCHED or MUTATE, "the mutation runs are the parent's job")
    def test_each_mutation_turns_a_test_red(self):
        for name, (what, _old, _new) in MUTATIONS.items():
            with self.subTest(name):
                r = subprocess.run([sys.executable, str(Path(__file__).resolve()), "ReportRule"], cwd=REPO, capture_output=True, text=True,
                                   env={**os.environ, "GUARD_REPORT_MUTATE": name}, timeout=900)
                self.assertNotEqual(r.returncode, 0, f"mutation {name} ({what}) left every test green")
                self.assertIn("FAILED", r.stderr)


if __name__ == "__main__":
    unittest.main()
