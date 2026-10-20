"""#174 (Alan, via Jarvis): ask creaite can't write a report-named draft through report.py adhoc and steerco-stage or docx_tools.py fill
and build-adhoc either. PROPOSAL test.

Run: python3 dev/tests/test_guard_steerco_adhoc.py                      (quick tier: no Chrome)
Fail-first: GUARD_STEERCO_UNPATCHED=1 python3 dev/tests/test_guard_steerco_adhoc.py   (the scratch copy is left without the diff)

v2.5.1's report rule covers `report.py weekly-stage` and `client-stage`. `report.py steerco-stage` and `adhoc`, and `docx_tools.py fill`
and `build-adhoc`, also write a Word draft into system/staging/drafts/, and `adhoc` names it from the spec's title, so the title
'Example Programme Weekly report' wrote a report-named draft outside the rule. `reach.py` is a guarded file: the fix is the proposal
dev/proposals/guard-174/reach-steerco-adhoc.diff (a third diff, which applies alone and in any order with reach.diff and
reach-report.diff). It refuses those builders ONLY when the draft is named like a report (report, weekly or client in the output file
name, or in the title of the spec file, or a client-safe Steerco one-pager); ordinary documents and internal one-pagers and every read
stay allowed. This file applies it with `patch -p0` to a copy of the whole of system/scripts/ in a throwaway vault (with spec files in
its system/staging/drafts/) and reads the guard's decisions from that copy (`reach.decide`, as the hook calls it) in every mode.
After the diff is applied to the repo the marker is found and the same tests keep guarding it (the unpatched copy is made with `patch -R`).
"""
import itertools
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
DIFF = PROPOSALS / "reach-steerco-adhoc.diff"
OTHER_DIFFS = (PROPOSALS / "reach.diff", PROPOSALS / "reach-report.diff")
UNPATCHED = os.environ.get("GUARD_STEERCO_UNPATCHED") == "1"
MUTATE = os.environ.get("GUARD_STEERCO_MUTATE", "")
MARKER = "def report_named_draft_refusal"
MODES = ("ask", "confirmed", "sweep", "prep", "held")
WHY = "reports are the user's"
D = "system/staging/drafts/"

MUTATIONS = {
    "drop-weekly": ("the word weekly is dropped from the report words", r'+ r"|report|weekly|client"', r'+ r"|report|client"'),
    "drop-title-read": ("the spec's title is not read", 'return str(spec.get("title") or ""), str(spec.get("version") or "")',
                        'return "", str(spec.get("version") or "")'),
    "fail-open-unreadable": ("an unreadable adhoc spec with a report-named file is let through",
                             'return sub == "adhoc" and bool(REPORT_WORDS.search(', 'return False and bool(REPORT_WORDS.search('),
    "drop-client-version": ("a client-safe one-pager is let through", 'version.lower() == "client"', "False"),
    "drop-output-name": ("the output file's name is not looked at", "if REPORT_WORDS.search(pos[3].rsplit", "if False and REPORT_WORDS.search(pos[3].rsplit"),
    "unsplittable-open": ("a command that can't be split is let through", "REPORT_WORDS.search(rest) else None", "False else None"),
}

SPECS = {                                 # file name -> content (a str is written as it is)
    "spec-a.json": {"title": "Example Programme Weekly report"}, "spec-b.json": {"title": "Client report for the steering"},
    "spec-c.json": {"title": "Weekly status pack"}, "spec-d.json": {"title": "Quarterly reporting"},
    "spec-n.json": {"title": "Open risks register"}, "spec-n2.json": {"title": "Data access decisions"},
    "spec-s-client.json": {"code": "ABC", "version": "client"}, "spec-s-int.json": {"code": "ABC", "version": "internal"},
    "spec-s-none.json": {"code": "ABC"}, "spec-s-title.json": {"code": "ABC", "title": "Weekly report one-pager"},
    "spec-notitle.json": {"audience": "internal"}, "spec-bad.json": "this is not json",
    "spec-weekly-pack.json": "this is not json",     # unreadable, and its own name is report-named
}
LAUNCHERS = {
    "python3": "python3 system/scripts/{s}", "python": "python system/scripts/{s}", "run": "system/scripts/run {s}",
    "abs-python3": "python3 {ROOT}/system/scripts/{s}", "abs-run": "{ROOT}/system/scripts/run {s}",
}
ADHOC_WORDS = ("adhoc", "'adhoc'", '"adhoc"', "ad''hoc", 'ad""hoc')
STEERCO_WORDS = ("steerco-stage", "'steerco-stage'", '"steerco-stage"', "steerco''-stage", "stee'rco-st'age")
TEMPLATE = "system/templates/adhoc-template.docx"

HARNESS = r'''
import json, sys
sys.path.insert(0, "system/scripts")
import reach
cmds, modes = json.loads(sys.stdin.read())
out = {"decide": {m: {c: list(reach.decide("Bash", {"command": c}, m, "r-1")) for c in cmds} for m in modes}}
if hasattr(reach, "report_named_draft_refusal"):
    out["unsplittable"] = reach.report_named_draft_refusal("python3 system/scripts/report.py adhoc 'weekly.json")
    out["unsplittable_neutral"] = reach.report_named_draft_refusal("python3 system/scripts/report.py adhoc 'notes.json")
print(json.dumps(out))
'''


def _patch(root, diff, *flags):
    r = subprocess.run(["patch", "-p0", "-s", *flags, "-i", str(diff)], cwd=root, capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError(f"patch {diff.name} {' '.join(flags)} failed in the scratch copy:\n{r.stdout}\n{r.stderr}")


def scratch(patched, others=(), mutation=""):
    """A throwaway vault with a copy of the whole of system/scripts/ and spec files in its drafts folder; reach.py with (or without)
    reach-steerco-adhoc.diff, after the other diffs named in `others` (a tuple of paths) were applied first."""
    v = Vault()
    v.run("init")
    shutil.copytree(REPO / "system" / "scripts", v.root / "system" / "scripts", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__"))
    drafts = v.root / "system" / "staging" / "drafts"
    drafts.mkdir(parents=True, exist_ok=True)
    for name, content in SPECS.items():
        (drafts / name).write_text(content if isinstance(content, str) else json.dumps(content), encoding="utf-8")
    reach = v.root / "system" / "scripts" / "reach.py"
    text = reach.read_text(encoding="utf-8")
    for diff in others:
        marker = "def _glob_refused" if diff.name == "reach.diff" else "def _stages_a_report"
        if marker not in reach.read_text(encoding="utf-8"):
            _patch(v.root, diff)
    already = MARKER in text
    if patched and not already:
        _patch(v.root, DIFF)
    if not patched and already:
        _patch(v.root, DIFF, "-R")
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


def report_calls(root, specs, words, mode_script="report.py"):
    out = {}
    for lname, launcher in LAUNCHERS.items():
        for spec in specs:
            for w in words:
                out[f"{lname} | {w} | {spec}"] = launcher.format(s=mode_script, ROOT=root) + f" {w} {D}{spec}"
    return out


def docx_calls(root):
    """name -> (command, whether it must be refused)."""
    def d(args, lname="python3"):
        return LAUNCHERS[lname].format(s="docx_tools.py", ROOT=root) + " " + args
    calls = {}
    for lname in LAUNCHERS:
        for out in ("'%s2026-10-16 Weekly status.docx'" % D, "'%sClient list.docx'" % D, "'%sQuarterly reporting.docx'" % D):
            calls[f"{lname} | fill, named {out[-24:]}"] = (d(f"fill {TEMPLATE} {D}spec-n.json {out}", lname), True)
            calls[f"{lname} | build-adhoc, named {out[-24:]}"] = (d(f"build-adhoc {TEMPLATE} {D}spec-n.json {out}", lname), True)
        calls[f"{lname} | quoted fill"] = (d(f"'fill' {TEMPLATE} {D}spec-n.json '{D}Weekly status.docx'", lname), True)
        calls[f"{lname} | spliced fill"] = (d(f"fi''ll {TEMPLATE} {D}spec-n.json {D}client.docx", lname), True)
        calls[f"{lname} | build-adhoc, report-titled spec, neutral file"] = (d(f"build-adhoc {TEMPLATE} {D}spec-a.json {D}out.docx", lname), True)
        calls[f"{lname} | fill, neutral"] = (d(f"fill {TEMPLATE} {D}spec-n.json {D}out.docx", lname), False)
        calls[f"{lname} | build-adhoc, neutral"] = (d(f"build-adhoc {TEMPLATE} {D}spec-n.json {D}Open risks.docx", lname), False)
    return calls


REFUSED_ADHOC = ("spec-a.json", "spec-b.json", "spec-c.json", "spec-d.json", "spec-weekly-pack.json")
REFUSED_STEERCO = ("spec-s-client.json", "spec-s-title.json")
ALLOWED_ADHOC = ("spec-n.json", "spec-n2.json", "spec-notitle.json", "spec-bad.json", "spec-missing.json")
ALLOWED_STEERCO = ("spec-s-int.json", "spec-s-none.json", "spec-missing.json")
READS = ("python3 system/scripts/report.py adhoc-data ABC", "system/scripts/run report.py steerco-data ABC",
         "python3 system/scripts/report.py weekly-data ABC", "system/scripts/run report.py client-data ABC",
         "python3 system/scripts/docx_tools.py text system/templates/adhoc-template.docx",
         "system/scripts/run docx_tools.py status system/templates/adhoc-template.docx")


class Builders(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patched = scratch(patched=not UNPATCHED, mutation=MUTATE)
        cls.base = scratch(patched=False)
        r = str(cls.patched.root)
        cls.refused = {**report_calls(r, REFUSED_ADHOC, ADHOC_WORDS), **report_calls(r, REFUSED_STEERCO, STEERCO_WORDS)}
        cls.allowed = {**report_calls(r, ALLOWED_ADHOC, ADHOC_WORDS[:2]), **report_calls(r, ALLOWED_STEERCO, STEERCO_WORDS[:2])}
        cls.docx = docx_calls(r)
        cls.got = decisions(cls.patched, list(cls.refused.values()) + list(cls.allowed.values()) + [c for c, _ in cls.docx.values()]
                            + list(READS))

    @classmethod
    def tearDownClass(cls):
        cls.patched.cleanup()
        cls.base.cleanup()

    def test_a_report_named_adhoc_or_steerco_draft_is_refused_in_every_mode(self):
        for name, cmd in self.refused.items():
            with self.subTest(name):
                for mode in MODES:
                    self.assertFalse(self.got["decide"][mode][cmd][0], f"{mode} lets it through: {cmd!r}")
                for mode in ("ask", "confirmed", "sweep"):          # the modes the report rule (ask_bash_refusal) is in
                    self.assertIn(WHY, self.got["decide"][mode][cmd][1], (mode, cmd))

    def test_docx_tools_fill_and_build_adhoc_with_a_report_named_file_or_title_are_refused(self):
        for name, (cmd, refused) in self.docx.items():
            if not refused:
                continue
            with self.subTest(name):
                for mode in MODES:
                    self.assertFalse(self.got["decide"][mode][cmd][0], f"{mode} lets it through: {cmd!r}")
                for mode in ("ask", "confirmed", "sweep"):
                    self.assertIn(WHY, self.got["decide"][mode][cmd][1], (mode, cmd))

    def test_ordinary_documents_and_internal_one_pagers_stay_allowed(self):
        for name, cmd in self.allowed.items():
            with self.subTest(name):
                for mode in ("ask", "confirmed", "sweep"):
                    self.assertEqual(self.got["decide"][mode][cmd], [True, ""], (mode, cmd))

    def test_neutral_docx_tools_runs_stay_allowed(self):
        for name, (cmd, refused) in self.docx.items():
            if refused:
                continue
            with self.subTest(name):
                for mode in ("ask", "confirmed", "sweep"):
                    self.assertEqual(self.got["decide"][mode][cmd], [True, ""], (mode, cmd))

    def test_reads_stay_allowed(self):
        for cmd in READS:
            with self.subTest(cmd):
                for mode in ("ask", "confirmed", "sweep"):
                    self.assertEqual(self.got["decide"][mode][cmd], [True, ""], (mode, cmd))

    def test_an_unsplittable_command_fails_closed(self):
        self.assertIn(WHY, self.got.get("unsplittable") or "")
        self.assertIsNone(self.got.get("unsplittable_neutral"))

    def test_nothing_else_changes(self):
        """The allowed and read commands are decided exactly as on the unpatched file."""
        cmds = list(self.allowed.values()) + [c for c, refused in self.docx.values() if not refused] + list(READS)
        base_cmds = [c.replace(str(self.patched.root), str(self.base.root)) for c in cmds]
        base = decisions(self.base, base_cmds)
        for mode in MODES:
            self.assertEqual([self.got["decide"][mode][c] for c in cmds], [base["decide"][mode][c] for c in base_cmds], mode)


class Hole(unittest.TestCase):
    """The hole is real on the unpatched file (so the proposal is needed)."""

    def test_unpatched_lets_report_named_drafts_through(self):
        v = scratch(patched=False)
        try:
            r = str(v.root)
            cmds = [*report_calls(r, ("spec-a.json",), ("adhoc", "'adhoc'")).values(),
                    *report_calls(r, ("spec-s-client.json",), ("steerco-stage", "'steerco-stage'")).values(),
                    f"python3 system/scripts/docx_tools.py fill {TEMPLATE} {D}spec-n.json '{D}Weekly status.docx'",
                    f"system/scripts/run docx_tools.py build-adhoc {TEMPLATE} {D}spec-a.json {D}out.docx"]
            got = decisions(v, cmds)
            for cmd in cmds:
                with self.subTest(cmd):
                    for mode in ("ask", "confirmed", "sweep"):
                        self.assertEqual(got["decide"][mode][cmd], [True, ""], (mode, cmd))
        finally:
            v.cleanup()


class Orders(unittest.TestCase):
    """Applies alone and in every order with reach.diff and reach-report.diff; the combined copy still refuses the draft."""

    @unittest.skipIf(UNPATCHED or MUTATE, "the unpatched and mutation runs look at the rule only")
    def test_every_order_applies_and_refuses(self):
        markers = {"reach.diff": "def _glob_refused", "reach-report.diff": "def _stages_a_report", DIFF.name: MARKER}
        for order in itertools.permutations((*OTHER_DIFFS, DIFF)):
            with self.subTest(order=[d.name for d in order]):
                v = scratch(patched=False)
                try:
                    reach = v.root / "system" / "scripts" / "reach.py"
                    for diff in order:                      # (a diff already in the repo's reach.py is skipped)
                        if markers[diff.name] not in reach.read_text(encoding="utf-8"):
                            _patch(v.root, diff)
                    r = str(v.root)
                    refused = report_calls(r, ("spec-a.json",), ("'adhoc'",))["python3 | 'adhoc' | spec-a.json"]
                    allowed = report_calls(r, ("spec-n.json",), ("adhoc",))["python3 | adhoc | spec-n.json"]
                    stage = "python3 system/scripts/report.py 'weekly-stage' system/staging/drafts/spec-n.json"
                    got = decisions(v, [refused, allowed, stage])
                    for mode in MODES:
                        self.assertFalse(got["decide"][mode][refused][0], mode)
                        self.assertFalse(got["decide"][mode][stage][0], mode)     # the report diff and this one together
                    for mode in ("ask", "confirmed", "sweep"):
                        self.assertEqual(got["decide"][mode][allowed], [True, ""], mode)
                finally:
                    v.cleanup()

    @unittest.skipIf(UNPATCHED or MUTATE, "the unpatched and mutation runs look at the rule only")
    def test_it_applies_alone(self):
        v = scratch(patched=True)
        v.cleanup()


class Mutations(unittest.TestCase):
    @unittest.skipIf(UNPATCHED or MUTATE, "the mutation runs are the parent's job")
    def test_each_mutation_turns_a_test_red(self):
        for name, (what, _old, _new) in MUTATIONS.items():
            with self.subTest(name):
                r = subprocess.run([sys.executable, str(Path(__file__).resolve()), "Builders"], cwd=REPO, capture_output=True, text=True,
                                   env={**os.environ, "GUARD_STEERCO_MUTATE": name}, timeout=900)
                self.assertNotEqual(r.returncode, 0, f"mutation {name} ({what}) left every test green")
                self.assertIn("FAILED", r.stderr)
                self.assertNotIn("AssertionError: mutation", r.stderr)      # a real failure, not a mutation that no longer applies


if __name__ == "__main__":
    unittest.main()
