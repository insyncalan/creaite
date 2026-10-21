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

DIFFS = ("live-server-prompt.diff",)
L = "system/scripts/live_server.py"
EXAMPLE = '"Bash(python3 system/scripts/<name>.py <subcommand> *) | <why> for a script'
MUTATIONS = {
    "search-write-back": ("the old Write(system/search/**) example", L, EXAMPLE,
                          '"Write(system/search/**) | to save summaries, or PERMISSION: Bash(python3 system/scripts/<name>.py <subcommand> *) | <why> for a script'),
    "ssh-read": ("an example reading a never-list folder", L, EXAMPLE,
                 '"Read(~/.ssh/**) | to check keys, or PERMISSION: Bash(python3 system/scripts/<name>.py <subcommand> *) | <why> for a script'),
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
print(json.dumps(out))
'''


class PromptExamplesAreUsable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = scratch(DIFFS, MUTATIONS)
        cls.got = in_vault(cls.v, CODE, timeout=120)

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


@unittest.skipIf(os.environ.get("GUARD_SMALL_MUTATE") or os.environ.get("GUARD_SMALL_UNPATCHED"), "the mutation run itself")
class Mutants(unittest.TestCase):
    def test_every_mutation_is_caught(self):
        missed = mutants_caught(Path(__file__), MUTATIONS, ["PromptExamplesAreUsable"])
        self.assertEqual(missed, [], "mutations the tests didn't notice")


if __name__ == "__main__":
    unittest.main()
