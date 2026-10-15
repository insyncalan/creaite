"""#92: an apply refused because a file changed after the item was staged is said in plain words on the dashboard, with what
to do. tracker.py's refusal is unchanged; the page maps it (core/server.js applyWords, used by applyNow and the save path).

Run: python3 dev/tests/test_refused_apply_words.py   (needs node)
"""
import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import ABC, Vault, action  # noqa: E402

SRC = Path(__file__).resolve().parents[2] / "system/templates/dashboard/src/core/server.js"


def words(message):
    code = re.search(r"export const applyWords=.*?\n.*?;\s*\};", SRC.read_text(), re.S).group(0).replace("export ", "")
    out = subprocess.run(["node", "-e", code + "\nprocess.stdout.write(JSON.stringify(applyWords(JSON.parse(process.argv[1]))))",
                          json.dumps(message)], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


@unittest.skipUnless(shutil.which("node"), "needs node")
class RefusedApplyWords(unittest.TestCase):
    def test_real_refusal_becomes_plain_words(self):
        v = Vault()
        self.addCleanup(v.cleanup)
        path = f"{ABC}/CLAUDE.md"
        v.run("init")
        v.propose("seed", [action(1)])
        v.run("apply")
        old = (v.root / path).read_text()
        spec = v.root / "system/staging/drafts/one.json"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text(json.dumps({"file_changes": {"title": "one", "file_ops": [
            {"op": "write", "path": path, "content": old + "- Mine.\n", "previous": old}]}}))
        v.run("stage", str(spec), script="propose.py")
        (v.root / path).write_text(old + "- Changed elsewhere.\n")
        r = v.run("apply", ok=False)
        raw = (r.stdout + r.stderr).strip()
        self.assertIn("changed since this proposal was made", raw)       # what the server passes through today
        shown = words(raw)
        self.assertIn("CLAUDE.md changed after this item was staged", shown)
        self.assertIn("Stage it again", shown)
        self.assertIn("drop it in Review", shown)
        self.assertNotIn("proposal", shown)
        self.assertNotIn("Apply failed", shown)

    def test_other_messages_pass_through(self):
        self.assertEqual(words("Nothing to apply: no decided items."), "Nothing to apply: no decided items.")
        self.assertEqual(words("Apply failed; nothing was written. Invalid: x"), "Apply failed; nothing was written. Invalid: x")

    def test_failed_apply_line_form(self):
        m = "Apply failed; nothing was written. Invalid: write: projects/_portfolio/people-register.md changed since this proposal was made"
        self.assertTrue(words(m).startswith("people-register.md changed after this item was staged"))


if __name__ == "__main__":
    unittest.main()
