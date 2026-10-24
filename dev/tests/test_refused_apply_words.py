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
    code = re.search(r"export const applyTitle=.*?(?=\n/\* #280: an apply that stopped)", SRC.read_text(), re.S).group(0).replace("export ", "")
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
        self.assertIn("A file changed after this suggestion was made", shown)
        self.assertIn("Make the suggestion again", shown)
        self.assertIn("drop it in Intake", shown)
        self.assertNotIn("CLAUDE.md", shown)                    # #291 Tier 1: never a file name
        self.assertNotIn("proposal", shown)
        self.assertNotIn("Apply failed", shown)

    def test_other_messages_pass_through(self):
        for line in ("Nothing to apply: no decided items.", "Nothing to save: no decided items."):     # tracker.py's wording today, and after #292's change
            self.assertEqual(words(line), line)
        failed = words("Apply failed; nothing was written. Invalid: x")           # #275 (Cap's 1): a failure Review can't fix
        self.assertIn("nothing was changed", failed)
        self.assertIn("Diagnostics", failed)
        self.assertNotIn("Review", failed)

    def test_the_recode_refusal_and_a_stop_are_not_sent_to_review_to_fix(self):
        recode = "Apply stopped. Nothing was written.\n  proposed-x.json: a recode is applied on its own, with no other items in its proposal."
        shown = words(recode)
        self.assertIn("has to go through on its own", shown)
        self.assertIn("ask for the code change again", shown)
        self.assertNotIn("needs fixing", shown)
        self.assertNotIn("proposed-", shown)
        stop = words("Apply stopped. Nothing was written.\n  proposed-x.json something new")
        self.assertIn("Diagnostics", stop)
        self.assertNotIn("needs fixing in Review", stop)

    def test_failed_apply_line_form(self):
        m = "Apply failed; nothing was written. Invalid: write: projects/_portfolio/people-register.md changed since this proposal was made"
        self.assertTrue(words(m).startswith("A file changed after this suggestion was made"))

    def test_track_refusal_drops_the_header_and_the_file_name(self):
        """#275 round 3 (Cap's 3): the page says "Apply stopped" itself; the proposal's file name is never shown."""
        m = ("Apply stopped. Nothing was written.\n  proposed-2026-10-01-x.json item 2: crossed in the minutes' Track column; "
             "it is back on Intake\n  proposed-2026-10-01-x.json minutes: the minutes record can't be read (gone), so its Track "
             "column can't be checked")
        shown = words(m)
        self.assertEqual(shown.split("\n")[0], "an item was crossed in the minutes' Track column; it is back on Intake")
        self.assertTrue(shown.split("\n")[1].startswith("the minutes record can't be read"))
        self.assertNotIn("proposed-", shown)
        self.assertNotIn("Apply stopped", shown)
        other = "Apply stopped. Nothing was written.\n  proposed-x.json item 1: invalid owner"
        self.assertEqual(words(other), "One suggestion couldn't be saved. It needs fixing in Intake. Nothing was saved.")   # #291 Tier 1
        field = ("Apply stopped. Nothing was written.\n  proposed-2026-10-22-0905-sweep.json item 1: unknown field(s) for decisions: raised. "
                 "Valid: project, decision, made_by")
        shown = words(field)
        for banned in ("proposed-", ".json", "Valid", "unknown field", "Apply stopped"):
            self.assertNotIn(banned, shown)

    def test_missing_source_says_the_transcript_is_gone(self):                  # #291 Tier 1
        m = ("Apply stopped. Nothing was written.\n  proposed-2026-10-22-0910-minutes.json minutes_decision: copy: source not "
             "found (inbox/Recording - X.vtt)")
        shown = words(m)
        self.assertIn("couldn't be filed: the transcript isn't in your inbox any more", shown)
        self.assertNotIn("inbox/", shown)
        self.assertNotIn(".vtt", shown)


if __name__ == "__main__":
    unittest.main()
