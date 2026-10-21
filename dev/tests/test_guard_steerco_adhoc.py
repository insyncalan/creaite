"""#174 (Alan, via Jarvis): ask creaite can't write a report-named draft through report.py adhoc and steerco-stage or docx_tools.py fill,
build-adhoc and clean either. PROPOSAL test.

Run: python3 dev/tests/test_guard_steerco_adhoc.py                      (quick tier: no Chrome)
Fail-first: GUARD_STEERCO_UNPATCHED=1 python3 dev/tests/test_guard_steerco_adhoc.py   (the scratch copy is left without the diff)

v2.5.1's report rule covers `report.py weekly-stage` and `client-stage`. `report.py steerco-stage` and `adhoc`, and `docx_tools.py fill`,
`build-adhoc` and `clean`, also write a Word draft into system/staging/drafts/, and `adhoc` names it from the spec's title, so the title
'Example Programme Weekly report' wrote a report-named draft outside the rule. `reach.py` is a guarded file: the fix is the proposal
dev/proposals/guard-174/reach-steerco-adhoc.diff (a third diff, which applies alone and in any order with reach.diff and
reach-report.diff). It refuses those builders ONLY when the draft is named like a report (report, weekly or client, in the output file name,
the title of the spec file, or a client-safe Steerco one-pager, read the way the scripts read their arguments); ordinary documents and
internal one-pagers and every read stay allowed. A spec that can't be read, is over 1 MB, starts with ~, or an odd argument shape, counts as
report-named. This file applies the diff with `patch -p0` to a copy of the whole of system/scripts/ in a throwaway vault (with spec
files in it and a fake home folder) and reads the guard's decisions from that copy (`reach.decide`, as the hook calls it) in every mode.
After the diff is applied to the repo the marker is found and the same tests keep guarding it (the unpatched copy is made with `patch -R`).
Round 7 (reach-r7.diff, applied after the others) adds the Cn category to what _plain removes; the scratch copy gets it too, and
GUARD_STEERCO_NO_R7=1 leaves it out (fail-first for the unassigned-code-point cases).
"""
import itertools
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
from test_tracker import Vault  # noqa: E402

REPO = HERE.parents[1]
PROPOSALS = REPO / "dev" / "proposals" / "guard-174"
DIFF = PROPOSALS / "reach-steerco-adhoc.diff"
OTHER_DIFFS = (PROPOSALS / "reach.diff", PROPOSALS / "reach-report.diff")
R7 = PROPOSALS / "reach-r7.diff"                  # round 7: _plain also drops unassigned code points (applies after DIFF)
R7_MARKER = '"Cc", "Cn", "Mn", "Me"'
NO_R7 = os.environ.get("GUARD_STEERCO_NO_R7") == "1"      # fail-first: the scratch copy is left without round 7
UNPATCHED = os.environ.get("GUARD_STEERCO_UNPATCHED") == "1"
MUTATE = os.environ.get("GUARD_STEERCO_MUTATE", "")
MARKER = "def report_named_draft_refusal"
MODES = ("ask", "confirmed", "sweep", "prep", "held")
WHY = "reports are the user's"
D = "system/staging/drafts/"

MUTATIONS = {
    "drop-weekly": ("the word weekly is dropped from the report words", r'+ r"|report|weekly|client"', r'+ r"|report|client"'),
    "drop-title-read": ("the spec's title is not read", 'for k, v in top if str(k).lower() == "title"]', 'for k, v in top if str(k).lower() == "none"]'),
    "first-title-only": ("only the first title key counts", 'for k, v in top if str(k).lower() == "title"]',
                         'for k, v in top[:1] if str(k).lower() == "title"]'),
    "unreadable-steerco-open": ("an unreadable steerco-stage spec is let through", "    if fields is None:\n        return True",
                                '    if fields is None:\n        return verb == "adhoc"'),
    "oversized-open": ("a spec over 1 MB is read as if it were small", "if p.stat().st_size > 1_000_000:", "if False:"),
    "drop-client-version": ("a client-safe one-pager is let through", 'any("client" in _plain(v) for v in versions)', "False"),
    "drop-output-name": ("the output file's name is not looked at", "or _report_word(rest[2].rsplit", "or False and _report_word(rest[2].rsplit"),
    "dash-words-dropped": ("words starting with - are dropped from the arguments, as v1 of this diff did",
                           'script, argv = w.rsplit("/", 1)[-1], list(words[i + 1:])',
                           'script, argv = w.rsplit("/", 1)[-1], [x for x in words[i + 1:] if not x.startswith("-")]'),
    "expanduser-tilde": ("a ~ path is expanded by the guard, though the shell doesn't expand a quoted one",
                         '    if _odd_word(path):\n        return None\n', "    path = os.path.expanduser(path)\n"),
    "tilde-only-at-start": ("only a leading ~ is refused (x=~/spec is read as a neutral file)", 'return "~" in word or word.startswith("=")',
                            'return word.startswith(("~", "="))'),
    "no-equals-start": ("a word starting with = is let through", 'or word.startswith("=")', ""),
    "no-filler-strip": ("filler letters are kept: a Hangul filler hides the word", 'and c not in FILLERS)', ")"),
    "no-bidi-refuse": ("a bidirectional control character is let through", "return any(c in BIDI_CONTROLS for c in text) or bool(",
                       "return bool("),
    "no-reversed-match": ("the reversed text isn't matched: a bidi override hides the word", " or REPORT_WORDS.search(plain[::-1]))", ")"),
    "odd-words-in-docx-open": ("path words are not checked for ~ and = in docx_tools calls", "    if any(_odd_word(w) for w in rest):\n        return True\n",
                               ""),
    "no-nfkc": ("no NFKC: fullwidth letters don't match", 'unicodedata.normalize("NFKC", text)', "text"),
    "no-mark-strip": ("combining marks are kept: accents hide the word", '("Cf", "Cc", "Cn", "Mn", "Me")', '("Cf", "Cc", "Cn")'),
    "no-zero-width-strip": ("format characters are kept: a zero-width space hides the word", '("Cf", "Cc", "Cn", "Mn", "Me")', '("Cn", "Mn", "Me")'),
    "no-cn-strip": ("unassigned code points are kept: U+FFF0 or U+2065 hides the word (round 7)", '("Cf", "Cc", "Cn", "Mn", "Me")',
                    '("Cf", "Cc", "Mn", "Me")'),
    "no-clean": ("clean is not looked at", 'verb in ("fill", "build-adhoc", "clean")', 'verb in ("fill", "build-adhoc")'),
    "unsplittable-open": ("a command that can't be split is let through", "_report_word(rest) else None", "False else None"),
}

# the mutation test runs this subset (the file must finish inside run_tests.py's 900 s limit); GUARD_STEERCO_ALL_MUTATIONS=1 runs all
DEFAULT_MUTATIONS = ("drop-title-read", "unreadable-steerco-open", "expanduser-tilde", "no-filler-strip", "no-bidi-refuse",
                     "tilde-only-at-start", "no-equals-start", "no-reversed-match", "no-cn-strip")

WEEKLY = {"title": "Example Programme Weekly report"}
SPECS = {                                 # file name (relative to the drafts folder) -> content (a str is written as it is)
    "spec-a.json": WEEKLY, "spec-b.json": {"title": "Client report for the steering"},
    "spec-c.json": {"title": "Weekly status pack"}, "spec-d.json": {"title": "Quarterly reporting"},
    "spec-n.json": {"title": "Open risks register"}, "spec-n2.json": {"title": "Data access decisions"},
    "spec-s-client.json": {"code": "ABC", "version": "client"}, "spec-s-int.json": {"code": "ABC", "version": "internal"},
    "spec-s-none.json": {"code": "ABC"}, "spec-s-title.json": {"code": "ABC", "title": "Weekly report one-pager"},
    "spec-notitle.json": {"audience": "internal"}, "spec-bad.json": "this is not json", "spec-list.json": "[1, 2]",
    "spec-weekly-pack.json": "this is not json",     # unreadable, and its own name is report-named
    # a duplicate key: the script keeps the last value, the guard checks every one (and the other spellings of the key)
    "spec-dup1.json": '{"title": "Open risks register", "title": "Example Programme Weekly report"}',
    "spec-dup2.json": '{"title": "Example Programme Weekly report", "title": "Open risks register"}',
    "spec-dup3.json": '{"Title": "Example Programme Weekly report", "title": "Open risks register"}',
    "spec-dup-v.json": '{"code": "ABC", "version": "client", "version": "internal"}',
    "spec-dup-v2.json": '{"code": "ABC", "version": "internal", "version": "client"}',
    # lookalikes of the words
    "spec-acc1.json": {"title": "Wéekly pack"}, "spec-acc2.json": {"title": "Ｗｅｅｋｌｙ pack"},
    "spec-acc3.json": {"title": "Wee​kly pack"}, "spec-acc4.json": {"title": "Cliént list"},
    "spec-acc5.json": {"title": "Réport pack"},
    # blank-looking letters inside the words, and a right-to-left override
    "spec-fill1.json": {"title": "Wee\u3164kly re\u3164port"}, "spec-fill2.json": {"title": "Wee\uffa0kly pack"},
    "spec-fill3.json": {"title": "Wee\u2800kly pack"}, "spec-fill4.json": {"title": "Cli\u115fent list"},
    "spec-fill5.json": {"title": "Repo\u1160rt pack"}, "spec-fill6.json": {"title": "Wee\u17b4kly pack"},
    "spec-fill7.json": {"title": "Wee\u180ekly pack"}, "spec-fill8.json": {"title": "Wee\u2063kly pack"},
    # unassigned default-ignorable code points (round 7): U+FFF0 to U+FFF8, U+2065, the unassigned part of U+E0000
    "spec-cn1.json": {"title": "Example Wee\ufff0kly Rep\u2065ort"}, "spec-cn2.json": {"title": "Cli\U000e0000ent list"},
    "spec-cn3.json": {"title": "Wee\ufff8kly pack"},
    "spec-rlo.json": {"title": "\u202etroper ylkeeW"}, "spec-rev.json": {"title": "troper ylkeeW"},
    "spec-bidi.json": {"title": "Open \u2066risks\u2069 register"},
    # over 1 MB: the script reads it anyway
    "spec-big.json": {"title": "Example Programme Weekly report", "pad": "x" * 1_100_000},
    "spec-big-n.json": {"title": "Open risks register", "pad": "x" * 1_100_000},
    "spec-big-c.json": {"code": "ABC", "version": "client", "pad": "x" * 1_100_000},
}
ROOT_SPECS = {                           # relative to the vault root: the dash-led names report.py reads literally
    "-w.json": WEEKLY, "-": WEEKLY, "-c.json": {"code": "ABC", "version": "client"}, "-s.json": WEEKLY,
    "~/spec-n.json": WEEKLY,             # a folder literally called ~ in the vault: a quoted '~/...' reads this
}
HOME_SPECS = {"spec-n.json": {"title": "Open risks register"}}    # what an expanded ~ would find: neutral
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


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content if isinstance(content, str) else json.dumps(content, ensure_ascii=False), encoding="utf-8")


def _set_patches(root, reach, patched):
    """Leave reach.py with (or without) reach-steerco-adhoc.diff, and with round 7 on top of it unless NO_R7 (a diff the repo's
    reach.py already has is not applied again; round 7 comes off first, as it sits on a line the steerco diff adds)."""
    has = lambda marker: marker in reach.read_text(encoding="utf-8")        # noqa: E731
    if not patched and has(R7_MARKER):
        _patch(root, R7, "-R")
    if patched and not has(MARKER):
        _patch(root, DIFF)
    if not patched and has(MARKER):
        _patch(root, DIFF, "-R")
    if patched and not NO_R7 and not has(R7_MARKER):
        _patch(root, R7)
    if patched and NO_R7 and has(R7_MARKER):
        _patch(root, R7, "-R")


def scratch(patched, mutation=""):
    """A throwaway vault with a copy of the whole of system/scripts/, spec files (in its drafts folder and its root) and a fake home
    folder; reach.py with (or without) reach-steerco-adhoc.diff."""
    v = Vault()
    v.run("init")
    shutil.copytree(REPO / "system" / "scripts", v.root / "system" / "scripts", dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__"))
    for name, content in SPECS.items():
        _write(v.root / "system" / "staging" / "drafts" / name, content)
    for name, content in ROOT_SPECS.items():
        _write(v.root / name, content)
    v.home = Path(tempfile.mkdtemp(prefix="creaite-test-home-"))
    for name, content in HOME_SPECS.items():
        _write(v.home / name, content)
    reach = v.root / "system" / "scripts" / "reach.py"
    _set_patches(v.root, reach, patched)
    if mutation:
        _what, old, new = MUTATIONS[mutation]
        text = reach.read_text(encoding="utf-8")
        assert text.count(old) == 1, f"mutation {mutation}: {old!r} found {text.count(old)} times"
        reach.write_text(text.replace(old, new), encoding="utf-8")
    return v


def cleanup(v):
    v.cleanup()
    shutil.rmtree(v.home, ignore_errors=True)


def decisions(v, commands):
    r = subprocess.run([sys.executable, "-c", HARNESS], input=json.dumps([commands, list(MODES)]), cwd=v.root,
                       capture_output=True, text=True, timeout=300, env={**os.environ, "HOME": str(v.home)})
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def report_calls(root, specs, words, script="report.py"):
    """name -> command: each launcher, each spelling of the verb, each spec (a name in the drafts folder, or a literal word if it has
    no folder and starts with - or ~, or is given with a leading / or ./)."""
    out = {}
    for lname, launcher in LAUNCHERS.items():
        for spec in specs:
            arg = spec if spec.startswith(("-", "~", "'", "system/", "x=", "a:", "=")) else f"{D}{spec}"
            for w in words:
                out[f"{lname} | {w} | {spec}"] = launcher.format(s=script, ROOT=root) + f" {w} {arg}"
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
        calls[f"{lname} | build-adhoc, dashed template"] = (d(f"build-adhoc -t.docx {D}spec-n.json '{D}Weekly status.docx'", lname), True)
        calls[f"{lname} | fill, dashed template and values"] = (d(f"fill -t.docx -v.json '{D}Client list.docx'", lname), True)
        calls[f"{lname} | build-adhoc, dashed report-titled spec"] = (d(f"build-adhoc {TEMPLATE} -s.json {D}out.docx", lname), True)
        calls[f"{lname} | build-adhoc, oversized spec"] = (d(f"build-adhoc {TEMPLATE} {D}spec-big-n.json {D}out.docx", lname), True)
        calls[f"{lname} | build-adhoc, accented title"] = (d(f"build-adhoc {TEMPLATE} {D}spec-acc1.json {D}out.docx", lname), True)
        calls[f"{lname} | clean into a report-named file"] = (d(f"clean {D}spec-n.docx 'system/staging/drafts/Example Client pack.docx'", lname), True)
        calls[f"{lname} | clean in place, report-named"] = (d("clean 'system/staging/drafts/Example Client pack.docx'", lname), True)
        calls[f"{lname} | clean, dashed input"] = (d(f"clean -x.docx '{D}Weekly pack.docx'", lname), True)
        calls[f"{lname} | clean, spliced"] = (d(f"cl''ean {D}a.docx {D}client.docx", lname), True)
        calls[f"{lname} | fill, tilde after ="] = (d(f"fill x=~/t.docx {D}spec-n.json {D}out.docx", lname), True)
        calls[f"{lname} | fill, tilde in the output"] = (d(f"fill {TEMPLATE} {D}spec-n.json {D}out~.docx", lname), True)
        calls[f"{lname} | fill, = first"] = (d(f"fill =t {D}spec-n.json {D}out.docx", lname), True)
        calls[f"{lname} | build-adhoc, tilde spec"] = (d(f"build-adhoc {TEMPLATE} a:~/s.json {D}out.docx", lname), True)
        calls[f"{lname} | clean, tilde"] = (d("clean x=~/a.docx", lname), True)
        for tag, name in (("hangul filler", "Wee\u3164kly status"), ("halfwidth filler", "Wee\uffa0kly"), ("braille blank", "Client\u2800 list"),
                          ("bidi override", "\u202etroper"), ("reversed", "ylkeeW pack"), ("zero-width joiner", "Re\u2063port pack"),
                          ("unassigned U+FFF0", "Wee\ufff0kly"), ("unassigned U+2065", "Re\u2065port pack")):
            calls[f"{lname} | fill, {tag} in the output name"] = (d(f"fill {TEMPLATE} {D}spec-n.json '{D}{name}.docx'", lname), True)
            calls[f"{lname} | clean, {tag} in the output name"] = (d(f"clean {D}a.docx '{D}{name}.docx'", lname), True)
        calls[f"{lname} | fill, too few arguments"] = (d(f"fill {TEMPLATE} {D}out.docx", lname), True)
        calls[f"{lname} | build-adhoc, too many arguments"] = (d(f"build-adhoc {TEMPLATE} {D}spec-n.json {D}out.docx extra", lname), True)
        calls[f"{lname} | clean, no arguments"] = (d("clean", lname), True)
        calls[f"{lname} | fill, neutral"] = (d(f"fill {TEMPLATE} {D}spec-n.json {D}out.docx", lname), False)
        calls[f"{lname} | fill, dashed template, neutral file"] = (d(f"fill -t.docx -v.json {D}out.docx", lname), False)
        calls[f"{lname} | build-adhoc, neutral"] = (d(f"build-adhoc {TEMPLATE} {D}spec-n.json '{D}Open risks.docx'", lname), False)
        calls[f"{lname} | clean, neutral in place"] = (d(f"clean {D}out.docx", lname), False)
        calls[f"{lname} | clean, neutral into"] = (d(f"clean {D}a.docx {D}b.docx", lname), False)
    return calls


REFUSED_ADHOC = ("spec-a.json", "spec-b.json", "spec-c.json", "spec-d.json", "spec-weekly-pack.json", "spec-dup1.json", "spec-dup2.json",
                 "spec-dup3.json", "spec-acc1.json", "spec-acc2.json", "spec-acc3.json", "spec-acc4.json", "spec-acc5.json",
                 "spec-fill1.json", "spec-fill2.json", "spec-fill3.json", "spec-fill4.json", "spec-fill5.json", "spec-fill6.json",
                 "spec-fill7.json", "spec-fill8.json", "spec-cn1.json", "spec-cn2.json", "spec-cn3.json", "spec-rlo.json", "spec-rev.json", "spec-bidi.json",
                 "spec-big.json", "spec-big-n.json", "spec-bad.json", "spec-list.json", "spec-missing.json")
REFUSED_STEERCO = ("spec-s-client.json", "spec-s-title.json", "spec-dup-v2.json", "spec-dup-v.json", "spec-big-c.json", "spec-bad.json",
                   "spec-missing.json", "spec-list.json")
DASHED_ADHOC = ("-w.json", "-", "-s.json", "'~/spec-n.json'", "~/spec-n.json", "x=~/spec-n.json", "a:~/spec-n.json", "'a~b.json'",
                "system/staging/drafts/spec~n.json", "=spec-n.json", "=ls")        # step 2 of the review's bypasses (steps 1: filechange create)
DASHED_STEERCO = ("-c.json", "'~/spec-n.json'", "x=~/spec-s-int.json", "=spec-s-int.json")
ALLOWED_ADHOC = ("spec-n.json", "spec-n2.json", "spec-notitle.json")
ALLOWED_STEERCO = ("spec-s-int.json", "spec-s-none.json")
ODD_SHAPES = ("python3 system/scripts/report.py adhoc", "python3 system/scripts/report.py adhoc system/staging/drafts/spec-n.json x",
              "python3 system/scripts/report.py steerco-stage", "python3 system/scripts/report.py steerco-stage a b")
READS = ("python3 system/scripts/report.py adhoc-data ABC", "system/scripts/run report.py steerco-data ABC",
         "python3 system/scripts/report.py weekly-data ABC", "system/scripts/run report.py client-data ABC",
         "python3 system/scripts/docx_tools.py text system/templates/adhoc-template.docx",
         "system/scripts/run docx_tools.py status system/templates/adhoc-template.docx")
# NOT covered by this diff (the README says so): the draft is not made by one of these builders, or its name comes from somewhere else
STILL_ALLOWED = (
    "python3 system/scripts/filechange.py create 'system/staging/drafts/Weekly status.docx' --from system/staging/drafts/spec-n.json --why x",
    "python3 system/scripts/filechange.py create 'system/staging/drafts/Example Client pack.docx' --from system/staging/drafts/spec-n.json --why x",
)


class Builders(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patched = scratch(patched=not UNPATCHED, mutation=MUTATE)
        cls.base = scratch(patched=False)
        r = str(cls.patched.root)
        cls.refused = {**report_calls(r, REFUSED_ADHOC, ADHOC_WORDS), **report_calls(r, REFUSED_STEERCO, STEERCO_WORDS),
                       **report_calls(r, DASHED_ADHOC, ADHOC_WORDS), **report_calls(r, DASHED_STEERCO, STEERCO_WORDS[:2])}
        cls.odd = {f"odd | {c}": c for c in ODD_SHAPES}
        cls.allowed = {**report_calls(r, ALLOWED_ADHOC, ADHOC_WORDS[:2]), **report_calls(r, ALLOWED_STEERCO, STEERCO_WORDS[:2])}
        cls.docx = docx_calls(r)
        cls.got = decisions(cls.patched, list(cls.refused.values()) + list(cls.odd.values()) + list(cls.allowed.values())
                            + [c for c, _ in cls.docx.values()] + list(READS) + list(STILL_ALLOWED))

    @classmethod
    def tearDownClass(cls):
        cleanup(cls.patched)
        cleanup(cls.base)

    def assert_refused(self, cmd):
        for mode in MODES:
            self.assertFalse(self.got["decide"][mode][cmd][0], f"{mode} lets it through: {cmd!r}")
        for mode in ("ask", "confirmed", "sweep"):          # the modes the report rule (ask_bash_refusal) is in
            reason = self.got["decide"][mode][cmd][1]
            # (with reach.diff applied too, an unquoted ~ inside a word is refused earlier, by its pattern rule)
            self.assertTrue(WHY in reason or ("wildcard or pattern character" in reason and "~" in cmd), (mode, cmd, reason))

    def test_a_report_named_adhoc_or_steerco_draft_is_refused_in_every_mode(self):
        for name, cmd in self.refused.items():
            with self.subTest(name):
                self.assert_refused(cmd)

    def test_an_argument_shape_the_scripts_would_not_run_is_refused(self):
        for name, cmd in self.odd.items():
            with self.subTest(name):
                self.assert_refused(cmd)

    def test_docx_tools_fill_build_adhoc_and_clean_with_a_report_named_file_or_title_are_refused(self):
        for name, (cmd, refused) in self.docx.items():
            if refused:
                with self.subTest(name):
                    self.assert_refused(cmd)

    def test_ordinary_documents_and_internal_one_pagers_stay_allowed(self):
        for name, cmd in self.allowed.items():
            with self.subTest(name):
                for mode in ("ask", "confirmed", "sweep"):
                    self.assertEqual(self.got["decide"][mode][cmd], [True, ""], (mode, cmd))

    def test_neutral_docx_tools_runs_stay_allowed(self):
        for name, (cmd, refused) in self.docx.items():
            if not refused:
                with self.subTest(name):
                    for mode in ("ask", "confirmed", "sweep"):
                        self.assertEqual(self.got["decide"][mode][cmd], [True, ""], (mode, cmd))

    def test_reads_stay_allowed(self):
        for cmd in READS:
            with self.subTest(cmd):
                for mode in ("ask", "confirmed", "sweep"):
                    self.assertEqual(self.got["decide"][mode][cmd], [True, ""], (mode, cmd))

    def test_what_this_diff_does_not_cover_is_still_allowed(self):
        """Documented in the README, so a later change that closes one must update both."""
        for cmd in STILL_ALLOWED:
            with self.subTest(cmd):
                self.assertEqual(self.got["decide"]["ask"][cmd], [True, ""], cmd)

    def test_an_unsplittable_command_fails_closed(self):
        self.assertIn(WHY, self.got.get("unsplittable") or "")
        self.assertIsNone(self.got.get("unsplittable_neutral"))

    def test_nothing_else_changes(self):
        """The allowed and read commands are decided exactly as on the unpatched file."""
        cmds = list(self.allowed.values()) + [c for c, refused in self.docx.values() if not refused] + list(READS) + list(STILL_ALLOWED)
        base_cmds = [c.replace(str(self.patched.root), str(self.base.root)) for c in cmds]
        base = decisions(self.base, base_cmds)
        for mode in MODES:
            self.assertEqual([self.got["decide"][mode][c] for c in cmds], [base["decide"][mode][c] for c in base_cmds], mode)


class Premise(unittest.TestCase):
    """The bypasses are real: report.py takes these arguments as the spec, and writes a report-named draft (run for real in a throwaway
    vault, with the argument list a shell would pass)."""

    @classmethod
    def setUpClass(cls):
        cls.v = scratch(patched=False)

    @classmethod
    def tearDownClass(cls):
        cleanup(cls.v)

    def drafts(self):
        return {p.name for p in (self.v.root / "system" / "staging" / "drafts").glob("*Weekly report*.docx")}

    def run_adhoc(self, spec):
        r = subprocess.run([sys.executable, str(self.v.root / "system" / "scripts" / "report.py"), "adhoc", spec], cwd=self.v.root,
                           capture_output=True, text=True, env={**os.environ, "HOME": str(self.v.home), "CREAITE_NO_LAUNCH": "1"})
        return r

    def test_a_dash_led_spec_a_dash_and_a_quoted_tilde_are_read_literally_and_oversized_is_read(self):
        for spec in ("-w.json", "-", "~/spec-n.json", f"{D}spec-big.json", f"{D}spec-dup1.json"):
            with self.subTest(spec):
                before = self.drafts()
                r = self.run_adhoc(spec)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                self.assertGreater(len(self.drafts()), len(before), spec)       # a report-named draft was written


class ShellPremise(unittest.TestCase):
    """What the shell does that the guard can't see: bash expands a ~ after an = in an argument."""

    def test_bash_expands_a_tilde_after_an_equals_sign(self):
        bash = shutil.which("bash")
        if not bash:
            self.skipTest("bash is not installed")
        r = subprocess.run([bash, "-c", "printf '%s' x=~/spec-n.json"], capture_output=True, text=True, env={**os.environ, "HOME": "/fake-home"})
        self.assertEqual(r.stdout, "x=/fake-home/spec-n.json")


class Hole(unittest.TestCase):
    """The hole is real on the unpatched file (so the proposal is needed)."""

    def test_unpatched_lets_report_named_drafts_through(self):
        v = scratch(patched=False)
        try:
            r = str(v.root)
            cmds = [*report_calls(r, ("spec-a.json",), ("adhoc", "'adhoc'")).values(),
                    *report_calls(r, ("spec-s-client.json",), ("steerco-stage", "'steerco-stage'")).values(),
                    *report_calls(r, ("-w.json", "-", "spec-big.json", "spec-dup1.json"), ("adhoc",)).values(),
                    "python3 system/scripts/report.py steerco-stage -c.json",
                    f"python3 system/scripts/docx_tools.py fill {TEMPLATE} {D}spec-n.json '{D}Weekly status.docx'",
                    f"python3 system/scripts/docx_tools.py clean {D}a.docx 'system/staging/drafts/Example Client pack.docx'",
                    f"system/scripts/run docx_tools.py build-adhoc {TEMPLATE} {D}spec-a.json {D}out.docx"]
            got = decisions(v, cmds)
            for cmd in cmds:
                with self.subTest(cmd):
                    for mode in ("ask", "confirmed", "sweep"):
                        self.assertEqual(got["decide"][mode][cmd], [True, ""], (mode, cmd))
        finally:
            cleanup(v)


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
                    if R7_MARKER not in reach.read_text(encoding="utf-8"):
                        _patch(v.root, R7)                  # round 7 comes last: it edits a line the steerco diff adds
                    r = str(v.root)
                    refused = report_calls(r, ("spec-a.json",), ("'adhoc'",))["python3 | 'adhoc' | spec-a.json"]
                    dashed = report_calls(r, ("-w.json",), ("adhoc",))["python3 | adhoc | -w.json"]
                    allowed = report_calls(r, ("spec-n.json",), ("adhoc",))["python3 | adhoc | spec-n.json"]
                    stage = "python3 system/scripts/report.py 'weekly-stage' system/staging/drafts/spec-n.json"
                    unassigned = report_calls(r, ("spec-cn1.json",), ("adhoc",))["python3 | adhoc | spec-cn1.json"]
                    got = decisions(v, [refused, dashed, allowed, stage, unassigned])
                    for mode in MODES:
                        for cmd in (refused, dashed, stage, unassigned):     # the report diff and this one together
                            self.assertFalse(got["decide"][mode][cmd][0], (mode, cmd))
                    for mode in ("ask", "confirmed", "sweep"):
                        self.assertEqual(got["decide"][mode][allowed], [True, ""], mode)
                finally:
                    cleanup(v)


class Mutations(unittest.TestCase):
    @unittest.skipIf(UNPATCHED or MUTATE, "the mutation runs are the parent's job")
    def test_each_mutation_turns_a_test_red(self):
        names = MUTATIONS if os.environ.get("GUARD_STEERCO_ALL_MUTATIONS") == "1" else DEFAULT_MUTATIONS
        for name in names:
            what = MUTATIONS[name][0]
            with self.subTest(name):
                r = subprocess.run([sys.executable, str(Path(__file__).resolve()), "Builders"], cwd=REPO, capture_output=True, text=True,
                                   env={**os.environ, "GUARD_STEERCO_MUTATE": name}, timeout=900)
                self.assertNotEqual(r.returncode, 0, f"mutation {name} ({what}) left every test green")
                self.assertIn("FAILED", r.stderr)
                self.assertNotIn("AssertionError: mutation", r.stderr)      # a real failure, not a mutation that no longer applies


if __name__ == "__main__":
    unittest.main()
