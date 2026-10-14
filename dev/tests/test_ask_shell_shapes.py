"""ask creaite never needs a shell redirect, pipe or /tmp (defect from 11-10-2026: `propose.py new-project … > /tmp/x.json` refused).

Run: python3 dev/tests/test_ask_shell_shapes.py
Two guarantees: (1) the commands that only printed a spec to be kept (propose.py new-project and close-project) can save it with
--out, in system/staging/drafts/ and nowhere else; (2) no skill or rules file shows a creaite command in a shape the guard refuses
(a redirect, a pipe into another program, `&&`, `2>&1`, a heredoc, `$(…)` or /tmp), since ask creaite copies what the docs show.
"""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import Vault, action  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system/scripts"))
import reach  # noqa: E402

DOCS = sorted((REPO / ".claude/skills").glob("*/SKILL.md")) + sorted((REPO / ".claude/skills").glob("*/references/*.md")) + [
    REPO / "system/creaite-rules.md"]
SPAN = re.compile(r"`(python3? system/scripts/[^`]+)`")
BAD = re.compile(r"(?:\s>>?\s*\S|2>&1|&&|<<|\$\(|\s\|\s+(?:python|grep|head|tail|jq|tee|cat|sort|wc)\b|/tmp/)")


class DocsShowOnlyAllowedShapes(unittest.TestCase):
    def test_no_command_in_the_docs_uses_a_refused_shape(self):
        bad = []
        for f in DOCS:
            for m in SPAN.finditer(f.read_text(encoding="utf-8")):
                if BAD.search(m.group(1)):
                    bad.append(f"{f.relative_to(REPO)}: {m.group(1)[:90]}")
        self.assertEqual(bad, [], "a doc shows a command the guard refuses")

    def test_the_guard_still_refuses_a_redirect_and_says_what_to_do(self):
        why = reach.bash_problem('python3 system/scripts/propose.py new-project --code MER --name "X" > /tmp/m.json')
        self.assertIn("--out", why)
        self.assertIn("Write tool", why)
        self.assertIsNone(reach.bash_problem('python3 system/scripts/propose.py new-project --code MER --name "X" --out p.json'))


class SpecOut(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.v.propose("seed", [action(1)])
        self.v.run("apply")
        self.drafts = self.v.root / "system/staging/drafts"

    def tearDown(self):
        self.v.cleanup()

    def p(self, *args, ok=True):
        return self.v.run(*args, script="propose.py", ok=ok)

    def test_new_project_out_saves_the_spec_and_it_previews_and_stages(self):
        r = self.p("new-project", "--code", "DEF", "--name", "Digital Enablement", "--out", "new-project.json")
        self.assertIn("system/staging/drafts/new-project.json", r.stdout)
        self.assertNotIn('"source_run"', r.stdout)
        f = self.drafts / "new-project.json"
        self.assertEqual(json.loads(f.read_text())["items"][0]["values"]["code"], "DEF")
        self.assertIn("New project: ", self.p("preview", str(f)).stdout)
        self.p("stage", str(f))
        self.assertFalse(f.exists(), "stage removes the draft it consumed")
        self.v.run("apply")
        self.assertIn("DEF", [p["code"] for p in self.v.rows("projects")])

    def test_without_out_the_spec_is_still_printed(self):
        out = self.p("new-project", "--code", "DEF", "--name", "Digital Enablement").stdout
        self.assertEqual(json.loads(out)["items"][0]["values"]["code"], "DEF")
        self.assertEqual(list(self.drafts.glob("*.json")) if self.drafts.exists() else [], [])

    def test_out_never_overwrites_and_takes_a_bare_name_only(self):
        for _ in range(2):
            self.p("new-project", "--code", "DEF", "--name", "Digital Enablement", "--out", "np")
        self.assertEqual(sorted(x.name for x in self.drafts.glob("np*.json")), ["np-2.json", "np.json"])
        for bad in ("../x.json", "sub/x.json", "/tmp/x.json", ".hidden"):
            r = self.p("new-project", "--code", "DEF", "--name", "Digital Enablement", "--out", bad, ok=False)
            self.assertIn("file name only", r.stderr)
        self.assertEqual(sorted(x.name for x in self.drafts.glob("*")), ["np-2.json", "np.json"])

    def test_close_project_out(self):
        r = self.p("close-project", "ABC", "--out", "close-abc.json")
        self.assertIn("system/staging/drafts/close-abc.json", r.stdout)
        spec = json.loads((self.drafts / "close-abc.json").read_text())
        self.assertEqual(spec["items"][0]["changes"], {"active": 0})
        self.assertEqual(json.loads(self.p("close-project", "ABC").stdout)["items"][0]["id"], "ABC")


if __name__ == "__main__":
    unittest.main()
