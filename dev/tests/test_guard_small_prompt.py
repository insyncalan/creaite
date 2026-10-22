"""guard-small (2), #269 round 2 delta LOW 2: no PERMISSION example in ask creaite's prompt names a path on reach's never list or
asks for a rule the panel always refuses. PROPOSAL test for dev/proposals/guard-small/live-server-prompt.diff (live_server.py is
a guarded file).

Run: python3 dev/tests/test_guard_small_prompt.py
Fail-first: GUARD_SMALL_UNPATCHED=1 python3 dev/tests/test_guard_small_prompt.py

The prompt gave `PERMISSION: Write(system/search/**) | to save summaries` as its example; since #269 M-B system/search is on the
never list for writes, and the panel refuses every Edit or Write rule anyway (ask creaite changes files through filechange.py), so
the example only led to a useless card. Each example is read from the prompt (live_server.ASK_PROMPT in a scratch copy) and its
paths are put through reach.classify: none may be "never", and none may be an Edit or Write rule.
"""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guard_small_support import in_vault, mutants_caught, scratch  # noqa: E402

DIFFS = ("live-server-prompt.diff",)       # it also changes permissions.py (check: reach.py hook and wrap)
L = "system/scripts/live_server.py"
EXAMPLE = '"Bash(python3 system/scripts/<name>.py <subcommand> *) | <why> for a script'
MUTATIONS = {
    "search-write-back": ("the old Write(system/search/**) example", L, EXAMPLE,
                          '"Write(system/search/**) | to save summaries, or PERMISSION: Bash(python3 system/scripts/<name>.py <subcommand> *) | <why> for a script'),
    "ssh-read": ("an example reading a never-list folder", L, EXAMPLE,
                 '"Read(~/.ssh/**) | to check keys, or PERMISSION: Bash(python3 system/scripts/<name>.py <subcommand> *) | <why> for a script'),
    "path-rules-accepted": ("the prompt says a path rule is accepted again", L, '"for a creaite script is accepted. Never edit',
                            '"for a creaite script or a path inside one project\'s folder is accepted. Never edit'),
    "reach-addable": ("a reach.py hook rule is addable again", "system/scripts/permissions.py",
                      '    if tool == "Bash" and re.search(r"reach\\.py(?!', '    if False and re.search(r"reach\\.py(?!'),
    "project-edit": ("an Edit rule the panel always refuses", L, EXAMPLE,
                     '"Edit(projects/ABC Example Programme/documents/**) | to save it, or PERMISSION: Bash(python3 system/scripts/<name>.py <subcommand> *) | <why> for a script'),
}

# every PERMISSION example in the prompt, each path in it put through reach.classify
CODE = r'''
import os, re, reach, live_server
p = live_server.ASK_PROMPT
out = []
for rule in re.findall(r"PERMISSION:\s*(.+?)\s*\|", p):
    if rule.startswith("<"):
        continue                                          # the placeholder "<the rule>"
    m = re.fullmatch(r"(\w+)\((.*)\)", rule.strip())
    tool, spec = (m.group(1), m.group(2)) if m else ("?", rule)
    words = spec.split() if tool == "Bash" else [spec]
    verdicts = []
    for w in words:
        if "/" not in w:
            continue
        w = re.sub(r"(/\*\*|/\*|\*)$", "", w).replace("<name>", "search")
        op = "read" if tool in ("Bash", "Read", "Grep", "Glob", "LS") else "create"
        verdicts.append([w, op, reach.classify(os.path.expanduser(w), op)[0]])
    out.append({"rule": rule, "tool": tool, "verdicts": verdicts})
import permissions
rules = ["Bash(python3 system/scripts/reach.py hook *)", "Bash(system/scripts/run reach.py hook *)",
         "Bash(python3 system/scripts/reach.py wrap *)", "Bash(python3 system/scripts/reach.py *)",
         "Bash(python3 system/scripts/reach.py classify *)"]
print(json.dumps({"examples": out, "prompt": p, "states": {r: permissions.check_full(r)["state"] for r in rules}}))
'''


class PromptExamplesAreUsable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = scratch(DIFFS, MUTATIONS)
        got = in_vault(cls.v, CODE, timeout=120)
        cls.got, cls.prompt, cls.states = got["examples"], got["prompt"], got["states"]

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_the_prompt_still_gives_an_example(self):
        self.assertTrue(self.got, "no PERMISSION example left in the prompt")
        self.assertTrue(any(e["tool"] == "Bash" for e in self.got), self.got)

    def test_no_example_names_a_never_list_path(self):
        for e in self.got:
            for path, op, kind in e["verdicts"]:
                with self.subTest(rule=e["rule"], path=path):
                    self.assertNotEqual(kind, "never", f"{e['rule']}: {path} ({op}) is on the never list")

    def test_no_example_is_an_edit_or_write_rule(self):
        for e in self.got:
            with self.subTest(rule=e["rule"]):
                self.assertNotIn(e["tool"], ("Edit", "Write", "MultiEdit", "NotebookEdit"),
                                 f"{e['rule']}: the panel refuses every Edit or Write rule")


    def test_the_prompt_never_says_a_path_rule_is_accepted(self):
        self.assertNotIn("path inside one project", self.prompt)
        self.assertIn("only a rule for a creaite script is accepted", self.prompt)

    def test_a_reach_hook_or_wrap_rule_is_never_addable(self):
        """The guard's own hand-over commands are never offered as a rule on the card (the hook refuses them anyway)."""
        for rule, state in self.states.items():
            if "classify" not in rule:
                with self.subTest(rule):
                    self.assertNotEqual(state, "addable", rule)


@unittest.skipIf(os.environ.get("GUARD_SMALL_MUTATE") or os.environ.get("GUARD_SMALL_UNPATCHED"), "the mutation run itself")
class Mutants(unittest.TestCase):
    def test_every_mutation_is_caught(self):
        missed = mutants_caught(Path(__file__), MUTATIONS, ["PromptExamplesAreUsable"])
        self.assertEqual(missed, [], "mutations the tests didn't notice")


if __name__ == "__main__":
    unittest.main()
